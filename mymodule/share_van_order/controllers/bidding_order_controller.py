# -*- coding: utf-8 -*-

from odoo import http
from mymodule.base_next.models.bidding_vehicle import BiddingVehicle
from mymodule.constants import Constants
from mymodule.constants.Constants import RES_PARTNER
from mymodule.share_van_order.controllers.api.bidding_order_api import BiddingOrderApi
from odoo import http
from odoo.http import request


class BiddindOrderController(http.Controller):
    @http.route('/bidding/get_bidding_information', type='json')
    def get_bidding_information(self, uID, status_cargo, type, order_by, offset, limit):
        return http.request.env['sharevan.cargo'].get_bidding_information(uID, status_cargo, type, order_by, offset,
                                                                          limit)

    @http.route('/bidding/confirm_bidding_vehicle', type='json')
    def confirm_bidding_vehicle_01(self, bidding_order_id, bidding_vehicle_id):
        return http.request.env[BiddingVehicle._name].confirm_bidding_vehicle(bidding_order_id, bidding_vehicle_id)

    @http.route('/bidding/edit_bidding_information', type='json')
    def edit_bidding_information(self, bidding_vehicle_id, bidding_id):
        return http.request.env['sharevan.cargo'].edit_bidding_information(bidding_vehicle_id, bidding_id)

    @http.route('/bidding/get_list_bidding_vehicle', type='json')
    def get_list_bidding_vehicle(self, uID):
        return http.request.env[BiddingVehicle._name].get_list_bidding_vehicle(uID)

    @http.route('/bidding/get_support_phone_number', type='json')
    def get_support_phone_number(self):
        return http.request.env[BiddingVehicle._name].get_support_phone_number()

    @http.route('/bidding/get_company_information', type='json')
    def get_company_information(self):
        return http.request.env[BiddingVehicle._name].get_company_information()

    @http.route('/bidding/get_history_bidding', type='json', auth="user")
    def get_history_bidding(self, **kwargs):
        return BiddingOrderApi.get_history_bidding(**kwargs)

    @http.route('/bidding/get_history_bidding_price', type='json', auth="user")
    def get_history_bidding_price(self, **kwargs):
        return BiddingOrderApi.get_history_bidding_price(**kwargs)

    @http.route('/bidding/get_bidding_detail', type='json', auth="user")
    def get_bidding_detail(self, **kwargs):
        return http.request.env['sharevan.bidding.order'].get_bidding_detail(**kwargs)

    @http.route('/bidding/bidding_cargo', type='json', auth="user", csrf=False)
    def bidding_cargo(self, cargo_id, user_id):
        return http.request.env['sharevan.cargo'].bidding_cargo(cargo_id, user_id)

    @http.route('/bidding/get_list_bidding_vehicle_for_company', type='json', auth="user")
    def get_list_bidding_vehicle_for_company(self, text_search, status, offset, limit):
        return http.request.env['sharevan.bidding.vehicle'].get_list_bidding_vehicle_for_company(text_search, status,
                                                                                                 offset, limit)

    @http.route('/bidding/get_lst_vehicle', type='json', auth="user")
    def get_lst_vehicle(self, text_search, status, offset, limit):
        return http.request.env['sharevan.bidding.vehicle'].get_lst_vehicle(text_search, status, offset, limit)

    @http.route('/bidding/creat_account_driver', methods=['POST'], type='http', csrf=False, auth="user")
    def creat_account_driver(self, driverInfo):
        files = request.httprequest.files.getlist('files')
        return http.request.env['sharevan.bidding.vehicle'].creat_account_driver(driverInfo, files)

    @http.route('/bidding/update_account_driver', methods=['POST'], csrf=False, type='http', auth="user")
    def update_account_driver(self, driverInfo):
        files = request.httprequest.files.getlist('files')
        return http.request.env['sharevan.bidding.vehicle'].update_account_driver(driverInfo, files)

    @http.route('/bidding/delete_account_driver', type='json', auth="user")
    def delete_account_driver(self, vehicle_id):
        return http.request.env['sharevan.bidding.vehicle'].delete_account_driver(vehicle_id)

    @http.route('/bidding/approve', type='json', auth="user")
    def bidding_approve(self, bidding_id):
        return http.request.env[Constants.SHAREVAN_BIDDING_ORDER].bidding_approve(bidding_id)

    @http.route('/bidding/confirm_received_items', type='json', auth="user")
    def confirm_received_items(self, bidding_id, bidding_received_id):
        return http.request.env[Constants.SHAREVAN_BIDDING_ORDER_RECEIVE].confirm_received_items(bidding_id,
                                                                                                 bidding_received_id)

    @http.route('/bidding/confirm_return_items', type='json', auth="user")
    def confirm_(self, bidding_id, bidding_return_id):
        return http.request.env[Constants.SHAREVAN_BIDDING_ORDER_RETURN].confirm_return_items(bidding_id,
                                                                                              bidding_return_id)

    @http.route('/bidding/get_driver_biding_order_information', type='json', auth="user")
    def get_driver_biding_order_information(self, bidding_vehicle_id, from_date, to_date, category_item_type, order_by,
                                            offset, limit):
        return http.request.env[Constants.SHAREVAN_BIDDING_ORDER].get_driver_biding_order_information(
            bidding_vehicle_id, from_date, to_date, category_item_type, order_by, offset, limit)

    @http.route('/bidding/create_action_log', type='json', auth="user")
    def create_action_log(self, action_logs):
        return http.request.env[Constants.ACTION_LOG].create_action_log(action_logs)

    @http.route('/bidding/get_bidding_vehicle_information_for_login', type='json')
    def get_bidding_vehicle_information_for_login(self, license_plate):
        return http.request.env[Constants.SHAREVAN_BIDDING_VEHICLE].get_bidding_vehicle_information_for_login(
            license_plate)

    @http.route('/bidding/get_bidding_package_information', type='json')
    def get_bidding_package_information(self, bidding_time, order_by, offset, limit):
        return http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].get_bidding_package_information(bidding_time,
                                                                                                    order_by, offset,
                                                                                                    limit)

    @http.route('/bidding/get_bidding_package_information_v2', type='json')
    def get_bidding_package_information_v2(self, bidding_time, search_code, order_by, offset, limit):
        return http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].get_bidding_package_information_v2(bidding_time,
                                                                                                       search_code,
                                                                                                       order_by, offset,
                                                                                                       limit)

    @http.route('/bidding/create_bidding_order', type='json')
    def create_bidding_order(self, bidding_package_id, confirm_time):
        return http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].create_bidding_order(bidding_package_id,
                                                                                         confirm_time)

    @http.route('/bidding/get_bidding_package_detail', type='json')
    def get_bidding_package_detail(self, bidding_package_id):
        return http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].get_bidding_package_detail(bidding_package_id)

    @http.route('/bidding/list_bidding_vehicle', type='json')
    def list_bidding_vehicle(self):
        return http.request.env[Constants.SHAREVAN_BIDDING_VEHICLE].list_bidding_vehicle()

    @http.route('/bidding/confirm_bidding_vehicle_for_bidding_order', type='json')
    def confirm_bidding_vehicle_for_bidding_order(self, bidding_order_id, bidding_vehicle_ids):
        return http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].confirm_bidding_vehicle_for_bidding_order(
            bidding_order_id, bidding_vehicle_ids)

    @http.route('/bidding/confirm_bidding_vehicle_for_bidding_order_origin', type='json')
    def confirm_bidding_vehicle_for_bidding_order_origin(self, bidding_order_id, bidding_vehicle_ids):
        return http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].confirm_bidding_vehicle_for_bidding_order_origin(
            bidding_order_id, bidding_vehicle_ids)

    @http.route('/bidding/get_bidding_order_bidded', type='json')
    def get_bidding_order_bidded(self, **kwargs):
        return http.request.env[Constants.SHAREVAN_BIDDING_ORDER].get_bidding_order_bidded(**kwargs)

    @http.route('/bidding/get_bidding_order_bidded_stockman', type='json')
    def get_bidding_order_bidded_stockman(self, **kwargs):
        return http.request.env[Constants.SHAREVAN_BIDDING_ORDER].get_bidding_order_bidded_stockman(**kwargs)

    # @http.route('/bidding/get_bidding_order_bidded_v2', type='json')
    # def get_bidding_order_bidded_v2(self, **kwargs):
    #     return http.request.env[Constants.SHAREVAN_BIDDING_ORDER].get_bidding_order_bidded_v2(**kwargs)

    @http.route('/bidding/get_vehicle_tonnage', type='json')
    def get_bidding_vehicle_tonnage(self):
        return http.request.env[Constants.SHAREVAN_BIDDING_ORDER].get_bidding_vehicle_tonnage()

    @http.route('/bidding/get_bidding_order_detail', type='json')
    def get_bidding_order_detail(self, bidding_order_id):
        return http.request.env[Constants.SHAREVAN_BIDDING_ORDER].get_bidding_order_detail(bidding_order_id)

    @http.route('/bidding/get_bidding_vehicle_by_bidding_order', type='json')
    def get_bidding_vehicle_by_bidding_order(self, bidding_order_id):
        return http.request.env[Constants.SHAREVAN_BIDDING_ORDER].get_bidding_vehicle_by_bidding_order(bidding_order_id)

    @http.route('/bidding/check_driver_phone_number', type='json')
    def check_driver_phone_number(self, driver_phone_number):
        return http.request.env[Constants.SHAREVAN_BIDDING_VEHICLE].check_driver_phone_number(driver_phone_number)

    @http.route('/bidding/check_lisence_plate', type='json')
    def check_lisence_plate(self, lisence_plate):
        return http.request.env[Constants.SHAREVAN_BIDDING_VEHICLE].check_lisence_plate(lisence_plate)

    @http.route('/bidding/check_driver_id_card', type='json')
    def check_driver_id_card(self, id_card):
        return http.request.env[Constants.SHAREVAN_BIDDING_VEHICLE].check_driver_id_card(id_card)

    @http.route('/bidding/list_manager_bidding_vehicle', type='json')
    def list_manager_bidding_vehicle(self, **kwargs):
        return http.request.env[Constants.SHAREVAN_BIDDING_VEHICLE].list_manager_bidding_vehicle(**kwargs)

    @http.route('/bidding/get_list_bidding_order_by_bidding_vehicle_id', type='json')
    def get_list_bidding_order_by_bidding_vehicle_id(self, bidding_vehicle_id, offset, limit):
        return http.request.env[Constants.SHAREVAN_BIDDING_VEHICLE].get_list_bidding_order_by_bidding_vehicle_id(
            bidding_vehicle_id, offset, limit)

    @http.route('/bidding/driver_confirm_cargo_quantity', type='json')
    def driver_confirm_cargo_quantity(self, bidding_order_id, cargo_ids, type, confirm_time):
        return http.request.env[Constants.SHAREVAN_BIDDING_ORDER].driver_confirm_cargo_quantity(bidding_order_id,
                                                                                                cargo_ids, type,
                                                                                                confirm_time)

    @http.route('/bidding/get_bidding_order_detail_by_id', type='json')
    def get_bidding_order_detail_by_id(self, bidding_order_id):
        return http.request.env[Constants.SHAREVAN_BIDDING_ORDER].get_bidding_order_detail_by_id(bidding_order_id)

    @http.route('/bidding/get_list_bidding_order_shipping', type='json')
    def get_list_bidding_order_shipping(self, offset, limit, txt_search, status):
        return http.request.env[Constants.SHAREVAN_BIDDING_VEHICLE].get_list_bidding_order_shipping(offset, limit,
                                                                                                    txt_search, status)

    @http.route('/bidding/get_list_bidding_order_shipping_v2', type='json')
    def get_list_bidding_order_shipping_v2(self, offset, limit, txt_search, order_by, status):
        return http.request.env[Constants.SHAREVAN_BIDDING_VEHICLE].get_list_bidding_order_shipping_v2(offset, limit,
                                                                                                       txt_search,
                                                                                                       order_by, status)

    @http.route('/bidding/get_list_bidding_order_history', type='json')
    def get_list_bidding_order_history(self, from_date, to_date, txt_search, offset, limit):
        return http.request.env[Constants.SHAREVAN_BIDDING_VEHICLE].get_list_bidding_order_history(from_date, to_date,
                                                                                                   txt_search,
                                                                                                   offset, limit)

    @http.route('/bidding/get_list_bidding_order_history_enterprise', type='json')
    def get_list_bidding_order_history_enterprise(self, from_date, to_date, txt_search, order_by, offset, limit):
        return http.request.env[Constants.SHAREVAN_BIDDING_VEHICLE].get_list_bidding_order_history_enterprise(from_date,
                                                                                                              to_date,
                                                                                                              txt_search,
                                                                                                              order_by,
                                                                                                              offset,
                                                                                                              limit)

    @http.route('/bidding/get_bidding_notification_history', type='json')
    def get_bidding_notification_history(self, **kwargs):
        return http.request.env[Constants.SHAREVAN_NOTIFICATION_USER_REL].get_notification_all(**kwargs)

    @http.route('/bidding/get_company_view', type='json')
    def get_company_view(self):
        return http.request.env[Constants.SHAREVAN_BIDDING_ORDER].get_company_review()

    @http.route('/notification/check_user_read_message', type='json')
    def check_user_read_message(self):
        return http.request.env[Constants.SHAREVAN_NOTIFICATION].check_user_read_message()

    @http.route('/notification/accept_firebase_notification', type='json')
    def accept_firebase_notification(self, accept_firebase):
        return http.request.env[Constants.SHAREVAN_NOTIFICATION].accept_firebase_notification(accept_firebase)

    @http.route('/depot/get_all_cargo_size_standard', type='json')
    def get_all_cargo_size_standard(self):
        return http.request.env[Constants.SHAREVAN_CARGO].get_all_cargo_size_standard()

    @http.route('/depot/get_all_cargo_by_depot_id', type='json')
    def get_all_cargo_by_depot_id(self, **kwargs):
        return http.request.env[Constants.SHAREVAN_CARGO].get_all_cargo_by_depot_id(**kwargs)

    # @http.route('/bidding/get_information_employee', type='json')
    # def get_information_employee(self, depot_id, code, offset):
    #     return http.request.env[Constants.SHAREVAN_BIDDING_ORDER].get_information_employee(depot_id, code, offset)

    @http.route('/bidding/get_information_employee', type='json')
    def get_all_bidding_order_rating(self, limit, offset):
        return http.request.env[Constants.SHAREVAN_BIDDING_ORDER].get_all_bidding_order_rating(limit, offset)

    @http.route('/bidding/get_all_bidding_order_rating', type='json')
    def get_all_bidding_order_rating_v2(self, limit, offset):
        return http.request.env[Constants.SHAREVAN_BIDDING_ORDER].get_all_bidding_order_rating_v2(limit, offset)

    @http.route('/bidding/test_notification', type='json')
    def test(self):
        user = [105, 117]
        bidding_order_id = 1
        return http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].send_bidding_information_success(user,
                                                                                                     bidding_order_id)

    @http.route('/bidding/update_account_long_haul', methods=['POST'], csrf=False, type='http', auth="user")
    def update_account_long_haul(self, longHaulInfo):
        files = request.httprequest.files.getlist('files')
        return http.request.env[RES_PARTNER].update_account_long_haul(longHaulInfo, files)

    @http.route('/bidding/create_cargo_data_for_test', type='json')
    def create_cargo_data_for_test(self):
        return http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].create_cargo_data_for_test()

    @http.route('/bidding/create_bidding_package_for_test', type='json',auth='user')
    def create_bidding_package_for_test(self):
        return http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].create_bidding_package_for_test()

    @http.route('/bidding/get_fleet_vehicle', type='json',auth='user')
    def get_fleet_vehicle(self,**kwargs):
        return http.request.env[Constants.SHAREVAN_BIDDING_ORDER].get_fleet_vehicle(**kwargs)


    @http.route('/bidding/get_fleet_driver', type='json',auth='user')
    def get_fleet_driver(self,**kwargs):
        return http.request.env[Constants.SHAREVAN_BIDDING_ORDER].get_fleet_driver(**kwargs)

    @http.route('/bidding/get_vehicle_type', type='json',auth='user')
    def get_vehicle_type(self):
        return http.request.env[Constants.SHAREVAN_BIDDING_ORDER].get_vehicle_type()


    @http.route('/driver/market_place_confirm_order', csrf=False, type='json', auth="user")
    def driver_market_place_confirm_order(self, bidding_package_id, type):
        return http.request.env[Constants.SHAREVAN_BIDDING_ORDER].driver_market_place_confirm_order(bidding_package_id,
                                                                                                    type)

    @http.route('/market_place/get_bidding_package_id', csrf=False, type='json', auth="user")
    def get_bidding_package_id(self, bidding_package_id):
        return http.request.env[Constants.SHAREVAN_BIDDING_ORDER].get_bidding_package_id(bidding_package_id)

    @http.route('/sharevan/get_rating_title_award', csrf=False, type='json', auth="user")
    def get_rating_title_award(self):
        return http.request.env[Constants.SHAREVAN_BIDDING_ORDER].get_rating_title_award()

    @http.route('/sharevan/get_history_rating_point', csrf=False, type='json', auth="user")
    def get_history_rating_point(self, type, page, limit):
        return http.request.env[Constants.SHAREVAN_BIDDING_ORDER].get_history_rating_point(type, page, limit)

    @http.route('/sharevan/check_product_type', csrf=False, type='json', auth="public")
    def check_product_type(self, currentProductType, newProductType):
        return http.request.env[Constants.SHAREVAN_BIDDING_ORDER].check_product_type(currentProductType, newProductType)

    @http.route('/bidding/get_bidding_package_test', type='json', auth="public")
    def get_bidding_package_information_test(self, search_info, offset, limit):
        return http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].get_bidding_package_information_test(search_info, offset,
                                                                                                       limit)
    @http.route('/bidding/create_bidding_orderV3', type='json')
    def create_bidding_orderV3(self, bidding_package_id):
        return http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].create_bidding_orderv3(bidding_package_id)

