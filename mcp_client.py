import os
import asyncio

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

#load_dotenv()
load_dotenv(override=True)
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
print(f"Key loaded: {str(TAVILY_API_KEY)[:5]}...") # Should print 'tvly-...'
client = MultiServerMCPClient(
    {
        "tavily": {
            "transport": "streamable_http",
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"
        }
    }
)

async def main():
    tools = await client.get_tools()

    search_tool = next(
        tool
        for tool in tools
        if tool.name == "tavily_search"
    )

    result = await search_tool.ainvoke(
        {
            "query": "Best hotels in Delhi"
        }
    )

    print(result)

asyncio.run(main()) 
