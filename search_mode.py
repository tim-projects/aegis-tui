import curses

from tui_display import draw_main_screen

def run_search_mode(
    stdscr, vault_data, group_names, args, colors, curses_colors_enabled
):
    """Runs the interactive search mode for OTP entries."""

    NORMAL_TEXT_COLOR = colors["NORMAL_TEXT_COLOR"]
    HIGHLIGHT_COLOR = colors["HIGHLIGHT_COLOR"]
    REVEAL_HIGHLIGHT_COLOR = colors["REVEAL_HIGHLIGHT_COLOR"]
    RED_TEXT_COLOR = colors["RED_TEXT_COLOR"]
    BOLD_WHITE_COLOR = colors["BOLD_WHITE_COLOR"]

    # Initialize state variables
    search_term = ""
    current_mode = "search" # "search" or "group_select"
    selected_row = -1 # Track the currently highlighted row for navigation (-1 for no selection)
    char = curses.ERR # Initialize char to prevent UnboundLocalError
    previous_search_term = ""
    current_group_filter = args.group # Use CLI group filter if provided
    group_selection_mode = False
    entry_to_reveal_uuid = None # Store the UUID of the selected entry
    needs_redraw = True # Initial redraw needed

    # Prepare initial data based on CLI arguments (group filter)
    all_entries = []
    for i, entry in enumerate(vault_data.db.entries):
        all_entries.append({
            "index": i,
            "name": entry.name,
            "issuer": entry.issuer if entry.issuer else "",
            "groups": ", ".join(group_names.get(g, g) for g in entry.groups) if entry.groups else "",
            "note": entry.note if entry.note else "",
            "uuid": entry.uuid
        })
    all_entries.sort(key=lambda x: x["name"].lower())

    if current_group_filter:
        # Apply initial group filter
        display_list_for_selection = [entry for entry in all_entries if current_group_filter in entry["groups"]]
    else:
        display_list_for_selection = all_entries

    # Ensure selected_row is valid for the initial display
    if len(display_list_for_selection) > 0:
        selected_row = 0
    else:
        selected_row = -1

    # --- Main Search Loop ---
    while True:
        # Prepare display list based on current mode and filters
        if current_mode == "search" and not group_selection_mode:
            if current_group_filter:
                display_list = [entry for entry in all_entries if current_group_filter in entry["groups"] and search_term.lower() in entry["name"].lower()]
            else:
                display_list = [entry for entry in all_entries if search_term.lower() in entry["name"].lower()]
        elif group_selection_mode:
            # In group selection mode, display available groups
            groups_list = [{"name": group.name, "uuid": group.uuid} for group in vault_data.db.groups]
            groups_list.sort(key=lambda x: x["name"].lower()) # Sort groups alphabetically

            # Filter groups by search_term if in group selection mode
            if search_term:
                display_list = [group for group in groups_list if search_term.lower() in group["name"].lower()]
            else:
                display_list = groups_list # No search term, show all groups

            # Adjust selected_row for group list
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

        # If no items are in display_list, reset selected_row
        if len(display_list) == 0:
            selected_row = -1
        else:
            # Ensure selected_row is within bounds for the current display_list
            selected_row = max(0, min(selected_row, len(display_list) - 1)) if selected_row != -1 else (0 if len(display_list) > 0 else -1)

        # --- Input Handling ---
        char = stdscr.getch() # Get a single character

        if char != curses.ERR: # Only process if a key was actually pressed
            needs_redraw = True # Input occurred, so redraw the screen
            if char == curses.KEY_RESIZE:
                # Terminal resized, re-get dimensions and force redraw
                max_rows, max_cols = stdscr.getmaxyx()
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
                elif char == 27 or char == 7: # ESC or Ctrl+G to cancel group selection
                    group_selection_mode = False
                    current_group_filter = None
                    search_term = "" # Clear search term
                    # Reset selected_row to the first item in the main OTP list if available
                    selected_row = 0 if len(all_entries) > 0 else -1
                elif char == curses.KEY_ENTER or char in [10, 13]:
                    if selected_row == -1: # "All OTPs" selected
                        current_group_filter = None # Clear filter
                    elif selected_row != -1 and len(display_list) > 0:
                        selected_group = display_list[selected_row]
                        current_group_filter = selected_group["name"]
                    # revealed_otps.clear() # Clear revealed OTPs when a new group filter is applied or cleared
                    group_selection_mode = False
                    current_mode = "search" # Explicitly set mode to search after group selection
                    # Reset selected_row for the filtered OTP list
                    initial_filtered_entries = [entry for entry in all_entries if current_group_filter in entry["groups"]] if current_group_filter else all_entries
                    selected_row = 0 if len(initial_filtered_entries) > 0 else -1
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
                    # revealed_otps.clear()
                    current_group_filter = None # Clear group filter on ESC
                    # Reset selected_row for the OTP list
                    selected_row = 0 if len(all_entries) > 0 else -1
                elif char in [curses.KEY_BACKSPACE, 127, 8]: # Backspace key
                    if search_term: # Only modify search_term if it's not empty
                        search_term = search_term[:-1]
                elif 32 <= char < 127: # Printable character
                    search_term += chr(char)
                elif char == 7: # Ctrl+G to toggle group selection mode
                    group_selection_mode = not group_selection_mode
                    # revealed_otps.clear() # Clear revealed OTPs on mode change
                    if group_selection_mode:
                        selected_row = -1 # Default to "All OTPs" in group selection mode
                        search_term = "" # Clear search term when entering group selection
                    else:
                        current_group_filter = None # Clear filter if exiting group selection mode
                        # Reset selected_row for the OTP list
                        selected_row = 0 if len(all_entries) > 0 else -1
                        search_term = "" # Clear search term when exiting group selection
                elif char == 3: # Ctrl+C to exit application
                    return None # Signal to exit
                elif char == curses.KEY_ENTER or char in [10, 13]:
                    # Only reveal if an item is selected
                    if selected_row != -1 and len(display_list) > 0:
                        entry_to_reveal_uuid = display_list[selected_row]["uuid"] # Return the UUID of the selected entry
                        break # Exit search loop to process reveal
        else:
            import time
            time.sleep(0.01) # Small delay to prevent tight loop if no input

        if needs_redraw:
            max_rows, max_cols = stdscr.getmaxyx()
            draw_main_screen(
                stdscr, max_rows, max_cols, display_list, selected_row, search_term,
                current_mode, group_selection_mode, current_group_filter, args.group,
                colors, curses_colors_enabled
            )
            needs_redraw = False # Redraw completed

    # Return the selected UUID or None if user exited
    return entry_to_reveal_uuid
