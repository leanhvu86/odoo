# -*- coding: utf-8 -*-
from datetime import datetime

from mymodule.enum.StatusType import StatusType
from mymodule.share_van_order.models.sharevan_insurance import SharevanServiceType
from odoo import http
from odoo.http import Response, request
from odoo.tools import config
from .api.bill_lading_detail import BillLadingDetailApi
from .api.warehouse import WarehouseApi
from ..models.models import ShareVanInsurance
from ..models.sharevan_bill_lading import BillLading, ProductType
from ..models.subcribe import Subscribe
from ...base_next.controllers.api.base_method import BaseMethod


class BillController(http.Controller):
    @http.route('/share_van_order/bill/list_date', type='json', auth='public')
    def get_list_date(self, from_date, to_date):
        from_date = datetime.fromtimestamp(int(from_date) / 1000.0)
        to_date = datetime.fromtimestamp(int(to_date) / 1000.0)
        return http.request.env[BillLadingDetailApi.MODEL].get_list_date(from_date, to_date)

    @http.route('/share_van_order/bill/list_by_date', type='json', auth='public')
    def get_list_by_date(self, date, status_order):
        from_date = datetime.fromtimestamp(int(date) / 1000.0)
        if status_order:
            pass
        else:
            status_order = StatusType.Running
        return http.request.env[BillLading._name].get_list_by_date(from_date, status_order)

    @http.route('/share_van_order/insurance/list_active', type='json', auth='public', csrf=False)
    def get_list_active(self, status):
        records = http.request.env[ShareVanInsurance._name]. \
            web_search_read([['status', '=', status], ['insurance_type', '=', '0']], fields=None, offset=0, limit=80,
                            order='')
        return records

    @http.route('/share_van_order/service/list_active', type='json', auth='public', csrf=False)
    def get_list_service(self, status):
        records = http.request.env[SharevanServiceType._name]. \
            web_search_read([['status', '=', status]], fields=None, offset=0, limit=80, order='')
        return records

    @http.route('/share_van_order/product_type/list_active', type='json', auth='public', csrf=False)
    def get_list_product_type(self, status):
        records = http.request.env[ProductType._name]. \
            web_search_read([['status', '=', status], ['type', '=', '0'], ['active_shipping', '=', True]], fields=None,
                            offset=0, limit=80, order='')
        return records

    @http.route('/share_van_order/subscribe/list', type='json', auth='public', csrf=False)
    def get_list_subscribe(self, status):
        records = http.request.env[Subscribe._name]. \
            web_search_read([['status', '=', status]], fields=None, offset=0, limit=80, order='')
        return records

    @http.route('/share_van_order/check_warehouse_info', type='json', auth='public')
    def check_warehouse_info(self, warehouse):
        res = WarehouseApi.getZoneFromAddress(warehouse)
        res = http.request.env[WarehouseApi.AREA_MODEL].getZoneByProvince(res[0], res[1], res[2])
        return res

    @http.route('/share_van_order/get_warehouse', type='json', auth='public', csrf=False)
    def get_warehouse_list(self, companyId):
        records = WarehouseApi.getWarehouseList(companyId)
        return records

    @http.route('/share_van_order/get_warehouse_by_id', type='json', auth='user')
    def get_warehouse_by_id(self, warehouseId):
        records = WarehouseApi.getWarehouseById(warehouseId)
        return records

    @http.route('/share_van_order/get_depot', type='json', auth='user')
    def get_depot_list(self):
        records = WarehouseApi.getDepotList()
        return records

    @http.route('/share_van_order/create_bill_routings', type='json', auth='none', csrf=False)
    def create_bill_routings(self, bill_lading_ids, secret_key):
        if secret_key == config['client_secret']:
            request.session['db'] = config['database']
            uid = request.session.post_sso_authenticate(config['database'], config['account_admin'])
            request.env['ir.http'].session_info()['uid'] = uid
            request.env['ir.http'].session_info()['login_success'] = True
            request.env['ir.http'].session_info()
            return http.request.env['sharevan.bill.routing'].create_bill_routings(bill_lading_ids)
        else:
            return Response(response=str('Wrong Secret key'), status=500)
