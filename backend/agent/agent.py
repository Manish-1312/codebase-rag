"""
backend/agent/agent.py
=======================
The LangGraph ReAct agent — the brain of the project.

What is ReAct?
ReAct = Reason + Act
The agent thinks step by step:
  1. THOUGHT  — what do I need to find out?
  2. ACTION   — which tool should I use?
  3. OBSERVATION — what did the tool return?
  4. THOUGHT  — is this enough to answer?
  5. Repeat until confident
  6. FINAL ANSWER — cited, grounded response

What is LangGraph?
LangGraph lets us define this loop as a graph.
Each node in the graph is a step.
Edges connect the steps and define the flow.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from backend.agent.tools import search_code, get_file_code


# ── System prompt — tells the agent how to behave ────────────
SYSTEM_PROMPT = """You are an expert code assistant that answers questions 
about a software codebase.

You have access to two tools:
- search_code: search for relevant code by meaning
- get_file_code: get all code from a specific file

How to answer:
1. ALWAYS use search_code first to find relevant chunks
2. If you need more context, use get_file_code
3. Base your answer ONLY on what the tools return
4. ALWAYS cite the file name and line numbers
5. If you can't find the answer, say so clearly

Format your final answer like this:
- Plain English explanation
- File: filename.py, Lines: X-Y
- Relevant code snippet if helpful

Never make up code that wasn't in the search results."""


def create_agent():
    """
    Create and return the ReAct agent.
    
    We use gpt-4o because it's best at:
    - Deciding when to use tools
    - Reasoning about code
    - Producing cited answers
    """
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0,  # 0 = deterministic, no creativity
                        # We want facts, not creativity
    )

    tools = [search_code, get_file_code]

    agent = create_react_agent(
        model=llm,
        tools=tools,
    )

    return agent


def ask(question: str) -> dict:
    """
    Ask the agent a question about the codebase.
    
    Returns a dict with:
    - answer   : the final text answer
    - steps    : what the agent did (tool calls + observations)
    - question : the original question
    """
    agent = create_agent()

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=question),
    ]

    print(f"\n[agent] Question: {question}")
    print("[agent] Thinking...\n")

    result = agent.invoke({"messages": messages})

    # Extract the final answer — it's the last message
    final_answer = result["messages"][-1].content

    # Extract the steps the agent took
    steps = []
    for msg in result["messages"]:
        msg_type = type(msg).__name__
        if msg_type == "AIMessage" and msg.tool_calls:
            for tc in msg.tool_calls:
                steps.append({
                    "type": "tool_call",
                    "tool": tc["name"],
                    "input": tc["args"],
                })
        elif msg_type == "ToolMessage":
            steps.append({
                "type": "tool_result",
                "content": msg.content[:300],  # truncate for readability
            })

    return {
        "question": question,
        "answer":   final_answer,
        "steps":    steps,
    }