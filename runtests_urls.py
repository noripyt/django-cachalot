import debug_toolbar
from django.conf.urls import url, include
from django.http import HttpResponse


def empty_page(request):
    return HttpResponse('<body></body>')


urlpatterns = [
    url(r'^$', empty_page),
    url(r'^__debug__/', include(debug_toolbar.urls)),
]
