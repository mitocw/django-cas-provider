from django import forms
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _
from .models import LoginTicket
import datetime


__all__ = ['LoginForm', ]


class LoginForm(AuthenticationForm):
    lt = forms.CharField(widget=forms.HiddenInput)
    service = forms.CharField(widget=forms.HiddenInput, required=False)

    def clean_lt(self):
        ticket = self.cleaned_data['lt']
        timeframe = datetime.datetime.now() - \
                    datetime.timedelta(minutes=settings.CAS_TICKET_EXPIRATION)
        try:
            return LoginTicket.objects.get(ticket=ticket, created__gte=timeframe)
        except LoginTicket.DoesNotExist:
            raise ValidationError(_('Login ticket expired. Please try again.'))
        return ticket

    def clean(self):
        AuthenticationForm.clean(self)
        self.cleaned_data.get('lt').delete()
        return self.cleaned_data

    def get_errors(self):
        errors = []
        for k, error in self.errors.items():
            errors += [e for e in error]
        return errors
