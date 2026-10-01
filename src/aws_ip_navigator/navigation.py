"""Pure navigation and scroll math for the selection lists.

This module holds the side-effect-free logic that backs keyboard navigation
(clamped selection-index movement), scroll-offset computation (keeping the
selected item visible), scroll-only wheel handling (moving the visible window
without touching the selection), and the Tab toggle for the active panel.

Keeping this math pure makes it exhaustively testable in isolation and lets the
presentation layer (``app.py``) reuse the exact same logic for both keyboard and
mouse input. See the design's Correctness Properties 9, 10, 11, and 17.
"""

from __future__ import annotations

from enum import Enum


class Active_Panel(Enum):
    """Which selection list currently receives navigation input.

    Exactly one of the two selection lists is active at any time. ``Tab``
    toggles between them (design Property 11).
    """

    REGION = "region"
    SERVICE = "service"


def move_down(index: int, list_length: int) -> int:
    """Return the selection index after pressing the Down arrow.

    Moves the selection to the next item unless it is already on the last item,
    in which case the index is kept. When the list is empty the selection does
    not change. The result always lies within the valid range
    ``0 <= result < list_length`` for a non-empty list (design Property 9,
    Requirements 5.1, 5.3, 5.5).

    Args:
        index: The current selection index.
        list_length: The number of items in the active list.

    Returns:
        The clamped selection index after moving down.
    """
    if list_length <= 0:
        return 0
    last_index = list_length - 1
    return min(index + 1, last_index)


def move_up(index: int, list_length: int) -> int:
    """Return the selection index after pressing the Up arrow.

    Moves the selection to the previous item unless it is already on the first
    item, in which case the index is kept. When the list is empty the selection
    does not change. The result always lies within the valid range
    ``0 <= result < list_length`` for a non-empty list (design Property 9,
    Requirements 5.2, 5.4, 5.5).

    Args:
        index: The current selection index.
        list_length: The number of items in the active list.

    Returns:
        The clamped selection index after moving up.
    """
    if list_length <= 0:
        return 0
    return max(index - 1, 0)


def scroll_offset(list_length: int, viewport_height: int, selected_index: int) -> int:
    """Compute the scroll offset that keeps the selected item visible.

    The returned offset satisfies ``offset <= selected_index <
    offset + viewport_height`` and stays within the valid range so the visible
    window never extends beyond the list bounds (design Property 10,
    Requirement 5.6).

    The offset is derived purely from the selection: if the selected item is
    above the current window it becomes the top of the window; if it is below,
    the window slides down so the selected item is the last visible row. The
    result is then clamped so that ``0 <= offset <= max(0, list_length -
    viewport_height)``.

    Args:
        list_length: The number of items in the list.
        viewport_height: The number of rows visible at once. Values less than
            one are treated as one.
        selected_index: The index of the currently selected item.

    Returns:
        A scroll offset within the valid range that keeps the selection
        visible. Returns ``0`` for an empty list.
    """
    if list_length <= 0:
        return 0
    height = max(viewport_height, 1)
    max_offset = max(0, list_length - height)
    # Bring the selected index into a sensible range before computing.
    index = max(0, min(selected_index, list_length - 1))
    # The smallest offset that still keeps the selection visible is
    # index - height + 1; the largest is index itself.
    offset = max(0, index - height + 1)
    return min(offset, max_offset)


def scroll_by(current_offset: int, amount: int, list_length: int, viewport_height: int) -> int:
    """Adjust the scroll offset by a wheel amount, leaving the selection alone.

    This is the scroll-only helper: it changes only the visible window and does
    not read or modify the selected index. The new offset is clamped to the
    valid range ``0 <= offset <= max(0, list_length - viewport_height)`` so the
    window never extends past the list bounds (design Property 17,
    Requirements 12.5, 12.7).

    A non-overflowing list (``list_length <= viewport_height``) has a maximum
    offset of zero, so any wheel input resolves to ``0`` (no movement).

    Args:
        current_offset: The current scroll offset.
        amount: The signed wheel delta. Positive scrolls toward the end of the
            list, negative scrolls toward the start.
        list_length: The number of items in the list.
        viewport_height: The number of rows visible at once. Values less than
            one are treated as one.

    Returns:
        The new scroll offset within the valid range.
    """
    if list_length <= 0:
        return 0
    height = max(viewport_height, 1)
    max_offset = max(0, list_length - height)
    return max(0, min(current_offset + amount, max_offset))


def toggle_panel(active: Active_Panel) -> Active_Panel:
    """Return the other panel, toggling the active selection list.

    ``Tab`` switches focus from the Region_List to the Service_List and back.
    Exactly one panel is active at any time, so toggling an even number of
    times returns to the starting panel and an odd number lands on the other
    (design Property 11, Requirements 4.1, 4.2).

    Args:
        active: The currently active panel.

    Returns:
        The panel that becomes active after a Tab press.
    """
    if active is Active_Panel.REGION:
        return Active_Panel.SERVICE
    return Active_Panel.REGION
