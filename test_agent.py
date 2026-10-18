"""
test_agent.py
=============
Test the agent with real questions about the indexed codebase.
Run: python test_agent.py
"""

import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.agent.agent import ask

questions = [
    "How does backpropagation work in this codebase?",
    "What does the Value class do?",
    "How is the forward pass implemented?",
]

print("=" * 60)
print("Agentic RAG — Week 2 Agent Test")
print("=" * 60)

for question in questions:
    result = ask(question)

    print(f"\nQ: {result['question']}")
    print(f"\nSteps taken:")
    for step in result['steps']:
        if step['type'] == 'tool_call':
            print(f"  → Called {step['tool']}({step['input']})")
        else:
            print(f"  ← Got result: {step['content'][:100]}...")

    print(f"\nAnswer:\n{result['answer']}")
    print("\n" + "=" * 60)