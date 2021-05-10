from mymodule.fleet.models.fleet_driver import FleetDriver
from mymodule.fleet.models.request_time_off import GroupRequestTO
from odoo import http
from odoo.http import request, Response
from odoo.tools import config


class DriverController(http.Controller):
    @http.route('/fleet/driver', type='json', auth='user')
    def getDriver(self):
        uid = http.request.session['uid']
        return http.request.env[FleetDriver._name].get_fleet_driver(uid)

    @http.route('/fleet_vehicle/get_driver_rating', type='json', auth='user')
    def getDriverRating(self, driver_id):
        return http.request.env[FleetDriver._name].get_profile(driver_id)

    @http.route('/fleet_vehicle/info_vehicle', type='json', auth='user')
    def getInforVehicle(self, assignation_log_id):
        return http.request.env[FleetDriver._name].getInforVehicle(assignation_log_id)

    @http.route('/fleet/edit_info_driver', type='json', auth='user')
    def editInfoDriver(self, driverInfo):
        return http.request.env[FleetDriver._name].editInfoDriver(driverInfo)

    @http.route('/fleet/receive_return_vehicle', auth='user', csrf=False)
    def receive_return_vehicle(self, driverInfo):
        files = request.httprequest.files.getlist('ufile')
        return http.request.env[FleetDriver._name].receive_return_vehicle(driverInfo, files)

    @http.route('/fleet/history_vehicle', type='json', auth='user', csrf=False)
    def history_vehicle(self, date):
        return http.request.env[FleetDriver._name].history_vehicle(date)

    @http.route('/driver/get_driver', type='json', auth='user')
    def search_driver(self, **kwargs):
            return http.request.env[FleetDriver._name].search_driver(**kwargs)

    @http.route('/driver/request_time_off', type='json', auth='user')
    def request_time_off(self, driver_id, request_days, reason):
        request_params = {
            "driver_id": driver_id,
            "request_days": request_days,
            "reason": reason
        }
        return http.request.env[GroupRequestTO._name].create(request_params)

    @http.route('/driver/cancel_request_time_off', type='json', auth='user')
    def cancel_request_time_off(self, group_request_id):
        return http.request.env[GroupRequestTO._name].cancel_request(group_request_id)

    @http.route('/driver/list_request_time_off', type='json', auth='user')
    def list_request_time_off(self, year, month):
        return http.request.env[GroupRequestTO._name].get_list_request(year, month)

    @http.route('/driver/update_vehicle_sos_status', type='json', auth='user')
    def update_vehicle_sos_status(self,vehicle_id):
        return http.request.env['fleet.vehicle'].update_vehicle_sos_status(vehicle_id)

    @http.route('/driver/send_noti', type='json', auth='none')
    def send_noti_driver(self, secret_key, driver_ids, title, body):
        if secret_key == config['client_secret']:
            if not http.request.db:
                http.request.db = config['database']
            return http.request.env['fleet.driver'].send_notification_drivers(driver_ids, title, body)
        else:
            return Response(response=str('Wrong Secret key'), status=500)
