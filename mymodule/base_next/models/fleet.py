# -*- coding: utf-8 -*-
import base64
import json
import logging
from datetime import timedelta, datetime

import requests

from mymodule.base_next.controllers.api.base_method import BaseMethod
from mymodule.base_next.models.notification import SosRegisterDriver, Notification
from mymodule.base_next.models.routing_plan_day import RoutingPlanDay
from mymodule.constants import Constants
from mymodule.enum.BillRoutingStatus import BillRoutingStatus
from mymodule.enum.ClickActionType import ClickActionType
from mymodule.enum.MessageType import MessageType, NotificationSocketType
from mymodule.enum.NotificationType import NotificationType
from mymodule.enum.RoutingDetailStatus import RoutingDetailStatus
from mymodule.enum.RoutingTroubleType import RoutingTroubleType
from odoo import fields, models, http, api
from odoo.addons.base.models.ir_attachment import IrAttachment
from odoo.exceptions import ValidationError
from odoo.tools import config

INSERT_QUERY_SOS = "INSERT INTO ir_attachment_sharevan_driver_sos_rel " \
                   " VALUES ( %s , %s ) "
logger = logging.getLogger(__name__)


class FleetVehicleType(models.Model):
    _name = 'fleet.vehicle.type'
    _description = 'Vehicle type'
    _order = 'name'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code')
    description = fields.Text(string='Description')
    status = fields.Selection([('running', 'Running'), ('deleted', 'Deleted')], string='Status',
                              default='running')

    def unlink(self):
        print(self)
        for record in self.ids:
            record_id = self.env['fleet.vehicle.type'].search([('id', '=', record)])
            record_id.write({
                'status': 'deleted'
            })
        return self


class TcPositions(models.Model):
    _name = 'tc.positions'
    _description = 'positions'

    protocol = fields.Char()
    deviceid = fields.Integer()
    vehicle_id = fields.Integer()
    servertime = fields.Datetime()
    devicetime = fields.Datetime()
    fixtime = fields.Datetime()
    valid = fields.Boolean()
    latitude = fields.Float()
    longitude = fields.Float()
    altitude = fields.Float()
    speed = fields.Float()
    course = fields.Float()
    address = fields.Char()
    attributes = fields.Char()
    accuracy = fields.Float()
    network = fields.Char()


# class TcDevices(models.TransientModel):
#     _name = 'tc.devices'
#     _description = 'devices'
# positionid = fields.Char()


class FleetVehicle(models.Model):
    _name = 'fleet.vehicle'
    _description = 'Vehicle'

    name = fields.Char(store=True)
    iot_type = fields.Boolean('IOT', default=True)
    active = fields.Boolean('Active', default=True, tracking=True)
    sos_ids = fields.One2many('sharevan.driver.sos', 'vehicle_id', string='Sos Type')
    position_ids = fields.One2many('tc.positions', 'deviceid', string='Position')
    from_date = fields.Date()
    to_date = fields.Date()
    fleet_management_id = fields.Many2one('fleet.management', string="Fleet management")
    is_selected = fields.Boolean(default = False)
    deviation_capacity = fields.Float('Deviation Capacity')

    def accept_sos_type_last(self, sos_type, files):
        sos_type_object = json.loads(sos_type)
        lst_image = []
        uid = http.request.env.uid
        query = """
            SELECT json_agg(t) FROM (
                SELECT  routing.vehicle_id, routing.driver_id
                    FROM  fleet_driver driver on driver.id =  dri_cale.driver_id
                        join sharevan_routing_plan_day routing on routing.driver_id = dri_cale.driver_id
                where dri_cale.vehicle_id = %s and driver.user_id = %s AND routing.id= %s
            )t
            """
        self._cr.execute(query, (sos_type_object['vehicle_id'], uid, sos_type_object['routing_plan_day_id'],))
        record = self._cr.fetchall()
        if record[0]:
            if record[0][0]:
                sos_type_object['driver_id'] = record[0][0][0]['driver_id']
                result = http.request.env[SosRegisterDriver._name].create(sos_type_object)
                for file in files:
                    if file.filename:
                        val = {
                            'res_model': 'sharevan.driver.sos',
                            'mimetype': file.mimetype,
                            'name': file.filename,
                            'res_id': 0,
                            'company_id': http.request.env.company.id,
                            'type': 'binary',
                            'datas': base64.b64encode(file.read())
                        }
                        rec = http.request.env[IrAttachment._name].create(val)
                        http.request.cr.execute(INSERT_QUERY_SOS, (result['id'], rec['id'],))
                ids = []
                # employee share van
                query = """
                 SELECT json_agg(t)
                    FROM (
                        select us.id from res_users us
                            join res_company company on us.company_id = company.id
                        where company.company_type = '2' and us.active = true )t """
                self._cr.execute(query, ())
                record = self._cr.fetchall()
                if record[0]:
                    if record[0][0]:
                        for re in record[0][0]:
                            ids.append(re['id'])
                # user fleet company
                query = """
                 SELECT json_agg(t)
                    FROM (select us.id 
                            from res_users us
                                join sharevan_channel channel on channel.id = us.channel_id 
                            where us.company_id = %s and us.active = true
                                and channel.name = 'fleet' and channel_type= 'manager' )t"""
                self._cr.execute(query, (http.request.env.company.id,))
                record = self._cr.fetchall()
                if record[0]:
                    if record[0][0]:
                        for re in record[0][0]:
                            ids.append(re['id'])
                query = """ 
                    select company_id, routing_plan_day_code
                        from sharevan_routing_plan_day  where id = %s """
                self._cr.execute(query, (sos_type_object['routing_plan_day_id'],))
                record = self._cr.fetchall()
                routing_plan_day_list = []
                if record:
                    for re in record:
                        routing_plan_day_code = re[1]
                        company_id = re[0]
                        routing_plan_day_list.append(routing_plan_day_code)
                        query = """ 
                            SELECT json_agg(t)
                                FROM (
                                select us.id from res_users us
                                join sharevan_channel channel on channel.id = us.channel_id 
                            where us.company_id = %s and us.active = true
                                and channel.name = 'customer' and channel_type in ('manager','employee') )t """
                        self._cr.execute(query, (company_id,))
                        record = self._cr.fetchall()
                        if record[0]:
                            if record[0][0]:
                                for re in record[0][0]:
                                    ids.append(re['id'])
                        title = 'SOS WARNING!'
                        body = 'Van trouble in routing plan day! ' \
                               + routing_plan_day_code
                        item_id = routing_plan_day_code
                        try:
                            val = {
                                'user_id': ids,
                                'title': title,
                                'content': body,
                                'click_action': ClickActionType.routing_plan_day_customer.value,
                                'message_type': MessageType.danger.value,
                                'type': NotificationType.RoutingMessage.value,
                                'object_status': RoutingDetailStatus.Done.value,
                                'item_id': item_id,
                            }
                            http.request.env[Notification._name].create(val)
                            # return http.Response('Successful')
                        except:
                            logger.warn(
                                "Save sos warning Successful! But can not send message",
                                RoutingPlanDay._name, item_id,
                                exc_info=True)
                            # return http.Response('Successful')

                else:
                    raise ValidationError('Routing not found!')
            else:
                raise ValidationError('Driver not assgin for vehicle today! Please check information again!')
        else:
            raise ValidationError('Driver not assgin for vehicle today! Please check information again!')

    def accept_sos_type(self, sos_type, order_number, files):
        sos_type_object = json.loads(sos_type)
        lst_image = []
        uid = http.request.env.uid
        BaseMethod.check_role_access(http.request.env.user, 'sharevan.routing.plan.day', sos_type_object['routing_plan_day_id'])
        vehicle_id =0
        date_plan=''
        sos_status='0'
        query = """
            select plan.id, plan.status,plan.order_number,plan.driver_id,plan.vehicle_id,plan.so_type,plan.company_id,
                routing.qr_code,routing.code,plan.bill_routing_id,plan.type,plan.date_plan
            from sharevan_routing_plan_day plan 
                join fleet_driver driver on driver.id = plan.driver_id 
                left join sharevan_bill_routing routing on routing.id = plan.bill_routing_id
            where date_plan = CURRENT_DATE and user_id = %s order by order_number
            """
        self._cr.execute(query, (uid,))
        record = self._cr.dictfetchall()
        if record:
            company_ids = []
            so_check = False
            so_bill_code = ''
            driver_id = 0
            plan_tree_list_ids = []
            update_list_record=[]
            for rec in record:
                date_plan= rec['date_plan']
                update_list_record.append(rec['id'])
                driver_id = rec['driver_id']
                vehicle_id = rec['vehicle_id']
                if rec['type'] == '0':
                    plan_tree_list_ids.append(rec['id'])
                if rec['so_type'] and int(rec['status']) < 2:
                    so_bill_code += rec['qr_code'] + ','
                    so_check = True
                elif int(rec['status']) < 2:
                    info = {
                        'company_id': rec['company_id'],
                        'bill_code': [rec['code']],
                        'item_id': rec['bill_routing_id']
                    }
                    company_ids.append(info)
                    # else:
                    #     for company in company_ids:
                    #         if rec['company_id'] == company['company_id']:
                    #             company['bill_code'].append(rec['code'])
                    #         else:
                    #             info = {
                    #                 'company_id': rec['company_id'],
                    #                 'bill_code': [rec['code']],
                    #                 'item_id': rec['bill_routing_id']
                    #             }
                    #             company_ids.append(info)
            if sos_type_object['continue_check'] == True:
                sos_status= '1'
                sos_type_object['driver_id'] = driver_id
                sos_type_object['date_plan'] = date_plan
                print(sos_type_object)
                result = http.request.env[SosRegisterDriver._name].create(sos_type_object)
                for file in files:
                    if file.filename:
                        val = {
                            'res_model': 'sharevan.driver.sos',
                            'mimetype': file.mimetype,
                            'name': file.filename,
                            'res_id': 0,
                            'company_id': http.request.env.company.id,
                            'type': 'binary',
                            'datas': base64.b64encode(file.read())
                        }
                        rec = http.request.env[IrAttachment._name].create(val)
                        http.request.cr.execute(INSERT_QUERY_SOS, (result['id'], rec['id'],))
                for rec in record:
                    if int(rec['status']) < 2:
                        routing_update = http.request.env['sharevan.routing.plan.day'].search(
                            [('id', '=', rec['id'])])
                        if routing_update:
                            expected_from_time = routing_update['expected_from_time'] + \
                                                 timedelta(minutes=sos_type_object['delay_time'])
                            expected_to_time = routing_update['expected_to_time'] + \
                                               timedelta(minutes=sos_type_object['delay_time'])
                            print(expected_from_time, expected_to_time, routing_update['id'])
                            routing_update.write({
                                'expected_from_time': expected_from_time, 'expected_to_time': expected_to_time
                            })
                        else:
                            logger.warn(
                                "Can not find routing plan day id on sos create",
                                RoutingPlanDay._name, rec['id'],
                                exc_info=True)
            else:
                sos_status='2'
                bill_routing_id=0
                sos_record_id=0
                waiting_routing_plan_day_change = []
                # kiểm tra kho xuất đã xuất chưa
                for routing_export in plan_tree_list_ids:
                    tree_routing_query = """
                        select plan.*,driver.phone driver_phone from sharevan_routing_plan_day plan
	                        join fleet_driver driver on driver.id = plan.driver_id 
                        where plan.id in (WITH RECURSIVE c AS (
                        SELECT %s AS id
                        UNION ALL
                        SELECT sa.id
                        FROM sharevan_routing_plan_day AS sa
                        JOIN c ON c.id = sa.from_routing_plan_day_id
                        )
                        SELECT id FROM c)
                        order by plan.id asc

                    """
                    self._cr.execute(tree_routing_query, (routing_export,))
                    list_tree = self._cr.dictfetchall()
                    if list_tree:
                        update_all = False
                        for routing in list_tree:
                            bill_routing_id= routing['bill_routing_id']
                            # kho xuất chưa xuât => cho driver_id và vehicle_id => null
                            if routing_export == routing['id'] and routing['status'] == '0':
                                # bên routing tự update
                                # update_query = """
                                #     UPDATE public.sharevan_routing_plan_day
                                #         SET driver_id = null ,vehicle_id = null, order_number = null
                                #     WHERE id = %s
                                # """
                                # self._cr.execute(update_query, (routing_export,))
                                update_all = True
                            elif routing_export == routing['id'] and routing['status'] == '2':
                                new_routing_package_info = []
                                finish_routing_export = []
                                capacity_expected= routing['capacity_expected']*-1
                                for routing_child in list_tree:
                                    if routing_child['type'] == '1' and routing_child['status'] == '0':
                                        new_routing_package_info.append(routing_child['id'])
                                    elif routing_child['type'] == '1' and routing_child['status'] == '2':
                                        finish_routing_export.append(routing_child['id'])
                                    elif routing_child['type'] == '1' and routing_child['status'] == '1':
                                        raise ValidationError('You have not complete routing')
                                # tạo 2 routing mới và bill_package mới:
                                now = datetime.now()
                                end_routing_old_driver = {
                                    'routing_plan_day_code': routing['routing_plan_day_code'] + '_SOS_EXPORT',
                                    'date_plan': routing['date_plan'],
                                    'driver_id': routing['driver_id'],
                                    'vehicle_id': routing['vehicle_id'],
                                    'latitude': sos_type_object['latitude'],
                                    'longitude': sos_type_object['longitude'],
                                    'address': sos_type_object['address'],
                                    'order_number': int(order_number),
                                    'status': '2',
                                    'expected_from_time': now,
                                    'expected_to_time': now,
                                    'actual_time': now,
                                    'accept_time': now,
                                    'depot_id': routing['depot_id'],
                                    'zone_area_id': routing['zone_area_id'],
                                    'type': '1',
                                    'warehouse_name': 'driver sos',
                                    'bill_lading_detail_code': routing['bill_lading_detail_code'],
                                    'phone': routing['driver_phone'],
                                    'trouble_type': RoutingTroubleType.Sos.value,
                                    'confirm_time': now,
                                    'partner_id': routing['partner_id'],
                                    'max_tonnage_shipping': routing['max_tonnage_shipping'],
                                    'previous_id': routing['previous_id'],
                                    'company_id': routing['company_id'],
                                    'capacity_expected': routing['capacity_expected'],
                                    'stock_man_id': routing['stock_man_id'],
                                    'insurance_id': routing['insurance_id'],
                                    'assess_amount': routing['assess_amount'],
                                    'total_volume': routing['total_volume'],
                                    'total_package': routing['total_package'],
                                    'capacity_actual': routing['capacity_actual'],
                                    'hub_id': routing['hub_id'],
                                    'description': sos_type_object['note'],
                                    'ship_type': routing['ship_type'],
                                    'bill_lading_detail_id': routing['bill_lading_detail_id'],
                                    'from_routing_plan_day_id': routing['id'],
                                    'qr_so': routing['qr_so'],
                                    'solution_day_id': routing['solution_day_id'],
                                    'so_type': routing['so_type'],
                                    'num_receive': routing['num_receive'],
                                    'bill_routing_id': routing['bill_routing_id']
                                }
                                print('_SOS_EXPORT', end_routing_old_driver)
                                end_routing_record = http.request.env['sharevan.routing.plan.day'].create(
                                    end_routing_old_driver)
                                update_list_record.append(end_routing_record['id'])
                                # tạo sos for new routing old car
                                sos_type_object['driver_id'] = driver_id
                                sos_type_object['date_plan'] = date_plan
                                print(sos_type_object)
                                sos_type_object['routing_plan_day_id']= end_routing_record['id']
                                result = http.request.env[SosRegisterDriver._name].create(sos_type_object)
                                sos_record_id=result['id']
                                for file in files:
                                    if file.filename:
                                        val = {
                                            'res_model': 'sharevan.driver.sos',
                                            'mimetype': file.mimetype,
                                            'name': file.filename,
                                            'res_id': 0,
                                            'company_id': http.request.env.company.id,
                                            'type': 'binary',
                                            'datas': base64.b64encode(file.read())
                                        }
                                        rec = http.request.env[IrAttachment._name].create(val)
                                        http.request.cr.execute(INSERT_QUERY_SOS, (sos_record_id, rec['id'],))
                                print('new_routing_package_info', new_routing_package_info)
                                new_routing = {
                                    'routing_plan_day_code': routing['routing_plan_day_code'] + '_SOS_IMPORT',
                                    'date_plan': routing['date_plan'],
                                    'latitude': sos_type_object['latitude'],
                                    'longitude': sos_type_object['longitude'],
                                    'address': sos_type_object['address'],
                                    'status': '5',
                                    'expected_from_time': now,
                                    'expected_to_time': now,
                                    'depot_id': routing['depot_id'],
                                    'driver_id': routing['driver_id'],
                                    'vehicle_id': routing['vehicle_id'],
                                    'capacity_expected': routing['capacity_expected'],
                                    'stock_man_id': routing['stock_man_id'],
                                    'insurance_id': routing['insurance_id'],
                                    'assess_amount': routing['assess_amount'],
                                    'total_volume': routing['total_volume'],
                                    'total_package': routing['total_package'],
                                    'capacity_actual': routing['capacity_actual'],
                                    'hub_id': routing['hub_id'],
                                    'zone_area_id': routing['zone_area_id'],
                                    'max_tonnage_shipping': routing['max_tonnage_shipping'],
                                    'type': '0',
                                    'warehouse_name': 'driver sos',
                                    'bill_lading_detail_code': routing['bill_lading_detail_code'],
                                    'phone': routing['driver_phone'],
                                    'trouble_type': RoutingTroubleType.Sos.value,
                                    'partner_id': routing['partner_id'],
                                    'order_number': int(order_number)-1,
                                    'previous_id': routing['previous_id'],
                                    'company_id': routing['company_id'],
                                    'description': sos_type_object['note'],
                                    'ship_type': routing['ship_type'],
                                    'bill_lading_detail_id': routing['bill_lading_detail_id'],
                                    'qr_so': routing['qr_so'],
                                    'qr_gen_check': True,
                                    'solution_day_id': routing['solution_day_id'],
                                    'so_type': routing['so_type'],
                                    'num_receive': routing['num_receive'],
                                    'bill_routing_id': routing['bill_routing_id'],
                                    'from_routing_plan_day_id': end_routing_record['id'],
                                }
                                print('_SOS_IMPORT', new_routing)
                                new_routing_record = http.request.env['sharevan.routing.plan.day'].create(new_routing)
                                update_list_record.append(new_routing_record['id'])
                                waiting_routing_plan_day_change.append(new_routing_record['id'])
                                # tạo bản ghi bill package tương ứng với 2 record trên và
                                bill_plan_query = """
                                    SELECT id, quantity, length, width, height, total_weight, capacity, product_type_id, product_package_type_id, bill_package_id, bill_lading_detail_id, note, item_name, insurance_name, service_name, from_warehouse_id, to_warehouse_id, "QRchar", qr_char, routing_plan_day_id, status,  name, gen_qr_check
	                                FROM public.sharevan_bill_package_routing_plan where routing_plan_day_id =%s
                                """
                                self._cr.execute(bill_plan_query, (routing_export,))
                                bill_routing_package_plan = self._cr.dictfetchall()
                                new_place_pack_plan_old_car = []
                                new_place_pack_import_old_car = []
                                if bill_routing_package_plan:
                                    for plan in bill_routing_package_plan:
                                        new_place_pack_plan_old_car.append(plan)
                                bill_import_query = """
                                    SELECT package.id, package.quantity_import, package.length, package.width, package.height, package.total_weight, 
                                        package.capacity, package.product_type_id, package.product_package_type_id, package.bill_package_id, 
                                        package.bill_lading_detail_id, package.note, package.item_name,package.qr_char, package.routing_plan_day_id, 
                                        package.routing_plan_code, 
                                        package.name, package.routing_package_plan, package.qr_char_confirms
                                    FROM public.sharevan_bill_package_routing_import package
                                        where routing_plan_day_id =%s
                                                                """
                                self._cr.execute(bill_import_query, (routing_export,))
                                bill_routing_package_plan_import = self._cr.dictfetchall()
                                if bill_routing_package_plan_import:
                                    for plan in bill_routing_package_plan_import:
                                        new_place_pack_import_old_car.append(plan)
                                pack_plan_code = BaseMethod.get_new_sequence('sharevan.bill.package.routing.plan',
                                                                             'BRP', 12, 'name')
                                # package_old_car_export = []
                                # package_new_car_import = []
                                # Xử lý cộng trừ quantity đối với các kho đã xuất khi finish_routing_export length >0
                                for routing_child in finish_routing_export:
                                    bill_routing_package_child_plan = http.request.env[
                                        'sharevan.bill.package.routing.plan'].search(
                                        [('routing_plan_day_id', '=', routing_child)])
                                    bill_routing_package_child_plan_export = http.request.env[
                                        'sharevan.bill.package.routing.export'].search(
                                        [('routing_plan_day_id', '=', routing_child)])
                                    for bil_pack_parent_plan in new_place_pack_plan_old_car:
                                        # trừ số lượng hàng đã xuất theo kế hoạch
                                        for bil_pack_child_plan in bill_routing_package_child_plan:
                                            if bil_pack_parent_plan['product_type_id'] == bil_pack_child_plan[
                                                'product_type_id'] and bil_pack_parent_plan['length'] == \
                                                    bil_pack_child_plan['length'] \
                                                    and bil_pack_parent_plan['width'] == bil_pack_child_plan[
                                                'width'] \
                                                    and bil_pack_parent_plan['height'] == bil_pack_child_plan[
                                                'height']:
                                                print('bil_pack_parent_plan', bil_pack_parent_plan['quantity'])
                                                print('bil_pack_child_plan', bil_pack_child_plan['quantity'])
                                                bil_pack_parent_plan['quantity'] = bil_pack_parent_plan['quantity'] - \
                                                                                   bil_pack_child_plan['quantity']
                                        new_old_car_plan_record = None
                                        new_car_package_plan_record = None
                                        if bil_pack_parent_plan['quantity'] > 0:
                                            print(bil_pack_parent_plan['quantity'])
                                            bil_pack_parent_plan_new = {
                                                'quantity': bil_pack_parent_plan['quantity'],
                                                'length': bil_pack_parent_plan['length'],
                                                'width': bil_pack_parent_plan['width'],
                                                'height': bil_pack_parent_plan['height'],
                                                'total_weight': bil_pack_parent_plan['total_weight'],
                                                'capacity': bil_pack_parent_plan['capacity'],
                                                'product_type_id': bil_pack_parent_plan['product_type_id'],
                                                'bill_package_id': bil_pack_parent_plan['bill_package_id'],
                                                'bill_lading_detail_id': bil_pack_parent_plan['bill_lading_detail_id'],
                                                'note': bil_pack_parent_plan['note'],
                                                'item_name': bil_pack_parent_plan['item_name'],
                                                'qr_char': bil_pack_parent_plan['qr_char'],
                                                'name': bil_pack_parent_plan['name'] + '_SOS_OLD',
                                                'gen_qr_check': bil_pack_parent_plan['gen_qr_check'],
                                                'routing_plan_day_id': end_routing_record['id']
                                            }
                                            new_old_car_plan_record = http.request.env[
                                                'sharevan.bill.package.routing.plan'].create(bil_pack_parent_plan_new)
                                            bil_pack_parent_new_car_plan_new = bil_pack_parent_plan_new
                                            bil_pack_parent_new_car_plan_new['routing_plan_day_id'] = new_routing_record['id']
                                            print('package_plan_new', bil_pack_parent_new_car_plan_new)
                                            bil_pack_parent_new_car_plan_new['name'] = bil_pack_parent_plan[
                                                                                           'name'] + '_SOS_NEW'
                                            new_car_package_plan_record = http.request.env[
                                                'sharevan.bill.package.routing.plan'].create(
                                                bil_pack_parent_new_car_plan_new)
                                        for bil_pack_parent_import in new_place_pack_import_old_car:
                                            if bil_pack_parent_plan['id'] == bil_pack_parent_import[
                                                'routing_package_plan']:
                                                quantity = bil_pack_parent_import['quantity_import']

                                                # Trù số lượng hàng đã xuất thực tế
                                                for bil_pack_child_export in bill_routing_package_child_plan_export:
                                                    if bil_pack_child_export['product_type_id'] == \
                                                            bil_pack_parent_import[
                                                                'product_type_id'] and bil_pack_child_export[
                                                        'length'] == \
                                                            bil_pack_parent_import['length'] \
                                                            and bil_pack_child_export['width'] == \
                                                            bil_pack_parent_import[
                                                                'width'] \
                                                            and bil_pack_child_export['height'] == \
                                                            bil_pack_parent_import[
                                                                'height']:
                                                        print('bil_pack_parent_import',
                                                              quantity)
                                                        print('bil_pack_child_export',
                                                              bil_pack_child_export['quantity_export'])
                                                    quantity = quantity - bil_pack_child_export['quantity_export']
                                                    capacity_expected = capacity_expected - bil_pack_child_export[
                                                        'quantity_export'] * bil_pack_child_export['total_weight']
                                                    if quantity > 0 and new_old_car_plan_record:
                                                        # thêm vào hàng hóa xuất tại kho sos cho lái xe cũ
                                                        bil_pack_new_export = {
                                                            'quantity_export': quantity,
                                                            'length': bil_pack_parent_plan['length'],
                                                            'width': bil_pack_parent_plan['width'],
                                                            'height': bil_pack_parent_plan['height'],
                                                            'total_weight': bil_pack_parent_plan['total_weight'],
                                                            'capacity': bil_pack_parent_plan['capacity'],
                                                            'product_type_id': bil_pack_parent_plan['product_type_id'],
                                                            'bill_package_id': bil_pack_parent_plan['bill_package_id'],
                                                            'bill_lading_detail_id': bil_pack_parent_plan[
                                                                'bill_lading_detail_id'],
                                                            'note': bil_pack_parent_plan['note'],
                                                            'item_name': bil_pack_parent_plan['item_name'],
                                                            'qr_char': bil_pack_parent_plan['qr_char'],
                                                            'routing_plan_day_id': end_routing_record['id'],
                                                            'routing_package_plan': new_old_car_plan_record['id']
                                                        }
                                                        print('bil_pack_old_export', bil_pack_new_export)
                                                        # tạo các package export mới cho xe cũ
                                                        old_car_export_record = http.request.env[
                                                            'sharevan.bill.package.routing.export'].create(
                                                            bil_pack_new_export)
                                                        # tạo các package import mới
                                                        bil_pack_parent_import['quantity_import'] = quantity
                                                        bil_pack_parent_import['name'] = bil_pack_parent_plan[
                                                                                             'name'] + '_SOS_NEW'
                                                        bil_pack_parent_import['routing_plan_day_id'] = \
                                                        new_routing_record['id']
                                                        bil_pack_parent_import['routing_package_plan'] = \
                                                        new_car_package_plan_record['id']
                                                        print('bil_pack_new_import', bil_pack_parent_import)
                                                        # tạo package import cho xe mơi
                                                        new_car_import_record = http.request.env[
                                                            'sharevan.bill.package.routing.import'].create(
                                                            bil_pack_parent_import)
                                if len(finish_routing_export) == 0:
                                    for plan in new_place_pack_plan_old_car:
                                        code = plan['name']
                                        plan['routing_plan_day_id'] = end_routing_record['id']
                                        plan['name'] = code + '_SOS_OLD'
                                        plan.pop('id')
                                        new_old_car_record = http.request.env[
                                            'sharevan.bill.package.routing.plan'].create(
                                            plan)
                                        plan['routing_plan_day_id'] = new_routing_record['id']
                                        print('plan_old_car', new_old_car_record)
                                        plan['name'] = code + '_SOS_NEW'
                                        new_plan_car_record = http.request.env[
                                            'sharevan.bill.package.routing.plan'].create(
                                            plan)
                                        print('plan_new_car', new_plan_car_record)
                                    for export in new_place_pack_import_old_car:
                                        export['routing_plan_day_id'] = new_routing_record['id']
                                        new_plan_car_record = http.request.env[
                                            'sharevan.bill.package.routing.import'].create(
                                            export)
                                        print('export_new_car', new_plan_car_record)
                                        export['routing_plan_day_id'] = end_routing_record['id']
                                        export.pop('id')
                                        quantity_export = export['quantity_import']
                                        export.pop('quantity_import')
                                        export.pop('routing_plan_code')
                                        export.pop('name')
                                        export['quantity_export'] = quantity_export
                                        new_old_car_record = http.request.env[
                                            'sharevan.bill.package.routing.export'].create(
                                            export)
                                        print('new_old_car_record',new_old_car_record)
                                # update routing plan export cũ theo id mới bên routing tự update chỉ gửi thông tin sang thôi
                                for routing_plan_old in new_routing_package_info:
                                    waiting_routing_plan_day_change.append(routing_plan_old)
                                #     update_query = """
                                #         UPDATE public.sharevan_routing_plan_day
                                #             SET driver_id = null ,vehicle_id = null
                                #         WHERE id = %s
                                #     """
                                #     self._cr.execute(update_query, (routing_plan_old,))
                                new_routing_record.write({'capacity_expected': capacity_expected})
                                end_routing_record.write({'capacity_expected': capacity_expected})
                            # update kho nhập khi chưa xuất bên routing tự update chỉ gửi routing sang thôi
                            if update_all == True and routing['type'] == '1':
                            #     update_query = """
                            #         UPDATE public.sharevan_routing_plan_day
                            #             SET driver_id = null ,vehicle_id = null
                            #         WHERE id = %s
                            #     """
                                waiting_routing_plan_day_change.append(routing['id'])
                            #     self._cr.execute(update_query, (routing['id'],))

                bill_routing_update = http.request.env['sharevan.bill.routing'].search(
                                        [('id', '=', bill_routing_id)])
                bill_routing_update.write({'status_routing':BillRoutingStatus.InClaim.value})
                print('send routing list sos routing',waiting_routing_plan_day_change)
                for routing_id in update_list_record:
                    update_query = """
                        UPDATE public.sharevan_routing_plan_day
                            SET driver_sos_id = %s 
                        WHERE id = %s
                    """
                    self._cr.execute(update_query, (str(sos_record_id),routing_id,))
            # Gửi thông báo đến nhà xe
            fleet_ids = BaseMethod.get_fleet_manager(driver_id)
            print(fleet_ids)
            if len(fleet_ids) > 0:
                title = 'SOS WARNING!'
                body = 'Van trouble in routing plan day! ' \
                       + sos_type_object['vehicle_id']
                item_id = sos_type_object['vehicle_id']
                try:
                    val = {
                        'user_id': fleet_ids,
                        'title': title,
                        'content': body,
                        'res_id': item_id,
                        'res_model': 'fleet.vehicle',
                        'click_action': ClickActionType.routing_plan_day_customer.value,
                        'message_type': MessageType.danger.value,
                        'type': NotificationType.SOS.value,
                        'object_status': RoutingDetailStatus.Done.value,
                        'item_id': item_id,
                    }
                    http.request.env[Notification._name].create(val)
                    notice = body
                    print(len(fleet_ids))
                    for user in fleet_ids:
                        users = self.env['res.users'].search(
                            [('id', '=', user)])
                        users.notify_info(message=notice, title=NotificationSocketType.NOTIFICATION.value)
                except:
                    logger.warn(
                        "Save sos warning Successful! But can not send message",
                        RoutingPlanDay._name, item_id,
                        exc_info=True)
            # Luôn gửi tin nhắn đến share van employee và customer employee

            vehicle= http.request.env['fleet.vehicle'].search([('id', '=', vehicle_id)])
            if vehicle:
                vehicle.write({'sos_status':sos_status})
            else:
                logger.warn(
                    "Can not find vehicle by id and update sos status",
                    FleetVehicle._name, vehicle_id,
                    exc_info=True)
            if len(company_ids) > 0:
                for rec in company_ids:
                    ids = []
                    customer_ids = BaseMethod.get_customer_employee(rec['company_id'], 'manager')
                    if len(customer_ids) > 0:
                        ids.extend(customer_ids)
                        title = 'SOS WARNING!'
                        code_warning = ''
                        for code in rec['bill_code']:
                            code_warning += code
                        body = 'Van trouble in routing plan day! ' \
                               + code_warning
                        item_id = rec['item_id']
                        try:
                            val = {
                                'user_id': ids,
                                'title': title,
                                'content': body,
                                'res_id': item_id,
                                'res_model': 'sharevan.bill.routing',
                                'click_action': ClickActionType.bill_routing_detail.value,
                                'message_type': MessageType.danger.value,
                                'type': NotificationType.SOS.value,
                                'object_status': RoutingDetailStatus.Done.value,
                                'item_id': item_id,
                            }
                            http.request.env[Notification._name].create(val)
                        except:
                            logger.warn(
                                "Save sos warning Successful! But can not send message",
                                RoutingPlanDay._name, item_id,
                                exc_info=True)
            elif so_check == True:
                # send message to mstore if routing delay for Z minutes
                # else routing monitor will send message after scanning new van
                if sos_type_object['continue_check']==True:
                    url = config['security_url'] + config['mstore_server_url'] + '/notification/deliveryDelay'
                    code_array =so_bill_code.split(',')
                    code_array=set(code_array)
                    try:
                        payload = {
                            "delayMinutes": sos_type_object['delay_time'],
                            'orderCodes': code_array
                        }
                        # {
                        #     "delayMinutes": 120,
                        #     "orderCodes": ["1113100627JXUVK", "1113100627JXUGF"]
                        # }

                        headers = {
                            'Authorization': 'Bearer ' + http.request.session['access_token']
                        }
                        resps = requests.get(url, json=payload, headers=headers, timeout=3)
                        print('mstore send message', resps.status_code)
                    except:
                        logger.warn(
                            "Send message fail to mstore delay time",
                            RoutingPlanDay._name, sos_type_object['routing_plan_day_id'],
                            exc_info=True)
                print('send request Mstore', so_bill_code)
            dlp_ids = BaseMethod.get_dlp_employee()
            if len(dlp_ids) > 0:
                title = 'SOS WARNING!'
                body = 'Van trouble in routing plan day! ' \
                       + str(vehicle_id)
                item_id = ''
                try:
                    val = {
                        'user_id': dlp_ids,
                        'title': title,
                        'content': body,
                        'res_id': item_id,
                        'res_model': 'fleet.vehicle',
                        'click_action': ClickActionType.bill_routing_detail.value,
                        'message_type': MessageType.danger.value,
                        'type': NotificationType.SOS.value,
                        'object_status': RoutingDetailStatus.Done.value,
                        'item_id': item_id,
                    }
                    http.request.env[Notification._name].create(val)
                    notice = body
                    print(len(dlp_ids))
                    for user in dlp_ids:
                        users = self.env['res.users'].search(
                            [('id', '=', user)])
                        users.notify_info(message=notice, title=NotificationSocketType.NOTIFICATION.value)
                except:
                    logger.warn(
                        "Save sos warning Successful! But can not send message",
                        RoutingPlanDay._name, item_id,
                        exc_info=True)
            return http.Response('Successful')
        else:
            raise ValidationError('Driver not assgin for vehicle today! Please check information again!')


class FleetVehicleResPartnerRel(models.Model):
    _name = Constants.PARTNER_VEHICLE
    _description = 'table many2many of fleet_vehicle and res_partner'
    vehicle_id = fields.Many2one(Constants.FLEET_VEHILCE, string='Vehicle')
    partner_id = fields.Many2one(Constants.RES_PARTNER, string='Partner')
    company_id = fields.Many2one(Constants.RES_COMPANY, string='Company')
    from_date = fields.Date('from date')
    to_date = fields.Date('to date')
    role_id = fields.Integer('role')
    specific_type = fields.Integer('Specific type')

    @api.onchange('partner_id')
    def _change_partner(self):
        for record in self:
            record.update({'company_id': record['partner_id'].company_id.id})
