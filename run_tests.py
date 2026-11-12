# run_tests.py
import sys
import types

# 1. Apply the LangChain 0.3.x patch BEFORE Pytest boots and discovers plugins
import langchain
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.documents import Document
from langchain_core.outputs import Generation, LLMResult

mock_schema = types.ModuleType("langchain.schema")
mock_schema.HumanMessage = HumanMessage
mock_schema.AIMessage = AIMessage
mock_schema.SystemMessage = SystemMessage
mock_schema.BaseMessage = BaseMessage
mock_schema.Document = Document
mock_schema.Generation = Generation
mock_schema.LLMResult = LLMResult

# Bind the mock module into Python's memory
sys.modules["langchain.schema"] = mock_schema
langchain.schema = mock_schema

# 2. Launch Pytest programmatically
import pytest
sys.exit(pytest.main(["-v"]))
