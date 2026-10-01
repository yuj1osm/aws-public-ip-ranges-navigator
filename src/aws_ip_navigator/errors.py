"""Exception hierarchy for the AWS Public IP Ranges Navigator.

All errors raised by the Navigator's own layers derive from
:class:`NavigatorError`, so callers can catch the whole family with a single
base type while still branching on a specific subclass. The two failure
domains — networking (fetch) and parsing — each have their own subtree:

- :class:`FetchError` and its :class:`FetchTimeoutError` specialization cover
  retrieval failures from the networking layer (Requirements 2.4, 2.6).
- :class:`ParseError` and its :class:`StructuralParseError` and
  :class:`MissingPrefixCollectionError` specializations cover the distinct
  parse-failure modes (Requirements 2.7, 11.2, 11.3).

Because every failure mode is a distinct type, callers never need a bare
``except Exception``: they can catch exactly the condition they handle (for
example, distinguishing a timeout from a generic fetch failure, or a
structurally invalid document from a merely incomplete one) and let anything
unexpected propagate.
"""


class NavigatorError(Exception):
    """Base class for every error raised by the Navigator's own layers.

    Catch this to handle any Navigator-originated failure uniformly; catch a
    more specific subclass to branch on the particular failure mode.
    """


class FetchError(NavigatorError):
    """The IP ranges document could not be retrieved.

    Raised by the networking layer for any retrieval failure that is not a
    timeout — for example a connection error or an unsuccessful HTTP status.
    Callers surface this as "the data could not be retrieved" and leave the
    Data_Store unchanged (Requirement 2.4).
    """


class FetchTimeoutError(FetchError):
    """A complete IP ranges document was not received within the timeout.

    A specialization of :class:`FetchError` raised when the retrieval does not
    complete within the allotted time (15 seconds). Because it derives from
    :class:`FetchError`, callers that only care that retrieval failed can catch
    the base type, while callers that want to react specifically to a timeout
    can catch this type (Requirement 2.6).
    """


class ParseError(NavigatorError):
    """The retrieved IP ranges document could not be parsed.

    Base class for the parse-failure modes. Callers surface this as "the data
    could not be parsed" and leave the Data_Store unchanged (Requirement 2.7).
    """


class StructuralParseError(ParseError):
    """The document text is not a structurally valid IP ranges document.

    Raised when the text is not valid JSON, or is a valid JSON value whose top
    level is not an object. Distinct from
    :class:`MissingPrefixCollectionError` so callers can tell a malformed
    document from a well-formed one that lacks the prefix collection
    (Requirement 11.2).
    """


class MissingPrefixCollectionError(ParseError):
    """The document is structurally valid but lacks the prefix collection.

    Raised when the text parses into a JSON object that does not contain the
    expected prefix collection (the ``prefixes`` key). Distinct from
    :class:`StructuralParseError` so callers can branch on the specific cause
    (Requirement 11.3).
    """
