import rich
import uuid
import argparse
from agentuniverse.agent.agent import Agent
from agentuniverse.agent.agent_manager import AgentManager
from agentuniverse.base.agentuniverse import AgentUniverse

AgentUniverse().start(config_path='config/config.toml', core_mode=True)


def chat(question: str, session_id: str = str(uuid.uuid4())):
    agent: Agent = AgentManager().get_instance_obj('group_agent')
    agent_task = agent.run(input=question, session_id=session_id)
    # rich.inspect(agent_task, methods=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-q', "--question", type=str, default="如何解决数据库中的主从复制延迟问题")
    parser.add_argument('-s', "--session_id", type=str, default=str(uuid.uuid4()))
    args = parser.parse_args()
    chat(args.question, args.session_id)