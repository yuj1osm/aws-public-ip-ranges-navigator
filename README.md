# AWS Public IP Ranges Navigator

A keyboard-driven terminal UI (TUI) for browsing and filtering the public IP
ranges that AWS publishes at
[ip-ranges.amazonaws.com](https://ip-ranges.amazonaws.com/ip-ranges.json).
It fetches the document on launch, lets you narrow the list by Region and
Service, and shows the matching CIDR prefixes in a numbered table.

Built on [Textual](https://textual.textualize.io/).

## Features

- Fetches the AWS IP ranges document over HTTPS on startup (15s timeout).
- Three-panel layout: a Region list and a Service list on the left, a results
  table on the right, and a footer showing the available key actions.
- Filter the results table by Region, by Service, or by both. An `ALL` entry
  at the top of each list means "no filter" on that axis.
- Results table shows gap-free sequential numbering, the CIDR prefix, Region,
  and Service, with a live count of matching prefixes in the panel title.
- Reload the data on demand without leaving the app. Fetch and parse run off
  the UI thread, so the interface stays responsive.
- On any fetch or parse failure the existing data is kept and a non-blocking
  message is shown; the app keeps running.
- Mouse support: click a list to activate it and select an item, and use the
  wheel to scroll a list's visible window.

## Requirements

- Python 3.9 or newer
- [Textual](https://pypi.org/project/textual/) (installed as a dependency)

## Installation

```bash
# From the project root, ideally inside a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install the app (add the dev extras for tests and linting)
pip install -e .
pip install -e ".[dev]"   # optional: hypothesis, pytest, ruff
```

## Usage

Launch the app with:

```bash
python -m aws_ip_navigator
```

The application takes no command-line options. Any arguments you pass are
ignored, so it always starts with the same default behavior.

## Keyboard controls

| Key       | Action                                                        |
| --------- | ------------------------------------------------------------- |
| `↑` / `↓` | Move the selection within the active list                     |
| `Tab`     | Switch the active panel between the Region and Service lists   |
| `x`       | Clear the filter (reset both lists back to `ALL`)             |
| `r`       | Reload the IP ranges document                                 |
| `q`       | Quit                                                          |

The active list is highlighted with an accent border, and the highlighted item
in that list is marked with a `❯` caret. Selecting an item immediately
re-filters the results table.

## Mouse controls

- Click a list to make it the active panel; clicking an item also selects it.
- Clicking empty space in a list activates it without changing the selection.
- The mouse wheel scrolls a list's visible window without changing the
  selection or the results.

## Project layout

```
aws-public-ip-ranges-navigator/
├── src/
│   └── aws_ip_navigator/
│       ├── __main__.py     # CLI entry point (python -m aws_ip_navigator)
│       ├── app.py          # Textual App: layout, key/mouse handling, reload
│       ├── fetcher.py      # HTTPS retrieval of the IP ranges document
│       ├── parser.py       # Parse the document into IP_Prefix entries
│       ├── store.py        # In-memory store + distinct Region/Service values
│       ├── filtering.py    # Pure filter logic + numbered result rows
│       ├── navigation.py   # Pure navigation/scroll math + panel toggle
│       ├── models.py       # IP_Prefix, Filter_Selection, ALL sentinel
│       └── errors.py       # Exception hierarchy (fetch/parse failures)
├── tests/
└── .kiro/specs/
```

The domain layers (`parser`, `store`, `filtering`, `navigation`, `models`) are
pure and side-effect free; `fetcher` owns the network I/O and `app` orchestrates
everything in the presentation layer.

## Development

Run the tests and linter with the dev extras installed:

```bash
pytest
ruff check .
```
