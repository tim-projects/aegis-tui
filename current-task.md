# Current Task: Implement Arrow Key Navigation for OTP entries

## Objective
Enhance the interactive OTP selection in `aegis-tui.py` by implementing a Text User Interface (TUI) with arrow key navigation for selecting entries. The user will be able to move a cursor up and down the full list, type characters to move the cursor to the first matching item, and press Enter to reveal the OTP for the selected entry.

## Status
We are now implementing a `ncurses`-based TUI to provide a more intuitive selection mechanism. Vault generation and decryption are successful, and the `aegis-tui.py` application runs without runtime errors (aside from the expected `termios.error` in this environment).

## Findings & Mitigations
*   **`_curses.error: cbreak() returned ERR` and `_curses.error: nocbreak() returned ERR`:**
    *   **Finding:** These errors occurred during automated execution of `aegis-tui.py`, indicating issues with `cbreak` mode setup and teardown within `curses.wrapper`.
    *   **Mitigation:** This is an environmental limitation of the non-interactive shell used for automated execution, as `curses` applications require a fully interactive terminal. This issue cannot be resolved by code changes within the application or tests.
*   **`termios.error: (25, 'Inappropriate ioctl for device')`:**
    *   **Finding:** Occurred in non-interactive environments when `aegis-tui.py` attempted interactive terminal operations.
    *   **Mitigation:** Acknowledged as an expected environmental limitation; no code changes were made.
*   **`Killed` error during `pytest` execution:**
    *   **Finding:** Tests were crashing due to excessive memory usage with `MagicMock(spec=...)`.
    *   **Mitigation:** Removed `spec=Entry` and `spec=OTP` from `MagicMock` instances in unit tests.
*   **`io.UnsupportedOperation: redirected stdin is pseudofile, has no fileno()` in unit tests:**
    *   **Finding:** `select.select` calls failed when `sys.stdin` was mocked as `StringIO`.
    *   **Mitigation:** Patched `select.select` in unit tests to simulate input availability.
*   **OTP entry list overlapping top border in search mode:**
    *   **Finding:** The list of TOTP entries in search mode was not correctly positioned within the display box and overlapped the top border.
    *   **Mitigation:** Adjusted the starting `row` for content display within the main box to `header_row_offset + 1`, ensuring the content starts one row below the top border of the box. **(Resolved)**
*   **Excessive screen redraws:**
    *   **Finding:** The entire screen was being redrawn continuously in both search and reveal modes, leading to potential performance issues or visual artifacts.
    *   **Mitigation:**
        *   **Search Mode (`cli_main`):** Implemented a `needs_redraw` boolean flag. This flag is set to `True` initially and whenever an input event (key press, search term change, selection change, group mode toggle) occurs or a terminal resize is detected (`curses.KEY_RESIZE`). The entire display logic (from `stdscr.clear()` to `stdscr.refresh()`) is now wrapped in an `if needs_redraw:` block, ensuring redrawing only happens when necessary. After `stdscr.refresh()`, `needs_redraw` is reset to `False`.
        *   **Reveal Mode (`_run_reveal_mode`):** Optimized redraws to only update the "Time to Next" countdown. Instead of `stdscr.clear()` in every loop iteration, the function now performs an initial full redraw of the reveal box and static content. Subsequent iterations only clear and redraw the specific line where the countdown timer is displayed. A full redraw of the reveal mode is triggered only on `curses.KEY_RESIZE`. **(Resolved)**

## Completed Tasks & Mitigations
*   **`NameError: name 'group_names' is not defined`:**
    *   **Finding:** A `NameError` occurred because `group_names` was defined inside the `while True` loop, but was being accessed before the loop in the initial `all_entries` preparation blocks.
    *   **Mitigation:** Moved the initialization of `otps = get_otps(vault_data)` and `group_names = {group.uuid: group.name for group in vault_data.db.groups}` to directly after successful vault decryption, ensuring they are available in the correct scope when `all_entries` is populated. This also optimizes performance by avoiding redundant recalculations in each loop iteration. **(Resolved)**
*   **Complex Column Width Distribution:**
    *   **Finding:** The initial logic for distributing column widths proportionally was overly complex and led to incorrect truncation behavior.
    *   **Mitigation:** Reverted to a simpler, more robust method that calculates maximum content lengths, determines available display width, and then caps the lengths to prevent truncation while ensuring headers fit.
*   **`StopIteration` errors in tests due to input simulation:**
    *   **Finding:** Tests failed with `StopIteration` errors because the `getch.side_effect` iterator was exhausted prematurely or input was not correctly simulated.
    *   **Mitigation:** Refactored `mock_curses_wrapper` to correctly accept `getch_side_effects` and use an iterator, ensuring `select.select` is mocked to indicate input availability for a sufficient duration. Individual tests were updated to pass `getch_side_effects` to `mock_curses_wrapper` directly.
*   **`TypeError: cli_main() got an unexpected keyword argument 'getch_side_effects'` in tests:**
    *   **Finding:** Passing `getch_side_effects` as a keyword argument to `mock_curses_wrapper` resulted in it being incorrectly passed to `cli_main_func`, which does not expect it.
    *   **Mitigation:** Modified `mock_curses_wrapper` to explicitly filter out `getch_side_effects` from the `kwargs` before passing them to `cli_main_func`.
*   **`AssertionError: 'Test OTP 1' not found in '\nExiting.\n'` in tests:**
    *   **Finding:** Tests checking for revealed OTP content failed because the `sys.stdout` capture was exiting prematurely, before the reveal mode could fully render the OTP.
    *   **Mitigation:** Switched test assertions from capturing `sys.stdout` to inspecting `mock_stdscr_instance.addstr.call_args_list` directly, which captures all `curses.addstr` calls and allows for more precise verification of TUI content, including the revealed OTP. Also, adjusted `getch_side_effects` to ensure the reveal mode has enough `curses.ERR` (idle) calls to fully display.
*   **`IndentationError` in `aegis-tui.py` due to reveal mode refactoring:**
    *   **Finding:** After extracting the reveal mode into `_run_reveal_mode`, multiple `IndentationError`s occurred in the `cli_main` function's main loop, particularly in the `else` block and nested statements.
    *   **Mitigation:** Systematically corrected all `IndentationError`s by adjusting the indentation of the affected code blocks and statements in `aegis-tui.py` to ensure proper Python syntax.
*   **`UnboundLocalError: cannot access local variable 'char'`:**
    *   **Finding:** The `char` variable was being used in a conditional statement before it was guaranteed to be assigned a value from `stdscr.getch()`.
    *   **Mitigation:** Initialized `char = curses.ERR` at the beginning of the `cli_main` function to ensure it always has a value.
*   **`KeyError: 'index'`:**
    *   **Finding:** The `item` dictionaries within `display_data` (derived from `all_entries`) were missing the `'index'` key, leading to a `KeyError` when attempting to access `item["index"]`.
    *   **Mitigation:** Modified the population of `all_entries` to include an `'index'` key for each entry, using `enumerate` to assign the original order index.
*   **`_curses.error: init_pair() can't be called before start_color()`:**
    *   **Finding:** The error occurred because `curses.A_BOLD` was incorrectly included in the `curses.init_pair()` call, which expects only color numbers.
    *   **Mitigation:** Removed `curses.A_BOLD` from `curses.init_pair(2, ...)` and ensured `curses.A_BOLD` is applied separately as an attribute when defining `BOLD_WHITE_COLOR` for use with `addstr`.
*   **`_curses.error: must call initscr() first` in tests:**
    *   **Finding:** Tests failed because `cli_main` was calling `curses` functions without `initscr()` being initialized in the mocked environment.
    *   **Mitigation:** Added mocks for `curses` module functions (`curses.curs_set`, `curses.start_color`, `curses.init_pair`, `curses.use_default_colors`, `curses.has_colors`) in the test setup to prevent this error.
*   **`SyntaxError: invalid syntax` in `tests/test_aegis_cli.py` (line 145 and others):**
    *   **Finding:** A `SyntaxError` occurred due to incorrect placement/indentation of `prompt_string_prefix` after a `pass` statement, and the `output = mock_stdout.getvalue()` line was missing or misplaced.
    *   **Mitigation:** Corrected the indentation and placement of `prompt_string_prefix` and re-introduced the `output = mock_stdout.getvalue()` line at the correct level within all test methods.
*   **`TypeError: cli_main() missing 1 required positional argument: 'stdscr'` in tests:**
    *   **Finding:** Tests failed because `aegis_cli.cli_main()` was called directly, but it expects a `stdscr` argument from `curses.wrapper`.
    *   **Mitigation:** Modified test methods to call `mock_curses_wrapper(aegis_cli.cli_main)` to correctly pass the mocked `stdscr` object.
*   **Multiple `IndentationError`s in `aegis-tui.py` (lines 276, 331, 326, 351, 354, 358, 361):**
    *   **Finding:** Various indentation issues throughout the `cli_main` function, including incorrect alignment of blocks and a stray `row += 1` statement.
    *   **Mitigation:** Systematically corrected all reported `IndentationError`s by adjusting the indentation of affected code blocks and statements.
*   **`TypeError: string indices must be integers, not 'str'` during vault decryption:**
    *   **Finding:** Vault decryption failed due to a structural mismatch in `generate_test_vault.py` and incorrect encoding for cryptographic fields.
    *   **Mitigation:** Updated dataclass definitions and encoding/decoding methods in `generate_test_vault.py` to align with `vault.py`, and regenerated `test_vault.json`.
*   **`NameError: name 'display_data' is not defined. Did you mean: 'display_list'?` (multiple occurrences):**
    *   **Finding:** In the reveal mode, `display_data` was referenced instead of `display_list`.
    *   **Mitigation:** Replaced all instances of `display_data` with `display_list` in the reveal mode logic.
*   **`AssertionError: 'Nomatch' not found in ...` (incorrect reveal behavior):**
    *   **Finding:** The application was incorrectly transitioning to "reveal" mode when the search term was empty and only one OTP entry existed, even if that entry's didn't match.
    *   **Mitigation:** Modified the condition for entering "reveal" mode to require a non-empty `search_term` in addition to having a single matching entry.
*   **Rapid blinking of prompt and filtering issues:**
    *   **Finding:** Rapid screen clearing and unresponsive filtering due to fast loop cycles and `search_term` not updating before display.
    *   **Mitigation:** Reordered input processing, ensuring `search_term` update before display, and added `time.sleep(0.1)` in search mode for stability.
*   **Arrow key highlighting and general `ncurses` TUI issues:**
    *   **Finding:** Double highlighting, screen blinking, disappearing list, limited OTP reveal duration, and non-standard color theme.
    *   **Mitigation:** Removed `stdscr.timeout(100)` to make `stdscr.getch()` blocking, refined `selected_row` management, modified OTP reveal to persist until `ESC`, used `curses.use_default_colors()`, and defined a new `HIGHLIGHT_COLOR`.
*   **Group Filtering Implementation:**
    *   **Progress:** Initial implementation for group filtering via Ctrl+G is complete.
    *   **Fixed:**
        *   Corrected `NameError: name 'display_data' is not defined` (multiple occurrences).
        *   Added "All OTPs" option to group selection, allowing users to clear the group filter.
        *   Resolved issues where the filtered group list lacked a highlighted selection and OTPs were unexpectedly revealed, by ensuring `revealed_otps` is cleared on mode change and group selection, and explicitly setting `current_mode = "search"` after group selection.
        *   Implemented dark blue border highlighting for the revealed OTP code.
*   **Border box for OTP list, group list, and reveal mode:**
    *   **Progress:** The border box is now manually drawn and includes minimum dimension checks.
    *   **Fixed:**
        *   Previously used `stdscr.box()` resulted in `TypeError`. The border is now manually drawn using `stdscr.addch()`, `stdscr.hline()`, and `stdscr.vline()` with ACS characters.
        *   Ensured `box_height` and `box_width` for the main display and `reveal_box_height` and `reveal_box_width` for the reveal mode are at least 2 to prevent drawing issues in very small terminal dimensions.
        *   The border drawing logic was moved inside the `reveal` mode's loop and its content positioning was adjusted to use the calculated box coordinates.
*   **`TypeError: 'PyTOTP' object is not subscriptable` / `AttributeError: 'PyHOTP' object has no attribute 'uuid'` (Incorrect item revealed):**
    *   **Finding:** The `entry_to_reveal` was inconsistently treated as either a dictionary or an `OtpEntry` object, leading to `TypeError` or `AttributeError` during revelation.
    *   **Mitigation:** Consolidated the logic: `entry_to_reveal` is now consistently the dictionary representation of the entry (from `all_entries`), allowing `entry_to_reveal["uuid"]` access. The actual `OTP` object is retrieved from the `otps` dictionary (using `otps[entry_to_reveal["uuid"]]`) only when its `string()` method is needed for display or copying.
*   **`Reveal always selecting entry with ID 42 no matter the selection` (Incorrect item revealed in reveal mode, part 1):**
    *   **Finding:** Even after previous fixes, the dedicated "reveal mode" displayed details for a fixed entry (ID 42) or an outdated `item` reference, rather than the user's selected entry.
    *   **Mitigation:** Modified the reveal mode's display logic to consistently use the `entry_to_reveal` dictionary (which holds the correctly selected item's details) for all display elements, including the header and individual field values. This ensures that the visually selected entry's information is accurately presented.
*   **`Selected_row mismatch for navigation` (Incorrect item revealed in reveal mode, part 2):**
    *   **Finding:** The `selected_row` variable in `search` mode was incorrectly updated based on `len(all_entries)` instead of `len(display_list)`, causing an index mismatch for item revelation.
    *   **Mitigation:** Corrected all `selected_row` updates in `search` mode to consistently use `len(display_list)`, synchronizing visual selection with internal indexing.
*   **`Reveal mode broken; pressing Enter shows code on search screen, reveal mode never shown` (Incorrect state transition):**
    *   **Finding:** The main `cli_main` loop's order of operations caused display rendering before input processing, leading to the search screen being redrawn even after `current_mode` was set to "reveal".
    *   **Mitigation:** Restructured the `cli_main` loop to process all input and mode changes *before* rendering any display. If `current_mode` is set to "reveal", the main loop's display logic is bypassed, and the dedicated `reveal` mode's inner `while True` loop is entered directly.
*   **Resolved `SyntaxError` and duplicate display logic:**
    *   **Finding:** Multiple, inadvertently introduced duplicate blocks of display logic within the `cli_main` loop during previous refactoring caused `SyntaxError`s and incorrect UI rendering.
    *   **Mitigation:** These redundant and malformed code sections have been systematically identified and removed, ensuring correct program flow and display.
*   **Graceful Exit from Reveal Mode:**
    *   **Finding:** The application would not exit correctly from the main loop after `_run_reveal_mode` returned `running = False`.
    *   **Mitigation:** Implemented `if not running: break` after `_run_reveal_mode` call in `cli_main` to ensure the main application loop terminates when `_run_reveal_mode` signals an exit, preventing unintended infinite loops or hanging behavior.
*   **Removed temporary debug prints:**
    *   **Finding:** Temporary `print` statements were added for debugging purposes.
    *   **Mitigation:** All temporary debug `print` statements from `aegis-tui.py` were removed.
*   **Initial Mode and `stdscr.nodelay` State:**
    *   **Finding:** The application was inadvertently starting in reveal mode because `stdscr.getch()` in `cli_main` was blocking (waiting for input) and `selected_row` would default to `0` if entries existed. Also, `stdscr.nodelay(True)` set in `_run_reveal_mode` was not being reset, affecting the main loop.
    *   **Mitigation:** Ensured `stdscr.nodelay(False)` is called upon exiting `_run_reveal_mode` to restore the blocking `getch()` behavior in `cli_main`. This, combined with the normal `KEY_ENTER` logic, prevents automatic entry into reveal mode on startup. Moved `stdscr.nodelay(True)` to the beginning of `cli_main` for consistent non-blocking input, and added `time.sleep(0.1)` in the main loop's idle state. Also, cleared the input buffer after vault decryption.
*   **Incorrect `Time to Next` display in Reveal Mode:**
    *   **Finding:** The countdown timer in reveal mode was reported to be displaying values in milliseconds instead of seconds, resulting in unexpectedly large numbers. (Upon inspection of `aegis_core.py`, `get_ttn` *does* return milliseconds, so the division by 1000 in `aegis-tui.py` is correct for displaying seconds.)
    *   **Mitigation:** Modified the `display_field` call for "Time to Next" in `_run_reveal_mode` to divide the value returned by `get_ttn_func()` by 1000, ensuring the timer is displayed in seconds. Reduced `time.sleep` in reveal mode to 0.01s for responsiveness.
*   **`IndentationError` in `aegis-tui.py`:**
    *   **Finding:** An `IndentationError` at line 400 (`if group_selection_mode:`) was caused by incorrectly indented input handling blocks after `max_rows, max_cols = stdscr.getmaxyx()`.
    *   **Mitigation:** Removed the duplicated and incorrectly indented input handling blocks and re-inserted them correctly within the `if char != curses.ERR:` block, after the `curses.KEY_RESIZE` handling.
*   **Extra Enter to enter Search Mode after Password:**
    *   **Finding:** After successfully entering the vault password, the user had to press Enter again to proceed to the main search interface.
    *   **Mitigation:** Removed the `stdscr.addstr` and `stdscr.refresh()` calls immediately following "Vault decrypted successfully.", allowing direct transition to the search mode after password entry. Added `stdscr.addstr` for initial vault path messages after password is entered. Updated the `_run_reveal_mode` to ensure `stdscr.nodelay(True)` (not `False`) is the state of `cli_main` when returning from `_run_reveal_mode`.
*   **Blank screen and incorrect mode transition after ESC in Reveal Mode:**
    *   **Finding:** Pressing ESC in reveal mode resulted in a blank screen, and pressing Enter then returned to reveal mode, rather than transitioning to search mode.
    *   **Mitigation:** The display logic for the `cli_main` loop was incomplete or missing after previous modifications. The full rendering code for headers, the main box, OTP/group list display, and the search prompt has been reconstructed and re-inserted, ensuring the search screen is properly drawn after exiting reveal mode. Additionally, it has been confirmed that `_run_reveal_mode` does not incorrectly reset `stdscr.nodelay` to `False` on exit, allowing `cli_main` to maintain its non-blocking input state (`stdscr.nodelay(True)`). **(Resolved)**
*   **`SyntaxError: expected 'except' or 'finally' block`:**
    *   **Finding:** A `SyntaxError` occurred at line 567 (which corresponds to the `argparse.ArgumentParser` definition) because the `except KeyboardInterrupt` block for `cli_main` was missing, and the `argparse` definition was incorrectly indented.
    *   **Mitigation:** Re-added the `except KeyboardInterrupt` block for the `cli_main` function and de-indented the `argparse` parser definition and the `if __name__ == "__main__":` block to the global scope. Also, restored the `print("\nExiting.")` statement within the `except KeyboardInterrupt` block. **(Resolved)**
*   **Unlocking the vault goes to reveal mode not search mode:**
    *   **Finding:** The application was inadvertently starting in reveal mode after vault decryption.
    *   **Mitigation:** This was related to the `stdscr.nodelay` state and input buffer. Clearing the input buffer after decryption and ensuring correct `stdscr.nodelay` state in `cli_main` and `_run_reveal_mode` has resolved this. The application now correctly starts in search mode. **(Resolved)**
*   **Pressing escape in reveal mode doesn't go to search mode:**
    *   **Finding:** Pressing ESC in reveal mode would not correctly transition back to search mode.
    *   **Mitigation:** This was resolved by re-inserting the complete display logic for the `cli_main` loop and ensuring correct `stdscr.nodelay` state management. The application now correctly returns to search mode upon pressing ESC. **(Resolved)**
*   **The reveal mode shows a timer with milliseconds:**
    *   **Finding:** The countdown timer in reveal mode was reported to be displaying values in milliseconds instead of seconds.
    *   **Mitigation:** Verified that `aegis-tui.py` already divides `get_ttn_func()` (which returns milliseconds from `aegis_core.py`) by 1000 when displaying "Time to Next", ensuring the value is shown in seconds. **(Resolved)**

## Findings & Mitigations
*   **Reveal Mode OTP Code Not Refreshing:**
    *   **Finding:** The OTP code displayed in reveal mode does not refresh when the countdown timer runs out, displaying a stale code until the mode is re-entered.
    *   **Mitigation:** Implemented logic within `_run_reveal_mode` to check `get_ttn_func()`. If the time to next OTP is less than or equal to 0, the OTP string is regenerated using `otp_object.string()` and the OTP code line is redrawn on the screen. **(Implemented)**

*   **Column Truncation and Missing Notes Column:**
    *   **Finding:** Columns were not truncating as expected, and the 'Notes' column was sometimes missing from the display, despite available horizontal space.
    *   **Mitigation:** The `fixed_otp_display_width` calculation was corrected to `11`. Further, the column width allocation logic was revised. Instead of capping all columns proportionally, 'Name', 'Issuer', and 'Group' are now capped by their content length or proportional share, and then all remaining horizontal space is explicitly allocated to the 'Note' column. This ensures the 'Note' column is always visible and utilizes the available width, even if its content is brief or empty. **(Resolved)**

*   **UI Improvement: Highlight First Item on Load:**
    *   **Finding:** When the application loaded in search mode, no item was initially highlighted, leading to a less intuitive user experience.
    *   **Mitigation:** Modified the `selected_row` initialization logic in `cli_main` to set `selected_row = 0` if the `display_list` is not empty when the application starts or when `selected_row` would otherwise be -1. This ensures the first item in the list is highlighted immediately, improving UI usability. **(Resolved)**

*   **OTP Code and Countdown Timer Display Issues:**
    *   **Finding:** The revealed OTP code displayed as a black block, making it unreadable, and the countdown timer did not turn red when less than 10 seconds remained.
    *   **Mitigation:**
        1.  **OTP Code Visibility:** Changed `REVEAL_HIGHLIGHT_COLOR` from `curses.COLOR_BLACK` on `curses.COLOR_CYAN` to `curses.COLOR_WHITE` on `curses.COLOR_BLUE` to ensure clear readability with a contrasting background.
        2.  **Countdown Timer Color:** Modified the `display_field` function to directly use the `attr_to_use` parameter for all fields, removing conditional overrides. All calls to `display_field` were updated to explicitly pass the correct color attributes: `REVEAL_HIGHLIGHT_COLOR` for the OTP code, `ttn_attr` (which is `RED_TEXT_COLOR` or `NORMAL_TEXT_COLOR` based on time) for the countdown, and `NORMAL_TEXT_COLOR` for other static fields. This ensures proper color application for both the OTP code and the red countdown timer. **(Resolved)**

*   **`NameError: name 'otp_code_display_row' is not defined` in Reveal Mode (re-occurrence):**
    *   **Finding:** Despite previous attempts, the `NameError` persisted during `_run_reveal_mode` when initially revealing an OTP or during a terminal resize, indicating `otp_code_display_row` was still undefined at critical points.
    *   **Mitigation:** Refactored the `display_field` function to return the `row_num + 1` (the next available row). All calls to `display_field` within `_run_reveal_mode` (for both initial display and `curses.KEY_RESIZE` handling) were updated to reassign the returned row number to `display_row` or `display_row_static`. This ensures consistent and correct tracking of row positions and explicit definition of `otp_code_display_row`, `otp_code_display_row_static`, and `ttn_display_row` before their usage. **(Resolved)**

*   **OTP Code Not Refreshing in Reveal Mode (Persistent Issue):**
    *   **Finding:** Despite ensuring correct display row and color, the OTP code still does not update when its countdown timer expires, indicating `otp_object.string()` might be returning a stale value because the `PyTOTP` instance itself is not being refreshed for the new time window.
    *   **Mitigation:** The underlying `PyTOTP` object needs to be regenerated when the timer reaches zero. The plan is to:
        1.  Obtain the original `Entry` object corresponding to `entry_to_reveal["uuid"]` from `vault_data.db.entries` once at the beginning of `_run_reveal_mode`.
        2.  Inside the `while` loop, when `time_to_next_ms <= 0`, regenerate the `otp_object` by calling `otp_object = get_otp(original_entry)`. This will create a fresh OTP instance reflecting the current time window.
        3.  Then, update `new_otp_code = otp_object.string()` and proceed with the existing redraw logic. **(In Progress)**