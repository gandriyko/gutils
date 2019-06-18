# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from __future__ import print_function
from django.conf import settings
from django.utils.encoding import force_text, smart_bytes, force_bytes
from django.core.cache import cache
from django.utils.http import urlquote
from subprocess import check_output, CalledProcessError
from ftplib import FTP
import re
import os
import sys
import random
import hashlib
from gutils import Struct
import requests
import certifi
from io import BytesIO

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

DEFAULT_CA_BUNDLE_PATH = certifi.old_where()

class FTPNoFiles(Exception):
    pass


def generate_password(size=9):
    secure_random = random.SystemRandom()
    allow_chars = '1234567890qwertyuopasdghkzxcvbnmQWERTYUOPASDGHKZXCVBNM'
    return ''.join([secure_random.choice(allow_chars) for i in range(size)])


def print_to_console(value):
    value = force_text(value)
    print(smart_bytes(value, getattr(sys.stdout, 'encoding', None) or 'UTF-8', errors='replace'))


def execute(command, *params):
    # input_encoding = sys.getfilesystemencoding() or 'UTF-8'
    output_encoding = getattr(sys.stdout, 'encoding', None) or 'UTF-8'
    command = "%s %s" % (command, " ".join(params))
    try:
        output = check_output(command, shell=True)
    except CalledProcessError as e:
        return e.output
    return force_text(output, output_encoding)


def get_random_user_agent():
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2226.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) like Gecko',
        'Mozilla/5.0 (compatible, MSIE 11, Windows NT 6.3; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 7.0; InfoPath.3; .NET CLR 3.1.40767; Trident/6.0; en-IN)',
        'Mozilla/5.0 (Windows; U; MSIE 9.0; WIndows NT 9.0; en-US))',
        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1',
        'Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10; rv:33.0) Gecko/20100101 Firefox/33.0',
        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:31.0) Gecko/20130401 Firefox/31.0',
        'Mozilla/5.0 (Windows NT 5.1; rv:31.0) Gecko/20100101 Firefox/31.0',
    ]
    secure_random = random.SystemRandom()
    return secure_random.choice(USER_AGENTS)


def download_ftp(path, encoding='utf-8'):
    path = re.sub(r'ftp\://', '', path)
    login = passwd = ''
    r = re.search(r'([^\:]+)\:?(.*)@(.+?)/(.+)', path)
    if not r:
        raise Exception('FTP error wrong address: %s' % path)
    login = r.group(1)
    passwd = r.group(2)
    domain = r.group(3)
    filename = r.group(4)
    ftp = FTP(domain)
    ftp.login(login, passwd)
    out = BytesIO()
    filename = force_text(filename, encoding)
    cmd = 'RETR %s' % filename
    ftp.retrbinary(cmd, out.write)
    ftp.close()
    return out.getvalue()


def smart_download(url, **kwargs):
    filename_encoding = kwargs.get('filename_encoding', 'utf-8')
    url = force_text(url)
    result = Struct(data='', content_type='', error='', file_name='', ext='')
    force_extension = kwargs.get('force_extension', '')
    # detect extension by URL
    result.ext = force_extension or os.path.splitext(re.sub(r'\?.+', '', url))[1].lower()
    timeout = kwargs.get('timeout', 60)
    save_to = kwargs.get('save_to')
    login_page = kwargs.get('login_page')
    login_data = kwargs.get('login_data', {})

    client = requests.session()
    headers = {'User-Agent': get_random_user_agent()}
    detect_extension = kwargs.get('detect_extension')
    if not url.startswith('ftp://'):
        if login_page:
            client.get(login_page, timeout=timeout, headers=headers, verify=DEFAULT_CA_BUNDLE_PATH)
            client.post(login_page, data=login_data, headers=headers, verify=DEFAULT_CA_BUNDLE_PATH)
        # catch redirect
        response = client.get(url, allow_redirects=False, timeout=timeout,
                              headers=headers, verify=DEFAULT_CA_BUNDLE_PATH)
        location = response.headers.get('Location', '')
        if location:
            url = location
            result.ext = force_extension or os.path.splitext(re.sub(r'\?.+', '', url))[1]
            response = client.get(url, timeout=timeout, headers=headers, verify=DEFAULT_CA_BUNDLE_PATH)
        # detect extension
        if not url.startswith('ftp://') and detect_extension and not force_extension:
            result.content_type = response.headers.get('Content-Type', '')
            content_disposition = response.headers.get('Content-disposition', '')
            # by Content-disposition
            r = re.search(r'filename="?.+(\.\w+)', content_disposition)
            if r:
                result.ext = r.group(1).lower()
            else:
                # by Content-Type
                ext = get_extension(result.content_type)
                if ext:
                    result.ext = ext
    if save_to:
        if detect_extension:
            save_to = '%s%s' % (os.path.splitext(save_to)[0], result.ext)
        output = open(save_to, 'wb')
        result.file_name = save_to
    else:
        output = StringIO()
    if url.startswith('ftp://'):
        output.write(download_ftp(url, filename_encoding))
    else:
        output.write(response.content)
    if not save_to:
        result.data = output.getvalue()
    output.close()
    return result


def clear_template_cache(key, *args):
    args = hashlib.md5(':'.join([urlquote(arg) for arg in args]))
    cache_key = 'template.cache.%s.%s' % (key, args.hexdigest())
    cache.delete(cache_key)


def make_key(value):
    value = smart_bytes(value)
    return hashlib.md5(value).hexdigest()


def get_extension(string):
    content_types = [
        ('.html', ['text/html']),
        ('.jpeg', ['image/jpeg']),
        ('.doc', ['application/msword']),
        ('.docx', ['application/vnd.openxmlformats-officedocument.wordprocessingml.document']),
        ('.xls', ['application/vnd.ms-excel', 'application/x-msexcel', 'application/excel', 'application/x-excel']),
        ('.xlsx', ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']),
        ('.gif', ['image/gif']),
        ('.jpg', ['image/jpeg']),
        ('.txt', ['text/plain']),
        ('.csv', ['text/csv']),
        ('.pdf', ['application/pdf']),
        ('.png', ['image/png']),
        ('.zip', ['application/x-compressed', 'application/x-zip-compressed', 'application/zip', 'multipart/x-zip']),
        ('.rar', ['application/x-rar-compressed', 'application/rar']),
        ('.7z', ['application/x-7z-compressed', 'application/7z']),
        ('.dbf', ['application/dbf']),
    ]
    for item in content_types:
        if string in item[1]:
            return item[0]
    return ''


def ftp_get(server, login, passwd, name, destination):
    ftp = FTP(server)
    ftp.login(login, passwd)
    _destination = '%s_' % destination
    try:
        f = open(_destination, 'wb')
        ftp.retrbinary('RETR %s' % name, f.write)
    except Exception as e:
        os.remove(_destination)
        raise e
    if os.path.exists(_destination):
        os.rename(_destination, destination)
    ftp.close()


def ftp_delete(server, login, passwd, name):
    ftp = FTP(server)
    ftp.login(login, passwd)
    ftp.delete(name)
    ftp.close()


def ftp_list(server, login, passwd, mask):
    ftp = FTP(server)
    ftp.login(login, passwd)
    result = [os.path.basename(f) for f in ftp.nlst(mask)]
    ftp.close()
    return result


def ftp_send(server, login, passwd, name, filename):
    ftp = FTP(server)
    ftp.login(login, passwd)
    with open(filename, 'rb') as f:
        ftp.storbinary('STOR %s' % name, f)
    ftp.close()
