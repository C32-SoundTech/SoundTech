#!/bin/bash
# SoundTech 数据初始化脚本
# 用于首次部署时初始化向量数据库

set -e

echo "=========================================="
echo "SoundTech 声像科技 - 数据初始化"
echo "=========================================="

# 检查环境变量
if [ -z "$DASHSCOPE_API_KEY" ]; then
    echo "错误: 请设置 DASHSCOPE_API_KEY 环境变量"
    exit 1
fi

# 进入应用目录
cd /app

# 初始化向量数据库
echo "正在初始化知识库向量数据..."
python -c "
import os
os.environ.setdefault('ANONYMIZED_TELEMETRY', 'False')

from handlers.rubost import *
from agentuniverse.base.agentuniverse import AgentUniverse
from agentuniverse.agent.action.knowledge.knowledge_manager import KnowledgeManager

print('启动 AgentUniverse...')
AgentUniverse().start(config_path='./config/config.toml', core_mode=True)

print('加载知识库...')
maoist_store_list = ['maoist_chroma_store', 'maoist_sqlite_store']
maoist_knowledge = KnowledgeManager().get_instance_obj('maoist_knowledge')

print('插入知识文档...')
maoist_knowledge.insert_knowledge(
    source_path='./resources/毛泽东思想与中国特色社会主义理论体系概论.pdf',
    stores=maoist_store_list
)

print('知识库初始化完成!')
"

echo "=========================================="
echo "数据初始化完成!"
echo "=========================================="
