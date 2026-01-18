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

    scroll_offset = 0
    items_per_page = 10 # Initial estimate, will be updated by draw_main_screen

    # --- Main Search Loop ---
    while True:
        # Prepare display list based on current mode and filters
        if current_mode == "search" and not group_selection_mode:
            term = search_term.lower()
            if current_group_filter:
                display_list = [
                    entry for entry in all_entries 
                    if current_group_filter in entry["groups"] and 
                    (term in entry["name"].lower() or term in entry["issuer"].lower())
                ]
            else:
                display_list = [
                    entry for entry in all_entries 
                    if term in entry["name"].lower() or term in entry["issuer"].lower()
                ]
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
            # Note: We don't auto-adjust selected_row here because it messes up navigation state
            # unless the list drastically changed (e.g. search filter).
            # We'll rely on bounds checking below.
        else:
            display_list = all_entries # Use filtered entries for display

        # If no items are in display_list, reset selected_row
        if len(display_list) == 0:
            if not group_selection_mode:
                selected_row = -1
            else:
                # In group mode, we always have "All OTPs" (index -1) unless filtered out? 
                # Actually "All OTPs" is static. If filter excludes all groups, we can still select "All OTPs".
                # If search term doesn't match "All OTPs" (conceptually), maybe? 
                # For now, let's assume "All OTPs" is always selectable if search_term is empty or ignored for it.
                # But if we type "Fina", "All OTPs" shouldn't show? 
                # Current display logic: "All OTPs" is index 0 of virtual list.
                # Let's keep it simple: "All OTPs" is always there as index -1.
                if selected_row != -1:
                     selected_row = -1
        else:
            # Ensure selected_row is within bounds for the current display_list
            selected_row = max(-1 if group_selection_mode else 0, min(selected_row, len(display_list) - 1))

        if needs_redraw:
            max_rows, max_cols = stdscr.getmaxyx()
            items_per_page = draw_main_screen(
                stdscr, max_rows, max_cols, display_list, selected_row, search_term,
                current_mode, group_selection_mode, current_group_filter, args.group,
                colors, curses_colors_enabled, scroll_offset
            )
            needs_redraw = False # Redraw completed

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
                    # Virtual index mapping: -1 -> 0, 0 -> 1, ...
                    current_v_idx = selected_row + 1
                    if current_v_idx > 0:
                        current_v_idx -= 1
                        selected_row = current_v_idx - 1
                        
                        # Scrolling Up
                        if current_v_idx < scroll_offset:
                            scroll_offset = current_v_idx
                            
                elif char == curses.KEY_DOWN:
                    current_v_idx = selected_row + 1
                    total_virtual_items = len(display_list) + 1
                    if current_v_idx < total_virtual_items - 1:
                        current_v_idx += 1
                        selected_row = current_v_idx - 1
                        
                        # Scrolling Down
                        if current_v_idx >= scroll_offset + items_per_page:
                            scroll_offset = current_v_idx - items_per_page + 1

                elif char == 27 or char == 7: # ESC or Ctrl+G to cancel group selection
                    group_selection_mode = False
                    current_group_filter = None
                    search_term = "" # Clear search term
                    # Reset selected_row to the first item in the main OTP list if available
                    selected_row = 0 if len(all_entries) > 0 else -1
                    scroll_offset = 0 # Reset scroll
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
                    scroll_offset = 0 # Reset scroll
                    search_term = "" # Clear search term
            elif current_mode == "search": # Normal search mode
                if char == curses.KEY_UP:
                    if len(display_list) > 0:
                        selected_row = max(0, selected_row - 1)
                        if selected_row < scroll_offset:
                            scroll_offset = selected_row
                    else:
                        selected_row = -1
                elif char == curses.KEY_DOWN:
                    if len(display_list) > 0:
                        selected_row = min(len(display_list) - 1, selected_row + 1)
                        if selected_row >= scroll_offset + items_per_page:
                            scroll_offset = selected_row - items_per_page + 1
                    else:
                        selected_row = -1
                elif char == 27: # ESC key
                    search_term = ""
                    # revealed_otps.clear()
                    current_group_filter = None # Clear group filter on ESC
                    # Reset selected_row for the OTP list
                    selected_row = 0 if len(all_entries) > 0 else -1
                    scroll_offset = 0
                elif char in [curses.KEY_BACKSPACE, 127, 8]: # Backspace key
                    if search_term: # Only modify search_term if it's not empty
                        search_term = search_term[:-1]
                        scroll_offset = 0 # Reset scroll on search change
                elif 32 <= char < 127: # Printable character
                    search_term += chr(char)
                    scroll_offset = 0 # Reset scroll on search change
                elif char == 7: # Ctrl+G to toggle group selection mode
                    group_selection_mode = not group_selection_mode
                    # revealed_otps.clear() # Clear revealed OTPs on mode change
                    if group_selection_mode:
                        selected_row = -1 # Default to "All OTPs" in group selection mode
                        search_term = "" # Clear search term when entering group selection
                        scroll_offset = 0
                    else:
                        current_group_filter = None # Clear filter if exiting group selection mode
                        # Reset selected_row for the OTP list
                        selected_row = 0 if len(all_entries) > 0 else -1
                        search_term = "" # Clear search term when exiting group selection
                        scroll_offset = 0
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

    # Return the selected UUID or None if user exited
    return entry_to_reveal_uuid
