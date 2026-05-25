# BiliRSS Docker 镜像
# 基于 Python 3.11-slim，包含 yt-dlp + ffmpeg

FROM python:3.11-slim

LABEL maintainer="jiajin"
LABEL description="BiliRSS - Bilibili Audio RSS Server"

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 【核心优化】将 Debian 官方源替换为清华大学开源镜像站
# python:3.11-slim 底层是 Debian 系统，因此需要修改 /etc/apt/sources.list.d/debian.sources
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# 应用目录
WORKDIR /opt/bili-rss

# 安装 yt-dlp（独立安装，不放在 requirements.txt 中便于单独升级）
RUN pip install --no-cache-dir yt-dlp

# 复制并安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码（保留完整包结构，支持相对导入）
COPY bili_rss /opt/bili-rss/bili_rss/

# 创建数据目录 + 初始化 db.json 文件（正确的 JSON 结构）
RUN mkdir -p /opt/bili-rss/audio /opt/bili-rss/meta /opt/bili-rss/rss /opt/bili-rss/cookies /opt/bili-rss/covers && \
    echo '{"categories": [], "collections": [], "tasks": []}' > /opt/bili-rss/db.json

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# 启动（使用模块方式，支持相对导入）
CMD ["python", "-m", "bili_rss.app"]
