from django.urls import re_path
from django.utils import timezone
from django.views.decorators.http import last_modified
from gutils.views import JavaScriptCatalog
from gutils.admin import views

last_modified_date = timezone.now()

urlpatterns = [
    re_path(r'^item\-change/(?P<model_path>[\w\.\-]+)/(?P<pk>\d+)/(?P<field>[\w_\.]+)/$', views.ItemChangeView.as_view(),
        name='admin-item-change'),
    re_path(r'^item\-delete/(?P<model_path>[\w\.]+)/(?P<pk>\d+)/$', views.ItemDeleteView.as_view(),
        name='admin-item-delete'),
    re_path(r'^images/$', views.ImageListView.as_view(),
        name='admin-image-list'),
    re_path(r'^gutils\-locale\.js$', last_modified(lambda req, **kw: last_modified_date)(JavaScriptCatalog.as_view()),
        name='gutils-locale-js'),
]
