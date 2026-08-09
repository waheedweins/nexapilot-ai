from app.agents import lead_agent, ops_agent, research_agent


async def test_research_agent_stub_result():
    state = {"payload": {"topic": "test query"}, "log": []}
    result = await research_agent.run(state)
    assert len(result["research_notes"]) == 1
    assert "test query" in result["log"][0]


async def test_lead_agent_warm_with_website_and_notes():
    state = {
        "payload": {"website": "https://acme.com"},
        "research_notes": [{"url": "https://acme.com/about"}],
        "log": [],
    }
    result = await lead_agent.run(state)
    assert result["lead_score"] == "warm"


async def test_lead_agent_cold_without_website():
    state = {"payload": {}, "research_notes": [], "log": []}
    result = await lead_agent.run(state)
    assert result["lead_score"] == "cold"


async def test_ops_agent_safe_action_executes():
    state = {"payload": {"action": "log_lead"}, "log": []}
    result = await ops_agent.run(state)
    assert result["ops_result"]["status"] == "executed"


async def test_ops_agent_unsafe_action_requires_approval():
    state = {"payload": {"action": "send_wire_transfer"}, "log": []}
    result = await ops_agent.run(state)
    assert result["ops_result"]["status"] == "pending_human_approval"
