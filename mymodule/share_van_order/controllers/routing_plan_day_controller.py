# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class RoutingPlanDayController(http.Controller):
    @http.route('/share_van_order/get_bill_routing_by_day', type='json', auth='user')
    def get_bill_routing_by_day(self, **kwargs):
        return http.request.env['sharevan.bill.routing'].get_bill_routing_by_day(**kwargs)

    @http.route('/share_van_order/get_bill_routing_detail_by_name', type='http', auth="public", csrf=False)
    def get_bill_routing_detail_by_code(self,pageNumber, pageSize):
        return http.request.env['sharevan.bill.routing'].get_bill_routing_detail_by_code(pageNumber, pageSize)

    @http.route('/share_van_order/get_bill_routing_detail', type='json', auth='public')
    def get_bill_routing_detail(self, bill_routing_id):
        return http.request.env['sharevan.bill.routing'].get_bill_routing_detail(bill_routing_id)

    @http.route('/share_van_order/get_total_resutl_routing_plan', type='json', auth='user')
    def get_total_resutl_routing_plan(self, **kwargs):
        return http.request.env['sharevan.bill.routing'].get_total_resutl_routing_plan(**kwargs)

    @http.route('/share_van_order/customer_not_found', csrf=False, type='http', auth='user')
    def customer_not_found(self, routing_plan_day_id, type, time_pay_back, files):
        files = request.httprequest.files.getlist('files')
        return http.request.env['sharevan.bill.routing'].customer_not_found(routing_plan_day_id, type, time_pay_back,
                                                                            files)

    @http.route('/sharevan_bill_lading/create_dlp_from_so', methods=['POST'], type='json', csrf=False, auth="none")
    def create_dlp_from_so(self, soInfor, company_name, access_token):
        return http.request.env['sharevan.bill.lading'].create_dlp_from_so(soInfor, company_name, access_token)

    @http.route('/sharevan/list_routing_plan_day_pending', type='json', csrf=False, auth="none")
    def list_routing_plan_day_pending(self, datePlan, access_token):
        return http.request.env['sharevan.bill.lading'].list_routing_plan_day_pending(datePlan, access_token)

    @http.route('/sharevan/routing_plan_day_confirm_or_cancel_from_so', methods=['PATCH'], type='json', csrf=False,
                auth="none")
    def routing_plan_day_confirm_or_cancel_from_so(self, **kwargs):
        return http.request.env['sharevan.bill.lading'].routing_plan_day_confirm_or_cancel_from_so(**kwargs)

    @http.route('/so_request/cancel_routing_SO', type='http', csrf=False, auth="none")
    def cancel_routing_SO(self, soInfor, access_token):
        return http.request.env['sharevan.bill.routing'].cancel_routing_SO(soInfor, access_token)
