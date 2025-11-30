# Delete the deployed agent in Vertex AI to save resources

import vertexai
from vertexai import agent_engines

vertexai.init(project="gen-lang-client-0639727679", location="europe-west1")

# Find it
agents_list = list(agent_engines.list())
if agents_list:
    remote_agent = agents_list[0]
    print(f"Deleting: {remote_agent.resource_name}")
    agent_engines.delete(resource_name=remote_agent.resource_name, force=True)
    print("✅ Deleted")
else:
    print("No agents found")