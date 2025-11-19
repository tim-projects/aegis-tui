import argparse
import getpass
import os
import time

from avdu_core import find_vault_path, read_and_decrypt_vault_file, get_otps, get_ttn

def main():
    parser = argparse.ArgumentParser(description="Aegis Authenticator CLI in Python.")
    parser.add_argument("-v", "--vault-path", help="Path to the Aegis vault file. If not provided, attempts to find the latest in default locations.")
    parser.add_argument("-d", "--vault-dir", help="Directory to search for vault files. Defaults to current directory.", default=".")
    parser.add_argument("-p", "--password", help="Vault password. If not provided, will prompt securely.")
    parser.add_argument("-u", "--uuid", help="Display OTP for a specific entry UUID.")
    parser.add_argument("positional_vault_path", nargs="?", help="Path to the Aegis vault file (positional argument).", default=None)

    args = parser.parse_args()

    vault_path = args.vault_path
    if not vault_path and args.positional_vault_path and args.positional_vault_path.endswith(".json"):
        vault_path = args.positional_vault_path

    if not vault_path:
        print(f"Searching for vault in {os.path.abspath(args.vault_dir)}...")
        vault_path = find_vault_path(args.vault_dir)
        if not vault_path:
            print("Error: No vault file found. Please specify with -v, provide a .json file as a positional argument, or ensure one exists in the vault directory.")
            return
        print(f"Found vault: {vault_path}")

    password = args.password
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

                # Collect data and calculate max widths (re-do this to ensure accurate padding if names/issuers change, though unlikely)
                display_data = []
                max_name_len = 0
                max_issuer_len = 0

                for entry in vault_data.db.entries:
                    name = entry.name
                    issuer = entry.issuer if entry.issuer else ""
                    uuid = entry.uuid

                    display_data.append({
                        "name": name,
                        "issuer": issuer,
                        "uuid": uuid
                    })

                    if len(name) > max_name_len:
                        max_name_len = len(name)
                    if len(issuer) > max_issuer_len:
                        max_issuer_len = len(issuer)
                
                # Sort alphabetically by issuer
                display_data.sort(key=lambda x: x["issuer"].lower())

                # Print formatted output
                for item in display_data:
                    name = item["name"]
                    issuer = item["issuer"]
                    uuid = item["uuid"]

                    otp_value = "Error generating OTP"
                    if uuid in otps:
                        otp_value = otps[uuid].string()
                    
                    print(f"{name.ljust(max_name_len)}  {issuer.ljust(max_issuer_len)}  {otp_value}")
                
                ttn = get_ttn()
                initial_ttn_seconds = int(ttn / 1000)

                for remaining_seconds in range(initial_ttn_seconds, 0, -1):
                    # Clear the screen for each second of countdown
                    os.system('clear')
                    print("--- All OTPs ---")
                    
                    # Re-print the OTPs (they don't change during the 1-second countdown)
                    for item in display_data:
                        name = item["name"]
                        issuer = item["issuer"]
                        uuid = item["uuid"]

                        otp_value = "Error generating OTP"
                        if uuid in otps:
                            otp_value = otps[uuid].string()
                        
                        print(f"{name.ljust(max_name_len)}  {issuer.ljust(max_issuer_len)}  {otp_value}")

                    print(f"\nTime until next refresh: {remaining_seconds:.1f} seconds")
                    time.sleep(1)
        except KeyboardInterrupt:
            print("\nExiting OTP display.")
            os.system('clear') # Clear the screen on exit

if __name__ == "__main__":
    main()
