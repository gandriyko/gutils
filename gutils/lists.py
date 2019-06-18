import itertools


def iter_parts(iterable, n):
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, n))
        if not chunk:
            return
        yield chunk


def split_list(alist, wanted_parts=1):
    length = len(alist)
    return [alist[i * length // wanted_parts: (i + 1) * length // wanted_parts]
            for i in range(wanted_parts)]


def split_range(range_min, range_max, wanted_parts=1):
    length = range_max - range_min
    return [[i * length // wanted_parts, (i + 1) * length // wanted_parts] for i in range(wanted_parts)]
