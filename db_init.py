import warnings
warnings.filterwarnings("ignore", module="jieba")
warnings.filterwarnings("ignore", module="pydantic")

import jieba
jieba.setLogLevel(jieba.logging.INFO)

from agentuniverse.base.agentuniverse import AgentUniverse
from agentuniverse.agent.action.knowledge.knowledge_manager import KnowledgeManager


if __name__ == '__main__':
    AgentUniverse().start(config_path='./config/config.toml', core_mode=True)
    maoist_store_list = ["maoist_chroma_store", "maoist_sqlite_store"]
    maoist_knowledge = KnowledgeManager().get_instance_obj("maoist_knowledge")
    maoist_knowledge.insert_knowledge(
        source_path="./resources/毛泽东思想与中国特色社会主义理论体系概论.pdf",
        stores=maoist_store_list
    )
