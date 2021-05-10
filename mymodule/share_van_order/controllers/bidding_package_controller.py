# -*- coding: utf-8 -*-
from mymodule.constants import Constants
from odoo import http
from odoo.http import request
from odoo.tools import config


class BiddingPackageController(http.Controller):

    @http.route('/bidding/bidding_package_time', type='json', auth="user")
    def get_bidding_package_time(self):
        return http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].get_bidding_package_time()

    @http.route('/market_place/request_driver_order', type='json', auth='none')
    def request_driver_order(self, driver_id, bidding_package_id):
        return http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].request_driver_order(driver_id, bidding_package_id)

    @http.route('/market_place/accept_driver_order', type='json', auth='user')
    def accept_driver_order(self, driver_id, bidding_package_id):
        return http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].accept_driver_order(driver_id, bidding_package_id)

    @http.route('/market_place/assign_routing_driver', type='json', auth='user')
    def assign_routing_driver(self, routingDriver):
        return http.request.env['sharevan.driver.assign.routing'].assign_routing_driver(routingDriver)

    @http.route('/market_place/get_area', type='json', auth='none')
    def get_area(self, location_type,parent_id):
        request.session['db'] = config['database']
        return http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].get_area(location_type,parent_id)

    @http.route('/market_place/get_area', type='json', auth='none')
    def get_area(self, location_type, parent_id):
        request.session['db'] = config['database']
        return http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].get_area(location_type, parent_id)

    @http.route('/market_place/get_driver_assign', type='json', auth='user')
    def get_driver_assign(self):
        return http.request.env['sharevan.driver.assign.routing'].get_driver_assign()
