import logging
from lxml import etree
from urllib import urlencode
import urllib2
import urlparse
from django.conf import settings
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.core.urlresolvers import get_callable
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from cas_provider.attribute_formatters import NSMAP, CAS
from cas_provider.models import ProxyGrantingTicket, ProxyTicket
from forms import LoginForm
from models import ServiceTicket, LoginTicket


__all__ = ['login', 'validate', 'logout', 'service_validate']

INVALID_TICKET = 'INVALID_TICKET'
INVALID_SERVICE = 'INVALID_SERVICE'
INVALID_REQUEST = 'INVALID_REQUEST'
INTERNAL_ERROR = 'INTERNAL_ERROR'

ERROR_MESSAGES = (
    (INVALID_TICKET, u'The provided ticket is invalid.'),
    (INVALID_SERVICE, u'Service is invalid'),
    (INVALID_REQUEST, u'Not all required parameters were sent.'),
    (INTERNAL_ERROR, u'An internal error occurred during ticket validation'),
    )


logger = logging.getLogger(__name__)

def login(request, template_name='cas/login.html',\
          success_redirect=settings.LOGIN_REDIRECT_URL,
          warn_template_name='cas/warn.html',
          form_class=LoginForm):
    service = request.GET.get('service', None)
    if request.user.is_authenticated():
        if service is not None:
            if request.GET.get('warn', False):
                return render_to_response(warn_template_name, {
                    'service': service,
                    'warn': False
                }, context_instance=RequestContext(request))
            ticket = ServiceTicket.objects.create(service=service, user=request.user)
            return HttpResponseRedirect(ticket.get_redirect_url())
        else:
            return HttpResponseRedirect(success_redirect)
    if request.method == 'POST':
        form = form_class(data=request.POST, request=request)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            service = form.cleaned_data.get('service')
            if service is not None:
                ticket = ServiceTicket.objects.create(service=service, user=user)
                success_redirect = ticket.get_redirect_url()
            return HttpResponseRedirect(success_redirect)
    else:
        form = form_class(request=request, initial={
            'service': service,
            'lt': LoginTicket.objects.create()
        })
    if hasattr(request, 'session') and hasattr(request.session, 'set_test_cookie'):
        request.session.set_test_cookie()
    return render_to_response(template_name, {
        'form': form,
        'errors': form.get_errors() if hasattr(form, 'get_errors') else None,
        }, context_instance=RequestContext(request))


def validate(request):
    """Validate ticket via CAS v.1 protocol"""
    service = request.GET.get('service', None)
    ticket_string = request.GET.get('ticket', None)
    if service is not None and ticket_string is not None:
        #renew = request.GET.get('renew', True)
        #if not renew:
        # TODO: check user SSO session
        try:
            ticket = ServiceTicket.objects.get(ticket=ticket_string)
            assert ticket.service == service
            username = ticket.user.username
            return HttpResponse("yes\n%s\n" % username)
        except:
            pass
    return HttpResponse("no\n\n")


def logout(request, template_name='cas/logout.html',
           auto_redirect=settings.CAS_AUTO_REDIRECT_AFTER_LOGOUT):
    url = request.GET.get('url', None)
    if request.user.is_authenticated():
        for ticket in ServiceTicket.objects.filter(user=request.user):
            ticket.delete()
        auth_logout(request)
        if url and auto_redirect:
            return HttpResponseRedirect(url)
    return render_to_response(template_name, {'url': url},
        context_instance=RequestContext(request))


def proxy(request):
    targetService = request.GET['targetService']
    pgt_id = request.GET['pgt']

    try:
        proxyGrantingTicket = ProxyGrantingTicket.objects.get(ticket=pgt_id)
    except ProxyGrantingTicket.DoesNotExist:
        return _cas2_error_response(INVALID_TICKET)

    pt = ProxyTicket.objects.create(proxyGrantingTicket=proxyGrantingTicket,
        user=proxyGrantingTicket.serviceTicket.user,
        service=targetService)
    return _cas2_proxy_success(pt.ticket)


def ticket_validate(service, ticket_string, pgtUrl):
    if service is None or ticket_string is None:
        return _cas2_error_response(INVALID_REQUEST)

    try:
        if ticket_string.startswith('ST'):
            ticket = ServiceTicket.objects.get(ticket=ticket_string)
        elif ticket_string.startswith('PT'):
            ticket = ProxyTicket.objects.get(ticket=ticket_string)
        else:
            return _cas2_error_response(INVALID_TICKET,
                '%(ticket)s is neither Service (ST-...) nor Proxy Ticket (PT-...)' % {
                    'ticket': ticket_string})
    except ServiceTicket.DoesNotExist:
        return _cas2_error_response(INVALID_TICKET)

    ticketUrl =  urlparse.urlparse(ticket.service)
    serviceUrl =  urlparse.urlparse(service)

    if not(ticketUrl.hostname == serviceUrl.hostname and ticketUrl.path == serviceUrl.path and ticketUrl.port == serviceUrl.port):
        return _cas2_error_response(INVALID_SERVICE)

    pgtIouId = None
    proxies = ()
    if pgtUrl is not None:
        pgt = generate_proxy_granting_ticket(pgtUrl, ticket)
        if pgt:
            pgtIouId = pgt.pgtiou

    if hasattr(ticket, 'proxyticket'):
        pgt = ticket.proxyticket.proxyGrantingTicket
        # I am issued by this proxy granting ticket
        if hasattr(pgt.serviceTicket, 'proxyticket'):
            while pgt:
                if hasattr(pgt.serviceTicket, 'proxyticket'):
                    proxies += (pgt.serviceTicket.service,)
                    pgt = pgt.serviceTicket.proxyticket.proxyGrantingTicket
                else:
                    pgt = None

    user = ticket.user
    return _cas2_sucess_response(user, pgtIouId, proxies)


def service_validate(request):
    """Validate ticket via CAS v.2 protocol"""
    service = request.GET.get('service', None)
    ticket_string = request.GET.get('ticket', None)
    pgtUrl = request.GET.get('pgtUrl', None)
    if ticket_string.startswith('PT-'):
        return _cas2_error_response(INVALID_TICKET, "serviceValidate cannot verify proxy tickets")
    else:
        return ticket_validate(service, ticket_string, pgtUrl)


def proxy_validate(request):
    """Validate ticket via CAS v.2 protocol"""
    service = request.GET.get('service', None)
    ticket_string = request.GET.get('ticket', None)
    pgtUrl = request.GET.get('pgtUrl', None)
    return ticket_validate(service, ticket_string, pgtUrl)


def generate_proxy_granting_ticket(pgt_url, ticket):
    proxy_callback_good_status = (200, 202, 301, 302, 304)
    uri = list(urlparse.urlsplit(pgt_url))

    pgt = ProxyGrantingTicket()
    pgt.serviceTicket = ticket
    pgt.targetService = pgt_url

    if hasattr(ticket, 'proxyGrantingTicket'):
        # here we got a proxy ticket! tata!
        pgt.pgt = ticket.proxyGrantingTicket

    params = {'pgtId': pgt.ticket, 'pgtIou': pgt.pgtiou}

    query = dict(urlparse.parse_qsl(uri[4]))
    query.update(params)

    uri[3] = urlencode(query)

    try:
        response = urllib2.urlopen(urlparse.urlunsplit(uri))
    except urllib2.HTTPError, e:
        if not e.code in proxy_callback_good_status:
            logger.debug('Checking Proxy Callback URL {} returned {}. Not issuing PGT.'.format(uri, e.code))
            return
    except urllib2.URLError, e:
        logger.debug('Checking Proxy Callback URL {} raised URLError. Not issuing PGT.'.format(uri))
        return

    pgt.save()
    return pgt


def _cas2_proxy_success(pt):
    return HttpResponse(proxy_success(pt), mimetype='text/xml')


def _cas2_sucess_response(user, pgt=None, proxies=None):
    return HttpResponse(auth_success_response(user, pgt, proxies), mimetype='text/xml')


def _cas2_error_response(code, message=None):
    return HttpResponse(u'''<cas:serviceResponse xmlns:cas="http://www.yale.edu/tp/cas">
            <cas:authenticationFailure code="%(code)s">
                %(message)s
            </cas:authenticationFailure>
        </cas:serviceResponse>''' % {
        'code': code,
        'message': message if message else dict(ERROR_MESSAGES).get(code)
    }, mimetype='text/xml')


def proxy_success(pt):
    response = etree.Element(CAS + 'serviceResponse', nsmap=NSMAP)
    proxySuccess = etree.SubElement(response, CAS + 'proxySuccess')
    proxyTicket = etree.SubElement(proxySuccess, CAS + 'proxyTicket')
    proxyTicket.text = pt
    return unicode(etree.tostring(response, encoding='utf-8'), 'utf-8')


def auth_success_response(user, pgt, proxies):
    response = etree.Element(CAS + 'serviceResponse', nsmap=NSMAP)
    auth_success = etree.SubElement(response, CAS + 'authenticationSuccess')
    username = etree.SubElement(auth_success, CAS + 'user')
    username.text = user.username

    if settings.CAS_CUSTOM_ATTRIBUTES_CALLBACK:
        callback = get_callable(settings.CAS_CUSTOM_ATTRIBUTES_CALLBACK)
        attrs = callback(user)
        if len(attrs) > 0:
            formater = get_callable(settings.CAS_CUSTOM_ATTRIBUTES_FORMATER)
            formater(auth_success, attrs)

    if pgt:
        pgtElement = etree.SubElement(auth_success, CAS + 'proxyGrantingTicket')
        pgtElement.text = pgt

    if proxies:
        proxiesElement = etree.SubElement(auth_success, CAS + "proxies")
        for proxy in proxies:
            proxyElement = etree.SubElement(proxiesElement, CAS + "proxy")
            proxyElement.text = proxy

    return unicode(etree.tostring(response, encoding='utf-8'), 'utf-8')
