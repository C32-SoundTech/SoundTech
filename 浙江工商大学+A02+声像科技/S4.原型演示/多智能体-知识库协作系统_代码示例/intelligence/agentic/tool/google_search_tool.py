from typing import Optional

from pydantic import Field
from langchain_community.utilities.google_serper import GoogleSerperAPIWrapper
from agentuniverse.agent.action.tool.tool import Tool, ToolInput
from agentuniverse.base.util.env_util import get_from_env

class GoogleSearchTool(Tool):
    """The demo google search tool.

    Implement the execute method of demo google search tool, using the `GoogleSerperAPIWrapper` to implement a simple Google search.

    Note:
        You need to sign up for a free account at https://serper.dev and get the serpher api key (2500 free queries).
    """

    serper_api_key: Optional[str] = Field(default_factory=lambda: get_from_env("SERPER_API_KEY"))

    def execute(self, input: str):
        # get top10 results from Google search.
        if __name__ == "__main__":
            from rich.console import Console
            console = Console()
            console.log(f"[bold green]使用Google搜索工具:[/bold green]\n{input}")
            
        search = GoogleSerperAPIWrapper(serper_api_key=self.serper_api_key, k=10, gl="us", hl="en", type="search")
        output = search.run(query=input)
        return output