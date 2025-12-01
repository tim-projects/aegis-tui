# Gemini CLI Assistant - Project-Specific Information

## `aegis-tui` Project Context

This project (`aegis-tui`) heavily utilizes the `ncurses` library for its Text User Interface (TUI). This has significant implications for testing and interaction:

*   **`ncurses` in Non-Interactive Environments:** `ncurses` applications *require* an interactive terminal. When running automated tests or executing the application in a non-interactive shell (like a CI/CD pipeline or certain automated environments), `ncurses`-related operations (e.g., `cbreak()`, `nocbreak()`, `addch()`, `getch()`) will likely result in errors such as `_curses.error: cbreak() returned ERR` or `termios.error: (25, 'Inappropriate ioctl for device')`.
*   **Testing `ncurses` Applications:** Directly testing the visual output and interactive input of `ncurses` applications with standard unit testing frameworks (like `pytest`) is challenging and often impractical without a fully mocked `curses` environment.
    *   **Limitation:** It is not feasible to write unit tests that directly assert on the visual appearance or the precise interactive flow of the `ncurses` TUI *if you cannot navigate or use the ncurses input in the test environment*. This means tests relying on `stdscr.getch()` to simulate user input for navigation or feature interaction may fail or behave unpredictably in non-interactive setups.
    *   **Mitigation for Gemini CLI:** For the purpose of interaction with the Gemini CLI assistant, *manual verification* by running the `aegis-tui.py` application in an interactive terminal is the primary and most reliable method to confirm TUI behavior, arrow key navigation, group filtering, OTP revelation, and timer countdown functionality. Automated tests should focus on non-TUI logic where possible (e.g., vault decryption, OTP generation logic if separable).
*   **Input Simulation in Tests (Advanced):** If unit tests are absolutely necessary for `ncurses` interaction, a comprehensive mocking strategy for the `curses` module and its `stdscr` object is required. This involves:
    *   Mocking all `curses` functions (e.g., `curses.initscr`, `curses.endwin`, `curses.cbreak`, `curses.nocbreak`, `curses.has_colors`, `curses.start_color`, `curses.init_pair`, `curses.curs_set`).
    *   Mocking the `stdscr` object and its methods (`stdscr.getch`, `stdscr.addstr`, `stdscr.refresh`, `stdscr.clear`, `stdscr.getmaxyx`, `stdscr.addch`, `stdscr.hline`, `stdscr.vline`).
    *   Implementing `side_effect` for `mock_stdscr.getch` to simulate a sequence of key presses.
    *   Patching `select.select` to simulate input availability.
    *   Assertions should inspect `mock_stdscr.addstr.call_args_list` to verify what text was written to the screen, rather than capturing `sys.stdout`.

**Conclusion for Gemini CLI:** Given the inherent complexities of testing `ncurses` in automated environments, **prioritize manual verification of TUI functionality.** When requested to write tests, focus on the application's core logic that is independent of `ncurses` interaction, or clarify with the user if a specific, highly mocked `ncurses` test is desired and feasible within the current constraints.