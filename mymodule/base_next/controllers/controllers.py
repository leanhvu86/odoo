# -*- coding: utf-8 -*-
import hashlib
import imghdr
import json
import mimetypes
import os

from flask import Flask, send_from_directory, jsonify

from addons.web.controllers.main import auth_api
from mymodule.base_next.controllers.api.file_controller import FileApi
from mymodule.base_next.models.depot_goods import DepotGoods
from mymodule.base_next.models.notification import NotificationUser
from mymodule.base_next.models.routing_plan_day import RoutingPlanDay
from mymodule.base_next.models.vendor import Vendor
from odoo import http
from odoo.addons.base.models.ir_attachment import IrAttachment
from odoo.exceptions import ValidationError, AccessDenied
from odoo.http import request, Response
from odoo.tools import config
from ..MVR.main import Routing
from mymodule.constants import Constants
class BaseNext(http.Controller):

    @http.route('/images/<path:fname>', auth='none')
    def send_file(self, fname):
        file_path = http.request.env[IrAttachment.model]._full_path(fname)
        if not os.path.exists(file_path):
            return http.Response("File does not exist!")
        extension = imghdr.what(file_path)
        if extension is None or extension.lower() not in ['png', 'jpg', 'jpeg']:
            return None
        app = Flask(__name__, static_folder=http.request.env[IrAttachment.model]._filestore())
        with app.app_context() and app.test_request_context():
            return send_from_directory(directory=app.static_folder, filename=fname,
                                       mimetype='image/' + extension)

    @http.route('/images', auth='user', csrf=False)
    def upload_image(self, model):
        files = request.httprequest.files.getlist('ufile')
        res = FileApi.upload_image_file(files, model)
        app = Flask(__name__)
        with app.app_context() and app.test_request_context():
            return jsonify(res)

    @http.route('/upload', auth='user', csrf=False)
    def upload_attachment(self, multipart):
        try:
            file = multipart.read()
            checksum = hashlib.sha1(file).hexdigest()
            fname, full_path = http.request.env[IrAttachment.model]._get_path('', checksum)
            with open(full_path, 'wb') as f:
                f.write(file)
            re = {
                "store_fname": fname
            }
            records = {
                "length": 1,
                "records": re
            }
            app = Flask(__name__, static_folder=http.request.env[IrAttachment.model]._filestore())
            with app.app_context() and app.test_request_context():
                return jsonify(records)
        except Exception as e:
            raise e

    @http.route('/download/<path:fname>', auth='user')
    def download_attachment(self, fname):
        domain = (('id', '<>', -1), ('store_fname', '=', fname))
        att = http.request.env[IrAttachment.model].search(args=domain, limit=1)
        if att:
            extension = mimetypes.guess_type(att.name)[0]
            app = Flask(__name__, static_folder=http.request.env[IrAttachment.model]._filestore())
            with app.app_context() and app.test_request_context():
                return send_from_directory(directory=app.static_folder, filename=fname,
                                           mimetype=extension or 'text/plain',
                                           as_attachment=True,
                                           attachment_filename=att.name
                                           )
        else:
            return http.Response("Not found")

    @http.route('/delete_attachment', auth='user')
    def delete_attachment(self, fname):
        return FileApi.delete_attachment(fname)

    @http.route('/notification', type='json', auth='user')
    def get_notification(self, **kwargs):
        return http.request.env[NotificationUser._name].get_notification_all(**kwargs)

    @http.route('/notification/is_read', type='json', auth='user')
    def update_notification(self, **kwargs):
        id_message = 0
        if 'id' in kwargs:
            id_message = int(kwargs.get('id'))
        records = http.request.env[NotificationUser._name]. \
            browse(id_message).write({'is_read': True})
        return records

    @http.route('/mobile/logout', type='http', auth="none", csrf=False)
    def logout(self,user_id):
        http.request.cr.execute('update res_users set fcm_token = null where id = %s', (int(user_id),))
        request.session.logout(keep_db=True)
        return Response(response='log out', status=200)

    @http.route('/sos/type', type='json', auth="user", csrf=False)
    def get_sos_type(self):
        return http.request.env[Vendor._name].get_sos_type()

    @http.route('/sos/number', type='json', auth="user", csrf=False)
    def get_sos_number(self):
        return http.request.env[Vendor._name].get_sos_number()

    # @http.route('/server/save_token', type='json', auth='user')
    # def save_token(self, fcm_token):
    #     record = http.request.env['res.users'].search([('fcm_token', '=', fcm_token)])
    #     record.write({'fcm_token': ''})
    #     user_token = http.request.env['res.users'].browse(http.request.env.uid).write({'fcm_token': fcm_token})
    #     return {
    #         'records': ['Successful']
    #     }

    @http.route('/routing_plan_day/accept_comming', type='json', auth="user", csrf=False)
    def driver_send_routing_comming_notification(self, routing_plan_day_id):
        return http.request.env[RoutingPlanDay._name].driver_send_routing_comming_notification(routing_plan_day_id)

    @http.route('/routing_plan_day/check_driver_waiting_time', type='json', auth="user", csrf=False)
    def check_driver_waiting_time(self, from_latitude, from_longitude, to_latitude, to_longitude):
        return FileApi.check_driver_waiting_time(from_latitude, from_longitude, to_latitude, to_longitude)

    @http.route('/send/notification_routing', type='json', auth='none')
    def send_notification(self, list_driver, secret_key):
        return http.request.env[NotificationUser._name].notification_routing(list_driver, secret_key)

    @http.route('/send/notification_driver', type='json', auth='none')
    def notification_drivers(self, vehicle):
        return http.request.env[NotificationUser._name].notification_drivers(vehicle)

    @http.route('/depot/import_export', type='json', auth='user', csrf=False)
    def import_into_depot(self, depot_vals):
        if 'routing_plan_day_id' not in depot_vals or 'depot_id' not in depot_vals:
            raise ValidationError("Not enough params")
        if 'type' in depot_vals and depot_vals['type'] == "0":
            return http.request.env[DepotGoods._name].import_goods(depot_vals)
        if 'type' in depot_vals and depot_vals['type'] == "1":
            return http.request.env[DepotGoods._name].export_goods(depot_vals)

    @http.route('/web/send_noti', type='json', auth='none')
    def send_notification_web(self, secret_key, user_ids, title, body):
        if secret_key == config['client_secret']:
            if not http.request.db:
                http.request.db = config['database']
            return http.request.env['res.users'].send_notis_web(user_ids, title, body)
        else:
            return Response(response=str('Wrong Secret key'), status=500)

    @http.route('/web/send_noti_routing', type='json', auth='none')
    def notify_change_routing(self, secret_key, vehicle_id, driver_id, new_driver_id):
        if secret_key == config['client_secret']:
            request.session['db'] = config['database']
            uid = request.session.post_sso_authenticate(config['database'], config['account_admin'])
            request.env['ir.http'].session_info()['uid'] = uid
            request.env['ir.http'].session_info()['login_success'] = True
            request.env['ir.http'].session_info()
            return http.request.env[RoutingPlanDay._name].notify_change_routing_plan(vehicle_id, driver_id, new_driver_id)
        else:
            return Response(response=str('Wrong Secret key'), status=500)

    @http.route('/web/send_noti_customer', type='json', auth='none')
    def notify_change_rt_customer(self, secret_key, order_code, vehicle_id, new_driver_id, company_id, type, title, body):
        if secret_key == config['client_secret']:
            request.session['db'] = config['database']
            data = auth_api.login_sso(config['account_admin'], 'abc@123')
            data_decoded = json.loads(data.decode("utf-8"))
            if 'error' in data_decoded or 'access_token' not in data_decoded:
                raise AccessDenied()
            request.session.access_token = data_decoded['access_token']
            uid = request.session.post_sso_authenticate(config['database'], config['account_admin'])
            request.env['ir.http'].session_info()['uid'] = uid
            request.env['ir.http'].session_info()['login_success'] = True
            request.env['ir.http'].session_info()
            return http.request.env[RoutingPlanDay._name].\
                notify_customer_change_routing(order_code, vehicle_id, new_driver_id, company_id, type, title, body)
        else:
            return Response(response=str('Wrong Secret key'), status=500)

    @http.route('/send/notification_license_expired', type='json', auth='none')
    def send_notification_license_expired(self, list_driver, secret_key):
        return http.request.env[NotificationUser._name].notification_outdate_license(list_driver, secret_key)

    @http.route('/web/reload_routing', type='http', auth='none')
    def reload_routing(self, secret_key, routing_vehicle_id):
        if secret_key == config['client_secret']:
            request.session['db'] = config['database']
            uid = request.session.post_sso_authenticate(config['database'], config['account_admin'])
            request.env['ir.http'].session_info()['uid'] = uid
            request.env['ir.http'].session_info()['login_success'] = True
            request.env['ir.http'].session_info()
            return http.request.env['sharevan.routing.vehicle'].reload_routing(routing_vehicle_id)
        else:
            return Response(response=str('Wrong Secret key'), status=500)
    @http.route('/mvr/routing_mstore', type='json', auth='none')
    def routing_mstore(self,date_plan):
        print('rule1')
        http.request.env[Constants.SHAREVAN_ROUTING_PLAN_DAY].routing_mstore(date_plan)

    @http.route('/mvr/routing_mstore_new', type='json', auth='none')
    def routing_mstore_new(self, date_plan):
        print('rule2')
        http.request.env[Constants.SHAREVAN_ROUTING_PLAN_DAY].routing_mstore_new(date_plan)
        #Routing.main(self)