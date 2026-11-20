import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_llm():
    with patch(
        "app.api.chat.llm_service.generate_response",
        new_callable=AsyncMock,
        return_value="Mohit is an AI/ML engineer at SAP Labs India.",
    ) as mock:
        yield mock
