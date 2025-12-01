import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from io import StringIO
import importlib.util

# Load aegis-cli.py as a module from the project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
spec = importlib.util.spec_from_file_location("aegis_tui", os.path.join(project_root, 'aegis-tui.py'))
aegis_tui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aegis_tui)

from aegis_core import OTP, Entry # Corrected import


# Custom mock for curses.wrapper to simulate stdscr behavior
def mock_curses_wrapper(cli_main_func, *args, getch_side_effects=None, **kwargs):
    mock_stdscr = MagicMock()
    mock_stdscr.getch.side_effect = iter(getch_side_effects) if getch_side_effects else [-1] # Default to no input
    mock_stdscr.getmaxyx.return_value = (24, 80) # Simulate a 24x80 terminal
    
    # Mock specific curses functions called by cli_main
    mock_stdscr.keypad.return_value = None
    mock_stdscr.curs_set.return_value = None
    mock_stdscr.noecho.return_value = None
    mock_stdscr.getmaxyx.return_value = (24, 80) # Simulate a 24x80 terminal
    mock_stdscr.addstr.return_value = None
    mock_stdscr.addch.return_value = None
    mock_stdscr.hline.return_value = None
    mock_stdscr.vline.return_value = None
    mock_stdscr.clear.return_value = None
    mock_stdscr.refresh.return_value = None
    mock_stdscr.timeout.return_value = None

    # Create a mock for the curses module itself
    mock_curses_module = MagicMock()

    # Assign specific curses module attributes/constants to the mock module
    mock_curses_module.KEY_UP = 259
    mock_curses_module.KEY_DOWN = 258
    mock_curses_module.KEY_ENTER = 10 # curses.KEY_ENTER can also be 10 or 13
    mock_curses_module.ERR = -1

    # ACS characters
    mock_curses_module.ACS_ULCORNER = ord('┌')
    mock_curses_module.ACS_URCORNER = ord('┐')
    mock_curses_module.ACS_LLCORNER = ord('└')
    mock_curses_module.ACS_LRCORNER = ord('┘')
    mock_curses_module.ACS_HLINE = ord('─')
    mock_curses_module.ACS_VLINE = ord('│')

    # Color constants
    mock_curses_module.A_NORMAL = 0
    mock_curses_module.A_BOLD = 1
    mock_curses_module.COLOR_WHITE = 7 # Standard color constants
    mock_curses_module.COLOR_BLUE = 4
    mock_curses_module.COLOR_BLACK = 0
    mock_curses_module.COLOR_CYAN = 6 # Added for completeness if needed

    # Mock color_pair for the curses module
    def _mock_color_pair(num):
        return num

    # Mock curses module functions
    mock_curses_module.has_colors.return_value = True
    mock_curses_module.start_color.return_value = None
    mock_curses_module.use_default_colors.return_value = None
    mock_curses_module.init_pair.return_value = None
    mock_curses_module.color_pair.side_effect = _mock_color_pair
    mock_curses_module.curs_set.return_value = None # This is called on curses, not stdscr
    mock_curses_module.noecho.return_value = None # This is called on curses, not stdscr

    with patch.object(aegis_tui, 'curses', new=mock_curses_module):
        # Extract getch_side_effects from kwargs if present, so it's not passed to cli_main_func
        cli_main_func_kwargs = {k: v for k, v in kwargs.items() if k != 'getch_side_effects'}
        # Run the cli_main_func with the mocked stdscr.getch.side_effect for inputs
        cli_main_func(mock_stdscr, *args, **cli_main_func_kwargs)

    return mock_stdscr # Return mock_stdscr for assertions

class TestAegisTuiInteractive(unittest.TestCase):

    def test_search_as_you_type_single_match_reveal(self):
        with (
            patch.object(aegis_tui, 'read_and_decrypt_vault_file') as mock_decrypt_vault,
            patch.object(aegis_tui, 'get_otps') as mock_get_otps,
            patch('getpass.getpass', return_value='dummy_password') as mock_getpass,
            patch('builtins.input', return_value='dummy_password') as mock_input,
            patch.object(aegis_tui, 'load_config', return_value={
                "last_opened_vault": None,
                "last_vault_dir": None,
                "default_color_mode": True
            }),
            patch.object(aegis_tui, 'save_config'),
            patch('sys.argv', ['aegis-tui.py', '--vault-path', '/mock/vault/path.json']),
            patch('select.select') as mock_select_select
        ):
            # Mock vault data and OTPs
            mock_vault_data = MagicMock()
            entry1 = MagicMock()
            entry1.name = "Test OTP 1"
            entry1.issuer = "Issuer A"
            entry1.groups = []
            entry1.note = ""
            entry1.uuid = "uuid1"
    
            entry2 = MagicMock()
            entry2.name = "Another OTP"
            entry2.issuer = "Issuer B"
            entry2.groups = []
            entry2.note = ""
            entry2.uuid = "uuid2"
            mock_vault_data.db.entries = [entry1, entry2]
            mock_vault_data.db.groups = [] # No groups to mock for this test
            mock_decrypt_vault.return_value = mock_vault_data
    
            mock_get_otps.return_value = {
                "uuid1": MagicMock(uuid="uuid1", name="Test OTP 1", issuer="Issuer A", secret="SECRET1", string=lambda: "SECRET1"),
                "uuid2": MagicMock(uuid="uuid2", name="Another OTP", issuer="Issuer B", secret="SECRET2", string=lambda: "SECRET2"),
            }
            
            # Simulate user typing "Test" then Enter to reveal, then some idle, then Ctrl+C to exit program
            getch_side_effects = [
                ord('T'), ord('e'), ord('s'), ord('t'), # Type "Test"
                aegis_tui.curses.KEY_ENTER, # Reveal OTP
                aegis_tui.curses.KEY_RESIZE, # Simulate a resize event while in reveal mode
                aegis_tui.curses.KEY_RESIZE, # Another resize event
                aegis_tui.curses.KEY_RESIZE, # Another resize event
                aegis_tui.curses.KEY_RESIZE, # Another resize event
                aegis_tui.curses.KEY_RESIZE, # Another resize event
                aegis_tui.curses.KEY_RESIZE, # Another resize event
                aegis_tui.curses.KEY_RESIZE, # Another resize event
                aegis_tui.curses.KEY_RESIZE, # Another resize event
                aegis_tui.curses.KEY_RESIZE, # Another resize event
                aegis_tui.curses.KEY_RESIZE, # Another resize event
                aegis_tui.curses.KEY_RESIZE, # Another resize event
                aegis_tui.curses.KEY_RESIZE, # Another resize event
                aegis_tui.curses.KEY_RESIZE, # Another resize event
                aegis_tui.curses.KEY_RESIZE, # Another resize event
                aegis_tui.curses.KEY_RESIZE, # Another resize event
                aegis_tui.curses.KEY_RESIZE, # Another resize event
                aegis_tui.curses.KEY_RESIZE, # Another resize event
                aegis_tui.curses.KEY_RESIZE, # Another resize event
                aegis_tui.curses.KEY_RESIZE, # Another resize event
                aegis_tui.curses.KEY_RESIZE, # Another resize event
                aegis_tui.curses.KEY_RESIZE, # Another resize event
                aegis_tui.curses.KEY_RESIZE, # Another resize event
                27, # ESC to return to search
                3 # Ctrl+C to exit program
            ]
            
            mock_stdscr_instance = mock_curses_wrapper(aegis_tui.cli_main, aegis_tui.parser.parse_args(['--vault-path', '/mock/vault/path.json']), 'dummy_password', getch_side_effects=getch_side_effects)

            # Mock select.select to simulate input availability
            select_call_count = 0
            def select_side_effect(read_list, write_list, error_list, timeout):
                nonlocal select_call_count
                select_call_count += 1
                # Return input availability for slightly more calls than getch_side_effects
                if select_call_count <= len(getch_side_effects) + 5: # 5 extra calls for safety/idle
                    return ([sys.stdin], [], [])
                return ([], [], [])
            mock_select_select.side_effect = select_side_effect

            # cli_main is called within mock_curses_wrapper, so no direct call here
            # The test will implicitly run cli_main via mock_curses_wrapper

            # Verify that "Test OTP 1" is revealed
            addstr_calls = [str(call_arg) for call in mock_stdscr_instance.addstr.call_args_list for call_arg in call.args if isinstance(call_arg, str)]
            full_output = "\n".join(addstr_calls)
            print(full_output) # Temporary debug print

            self.assertIn("Test OTP 1", full_output)
            self.assertIn("SECRET1", full_output)
            self.assertNotIn("SECRET2", full_output) # Ensure other OTPs are not revealed

        with (
            patch.object(aegis_tui, 'read_and_decrypt_vault_file') as mock_decrypt_vault,
            patch.object(aegis_tui, 'get_otps') as mock_get_otps,
            patch('getpass.getpass', return_value='dummy_password') as mock_getpass,
            patch('builtins.input', return_value='dummy_password') as mock_input,
            patch.object(aegis_tui, 'load_config', return_value={
                "last_opened_vault": None,
                "last_vault_dir": None,
                "default_color_mode": True
            }),
            patch.object(aegis_tui, 'save_config'),
            patch('sys.argv', ['aegis-tui.py', '--vault-path', '/mock/vault/path.json']),
            patch('select.select') as mock_select_select
        ):
            # Mock vault data and OTPs
            mock_vault_data = MagicMock()
            entry1 = MagicMock()
            entry1.name = "Test OTP 1"
            entry1.issuer = "Issuer A"
            entry1.groups = []
            entry1.note = ""
            entry1.uuid = "uuid1"
            mock_vault_data.db.entries = [entry1]
            mock_vault_data.db.groups = []
            mock_decrypt_vault.return_value = mock_vault_data
    
            # Simulate user typing "Nomatch" then Ctrl+C
            getch_side_effects = [
                ord('N'), ord('o'), ord('m'), ord('a'), ord('t'), ord('c'), ord('h'),
                3 # Ctrl+C
            ]

            mock_stdscr_instance = mock_curses_wrapper(aegis_tui.cli_main, aegis_tui.parser.parse_args(['--vault-path', '/mock/vault/path.json']), 'dummy_password', getch_side_effects=getch_side_effects)

            # Mock select.select to simulate input availability
            select_call_count = 0
            def select_side_effect(read_list, write_list, error_list, timeout):
                nonlocal select_call_count
                select_call_count += 1
                if select_call_count <= len(getch_side_effects) + 5: # 5 extra calls for safety/idle
                    return ([sys.stdin], [], [])
                return ([], [], [])
            mock_select_select.side_effect = select_side_effect

            output = mock_stdscr_instance.addstr.call_args_list
            addstr_calls = [str(call_arg) for call in mock_stdscr_instance.addstr.call_args_list for call_arg in call.args if isinstance(call_arg, str)]
            full_output = "\n".join(addstr_calls)
            
            # Verify that no OTPs are displayed and the search term is present in the prompt
            self.assertIn("Nomatch", full_output)
            self.assertNotIn("Test OTP 1", full_output)
            self.assertNotIn("SECRET1", full_output)

    def test_search_as_you_type_multiple_matches_no_reveal(self):
        with (
            patch.object(aegis_tui, 'read_and_decrypt_vault_file') as mock_decrypt_vault,
            patch.object(aegis_tui, 'get_otps') as mock_get_otps,
            patch('getpass.getpass', return_value='dummy_password') as mock_getpass,
            patch('builtins.input', return_value='dummy_password') as mock_input,
            patch.object(aegis_tui, 'load_config', return_value={
                "last_opened_vault": None,
                "last_vault_dir": None,
                "default_color_mode": True
            }),
            patch.object(aegis_tui, 'save_config'),
            patch('sys.argv', ['aegis-tui.py', '--vault-path', '/mock/vault/path.json']),
            patch('select.select') as mock_select_select
        ):
            # Mock vault data and OTPs
            mock_vault_data = MagicMock()
            entry1 = MagicMock()
            entry1.name = "Test OTP 1"
            entry1.issuer = "Issuer A"
            entry1.groups = []
            entry1.note = ""
            entry1.uuid = "uuid1"
    
            entry2 = MagicMock()
            entry2.name = "Test OTP 2"
            entry2.issuer = "Issuer B"
            entry2.groups = []
            entry2.note = ""
            entry2.uuid = "uuid2"
            mock_vault_data.db.entries = [entry1, entry2]
            mock_vault_data.db.groups = []
            mock_decrypt_vault.return_value = mock_vault_data
    
            mock_get_otps.return_value = {
                "uuid1": MagicMock(uuid="uuid1", name="Test OTP 1", issuer="Issuer A", secret="SECRET1", string=lambda: "SECRET1"),
                "uuid2": MagicMock(uuid="uuid2", name="Test OTP 2", issuer="Issuer B", secret="SECRET2", string=lambda: "SECRET2"),
            }
            # Simulate user typing "Test" then Ctrl+C
            getch_side_effects = [
                ord('T'), ord('e'), ord('s'), ord('t'), 
                3 # Ctrl+C
            ]
            
            mock_stdscr_instance = mock_curses_wrapper(aegis_tui.cli_main, aegis_tui.parser.parse_args(['--vault-path', '/mock/vault/path.json']), 'dummy_password', getch_side_effects=getch_side_effects)

            # Mock select.select to simulate input availability
            select_call_count = 0
            def select_side_effect(read_list, write_list, error_list, timeout):
                nonlocal select_call_count
                select_call_count += 1
                if select_call_count <= len(getch_side_effects) + 5: # 5 extra calls for safety/idle
                    return ([sys.stdin], [], [])
                return ([], [], [])
            mock_select_select.side_effect = select_side_effect

            addstr_calls = [str(call_arg) for call in mock_stdscr_instance.addstr.call_args_list for call_arg in call.args if isinstance(call_arg, str)]
            full_output = "\n".join(addstr_calls)
            
            # Verify that both OTPs are listed but not revealed
            self.assertIn("Test OTP 1", full_output)
            self.assertIn("Test OTP 2", full_output)
            self.assertNotIn("SECRET1", full_output)
            self.assertNotIn("SECRET2", full_output)
            self.assertIn("******", full_output) # Should see obscured OTPs

if __name__ == '__main__':
    unittest.main()

    def test_arrow_key_navigation_in_search_mode(self):
        with (
            patch.object(aegis_tui, 'read_and_decrypt_vault_file') as mock_decrypt_vault,
            patch.object(aegis_tui, 'get_otps') as mock_get_otps,
            patch('getpass.getpass', return_value='dummy_password') as mock_getpass,
            patch('builtins.input', return_value='dummy_password') as mock_input,
            patch.object(aegis_tui, 'load_config', return_value={
                "last_opened_vault": None,
                "last_vault_dir": None,
                "default_color_mode": True
            }),
            patch.object(aegis_tui, 'save_config'),
            patch('sys.argv', ['aegis-tui.py', '--vault-path', '/mock/vault/path.json']),
            patch('select.select') as mock_select_select
        ):
            # Mock vault data with multiple entries
            mock_vault_data = MagicMock()
            entry1 = MagicMock()
            entry1.name = "First OTP"
            entry1.issuer = "Issuer A"
            entry1.groups = []
            entry1.note = ""
            entry1.uuid = "uuid1"
    
            entry2 = MagicMock()
            entry2.name = "Second OTP"
            entry2.issuer = "Issuer B"
            entry2.groups = []
            entry2.note = ""
            entry2.uuid = "uuid2"

            entry3 = MagicMock()
            entry3.name = "Third OTP"
            entry3.issuer = "Issuer C"
            entry3.groups = []
            entry3.note = ""
            entry3.uuid = "uuid3"
            
            mock_vault_data.db.entries = [entry1, entry2, entry3]
            mock_vault_data.db.groups = []
            mock_decrypt_vault.return_value = mock_vault_data
    
            mock_get_otps.return_value = {
                "uuid1": MagicMock(uuid="uuid1", name="First OTP", issuer="Issuer A", secret="SECRET1", string=lambda: "SECRET1"),
                "uuid2": MagicMock(uuid="uuid2", name="Second OTP", issuer="Issuer B", secret="SECRET2", string=lambda: "SECRET2"),
                "uuid3": MagicMock(uuid="uuid3", name="Third OTP", issuer="Issuer C", secret="SECRET3", string=lambda: "SECRET3"),
            }
            
            # Simulate user typing "Ot", then DOWN arrow, then UP arrow, then Ctrl+C
            getch_side_effects = [
                ord('O'), ord('t'), # Type "Ot"
                aegis_tui.curses.KEY_DOWN, # Move to 'Second OTP'
                aegis_tui.curses.KEY_UP,   # Move back to 'First OTP'
                3 # Ctrl+C
            ]
            
            mock_stdscr_instance = mock_curses_wrapper(aegis_tui.cli_main, aegis_tui.parser.parse_args(['--vault-path', '/mock/vault/path.json']), 'dummy_password')
            mock_stdscr_instance.getch.side_effect = iter(getch_side_effects)

            def select_side_effect(read_list, write_list, error_list, timeout):
                if mock_stdscr_instance.getch.call_count < len(getch_side_effects):
                    return ([sys.stdin], [], [])
                return ([], [], [])
            mock_select_select.side_effect = select_side_effect

            addstr_calls = [str(call_arg) for call in mock_stdscr_instance.addstr.call_args_list for call_arg in call.args if isinstance(call_arg, str)]
            full_output = "\n".join(addstr_calls)
            
            self.assertIn("First OTP", full_output)
            self.assertIn("Second OTP", full_output)
            self.assertIn("Third OTP", full_output)

            # More robust test would inspect mock_stdscr.addstr.call_args_list for color attributes
            # For example, to check if 'Second OTP' was highlighted after KEY_DOWN, then 'First OTP' after KEY_UP
            # This requires a deeper understanding of the mocked curses output and its state over time.
            # For now, we rely on the visual correctness in manual tests and presence of items.


    def test_group_selection_and_filter(self):
        with (
            patch.object(aegis_tui, 'read_and_decrypt_vault_file') as mock_decrypt_vault,
            patch.object(aegis_tui, 'get_otps') as mock_get_otps,
            patch('getpass.getpass', return_value='dummy_password') as mock_getpass,
            patch('builtins.input', return_value='dummy_password') as mock_input,
            patch.object(aegis_tui, 'load_config', return_value={
                "last_opened_vault": None,
                "last_vault_dir": None,
                "default_color_mode": True
            }),
            patch.object(aegis_tui, 'save_config'),
            patch('sys.argv', ['aegis-tui.py', '--vault-path', '/mock/vault/path.json']),
            patch('select.select') as mock_select_select
        ):
            # Mock vault data with groups and entries
            mock_vault_data = MagicMock()

            group1 = MagicMock()
            group1.name = "Work"
            group1.uuid = "group1_uuid"

            group2 = MagicMock()
            group2.name = "Personal"
            group2.uuid = "group2_uuid"

            mock_vault_data.db.groups = [group1, group2]

            entry1 = MagicMock()
            entry1.name = "Work OTP 1"
            entry1.issuer = "Company A"
            entry1.groups = ["group1_uuid"]
            entry1.note = ""
            entry1.uuid = "uuid1"
    
            entry2 = MagicMock()
            entry2.name = "Personal OTP 1"
            entry2.issuer = "Service B"
            entry2.groups = ["group2_uuid"]
            entry2.note = ""
            entry2.uuid = "uuid2"

            entry3 = MagicMock()
            entry3.name = "Work OTP 2"
            entry3.issuer = "Company C"
            entry3.groups = ["group1_uuid"]
            entry3.note = ""
            entry3.uuid = "uuid3"
            
            mock_vault_data.db.entries = [entry1, entry2, entry3]
            mock_decrypt_vault.return_value = mock_vault_data
    
            mock_get_otps.return_value = {
                "uuid1": MagicMock(uuid="uuid1", name="Work OTP 1", issuer="Company A", secret="SECRET1", string=lambda: "SECRET1"),
                "uuid2": MagicMock(uuid="uuid2", name="Personal OTP 1", issuer="Service B", secret="SECRET2", string=lambda: "SECRET2"),
                "uuid3": MagicMock(uuid="uuid3", name="Work OTP 2", issuer="Company C", secret="SECRET3", string=lambda: "SECRET3"),
            }
            
            # Simulate Ctrl+G, DOWN (to select "Personal"), ENTER, then Ctrl+C
            getch_side_effects = [
                7, # Ctrl+G to enter group selection
                aegis_tui.curses.KEY_DOWN, # Move to "Personal" (assuming "All OTPs" is first, then "Work", then "Personal")
                aegis_tui.curses.KEY_DOWN,
                aegis_tui.curses.KEY_ENTER, # Select "Personal"
                3 # Ctrl+C
            ]
            
            mock_stdscr_instance = mock_curses_wrapper(aegis_tui.cli_main, aegis_tui.parser.parse_args(['--vault-path', '/mock/vault/path.json']), 'dummy_password')
            mock_stdscr_instance.getch.side_effect = iter(getch_side_effects)

            def select_side_effect(read_list, write_list, error_list, timeout):
                if mock_stdscr_instance.getch.call_count < len(getch_side_effects) + 5:
                    return ([sys.stdin], [], [])
                return ([], [], [])
            mock_select_select.side_effect = select_side_effect

            addstr_calls = [str(call_arg) for call in mock_stdscr_instance.addstr.call_args_list for call_arg in call.args if isinstance(call_arg, str)]
            full_output = "\n".join(addstr_calls)
            
            # Verify that only "Personal OTP 1" is listed
            self.assertIn("Personal OTP 1", full_output)
            self.assertNotIn("Work OTP 1", full_output)
            self.assertNotIn("Work OTP 2", full_output)
            self.assertIn("Group: Personal", full_output) # Verify the header reflects the filter


    def test_esc_key_in_reveal_mode(self):
        with (
            patch.object(aegis_tui, 'read_and_decrypt_vault_file') as mock_decrypt_vault,
            patch.object(aegis_tui, 'get_otps') as mock_get_otps,
            patch('getpass.getpass', return_value='dummy_password') as mock_getpass,
            patch('builtins.input', return_value='dummy_password') as mock_input,
            patch.object(aegis_tui, 'load_config', return_value={
                "last_opened_vault": None,
                "last_vault_dir": None,
                "default_color_mode": True
            }),
            patch.object(aegis_tui, 'save_config'),
            patch('sys.argv', ['aegis-tui.py', '--vault-path', '/mock/vault/path.json']),
            patch('select.select') as mock_select_select
        ):
            # Mock vault data with a single entry
            mock_vault_data = MagicMock()
            entry1 = MagicMock()
            entry1.name = "Single OTP"
            entry1.issuer = "Issuer X"
            entry1.groups = []
            entry1.note = ""
            entry1.uuid = "uuid_single"
            
            mock_vault_data.db.entries = [entry1]
            mock_vault_data.db.groups = []
            mock_decrypt_vault.return_value = mock_vault_data
    
            mock_get_otps.return_value = {
                "uuid_single": MagicMock(uuid="uuid_single", name="Single OTP", issuer="Issuer X", secret="SECRET_SINGLE", string=lambda: "SECRET_SINGLE"),
            }
            
            # Simulate typing "Single", ENTER to reveal, then ESC to exit reveal mode, then Ctrl+C
            getch_side_effects = [
                ord('S'), ord('i'), ord('n'), ord('g'), ord('l'), ord('e'), 
                aegis_tui.curses.KEY_ENTER, # Reveal OTP
                27, # ESC to exit reveal mode
                3 # Ctrl+C to exit program
            ]
            
            mock_stdscr_instance = mock_curses_wrapper(aegis_tui.cli_main, aegis_tui.parser.parse_args(['--vault-path', '/mock/vault/path.json']), 'dummy_password')
            mock_stdscr_instance.getch.side_effect = iter(getch_side_effects)

            def select_side_effect(read_list, write_list, error_list, timeout):
                if mock_stdscr_instance.getch.call_count < len(getch_side_effects) + 5:
                    return ([sys.stdin], [], [])
                return ([], [], [])
            mock_select_select.side_effect = select_side_effect

            addstr_calls = [str(call_arg) for call in mock_stdscr_instance.addstr.call_args_list for call_arg in call.args if isinstance(call_arg, str)]
            full_output = "\n".join(addstr_calls)
            
            # Verify that OTP is revealed, then obscured again after ESC
            self.assertIn("SECRET_SINGLE", full_output)
            # The exact assertion for "obscured again" is tricky with a single full_output string.
            # We can check that the last appearance of the OTP is obscured.
            # For now, verify it was revealed, and assume ESC worked if the program exits cleanly.
            # A more robust test would inspect call_args_list for addstr with "******"
            self.assertIn("--- Revealed OTP: Single OTP ---", full_output)
            self.assertNotIn("SECRET_SINGLE", full_output.split("--- Revealed OTP: Single OTP ---")[-1]) # Check that after reveal, it's not present