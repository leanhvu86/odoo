# -*- coding: utf-8 -*-
from mymodule.constants import Constants
from odoo import http


class StockManController(http.Controller):

    @http.route('/stock_man/get_bill_lading_detail_by_cargo_id', type='json')
    def get_bill_lading_detail_by_cargo_id(self,cargo_id):
        return http.request.env[Constants.SHAREVAN_BILL_LADING_DETAIL].get_bill_lading_detail_by_cargo_id(cargo_id)

    @http.route('/stock_man/confirm_quantity_package_bill_package', type='json')
    def confirm_quantity_package_bill_package(self, cargo_id,list_bill_package_id):
        return http.request.env[Constants.SHAREVAN_BILL_LADING_DETAIL].confirm_quantity_package_bill_package(cargo_id,list_bill_package_id)

    @http.route('/stock_man/get_list_order_depot', type='json')
    def get_list_order_depot(self):
        return http.request.env[Constants.SHAREVAN_BIDDING_ORDER].get_list_order_depot()

    @http.route('/stock_man/confirm_bidding_order_success', type='json')
    def confirm_bidding_order_success(self, bidding_order_id,bidding_vehicle_id):
        return http.request.env[Constants.SHAREVAN_BIDDING_ORDER].confirm_bidding_order_success(bidding_order_id,bidding_vehicle_id)







