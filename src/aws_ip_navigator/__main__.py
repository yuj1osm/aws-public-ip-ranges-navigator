"""CLI entry point for the AWS Public IP Ranges Navigator.

This module makes the package runnable with ``python -m aws_ip_navigator``. It
deliberately provides no command-line option parsing: any arguments the user
supplies are ignored, so the application always launches with the same default
behavior whether it is started with no arguments or with several
(Requirement 1.1, 1.2). Launching ``NavigatorApp`` triggers the startup fetch
of the AWS IP ranges document before interactive navigation is enabled
(Requirement 1.3).
"""

from __future__ import annotations

from .app import NavigatorApp


def main() -> None:
    """Launch the Navigator, ignoring any command-line arguments.

    ``sys.argv`` is intentionally never read: the application takes no options,
    so a no-argument launch and a launch with arguments behave identically
    (Requirement 1.1, 1.2). Running the app performs the startup fetch and then
    enables navigation, and Textual restores the terminal on teardown
    (Requirement 1.3).
    """
    NavigatorApp().run()


if __name__ == "__main__":
    main()
