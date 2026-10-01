"""Property-based tests for ``filter_entries`` (Requirement 6.1, 6.2, 6.3, 6.6).

These tests use Hypothesis to assert the invariants that hold for *any* list of
``IP_Prefix`` entries and *any* Region/Service selection, rather than a handful
of hand-picked examples. The properties are drawn directly from Requirement 6:

- 6.1  A specific/specific selection matches an entry exactly when its Region and
       its Service both equal the selection; every other entry is excluded.
- 6.2  Service ``ALL`` matches on Region alone, regardless of Service.
- 6.3  Region ``ALL`` matches on Service alone, regardless of Region.
- 6.6  When nothing matches, the result is empty.

Alongside those, the module's documented contract is checked: the filter is
order-preserving, is a pure function that does not mutate its input, and returns
a subsequence of the original entries.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from aws_ip_navigator.filtering import filter_entries
from aws_ip_navigator.models import ALL, IP_Prefix

# --- Strategies ----------------------------------------------------------

#: A small pool of Region/Service label values. Drawing from a deliberately
#: tiny pool (rather than free text) makes collisions between an entry's value
#: and the selected value common, so both the "matches" and "excluded" branches
#: of every property get exercised. ``ALL`` is intentionally excluded here so a
#: label never accidentally coincides with the sentinel.
_LABELS = st.sampled_from(["ap-northeast-1", "us-east-1", "eu-west-1", "S3", "EC2", "AMAZON"])

#: CIDR strings only need to be distinct-ish payload; their value never affects
#: filtering, so any short text is fine.
_CIDRS = st.text(min_size=1, max_size=12)


@st.composite
def _entries(draw: st.DrawFn) -> list[IP_Prefix]:
    """Generate a list of IP_Prefix entries with reused Region/Service labels."""
    return draw(
        st.lists(
            st.builds(IP_Prefix, cidr=_CIDRS, region=_LABELS, service=_LABELS),
            max_size=20,
        )
    )


#: A selection value is either a concrete label or the ``ALL`` sentinel.
_selection = st.one_of(_LABELS, st.just(ALL))


# --- Requirement 6.1: specific Region + specific Service -----------------


@given(entries=_entries(), region=_LABELS, service=_LABELS)
def test_specific_specific_matches_both_criteria(
    entries: list[IP_Prefix], region: str, service: str
) -> None:
    """6.1: with a specific Region and Service, an entry is kept exactly when
    both its Region and Service equal the selection; all others are excluded."""
    result = filter_entries(entries, region, service)

    # Every kept entry matches both criteria.
    for entry in result:
        assert entry.region == region
        assert entry.service == service

    # Every excluded entry fails at least one criterion.
    for entry in entries:
        if entry not in result:
            assert entry.region != region or entry.service != service


# --- Requirement 6.2: Service ALL matches on Region alone -----------------


@given(entries=_entries(), region=_LABELS)
def test_service_all_matches_on_region_only(entries: list[IP_Prefix], region: str) -> None:
    """6.2: with Service ``ALL`` and a specific Region, the result is exactly the
    entries whose Region equals the selection, regardless of Service."""
    result = filter_entries(entries, region, ALL)

    expected = [entry for entry in entries if entry.region == region]
    assert result == expected


# --- Requirement 6.3: Region ALL matches on Service alone -----------------


@given(entries=_entries(), service=_LABELS)
def test_region_all_matches_on_service_only(entries: list[IP_Prefix], service: str) -> None:
    """6.3: with Region ``ALL`` and a specific Service, the result is exactly the
    entries whose Service equals the selection, regardless of Region."""
    result = filter_entries(entries, ALL, service)

    expected = [entry for entry in entries if entry.service == service]
    assert result == expected


# --- Requirement 6.2 + 6.3 combined: ALL / ALL returns everything ---------


@given(entries=_entries())
def test_all_all_returns_every_entry_in_order(entries: list[IP_Prefix]) -> None:
    """ALL/ALL is the unfiltered view: the result equals the input unchanged."""
    assert filter_entries(entries, ALL, ALL) == entries


# --- Requirement 6.6: no match yields an empty list -----------------------


@given(entries=_entries(), region=_selection, service=_selection)
def test_no_match_yields_empty_list(
    entries: list[IP_Prefix], region: str, service: str
) -> None:
    """6.6: whenever no entry satisfies the selection, the result is empty.

    This is the contrapositive of the match rule: if the result is non-empty,
    then at least one entry must have satisfied both criteria.
    """
    result = filter_entries(entries, region, service)

    def matches(entry: IP_Prefix) -> bool:
        return (region == ALL or entry.region == region) and (
            service == ALL or entry.service == service
        )

    if not any(matches(entry) for entry in entries):
        assert result == []


# --- Module contract: order-preserving, pure, subsequence -----------------


@given(entries=_entries(), region=_selection, service=_selection)
def test_result_is_a_subsequence_in_original_order(
    entries: list[IP_Prefix], region: str, service: str
) -> None:
    """The result preserves the input order and drops no interior ordering:
    it is a subsequence of ``entries`` (Requirement 6, order-preserving)."""
    result = filter_entries(entries, region, service)

    # Walk the original list once; each kept entry must appear in order.
    iterator = iter(entries)
    for kept in result:
        assert any(kept is candidate for candidate in iterator)


@given(entries=_entries(), region=_selection, service=_selection)
def test_filter_does_not_mutate_input(
    entries: list[IP_Prefix], region: str, service: str
) -> None:
    """The filter is pure: it leaves the input list and its contents unchanged."""
    snapshot = list(entries)
    filter_entries(entries, region, service)
    assert entries == snapshot


@given(entries=_entries(), region=_selection, service=_selection)
def test_result_membership_agrees_with_predicate(
    entries: list[IP_Prefix], region: str, service: str
) -> None:
    """The overarching rule spanning 6.1/6.2/6.3: an entry is in the result
    exactly when it satisfies the (region, service) predicate, and the count of
    kept entries equals the number of satisfying entries (Requirement 6.5)."""
    result = filter_entries(entries, region, service)

    def matches(entry: IP_Prefix) -> bool:
        return (region == ALL or entry.region == region) and (
            service == ALL or entry.service == service
        )

    expected = [entry for entry in entries if matches(entry)]
    assert result == expected
    assert len(result) == sum(1 for entry in entries if matches(entry))
