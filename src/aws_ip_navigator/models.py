"""Pure data models for the AWS Public IP Ranges Navigator.

This module defines the immutable ``IP_Prefix`` value type produced by the
parser and held by the store, and the mutable ``Filter_Selection`` that drives
the results table. It also defines the shared ``ALL`` sentinel used by both the
selection state here and the filter logic in ``filtering.py``.
"""

from dataclasses import dataclass

#: Sentinel meaning "no filter" for a Region or Service selection. Shared
#: between the selection state below and the filter logic in ``filtering.py``;
#: it lives here because ``filtering`` already depends on this module, which
#: keeps the sentinel available to both without a circular import.
ALL = "ALL"


@dataclass(frozen=True)
class IP_Prefix:
    """An immutable AWS public IP range entry.

    ``frozen=True`` makes the entry immutable and hashable: a parsed entry is a
    fact about the fetched data that must not mutate after creation, which also
    makes it safe to share between the store, filter, and table, and usable in
    distinct-value computations.
    """

    cidr: str  # e.g. "52.94.0.0/22"
    region: str  # e.g. "ap-northeast-1"
    service: str  # e.g. "EC2"


@dataclass
class Filter_Selection:
    """The current Region/Service selection driving the results table.

    Mutable because it changes as the user navigates. The initial (reset) state
    is ``ALL``/``ALL``, which the clear-filter action restores to show the
    unfiltered view.
    """

    region: str = ALL
    service: str = ALL

    @classmethod
    def initial(cls) -> "Filter_Selection":
        """Return the unfiltered default selection: region ``ALL``, service ``ALL``."""
        return cls(region=ALL, service=ALL)
