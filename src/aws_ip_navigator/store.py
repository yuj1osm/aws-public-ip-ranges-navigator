"""In-memory store for parsed AWS IP range entries.

``Data_Store`` holds the ``IP_Prefix`` entries produced by the parser and
derives the distinct Region and Service values used to build the selection
lists. It is a pure, side-effect-free domain component: it never performs I/O
and is replaced atomically on a successful reload.
"""

from dataclasses import dataclass, field

from .models import IP_Prefix


@dataclass
class Data_Store:
    """The in-memory representation of parsed ``IP_Prefix`` entries.

    Mutable so a successful reload can swap its contents in place. The
    presentation layer prepends the ``ALL`` entry when rendering the selection
    lists, so ``regions()`` and ``services()`` deliberately omit it.
    """

    entries: list[IP_Prefix] = field(default_factory=list)

    def replace(self, new_entries: list[IP_Prefix]) -> None:
        """Replace all entries atomically.

        Called only after a fully successful fetch+parse, so a reload never
        leaves the store partially updated. A defensive copy of ``new_entries``
        is taken so the caller cannot mutate the store's contents afterward.
        """
        self.entries = list(new_entries)

    def regions(self) -> list[str]:
        """Return the distinct Region values present, sorted ascending.

        Excludes the ``ALL`` sentinel; the presentation layer prepends it when
        building the Region_List.
        """
        return sorted({entry.region for entry in self.entries})

    def services(self) -> list[str]:
        """Return the distinct Service values present, sorted ascending.

        Excludes the ``ALL`` sentinel; the presentation layer prepends it when
        building the Service_List.
        """
        return sorted({entry.service for entry in self.entries})
