import debug_toolbar
from django.urls import re_path, include
from django.http import HttpResponse


def empty_page(request):
    return HttpResponse('<body></body>')


urlpatterns = [
    re_path(r'^$', empty_page),
    re_path(r'^__debug__/', include(debug_toolbar.urls)),
]
