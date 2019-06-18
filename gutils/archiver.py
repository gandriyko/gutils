# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from django.conf import settings
from gutils.systems import execute
import tempfile
import os
import shutil
import glob
import re


def check_result(value):
    if not value:
        return False
    return ('Everything is Ok' in value) or ('All OK' in value)


def unpack_file(filename, destination, force_name='', **kwarg):
    password = kwarg.get('password', '')
    result = None
    ext = os.path.splitext(filename)[1].lower()
    if not os.path.exists(filename):
        raise Exception('File %s does not exists' % filename)
    tmp_dir = tempfile.mkdtemp()
    if password:
        password = '-p%s' % password
    if ext in ('.zip', '.7z', '.zip_'):
        command = '7z e -y %s -o%s %s' % (password, tmp_dir, filename)
    elif ext in ('.rar', '.rar_'):
        if password == '':
            password = '-p-'
        command = 'unrar e -y %s %s %s' % (password, filename, tmp_dir)
    elif ext in ('.gz', '.gzip'):
        _filename = re.sub(r'\.gz^', '', filename, flags=re.I)
        _ext = os.path.splitext(_filename.replace('.gz', ''))[1].lower() or '.csv'
        result = os.path.join(destination, '%s%s' % (force_name, _ext))
        command = 'gunzip -c %s > %s' % (filename, result)
        execute(command)
        return result
    else:
        raise Exception('Wrong archive format')
    if not check_result(execute(command)):
        raise Exception('Error unpack "%s"' % filename)
    files = glob.glob(os.path.join(tmp_dir, '*.*'))
    if files:
        name = os.path.basename(files[0])
        if force_name:
            name = '%s%s' % (force_name, os.path.splitext(name)[1])
        result = os.path.join(destination, name)
        shutil.move(files[0], result)
    try:
        shutil.rmtree(tmp_dir)  # delete directory
    except OSError:
        pass
    return result


def pack_file(filename):
    if not os.path.exists(filename):
        raise Exception('File "%s" does not exists.' % filename)
    destination = u"%s.zip" % filename
    if os.path.exists(destination):
        os.remove(destination)
    if not check_result(execute(settings.GUTILS_ARCHIVER_NAME, 'a', '-tzip', '-y', '-mx1', destination, filename)):
        raise Exception('Error creating "%s"' % destination)
    return destination
