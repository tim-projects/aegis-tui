import argparse
import getpass
import os
import time
import sys
import curses

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False
    print("Warning: pyperclip library not found. OTP copying to clipboard will not be available.")

from aegis_core import find_vault_path, read_and_decrypt_vault_file, get_otps, get_ttn
from tui_ui import run_reveal_mode
from config import load_config, save_config, DEFAULT_AEGIS_VAULT_DIR
from search_mode import run_search_mode
from tui_utils import init_colors

def cli_main(stdscr, args, password):
    stdscr.keypad(True) # Enable special keys like arrow keys

    # Get terminal dimensions
    max_rows, max_cols = stdscr.getmaxyx()

    # Initialize colors
    colors, curses_colors_enabled = init_colors(stdscr, args.no_color)
    NORMAL_TEXT_COLOR = colors["NORMAL_TEXT_COLOR"]
    HIGHLIGHT_COLOR = colors["HIGHLIGHT_COLOR"]
    REVEAL_HIGHLIGHT_COLOR = colors["REVEAL_HIGHLIGHT_COLOR"]
    RED_TEXT_COLOR = colors["RED_TEXT_COLOR"]
    BOLD_WHITE_COLOR = colors["BOLD_WHITE_COLOR"]

    config = load_config()

    # Override args.no_color if default_color_mode is false and --no-color is not explicitly set
    if not config["default_color_mode"] and not args.no_color:
        args.no_color = True

    vault_path = args.vault_path

    row = 0
    
    if not vault_path and config["last_opened_vault"]:
        vault_path = config["last_opened_vault"]
        # row += 1 # Avoid unnecessary printing in TUI
        # stdscr.refresh()

    if not vault_path:
        # stdscr.addstr(row, 0, f"Debug: Searching for vault in {os.path.abspath(args.vault_dir)}...")
        # row += 1
        # stdscr.refresh()
        vault_path = find_vault_path(args.vault_dir)

        if not vault_path and args.vault_dir != DEFAULT_AEGIS_VAULT_DIR:
            vault_path = find_vault_path(DEFAULT_AEGIS_VAULT_DIR)
            args.vault_dir = DEFAULT_AEGIS_VAULT_DIR # Update for consistent messaging

        if not vault_path:
            stdscr.addstr(row, 0, "Error: No vault file found. Exiting.")
            row += 1
            stdscr.refresh()
            time.sleep(2)
            return
    
    vault_data = None
    attempts = 0
    max_attempts = 3
    
    while attempts < max_attempts:
        try:
            vault_data = read_and_decrypt_vault_file(vault_path, password)
            break # Success, exit retry loop
        except ValueError as e:
            attempts += 1
            if attempts >= max_attempts:
                stdscr.addstr(row, 0, f"Error decrypting vault: {e}", RED_TEXT_COLOR)
                stdscr.addstr(row + 1, 0, "Maximum attempts reached. Exiting.", RED_TEXT_COLOR)
                stdscr.refresh()
                time.sleep(2)
                return

            stdscr.addstr(row, 0, f"Error: {e}. Try again ({attempts}/{max_attempts})", RED_TEXT_COLOR)
            row += 1
            stdscr.addstr(row, 0, "Enter vault password: ")
            stdscr.refresh()
            
            # Secure password input in curses
            curses.echo() # Ideally we shouldn't use echo for password, but manual masking is complex.
            # Actually, let's implement a simple masked input loop
            curses.noecho()
            pwd_input = []
            while True:
                ch = stdscr.getch()
                if ch in [10, 13]: # Enter
                    break
                elif ch in [8, 127, curses.KEY_BACKSPACE]: # Backspace
                    if pwd_input:
                        pwd_input.pop()
                        y, x = stdscr.getyx()
                        stdscr.move(y, x - 1)
                        stdscr.delch()
                elif 32 <= ch <= 126:
                    pwd_input.append(chr(ch))
                    stdscr.addch("*")
            
            password = "".join(pwd_input)
            row += 1 # Move past password line for next attempt error or success
            stdscr.addstr(row, 0, "Verifying...", NORMAL_TEXT_COLOR)
            stdscr.refresh()
            row += 1

    try:
        # Save the successfully opened vault path to config

        config["last_opened_vault"] = vault_path
        config["last_vault_dir"] = os.path.dirname(vault_path)
        save_config(config)

        # Clear any residual input from the buffer (e.g., Enter key after password)
        stdscr.nodelay(True)
        while True:
            ch = stdscr.getch()
            if ch == curses.ERR: # No more input
                break
        stdscr.nodelay(False)

        group_names = {group.uuid: group.name for group in vault_data.db.groups}
        otps = get_otps(vault_data)

        # Handle direct UUID display via CLI argument
        if args.uuid:
            entry_to_reveal = next((entry for entry in vault_data.db.entries if entry.uuid == args.uuid), None)
            if entry_to_reveal:
                # Create a display_list containing only the selected entry for run_reveal_mode compatibility
                initial_display_list = [{
                    "index": 0, # Dummy index for single entry
                    "name": entry_to_reveal.name,
                    "issuer": entry_to_reveal.issuer if entry_to_reveal.issuer else "",
                    "groups": ", ".join(group_names.get(g, g) for g in entry_to_reveal.groups) if entry_to_reveal.groups else "",
                    "note": entry_to_reveal.note if entry_to_reveal.note else "",
                    "uuid": entry_to_reveal.uuid
                }]
                # Call reveal mode directly.
                run_reveal_mode(stdscr, initial_display_list[0], otps, set(), get_ttn, config, max_rows, max_cols, curses_colors_enabled, initial_display_list, vault_data, colors)
                if not args.group: # If no group filter, then exit after showing single OTP
                    return
            else:
                stdscr.addstr(row, 0, f"Error: No entry found with UUID {args.uuid}.", RED_TEXT_COLOR)
                stdscr.refresh()
                time.sleep(2)
                return

        # Main application loop: Enter search mode
        while True:
            selected_otp_uuid = run_search_mode(
                stdscr, vault_data, group_names, args, colors, curses_colors_enabled
            )

            # If an OTP was selected in search mode, enter reveal mode
            if selected_otp_uuid:
                entry_to_reveal = next((entry for entry in vault_data.db.entries if entry.uuid == selected_otp_uuid), None)
                if entry_to_reveal:
                    # Construct a minimal display_list for consistency with run_reveal_mode's expectation
                    display_list_for_reveal = [{
                        "index": 0, # Dummy index
                        "name": entry_to_reveal.name,
                        "issuer": entry_to_reveal.issuer if entry_to_reveal.issuer else "",
                        "groups": ", ".join(group_names.get(g, g) for g in entry_to_reveal.groups) if entry_to_reveal.groups else "",
                        "note": entry_to_reveal.note if entry_to_reveal.note else "",
                        "uuid": entry_to_reveal.uuid
                    }]
                    # Call run_reveal_mode directly
                    run_reveal_mode(stdscr, display_list_for_reveal[0], otps, set(), get_ttn, config, max_rows, max_cols, curses_colors_enabled, display_list_for_reveal, vault_data, colors)
                else:
                    stdscr.addstr(max_rows - 1, 0, f"Error: Selected entry with UUID {selected_otp_uuid} not found.", RED_TEXT_COLOR)
                    stdscr.refresh()
                    time.sleep(2)
            else:
                # If run_search_mode returns None, it means the user exited.
                break

    except KeyboardInterrupt:
        return
    except Exception as e:
        import traceback
        stdscr.addstr(row, 0, f"An unexpected error occurred: {e}")
        stdscr.refresh()
        time.sleep(3)
        # In a real TUI we might not want to print traceback to stdout here, 
        # but for debugging it's useful if it doesn't mess up the screen too much.
        # traceback.print_exc() 
        return

def main():
    parser = argparse.ArgumentParser(description="Aegis Authenticator CLI in Python.", prog="aegis-cli")
    parser.add_argument("vault_path", nargs="?", help="Path to the Aegis vault file. If not provided, attempts to find the latest in default locations.", default=None)
    parser.add_argument("-d", "--vault-dir", help="Directory to search for vault files. Defaults to current directory.", default=".")
    parser.add_argument("-u", "--uuid", help="Display OTP for a specific entry UUID.")
    parser.add_argument("-g", "--group", help="Filter OTP entries by a specific group name.")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output.")
    
    args = parser.parse_args()

    password = os.getenv("AEGIS_CLI_PASSWORD")
    if not password:
        try:
            password = getpass.getpass("Enter vault password: ")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)

    curses.wrapper(cli_main, args, password)

if __name__ == "__main__":
    main()
