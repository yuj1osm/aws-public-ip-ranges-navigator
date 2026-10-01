"""Pure filter logic for the AWS Public IP Ranges Navigator.

This module computes the filtered view of the parsed entries that the results
table displays. It is pure (no I/O, no mutation of inputs) and order-preserving,
which keeps the sequential row numbers in the table stable and gap-free.

``filter_entries`` expresses all four selection combinations
(specific/specific, ALL/specific, specific/ALL, ALL/ALL) with a single
predicate (Requirement 6.1, 6.2, 6.3). ``build_rows`` turns a filtered list into
numbered display rows starting at 1 (Requirement 6.4).
"""

from dataclasses import dataclass

from .models import ALL, IP_Prefix


def filter_entries(entries: list[IP_Prefix], region: str, service: str) -> list[IP_Prefix]:
    """Return the entries matching the given Region and Service selection.

    An entry matches when ``(region == ALL or entry.region == region)`` and
    ``(service == ALL or entry.service == service)``. The order of ``entries``
    is preserved, and an empty list is returned when nothing matches
    (Requirement 6.1, 6.2, 6.3, 6.6).
    """
    return [
        entry
        for entry in entries
        if (region == ALL or entry.region == region)
        and (service == ALL or entry.service == service)
    ]


@dataclass(frozen=True)
class Row:
    """One numbered display row of the results table.

    ``number`` is the 1-based sequential position of the row in top-to-bottom
    display order; the remaining fields carry the matching entry's values.
    """

    number: int
    cidr: str
    region: str
    service: str


def build_rows(entries: list[IP_Prefix]) -> list[Row]:
    """Return numbered display rows for a filtered list of entries.

    Each row carries a sequential number starting at 1 and incrementing by 1
    with no gaps, in top-to-bottom display order, along with the corresponding
    entry's CIDR, Region, and Service (Requirement 6.4). An empty input yields
    an empty list.
    """
    return [
        Row(number, entry.cidr, entry.region, entry.service)
        for number, entry in enumerate(entries, start=1)
    ]
