#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""This script sanitizes filenames in a Nextcloud instance to comply with Windows naming conventions.

Nextcloud annoyingly still does not offer a built-in way to make file and foldernames Windows-compatible.
This script connects to a Nextcloud instance via WebDAV and renames files and folders to comply with Windows naming conventions.
This script is intended as a PoC, as I have seen this issue in multiple instances without a solution.
Maybe this feature makes it into an official Nextcloud plugin.
Starting with Nextcloud 30, there is the possibility to block files with invalid characters from being uploaded.
This is not a good user experience and creates extra work for helpdesk staff.

WebDAV is used so Nextcloud is instantly aware of the changes. While these actions could be performed directly on the server,
occ files:scan would have to be called afterwards to make Nextcloud aware of the changes. This invites new file conflicts.

It tries to be safe by default. Conflicts are resolved by appending '_1' to the filename, unless --overwrite is set.

Examples:
    # Initialize the script in your environment (asks for password interactively)
        $ python nextcloud_filename_sanitizer.py -i
    # Run the script in safe mode on a directory and log to a file
        $ python nextcloud_filename_sanitizer.py -s -d '/path/to/directory' -l 'log.txt'
    # Run the script and overwrite existing files on conflict (USE WITH CAUTION)
        $ python nextcloud_filename_sanitizer.py -d '/path/to/directory' -o -l 'log.txt'

Attributes:
    WEBDAV_ADDRESS (str): The address of the Nextcloud WebDAV server.
    WEBDAV_USERNAME (str): The username to authenticate with.

Parameters:
    -i, --init: Initialize the script by storing the password in the OS credential store and performing a connection test.
    -v, --verbose: Enable debug logging.
    -l, --logfile [/path/to/directory]: Log to a file.
    -s, --safe-mode: Do not perform any actions, only log what would be done.
    -r, --replace-with: [char] Replace invalid characters with this character. Default is '_'.
    -d, --directory: [/path/to/directory] The directory to sanitize.
    -o, --overwrite: Overwrite existing files on conflict.

Dependencies:
    webdav4: https://pypi.org/project/webdav4/
    keyring: https://pypi.org/project/keyring/
"""

import re
import argparse
import logging
import getpass
import urllib.parse as urllib
import keyring
from pathlib import PurePosixPath
from webdav4.fsspec import WebdavFileSystem, ResourceAlreadyExists

__author__ = "Manuel J. Mehltretter"
__copyright__ = "Copyright 2024, Manuel J. Mehltretter"
__credits__ = "Manuel J. Mehltretter"
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Manuel J. Mehltretter"
__email__ = "status@mehltretters.com"
__status__ = "Production"

# Global constants - change these to match your setup
WEBDAV_ADDRESS = 'https://cloud.example.com/remote.php/dav/files/username/'
WEBDAV_USERNAME = 'username'

### No changes needed below this line ###

# Global variables
keyring_system = 'f{WEBDAV_ADDRESS}-filename-sanitizer'
replace_with = '_'
safe_mode = False
overwrite = False
logger: logging.Logger
fs: WebdavFileSystem


def init():
    """Initialize the script by storing the password in the OS credential store and performing a connection test."""
    
    keyring.set_password(keyring_system, WEBDAV_USERNAME, getpass.getpass('Please enter your webdav password: '))

    # Perform a connection test
    try:
        fs = WebdavFileSystem(WEBDAV_ADDRESS, 
                              auth=(WEBDAV_USERNAME, keyring.get_password(keyring_system, WEBDAV_USERNAME)))
        fs.ls('/')
        logger.info('Connection successful! - You are ready to go.')
    except Exception as e:
        logger.error(f'Connection failed: {e}')
        exit(1)


def sanitize_filename(path: PurePosixPath) -> PurePosixPath:
    """Sanitize a filename to comply with Windows naming conventions.

    This function first replaces or removes invalid characters.
    Then it removes trailing spaces or periods. Finally, it checks for reserved names on Windows.
    https://docs.microsoft.com/en-us/windows/win32/fileio/naming-a-file

    Parameters
    ----------
    path : PurePosixPath
        The path to the file or folder to be sanitized.
        
    Returns
    -------
    PurePosixPath
        The sanitized path.
    """

    windows_reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM¹', 'COM²', 'COM³', 'LPT¹', 'LPT²', 'LPT³',
                          'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 
                          'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
    invalid_characters = r'[\\/:*?"<>|]'

    # Replace invalid characters
    path = path.with_name(re.sub(invalid_characters, replace_with, path.name))
    # Check for reserved names on Windows
    if path.name.upper() in windows_reserved_names:
        path = path.with_name('_reserved')
    return path


def process_item(path: PurePosixPath) -> PurePosixPath:
    """Process a single file or folder.

    Calls the sanitize_filename function. If the filename is changed, the file is renamed.
    This script tries to be safe by default. Conflicts are resolved by appending '_1' to the filename.
    Files will only be overwritten if the overwrite flag is set.
    
    Parameters
    ----------
    path : PurePosixPath
        The path to the file or folder to be processed.

    Returns
    -------
    PurePosixPath
        The new path of the file or folder. This is important if the item is a folder,
        because the path of its content will change if the folder is renamed.
    """

    new_path = sanitize_filename(path)
    if new_path != path:
        if safe_mode:
            logger.info(f'''Would rename: '{path}') 
                        to '{new_path}'
                        ''')
        else:
            try:
                fs.mv(urllib.quote(str(path)), urllib.quote(str(new_path)), recursive=True)
                logger.info(f'''Renamed: '{path}'
                            to '{new_path}'
                            ''')
            except ResourceAlreadyExists as e:
                if not overwrite:
                    logger.warning(f'''Conflict: '{new_path}' already exists. 
                                    Appended '_1' to the filename.
                                    ''')
                    new_path = new_path.with_name(new_path.name + '_1')
                    fs.mv(urllib.quote(str(path)), urllib.quote(f'{new_path}_1'), recursive=True)
                else:
                    logger.warning(f'''Conflict: Overwriting {new_path}
                    ''')
                    fs.rm(urllib.quote(str(new_path)))
                    fs.mv(urllib.quote(str(path)), urllib.quote(str(new_path)), recursive=True)
            except Exception as e:
                logger.error(f'''Could not rename '{path}': 
                             {e}''')
    else:
        logger.debug(f'Skipped: {path}')
    
    return new_path


def process_recursive(path: PurePosixPath):
    """Process all files and folders in a directory recursively.
    
    webdav4 does not support recursive listing. 
    webdav4 would support recursive listing with fs.glob("/**"), but can't be used here.
    The reason is, that the folder name must be renamed, before we traverse the tree further.
    Therefore, this function recursively traverses the directory tree and calls process_item on each item.
    
    Parameters
    ----------
    path : PurePosixPath
        The path to the directory to be traversed.
    """

    try:
        for item in fs.ls(urllib.quote(str(path)), detail=True):
            item_path = PurePosixPath(item['name'])
            if item['type'] == 'file':
                process_item(item_path)
            elif item['type'] == 'directory':
                new_folder_name = process_item(item_path)
                process_recursive(new_folder_name)
    except Exception as e:
        logger.error(f'''Could not list '{path}' 
                     {e}''')


if __name__ == '__main__':
    """Main function. Sets up logging, parses command line arguments and calls the appropriate functions."""

    # Set up logger
    logger = logging.getLogger(__name__)
    formatter = logging.Formatter('{asctime} - {levelname} - {message}', 
                                  style='{', datefmt='%Y-%m-%d %H:%M:%S')
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)

    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--init', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-l', '--logfile', type=str, required=False)
    parser.add_argument('-s', '--safe-mode', action='store_true')
    parser.add_argument('-r', '--replace-with', type=str)
    parser.add_argument('-d', '--directory', type=str, required=True)
    parser.add_argument('-o', '--overwrite', action='store_true')
    args = parser.parse_args()

    # Process command line arguments
    if args.init:
        init()
    if args.logfile:
        file_handler = logging.FileHandler(args.logfile, mode='a')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    if args.safe_mode:
        safe_mode = True
    if args.replace_with:
        replace_with = args.replace_with
    if args.overwrite:
        overwrite = True
    
    # Do stuff
    fs = WebdavFileSystem(WEBDAV_ADDRESS, 
                          auth=(WEBDAV_USERNAME, keyring.get_password(keyring_system, WEBDAV_USERNAME)))
    path = PurePosixPath(args.directory.strip())
    logger.info(f'Starting to sanitize filenames in {str(path)}')
    process_recursive(path)
