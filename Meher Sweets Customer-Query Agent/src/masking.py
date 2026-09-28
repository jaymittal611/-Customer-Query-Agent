import re

def mask_email(email: str) -> str:
    """Masks an email like rahul@example.com -> r*****@example.com"""
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 1:
        masked_local = "*" * len(local)
    else:
        masked_local = local[0] + ("*" * 5)
    return f"{masked_local}@{domain}"

def mask_phone(phone: str) -> str:
    """Masks a 10-digit phone number like 9876543210 -> ******3210"""
    digits = re.sub(r"\D", "", phone)
    if len(digits) >= 10:
        last4 = digits[-4:]
        return f"******{last4}"
    return "******" + digits[-2:] if len(digits) > 2 else "******"

def mask_text(text: str) -> str:
    """Sanitizes text for safe logging by masking emails and phone numbers."""
    # Mask email patterns
    text = re.sub(
        r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
        lambda m: mask_email(m.group(0)),
        text
    )
    # Mask Indian mobile numbers (10 digits, optional +91 or leading 0)
    text = re.sub(
        r"(?:\+91[\s-]?)?[0]?[6-9]\d{9}",
        lambda m: mask_phone(m.group(0)),
        text
    )
    return text