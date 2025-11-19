import argparse
import getpass
import os
import time

from aegis_core import find_vault_path, read_and_decrypt_vault_file, get_otps, get_ttn

DEFAULT_AEGIS_VAULT_DIR = os.path.expanduser("~/.config/aegis")

def main():
    parser = argparse.ArgumentParser(description="Aegis Authenticator CLI in Python.", prog="aegis-cli")
    parser.add_argument("-v", "--vault-path", help="Path to the Aegis vault file. If not provided, attempts to find the latest in default locations.")
    parser.add_argument("-d", "--vault-dir", help="Directory to search for vault files. Defaults to current directory.", default=".")
    parser.add_argument("-u", "--uuid", help="Display OTP for a specific entry UUID.")
    parser.add_argument("-g", "--group", help="Filter OTP entries by a specific group name.")
    parser.add_argument("positional_vault_path", nargs="?", help=argparse.SUPPRESS, default=None)

    args = parser.parse_args()

    vault_path = args.vault_path
    if not vault_path and args.positional_vault_path and args.positional_vault_path.endswith(".json"):
        vault_path = args.positional_vault_path

    if not vault_path:
        # First, try to find in the explicitly provided or default vault_dir
        print(f"Searching for vault in {os.path.abspath(args.vault_dir)}...")
        vault_path = find_vault_path(args.vault_dir)

        if not vault_path and args.vault_dir != DEFAULT_AEGIS_VAULT_DIR:
            # If not found in vault_dir, try the default Aegis config directory
            print(f"Vault not found in {os.path.abspath(args.vault_dir)}. Searching in {DEFAULT_AEGIS_VAULT_DIR}...")
            vault_path = find_vault_path(DEFAULT_AEGIS_VAULT_DIR)
            args.vault_dir = DEFAULT_AEGIS_VAULT_DIR # Update for consistent messaging

        if not vault_path:
            print("Error: No vault file found.")
            parser.print_help()
            return
        print(f"Found vault: {vault_path}")

    password = os.getenv("AEGIS_CLI_PASSWORD")
    if not password:
        try:
            try:
                password = getpass.getpass("Enter vault password: ")
            except Exception:
                print("Warning: getpass failed. Falling back to insecure password input.")
                password = input("Enter vault password (will be echoed): ")
        except KeyboardInterrupt:
            print("\nExiting.")
            os.system('clear')
            return

    try:
        vault_data = read_and_decrypt_vault_file(vault_path, password)
        print("Vault decrypted successfully.")
    except ValueError as e:
        print(f"Error decrypting vault: {e}")
        return
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return

    if args.uuid:
        otps = get_otps(vault_data)
        if args.uuid in otps:
            otp_entry = otps[args.uuid]
            print(f"OTP for {args.uuid}: {otp_entry.string()}")
        else:
            print(f"Error: No entry found with UUID {args.uuid}.")
    else:
        try:
            while True:
                os.system('clear') # Clear the screen for each second of countdown
                print("--- All OTPs ---")
                
                # Recalculate OTPs for the current time, as they might change during the countdown
                otps = get_otps(vault_data)

                # Collect data and calculate max widths
                display_data = []
                max_name_len = 0
                max_issuer_len = 0
                max_group_len = 0
                max_note_len = 0

                # Create a mapping of group UUIDs to group names
                group_names = {group.uuid: group.name for group in vault_data.db.groups}

                for entry in vault_data.db.entries:
                    # Resolve group UUIDs to names
                    resolved_groups = []
                    for group_uuid in entry.groups:
                        resolved_groups.append(group_names.get(group_uuid, group_uuid)) # Fallback to UUID if name not found
                    
                    # Apply group filter if provided
                    if args.group and args.group not in resolved_groups:
                        continue

                    name = entry.name
                    issuer = entry.issuer if entry.issuer else ""
                    groups = ", ".join(resolved_groups) if resolved_groups else ""
                    note = entry.note if entry.note else ""
                    uuid = entry.uuid

                    display_data.append({
                        "name": name,
                        "issuer": issuer,
                        "groups": groups,
                        "note": note,
                        "uuid": uuid
                    })

                    if len(name) > max_name_len:
                        max_name_len = len(name)
                    if len(issuer) > max_issuer_len:
                        max_issuer_len = len(issuer)
                    if len(groups) > max_group_len:
                        max_group_len = len(groups)
                    if len(note) > max_note_len:
                        max_note_len = len(note)
                
                # Sort alphabetically by issuer
                display_data.sort(key=lambda x: x["issuer"].lower())

                # Print header
                print(f"{'Issuer'.ljust(max_issuer_len)}  {'Name'.ljust(max_name_len)}  {'Code'.ljust(6)}  {'Group'.ljust(max_group_len)}  {'Note'.ljust(max_note_len)}")
                print(f"{'-' * max_issuer_len}  {'-' * max_name_len}  {'------'}  {'-' * max_group_len}  {'-' * max_note_len}")

                # Print formatted output
                for item in display_data:
                    name = item["name"]
                    issuer = item["issuer"]
                    groups = item["groups"]
                    note = item["note"]
                    uuid = item["uuid"]

                    otp_value = "Error"
                    if uuid in otps:
                        otp_value = otps[uuid].string()
                    
                    print(f"{issuer.ljust(max_issuer_len)}  {name.ljust(max_name_len)}  {otp_value.ljust(6)}  {groups.ljust(max_group_len)}  {note.ljust(max_note_len)}")
                
                ttn = get_ttn()
                initial_ttn_seconds = int(ttn / 1000)

                for remaining_seconds in range(initial_ttn_seconds, 0, -1):
                    # Only update the countdown line
                    print(f"\n\rTime until next refresh: {remaining_seconds:.1f} seconds", end='')
                    time.sleep(1)
                print() # Move to the next line after countdown finishes
        except KeyboardInterrupt:
            print("\nExiting OTP display.")
            os.system('clear') # Clear the screen on exit

if __name__ == "__main__":
    main()
