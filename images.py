# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.conf import settings
from django.db import models
from django.utils.encoding import force_text
from gutils.strings import get_slug
from gutils import to_int, base36encode
import os
import glob
import re
import uuid
import shutil

try:
    from PIL import Image, ImageOps
except ImportError:
    import Image
    import ImageOps


def upload_to(field, path, func=None):
    def wrapper(instance, filename):
        ext = os.path.splitext(filename)[1]
        if func:
            filename = func(instance)
        else:
            filename = base36encode(uuid.uuid4().int).lower()
        image = os.path.join(path, '%s%s' % (filename, ext))
        delete_image(image)
        if instance.pk:
            item = instance.__class__.objects.get(pk=instance.pk)
            prev_image = getattr(item, field)
            if prev_image:
                delete_image(prev_image)
        return image
    return wrapper


class ImageField(models.ImageField):

    def __init__(self, *args, **kwargs):
        name_func = kwargs.get('name_func')
        if hasattr(kwargs, 'name_func'):
            del kwargs['name_func']
        partition = kwargs.get('partition', None)
        if hasattr(kwargs, 'partition'):
            del kwargs['partition']
        super(ImageField, self).__init__(*args, **kwargs)
        self.name_func = name_func
        self.partition = partition

    def generate_filename(self, instance, filename):
        ext = os.path.splitext(filename)[1]
        if self.name_func:
            filename = self.name_func(instance) + ext
        else:
            filename = base36encode(uuid.uuid4().int).lower() + ext
            if self.partition:
                filename = os.path.join(filename[:2], filename)
        image = os.path.join(self.upload_to, filename)
        delete_image(image)
        return image

    def pre_save(self, model_instance, add):
        file = super(ImageField, self).pre_save(model_instance, add)
        if model_instance.pk:
            item = model_instance.__class__.objects.get(pk=model_instance.pk)
            prev_file = getattr(item, self.attname)
            if file != prev_file:
                delete_image(prev_file)
        return file


class ImageModel(models.Model):

    '''
        Abstract model implementing a two-phase save in order to rename and resize
        IMAGES = { 'image1': {'dest': 'imagesfolder', 'max_size': '800x600' } }
    '''
    IMAGES = {}

    class Meta:
        abstract = True

    def save(self, force_insert=False, force_update=False):
        images = getattr(self, 'IMAGES', None)
        if images:
            super(ImageModel, self).save(force_insert, force_update)
            force_insert, force_update = False, False
            for field_name, options in images.iteritems():
                field = getattr(self, field_name)
                if not field:
                    continue
                file_name = field.name
                name, ext = os.path.splitext(file_name)
                ext = ext.lower()
                name = base36encode(uuid.uuid4().int).lower()
                final_name = os.path.join(options['dest'], name)
                final_name += ext
                final_name = final_name.replace('\\', '/')
                if file_name != final_name:
                    field.storage.delete(final_name)
                    # delete thumbnails
                    delete_thumbnail(final_name)
                    field.storage.save(final_name, field)
                    if options['max_size']:
                        full_path = os.path.join(settings.MEDIA_ROOT, final_name).replace('\\', '/')
                        width, height = options['max_size'].split('x')
                        resize(full_path, full_path, width, height, False)
                    setattr(self, field_name, final_name)
                    try:  # windows fix
                        field.storage.delete(file_name)
                    except:
                        pass
        super(ImageModel, self).save(force_insert, force_update)


def save_uploaded(post_file, name):
    destination = open(name, 'wb+')
    for chunk in post_file.chunks():
        destination.write(chunk)
    destination.close()


def _check_dir(filename):
    """
    Check directory if exists
    """
    dir = os.path.dirname(filename)
    if not os.path.exists(dir):
        current_mask = os.umask(0000)
        os.makedirs(dir)
        os.umask(current_mask)


def save_temp_image(obj, path):
    s = str(obj.pk).zfill(9)
    ext = path.split('.')[-1]
    image = '%s/%s/%s/%s.%s' % (obj.image.field.upload_to, s[:-6], s[-6:-3], obj.pk, ext)
    if not move_image('temp/%s' % path, image):
        return False
    else:
        obj.image = image
        obj.save()
        return True


def move_image(source, destination):
    source = force_text(source)
    destination = force_text(destination)
    source = os.path.join(settings.MEDIA_ROOT, source).replace('\\', '/')
    if not os.path.isfile(source):
        return False
    destination = os.path.join(settings.MEDIA_ROOT, destination).replace('\\', '/')
    _check_dir(destination)
    shutil.move(source, destination)
    return destination


def resize(source, destination, width, height, crop=False, watermark=None, quality=85):
    """
    Resize image. Example: resize(a, b, 100, 100)
    """
    img = Image.open(source)
    width = to_int(width)
    height = to_int(height)
    img_width, img_height = img.size
    if width or height:
        if width and not height:
            height = int(float(img_height) * width / img_width)
            crop = True
        if height and not width:
            width = int(float(img_width) * height / img_height)
            crop = True

        if img_width > width or img_height > height:
            if crop:
                img = ImageOps.fit(img, (width, height), Image.LANCZOS)
            else:
                img.thumbnail((width, height), Image.LANCZOS)
        elif crop:
            if width > height:
                height = int(float(img_width) * height / width)
                width = img_width
            else:
                width = int(float(img_height) * width / height)
                height = img_height
            img = ImageOps.fit(img, (width, height), Image.LANCZOS)

    if watermark:
        try:
            mark = Image.open(settings.WATERMARK)
        except Exception:
            mark = None
        if mark:
            ratio = min(float(img_width) / mark.size[0],
                        float(img_height) / mark.size[1])
            width = int(mark.size[0] * ratio)
            height = int(mark.size[1] * ratio)
            mark = mark.resize((width, height), Image.LANCZOS)
            img.paste(mark, (0, 0), mark)
    _check_dir(destination)
    ext = os.path.splitext(source)[1].lower()
    if ext in ('.jpeg', '.jpg') and img.mode == 'RGBA':
        img = img.convert('RGB')
    img.save(destination, quality=quality)
    return destination


def save_image(post_file, **kwargs):
    folder = kwargs.get('folder', '')
    if folder:
        folder = force_text(folder)
        if not folder.endswith('/'):
            folder = '%s/' % folder
    size = kwargs.get('size')
    name = kwargs.get('name', '')
    media_root = kwargs.get('media_root', settings.MEDIA_ROOT)
    prefix = kwargs.get('prefix')
    quality = kwargs.get('quality', getattr(settings, 'GUTILS_IMAGE_QUALITY', 85))
    partition = kwargs.get('partition', False)
    overwrite = kwargs.get('overwrite', False)
    if name:
        name = force_text(name)
        name = get_slug(os.path.splitext(name)[0])
    else:
        name = base36encode(uuid.uuid4().int).lower()
    image = folder
    if prefix is not None:
        image = '%s%s/' % (folder, prefix)
    if partition:
        if to_int(name):
            image = '%s%s/' % (image, to_int(name) // 1000)
        else:
            image = '%s%s/' % (image, name[:2])

    filename, ext = os.path.splitext(post_file.name)
    ext = ext.lower()
    if ext == '.jpeg':
        ext = '.jpg'

    image = '%s%s%s' % (image, name, ext)
    image = image.replace('\\', '/').replace('//', '/')
    if not overwrite:
        image = unique_image(image, media_root)
    filename = '%s/%s' % (media_root, image)
    filename = filename.replace('\\', '/')
    _check_dir(filename)
    if not overwrite:
        delete_image(image)
    save_uploaded(post_file, filename)
    if size:
        r = re.search(r'(\d+)x(\d+)', size)
        if r:
            width = r.group(1)
            height = r.group(2)
            try:
                resize(filename, filename, width, height, quality=quality)
            except IOError:
                return ''
    return image


def unique_image(image, media_root=None):
    if not media_root:
        media_root = settings.MEDIA_ROOT
    path = os.path.join(media_root, image).replace('\\', '/')
    if not os.path.exists(path):
        return image
    name, ext = os.path.splitext(image)
    max_n = 1
    path = os.path.join(media_root, '%s~*%s' % (name, ext)).replace('\\', '/')
    for f in glob.glob(path):
        n = to_int(f.split('~')[-1].split('.')[0])
        if n > max_n:
            max_n = n
    return '%s~%s%s' % (name, max_n + 1, ext)


def delete_image(filename):
    try:
        filename = force_text(filename)
        if filename:
            delete_thumbnail(filename)
            path = os.path.join(settings.MEDIA_ROOT, filename).replace('\\', '/')
            if os.path.exists(path):
                os.remove(path)
    except:
        return False
    return True


def thumbnail(name, params='', replace=False, fake=False, exclude=None):
    '''
        Create thumbnail from image in filename.
        Note: filename is short name
    '''
    name = force_text(name)
    if exclude:
        for e in exclude.split(','):
            if name.startswith(e):
                return name
    if name.startswith('https://'):
        name = name[8:]
    elif name.startswith('http://'):
        name = name[7:]
    if name.startswith(settings.DOMAIN):
        name = name[len(settings.DOMAIN):]
    if name.startswith(settings.MEDIA_URL):
        name = name[len(settings.MEDIA_URL):]
    if not name or '.' not in name:
        name = 'no.png'
    filename = os.path.join(settings.MEDIA_ROOT, name).replace('\\', '/')
    if not fake and not os.path.exists(filename):
        name = 'no.png'
        filename = os.path.join(settings.MEDIA_ROOT, name).replace('\\', '/')
    if not params:
        return os.path.join(settings.MEDIA_URL, name)
    basename, format = name.rsplit('.', 1)
    miniature = ("%s_%s.%s") % (basename, params.replace(' ', ''), format)
    miniature_filename = os.path.join(settings.MEDIA_ROOT, 'thumbs', miniature).replace('\\', '/')
    miniature_url = os.path.join(settings.MEDIA_URL, 'thumbs', miniature).replace('\\', '/')
    if fake:
        return miniature_url
    if not os.path.exists(miniature_filename) or replace:
        if 'c' in params:
            crop = True
        else:
            crop = False
        if 'w' in params:
            watermark = True
        else:
            watermark = False
        r = re.search(r'(\d+)x(\d+)', params)
        if r:
            width = r.group(1)
            height = r.group(2)
        else:
            width = 0
            height = 0
        resize(filename, miniature_filename, width, height, crop, watermark)
    return miniature_url


def delete_thumbnail(filename):
    try:
        filename = force_text(filename)
        if filename:
            path = os.path.join(settings.MEDIA_ROOT, 'thumbs', filename).replace('\\', '/')
            name, ext = path.rsplit('.', 1)
            name = name.replace('\\', '/')
            for file in glob.glob(name + '_*'):
                if os.path.exists(file):
                    os.remove(file)
    except:
        return False
    return True


def text_thumbnails(text):
    images = re.findall(r'(<img[^>]* src="%s[^>]+>)' % settings.MEDIA_URL, text)
    for img in images:
        src = re.findall(r' src="(.+?)"', img)[0]
        res = re.findall(r' width="(\d+)"', img)
        if res:
            width = res[0]
        else:
            width = 0
        res = re.findall(r' height="(\d+)"', img)
        if res:
            height = res[0]
        else:
            height = 0
        if width or height:
            thumb = img.replace('src="%s"' % src, 'src="%s"' % thumbnail(src, '%sx%s' % (width, height)))
            text = text.replace(img, thumb)
    return text


def generate_thumbnails(items, field='text'):
    r = re.compile(r'%sthumbs/(\w+)/(\w+?)_([\dx]+)([\w\.]*)' % settings.MEDIA_URL)
    for item in items:
        text = getattr(item, field)
        images = r.findall(text)
        for i in images:
            thumbnail('%s/%s%s' % (i[0], i[1], i[3]), i[2], True)


def encode_text_images(text, path):
    '''
    замінити всі посилання на малюнок на ід
    <a href="/static/article/12.jpg"> ==> <a href="image::12">
    <img src="/static/article/12_100x100.jpg" /> ==> <img src="image::12_100x100"/>
    '''
    if not path.endswith('/'):
        path += '/'
    re_link = re.compile(r'href="%s(\d+).+?"' % path)
    re_img = re.compile(r'\<img(.*?)\>')
    re_src = re.compile(r'src="%s(\d+).+?"' % path)
    re_widht = re.compile(r'width="(\d+)"')
    re_height = re.compile(r'height="(\d+)"')
    ids = []

    links = re_link.findall(text)
    if links:
        for id in links:
            id = int(id)
            ids.append(id)
            replace = r'href="image::%s"' % id
            text = re.sub(r'\href="(%s%s\.\w+?)"' % (path, id), replace, text)
    images = re_img.findall(text)
    if images:
        for img in images:
            res = re_src.search(img)
            if not res:
                continue
            id = int(res.groups()[0])
            ids.append(id)
            res = re_widht.search(img)
            if res:
                width = int(res.groups()[0])
            else:
                width = 0
            res = re_height.search(img)
            if res:
                height = int(res.groups()[0])
            else:
                height = 0
            if width or height:
                replace = 'src="image::%s_%sx%s"' % (id, width, height)
            else:
                replace = 'src="image::%s"' % id
            text = re.sub(r'src="%s%s.+?"' % (path, id), replace, text, 1)
    return text, ids


def decode_text_images(text, images):
    images = dict((i.pk, i) for i in images)
    re_out = re.compile(r'"image::([\d_x]+)"')
    res = re_out.findall(text)
    noimage = '%s%s' % (settings.MEDIA_URL, 'no.png')
    for r in res:
        if '_' in r:
            id, size = r.split('_')
            id = int(id)
        else:
            id = int(r)
            size = 0
        image = images.get(id)
        if image:
            if size:
                filename = thumbnail(image.image, size)
            else:
                filename = "%s%s" % (settings.MEDIA_URL, image.image)
        else:
            filename = noimage
        text = text.replace('"image::%s"' % r, '"%s"' % filename, 1)
    return text
