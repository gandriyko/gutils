import base64
import email
import os
import re

from email.header import decode_header
from gutils import Struct
from gutils.strings import clean_non_alphanumerics
from imaplib import IMAP4_SSL


def get_email_attachment(**kwargs):
    key = kwargs['key']
    if not key:
        return
    host = kwargs['host']
    login = kwargs['login']
    password = kwargs['password']
    port = kwargs.get('port') or 993
    save_to = kwargs.get('save_to')

    result = Struct(data='', content_type='', error='', file_name='', ext='')
    mail_server = IMAP4_SSL(host, port=port)
    mail_server.login(login, password)
    mail_server.select()
    res, mail_ids = mail_server.search(None, '(UNSEEN)')
    if res != 'OK':
        result.error = res
        return result
    mail_ids = mail_ids[0].split()
    mail_ids = list(reversed(mail_ids))
    for mail_id in mail_ids:
        res, email_data = mail_server.fetch(mail_id, '(BODY.PEEK[])')
        msg = email.message_from_bytes(email_data[0][1])
        match = re.search(r'[\w\.-]+@[\w\.-]+', msg['from'])
        if match:
            sender = match.group(0)
        else:
            sender = msg['from']
        result.mail_server = sender
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            name = part.get_filename()
            if not name:
                continue
            # filename = part.get_filename()
            raw, encoding = decode_header(name)[0]
            if encoding is not None:
                name = raw.decode(encoding)
            if key not in name:
                continue
            result.file_name = name
            result.ext = os.path.splitext(result.file_name)[1].strip()
            if save_to:
                save_to = '%s%s' % (os.path.splitext(save_to)[0], result.ext)
                raw = part.get_payload(None, True)
                if raw is None:
                    result.error = 'Empty attachment'
                    result.ext = ''
                    result.file_name = ''
                    return result
                open(save_to, 'wb').write(raw)
                result.file_name = save_to
            mail_server.store(mail_id, '+FLAGS', '(\\SEEN)')
            return result
    return result


def check_email(value):
    return base64.b64decode(clean_non_alphanumerics(value) + '=')
