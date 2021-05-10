# -*- coding: utf-8 -*-
import logging
from datetime import datetime

import pytz
import werkzeug

from mymodule.base_next.controllers.api.base_method import BaseMethod
from mymodule.enum.ClickActionType import ClickActionType
from mymodule.enum.MessageType import MessageType
from mymodule.enum.NotificationType import NotificationType
from mymodule.enum.PointUpgradeType import PointUpgradeType
from mymodule.enum.RoutingDetailStatus import RoutingDetailStatus
from mymodule.enum.WarehouseType import WarehouseType
from mymodule.share_van_order.controllers.api.base import BaseApi
from mymodule.share_van_order.controllers.api.bill_lading_detail import BillLadingDetailApi
from mymodule.share_van_order.models.sharevan_notification import Notification
from odoo import http
from odoo.exceptions import ValidationError

logger = logging.getLogger(__name__)


class BillLadingApi:
    MODEL = 'sharevan.bill.lading'

    @staticmethod
    def create_bill_lading(billLading):
        insurance_id = 0
        order_package_id = 0
        start_date = ''
        for key in billLading.keys():
            if key == 'insurance':
                insurance = billLading[key]
                insurance_id = insurance['id']
            if key == 'order_package':
                order_package = billLading[key]
                order_package_id = order_package['id']
            if key == 'startDateStr':
                start_date = billLading[key]
        if start_date == '':
            raise werkzeug.exceptions.ExpectationFailed("Validation error start date")
        date_arr = start_date.split('/')
        date = datetime(int(date_arr[2]), int(date_arr[1]), int(date_arr[0]), 0, 0)
        instance = BaseApi.getInstance(BillLadingApi.MODEL, billLading)
        instance['start_date'] = date
        instance['insurance_id'] = insurance_id
        session, data_json = BaseMethod.check_authorized()
        company_id = http.request.env.company.id
        if not company_id:
            company_id =session['company_id']
        billLading['company_id']=company_id
        instance['order_package_id'] = order_package_id
        instance['bill_lading_detail_ids'] = BillLadingDetailApi. \
            create_bill_lading_details(billLading['arrBillLadingDetail'])
        return http.request.env[BillLadingApi.MODEL].create(instance)

    def update_routing_now(self, billLading):
        query = """
            select rpd.id, rpd.type,rpd.routing_plan_day_code,rpd.from_routing_plan_day_id,
                rpd.bill_lading_detail_id 
                from sharevan_routing_plan_day rpd
                join (WITH RECURSIVE c AS (
                    SELECT (
                        SELECT sharevan_routing_plan_day.id from sharevan_routing_plan_day 
                            join sharevan_bill_lading_detail bill_detail 
                        on sharevan_routing_plan_day.bill_lading_detail_id = bill_detail.id
                            where bill_detail.bill_lading_id =  """
        query += str(billLading['from_bill_lading_id'])
        query += """ and date_plan = CURRENT_DATE and bill_detail.warehouse_type ='0'
                   ) AS id
                   UNION ALL
                   SELECT sa.id
                   FROM sharevan_routing_plan_day AS sa
                      JOIN c ON c.id = sa.from_routing_plan_day_id
                )
                    SELECT id FROM c) routing on routing.id = rpd.id
                order by id
                    """
        http.request.cr.execute(query, ())
        record = http.request._cr.dictfetchall()
        # YTI TODO:  chờ check case
        if len(record) > 0:
            bill_detail_import = billLading['arrBillLadingDetail'][0]
            bill_package = billLading['arrBillLadingDetail'][0]['billPackages']
            billLading['arrBillLadingDetail'].pop(0)
            bill_lading_detail_export = billLading['arrBillLadingDetail']
            routing_import = record[0]
            record.pop(0)
            routing_export = record
            BaseMethod.check_role_access(http.request.env.user, 'sharevan.routing.plan.day', routing_export[0]['id'])
            for package in bill_package:
                import_change = http.request.env['sharevan.bill.package.routing.import'].search(
                    [('routing_plan_day_id', '=', routing_import['id']),
                     ('bill_package_id', '=', package['from_bill_package_id'])])
                if import_change:
                    import_change.write({
                        'quantity_import': package['quantity_package'],
                        'length': package['length'],
                        'width': package['width'],
                        'height': package['height'],
                        'total_weight': package['net_weight'],
                        'bill_package_id': package['id']
                    })
                else:
                    raise ValidationError('There is a trouble in update routing! Import bill package not found')
            for export in routing_export:
                if export['type'] == WarehouseType.Import.value:
                    for billLading_detail in bill_lading_detail_export:
                        if export['bill_lading_detail_id'] == billLading_detail['id']:
                            routing_change = http.request.env['sharevan.routing.plan.day'].search(
                                [('id', '=', export['id'])])
                            if routing_change:
                                routing_change.write({
                                    # 'total_weight': billLading_detail['total_weight'],
                                    'total_volume': billLading_detail['total_volume'],
                                    'assess_amount': billLading_detail['price']
                                })
                            else:
                                raise ValidationError('Routing change not found!')
                        for bill_package in billLading_detail['billPackages']:
                            import_change = http.request.env['sharevan.bill.package.routing.import'].search(
                                [('routing_plan_day_id', '=', export['id']),
                                 ('bill_package_id', '=', bill_package['id'])])
                            if import_change:
                                import_change.write({
                                    'quantity_import': bill_package['quantity_package'],
                                    'length': bill_package['length'],
                                    'width': bill_package['width'],
                                    'height': bill_package['height'],
                                    'total_weight': bill_package['net_weight'],
                                    'bill_package_id': bill_package['id']
                                })
                elif export['type'] == WarehouseType.Export.value:
                    for billLading_detail in bill_lading_detail_export:
                        if export['bill_lading_detail_id'] == billLading_detail['id']:
                            routing_change = http.request.env['sharevan.routing.plan.day'].search(
                                [('id', '=', export['id'])])
                            if routing_change:
                                routing_change.write({
                                    # 'total_weight': billLading_detail['total_weight'],
                                    'total_volume': billLading_detail['total_volume'],
                                    'assess_amount': billLading_detail['price']
                                })
                            else:
                                raise ValidationError('Routing change not found!')
                        for bill_package in billLading_detail['billPackages']:
                            export_change = http.request.env['sharevan.bill.package.routing.export'].search(
                                [('routing_plan_day_id', '=', export['id']),
                                 ('bill_package_id', '=', bill_package['id'])])
                            if export_change:
                                export_change.write({
                                    'quantity_export': bill_package['quantity_package'],
                                    'length': bill_package['length'],
                                    'width': bill_package['width'],
                                    'height': bill_package['height'],
                                    'total_weight': bill_package['net_weight'],
                                    'bill_package_id': bill_package['id']
                                })
                else:
                    raise ValidationError('There is a trouble in update routing! routing bill package not found')
            item_id = routing_import['routing_plan_day_code']
            driver_id = 0
            routing_plan_day = http.request.env['sharevan.routing.plan.day'].search(
                [('routing_plan_day_code', '=', item_id)])
            if routing_plan_day:
                driver_id = routing_plan_day['driver_id']
                routing_plan_day.write({'status': '2', 'assess_amount': bill_detail_import['price'],
                                        # 'total_weight': bill_detail_import['total_weight'],
                                        'total_volume': bill_detail_import['total_volume'], })
                bill_routing = http.request.env['sharevan.bill.routing'].search(
                    [('id', '=', routing_plan_day['bill_routing_id'].id)])
                bill_routing.write({'status_routing':'1','total_amount':billLading['total_amount']})
                point_record = http.request.env['sharevan.reward.point'].search(
                    [('code', '=', PointUpgradeType.Routing.value),('type_reward_point', '=', 'driver')])
                if point_record:
                    driver_record = http.request.env['fleet.driver'].search(
                    [('id', '=', driver_id.id)])
                    if driver_record['point']:
                        point = driver_record['point'] + point_record['point']
                        driver_record.write({'point':point})
            else:
                raise ValidationError('There is a trouble when update routing plan day')
            ids = []
            # employee share van
            query = """ 
                select us.id from res_users us
                    join res_company company on us.company_id = company.id
                where company.company_type = '2' and us.active = true """
            http.request.cr.execute(query, ())
            record = http.request._cr.dictfetchall()
            for id in record:
                ids.append(id['id'])
            # driver_id
            driver_query = """ 
                            select us.user_id from fleet_driver us
                             where us.id = %s """
            http.request.cr.execute(driver_query, (driver_id.id,))
            record = http.request._cr.dictfetchall()
            for id in record:
                driver_id = id['user_id']
            # gui den quan ly cua cong ty thong bao thay doi
            query = """ 
                select us.id from res_users us
                    join sharevan_channel channel on channel.id = us.channel_id 
                where us.company_id = %s and us.active = true
                    and channel.name = 'customer' and channel_type in ('manager','employee') """
            http.request.cr.execute(query, (http.request.env.company.id,))
            record = http.request._cr.dictfetchall()
            if len(record) > 0:
                for id in record:
                    ids.append(id['id'])
                title = 'Routing plan day change'
                body = 'Routing plan day has change ' + item_id + '! '
                try:
                    val = {
                        'user_id': ids,
                        'title': title,
                        'content': body,
                        'click_action': ClickActionType.routing_plan_day_customer.value,
                        'message_type': MessageType.danger.value,
                        'type': NotificationType.RoutingMessage.value,
                        'object_status': RoutingDetailStatus.Unconfimred.value,
                        'item_id': item_id,
                    }
                    http.request.env['sharevan.notification'].create(val)
                    val = {
                        'user_id': [driver_id],
                        'title': title,
                        'content': body,
                        'click_action': ClickActionType.routing_plan_day_driver.value,
                        'message_type': MessageType.danger.value,
                        'type': NotificationType.RoutingMessage.value,
                        'object_status': RoutingDetailStatus.Unconfimred.value,
                        'item_id': item_id,
                    }
                    http.request.env['sharevan.notification'].create(val)
                    return {
                        'status': 200,
                        'message': 'update routing successful!'
                    }
                except:
                    try:
                        val = {
                            'user_id': [driver_id],
                            'title': title,
                            'content': body,
                            'click_action': ClickActionType.routing_plan_day_driver.value,
                            'message_type': MessageType.danger.value,
                            'type': NotificationType.RoutingMessage.value,
                            'object_status': RoutingDetailStatus.Unconfimred.value,
                            'item_id': item_id,
                        }
                        http.request.env['sharevan.notification'].create(val)
                        return {
                            'status': 200,
                            'message': 'update routing successful!'
                        }
                    except:
                        logger.warn(
                            "Save bill of lading change! But can not send message",
                            'Routing Plan Day', item_id,
                            exc_info=True)
                        return {
                            'status': 200,
                            'message': 'update routing successful!'
                        }
            else:
                title = 'Routing plan day change'
                body = 'Routing plan day has change ' + item_id + '! '
                try:
                    val = {
                        'user_id': ids,
                        'title': title,
                        'content': body,
                        'click_action': ClickActionType.routing_plan_day_customer.value,
                        'message_type': MessageType.danger.value,
                        'type': NotificationType.RoutingMessage.value,
                        'object_status': RoutingDetailStatus.Unconfimred.value,
                        'item_id': item_id,
                    }
                    http.request.env['sharevan.notification'].create(val)
                    val = {
                        'user_id': [driver_id],
                        'title': title,
                        'content': body,
                        'click_action': ClickActionType.routing_plan_day_driver.value,
                        'message_type': MessageType.danger.value,
                        'type': NotificationType.RoutingMessage.value,
                        'object_status': RoutingDetailStatus.Unconfimred.value,
                        'item_id': item_id,
                    }
                    http.request.env['sharevan.notification'].create(val)
                    return {
                        'status': 200,
                        'message': 'update routing successful!'
                    }
                except:
                    try:
                        val = {
                            'user_id': [driver_id],
                            'title': title,
                            'content': body,
                            'click_action': ClickActionType.routing_plan_day_driver.value,
                            'message_type': MessageType.danger.value,
                            'type': NotificationType.RoutingMessage.value,
                            'object_status': RoutingDetailStatus.Unconfimred.value,
                            'item_id': item_id,
                        }
                        http.request.env['sharevan.notification'].create(val)
                        return {
                            'status': 200,
                            'message': 'update routing successful!'
                        }
                    except:
                        logger.warn(
                            "Save bill of lading change! But can not send message",
                            'Routing Plan Day', item_id,
                            exc_info=True)
                        return {
                            'status': 200,
                            'message': 'update routing successful!'
                        }
        else:
            raise ValidationError('There is a trouble in update bill of lading')

    def update_bill_lading_origin(from_bill_lading_id):
        time_now = datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d")
        origin_bill = http.request.env['sharevan.bill.lading'].search([('id', '=', from_bill_lading_id)])
        check = origin_bill.write({'end_date', time_now})
        return check['id']
