#!/bin/bash
# SoundTech Docker 入口脚本

set -e

echo "=========================================="
echo "SoundTech 声像科技 启动中..."
echo "=========================================="

# 检查必要的环境变量
if [ -z "$DASHSCOPE_API_KEY" ]; then
    echo "警告: DASHSCOPE_API_KEY 未设置，AI 答疑功能将不可用"
else
    echo "DASHSCOPE_API_KEY 已配置"
fi

# 设置默认值
export DASHSCOPE_API_BASE=${DASHSCOPE_API_BASE:-"https://dashscope.aliyuncs.com/compatible-mode/v1"}
export SECRET_KEY=${SECRET_KEY:-"soundtech-default-secret-key"}
export ANONYMIZED_TELEMETRY="False"

# 更新配置文件中的 API Key (使用环境变量)
if [ -n "$DASHSCOPE_API_KEY" ]; then
    cat > /app/config/custom_key.toml << EOF
[KEY_LIST]
DASHSCOPE_API_KEY='${DASHSCOPE_API_KEY}'
DASHSCOPE_API_BASE='${DASHSCOPE_API_BASE}'
EOF
    echo "API Key 配置已更新到 config/custom_key.toml"
fi

# 确保目录存在且有正确权限
mkdir -p /app/logs
mkdir -p /app/data

# 检查向量数据库是否存在
if [ -f "/app/static/chroma.sqlite3" ]; then
    echo "向量数据库已就绪 (ChromaDB)"
else
    echo "警告: 向量数据库不存在，AI 答疑功能可能受限"
fi

# 检查知识库是否存在
if [ -f "/app/static/maoist_sqlite.db" ]; then
    echo "知识库已就绪 (SQLite Store)"
else
    echo "警告: 知识库不存在"
fi

# 检查用户数据库
if [ ! -f "/app/static/database.db" ]; then
    echo "用户数据库将在首次启动时自动创建"
fi

echo "=========================================="
echo "启动 Flask 应用 (端口: ${PORT:-443})..."
echo "=========================================="

# 创建符合 AgentUniverse 路径要求的目录结构
# AgentUniverse 需要 parents[1] 存在，所以需要在子目录中运行
mkdir -p /workspace/soundtech
cd /workspace/soundtech

# 创建软链接到实际应用目录
ln -sf /app/app.py .
ln -sf /app/config .
ln -sf /app/handlers .
ln -sf /app/agentic .
ln -sf /app/templates .
ln -sf /app/resources .
ln -sf /app/static .
ln -sf /app/logs .

# 启动应用
exec python app.py --host 0.0.0.0 --port ${PORT:-443} --logdir /app/logs "$@"
