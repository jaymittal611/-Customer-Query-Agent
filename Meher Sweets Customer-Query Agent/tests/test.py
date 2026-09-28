import pytest
from src.masking import mask_email, mask_phone, mask_text
from src.tools import normalize_and_validate_phone, validate_email, SaveLeadInput

def test_phone_normalization():
    # Valid Indian formats
    assert normalize_and_validate_phone("+91 98765 43210") == "9876543210"
    assert normalize_and_validate_phone("09876543210") == "9876543210"
    assert normalize_and_validate_phone("98765-43210") == "9876543210"
    assert normalize_and_validate_phone("7123456789") == "7123456789"

    # Invalid cases (must raise ValueError)
    with pytest.raises(ValueError):
        normalize_and_validate_phone("1234567890")  # starts with 1
    with pytest.raises(ValueError):
        normalize_and_validate_phone("98765")       # too short

def test_email_validation():
    assert validate_email("User@Example.COM") == "user@example.com"
    with pytest.raises(ValueError):
        validate_email("invalid-email-string")

def test_save_lead_requires_at_least_one_contact():
    with pytest.raises(ValueError, match="At least one contact method"):
        SaveLeadInput(name="Rahul", need="10 kg Laddoos").clean_and_validate()

def test_masking():
    assert mask_email("rahul@example.com") == "r*****@example.com"
    assert mask_phone("9876543210") == "******3210"
    
    log_line = "User 9876543210 ordered sweets. Email: rahul@example.com"
    sanitized = mask_text(log_line)
    assert "9876543210" not in sanitized
    assert "rahul@example.com" not in sanitized
    assert "******3210" in sanitized
    assert "r*****@example.com" in sanitized