"""GATE TEST: Three-valued Kleene logic.

Property-based tests using Hypothesis to verify:
1. all_of / any_of / not_ follow Kleene truth tables
2. UNKNOWN never collapses to TRUE or FALSE inappropriately
3. Bool conversion raises TypeError
"""
from __future__ import annotations

import pytest
from hypothesis import given, strategies as st

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from packages.common.three_valued import Ternary


pytestmark = pytest.mark.gate

ternary_values = st.sampled_from([Ternary.TRUE, Ternary.FALSE, Ternary.UNKNOWN])


class TestKleeneNot:
    def test_not_true(self):
        assert Ternary.not_(Ternary.TRUE) == Ternary.FALSE

    def test_not_false(self):
        assert Ternary.not_(Ternary.FALSE) == Ternary.TRUE

    def test_not_unknown(self):
        assert Ternary.not_(Ternary.UNKNOWN) == Ternary.UNKNOWN

    @given(ternary_values)
    def test_double_negation(self, v):
        """not(not(x)) == x for all Kleene values."""
        assert Ternary.not_(Ternary.not_(v)) == v


class TestKleeneAllOf:
    def test_all_true(self):
        assert Ternary.all_of([Ternary.TRUE, Ternary.TRUE]) == Ternary.TRUE

    def test_any_false_gives_false(self):
        assert Ternary.all_of([Ternary.TRUE, Ternary.FALSE]) == Ternary.FALSE
        assert Ternary.all_of([Ternary.FALSE, Ternary.TRUE]) == Ternary.FALSE
        assert Ternary.all_of([Ternary.FALSE, Ternary.UNKNOWN]) == Ternary.FALSE

    def test_unknown_with_true_gives_unknown(self):
        assert Ternary.all_of([Ternary.TRUE, Ternary.UNKNOWN]) == Ternary.UNKNOWN
        assert Ternary.all_of([Ternary.UNKNOWN, Ternary.TRUE]) == Ternary.UNKNOWN

    def test_all_unknown_gives_unknown(self):
        assert Ternary.all_of([Ternary.UNKNOWN, Ternary.UNKNOWN]) == Ternary.UNKNOWN

    def test_empty_gives_true(self):
        """all_of on empty set is TRUE (vacuous truth)."""
        assert Ternary.all_of([]) == Ternary.TRUE

    @given(st.lists(ternary_values, min_size=1, max_size=10))
    def test_false_dominates(self, items):
        """If any item is FALSE, result is FALSE."""
        result = Ternary.all_of(items)
        if any(i == Ternary.FALSE for i in items):
            assert result == Ternary.FALSE

    @given(st.lists(ternary_values, min_size=1, max_size=10))
    def test_unknown_never_true_when_present(self, items):
        """If UNKNOWN is present and no FALSE, result is UNKNOWN (not TRUE)."""
        result = Ternary.all_of(items)
        has_false = any(i == Ternary.FALSE for i in items)
        has_unknown = any(i == Ternary.UNKNOWN for i in items)
        if has_unknown and not has_false:
            assert result == Ternary.UNKNOWN


class TestKleeneAnyOf:
    def test_all_false(self):
        assert Ternary.any_of([Ternary.FALSE, Ternary.FALSE]) == Ternary.FALSE

    def test_any_true_gives_true(self):
        assert Ternary.any_of([Ternary.FALSE, Ternary.TRUE]) == Ternary.TRUE
        assert Ternary.any_of([Ternary.TRUE, Ternary.UNKNOWN]) == Ternary.TRUE

    def test_unknown_with_false_gives_unknown(self):
        assert Ternary.any_of([Ternary.FALSE, Ternary.UNKNOWN]) == Ternary.UNKNOWN

    def test_empty_gives_false(self):
        assert Ternary.any_of([]) == Ternary.FALSE

    @given(st.lists(ternary_values, min_size=1, max_size=10))
    def test_true_dominates(self, items):
        result = Ternary.any_of(items)
        if any(i == Ternary.TRUE for i in items):
            assert result == Ternary.TRUE


class TestBoolConversionBlocked:
    def test_bool_raises(self):
        """Ternary values must not be used in boolean context."""
        with pytest.raises(TypeError, match="must not be used in boolean context"):
            if Ternary.TRUE:
                pass

    def test_unknown_bool_raises(self):
        with pytest.raises(TypeError):
            bool(Ternary.UNKNOWN)


class TestUnknownNeverRejects:
    """UNKNOWN must never produce a rejection — the central safety property."""

    @given(st.lists(ternary_values, min_size=1, max_size=10))
    def test_all_of_unknown_is_not_false_without_false_input(self, items):
        """If no input is FALSE, all_of never returns FALSE."""
        if not any(i == Ternary.FALSE for i in items):
            assert Ternary.all_of(items) != Ternary.FALSE

    @given(st.lists(ternary_values, min_size=1, max_size=10))
    def test_any_of_unknown_is_not_true_without_true_input(self, items):
        """If no input is TRUE, any_of never returns TRUE."""
        if not any(i == Ternary.TRUE for i in items):
            assert Ternary.any_of(items) != Ternary.TRUE
