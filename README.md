# aegis-cli

A command-line interface (CLI) tool for viewing Aegis Authenticator Time-based One-Time Passwords (TOTP).

This project is a complete rewrite in Python, originally inspired by the `avdu` project (https://github.com/Sammy-T/avdu). It provides CLI functionality for displaying OTP codes from an encrypted Aegis vault.

**Note:** This tool is primarily a viewer and does not support editing or creating new OTP codes.

## Features

*   Decrypts Aegis Authenticator vault files using a provided password.
*   Continuously displays OTP codes for all entries in a real-time refreshing table.
*   Automatically refreshes OTPs based on their configured periods, with a live countdown.
*   Outputs OTPs in a clear, sorted table format (by Issuer).
*   Purely command-line based, with no graphical interface.
*   Graceful exit on `Ctrl+C` (KeyboardInterrupt), clearing the screen for security.

## Usage

To run the `aegis-cli` tool, execute the `cli.py` script with the path to your Aegis vault `.json` file as an argument.

```bash
python cli.py /path/to/your/aegis-backup.json
```

Alternatively, you can specify the password directly:

```bash
python cli.py /path/to/your/aegis-backup.json -p "YourVaultPassword"
```


## License

This project is licensed under the GNU General Public License v3.0. See the `LICENSE` file for details.
