import csv
import re
from pathlib import Path
from typing import Dict, Any, Set

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

class KnowledgeBase:
    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self.products: Dict[str, Dict[str, Any]] = {}
        self.sections: Dict[str, str] = {}
        self.allowed_prices: Set[int] = {60, 999, 5000}  # Baseline amounts from policies
        self._load_data()

    def _slugify(self, text: str) -> str:
        """
        Converts headings to lower case with hyphens.
        Example: 'Bulk orders' -> 'bulk-orders', 'About' -> 'about'
        """
        text = text.strip().lower()
        text = re.sub(r"[^\w\s-]", "", text)
        return re.sub(r"[\s_]+", "-", text)

    def _load_prices(self):
        csv_path = self.data_dir / "prices.csv"
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row["sku"].strip()
                price = int(row["price_inr"])
                source_id = f"prices.csv#{sku}"

                self.allowed_prices.add(price)
                self.products[source_id] = {
                    "sku": sku,
                    "item": row["item"].strip(),
                    "pack": row["pack"].strip(),
                    "price_inr": price,
                    "type": row["type"].strip(),
                    "contains": row["contains"].strip(),
                    "shelf_life_days": int(row["shelf_life_days"]),
                    "source_id": source_id
                }

    def _load_markdown(self, filename: str):
        md_path = self.data_dir / filename
        with open(md_path, mode="r", encoding="utf-8") as f:
            content = f.read()

        # Split on any heading level (# Title, ## Section, etc.)
        # Groups by the heading line and the subsequent content
        tokens = re.split(r"(^#{1,6}\s+[^\n]+)", content, flags=re.MULTILINE)
        
        current_slug = None
        for token in tokens:
            token = token.strip()
            if not token:
                continue
            if re.match(r"^#{1,6}\s+", token):
                heading_title = re.sub(r"^#{1,6}\s+", "", token).strip()
                current_slug = self._slugify(heading_title)
            elif current_slug:
                source_id = f"{filename}#{current_slug}"
                self.sections[source_id] = token

    def _load_data(self):
        self._load_prices()
        self._load_markdown("business.md")
        self._load_markdown("policies.md")

# Singleton instance
kb = KnowledgeBase()