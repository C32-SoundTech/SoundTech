# SoundTech 声像科技 - Docker 部署镜像
# 基于 Python 3.11 官方镜像

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    TZ=Asia/Shanghai \
    ANONYMIZED_TELEMETRY=False

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsqlite3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app.py .
COPY config/ ./config/
COPY handlers/ ./handlers/
COPY agentic/ ./agentic/
COPY templates/ ./templates/
COPY resources/ ./resources/

# 复制静态文件 (包含向量数据库、知识库等 AI 答疑必需文件)
COPY static/ ./static/

# 创建日志目录
RUN mkdir -p /app/logs

# 复制入口脚本
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 暴露端口
EXPOSE 443

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f -k https://localhost:443/login || exit 1

# 入口点
ENTRYPOINT ["/entrypoint.sh"]
