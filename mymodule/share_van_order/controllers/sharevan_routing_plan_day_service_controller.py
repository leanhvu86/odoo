# -*- coding: utf-8 -*-
from mymodule.share_van_order.models.routing_plan_day import RoutingPlanDay
from odoo import http


class SharevanRoutingPlanDayServiceController(http.Controller):

    @http.route('/routing_plan_day/sos', type='json', auth='user')
    def get_sos_lst(self, routing_plan_day_id):
        return http.request.env[RoutingPlanDay._name].get_sos_lst(routing_plan_day_id)

    @http.route('/routing/accept_warehouse_place', type='json', auth='user')
    def accept_warehouse_place(self, routing_plan_day_id):
        return http.request.env[RoutingPlanDay._name].accept_warehouse_place(routing_plan_day_id)

    @http.route('/routing_plan_day/update_rating_customer_check', type='json', auth='user')
    def update_rating_customer_check(self, routing_plan_day_id):
        return http.request.env[RoutingPlanDay._name].update_rating_customer_check(routing_plan_day_id)

    @http.route('/routing_plan_day/gen_qr_code', type='json', auth='user')
    def gen_qr_code(self, routing_plan_day_id):
        # not allow qr code gen now
        return None
        # return http.request.env[RoutingPlanDay._name].gen_qr_code(routing_plan_day_id)

    @http.route('/routing_plan_day/get_driver_routing_plan_by_vehicle', type='json', auth='user')
    def get_driver_routing_plan_by_vehicle(self, vehicle_id, date_plan, type):
        return http.request.env[RoutingPlanDay._name].get_driver_routing_plan_by_vehicle(vehicle_id, date_plan, type)

    @http.route('/routing_plan_day/get_driver_routing_distinct_vehicle', type='json', auth='user')
    def get_driver_routing_distinct_vehicle(self, lst_vehicle_ids, date_plan):
        return http.request.env[RoutingPlanDay._name].get_vehicle_routing_distinct_vehicle(lst_vehicle_ids, date_plan)
