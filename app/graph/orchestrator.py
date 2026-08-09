"""LangGraph StateGraph wiring the Research / Lead / Ops agents.

Routing is driven by `task_type` in the incoming state:

  research_only          -> research_agent -> END
  lead_qualification      -> research_agent -> lead_agent -> ops_agent -> END
  operations               -> ops_agent -> END

The graph is compiled once at import time and reused across requests.
"""

from langgraph.graph import END, StateGraph

from app.agents import lead_agent, ops_agent, research_agent
from app.agents.base import GraphState


def _route_from_start(state: GraphState) -> str:
    task_type = state.get("task_type", "lead_qualification")
    if task_type == "research_only":
        return research_agent.name
    if task_type == "operations":
        return ops_agent.name
    return research_agent.name  # default: full lead_qualification pipeline


def _route_after_research(state: GraphState) -> str:
    if state.get("task_type") == "research_only":
        return END
    return lead_agent.name


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node(research_agent.name, research_agent.run)
    graph.add_node(lead_agent.name, lead_agent.run)
    graph.add_node(ops_agent.name, ops_agent.run)

    graph.set_conditional_entry_point(
        _route_from_start,
        {
            research_agent.name: research_agent.name,
            ops_agent.name: ops_agent.name,
        },
    )

    graph.add_conditional_edges(
        research_agent.name,
        _route_after_research,
        {lead_agent.name: lead_agent.name, END: END},
    )
    graph.add_edge(lead_agent.name, ops_agent.name)
    graph.add_edge(ops_agent.name, END)

    return graph.compile()


# Compiled once, reused across requests (LangGraph graphs are stateless/thread-safe
# aside from the state dict passed in on each invocation).
orchestrator = build_graph()


async def run_orchestrator(initial_state: GraphState) -> GraphState:
    result = await orchestrator.ainvoke(initial_state)
    return result
