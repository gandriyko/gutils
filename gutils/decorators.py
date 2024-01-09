# -*- coding: utf-8 -*-

from django.shortcuts import redirect
from django.core.cache import cache
from django.utils.encoding import force_bytes
from django.http import HttpResponse
from django.utils.safestring import mark_safe
from django.core.mail import mail_admins
import hashlib
import time
import functools
from markupsafe import Markup
import pickle
from gutils.shortcuts import get_ip


def safe(function):
    @functools.wraps(function)
    def _decorator(*args, **kwargs):
        return Markup(mark_safe(function(*args, **kwargs)))
    return _decorator


def save_path(view):
    def wrapped(request, *args, **kwargs):
        key = 'sp:%s.%s' % (view.__module__, view.__name__)
        if request.method == 'GET':
            if request.GET.items():
                request.user.set_data(key, request.get_full_path())
            elif request.META.get('HTTP_REFERER'):
                path = request.user.get_data(key)
                if path:
                    if request.META['HTTP_REFERER'].endswith(path):
                        request.user.set_data(key, '')
                    else:
                        return redirect(path)
            else:
                request.user.set_data(key, '')
        return view(request, *args, **kwargs)
    return wrapped


def duplicate_protection(view_name):
    def wrapped(request, *args, **kwargs):
        if request.method != 'POST':
            return view_name(request, *args, **kwargs)
        _key = '%s:%s:%s' % (getattr(request.user, 'pk', 0), request.get_full_path(), get_ip(request))
        key = 'lock-%s' % hashlib.md5(force_bytes(_key)).hexdigest()
        result = cache.get(key)
        if result is not None:
            if result == '':
                time.sleep(1)
                return HttpResponse('Duplication error')
            try:
                return pickle.loads(str(result))
            except Exception:
                return HttpResponse('SitePage error.')
        cache.set(key, '', 2)
        result = view_name(request, *args, **kwargs)
        cache.set(key, pickle.dumps(result), 2)
        return result
    return wrapped
