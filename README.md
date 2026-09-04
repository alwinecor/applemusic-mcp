# applemusic-mcp

**English** | [简体中文](README.zh-CN.md)

[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![macOS](https://img.shields.io/badge/macOS-15%20%7C%2026-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-server-purple.svg)](https://modelcontextprotocol.io/)

> **Independent fork of [epheterson/applemusic-mcp](https://github.com/epheterson/applemusic-mcp).**
>
> The upstream project provides the core Apple Music MCP server and local Apple Music integrations. This fork builds on that foundation with a **ChatGPT bridge**, **playlist track reordering**, and additional fork-specific integration and workflow refinements.
>
> For the complete upstream feature set, engine details, API behavior, and original documentation, see the **[upstream README](https://github.com/epheterson/applemusic-mcp#readme)**.

## About this fork

The upstream project, originally created by Eric Pheterson, provides the Apple Music MCP foundation used here.

At a high level, upstream supports:

- **Catalog and library access** — search, browse, recently played/added items, recommendations, charts, favorites, ratings where supported, and library writes.
- **Playlist management** — list, search, create, add/remove tracks, copy, rename, delete, folders, and related playlist operations.
- **Playback and queue control** — playback, transport controls, volume/shuffle/repeat, Now Playing, AirPlay where supported, and the Up Next queue.
- **Multiple Apple Music engines** — Music.app and Safari on macOS, plus Apple Music API and Chrome-based MusicKit paths across platforms.
- **Local MCP operation** — the standard `applemusic-mcp serve` stdio server for local MCP clients such as Claude Desktop, Cursor, Cline, Windsurf, and Codex.

The original seven action-based MCP tools are:

| Tool | Main purpose |
|---|---|
| `playlist` | Playlist and folder operations |
| `library` | Library search, browse, writes, favorites, ratings, snapshots |
| `catalog` | Apple Music catalog search and metadata |
| `discover` | Recommendations, charts, stations, related artists |
| `playback` | Playback, transport, settings, reveal, AirPlay |
| `queue` | Up Next queue management |
| `config` | Sign-in, preferences, status, audit log, storefronts |

This fork currently adds or changes:

1. **ChatGPT bridge** — connects the locally running MCP server to ChatGPT through OpenAI Secure MCP Tunnel.
2. **Playlist track reordering** — adds `playlist(action="reorder")` with preview, verification, and safeguards around partial or concurrent edits.
3. **Fork-specific refinements** — bilingual documentation, bridge installation/startup tooling, validation tests, clearer batch-track tool descriptions, and maintenance changes appropriate to an independently developed fork.

The fork will continue independent development primarily around **remote ChatGPT connectivity, richer playlist manipulation, integration reliability, and workflow/documentation improvements**. Upstream changes may still be incorporated where useful, but fork-specific features are maintained independently and should not be interpreted as upstream functionality or support.

---

## Local MCP setup

If you only need the original upstream package and local MCP behavior, the simplest installation path remains the one documented in the [upstream README](https://github.com/epheterson/applemusic-mcp#readme).

To run **this fork**, install it from source so the fork-specific features are available.

### Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) for the source workflow below
- Either a Mac for local Music.app/Safari paths, or an Apple Music subscription for API/browser-backed features
- Google Chrome + Playwright when using the Chrome web-player engine

### Install from source

```bash
git clone https://github.com/alwinecor/applemusic-mcp.git
cd applemusic-mcp
uv sync --extra dev
```

Start the local stdio MCP server from the repository environment:

**Windows**

```powershell
.\.venv\Scripts\applemusic-mcp.exe serve
```

**macOS / Linux**

```bash
./.venv/bin/applemusic-mcp serve
```

For a local MCP client, point the client at that executable and pass `serve`.

Example shape:

```json
{
  "mcpServers": {
    "Apple Music": {
      "command": "/absolute/path/to/applemusic-mcp/.venv/bin/applemusic-mcp",
      "args": ["serve"]
    }
  }
}
```

On Windows, use the corresponding absolute path to `.venv\Scripts\applemusic-mcp.exe`.

### Apple Music sign-in

The upstream server provides two main cross-platform authorization paths:

```bash
applemusic-mcp login --dev
```

uses an Apple Developer MusicKit key and is the preferred sanctioned API route.

```bash
applemusic-mcp login
```

uses the signed-in Apple Music web session. On macOS it can harvest the session from Safari; on Windows/Linux it uses the Chrome path.

On macOS, native Music.app operations can also cover a substantial local feature set without the cross-platform API path.

For the complete engine matrix, browser requirements, token behavior, rate limits, and Apple-specific caveats, use the **[upstream README](https://github.com/epheterson/applemusic-mcp#readme)**.

---

## ChatGPT bridge setup

This is a feature added by this fork on top of the upstream local MCP.

The ChatGPT bridge makes the same local Apple Music MCP server available to ChatGPT Chat through **OpenAI Secure MCP Tunnel**.

The bridge runs on the computer that already hosts the Apple Music engines. It does not move Apple Music execution into the cloud: library operations, browser automation, Music.app control, and playback still happen on the host machine.

### Architecture

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

The official `tunnel-client` handles transport and tunnel authentication. The bridge starts one local MCP process and dispatches requests serially to it, so remote calls share the same player and engine state.

Because the connection is initiated outbound from the host, the private tunnel does not require opening an inbound internet port on the local machine.

The tunnel described here is intended for private personal/workspace use through ChatGPT developer mode. Public plugin deployment has different hosting and authentication requirements.

### Requirements

- A checkout of this fork with the bridge implementation
- Python 3.10+
- `uv` for the Windows source workflow
- Apple Music configured on the host for whichever engines you intend to use
- The official [OpenAI tunnel-client](https://github.com/openai/tunnel-client/releases/latest)
- ChatGPT developer-mode access for the target account or workspace
- An OpenAI tunnel associated with the ChatGPT workspace
- A runtime API key with **Tunnels Read + Use** permissions
- **Read + Manage** permissions when creating or modifying the tunnel

Tunnel credentials authenticate the local bridge to OpenAI. Apple Music credentials remain local to the Apple Music engines and continue to authenticate those engines to Apple.

### Windows bridge setup

Run the following commands in PowerShell from the repository root.

#### Step 1 — Install the project and tunnel client

```powershell
uv sync --extra dev
```

Then install the official Windows tunnel client:

```powershell
.\scripts\install-bridge.ps1
```

The installer downloads the current official release for the detected architecture, verifies it against the release SHA-256 checksum, and extracts it under `.bridge/tunnel-client`. Downloaded bridge binaries and archives are excluded from Git.

#### Step 2 — Validate the local MCP side

```powershell
.\scripts\start-bridge.ps1 -Check
```

This performs a real local stdio handshake and checks that the original MCP tool definitions exposed through the bridge match the local server. It does **not** require an OpenAI key and does **not** establish a ChatGPT connection.

#### Step 3 — Prepare an OpenAI tunnel

Create or select a tunnel in [OpenAI Tunnel settings](https://platform.openai.com/settings/organization/tunnels), associate it with the ChatGPT workspace that will use it, and obtain a runtime API key with the required tunnel permissions.

Use a runtime key for the bridge rather than an admin key.

#### Step 4 — Start the bridge

```powershell
.\scripts\start-bridge.ps1
```

On first start, enter the Tunnel ID and runtime API key in the local terminal. Key entry is hidden. The launcher stores the selected tunnel configuration so subsequent starts can reuse it.

Keep the terminal running while ChatGPT is using the bridge. The default local status page is:

```text
http://127.0.0.1:8787/ui
```

Press **Ctrl+C** to stop the bridge.

### Connect the tunnel from ChatGPT

Keep the bridge running during connection setup and tool discovery.

1. In ChatGPT, open **Settings > Security and login** and enable **Developer mode**.
2. Open **ChatGPT Plugins** and add a new plugin/connection.
3. Give it a name such as **Apple Music Local Bridge**.
4. Under **Connection**, select **Tunnel**.
5. Select the tunnel or enter its Tunnel ID.
6. Create the connection and review the discovered tools.
7. Select the plugin in a new conversation and begin with a status check or playlist listing.

The bridge exposes the seven original Apple Music tools plus the additional read-only `exports` tool.

Read/write execution remains subject to ChatGPT tool permissions, confirmation settings, and account/workspace policy.

Official references:

- [Secure MCP Tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
- [Connect plugins to ChatGPT](https://developers.openai.com/plugins/deploy/connect-chatgpt)
- [Developer mode](https://developers.openai.com/api/docs/guides/developer-mode)

### Saved credentials and everyday use

For ordinary use, start the bridge with:

```powershell
.\scripts\start-bridge.ps1
```

On Windows, credentials are split between the project profile and the operating-system credential store:

| Value | Storage |
|---|---|
| Selected Tunnel ID | `~/.config/applemusic-mcp/bridge.json` |
| Runtime API key | Windows Credential Manager, service `applemusic-mcp-bridge`, indexed by Tunnel ID |

The profile stores the Tunnel ID only. The API key is loaded into the tunnel client's environment at startup. It is not written to a plaintext key file and is not passed as a command-line argument. If secure credential storage fails, the launcher reports an error instead of silently falling back to plaintext storage.

To replace credentials or save them without starting the bridge:

```powershell
.\scripts\start-bridge.ps1 -Setup
```

Explicit CLI arguments and environment variables take precedence over saved values.

### Bridge CLI and other platforms

On macOS or Linux, install the official `tunnel-client` and make it available on `PATH`, or provide its path explicitly with `--client`.

From an environment where this fork is installed:

```bash
applemusic-mcp bridge --check
applemusic-mcp bridge --setup
applemusic-mcp bridge --doctor
applemusic-mcp bridge
```

Key options:

| Option | Purpose |
|---|---|
| `--check` | Verify local MCP tool definitions and resource discovery, then exit |
| `--setup` | Enter and save bridge credentials, then exit |
| `--doctor` | Run official tunnel-client diagnostics |
| `--interactive` | Prompt locally for missing credentials |
| `--remember` | Save the selected Tunnel ID and runtime key |
| `--tunnel-id ID` | Override the saved Tunnel ID |
| `--client PATH` | Select the tunnel-client executable |
| `--health-port PORT` | Set the loopback status port; default `8787`, `0` for automatic allocation |

`--check`, `--setup`, and `--doctor` are mutually exclusive.

Environment overrides:

| Variable | Purpose |
|---|---|
| `CONTROL_PLANE_TUNNEL_ID` | Tunnel ID override |
| `CONTROL_PLANE_API_KEY` | Runtime API key override |
| `APPLEMUSIC_TUNNEL_CLIENT` | tunnel-client executable override |

Where no system credential store is available, credentials can be supplied through environment variables and `--remember` omitted.

The original local server entry points remain available; the bridge is an additional transport path rather than a replacement for stdio MCP.

### Bridge tools and exports

The bridge reuses `playlist`, `library`, `catalog`, `discover`, `playback`, `queue`, and `config`. Their action implementations and schemas remain aligned with the local MCP server. This includes playlist writes and reordering, playback, queue management, sign-in, and preferences.

The original export resources remain available:

```text
exports://list
exports://{filename}
```

The bridge also adds a read-only `exports` tool for clients that can invoke tools but do not directly consume MCP resources.

List exports:

```json
{"action": "list"}
```

Read an export:

```json
{"action": "read", "filename": "tracks_YYYYMMDD_HHMMSS.csv"}
```

CSV/JSON files remain on the host. The tool returns their text content; a host-side file path does not automatically become a downloadable ChatGPT attachment.

### Bridge operating limits

- **Host availability:** the host computer must stay online and awake.
- **Playback location:** audio is played by the host computer; the bridge does not stream Apple Music audio into ChatGPT.
- **Desktop requirements:** browser/Music.app playback still requires the host desktop session and player to be usable.
- **Platform capabilities:** the bridge does not create new engine capabilities. Windows does not gain macOS-only Music.app, AirPlay, or star-rating support.
- **Player ownership:** avoid running multiple MCP instances that compete for the same Chrome profile. The bridge manages one local MCP process of its own.
- **Apple Music sign-in:** interactive Apple Music authorization must be completed on the host; remote calls reuse the host's credentials and preferences.

### Bridge troubleshooting

| Symptom | Check |
|---|---|
| ChatGPT cannot find the tunnel | Workspace association and **Tunnels Read + Use** permissions |
| Tool discovery/calls fail | Keep the bridge running; run `.\scripts\start-bridge.ps1 -Doctor`; inspect the local status page |
| Credentials are requested again | OS account, config directory, and credential-store availability |
| A replaced key is not used | Environment overrides, then run `-Setup` with the intended values |
| Port `8787` is in use | Select another `--health-port` |
| Library queries work but playback fails | Host desktop session, Apple Music sign-in, engine selection, Chrome profile ownership |
| Tool definitions changed after an update | Restart the bridge, refresh the ChatGPT connection, and start a new conversation |

### Bridge development and validation

Focused bridge tests:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_bridge.py tests/test_bridge_tunnel.py tests/test_cli_cov.py -q
```

The test suite covers credential reuse/overrides, child-process credential handling, local stdio initialization, tool-schema parity, export path boundaries, and — when the official client is installed — actual tunnel forwarding against an isolated loopback control plane.

The current bridge validation baseline documented in this fork is MCP Python SDK **1.25.0** with official tunnel-client **0.0.14** on Windows. Re-run validation when those dependencies change.

---

## Added tool: Playlist track reordering

This fork adds:

```text
playlist(action="reorder")
```

for changing the stored track order of an existing editable Apple Music playlist without recreating the playlist or deleting/re-adding its contents.

### Move one entry

```text
playlist(
  action="reorder",
  playlist="Road Trip",
  from_position=5,
  to_position=2
)
```

This moves the fifth entry to the second position.

### Apply a complete order

```text
playlist(
  action="reorder",
  playlist="Road Trip",
  order="3,1,2"
)
```

A JSON-array string is also accepted for a complete permutation.

### Reorder semantics and safeguards

- Positions are **1-based** and refer to the playlist's current API order.
- Display sorting and shuffle state do not change those stored positions.
- A full permutation must contain every current position exactly once.
- Repeated songs are preserved as separate occurrences.
- Music videos and supported track resource types are preserved.
- The playlist ID and playlist membership are preserved.
- `dry_run=True` previews the target order without writing.
- Writes are read back and verified by default.
- `verify=False` submits without post-write verification.
- The implementation reads the complete playlist before writing and rejects partial pagination data.
- A second pre-write check detects edits that occurred during preparation and cancels the reorder.
- This is not an atomic cross-device lock; another device can still edit concurrently after the final check.
- Uncertain writes are **not automatically retried**, because a timeout may occur after Apple already applied the new order.
- The audit log records the previous and requested order for later inspection.

### Requirements

Reordering uses the Apple Music web-player API path and therefore requires:

- a signed-in web session;
- a playlist the web API reports as editable;
- either an exact, unambiguous playlist name or a library playlist ID such as `p.…`.

It works independently of playback `mode` on supported operating systems because it is a playlist web-API operation rather than a playback-engine operation.

---

## Other fork-specific changes

In addition to the two main features above, this fork currently contains several smaller development changes:

- **Batch-track tool descriptions were clarified** so MCP clients can more reliably see that a single `track` parameter can accept multiple tracks, including arrays and comma/newline-separated input.
- **Bilingual project documentation** was added for the fork and the ChatGPT bridge.
- **Bridge installation and startup scripts** were added for the Windows workflow, together with focused bridge/tunnel tests.
- **Personal-fork release automation was disabled/removed** so development in this repository does not accidentally run upstream-oriented publishing workflows.
- Smaller compatibility, integration, workflow, and documentation refinements may be added as the fork evolves.

These changes are maintained in this fork rather than presented as upstream behavior.

---

## Development direction

This repository is intended to remain compatible with useful upstream improvements while developing independently in several areas:

- ChatGPT and remote MCP connectivity
- safer and richer playlist editing
- better batch operations and assistant-facing tool ergonomics
- reliability and validation around remote/local integration
- documentation and setup workflows for personal deployments

Upstream changes may be merged when appropriate, but there is no expectation that fork-specific features will be accepted, released, or supported by the upstream project.

---

## License

This project is distributed under the [MIT License](LICENSE).

It is based on and contains code from [epheterson/applemusic-mcp](https://github.com/epheterson/applemusic-mcp), Copyright © 2024 Eric Pheterson. Modifications and additional functionality in this fork are Copyright © 2026 alwinecor. Both are distributed under the MIT License.

Modifications and additional functionality in this fork are released under the same MIT License.

Apple Music is a trademark of Apple Inc. This is an unofficial community project and is not affiliated with or endorsed by Apple or OpenAI.

## Credits

Upstream project: [epheterson/applemusic-mcp](https://github.com/epheterson/applemusic-mcp)

This project is developed by [@alwinecor](https://github.com/alwinecor) with Codex / ChatGPT.
