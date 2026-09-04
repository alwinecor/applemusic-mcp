# ChatGPT bridge

**English** | [简体中文](chatgpt-bridge.zh-CN.md)

Connect the local Apple Music MCP server to ChatGPT Chat using OpenAI Secure MCP
Tunnel. The bridge runs on the computer that already hosts your Apple Music
engines and makes its tools available through a ChatGPT plugin connection.

For clients that launch the server locally over stdio, use the
[local MCP setup](../README.md#local-mcp-setup).

## How it works

```text
ChatGPT Chat plugin connection
             |
OpenAI Secure MCP Tunnel
             | outbound HTTPS from the host
Local tunnel-client
             | stdio
applemusic_mcp.bridge_server
             |
Existing Apple Music API / Chrome / Safari / Music.app engines
```

The official `tunnel-client` handles transport and tunnel authentication. The
bridge starts one local MCP process and dispatches requests serially to that
process, so remote calls share the same desktop player and engine state.

Secure MCP Tunnel supports private connections in ChatGPT developer mode without
opening inbound internet ports. Public plugin submission requires a stable,
public HTTPS MCP endpoint and the applicable authentication setup; the private
tunnel described here is intended for personal or workspace use.
See the [official Secure MCP Tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).

## Requirements

- A checkout of this repository containing the bridge feature, Python 3.10+, and
  [uv](https://docs.astral.sh/uv/) for the Windows setup below.
- The [Apple Music prerequisites](../README.md#local-mcp-setup) for the engines you
  intend to use. Set up Apple Music sign-in on the host before connecting ChatGPT.
- The official [OpenAI tunnel-client](https://github.com/openai/tunnel-client/releases/latest).
- ChatGPT developer-mode access for the target account or workspace.
- An OpenAI tunnel associated with that ChatGPT workspace and a runtime API key
  with **Tunnels Read + Use** permissions. Creating or editing a tunnel also
  requires **Read + Manage**. These permissions are separate from ChatGPT
  developer-mode access.

Tunnel credentials authenticate the bridge to OpenAI. Your existing Apple Music
credentials continue to authenticate the local engines to Apple Music.

## Set up on Windows

Run these commands in PowerShell from the repository root.

### 1. Install the project and tunnel client

Create or update the project environment:

```powershell
uv sync --extra dev
```

Install the official Windows tunnel client:

```powershell
.\scripts\install-bridge.ps1
```

The installer downloads the latest official release for the detected architecture,
checks it against the release's SHA-256 checksum, and extracts it into
`.bridge/tunnel-client`. Downloaded archives and binaries are excluded from Git.

### 2. Check the local MCP

```powershell
.\scripts\start-bridge.ps1 -Check
```

This performs a real local stdio handshake and compares the bridge's original
tool definitions against the local server. It requires no OpenAI key and does
not establish a connection to ChatGPT.

### 3. Prepare the tunnel

Create or select a tunnel in
[OpenAI Tunnel settings](https://platform.openai.com/settings/organization/tunnels)
and associate it with the ChatGPT workspace that will use it. Obtain a runtime
API key with the required tunnel permissions. Use a runtime key for the bridge,
not an admin key.

### 4. Start the bridge

```powershell
.\scripts\start-bridge.ps1
```

On the first start, enter the Tunnel ID and runtime key in the local terminal.
Key entry is hidden. The launcher saves the credentials as described below;
subsequent starts reuse them automatically.

Keep the terminal running while ChatGPT uses the connection. The default local
status page is [http://127.0.0.1:8787/ui](http://127.0.0.1:8787/ui).
Press **Ctrl+C** to stop the bridge.

## Connect from ChatGPT

Keep the bridge running during connection setup and tool discovery.

1. In ChatGPT, open **Settings > Security and login** and enable **Developer mode**.
2. Open [ChatGPT Plugins](https://chatgpt.com/plugins) and select the add button.
3. Enter a name such as **Apple Music Local Bridge**.
4. Under **Connection**, select **Tunnel**, then choose your tunnel or enter its ID.
5. Create the connection and review the discovered tools: the seven original
   Apple Music tools plus `exports`.
6. Select the plugin in a new conversation. Start with a status request, then
   ask it to list your playlists.

For example:

> Use Apple Music Local Bridge to check my Apple Music connection status.

Read and write tools remain subject to ChatGPT's tool enablement and confirmation
settings. Account and workspace policies determine developer-mode availability.
See the [official connection instructions](https://developers.openai.com/plugins/deploy/connect-chatgpt)
and [developer-mode guide](https://developers.openai.com/api/docs/guides/developer-mode).

## Saved credentials and everyday use

Start the bridge with the same command each time:

```powershell
.\scripts\start-bridge.ps1
```

The Windows launcher remembers credentials in two locations:

| Value | Storage |
|---|---|
| Selected Tunnel ID | `~/.config/applemusic-mcp/bridge.json` |
| Runtime API key | Windows Credential Manager, under service `applemusic-mcp-bridge`, indexed by Tunnel ID |

The profile directory follows the project's `APPLEMUSIC_CONFIG_DIR` and
`APPLEMUSIC_MCP_HOME` overrides. The profile contains only the Tunnel ID. The key
is loaded into the tunnel client's environment at startup; it is never written
to a plaintext key file or included in command-line arguments. A failure to save
to the credential store produces an error instead of a plaintext fallback.

To replace credentials, or save them without starting the tunnel:

```powershell
.\scripts\start-bridge.ps1 -Setup
```

Explicit arguments and environment variables take precedence over saved values.
`-Setup` ignores previously saved values, but still uses supplied arguments or
environment variables. Clear those overrides first if you want to enter new values.

The Windows launcher saves the selected values on each invocation. To use a
temporary environment override without updating stored credentials, run the CLI
directly without `--remember`.

## CLI reference and other platforms

On macOS or Linux, install the official `tunnel-client` and make it available on
`PATH`, or pass its path with `--client`. Run the CLI from the Python environment
where this checkout is installed:

```bash
applemusic-mcp bridge --check
applemusic-mcp bridge --setup
applemusic-mcp bridge --doctor
applemusic-mcp bridge
```

Saving credentials requires a working system credential store. For environments
without one, supply `CONTROL_PLANE_TUNNEL_ID` and `CONTROL_PLANE_API_KEY` through
your environment and omit `--remember`.

| Option | Purpose |
|---|---|
| `--check` | Verify local MCP tool definitions and resource discovery, then exit. |
| `--setup` | Enter and save credentials, then exit. |
| `--doctor` | Run the official tunnel client's diagnostics. |
| `--interactive` | Prompt locally for missing credentials. |
| `--remember` | Save the selected Tunnel ID and runtime key. |
| `--tunnel-id ID` | Override the saved Tunnel ID. |
| `--client PATH` | Specify the official tunnel-client executable. |
| `--health-port PORT` | Set the loopback status port; default `8787`, or `0` for automatic allocation. |

`--check`, `--setup`, and `--doctor` are mutually exclusive.

| Environment variable | Purpose |
|---|---|
| `CONTROL_PLANE_TUNNEL_ID` | Tunnel ID override; an explicit `--tunnel-id` takes precedence. |
| `CONTROL_PLANE_API_KEY` | Runtime key override for the selected tunnel. |
| `APPLEMUSIC_TUNNEL_CLIENT` | Executable path override; an explicit `--client` takes precedence. |

The original `applemusic-mcp serve` command and bare `python -m applemusic_mcp`
continue to start the local stdio MCP server.

## Tools and exports

The bridge reuses `playlist`, `library`, `catalog`, `discover`, `playback`, `queue`,
and `config`. Their names, descriptions, input and output schemas, annotations,
and action implementations remain unchanged. This includes playlist writes and
reordering, playback, queue management, sign-in, and preferences.

The original `exports://list` and `exports://{filename}` resources are also
available. An additional read-only `exports` tool exposes their contents to
clients that only invoke tools.

List available exports by calling `exports` with:

```json
{"action": "list"}
```

Then read a file using the exact filename returned by that call:

```json
{"action": "read", "filename": "tracks_YYYYMMDD_HHMMSS.csv"}
```

The example filename is a placeholder. CSV and JSON files remain on the host;
the read action returns their text. A local file path does not automatically
become a downloadable ChatGPT attachment, and large results remain subject to
the client's tool-output limits.

## Operating limits

- **Host availability:** The host must remain online and awake. Playback requires
  its desktop session and player to be available.
- **Audio output:** Audio plays on the host computer. The bridge does not stream
  the player's audio into ChatGPT.
- **Platform support:** The bridge preserves what the host's existing engines
  support. It does not add macOS-only Music.app, AirPlay, or star-rating features
  to Windows. See the [engine capability table](../README.md#features).
- **Player ownership:** Avoid running multiple MCP instances that compete for
  the same Chrome profile. The bridge manages one local MCP process of its own.
- **Sign-in:** Complete interactive Apple Music sign-in on the host computer.
  Remote calls continue to use that host's credentials and preferences.

## Troubleshooting

| Symptom | What to check |
|---|---|
| ChatGPT cannot find the tunnel | Confirm the target workspace association and the caller's Tunnels Read + Use permissions. |
| Discovery or calls fail | Keep the bridge running and run `.\scripts\start-bridge.ps1 -Doctor`. Check the local status page. |
| Credentials are requested again | Use the same OS account and configuration directory. Check access to the system credential store. |
| A replaced key is not being used | Check environment overrides, then run `-Setup` with the intended values. |
| Port `8787` is already in use | Run the CLI with another `--health-port`. |
| Playback fails but library queries work | Check the host desktop session, Apple Music sign-in, selected engine, and Chrome profile ownership. |
| Tool definitions changed after an update | Restart the bridge, refresh the plugin connection in ChatGPT, and use a new conversation. |

## Development and validation

Run the focused suite from the repository root:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_bridge.py tests/test_bridge_tunnel.py tests/test_cli_cov.py -q
```

It covers credential reuse and overrides, child-process credential handling,
local stdio initialization, original tool-schema parity, and export path
boundaries. With the official binary installed, it also exercises actual tunnel
forwarding against a simulated loopback control plane: tool discovery, Unicode
export reads, resource reads, error forwarding, and ping. That test is skipped
when the binary is unavailable.

These tests use isolated state and do not require real OpenAI or Apple accounts.
They do not replace account-level ChatGPT connection checks or live playback
validation. The local validation baseline is MCP Python SDK **1.25.0** and official
tunnel-client **0.0.14** on Windows. Re-run the checks when upgrading dependencies.
