"""
Pytest configuration and fixtures for ARGUS tests.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def complete_prohibition_screen():
    from langchain.schema import Document
    text='Article 5 - Prohibited AI practices\n1. The following AI practices shall be prohibited: '
    text+=' '.join(f'({letter}) the placing of mock practice;' for letter in 'abcdefgh')
    text+=' 2. The use of mock safeguards.'
    return [Document(page_content=text,metadata={'section_type':'article','article_number':5,'chunk_index':0})]


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_anthropic():
    """Mock Anthropic API client."""
    with patch("anthropic.Anthropic") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"inferred_model_type": "neural_network", "inferred_output_type": "binary_classification", "inferred_affected_demographics": ["age"], "data_sensitivity": "HIGH", "model_card": "# Model Card"}')]
        mock_client.messages.create.return_value = mock_response
        
        yield mock_client


@pytest.fixture(autouse=True)
def no_real_llm_calls(monkeypatch):
    """The suite must never send paid/provider requests, even with local keys set."""
    import httpx

    def blocked(*args, **kwargs):
        raise AssertionError("External HTTP calls must be mocked in this test suite")

    monkeypatch.setattr(httpx.Client, "send", blocked)
    monkeypatch.setattr(httpx.AsyncClient, "send", blocked)


@pytest.fixture
def sample_system_payload():
    """Sample AISystemCreate payload for testing."""
    return {
        "name": "Credit Scoring System",
        "version": "1.0.0",
        "purpose": "Assess creditworthiness of loan applicants using demographic and financial data",
        "model_type": "xgboost",
        "output_type": "binary_classification",
        "owner_team": "Finance AI",
        "owner_email": "finance-ai@bank.com",
        "data_sources": ["credit_bureau_data", "transaction_history"],
        "affected_demographics": ["age", "income"],
        "jurisdictions": ["EU", "IN"],
        "prediction_endpoint": "http://api.bank.com/credit-score",
    }
