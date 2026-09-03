"""Optional wire test using the real official binary and a loopback control plane.

No OpenAI account/key or Apple account is used. Install the official client with
scripts/install-bridge.ps1 or APPLEMUSIC_TUNNEL_CLIENT to enable this test.
"""

import asyncio
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import queue
import subprocess
import threading

import pytest

from applemusic_mcp import bridge, server


def test_official_tunnel_forwards_original_mcp(tmp_path):
    try:
        client = bridge.find_client(os.getenv("APPLEMUSIC_TUNNEL_CLIENT"))
    except ValueError:
        pytest.skip("optional official tunnel-client binary is not installed")

    pending = queue.Queue()
    responses = queue.Queue()
    violations = []
    tunnel_id = "tunnel_" + "0" * 32

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, payload=None):
            body = json.dumps(payload).encode() if payload is not None else b""
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.headers.get("Authorization") != "Bearer local-test-key":
                violations.append("missing control-plane authentication")
            if "/poll" in self.path:
                try:
                    command = pending.get(timeout=0.1)
                except queue.Empty:
                    self.reply(204)
                else:
                    self.reply(200, {"commands": [command]})
            else:
                self.reply(200, {"id": tunnel_id, "name": "local test"})

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.headers.get("X-Tunnel-Shard-Token") != "test-shard":
                violations.append("wrong correlation token")
            responses.put(payload)
            self.reply(200, {"status": "ok"})

    control_plane = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=control_plane.serve_forever, daemon=True)
    command = bridge.tunnel_command(client, tunnel_id, 0)
    command[command.index("--control-plane.base-url") + 1] = (
        f"http://127.0.0.1:{control_plane.server_port}"
    )
    # A Unicode export proves the extra tool and the original resource both work.
    cache = tmp_path / ".cache" / "applemusic-mcp"
    cache.mkdir(parents=True, exist_ok=True)
    export = "name,artist\n夜曲,周杰伦\n"
    (cache / "tracks.csv").write_text(export, encoding="utf-8")
    env = dict(os.environ, CONTROL_PLANE_API_KEY="local-test-key", PYTHONIOENCODING="utf-8")
    env.update(APPLEMUSIC_MCP_HOME=str(tmp_path), APPLEMUSIC_CACHE_DIR=str(cache))
    sequence = 0

    def rpc(method, params=None):
        nonlocal sequence
        sequence += 1
        request_id = f"req_{sequence}"
        pending.put(
            {
                "request_id": request_id,
                "shard_token": "test-shard",
                "channel": "main",
                "command_type": "jsonrpc",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "response_timeout": "20s",
                "jsonrpc": {
                    "jsonrpc": "2.0",
                    "id": sequence,
                    "method": method,
                    "params": params or {},
                },
            }
        )
        result = responses.get(timeout=25)
        assert result["request_id"] == request_id
        assert result["resp_code"] == 200, result
        assert result["resp_json"]["id"] == sequence
        return result["resp_json"]

    log = tmp_path / "tunnel.log"
    worker.start()
    with log.open("w", encoding="utf-8") as output:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            init = rpc(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "bridge-test", "version": "1"},
                },
            )
            assert init["result"]["serverInfo"]["name"] == "Apple Music"
            # Deliberately omit initialized: the official lifecycle shim supplies it.
            tools = rpc("tools/list")["result"]["tools"]
            actual = {tool["name"]: tool for tool in tools}
            expected = asyncio.run(server.mcp.list_tools())
            for tool in expected:
                assert actual[tool.name] == tool.model_dump(by_alias=True, exclude_none=True)
            assert set(actual) == {tool.name for tool in expected} | {"exports"}
            result = rpc(
                "tools/call",
                {"name": "exports", "arguments": {"action": "read", "filename": "tracks.csv"}},
            )
            assert result["result"]["content"][0]["text"] == export
            resource = rpc("resources/read", {"uri": "exports://tracks.csv"})
            assert resource["result"]["contents"][0]["text"] == export
            assert "error" in rpc("unknown/method")
            assert rpc("ping")["result"] == {}
            assert not violations
        except queue.Empty:
            pytest.fail("Tunnel did not forward the request: " + log.read_text(encoding="utf-8"))
        finally:
            process.terminate()
            process.wait(timeout=10)
            control_plane.shutdown()
            control_plane.server_close()
            worker.join(timeout=5)
