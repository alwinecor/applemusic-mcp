# applemusic-mcp

[English](README.md) | **简体中文**

[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![macOS](https://img.shields.io/badge/macOS-15%20%7C%2026-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-server-purple.svg)](https://modelcontextprotocol.io/)

> **本仓库是 [epheterson/applemusic-mcp](https://github.com/epheterson/applemusic-mcp) 的独立 fork。**
>
> 上游项目提供 Apple Music MCP server 的核心实现及本地 Apple Music 集成。本 fork 在此基础上继续开发，目前主要增加了 **ChatGPT bridge**、**歌单曲目顺序调整**，以及若干面向独立 fork 的集成、工作流与文档改进。
>
> 如需查看上游项目完整的功能说明、引擎实现、API 行为及原始文档，请直接参阅 **[上游 README](https://github.com/epheterson/applemusic-mcp#readme)**。

## 关于本 fork

上游项目由 Eric Pheterson 创建，提供了本仓库所基于的 Apple Music MCP 核心能力。

概括而言，上游已经实现：

- **音乐目录与资料库访问**：搜索、浏览、最近播放/添加、推荐、排行榜、喜爱项目、支持情况下的评分，以及资料库写入。
- **歌单管理**：列出、搜索、创建、添加/移除曲目、复制、重命名、删除、文件夹及相关歌单操作。
- **播放与待播清单控制**：播放、暂停/切歌等 transport controls、音量/随机/循环、Now Playing、支持情况下的 AirPlay，以及 Up Next queue。
- **多种 Apple Music 引擎**：macOS 上的 Music.app 与 Safari，以及跨平台的 Apple Music API 和基于 Chrome 的 MusicKit 路径。
- **本地 MCP 运行方式**：通过标准的 `applemusic-mcp serve` stdio server 连接 Claude Desktop、Cursor、Cline、Windsurf、Codex 等本地 MCP 客户端。

上游原有七组 action-based MCP 工具：

| 工具 | 主要用途 |
|---|---|
| `playlist` | 歌单与文件夹操作 |
| `library` | 资料库搜索、浏览、写入、喜爱项目、评分、快照 |
| `catalog` | Apple Music 目录搜索与元数据 |
| `discover` | 推荐、排行榜、电台、相关艺人 |
| `playback` | 播放、transport controls、设置、应用内显示、AirPlay |
| `queue` | Up Next 待播清单管理 |
| `config` | 登录、偏好、状态、审计日志、storefront |

本 fork 目前主要增加或修改了：

1. **ChatGPT bridge**：通过 OpenAI Secure MCP Tunnel，将运行在本地的 MCP server 连接到 ChatGPT。
2. **歌单曲目顺序调整**：增加 `playlist(action="reorder")`，支持预览、写入后验证，并针对不完整读取或检测到的并发编辑进行保护。
3. **其他 fork-specific 改进**：英/中文文档、bridge 安装与启动工具、验证测试、批量曲目参数说明，以及适合独立 fork 的维护调整。

此后，本 fork 将主要围绕 **ChatGPT 远程连接、更丰富的歌单操作、集成可靠性，以及工作流/文档完善** 继续独立开发。适合的上游更新仍可能继续合并，但本仓库特有的功能由本 fork 独立维护，不应被视为上游项目已经实现或正式支持的功能。

---

## 本地 MCP 配置

如果只需要上游原始版本及其标准本地 MCP 功能，最简单的安装方式仍然是直接按照 **[上游 README](https://github.com/epheterson/applemusic-mcp#readme)** 操作。

如果需要使用**本 fork 的新增功能**，应从本仓库源码安装。

### 使用要求

- Python 3.10+
- 下述源码工作流使用的 [uv](https://docs.astral.sh/uv/)
- 以下条件之一：使用 Mac 上的 Music.app / Safari 路径，或拥有 Apple Music 订阅以使用 API / 浏览器路径
- 使用 Chrome 网页播放器引擎时需要 Google Chrome + Playwright

### 从源码安装

```bash
git clone https://github.com/alwinecor/applemusic-mcp.git
cd applemusic-mcp
uv sync --extra dev
```

在仓库环境中启动本地 stdio MCP server：

**Windows**

```powershell
.\.venv\Scripts\applemusic-mcp.exe serve
```

**macOS / Linux**

```bash
./.venv/bin/applemusic-mcp serve
```

在本地 MCP 客户端中，将 `command` 指向上述可执行文件，并传入 `serve`。

例如：

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

Windows 请改为 `.venv\Scripts\applemusic-mcp.exe` 对应的绝对路径。

### Apple Music 登录

上游 server 主要提供两种跨平台授权方式：

```bash
applemusic-mcp login --dev
```

使用 Apple Developer MusicKit key，是推荐的官方 API 路径。

```bash
applemusic-mcp login
```

使用已经登录的 Apple Music 网页会话。macOS 可从 Safari 获取会话；Windows / Linux 使用 Chrome 路径。

在 macOS 上，本地 Music.app 路径本身也可以在不使用跨平台 API 的情况下覆盖相当一部分资料库和播放功能。

完整的引擎能力矩阵、浏览器要求、token 行为、限流及 Apple 相关注意事项请查看 **[上游 README](https://github.com/epheterson/applemusic-mcp#readme)**。

---

## ChatGPT bridge 配置

这是本 fork 在上游本地 MCP 基础上新增的功能。

ChatGPT bridge 通过 **OpenAI Secure MCP Tunnel**，将同一个本地 Apple Music MCP server 提供给 ChatGPT Chat 使用。

Bridge 运行在实际承载 Apple Music 引擎的电脑上。它不会把 Apple Music 的执行过程迁移到云端：资料库操作、浏览器自动化、Music.app 控制和音乐播放仍发生在主机电脑。

### 架构

```text
ChatGPT Chat 插件连接
             |
OpenAI Secure MCP Tunnel
             | 主机发起的出站 HTTPS 连接
本地 tunnel-client
             | stdio
applemusic_mcp.bridge_server
             |
现有 Apple Music API / Chrome / Safari / Music.app 引擎
```

官方 `tunnel-client` 负责传输与隧道认证。Bridge 启动一个本地 MCP 进程，并串行将请求派发给它，因此远程调用共享同一个播放器及引擎状态。

由于连接由主机主动向外建立，私有 tunnel 不需要在本地电脑上开放互联网入站端口。

这里介绍的 tunnel 主要用于 ChatGPT developer mode 下的个人/工作区私有连接。公开发布 plugin 需要不同的公网托管和认证配置。

### 使用要求

- 包含 bridge 实现的本 fork 源码
- Python 3.10+
- Windows 源码工作流使用的 `uv`
- 已在主机上配置好准备使用的 Apple Music 引擎
- 官方 [OpenAI tunnel-client](https://github.com/openai/tunnel-client/releases/latest)
- 目标 ChatGPT 账户或工作区的 developer mode 权限
- 一个与该 ChatGPT 工作区关联的 OpenAI tunnel
- 具有 **Tunnels Read + Use** 权限的 runtime API key
- 创建或修改 tunnel 时需要 **Read + Manage** 权限

Tunnel 凭据用于让本地 bridge 向 OpenAI 认证。Apple Music 凭据仍保留在本地 Apple Music 引擎中，用于向 Apple 完成相应认证。

### Windows bridge 配置

在仓库根目录的 PowerShell 中执行以下步骤。

#### 第 1 步：安装项目和 tunnel client

```powershell
uv sync --extra dev
```

然后安装官方 Windows tunnel client：

```powershell
.\scripts\install-bridge.ps1
```

安装脚本会根据检测到的系统架构下载当前官方 release，对照 release 提供的 SHA-256 校验值进行验证，然后解压到 `.bridge/tunnel-client`。下载的 bridge 二进制文件和压缩包不会纳入 Git。

#### 第 2 步：检查本地 MCP

```powershell
.\scripts\start-bridge.ps1 -Check
```

该命令会执行真实的本地 stdio 握手，并检查 bridge 暴露的原有 MCP 工具定义是否与本地 server 保持一致。此步骤**不需要** OpenAI key，也**不会**建立到 ChatGPT 的连接。

#### 第 3 步：准备 OpenAI tunnel

在 [OpenAI Tunnel settings](https://platform.openai.com/settings/organization/tunnels) 中创建或选择 tunnel，将其关联到准备使用该 tunnel 的 ChatGPT workspace，并获取具有对应 tunnel 权限的 runtime API key。

运行 bridge 应使用 runtime key，而不是 admin key。

#### 第 4 步：启动 bridge

```powershell
.\scripts\start-bridge.ps1
```

首次启动时，在本地终端输入 Tunnel ID 和 runtime API key。密钥输入会隐藏。启动器会保存所选 tunnel 的相关配置，后续启动可以自动复用。

ChatGPT 使用 bridge 期间需要保持该终端运行。默认本地状态页：

```text
http://127.0.0.1:8787/ui
```

按 **Ctrl+C** 停止 bridge。

### 从 ChatGPT 连接 tunnel

配置连接和发现工具时，请保持 bridge 正在运行。

1. 在 ChatGPT 中打开 **Settings > Security and login**，启用 **Developer mode**。
2. 打开 **ChatGPT Plugins**，添加新的 plugin / connection。
3. 填写名称，例如 **Apple Music Local Bridge**。
4. 在 **Connection** 中选择 **Tunnel**。
5. 选择对应 tunnel，或输入 Tunnel ID。
6. 创建连接并检查发现出的工具。
7. 在新对话中选择该 plugin，可以先检查连接状态，再尝试列出歌单。

Bridge 会暴露上游原有七组 Apple Music 工具，以及额外的只读 `exports` 工具。

读写操作仍受 ChatGPT 的工具权限、确认设置和账户/工作区策略约束。

官方参考：

- [Secure MCP Tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
- [Connect plugins to ChatGPT](https://developers.openai.com/plugins/deploy/connect-chatgpt)
- [Developer mode](https://developers.openai.com/api/docs/guides/developer-mode)

### 凭据保存与日常使用

日常使用只需运行：

```powershell
.\scripts\start-bridge.ps1
```

Windows 下，凭据分别保存在项目配置和操作系统凭据存储中：

| 内容 | 保存位置 |
|---|---|
| 当前选择的 Tunnel ID | `~/.config/applemusic-mcp/bridge.json` |
| Runtime API key | Windows Credential Manager，service 为 `applemusic-mcp-bridge`，按 Tunnel ID 区分 |

配置文件只保存 Tunnel ID。API key 在启动时被注入 tunnel client 的进程环境，不会写入明文 key 文件，也不会作为命令行参数传递。如果安全凭据存储失败，启动器会报错，而不是自动降级为明文保存。

要更换凭据，或只保存凭据而不启动 bridge：

```powershell
.\scripts\start-bridge.ps1 -Setup
```

显式 CLI 参数和环境变量的优先级高于已保存值。

### Bridge CLI 与其他平台

在 macOS 或 Linux 上，安装官方 `tunnel-client` 并将其加入 `PATH`，也可以使用 `--client` 显式指定路径。

在已安装本 fork 的 Python 环境中运行：

```bash
applemusic-mcp bridge --check
applemusic-mcp bridge --setup
applemusic-mcp bridge --doctor
applemusic-mcp bridge
```

主要选项：

| 选项 | 用途 |
|---|---|
| `--check` | 验证本地 MCP 工具定义和资源发现，然后退出 |
| `--setup` | 输入并保存 bridge 凭据，然后退出 |
| `--doctor` | 运行官方 tunnel-client 诊断 |
| `--interactive` | 在本地提示输入缺失凭据 |
| `--remember` | 保存选择的 Tunnel ID 和 runtime key |
| `--tunnel-id ID` | 覆盖已保存的 Tunnel ID |
| `--client PATH` | 指定 tunnel-client 可执行文件 |
| `--health-port PORT` | 设置本机回环状态端口；默认 `8787`，`0` 为自动分配 |

`--check`、`--setup` 和 `--doctor` 互斥。

环境变量：

| 变量 | 用途 |
|---|---|
| `CONTROL_PLANE_TUNNEL_ID` | 覆盖 Tunnel ID |
| `CONTROL_PLANE_API_KEY` | 覆盖 runtime API key |
| `APPLEMUSIC_TUNNEL_CLIENT` | 覆盖 tunnel-client 可执行文件 |

如果系统没有可用的 credential store，可以通过环境变量提供凭据，并省略 `--remember`。

原有本地 server 的启动入口仍然保留；bridge 是新增的 transport path，并不会取代 stdio MCP。

### Bridge 工具与导出

Bridge 复用 `playlist`、`library`、`catalog`、`discover`、`playback`、`queue` 和 `config`。这些工具的 action 实现和 schema 与本地 MCP server 保持一致，包括歌单写入和排序、播放、队列管理、登录和偏好设置。

原有导出资源继续可用：

```text
exports://list
exports://{filename}
```

Bridge 另外增加一个只读 `exports` 工具，供能够调用工具、但不能直接消费 MCP resource 的客户端读取导出内容。

列出导出文件：

```json
{"action": "list"}
```

读取导出：

```json
{"action": "read", "filename": "tracks_YYYYMMDD_HHMMSS.csv"}
```

CSV / JSON 文件仍保存在主机上。工具返回其文本内容；主机本地文件路径不会自动变成 ChatGPT 中可下载的附件。

### Bridge 运行限制

- **主机可用性**：主机需要保持在线且不休眠。
- **播放位置**：音乐由主机电脑播放；bridge 不会把 Apple Music 音频流传入 ChatGPT。
- **桌面环境**：浏览器 / Music.app 播放仍要求主机桌面会话和播放器可用。
- **平台能力**：bridge 不会创造新的引擎能力，例如 Windows 不会因此获得 macOS 专属的 Music.app、AirPlay 或星级评分功能。
- **播放器占用**：避免同时运行多个争用同一 Chrome profile 的 MCP 实例；bridge 会自行管理一个本地 MCP 进程。
- **Apple Music 登录**：交互式 Apple Music 授权仍需在主机完成；远程调用复用主机的凭据与偏好。

### Bridge 故障排查

| 问题 | 检查内容 |
|---|---|
| ChatGPT 找不到 tunnel | Workspace 关联以及 **Tunnels Read + Use** 权限 |
| 工具发现/调用失败 | 保持 bridge 运行；执行 `.\scripts\start-bridge.ps1 -Doctor`；查看本地状态页 |
| 再次要求输入凭据 | OS 账户、配置目录以及 credential store 是否可访问 |
| 更换 key 后仍未生效 | 检查环境变量覆盖，然后使用预期值运行 `-Setup` |
| `8787` 端口被占用 | 改用其他 `--health-port` |
| 资料库查询正常但播放失败 | 主机桌面会话、Apple Music 登录、引擎选择、Chrome profile 占用 |
| 更新后工具定义变化 | 重启 bridge、刷新 ChatGPT connection，并开启新对话 |

### Bridge 开发与验证

运行 bridge 相关测试：

```powershell
.venv\Scripts\python.exe -m pytest tests/test_bridge.py tests/test_bridge_tunnel.py tests/test_cli_cov.py -q
```

测试覆盖凭据复用/覆盖、子进程凭据处理、本地 stdio 初始化、工具 schema 一致性、导出路径边界；安装官方 client 后，还会通过隔离的本机回环 control plane 验证实际 tunnel forwarding。

本 fork 当前记录的 bridge 验证基准为 Windows 上的 MCP Python SDK **1.25.0** 与官方 tunnel-client **0.0.14**。升级相关依赖后应重新运行验证。

---

## 新增工具：歌单曲目顺序调整

本 fork 增加：

```text
playlist(action="reorder")
```

用于调整已有、可编辑 Apple Music 歌单中实际储存的曲目顺序，而无需重新创建歌单，也不会通过删除并重新添加曲目的方式实现。

### 移动一项

```text
playlist(
  action="reorder",
  playlist="Road Trip",
  from_position=5,
  to_position=2
)
```

将第 5 项移动到第 2 项。

### 指定完整顺序

```text
playlist(
  action="reorder",
  playlist="Road Trip",
  order="3,1,2"
)
```

完整 permutation 也可以使用 JSON 数组字符串。

### Reorder 语义与保护机制

- 位置从 **1 开始**，对应歌单当前的 API 顺序。
- 播放器界面排序方式和 shuffle 状态不会改变这些储存位置。
- 完整 permutation 必须包含当前每个位置，并且每个位置只出现一次。
- 重复歌曲会作为不同 occurrence 保留。
- 音乐视频及支持的 track resource types 会保留。
- 歌单 ID 和歌单曲目成员不会改变。
- `dry_run=True` 可在不写入的情况下预览目标顺序。
- 默认在写入后重新读取并验证。
- `verify=False` 可提交写入但跳过写入后验证。
- 写入前会读取完整歌单，若分页结果不完整则拒绝执行。
- 真正写入前会再次检查，若发现准备过程中发生了编辑则取消 reorder。
- 该检查并不是跨设备的原子锁；最终检查之后，其他设备仍可能同时修改歌单。
- 写入结果不确定时**不会自动重试**，因为 timeout 可能发生在 Apple 已经接受新顺序之后。
- 审计日志会记录原顺序和请求的新顺序，供后续检查。

### 使用要求

Reorder 走 Apple Music 网页播放器 API 路径，因此需要：

- 已登录的网页会话；
- 一个被网页 API 标记为可编辑的歌单；
- 精确且唯一的歌单名称，或 `p.…` 形式的 library playlist ID。

由于这是歌单 web-API 操作而非播放引擎操作，因此在支持的操作系统上不依赖当前 playback `mode`。

---

## 其他 fork-specific 改动

除上述两项主要功能之外，本 fork 当前还包含一些较小的开发改动：

- **进一步明确批量曲目参数说明**，使 MCP 客户端更容易识别一个 `track` 参数可以一次传入多首曲目，包括数组、逗号分隔和换行分隔形式。
- **增加英/中文项目文档**以及完整的 ChatGPT bridge 双语说明。
- **增加 Windows bridge 安装与启动脚本**，并补充针对 bridge / tunnel 的验证测试。
- **禁用/移除个人 fork 不需要的上游自动发布流程**，避免本仓库的日常开发误触发面向上游 package/release 的发布工作流。
- 后续仍可能继续加入较小的兼容性、集成、工作流和文档调整。

这些内容由本 fork 独立维护，不作为上游项目行为进行描述。

---

## 后续开发方向

本仓库会在吸收有价值的上游更新的同时，主要沿以下方向继续独立开发：

- ChatGPT 与远程 MCP 连接
- 更安全、更丰富的歌单编辑能力
- 更好的批量操作与面向 AI assistant 的工具 ergonomics
- 本地/远程集成的可靠性与验证
- 面向个人部署的文档及 setup workflow

适合的 upstream changes 仍可能继续 merge，但本 fork 的特有功能并不默认会被上游接受、发布或提供支持。

---

## 许可证

本项目以 [MIT License](LICENSE) 发布。

本仓库基于并包含 [epheterson/applemusic-mcp](https://github.com/epheterson/applemusic-mcp) 的代码，原项目 Copyright © 2024 Eric Pheterson，同样采用 MIT License。

本 fork 中的修改和新增功能也以相同的 MIT License 发布。

Apple Music 是 Apple Inc. 的商标。本项目为非官方社区项目，与 Apple 或 OpenAI 均无关联，也未获得其背书。

## 致谢

上游项目：[epheterson/applemusic-mcp](https://github.com/epheterson/applemusic-mcp)

本项目由 [@alwinecor](https://github.com/alwinecor) 与Codex / ChatGPT 共同实现。
