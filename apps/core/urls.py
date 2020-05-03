from django.conf.urls import include, url
from djoser import views as djoser_views

from . import views

auth_urls = [
    url(r'^login', views.ObtainJSONWebToken.as_view(), name='login'),
    url(r'^check_email/$', views.check_email, name='check_email'),
    url(r'^password/$', djoser_views.SetPasswordView.as_view(), name='set_password'),
    url(r'^password/reset/$', djoser_views.PasswordResetView.as_view(), name='password_reset'),
    url(r'^password/reset/confirm/$', djoser_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    url(r'', include('djoser.urls.authtoken')),
]

urlpatterns = [
    url(r'^auth/', include(auth_urls)),
]
