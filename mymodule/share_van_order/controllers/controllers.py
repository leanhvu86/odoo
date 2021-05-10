# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import json
from .api.bill_lading import BillLadingApi
from ..models.res_partner import ResPartner
from ..models.routing_plan_day import RoutingPlanDay
from ..models.sharevan_area import ShareVanArea


class ShareVanModule(http.Controller):
    @http.route('/share_van_order/share_van_order/', auth='public')
    def index(self):
        return 'hello world'

    @http.route('/share_van_order/get_area_list', type='http', auth="public", csrf=False)
    def get_area_list_web(self, country_id):
        return http.request.env[ShareVanArea._name].getAllArea(country_id)

    @http.route('/share_van_order/create_order/', type='json', auth='public')
    def create_order(self, billLading):
        if 'subscribe' in billLading:
            billLading['subscribe_id'] = billLading['subscribe']['id']
        res = BillLadingApi.create_bill_lading(billLading)
        return res['id']

    @http.route('/share_van_order/update_order', type='json', auth='public')
    def update_order(self, billLading, routing):
        return BillLadingApi.update_routing_now(self, billLading)

    @http.route('/share_van_order/routing_plan_day_by_employeeid', type='json', auth="user")
    def get_routing_plan_day_by_employee(self, **kwargs):
        return http.request.env[RoutingPlanDay._name].get_routing_plan_day_by_employeeid(**kwargs)

    # lấy danh sách date plan
    # required: from_date
    # to_date options chưa dùng
    @http.route('/share_van_order/routing_plan/list_date', type='json', auth='public')
    def get_list_date(self, from_date, to_date, type):
        return http.request.env[RoutingPlanDay.MODEL].get_list_date_routing_plan(from_date, to_date, type)

    # lấy danh sách routing plan day theo điều kiện truyền vào
    # required: status : [] , driver_id
    # check: date or ( from_date && to_date && offset && limit )
    @http.route('/share_van_order/routing_plan_day', type='json', auth="user")
    def get_routing_plan(self, **kwargs):
        # xong phan trang
        return http.request.env[RoutingPlanDay._name].get_driver_routing_plan(**kwargs)

    @http.route('/share_van_order/bill_lading_history', method=['GET'], type='json', auth="user")
    def get_bill_lading_history(self, **kwargs):
        return http.request.env['sharevan.bill.lading'].get_bill_lading_history(**kwargs)

    # lấy danh sách bill_lading theo điều kiện truyền vào
    # tuy bien theo dieu kien
    # check: (  offset && limit )
    @http.route('/share_van_order/bill_lading_history_ad', type='json', auth="user")
    def get_bill_lading_history_ad(self, **kwargs):
        return http.request.env['sharevan.bill.lading'].get_bill_lading_history_ad(**kwargs)

    # lấy chi tiet routing plan day
    # required: routing_plan_day_code
    @http.route('/share_van_order/routing_plan_day/detail', type='json', auth="user")
    def get_routing_detail(self, **kwargs):
        routing_plan_day_code = None
        for arg in kwargs:
            if arg == 'routing_plan_day_code':
                routing_plan_day_code = kwargs.get(arg)
        return http.request.env[RoutingPlanDay._name].get_routing_detail(routing_plan_day_code)

    @http.route('/share_van_order/accept_package', auth='user', csrf=False)
    def accept_package(self, routingPlan):
        files = request.httprequest.files.getlist('ufile')
        return http.request.env[RoutingPlanDay._name].accept_package(routingPlan, files)

    @http.route('/share_van_order/get_customer_information', type='json', auth="public")
    def get_customer_information(self):
        return http.request.env['res.partner'].get_customer_information_detail()

    @http.route('/share_van_order/get_customer_information_web', type='json', auth="public")
    def get_customer_information_web(self):
        return http.request.env['res.partner'].get_customer_information_detail_web()

    @http.route('/share_van_order/edit_customer_information_web', type='json', auth="public")
    def edit_customer_information_web(self, customerInfo):
        return http.request.env[ResPartner._name].edit_customer_information_detail_web(customerInfo)

    @http.route('/share_van_order/edit_customer_information', type='json', auth="user")
    def edit_customer_information(self, customerInfo):
        return http.request.env[ResPartner._name].edit_customer_information_detail(customerInfo)

    @http.route('/share_van_order/driver_rating', type='json', auth='user')
    def driver_rating_star(self, rating):
        return http.request.env[ResPartner._name].driver_rating_start(rating)

    @http.route('/share_van_order/get_list_rating_badges', type='json', auth='user')
    def get_list_rating_badges(self, type):
        return http.request.env[ResPartner._name].get_list_rating_badges(type)

    # @http.route('/share_van_order/get_detail_routing_plan_customer', type='json', auth='user')
    # def get_detail_routing_plan_warehouse(self, routing_plan_day_detail_id):
    #     return http.request.env[RoutingPlanDayDetail._name].get_detail_routing_plan_warehouse(
    #         routing_plan_day_detail_id)

    @http.route('/share_van_order/get_list_confirm_routing', type='json', auth='user')
    def get_list_confirm_routing(self, **kwargs):
        return http.request.env[RoutingPlanDay._name].get_list_confirm_routing(**kwargs)

    @http.route('/share_van_order/get_bill_lading_details', type='json', auth='public', csrf=False)
    def get_bill_lading_details(self, bill_ladding_id):
        return http.request.env[RoutingPlanDay._name].get_bill_lading_details(bill_ladding_id)

    @http.route('/share_van_order/get_model_name', type='json', auth='user')
    def get_model_name(self, model):
        return http.request.env[RoutingPlanDay._name].get_model_name(model)

    @http.route('/share_van_order/get_model_name_warehouse', type='json', auth='user')
    def get_model_name_warehouse(self, model, id):
        return http.request.env[RoutingPlanDay._name].get_model_name_warehouse(model, id)

    @http.route('/share_van_order/get_service_type', type='json', auth='public', csrf=False)
    def get_service_type(self):
        return http.request.env[RoutingPlanDay._name].get_service_type()

    @http.route('/share_van_order/update_routing_plan_day', type='json', auth='user')
    def update_routing_plan_day(self, routing_plan_day):
        return http.request.env[RoutingPlanDay._name].update_routing_plan_day(routing_plan_day)

    @http.route('/share_van_order/update_routing_plan_day_with_image', csrf=False, type='http', auth='user')
    def update_routing_plan_day_with_image(self, routingPlan):
        files = request.httprequest.files.getlist('files')
        return http.request.env[RoutingPlanDay._name].update_routing_plan_day_with_image(routingPlan, files)

    @http.route('/share_van_order/get_bill_lading_update', type='json', auth='user')
    def get_bill_lading_update(self, bill_lading_detail_id):
        return http.request.env[BillLadingApi.MODEL].get_bill_lading_update(bill_lading_detail_id)

    @http.route('/share_van_order/cancel_update_rpd', type='json', auth='user')
    def cancel_update_rpd(self, bill_lading_detail_id):
        return http.request.env[RoutingPlanDay.MODEL].cancel_update_rpd(bill_lading_detail_id)

    # @http.route('/share_van_order/import_export_detail', type='json', auth="user")
    # def get_import_export_detail(self, **kwargs):
    #     routing_plan_detail_code = None
    #     type_value = None
    #     for arg in kwargs:
    #         if arg == 'routing_plan_detail_code':
    #             routing_plan_detail_code = kwargs.get(arg)
    #         if arg == 'type_value':
    #             type_value = kwargs.get(arg)
    #     return http.request.env[RoutingPlanDayDetail._name].get_import_export_detail(routing_plan_detail_code,
    #                                                                                  type_value)

    @http.route('/share_van_order/history_routing_bill', type='json', auth='user')
    def get_history_routing(self, from_date, to_date):
        return http.request.env[RoutingPlanDay._name].get_history_routing_bill(from_date, to_date)

    @http.route('/share_van_order/routing_plan_day_details', type='json', auth='user')
    def routing_plan_day_details(self, uID, routing_plan_day_id, from_date, to_date, status):
        return http.request.env[RoutingPlanDay._name].get_list_routing_day_detail_by_routing_plan_day_id(uID,
                                                                                                         routing_plan_day_id,
                                                                                                         from_date,
                                                                                                         to_date,
                                                                                                         status)

    @http.route('/share_van_order/update_rpd', type='json', auth='public')
    def update_rpd(self, bill_lading_detail):
        return http.request.env[RoutingPlanDay._name].update_rpd(bill_lading_detail)

    @http.route('/share_van_order/cancel_update_rpd', type='json', auth='public')
    def cancel_update_rpd(self, bill_lading_detail):
        return http.request.env[RoutingPlanDay._name].cancel_update_rpd(bill_lading_detail)

    @http.route('/share_van_order/cancel_routing_once_day', csrf=False, type='http', auth="user")
    def cancel_routing_once_day(self, bill_lading_detail, description):
        files = request.httprequest.files.getlist('files')
        return http.request.env[RoutingPlanDay._name].cancel_routing_once_day(bill_lading_detail, description, files)

    @http.route('/sharevan/cancel_routing_plan_day', type='json', csrf=False, auth="user")
    def cancel_routing_plan_day(self, idRoutingPlanDay):
        return http.request.env['sharevan.bill.lading'].cancel_routing_plan_day(idRoutingPlanDay)

    @http.route('/sharevan/get_countries_flat_tree_node', type='json', auth='none')
    def get_countries_flat_tree_node(self, location_type):
        # request.session['db'] = config['database']
        # query_area = """
        #             Select id , name, code,parent_id
        #             from sharevan_area
        #                 where  and status = 'running'
        #                                """
        # self.env.cr.execute(query_area, ())
        # result_area = self._cr.dictfetchall()
        # result_area: {
        #     'value': 'R1',
        #     'displayValue': 'R1 - Yangon',
        #     'children': [
        #         {
        #             'value': 'R1',
        #             'displayValue': 'R1 - Yangon',
        #             'children': []
        #         }
        #     ]
        # }

        # return {
        #     'records': result_area
        # }
        links = (
            ("Tom", "Dick"), ("Dick", "Harry"), ("Tom", "Larry"), ("Tom", "Hurbert"), ("Tom", "Neil"), ("Bob", "Leroy"),
            ("Bob", "Earl"), ("Tom", "Reginald"))

        name_to_node = {}
        root = {'name': 'Root', 'children': []}
        for parent, child in links:
            parent_node = name_to_node.get(parent)
            if not parent_node:
                name_to_node[parent] = parent_node = {'name': parent}
                root['children'].append(parent_node)
            name_to_node[child] = child_node = {'name': child}
            parent_node.setdefault('children', []).append(child_node)
        return json.dumps(root, indent=4)
