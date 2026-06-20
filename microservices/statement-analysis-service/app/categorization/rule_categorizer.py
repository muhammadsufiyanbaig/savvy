"""Rule-based transaction categoriser — always available, no external deps."""

import re
from typing import Dict, List, Optional, Tuple

# (pattern, category, subcategory, tags)
_RULES: List[Tuple[re.Pattern, str, str, List[str]]] = [
    # ── Food & Dining ─────────────────────────────────────────────────────────
    (re.compile(r"starbucks|coffee|cafe|espresso|dunkin", re.I), "Food & Dining", "Coffee Shops", ["coffee", "food"]),
    (re.compile(r"mcdonald|burger king|wendy|kfc|popeyes|chick.fil|taco bell|subway|chipotle|pizza|domino|papa john", re.I), "Food & Dining", "Fast Food", ["food", "fast food"]),
    (re.compile(r"restaurant|dining|dine|grubhub|doordash|ubereats|postmates|seamless|instacart", re.I), "Food & Dining", "Restaurants", ["food", "dining"]),
    (re.compile(r"grocery|supermarket|walmart|target|costco|whole foods|trader joe|kroger|safeway|publix|aldi|food lion", re.I), "Food & Dining", "Groceries", ["groceries", "food"]),

    # ── Transportation ────────────────────────────────────────────────────────
    (re.compile(r"uber|lyft|taxi|cab|ride", re.I), "Transportation", "Ride Sharing", ["transportation", "ride"]),
    (re.compile(r"shell|exxon|bp |chevron|mobil|valero|citgo|gas station|fuel|petro", re.I), "Transportation", "Gas & Fuel", ["gas", "fuel"]),
    (re.compile(r"parking|park meter|parkway", re.I), "Transportation", "Parking", ["parking"]),
    (re.compile(r"mta|metro|subway|bus pass|transit|amtrak|greyhound", re.I), "Transportation", "Public Transit", ["transit"]),
    (re.compile(r"airline|delta|united|american air|southwest|jetblue|spirit air|frontier", re.I), "Travel", "Flights", ["travel", "flight"]),

    # ── Shopping ──────────────────────────────────────────────────────────────
    (re.compile(r"amazon|ebay|etsy|shopify|aliexpress|wish\.com", re.I), "Shopping", "Online Shopping", ["shopping", "online"]),
    (re.compile(r"nike|adidas|\bgap\b|h&m|zara|forever 21|old navy|nordstrom|\bmacy\b|bloomingdale", re.I), "Shopping", "Clothing", ["shopping", "clothing"]),
    (re.compile(r"best buy|apple store|microsoft|newegg|b&h photo|tech|electronics", re.I), "Shopping", "Electronics", ["shopping", "electronics"]),

    # ── Entertainment ─────────────────────────────────────────────────────────
    (re.compile(r"netflix|spotify|hulu|disney\+|hbo|amazon prime|apple tv|paramount|peacock", re.I), "Entertainment", "Streaming", ["entertainment", "streaming"]),
    (re.compile(r"cinema|movie|amc|regal|theater|theatre", re.I), "Entertainment", "Movies", ["entertainment", "movies"]),
    (re.compile(r"steam|playstation|xbox|nintendo|gaming|twitch", re.I), "Entertainment", "Gaming", ["entertainment", "gaming"]),

    # ── Bills & Utilities ─────────────────────────────────────────────────────
    (re.compile(r"electric|electricity|pge|con ed|duke energy|dominion energy", re.I), "Bills & Utilities", "Electricity", ["utilities", "electricity"]),
    (re.compile(r"water bill|water utility|sewage", re.I), "Bills & Utilities", "Water", ["utilities", "water"]),
    (re.compile(r"verizon|at&t|t-mobile|sprint|comcast|xfinity|spectrum|internet|phone bill|mobile plan", re.I), "Bills & Utilities", "Phone & Internet", ["utilities", "phone"]),
    (re.compile(r"rent|mortgage|lease payment|property", re.I), "Bills & Utilities", "Rent & Mortgage", ["housing", "rent"]),
    (re.compile(r"insurance|geico|progressive|state farm|allstate|usaa|liberty mutual", re.I), "Bills & Utilities", "Insurance", ["insurance"]),

    # ── Healthcare ────────────────────────────────────────────────────────────
    (re.compile(r"pharmacy|cvs|walgreens|rite aid|drug store|medicine|prescription", re.I), "Healthcare", "Pharmacy", ["health", "pharmacy"]),
    (re.compile(r"doctor|hospital|clinic|medical|dental|optometrist|urgent care|health care", re.I), "Healthcare", "Medical", ["health", "medical"]),
    (re.compile(r"gym|fitness|planet fitness|la fitness|24 hour fitness|crossfit|yoga|workout", re.I), "Personal Care", "Fitness", ["fitness", "health"]),

    # ── Travel ────────────────────────────────────────────────────────────────
    (re.compile(r"hotel|marriott|hilton|hyatt|sheraton|airbnb|vrbo|motel|inn\b|resort", re.I), "Travel", "Hotels", ["travel", "hotel"]),
    (re.compile(r"car rental|hertz|avis|enterprise|budget rent|national car", re.I), "Travel", "Car Rental", ["travel", "car"]),

    # ── Personal Care ─────────────────────────────────────────────────────────
    (re.compile(r"salon|barber|haircut|spa|nail|beauty supply", re.I), "Personal Care", "Hair & Beauty", ["personal care"]),

    # ── Education ─────────────────────────────────────────────────────────────
    (re.compile(r"tuition|university|college|coursera|udemy|skillshare|khan academy|linkedin learning", re.I), "Education", "Tuition & Courses", ["education"]),
    (re.compile(r"bookstore|amazon books|textbook|library fine", re.I), "Education", "Books", ["education", "books"]),

    # ── Income / Transfers ────────────────────────────────────────────────────
    (re.compile(r"payroll|direct deposit|salary|wage|paycheck|ach credit", re.I), "Income", "Salary", ["income"]),
    (re.compile(r"transfer|zelle|venmo|paypal|cash app|wire transfer", re.I), "Transfer", "P2P Transfer", ["transfer"]),
    (re.compile(r"refund|return credit|chargeback|reversal", re.I), "Income", "Refund", ["refund"]),
    (re.compile(r"interest earned|dividend|investment return", re.I), "Income", "Investment", ["investment", "income"]),
]

_DEFAULT = ("Other", "Uncategorised", [])


def categorise(description: str, amount: float = 0.0, category_hint: Optional[str] = None) -> Dict:
    """Return categorisation dict with category, subcategory, confidence, tags."""
    desc = (description or "").strip()

    for pattern, category, subcategory, tags in _RULES:
        if pattern.search(desc):
            return {
                "category": category,
                "subcategory": subcategory,
                "confidence_score": 0.75,
                "tags": tags,
                "categorization_method": "rule",
            }

    # Use AI hint if available
    if category_hint:
        return {
            "category": category_hint,
            "subcategory": None,
            "confidence_score": 0.55,
            "tags": [],
            "categorization_method": "ai_hint",
        }

    return {
        "category": _DEFAULT[0],
        "subcategory": _DEFAULT[1],
        "confidence_score": 0.3,
        "tags": _DEFAULT[2],
        "categorization_method": "rule",
    }
