===================
django-cas-provider
===================

OVERVIEW
=========

django-cas-provider is a provider for the `Central Authentication Service <http://jasig.org/cas>`_. It supports CAS version 1.0 and parts of CAS version 2.0 protocol. It allows remote services to authenticate users for the purposes of Single Sign-On (SSO). For example, a user logs into a CAS server
(provided by django-cas-provider) and can then access other services (such as email, calendar, etc) without re-entering her password for each service. For more details, see the `CAS wiki <http://www.ja-sig.org/wiki/display/CAS/Home>`_ and `Single Sign-On on Wikipedia <http://en.wikipedia.org/wiki/Single_Sign_On>`_.

INSTALLATION
=============

To install, run the following command from this directory::

    python setup.py install

Or, put `cas_provider` somewhere on your Python path.

If you want use CAS v.2 protocol or above, you must install `lxml` package to correct work.

UPDATING FROM PREVIOUS VERSION
===============================

I introduced south for DB schema migration. The schema from any previous version without south is 0001_initial.
You will get an error:

    ``Running migrations for cas_provider:``

    ``- Migrating forwards to 0001_initial.``

    ``> cas_provider:0001_initial``

    ``Traceback (most recent call last):``

    ``...``

    ``django.db.utils.DatabaseError: relation "cas_provider_serviceticket" already exists``

to circumvent that problem you will need to fake the initial migration:

 python manage.py migrate cas_provider 0001_initial --fake


USAGE
======

#. Add ``'cas_provider'`` to your ``INSTALLED_APPS`` tuple in *settings.py*.
#. In *settings.py*, set ``LOGIN_URL`` to ``'/cas/login/'`` and ``LOGOUT_URL`` to ``'/cas/logout/'``
#. In *urls.py*, put the following line: ``(r'^cas/', include('cas_provider.urls')),``
#. Create login/logout templates (or modify the samples)
#. Use 'cleanuptickets' management command to clean up expired tickets

SETTINGS
=========

CAS_TICKET_EXPIRATION - minutes to tickets expiration. Default is 5 minutes.

CAS_CUSTOM_ATTRIBUTES_CALLBACK - name of callback to provide dictionary with
extended user attributes (may be used in CAS v.2 or above). Default is None.

CAS_CUSTOM_ATTRIBUTES_FORMAT - name of custom attribute formatter callback will be
used to format custom user attributes. This package provide module `attribute_formatters`
with formatters for common used formats. Available formats styles are `RubyCAS`, `Jasig`
and `Name-Value. Default is Jasig style. See module source code for more details.

CAS_AUTO_REDIRECT_AFTER_LOGOUT - If False (default behavior, specified in CAS protocol)
after successful logout notification page will be shown. If it's True, after successful logout will
be auto redirect back to service without any notification.

CAS_USERNAME_FIELD - Specify the user model field to send back as the username. e.g. email instead
of username. Default is username


PROTOCOL DOCUMENTATION
=====================

* `CAS Protocol <http://www.jasig.org/cas/protocol>`
* `CAS 1 Architecture <http://www.jasig.org/cas/cas1-architecture>`
* `CAS 2 Architecture <http://www.jasig.org/cas/cas2-architecture>`
* `Proxy Authentication <http://www.jasig.org/cas/proxy-authentication>`
* `CAS – Central Authentication Service <http://www.jusfortechies.com/cas/overview.html>`
* `Proxy CAS Walkthrough <https://wiki.jasig.org/display/CAS/Proxy+CAS+Walkthrough>`

PROVIDED VIEWS
=============

login
---------

It has not required arguments.

Optional arguments:

* template_name - login form template name (default is 'cas/login.html')
* success_redirect - redirect after successful login if service GET argument is not provided
   (default is settings.LOGIN_REDIRECT_URL)
* warn_template_name - warning page template name to allow login user to service if he
  already authenticated in SSO (default is 'cas/warn.html')

If request.GET has 'warn' argument and user has already authenticated in SSO it shows
warning message instead of generate Service Ticket and redirect.

logout
-----------

This destroys a client's single sign-on CAS session. The ticket-granting cookie is destroyed,
and subsequent requests to login view will not obtain service tickets until the user again
presents primary credentials (and thereby establishes a new single sign-on session).

It has not required arguments.

Optional arguments:

* template_name - template name for page with successful logout message (default is 'cas/logout.html')

validate
-------------

It checks the validity of a service ticket. It is part of the CAS 1.0 protocol and thus does
not handle proxy authentication.

It has not arguments.

service_validate
-------------------------

It checks the validity of a service ticket and returns an XML-fragment response via CAS 2.0 protocol.
Work with proxy is not supported yet.

It has not arguments.


CUSTOM USER ATTRIBUTES FORMAT
===========================

Custom attribute format style may be changed in project settings with 
CAS_CUSTOM_ATTRIBUTES_FORMAT constant. You can provide your own formatter callback
or specify existing in this package in `attribute_formatters` module.

Attribute formatter callback takes two arguments:

*  `auth_success` - `cas:authenticationSuccess` node. It is `lxml.etree.SubElement`instance;
*  `attrs` - dictionary with user attributes received from callback specified in 
    CAS_CUSTOM_ATTRIBUTES_CALLBACK in project settings. 

Example of generated XML below::
 
     <cas:serviceResponse xmlns:cas='http://www.yale.edu/tp/cas'>
         <cas:authenticationSuccess>
             <cas:user>jsmith</cas:user>

             <!-- extended user attributes wiil be here -->

             <cas:proxyGrantingTicket>PGTIOU-84678-8a9d2sfa23casd</cas:proxyGrantingTicket>
         </cas:authenticationSuccess>
     </cas:serviceResponse>


* Name-Value style (provided in `cas_provider.attribute_formatters.name_value`)::

    <cas:attribute name='attraStyle' value='Name-Value' />
    <cas:attribute name='surname' value='Smith' />
    <cas:attribute name='givenName' value='John' />
    <cas:attribute name='memberOf' value='CN=Staff,OU=Groups,DC=example,DC=edu' />
    <cas:attribute name='memberOf' value='CN=Spanish Department,OU=Departments,OU=Groups,DC=example,DC=edu' />


*  Jasig Style attributes (provided in `cas_provider.attribute_formatters.jasig`)::

    <cas:attributes>
        <cas:attraStyle>Jasig</cas:attraStyle>
        <cas:surname>Smith</cas:surname>
        <cas:givenName>John</cas:givenName>
        <cas:memberOf>CN=Staff,OU=Groups,DC=example,DC=edu</cas:memberOf>
        <cas:memberOf>CN=Spanish Department,OU=Departments,OU=Groups,DC=example,DC=edu</cas:memberOf>
    </cas:attributes>


* RubyCAS style (provided in `cas_provider.attribute_formatters.ruby_cas`)::

    <cas:attraStyle>RubyCAS</cas:attraStyle>
    <cas:surname>Smith</cas:surname>
    <cas:givenName>John</cas:givenName>
    <cas:memberOf>CN=Staff,OU=Groups,DC=example,DC=edu</cas:memberOf>
    <cas:memberOf>CN=Spanish Department,OU=Departments,OU=Groups,DC=example,DC=edu</cas:memberOf>

