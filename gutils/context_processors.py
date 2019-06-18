# -*- coding: utf-8 -*-

from django.conf import settings
from gutils.shortcuts import get_next_url


def variables(request):
    if request.is_popup:
        base_template = 'gutils/popup.html'
    else:
        base_template = 'gutils/base.html'
    full_path = request.get_full_path()
    if full_path.startswith('/%s/' % request.LANGUAGE_CODE):
        full_path = full_path[len(request.LANGUAGE_CODE) + 2:]
    else:
        full_path = ''
    LANGUAGES_REGION = getattr(settings, 'LANGUAGES_REGION', {})
    alternate_languages = list(dict(code=l[0], name=l[1], url='/%s/%s' % (l[0], full_path), region=LANGUAGES_REGION.get(l[0]))
                               for l in settings.LANGUAGES)
    current_language = ''
    for l in settings.LANGUAGES:
        if l[0] == request.LANGUAGE_CODE:
            current_language = l[1]

    return {'user': getattr(request, 'user', None),
            'path': request.path,
            'full_path': request.get_full_path(),
            'scheme': request.scheme,
            'is_popup': request.is_popup,
            'view_func': getattr(request, 'view_func', ''),
            'view_name': getattr(request, 'view_name', ''),
            'url_name': getattr(request, 'url_name', ''),
            'country': getattr(request, 'country', None),
            'next_url': get_next_url(request),
            'alternate_languages': alternate_languages,
            'current_language': current_language,
            'base_template': base_template,
            'query_dict': request.GET,
            'static_css': {},
            'static_js': [],
            'cookies': request.COOKIES,
            'DOMAIN': settings.DOMAIN,
            'HTTP_HOST': request.META.get('HTTP_HOST'),
            'DEBUG': settings.DEBUG
            }
