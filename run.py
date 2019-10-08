#!/usr/bin/env python3

import csv
import os
import sys

from imessage2csv import Reader

paths = [
    # macOS Contacts
    '~/Library/Application Support/AddressBook/Sources',

    # macOS Messages
    '~/Library/Messages',

    # iOS Backup
    # If it is encrypted, then it must be decrypted first
    '~/Library/Application Support/MobileSync/Backup',
]

reader = Reader()

for path in paths:
    expanded_path = os.path.expanduser(path)
    if os.path.exists(expanded_path):
        reader.add(expanded_path)

messages = reader.read()
fieldnames = list(messages[0].keys())
writer = csv.DictWriter(sys.stdout, fieldnames)
writer.writerows(messages)
