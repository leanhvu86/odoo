# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json


class WebsiteOrderCustomer(http.Controller):

    @http.route('/order_details', type="json", auth="user", website=True)
    def order_details(self, id):
        print('longfzzz  ', id)
        print('xxxxx')
        # url = 'localhost:8070/bidding/get_vehicle_tonnage'
        # response = requests.get(url)
        # movies = response.json()
        result = request.env['fleet.vehicle'].search([])
        return result

    @http.route('/test', type='http', csrf=False, auth='public', website=True)
    def home_page(self, **kwargs):
        headers = ['Mã đơn hàng', 'Trạng thái', 'Điểm bốc', 'Điểm dỡ', 'Xử lý']
        return http.request.render('website_order_customer.test_page_template', {
            'list_variable': [1, 2],
            'headers': headers
        })

    @http.route('/order_customer', auth="user", website=True)
    def order_customer(self, **kwargs):
        print('xxxxx')
        # url = 'localhost:8070/bidding/get_vehicle_tonnage'
        # response = requests.get(url)
        # movies = response.json()
        return http.request.render('website_order_customer.order_customer_page', {
        })

#     @http.route('/website_order_customer/website_order_customer/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('website_order_customer.listing', {
#             'root': '/website_order_customer/website_order_customer',
#             'objects': http.request.env['website_order_customer.website_order_customer'].search([]),
#         })

#     @http.route('/website_order_customer/website_order_customer/objects/<model("website_order_customer.website_order_customer"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('website_order_customer.object', {
#             'object': obj
#         })
