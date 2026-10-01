"""Parsing of the AWS public IP ranges document into ``IP_Prefix`` entries.

This module is pure (no I/O): it turns the raw document text produced by the
networking layer into a list of :class:`~aws_ip_navigator.models.IP_Prefix`
values. It distinguishes the two parse-failure modes with distinct exception
types so the orchestrator can react to each precisely:

- :class:`StructuralParseError` when the text is not valid JSON or its top
  level is not an object (Requirement 11.2).
- :class:`MissingPrefixCollectionError` when the document is a valid object
  but lacks the ``prefixes`` collection (Requirement 11.3).

Each entry in the ``prefixes`` collection maps ``ip_prefix``/``region``/
``service`` to ``IP_Prefix(cidr, region, service)`` (Requirement 11.1). An
entry is skipped when any of those three fields is missing, empty, or blank
after trimming; the remaining entries preserve input order (Requirement 2.8,
11.4).
"""

import json

from .errors import MissingPrefixCollectionError, StructuralParseError
from .models import IP_Prefix

#: Top-level key holding the IPv4 prefix collection in the AWS document.
_PREFIXES_KEY = "prefixes"

#: Per-entry field names mapped onto ``IP_Prefix(cidr, region, service)``.
_CIDR_FIELD = "ip_prefix"
_REGION_FIELD = "region"
_SERVICE_FIELD = "service"


def parse_ip_ranges(document_text: str) -> list[IP_Prefix]:
    """Parse the IP ranges document into ``IP_Prefix`` entries.

    Reads the IPv4 prefix collection ("prefixes"), producing one ``IP_Prefix``
    per entry that has a non-empty CIDR, region, and service. Entries missing,
    empty, or blank in any of those three fields are skipped, and the remaining
    entries preserve input order.

    Raises :class:`StructuralParseError` if the text is not a structurally
    valid document (for example, not valid JSON, or not a JSON object).
    Raises :class:`MissingPrefixCollectionError` if the document is
    structurally valid but does not contain the expected prefix collection.
    """
    try:
        document = json.loads(document_text)
    except json.JSONDecodeError as exc:
        raise StructuralParseError("document text is not valid JSON") from exc

    if not isinstance(document, dict):
        raise StructuralParseError("document top level is not an object")

    if _PREFIXES_KEY not in document:
        raise MissingPrefixCollectionError(f"document lacks the {_PREFIXES_KEY!r} collection")

    prefixes = document[_PREFIXES_KEY]
    if not isinstance(prefixes, list):
        raise StructuralParseError(f"{_PREFIXES_KEY!r} is not a list")

    return [
        IP_Prefix(cidr, region, service)
        for entry in prefixes
        for cidr, region, service in (_extract_fields(entry),)
        if cidr and region and service
    ]


def _extract_fields(entry: object) -> tuple[str, str, str]:
    """Return the trimmed (cidr, region, service) for one prefix entry.

    A field that is missing, not a string, or blank after trimming becomes an
    empty string so the caller can skip the entry uniformly.
    """
    if not isinstance(entry, dict):
        return "", "", ""
    return (
        _trimmed(entry.get(_CIDR_FIELD)),
        _trimmed(entry.get(_REGION_FIELD)),
        _trimmed(entry.get(_SERVICE_FIELD)),
    )


def _trimmed(value: object) -> str:
    """Return ``value`` trimmed of surrounding whitespace, or "" if not a string."""
    if isinstance(value, str):
        return value.strip()
    return ""
