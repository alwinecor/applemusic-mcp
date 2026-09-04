# applemusic-mcp

[English](README.md) | **简体中文**

[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![macOS](https://img.shields.io/badge/macOS-15%20%7C%2026-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-server-purple.svg)](https://modelcontextprotocol.io/)

Apple Music 的 MCP 服务器，让各类 [MCP 客户端](https://modelcontextprotocol.io/clients)（Claude、Cursor、Cline、Windsurf 等）管理歌单、资料库、音乐目录、发现推荐、播放和“待播清单”（Up Next）。支持 macOS、Windows 和 Linux。

**本地使用只需一台 Mac，或一个 Apple Music 订阅。** 四种引擎可按调用选择：Mac 上的 Music.app 和 Safari，以及跨平台的 Apple Music API 和 Chrome。

## 连接方式

根据助手的运行方式选择连接：

| 连接方式 | 客户端 | 启动入口 | 说明 |
|---|---|---|---|
| **本地 MCP**（默认） | Claude Desktop、Cursor、Codex 等本地 MCP 客户端 | `applemusic-mcp serve` | [本地 MCP 配置](#local-mcp-setup) |
| **ChatGPT bridge**（可选） | 通过 Secure MCP Tunnel 插件连接的 ChatGPT Chat | `applemusic-mcp bridge` | [ChatGPT bridge 使用指南](docs/chatgpt-bridge.zh-CN.md) |

两种连接方式使用相同的本地 Apple Music 引擎。Bridge 通过 OpenAI Secure MCP Tunnel 提供远程访问，支持保存隧道凭据，并增加供 ChatGPT 读取导出文件的工具。它需要配置 OpenAI 隧道，并具有 ChatGPT 开发者模式权限。音乐仍在运行 MCP 的电脑上播放；该电脑需要保持在线，桌面播放器也需要可用。

<a id="features"></a>

## 功能

服务器提供四种引擎。**Native** 通过 AppleScript 控制 macOS 本机的 Music.app；**API** 在各操作系统上调用 Apple Music 网页 API（`amp-api.music.apple.com`）；**Safari** 在 macOS 上控制已登录的 Safari MusicKit 播放器，原生支持 DRM，无需额外安装；**Chrome** 在各操作系统上启动本地 Google Chrome 窗口，通过 MusicKit 播放 DRM 音频。

`mode` 偏好决定默认引擎：`auto`（默认）组合各引擎的能力，在 macOS 上用 Music.app 播放、Safari 管理待播清单、API 获取数据，其他平台使用 Chrome。也可固定为 `native` / `safari` / `chrome` / `api`，或通过 `engine=` 覆盖某一次播放或队列调用。下表的 **Browser** 同时包含 Safari 和 Chrome 网页播放器。`✓` 表示支持，`✗` 表示该引擎无法实现，`—` 表示不适用。

| 功能 | Native（Music.app）macOS | API（amp-api）各平台 | Browser（Safari：macOS / Chrome：各平台） |
|---|:---:|:---:|:---:|
| **音乐目录搜索 / 浏览** | ✓ | ✓（另支持无需 token 的匹配解析） | — |
| 推荐 / 排行榜 / 搜索建议 | ✗ | ✓ | — |
| **资料库搜索 / 浏览** | ✓ | ✓ | — |
| 按流派搜索 | ✓ | ✗ | — |
| 最近播放 / 最近添加 | ✓ | ✓ | — |
| **将目录中的音乐加入资料库** | ✓ | ✓ | ✓（页面内 POST） |
| 从资料库移除 | ✓ | ✓ | — |
| 喜欢 / 不喜欢 | ✓ | ✓ | — |
| **1–5 星评分** | ✓ | ✗ | ✗ |
| 喜爱项目列表 | ✓ | ✗ | ✗ |
| **歌单**创建 / 添加 / 移除 / 重命名 | ✓ | ✓ | — |
| 复制歌单 | ✓ | ✗ | — |
| 删除歌单 | ✓ | ✓（网页 token） | — |
| 文件夹：单层及移入 / 移出 | ✓ | ✓ | — |
| 文件夹：嵌套路径 / 树 / `path` | ✓ | ✗ | ✗ |
| **播放**：歌曲 / 专辑 / 歌单 / URL | ✓ | — | ✓ |
| 控制：暂停 / 停止 / 下一首 / 上一首 / 跳转进度 | ✓ | — | ✓ |
| 设置：音量 / 随机播放 / 循环播放 | ✓ | — | ✓ |
| 当前播放信息 `now_playing` | ✓ | — | ✓ |
| **待播清单**：查看 / 下一首 / 最后播放 / 移除 / 跳转 / 清空 / 自动播放 | ✗ | — | ✓ |
| 在应用中显示 | ✓ | — | ✓（页面跳转） |
| 选择 AirPlay 设备 | ✓ | ✗ | ✗ |
| 资料库快照 / 完整性检查 | ✓ | ✗ | ✗ |
| **无需 Apple 账户即可使用** | ✓ | ✗ | ✗ |
| **跨平台（Windows / Linux）** | ✗ | ✓ | ✓ |

**API** 列中的功能均可独立运行，不需要浏览器或“音乐”应用。浏览器播放和待播清单需要桌面会话及网页播放器：macOS 可用 **Safari**（无需安装），其他平台使用 **Google Chrome**。

<a id="setup"></a>
<a id="local-mcp-setup"></a>

## 本地 MCP 配置

本节适用于由本地 MCP 客户端通过 stdio 启动服务器的方式。要在 ChatGPT Chat 中建立插件连接，请参阅独立的 [ChatGPT bridge 使用指南](docs/chatgpt-bridge.zh-CN.md)。

**要求：** Python 3.10+，以及一台 Mac 或一个 Apple Music 订阅。Chrome 网页播放器提供跨平台播放和待播清单功能，需要 [Google Chrome](https://www.google.com/chrome/) 和 Playwright。**macOS 可以不安装这两项**：通过 Safari 登录，并使用“音乐”应用播放。因此 macOS 默认安装较轻量，不包含约 500 MB 的 Playwright 下载。Windows / Linux 默认包含 Playwright，因为这是这些平台的播放路径。

**Claude Code** 可用一行命令配置：

```bash
claude mcp add "Apple Music" -- uvx applemusic-mcp serve
```

**Claude Desktop / Cursor / Cline / Windsurf**：先安装，再添加配置：

```bash
pipx install applemusic-mcp        # 或：pip install applemusic-mcp
# 非 macOS 平台还需下载浏览器引擎：playwright install chromium
# macOS 可使用 Safari 登录 + Music.app，无需上述浏览器安装。
# 若要在 Mac 使用 Chrome 网页播放器：
# pipx install 'applemusic-mcp[browser]'，然后 playwright install chromium
```

```json
{
  "mcpServers": {
    "Apple Music": {
      "command": "applemusic-mcp",
      "args": ["serve"]
    }
  }
}
```

重启客户端，然后试着说：“列出我的 Apple Music 歌单”或“播放我喜欢的歌曲”。macOS 本地资料库和播放功能可以立即使用。要添加目录中的音乐，或在其他操作系统上使用，请先登录。

### 登录

跨平台 API 支持两种凭据获取方式。

**Apple Developer token（推荐）。** 这是 Apple 官方支持的路径，需要加入 [Apple Developer Program](https://developer.apple.com/programs/) 并创建 MusicKit 密钥。一条引导命令即可写入配置、生成有效期为 6 个月的 token，并完成授权：

```bash
applemusic-mcp login --dev      # 提示输入 Team ID、Key ID 和 .p8 路径
```

获取 MusicKit 密钥的方法见[附录](#appendix-developer-token)。

**网页登录。** 这是快捷路径，也是直接运行 `applemusic-mcp login` 的默认行为。密码不会交给本工具；登录状态会保留，token 会在过期前重新获取。也可以直接让助手帮你启动登录流程。网页登录使用 Apple 网页播放器 API，与 [Cider](https://github.com/ciderapp/Cider-2)、[Music Assistant](https://www.music-assistant.io/music-providers/apple-music/) 等开源客户端采用的路径相同。

- **macOS：从已登录的 Safari 读取会话，无需 Chrome 或约 500 MB 的 Playwright。**

  ```bash
  applemusic-mcp login            # macOS 默认从 Safari 获取会话
  applemusic-mcp status           # 检查状态
  ```

  Safari 需要一次性设置：在 **Safari → 设置 → 高级** 中启用 **“显示网页开发者功能”**，再从 **“开发”** 菜单启用 **“允许来自 Apple 事件的 JavaScript”**。这是由你手动开启的安全选项，工具不会代为切换。请先在 Safari 的 [music.apple.com](https://music.apple.com) 页面登录。工具通过该功能从你自己的 Safari 会话中读取一个 cookie，即 Apple Music token；之后可关闭该选项。如果选项未开启或尚未登录，`login` 会给出处理步骤，也可改用 `--dev` 或 `--chrome`。想在 Mac 上使用 Chrome，可先运行 `pip install 'applemusic-mcp[browser]'`，再运行 `applemusic-mcp login --chrome`。使用 Safari 登录并配合 Music.app 播放时，Mac 完全不需要 Chrome。

- **Windows / Linux：打开本地 Chrome。** 这些平台默认安装 Playwright，并使用这一路径。

  ```bash
  applemusic-mcp login            # 打开 Chrome 的 music.apple.com 页面，登录一次即可
  ```

**批量操作建议使用 `--dev`。** 网页登录使用 Apple 网页播放器的公共 token，请求配额与其他使用者共享。普通交互通常不会触及限额，但每小时数百次目录搜索，例如导入歌单或迁移资料库，可能触发 `HTTP 429`。这条路径不会返回 `Retry-After`，限流采用约 60 分钟的滚动窗口，短暂等待通常不能解除，继续重试还可能延长等待。`applemusic-mcp login --dev` 使用你自己的 MusicKit 密钥，拥有独立且更大的配额。遭遇限流时，工具会明确报告，不会把空结果当成“找不到歌曲”。

<details>
<summary>配置文件位置、引擎模式与源码安装</summary>

**客户端配置文件：** Claude Desktop 在 macOS 上使用 `~/Library/Application Support/Claude/claude_desktop_config.json`，Windows 上使用 `%APPDATA%\Claude\claude_desktop_config.json`。Cursor、Cline、Windsurf 使用同样的 `mcpServers` 结构，具体位置请参阅各客户端文档。

**`mode` 偏好**决定引擎：`auto` 默认组合各引擎；`native` 只使用 Music.app，无需账户；`safari` 控制已登录的 Safari，仅限 macOS，无需 Chrome / Playwright；`chrome` 使用跨平台 Chrome 网页播放器；`api` 只使用 REST，支持数据读取和写入，不支持播放。可通过对话设置，例如 `config(action="set-pref", preference="mode", string_value="safari")`。单次播放或队列调用可用 `engine=`（`native` / `safari` / `chrome` / `web`）覆盖，例如先在 Safari 排队，再调用 `playback(action="play", engine="safari")`。操作队列会将对应引擎设为当前活动引擎，后续播放控制也会发往该引擎。Safari 引擎操作你实际使用的 Safari，但只操作 `music.apple.com` 标签页；Chrome 使用独立窗口。

**Chrome 网页播放器功能**需要 Google Chrome 和 Playwright。非 macOS 平台默认安装 Playwright；**macOS 需自行选择安装**（`pip install 'applemusic-mcp[browser]'`），因为 Safari 登录和 Music.app 播放已能覆盖常见需求。安装后需执行一次浏览器下载：`playwright install chromium`，或 `uvx --from applemusic-mcp playwright install chromium`。Playwright 自带的 Chromium 无法解码 Apple DRM，因此仍需安装真正的 Chrome。这些功能会打开本地 Chrome 窗口，不适合无桌面的服务器。网页播放器会自动使用现有登录凭据授权，无需再次登录：Safari 获取的 token 或开发者 token 会传入播放器配置。因此在 macOS 上，一次 `login` 即可覆盖 API、原生播放以及 Chrome 网页播放器和队列。

**源码安装：** `git clone … && pip install -e .`，然后将客户端配置的 `command` 指向 `<repo>/venv/bin/applemusic-mcp`，也可使用 `python -m applemusic_mcp`。

</details>

## 官方 API 与网页接口

服务器通过三条路径访问 Apple Music，并优先使用可用的官方方式：

- **Apple Music API（官方）。** 使用 `login --dev` 生成的开发者 token，调用 Apple 公开文档中的 `api.music.apple.com`。
- **网页播放器（社区使用的路径）。** 使用已登录 `music.apple.com` 会话的 token 调用网页播放器后端，与 [Cider](https://github.com/ciderapp/Cider-2)、[Music Assistant](https://www.music-assistant.io/music-providers/apple-music/) 类似，补充公开 API 未提供的功能。
- **Music.app（macOS）。** 通过 AppleScript 在本机操作你自己的应用，无需 token 或网络。

有开发者 token 时，写入优先使用官方 API；只有公开 API 无法完成的操作才走网页接口。仅使用网页登录时，操作走网页接口。在 macOS 上，资料库和歌单编辑还可以在 Music.app 本地完成。每次写入都会报告使用了哪条路径。

| 写入操作 | Apple Music API | 网页播放器 | Music.app（macOS） |
|---|:---:|:---:|:---:|
| 添加到资料库 | ✓ | ✓ | ✓ |
| 创建歌单 | ✓ | ✓ | ✓ |
| 添加歌曲到 API 创建的歌单 | ✓ | ✓ | ✓ |
| 添加歌曲到 Music.app 创建的歌单 | ✗ | ✗ | ✓ |
| 1–5 星评分 | ✗ | ✗ | ✓ |
| 喜欢 / 不喜欢 | ✓ | ✓ | ✓ |
| 删除歌单 | ✗ | ✓ | ✓ |
| 重命名 / 移入文件夹 | 部分支持 | ✓ | ✓ |

`✗` 表示对应路径无法完成该操作，工具会尝试其他路径。Apple 的一项限制是：**只有创建歌单的客户端才能编辑该歌单**。因此，Music.app 创建的歌单不能通过开发者 token API 或网页播放器写入；macOS 上会转为 Music.app 本地添加，其他平台应使用 API / 网页创建的歌单。

## 使用示例

直接告诉助手你想做什么：

- “创建一个叫 Road Trip 的歌单，加入节奏明快的 90 年代另类音乐。”
- “把 Hey Jude 加到 Road Trip 歌单，再从健身歌单移除最后 3 首。”
- “把我的歌单整理到摇滚、爵士、电子三个文件夹里。”
- “随机播放健身歌单，并将 Bohemian Rhapsody 设为下一首。”
- “找一些和 Bohemian Rhapsody 类似的歌曲，加入我的资料库。”
- “我最近都听了什么？现在排行榜上有什么？”
- “将我的资料库导出为 CSV。”

## 工具

七组以 `action` 为入口的工具减少 MCP 上下文占用。每组工具按操作选择相应引擎。

| 工具 | 操作 |
|---|---|
| `playlist` | list, folders, tracks, search, create, add, copy, move, reorder, remove, delete, rename, path（歌单和文件夹） |
| `library` | search, add, browse, favorites, recently_played, recently_added, rate, remove, snapshot |
| `catalog` | search, resolve, album_tracks, album_details, song_details, artist_details, genres, suggestions |
| `discover` | recommendations, heavy_rotation, charts, top_songs, similar_artists, personal_station, song_station |
| `playback` | play（歌曲 / 专辑 / 歌单 / URL）, control, now_playing, settings, reveal, airplay |
| `queue` | list, set, play_next, play_last, remove, jump, clear, autoplay（待播清单：macOS 默认 Safari，其他平台默认 Chrome；可用 `engine=` 指定） |
| `config` | status, signin, logout, reset, set-pref, audit-log, clear-audit-log, list-storefronts |

<details>
<summary>常用模式</summary>

- **`track` 一个参数即可批量传入歌曲。** 可传单个名称或 ID、逗号或换行分隔的列表，或 JSON 数组（`["A","B"]`、`[{"name":"A","artist":"X"}]`）。整张专辑可用 `album`。
- **从其他服务导入歌单时，先匹配，再添加。** `catalog(action="resolve", …)` 将曲目列表匹配为目录 ID，不执行写入。有 ISRC 时使用 `isrcs=`；Spotify、Rekordbox 和 Plex 导出都可能包含 ISRC，可以每次请求精确匹配 25 首，避免逐首模糊搜索带来的 `429`。使用 `tracks=` 传入名称和艺人时，结果会报告匹配置信度，便于写入前识别错误版本；这条路径每首歌曲需要一次请求，默认最多处理 25 首，可通过 `max_tracks` 提高。两种方式返回的 ID 均可直接交给 `playlist(action="add", track=…)`。
- **添加前预览：** `playlist(action="add", …, dry_run=True)` 会执行与实际添加相同的匹配，并比较歌单现有内容，但不写入。例如仅搜索 `Dont Let Me Down` 而不指定艺人，可能匹配到 The Chainsmokers 而非 The Beatles，预览可提前发现。它只预览匹配和重复情况，不保证后续写入一定成功。
- **调整歌单顺序：** `playlist(action="reorder", playlist="Road Trip", from_position=5, to_position=2)` 将第 5 项移到第 2 项。也可用 `order="3,1,2"` 指定三首歌的完整顺序，或传 JSON 数组字符串。位置从 **1 开始，以当前 API 歌单顺序为准**，不受播放器界面排序或随机播放影响。完整顺序必须包含每个位置且仅出现一次，包括重复歌曲的不同位置。`dry_run=True` 可预览；默认写入后验证，`verify=False` 可跳过验证。操作保留歌单 ID 和曲目成员，包括音乐视频。任意操作系统上均需要网页登录会话和网页 API 标记为可编辑的歌单，不受 `mode` 影响；名称须精确且唯一，也可使用资料库歌单 ID（`p.…`）。写入前会完整读取并再次检查，拒绝不完整数据或已发现的并发编辑；该检查不是对其他设备编辑的原子锁。失败或结果不确定的写入不会自动重试，审计日志会记录原顺序及目标顺序供检查。
- **添加到歌单时**会自动搜索目录并跳过重复歌曲。连续填充歌单的工作流可将 `auto_add` 偏好设为 `true`（默认 `false`）。`track` 也支持**目录歌曲 ID**（例如 `1440857781`），便于准确指定不同发行版本。
- **将尚未入库的目录歌曲加入 Music.app 创建的歌单，需要两步。** 开发者 API 无法直接写入这类歌单，工具会先通过 API 加入资料库，再等 iCloud 同步到本机后附加到歌单，通常只需几秒。同步较慢时会提示“已加入资料库，请重新执行以添加到歌单”，此时重复同一次添加即可。少数情况下，同步等待超过约 20 秒后，Music.app 会短暂显示以触发最后一次同步尝试，然后将焦点还给原应用，这是预期行为。
- **列表输出格式：** `format` 可为 `text` / `json` / `csv` / `none`；`export` 将结果写入文件，通过 `exports://` MCP resource 读取；`full` 包含完整元数据。
- **URL 播放**支持专辑、歌单和歌曲：`playback(action="play", url="https://music.apple.com/...")`。
- **地区商店：** 目录操作支持可选的 `storefront`，例如 `storefront="it"`，可查询其他地区而不修改默认设置。

</details>

## CLI

```bash
applemusic-mcp serve            # 启动 MCP 服务器，由客户端调用
applemusic-mcp login            # 网页登录：macOS 使用 Safari，Windows/Linux 使用 Chrome
applemusic-mcp login --chrome   # 强制使用 Chrome 网页播放器，macOS 需选装
applemusic-mcp login --dev      # Apple Developer token 授权流程（.p8）
applemusic-mcp logout           # 退出登录，可用于切换账户
applemusic-mcp status           # 显示认证状态
applemusic-mcp reset --force    # 清除凭据，保留 .p8 密钥文件
applemusic-mcp reset --all --force   # 完全卸载状态：同时删除 .p8、浏览器配置和缓存
```

## 使用提示

- **macOS 播放需要屏幕解锁并授予辅助功能权限。** 原生目录播放通过 System Events 操作 Music.app，并移动鼠标点击播放。请在“系统设置 → 隐私与安全性 → 辅助功能”中授权，或设置 `mode="safari"` 改用 Safari 网页播放器，后者无需辅助功能权限或 Chrome。
- **Safari 首次播放需要一次真实点击。** 新打开或重新加载的标签页受浏览器自动播放规则限制，必须先手动点击 Apple Music 页面中的 ▶。之后即可免手动操作地播放、暂停和切歌。如果工具显示队列已就绪，但歌曲停在 0:00，通常只需在页面点击一次播放。
- **新创建的歌单需要短暂等待**，云端完成同步后才能通过 API 添加歌曲；已有歌单通常可立即操作。
- **部分功能仅限 macOS**，没有对应的 Apple Music API：1–5 星评分、喜爱项目、资料库快照、AirPlay 和嵌套文件夹路径。
- **目录操作开始失败时**，请重新运行 `applemusic-mcp login`。部分歌单会静默撤销 AppleScript 修改，这是一个[已知的 Music.app 问题](https://www.macscripter.net/t/add-current-track-from-apple-music-to-playlist/72058)；服务器会检测并报告这种回滚。

<a id="appendix-developer-token"></a>

## 附录：开发者 token

推荐使用此路径。加入 [Apple Developer Program](https://developer.apple.com/programs/) 后：

1. **获取 MusicKit 密钥。** 打开 [Apple Developer Portal → Keys](https://developer.apple.com/account/resources/authkeys/list)，点击 **+**、填写名称、勾选 **MusicKit**、注册，然后下载仅能下载一次的 `.p8` 文件。记录 **Key ID** 和 **Team ID**。
2. **运行引导流程：**

   ```bash
   applemusic-mcp login --dev
   ```

   按提示输入 Team ID、Key ID 和 `.p8` 路径，也可用 `--team-id`、`--key-id`、`--key-path` 参数传入。工具会写入 `~/.config/applemusic-mcp/config.json`，生成有效期为 180 天、使用时自动续期的开发者 token，并授权用户 token。

---

## 上游项目与本分支开发

本仓库是 [epheterson/applemusic-mcp](https://github.com/epheterson/applemusic-mcp) 的独立 fork，原项目由 Eric Pheterson 创建。

上游项目提供 Apple Music MCP 服务器的核心实现及本地 Apple Music 集成功能。本 fork 在此基础上继续开发。目前已经加入或完成的主要改动包括：

- **ChatGPT bridge：** 通过 OpenAI Secure MCP Tunnel，让 ChatGPT Chat 可以远程连接运行在本地的 Apple Music MCP server；同时支持保存隧道凭据，并提供可供 ChatGPT 读取导出内容的机制。
- **歌单曲目顺序调整：** 为 `playlist` 工具增加 `reorder` action，可在保留歌单本身及曲目成员的前提下调整顺序，并支持预览、写入后验证和并发修改检查。
- **其他细节改进：** 随着开发继续进行，包含一些较小的集成、兼容性、工作流和文档层面的调整与完善。

在条件合适时，本 fork 仍可能继续吸收上游项目的更新。本仓库特有的功能由本 fork 独立维护，不应视为上游项目的一部分，也不代表获得上游项目的官方支持。

ChatGPT bridge 的架构和配置方式见 [docs/chatgpt-bridge.zh-CN.md](docs/chatgpt-bridge.zh-CN.md)。

## 许可证

本项目以 [MIT License](LICENSE) 发布。

本仓库基于并包含 [epheterson/applemusic-mcp](https://github.com/epheterson/applemusic-mcp) 的代码，原项目 Copyright © 2024 Eric Pheterson，同样采用 MIT License。

本 fork 中的修改和新增功能也以相同的 MIT License 发布。

Apple Music 是 Apple Inc. 的商标。本项目为非官方社区项目，与 Apple 或 OpenAI 均无关联，也未获得其背书。

## 致谢

[FastMCP](https://github.com/jlowin/fastmcp) · [Apple MusicKit](https://developer.apple.com/documentation/applemusicapi) · [Model Context Protocol](https://modelcontextprotocol.io/)
