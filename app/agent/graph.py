from app.agent.state import AgentState
from langgraph.prebuilt import ToolNode
from langgraph.graph import END, START, StateGraph
from langchain_core.messages import SystemMessage
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.llm import get_llm

from app.agent.tools import ALL_TOOLS, RISKY_TOOLS, SAFE_TOOLS

from typing import Literal
import os

from langgraph.checkpoint.postgres import PostgresSaver
from psycopg import Connection
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()


def agent_node(state: AgentState) -> dict:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]

    llm = get_llm()
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    response = llm_with_tools.invoke(messages)

    return {"messages": [response]}


safe_tools_node = ToolNode(SAFE_TOOLS)
risky_tools_node = ToolNode(RISKY_TOOLS)


def route_after_agent_node(
    state: AgentState,
) -> Literal["safe_tools", "risky_tools", "__end__"]:

    last_message = state["messages"][-1]

    if not getattr(last_message, "tool_calls", None):
        return END
    requested_tools = {tc["name"] for tc in last_message.tool_calls}
    risky_tools_names = {t.name for t in RISKY_TOOLS}

    if requested_tools & risky_tools_names:
        return "risky_tools"
    return "safe_tools"


builder = StateGraph(AgentState)

builder.add_node("agent", agent_node)
builder.add_node("safe_tools", safe_tools_node)
builder.add_node("risky_tools", risky_tools_node)

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", route_after_agent_node)
builder.add_edge("safe_tools", "agent")
builder.add_edge("risky_tools", "agent")

raw_db_url = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/helpdesk_db",
).replace("postgresql+psycopg://", "postgresql://")

conn = Connection.connect(raw_db_url, autocommit=True, row_factory=dict_row)
checkpointer = PostgresSaver(conn)
checkpointer.setup()

it_agent_graph = builder.compile(
    checkpointer=checkpointer,
    interrupt_before=["risky_tools"],
)
