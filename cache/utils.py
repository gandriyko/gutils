from __future__ import unicode_literals
from __future__ import print_function

from django.utils.encoding import force_text, smart_bytes, force_bytes
from unidecode import unidecode
from six import string_types
import hashlib
import sys

CONTROL_CHARACTERS = set([chr(i) for i in range(0, 33)])
CONTROL_CHARACTERS.add(chr(127))
MAX_LENGTH = 230


def _func_info(func, args):
    ''' introspect function's or method's full name.
    Returns a tuple (name, normalized_args,) with
    'cls' and 'self' removed from normalized_args '''

    func_type = _func_type(func)
    if sys.version_info < (3, 0):
        lineno = ":%s" % func.func_code.co_firstlineno
    else:
        lineno = ":%s" % func.__code__.co_firstlineno

    if func_type == 'function':
        name = ".".join([func.__module__, func.__name__]) + lineno
        return name, args

    class_name = args[0].__class__.__name__
    if func_type == 'classmethod':
        class_name = args[0].__name__

    name = ".".join([func.__module__, class_name, func.__name__]) + lineno
    return name, args[1:]


def _func_type(func):
    """ returns if callable is a function, method or a classmethod """
    if sys.version_info < (3, 0):
        argnames = func.func_code.co_varnames[:func.func_code.co_argcount]
    else:
        argnames = func.__code__.co_varnames[:func.__code__.co_argcount]

    if len(argnames) > 0:
        if argnames[0] == 'self':
            return 'method'
        if argnames[0] == 'cls':
            return 'classmethod'
    return 'function'


def _args_to_unicode(args, kwargs):

    def as_string(value):
        if value is None:
            return 'None'
        if hasattr(value, 'pk'):
            return force_text(getattr(value, 'pk', None))
        if isinstance(value, (list, tuple)):
            res = [force_text(v) for v in value]
            return "[%s]" % ",".join(res)
        if isinstance(value, string_types):
            return unidecode(force_text(value))
        return str(value)

    key = []
    if args:
        key += [as_string(a) for a in args]
    if kwargs:
        key += ['%s=%s' % (smart_bytes(k), as_string(v)) for k, v in kwargs.items()]
    return u",".join(key)


def _cache_key(func_name, func_type, args, kwargs, force_key=None):
    """ Construct readable cache key """
    if force_key:
        return force_key
    if func_type == 'function':
        args_string = _args_to_unicode(args, kwargs)
    else:
        args_string = _args_to_unicode(args[1:], kwargs)
    key = '%s(%s)' % (func_name, args_string,)
    key = ''.join([c for c in key if c not in CONTROL_CHARACTERS])
    key = force_bytes(key)
    if len(key) > MAX_LENGTH:
        try:
            h = force_text(hashlib.md5(key).hexdigest())
        except Exception as e:
            print(e)
            h = ''
        key = "%s-%s" % (key[:MAX_LENGTH - 33], h)
    return key
