# BiliRSS

**Bilibili 音频下载 + RSS 播客订阅服务**

将 B 站 UP 主的视频自动提取音频，生成 苹果（播客）兼容的 RSS 播客订阅源，配合 Web 管理面板进行统一的下载、分类、合辑和文件管理。

---

## 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [环境要求](#环境要求)
- [快速开始（本地开发）](#快速开始本地开发)
- [服务器部署](#服务器部署)
- [项目结构](#项目结构)
- [使用指南](#使用指南)
  - [下载音频](#下载音频)
  - [分类与合集](#分类与合集)
  - [文件管理](#文件管理)
  - [Cookie 配置](#cookie-配置)
- [RSS 订阅](#rss-订阅)
- [音频格式说明](#音频格式说明)
- [API 参考](#api-参考)
- [安全机制](#安全机制)
- [常见问题](#常见问题)
- [版本历史](#版本历史)

---

## 功能特性

- **视频 → 音频** — 单个视频或 UP 主整站批量下载，自动提取音频
- **6 种音频格式** — MP3 / FLAC / M4A / Opus / WAV / 最佳质量
- **RSS 播客源** — 生成 苹果（播客） 兼容的 RSS 2.0 订阅源，可直接导入 Apple Podcasts、小宇宙等播客客户端
- **分类管理** — 按 UP 主或主题创建分类，音频自动归类
- **合集功能** — 跨分类创建精选合集，支持封面图片上传和密码保护
- **Web 管理面板** — 现代化暗色主题界面，实时任务状态、文件搜索过滤、批量操作
- **实时统计** — 首页 5 秒刷新音频总数、占用空间、磁盘用量、运行时长
- **安全删除** — 密钥保护的单个/批量删除，防止误操作
- **Cookie 支持** — 支持传入 B 站 Cookie 以下载仅会员可见内容
- **跨平台** — 本地 Windows 开发 + Linux 服务器生产部署

---

## 技术栈

| 层次 | 技术 |
|------|------|
| Web 框架 | Flask (Python) |
| 模板引擎 | Jinja2 (`render_template_string`) |
| 前端交互 | 原生 JavaScript + Vue 3 (CDN) |
| 主题风格 | Tokyo Night Dark |
| 下载引擎 | yt-dlp |
| 音频转码 | ffmpeg |
| 数据存储 | JSON 文件 (`db.json`) |
| 部署 | systemd + Nginx 反向代理 |

---

## 环境要求

| 依赖 | 最低版本 | 说明 |
|------|----------|------|
| Python | 3.8+ | 推荐 3.10+ |
| Flask | 2.0+ | Web 框架 |
| yt-dlp | 2024.0+ | 视频/音频下载 |
| ffmpeg | 系统安装 | 音频格式转码（必需） |
| paramiko | 2.0+ | 仅服务器部署脚本需要 |

### 安装依赖

```bash
pip install -r requirements.txt
```

### 安装 ffmpeg

- **Windows**: 从 [ffmpeg.org](https://ffmpeg.org/download.html) 下载，添加到系统 PATH
- **Linux (Ubuntu/Debian)**:
  ```bash
  sudo apt install ffmpeg
  ```
- **macOS**:
  ```bash
  brew install ffmpeg
  ```

---

## 快速开始（本地开发）

```bash
# 1. 克隆/进入项目
cd musicxx-main

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动本地服务
python run_local.py
```

启动后访问 **http://服务器IP:5000** 即可看到管理面板。

`run_local.py` 会自动在项目目录下创建 `local_data/` 文件夹存放音频、元数据和 RSS，不会与系统其他路径冲突。

### PyCharm 运行配置

1. 右键 `run_local.py` → **Run 'run_local'**
2. 或在 PyCharm 中创建运行配置：
   - Script path: `run_local.py`
   - Working directory: 项目根目录
   - Python interpreter: 你的虚拟环境

---

## 服务器部署

### 环境信息

| 项目 | 值 |
|------|-----|
| 服务器 IP | 服务器IP |
| 部署路径 | `/opt/bili-rss/` |
| 服务名 | `bilisrs` |
| 端口 | 5000（Nginx 反向代理对外） |
| 管理面板 | 1Panel |

### 方式一：自动部署（推荐）

项目自带部署脚本，上传 + 重启 + 验证一气呵成：

```bash
cd musicxx-main
python deploy/deploy.py
```

脚本会自动将本地 Python 包结构展平为服务器所需的扁平结构。

### 方式二：手动部署

```bash
# 上传主程序和模板
scp bili_rss/app.py root@服务器IP:/opt/bili-rss/app.py
scp bili_rss/templates/index.py root@服务器IP:/opt/bili-rss/templates_index.py
scp bili_rss/templates/category.py root@服务器IP:/opt/bili-rss/templates_category.py

# 重启服务
ssh root@服务器IP "systemctl restart bilisrs"

# 验证状态
ssh root@服务器IP "systemctl is-active bilisrs"
```

### 运维命令

```bash
# 查看服务状态
ssh root@服务器IP "systemctl status bilisrs"

# 查看实时日志
ssh root@服务器IP "journalctl -u bilisrs -f"

# 查看音频占用
ssh root@服务器IP "du -sh /opt/bili-rss/audio/"
```

### 部署文件映射

| 本地文件 | 服务器路径 |
|----------|------------|
| `bili_rss/app.py` | `/opt/bili-rss/app.py` |
| `bili_rss/templates/index.py` | `/opt/bili-rss/templates_index.py` |
| `bili_rss/templates/category.py` | `/opt/bili-rss/templates_category.py` |

> **设计说明**: 本地使用 Python 包结构（`bili_rss/` + 相对导入），服务器展平为单文件以便直接 `python app.py` 运行。

---

## 项目结构

```
BRSS/
├── bili_rss/                        # 主应用包
│   ├── __init__.py                  # 包标识
│   ├── app.py                       # Flask 入口 + 路由 + 下载逻辑
│   └── templates/                   # HTML 模板（作为 Python 模块）
│       ├── __init__.py
│       ├── index.py                 # 首页模板 TEMPLATE_INDEX
│       └── category.py              # 合集页模板 CATEGORY_DETAIL_TEMPLATE
│
├── scripts/                         # 辅助脚本
│   ├── create_task.py              # 通过 HTTP API 创建下载任务
│   ├── test_wbi_api.py             # 测试 Bilibili wbi API
│   ├── test_wbi_server.py          # 测试 API（使用服务器 cookie）
│   └── test_polymer_api.py         # 测试 Polymer 动态 API
│
├── deploy/                          # 部署
│   ├── deploy.py                   # 部署脚本（上传 + 重启 + 验证）
│   └── history/                    # 历史版本归档
│       ├── v2/                     # v2: 基础功能
│       ├── v3/                     # v3: 功能完善
│       ├── v4/                     # v4: 删除密钥、封面、状态页
│       └── v5/                     # v5: 批量删除、动态统计、Tab 保持
│
│
└── requirements.txt                # Python 依赖
    
```

### 服务器端数据目录

```
/opt/bili-rss/
├── app.py                   # 主应用
├── templates_index.py       # 首页模板
├── templates_category.py    # 合集模板
├── db.json                  # JSON 数据库
├── audio/                   # 音频文件 (.mp3/.flac/.m4a 等)
├── meta/                    # 元数据 (.info.json)
├── rss/                     # RSS XML 文件
├── cookies/                 # Cookie 文件
└── covers/                  # 合集封面图片
```

---

## 使用指南

### 下载音频

#### 单个视频

1. 打开管理面板，定位到「下载管理」标签页
2. 选择或创建分类
3. 粘贴 B 站视频链接（如 `https://www.bilibili.com/video/BV1xx411c7mD` 或直接输入 `BV1xx411c7mD`）
4. 选择音频格式（默认 MP3）
5. 如有需要，填写 B 站 Cookie
6. 点击「创建任务」

#### UP 主整站下载

1. 类型切换为「UP 主」
2. 粘贴 UP 主空间链接（如 `https://space.bilibili.com/123456`）或直接输入 UID
3. 服务会自动拉取该 UP 主的全部视频列表，跳过已下载的，只下载新增视频

> **注意**: 部分 UP 主的视频列表需要 B 站 Cookie 才能获取，若提示「未找到视频」，请填入有效的 Cookie。

### 分类与合集

**分类（Category）**：按 UP 主或主题对已下载音频进行分组，每个分类有独立的 RSS 订阅源。

**合集（Collection）**：精选跨分类的音频集合，支持：
- 自定义名称和描述
- 上传封面图片（JPG/PNG/GIF/WEBP）
- 设置删除密码保护
- 独立 RSS 订阅源

创建合集后，可在「文件管理」标签页将音频批量添加到合集中。

### 文件管理

- **搜索过滤**: 按标题、BV 号、UP 主名称搜索
- **格式筛选**: 按音频格式（MP3/FLAC/M4A 等）过滤
- **批量选择**: 勾选多个文件，使用底部批量操作栏
- **添加到合集**: 选中文件一键加入指定合集
- **删除**: 需要输入密钥验证，防止误操作

### Cookie 配置

BiliRSS 使用全局 Cookie 机制：最新提交的 Cookie 会保存为全局共享 Cookie 文件。所有任务默认使用此 Cookie，也可以在创建任务时重新提供。

**获取 B 站 Cookie**:
1. 在浏览器中登录 B 站
2. 按 F12 打开开发者工具
3. 进入 Application / 存储 → Cookies → `bilibili.com`
4. 复制完整的 Cookie 字符串

**Cookie 格式示例**:
```
SESSDATA=xxx; bili_jct=xxx; buvid3=xxx; ...
```

---

## RSS 订阅

### 订阅地址

| 类型 | 服务端地址 | 本地地址 |
|------|-----------|----------|
| 全局 | `http://服务器IP/rss/all.xml` | `http://服务器IP:5000/rss/all.xml` |
| 分类 | `http://服务器IP/rss/<类别ID>.xml` | `http://服务器IP:5000/rss/<类别ID>.xml` |
| 合集 | `http://服务器IP/rss/col_<合集ID>.xml` | `http://服务器IP:5000/rss/col_<合集ID>.xml` |

### 支持的播客客户端

RSS 输出兼容 iTunes 播客规范（`xmlns:itunes`），支持以下扩展字段：

- `itunes:category` — 播客分类
- `itunes:image` — 封面图片
- `itunes:duration` — 音频时长
- `itunes:author` — 作者/UP 主

可导入 **Apple Podcasts**、**小宇宙**、**Pocket Casts**、**Overcast**、**AntennaPod** 等主流播客应用。

### 手动重新生成

在管理面板的「RSS 订阅」标签页点击「重新生成」，或调用 API：

```bash
curl -X POST http://服务器IP:5000/api/rss/regenerate
```

> RSS 在每次下载完成、分类删除、合集增删后会自动重新生成。

---

## 音频格式说明

| 格式 | 标签 | 扩展名 | 特点 | 适用场景 |
|------|------|--------|------|----------|
| MP3 | MP3（通用压缩） | `.mp3` | 兼容性最好，几乎所有设备支持 | 日常收听、跨设备同步 |
| FLAC | FLAC（无损） | `.flac` | 无损压缩，音质最佳但文件大 | 发烧友、存档 |
| M4A | AAC/M4A（苹果兼容） | `.m4a` | Apple 生态友好，同码率下优于 MP3 | iPhone/iPad/Mac 用户 |
| Opus（Podcasts不支持） | Opus（高效压缩） | `.opus` | 最低码率下音质优异，文件最小 | 节省存储空间 |
| WAV | WAV（原始无损） | `.wav` | 未压缩原始数据，文件极大 | 后期处理、混音 |
| 最佳质量 | 最佳质量（自动） | 自动 | 由 yt-dlp 选择最佳可用音频流 | 不确定时使用 |

---

## API 参考

> 所有 API 返回 JSON 格式，`ok` 字段表示操作是否成功。

### 分类

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/category` | 创建分类（`name` 必填，`description` 可选） |
| `DELETE` | `/api/category/<cat_id>` | 删除分类及其所有任务 |

### 合集

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/collection` | 创建合集（`name` 必填，`description`/`delete_password` 可选） |
| `DELETE` | `/api/collection/<col_id>` | 删除合集（若设密码需提供 `password`） |
| `POST` | `/api/collection/<col_id>/check-password` | 检查合集密码 |
| `POST` | `/api/collection/<col_id>/add` | 添加 BV 到合集（`bv_ids` 逗号分隔） |
| `POST` | `/api/collection/<col_id>/remove` | 从合集中移除 BV（`bv_ids` 逗号分隔） |
| `POST` | `/api/collection/<col_id>/cover` | 上传合集封面图（multipart，支持 JPG/PNG/GIF/WEBP） |

### 任务

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/task` | 创建下载任务 |
| `DELETE` | `/api/task/<task_id>` | 删除任务记录 |
| `POST` | `/api/task/<task_id>/download` | 重新下载任务 |

**创建任务参数** (`/api/task`):

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `category_id` | string | 是 | 分类 ID |
| `url` | string | 是 | 视频链接/BV号 或 UP 主空间链接/UID |
| `url_type` | string | 是 | `video`（单个视频）或 `up`（UP 主） |
| `cookie` | string | 否 | B 站 Cookie 字符串 |
| `audio_format` | string | 否 | 音频格式，默认 `mp3` |

### 音频管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/audio/list` | 获取全部音频列表（支持 `?search=` 过滤） |
| `DELETE` | `/api/audio/<bv_id>` | 删除单个音频（需 `secret_key`） |
| `POST` | `/api/audio/batch-delete` | 批量删除（需 `secret_key` + `bv_ids`） |
| `POST` | `/api/audio/verify-key` | 验证删除密钥 |

### 统计与状态

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/stats` | 动态统计（音频数、大小、磁盘、运行时长等） |
| `GET` | `/api/status` | 任务下载状态 |
| `GET` | `/api/server-status` | 服务器磁盘与运行时长 |
| `POST` | `/api/rss/regenerate` | 手动触发 RSS 重新生成 |

---

## 安全机制

### 删除密钥

删除音频文件需要提供预置的密钥值。密钥的 SHA256 哈希硬编码在 `app.py` 中，不会以明文存储。

**使用方式**:
1. 在管理面板执行删除操作时弹窗要求输入密钥
2. 密钥验证通过后（sessionStorage 缓存），本次会话可直接操作，无需反复输入

**默认密钥**: 项目内置了一个默认密钥，建议部署到服务器后修改 `app.py` 中的 `DELETE_SECRET_KEY` 常量。

### 合集密码保护

创建合集时可设置删除密码（SHA256 哈希存储），删除该合集时必须提供正确密码，防止误删重要合集。

---

## 常见问题

### Q: 下载报错 `ffmpeg not found`？

A: 需要系统安装 ffmpeg 并确保在 PATH 中。Windows 上从 [ffmpeg.org](https://ffmpeg.org) 下载并添加环境变量；Linux 上执行 `sudo apt install ffmpeg`。

### Q: UP 主整站下载提示「未找到视频」？

A: B 站的 UP 主动态 API 部分需要登录态 Cookie 才能访问。请在创建任务时填写有效的 B 站 Cookie。

### Q: 下载速度慢？

A: yt-dlp 默认不使用代理。如果需要，可在 `app.py` 的 `download_audio` 函数中添加 `--proxy` 参数。B 站对非登录用户的下载有速率限制，使用 Cookie 可改善。

### Q: 如何修改默认音频保存路径？

A: 修改 `app.py` 中的 `BASE_DIR` 常量。本地开发直接在 `run_local.py` 的 `LOCAL_DATA` 变量中修改。

### Q: 页面样式异常或不更新？

A: 清除浏览器缓存。生产模式下 Flask 会缓存 `render_template_string`，更新模板后必须重启服务。

### Q: 如何更换删除密钥？

A: 在 `app.py` 中修改 `DELETE_SECRET_KEY` 常量为你的新密钥，SHA256 哈希会自动重新计算。注意需要同步更新管理面板中已缓存的密钥。

---

## 版本历史

| 版本 | 主要更新 |
|------|----------|
| v2 | 基础功能：Web 管理界面、yt-dlp 下载、RSS 生成 |
| v3 | 功能完善、Bug 修复 |
| v4 | 删除密钥保护、合集封面图上传、服务器状态页、版权声明 |
| v5 | 批量删除 + 密钥核验、首页统计 5 秒实时刷新、Tab 状态保持（sessionStorage）、模态框独立渲染、Vue 3 动态运行时长计数器 |

---

## 许可证

本项目为 MIT License。

---

*BiliRSS — 把 B 站变成你的私人播客*
