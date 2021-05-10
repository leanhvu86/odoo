# -*- coding: utf-8 -*-
from mymodule.share_van_order.models.sharevan_recurrent import OrderPackage
from odoo import http


class BillLadingDetailController(http.Controller):
    @http.route('/share_van_order/get_bill_order_package', type='json', auth='none')
    def get_bill_order_package(self):
        return http.request.env[OrderPackage._name].get_bill_order_package()
