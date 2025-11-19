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

### Installation (Arch Linux AUR)

To install `aegis-cli` on Arch Linux, you can use an AUR helper like `yay` or `paru`:

```bash
yay -S aegis-cli
# or
paru -S aegis-cli
```

Alternatively, you can build it manually:

```bash
git clone https://aur.archlinux.org/aegis-cli.git
cd aegis-cli
makepkg -si
```

### Running the CLI

Once installed, you can run `aegis-cli` from any terminal with the path to your Aegis vault `.json` file:

```bash
aegis-cli /path/to/your/aegis-backup.json
```

If your vault requires a password, you will be prompted securely. You can also provide the password directly (use with caution in scripts):

```bash
aegis-cli /path/to/your/aegis-backup.json -p "YourVaultPassword"
```

### Example Output

```
--- All OTPs ---
MyBank             (Bank of America)  123456
MyEmail            (Google)           789012
MySocial           (Facebook)         345678
MyGaming           (Steam)            901234

Time until next refresh: 25.0 seconds
```


## License

This project is licensed under the GNU General Public License v3.0. See the `LICENSE` file for details.
