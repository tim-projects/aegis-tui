# Current Task: Enhanced Clipboard Integration and User Feedback

## Objective
Refine clipboard functionality to include configurable clipboard tools (e.g., for Xorg/Wayland via `config.json`) and display the message "Press <Enter> to copy the OTP code to the clipboard." when an item is revealed. This message should only appear if a clipboard tool is configured.

## Status
- **Refactoring & Blank Screen Fix:** Completed.
- **Scrolling:** Completed.
- **Clipboard Integration:** Pending start.

## Findings & Mitigations
*   **Scrolling Implementation:**
    *   Implemented viewport/window system in `tui_display.py` and `search_mode.py`.
    *   `scroll_offset` tracks the top visible item.
    *   `draw_main_screen` renders only visible items and returns `items_per_page`.
    *   Navigation keys update `scroll_offset` correctly for both OTP list and Group list (including the static "All OTPs" item).