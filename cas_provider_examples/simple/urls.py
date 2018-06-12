from django.conf.urls import url, include
from django.views.generic import TemplateView

urlpatterns = [
    url(r'^', include('cas_provider.urls')),
    url(r'^accounts/profile', TemplateView.as_view(template_name='login-success-redirect-target.html')),
]
