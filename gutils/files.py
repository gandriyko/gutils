from django.utils.encoding import force_text, force_bytes
from django.conf import settings
from gutils.archiver import unpack_file
from gutils.strings import get_slug
import shutil
import random
import hashlib
import os


bufsize = 8096


def file_generate_name():
    name = settings.FILE_UPLOAD_TEMP_DIR + "/%s" % random.randint(1, 10000000)
    return name.replace('\\', '/')


def file_get_path(name, root=settings.MEDIA_ROOT):
    return os.path.join(root, name).replace('\\', '/')


def file_ext(file_name):
    return os.path.splitext(file_name)[1].lower()


def file_fix_new_line(file_name):
    source = open(file_name, 'r')
    destination = open(file_name + '_', 'wb+')
    for line in source:
        line = line.replace("\n", '').replace("\r", '')
        destination.write("%s\n" % line)
    source.close()
    destination.close()
    os.remove(file_name)
    os.rename(file_name + '_', file_name)


def replace_original(file_name):
    source = file_name
    destination = file_name[:-1]
    shutil.copyfile(source, destination)
    os.remove(file_name)


def file_save_uploaded(post_file, destination):
    destination = open(destination, 'wb+')
    for chunk in post_file.chunks():
        destination.write(chunk)
    destination.close()


def create_directory(filename):
    dir = os.path.dirname(filename)
    if not os.path.exists(dir):
        current_mask = os.umask(0000)
        os.makedirs(dir)
        os.umask(current_mask)


def upload_file(post_file, file_path, file_name=''):
    name = post_file.name.lower()
    name, ext = os.path.splitext(name)
    name = "%s%s" % (get_slug(name) or 'unknown', ext)
    if not file_name:
        file_name = os.path.splitext(post_file.name)[0].lower()
    if ext in ('.rar', '.zip', '.7z', '.gz', '.gzip'):
        temp = os.path.join(file_path, name).replace('\\', '/')
        file_save_uploaded(post_file, temp)
        _name = unpack_file(temp, file_path, file_name)
        os.remove(temp)
        return _name
    else:
        file_name = '%s%s' % (file_name, os.path.splitext(name)[1])
        destination = os.path.join(file_path, file_name).replace('\\', '/')
        file_save_uploaded(post_file, destination)
    return destination


def save_file(afile, **kwargs):
    folder = kwargs.get('folder', '')
    if folder:
        folder = force_text(folder)
        if not folder.endswith('/'):
            folder = u"%s/" % folder
    name = str(kwargs.get('name', ''))
    media_root = kwargs.get('media_root', settings.MEDIA_ROOT)
    prefix = kwargs.get('prefix')
    filename, ext = os.path.splitext(afile)
    ext = ext.lower()
    if ext == '.jpeg':
        ext = '.jpg'
    if name:
        name = force_text(name)
        name = get_slug(os.path.splitext(name)[0])
    else:
        name = force_text(hashlib.md5(force_bytes(str(random.random()) + settings.SECRET_KEY + ':)')).hexdigest())
    if prefix is not None:
        imagename = u"%s%s/%s%s" % (folder, prefix, name, ext)
    else:
        imagename = u"%s%s%s" % (folder, name, ext)
    filename = "%s/%s" % (media_root, imagename)
    filename = filename.replace('\\', '/')
    create_directory(filename)
    shutil.copyfile(afile, filename)
    if prefix is not None:
        return "%s%s/%s%s" % (folder, prefix, name, ext)
    else:
        return "%s%s%s" % (folder, name, ext)


def get_file_hash(filename, blocksize=2 * 1024 * 1024):
    with open(filename, 'rb') as f:
        buf = [0]
        shasum = hashlib.sha1()
        while len(buf) > 0:
            buf = f.read(blocksize)
            shasum.update(buf)
    return str(shasum.hexdigest())


def file_md5sum(filename):
    try:
        f = open(filename, 'rb')
    except Exception:
        return -1
    m = hashlib.md5()
    while True:
        d = f.read(bufsize)
        if not d:
            break
        m.update(d)
    result = m.hexdigest()
    f.close()
    return result
