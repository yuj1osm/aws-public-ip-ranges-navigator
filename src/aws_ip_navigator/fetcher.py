"""Data_Fetcher: HTTPS retrieval of the AWS IP ranges document.

This is the Navigator's networking (I/O) layer. It performs a single HTTPS
retrieval of the IP ranges document with a hard timeout and returns the
response body as text, or raises on failure.

The fetcher is deliberately narrow: it does not parse the document and does
not touch the Data_Store. It either returns text or raises, which keeps the
"retain existing data on failure" decision entirely in the orchestrator
(Requirement 2.4). Failure modes are surfaced as the project's own exception
types so callers can branch on the specific cause:

- :class:`~aws_ip_navigator.errors.FetchTimeoutError` when a complete document
  is not received within the timeout (Requirement 2.6).
- :class:`~aws_ip_navigator.errors.FetchError` for any other retrieval failure,
  such as a connection error or an unsuccessful HTTP status (Requirement 2.4).
"""

import socket
import urllib.error
import urllib.request

from .errors import FetchError, FetchTimeoutError

Data_Source_URL = "https://ip-ranges.amazonaws.com/ip-ranges.json"


def fetch_ip_ranges(url: str, timeout_seconds: float = 15.0) -> str:
    """Retrieve the IP ranges document over HTTPS.

    Args:
        url: The URL to retrieve. Callers pass :data:`Data_Source_URL`, which
            is HTTPS by construction (Requirement 2.1).
        timeout_seconds: Maximum time to wait for the complete document. If the
            document is not received within this window the retrieval is
            aborted (Requirement 2.6).

    Returns:
        The response body decoded as text.

    Raises:
        FetchTimeoutError: If the complete document is not received within
            ``timeout_seconds``.
        FetchError: For any other retrieval failure, including connection
            errors and unsuccessful HTTP statuses.
    """
    request = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
            return body.decode(charset)
    except socket.timeout as exc:
        raise FetchTimeoutError(
            f"Timed out retrieving IP ranges document after {timeout_seconds}s"
        ) from exc
    except urllib.error.URLError as exc:
        # A timeout raised through URLError (its reason is a socket.timeout)
        # is still a timeout, not a generic retrieval failure.
        if isinstance(exc.reason, socket.timeout):
            raise FetchTimeoutError(
                f"Timed out retrieving IP ranges document after {timeout_seconds}s"
            ) from exc
        raise FetchError(f"Failed to retrieve IP ranges document: {exc}") from exc
    except OSError as exc:
        raise FetchError(f"Failed to retrieve IP ranges document: {exc}") from exc
