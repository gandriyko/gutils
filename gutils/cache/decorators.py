from django.conf import settings
from django.core.cache import cache
from django.utils.functional import wraps
from gutils.cache.utils import _cache_key, _func_type, _func_info


def cached(timeout=None, force_key=None):
    if not timeout:
        timeout = getattr(settings, 'DEFAULT_CACHE_TIME', 60)

    def _cached(func):

        func_type = _func_type(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            if not hasattr(wrapper, '_full_name'):
                name, _args = _func_info(func, args)
                wrapper._full_name = name
            key = _cache_key(wrapper._full_name, func_type, args, kwargs, force_key)
            value = cache.get(key)
            if value is None:
                value = func(*args, **kwargs)
                cache.set(key, value, timeout)
            return value

        def invalidate(*args, **kwargs):
            if not hasattr(wrapper, '_full_name'):
                return
            key = _cache_key(wrapper._full_name, 'function', args, kwargs)
            cache.delete(key)

        wrapper.invalidate = invalidate
        return wrapper
    return _cached


def cached_by_key(cache_key='', timeout_seconds=1800):
    """
    Django cache decorator

    Example 1:
    class MenuItem(models.Model):
        @classmethod
        @cached('menu_root', 3600*24)
        def get_root(self):
            return MenuItem.objects.get(pk=1)

    Example 2:
    @cached(lambda u: 'user_privileges_%s' % u.email, 3600)
    def get_user_privileges(user):
        #...
    """
    def _cached(func):
        def wrapper(*args, **kws):
            if isinstance(cache_key, str):
                key = cache_key % locals()
            elif callable(cache_key):
                key = cache_key(*args, **kws)
            data = cache.get(key)
            if data is not None:
                return data
            data = func(*args, **kws)
            cache.set(key, data, timeout_seconds)
            return data
        return wrapper
    return _cached
