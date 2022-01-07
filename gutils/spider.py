from django.core.cache import caches
from user_agent import generate_user_agent
import requests
import random
import time
import hashlib


def get_hash(value):
    m = hashlib.md5()
    m.update(value)
    return m.hexdigest()


class Spider(object):

    def __init__(self, **kwargs):
        self.session = requests.Session()
        self.cookies = {}
        self.sleep = kwargs.get('sleep', False)
        self.cached = kwargs.get('cached', False)
        self.use_proxy = kwargs.get('use_proxy', False)
        self.proxies = kwargs.get('proxies', [])
        self.proxy_auth = kwargs.get('proxy_auth', '')
        self.verbose = kwargs.get('verbose', False)
        self.use_session = kwargs.get('use_session', False)
        self.response = None
        self.timeout = kwargs.get('timeout', 10)

    def get_cookies(self):
        return self.cookies

    def get_headers(self, override=None):
        result = {'User-agent': generate_user_agent(),
                  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                  'Accept-language': 'ru,ru-RU,en-US,en'}
        if override:
            result.update(override)
        return result

    def get(self, url, **kwargs):
        cached = kwargs.get('cached', self.cached)
        force = kwargs.get('force', False)
        encoding = kwargs.get('encoding', 'utf-8')
        headers = kwargs.get('headers')
        if cached and not force:
            key = 'spider-%s' % get_hash(url)
            result = caches['file'].get(key)
            if result is not None:
                if self.verbose:
                    print('Get chached %s' % url)
                return result

        sleep = kwargs.get('sleep', self.sleep)
        min_length = kwargs.get('min_length', 0)
        raw = kwargs.get('raw', False)
        retrying = kwargs.get('retrying', 5)

        for i in range(0, retrying):
            if self.use_proxy and self.proxies:
                ip = random.choice(self.proxies)
                if self.proxy_auth:
                    p = 'http://%s@%s' % (self.proxy_auth, ip)
                else:
                    p = 'http://%s' % ip
                proxy = {'http': p, 'https': p}
                if self.verbose:
                    print('Get [%20s] %s' % (ip, url))
            else:
                proxy = None
                if self.verbose:
                    print('Get %s' % url)
            try:
                if self.use_session:
                    get = self.session.get
                else:
                    get = requests.get
                response = get(url,
                               headers=self.get_headers(headers),
                               cookies=self.get_cookies(),
                               proxies=proxy,
                               timeout=self.timeout)
                self.response = response
                if response.status_code != 200:
                    print('HTTP Status: %s' % response.status_code, url)
                    continue
                if sleep:
                    time.sleep(sleep)
                if raw:
                    if cached:
                        key = 'spider-%s' % get_hash(url)
                        caches['file'].set(key, response.content, 7 * 24 * 60 * 60)
                    return response.content
                response.encoding = encoding
                text = response.text
                if not text or (min_length and len(text) < min_length):
                    print('Http response length < %s' % min_length, url)
                    continue
                text = text.replace('\ufeff', '')
                if cached:
                    key = 'spider-%s' % get_hash(url)
                    caches['file'].set(key, text, 24 * 60 * 60)
                return text
            except Exception as e:
                print(e, url)
                continue

    def post(self, url, data, **kwargs):
        encoding = kwargs.get('encoding', 'utf-8')
        sleep = kwargs.get('sleep', False)
        min_length = kwargs.get('min_length', 0)
        raw = kwargs.get('raw', False)
        retrying = kwargs.get('retrying', 5)
        headers = kwargs.get('headers')

        for i in range(0, retrying):
            if self.use_proxy and self.proxies:
                ip = random.choice(self.proxies)
                if self.proxy_auth:
                    p = 'http://%s@%s' % (self.proxy_auth, ip)
                else:
                    p = 'http://%s' % ip
                proxy = {'http': p, 'https': p}
                if self.verbose:
                    print('Get [%20s] %s' % (ip, url))
            else:
                proxy = None
                if self.verbose:
                    print('Post %s' % url)
            try:
                if self.use_session:
                    post = self.session.post
                else:
                    post = requests.post
                response = post(url,
                                headers=self.get_headers(headers),
                                cookies=self.get_cookies(),
                                proxies=proxy,
                                timeout=self.timeout,
                                data=data)
                self.response = response
                if response.status_code != 200:
                    print('HTTP Status: %s' % response.status_code)
                    continue
                if sleep:
                    time.sleep(sleep)
                if raw:
                    return response.content
                response.encoding = encoding
                text = response.text
                if not text or (min_length and len(text) < min_length):
                    continue
                text = text.replace('\ufeff', '')
                return text
            except Exception as e:
                print(e)
                continue
