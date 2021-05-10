# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request, Response
from odoo.tools import config


class CompanyAwardController(http.Controller):

    @http.route('/share_van_order/create_individual_customer', type='http', auth='none', csrf=False)
    def create_individual_customer(self, customer, files,secret_key):
        secret_key = secret_key[:-1]
        secret_key = secret_key[1:]
        if secret_key == config['client_secret']:
            request.session['db'] = config['database']
            files = request.httprequest.files.getlist('files')
            return http.request.env['res.users'].create_individual_customer(customer, files)
        else:
            return Response(response=str('Wrong Secret key'), status=500)

    @http.route('/company/get_career', type='json', auth='none', csrf=False)
    def get_career(self):
        request.session['db'] = config['database']
        return http.request.env['res.company'].get_career()

    @http.route('/company/get_country', type='json', auth='user')
    def get_country(self):
        return http.request.env['res.company'].get_country()

    @http.route('/share_van_order/update_avatar', type='http', auth='user', csrf=False)
    def update_avatar(self,files):
        files = request.httprequest.files.getlist('files')
        return http.request.env['res.users'].update_avatar(files)

