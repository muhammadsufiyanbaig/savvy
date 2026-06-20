"""Shariah compliance checker tests — pure Python, no external deps."""

import pytest
from app.services.shariah_checker import (
    ShariahChecker,
    PROHIBITED_INDUSTRIES,
    MAX_DEBT_RATIO,
    MAX_INTEREST_INCOME,
    MAX_RECEIVABLES_RATIO,
    EXCLUDED_CATEGORIES,
)


@pytest.fixture
def checker():
    return ShariahChecker()


def _inv(**kwargs):
    """Base compliant investment dict, override with kwargs."""
    base = {
        "investment_type": "stocks",
        "asset_name": "Test Corp",
        "sector": "technology",
        "debt_ratio": 0.10,
        "interest_income_ratio": 0.01,
        "receivables_ratio": 0.20,
        "is_shariah_compliant": True,
    }
    return {**base, **kwargs}


# ── is_compliant — passing cases ──────────────────────────────────────────────

class TestIsCompliantPasses:
    def test_clean_investment_passes(self, checker):
        compliant, issues = checker.is_compliant(_inv())
        assert compliant is True
        assert issues == []

    def test_zero_ratios_passes(self, checker):
        compliant, issues = checker.is_compliant(
            _inv(debt_ratio=0.0, interest_income_ratio=0.0, receivables_ratio=0.0)
        )
        assert compliant is True

    def test_exactly_at_max_debt_ratio_passes(self, checker):
        # Boundary: equal to max is NOT above → should pass
        compliant, issues = checker.is_compliant(_inv(debt_ratio=MAX_DEBT_RATIO))
        assert compliant is True

    def test_exactly_at_max_interest_passes(self, checker):
        compliant, issues = checker.is_compliant(_inv(interest_income_ratio=MAX_INTEREST_INCOME))
        assert compliant is True

    def test_exactly_at_max_receivables_passes(self, checker):
        compliant, issues = checker.is_compliant(_inv(receivables_ratio=MAX_RECEIVABLES_RATIO))
        assert compliant is True

    def test_empty_sector_passes(self, checker):
        compliant, issues = checker.is_compliant(_inv(sector=""))
        assert compliant is True

    def test_none_sector_passes(self, checker):
        compliant, issues = checker.is_compliant(_inv(sector=None))
        assert compliant is True

    def test_missing_ratio_fields_pass(self, checker):
        """Investments without ratio fields default to 0 — should pass."""
        compliant, issues = checker.is_compliant({"sector": "technology"})
        assert compliant is True


# ── is_compliant — failing cases ──────────────────────────────────────────────

class TestIsCompliantFails:
    def test_high_debt_ratio_fails(self, checker):
        compliant, issues = checker.is_compliant(_inv(debt_ratio=0.50))
        assert compliant is False
        assert any("Debt ratio" in i for i in issues)

    def test_high_interest_income_fails(self, checker):
        compliant, issues = checker.is_compliant(_inv(interest_income_ratio=0.10))
        assert compliant is False
        assert any("Interest income" in i for i in issues)

    def test_high_receivables_fails(self, checker):
        compliant, issues = checker.is_compliant(_inv(receivables_ratio=0.60))
        assert compliant is False
        assert any("Receivables" in i for i in issues)

    def test_multiple_violations_returns_all_issues(self, checker):
        compliant, issues = checker.is_compliant(
            _inv(debt_ratio=0.50, interest_income_ratio=0.10, receivables_ratio=0.60)
        )
        assert compliant is False
        assert len(issues) == 3

    @pytest.mark.parametrize("industry", PROHIBITED_INDUSTRIES)
    def test_prohibited_industry_fails(self, checker, industry):
        compliant, issues = checker.is_compliant(_inv(sector=industry))
        assert compliant is False
        assert any("Prohibited industry" in i for i in issues)

    def test_sector_substring_match_fails(self, checker):
        """Sector containing a prohibited word should fail."""
        compliant, issues = checker.is_compliant(_inv(sector="gambling_platform"))
        assert compliant is False

    def test_combined_industry_and_ratio_fails(self, checker):
        compliant, issues = checker.is_compliant(
            _inv(sector="alcohol", debt_ratio=0.50)
        )
        assert compliant is False
        # Industry issue + debt ratio issue
        assert len(issues) >= 2


# ── filter_compliant ──────────────────────────────────────────────────────────

class TestFilterCompliant:
    def test_filters_out_non_compliant(self, checker):
        investments = [
            _inv(sector="technology", debt_ratio=0.10),   # compliant
            _inv(sector="alcohol"),                         # not compliant
            _inv(sector="gambling"),                        # not compliant
        ]
        result = checker.filter_compliant(investments)
        assert len(result) == 1
        assert result[0]["sector"] == "technology"

    def test_all_compliant_returns_all(self, checker):
        investments = [_inv(), _inv(sector="healthcare"), _inv(sector="consumer_staples")]
        result = checker.filter_compliant(investments)
        assert len(result) == 3

    def test_all_non_compliant_returns_empty(self, checker):
        investments = [
            _inv(sector="alcohol"),
            _inv(debt_ratio=0.80),
        ]
        result = checker.filter_compliant(investments)
        assert result == []

    def test_filter_marks_is_shariah_compliant_true(self, checker):
        investments = [_inv(is_shariah_compliant=False)]
        result = checker.filter_compliant(investments)
        # After filtering, surviving investments should be marked compliant
        assert result[0]["is_shariah_compliant"] is True

    def test_empty_list_returns_empty(self, checker):
        assert checker.filter_compliant([]) == []

    def test_does_not_mutate_original(self, checker):
        orig = _inv(is_shariah_compliant=False)
        checker.filter_compliant([orig])
        # Original dict should NOT be mutated
        assert orig.get("is_shariah_compliant") is False


# ── static helpers ────────────────────────────────────────────────────────────

class TestStaticHelpers:
    def test_get_excluded_categories_is_list(self, checker):
        cats = ShariahChecker.get_excluded_categories()
        assert isinstance(cats, list)
        assert len(cats) > 0

    def test_get_excluded_categories_returns_copy(self):
        cats1 = ShariahChecker.get_excluded_categories()
        cats2 = ShariahChecker.get_excluded_categories()
        cats1.append("mutated")
        assert "mutated" not in cats2

    def test_get_screening_note_is_string(self):
        note = ShariahChecker.get_screening_note()
        assert isinstance(note, str)
        assert len(note) > 10
        assert "riba" in note.lower() or "shariah" in note.lower() or "interest" in note.lower()

    def test_excluded_categories_constant_unchanged(self):
        assert "conventional_bonds" in EXCLUDED_CATEGORIES
        assert "gambling" in EXCLUDED_CATEGORIES


# ── threshold constants ───────────────────────────────────────────────────────

class TestThresholds:
    def test_debt_ratio_threshold(self):
        assert MAX_DEBT_RATIO == 0.33

    def test_interest_income_threshold(self):
        assert MAX_INTEREST_INCOME == 0.05

    def test_receivables_threshold(self):
        assert MAX_RECEIVABLES_RATIO == 0.49

    def test_just_above_debt_ratio_fails(self, checker):
        compliant, _ = checker.is_compliant(_inv(debt_ratio=MAX_DEBT_RATIO + 0.001))
        assert compliant is False

    def test_just_above_interest_fails(self, checker):
        compliant, _ = checker.is_compliant(_inv(interest_income_ratio=MAX_INTEREST_INCOME + 0.001))
        assert compliant is False
