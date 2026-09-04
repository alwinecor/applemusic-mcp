"""Bridge contract checks; all Apple state is isolated by conftest.py."""

import argparse
import asyncio
import json
import os
import shlex
import sys

import pytest

from applemusic_mcp import bridge, bridge_server, server

TUNNEL_ID = "tunnel_" + "0" * 32


@pytest.fixture(autouse=True)
def isolated_bridge_credentials(monkeypatch, tmp_path):
    values = {}

    class MemoryVault:
        def get_password(self, service, username):
            return values.get((service, username))

        def set_password(self, service, username, password):
            values[service, username] = password

    monkeypatch.setattr(bridge, "_credential_store", MemoryVault)
    monkeypatch.setattr(bridge.paths, "config_dir", lambda: tmp_path / "bridge-config")
    monkeypatch.delenv("CONTROL_PLANE_API_KEY", raising=False)
    monkeypatch.delenv("CONTROL_PLANE_TUNNEL_ID", raising=False)
    return values


def test_first_start_remembers_and_next_start_needs_no_input(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: TUNNEL_ID)
    monkeypatch.setattr(bridge.getpass, "getpass", lambda _: "test-runtime-key")
    assert bridge.resolve_credentials(None, interactive=True, remember=True) == (
        TUNNEL_ID,
        "test-runtime-key",
    )
    profile = bridge.paths.config_dir() / "bridge.json"
    assert json.loads(profile.read_text()) == {"tunnel_id": TUNNEL_ID}
    assert "test-runtime-key" not in profile.read_text()
    monkeypatch.setattr("builtins.input", lambda _: pytest.fail("should reuse saved ID"))
    monkeypatch.setattr(bridge.getpass, "getpass", lambda _: pytest.fail("should reuse saved key"))
    assert bridge.resolve_credentials(None, interactive=True) == (TUNNEL_ID, "test-runtime-key")


def test_explicit_credentials_override_saved_without_overwriting(monkeypatch):
    monkeypatch.setenv("CONTROL_PLANE_API_KEY", "saved-key")
    bridge.resolve_credentials(TUNNEL_ID, remember=True)
    alternate = "tunnel_" + "1" * 32
    monkeypatch.setenv("CONTROL_PLANE_API_KEY", "temporary-key")
    assert bridge.resolve_credentials(alternate) == (alternate, "temporary-key")
    monkeypatch.delenv("CONTROL_PLANE_API_KEY")
    assert bridge.resolve_credentials(None) == (TUNNEL_ID, "saved-key")
    with pytest.raises(ValueError, match="CONTROL_PLANE_API_KEY"):
        bridge.resolve_credentials(alternate)


def test_vault_failure_never_writes_key_to_disk(monkeypatch):
    def unavailable():
        raise RuntimeError("vault locked")

    monkeypatch.setattr(bridge, "_credential_store", unavailable)
    monkeypatch.setenv("CONTROL_PLANE_API_KEY", "secret-test-key")
    with pytest.raises(ValueError, match="No plaintext"):
        bridge.resolve_credentials(TUNNEL_ID, remember=True)
    assert not bridge.paths.config_dir().exists()
    assert bridge.resolve_credentials(TUNNEL_ID) == (TUNNEL_ID, "secret-test-key")


def test_saved_key_only_enters_child_environment(monkeypatch):
    monkeypatch.setenv("CONTROL_PLANE_API_KEY", "stored-test-key")
    bridge.resolve_credentials(TUNNEL_ID, remember=True)
    monkeypatch.delenv("CONTROL_PLANE_API_KEY")
    monkeypatch.setattr(bridge, "find_client", lambda _: "tunnel-client")

    def launch(command, *, env):
        assert "stored-test-key" not in " ".join(command)
        assert env["CONTROL_PLANE_API_KEY"] == "stored-test-key"
        assert "CONTROL_PLANE_API_KEY" not in os.environ
        return 0

    monkeypatch.setattr(bridge.subprocess, "call", launch)
    args = argparse.Namespace(check=False, doctor=False, client=None, tunnel_id=None, health_port=0)
    assert bridge.cmd_bridge(args) == 0


def test_setup_replaces_saved_key_without_starting_tunnel(monkeypatch, capsys):
    monkeypatch.setenv("CONTROL_PLANE_API_KEY", "old-key")
    bridge.resolve_credentials(TUNNEL_ID, remember=True)
    monkeypatch.delenv("CONTROL_PLANE_API_KEY")
    monkeypatch.setattr("builtins.input", lambda _: TUNNEL_ID)
    monkeypatch.setattr(bridge.getpass, "getpass", lambda _: "new-key")
    monkeypatch.setattr(bridge.subprocess, "call", lambda *a, **k: pytest.fail("must not start"))
    args = argparse.Namespace(check=False, setup=True, tunnel_id=None)
    assert bridge.cmd_bridge(args) == 0
    assert bridge.resolve_credentials(None) == (TUNNEL_ID, "new-key")
    assert "new-key" not in capsys.readouterr().out


def test_real_stdio_preserves_original_schemas():
    report = asyncio.run(bridge.check_local())
    assert report["server"] == "Apple Music"
    assert report["preserved_tools"] == [
        "catalog",
        "config",
        "discover",
        "library",
        "playback",
        "playlist",
        "queue",
    ]
    assert report["additional_tools"] == ["exports"]
    assert report["resources"] == ["exports://list"]
    assert report["resource_templates"] == ["exports://{filename}"]


def test_launcher_quotes_python_path_and_serializes_desktop_calls(monkeypatch):
    monkeypatch.setattr(sys, "executable", "C:/Test Folder/Python/python.exe")
    cmd = bridge.tunnel_command("tunnel-client", TUNNEL_ID, 8787)
    assert shlex.split(cmd[cmd.index("--mcp.command") + 1]) == [
        "C:/Test Folder/Python/python.exe",
        "-m",
        "applemusic_mcp.bridge_server",
    ]
    assert cmd[cmd.index("--mcp.max-concurrent-requests") + 1] == "1"
    assert cmd[cmd.index("--control-plane.api-key") + 1] == "env:CONTROL_PLANE_API_KEY"
    assert "--mcp.stdio-send-initialized-notification" in cmd
    assert "127.0.0.1:8787" in cmd


@pytest.mark.parametrize(
    "tunnel_id,port", [("", 8787), ("bad-id", 8787), (TUNNEL_ID, -1), (TUNNEL_ID, 65536)]
)
def test_invalid_config(tunnel_id, port):
    with pytest.raises(ValueError):
        bridge.tunnel_command("tunnel-client", tunnel_id, port)


def test_missing_key_does_not_start_tunnel(monkeypatch, capsys):
    monkeypatch.delenv("CONTROL_PLANE_API_KEY", raising=False)
    monkeypatch.setattr(bridge, "find_client", lambda _: "tunnel-client")
    monkeypatch.setattr(bridge.subprocess, "call", lambda *a, **k: pytest.fail("must not start"))
    args = argparse.Namespace(
        check=False, doctor=False, client=None, tunnel_id=TUNNEL_ID, health_port=0
    )
    assert bridge.cmd_bridge(args) == 1
    assert "CONTROL_PLANE_API_KEY" in capsys.readouterr().err


def test_exports_tool_preserves_content_and_blocks_traversal(monkeypatch, tmp_path):
    registered = {}

    def register(**kwargs):
        def decorator(fn):
            registered["fn"] = fn
            registered["annotations"] = kwargs["annotations"]
            return fn

        return decorator

    monkeypatch.setattr(server.mcp, "tool", register)
    monkeypatch.setattr(server, "get_cache_dir", lambda: tmp_path / "exports")
    (tmp_path / "exports").mkdir()
    content = 'name,artist\n"Hello", "Adele"\n'
    (tmp_path / "exports" / "tracks.csv").write_text(content, encoding="utf-8")
    (tmp_path / "private.txt").write_text("outside-secret", encoding="utf-8")
    bridge_server.register_exports_tool()
    tool = registered["fn"]
    assert "tracks.csv" in tool("list")
    assert tool("read", "tracks.csv") == content
    assert "outside-secret" not in tool("read", "../private.txt")
    assert "Error" in tool("read", "")
    assert registered["annotations"].model_dump(by_alias=True)["readOnlyHint"] is True


def test_find_explicit_client(tmp_path):
    exe = tmp_path / "tunnel-client.exe"
    exe.touch()
    assert bridge.find_client(str(exe)) == str(exe.resolve())
    with pytest.raises(ValueError, match="not found"):
        bridge.find_client(str(tmp_path / "missing"))
