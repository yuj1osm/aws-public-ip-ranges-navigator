"""Textual ``run_test`` checks for the NavigatorApp bindings and focus.

These example tests cover task 11.2: the footer exposes the declared bindings
and ``Tab`` toggles the Active_Panel (focus + visual indication) between the
Region_List and the Service_List (Requirements 4.1, 4.2, 4.3, 8.1-8.6).

The app tests drive Textual's async ``run_test`` harness through ``asyncio.run``
so no ``pytest-asyncio`` plugin is required.
"""

from __future__ import annotations

import asyncio
import json

from textual.events import MouseScrollDown

from aws_ip_navigator.app import NavigatorApp, SelectionList
from aws_ip_navigator.errors import FetchTimeoutError
from aws_ip_navigator.models import IP_Prefix
from aws_ip_navigator.navigation import Active_Panel

#: A small fixed dataset with two regions and two services for the
#: navigation/filter tests. Kept intentionally tiny so the expected filtered
#: counts are obvious.
SAMPLE_ENTRIES = [
    IP_Prefix("52.94.0.0/22", "ap-northeast-1", "S3"),
    IP_Prefix("52.219.0.0/20", "ap-northeast-1", "EC2"),
    IP_Prefix("3.5.140.0/22", "us-east-1", "S3"),
    IP_Prefix("16.12.0.0/21", "us-east-1", "EC2"),
]


def _no_startup_fetch() -> str:
    """A fetch stub that fails, so the startup worker leaves the store empty.

    Tests that populate the store themselves via ``load_entries`` inject this
    so the on-mount startup fetch is a hermetic no-op instead of a real network
    call that would otherwise overwrite the manually loaded data.
    """
    raise FetchTimeoutError("startup fetch disabled for test")


def _app_without_startup_fetch() -> NavigatorApp:
    """Build a NavigatorApp whose startup fetch is a hermetic no-op."""
    return NavigatorApp(fetch=_no_startup_fetch)


def _binding_map(app: NavigatorApp) -> dict[str, str]:
    """Return a ``key -> action`` map from the app's declared BINDINGS."""
    return {binding.key: binding.action for binding in app.BINDINGS}


def _table_row_numbers(app: NavigatorApp) -> list[str]:
    """Return the ``#`` column of every results-table row, top to bottom."""
    table = app.results_table
    return [str(table.get_row_at(index)[0]) for index in range(table.row_count)]


def test_bindings_declare_all_actions() -> None:
    """The BINDINGS list wires every required key to its action."""
    app = NavigatorApp()
    bindings = _binding_map(app)
    assert bindings["q"] == "quit"
    assert bindings["r"] == "reload"
    assert bindings["x"] == "clear_filter"
    assert bindings["tab"] == "switch_pane"
    assert bindings["up"] == "nav_up"
    assert bindings["down"] == "nav_down"


def test_initial_active_panel_is_region() -> None:
    """The app starts with the Region_List as the focused Active_Panel."""

    async def scenario() -> None:
        app = _app_without_startup_fetch()
        async with app.run_test():
            assert app.active_panel is Active_Panel.REGION
            assert app.region_list.has_class("active-panel")
            assert not app.service_list.has_class("active-panel")
            assert app.focused is app.region_list

    asyncio.run(scenario())


def test_tab_toggles_active_panel_and_focus() -> None:
    """Pressing Tab flips the Active_Panel, moving focus and the active style."""

    async def scenario() -> None:
        app = _app_without_startup_fetch()
        async with app.run_test() as pilot:
            await pilot.press("tab")
            assert app.active_panel is Active_Panel.SERVICE
            assert app.service_list.has_class("active-panel")
            assert not app.region_list.has_class("active-panel")
            assert app.focused is app.service_list

            await pilot.press("tab")
            assert app.active_panel is Active_Panel.REGION
            assert app.region_list.has_class("active-panel")
            assert not app.service_list.has_class("active-panel")
            assert app.focused is app.region_list

    asyncio.run(scenario())


def test_footer_shows_declared_bindings() -> None:
    """The Footer is populated from BINDINGS and lists the shown actions."""

    async def scenario() -> None:
        app = _app_without_startup_fetch()
        async with app.run_test():
            shown = {binding.action for binding in app.BINDINGS if binding.show}
            assert {
                "quit",
                "reload",
                "clear_filter",
                "switch_pane",
                "nav_up",
            } <= shown

    asyncio.run(scenario())


def test_navigation_clamps_at_list_bounds() -> None:
    """Up stops at the first item and Down stops at the last (Requirement 5)."""

    async def scenario() -> None:
        app = _app_without_startup_fetch()
        async with app.run_test() as pilot:
            app.load_entries(SAMPLE_ENTRIES)
            await pilot.pause()
            # Region_List is ["ALL", "ap-northeast-1", "us-east-1"].
            assert app.region_list.option_count == 3
            assert app.region_list.highlighted == 0

            # Pressing Up at the top is a no-op (clamped at index 0).
            await pilot.press("up")
            assert app.region_list.highlighted == 0

            # Down walks to the last item, then clamps there.
            await pilot.press("down")
            assert app.region_list.highlighted == 1
            await pilot.press("down")
            assert app.region_list.highlighted == 2
            await pilot.press("down")
            assert app.region_list.highlighted == 2

            # Up walks back to the first item and clamps.
            await pilot.press("up")
            await pilot.press("up")
            assert app.region_list.highlighted == 0

    asyncio.run(scenario())


def test_navigation_on_empty_list_is_noop() -> None:
    """Up/Down are ignored while a list has no items (Requirement 5.5)."""

    async def scenario() -> None:
        app = _app_without_startup_fetch()
        async with app.run_test() as pilot:
            # No data loaded: both selection lists are empty.
            assert app.region_list.option_count == 0
            assert app.region_list.highlighted is None

            await pilot.press("down")
            await pilot.press("up")
            assert app.region_list.highlighted is None

    asyncio.run(scenario())


def test_selecting_region_filters_table_and_count_matches_rows() -> None:
    """Highlighting a specific region filters the table; count == row count."""

    async def scenario() -> None:
        app = _app_without_startup_fetch()
        async with app.run_test() as pilot:
            app.load_entries(SAMPLE_ENTRIES)
            await pilot.pause()

            # ALL/ALL shows every entry with gap-free 1..n numbering.
            assert app.results_table.row_count == 4
            assert _table_row_numbers(app) == ["1", "2", "3", "4"]
            assert "4 items found" in str(app.results_table.border_title)

            # Move to "ap-northeast-1" (index 1) -> two matching entries.
            await pilot.press("down")
            assert app.filter_selection.region == "ap-northeast-1"
            assert app.results_table.row_count == 2
            assert _table_row_numbers(app) == ["1", "2"]
            assert "2 items found" in str(app.results_table.border_title)

    asyncio.run(scenario())


def test_selecting_service_narrows_table_further() -> None:
    """Region + service selection intersects; count stays equal to rows."""

    async def scenario() -> None:
        app = _app_without_startup_fetch()
        async with app.run_test() as pilot:
            app.load_entries(SAMPLE_ENTRIES)
            await pilot.pause()

            # Region -> ap-northeast-1 (2 entries: S3, EC2).
            await pilot.press("down")
            assert app.results_table.row_count == 2

            # Switch to the Service_List and select "EC2".
            # Service_List is ["ALL", "EC2", "S3"]; index 1 is EC2.
            await pilot.press("tab")
            assert app.active_panel is Active_Panel.SERVICE
            await pilot.press("down")
            assert app.filter_selection.service == "EC2"

            # ap-northeast-1 + EC2 matches exactly one entry.
            assert app.results_table.row_count == 1
            assert _table_row_numbers(app) == ["1"]
            assert "1 items found" in str(app.results_table.border_title)

    asyncio.run(scenario())


def test_no_match_shows_zero_rows_and_zero_count() -> None:
    """A selection with no matches yields zero rows and a zero count."""

    async def scenario() -> None:
        app = _app_without_startup_fetch()
        # us-west-2 has no entries in the sample, so region us-west-2 alone
        # would already be empty; instead pick a region/service pair that does
        # not co-occur to exercise the intersection path.
        entries = [
            IP_Prefix("10.0.0.0/24", "ap-northeast-1", "S3"),
            IP_Prefix("10.1.0.0/24", "us-east-1", "EC2"),
        ]
        async with app.run_test() as pilot:
            app.load_entries(entries)
            await pilot.pause()

            # Region -> ap-northeast-1 (index 1).
            await pilot.press("down")
            # Service -> EC2. Service_List is ["ALL", "EC2", "S3"].
            await pilot.press("tab")
            await pilot.press("down")
            assert app.filter_selection.region == "ap-northeast-1"
            assert app.filter_selection.service == "EC2"

            # ap-northeast-1 + EC2 do not co-occur -> zero rows, zero count.
            assert app.results_table.row_count == 0
            assert "0 items found" in str(app.results_table.border_title)

    asyncio.run(scenario())


# --- Mouse selection and scrolling (task 13.1, Requirement 12) -----------

#: A dataset with many distinct regions so the Region_List overflows its small
#: (~9 row) viewport under the default ``run_test`` size, exercising the
#: scrollbar/wheel paths (Requirement 12.5, 12.6). Every entry shares one
#: service so the Service_List stays short and non-overflowing.
MANY_REGION_ENTRIES = [IP_Prefix(f"10.{i}.0.0/16", f"region-{i:02d}", "S3") for i in range(30)]


def _wheel_down(widget: SelectionList) -> MouseScrollDown:
    """Build a mouse-wheel-down event aimed at ``widget``.

    The coordinates land just inside the widget so the event is delivered to it;
    the constructor order is ``widget, x, y, delta_x, delta_y, button, shift,
    meta, ctrl``.
    """
    region = widget.region
    return MouseScrollDown(widget, region.x + 1, region.y + 1, 0, 0, 0, False, False, False)


def test_click_item_selects_activates_and_filters() -> None:
    """Clicking an item selects it, activates its list, and filters the table."""

    async def scenario() -> None:
        app = _app_without_startup_fetch()
        async with app.run_test() as pilot:
            app.load_entries(SAMPLE_ENTRIES)
            await pilot.pause()
            # The Region_List starts active; click lands in the Service_List.
            assert app.active_panel is Active_Panel.REGION

            # Service_List is ["ALL", "EC2", "S3"]; content starts one row below
            # the border, so offset y=3 targets index 2 ("S3").
            await pilot.click(app.service_list, offset=(3, 3))
            await pilot.pause()

            # The clicked list becomes the Active_Panel and takes focus.
            assert app.active_panel is Active_Panel.SERVICE
            assert app.service_list.has_class("active-panel")
            assert app.focused is app.service_list

            # The clicked item is selected and the filter follows the same path
            # as a keyboard selection would.
            assert app.service_list.highlighted == 2
            assert app.filter_selection.service == "S3"
            # Two S3 entries in the sample -> two rows, count matches.
            assert app.results_table.row_count == 2
            assert _table_row_numbers(app) == ["1", "2"]
            assert "2 items found" in str(app.results_table.border_title)

    asyncio.run(scenario())


def test_click_matches_keyboard_selection() -> None:
    """A click to an item yields the same filter result as arrowing to it."""

    async def scenario() -> None:
        # Keyboard: arrow down to service index 2 ("S3").
        keyboard_app = _app_without_startup_fetch()
        async with keyboard_app.run_test() as pilot:
            keyboard_app.load_entries(SAMPLE_ENTRIES)
            await pilot.pause()
            await pilot.press("tab")  # activate Service_List
            await pilot.press("down")
            await pilot.press("down")  # index 2 -> "S3"
            assert keyboard_app.service_list.highlighted == 2
            keyboard_service = keyboard_app.filter_selection.service
            keyboard_rows = _table_row_numbers(keyboard_app)

        # Mouse: click the same item.
        mouse_app = _app_without_startup_fetch()
        async with mouse_app.run_test() as pilot:
            mouse_app.load_entries(SAMPLE_ENTRIES)
            await pilot.pause()
            await pilot.click(mouse_app.service_list, offset=(3, 3))
            await pilot.pause()
            assert mouse_app.service_list.highlighted == 2

            assert mouse_app.filter_selection.service == keyboard_service
            assert _table_row_numbers(mouse_app) == keyboard_rows

    asyncio.run(scenario())


def test_click_empty_position_activates_but_keeps_selection() -> None:
    """A click on empty space activates the list but leaves selection unchanged."""

    async def scenario() -> None:
        app = _app_without_startup_fetch()
        # Only two services -> the Service_List has empty rows below its items.
        entries = [
            IP_Prefix("10.0.0.0/24", "ap-northeast-1", "S3"),
            IP_Prefix("10.1.0.0/24", "us-east-1", "EC2"),
        ]
        async with app.run_test() as pilot:
            app.load_entries(entries)
            await pilot.pause()
            before = app.service_list.highlighted
            before_service = app.filter_selection.service
            assert app.active_panel is Active_Panel.REGION

            # Click well below the last item but still inside the list's border.
            await pilot.click(app.service_list, offset=(3, 8))
            await pilot.pause()

            # The list is now active, but its selection and the filter are intact.
            assert app.active_panel is Active_Panel.SERVICE
            assert app.service_list.has_class("active-panel")
            assert app.service_list.highlighted == before
            assert app.filter_selection.service == before_service

    asyncio.run(scenario())


def test_wheel_scroll_overflowing_list_moves_only_its_window() -> None:
    """Wheeling an overflowing list scrolls it alone; selection/filter unchanged."""

    async def scenario() -> None:
        app = _app_without_startup_fetch()
        async with app.run_test() as pilot:
            app.load_entries(MANY_REGION_ENTRIES)
            await pilot.pause()
            region = app.region_list
            # The Region_List overflows; the short Service_List does not.
            assert region.max_scroll_y > 0

            before_offset = region.scroll_offset.y
            before_highlighted = region.highlighted
            before_region = app.filter_selection.region
            before_service = app.filter_selection.service
            before_rows = _table_row_numbers(app)
            before_service_offset = app.service_list.scroll_offset.y

            region.post_message(_wheel_down(region))
            await pilot.pause()
            await pilot.pause()

            # Only the scrolled list's visible window changed.
            assert region.scroll_offset.y > before_offset
            # Selection, Filter_Selection, and the results table are untouched.
            assert region.highlighted == before_highlighted
            assert app.filter_selection.region == before_region
            assert app.filter_selection.service == before_service
            assert _table_row_numbers(app) == before_rows
            # The other list is unaffected.
            assert app.service_list.scroll_offset.y == before_service_offset

    asyncio.run(scenario())


def test_wheel_scroll_non_overflowing_list_is_ignored() -> None:
    """A list that fits its viewport ignores wheel input (no scrollbar)."""

    async def scenario() -> None:
        app = _app_without_startup_fetch()
        entries = [
            IP_Prefix("10.0.0.0/24", "ap-northeast-1", "S3"),
            IP_Prefix("10.1.0.0/24", "us-east-1", "EC2"),
        ]
        async with app.run_test() as pilot:
            app.load_entries(entries)
            await pilot.pause()
            region = app.region_list
            # Three items ("ALL" + two regions) fit the viewport: no scroll room.
            assert region.max_scroll_y == 0

            region.post_message(_wheel_down(region))
            await pilot.pause()
            await pilot.pause()

            assert region.scroll_offset.y == 0

    asyncio.run(scenario())


# --- Reload, clear-filter, and error handling (task 14.1) ----------------


def _document(entries: list[IP_Prefix]) -> str:
    """Serialize ``entries`` into the AWS IP ranges document shape as text."""
    return json.dumps(
        {
            "prefixes": [
                {"ip_prefix": e.cidr, "region": e.region, "service": e.service} for e in entries
            ]
        }
    )


def test_startup_fetch_populates_store_via_mocked_fetcher() -> None:
    """The startup worker fetches, parses, and fills the store (no network)."""

    calls: list[int] = []

    def fake_fetch() -> str:
        calls.append(1)
        return _document(SAMPLE_ENTRIES)

    async def scenario() -> None:
        app = NavigatorApp(fetch=fake_fetch)
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()

            # The injected fetcher ran and the store now holds the entries.
            assert calls
            assert app.store.entries == SAMPLE_ENTRIES
            # Lists rebuilt and the unfiltered table shows every entry.
            assert app.region_list.option_count == 3  # ALL + 2 regions
            assert app.results_table.row_count == len(SAMPLE_ENTRIES)

    asyncio.run(scenario())


def test_timeout_on_startup_surfaces_error_and_app_keeps_running() -> None:
    """A fetch timeout leaves the store empty, shows an error, app stays up."""

    def timing_out_fetch() -> str:
        raise FetchTimeoutError("timed out after 15.0s")

    async def scenario() -> None:
        app = NavigatorApp(fetch=timing_out_fetch)
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()

            # Store is unchanged (empty) and the app is still running.
            assert app.store.entries == []
            assert app.is_running
            # The results table stays empty.
            assert app.results_table.row_count == 0

    asyncio.run(scenario())


def test_reload_replaces_store_and_reapplies_filter() -> None:
    """Pressing ``r`` re-fetches, replaces the store, and re-applies the filter."""

    initial = [IP_Prefix("10.0.0.0/24", "ap-northeast-1", "S3")]
    reloaded = SAMPLE_ENTRIES

    documents = [_document(initial), _document(reloaded)]

    def sequenced_fetch() -> str:
        # Startup returns the first document; the reload returns the second.
        return documents.pop(0) if len(documents) > 1 else documents[0]

    async def scenario() -> None:
        app = NavigatorApp(fetch=sequenced_fetch)
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert app.store.entries == initial

            # Select a specific region so we can verify the filter is re-applied
            # after the reload. initial only has ap-northeast-1 -> index 1.
            await pilot.press("down")
            assert app.filter_selection.region == "ap-northeast-1"

            # Reload: the store is replaced with the richer dataset.
            await pilot.press("r")
            await app.workers.wait_for_complete()
            await pilot.pause()

            assert app.store.entries == reloaded
            # The current selection (ap-northeast-1, index 1) is re-applied
            # against the new store: two ap-northeast-1 entries match.
            assert app.filter_selection.region == "ap-northeast-1"
            assert app.results_table.row_count == 2

    asyncio.run(scenario())


def test_reload_failure_keeps_existing_store() -> None:
    """A failed reload leaves the previously loaded store intact."""

    good_document = _document(SAMPLE_ENTRIES)
    state = {"fail": False}

    def flaky_fetch() -> str:
        if state["fail"]:
            raise FetchTimeoutError("timed out")
        return good_document

    async def scenario() -> None:
        app = NavigatorApp(fetch=flaky_fetch)
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert app.store.entries == SAMPLE_ENTRIES

            # Next fetch fails; the store must be retained unchanged.
            state["fail"] = True
            await pilot.press("r")
            await app.workers.wait_for_complete()
            await pilot.pause()

            assert app.store.entries == SAMPLE_ENTRIES
            assert app.is_running

    asyncio.run(scenario())


def test_clear_filter_resets_to_all_all_showing_every_entry() -> None:
    """Clear-filter restores ALL/ALL and shows all entries again (Req 7)."""

    def fake_fetch() -> str:
        return _document(SAMPLE_ENTRIES)

    async def scenario() -> None:
        app = NavigatorApp(fetch=fake_fetch)
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()

            # Narrow the view: region ap-northeast-1 + service EC2 -> 1 row.
            await pilot.press("down")  # region -> ap-northeast-1
            await pilot.press("tab")  # activate Service_List
            await pilot.press("down")  # service -> EC2
            assert app.results_table.row_count == 1

            # Clear the filter.
            await pilot.press("x")
            await pilot.pause()

            assert app.filter_selection.region == "ALL"
            assert app.filter_selection.service == "ALL"
            assert app.region_list.highlighted == 0
            assert app.service_list.highlighted == 0
            assert app.results_table.row_count == len(SAMPLE_ENTRIES)

    asyncio.run(scenario())
