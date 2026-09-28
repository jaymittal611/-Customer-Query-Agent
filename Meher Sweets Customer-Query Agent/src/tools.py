import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

# Global in-memory storage for saved leads
SAVED_LEADS: List[Dict[str, Any]] = []

def normalize_and_validate_phone(phone_str: str) -> str:
    """
    Normalizes Indian mobile number to 10 digits starting with 6-9.
    Accepts +91, leading 0, spaces, dashes.
    """
    clean = re.sub(r"[\s-]", "", phone_str)
    if clean.startswith("+91"):
        clean = clean[3:]
    elif clean.startswith("0"):
        clean = clean[1:]
    
    if len(clean) != 10 or not clean.isdigit() or clean[0] not in "6789":
        raise ValueError(
            f"Invalid Indian mobile number: '{phone_str}'. Must be a 10-digit number starting with 6, 7, 8, or 9."
        )
    return clean

def validate_email(email_str: str) -> str:
    """Lowercases and checks for a valid email structure."""
    clean = email_str.strip().lower()
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(email_regex, clean):
        raise ValueError(f"Invalid email address: '{email_str}'.")
    return clean

class SaveLeadInput(BaseModel):
    name: str = Field(..., min_length=1)
    need: str = Field(..., min_length=1)
    phone: Optional[str] = None
    email: Optional[str] = None
    quantity: Optional[str] = None
    date: Optional[str] = None

    def clean_and_validate(self) -> Dict[str, Any]:
        if not self.phone and not self.email:
            raise ValueError("At least one contact method (phone or email) is required.")

        normalized_phone = normalize_and_validate_phone(self.phone) if self.phone else None
        normalized_email = validate_email(self.email) if self.email else None

        if self.date:
            try:
                datetime.strptime(self.date.strip(), "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Invalid date format: '{self.date}'. Must be YYYY-MM-DD.")

        return {
            "name": self.name.strip(),
            "need": self.need.strip(),
            "phone": normalized_phone,
            "email": normalized_email,
            "quantity": self.quantity.strip() if self.quantity else None,
            "date": self.date.strip() if self.date else None,
        }
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "save_lead",
            "description": "Record customer order inquiry when contact info is provided.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Customer name"},
                    "phone": {"type": "string", "description": "Phone number"},
                    "email": {"type": "string", "description": "Email address"},
                    "need": {"type": "string", "description": "Inquiry summary"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "escalate",
            "description": "Escalate complaints, damaged orders, or human manager requests.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Reason for escalation"}
                },
                "required": ["reason"]
            }
        }
    }
]

def execute_save_lead(args: Dict[str, Any]) -> Dict[str, Any]:
    validated = SaveLeadInput(**args).clean_and_validate()
    SAVED_LEADS.append(validated)
    return {"status": "success", "lead": validated}

def execute_escalate(args: Dict[str, Any]) -> Dict[str, Any]:
    reason = args.get("reason", "").strip()
    if not reason:
        raise ValueError("A reason is required to escalate.")
    return {"status": "success", "escalated": True, "reason": reason}