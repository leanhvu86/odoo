# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class BiddingDriverController(http.Controller):
    @http.route('/market/get_driver_wallet', type='json', auth="user")
    def get_driver_wallet(self, **kwargs):
        return http.request.env['sharevan.driver.received'].get_driver_wallet(**kwargs)

    @http.route('/market/get_driver_compute', type='json', auth="user")
    def get_driver_compute(self, **kwargs):
        return http.request.env['sharevan.driver.received'].get_driver_compute()

    @http.route('/market/get_driver_last_money', type='json', auth="user")
    def get_driver_last_money(self, **kwargs):
        return http.request.env['sharevan.driver.received'].get_driver_last_money()

    @http.route('/code_share/create_driver_code_share', type='http', csrf=False, auth="user")
    def create_driver_code_share(self, driver, files):
        files = request.httprequest.files.getlist('files')
        return http.request.env['fleet.driver'].create_driver_code_share(driver, files)

    @http.route('/code_share/update_deactive_driver', type='http', csrf=False, auth="user")
    def update_deactive_driver(self, driver):
        files = request.httprequest.files.getlist('files')
        return http.request.env['fleet.driver'].update_deactive_driver(driver, files)

    @http.route('/code_share/get_driver_license', type='json', auth="user")
    def get_driver_license(self, country_id):
        return http.request.env['fleet.driver'].get_driver_license(country_id)

    @http.route('/code_share/create_vehicle_code_share', type='http', csrf=False, auth="user")
    def create_vehicle_code_share(self, vehicle, files):
        files = request.httprequest.files.getlist('files')
        return http.request.env['fleet.vehicle'].create_vehicle_code_share(vehicle, files)

    @http.route('/code_share/get_vehicle_model', type='json', auth="user")
    def get_vehicle_model(self):
        return http.request.env['fleet.vehicle'].get_vehicle_model()

    @http.route('/code_share/scanning_distance_compute', type='json', auth="user")
    def scanning_distance_compute(self, type, zone_id):
        return http.request.env['sharevan.distance.compute'].scanning_distance_compute(type, zone_id)
