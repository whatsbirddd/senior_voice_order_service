from .core import Agent
from .memory import Memory
from .tools import build_default_tools
from .config import default_prompt

def build_agent():
    memory = Memory()
    tools = build_default_tools()
    agent = Agent(prompt=default_prompt, tools=tools, memory=memory)
    return agent

