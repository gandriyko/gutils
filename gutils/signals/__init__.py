import django.dispatch

post_delete = django.dispatch.Signal()
post_change = django.dispatch.Signal()

pre_init_view = django.dispatch.Signal()
post_init_view = django.dispatch.Signal()
