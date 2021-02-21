import os
import re
import sqlite3
import sys


# Reader.add(directory)
# Reader.add(file)
# Reader.parse()


class Reader:
    def __init__(self):
        self._contacts_paths = {}
        self._messages_paths = {}
        self.contacts = {}
        self.messages = {}

    # echo -n HomeDomain-Library/AddressBook/AddressBook.sqlitedb | sha1sum
    # 31bb7ba8914766d4ba40d6dfb6113c8b614be442

    # echo -n HomeDomain-Library/SMS/sms.db | sha1sum
    # 3d0d7e5fb2ce288813306e4d4636395e047a3d28

    def add(self, path, _quiet=False):
        if os.path.isdir(path):
            for filename in os.listdir(path):
                self.add(os.path.join(path, filename), _quiet=True)
            return
        basename = os.path.basename(path)
        if basename in {'31bb7ba8914766d4ba40d6dfb6113c8b614be442', 'AddressBook.sqlitedb'}:
            self._contacts_paths[path] = self._ios_contacts_reader
        elif basename in {'AddressBook-v22.abcddb'}:
            self._contacts_paths[path] = self._macos_contacts_reader
        elif basename in {'3d0d7e5fb2ce288813306e4d4636395e047a3d28', 'sms.db', 'chat.db'}:
            self._messages_paths[path] = self._message_reader
        else:
            if _quiet:
                return
            raise Exception('Cannot determine database type')

    def read(self):
        contacts_paths = sorted(self._contacts_paths, key=os.path.getmtime, reverse=True)
        messages_paths = sorted(self._messages_paths, key=os.path.getmtime, reverse=True)
        for path in contacts_paths:
            reader = self._contacts_paths[path]
            count = self._parse(path, reader)
            print('{:>9}'.format(int(count)), 'new contacts in', path, file=sys.stderr)
        for path in messages_paths:
            reader = self._messages_paths[path]
            count = self._parse(path, reader)
            print('{:>9}'.format(int(count)), 'new messages in', path, file=sys.stderr)
        return list(self.messages.values())

    def _parse(self, path, reader):
        class Count:
            def __init__(self):
                self.n = 0

            def add(self, k):
                self.n += k

            def __int__(self):
                return self.n

        count = Count()
        with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as connection:
            cursor = connection.cursor()
            try:
                reader(cursor, count)
            except sqlite3.DatabaseError as exception:
                print(exception, 'in', path, file=sys.stderr)
        return count

    def _ios_contacts_reader(self, cursor, count):
        cursor.execute('''
            SELECT  ABMultiValue.value,
                    ABPerson.First,
                    ABPerson.Middle,
                    ABPerson.Last
                FROM ABPerson
            INNER JOIN ABMultiValue
                ON ABMultiValue.record_id = ABPerson.ROWID AND ABMultiValue.property IN (3, 4)
            ''')

        for value, first, middle, last in _fetch_safely(cursor):
            _add_contact(value, (first, middle, last), self.contacts, count)

    def _macos_contacts_reader(self, cursor, count):
        cursor.execute('''
            SELECT  ZABCDPHONENUMBER.ZFULLNUMBER,
                    ZABCDEMAILADDRESS.ZADDRESS,
                    ZABCDRECORD.ZFIRSTNAME,
                    ZABCDRECORD.ZMIDDLENAME,
                    ZABCDRECORD.ZLASTNAME
                FROM ZABCDRECORD
            LEFT OUTER JOIN ZABCDPHONENUMBER
                ON ZABCDPHONENUMBER.ZOWNER = ZABCDRECORD.Z_PK
            LEFT OUTER JOIN ZABCDEMAILADDRESS
                ON ZABCDEMAILADDRESS.ZOWNER = ZABCDRECORD.Z_PK
            ''')

        for phone, email, first, middle, last in _fetch_safely(cursor):
            _add_contact(phone, (first, middle, last), self.contacts, count)
            _add_contact(email, (first, middle, last), self.contacts, count)

    def _message_reader(self, cursor, count):
        cursor.execute('''
            SELECT  message.ROWID,
                    message.guid,
                    strftime("%w %Y-%m-%d %H:%M:%f",
                        CASE WHEN message.date > 1000000000 THEN message.date / 1000000000.0 ELSE message.date END
                        + strftime("%s", "2001-01-01"), "unixepoch", "localtime"),
                    message_handle.id,
                    GROUP_CONCAT(DISTINCT chat_handle.id),
                    message.is_from_me,
                    message.text,
                    GROUP_CONCAT(DISTINCT attachment.filename)
                FROM message

            LEFT OUTER JOIN handle AS message_handle
                ON message_handle.ROWID = message.handle_id

            LEFT OUTER JOIN chat_message_join
                ON chat_message_join.message_id = message.ROWID
            LEFT OUTER JOIN chat_handle_join
                ON chat_handle_join.chat_id = chat_message_join.chat_id
            LEFT OUTER JOIN handle AS chat_handle
                ON chat_handle.ROWID = chat_handle_join.handle_id

            LEFT OUTER JOIN message_attachment_join
                ON message_attachment_join.message_id = message.ROWID
            LEFT OUTER JOIN attachment
                ON attachment.rowid = message_attachment_join.attachment_id

            GROUP BY message.ROWID
            ORDER BY message.date  /* Necessary to make the previous_handles hack work */
            ''')

        #previous_handles = None

        for rowid, guid, date, message_handle, chat_handles, from_me, text, filenames in _fetch_safely(cursor):
            if guid in self.messages:
                continue

            def handle_display(handle, emphasize=False):
                canonical = _canonicalize_handle(handle)
                if canonical in self.contacts:
                    display = '/'.join(self.contacts[canonical])
                else:
                    display = handle
                if emphasize and handle == message_handle and len(chat_handles) > 1:
                    display = '[' + display + ']'
                return display

            if chat_handles is not None:
                chat_handles = chat_handles.split(',')
                chat_handles.sort(key=handle_display)

            if filenames is not None:
                filenames = filenames.split(',')

            # Not necessary because we do not use message_handle anywhere

            #if message_handle is None and chat_handles is not None and len(chat_handles) == 1:
            #    message_handle = chat_handles[0]
            #    if args.verbose:
            #        print(f'[{guid}] Fix #2 message_handle = chat_handles[0] = {message_handle}', file=sys.stderr)

            # Some messages have no corresponding rows in the chat_message_join table
            # These messages seem to be associated with iMessage using an email address as opposed to a phone number
            # When is_from_me == 0, these messages have handle_id != 0, so we can reconstruct chat_handles by looking
            # up the handle_id in the handle table and retrieving the handle.id

            if message_handle is not None and chat_handles is None:
                chat_handles = [message_handle]
                print(guid, 'Fix chat_handles = [message_handle] =', chat_handles, file=sys.stderr)

            # When is_from_me == 1, these messages have handle_id == 0, so there is no apparent way to obtain the
            # recipient handle. These messages are not shown in Messages.app, so it seems to be a bug in iMessage
            # previous_handles is an imprecise hack to attempt to overcome this issue

            if chat_handles is not None:
                #pr     return self.messagesevious_handles = chat_handles
                displays = ', '.join(handle_display(handle, emphasize=True) for handle in chat_handles)
            #elif previous_handles is not None:
            #    displays = ', '.join(handle_display(handle, emphasize=True) for handle in previous_handles) + ' [?]'
            else:
                displays = ''

            if text is not None:
                text = text.replace("‘", "'").replace("’", "'").replace('“', '"').replace('”', '"')

            if filenames is not None:
                if text is None:
                    text = ''
                else:
                    text += '\n'
                text += '\n'.join('[' + filename + ']' for filename in filenames)

            #nfiles = len(filenames) if filenames is not None else 0
            #nobjects = text.count('\uFFFC') if text is not None else 0
            #if nfiles != nobjects:
            #    print(f'[{guid}] nfiles={nfiles} but nobjects={nobjects}', file=sys.stderr)

            day, date = date.split(' ', 1)
            day = ('Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday')[int(day)][:3]

            self.messages[guid] = {
                'guid': guid,
                'date': date,
                'day': day,
                'display': displays,
                'from_me': from_me,
                'text': text
            }
            count.add(1)

def _canonicalize_handle(handle):
    if '@' in handle:
        canonical = handle.lower()
    else:
        canonical = re.sub('[^0-9]+', '', handle)
        if len(canonical) == 11 and canonical[0] == '1':
            canonical = canonical[1:]
    return canonical

def _add_contact(handle, names, contacts, count):
    if handle is not None and any(name is not None for name in names):
        canonical = _canonicalize_handle(handle)
        if canonical not in contacts:
            contacts[canonical] = []
        display = ' '.join(name for name in names if name is not None).strip()
        if display not in contacts[canonical]:
            contacts[canonical].append(display)
            count.add(1)

def _fetch_safely(cursor):
    while True:
        try:
            row = cursor.fetchone()
            if row:
                yield row
            else:
                break
        except sqlite3.DatabaseError as exception:
            # Database may be partially corrupted
            # We want to extract as many rows as possible
            print(exception, file=sys.stderr)
            break
