# BiliRSS

**Bilibili 音频下载 + RSS 播客订阅服务**

将 B 站 UP 主的视频自动提取音频，生成 Apple 播客兼容的 RSS 订阅源，配合 Web 管理面板进行统一的下载、分类、合集和文件管理。

---
[Bug反馈链接](https://my.feishu.cn/share/base/form/shrcnCWSzz9ZcX8dZTRsa09a8S2)

## 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
  - [本地开发](#本地开发)
  - [服务器部署](#服务器部署)
- [项目结构](#项目结构)
- [使用指南](#使用指南)
- [RSS 订阅](#rss-订阅)
- [音频格式说明](#音频格式说明)
- [API 参考](#api-参考)
- [安全机制](#安全机制)
- [常见问题](#常见问题)
- [更新日志](#更新日志)

---

## 功能特性

- **视频 → 音频** — 单个视频或 UP 主整站批量下载，自动提取音频
- **6 种音频格式** — MP3 / FLAC / M4A / Opus / WAV / 最佳质量
- **RSS 播客源** — 生成 iTunes 兼容的 RSS 2.0 订阅源，可导入 Apple Podcasts、小宇宙等播客客户端
- **分类管理** — 按 UP 主或主题创建分类，音频自动归类
- **合集功能** — 跨分类创建精选合集，支持封面图片上传和密码保护
- **Web 管理面板** — 现代化暗色主题界面，实时任务状态、文件搜索过滤、批量操作
- **实时统计** — 首页 5 秒刷新音频总数、占用空间、磁盘用量、运行时长
- **安全删除** — 全局密钥保护的单个/批量删除，防止误操作
- **一键部署 EXE** — Windows 上无需 Python 环境，双击 `BiliRSS-Deploy.exe` 管理服务器（首次部署 / 更新代码 / 启停 / 日志 / 密钥管理等 11 项功能）
- **Cookie 支持** — 支持传入 B 站 Cookie 以下载仅会员可见内容
- **跨平台** — 本地 Windows 开发 + Linux 服务器生产部署 + Docker 容器化

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
| 部署方式 | systemd / Nginx 反向代理 |

---

## 环境要求

| 依赖 | 最低版本 | 说明 |
|------|----------|------|
| Python | 3.8+ | 推荐 3.10+ |
| Flask | 2.0+ | Web 框架 |
| yt-dlp | 2024.0+ | 视频/音频下载 |
| ffmpeg | 系统安装 | 音频格式转码（必需） |
| paramiko | 2.0+ | 仅部署脚本需要（exe 已内置） |

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

## 快速开始

### 本地开发

```bash
# 1. 进入项目
cd BRSS

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动本地服务
python run_local.py
```

启动后访问 `http://127.0.0.1:5000` 即可看到管理面板。

`run_local.py` 自动在项目目录下创建 `local_data/` 文件夹存放所有数据，不会与系统其他路径冲突。

#### PyCharm 运行配置

1. 右键 `run_local.py` → **Run 'run_local'**
2. 或在 PyCharm 中创建运行配置：
   - Script path: `run_local.py`
   - Working directory: 项目根目录
   - Python interpreter: 你的虚拟环境

### 服务器部署

#### 方式一：一键部署 EXE（推荐，无需 Python 环境）

1. 将 `deploy/dist/` 整个文件夹拷贝到 Windows 电脑
2. 编辑 `config.ini` 填写服务器信息（IP、用户名、密码/密钥）
3. 双击 `BiliRSS-Deploy.exe`，按菜单操作

```
════════════════════════════════════════
  BiliRSS 部署工具
════════════════════════════════════════
  1. 首次部署          6. 查看状态
  2. 更新代码          7. 查看日志
  3. 启动服务          8. 卸载服务
  4. 停止服务          9. 查看密钥
  5. 重启服务         10. 修改密钥
                       0. 退出
════════════════════════════════════════
```

**菜单说明**：

| 选项 | 功能 | 说明 |
|------|------|------|
| 1. 首次部署 | git clone → 上传文件 → 安装依赖 → 创建 systemd → 启动 | 全新服务器一键部署 |
| 2. 更新代码 | git pull → 上传文件 → 重启服务 | 日常更新用 |
| 3-5. 启停重启 | systemctl start/stop/restart | 服务控制 |
| 6. 查看状态 | 运行状态 + 端口监听 + 磁盘用量 | 快速诊断 |
| 7. 查看日志 | journalctl 最近 30 行 | 排查问题 |
| 8. 卸载服务 | 停止 + 禁用 + 删除文件 | 需输入 "yes" 确认 |
| 9. 查看密钥 | 显示服务器当前的删除密钥 | 用于删除音频时的验证 |
| 10. 修改密钥 | 修改删除密钥并自动重启服务 | 密钥含特殊字符也能安全替换 |

#### 方式二：Python 脚本部署

```bash
cd BRSS
python deploy/deploy.py
```

功能和 EXE 完全一致，但需要本机安装 Python 3.8+ 和 paramiko。

#### 方式三：手动部署

```bash
# 上传主程序和模板
scp bili_rss/app.py root@<服务器IP>:/opt/bili-rss/app.py
scp bili_rss/templates/index.py root@<服务器IP>:/opt/bili-rss/templates_index.py
scp bili_rss/templates/category.py root@<服务器IP>:/opt/bili-rss/templates_category.py

# 重启服务
ssh root@<服务器IP> "systemctl restart bilisrs"
```

#### 运维命令

```bash
# 查看状态 + 实时日志
systemctl status bilisrs
journalctl -u bilisrs -f

# 查看音频占用
du -sh /opt/bili-rss/audio/
```

#### 部署文件映射

| 本地文件 | 服务器路径 |
|----------|------------|
| `bili_rss/app.py` | `/opt/bili-rss/app.py` |
| `bili_rss/templates/index.py` | `/opt/bili-rss/templates_index.py` |
| `bili_rss/templates/category.py` | `/opt/bili-rss/templates_category.py` |

> **设计说明**: 本地使用 Python 包结构（`bili_rss/` + 相对导入），服务器展平为单文件以便直接 `python app.py` 运行。部署脚本会自动完成 import 重写。

#### 配置说明（config.ini）

```ini
[BiliRSS Deploy]
SERVER_HOST = 192.168.124.20    # 服务器 IP
SERVER_USER = root              # SSH 用户
SERVER_PORT = 22                # SSH 端口
SERVER_PASS =                   # SSH 密码（与密钥二选一）
SSH_KEY_PATH =                  # SSH 密钥路径（与密码二选一）
APP_PORT = 5000                 # 应用端口
REPO_URL = https://gitee.com/jiajin0920/BRSS.git
REMOTE_BASE = /opt/bili-rss     # 服务器部署路径
SERVICE_NAME = bilisrs          # systemd 服务名
```

> 配置优先级：**环境变量** > `config.ini` > 默认值。支持 `BILI_RSS_BASE_URL`、`SERVER_HOST`、`SERVER_PASS` 等环境变量覆盖。

---

## 项目结构

```
BRSS/
├── bili_rss/                        # 主应用包
│   ├── __init__.py                  # 包标识
│   ├── app.py                       # Flask 入口 + 路由 + 下载逻辑
│   └── templates/                   # HTML 模板（作为 Python 模块）
│       ├── __init__.py
│       ├── index.py                 # 首页模板
│       └── category.py              # 合集页模板
│
├── deploy/                          # 部署工具
│   ├── deploy.py                   # 交互式部署脚本（11 项菜单）
│   ├── build_exe.py                # PyInstaller 打包脚本
│   ├── config.ini                  # 部署配置示例
│   └── dist/                       # 打包输出
│       ├── BiliRSS-Deploy.exe      # Windows 一键部署 EXE
│       └── config.ini              # EXE 同目录配置文件
│
├── scripts/                         # 辅助脚本
│   ├── create_task.py              # 通过 HTTP API 创建下载任务
│   ├── test_wbi_api.py             # 测试 Bilibili wbi API
│   ├── test_wbi_server.py          # 测试 API（使用服务器 cookie）
│   └── test_polymer_api.py         # 测试 Polymer 动态 API
│
├── run_local.py                     # 本地开发入口
├── regen_rss.py                     # 手动 RSS 重新生成
├── requirements.txt                 # Python 依赖
├── UPDATE.md                        # 更新日志
├── README.md                        # 本文件
└── LICENSE                          # MIT License
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

### 分类与合集

**分类（Category）**：按 UP 主或主题对已下载音频进行分组，每个分类有独立的 RSS 订阅源。

**合集（Collection）**：精选跨分类的音频集合，支持：
- 自定义名称和描述
- 上传封面图片（JPG/PNG/GIF/WEBP）
- 设置删除密码保护
- 独立 RSS 订阅源

### 文件管理

- **搜索过滤**: 按标题、BV 号、UP 主名称搜索
- **格式筛选**: 按音频格式（MP3/FLAC/M4A 等）过滤
- **批量选择**: 勾选多个文件，使用底部批量操作栏
- **添加到合集**: 选中文件一键加入指定合集
- **删除**: 需要输入全局删除密钥验证，防止误操作

### Cookie 配置

BiliRSS 使用全局 Cookie 机制。获取方法：
1. 浏览器登录 B 站 → F12 → Application → Cookies → `bilibili.com`
2. 复制完整 Cookie 字符串，粘贴到管理面板

---

## RSS 订阅

### 订阅地址

| 类型 | 地址格式 |
|------|----------|
| 全局 | `http://<IP>:5000/rss/all.xml` |
| 分类 | `http://<IP>:5000/rss/<类别ID>.xml` |
| 合集 | `http://<IP>:5000/rss/col_<合集ID>.xml` |

### 支持的播客客户端

RSS 输出兼容 iTunes 播客规范（`xmlns:itunes`），支持 `itunes:category`、`itunes:image`、`itunes:duration`、`itunes:author` 等扩展字段。

可导入 **Apple Podcasts**、**小宇宙**、**Pocket Casts**、**Overcast**、**AntennaPod** 等主流播客应用。

---

## 音频格式说明

| 格式 | 扩展名 | 特点 | 适用场景 |
|------|--------|------|----------|
| MP3 | `.mp3` | 兼容性最好 | 日常收听 |
| FLAC | `.flac` | 无损压缩，文件较大 | 发烧友、存档 |
| M4A | `.m4a` | Apple 生态友好 | iPhone/iPad/Mac 用户 |
| Opus | `.opus` | 最低码率下音质优异 | 节省存储 |
| WAV | `.wav` | 未压缩原始数据 | 后期处理 |
| 最佳质量 | 自动 | yt-dlp 自动选择 | 不确定时使用 |

---

## API 参考

> 所有 API 返回 JSON，`ok` 字段表示操作是否成功。

### 分类

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/category` | 创建分类 |
| `DELETE` | `/api/category/<cat_id>` | 删除分类 |

### 合集

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/collection` | 创建合集 |
| `DELETE` | `/api/collection/<col_id>` | 删除合集 |
| `POST` | `/api/collection/<col_id>/add` | 添加音频到合集 |
| `POST` | `/api/collection/<col_id>/remove` | 从合集移除音频 |
| `POST` | `/api/collection/<col_id>/cover` | 上传封面图 |

### 任务

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/task` | 创建下载任务 |
| `DELETE` | `/api/task/<task_id>` | 删除任务记录 |
| `POST` | `/api/task/<task_id>/download` | 重新下载 |

**创建任务参数** (`/api/task`):

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `category_id` | string | 是 | 分类 ID |
| `url` | string | 是 | 视频链接/BV号 或 UP 主链接/UID |
| `url_type` | string | 是 | `video` 或 `up` |
| `cookie` | string | 否 | B 站 Cookie 字符串 |
| `audio_format` | string | 否 | 音频格式，默认 `mp3` |

### 音频管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/audio/list` | 获取音频列表（支持 `?search=` 过滤） |
| `DELETE` | `/api/audio/<bv_id>` | 删除单个音频（需 `secret_key`） |
| `POST` | `/api/audio/batch-delete` | 批量删除（需 `secret_key` + `bv_ids`） |
| `POST` | `/api/audio/verify-key` | 验证删除密钥 |

### 统计与状态

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/stats` | 动态统计 |
| `GET` | `/api/status` | 任务下载状态（SSE） |
| `GET` | `/api/server-status` | 服务器磁盘与运行时长 |
| `POST` | `/api/rss/regenerate` | 手动重新生成 RSS |

---

## 安全机制

### 全局删除密钥

删除音频文件需要提供预置的全局密钥。密钥的 SHA256 哈希存储在 `app.py` 中用于验证。

- **查看/修改密钥**：通过部署 EXE 菜单选项 9/10 直接操作服务器上的 `DELETE_SECRET_KEY`
- **使用方式**：管理面板删除操作时弹窗输入密钥，本次会话缓存（sessionStorage），无需反复输入
- **修改密钥后自动重启服务**，立即生效

### 合集密码保护

创建合集时可设置独立的删除密码（SHA256 哈希存储），删除该合集时必须提供正确密码。

---

## 常见问题

### Q: 下载报错 `ffmpeg not found`？

A: 需要系统安装 ffmpeg。Windows: [ffmpeg.org](https://ffmpeg.org) 下载并添加 PATH；Linux: `sudo apt install ffmpeg`。Docker 部署已内置。

### Q: UP 主整站下载提示「未找到视频」？

A: 部分 UP 主动态 API 需登录态 Cookie，请在创建任务时填写有效的 B 站 Cookie。

### Q: RSS 中音频链接指向 localhost？

A: 设置环境变量 `BILI_RSS_BASE_URL=http://你的IP:5000`，或在 systemd unit 中添加 `Environment=` 行。Docker 部署通过 `docker-compose.yml` 的环境变量配置。

### Q: 如何更换删除密钥？

A: 使用部署 EXE 的「10. 修改密钥」选项，输入新密钥后自动替换并重启服务。或手动修改服务器上 `app.py` 中的 `DELETE_SECRET_KEY` 常量并重启。

### Q: 如何部署到新服务器？

A: 使用部署 EXE 的「1. 首次部署」一键完成。

---

## 更新日志

详见 **[UPDATE.md](UPDATE.md)**

---

## 许可证

MIT License — 详见 [LICENSE](LICENSE)

---

*BiliRSS — 把 B 站变成你的私人播客*
