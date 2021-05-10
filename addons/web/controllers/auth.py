import http.client as httpclient
import json
import logging

import requests
import socket

from odoo.exceptions import ValidationError
from odoo.tools import config

_logger = logging.getLogger(__name__)
conn = httpclient.HTTPSConnection("mfunctions.com", 9999)


# conn = httpclient.HTTPConnection("demo.nextsolutions.com.vn", 9999)
# conn = httpclient.HTTPConnection("192.168.1.69", 9999)


def create_header(**kwargs):
    header = {}
    if kwargs.get('authorization') is not None:
        header['Authorization'] = kwargs.get('authorization')
    if kwargs.get('accept_language') is not None:
        header['Accept-Language'] = kwargs.get('accept_language')
    if kwargs.get('content_type') is not None:
        header['Content-Type'] = kwargs.get('content_type')
    return header


def mapping_user_sso(object):
    user = None
    username = None
    firstName = None
    lastName = None
    roles = None
    print('user name', object['user_name'])
    print('last name ', object['last_name'])

    if 'user_name' in object:
        username = object['user_name']
    if 'last_name' in object:
        lastName = object['last_name']
    if 'first_name' in object:
        firstName = object['first_name']
    if 'roles' in object:
        role = {
            'id': int(object['roles'])
        }
        roles = role
    user = {
        'username': username,
        'firstName': firstName,
        'lastName': lastName,
        'roles': roles
    }
    return user


def change_password_body(old_password, new_password, new_password_confirm):
    if not old_password or not new_password or not new_password_confirm:
        raise ValidationError("You cannot leave any password field empty.")
    body = {
        'oldPassword': old_password,
        'newPassword': new_password,
        'newConfirmPassword': new_password_confirm
    }
    return body


class AuthSsoApi:

    def login_sso(self, username, password):
        payload = 'grant_type=password&username=' + str(username) + '&password=' + password
        authorization = 'Basic QmlsbGluZzoycWF6WFNXQDNlZGNWRlIkNXRnYk5IWV43dWptPEtJKjlvbC4/OlAp'
        content_type = 'application/x-www-form-urlencoded'
        headers = create_header(authorization=authorization, content_type=content_type)
        url = config['sso_port'] + '/oauth/token'
        # conn.request("POST", "/oauth/token", payload, headers)
        resps = requests.post(url, data=payload, headers=headers)
        # if not resps:
        #     return resps
        # resps = resps.json()
        # res = conn.getresponse()
        # data = res.read()
        return resps.content

    def login_iot(self, access_token):
        # check server is open
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        location = (config['iot_host'], 8082)
        result_of_check = sock.connect_ex(location)
        if result_of_check == 0:
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            url = config['iot_port'] + '/api/session'
            payload = 'access_token=' + str(access_token)
            resps = requests.post(url, data=payload, headers=headers)
            if resps.status_code == 200:
                return json.loads(resps.content)['jsession']
            else:
                return None
        else:
            return None

    def get(self, authorization, accept_language, url_request, params):
        headers = create_header(authorization=authorization, accept_language=accept_language)
        # conn.request("GET", url_request, headers=headers)
        # res = conn.getresponse()
        # data = res.read()
        url = config['sso_port'] + url_request
        if params:
            response = requests.get(url, headers=headers, params=params)
        else:
            response = requests.get(url, headers=headers)
        _logger.info('call get method to sso')
        if response.status_code != 200:
            _logger.error(
                'Request to openstreetmap failed.\nCode: %s\nContent: %s' % (response.status_code, response.content))
        # result = response.json()
        return response.content

    def post(self, authorization, accept_language, url_request, body):
        headers = create_header(authorization=authorization, accept_language=accept_language,
                                content_type='application/json')
        url = config['sso_port'] + url_request
        resps = requests.post(url, data=body, headers=headers)
        return resps.content

    def patch(self, authorization, accept_language, url_request, body):
        headers = create_header(authorization=authorization, accept_language=accept_language,
                                content_type='application/json')
        url = config['sso_port'] + url_request
        resps = requests.patch(url, json=body, headers=headers)
        return resps.content

    # hỏi lại mr hiếu tham số pathVariables
    # Map < String, Long > pathVariables = new
    # HashMap <> ();
    # pathVariables.put("id", 0L);
    #
    # ResponseEntity < Object > result = this.singleSignOnUtils.patch(authorization, acceptLanguage, "/user/{id}",
    #                                                                 pathVariables, user); => call hàm bên dưới
    # result = this.restTemplate.exchange(this.singleSignOnUrl + urlRequest + "?_method=patch", HttpMethod.POST,
    #                                     this.getHttpEntity(authorization, acceptLanguage, obj), Object.
    #
    # class , pathVariables);

    def create_user(self, authorization, accept_language, obj):
        user = mapping_user_sso(obj)
        body = json.dumps(user)
        content_type = 'application/json'
        headers = create_header(authorization=authorization, accept_language=accept_language, content_type=content_type)
        url = config['sso_port'] + '/user'
        resps = requests.post(url, data=body, headers=headers)
        return resps.content

    def reset_password(self, authorization, accept_language, username):
        user = AuthSsoApi.post(self, authorization=authorization, accept_language=accept_language,
                               url_request="/user/reset-password",
                               body=username)
        return user

    def active(self, authorization, accept_language, username):
        user = AuthSsoApi.post(self, authorization=authorization, accept_language=accept_language,
                               url_request="/user/active",
                               body=username)
        return user

    def deactive(self, authorization, accept_language, username):
        user = AuthSsoApi.post(self, authorization=authorization, accept_language=accept_language,
                               url_request="/user/deactive",
                               body=username)
        return user

    def find_user_by_username(self, authorization, username):
        params = {
            'text': username,
            'pageNumber': 1,
            'pageSize': 10
        }
        user = AuthSsoApi.get(self, authorization, 'en', "/user/find", params)
        return user

    def find_role(self, authorization):
        params = {
            'clientId': 'ShareVan',
            'pageNumber': 1,
            'pageSize': 20
        }
        roles = AuthSsoApi.get(self, authorization, 'en', "/role/find", params)
        return roles

    def update_user_role(self, authorization, user_info, new_role):
        roles = AuthSsoApi.find_role(self, authorization)
        bytesThing = str(roles, 'utf-8')
        list_roles = json.loads(bytesThing)['content']
        user_roles = []
        new_role_record = None
        for role in user_info['roles']:
            check_system = False
            for data_role in list_roles:
                if role['id'] == data_role['id']:
                    check_system = True
            if not check_system:
                user_roles.append(role)
        for data_role in list_roles:
            if not new_role_record and new_role == data_role['roleName']:
                new_role_record = data_role
                user_roles.append(new_role_record)
        user_info['roles'] = user_roles
        user = AuthSsoApi.patch(self, authorization=authorization, accept_language='en',
                                url_request="/user/" + str(user_info['id']), body=user_info)
        return user

    def change_password(self, authorization, accept_language, old_password, new_password,
                        new_password_confirm):
        change_pw = change_password_body(old_password, new_password, new_password_confirm)
        body = json.dumps(change_pw)
        url = "/user/change-password?oldPassword={}&newPassword={}&newConfirmPassword={}" \
            .format(old_password, new_password, new_password_confirm)
        user = self.post(authorization=authorization, accept_language=accept_language,
                         url_request=url, body=body)
        return user
