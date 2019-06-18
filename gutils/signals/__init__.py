import django.dispatch

post_delete = django.dispatch.Signal(providing_args=["sender"])
post_change = django.dispatch.Signal(providing_args=["sender"])

pre_init_view = django.dispatch.Signal(providing_args=["sender"])
post_init_view = django.dispatch.Signal(providing_args=["sender"])
