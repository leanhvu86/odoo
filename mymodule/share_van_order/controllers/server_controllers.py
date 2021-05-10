# -*- coding: utf-8 -*-
from mymodule.constants.Constants import RES_PARTNER
from mymodule.share_van_order.controllers.api.fleet_driver import FleetDriverApi
from mymodule.share_van_order.models.fleet_vehicle import FleetVehicle
from odoo import http
from odoo.http import request


class ServerController(http.Controller):

    @http.route('/server/change_password', type='json', auth='user')
    def change_password_mobile(self, old_password, new_password):
        http.request.env['res.users'].change_password(old_password, new_password)
        return True

    @http.route('/server/duration_log', type='json', auth='user')
    def duration_log(self, log):
        http.request.env['tc.positions'].create_multiple(log)
        return {
            'records': ['Successful']
        }

    @http.route('/routing/driver_location', type='json', auth='user', csrf=False)
    def location_vehicle(self, routing_plan_day_id):
        return FleetDriverApi.getDriverLocation(routing_plan_day_id)

    @http.route('/stock_man/location_vehicle', type='json', auth='user', csrf=False)
    def bidding_location_vehicle(self, bidding_vehicle_ids):
        return FleetDriverApi.bidding_location_vehicle(bidding_vehicle_ids)

    @http.route('/sos/create', type='http', csrf=False)
    def accept_sos_type(self, sos_type,order_number):
        files = request.httprequest.files.getlist('files')
        return http.request.env[FleetVehicle._name].accept_sos_type(sos_type,order_number, files)

    @http.route('/share_van_order/rating_customer', type='json', auth='user')
    def rating_customer(self, rating):
        print(rating)
        return http.request.env[RES_PARTNER].rating_customer(rating)

    @http.route('/share_van_order/get_rating_customer_info', type='json', auth='user')
    def get_rating_customer_info(self, routing_plan_day_id):
        return http.request.env[RES_PARTNER].get_rating_customer_info(routing_plan_day_id)