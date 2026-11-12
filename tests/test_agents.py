from app.graph.orchestrator import run_orchestrator

API_KEY = "test-api-key"


async def test_invoke_requires_api_key(client):
    response = await client.post("/v1/agents/invoke", json={"task_type": "research_only"})
    assert response.status_code == 401


async def test_invoke_research_only(client):
    response = await client.post(
        "/v1/agents/invoke",
        headers={"X-API-Key": API_KEY},
        json={"task_type": "research_only", "payload": {"topic": "acme corp"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "enqueued"
    assert body["job_id"]
    assert body["session_id"]

    session_res = await client.get(
        f"/v1/agents/sessions/{body['session_id']}",
        headers={"X-API-Key": API_KEY},
    )
    assert session_res.status_code == 200
    assert session_res.json()["task_type"] == "research_only"


async def test_invoke_lead_qualification(client):
    payload = {"company_name": "Acme Corp", "website": "https://acme.com"}
    response = await client.post(
        "/v1/agents/invoke",
        headers={"X-API-Key": API_KEY},
        json={
            "task_type": "lead_qualification",
            "payload": payload,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "enqueued"
    assert body["session_id"]

    # Also verify the full 3-agent LangGraph pipeline end-to-end
    result = await run_orchestrator(
        {"task_type": "lead_qualification", "payload": payload, "log": []}
    )
    assert result["lead_score"] in {"hot", "warm", "cold"}
    assert result["ops_result"]["status"] in {"executed", "pending_human_approval"}
    assert len(result["log"]) == 3  # research -> lead -> ops
