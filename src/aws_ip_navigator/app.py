"""Presentation layer for the AWS Public IP Ranges Navigator.

This module defines ``NavigatorApp``, the Textual ``App`` that composes the
three-panel layout: a left ``Selection_Panel`` stacking the ``Region_List``
above the ``Service_List``, a right ``Results_Table``, and a docked ``Footer``
(the Action_Bar). It reuses the pure domain modules (``store``, ``filtering``,
``models``) for data and filtering.

This task adds the key bindings and focus/Active_Panel switching. The footer
is populated from ``BINDINGS`` so it always lists the available actions
(Requirement 8), and ``Tab`` toggles which selection list is the Active_Panel,
moving focus and the visual active indication with it (Requirement 4).

Mouse handling (task 13.1) is also wired in: a click within a list makes that
list the Active_Panel and, when it lands on an item, selects it and re-applies
the filter through the same pure path as keyboard selection; a click on empty
space activates the list without changing its selection (Requirement 12.1-12.4).
Mouse-wheel scrolling is routed through the pure ``navigation.scroll_by`` helper
so it moves only a list's visible window and leaves the selection, the
``Filter_Selection``, the ``Results_Table``, and the other list unchanged; a
non-overflowing list ignores the wheel (Requirement 12.5-12.7).

The reload/clear/quit actions (task 14.1) are wired in here: ``action_reload``
runs the fetch+parse off the UI thread in a Textual worker and, only on a
fully successful fetch+parse yielding at least one entry, replaces the store
and rebuilds the views; every failure mode keeps the store unchanged and shows
a non-blocking notification while the app stays running. The same fetch+parse
runs once at startup. ``action_clear_filter`` restores the unfiltered view and
``action_quit`` is inherited from Textual's ``App`` (it exits and restores the
terminal on teardown).
"""

from __future__ import annotations

from typing import Callable

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import DataTable, Footer, OptionList
from textual.widgets.option_list import Option

from . import navigation
from .errors import FetchError, ParseError
from .fetcher import Data_Source_URL, fetch_ip_ranges
from .filtering import build_rows, filter_entries
from .models import ALL, Filter_Selection, IP_Prefix
from .navigation import Active_Panel
from .parser import parse_ip_ranges
from .store import Data_Store

#: Non-blocking messages shown when a reload (or the startup fetch) fails. The
#: store is left unchanged in every failure case and the app keeps running
#: (Requirement 2.4, 2.6, 2.7).
_RETRIEVAL_ERROR = "IP ranges could not be retrieved."
_PARSE_ERROR = "IP ranges could not be parsed."

#: The columns of the Results_Table, in display order (Requirement 6.4).
RESULTS_COLUMNS = ("#", "IP Prefix (CIDR)", "Region", "Service")

#: Caret prefix drawn on the highlighted item of a selection list
#: (Requirement 3.8). Non-highlighted items are indented by the same width so
#: labels stay vertically aligned.
_HIGHLIGHT_CARET = "❯ "
_PLAIN_INDENT = "  "


class SelectionList(OptionList):
    """A vertical selection list that marks its highlighted item with ``❯``.

    Rendering one item per line, keyboard navigation, click-to-select, and an
    automatic scrollbar on overflow all come from the underlying Textual
    ``OptionList`` (Requirement 3.4, 3.5, 3.6, 3.7, 12.1, 12.2). This subclass
    adds the ``❯`` caret on the highlighted row by rebuilding the option prompts
    whenever the highlight moves, keeping the labels themselves free of the
    marker.

    It also adapts the mouse behavior to the spec: any click posts a
    :class:`SelectionList.PanelActivated` message so the app can make this list
    the Active_Panel even when the click misses every item (Requirement 12.4),
    and the mouse wheel is routed through the pure ``navigation.scroll_by`` so it
    moves only the visible window without touching the selection, and a
    non-overflowing list ignores it (Requirement 12.5, 12.6, 12.7).
    """

    class PanelActivated(Message):
        """Posted when this list is clicked, so it becomes the Active_Panel.

        A click makes a list the Active_Panel whether or not it lands on an item
        (Requirement 12.1, 12.2, 12.4); the app listens for this message to move
        the active-panel state and its visual indication to ``selection_list``.
        """

        def __init__(self, selection_list: "SelectionList") -> None:
            super().__init__()
            self.selection_list = selection_list

        @property
        def control(self) -> "SelectionList":
            """The list that was clicked (Textual message ``control`` hook)."""
            return self.selection_list

    def set_items(self, labels: list[str]) -> None:
        """Replace the list contents with ``labels``, one item per line.

        The list resets to highlight its first item so the ``❯`` caret is
        visible, or to no highlight when ``labels`` is empty. Preserving the
        prior position across a reload is handled by a later task.
        """
        self.clear_options()
        self.add_options([Option(f"{_PLAIN_INDENT}{label}") for label in labels])
        self.highlighted = 0 if labels else None
        self._apply_caret()

    def _apply_caret(self) -> None:
        """Redraw prompts so only the highlighted item carries the ``❯`` caret."""
        highlighted = self.highlighted
        for index, option in enumerate(self.options):
            label = self._strip_prefix(str(option.prompt))
            prefix = _HIGHLIGHT_CARET if index == highlighted else _PLAIN_INDENT
            self.replace_option_prompt_at_index(index, f"{prefix}{label}")

    @staticmethod
    def _strip_prefix(prompt: str) -> str:
        """Return ``prompt`` without its caret/indent prefix, if present."""
        if prompt.startswith(_HIGHLIGHT_CARET):
            return prompt[len(_HIGHLIGHT_CARET) :]
        if prompt.startswith(_PLAIN_INDENT):
            return prompt[len(_PLAIN_INDENT) :]
        return prompt

    def highlighted_label(self) -> str | None:
        """Return the caret-free label of the highlighted item, or ``None``.

        Returns ``None`` when the list is empty (no item highlighted), so the
        caller can fall back to the ``ALL`` selection.
        """
        index = self.highlighted
        if index is None or index >= self.option_count:
            return None
        return self._strip_prefix(str(self.get_option_at_index(index).prompt))

    def _on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        """Move the ``❯`` caret to follow the newly highlighted item."""
        self._apply_caret()

    async def _on_click(self, event: events.Click) -> None:
        """Activate this list on any click, then run the default selection.

        A click always makes this list the Active_Panel, so a click that lands
        on empty space still activates the list while leaving its selection
        unchanged (Requirement 12.4). A click on an item additionally selects it
        via the base ``OptionList._on_click``, which sets ``highlighted`` and
        posts ``OptionSelected`` — feeding the same filter path as keyboard
        selection (Requirement 12.1, 12.2, 12.3).
        """
        self.post_message(self.PanelActivated(self))
        await super()._on_click(event)

    def _wheel_scroll(self, amount: int) -> None:
        """Scroll the visible window by ``amount`` lines via ``scroll_by``.

        The new offset comes from the pure ``navigation.scroll_by`` applied to
        the current vertical offset, so a non-overflowing list (max offset zero)
        does not move and the selection, highlight, and other state are never
        read or changed (Requirement 12.5, 12.6, 12.7).
        """
        current_offset = int(self.scroll_offset.y)
        viewport_height = self.scrollable_content_region.height
        new_offset = navigation.scroll_by(
            current_offset, amount, self.option_count, viewport_height
        )
        if new_offset != current_offset:
            self.scroll_to(y=new_offset, animate=False)

    def _on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        """Route wheel-down through ``scroll_by`` instead of the default scroll.

        Stopping the event keeps Textual's built-in scrolling from also running,
        so the visible window moves by exactly the clamped ``scroll_by`` amount
        and nothing else changes (Requirement 12.5, 12.7).
        """
        event.stop()
        self._wheel_scroll(1)

    def _on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        """Route wheel-up through ``scroll_by`` instead of the default scroll.

        See :meth:`_on_mouse_scroll_down`; the amount is negative to move the
        visible window toward the start of the list (Requirement 12.5, 12.7).
        """
        event.stop()
        self._wheel_scroll(-1)


class NavigatorApp(App):
    """The Textual application that renders and orchestrates the Navigator.

    Owns the ``Data_Store``, the current ``Filter_Selection``, the active-panel
    state, and the widgets. Exactly one selection list is the Active_Panel at
    any time; ``Tab`` toggles it and moves both focus and the visual active
    indication (Requirement 4.1, 4.2, 4.3).
    """

    #: Declarative key bindings. The same metadata drives the ``Footer`` text,
    #: so the key bar always lists these actions and stays in sync with
    #: behavior (Requirement 8.1-8.6). ``action_quit`` is provided by the
    #: Textual ``App`` base class.
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "reload", "Reload"),
        Binding("x", "clear_filter", "Clear filter"),
        # ``priority`` so the app-level Tab toggle wins over Textual's default
        # focus-cycling binding for Tab (Requirement 4.2).
        Binding("tab", "switch_pane", "Switch pane", priority=True),
        # ``priority`` so the app-level Up/Down routing through the pure
        # navigation math wins over the focused ``OptionList``'s own cursor
        # bindings, which otherwise wrap around at the list ends instead of
        # clamping (Requirement 5.3, 5.4).
        Binding("up", "nav_up", "Navigate", show=True, priority=True),
        Binding("down", "nav_down", "Navigate", show=False, priority=True),
    ]

    CSS = """
    #main {
        height: 1fr;
    }

    #selection_panel {
        width: 40%;
        min-width: 32;
    }

    #region_list {
        height: 1fr;
        border: round $panel;
        border-title-align: left;
        scrollbar-gutter: stable;
    }

    #service_list {
        height: 1fr;
        border: round $panel;
        border-title-align: left;
        scrollbar-gutter: stable;
    }

    /* The Active_Panel is visually distinguished with an accent border and
       title so the user can tell which list Up/Down will act on
       (Requirement 4.3). */
    SelectionList.active-panel {
        border: round $accent;
    }

    #results_table {
        width: 1fr;
        border: round $panel;
        border-title-align: left;
    }
    """

    def __init__(self, fetch: Callable[[], str] | None = None) -> None:
        """Create the app with an empty store and the unfiltered selection.

        Command-line arguments are intentionally ignored so the app always
        launches with the same default behavior (Requirement 1.2).

        Args:
            fetch: A zero-argument callable returning the raw IP ranges
                document text. Defaults to retrieving
                :data:`~aws_ip_navigator.fetcher.Data_Source_URL` over HTTPS.
                Injecting a callable lets tests exercise the reload/startup
                flow without touching the network.
        """
        super().__init__()
        self.store = Data_Store()
        self.filter_selection = Filter_Selection.initial()
        #: The Active_Panel starts on the Region_List (Requirement 4.1).
        self.active_panel = Active_Panel.REGION
        self.region_list = SelectionList(id="region_list")
        self.service_list = SelectionList(id="service_list")
        self.results_table: DataTable = DataTable(id="results_table")
        #: Injectable fetch step. Defaults to the real HTTPS fetcher; tests pass
        #: a stub so the reload/startup path never hits the network.
        self._fetch: Callable[[], str] = fetch if fetch is not None else self._default_fetch

    @staticmethod
    def _default_fetch() -> str:
        """Retrieve the IP ranges document from the fixed HTTPS source URL.

        Wraps :func:`~aws_ip_navigator.fetcher.fetch_ip_ranges` with the fixed
        :data:`~aws_ip_navigator.fetcher.Data_Source_URL` and the default 15s
        timeout (Requirement 2.1, 2.6).
        """
        return fetch_ip_ranges(Data_Source_URL)

    def compose(self) -> ComposeResult:
        """Build the three-panel layout with a docked footer.

        A horizontal split holds the ``Selection_Panel`` (Region_List above
        Service_List) on the left and the ``Results_Table`` on the right; the
        ``Footer`` docks at the bottom (Requirement 3.3, 8.1).
        """
        with Horizontal(id="main"):
            with Vertical(id="selection_panel"):
                yield self.region_list
                yield self.service_list
            yield self.results_table
        yield Footer()

    def on_mount(self) -> None:
        """Set panel titles and the results-table columns after mounting.

        The selection lists start empty until data is fetched and parsed by a
        later task; the results table's columns are fixed and set up here
        (Requirement 6.4).
        """
        self.region_list.border_title = "Regions (↑/↓ to select)"
        self.service_list.border_title = "Services (↑/↓ to select)"
        self.results_table.add_columns(*RESULTS_COLUMNS)
        self._refresh_results_title()
        # Reflect the initial Active_Panel: focus the Region_List and mark it
        # as active (Requirement 4.1, 4.3).
        self._apply_active_panel()
        # Perform the startup fetch+parse off the UI thread, reusing the same
        # path as an on-demand reload. Navigation over the (empty) lists is
        # already safe; it becomes useful once the worker populates the store
        # (Requirement 1.3, 9.1).
        self._start_reload()

    def _active_list(self) -> SelectionList:
        """Return the selection list that is currently the Active_Panel."""
        if self.active_panel is Active_Panel.REGION:
            return self.region_list
        return self.service_list

    def _apply_active_panel(self) -> None:
        """Focus the active list and give it the distinguishing active style.

        Exactly one list carries the ``active-panel`` class and holds focus at
        a time, so the user can always tell which list Up/Down and selection
        act on (Requirement 4.1, 4.3).
        """
        active = self._active_list()
        for selection_list in (self.region_list, self.service_list):
            selection_list.set_class(selection_list is active, "active-panel")
        active.focus()

    def action_switch_pane(self) -> None:
        """Toggle the Active_Panel between the Region_List and Service_List.

        Reuses the pure ``navigation.toggle_panel`` helper so the toggle logic
        stays in one tested place, then moves focus and the visual active
        indication to the newly active list (Requirement 4.2, 4.3).
        """
        self.active_panel = navigation.toggle_panel(self.active_panel)
        self._apply_active_panel()

    def action_reload(self) -> None:
        """Re-fetch and re-parse the IP ranges document on demand (key ``r``).

        The work runs in a background worker so the fetch never blocks the UI
        thread and the interface stays responsive and running throughout
        (Requirement 9.1). Success and every failure mode are handled inside the
        worker; on failure the store is left unchanged and a non-blocking
        message is shown (Requirement 2.4, 2.6, 2.7, 9.3).
        """
        self._start_reload()

    def _start_reload(self) -> None:
        """Launch the fetch+parse worker off the UI thread.

        A ``thread=True`` worker is used because the fetch performs blocking
        network I/O; running it on a worker thread keeps the event loop free so
        the app stays interactive during the retrieval (Requirement 9.1). The
        worker is exclusive so a rapid second reload supersedes an in-flight one
        rather than racing it.
        """
        self.run_worker(
            self._reload_worker,
            name="reload",
            group="reload",
            exclusive=True,
            thread=True,
        )

    def _reload_worker(self) -> None:
        """Fetch, parse, and apply new data, handling each failure precisely.

        Runs on a worker thread. On a fully successful fetch+parse that yields
        at least one entry, the store is replaced and every dependent view is
        rebuilt on the UI thread via ``call_from_thread`` (Requirement 2.3,
        9.2). Only the specific Navigator exception types are caught, so an
        unexpected error still surfaces rather than being silently swallowed:

        - ``FetchError`` (and its ``FetchTimeoutError`` subclass) → the data
          could not be retrieved (Requirement 2.6).
        - ``ParseError`` → the data could not be parsed (Requirement 2.7).
        - a parse that yields zero entries is treated as a parse failure for the
          purpose of the message (Requirement 2.7).

        In every failure case the store is left untouched and the app keeps
        running (Requirement 2.4).
        """
        try:
            document = self._fetch()
        except FetchError:
            self.call_from_thread(self._notify_error, _RETRIEVAL_ERROR)
            return

        try:
            entries = parse_ip_ranges(document)
        except ParseError:
            self.call_from_thread(self._notify_error, _PARSE_ERROR)
            return

        if not entries:
            self.call_from_thread(self._notify_error, _PARSE_ERROR)
            return

        self.call_from_thread(self.load_entries, entries)

    def _notify_error(self, message: str) -> None:
        """Show a non-blocking error notification, keeping the app running.

        Used for both retrieval and parse failures; the store is never modified
        on this path (Requirement 2.4, 2.6, 2.7).
        """
        self.notify(message, severity="error", title="Reload failed")

    def action_clear_filter(self) -> None:
        """Reset the Region/Service selection to the unfiltered view (key ``x``).

        Restores ``Filter_Selection`` to its ``ALL``/``ALL`` initial state,
        moves both selection lists' highlight back to the ``ALL`` entry
        (index 0 when the lists are populated), and refreshes the table so it
        shows every entry again (Requirement 7.1, 7.2).
        """
        self.filter_selection = Filter_Selection.initial()
        if self.region_list.option_count > 0:
            self.region_list.highlighted = 0
        if self.service_list.option_count > 0:
            self.service_list.highlighted = 0
        self._apply_filter()

    def action_nav_up(self) -> None:
        """Move the highlighted item up within the Active_Panel.

        Routes through the pure ``navigation.move_up`` so the index is clamped
        at the top of the list; an empty list is a no-op (Requirement 5.2, 5.4,
        5.5). After moving, the selection is scrolled back into view
        (Requirement 5.6).
        """
        self._navigate(navigation.move_up)

    def action_nav_down(self) -> None:
        """Move the highlighted item down within the Active_Panel.

        Routes through the pure ``navigation.move_down`` so the index is clamped
        at the bottom of the list; an empty list is a no-op (Requirement 5.1,
        5.3, 5.5). After moving, the selection is scrolled back into view
        (Requirement 5.6).
        """
        self._navigate(navigation.move_down)

    def _navigate(self, move: Callable[[int, int], int]) -> None:
        """Apply a pure move function to the Active_Panel's highlighted index.

        ``move`` is ``navigation.move_up`` or ``navigation.move_down``. The list
        length comes from the widget's ``option_count`` so the clamp uses the
        live data; on an empty list the keys are ignored entirely
        (Requirement 5.5). The highlight-changed message emitted by setting
        ``highlighted`` drives the caret redraw and the filter re-application.
        """
        active = self._active_list()
        length = active.option_count
        if length <= 0:
            return
        current = active.highlighted if active.highlighted is not None else 0
        active.highlighted = move(current, length)
        self._scroll_to_selection(active)

    @staticmethod
    def _scroll_to_selection(selection_list: SelectionList) -> None:
        """Scroll ``selection_list`` so its highlighted item stays visible.

        The target offset is computed by the pure ``navigation.scroll_offset``
        from the list length, the visible height, and the selected index, then
        applied to the widget. This keeps the scroll math in one tested place
        (Requirement 5.6).
        """
        index = selection_list.highlighted
        if index is None:
            return
        viewport_height = selection_list.scrollable_content_region.height
        offset = navigation.scroll_offset(selection_list.option_count, viewport_height, index)
        selection_list.scroll_to(y=offset, animate=False)

    def load_entries(self, entries: list[IP_Prefix]) -> None:
        """Replace the store contents and refresh every dependent view.

        Swaps the store atomically, rebuilds both selection lists from the new
        distinct values, and re-applies the current filter so the table and its
        count match the highlighted selection. The current Region/Service
        selection is preserved across the rebuild when those values still exist
        in the new data, so an on-demand reload keeps the user's active filter
        rather than snapping back to ``ALL``; a value that is no longer present
        falls back to ``ALL`` (Requirement 2.3, 9.2, 9.3). Used both by the
        reload flow and by tests to populate data.
        """
        self.store.replace(entries)
        self._rebuild_selection_lists()
        self._apply_filter()

    def _rebuild_selection_lists(self) -> None:
        """Rebuild the Region_List and Service_List from the store.

        Each list is ``["ALL"]`` followed by the store's distinct, sorted values
        so ``ALL`` is always present exactly once and first (Requirement 3.1,
        3.2). The current selection is preserved where the value still exists so
        a reload re-applies the active filter; a value that has disappeared
        (or an empty list) falls back to the ``ALL`` entry (Requirement 9.3).
        """
        region_labels = [ALL, *self.store.regions()]
        service_labels = [ALL, *self.store.services()]
        self.region_list.set_items(region_labels)
        self.service_list.set_items(service_labels)
        self._restore_highlight(self.region_list, region_labels, self.filter_selection.region)
        self._restore_highlight(self.service_list, service_labels, self.filter_selection.service)
        self._sync_filter_selection()

    @staticmethod
    def _restore_highlight(selection_list: SelectionList, labels: list[str], value: str) -> None:
        """Highlight ``value`` in ``selection_list`` if present, else the first.

        ``set_items`` resets the highlight to index 0 (the ``ALL`` entry); this
        moves it back to the previously selected ``value`` when that value still
        appears in ``labels`` so a reload preserves the active filter. When the
        value is gone or the list is empty the ``ALL`` default at index 0 is
        kept (Requirement 9.3).
        """
        if not labels:
            return
        if value in labels:
            selection_list.highlighted = labels.index(value)

    def _sync_filter_selection(self) -> None:
        """Update ``filter_selection`` from the two lists' highlighted labels.

        A missing highlight (empty list) falls back to ``ALL`` so the filter
        stays well-defined (Requirement 6.1).
        """
        region = self.region_list.highlighted_label()
        service = self.service_list.highlighted_label()
        self.filter_selection.region = region if region is not None else ALL
        self.filter_selection.service = service if service is not None else ALL

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        """Re-apply the filter whenever either list's highlight changes.

        A highlight change from keyboard navigation or a mouse click feeds the
        same pure ``filter_entries`` path, so both input methods produce the
        same filtered table (Requirement 6.1, 6.2, 6.3). The event is allowed to
        keep bubbling so the ``SelectionList`` caret redraw still runs.
        """
        self._apply_filter()

    def on_selection_list_panel_activated(self, event: SelectionList.PanelActivated) -> None:
        """Make a clicked selection list the Active_Panel.

        A click on either list — on an item or on empty space — activates that
        list, moving the active-panel state, focus, and the visual active
        indication to it (Requirement 12.1, 12.2, 12.4). Item selection and the
        resulting filter update are driven separately by the list's highlight
        change, so this handler only owns the active-panel switch.
        """
        if event.selection_list is self.service_list:
            self.active_panel = Active_Panel.SERVICE
        else:
            self.active_panel = Active_Panel.REGION
        self._apply_active_panel()

    def _apply_filter(self) -> None:
        """Recompute the filtered entries and repopulate the results table.

        Derives the matching entries with ``filter_entries``, rebuilds the
        ``DataTable`` rows with 1..n gap-free numbering via ``build_rows``, and
        sets the header count from that same list so the count always equals the
        number of displayed rows, including zero matches (Requirement 6.4, 6.5,
        6.6).
        """
        self._sync_filter_selection()
        matches = filter_entries(
            self.store.entries,
            self.filter_selection.region,
            self.filter_selection.service,
        )
        rows = build_rows(matches)
        self.results_table.clear()
        for row in rows:
            self.results_table.add_row(str(row.number), row.cidr, row.region, row.service)
        self.results_table.border_title = f"Matching IP Prefixes ({len(rows)} items found)"

    def _refresh_results_title(self) -> None:
        """Set the results-table title to the current matching-row count.

        Called on mount before any data is loaded so the header shows a zero
        count; ``_apply_filter`` keeps it in sync thereafter (Requirement 6.5).
        """
        matches = filter_entries(
            self.store.entries,
            self.filter_selection.region,
            self.filter_selection.service,
        )
        count = len(build_rows(matches))
        self.results_table.border_title = f"Matching IP Prefixes ({count} items found)"


__all__ = ["NavigatorApp", "SelectionList", "RESULTS_COLUMNS"]
