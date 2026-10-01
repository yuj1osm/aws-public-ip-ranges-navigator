# Implementation Plan: AWS Public IP Ranges Navigator

## Overview

This plan builds the application from the pure, testable core outward to the I/O and
presentation layers, matching the layering in the design. The order is:

1. **Project scaffold** — package layout and `pyproject.toml` so tests can run.
2. **Pure domain core** — `errors`, `models`, `parser`, `store`, `filtering`, `navigation` —
   each paired with its Hypothesis property tests (Properties 1–17 that target pure logic).
3. **I/O layer** — `fetcher` with mock-based and timeout tests.
4. **Presentation layer** — `app.py` (`NavigatorApp`): layout, focus/Tab, keyboard navigation,
   mouse click/scroll, filter application, actions (reload/clear/quit), and error display —
   verified with Textual `run_test` and integration tests.
5. **Entry point** — `__main__.py` (args ignored).
6. **Packaging & docs** — finalize `pyproject.toml` and `README.md`.

Each task builds on the previous ones and ends by wiring its output into the growing application,
so no code is left orphaned. Property tests use Hypothesis with `max_examples >= 100` and are
tagged `# Feature: aws-public-ip-ranges-navigator, Property {number}: {property_text}`.

## Tasks

- [x] 1. Set up project scaffold and packaging
  - Create the `src/aws_ip_navigator/` package with an empty-but-present `__init__.py` exposing the package version/public API marker.
  - Create the `tests/` directory mirroring `src/`.
  - Create `pyproject.toml` with project metadata and dependencies `textual`, `hypothesis`, `pytest`; configure the `src/` layout and the `python -m aws_ip_navigator` entry so pytest can import the package.
  - Follow PEP 8 and the project `src/` + `tests/` + `.kiro/specs/` convention.
  - _Requirements: 1.1, 1.3_

- [x] 2. Implement the exception hierarchy
  - [x] 2.1 Create `errors.py` with the `NavigatorError` hierarchy
    - Define `NavigatorError` base and subclasses `FetchError`, `FetchTimeoutError(FetchError)`, `ParseError`, `StructuralParseError(ParseError)`, `MissingPrefixCollectionError(ParseError)`.
    - Add docstrings so callers can branch on the specific type; no bare-except reliance.
    - _Requirements: 2.4, 2.6, 2.7, 11.2, 11.3_

- [x] 3. Implement the data models
  - [x] 3.1 Create `models.py` with `IP_Prefix` and `Filter_Selection`
    - Define `IP_Prefix` as `@dataclass(frozen=True)` with `cidr`, `region`, `service` (immutable, hashable).
    - Define `Filter_Selection` as a mutable `@dataclass` with `region="ALL"`, `service="ALL"` and a `Filter_Selection.initial()` classmethod returning `ALL`/`ALL`.
    - Define the `ALL = "ALL"` sentinel where it belongs for shared use.
    - _Requirements: 2.5, 6.1, 7.1, 11.1_

  - [ ]* 3.2 Write property test for clear-filter reset in `test_models.py`
    - **Property 14: Clear-filter resets to the unfiltered view**
    - **Validates: Requirements 7.1, 7.2**
    - Assert `Filter_Selection.initial()` yields `ALL`/`ALL` for any prior selection (the "all entries" half of P14 is completed in task 6.2 once `filter_entries` exists).
    - Comment tag `# Feature: aws-public-ip-ranges-navigator, Property 14: ...`; `max_examples >= 100`.

- [x] 4. Implement the parser
  - [x] 4.1 Implement `parse_ip_ranges` in `parser.py`
    - Parse `document_text` as JSON; raise `StructuralParseError` when it is not valid JSON or the top level is not an object.
    - Raise `MissingPrefixCollectionError` when the object lacks the `prefixes` collection.
    - For each entry in `prefixes`, map `ip_prefix`/`region`/`service` to `IP_Prefix(cidr, region, service)`; skip entries whose CIDR, region, or service is missing, empty, or blank after trimming; preserve input order.
    - Use specific exceptions only (no bare `except`).
    - _Requirements: 2.5, 2.8, 11.1, 11.2, 11.3, 11.4_

  - [ ]* 4.2 Write property test for parse round-trip in `test_parser.py`
    - **Property 1: Parse round-trip**
    - **Validates: Requirements 2.5, 11.1**
    - Strategy generates lists of valid `IP_Prefix`, serializes to the AWS document shape, parses back, asserts equivalence.
    - Comment tag `# Feature: aws-public-ip-ranges-navigator, Property 1: ...`; `max_examples >= 100`.

  - [ ]* 4.3 Write property test for skipping invalid entries in `test_parser.py`
    - **Property 2: Parse skips invalid entries**
    - **Validates: Requirements 2.8, 11.4**
    - Strategy generates documents mixing valid entries with entries having missing/empty/blank CIDR, region, or service; assert result equals exactly the valid entries in original order.
    - Comment tag `# Feature: aws-public-ip-ranges-navigator, Property 2: ...`; `max_examples >= 100`.

  - [ ]* 4.4 Write property test for structural parse failure in `test_parser.py`
    - **Property 3: Structural parse failure is reported**
    - **Validates: Requirements 11.2**
    - Strategy generates non-JSON text and JSON values that are not objects; assert `StructuralParseError` is raised and no entries are produced.
    - Comment tag `# Feature: aws-public-ip-ranges-navigator, Property 3: ...`; `max_examples >= 100`.

  - [ ]* 4.5 Write property test for missing prefix collection in `test_parser.py`
    - **Property 4: Missing prefix collection is reported**
    - **Validates: Requirements 11.3**
    - Strategy generates valid JSON objects lacking `prefixes`; assert `MissingPrefixCollectionError` is raised, distinct from `StructuralParseError`.
    - Comment tag `# Feature: aws-public-ip-ranges-navigator, Property 4: ...`; `max_examples >= 100`.

- [x] 5. Implement the data store
  - [x] 5.1 Implement `Data_Store` in `store.py`
    - `@dataclass` holding `entries: list[IP_Prefix]`; `replace(new_entries)` swaps contents atomically.
    - `regions()` and `services()` return distinct values sorted (no `ALL`; the presentation layer prepends it).
    - _Requirements: 2.3, 3.1, 3.2, 9.2_

  - [ ]* 5.2 Write property test for selection list derivation in `test_store.py`
    - **Property 5: Selection list derivation**
    - **Validates: Requirements 3.1, 3.2, 9.2**
    - For any store contents, assert `["ALL"] + regions()` (and services) contains `ALL` exactly once, has no duplicates, and equals `ALL` followed by the distinct present values; holds after `replace` (reload rebuild).
    - Comment tag `# Feature: aws-public-ip-ranges-navigator, Property 5: ...`; `max_examples >= 100`.

  - [ ]* 5.3 Write property test for replace semantics in `test_store.py`
    - **Property 12: Successful replace yields exactly the new entries**
    - **Validates: Requirements 2.3**
    - For any initial contents and any new list, assert after `replace` the store equals exactly the new entries with no residue.
    - Comment tag `# Feature: aws-public-ip-ranges-navigator, Property 12: ...`; `max_examples >= 100`.

- [x] 6. Implement the filter logic
  - [x] 6.1 Implement `filter_entries` in `filtering.py`
    - Pure order-preserving predicate: an entry matches when `(region == ALL or entry.region == region)` and `(service == ALL or entry.service == service)`.
    - Return an empty list when nothing matches.
    - _Requirements: 6.1, 6.2, 6.3, 6.6_

  - [ ]* 6.2 Write property test for filter correctness in `test_filtering.py`
    - **Property 6: Filter correctness across ALL and specific selections**
    - **Validates: Requirements 6.1, 6.2, 6.3**
    - Also complete the "reset selection returns all entries" half of **Property 14** here by asserting `filter_entries(entries, ALL, ALL)` equals all entries.
    - Comment tag `# Feature: aws-public-ip-ranges-navigator, Property 6: ...`; `max_examples >= 100`.

  - [ ]* 6.3 Write property test for count equals displayed rows in `test_filtering.py`
    - **Property 7: Count equals displayed rows**
    - **Validates: Requirements 6.5, 6.6**
    - Assert the derived count equals `len(filter_entries(...))` including the zero-match case.
    - Comment tag `# Feature: aws-public-ip-ranges-navigator, Property 7: ...`; `max_examples >= 100`.

  - [ ]* 6.4 Write property test for sequential gap-free row numbering in `test_filtering.py`
    - **Property 8: Sequential gap-free row numbering**
    - **Validates: Requirements 6.4**
    - Build the row model (a pure helper producing `(index, cidr, region, service)`) from a filtered list and assert row numbers are 1..n with no gaps and each row carries the i-th entry's fields.
    - Comment tag `# Feature: aws-public-ip-ranges-navigator, Property 8: ...`; `max_examples >= 100`.

- [x] 7. Checkpoint - Ensure the domain-data core and its property tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement navigation and scroll math
  - [x] 8.1 Implement clamped index and scroll-offset functions in `navigation.py`
    - Pure `move_up`/`move_down` (clamp at ends; empty list is a no-op) returning the new index within valid range.
    - Pure `scroll_offset(list_length, viewport_height, selected_index)` satisfying `offset <= index < offset + viewport_height` and staying within valid bounds.
    - Pure scroll-only helper that changes offset by a wheel amount within valid range without touching the selected index.
    - Pure Tab toggle helper for the active-panel state (used by the app).
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 4.1, 4.2, 12.5, 12.7_

  - [ ]* 8.2 Write property test for clamped navigation in `test_navigation.py`
    - **Property 9: Clamped navigation within bounds**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**
    - Comment tag `# Feature: aws-public-ip-ranges-navigator, Property 9: ...`; `max_examples >= 100`.

  - [ ]* 8.3 Write property test for scroll visibility in `test_navigation.py`
    - **Property 10: Scroll keeps the selection visible**
    - **Validates: Requirements 5.6**
    - Comment tag `# Feature: aws-public-ip-ranges-navigator, Property 10: ...`; `max_examples >= 100`.

  - [ ]* 8.4 Write property test for Tab toggle in `test_navigation.py`
    - **Property 11: Exactly one active panel and Tab toggles it**
    - **Validates: Requirements 4.1, 4.2**
    - Assert exactly one active panel after each toggle; even Tab count returns to start, odd count lands on the other.
    - Comment tag `# Feature: aws-public-ip-ranges-navigator, Property 11: ...`; `max_examples >= 100`.

  - [ ]* 8.5 Write property test for scroll invariance in `test_navigation.py`
    - **Property 17: Scrolling leaves the selection invariant**
    - **Validates: Requirements 12.5, 12.7**
    - For any length, viewport, index, and scroll amount, assert a scroll-only op changes only the offset (within range) and leaves the selected index unchanged.
    - Comment tag `# Feature: aws-public-ip-ranges-navigator, Property 17: ...`; `max_examples >= 100`.

- [x] 9. Implement the networking layer
  - [x] 9.1 Implement `fetch_ip_ranges` in `fetcher.py`
    - Retrieve the document over HTTPS using `urllib.request` with an explicit `timeout` (default 15.0s); return the body as text.
    - Acquire the network resource with `with` so it is always released.
    - Raise `FetchTimeoutError` on timeout, `FetchError` on any other retrieval failure; define `Data_Source_URL = "https://ip-ranges.amazonaws.com/ip-ranges.json"` as a module constant.
    - _Requirements: 2.1, 2.2, 2.6_

  - [ ]* 9.2 Write mock-based tests for fetch and timeout in `test_fetcher.py`
    - Mock the HTTP client: assert the fixed HTTPS `Data_Source_URL` is requested and text is returned on success (Requirement 2.1, 2.2).
    - Assert a timeout raises `FetchTimeoutError` and a generic failure raises `FetchError`; no real network call is made.
    - _Requirements: 2.1, 2.2, 2.6_

- [x] 10. Checkpoint - Ensure the pure core plus fetcher tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Build the presentation layer scaffold (NavigatorApp layout, focus, bindings)
  - [x] 11.1 Compose the three-panel layout and footer in `app.py`
    - Create `NavigatorApp(App)` composing a horizontal split: `Selection_Panel` (Region_List above Service_List using `ListView`/`OptionList`) on the left, `Results_Table` (`DataTable` with columns `#`, `IP Prefix (CIDR)`, `Region`, `Service`) on the right, and a docked `Footer`.
    - Render each list vertically (one item per line) with `❯` highlight on the selected item and an independent scrollbar on overflow.
    - _Requirements: 3.3, 3.4, 3.5, 3.6, 3.7, 6.4, 8.1_

  - [x] 11.2 Declare `BINDINGS` and wire focus/Active_Panel with Tab
    - Bind `q`→quit, `r`→reload, `x`→clear_filter, Tab→switch_pane, Up/Down→navigate, so the footer lists all actions.
    - Maintain exactly one focused selection list; Tab toggles it (reusing the navigation toggle helper) and the focused list is visually distinguished.
    - _Requirements: 4.1, 4.2, 4.3, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [ ]* 11.3 Write Textual `run_test` tests for layout and bindings in `test_app.py`
    - Assert the app composes the three panels plus footer, the footer exposes each binding with a visible description, the selected item is highlighted, and the active-panel indicator moves on Tab.
    - _Requirements: 1.1, 3.3, 3.4, 4.3, 8.2, 8.3, 8.4, 8.5, 8.6_

- [x] 12. Wire navigation, filtering, and selection-list rendering into the app
  - [x] 12.1 Implement keyboard navigation and filter application in `app.py`
    - Route Up/Down through the `navigation.py` math (clamp, empty-list no-op, scroll-to-visible); ignore keys on an empty list.
    - Build each list as `["ALL"] + store.regions()` / `["ALL"] + store.services()`; on any selection change recompute `filter_entries` and repopulate the `DataTable`, deriving the header count from the same filtered list so count equals row count, with 1..n gap-free row numbers.
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 3.1, 3.2, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [ ]* 12.2 Write property test for mouse/keyboard selection equivalence in `test_filtering.py`
    - **Property 16: Mouse selection matches keyboard selection**
    - **Validates: Requirements 12.1, 12.2, 12.3**
    - Assert a click-driven selection to a target item feeds the same pure `filter_entries` path and yields the same `Filter_Selection` and filtered result as a keyboard-driven selection to the same item.
    - Comment tag `# Feature: aws-public-ip-ranges-navigator, Property 16: ...`; `max_examples >= 100`.

- [x] 13. Wire mouse click and scroll into the app
  - [x] 13.1 Implement mouse selection and scrolling in `app.py`
    - On a click within a list, select the clicked item, make that list the Active_Panel, and apply the filter through the same path as keyboard selection; a click on an empty position leaves the selection unchanged but still activates that list.
    - Route wheel/scrollbar scrolling through the `navigation.py` scroll-only helper so scrolling one list changes only its visible window, leaving the selected item, `Filter_Selection`, `Results_Table`, and the other list unchanged; a non-overflowing list shows no scrollbar and ignores wheel input.
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7_

  - [ ]* 13.2 Write Textual `run_test` tests for mouse click and scroll in `test_app.py`
    - Assert clicking an item selects it and activates that list; clicking an empty position leaves the selection unchanged but activates the list; an overflowing list shows a scrollbar and scrolls on the wheel independently while a non-overflowing list shows none and ignores the wheel.
    - _Requirements: 12.1, 12.2, 12.4, 12.5, 12.6_

- [x] 14. Wire reload, clear-filter, and quit actions with error display
  - [x] 14.1 Implement `reload`, `clear_filter`, `quit` actions and error handling in `app.py`
    - `action_reload` runs fetch+parse in an async worker (off the UI thread); on success `replace` the store, rebuild both lists, and re-apply the current filter; on `FetchError`/`FetchTimeoutError` show "could not be retrieved" and on `ParseError` or zero parseable entries show "could not be parsed", keeping the store unchanged and the app running.
    - `action_clear_filter` resets `Filter_Selection` to `initial()` and refreshes the table; `action_quit` exits so Textual restores the terminal on teardown; catch only specific exception types.
    - Also perform the startup fetch during app start before enabling navigation.
    - _Requirements: 1.3, 2.3, 2.4, 2.6, 2.7, 7.1, 7.2, 9.1, 9.2, 9.3, 10.1, 10.2_

  - [ ]* 14.2 Write property test for retain-store-on-failure in `test_store.py`
    - **Property 13: Failed fetch or parse retains the store**
    - **Validates: Requirements 2.4, 2.7**
    - Model a reload attempt whose fetch fails/times out or yields <1 entry; assert store contents are identical before and after and a non-fatal error is surfaced.
    - Comment tag `# Feature: aws-public-ip-ranges-navigator, Property 13: ...`; `max_examples >= 100`.

  - [ ]* 14.3 Write integration/lifecycle tests in `test_app.py`
    - Mocked fetcher: assert the fixed HTTPS URL is requested on startup and on `r`, a 15s timeout surfaces the retrieval error while the app stays running, a successful reload replaces the store and re-applies the filter, and pressing `q` exits with the terminal restored (via `run_test`).
    - _Requirements: 2.1, 2.2, 2.6, 9.1, 9.2, 9.3, 10.1, 10.2_

- [x] 15. Implement the CLI entry point
  - [x] 15.1 Implement `__main__.py`
    - Provide the `python -m aws_ip_navigator` entry that ignores any supplied command-line arguments and launches `NavigatorApp`.
    - _Requirements: 1.1, 1.2, 1.3_

  - [ ]* 15.2 Write property test for CLI arguments ignored in `test_app.py`
    - **Property 15: Command-line arguments are ignored**
    - **Validates: Requirements 1.2**
    - For any argument vector, assert the resolved startup behavior equals the no-argument behavior.
    - Comment tag `# Feature: aws-public-ip-ranges-navigator, Property 15: ...`; `max_examples >= 100`.

- [x] 16. Finalize packaging and documentation
  - [x] 16.1 Finalize `pyproject.toml` and write `README.md`
    - Confirm dependencies and the `python -m aws_ip_navigator` run configuration in `pyproject.toml`.
    - Write `README.md` with install and run instructions and a short feature overview (English).
    - _Requirements: 1.1_

- [x] 17. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional test sub-tasks (property, unit, integration) and can be skipped for a faster MVP; core implementation tasks are never optional.
- Property tests are implemented with Hypothesis (`max_examples >= 100`) and tagged with `# Feature: aws-public-ip-ranges-navigator, Property {number}: {property_text}`. Each of Properties 1–17 is a single property test.
- PBT targets are the pure modules: `models`, `parser`, `store`, `filtering`, `navigation`. `fetcher` uses mock-based tests and `app` uses Textual `run_test` and integration tests.
- Property 14 is split across two tasks (3.2 asserts the reset selection; 6.2 asserts the reset yields all entries) because it depends on both `Filter_Selection` and `filter_entries`.
- Each task references the specific requirements and/or design properties it implements for traceability.
- Follows the Python guidelines: PEP 8, frozen dataclasses where noted, the custom exception hierarchy, no bare `except`, and `with`/`try-finally` cleanup.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1"] },
    { "id": 1, "tasks": ["3.1", "9.1"] },
    { "id": 2, "tasks": ["3.2", "4.1", "5.1", "8.1", "9.2"] },
    { "id": 3, "tasks": ["4.2", "4.3", "4.4", "4.5", "5.2", "5.3", "6.1", "8.2", "8.3", "8.4", "8.5"] },
    { "id": 4, "tasks": ["6.2", "6.3", "6.4", "11.1"] },
    { "id": 5, "tasks": ["11.2", "12.1"] },
    { "id": 6, "tasks": ["11.3", "12.2", "13.1"] },
    { "id": 7, "tasks": ["13.2", "14.1"] },
    { "id": 8, "tasks": ["14.2", "14.3", "15.1"] },
    { "id": 9, "tasks": ["15.2", "16.1"] }
  ]
}
```
