# -*- coding: utf-8 -*-
import json

from mymodule.base_next.controllers.api.base_method import BaseMethod
from mymodule.base_next.controllers.api.firebase_messaging import FirebaseMessagingAPI
from mymodule.base_next.models.notification import NotificationUser
from mymodule.constants.Constants import RES_PARTNER
from mymodule.enum.ClickActionType import ClickActionType
from mymodule.enum.MessageType import MessageType
from mymodule.enum.NotificationType import NotificationType
from mymodule.enum.ObjectStatus import ObjectStatus
from mymodule.share_van_order.controllers.api.warehouse import WarehouseApi
from odoo import http
from odoo.http import request, Response


class ResPartnerController(http.Controller):

    @http.route('/bidding/update_account_long_haul', methods=['POST'], csrf=False, type='http', auth="user")
    def update_account_long_haul(self, longHaulInfo):
        files = request.httprequest.files.getlist('files')
        return http.request.env[RES_PARTNER].update_account_long_haul(longHaulInfo, files)

    @http.route('/server/save_token', type='json', auth='public')
    def save_token(self, fcm_token):
        session, data_json = BaseMethod.check_authorized()
        uid = http.request.env.uid
        if not session and not uid:
            return Response(json.dumps('UN_AUTHORIZED'), content_type="application/json", status=403)
        if not uid:
            uid = session.uid
        record = http.request.env['res.users'].search([('fcm_token', '=', fcm_token)])

        record_old = http.request.env['res.users'].search([('id', '=', uid)])
        if record_old and record_old['fcm_token'] and fcm_token != record_old['fcm_token'] and record['id'] != \
                record_old['id']:
            title = ''
            body = ''
            type = NotificationType.RoutingMessage.value
            message_type = MessageType.warning.value
            object_status = ObjectStatus.LogOutByAccount.value
            click_action = ClickActionType.notification_driver.value
            val = {
                "title": title,
                "name": 'res.users',
                "content": body,
                "type": type,
                "object_status": object_status,
                "click_action": click_action,
                "message_type": message_type,
                "item_id": '',
                "is_read": False
            }
            val = json.dumps(val)
            item_id = ''
            FirebaseMessagingAPI.send_message_for_all_with_fcm_token(tokens=[record_old['fcm_token']], title=title,
                                                                     body=str(val), short_body=body,
                                                                     item_id=item_id,
                                                                     click_action=click_action,
                                                                     message_type=message_type)
        record.write({'fcm_token': ''})
        # query = """ update res_users set fcm_token = '%s' where id= '%s' """ % (fcm_token,uid,)
        # http.request.env.cr.execute(query, ())
        # result = http.request._cr.fetchall()
        if record_old != record:
            record_old.write({'fcm_token': fcm_token})
        return {
            'records': ['Successful']
        }

    # lấy danh sách bill_lading theo điều kiện truyền vào new
    # tuy bien theo dieu kien
    @http.route('/share_van_order/bill_lading_history_web', type='http', auth="public", csrf=False)
    def bill_lading_history_web(self, pageNumber, pageSize):
        return http.request.env['sharevan.bill.lading'].bill_lading_history_web(pageNumber, pageSize)

    @http.route('/share_van_order/get_notification_web', type='http', auth="public", csrf=False)
    def get_notification_web(self):
        return http.request.env[NotificationUser._name].get_notification_web()

    @http.route('/share_van_order/get_warehouse_list_web', type='http', auth="public", csrf=False)
    def get_warehouse_list_web(self, pageNumber, pageSize):
        return WarehouseApi.get_warehouse_list_web(self, pageNumber, pageSize)

    @http.route('/share_van_order/upload_image_user', auth="public", csrf=False)
    def upload_image_user(self):
        files = request.httprequest.files.get('file')
        return http.request.env[RES_PARTNER].update_image_user_web(files)

    @http.route('/share_van_order/bill_list_date', type='http', auth='public', csrf=False)
    def bill_list_date(self, from_date, to_date):
        return WarehouseApi.bill_list_date(self, from_date, to_date)

    @http.route('/share_van_order/get_area_distance', type='json', auth='public', csrf=False)
    def get_area_distance(self, from_warehouse, to_warehouse):
        return WarehouseApi.get_area_distance(from_warehouse, to_warehouse)

    @http.route('/share_van_order/get_warehouse_table', type='http', auth='public', csrf=False)
    def get_warehouse_table(self, warehouse_name_search, warehouse_code_search, address_search):
        return WarehouseApi.get_warehouse_table(warehouse_name_search, warehouse_code_search, address_search)
