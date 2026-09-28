import pytest
from src.data_loader import kb
from src.retriever import retrieve_grounded_context

def test_prices_loaded():
    """Verify all 14 SKUs and policy amounts are indexed."""
    assert len(kb.products) == 14
    assert "prices.csv#KK-1000" in kb.products
    assert kb.products["prices.csv#KK-1000"]["price_inr"] == 1200
    assert {60, 999, 5000}.issubset(kb.allowed_prices)

def test_markdown_section_slugs():
    """Verify section IDs conform to policies.md#<section> format."""
    expected_slugs = [
        "business.md#about",
        "business.md#address",
        "business.md#opening-hours",
        "policies.md#delivery",
        "policies.md#bulk-orders",
        "policies.md#diwali-2026-gift-boxes-and-discounts"
    ]
    for slug in expected_slugs:
        assert slug in kb.sections, f"Missing expected slug: {slug}"

def test_retriever_outputs_valid_ids():
    """Verify retrieval returns expected source IDs."""
    _, sources = retrieve_grounded_context("What is the cost of Motichoor Laddoo?")
    assert "prices.csv#ML-1000" in sources

    _, sources = retrieve_grounded_context("Do you deliver and how much does it cost?")
    assert "policies.md#delivery" in sources