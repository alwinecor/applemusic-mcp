# ChatGPT bridge

[English](chatgpt-bridge.md) | **简体中文**

通过 OpenAI Secure MCP Tunnel，将本地 Apple Music MCP 服务器连接到 ChatGPT Chat。Bridge 运行在已有 Apple Music 引擎的电脑上，通过 ChatGPT 插件连接提供这些工具。

如果客户端通过 stdio 在本机启动服务器，请使用[本地 MCP 配置](../README.zh-CN.md#local-mcp-setup)。

## 工作原理

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

官方 `tunnel-client` 负责传输和隧道认证。Bridge 启动一个本地 MCP 进程，并串行向它派发请求，让远程调用共享同一个桌面播放器和引擎状态。

Secure MCP Tunnel 支持在 ChatGPT 开发者模式中建立私有连接，无需开放供互联网入站访问的端口。公开提交插件需要稳定的公网 HTTPS MCP 服务及相应认证配置；本指南中的私有隧道适用于个人或工作区使用。详情见[官方 Secure MCP Tunnel 指南](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)。

## 使用要求

- 包含 bridge 功能的本仓库源码、Python 3.10+，以及下述 Windows 配置步骤使用的 [uv](https://docs.astral.sh/uv/)。
- 满足所选引擎的 [Apple Music 使用要求](../README.zh-CN.md#local-mcp-setup)。连接 ChatGPT 前，请先在主机上完成 Apple Music 登录。
- 官方 [OpenAI tunnel-client](https://github.com/openai/tunnel-client/releases/latest)。
- 目标 ChatGPT 账户或工作区的开发者模式权限。
- 一个关联到该 ChatGPT 工作区的 OpenAI 隧道，以及具有 **Tunnels Read + Use** 权限的 runtime API key。创建或编辑隧道还需要 **Read + Manage** 权限。这些权限与 ChatGPT 开发者模式权限相互独立。

隧道凭据用于向 OpenAI 认证 bridge。现有 Apple Music 凭据继续用于向 Apple Music 认证本地引擎。

## Windows 配置

在仓库根目录的 PowerShell 中执行以下命令。

### 1. 安装项目和隧道客户端

创建或更新项目环境：

```powershell
uv sync --extra dev
```

安装官方 Windows 隧道客户端：

```powershell
.\scripts\install-bridge.ps1
```

安装脚本会根据检测到的系统架构下载官方最新版本，对照发布文件中的 SHA-256 校验值进行验证，然后解压到 `.bridge/tunnel-client`。下载的压缩包和程序文件均不会纳入 Git。

### 2. 检查本地 MCP

```powershell
.\scripts\start-bridge.ps1 -Check
```

该命令执行真实的本地 stdio 握手，并逐项比较 bridge 中的原有工具定义与本地服务器是否一致。它不需要 OpenAI 密钥，也不会建立到 ChatGPT 的连接。

### 3. 准备隧道

在 [OpenAI Tunnel 设置](https://platform.openai.com/settings/organization/tunnels)中创建或选择隧道，将其关联到准备使用它的 ChatGPT 工作区，并获取具有所需隧道权限的 runtime API key。运行 bridge 应使用 runtime key，不要使用 admin key。

### 4. 启动 bridge

```powershell
.\scripts\start-bridge.ps1
```

首次启动时，在本地终端输入 Tunnel ID 和 runtime key。密钥输入隐藏。启动器会按下文说明保存凭据，后续启动自动读取。

ChatGPT 使用该连接期间，请保持终端运行。默认本地状态页为 [http://127.0.0.1:8787/ui](http://127.0.0.1:8787/ui)。按 **Ctrl+C** 可停止 bridge。

## 从 ChatGPT 连接

配置连接和发现工具时，请保持 bridge 运行。

1. 在 ChatGPT 中打开 **Settings > Security and login**，启用 **Developer mode**。
2. 打开 [ChatGPT Plugins](https://chatgpt.com/plugins)，点击添加按钮。
3. 填写名称，例如 **Apple Music Local Bridge**。
4. 在 **Connection** 中选择 **Tunnel**，然后选择隧道或输入其 ID。
5. 创建连接并检查发现的工具：原有七组 Apple Music 工具，加上 `exports`。
6. 在新对话中选择该插件。先请求检查状态，再让它列出歌单。

例如：

> 使用 Apple Music Local Bridge 检查我的 Apple Music 连接状态。

读写工具仍受 ChatGPT 的工具启用和确认设置约束。开发者模式是否可用，取决于账户和工作区策略。详情见[官方连接说明](https://developers.openai.com/plugins/deploy/connect-chatgpt)和[开发者模式指南](https://developers.openai.com/api/docs/guides/developer-mode)。

## 凭据保存与日常使用

每次使用相同命令启动即可：

```powershell
.\scripts\start-bridge.ps1
```

Windows 启动器将凭据分别保存在两处：

| 内容 | 保存位置 |
|---|---|
| 当前选择的 Tunnel ID | `~/.config/applemusic-mcp/bridge.json` |
| Runtime API key | Windows 凭据管理器，服务名为 `applemusic-mcp-bridge`，按 Tunnel ID 区分 |

配置目录遵循项目的 `APPLEMUSIC_CONFIG_DIR` 和 `APPLEMUSIC_MCP_HOME` 覆盖设置。配置文件只保存 Tunnel ID。密钥在启动时注入隧道客户端的进程环境，不写入明文密钥文件，也不出现在命令行参数中。凭据存储失败时会报错，不会自动降级为明文保存。

要更换凭据，或只保存凭据而不启动隧道：

```powershell
.\scripts\start-bridge.ps1 -Setup
```

显式参数和环境变量的优先级高于已保存的值。`-Setup` 忽略之前保存的值，但仍会使用传入的参数或环境变量。若要手动输入新值，请先清除这些覆盖设置。

Windows 启动器每次运行都会保存本次选用的值。若只想通过环境变量临时覆盖，而不更新已保存的凭据，请直接运行 CLI，且不要加 `--remember`。

## CLI 参考与其他平台

在 macOS 或 Linux 上，安装官方 `tunnel-client` 并将其加入 `PATH`，也可通过 `--client` 指定程序路径。在已安装本仓库的 Python 环境中运行：

```bash
applemusic-mcp bridge --check
applemusic-mcp bridge --setup
applemusic-mcp bridge --doctor
applemusic-mcp bridge
```

保存凭据需要可用的系统凭据存储。若环境中没有可用的凭据存储，请通过环境变量提供 `CONTROL_PLANE_TUNNEL_ID` 和 `CONTROL_PLANE_API_KEY`，并省略 `--remember`。

| 选项 | 用途 |
|---|---|
| `--check` | 验证本地 MCP 工具定义和资源发现，然后退出。 |
| `--setup` | 输入并保存凭据，然后退出。 |
| `--doctor` | 运行官方隧道客户端的诊断。 |
| `--interactive` | 在本地提示输入缺失的凭据。 |
| `--remember` | 保存选用的 Tunnel ID 和 runtime key。 |
| `--tunnel-id ID` | 覆盖已保存的 Tunnel ID。 |
| `--client PATH` | 指定官方 tunnel-client 可执行文件。 |
| `--health-port PORT` | 设置本机回环地址的状态端口；默认为 `8787`，`0` 表示自动分配。 |

`--check`、`--setup` 和 `--doctor` 互斥，不能同时使用。

| 环境变量 | 用途 |
|---|---|
| `CONTROL_PLANE_TUNNEL_ID` | 覆盖 Tunnel ID；显式 `--tunnel-id` 参数优先。 |
| `CONTROL_PLANE_API_KEY` | 覆盖所选隧道的 runtime key。 |
| `APPLEMUSIC_TUNNEL_CLIENT` | 覆盖客户端程序路径；显式 `--client` 参数优先。 |

原有的 `applemusic-mcp serve` 和不带参数的 `python -m applemusic_mcp` 继续用于启动本地 stdio MCP 服务器。

## 工具与导出

Bridge 复用 `playlist`、`library`、`catalog`、`discover`、`playback`、`queue` 和 `config`。它们的名称、描述、输入与输出 schema、annotations，以及各项操作的实现均保持一致，包括歌单写入和排序、播放、队列管理、登录和偏好设置。

原有的 `exports://list` 和 `exports://{filename}` 资源同样可用。另增加只读 `exports` 工具，让只调用工具的客户端也能访问导出内容。

调用 `exports` 列出可用导出文件：

```json
{"action": "list"}
```

然后使用返回结果中的准确文件名读取内容：

```json
{"action": "read", "filename": "tracks_YYYYMMDD_HHMMSS.csv"}
```

示例文件名只是占位符。CSV 和 JSON 文件仍保存在主机上，读取操作返回其文本内容。本地文件路径不会自动变成 ChatGPT 中可下载的附件，较大结果也仍受客户端工具输出长度限制。

## 运行限制

- **主机可用性：** 主机需保持在线且不休眠。播放需要其桌面会话和播放器可用。
- **音频输出：** 音频从主机电脑播放，bridge 不会将播放器音频流传入 ChatGPT。
- **平台支持：** Bridge 保留主机现有引擎支持的能力，不会为 Windows 增加 macOS 专有的 Music.app、AirPlay 或星级评分功能。参见[引擎功能对照表](../README.zh-CN.md#features)。
- **播放器占用：** 避免同时运行多个争用同一 Chrome profile 的 MCP 实例。Bridge 会自行管理一个本地 MCP 进程。
- **登录：** 在主机电脑上完成交互式 Apple Music 登录。远程调用继续使用该主机的凭据和偏好。

## 故障排查

| 问题 | 检查方法 |
|---|---|
| ChatGPT 找不到隧道 | 确认隧道与目标工作区的关联，以及调用者的 Tunnels Read + Use 权限。 |
| 工具发现或调用失败 | 保持 bridge 运行，执行 `.\scripts\start-bridge.ps1 -Doctor`，并查看本地状态页。 |
| 再次要求输入凭据 | 确认使用相同的操作系统账户和配置目录，并检查系统凭据存储是否可访问。 |
| 更换密钥后仍未使用新密钥 | 检查环境变量覆盖设置，再用预期的值运行 `-Setup`。 |
| 端口 `8787` 已被占用 | 通过 CLI 的 `--health-port` 使用其他端口。 |
| 资料库查询正常，但播放失败 | 检查主机桌面会话、Apple Music 登录状态、所选引擎和 Chrome profile 是否被其他实例占用。 |
| 更新后工具定义发生变化 | 重启 bridge，在 ChatGPT 中刷新插件连接，并使用新对话。 |

## 开发与验证

在仓库根目录运行相关测试：

```powershell
.venv\Scripts\python.exe -m pytest tests/test_bridge.py tests/test_bridge_tunnel.py tests/test_cli_cov.py -q
```

测试覆盖凭据复用和覆盖规则、子进程凭据传递、本地 stdio 初始化、原有工具 schema 一致性，以及导出路径边界。安装官方客户端后，还会通过本机回环地址上的模拟控制面验证真实隧道转发，包括工具发现、Unicode 导出读取、资源读取、错误转发和 ping。未安装官方程序时，该项测试会跳过。

这些测试使用隔离状态，不需要真实的 OpenAI 或 Apple 账户，也不能替代 ChatGPT 账户级连接检查或真实播放验证。本地验证基准为 Windows 上的 MCP Python SDK **1.25.0** 和官方 tunnel-client **0.0.14**。升级依赖后，请重新运行这些检查。
