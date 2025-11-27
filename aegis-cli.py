import argparse
import getpass
import os
import time
import json
from pathlib import Path

import sys
import curses

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False
    print("Warning: pyperclip library not found. OTP copying to clipboard will not be available.")

from aegis_core import find_vault_path, read_and_decrypt_vault_file, get_otps, get_ttn



DEFAULT_AEGIS_VAULT_DIR = os.path.expanduser("~/.config/aegis-cli")
CONFIG_FILE_PATH = Path(DEFAULT_AEGIS_VAULT_DIR) / "config.json"

def load_config():
    if CONFIG_FILE_PATH.exists():
        try:
            with open(CONFIG_FILE_PATH, 'r') as f:
                config = json.load(f)
                # Provide default values for new config keys if they don't exist
                if "last_opened_vault" not in config: config["last_opened_vault"] = None
                if "last_vault_dir" not in config: config["last_vault_dir"] = None
                if "default_color_mode" not in config: config["default_color_mode"] = True # Default to color enabled
                return config
        except json.JSONDecodeError:
            print(f"Warning: Could not parse config file {CONFIG_FILE_PATH}. Using default config.")
    return {"last_opened_vault": None, "last_vault_dir": None, "default_color_mode": True}

def save_config(config):
    CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE_PATH, 'w') as f:
        json.dump(config, f, indent=4)



def cli_main(stdscr, args, password):
    stdscr.keypad(True) # Enable special keys like arrow keys
    curses.curs_set(0)  # Make the cursor invisible
    curses.noecho()     # Turn off automatic echoing of keys to the screen

    # Initialize colors
    curses_colors_enabled = False
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors() # Use default terminal background

        # Define color pairs
        # Pair 1: Default text (white on default background, but let terminal handle default foreground)
        curses.init_pair(1, curses.COLOR_WHITE, -1)
        # Pair 2: Highlighted item (bold white text on a contrasting background, e.g., blue)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_CYAN)
        # Pair 3: Dim text (gray on default background, or just normal if gray isn\'t distinct)
        curses.init_pair(3, curses.COLOR_BLACK, -1) # Using black for \'dim\' on light default backgrounds

        curses_colors_enabled = True

    # Define color attributes to be used with addstr
    DIM_COLOR = curses.color_pair(1) # Using white for 'dim' for better visibility
    BOLD_WHITE_COLOR = curses.A_BOLD | curses.color_pair(1) # For revealed OTP, bold white on default background
    HIGHLIGHT_COLOR = curses.color_pair(2) # For selected row in search mode

    config = load_config()

    
    # Override args.no_color if default_color_mode is false and --no-color is not explicitly set
    if not config["default_color_mode"] and not args.no_color:
        args.no_color = True

    vault_path = args.vault_path
    if not vault_path and args.positional_vault_path and args.positional_vault_path.endswith(".json"):
        vault_path = args.positional_vault_path

    row = 0
    if not vault_path and config["last_opened_vault"]:
        vault_path = config["last_opened_vault"]
        stdscr.addstr(row, 0, f"No vault path provided. Opening previously used vault: {vault_path}")
        row += 1
        stdscr.refresh()

    if not vault_path:
        stdscr.addstr(row, 0, f"Searching for vault in {os.path.abspath(args.vault_dir)}...")
        row += 1
        stdscr.refresh()
        vault_path = find_vault_path(args.vault_dir)

        if not vault_path and args.vault_dir != DEFAULT_AEGIS_VAULT_DIR:
            stdscr.addstr(row, 0, f"Vault not found in {os.path.abspath(args.vault_dir)}. Searching in {DEFAULT_AEGIS_VAULT_DIR}...")
            row += 1
            stdscr.refresh()
            vault_path = find_vault_path(DEFAULT_AEGIS_VAULT_DIR)
            args.vault_dir = DEFAULT_AEGIS_VAULT_DIR # Update for consistent messaging

        if not vault_path:
            stdscr.addstr(row, 0, "Error: No vault file found.")
            row += 1
            parser.print_help()
            stdscr.refresh()
            return
        stdscr.addstr(row, 0, f"Found vault: {vault_path}")
        row += 1
        stdscr.refresh()

    try:
        vault_data = read_and_decrypt_vault_file(vault_path, password)
        stdscr.addstr(row, 0, "Vault decrypted successfully.")
        row += 1
        stdscr.refresh()
        # Save the successfully opened vault path to config
        config["last_opened_vault"] = vault_path
        config["last_vault_dir"] = os.path.dirname(vault_path)
        save_config(config)
    except ValueError as e:
        stdscr.addstr(row, 0, f"Error decrypting vault: {e}")
        row += 1
        stdscr.refresh()
        time.sleep(3) # Display error message for 3 seconds before exiting
        return
    except Exception as e:
        import traceback
        stdscr.addstr(row, 0, f"An unexpected error occurred: {e}")
        row += 1
        stdscr.refresh()
        time.sleep(3) # Display error message for 3 seconds before exiting
        traceback.print_exc()
        return

    if args.uuid:
        otps = get_otps(vault_data)
        if args.uuid in otps:
            otp_entry = otps[args.uuid]
            stdscr.addstr(row, 0, f"OTP for {args.uuid}: {otp_entry.string()}")
            row += 1
            stdscr.refresh()
        else:
            stdscr.addstr(row, 0, f"Error: No entry found with UUID {args.uuid}.")
            row += 1
            stdscr.refresh()

    # Main interactive loop for search and reveal modes
    try:
        revealed_otps = set() # Keep track of which OTPs are revealed
        search_term = ""
        current_mode = "search" # Initialize mode
        selected_index_for_reveal = None # Initialize to None
        selected_row = -1 # Track the currently highlighted row for navigation (-1 for no selection)
        char = curses.ERR # Initialize char to prevent UnboundLocalError
        previous_search_term = "" # Track previous search term to detect changes
        
        while True:
                        stdscr.clear() # Clear the screen for each refresh
                        
                        otps = get_otps(vault_data)
        
                        display_data = []
                        max_name_len = len("Name")
                        max_issuer_len = len("Issuer")
                        max_group_len = len("Name") # Group max length to avoid overflow
                        max_note_len = len("Note")
        
                        group_names = {group.uuid: group.name for group in vault_data.db.groups}
        
                        all_entries = []
                        for idx, entry in enumerate(vault_data.db.entries): # Use enumerate to get the original index
                            resolved_groups = []
                            for group_uuid in entry.groups:
                                resolved_groups.append(group_names.get(group_uuid, group_uuid))
                            
                            if args.group and args.group not in resolved_groups:
                                continue
        
                            all_entries.append({
                                "index": idx, # Add the original index
                                "name": entry.name,
                                "issuer": entry.issuer if entry.issuer else "",
                    "groups": ", ".join(resolved_groups) if resolved_groups else "",
                    "note": entry.note if entry.note else "",
                    "uuid": entry.uuid
                })

            # Sort alphabetically by issuer
            all_entries.sort(key=lambda x: x["issuer"].lower())

            # Display all entries, search will only move the cursor
            display_data = all_entries

            # Adjust selected_row based on search_term
            if search_term:
                # Attempt to search by line number first
                if search_term.isdigit():
                    line_number = int(search_term)
                    if 1 <= line_number <= len(all_entries):
                        selected_row = line_number - 1
                        previous_search_term = search_term # Update to prevent resetting
                        # Skip text-based search if line number search is successful
                        if len(display_data) > 0:
                            selected_row = max(0, min(selected_row, len(display_data) - 1))
                        else:
                            selected_row = -1
                        line_number_search_successful = True
                    else:
                        line_number_search_successful = False
                else:
                    line_number_search_successful = False

                if not line_number_search_successful or search_term != previous_search_term: # Only perform text search if line number search failed or search term changed
                    found_match_in_search = False
                    for idx, entry in enumerate(all_entries):
                        search_string = f"{entry['issuer']} {entry['name']} {entry['groups']} {entry['note']}".lower()
                        if search_term.lower() in search_string:
                            selected_row = idx
                            found_match_in_search = True
                            break
                    if not found_match_in_search and len(all_entries) > 0:
                        if not (0 <= selected_row < len(all_entries)):
                            selected_row = 0
                    elif not all_entries:
                        selected_row = -1
            else: # No search term
                if previous_search_term: # If search_term just became empty
                    selected_row = 0 if len(all_entries) > 0 else -1 # Reset to first or none

            if len(display_data) > 0:
                selected_row = max(0, min(selected_row, len(display_data) - 1))
            else:
                selected_row = -1

            previous_search_term = search_term # Update previous search term for next iteration            for item in display_data:
                if len(item["name"]) > max_name_len: max_name_len = len(item["name"])
                if len(item["issuer"]) > max_issuer_len: max_issuer_len = len(item["issuer"])
                if len(item["groups"]) > max_group_len: max_group_len = len(item["groups"])
                if len(item["note"]) > max_note_len: max_note_len = len(item["note"])

            # --- Mode Management & Display ---
            entry_to_reveal = None

            # Check if an entry was selected for reveal via Enter key
            if current_mode == "search" and selected_row != -1 and (char == curses.KEY_ENTER or char in [10, 13]):
                entry_to_reveal = all_entries[selected_row]


            if entry_to_reveal:
                if entry_to_reveal["uuid"] not in revealed_otps:
                    revealed_otps.add(entry_to_reveal["uuid"])
                current_mode = "reveal"
                # Auto-copy logic (already exists and uses PYPERCLIP_AVAILABLE)
                if PYPERCLIP_AVAILABLE:
                    otp_to_copy = otps[entry_to_reveal["uuid"]].string()
                    pyperclip.copy(otp_to_copy)
                # Reset selected_row after revealing
                selected_row = 0


            row = 0 # Reset row for each refresh

            # Print header based on mode and search
            if current_mode == "search":
                if not search_term and not args.group:
                    stdscr.addstr(row, 0, "--- All OTPs ---")
                elif args.group:
                    stdscr.addstr(row, 0, f"--- Group: {args.group} ---")
                else:
                    stdscr.addstr(row, 0, f"--- Search: {search_term} ---")
            elif current_mode == "reveal" and len(display_data) == 1:
                 stdscr.addstr(row, 0, f"--- Revealed OTP: {display_data[0]['name']} ---")
            row += 1



            # Print header for table
            stdscr.addstr(row, 0, f"{'#'.ljust(3)} {'Issuer'.ljust(max_issuer_len)}  {'Name'.ljust(max_name_len)}  {'Code'.ljust(6)}  {'Group'.ljust(max_group_len)}  {'Note'.ljust(max_note_len)}")
            row += 1
            stdscr.addstr(row, 0, f"{'---'.ljust(3)} {'-' * max_issuer_len}  {'-' * max_name_len}  {'------'}  {'-' * max_group_len}  {'-' * max_note_len}")
            row += 1

            # Print formatted output
            for i, item in enumerate(display_data): # Use enumerate to get the index for highlighting
                index = item["index"]
                name = item["name"]
                issuer = item["issuer"]
                groups = item["groups"]
                note = item["note"]
                uuid = item["uuid"]

                otp_value = "******" # Obscure by default
                if uuid in otps and uuid in revealed_otps:
                    try:
                        otp_obj = otps[uuid]
                        otp_value = otp_obj.string()
                    except Exception as e:
                        otp_value = f"ERROR: {e}"
                
                line = f"{str(i + 1).ljust(3)} {issuer.ljust(max_issuer_len)}  {name.ljust(max_name_len)}  {otp_value.ljust(6)}  {groups.ljust(max_group_len)}  {note.ljust(max_note_len)}"

                # Determine color attribute
                attribute = curses.A_NORMAL
                if curses_colors_enabled:
                    if uuid in revealed_otps:
                        attribute = BOLD_WHITE_COLOR
                    elif i == selected_row and current_mode == "search": # Highlight if selected in search mode
                        attribute = HIGHLIGHT_COLOR # Use the new HIGHLIGHT_COLOR
                    else:
                        attribute = curses.A_NORMAL # Use standard terminal attributes for unhighlighted items
                
                stdscr.addstr(row, 0, line, attribute)
                row += 1
            stdscr.refresh()

            # --- Input Handling for "Search" Mode with Arrow Key Navigation ---
            if current_mode == "search":
                stdscr.addstr(row, 0, f"Type to filter, use arrows to select, Enter to reveal (Ctrl+C to exit): {search_term}")
                stdscr.refresh()

                char = stdscr.getch() # Get a single character

                if char != curses.ERR: # Only process if a key was actually pressed
                    if char == curses.KEY_UP:
                        if len(all_entries) > 0:
                            selected_row = max(0, selected_row - 1)
                        else:
                            selected_row = -1
                    elif char == curses.KEY_DOWN:
                        if len(all_entries) > 0:
                            selected_row = min(len(all_entries) - 1, selected_row + 1)
                        else:
                            selected_row = -1

                    elif char == 27: # ESC key
                        search_term = ""
                        revealed_otps.clear()
                        selected_row = 0 if len(all_entries) > 0 else -1 # Reset selection
                    elif char in [curses.KEY_BACKSPACE, 127, 8]: # Backspace key
                        if search_term: # Only modify search_term if it's not empty
                            search_term = search_term[:-1]
                            selected_row = 0 if len(all_entries) > 0 else -1 # Reset selection for new search term evaluation
                    elif 32 <= char < 127: # Printable character
                        search_term += chr(char)
                        selected_row = 0 if len(all_entries) > 0 else -1 # Reset selection for new search term evaluation
                    elif char == 3: # Ctrl+C
                        raise KeyboardInterrupt
                row += 1 # Advance row after input prompt
            
            # Add a small delay if no key was pressed to prevent CPU from spinning
            if char == curses.ERR:
                time.sleep(0.1)

            # Original "Search as you type" logic (retained for reference)
            if False: # Keep this block for historical reference, but it's currently disabled.
                key = None
                if select.select([sys.stdin], [], [], 0.1)[0]: # Check for input with a short timeout
                    key = readchar.readkey() # Read key if input is available

                if key: # Process key if one was pressed
                    if key == readchar.key.BACKSPACE:
                        search_term = search_term[:-1]
                    elif key == readchar.key.CTRL_C:
                        raise KeyboardInterrupt
                    elif key == readchar.key.ESC:
                        search_term = ""
                        revealed_otps.clear()
                    elif key == readchar.key.ENTER:
                        pass # Enter key is ignored in search mode, as automatic revelation handles it.
                    else:
                        search_term += key
                    
                # Display the prompt *after* processing any new key
                print(f"\nType the name or line number to reveal OTP code (Ctrl+C to exit): {search_term}", end='', flush=True)
                time.sleep(0.1) # Add a small delay to prevent rapid blinking and allow user to type

                
            elif current_mode == "reveal": # Ensure we are still in a valid reveal state
                if not entry_to_reveal: # If we are in reveal mode but no entry was revealed, it's an error state
                    current_mode = "search"
                    continue # Go back to search
                otp_to_reveal = otps[entry_to_reveal["uuid"]].string() # Define otp_to_reveal here
                # Get the actual time to next refresh
                actual_ttn = get_ttn()

                # Loop to keep OTP revealed until ESC is pressed
                while True:
                    current_remaining_ttn = get_ttn() # Get updated ttn in each iteration
                    remaining_seconds_for_display = int(current_remaining_ttn / 1000)

                    if PYPERCLIP_AVAILABLE:
                        pyperclip.copy(otp_to_reveal)
                    stdscr.clear() # Clear for each countdown second
                    
                    countdown_row = 0 # Local row counter for reveal mode
                    stdscr.addstr(countdown_row, 0, f"--- Revealed OTP: {display_data[0]['name']} ---")
                    countdown_row += 1
                    
                    stdscr.addstr(countdown_row, 0, f"{'#'.ljust(3)} {'Issuer'.ljust(max_issuer_len)}  {'Name'.ljust(max_name_len)}  {'Code'.ljust(6)}  {'Group'.ljust(max_group_len)}  {'Note'.ljust(max_note_len)}")
                    countdown_row += 1
                    stdscr.addstr(countdown_row, 0, f"{'---'.ljust(3)} {'-' * max_issuer_len}  {'-' * max_name_len}  {'------'}  {'-' * max_group_len}  {'-' * max_note_len}")
                    countdown_row += 1
                    
                    item = display_data[0]
                    line = f"{str(item['index']).ljust(3)} {item['issuer'].ljust(max_issuer_len)}  {item['name'].ljust(max_name_len)}  {otp_to_reveal.ljust(6)}  {item['groups'].ljust(max_group_len)}  {item['note'].ljust(max_note_len)}"
                    stdscr.addstr(countdown_row, 0, line, BOLD_WHITE_COLOR if curses_colors_enabled else curses.A_NORMAL)
                    countdown_row += 1

                    countdown_text = f"Time until next refresh: {remaining_seconds_for_display:.1f} seconds (Press ESC to go back)"
                    stdscr.addstr(countdown_row, 0, countdown_text, DIM_COLOR if curses_colors_enabled else curses.A_NORMAL)
                    
                    stdscr.refresh() # Refresh screen after all updates

                    # Set timeout for getch to allow for responsive exit
                    stdscr.timeout(1000) # 1-second timeout for getch
                    char = stdscr.getch()

                    if char == 27 or char in [curses.KEY_BACKSPACE, 127, 8]: # ESC or Backspace key
                        current_mode = "search"
                        selected_index_for_reveal = None
                        break # Exit the reveal loop
                    elif char == 3: # Ctrl+C
                        raise KeyboardInterrupt
                    # If other keys are pressed, or no key, getch will return ERR after 1 second

                # After countdown finishes (either by ESC/Backspace or OTP expiration)
                stdscr.timeout(-1) # Reset timeout to blocking upon exiting reveal loop
                current_mode = "search"
                search_term = ""
                revealed_otps.clear()
                    
    except KeyboardInterrupt:
        print("\nExiting.")
        return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aegis Authenticator CLI in Python.", prog="aegis-cli")
    parser.add_argument("-v", "--vault-path", help="Path to the Aegis vault file. If not provided, attempts to find the latest in default locations.")
    parser.add_argument("-d", "--vault-dir", help="Directory to search for vault files. Defaults to current directory.", default=".")
    parser.add_argument("-u", "--uuid", help="Display OTP for a specific entry UUID.")
    parser.add_argument("-g", "--group", help="Filter OTP entries by a specific group name.")
    parser.add_argument("positional_vault_path", nargs="?", help=argparse.SUPPRESS, default=None)
    parser.add_argument("--no-color", action="store_true", help="Disable colored output.")

    args = parser.parse_args()

    password = os.getenv("AEGIS_CLI_PASSWORD")
    if not password:
        try:
            password = getpass.getpass("Enter vault password: ")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0) # Exit cleanly

    curses.wrapper(cli_main, args, password)