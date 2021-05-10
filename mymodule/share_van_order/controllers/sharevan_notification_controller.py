# -*- coding: utf-8 -*-
import json
import logging
import random
import sys

from matrix_client.api import MatrixHttpApi
from matrix_client.client import MatrixClient
from matrix_client.errors import MatrixRequestError
from requests.exceptions import MissingSchema

from addons.web.controllers.auth import AuthSsoApi
from mymodule.base_next.models.zone import ShareVanChat
from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request, Response
from odoo.tools import config

matrix_client = MatrixClient(config['chat_server'])
# matrix_client = MatrixClient("https://mingalaba.nextsolutions.com.vn:8089")
server_key = ':demo.nextsolutions.com.vn'
_logger = logging.getLogger(__name__)

def message_event():
    print(matrix_client)


def run_chat_client(username, password):
    # Existing user
    try:
        # if 'access_token' in request.session:
        #     print('token login')
        #     matrix_client = MatrixClient('https://mingalaba.nextsolutions.com.vn:8089',
        #                                  user_id=request.session.user_id,
        #                                  token=request.session.access_token)
        # else:
        devide_id = str(random.randint(0, 99999999))
        matrix_client.login(username=username, password=password, device_id=devide_id)
        return True
    except MatrixRequestError as e:
        print(e)
        if e.code == 403:
            print("Bad username or password.")
            # sys.exit(4)
        else:
            print("Check your sever details are correct.")
            sys.exit(2)
        return False
    except MissingSchema as e:
        print("Bad URL format.")
        print(e)
        # sys.exit(3)
        return False


def on_message(room, event):
    if event['type'] == "m.room.member":
        if event['membership'] == "join":
            print("{0} joined".format(event['content']['displayname']))
    elif event['type'] == "m.room.message":
        if event['content']['msgtype'] == "m.text":
            print("{0}: {1}".format(event['sender'], event['content']['body']))
    else:
        print(event['type'])


class SharevanNotificationController(http.Controller):
    @http.route('/chat/send_message', type='json', auth="user")
    def chat_invite(self, deviceid):
        http.request.env.cr.execute("""
            select driver.phone ,veh.license_plate ,driver.driver_code ,re_us.login,
	                log_driver.date_start,log_driver.date_end 
                from fleet_vehicle_assignation_log log_driver
            join fleet_driver driver on driver.id= log_driver.driver_id
            join res_users re_us on re_us.id =  driver.user_id
			join fleet_vehicle veh on veh.id = log_driver.vehicle_id
                where  log_driver.vehicle_id = %s and log_driver.date_start < NOW() 
					and log_driver.date_end > NOW()
                    and log_driver.status = 'running'
            ORDER BY log_driver.date_start DESC limit 1 """,
                                    (deviceid,))
        result = http.request._cr.dictfetchall()
        if result and request.session.mx_access_token:
            user = result[0]['phone']
            matrix_api = MatrixHttpApi( config['chat_server'],
                                       token=request.session.mx_access_token,
                                       identity=request.session.user_id)
            # matrix_api = MatrixHttpApi("http://192.168.1.63:8080", token=request.session.mx_access_token,
            #                            identity=request.session.user_id)
            content = {
                'search_term': user
                # 'search_term': '@' + phone + ':demo.nextsolutions.com.vn'
            }
            response = matrix_api._send(method='POST', path='/user_directory/search', content=content)
            if response['results']:
                if response['results'][0]:
                    rooms = matrix_client.rooms
                    room_id = ''
                    user_id = response['results'][0]['user_id']
                    for room in rooms:
                        members = rooms[room].get_joined_members()
                        for member in members:
                            if member.user_id == user_id and len(members) < 3:
                                room_id = rooms[room].room_id
                    if room_id == '':
                        try:
                            room = matrix_client.create_room(is_public=True)
                            room.send_text("You have new message from " + request.session.login)
                            matrix_api.invite_user(room.room_id, user_id)
                            return room.room_id
                        except MatrixRequestError as e:
                            print(e)
                    elif room_id != '':
                        return room_id
                    else:
                        raise ValidationError('Driver not found')
                else:
                    raise ValidationError('Driver not found')
            else:
                raise ValidationError('Driver not found')
        else:
            raise ValidationError('Driver not found')

    @http.route('/chat/send_message_partner', type='json', auth="user")
    def chat_call(self,phone):
        if request.session.mx_access_token:
            user = phone
            matrix_api = MatrixHttpApi(config['security_url'] + config['chat_server'],
                                       token=request.session.mx_access_token,
                                       identity=request.session.user_id)
            # matrix_api = MatrixHttpApi("http://192.168.1.63:8080", token=request.session.mx_access_token,
            #                            identity=request.session.user_id)
            content = {
                'search_term': user
                # 'search_term': '@' + phone + ':demo.nextsolutions.com.vn'
            }
            response = matrix_api._send(method='POST', path='/user_directory/search', content=content)
            if response['results']:
                if response['results'][0]:
                    rooms = matrix_client.rooms
                    room_id = ''
                    user_id = response['results'][0]['user_id']
                    for room in rooms:
                        members = rooms[room].get_joined_members()
                        for member in members:
                            if member.user_id == user_id and len(members) < 3:
                                room_id = rooms[room].room_id
                    if room_id == '':
                        try:
                            room = matrix_client.create_room(is_public=True)
                            room.send_text("You have new message from " + request.session.login)
                            matrix_api.invite_user(room.room_id, user_id)
                            return room.room_id
                        except MatrixRequestError as e:
                            print(e)
                    elif room_id != '':
                        return room_id
                    else:
                        raise ValidationError('Customer not found')
                else:
                    raise ValidationError('Customer not found')
            else:
                raise ValidationError('Customer not found')
        else:
            raise ValidationError('You have to sign in chat app')

    @http.route('/chat/login', type='json', auth="user")
    def chat_login(self):
        username = request.session.login
        password = request.session.access_token
        login = run_chat_client(username, password)
        if login:
            request.session['mx_access_token'] = matrix_client.token
            request.session['user_id'] = matrix_client.user_id
            return {
                'mx_access_token': matrix_client.token,
                'user_id': matrix_client.user_id
            }

    @http.route('/web/get_user_info', type='http', auth="none", methods=['POST'], csrf=False)
    def get_user_info(self, username, access_token):
        request.session['db'] = config['database']
        access_token = 'Bearer ' + access_token
        me = AuthSsoApi.get(self, access_token, 'en', "/user/me",None)
        response_data = {}
        bytesThing = str(me, 'utf-8')
        data_json = json.dumps(bytesThing)
        if 'error' not in data_json:
            check_type_query="""
                SELECT us.login username , account_fleet_type
                    FROM public.res_users us
                where us.login = %s LIMIT 1
            """
            http.request.env.cr.execute(check_type_query, (username,))
            user_records = http.request.env.cr.dictfetchall()
            if len(user_records)>0:
                if user_records[0]['account_fleet_type']:
                    query = """
                        SELECT us.login username , employee.name display_name, employee.phone, ir.uri_path
                            FROM public.res_users us
                        JOIN fleet_driver employee on employee.user_id =us.id
                        left JOIN ir_attachment ir on ir.res_id = employee.id and res_model ='fleet.driver' and ir.name='image_1920'
                            where us.login = %s LIMIT 1
                    """
                else:
                    query = """
                        SELECT us.login username , partner.name display_name, partner.phone, ir.uri_path
                            FROM public.res_users us
                        JOIN res_partner partner on partner.user_id =us.id
                        left JOIN ir_attachment ir on ir.res_id = partner.id and res_model ='res.partner' and ir.name='image_256'
                            where us.login = %s LIMIT 1
                    """
            else:
                _logger.debug(
                "User not found. Log in by " + access_token,
                ShareVanChat._name, username,
                exc_info=True)
                return Response(json.dumps(response_data), content_type="application/json", status=500)

            http.request.env.cr.execute(query, (username,))
            records = http.request.env.cr.dictfetchall()
            if len(records) > 0:
                if records[0]['uri_path']:
                    response_data['result'] = {
                        'display_name': records[0]['display_name'],
                        'avatar': records[0]['uri_path'],
                        'phone': records[0]['phone']
                    }
                else:
                    response_data['result'] = {
                        'display_name': records[0]['display_name'],
                        'avatar': 'demo.nextsolutions.com.vn:8070/images/ad/adc83b19e793491b1c6ea0fd8b46cd9f32e592fc',
                        'phone': records[0]['phone']
                    }
                _logger.debug(
                    "Log in by " + access_token,
                    ShareVanChat._name, username,
                    exc_info=True)
                return Response(json.dumps(response_data), content_type="application/json", status=200)
            else:
                _logger.debug(
                    "User not found. Log in by " + access_token,
                    ShareVanChat._name, username,
                    exc_info=True)
                return Response(json.dumps(response_data), content_type="application/json", status=500)
        else:
            _logger.debug(
                "User not found when use/me. Log in by " + access_token,
                ShareVanChat._name, username,
                exc_info=True)
            return Response(json.dumps(response_data), content_type="application/json", status=500)
