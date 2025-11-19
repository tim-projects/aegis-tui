Rework the interactive OTP selection to use a "search as you type" method.

**Plan:**

1.  **Read user input character by character using `readchar`:** Implement non-blocking input to capture keystrokes without waiting for the Enter key. Use the `readchar` library for this.
2.  **Implement dynamic filtering:**
    *   As each character is typed, filter the `display_data` list case-insensitively.
    *   The search should match against the issuer, name, groups, or note fields of the OTP entries.
    *   If the input is a number, it should also match against the 1-based index (e.g., typing '1' filters to item 1, typing 'google' filters to entries with 'google' in their fields).
3.  **Update display in real-time:** Re-render the filtered list of OTPs after each keystroke.
4.  **Handle OTP revelation (interactive mode always):**
    *   **Default state:** All OTPs are hidden (`******`).
    *   **Single result revelation:** If the filtered list contains *exactly one* item, automatically reveal its OTP code.
    *   **User selection (future):** If the user presses Enter with a non-empty filtered list, and if there's an unambiguous selection (e.g., only one item left), reveal its OTP. (This might be a later refinement, focus on single result first).
    *   If the user clears the search, clear any active OTP revelation (unless it was a single item originally and remains the only item).
5.  **Maintain revealed state:** The `revealed_otps` set logic should ensure that an OTP, once explicitly selected or automatically revealed (due to a single filtered item), remains visible until a *different* item is specifically selected or the search input changes sufficiently to remove it from the filtered `revealed_otps` set.
6.  **Refine input prompts:** Adjust the prompt to guide the user on how to search and select.
7.  **Error handling and edge cases:** Consider scenarios like no matches, backspace, and special characters.
8.  **Add/Update Unit Tests:** Write tests for the new filtering and interactive display logic.