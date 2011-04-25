#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright (c) 2010 OpenStack, LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""
Auth Middleware that handles auth for a service

This module can be installed as a filter in front of your service to validate
that requests are coming from a trusted component that has handled
authenticating the call. If a call comes from an untrusted source, it will
redirect it back to be properly authenticated. This is done by sending our a 305
proxy redirect response with the URL for the auth service.

The auth service settings are specified in the INI file (keystone.ini). The ini
file is passed in as the WSGI config file when starting the service. For this
proof of concept, the ini file is in echo/echo/echo.ini.

In the current implementation use a basic auth password to verify that the
request is coming from a valid auth component or service

Refer to: http://wiki.openstack.org/openstack-authn


HEADERS
-------

www-authenticate    : only used if this component is being used remotely
HTTP_AUTHORIZATION  : basic auth password used to validate the connection
HTTP_X_AUTHORIZATION: the client token being passed in
HTTP_X_AUTH_TOKEN   : the client token being passed in
HTTP_X_STORAGE_TOKEN: the client token being passed in (legacy Rackspace use)
                      to support cloud files

"""

from webob.exc import HTTPUseProxy, HTTPUnauthorized


class PAPIAuth(object):

    # app is the downstream WSGI component, usually the OpenStack service
    #
    # if app is not provided, the assumption is this filter is being run
    # from a separate server.

    def __init__(self, app, conf):
        self.app = app
        self.conf = conf
        self.auth_host = conf.get('auth_ip', '127.0.0.1')
        self.auth_port = int(conf.get('auth_port', 11000))
        self.auth_pass = conf.get('auth_pass', 'dTpw')
        self.proxy_location = 'http://%s:%d/' % (self.auth_host,
            self.auth_port)
        print 'Starting PAPI Auth middleware'

    def __call__(self, env, start_response):
        print "PAPIAuth handling a service call"
        # Make sure that the user has been authenticated by the Auth Service
        if 'HTTP_X_AUTHORIZATION' not in env:
            self.proxy_location = 'http://' + self.auth_host + ':' + \
                str(self.auth_port) + '/'
            return HTTPUseProxy(location=self.proxy_location)(env,
                start_response)

        # Authenticate the Auth component itself.
        headers = [('www-authenticate', 'Basic realm="echo"')]
        if 'HTTP_AUTHORIZATION' not in env:
            return HTTPUnauthorized(headers=headers)(env, start_response)
        else:
            auth_type, encoded_creds = env['HTTP_AUTHORIZATION'].split(None, 1)
            if encoded_creds != self.auth_pass:
                return HTTPUnauthorized(headers=headers)(env, start_response)

        return self.app(env, start_response)


def filter_factory(global_conf, **local_conf):
    """Returns a WSGI filter app for use with paste.deploy."""
    conf = global_conf.copy()
    conf.update(local_conf)

    def auth_filter(app):
        return PAPIAuth(app, conf)
    return auth_filter
