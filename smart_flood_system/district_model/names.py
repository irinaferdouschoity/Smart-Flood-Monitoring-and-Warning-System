"""District-name matching shared by the label and dataset builders."""
import re

ALIASES = {  # alternative spellings -> normalised name used in bangladesh_districts.csv
    "comilla": "cumilla", "bogra": "bogura", "jessore": "jashore",
    "chittagong": "chattogram", "barisal": "barishal", "coxbazar": "coxsbazar",
    "maulvibazar": "moulvibazar", "moulavibazar": "moulvibazar", "jhalakathi": "jhalokati",
    "jhalakati": "jhalokati", "netrakona": "netrokona", "khagrachari": "khagrachhari",
    "nawabganj": "chapainawabganj", "chapainababganj": "chapainawabganj",
    "chapainawabgonj": "chapainawabganj", "hobiganj": "habiganj", "hobigonj": "habiganj",
    "sirajgonj": "sirajganj", "kishorganj": "kishoreganj", "kishoregonj": "kishoreganj",
    "narsingdi": "narsingdi", "narshingdi": "narsingdi", "munshigonj": "munshiganj",
}


def norm(name: str) -> str:
    key = re.sub(r"[^a-z]", "", str(name).lower())
    return ALIASES.get(key, key)
