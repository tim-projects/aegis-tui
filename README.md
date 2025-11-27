# aegis-tui

An unoffical interactive command-line interface (CLI) tool for viewing Aegis Authenticator Time-based One-Time Passwords (TOTP).

**Note:** This tool is primarily a viewer and does not support editing or creating new OTP codes. For that use the official app here: https://getaegis.app/

### Example Output

When run without a group filter, OTP codes are obscured by default. Other entries are dimmed, and the selected entry is highlighted with a dark blue background in search mode:

```text
--- All OTPs ---
#   Issuer             Name               Code    Group              Note
--- ---                ----               ----    -----              ----
1   Bank of America    MyBank             123456  Finance            Checking Account
2   Facebook           MySocial           ******  Social             Personal Profile
3   Google             MyEmail            ******  Personal           Primary Email
4   Steam              MyGaming           ******  Gaming             Steam Account

Type to filter, use arrows to select, Enter to reveal (Ctrl+C to exit): 
Time until next refresh: 25.0 seconds
```

When filtering by a specific group (e.g., `aegis-tui /path/to/your/aegis-backup.json --group Finance`) or by pressing g in interactive mode:

```text
--- All OTPs ---
#   Issuer             Name               Code    Group              Note
--- ---                ----               ----    -----              ----
1   Bank of America    MyBank             123456  Finance            Checking Account

Time until next refresh: 25.0 seconds
```

## Features

*   Decrypts Aegis Authenticator vault files using a provided password.
*   Continuously displays OTP codes for all entries in a real-time refreshing table.
*   Automatically reveals the code if only one OTP entry is displayed.
*   Interactive mode to type-search and reveal obscured OTP codes on demand.
*   Supports filtering OTP entries by group name.
*   Respects terminal dimensions to prevent output overflow.
*   Option to copy direct to the clipboard, if the clipboard app is configured in ~/.config/aegis-tui/config.json

## Usage

### Installation (Arch Linux AUR)

To install `aegis-tui` on Arch Linux, you can use an AUR helper like `yay` or `paru`:

```bash
yay -S aegis-tui
# or
paru -S aegis-tui
```

Alternatively, you can build it manually:

```bash
git clone https://aur.archlinux.org/aegis-tui.git
cd aegis-tui
makepkg -si
```

### Running the CLI

Once installed, you can run `aegis-tui` from any terminal with the path to your Aegis vault `.json` file:

```bash
aegis-tui /path/to/your/aegis-backup.json
```

If no vault path is provided, `aegis-tui` will first attempt to open the last used vault file stored in its configuration. If no last used vault is found, it will then automatically search for the most recently modified `aegis-backup-*.json` file in the current directory, and then in `~/.config/aegis`.

If your vault requires a password, you will be prompted securely. For non-interactive use (e.g., in scripts), you can provide the password via the `AEGIS_CLI_PASSWORD` environment variable:

```bash
export AEGIS_CLI_PASSWORD="YourVaultPassword"
aegis-tui /path/to/your/aegis-backup.json --no-color
```

## Configuration

`aegis-tui` stores its configuration in `~/.config/aegis-tui/config.json`. This file is automatically created if it doesn't exist. It currently stores the path to the last successfully opened Aegis vault file, allowing `aegis-tui` to quickly reopen it on subsequent runs without requiring the path to be specified again. It also stores `default_color_mode`, which determines if colored output is enabled by default (true) or disabled (false). This can be overridden by the `--no-color` flag.

Example `config.json`:

```json
{
    "last_opened_vault": "/home/user/.config/aegis-tui/aegis-backup-20251026-200544.json",
    "last_vault_dir": "/home/user/.config/aegis-tui",
    "default_color_mode": true
}
```

## License

This project is licensed under the GNU General Public License v3.0. See the `LICENSE` file for details.

This project is a complete rewrite in Python, originally inspired by the `avdu` project (https://github.com/Sammy-T/avdu). It provides CLI functionality for displaying OTP codes from an encrypted Aegis vault.
