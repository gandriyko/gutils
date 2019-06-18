# -*- coding: utf-8 -*-
from django.conf import settings
from django.http import HttpResponse
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.db.models.query import QuerySet
from gutils import to_int
from django.shortcuts import redirect, render, resolve_url
from django.urls import reverse
from gutils.strings import JSONEncoder

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse
import json


def get_page(request, objects, number=1, per_page=0, max_qty=None, total_qty=None, sort=None, sorting=None):
    if not per_page:
        per_page = getattr(settings, 'GUTILS_ITEMS_PER_PAGE', 30)
    if request:
        number = to_int(request.GET.get('page'), 1)
    else:
        number = to_int(number, 1)
    if request and isinstance(objects, QuerySet) and sorting:
        s = request.GET.get('sort', '')
        if s in sorting or (s.startswith('-') and s[1:] in sorting):
            sort = s
        if sort:
            objects = objects.order_by(sort)
    if max_qty:
        objects = objects[:max_qty]
    paginator = Paginator(objects, per_page)
    paginator._count = total_qty
    try:
        page = paginator.page(number)
    except (EmptyPage, InvalidPage):
        page = paginator.page(paginator.num_pages)
    page.sort = sort
    return page


def get_sort(request, name, default=None, sort_list=None):
    sort = request.GET.get('sort')
    if sort is not None:
        if sort_list and sort not in sort_list and not (sort.startswith('-') and sort[1:] in sort):
            sort = default
        if sort is not None and sort != request.session.get(name):
            request.session[name] = sort
        return sort
    return request.session.get(name, default)


def set_sort(request, name, value):
    request.session[name] = value


def close_view(request, **kwargs):
    url = kwargs.get('url')
    args = kwargs.get('args')
    next_url = kwargs.get('next')
    stay = kwargs.get('stay')
    popup = kwargs.get('popup', request.is_popup)
    timeout = to_int(kwargs.get('timeout'))
    if timeout:
        timeout *= 1000
    if request.is_popup and popup and not stay:
        return render(request, 'gutils/popup_done.html', {'timeout': timeout, 'next': ''})
    if next_url:
        result_url = next_url
    else:
        result_url = reverse(url, args=args)
    if popup and 'popup=1' not in result_url:
        if '?' in result_url:
            result_url += '&popup=1'
        else:
            result_url += '?popup=1'
    return redirect(result_url)


def redirect_view(request, url):
    result = url
    if request.is_popup:
        if '?' in result:
            result = '%s&popup=1' % result
        else:
            result = '%s?popup=1' % result
    return redirect(result)


def response_json(data):
    return HttpResponse(json.dumps(data, cls=JSONEncoder), content_type='application/json; charset=utf-8')


def get_ip(request):
    ip = request.META.get(settings.REMOTE_ADDR, '')
    if not ip:
        try:
            ip = request.META.get('HTTP_X_FORWARDED_FOR', ',').split(',')[0]
        except:
            pass
    if not ip:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


def get_referer(request, default_url='/', with_params=True, local_only=False):
    ref = urlparse(request.META.get('HTTP_REFERER', ''))
    if local_only and request.META['HTTP_HOST'] != ref.netloc:
        return default_url
    if ref.path and with_params and ref.query:
        return "%s?%s" % (ref.path, ref.query)
    return ref.path or default_url


def get_next_url(request, default='/'):
    next_url = request.POST.get('next', '')
    if not next_url:
        next_url = request.GET.get('next', '')
    if not next_url:
        next_url = request.META.get('HTTP_REFERER', '')
    next_url = next_url.replace('http://%s' % settings.DOMAIN, '')
    if next_url == request.get_full_path():
        return default
    return next_url or default
