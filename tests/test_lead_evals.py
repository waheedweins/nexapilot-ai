"""tests/test_lead_evals.py — Automated AI Evaluation Harness using DeepEval & LangChain"""

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from deepeval.metrics import HallucinationMetric, AnswerRelevancyMetric
from app.agents.lead_agent import _score_with_llm


@pytest.mark.asyncio
async def test_lead_agent_scoring_faithfulness():
    """EVAL: Ensures the lead agent's reasoning is faithful to research notes and avoids hallucination."""
    
    # 1. Mock inputs & grounded research notes
    payload = {"company_name": "SolarTech Pakistan", "website": "https://solartecha.example.com"}
    research_notes = [
        {
            "external_apollo_firmographics": {
                "company_name": "SolarTech Pakistan",
                "estimated_employees": 150,
                "industry": "Renewable Energy"
            }
        }
    ]

    # 2. Execute agent scoring logic
    score, reasoning = await _score_with_llm(payload, research_notes)

    # 3. Define DeepEval test case
    test_case = LLMTestCase(
        input=f"Qualify lead: {payload['company_name']}",
        actual_output=reasoning,
        retrieval_context=[str(research_notes)]
    )

    # 4. Assert metrics using DeepEval
    hallucination_metric = HallucinationMetric(threshold=0.5)
    relevancy_metric = AnswerRelevancyMetric(threshold=0.7)

    assert_test(test_case, [hallucination_metric, relevancy_metric])
