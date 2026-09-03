"""Reorder invariants at the HTTP boundary; no real account or browser access."""

import asyncio
import json

import pytest
import requests
import responses

from applemusic_mcp import amp_api, audit_log, playlist_order, server

PID = "p.TEST"
PLAYLIST_URL = f"{amp_api.AMP}/me/library/playlists/{PID}"
TRACKS_URL = f"{PLAYLIST_URL}/tracks"


def _track(item_id, title="", item_type="library-songs"):
    return {"id": item_id, "type": item_type, "attributes": {"name": title, "artistName": "Artist"}}


TRACKS = [_track("i.A", "Alpha"), _track("i.B", "Beta"), _track("i.C", "Gamma")]


@pytest.fixture(autouse=True)
def _offline_auth(monkeypatch):
    monkeypatch.setattr(amp_api.auth, "resolve_web_token", lambda: "WEB")
    monkeypatch.setattr(amp_api.auth, "get_user_token", lambda: "USER")
    monkeypatch.setattr(server, "_forced_tokenless", lambda: False)
    monkeypatch.setattr(playlist_order, "_VERIFY_DELAY", 0)


def _target(*, editable=True):
    responses.get(
        PLAYLIST_URL,
        json={
            "data": [
                {
                    "id": PID,
                    "type": "library-playlists",
                    "attributes": {"name": "Mix", "canEdit": editable},
                }
            ]
        },
    )


def _reads(*orders):
    for tracks in orders:
        responses.get(TRACKS_URL, json={"data": tracks})


def _call(**kwargs):
    return server.playlist(action="reorder", playlist=PID, **kwargs)


def _writes():
    return [call for call in responses.calls if call.request.method != "GET"]


@pytest.mark.parametrize(
    "from_pos,to_pos,expected",
    [
        (3, 1, [2, 0, 1]),
        (1, 3, [1, 2, 0]),
        (2, 3, [0, 2, 1]),
    ],
)
@responses.activate
def test_move_preserves_playlist_and_verifies_order(from_pos, to_pos, expected):
    _target()
    reordered = [TRACKS[i] for i in expected]
    _reads(TRACKS, TRACKS, reordered)
    responses.put(TRACKS_URL, status=204)
    result = _call(from_position=from_pos, to_position=to_pos)
    assert "order verified" in result
    assert len(_writes()) == 1
    request = _writes()[0].request
    assert request.method == "PUT" and request.url == TRACKS_URL
    assert request.headers["Authorization"] == "Bearer WEB"
    assert json.loads(request.body) == {
        "data": [{"id": t["id"], "type": t["type"]} for t in reordered]
    }
    entry = audit_log.get_recent_entries(1)[0]
    assert entry["details"]["status"] == "verified"
    assert [r["id"] for r in entry["undo_info"]["previous_order"]] == ["i.A", "i.B", "i.C"]


@pytest.mark.parametrize("order", ["3,1,2", "[3, 1, 2]", "3\n1\n2"])
@responses.activate
def test_full_order_preview_is_read_only(order):
    _target()
    _reads(TRACKS)
    result = _call(order=order, dry_run=True)
    assert "no changes made" in result
    assert "1. Gamma" in result and "was #3" in result
    assert "2. Alpha" in result
    assert not _writes()
    assert not audit_log.get_recent_entries()


@responses.activate
def test_duplicate_songs_and_video_keep_every_occurrence_and_type():
    _target()
    tracks = [TRACKS[0], _track("i.V", "Video", "library-music-videos"), TRACKS[0]]
    after = [tracks[2], tracks[0], tracks[1]]
    _reads(tracks, tracks, after)
    responses.put(TRACKS_URL, status=204)
    assert "verified" in _call(order="3,1,2")
    data = json.loads(_writes()[0].request.body)["data"]
    assert [t["id"] for t in data] == ["i.A", "i.A", "i.V"]
    assert data[-1]["type"] == "library-music-videos"


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"from_position": 1},
        {"from_position": -1, "to_position": 1},
        {"from_position": True, "to_position": 1},
        {"order": "1,2", "from_position": 1, "to_position": 2},
        {"order": "[]"},
        {"order": "[true,2,3]"},
        {"order": "[1.0,2,3]"},
        {"order": "1,,2"},
        {"order": "1,a,3"},
        {"order": "[1,"},
        {"order": "0,1,2"},
    ],
)
@responses.activate
def test_invalid_arguments_fail_before_any_request(kwargs):
    assert _call(**kwargs).startswith("Error:")
    assert not responses.calls


@pytest.mark.parametrize(
    "kwargs",
    [
        {"order": "1,1,3"},
        {"order": "1,2"},
        {"order": "1,2,4"},
        {"order": "1,2,3,4"},
        {"from_position": 4, "to_position": 1},
    ],
)
@responses.activate
def test_invalid_permutation_or_out_of_bounds_cannot_write(kwargs):
    _target()
    _reads(TRACKS)
    assert _call(**kwargs).startswith("Error:")
    assert not _writes()


@pytest.mark.parametrize("kwargs", [{"order": "1,2,3"}, {"from_position": 2, "to_position": 2}])
@responses.activate
def test_noop_does_not_write(kwargs):
    _target()
    _reads(TRACKS)
    assert "already in the requested order" in _call(**kwargs)
    assert not _writes()


@pytest.mark.parametrize(
    "tracks", [[], [{"id": "i.A"}], [_track("", "Missing ID")], [_track("x", "Unknown", "unknown")]]
)
@responses.activate
def test_empty_or_unrepresentable_playlist_cannot_write(tracks):
    _target()
    _reads(tracks)
    assert _call(from_position=1, to_position=2).startswith("Error:")
    assert not _writes()


@responses.activate
def test_read_only_playlist_refused():
    _target(editable=False)
    assert "does not permit editing" in _call(order="3,1,2")
    assert not _writes()


@pytest.mark.parametrize("names", [["Mix", "Mix"], ["Mix Tape"], []])
@responses.activate
def test_ambiguous_or_inexact_name_cannot_write(names):
    responses.get(
        f"{amp_api.AMP}/me/library/playlists",
        json={
            "data": [
                {"id": f"p.{i}", "attributes": {"name": name, "canEdit": True}}
                for i, name in enumerate(names)
            ]
        },
    )
    result = server.playlist(action="reorder", playlist="Mix", order="3,1,2")
    assert result.startswith("Error:")
    assert not _writes()


@responses.activate
def test_exact_name_can_be_found_on_later_page():
    url = f"{amp_api.AMP}/me/library/playlists"
    responses.get(
        url,
        json={
            "data": [{"id": "p.OTHER", "attributes": {"name": "Other"}}],
            "next": "/v1/me/library/playlists?offset=100",
        },
    )
    responses.get(
        f"{url}?offset=100",
        json={"data": [{"id": PID, "attributes": {"name": "Mix", "canEdit": True}}]},
    )
    _reads(TRACKS)
    result = server.playlist(action="reorder", name="mix", order="3,1,2", dry_run=True)
    assert "Preview reorder of 'Mix'" in result


@responses.activate
def test_pagination_includes_every_track():
    _target()
    for _ in range(2):
        responses.get(
            TRACKS_URL,
            json={
                "data": TRACKS[:2],
                "next": f"/v1/me/library/playlists/{PID}/tracks?offset=2",
                "meta": {"total": 3},
            },
        )
        responses.get(f"{TRACKS_URL}?offset=2", json={"data": TRACKS[2:], "meta": {"total": 3}})
    responses.put(TRACKS_URL, status=204)
    result = _call(order="3,1,2", verify=False)
    assert "verification disabled" in result
    assert len(json.loads(_writes()[0].request.body)["data"]) == 3


@responses.activate
def test_second_page_failure_never_writes_partial_playlist():
    _target()
    responses.get(
        TRACKS_URL,
        json={"data": TRACKS[:1], "next": f"/v1/me/library/playlists/{PID}/tracks?offset=1"},
    )
    responses.get(f"{TRACKS_URL}?offset=1", status=429)
    assert "429" in _call(order="1")
    assert not _writes()


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"data": {}},
        {"data": [None]},
        {"data": TRACKS[:1], "meta": {"total": 3}},
        {"data": TRACKS, "next": "https://untrusted.example/steal"},
        {"data": TRACKS, "next": f"{TRACKS_URL}?limit=100"},
        {"data": TRACKS, "next": 123},
        {"data": [], "next": "?offset=2"},
    ],
)
@responses.activate
def test_bad_pagination_or_response_fails_closed(body):
    _target()
    responses.get(TRACKS_URL, json=body)
    assert _call(order="3,1,2").startswith("Error:")
    assert not _writes()
    assert all("amp-api.music.apple.com" in call.request.url for call in responses.calls)


@responses.activate
def test_concurrent_edit_detected_before_write():
    _target()
    _reads(TRACKS, TRACKS[::-1])
    assert "Playlist changed" in _call(order="3,1,2")
    assert not _writes()


@responses.activate
def test_prewrite_read_failure_cannot_write():
    _target()
    _reads(TRACKS)
    responses.get(TRACKS_URL, status=503)
    assert "503" in _call(order="3,1,2")
    assert not _writes()


@responses.activate
def test_success_response_with_wrong_order_is_not_reported_as_success():
    _target()
    _reads(TRACKS)
    responses.put(TRACKS_URL, status=204)
    result = _call(order="3,1,2")
    assert result.startswith("Error:") and "could not be verified" in result
    assert len(_writes()) == 1


@responses.activate
def test_eventually_consistent_order_is_verified():
    _target()
    _reads(TRACKS, TRACKS, TRACKS, [TRACKS[2], TRACKS[0], TRACKS[1]])
    responses.put(TRACKS_URL, status=204)
    assert "order verified" in _call(order="3,1,2")
    assert len(_writes()) == 1


@responses.activate
def test_verification_read_failure_reports_submission_truthfully():
    _target()
    _reads(TRACKS, TRACKS)
    responses.get(TRACKS_URL, status=429)
    responses.put(TRACKS_URL, status=204)
    result = _call(order="3,1,2")
    assert "submitted" in result and "could not be verified" in result and "429" in result
    assert len(_writes()) == 1


@pytest.mark.parametrize("status", [401, 403, 429, 500])
@responses.activate
def test_http_write_failure_is_not_retried(status):
    _target()
    _reads(TRACKS)
    responses.put(TRACKS_URL, status=status)
    result = _call(order="3,1,2")
    assert result.startswith("Error:") and str(status) in result
    assert len(_writes()) == 1


@responses.activate
def test_write_timeout_is_uncertain_not_retried():
    _target()
    _reads(TRACKS)
    responses.put(TRACKS_URL, body=requests.Timeout("timed out"))
    result = _call(order="3,1,2")
    assert "uncertain" in result and "before retrying" in result
    assert len(_writes()) == 1


@responses.activate
def test_force_tokenless_prevents_network(monkeypatch):
    monkeypatch.setattr(server, "_forced_tokenless", lambda: True)
    assert "APPLEMUSIC_FORCE_TOKENLESS" in _call(order="3,1,2")
    assert not responses.calls


def test_reorder_parameters_are_exposed_to_mcp_clients():
    tools = asyncio.run(server.mcp.list_tools())
    # MCP 2.x renamed Python fields to snake_case. Both majors serialize the
    # same camelCase wire format, which is what clients actually consume.
    tool = next(tool for tool in tools if tool.name == "playlist").model_dump(by_alias=True)
    assert {"order", "from_position", "to_position"} <= tool["inputSchema"]["properties"].keys()
    assert "reorder" in tool["description"] and "1-based" in tool["description"]
