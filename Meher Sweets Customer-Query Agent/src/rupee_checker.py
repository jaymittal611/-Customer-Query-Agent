import re
from typing import List, Set, Tuple

def normalize_number_string(text: str) -> str:
    """
    Strips thousands separators from numbers, including Indian numbering
    e.g., '1,00,000' -> '100000' and '3,850' -> '3850'.
    """
    # Replace commas surrounded by digits
    return re.sub(r"(?<=\d),(?=\d)", "", text)

def extract_rupee_amounts(text: str) -> List[int]:
    """
    Extracts all integer rupee amounts based on Dhanur G2 specification:
    A number after ₹, Rs, Rs. or INR, or before 'rupees' / 'rupee'.
    """
    cleaned_text = normalize_number_string(text)
    extracted: List[int] = []

    # Pattern 1: numbers immediately following currency symbols/words
    # Matches: ₹500, Rs 1200, Rs. 480, INR 1680
    after_symbol_pattern = r"(?:₹|Rs\.?|INR)\s*(\d+)"
    for match in re.finditer(after_symbol_pattern, cleaned_text, flags=re.IGNORECASE):
        extracted.append(int(match.group(1)))

    # Pattern 2: numbers immediately before 'rupee' or 'rupees'
    # Matches: 500 rupees, 1200 rupee
    before_word_pattern = r"(\d+)\s*(?:rupees?|रुपये|रुपए)"
    for match in re.finditer(before_word_pattern, cleaned_text, flags=re.IGNORECASE):
        extracted.append(int(match.group(1)))

    return extracted

def verify_g2_rupee_compliance(
    text: str,
    base_allowed: Set[int],
    case_allowed: List[int] = None
) -> Tuple[bool, List[int], Set[int]]:
    """
    Verifies that every rupee amount in the reply belongs to allowed amounts.
    Returns: (is_compliant, extracted_amounts, unallowed_amounts)
    """
    allowed_pool = set(base_allowed)
    if case_allowed:
        allowed_pool.update(case_allowed)

    extracted = extract_rupee_amounts(text)
    disallowed = [amt for amt in extracted if amt not in allowed_pool]
    return (len(disallowed) == 0, extracted, set(disallowed))