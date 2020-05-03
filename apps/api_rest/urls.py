from django.conf.urls import include, url
from rest_framework_nested import routers

from . import views

router = routers.SimpleRouter()
router.register(r'items', views.ItemsListView)

api_urls = [
    url(r'^constants/$', views.get_constants, name='constants'),
    # url(r'^items/$', views.ItemsListView.as_view(), name='item-list'),
]

urlpatterns = [
    url(r'^', include(api_urls)),
    url(r'', include(router.urls)),
]
