# Orignal version taken from http://www.djangosnippets.org/snippets/186/
# Original author: udfalkso

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
import pprint
import cProfile
import pstats

from django.conf import settings
from django.db import connection
from django.http import HttpResponse
from django.utils.encoding import force_bytes


class ProfileMiddleware(object):

    def __init__(self, get_response=None):
        self.get_response = get_response
        super(ProfileMiddleware, self).__init__()

    def __call__(self, request):
        response = self.get_response(request)
        if settings.DEBUG and 'prof' in request.GET:
            self.profiler.create_stats()
            out = StringIO()
            ps = pstats.Stats(self.profiler, stream=out).sort_stats('tottime')
            ps.print_stats()
            response = HttpResponse(content_type='text/plain')
            response.content = force_bytes(out.getvalue())
            sql = '\n%d SQL Queries in %.3f seconds :\n' % (
                len(connection.queries), sum([float(i.get('time', 0))
                                              for i in connection.queries]))
            response.content += force_bytes(sql)
            response.content += force_bytes(pprint.pformat(connection.queries))
        return response

    def process_view(self, request, callback, callback_args, callback_kwargs):
        if settings.DEBUG and 'prof' in request.GET:
            self.profiler = cProfile.Profile()
            args = (request,) + callback_args
            return self.profiler.runcall(callback, *args, **callback_kwargs)
