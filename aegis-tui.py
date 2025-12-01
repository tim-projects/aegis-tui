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
    stdscr.nodelay(True) # Make getch non-blocking by default for continuous refresh

    # Get terminal dimensions
    max_rows, max_cols = stdscr.getmaxyx()

    # Initialize colors
    curses_colors_enabled = False
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors() # Use default terminal background

        # Define color pairs
        # Pair 1: Default text (white on default background, but let terminal handle default foreground)
        curses.init_pair(1, curses.COLOR_WHITE, -1)
        # Pair 2: Highlighted item (bold white text on a contrasting background, e.g., blue)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE)
        # Pair 3: Dim text (gray on default background, or just normal if gray isn't distinct)
        curses.init_pair(3, curses.COLOR_BLACK, -1) # Using black for 'dim' on light default backgrounds
        # Pair 4: Highlighted OTP code in reveal mode
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_CYAN) # Black text on cyan background for highlighting

        curses_colors_enabled = True

    # Define color attributes to be used with addstr
    NORMAL_TEXT_COLOR = curses.color_pair(1) # For normal text (white on default background)
    BOLD_WHITE_COLOR = curses.A_BOLD | NORMAL_TEXT_COLOR # For revealed OTP, bold white on default background
    HIGHLIGHT_COLOR = curses.color_pair(2) # For selected row in search mode
    REVEAL_HIGHLIGHT_COLOR = curses.color_pair(4) # For highlighting OTP code in reveal mode

    config = load_config()

    
    # Override args.no_color if default_color_mode is false and --no-color is not explicitly set
    if not config["default_color_mode"] and not args.no_color:
        args.no_color = True

    vault_path = args.vault_path

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
        # Save the successfully opened vault path to config
        config["last_opened_vault"] = vault_path
        config["last_vault_dir"] = os.path.dirname(vault_path)
        save_config(config)
        # Clear any residual input from the buffer (e.g., Enter key after password)
        while stdscr.getch() != curses.ERR:
            pass

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

    if args.uuid and not args.group: # Only process as a direct display if a UUID is provided and no group filter
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
        return # Exit after displaying the single OTP

    def _run_reveal_mode(stdscr, entry_to_reveal, otps, revealed_otps, get_ttn_func, current_config, initial_max_rows, initial_max_cols, curses_colors_enabled, display_list):
        current_mode = "reveal"
        running = True
        max_rows, max_cols = initial_max_rows, initial_max_cols # Initial dimensions
        selected_row = 0 # Default to first item in reveal display

        stdscr.nodelay(True) # Make getch non-blocking
        while current_mode == "reveal" and running:
            stdscr.clear()

            # Dynamic box dimensions for reveal mode
            reveal_box_height = max(7, max_rows - 2) # At least 7 lines for content + borders
            reveal_box_width = max(30, max_cols) # At least 30 cols

            reveal_start_row = (max_rows - reveal_box_height) // 2
            reveal_start_col = (max_cols - reveal_box_width) // 2
            
            # Ensure box dimensions are within screen limits
            if reveal_start_row < 0: reveal_start_row = 0
            if reveal_start_col < 0: reveal_start_col = 0
            if reveal_box_height > max_rows: reveal_box_height = max_rows
            if reveal_box_width > max_cols: reveal_box_width = max_cols

            # Draw border box for reveal mode
            # Top line
            stdscr.addch(reveal_start_row, reveal_start_col, curses.ACS_ULCORNER)
            stdscr.hline(reveal_start_row, reveal_start_col + 1, curses.ACS_HLINE, reveal_box_width - 2)
            stdscr.addch(reveal_start_row, reveal_start_col + reveal_box_width - 1, curses.ACS_URCORNER)

            # Middle lines
            for r in range(reveal_start_row + 1, reveal_start_row + reveal_box_height - 1):
                stdscr.addch(r, reveal_start_col, curses.ACS_VLINE)
                stdscr.addch(r, reveal_start_col + reveal_box_width - 1, curses.ACS_VLINE)

            # Bottom line
            stdscr.addch(reveal_start_row + reveal_box_height - 1, reveal_start_col, curses.ACS_LLCORNER)
            stdscr.hline(reveal_start_row + reveal_box_height - 1, reveal_start_col + 1, curses.ACS_HLINE, reveal_box_width - 2)
            stdscr.addch(reveal_start_row + reveal_box_height - 1, reveal_start_col + reveal_box_width - 1, curses.ACS_LRCORNER)

            # Header and OTP display
            header_text = f"--- Revealed OTP: {entry_to_reveal['name']} ---"
            stdscr.addstr(reveal_start_row + 1, reveal_start_col + (reveal_box_width - len(header_text)) // 2, header_text, curses.A_BOLD)

            # Display fields
            display_row = reveal_start_row + 3
            def display_field(label, value, row_num, col_num, max_w, highlight=False):
                line = f"{label}: {value}"
                display_line = line[:max_w] # Truncate if too long
                
                # Highlight only if explicitly requested AND value is a secret
                attr = REVEAL_HIGHLIGHT_COLOR if highlight and label == "OTP Code" else NORMAL_TEXT_COLOR
                stdscr.addstr(row_num, col_num, display_line, attr)

            inner_width = reveal_box_width - 4 # Account for box borders and padding
            field_col = reveal_start_col + 2

            otp_to_reveal = otps[entry_to_reveal["uuid"]].string()
            display_field("Issuer", entry_to_reveal["issuer"], display_row, field_col, inner_width)
            display_row += 1
            display_field("Name", entry_to_reveal["name"], display_row, field_col, inner_width)
            display_row += 1
            display_field("Group", entry_to_reveal["groups"], display_row, field_col, inner_width)
            display_row += 1
            display_field("Note", entry_to_reveal["note"], display_row, field_col, inner_width)
            display_row += 1
            display_field("OTP Code", otp_to_reveal, display_row, field_col, inner_width, highlight=True)
            display_row += 1
            display_field("Time to Next", f"{get_ttn_func() / 1000}s", display_row, field_col, inner_width)

            # Controls
            stdscr.addstr(reveal_start_row + reveal_box_height - 2, reveal_start_col + 2, "Press ESC to return to search, Ctrl+C to exit.", NORMAL_TEXT_COLOR)

            stdscr.refresh()

            reveal_char = stdscr.getch()
            if reveal_char == 27: # ESC key
                current_mode = "search"
                revealed_otps.clear()
                # Do not reset selected_row here, maintain selection from search mode
                break # Exit reveal loop
            elif reveal_char == 3: # Ctrl+C
                running = False
                break # Exit reveal loop and signal main loop to exit
            elif reveal_char == curses.KEY_RESIZE: # Handle terminal resize event
                max_rows, max_cols = stdscr.getmaxyx() # Update dimensions
                stdscr.clear()
                stdscr.refresh()
            elif reveal_char != curses.ERR: # Any other key press, clear revealed OTP and return to search
                current_mode = "search"
                revealed_otps.clear()
                # Do not reset selected_row here
                break # Exit reveal loop
            
            # Add a small delay if no key was pressed to prevent CPU from spinning
            if reveal_char == curses.ERR:
                time.sleep(0.01) # Shorter sleep for reveal mode responsiveness

        return current_mode, running, selected_row # Return selected_row as well
    # --- Main Application Loop ---
    try:
        revealed_otps = set() # Keep track of which OTPs are revealed
        search_term = ""
        current_mode = "search" # Initialize mode: "search", "reveal", or "group_select"
        selected_row = -1 # Track the currently highlighted row for navigation (-1 for no selection)
        char = curses.ERR # Initialize char to prevent UnboundLocalError
        previous_search_term = "" # Track previous search term to detect changes
        current_group_filter = None # New: Store the currently active group filter UUID
        group_selection_mode = False # New: Flag to indicate if we are in group selection mode
        entry_to_reveal = None # Store the entry dictionary selected for reveal

        while True:
            # --- Common Data Preparation for all modes (except initial reveal entry) ---
            otps = get_otps(vault_data)
            all_entries = []
            group_names = {group.uuid: group.name for group in vault_data.db.groups}

            # Prepare all_entries (filtered by current_group_filter if active)
            for idx, entry in enumerate(vault_data.db.entries):
                resolved_groups = []
                for group_uuid in entry.groups:
                    resolved_groups.append(group_names.get(group_uuid, group_uuid))

                # Apply group filter if active
                if current_group_filter and current_group_filter not in resolved_groups:
                    continue

                # Apply search filter if active and not in group selection mode
                if not group_selection_mode and search_term and \
                   not (search_term.lower() in entry.name.lower() or \
                        search_term.lower() in entry.issuer.lower() or \
                        search_term.lower() in ", ".join(resolved_groups).lower() or \
                        search_term.lower() in (entry.note.lower() if entry.note else "")):
                    continue

                all_entries.append({
                    "index": idx,
                    "name": entry.name,
                    "issuer": entry.issuer if entry.issuer else "",
                    "groups": ", ".join(resolved_groups) if resolved_groups else "",
                    "note": entry.note if entry.note else "",
                    "uuid": entry.uuid
                })

            # Sort alphabetically by issuer
            all_entries.sort(key=lambda x: x["issuer"].lower())

            # Determine display_list based on mode
            if group_selection_mode:
                display_list = [{
                    "name": group.name,
                    "uuid": group.uuid
                } for group in vault_data.db.groups]
                display_list.sort(key=lambda x: x["name"].lower()) # Sort groups alphabetically

                if current_group_filter == "-- All OTPs --":
                    selected_row = -1 # Indicate no specific group is selected from the list within the box
                elif len(display_list) > 0:
                    try:
                        selected_row = next(i for i, group in enumerate(display_list) if group["name"] == current_group_filter)
                    except StopIteration:
                        selected_row = 0 # Default to first group if not found
                else:
                    selected_row = -1
            else:
                display_list = all_entries # Use filtered entries for display

            # Adjust selected_row based on display_list (either groups or entries)
            if len(display_list) > 0:
                selected_row = max(0, min(selected_row, len(display_list) - 1))
            else:
                selected_row = -1

            # Define box dimensions. Leave 1 line for top/bottom borders + 1 for input prompt.
            # We use max_rows - 1 for input prompt, so actual content height is max_rows - row - 1.
            # These are defined early as they are needed for content width calculations.
            # Initial row for calculations starts at 0, will be adjusted later for display.
            temp_row_for_box_calc = 0 # Temporary row to calculate initial box dimensions
            box_start_row = temp_row_for_box_calc
            box_start_col = 0
            box_height = max(2, max_rows - box_start_row - 1) # Ensure min height of 2
            box_width = max(2, max_cols) # Ensure min width of 2

            # Initialize max lengths with header lengths
            max_name_len = len("Name")
            max_issuer_len = len("Issuer")
            max_group_len = len("Group")
            max_note_len = len("Note")

            # Calculate actual max content lengths from display_list
            if not group_selection_mode:
                for item in display_list:
                    if len(item["name"]) > max_name_len: max_name_len = len(item["name"])
                    if len(item["issuer"]) > max_issuer_len: max_issuer_len = len(item["issuer"])
                    if len(item["groups"]) > max_group_len: max_group_len = len(item["groups"])
                    if len(item["note"]) > max_note_len: max_note_len = len(item["note"])
            else:
                for item in display_list:
                    if len(item["name"]) > max_name_len: max_name_len = len(item["name"])

            # Re-adjust max_len for headers to ensure they fit, using the capped values
            max_name_len = max(len("Name"), max_name_len)
            max_issuer_len = max(len("Issuer"), max_issuer_len)
            max_group_len = max(len("Group"), max_group_len)
            max_note_len = max(len("Note"), max_note_len)

            # Now, calculate available content width inside the box
            inner_box_content_width = max(0, box_width - 2) # Account for left and right borders

            # Define minimum widths for fixed elements in OTP display mode (e.g., '#', 'Code', spaces)
            fixed_otp_display_width = 3 + 1 + 2 + 2 + 6 + 2 # # + space + spaces around name/issuer + code + spaces around group/note
            # Remaining width for dynamic fields (issuer, name, group, note)
            remaining_dynamic_width = max(0, inner_box_content_width - fixed_otp_display_width)

            # Define minimum widths for fixed elements in Group display mode
            fixed_group_display_width = 3 + 1 # # + space

            # Cap max lengths based on available width, prioritizing some fields over others
            # This is a heuristic to prevent overflow. Adjust ratios as needed.
            if not group_selection_mode:
                # Distribute remaining_dynamic_width. Example: Name (40%), Issuer (30%), Group (20%), Note (10%)
                max_name_len_cap = int(remaining_dynamic_width * 0.4)
                max_issuer_len_cap = int(remaining_dynamic_width * 0.3)
                max_group_len_cap = int(remaining_dynamic_width * 0.2)
                max_note_len_cap = int(remaining_dynamic_width * 0.1)

                max_name_len = min(max_name_len, max_name_len_cap)
                max_issuer_len = min(max_issuer_len, max_issuer_len_cap)
                max_group_len = min(max_group_len, max_group_len_cap)
                max_note_len = min(max_note_len, max_note_len_cap)
            else:
                # For group selection, the entire remaining width is for the group name
                max_name_len = min(max_name_len, max(0, inner_box_content_width - fixed_group_display_width))
            
            # --- Input Handling (NOW FIRST in loop) ---
            char = stdscr.getch() # Get a single character

            if char != curses.ERR: # Only process if a key was actually pressed
                if char == curses.KEY_RESIZE:
                    max_rows, max_cols = stdscr.getmaxyx()
                    stdscr.clear()
                    stdscr.refresh()
                    continue
                if group_selection_mode:
                    if char == curses.KEY_UP:
                        if selected_row == 0: # If at the first group, move to "All OTPs"
                            selected_row = -1
                        elif len(display_list) > 0:
                            selected_row = max(0, selected_row - 1)
                    elif char == curses.KEY_DOWN:
                        if selected_row == -1: # If at "All OTPs", move to the first group
                            if len(display_list) > 0:
                                selected_row = 0
                        elif len(display_list) > 0:
                            selected_row = min(len(display_list) - 1, selected_row + 1)
                    elif char == 27 or char == 7: # ESC or Ctrl+G
                        group_selection_mode = False
                        current_group_filter = None
                        selected_row = 0 if len(all_entries) > 0 else -1 # Reset selection for all entries
                        search_term = "" # Clear search term
                    elif char == curses.KEY_ENTER or char in [10, 13]:
                        if selected_row == -1: # "All OTPs" selected
                            current_group_filter = None # Clear filter
                        elif selected_row != -1 and len(display_list) > 0:
                            selected_group = display_list[selected_row]
                            current_group_filter = selected_group["name"]
                        revealed_otps.clear() # Clear revealed OTPs when a new group filter is applied or cleared
                        group_selection_mode = False
                        current_mode = "search" # Explicitly set mode to search after group selection
                        selected_row = 0 if len(all_entries) > 0 else -1 # Reset selection for filtered entries
                        search_term = "" # Clear search term
                elif current_mode == "search": # Normal search mode
                    if char == curses.KEY_UP:
                        if len(display_list) > 0:
                            selected_row = max(0, selected_row - 1)
                        else:
                            selected_row = -1
                    elif char == curses.KEY_DOWN:
                        if len(display_list) > 0:
                            selected_row = min(len(display_list) - 1, selected_row + 1)
                        else:
                            selected_row = -1
                    elif char == 27: # ESC key
                        search_term = ""
                        revealed_otps.clear()
                        selected_row = 0 if len(display_list) > 0 else -1 # Reset selection
                        current_group_filter = None # Clear group filter on ESC
                    elif char in [curses.KEY_BACKSPACE, 127, 8]: # Backspace key
                        if search_term: # Only modify search_term if it's not empty
                            search_term = search_term[:-1]
                    elif 32 <= char < 127: # Printable character
                        search_term += chr(char)
                    elif char == 7: # Ctrl+G
                        group_selection_mode = not group_selection_mode
                        revealed_otps.clear() # Clear revealed OTPs on mode change
                        if group_selection_mode:
                            selected_row = 0 # Reset selection for group list (first item is "All OTPs")
                        else:
                            current_group_filter = None # Clear filter if exiting group selection mode
                            selected_row = 0 if len(display_list) > 0 else -1 # Reset selection for all entries
                        search_term = "" # Clear search term when entering/exiting group selection
                    elif char == 3: # Ctrl+C
                        raise KeyboardInterrupt
                    elif char == curses.KEY_ENTER or char in [10, 13]:
                        # Handle reveal logic: set entry_to_reveal, current_mode = "reveal"
                        if selected_row != -1 and len(display_list) > 0:
                            entry_to_reveal = display_list[selected_row] # Make sure this is correct
                            if entry_to_reveal["uuid"] not in revealed_otps:
                                revealed_otps.add(entry_to_reveal["uuid"])
                            # Call reveal mode directly and let it handle its own loop
                            current_mode, running, selected_row = _run_reveal_mode(stdscr, entry_to_reveal, otps, revealed_otps, get_ttn, config, max_rows, max_cols, curses_colors_enabled, display_list)
                            # After reveal mode, reset current_mode to search and clear revealed OTPs
                            current_mode = "search"
                            revealed_otps.clear()
                            
            stdscr.clear() # Clear screen for each refresh
            # Update max_rows and max_cols at the beginning of each display cycle
            max_rows, max_cols = stdscr.getmaxyx()

            row = 0 # Reset row for each refresh
            header_row_offset = 0 # Offset for content after headers

            # Print main header based on mode, search, and group filter
            if group_selection_mode:
                stdscr.addstr(row, 0, "--- Select Group (Ctrl+G/Esc to cancel) ---")
            elif current_mode == "search":
                if current_group_filter:
                    stdscr.addstr(row, 0, f"--- Group: {current_group_filter} (Ctrl+G to clear) ---")
                elif search_term:
                    stdscr.addstr(row, 0, f"--- Search: {search_term} ---")
                elif args.group:
                    stdscr.addstr(row, 0, f"--- Group: {args.group} ---")
                else:
                    stdscr.addstr(row, 0, "--- All OTPs ---") # This will be the main header if no filters
            row += 1
            header_row_offset = row # Remember where content starts after header

            # Draw border box for the main display area
            box_height = max_rows - header_row_offset - 2 # Account for header, prompt, and bottom border
            box_width = max_cols
            
            # Ensure minimum dimensions for the box
            if box_height < 2: box_height = 2
            if box_width < 2: box_width = 2

            # Top line
            stdscr.addch(row, 0, curses.ACS_ULCORNER)
            stdscr.hline(row, 1, curses.ACS_HLINE, box_width - 2)
            stdscr.addch(row, box_width - 1, curses.ACS_URCORNER)
            row += 1 # Move past the top border

            # Middle lines
            for r in range(row, row + box_height - 1): # -1 because the bottom border uses one row
                stdscr.addch(r, 0, curses.ACS_VLINE)
                stdscr.addch(r, box_width - 1, curses.ACS_VLINE)
            
            # Bottom line
            stdscr.addch(row + box_height - 1, 0, curses.ACS_LLCORNER)
            stdscr.hline(row + box_height - 1, 1, curses.ACS_HLINE, box_width - 2)
            stdscr.addch(row + box_height - 1, box_width - 1, curses.ACS_LRCORNER)
            
            # Reset row to start of content area
            row = header_row_offset

            # Display "All OTPs" in group selection mode if there are no groups, or if it's the first option
            if group_selection_mode:
                # Always show "All OTPs" as the first selectable item
                all_otps_text = "-- All OTPs --"
                display_attr = HIGHLIGHT_COLOR if selected_row == -1 else NORMAL_TEXT_COLOR
                stdscr.addstr(row, 2, all_otps_text[:inner_box_content_width - fixed_group_display_width], display_attr)
                row += 1

            # Display OTPs or Groups
            for i, item in enumerate(display_list):
                if row >= max_rows - 2: # Leave room for prompt and bottom border
                    break

                display_attr = HIGHLIGHT_COLOR if i == selected_row else NORMAL_TEXT_COLOR
                
                # Dynamic width adjustment for printing OTP entries or groups
                if not group_selection_mode:
                    # OTP entries
                    name_str = item["name"][:max_name_len].ljust(max_name_len)
                    issuer_str = item["issuer"][:max_issuer_len].ljust(max_issuer_len)
                    group_str = item["groups"][:max_group_len].ljust(max_group_len)
                    note_str = item["note"][:max_note_len].ljust(max_note_len)
                    
                    # Construct the display line
                    line = f" {name_str} | {issuer_str} | {group_str} | {note_str} "
                    stdscr.addstr(row, 2, line[:inner_box_content_width], display_attr)
                else:
                    # Group names
                    group_name_str = item["name"][:max_name_len].ljust(max_name_len)
                    line = f" {group_name_str} "
                    stdscr.addstr(row, 2, line[:inner_box_content_width], display_attr)
                
                row += 1

            # Display search prompt/input line
            prompt_string_prefix = "Search: " if current_mode == "search" else "Group Filter: "
            
            # If in group selection mode, allow user to type a search term to filter groups
            current_input_text = search_term if current_mode == "search" else (search_term if group_selection_mode else "")

            # Ensure the prompt fits on the last line
            prompt_row = max_rows - 1
            if prompt_row < 0: prompt_row = 0 # Safety check for very small terminals

            stdscr.addstr(prompt_row, 0, (prompt_string_prefix + current_input_text)[:max_cols], NORMAL_TEXT_COLOR)

            # Instructions
            stdscr.addstr(max_rows - 2, 0, "Ctrl+G: Toggle Groups | ESC: Clear Search/Exit Group Select | Enter: Reveal", curses.A_DIM)

            stdscr.refresh()

    except KeyboardInterrupt:
        print("\nExiting.") # Handle exit gracefully
    finally:
        # Ensure nodelay is set to False for clean exit of curses
        stdscr.nodelay(False)
        stdscr.echo()
        curses.curs_set(1)

parser = argparse.ArgumentParser(description="Aegis Authenticator CLI in Python.", prog="aegis-cli")
parser.add_argument("vault_path", nargs="?", help="Path to the Aegis vault file. If not provided, attempts to find the latest in default locations.", default=None)
parser.add_argument("-d", "--vault-dir", help="Directory to search for vault files. Defaults to current directory.", default=".")
parser.add_argument("-u", "--uuid", help="Display OTP for a specific entry UUID.")
parser.add_argument("-g", "--group", help="Filter OTP entries by a specific group name.")
parser.add_argument("--no-color", action="store_true", help="Disable colored output.")


if __name__ == "__main__":
    args = parser.parse_args()

    password = os.getenv("AEGIS_CLI_PASSWORD")
    if not password:
        try:
            password = getpass.getpass("Enter vault password: ")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0) # Exit cleanly

    curses.wrapper(cli_main, args, password)