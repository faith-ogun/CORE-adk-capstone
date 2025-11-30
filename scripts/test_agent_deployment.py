import vertexai
from vertexai import agent_engines

vertexai.init(project="gen-lang-client-0639727679", location="europe-west1")

# Get your deployed agent
agents = list(agent_engines.list())
remote_agent = agents[0]

# Test it
import asyncio

async def test():
    async for item in remote_agent.async_stream_query(
        message="Get status for patient 123",
        user_id="test"
    ):
        print(item)

asyncio.run(test())