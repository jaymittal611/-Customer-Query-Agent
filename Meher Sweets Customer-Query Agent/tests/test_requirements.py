import pytest
from src.retriever import retrieve_grounded_context
from src.tools import (
    normalize_and_validate_phone,
    validate_email,
    SaveLeadInput,
    execute_save_lead
)
from src.masking import mask_email, mask_phone, mask_text
from src.rupee_checker import extract_rupee_amounts, normalize_number_string

# -------------------------------------------------------------
# 1. Retrieval & Source IDs
# -------------------------------------------------------------
def test_retrieval_returns_valid_ids():
    context, sources = retrieve_grounded_context("How much is Kaju Katli?")
    assert any(s.startswith("prices.csv#KK-") for s in sources)

    context, sources = retrieve_grounded_context("What are your store hours and address?")
    assert "business.md#opening-hours" in sources or "business.md#address" in sources

# -------------------------------------------------------------
# 2. Lead Validation
# -------------------------------------------------------------
def test_lead_validation_rules():
    # Valid Indian formats (start with 6-9, normalized to 10 digits)
    assert normalize_and_validate_phone("+91 9811122233") == "9811122233"
    assert normalize_and_validate_phone("08811122233") == "8811122233"
    assert normalize_and_validate_phone("78111-22233") == "7811122233"

    # Invalid phone formats
    with pytest.raises(ValueError):
        normalize_and_validate_phone("5511122233")  # doesn't start with 6-9
    with pytest.raises(ValueError):
        normalize_and_validate_phone("98111")        # short length

    # Email lowercasing
    assert validate_email("TestUser@Domain.COM") == "testuser@domain.com"
    with pytest.raises(ValueError):
        validate_email("not-an-email")

    # Requires at least one contact method
    with pytest.raises(ValueError):
        SaveLeadInput(name="Amit", need="Diwali sweets").clean_and_validate()

# -------------------------------------------------------------
# 3. Rupee Amount Extraction (G2 Specification)
# -------------------------------------------------------------
def test_rupee_amount_extraction_and_comma_stripping():
    # Number normalization including Indian numbering system
    text_with_commas = "Prices are 1,00,000 and 3,850."
    assert normalize_number_string(text_with_commas) == "Prices are 100000 and 3850."

    # Extract ₹, Rs, Rs., INR, and 'rupees'
    test_reply = (
        "Total is ₹1880. Motichoor is Rs. 560 and delivery is Rs 60. "
        "Also INR 240 for Soan Papdi, or 1200 rupees for Kaju Katli."
    )
    extracted = extract_rupee_amounts(test_reply)
    assert 1880 in extracted
    assert 560 in extracted
    assert 60 in extracted
    assert 240 in extracted
    assert 1200 in extracted

# -------------------------------------------------------------
# 4. Masking Utility
# -------------------------------------------------------------
def test_masking_rules():
    assert mask_email("rahul.sharma@example.com") == "r*****@example.com"
    assert mask_phone("+91 9876543210") == "******3210"

    raw_log = "Customer phone is 9876543210 and email is priya@domain.com"
    safe_log = mask_text(raw_log)
    assert "9876543210" not in safe_log
    assert "priya@domain.com" not in safe_log
    assert "******3210" in safe_log
    assert "p*****@domain.com" in safe_log

# -------------------------------------------------------------
# 5. Tool Call With Invalid Arguments
# -------------------------------------------------------------
def test_tool_call_invalid_arguments_handling():
    # Attempt save_lead without phone or email
    invalid_args = {"name": "Suresh", "need": "5 kg Gulab Jamun"}
    with pytest.raises(ValueError) as excinfo:
        execute_save_lead(invalid_args)
    assert "At least one contact method" in str(excinfo.value)

    # Attempt save_lead with invalid mobile number
    invalid_phone_args = {
        "name": "Suresh",
        "need": "5 kg Gulab Jamun",
        "phone": "12345"
    }
    with pytest.raises(ValueError) as excinfo:
        execute_save_lead(invalid_phone_args)
    assert "Invalid Indian mobile number" in str(excinfo.value)