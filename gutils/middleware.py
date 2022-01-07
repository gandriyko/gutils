# -*- coding: utf-8 -*-
from django.urls import resolve
from django.conf import settings


class BaseMiddleware(object):

    def __init__(self, get_response=None):
        self.get_response = get_response
        super(BaseMiddleware, self).__init__()

    def __call__(self, request):
        request.is_popup = 'popup' in request.GET
        request.country = request.META.get('GEOIP_COUNTRY_CODE')
        if not hasattr(request, 'LANGUAGE_CODE'):
            request.LANGUAGE_CODE = settings.LANGUAGE_CODE
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        try:
            request.view_func = view_func.__name__
            request.view_name = ".".join((view_func.__module__, view_func.__name__))
        except Exception:
            request.view_func = ''
            request.view_name = ''
        try:
            request.url_name = resolve(request.path_info).url_name or ''
        except Exception:
            request.url_name = ''


class XRealIPMiddleware(object):

    def __init__(self, get_response=None):
        self.get_response = get_response
        super(XRealIPMiddleware, self).__init__()

    def __call__(self, request):
        ip = request.META.get('HTTP_X_REAL_IP')
        if ip:
            request.META['REMOTE_ADDR'] = ip
        response = self.get_response(request)
        return response
