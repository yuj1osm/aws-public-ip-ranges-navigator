"""Sample module for the AWS Public IP Ranges Navigator.

This is a demonstration module showing the project's conventions: a module
docstring, ``@dataclass`` value types, comprehensions over plain loops, and
custom exceptions callers can branch on. It builds a few example ``IP_Prefix``
entries and offers a small helper to summarize them by service.
"""

from collections import Counter
from dataclasses import dataclass

from .models import IP_Prefix


class SampleError(Exception):
    """Base class for errors raised by the sample module."""


class EmptySampleError(SampleError):
    """Raised when a summary is requested for an empty set of entries."""


#: A few illustrative AWS public IP range entries.
SAMPLE_PREFIXES: list[IP_Prefix] = [
    IP_Prefix(cidr="52.94.0.0/22", region="ap-northeast-1", service="EC2"),
    IP_Prefix(cidr="52.219.0.0/20", region="ap-northeast-1", service="S3"),
    IP_Prefix(cidr="13.34.0.0/24", region="us-east-1", service="EC2"),
    IP_Prefix(cidr="99.77.128.0/18", region="eu-west-1", service="CLOUDFRONT"),
]


@dataclass(frozen=True)
class ServiceCount:
    """An immutable count of entries for a single service."""

    service: str
    count: int


def count_by_service(entries: list[IP_Prefix]) -> list[ServiceCount]:
    """Return per-service entry counts, sorted by service name.

    Raises ``EmptySampleError`` when ``entries`` is empty so callers can branch
    on the error type instead of inspecting an empty result.
    """
    if not entries:
        raise EmptySampleError("cannot summarize an empty set of entries")

    counts = Counter(entry.service for entry in entries)
    return [ServiceCount(service, counts[service]) for service in sorted(counts)]


def main() -> None:
    """Print a short summary of the sample entries to standard output."""
    for item in count_by_service(SAMPLE_PREFIXES):
        print(f"{item.service}: {item.count}")


if __name__ == "__main__":
    main()
