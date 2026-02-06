from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.teams import RoundRobinGroupChat
from dotenv import load_dotenv
from autogen_agentchat.base import TaskResult
import os

load_dotenv()

OPEAI_APIKEY = os.getenv("OPENAI_APIKEY")

model_client = OpenAIChatCompletionClient(model="gpt-4o", api_key= OPEAI_APIKEY)

print("Setting up Agents...")