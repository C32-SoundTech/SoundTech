import json
import dashscope

from agentuniverse.agent.action.tool.tool import Tool

class CalculatorTool(Tool):

    def execute(self, input: str):
        if __name__ == '__main__':
            from rich.console import Console
            console = Console()
            console.log(f"[bold green]使用计算器工具:[/bold green]\n{input}")

        code_interpreter = dashscope.Assistants.create(
            model='qwen-turbo',
            name='calculator-tool',
            description='该工具可以用来计算输入的文本表达式并给出答案，可以用中文或者数字。',
            instructions='该工具可以用来计算输入的文本表达式并给出答案，可以用中文或者数字。',
            tools=[
                {'type': 'calculator', 'description': '该工具可以用来计算输入的文本表达式并给出答案，可以用中文或者数字。'},
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
                    if call['type'] == 'calculator':
                        result = json.loads(call['calculator']['output'])
                        output += f"由'{input}'转换成的数学表达式为:'{result['equations'][0]}'\n"
                        output += f"数学表达式的结果为:'{result['results'][0]}'\n"

        return output

if __name__ == "__main__":
    code = CalculatorTool()
    code.execute("10加20")
