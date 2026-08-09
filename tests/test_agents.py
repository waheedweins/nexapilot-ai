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
    assert body["task_type"] == "research_only"
    assert body["research_notes"]
    assert body["lead_score"] is None


async def test_invoke_lead_qualification(client):
    response = await client.post(
        "/v1/agents/invoke",
        headers={"X-API-Key": API_KEY},
        json={
            "task_type": "lead_qualification",
            "payload": {"company_name": "Acme Corp", "website": "https://acme.com"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["lead_score"] in {"hot", "warm", "cold"}
    assert body["ops_result"]["status"] in {"executed", "pending_human_approval"}
    assert len(body["log"]) == 3  # research -> lead -> ops
