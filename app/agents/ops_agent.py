"""Operations Agent — takes safe automated actions, defers risky ones.

Any action not on the `SAFE_ACTIONS` allowlist is marked as requiring human
approval rather than executed, per the Phase 6 human-in-the-loop design.
"""

from app.agents.base import GraphState, log_step

name = "ops_agent"

SAFE_ACTIONS = {"log_lead", "notify_slack_summary"}


async def run(state: GraphState) -> GraphState:
    payload = state.get("payload", {})
    requested_action = payload.get("action", "log_lead")

    if requested_action in SAFE_ACTIONS:
        result = {"action": requested_action, "status": "executed"}
        message = f"{name}: executed safe action '{requested_action}'"
    else:
        result = {"action": requested_action, "status": "pending_human_approval"}
        message = f"{name}: '{requested_action}' requires human approval, not executed"

    return {
        "ops_result": result,
        "log": log_step(state, message),
    }
