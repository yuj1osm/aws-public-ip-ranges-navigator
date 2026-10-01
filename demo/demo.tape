# VHS tape for the AWS Public IP Ranges Navigator demo.
#
# Renders a ~1 minute GIF showing: startup + live fetch, selecting a region
# (ap-northeast-1) and a service (EC2) to narrow the results table, clearing
# the filter, then quitting.
#
# Render with:  vhs demo/demo.tape   (run from the project root)
#
# Note: the number of Down presses assumes the current AWS region/service
# ordering (see the comments below). If AWS adds regions/services the target
# rows shift; adjust the Down counts accordingly.

Output demo/demo.gif

# --- Recording surface -------------------------------------------------------
Set Shell "zsh"
Set FontSize 15
Set Width 1200
Set Height 720
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 90ms
Set PlaybackSpeed 1.0

# --- Launch ------------------------------------------------------------------
# Use the project virtualenv interpreter so the package resolves without an
# activation step.
Type ".venv/bin/python -m aws_ip_navigator"
Sleep 500ms
Enter

# Startup fetch of the live AWS IP ranges document, then the full table renders.
# Hold on the full result (all ~10,528 prefixes) so it is clearly readable.
Sleep 9s

# --- Select a region: ap-northeast-1 (Tokyo) --------------------------------
# Regions list order: 0=ALL, 1=GLOBAL, 2=af-south-1, 3=ap-east-1,
# 4=ap-east-2, 5=ap-northeast-1 -> 5 Down presses. The Regions list is the
# active panel on startup.
Down@900ms 5
Sleep 5s

# --- Switch to the Services list --------------------------------------------
Tab
Sleep 2500ms

# --- Select a service: EC2 --------------------------------------------------
# Services list order: 0=ALL ... 14=EC2 -> 14 Down presses. The results table
# narrows to the ap-northeast-1 + EC2 prefixes as the highlight moves.
Down@550ms 14
Sleep 5s

# Let the filtered result (ap-northeast-1 + EC2, 84 prefixes) sit to read.
Sleep 6s

# --- Clear the filter, back to every prefix ---------------------------------
Type "x"
Sleep 6s

# --- Quit and restore the terminal ------------------------------------------
Type "q"
Sleep 2s
