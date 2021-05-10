# -*- coding: utf-8 -*-

from mymodule.constants.Constants import RES_PARTNER
from odoo import http
from odoo.http import request, Response
from odoo.tools import config


class ShareVanEmployeeWarehouseController(http.Controller):

    @http.route('/customer/create_update_warehouse', csrf=False, type='http', auth='public')
    def create_update_warehouse(self, warehouse):
        return http.request.env['res.users'].create_update_warehouse(warehouse)

    @http.route('/customer/get_allow_area', type='json', auth='user')
    def get_allow_area(self, parent_id):
        return http.request.env['res.users'].get_allow_area(parent_id)

    @http.route('/customer/send_dlp_message', type='json', auth='none', csrf=False)
    def send_dlp_message(self, message, secret_key):
        if secret_key == config['client_secret']:
            request.session['db'] = config['database']
            uid = request.session.post_sso_authenticate(config['database'], config['account_admin'])
            request.env['ir.http'].session_info()['uid'] = uid
            request.env['ir.http'].session_info()['login_success'] = True
            request.env['ir.http'].session_info()
            return http.request.env['res.users'].send_dlp_message(message)
        else:
            return Response(response=str('Wrong Secret key'), status=500)
