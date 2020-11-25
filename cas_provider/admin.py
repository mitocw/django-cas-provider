from django.contrib import admin
from .models import *


class ServiceTicketAdmin(admin.ModelAdmin):
    list_display = ('user', 'service', 'created')
    list_filter = ('created',)

class ProxyTicketAdmin(admin.ModelAdmin):
    list_display = ('user', 'service', 'created')
    list_filter = ('created',)

class LoginTicketAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'created')
    list_filter = ('created',)

class ProxyGrantingTicketAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'created')
    list_filter = ('created',)

class ProxyGrantingTicketIOUAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'created')
    list_filter = ('created',)

admin.site.register(ServiceTicket, ServiceTicketAdmin)
admin.site.register(ProxyTicket, ProxyTicketAdmin)
admin.site.register(LoginTicket, LoginTicketAdmin)
admin.site.register(ProxyGrantingTicket, ProxyGrantingTicketAdmin)
admin.site.register(ProxyGrantingTicketIOU, ProxyGrantingTicketIOUAdmin)
