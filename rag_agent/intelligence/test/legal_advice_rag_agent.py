import jieba
import warnings
jieba.setLogLevel(jieba.logging.INFO)
warnings.filterwarnings("ignore", module="jieba")
warnings.filterwarnings("ignore", module="pydantic")

from agentuniverse.agent.output_object import OutputObject
from agentuniverse.agent.agent import Agent
from agentuniverse.agent.agent_manager import AgentManager
from agentuniverse.base.agentuniverse import AgentUniverse

AgentUniverse().start(config_path='../../config/config.toml', core_mode=True)


def chat(question: str):
    instance: Agent = AgentManager().get_instance_obj('law_rag_agent')
    output_object: OutputObject = instance.run(input=question)

    question = f"\nYour event is :\n"
    question += output_object.get_data('input')
    print(question)

    res_info = f"\nRag chat bot execution result is :\n"
    res_info += output_object.get_data('output')
    print(res_info)


if __name__ == '__main__':
    chat("张三在景区拍摄景区风景，李四闯入了镜头并被拍下。李四能否起诉张三侵犯肖像权，能否要求删除照片")
