import warnings
warnings.filterwarnings("ignore", module="jieba")
warnings.filterwarnings("ignore", module="pydantic")

import jieba
jieba.setLogLevel(jieba.logging.INFO)

from agentuniverse.agent.agent import Agent
from agentuniverse.agent.agent_manager import AgentManager
from agentuniverse.base.agentuniverse import AgentUniverse
from agentuniverse.agent.output_object import OutputObject

AgentUniverse().start(config_path='rag_agent/config/config.toml', core_mode=True)


def chat(question: str):
    instance: Agent = AgentManager().get_instance_obj('rag_agent')
    output_object: OutputObject = instance.run(input=question)

    question = f"\nYour event is :\n"
    question += output_object.get_data('input')
    print(question)

    background_info = f"\nRetrieved background is :\n"
    background_info += output_object.get_data('background').replace("\n","")
    print(background_info)

    res_info = f"\nRag chat bot execution result is :\n"
    res_info += output_object.get_data('output')
    print(res_info)


if __name__ == '__main__':
    chat("'三个代表'重要思想的核心内容")
