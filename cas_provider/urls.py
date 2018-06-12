from django.conf.urls import url

from cas_provider.views import (
    login,
    logout,
    validate,
    proxy,
    proxy_validate,
    service_validate,
)

urlpatterns = [
    url(r'^login/?$', login, name='cas_login'),
    url(r'^validate/?$', validate, name='cas_validate'),
    url(r'^proxy/?$', proxy, name='proxy'),
    url(r'^serviceValidate/?$', service_validate, name='cas_service_validate'),
    url(r'^proxyValidate/?$', proxy_validate, name='cas_proxy_validate'),
    url(r'^logout/?$', logout, name='cas_logout')
]
