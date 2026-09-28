import csv
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple

class KnowledgeBase:
    def __init__(self):
        self.products: Dict[str, Dict[str, Any]] = {}
        self.sections: Dict[str, str] = {}
        self._load_data()

    def _load_data(self):
        data_dir = Path("data")
        csv_path = data_dir / "prices.csv"
        if csv_path.exists():
            with open(csv_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    source_id = f"prices.csv#{row['sku']}"
                    self.products[source_id] = row

        for md_file in ["business.md", "policies.md"]:
            p = data_dir / md_file
            if p.exists():
                content = p.read_text(encoding="utf-8")
                parts = re.split(r"\n(?=##?\s+)", content)
                for part in parts:
                    lines = part.strip().split("\n")
                    if not lines:
                        continue
                    header = lines[0].replace("#", "").strip().lower()
                    slug = re.sub(r"[^a-z0-9]+", "-", header).strip("-")
                    source_id = f"{md_file}#{slug}"
                    self.sections[source_id] = part.strip()

kb = KnowledgeBase()

PRODUCT_ALIASES = {
    "kaju katli": ["prices.csv#KK-1000", "prices.csv#KK-500"],
    "काजू कतली": ["prices.csv#KK-1000", "prices.csv#KK-500"],
    "काजू": ["prices.csv#KK-1000", "prices.csv#KK-500"],
    "sugar-free": ["prices.csv#SF-500"],
    "sugar free": ["prices.csv#SF-500"],
    "शुगर": ["prices.csv#SF-500"],
    "motichoor": ["prices.csv#ML-1000"],
    "मोतीचूर": ["prices.csv#ML-1000"],
    "laddoo": ["prices.csv#ML-1000", "prices.csv#BL-1000"],
    "लड्डू": ["prices.csv#ML-1000", "prices.csv#BL-1000"],
    "besan": ["prices.csv#BL-1000"],
    "बेसन": ["prices.csv#BL-1000"],
    "gulab jamun": ["prices.csv#GJ-1000"],
    "गुलाब जामुन": ["prices.csv#GJ-1000"],
    "rasmalai": ["prices.csv#RM-500"],
    "रसमलाई": ["prices.csv#RM-500"],
    "samosa": ["prices.csv#SAM-01"],
    "समोसा": ["prices.csv#SAM-01"],
    "समोसे": ["prices.csv#SAM-01"],
    "dhokla": ["prices.csv#DH-500"],
    "ढोकला": ["prices.csv#DH-500"],
    "khaman": ["prices.csv#DH-500"],
    "soan papdi": ["prices.csv#SP-500"],
    "सोन पापड़ी": ["prices.csv#SP-500"],
    "large gift box": ["prices.csv#GB-L"],
    "large diwali": ["prices.csv#GB-L"],
    "small gift box": ["prices.csv#GB-S"],
    "gift box": ["prices.csv#GB-S", "prices.csv#GB-L"],
    "गिफ्ट": ["prices.csv#GB-S", "prices.csv#GB-L"],
    "दिवाली": ["prices.csv#GB-S", "prices.csv#GB-L"],
    "namkeen": ["prices.csv#MN-400"],
    "नमकीन": ["prices.csv#MN-400"],
    "bhujia": ["prices.csv#AB-400"],
    "भुजिया": ["prices.csv#AB-400"],
}

def retrieve_grounded_context(query: str, history: List[Dict[str, Any]] = None, max_chunks: int = 4) -> Tuple[str, List[str]]:
    search_text = query.lower()
    if history:
        for turn in history[-2:]:
            search_text += " " + turn.get("content", "").lower()

    matched_sources: List[str] = []
    blocks: List[str] = []

    for alias, source_ids in PRODUCT_ALIASES.items():
        if alias in search_text:
            for s_id in source_ids:
                if s_id in kb.products and s_id not in matched_sources:
                    matched_sources.append(s_id)
                    p = kb.products[s_id]
                    allergens = f" (Contains: {p['contains']})" if p.get('contains') else ""
                    blocks.append(f"[{s_id}] {p['item']} ({p['pack']}): Rs {p['price_inr']}{allergens}")

    for s_id, p in kb.products.items():
        if len(matched_sources) >= max_chunks:
            break
        if p['item'].lower() in search_text or p['sku'].lower() in search_text:
            if s_id not in matched_sources:
                matched_sources.append(s_id)
                blocks.append(f"[{s_id}] {p['item']} ({p['pack']}): Rs {p['price_inr']}")
    # Inside retrieve_grounded_context in src/retriever.py:
    for s_id in matched_sources:
        if s_id in kb.products:
            item = kb.products[s_id]
            name = item.get("item", "")
            pack = str(item.get("pack", "")).strip()
            price = int(item.get("price_inr", 0))

        if pack == "500 g":
            per_kg = price * 2
            line = (
            f"[{s_id}] {name}: Rs {price} per 500 g pack "
            f"(Unit rate: Rs {per_kg} per 1 kg. To calculate total: multiply kg requested by {per_kg})"
        )
        else:
            line = f"[{s_id}] {name} ({pack}): Rs {price}"

        blocks.append(line)

    policy_keywords = {
        "policies.md#delivery": ["deliver", "डिलीवरी", "km", "किलोमीटर", "distance", "rohini", "janakpuri", "punjabi bagh"],
        "policies.md#discounts": ["discount", "डिस्काउंट", "छूट", "offer", "pre-order", "5%"],
        "policies.md#bulk-orders": ["bulk", "wedding", "advance", "deposit", "office", "15 kg", "शादी"],
        "policies.md#returns": ["return", "refund", "damaged", "crushed", "spoiled", "insect"],
        "policies.md#hours": ["hours", "timings", "open", "close", "समय", "holi", "today", "raat", "band"],
        "business.md#location": ["location", "address", "where", "shop", "पता", "market", "दुकान"],
        "policies.md#payment": ["cod", "cash", "payment"]
    }

    for section_id, keywords in policy_keywords.items():
        if len(matched_sources) >= max_chunks:
            break
        if any(k in search_text for k in keywords):
            for s_id, text in kb.sections.items():
                if section_id.split("#")[1] in s_id and s_id not in matched_sources:
                    matched_sources.append(s_id)
                    blocks.append(f"[{s_id}]\n{text}")
                    break

    if not matched_sources:
        for s_id, text in kb.sections.items():
            if "about" in s_id:
                matched_sources.append(s_id)
                blocks.append(f"[{s_id}]\n{text}")
                break

    return "\n\n".join(blocks[:max_chunks]), matched_sources[:max_chunks]