
def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


def is_hx(request):
    return request.META.get('HTTP_HX_REQUEST')
