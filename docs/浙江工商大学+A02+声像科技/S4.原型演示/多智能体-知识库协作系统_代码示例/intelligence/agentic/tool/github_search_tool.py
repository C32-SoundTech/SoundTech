import json
import dashscope

from agentuniverse.agent.action.tool.tool import Tool

class GithubSearchTool(Tool):

    def execute(self, input: str):
        if __name__ == '__main__':
            from rich.console import Console
            console = Console()
            console.log(f"[bold green]使用github搜索工具:[/bold green]\n{input}")

        code_interpreter = dashscope.Assistants.create(
            model='qwen-turbo',
            name='github-search-tool',
            description='该工具可以用来进行github搜索，工具的输入是你想搜索的内容。',
            instructions='该工具可以用来进行github搜索，工具的输入是你想搜索的内容。',
            tools=[
                {'type': 'github_search', 'description': '该工具可以用来进行github搜索，工具的输入是你想搜索的内容。'},
            ]
        )
        thread = dashscope.Threads.create()

        dashscope.Messages.create(
            thread_id=thread.id,
            content=input
        )
        
        # 在线程上运行助手
        run = dashscope.Runs.create(
            thread_id=thread.id,
            assistant_id=code_interpreter.id
        )
        
        run = dashscope.Runs.wait(run.id, thread_id=thread.id)

        steps = dashscope.Steps.list(run.id, thread_id=thread.id)

        output = ""

        for step in steps.data:
            if step.step_details.type == 'tool_calls':
                for call in step.step_details.tool_calls:
                    if call['type'] == 'github_search':
                        output += json.dumps(json.loads(call['github_search']['output'])['items'])

        return output

if __name__ == "__main__":
    code = GithubSearchTool()
    code.execute("通义千问")