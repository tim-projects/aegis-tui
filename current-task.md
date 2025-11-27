# Current Task: Implement Arrow Key Navigation for OTP entries

## Objective
Enhance the interactive OTP selection in `aegis-tui.py` by implementing a Text User Interface (TUI) with arrow key navigation for selecting entries. The user will be able to move a cursor up and down the full list, type characters to move the cursor to the first matching item, and press Enter to reveal the OTP for the selected entry.

## Status
We are now implementing a `ncurses`-based TUI to provide a more intuitive selection mechanism. Vault generation and decryption are successful, and the `aegis-tui.py` application runs without runtime errors (aside from the expected `termios.error` in this environment).

## Findings & Mitigations
*   **`_curses.error: cbreak() returned ERR` and `_curses.error: nocbreak() returned ERR`:**
    *   **Finding:** These errors occurred during automated execution of `aegis-tui.py`, indicating issues with `cbreak` mode setup and teardown within `curses.wrapper`.
    *   **Mitigation:** This is an environmental limitation of the non-interactive shell used for automated execution, as `curses` applications require a fully interactive terminal. This issue cannot be resolved by code changes within the application or tests.
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
*   **`termios.error: (25, 'Inappropriate ioctl for device')`:**
    *   **Finding:** Occurred in non-interactive environments when `aegis-tui.py` attempted interactive terminal operations.
    *   **Mitigation:** Acknowledged as an expected environmental limitation; no code changes were made.
*   **`Killed` error during `pytest` execution:**
    *   **Finding:** Tests were crashing due to excessive memory usage with `MagicMock(spec=...)`.
    *   **Mitigation:** Removed `spec=Entry` and `spec=OTP` from `MagicMock` instances in unit tests.
*   **`io.UnsupportedOperation: redirected stdin is pseudofile, has no fileno()` in unit tests:**
    *   **Finding:** `select.select` calls failed when `sys.stdin` was mocked as `StringIO`.
    *   **Mitigation:** Patched `select.select` in unit tests to simulate input availability.
*   **`AssertionError: 'Nomatch' not found in ...` (incorrect reveal behavior):**
    *   **Finding:** The application was incorrectly transitioning to "reveal" mode when the search term was empty and only one OTP entry existed, even if that entry didn't match.
    *   **Mitigation:** Modified the condition for entering "reveal" mode to require a non-empty `search_term` in addition to having a single matching entry.
*   **Rapid blinking of prompt and filtering issues:**
    *   **Finding:** Rapid screen clearing and unresponsive filtering due to fast loop cycles and `search_term` not updating before display.
    *   **Mitigation:** Reordered input processing, ensuring `search_term` update before display, and added `time.sleep(0.1)` in search mode for stability.
*   **Unhighlighted items not using standard terminal colors/bolding:**
    *   **Finding:** Unhighlighted items are currently not using the standard terminal's default colors and are not unbolded as expected, leading to an inconsistent visual appearance.
    *   **Mitigation:** To be implemented.
*   **Arrow key navigation not working in Search Mode:**
    *   **Finding:** Pressing `curses.KEY_UP` and `curses.KEY_DOWN` does not change the `selected_row` as expected, preventing proper navigation of the list.
    *   **Mitigation:** To be implemented.
*   **ESC key not working in Reveal Mode:**
    *   **Finding:** Pressing `ESC` (char 27) in reveal mode does not exit the reveal loop and return to search mode.
    *   **Mitigation:** To be implemented.
*   **Arrow key highlighting and general `ncurses` TUI issues:**
    *   **Finding:** Double highlighting, screen blinking, disappearing list, limited OTP reveal duration, and non-standard color theme.
    *   **Mitigation:** Removed `stdscr.timeout(100)` to make `stdscr.getch()` blocking, refined `selected_row` management, modified OTP reveal to persist until `ESC`, used `curses.use_default_colors()`, and defined a new `HIGHLIGHT_COLOR`.

## Next Steps
1.  Implement group filtering via Ctrl+G.
2.  Update unit tests to cover new TUI interactions (acknowledging environmental limitations).
3.  Clean up: Remove temporary `test_ncurses.py` file (if it still exists).
4.  Commit and push changes.