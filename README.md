# nextcloud_filename_sanitizer
This script sanitizes filenames in a Nextcloud instance to comply with Windows naming conventions.

Nextcloud annoyingly still does not offer a built-in way to make file and foldernames Windows-compatible.
This script connects to a Nextcloud instance via WebDAV and renames files and folders to comply with Windows naming conventions.
This script is intended as a PoC, as I have seen this issue in multiple instances without a solution.
Maybe this feature makes it into an official Nextcloud plugin.
Starting with Nextcloud 30, there is the possibility to block files with invalid characters from being uploaded.
This is not a good user experience and creates extra work for helpdesk staff.

WebDAV is used so Nextcloud is instantly aware of the changes. While these actions could be performed directly on the server,
occ files:scan would have to be called afterwards to make Nextcloud aware of the changes. This invites new file conflicts.

It tries to be safe by default. Conflicts are resolved by appending '_1' to the filename, unless --overwrite is set.

## Installation
    pip install webdav4
    pip install keyring

## Usage
    - Initialize the script in your environment (asks for password interactively)
        $ python nextcloud_filename_sanitizer.py -i
    - Run the script in safe mode on a directory and log to a file
        $ python nextcloud_filename_sanitizer.py -s -d '/path/to/directory' -l 'log.txt'
    - Run the script and overwrite existing files on conflict (USE WITH CAUTION)
        $ python nextcloud_filename_sanitizer.py -d '/path/to/directory' -o -l 'log.txt'

## Attributes
    WEBDAV_ADDRESS (str): The address of the Nextcloud WebDAV server.
    WEBDAV_USERNAME (str): The username to authenticate with.

## Parameters
    -i, --init: Initialize the script by storing the password in the OS credential store and performing a connection test.
    -v, --verbose: Enable debug logging.
    -l, --logfile [/path/to/directory]: Log to a file.
    -s, --safe-mode: Do not perform any actions, only log what would be done.
    -r, --replace-with: [char] Replace invalid characters with this character. Default is '_'.
    -d, --directory: [/path/to/directory] The directory to sanitize.
    -o, --overwrite: Overwrite existing files on conflict.

## Dependencies
    webdav4: https://pypi.org/project/webdav4/
    keyring: https://pypi.org/project/keyring/

## Contribute
    - This could be built as a package and published on pip for easier installation
    - Convert to PHP and make a Nextcloud Plugin
