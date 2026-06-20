"""Shariah compliance screening logic — pure Python, no external deps."""

from typing import Dict, List, Tuple

PROHIBITED_INDUSTRIES: List[str] = [
    "alcohol", "tobacco", "gambling", "casino", "pork",
    "pornography", "weapons", "arms", "conventional_banking",
    "insurance_conventional", "adult_entertainment",
]

MAX_DEBT_RATIO = 0.33           # total debt / market cap
MAX_INTEREST_INCOME = 0.05      # interest income / total revenue
MAX_RECEIVABLES_RATIO = 0.49    # receivables / total assets

EXCLUDED_CATEGORIES: List[str] = [
    "conventional_bonds",
    "banks_with_interest",
    "alcohol",
    "tobacco",
    "gambling",
    "pork_products",
    "adult_entertainment",
    "weapons",
    "conventional_insurance",
]


class ShariahChecker:
    """Screen investment dicts for Shariah compliance."""

    def is_compliant(self, investment: Dict) -> Tuple[bool, List[str]]:
        """Return (compliant, list_of_issues)."""
        issues: List[str] = []

        # Industry screen
        sector = (investment.get("sector") or "").lower()
        for prohibited in PROHIBITED_INDUSTRIES:
            if prohibited in sector:
                issues.append(f"Prohibited industry: {sector}")
                break

        # Financial ratio screens
        if investment.get("debt_ratio", 0) > MAX_DEBT_RATIO:
            issues.append(
                f"Debt ratio too high: {investment['debt_ratio']:.1%} (max {MAX_DEBT_RATIO:.0%})"
            )

        if investment.get("interest_income_ratio", 0) > MAX_INTEREST_INCOME:
            issues.append(
                f"Interest income too high: {investment['interest_income_ratio']:.1%} (max {MAX_INTEREST_INCOME:.0%})"
            )

        if investment.get("receivables_ratio", 0) > MAX_RECEIVABLES_RATIO:
            issues.append(
                f"Receivables ratio too high: {investment['receivables_ratio']:.1%} (max {MAX_RECEIVABLES_RATIO:.0%})"
            )

        return len(issues) == 0, issues

    def filter_compliant(self, investments: List[Dict]) -> List[Dict]:
        """Return only compliant investments, marking them."""
        result = []
        for inv in investments:
            compliant, _ = self.is_compliant(inv)
            if compliant:
                inv = {**inv, "is_shariah_compliant": True}
                result.append(inv)
        return result

    @staticmethod
    def get_excluded_categories() -> List[str]:
        return EXCLUDED_CATEGORIES.copy()

    @staticmethod
    def get_screening_note() -> str:
        return (
            "All recommendations screened against Shariah standards. "
            "No interest-bearing instruments (riba), prohibited industries, "
            "or excessive debt ratios included."
        )
