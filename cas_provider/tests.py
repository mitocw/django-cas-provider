import StringIO
import urllib2
from xml import etree
from xml.etree import ElementTree
import cas_provider
from cas_provider.attribute_formatters import CAS, NSMAP
from cas_provider.models import ServiceTicket
from cas_provider.views import _cas2_sucess_response, INVALID_TICKET, _cas2_error_response, generate_proxy_granting_ticket
from django.contrib.auth.models import User, UserManager
from django.core.urlresolvers import reverse
from django.test import TestCase
from urlparse import urlparse, parse_qsl, parse_qs
from django.conf import settings




dummy_urlopen_url = None


def dummy_urlopen(url):
    cas_provider.tests.dummy_urlopen_url = url
    pass

class ViewsTest(TestCase):

    fixtures = ['cas_users', ]



    def setUp(self):
        self.service = 'http://example.com/'


    def test_successful_login_with_proxy(self):
        urllib2.urlopen = dummy_urlopen # monkey patching urllib2.urlopen so that the testcase doesnt really opens a url
        proxyTarget = "http://my.sweet.service"

        response = self._login_user('root', '123')
        response = self._validate_cas2(response, True, proxyTarget )

        # Test: I'm acting as the service that will call another service
        # Step 1: Get the proxy granting ticket
        responseXml = ElementTree.parse(StringIO.StringIO(response.content))
        auth_success = responseXml.find(CAS + 'authenticationSuccess', namespaces=NSMAP)
        pgt = auth_success.find(CAS + "proxyGrantingTicket", namespaces=NSMAP)
        user = auth_success.find(CAS + "user", namespaces=NSMAP)
        self.assertEqual('root', user.text)
        self.assertIsNotNone(pgt.text)
        self.assertTrue(pgt.text.startswith('PGTIOU'))

        pgtId = parse_qs(urlparse(cas_provider.tests.dummy_urlopen_url).query)['pgtId']

        #Step 2: Get the actual proxy ticket
        proxyTicketResponse = self.client.get(reverse('proxy'), {'targetService': proxyTarget, 'pgt': pgtId}, follow=False)
        proxyTicketResponseXml = ElementTree.parse(StringIO.StringIO(proxyTicketResponse.content))
        self.assertIsNotNone(proxyTicketResponseXml.find(CAS + "proxySuccess", namespaces=NSMAP))
        self.assertIsNotNone(proxyTicketResponseXml.find(CAS + "proxySuccess/cas:proxyTicket", namespaces=NSMAP))
        proxyTicket = proxyTicketResponseXml.find(CAS + "proxySuccess/cas:proxyTicket", namespaces=NSMAP);

        #Step 3: I have the proxy ticket I can talk to some other backend service as the currently logged in user!
        proxyValidateResponse = self.client.get(reverse('cas_proxy_validate'), {'ticket': proxyTicket.text, 'service': proxyTarget})
        proxyValidateResponseXml = ElementTree.parse(StringIO.StringIO(proxyValidateResponse.content))

        auth_success_2 = proxyValidateResponseXml.find(CAS + 'authenticationSuccess', namespaces=NSMAP)
        user_2 = auth_success.find(CAS + "user", namespaces=NSMAP)
        proxies_1  = auth_success_2.find(CAS + "proxies")
        self.assertIsNone(proxies_1) # there are no proxies. I am issued by a Service Ticket
        
        self.assertEqual(user.text, user_2.text)


    def test_successful_proxy_chaining(self):
        urllib2.urlopen = dummy_urlopen # monkey patching urllib2.urlopen so that the testcase doesnt really opens a url
        proxyTarget_1 = "http://my.sweet.service_1"
        proxyTarget_2 = "http://my.sweet.service_2"

        response = self._login_user('root', '123')
        response = self._validate_cas2(response, True, proxyTarget_1 )

        # Test: I'm acting as the service that will call another service
        # Step 1: Get the proxy granting ticket
        responseXml = ElementTree.parse(StringIO.StringIO(response.content))
        auth_success_1 = responseXml.find(CAS + 'authenticationSuccess', namespaces=NSMAP)
        pgt_1 = auth_success_1.find(CAS + "proxyGrantingTicket", namespaces=NSMAP)
        user_1 = auth_success_1.find(CAS + "user", namespaces=NSMAP)
        self.assertEqual('root', user_1.text)
        self.assertIsNotNone(pgt_1.text)
        self.assertTrue(pgt_1.text.startswith('PGTIOU'))

        pgtId_1 = parse_qs(urlparse(cas_provider.tests.dummy_urlopen_url).query)['pgtId']

        #Step 2: Get the actual proxy ticket
        proxyTicketResponse_1 = self.client.get(reverse('proxy'), {'targetService': proxyTarget_1, 'pgt': pgtId_1}, follow=False)
        proxyTicketResponseXml_1 = ElementTree.parse(StringIO.StringIO(proxyTicketResponse_1.content))
        self.assertIsNotNone(proxyTicketResponseXml_1.find(CAS + "proxySuccess", namespaces=NSMAP))
        self.assertIsNotNone(proxyTicketResponseXml_1.find(CAS + "proxySuccess/cas:proxyTicket", namespaces=NSMAP))
        proxyTicket_1 = proxyTicketResponseXml_1.find(CAS + "proxySuccess/cas:proxyTicket", namespaces=NSMAP);

        #Step 3: I'm backend service 1 - I have the proxy ticket - I want to talk to back service 2
        #
        proxyValidateResponse_1 = self.client.get(reverse('cas_proxy_validate'), {'ticket': proxyTicket_1.text, 'service': proxyTarget_1, 'pgtUrl': proxyTarget_2})
        proxyValidateResponseXml_1 = ElementTree.parse(StringIO.StringIO(proxyValidateResponse_1.content))

        auth_success_2 = proxyValidateResponseXml_1.find(CAS + 'authenticationSuccess', namespaces=NSMAP)
        user_2 = auth_success_2.find(CAS + "user", namespaces=NSMAP)

        proxies_1  = auth_success_2.find(CAS + "proxies")
        self.assertIsNone(proxies_1) # there are no proxies. I am issued by a Service Ticket
        self.assertIsNotNone(auth_success_2)
        self.assertEqual('root', user_2.text)

        pgt_2 = auth_success_2.find(CAS + "proxyGrantingTicket", namespaces=NSMAP)
        user = auth_success_2.find(CAS + "user", namespaces=NSMAP)
        self.assertEqual('root', user.text)
        self.assertIsNotNone(pgt_2.text)
        self.assertTrue(pgt_2.text.startswith('PGTIOU'))

        pgtId_2 = parse_qs(urlparse(cas_provider.tests.dummy_urlopen_url).query)['pgtId']

        #Step 4: Get the second proxy ticket
        proxyTicketResponse_2 = self.client.get(reverse('proxy'), {'targetService': proxyTarget_2, 'pgt': pgtId_2})
        proxyTicketResponseXml_2 = ElementTree.parse(StringIO.StringIO(proxyTicketResponse_2.content))
        self.assertIsNotNone(proxyTicketResponseXml_2.find(CAS + "proxySuccess", namespaces=NSMAP))
        self.assertIsNotNone(proxyTicketResponseXml_2.find(CAS + "proxySuccess/cas:proxyTicket", namespaces=NSMAP))
        proxyTicket_2 = proxyTicketResponseXml_2.find(CAS + "proxySuccess/cas:proxyTicket", namespaces=NSMAP)

        proxyValidateResponse_3 = self.client.get(reverse('cas_proxy_validate'), {'ticket': proxyTicket_2.text, 'service': proxyTarget_2, 'pgtUrl': None})
        proxyValidateResponseXml_3 = ElementTree.parse(StringIO.StringIO(proxyValidateResponse_3.content))

        auth_success_3 = proxyValidateResponseXml_3.find(CAS + 'authenticationSuccess', namespaces=NSMAP)
        user_3 = auth_success_3.find(CAS + "user", namespaces=NSMAP)

        proxies_3  = auth_success_3.find(CAS + "proxies")
        self.assertIsNotNone(proxies_3) # there should be a proxy. I am issued by a Proxy Ticket
        proxy_3 = proxies_3.find(CAS + "proxy", namespaces=NSMAP)
        self.assertEqual(proxyTarget_1, proxy_3.text )

        self.assertIsNotNone(auth_success_2)
        self.assertEqual('root', user_3.text)



    
    def test_succeessful_login(self):
        response = self._login_user('root', '123')
        self._validate_cas1(response, True)

        response = self.client.get(reverse('cas_login'), {'service': self.service}, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['location'].startswith('%s?ticket=' % self.service))

        response = self.client.get(reverse('cas_login'), follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['location'].startswith('http://testserver/'))

        response = self.client.get(response['location'], follow=False)
        self.assertIn(response.status_code, [302, 200])

        response = self.client.get(reverse('cas_login'), {'service': self.service, 'warn': True}, follow=False)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cas/warn.html')


    def _cas_logout(self):
        response = self.client.get(reverse('cas_logout'), follow=False)
        self.assertEqual(response.status_code, 200)


    def test_logout(self):
        response = self._login_user('root', '123')
        self._validate_cas1(response, True)

        self._cas_logout()

        response = self.client.get(reverse('cas_login'), follow=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user'].is_anonymous(), True)


    def test_broken_pwd(self):
        self._fail_login('root', '321')

    def test_broken_username(self):
        self._fail_login('notroot', '123')

    def test_nonactive_user_login(self):
        self._fail_login('nonactive', '123')

    def test_cas2_success_validate(self):
        response = self._login_user('root', '123')
        response = self._validate_cas2(response, True)
        user = User.objects.get(username=self.username)
        self.assertEqual(response.content, _cas2_sucess_response(user).content)

    def test_cas2_custom_attrs(self):
        settings.CAS_CUSTOM_ATTRIBUTES_CALLBACK = cas_mapping
        response = self._login_user('editor', '123')

        response = self._validate_cas2(response, True)
        self.assertEqual(response.content, '''<cas:serviceResponse xmlns:cas="http://www.yale.edu/tp/cas">'''
                                           '''<cas:authenticationSuccess>'''
                                           '''<cas:user>editor</cas:user>'''
                                           '''<cas:attributes>'''
                                           '''<cas:attraStyle>Jasig</cas:attraStyle>'''
                                           '''<cas:group>editor</cas:group>'''
                                           '''<cas:is_staff>True</cas:is_staff>'''
                                           '''<cas:is_active>True</cas:is_active>'''
                                           '''<cas:email>editor@exapmle.com</cas:email>'''
                                           '''</cas:attributes>'''
                                           '''</cas:authenticationSuccess>'''
                                           '''</cas:serviceResponse>''')

        self._cas_logout()
        response = self._login_user('editor', '123')
        settings.CAS_CUSTOM_ATTRIBUTES_FORMATER = 'cas_provider.attribute_formatters.ruby_cas'
        response = self._validate_cas2(response, True)
        self.assertEqual(response.content, '''<cas:serviceResponse xmlns:cas="http://www.yale.edu/tp/cas">'''
                                           '''<cas:authenticationSuccess>'''
                                           '''<cas:user>editor</cas:user>'''
                                           '''<cas:attraStyle>RubyCAS</cas:attraStyle>'''
                                           '''<cas:group>editor</cas:group>'''
                                           '''<cas:is_staff>True</cas:is_staff>'''
                                           '''<cas:is_active>True</cas:is_active>'''
                                           '''<cas:email>editor@exapmle.com</cas:email>'''
                                           '''</cas:authenticationSuccess>'''
                                           '''</cas:serviceResponse>''')

        self._cas_logout()
        response = self._login_user('editor', '123')
        settings.CAS_CUSTOM_ATTRIBUTES_FORMATER = 'cas_provider.attribute_formatters.name_value'
        response = self._validate_cas2(response, True)
        self.assertEqual(response.content, '''<cas:serviceResponse xmlns:cas="http://www.yale.edu/tp/cas">'''
                                           '''<cas:authenticationSuccess>'''
                                           '''<cas:user>editor</cas:user>'''
                                           '''<cas:attribute name="attraStyle" value="Name-Value"/>'''
                                           '''<cas:attribute name="group" value="editor"/>'''
                                           '''<cas:attribute name="is_staff" value="True"/>'''
                                           '''<cas:attribute name="is_active" value="True"/>'''
                                           '''<cas:attribute name="email" value="editor@exapmle.com"/>'''
                                           '''</cas:authenticationSuccess>'''
                                           '''</cas:serviceResponse>''')


    def test_cas2_fail_validate(self):
        for user, pwd in (('root', '321'), ('notroot', '123'), ('nonactive', '123')):
            response = self._login_user(user, pwd)
            self._validate_cas2(response, False)


    def test_generate_proxy_granting_ticket(self):
        urllib2.urlopen = dummy_urlopen # monkey patching urllib2.urlopen so that the testcase doesnt really opens a url
        url = 'http://my.call.back/callhere'

        user = User.objects.get(username = 'root')
        st = ServiceTicket.objects.create(user = user )
        pgt = generate_proxy_granting_ticket(url, st)
        self.assertIsNotNone(pgt)

        calledUrl = cas_provider.tests.dummy_urlopen_url
        parsedUrl = urlparse(calledUrl)
        params = parse_qs(parsedUrl.query)
        self.assertIsNotNone(params['pgtId'])
        self.assertIsNotNone(params['pgtIou'])



    def _fail_login(self, username, password):
        response = self._login_user(username, password)
        self._validate_cas1(response, False)

        response = self.client.get(reverse('cas_login'), {'service': self.service}, follow=False)
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('cas_login'), follow=False)
        self.assertEqual(response.status_code, 200)



    def _login_user(self, username, password):
        self.username = username
        response = self.client.get(reverse('cas_login'), {'service': self.service})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cas/login.html')
        form = response.context['form']
        service = form['service'].value()
        return self.client.post(reverse('cas_login'), {
            'username': username,
            'password': password,
            'lt': form['lt'].value(),
            'service': service
        }, follow=False)


    def _validate_cas1(self, response, is_correct=True):
        if is_correct:
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.has_header('location'))
            location = urlparse(response['location'])
            ticket = location.query.split('=')[1]

            response = self.client.get(reverse('cas_validate'), {'ticket': ticket, 'service': self.service}, follow=False)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(unicode(response.content), u'yes\n%s\n' % self.username)
        else:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.context['form'].errors), 1)

            response = self.client.get(reverse('cas_validate'), {'ticket': 'ST-12312312312312312312312', 'service': self.service}, follow=False)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, u'no\n\n')


    def _validate_cas2(self, response, is_correct=True, pgtUrl = None):
        if is_correct:
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.has_header('location'))
            location = urlparse(response['location'])
            ticket = location.query.split('=')[1]
            if pgtUrl:
                response = self.client.get(reverse('cas_service_validate'), {'ticket': ticket, 'service': self.service, 'pgtUrl': pgtUrl}, follow=False)
            else:
                response = self.client.get(reverse('cas_service_validate'), {'ticket': ticket, 'service': self.service}, follow=False)
            self.assertEqual(response.status_code, 200)
        else:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.context['form'].errors), 1)

            response = self.client.get(reverse('cas_service_validate'), {'ticket': 'ST-12312312312312312312312', 'service': self.service}, follow=False)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, _cas2_error_response(INVALID_TICKET).content)
        return response

class ModelsTestCase(TestCase):

    fixtures = ['cas_users.json', ]

    def setUp(self):
        self.user = User.objects.get(username='root')

    def test_redirects(self):
        ticket = ServiceTicket.objects.create(service='http://example.com', user=self.user)
        self.assertEqual(ticket.get_redirect_url(), '%(service)s?ticket=%(ticket)s' % ticket.__dict__)

    def test_plus_encoding(self):
        ticket = ServiceTicket.objects.create(
            service='http://example.com/?next=/courses/course-v1:MITx+6.042r_4+2017_Fall/',
            user=self.user
        )
        assert (
            "next=%2Fcourses%2Fcourse-v1%3AMITx%2B6.042r_4%2B2017_Fall%2F" in ticket.get_redirect_url()
        )


def cas_mapping(user):
    return {
        'is_staff': unicode(user.is_staff),
        'is_active': unicode(user.is_active),
        'email': user.email,
        'group': [g.name for g in user.groups.all()]
    }
