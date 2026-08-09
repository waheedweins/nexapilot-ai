"""Shared agent interface.

Every agent takes the current graph state (a plain dict) and returns a
partial state update, matching LangGraph's node contract. Keeping agents as
plain async functions (rather than classes with hidden state) makes them
easy to unit-test in isolation from the graph.
"""

from typing import Protocol, TypedDict


class GraphState(TypedDict, total=False):
    task_type: str
    session_id: str
    payload: dict
    research_notes: list[dict]
    lead_score: str | None
    lead_reasoning: str | None
    ops_result: dict | None
    next_agent: str | None
    log: list[str]


class Agent(Protocol):
    name: str

    async def __call__(self, state: GraphState) -> GraphState: ...


def log_step(state: GraphState, message: str) -> list[str]:
    entries = list(state.get("log", []))
    entries.append(message)
    return entries
