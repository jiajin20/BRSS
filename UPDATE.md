# BiliRSS 更新日志

## v6 — 2026-05-25

### 新增
- **一键部署 EXE**：`deploy/dist/BiliRSS-Deploy.exe`，无需 Python 环境，双击运行即可管理服务器
- **交互式部署菜单**：11 项功能（首次部署 / 更新代码 / 启停重启 / 状态 / 日志 / 卸载 / 查看密钥 / 修改密钥），操作完成后自动重新展示菜单
- **INI 配置文件**：`config.ini` 替代 Python 配置，exe 同目录放置，首次运行自动创建默认配置
- **部署进度显示**：Git clone、pip install、文件上传、服务操作均有旋转动画 + 计时器（MM:SS）
- **远程密钥管理**：菜单直接查看/修改服务器 `app.py` 中的删除密钥（DELETE_SECRET_KEY），修改完自动重启服务

### 修复
- 修复 `generate_rss()` 中 RSS enclosure URL 指向 `localhost` 而非实际访问 IP 的问题（改用 `Host` 请求头动态拼接）
- 修复 `download_audio` / `download_up_videos` 后台线程并发写 `db.json` 数据丢失（加 `threading.Lock`）
- 修复首次部署时 git clone 失败不清理、目录已存在不删除的问题（`_cleanup_clone` finally 清理）
- 修复 PyInstaller 打包后 `config.ini` 路径错误（`sys.frozen` 检测 exe 运行环境）
- 修复修改密钥时特殊字符（`$#.'"` 等）导致 shell 转义崩溃（改用 base64 + SFTP 临时脚本）

### 改进
- 部署时自动检查并安装缺失的 Python 依赖（逐包 `pip show` + 缺啥装啥）
- Systemd unit 通过 SFTP 写入（避免 heredoc 转义问题）
- 配置文件优先级：环境变量 > config.ini > 自动创建的默认值
- 环境变量支持 `BILI_RSS_BASE_URL` 和 `SERVER_PASS` / `SSH_KEY_PATH` 等配置项

---

## v5 — 2026-05

### 新增
- 批量删除音频 + 全局密钥核验（DELETE_SECRET_KEY）
- 首页统计 5 秒实时刷新（音频总数、磁盘用量、运行时长）
- Tab 状态保持（sessionStorage），刷新页面后回到最后操作标签页
- 模态框独立渲染，避免页面整体重载
- Vue 3 动态运行时长计数器

---

## v4

### 新增
- 合集删除密码保护（SHA256 哈希存储）
- 合集封面图上传（JPG/PNG/GIF/WEBP，保存到 `covers/`）
- 服务器磁盘与运行时长状态页（`/api/server-status`）
- 版权声明页

---

## v3

### 新增
- 功能完善，Bug 修复
- 删除密钥保护机制
- 合集增删改功能完善

---

## v2

### 新增
- Web 管理界面（Vue 3 + Tokyo Night Dark 主题）
- yt-dlp 视频/音频下载引擎
- RSS 2.0 播客源生成（iTunes 兼容）
- 分类管理（按 UP 主 / 主题分组）
- 6 种音频格式支持（MP3 / FLAC / M4A / Opus / WAV / 最佳质量）

---

## v1

- 项目初始化，基础 Flask 架构
