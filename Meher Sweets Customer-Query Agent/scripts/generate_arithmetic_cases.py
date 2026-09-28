# scripts/generate_arithmetic_cases.py
import json
from pathlib import Path

# Prices according to prices.csv and delivery policy in policies.md
CATALOG = {
    "motichoor_1kg": 560,
    "kaju_katli_1kg": 1200,
    "kaju_katli_500g": 620,
    "sugar_free_kk_500g": 780,
    "besan_laddoo_1kg": 520,
    "soan_papdi_500g": 240,
    "gulab_jamun_1kg": 480,
    "rasmalai_500g": 340,
    "mixed_namkeen_400g": 180,
    "aloo_bhujia_400g": 150,
    "samosa_piece": 20,
    "dhokla_500g": 160,
    "gift_box_small": 650,
    "gift_box_large": 1450,
}

def calc_delivery(subtotal: int) -> int:
    """Free on >= 999, else 60."""
    return 0 if subtotal >= 999 else 60

def generate_arithmetic_test_cases():
    cases = []

    # Case 1: 2 kg Besan Laddoo + delivery
    subtotal_1 = 2 * CATALOG["besan_laddoo_1kg"]
    del_1 = calc_delivery(subtotal_1)
    tot_1 = subtotal_1 + del_1
    cases.append({
        "id": "arith-gen-01",
        "category": "arithmetic",
        "turns": ["I want 2 kg Besan Laddoo delivered to Rajouri Garden 3 km away. What is the total?"],
        "must_include": [str(tot_1)],
        "allowed_amounts": [subtotal_1, tot_1, del_1] if del_1 > 0 else [subtotal_1, tot_1]
    })

    # Case 2: 5 Samosas + 1 kg Gulab Jamun (subtotal < 999, so delivery 60 applies)
    samosa_cost = 5 * CATALOG["samosa_piece"]
    gj_cost = 1 * CATALOG["gulab_jamun_1kg"]
    subtotal_2 = samosa_cost + gj_cost
    del_2 = calc_delivery(subtotal_2)
    tot_2 = subtotal_2 + del_2
    cases.append({
        "id": "arith-gen-02",
        "category": "arithmetic",
        "turns": ["I want 5 samosas and 1 kg Gulab Jamun delivered 4 km away. Can you give me the total bill?"],
        "must_include": [str(tot_2)],
        "allowed_amounts": [samosa_cost, gj_cost, subtotal_2, del_2, tot_2]
    })

    # Case 3: 2 boxes of Diwali Gift Box Small
    subtotal_3 = 2 * CATALOG["gift_box_small"]
    del_3 = calc_delivery(subtotal_3)
    tot_3 = subtotal_3 + del_3
    cases.append({
        "id": "arith-gen-03",
        "category": "arithmetic",
        "turns": ["How much for 2 small Diwali gift boxes with delivery to Punjabi Bagh?"],
        "must_include": [str(tot_3)],
        "allowed_amounts": [subtotal_3, tot_3]
    })

    # Case 4: 1 kg Kaju Katli + 2 packs Aloo Bhujia
    kk_cost = 1 * CATALOG["kaju_katli_1kg"]
    ab_cost = 2 * CATALOG["aloo_bhujia_400g"]
    subtotal_4 = kk_cost + ab_cost
    del_4 = calc_delivery(subtotal_4)
    tot_4 = subtotal_4 + del_4
    cases.append({
        "id": "arith-gen-04",
        "category": "arithmetic",
        "turns": ["1 kg Kaju Katli and 2 packs of Aloo Bhujia delivered to my home nearby. Total cost?"],
        "must_include": [str(tot_4)],
        "allowed_amounts": [kk_cost, ab_cost, subtotal_4, tot_4]
    })

    # Case 5: 3 packs of Sugar-free Kaju Katli (500g)
    subtotal_5 = 3 * CATALOG["sugar_free_kk_500g"]
    del_5 = calc_delivery(subtotal_5)
    tot_5 = subtotal_5 + del_5
    cases.append({
        "id": "arith-gen-05",
        "category": "arithmetic",
        "turns": ["What would be the total bill for 3 packs of sugar-free kaju katli?"],
        "must_include": [str(tot_5)],
        "allowed_amounts": [subtotal_5, tot_5]
    })

    # Case 6: Multi-turn arithmetic adjustment
    subtotal_6_initial = CATALOG["motichoor_1kg"]
    samosa_10 = 10 * CATALOG["samosa_piece"]
    subtotal_6_final = (3 * CATALOG["motichoor_1kg"]) + samosa_10
    del_6 = calc_delivery(subtotal_6_final)
    tot_6 = subtotal_6_final + del_6
    cases.append({
        "id": "arith-gen-06",
        "category": "arithmetic",
        "turns": [
            "What is the price of 1 kg motichoor laddoo?",
            "Make it 3 kg, and add 10 samosas. Deliver to 2 km away. Total?"
        ],
        "must_include": [str(tot_6)],
        "allowed_amounts": [subtotal_6_initial, 3 * CATALOG["motichoor_1kg"], samosa_10, subtotal_6_final, tot_6]
    })

    return cases

if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent.parent / "evals"
    out_dir.mkdir(exist_ok=True)
    generated = generate_arithmetic_test_cases()
    out_file = out_dir / "generated_arithmetic.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for c in generated:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"Generated {len(generated)} verified arithmetic cases in {out_file}")