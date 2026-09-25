import json
from pathlib import Path

import pytest

from src.data.normalizer import normalize

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def envelope():
    return json.loads((FIXTURES / "3702_202608_source.json").read_text("utf-8"))


@pytest.fixture
def real_rows(envelope):
    return normalize("3702", envelope)
