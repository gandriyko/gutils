URLS = {}


def replace_url(urlname):

    def wrapper(cls):
        URLS[urlname] = cls.as_view()
        return cls

    return wrapper


def patch_urls(url_patterns):
    if not URLS:
        return
    for url in url_patterns:
        if hasattr(url, 'url_patterns'):
            patch_urls(url.url_patterns)
        else:
            if url.name in URLS:
                url.callback = URLS[url.name]
