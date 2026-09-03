"""Playlist reordering over the web API, independent of the playback engine."""

import json
import re
import threading
import time

from . import amp_api, audit_log

# Serialize reorders in this process. A fresh read before PUT also catches edits
# by other clients; the remote API does not provide an atomic compare-and-swap.
_LOCK = threading.Lock()
_VERIFY_ATTEMPTS = 3
_VERIFY_DELAY = 0.5
_TRACK_TYPES = {"library-songs", "library-music-videos", "songs", "music-videos"}


def _positions(order: str, from_position: int, to_position: int) -> list[int] | None:
    """Parse one-based positions, rejecting mixed or incomplete instructions."""
    if order.strip():
        if from_position or to_position:
            raise ValueError("Use either order or from_position/to_position, not both")
        if order.lstrip().startswith("["):
            try:
                positions = json.loads(order)
            except ValueError as exc:
                raise ValueError("order must be a JSON array or comma-separated positions") from exc
        else:
            parts = re.split(r"[,\n]", order.strip())
            if any(not re.fullmatch(r"[0-9]+", part.strip()) for part in parts):
                raise ValueError("order must contain positive integer positions, e.g. '3,1,2'")
            positions = [int(part.strip()) for part in parts]
        if (
            not isinstance(positions, list)
            or not positions
            or any(type(pos) is not int or pos < 1 for pos in positions)
        ):
            raise ValueError("order must contain positive integer positions, e.g. '[3,1,2]'")
        return positions
    if any(type(pos) is not int or pos < 1 for pos in (from_position, to_position)):
        raise ValueError("Provide order, or positive from_position and to_position (1-based)")
    return None


def _references(tracks: list[dict]) -> list[dict]:
    """Preserve each occurrence, ID and media type; never omit an unknown item."""
    refs = []
    for track in tracks:
        item_id, item_type = track.get("id"), track.get("type")
        if not isinstance(item_id, str) or not item_id or item_type not in _TRACK_TYPES:
            raise ValueError(
                "Playlist contains a missing ID or unsupported media type; reorder cancelled"
            )
        refs.append({"id": item_id, "type": item_type})
    return refs


def _preview(name: str, tracks: list[dict], positions: list[int]) -> str:
    lines = [f"Preview reorder of '{name}' ({len(tracks)} tracks; no changes made):"]
    for new_pos, old_pos in enumerate(positions[:50], 1):
        track = tracks[old_pos - 1]
        attrs = track.get("attributes") or {}
        title = attrs.get("name") or track["id"]
        artist = f" — {attrs['artistName']}" if attrs.get("artistName") else ""
        lines.append(f"{new_pos}. {title}{artist} [{track['id']}; was #{old_pos}]")
    if len(positions) > 50:
        lines.append(f"… {len(positions) - 50} more tracks")
    return "\n".join(lines)


def reorder_playlist(
    playlist: str,
    *,
    order: str = "",
    from_position: int = 0,
    to_position: int = 0,
    dry_run: bool = False,
    verify: bool = True,
) -> str:
    """Move an entry or apply a full permutation of the current stored positions.

    A reorder preserves the playlist ID and every track occurrence. The second
    complete read aborts on concurrent edits, and a failed verification is never
    reported as success. No automatic write retries or destructive rollback.
    """
    try:
        if not playlist.strip():
            raise ValueError("playlist is required for reorder")
        requested = _positions(order, from_position, to_position)
        with _LOCK:
            return _reorder(playlist, requested, from_position, to_position, dry_run, verify)
    except Exception as exc:
        return f"Error: {exc}"


def _reorder(
    playlist: str,
    requested: list[int] | None,
    from_position: int,
    to_position: int,
    dry_run: bool,
    verify: bool,
) -> str:
    target = amp_api.get_playlist_for_reorder(playlist)
    playlist_id = target["id"]
    name = (target.get("attributes") or {}).get("name") or playlist_id
    tracks = amp_api.get_playlist_order(playlist_id)
    before = _references(tracks)
    count = len(before)
    if not count:
        raise ValueError("Playlist is empty; nothing to reorder")

    if requested is not None:
        if len(requested) != count or set(requested) != set(range(1, count + 1)):
            raise ValueError(f"order must contain every position 1–{count} exactly once")
        positions = requested
    else:
        if from_position > count or to_position > count:
            raise ValueError(f"from_position and to_position must be between 1 and {count}")
        positions = list(range(1, count + 1))
        positions.insert(to_position - 1, positions.pop(from_position - 1))
    after = [before[pos - 1] for pos in positions]
    if dry_run:
        return _preview(name, tracks, positions)
    if after == before:
        return f"Playlist '{name}' is already in the requested order; no changes made"

    # get_tracks() deliberately tolerates read failures and returns partial data.
    # The strict reader here must succeed for ALL pages on both reads before PUT.
    current = _references(amp_api.get_playlist_order(playlist_id))
    if current != before:
        raise ValueError("Playlist changed while preparing reorder; read it again and retry")
    ok, message = amp_api.reorder_tracks(playlist_id, after)
    status = "submitted" if ok else "unconfirmed"
    verification_error = ""
    if ok and verify:
        for attempt in range(_VERIFY_ATTEMPTS):
            if attempt:
                time.sleep(_VERIFY_DELAY)
            try:
                actual = _references(amp_api.get_playlist_order(playlist_id))
                if actual == after:
                    status = "verified"
                    break
            except Exception as exc:
                verification_error = str(exc)
                break
        else:
            verification_error = "the stored order does not match the requested order"

    audit_log.log_action(
        "reorder_playlist",
        {
            "playlist": name,
            "playlist_id": playlist_id,
            "track_count": count,
            "via": "web",
            "status": status,
        },
        undo_info={"playlist_id": playlist_id, "previous_order": before, "requested_order": after},
    )
    if not ok:
        return f"Error: {message}"
    if verify and status != "verified":
        return (
            f"Error: Reorder was submitted for '{name}', but could not be verified: "
            f"{verification_error}. Read the playlist before retrying; no automatic rollback was attempted"
        )
    if status == "verified":
        return f"Reordered '{name}' ({count} tracks); order verified (via web player)"
    return (
        f"Reorder submitted for '{name}' ({count} tracks; verification disabled) (via web player)"
    )
