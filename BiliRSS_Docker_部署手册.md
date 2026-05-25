# BiliRSS Docker 部署手册

> **项目简介**：BiliRSS 是一个 Bilibili 音频下载与 RSS 订阅服务，支持 Docker 一键部署。
> **适用系统**：Ubuntu / Debian / 其他 Linux 发行版
> **文档版本**：v1.0 | 2026-05-25

---

## 目录

1. [前置准备](#1-前置准备)
2. [完整部署流程](#2-完整部署流程)
3. [验证部署成功](#3-验证部署成功)
4. [日常更新操作](#4-日常更新操作)
5. [卸载服务](#5-卸载服务)
6. [常见问题与解决方案](#6-常见问题与解决方案)
7. [面板部署（推荐使用Docker Compose 一键部署）](#7面板部署（推荐使用Docker Compose 一键部署）)

---

## 1. 前置准备

### 1.1 系统要求

| 依赖 | 版本要求 | 检查命令 |
|------|----------|----------|
| Docker | 20.10+ | `docker --version` |
| Docker Compose | v2.0+ | `docker compose version` |
| 内存 | ≥ 1GB | `free -h` |
| 磁盘空间 | ≥ 2GB | `df -h` |

### 1.2 服务器准备

- **本地服务器**（物理机/虚拟机）：确保防火墙开放 5000 端口
- **云服务器**（阿里云/腾讯云/AWS 等）：除了系统防火墙，还需在**云控制台安全组**里开放 5000 端口

---

## 2. 完整部署流程

### 第一步：安装 Docker（如果未安装）

#### Ubuntu / Debian 系统

```bash
# 1. 卸载旧版本（如果有的话）
apt remove docker docker-engine docker.io containerd runc

# 2. 安装依赖
apt update
apt install -y ca-certificates curl gnupg

# 3. 添加 Docker 官方 GPG 密钥
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# 4. 添加 Docker 官方仓库
# 注意：如果系统是非标准 Ubuntu（如自定义版本），需手动指定代号
# 标准 Ubuntu 22.04 = jammy, 24.04 = noble
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

# 5. 如果上面报错 "Package has no installation candidate"，手动指定代号：
# echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu jammy stable" | sudo tee /etc/apt/sources.list.d/docker.list

# 6. 安装 Docker
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 7. 启动 Docker 服务
systemctl start docker
systemctl enable docker

# 8. 验证安装
docker --version
docker compose version
```

#### 问题：Docker 官方源访问超时

如果 `apt update` 或 `docker pull` 超时，配置国内镜像加速器：

```bash
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << EOF
{
  "registry-mirrors": [
    "https://docker.1panel.live",
    "https://docker.anyhub.us.kg",
    "https://dockerhub.icu"
  ]
}
EOF

systemctl daemon-reload
systemctl restart docker
```

---

### 第二步：配置 Docker 镜像加速（解决国内网络问题）

**问题现象**：`failed to resolve source metadata for docker.io/library/python:3.11-slim: i/o timeout`

**解决方法**：在 Dockerfile 里将 Debian 官方源替换为国内镜像

在 `Dockerfile` 中添加（在 `apt-get update` 之前）：

```dockerfile
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*
```

---

### 第三步：获取项目代码

```bash
cd ~
git clone https://gitee.com/jiajin0920/BRSS.git
cd BRSS
```

**问题：Git 克隆时提示认证失败**

- 确认仓库地址正确：`https://gitee.com/jiajin0920/BRSS.git`（国内Gitee地址已同步Github代码）

---

### 第四步：创建 .env 配置文件

```bash
cd ~/BRSS
cat > .env << EOF
BILI_RSS_BASE_URL=http://$(hostname -I | awk '{print $1}'):5000
HOST_PORT=5000
EOF
```

---

### 第五步：初始化数据目录

```bash
cd ~/BRSS
mkdir -p data
echo '{"categories": [], "collections": [], "tasks": []}' > data/db.json
```

---

### 第六步：构建并启动服务

```bash
cd ~/BRSS
docker compose up -d --build
```

**首次构建需要 2-3 分钟**（安装 Python 依赖 + ffmpeg + yt-dlp）。

---

## 3. 验证部署成功

### 3.1 检查容器状态

```bash
docker compose ps
```

**正常输出示例**：

```
NAME      IMAGE            COMMAND                  SERVICE   STATUS          PORTS
bilirss   brss-bilirss    "python -m bili_rss.…"   bilirss   Up 5 minutes (healthy)   0.0.0.0:5000->5000/tcp
```

**关键指标**：
- `STATUS` 应该是 `Up` 或 `Up (healthy)`
- `PORTS` 应该显示 `0.0.0.0:5000->5000/tcp`

### 3.2 查看启动日志

```bash
docker compose logs --tail=50
```

**正常输出示例**（最后几行）：

```
* Serving Flask app 'app'
* Debug mode: off
* Running on all addresses (0.0.0.0)
* Running on http://127.0.0.1:5000
* Running on http://172.18.0.2:5000
```

### 3.3 测试本地访问

```bash
curl http://localhost:5000
```

如果返回 HTML 内容，说明服务正常。

### 3.4 浏览器访问管理面板

打开浏览器，访问：

```
http://你的服务器IP:5000
```

> 查服务器 IP：`hostname -I`

---

## 4. 日常更新操作

### 4.1 快速更新（代码更新后）

```bash
cd ~/BRSS

# 1. 拉取最新代码
git pull

# 2. 重新构建并启动（会自动停止旧容器，启动新的）
docker compose up -d --build

# 3. 确认运行正常
docker compose ps
docker compose logs --tail=20
```

### 4.2 仅重启服务（没更新代码）

```bash
cd ~/BRSS
docker compose restart
```

### 4.3 清理旧镜像（节省空间）

```bash
# 删除未使用的镜像
docker image prune -f

# 或者删除所有未使用的资源（镜像+容器+网络）
docker system prune -f
```

---

## 5. 卸载服务

```bash
cd ~/BRSS

# 1. 停止并删除容器（保留数据卷）
docker compose down

# 2. 删除镜像（彻底清理）
docker image rm brss-bilirss

# 3. 清理数据（如果想完全重来，可选）
# rm -rf data/

# 4. 确认清理完成
docker compose ps
docker images | grep brss
```

---

## 6. 常见问题与解决方案

### 6.1 Docker 安装相关问题

#### 问题：Ubuntu 系统正在后台自动更新，导致 apt 锁被占用

**现象**：

```
Waiting for cache lock: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 10209 (unattended-upgr)
```

**原因**：Ubuntu 系统后台自动运行安全更新服务（`unattended-upgrades`），导致软件包管理器的锁文件被占用。

**解决方法**：

**方案一：耐心等待（最推荐）**

等待几分钟到十几分钟，待后台进程自动完成后，锁就会释放。

**方案二：手动终止进程并清理锁（如果不想等）**

```bash
# 1. 停止自动更新服务
systemctl stop unattended-upgrades

# 2. 强制删除残留的锁文件
rm -f /var/lib/dpkg/lock-frontend
rm -f /var/lib/dpkg/lock
rm -f /var/cache/apt/archives/lock
rm -f /var/lib/apt/lists/lock

# 3. 修复可能中断的配置
dpkg --configure -a
apt --fix-broken install
```

**方案三：永久关闭自动更新（可选）**

```bash
systemctl disable unattended-upgrades
```

**查看后台更新进度**：

```bash
# 方法一：查看更新日志
tail -f /var/log/unattended-upgrades/unattended-upgrades.log

# 方法二：检查进程是否还在运行
ps -p 10209  # 替换为实际 PID
```

---

#### 问题：Docker 官方源找不到安装包

**现象**：

```
Package docker-ce is not available, but is referred to by another package.
Error: Package 'docker-ce' has no installation candidate
```

**原因**：系统的 Ubuntu 版本代号（Codename）不在 Docker 官方源的支持列表中。

**解决方法**：

1. 查看系统版本代号：
   ```bash
   lsb_release -c
   cat /etc/os-release
   ```

2. 手动指定标准 Ubuntu 代号（如 `jammy` 或 `noble`）：
   ```bash
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu jammy stable" | tee /etc/apt/sources.list.d/docker.list
   apt update
   apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   ```

3. 或者使用 Docker 官方便捷脚本：
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   ```

---

### 6.2 Docker 构建相关问题

#### 问题：Docker Hub 访问超时

**现象**：

```
failed to resolve source metadata for docker.io/library/python:3.11-slim: failed to do request: Head "https://registry-1.docker.io/v2/library/python/manifests/3.11-slim": dial tcp 69.63.186.31:443: i/o timeout
```

**解决方法**：配置 Docker 镜像加速器（参见 [第二步](#第二步配置-docker-镜像加速解决国内网络问题)）

---

#### 问题：apt-get update 下载极慢（20 分钟以上）

**现象**：

```
[+] Building 1198.7s (3/3) FINISHED
 => RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl ca-certificates && rm -rf /var/lib/apt/lists/*
```

**原因**：Docker 容器内默认连接境外官方软件源，国内网络环境下延迟极高。

**解决方法**：在 Dockerfile 中换用国内镜像源（参见 [第二步](#第二步配置-docker-镜像加速解决国内网络问题)）

---

### 6.3 容器运行相关问题

#### 问题：容器反复重启（Restarting）

**现象**：

```
NAME      IMAGE         COMMAND         SERVICE   STATUS                    PORTS
bilirss   brss-bilirss  "python..."    bilirss   Restarting (1) 12 seconds ago
```

**解决方法**：

1. 查看日志定位错误：
   ```bash
   docker compose logs --tail=100 bilirss
   ```

2. 根据日志错误，对照本手册 [第四步](#第四步创建-env-配置文件) 和 [常见问题](#6-常见问题与解决方案) 进行修复。

---

#### 问题：db.json 缺少必要的 key

**现象**：

```
KeyError: 'categories'
KeyError: 'tasks'
```

**原因**：`db.json` 初始化结构不正确，缺少代码期望的字段。

**解决方法**：

1. 停止容器：
   ```bash
   docker compose down
   ```

2. 初始化正确的 `db.json`：
   ```bash
   echo '{"categories": [], "collections": [], "tasks": []}' > data/db.json
   ```

3. 重新构建启动：
   ```bash
   docker compose up -d --build
   ```

---

### 6.4 网络访问相关问题

#### 问题：服务启动正常，但外网无法访问

**现象**：

- `docker compose ps` 显示容器正常运行
- 服务器上 `curl http://localhost:5000` 能返回内容
- 外网浏览器访问 `http://服务器IP:5000` 超时

**原因**：

1. 服务器防火墙未开放 5000 端口
2. 云服务器安全组未开放 5000 端口

**解决方法**：

**步骤一：检查容器端口映射**

```bash
docker compose ps
```

确认 `PORTS` 列显示 `0.0.0.0:5000->5000/tcp`。

**步骤二：开放服务器防火墙端口**

```bash
# 查看防火墙状态
ufw status

# 如果防火墙是 active，开放 5000 端口
ufw allow 5000/tcp
ufw reload
```

**步骤三：配置云服务器安全组**

登录云控制台，找到服务器 → **安全组** / **防火墙规则**，添加入站规则：

| 协议 | 端口 | 来源 |
|------|------|------|
| TCP | 5000 | 0.0.0.0/0（或指定 IP 段） |

**步骤四：从外网测试**

在你的电脑（不在服务器网络上）运行：

```powershell
Test-NetConnection -ComputerName <服务器公网IP> -Port 5000
```

或者浏览器直接访问 `http://<服务器公网IP>:5000`

---

## 7.面板部署（推荐使用Docker Compose 一键部署）

`docker-compose.yml` 和 `Dockerfile`可以在代码仓库里下载

### 7.1 1Panel 可视化部署（推荐）

#### 第一步：安装 1Panel（如果还没装）

1Panel 是国产的服务器运维面板，对 Docker 支持很好：

- 官方安装文档：<https://1panel.cn/docs/>
- 一键安装命令（Linux）：

bash复制

```
curl -sSL https://resource.fit2cloud.com/1panel/package/quick_start.sh -o quick_start.sh && bash quick_start.sh
```

#### 第二步：通过 1Panel 部署 BiliRSS

1. 打开 1Panel 的 Web 界面（通常在 端口 随机）
2. 进入 **容器** → **编排**（Compose）
3. 点击 **创建编排**
4. 填入名称（如 `bilirss`）
5. 把下面的内容粘贴到编排配置里：

yaml复制

```yaml
services:
  bilirss:
    build: .
    container_name: bilirss
    restart: unless-stopped
    ports:
      - "5000:5000"
    environment:
      - TZ=Asia/Shanghai
      - BILI_RSS_BASE_URL=http://你的服务器IP:5000
    volumes:
      - ./data/audio:/opt/bili-rss/audio
      - ./data/meta:/opt/bili-rss/meta
      - ./data/rss:/opt/bili-rss/rss
      - ./data/cookies:/opt/bili-rss/cookies
      - ./data/covers:/opt/bili-rss/covers
      - ./data/db.json:/opt/bili-rss/db.json
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/"]
      interval: 30s
      timeout: 10s
      retries: 3
```

1. 先把修复后的 `Dockerfile` 上传到服务器
2. 点击 **构建并启动**

------

### 7.2 宝塔面板可视化部署

#### 方式一：用 Docker 管理器（简单）

1. 登录宝塔面板
2. 找到 **软件商店** → **Docker 管理器**
3. 点击 **创建容器**
4. 填写：

- 镜像：`python:3.11-slim`
- 端口映射：`5000:5000`
- 目录挂载：对应 `data/` 下的各个目录
- 启动命令：`python -m bili_rss.app`

1. 但宝塔的 Docker 管理器功能有限，复杂编排不太方便

#### 方式二：用 Docker Compose（推荐）

1. 安装 **宝塔 Docker 插件**（或在终端里操作）
2. 进入项目目录：`/www/wwwroot/BRSS`
3. 把 `docker-compose.yml` 和 `Dockerfile` 上传
4. 在宝塔的 **终端** 里运行：

bash复制

```
  cd /www/wwwroot/BRSS
  docker compose up -d --build
```



## 附录

### A. 常用命令速查表

| 操作 | 命令 |
|------|------|
| 启动服务 | `docker compose up -d` |
| 停止服务 | `docker compose down` |
| 重启服务 | `docker compose restart` |
| 查看状态 | `docker compose ps` |
| 查看日志 | `docker compose logs -f` |
| 重新构建 | `docker compose up -d --build` |
| 进入容器 | `docker compose exec bilirss bash` |
| 查看镜像 | `docker images` |
| 删除镜像 | `docker image rm <镜像名>` |
| 清理资源 | `docker system prune -f` |

### B. 项目文件结构

```
BRSS/
├── docker-compose.yml       # Docker Compose 配置文件
├── Dockerfile              # Docker 镜像构建文件
├── requirements.txt        # Python 依赖列表
├── .env                   # 环境变量配置文件
├── bili_rss/              # 应用源码
│   ├── app.py             # Flask 主应用
│   └── templates/         # 模板文件
└── data/                  # 持久化数据目录（挂载到宿主机）
    ├── audio/             # 下载的音频文件
    ├── meta/              # 音频元数据
    ├── rss/               # RSS XML 文件
    ├── cookies/           # B站 Cookie 文件
    ├── covers/            # 合集封面图片
    └── db.json            # 数据库（分类/合集/任务）
```

### C. 环境变量说明

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `BILI_RSS_BASE_URL` | `http://localhost:5000` | RSS 音频链接的基础地址 |
| `HOST_PORT` | `5000` | 宿主机映射端口 |
| `TZ` | `Asia/Shanghai` | 时区设置 |

---

**文档维护**：如有问题或建议，请在 Github 仓库提交 Issue。
