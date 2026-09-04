"""Connect the existing local MCP to ChatGPT through OpenAI Secure MCP Tunnel.

The official tunnel-client owns transport and authentication. This launcher
selects the same Python installation, preserves local Apple Music state, and
serializes calls to the one desktop player. It never puts the runtime key in argv.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from datetime import timedelta
from importlib.metadata import version
from pathlib import Path

from . import paths

_CREDENTIAL_SERVICE = "applemusic-mcp-bridge"


def _credential_store():
    # Use Windows' native vault explicitly; never fall back to a plaintext file.
    if sys.platform == "win32":
        from keyring.backends.Windows import WinVaultKeyring

        return WinVaultKeyring()
    import keyring

    backend = keyring.get_keyring()
    if backend.priority < 1:
        raise ValueError("An OS credential store is required to remember the runtime key")
    return backend


def _saved_tunnel_id() -> str | None:
    profile = paths.config_dir() / "bridge.json"
    if not profile.exists():
        return None
    try:
        value = json.loads(profile.read_text(encoding="utf-8"))["tunnel_id"]
        if not isinstance(value, str):
            raise ValueError
        return value
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Invalid bridge profile: {profile}; run bridge --setup") from error


def resolve_credentials(
    tunnel_id: str | None, *, interactive: bool = False, remember: bool = False, setup: bool = False
) -> tuple[str, str]:
    """Explicit values/environment override saved credentials; keys are tunnel-specific."""
    tunnel_id = tunnel_id or os.getenv("CONTROL_PLANE_TUNNEL_ID")
    if not tunnel_id and not setup:
        tunnel_id = _saved_tunnel_id()
    if not tunnel_id and interactive:
        tunnel_id = input("Tunnel ID: ").strip()
    if not re.fullmatch(r"tunnel_[0-9a-f]{32}", tunnel_id or ""):
        raise ValueError("Set a valid Tunnel ID or run bridge --setup")

    runtime_key = os.getenv("CONTROL_PLANE_API_KEY", "").strip()
    if not runtime_key and not setup:
        try:
            runtime_key = _credential_store().get_password(_CREDENTIAL_SERVICE, tunnel_id) or ""
        except Exception:
            # Environment-only use still works on hosts without an OS vault.
            if not interactive:
                raise ValueError(
                    "Cannot read the OS credential store; set CONTROL_PLANE_API_KEY locally"
                ) from None
    if not runtime_key and interactive:
        runtime_key = getpass.getpass("Runtime API key (hidden): ").strip()
    if not runtime_key:
        raise ValueError("Set CONTROL_PLANE_API_KEY locally or run bridge --setup")

    if remember:
        try:
            backend = _credential_store()
            if backend.get_password(_CREDENTIAL_SERVICE, tunnel_id) != runtime_key:
                backend.set_password(_CREDENTIAL_SERVICE, tunnel_id, runtime_key)
        except Exception:
            raise ValueError(
                "Could not save the runtime key in the OS credential store. "
                "No plaintext key file was written; omit --remember for environment-only use."
            ) from None
        profile = paths.config_dir() / "bridge.json"
        profile.parent.mkdir(parents=True, exist_ok=True)
        # The profile contains only the selected Tunnel ID, never the runtime key.
        payload = json.dumps({"tunnel_id": tunnel_id}, indent=2) + "\n"
        if not profile.exists() or profile.read_text(encoding="utf-8") != payload:
            profile.write_text(payload, encoding="utf-8")
    return tunnel_id, runtime_key


def add_bridge_parser(subparsers):
    parser = subparsers.add_parser(
        "bridge", help="Connect this local MCP to ChatGPT via a secure tunnel"
    )
    parser.add_argument("--tunnel-id", default=os.getenv("CONTROL_PLANE_TUNNEL_ID"))
    parser.add_argument(
        "--interactive", action="store_true", help="Prompt locally for missing credentials"
    )
    parser.add_argument(
        "--remember",
        action="store_true",
        help="Remember the Tunnel ID and store the key in the OS vault",
    )
    parser.add_argument(
        "--client",
        default=os.getenv("APPLEMUSIC_TUNNEL_CLIENT"),
        help="Path to the official tunnel-client executable (otherwise auto-detected)",
    )
    parser.add_argument(
        "--health-port", type=int, default=8787, help="Loopback admin UI port (0: automatic)"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check", action="store_true", help="Check local MCP tool/schema parity; no key needed"
    )
    mode.add_argument(
        "--doctor", action="store_true", help="Check tunnel configuration and connectivity"
    )
    mode.add_argument("--setup", action="store_true", help="Enter and save credentials, then exit")


def find_client(explicit: str | None = None) -> str:
    name = "tunnel-client.exe" if os.name == "nt" else "tunnel-client"
    if explicit:
        candidates = [Path(explicit).expanduser()]
        found = shutil.which(explicit)
        if found:
            candidates.insert(0, Path(found))
    else:
        # The source installer keeps the official binary outside version control.
        candidates = [Path(__file__).resolve().parents[2] / ".bridge" / "tunnel-client" / name]
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())
    raise ValueError(
        "tunnel-client not found. On Windows run scripts/install-bridge.ps1, "
        "or install the official OpenAI tunnel-client and pass --client PATH."
    )


def mcp_command() -> str:
    # tunnel-client parses a shell-style command on every OS (without a shell).
    # Forward slashes avoid backslash-escape parsing in Windows executable paths.
    executable = Path(sys.executable).as_posix()
    return shlex.join([executable, "-m", "applemusic_mcp.bridge_server"])


def tunnel_command(
    client: str, tunnel_id: str, health_port: int, *, doctor: bool = False
) -> list[str]:
    if not re.fullmatch(r"tunnel_[0-9a-f]{32}", tunnel_id or ""):
        raise ValueError(
            "Set CONTROL_PLANE_TUNNEL_ID or --tunnel-id to the ID from "
            "https://platform.openai.com/settings/organization/tunnels."
        )
    if not 0 <= health_port <= 65535:
        raise ValueError("--health-port must be between 0 and 65535")
    command = [
        client,
        "doctor" if doctor else "run",
        "--control-plane.tunnel-id",
        tunnel_id,
        "--control-plane.api-key",
        "env:CONTROL_PLANE_API_KEY",
        "--control-plane.base-url",
        "https://api.openai.com",
        "--control-plane.poll-channel",
        "main",
        "--mcp.command",
        mcp_command(),
        "--mcp.max-concurrent-requests",
        "1",
        "--mcp.stdio-send-initialized-notification",
        "--health.listen-addr",
        f"127.0.0.1:{health_port}",
        "--log.http-raw-unsafe=false",
        "--open-web-ui=false",
    ]
    if doctor:
        command.append("--explain")
    return command


async def check_local() -> dict:
    """Real stdio handshake; compare every original tool definition, not just names."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from .server import mcp

    # MCP 1.x takes a timedelta; 2.x takes seconds as a float.
    timeout = timedelta(seconds=30) if version("mcp").split(".")[0] == "1" else 30.0
    expected = {tool.name: tool.model_dump() for tool in await mcp.list_tools()}
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "applemusic_mcp.bridge_server"],
        env=dict(os.environ, PYTHONIOENCODING="utf-8"),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timeout) as session:
            initialized = await session.initialize()
            result = await session.list_tools()
            actual = {tool.name: tool.model_dump() for tool in result.tools}
            for name, definition in expected.items():
                if actual.get(name) != definition:
                    raise ValueError(f"Bridge changed or omitted the original tool: {name}")
            if "exports" not in actual:
                raise ValueError("Bridge exports tool is missing")
            resources = await session.list_resources()
            templates = await session.list_resource_templates()
            await session.send_ping()
    # Wire aliases are stable across MCP 1.x and 2.x's Python field renames.
    return {
        "server": initialized.model_dump(by_alias=True)["serverInfo"]["name"],
        "preserved_tools": sorted(expected),
        "additional_tools": sorted(set(actual) - set(expected)),
        "resources": [str(resource.uri) for resource in resources.resources],
        "resource_templates": [
            template["uriTemplate"]
            for template in templates.model_dump(by_alias=True)["resourceTemplates"]
        ],
    }


def cmd_bridge(args: argparse.Namespace) -> int:
    try:
        if args.check:
            print(json.dumps(asyncio.run(check_local()), indent=2, ensure_ascii=True))
            print("Local MCP check passed. ChatGPT connectivity has not been tested.")
            return 0
        setup = getattr(args, "setup", False)
        tunnel_id, runtime_key = resolve_credentials(
            args.tunnel_id,
            interactive=getattr(args, "interactive", False) or setup,
            remember=getattr(args, "remember", False) or setup,
            setup=setup,
        )
        if setup:
            print(
                "Saved Tunnel ID in the profile and runtime key in the OS credential store. Future starts reuse them."
            )
            return 0
        client = find_client(args.client)
        command = tunnel_command(client, tunnel_id, args.health_port, doctor=args.doctor)
        print("Connecting the local Apple Music MCP through OpenAI Secure MCP Tunnel.", flush=True)
        if not args.doctor:
            print("Keep this process and the desktop session running for playback.", flush=True)
            if args.health_port:
                print(f"Local status: http://127.0.0.1:{args.health_port}/ui", flush=True)
        return subprocess.call(
            command,
            env=dict(os.environ, PYTHONIOENCODING="utf-8", CONTROL_PLANE_API_KEY=runtime_key),
        )
    except (ValueError, OSError) as error:
        print(f"Bridge: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    except EOFError:
        print(
            "Bridge: credentials require an interactive terminal; run bridge --setup locally.",
            file=sys.stderr,
        )
        return 1
