import curses

def _calculate_column_widths(stdscr, max_cols, display_list, group_selection_mode):
    """Calculates optimal column widths for TUI display."""
    max_rows, max_cols = stdscr.getmaxyx()

    # Define box dimensions. Leave 1 line for top/bottom borders + 1 for input prompt.
    box_width = max(2, max_cols)

    # Initialize max lengths with header lengths
    # We removed ID ("#") column, so we start with Issuer
    max_issuer_len = len("Issuer")
    max_name_len = len("Name")
    max_code_len = len("Code")
    max_group_len = len("Group")
    max_note_len = len("Note")

    if not group_selection_mode:
        for i, item in enumerate(display_list):
            if len(item["issuer"]) > max_issuer_len: max_issuer_len = len(item["issuer"])
            if len(item["name"]) > max_name_len: max_name_len = len(item["name"])
            if len(item["groups"]) > max_group_len: max_group_len = len(item["groups"])
            if len(item["note"]) > max_note_len: max_note_len = len(item["note"])
    else:
         for item in display_list:
            if len(item["name"]) > max_name_len: max_name_len = len(item["name"])

    # Re-adjust max_len for headers to ensure they fit
    max_issuer_len = max(len("Issuer"), max_issuer_len)
    max_name_len = max(len("Name"), max_name_len)
    max_code_len = 6 # Fixed width for code (usually 6 digits)
    max_group_len = max(len("Group"), max_group_len)
    max_note_len = max(len("Note"), max_note_len)

    # Adjust inner width to allow for 1 space padding on left (col 1) and right (col width-2)
    # Content starts at col 2.
    inner_box_content_width = max(0, box_width - 4)

    separator_len = 3
    num_separators = 4 # Between 5 columns (Issuer, Name, Code, Group, Note)
    
    # Calculate fixed/base widths
    fixed_otp_display_width = max_code_len + (num_separators * separator_len)
    remaining_dynamic_width = max(0, inner_box_content_width - fixed_otp_display_width)

    if not group_selection_mode:
        # Distribute remaining width
        # Issuer: 25%, Name: 30%, Group: 20%, Note: Rest
        ideal_max_issuer_len = int(remaining_dynamic_width * 0.25)
        ideal_max_name_len = int(remaining_dynamic_width * 0.30)
        ideal_max_group_len = int(remaining_dynamic_width * 0.20)
        
        final_issuer_len = min(max_issuer_len, ideal_max_issuer_len)
        final_name_len = min(max_name_len, ideal_max_name_len)
        final_group_len = min(max_group_len, ideal_max_group_len)
        
        consumed = final_issuer_len + final_name_len + final_group_len
        final_note_len = max(len("Note"), remaining_dynamic_width - consumed)
        
        max_issuer_len = final_issuer_len
        max_name_len = final_name_len
        max_group_len = final_group_len
        max_note_len = final_note_len
    else:
        # Group mode uses simple layout
        pass

    return max_issuer_len, max_name_len, max_code_len, max_group_len, max_note_len, inner_box_content_width

def draw_main_screen(
    stdscr, max_rows, max_cols, display_list, selected_row, search_term,
    current_mode, group_selection_mode, current_group_filter,
    cli_args_group, colors, curses_colors_enabled, scroll_offset=0
):
    NORMAL_TEXT_COLOR = colors["NORMAL_TEXT_COLOR"]
    HIGHLIGHT_COLOR = colors["HIGHLIGHT_COLOR"]

    stdscr.clear()

    row = 0
    header_row_offset = 0

    if group_selection_mode:
        stdscr.addstr(row, 0, "--- Select Group (Ctrl+G/Esc to cancel) ---")
    elif current_mode == "search":
        if current_group_filter:
            stdscr.addstr(row, 0, f"--- Group: {current_group_filter} (Ctrl+G to clear) ---")
        elif search_term:
            stdscr.addstr(row, 0, f"--- Search: {search_term} ---")
        elif cli_args_group:
            stdscr.addstr(row, 0, f"--- Group: {cli_args_group} ---")
        else:
            stdscr.addstr(row, 0, "--- All OTPs ---")
    row += 1
    header_row_offset = row

    box_height = max_rows - header_row_offset - 3
    box_width = max_cols

    if box_height < 2: box_height = 2
    if box_width < 2: box_width = 2

    # Draw Box
    # Top
    stdscr.addch(row, 0, curses.ACS_ULCORNER)
    stdscr.hline(row, 1, curses.ACS_HLINE, box_width - 2)
    stdscr.addch(row, box_width - 1, curses.ACS_URCORNER)
    row += 1

    # Middle
    for r in range(row, row + box_height - 1):
        stdscr.addch(r, 0, curses.ACS_VLINE)
        stdscr.addch(r, box_width - 1, curses.ACS_VLINE)

    # Bottom
    stdscr.addch(row + box_height - 1, 0, curses.ACS_LLCORNER)
    stdscr.hline(row + box_height - 1, 1, curses.ACS_HLINE, box_width - 2)
    stdscr.addch(row + box_height - 1, box_width - 1, curses.ACS_LRCORNER)

    row = header_row_offset + 1

    # Calculate Widths (No Index)
    max_issuer_len, max_name_len, max_code_len, max_group_len, max_note_len, inner_box_content_width = \
        _calculate_column_widths(stdscr, max_cols, display_list, group_selection_mode)

    # Define Separator Gap
    sep = "    " # 4 spaces

    if not group_selection_mode:
        # Draw Header
        # Issuer             Name               Code    Group              Note
        header_str = (
            "Issuer".ljust(max_issuer_len) + sep +
            "Name".ljust(max_name_len) + sep +
            "Code".ljust(max_code_len) + sep +
            "Group".ljust(max_group_len) + sep +
            "Note".ljust(max_note_len)
        )
        stdscr.addstr(row, 2, header_str[:inner_box_content_width], curses.A_BOLD)
        row += 1

        # Draw Separator Line
        separator_line = (
            ("-" * max_issuer_len) + sep +
            ("-" * max_name_len) + sep +
            ("-" * max_code_len) + sep +
            ("-" * max_group_len) + sep +
            ("-" * max_note_len)
        )
        stdscr.addstr(row, 2, separator_line[:inner_box_content_width], curses.A_DIM)
        row += 1

    # Max visible items reduced by header lines
    max_visible_items = max(0, box_height - 2 - (2 if not group_selection_mode else 0))

    if group_selection_mode:
        total_virtual_items = len(display_list) + 1
        start_idx = scroll_offset
        end_idx = min(total_virtual_items, scroll_offset + max_visible_items)
        
        for v_idx in range(start_idx, end_idx):
            if row >= max_rows - 2: break
            
            if v_idx == 0:
                display_attr = HIGHLIGHT_COLOR if selected_row == -1 else NORMAL_TEXT_COLOR
                all_otps_text = "-- All OTPs --"
                stdscr.addstr(row, 2, all_otps_text[:inner_box_content_width], display_attr)
            else:
                item = display_list[v_idx - 1]
                is_selected = (selected_row == (v_idx - 1))
                display_attr = HIGHLIGHT_COLOR if is_selected else NORMAL_TEXT_COLOR
                
                # Simple list for groups
                group_name_str = item["name"][:inner_box_content_width - 2].ljust(inner_box_content_width - 2)
                stdscr.addstr(row, 2, group_name_str, display_attr)
            
            row += 1
    else:
        start_idx = scroll_offset
        end_idx = min(len(display_list), scroll_offset + max_visible_items)
        
        for i in range(start_idx, end_idx):
            if row >= max_rows - 2: break
            
            item = display_list[i]
            display_attr = HIGHLIGHT_COLOR if i == selected_row else NORMAL_TEXT_COLOR

            issuer_str = item["issuer"][:max_issuer_len].ljust(max_issuer_len)
            name_str = item["name"][:max_name_len].ljust(max_name_len)
            code_str = "******".ljust(max_code_len) # Placeholder code
            group_str = item["groups"][:max_group_len].ljust(max_group_len)
            note_str = item["note"][:max_note_len].ljust(max_note_len)

            line = (
                issuer_str + sep +
                name_str + sep +
                code_str + sep +
                group_str + sep +
                note_str
            )
            stdscr.addstr(row, 2, line[:inner_box_content_width], display_attr)
            row += 1

    # Prompt
    prompt_string_prefix = "Search: " if current_mode == "search" else "Group Filter: "
    current_input_text = search_term if current_mode == "search" else (search_term if group_selection_mode else "")
    prompt_row = max_rows - 1
    if prompt_row < 0: prompt_row = 0
    stdscr.addstr(prompt_row, 0, (prompt_string_prefix + current_input_text)[:max_cols], NORMAL_TEXT_COLOR)

    # Instructions
    stdscr.addstr(max_rows - 2, 0, "Ctrl+G: Toggle Groups | ESC: Clear Search/Exit Group Select | Enter: Reveal", curses.A_DIM)

    stdscr.refresh()
    return max_visible_items