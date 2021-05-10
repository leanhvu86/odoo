import json
import logging
from datetime import datetime
import numpy as np
import pytz
import requests
from mymodule.base_next.controllers.api.base_method import BaseMethod
from mymodule.base_next.controllers.api.file_controller import FileApi
from mymodule.enum.BillRoutingStatus import BillRoutingStatus
from mymodule.enum.ClickActionType import ClickActionType
from mymodule.enum.MessageType import MessageType, NotificationSocketType
from mymodule.enum.NotificationType import NotificationType
from mymodule.enum.ObjectStatus import ObjectStatus
from mymodule.enum.ReasonType import ReasonType
from mymodule.enum.RoutingDetailStatus import RoutingDetailStatus
from mymodule.enum.RoutingTroubleType import RoutingTroubleType
from mymodule.enum.VehicleStateStatus import VehicleStateStatus
from mymodule.enum.WarehouseType import WarehouseType
from mymodule.enum.StatusType import StatusType
from mymodule.enum.ShipType import ShipType
from odoo import api, models, fields, _, http
from odoo.exceptions import UserError, ValidationError
from mymodule.constants import Constants
from odoo.http import Response, request
from odoo.tools import config, date_utils
from ..MVR.main import Routing
from ..mvr_new.main import NewRouting

try:
    import qrcode
except ImportError:
    qrcode = None
try:
    import base64
except ImportError:
    base64 = None
from io import BytesIO

logger = logging.getLogger(__name__)


class RoutingPlanDay(models.Model):
    _name = 'sharevan.routing.plan.day'
    _description = 'all bill of lading by vehicle'

    routing_plan_day_code = fields.Char('Code', default='New', readonly=True)
    date_plan = fields.Date('Plan date')

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    driver_id = fields.Many2one('fleet.driver', string='Driver')
    latitude = fields.Float(string='Geo Latitude', digits=(9, 6))
    longitude = fields.Float(string='Geo Longitude', digits=(9, 6))
    address = fields.Text(string='Address')
    order_number = fields.Integer(help='Order number to run in routing')
    status = fields.Selection([('-1', 'Hủy đơn từ SO'),
                               ('0', 'Chưa xác nhận'),
                               ('1', 'Lái xe xác nhận'),
                               ('2', 'Khách hàng đã xác nhận'),
                               ('3', 'Đã hủy'),
                               ('4', 'Chờ xác nhận'),
                               ('5', 'Dự thảo')], 'Status', default='0', help='status bill of lading', required=True)
    trouble_type = fields.Selection(
        [('0', 'Normal'), ('1', 'Sos'),
         ('2', 'Retry'), ('3', 'Return'), ('4', 'Pick up fail'), ('5', 'Waiting confirm')],
        string='Trouble type', default='0', required=True)
    reason = fields.Selection(
        [('1', 'Customer not found'), ('2', 'Order package change'),
         ('3', 'Customer cancel'), ('4', 'System not satisfy')],
        string='Reason', required=True)
    bill_lading_detail_id = fields.Many2one('sharevan.bill.lading.detail', 'Bill of lading detail', required=True)
    capacity_expected = fields.Float('Capacity')
    expected_from_time = fields.Datetime('From time expected')
    expected_to_time = fields.Datetime('To time expected')
    actual_time = fields.Datetime('Actual time')
    warehouse_id = fields.Many2one('sharevan.warehouse', string='Warehouse')
    hub_id = fields.Many2one('sharevan.hub', string='Group area', help='Group area of warehouse')
    depot_id = fields.Many2one('sharevan.depot', string='Depot',
                               help='Depot info have two type: main type == True is Big Depot almost service for Codeshare,'
                                    ' main type == False is small hub service for In zone')
    to_depot_id = fields.Many2one('sharevan.depot', string='To', related="bill_lading_detail_id.depot_id", store=True, readonly=True)
    zone_area_id = fields.Many2one('sharevan.zone', string='Zone')
    wjson_address = fields.Char('address json', store=False)
    type = fields.Selection([('0', 'Kho xuất'), ('1', 'Kho nhập')], 'Type', default='0')
    stock_man_id = fields.Many2one('res.partner', 'Warehouseman')
    warehouse_name = fields.Char('Warehouse Name')
    bill_lading_detail_code = fields.Char('Origin bill code')
    phone = fields.Char('Warehouse Phone')
    rating_id = fields.Many2one('sharevan.rating', string='Rating driver')
    rating_badges = fields.Many2many('sharevan.rating.badges', string='')
    confirm_time = fields.Datetime(' update when status = 1')
    accept_time = fields.Datetime('Customer accepted')
    # qr_code = fields.Image("Image", max_width=512, max_height=512)
    due_time = fields.Datetime('Due time')
    ready_time = fields.Datetime('Ready time')
    partner_id = fields.Many2one('res.partner', string="Booking customer")
    next_id = fields.Char('next id')
    toogle = fields.Boolean('toogle', default=False)
    qr_gen_check = fields.Boolean('qr_gen_check', default=False)
    previous_id = fields.Char('previous id')
    company_id = fields.Many2one('res.company', string="Company")
    warning_new_order = fields.Integer('Phát sinh đơn hàng', store=False)
    attach_image = fields.Many2many('ir.attachment', string="Attach Image")
    description = fields.Text(string='Description')
    ship_type = fields.Selection([('0', 'Trong zone'), ('1', 'Long haul')], 'Ship Type', default='0')
    insurance_name = fields.Char('Insurance')
    insurance_id = fields.Many2one('sharevan.insurance', 'Insurance')
    service_ids = fields.One2many('sharevan.routing.plan.day.service', 'routing_plan_day_id', string='Service Type')
    sos_ids = fields.One2many('sharevan.driver.sos', 'routing_plan_day_id', string='Sos Type')
    bill_package_routing_import_line = fields.One2many('sharevan.bill.package.routing.import',
                                                       'routing_plan_day_id',
                                                       'Routing plan day import')
    bill_package_routing_export_line = fields.One2many('sharevan.bill.package.routing.export',
                                                       'routing_plan_day_id',
                                                       'Routing plan day export')
    rating_customer_id = fields.Many2one('sharevan.rating.customer', 'Rating customer')
    from_routing_plan_day_id = fields.Integer('from routing plan day id')
    qr_so = fields.Char('QR SO')
    assess_amount = fields.Float('Temporary price')
    solution_day_id = fields.Many2one('solution.day', 'Solution day id')
    so_type = fields.Boolean('SO type', default=False)
    rating_customer = fields.Boolean('Rating customer', default=False)
    first_rating_customer = fields.Boolean('Check rating customer', default=False)
    check_point = fields.Boolean('Send check point', default=False)
    arrived_check = fields.Boolean('Send arrived check', default=False)
    num_receive = fields.Integer('Num receive', default=0)
    packaged_cargo = fields.Char('Package cargo', default='0')
    driver_sos_id = fields.Many2one('sharevan.driver.sos', 'driver sos')
    total_package = fields.Integer('Total Package')
    max_tonnage_shipping = fields.Float('Max tonnage vehicle shipping')

    # fields.Selection([('0', 'In routing'),
    #                                         ('1', 'Waiting package'),
    #                                         ('2', 'Packaged'),
    #                                         ('3', 'Unpackaged')], 'Package cargo',
    #                                        default='0')

    @api.depends('toogle')
    def gen_qr_code_web(self):
        if self.type == '1':
            self.qr_gen_check = True
            return self
        query = """
                select  distinct package.id,plan.ship_type, package.qr_char,package.quantity from sharevan_routing_plan_day plan
                    join sharevan_bill_package_routing_plan package on package.routing_plan_day_id = plan.id
                where plan.id = %s and plan.type = '0'
            """
        self.env.cr.execute(query, (self['id'],))
        get_qr_record = self._cr.dictfetchall()
        if get_qr_record:
            for record in get_qr_record:
                if record['ship_type'] == '1':
                    raise ValidationError('you can get QR from here')
                record = self.env['sharevan.bill.package.routing.plan'].search([('id', '=', record['id'])])
                if record:
                    if record['gen_qr_check'] == False and int(record['quantity']) < 500:
                        qr_code_new = ''
                        count = 1
                        while True:
                            if record['quantity'] > count or record['quantity'] == count:
                                qr_code_new += record['qr_char'] + '_' + str(count) + ','
                                count += 1
                            else:
                                qr_code_new = qr_code_new[:-1]
                                break
                        record.write({'qr_char': qr_code_new, 'gen_qr_check': True})
                else:
                    raise ValidationError('Routing package not found or quantity more than 500 ')
            result = self.env['sharevan.routing.plan.day'].search([('id', '=', self.id)])
            result.write({'qr_gen_check': True})
            return result
        else:
            raise ValidationError('Routing plan export not found')

    def open_control_routing(self):
        result = self.env['sharevan.routing.request'].search([('routing_plan_day_id', '=', self.id)])
        if result:
            if result.user_id.id != self.env.uid:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Check bill',
                    'view_mode': 'form',
                    'res_model': 'sharevan.routing.request',
                    'res_id': result.id,
                    'target': 'new',
                    'context': {
                        'form_view_initial_mode': 'read',
                    },
                }
            else:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Check bill',
                    'view_mode': 'form',
                    'res_model': 'sharevan.routing.request',
                    'res_id': result.id,
                    'target': 'new',
                    'context': {
                        'form_view_initial_mode': 'edit',
                    },
                }
        else:
            type = False
            if self.type == '0':
                type = True
            vals = {
                'user_id': self.env.uid,
                'routing_plan_day_id': self.id,
                'bill_routing_id': self.bill_routing_id.id,
                'type': type,
            }
            result = self.env['sharevan.routing.request'].create(vals)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Check bill',
                'view_mode': 'form',
                'res_model': 'sharevan.routing.request',
                'res_id': result.id,
                'target': 'new',
                'context': {
                    'form_view_initial_mode': 'edit',
                },
            }

    def write(self, vals):
        count1 = 0
        count2 = 0
        if 'routing_plan_day_detail_line' in vals:
            for detail in vals['routing_plan_day_detail_line']:
                var = detail[2]
                if var and 'status' in var and var['status'] == '3':
                    count1 += 1
            for detail in self.routing_plan_day_detail_line:
                if detail.status == '3':
                    count2 += 1
        if count1 > 0 and count1 + count2 == len(self.routing_plan_day_detail_line):
            vals['status'] = '3'

        # if qrcode and base64:
        #     if 'routing_plan_day_code' not in self:
        #         vals['routing_plan_day_code'] = self.env['ir.sequence'].next_by_code(
        #             'self.routing.plan.day.code') or 'New'
        #     if 'qr_code' not in self or self.qr_code is False:
        #         vals['qr_code'] = FileApi.build_qr_code(self['routing_plan_day_code'])
        # else:
        #     raise UserError(_('Necessary Requirements To Run This Operation Is Not Satisfied'))
        res = super(RoutingPlanDay, self).write(vals)
        return res

    def generate_qr(self):
        if qrcode and base64:
            if not self.routing_plan_day_code:
                prefix = str(
                    self.env['ir.config_parameter'].sudo().get_param('customer_product_qr.config.customer_prefix'))
                if not prefix:
                    raise UserError(_('Set A Customer Prefix In General Settings'))
                self.routing_plan_day_code = prefix + self.env['ir.sequence']. \
                    next_by_code('self.routing.plan.day.code') or '/'
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(self.routing_plan_day_code)
            qr.make(fit=True)

            img = qr.make_image()
            temp = BytesIO()
            img.save(temp, format="PNG")
            qr_image = base64.b64encode(temp.getvalue())
            self.write({'qr_code': qr_image})
        else:
            raise UserError(_('Necessary Requirements To Run This Operation Is Not Satisfied'))

    def driver_send_routing_comming_notification(self, routing_plan_day_id):
        query = """
            select partner.user_id, plan.so_type,depot_id,warehouse_id,plan.company_id, 
                routing_plan_day_code,warehouse_name, plan.qr_so
                from sharevan_routing_plan_day plan
            join res_partner partner on partner.id = plan.partner_id 
            join fleet_driver driver on driver.id = plan.driver_id
                where plan.id = %s and driver.user_id =%s;
        """
        self.env.cr.execute(query, (routing_plan_day_id, http.request.env.uid,))
        routingPlan = self._cr.dictfetchall()
        response_data = {}
        if routingPlan and routingPlan[0]:
            record = self.env['sharevan.routing.plan.day'].search([('id', '=', routing_plan_day_id)])
            if record['check_point'] == True:
                return 201
            record.write({
                'check_point': True,
                'actual_time': datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")
            })
            if routingPlan[0]['so_type'] == False:
                user_ids = []
                user_ids.append(routingPlan[0]['user_id'])
                if routingPlan[0]['warehouse_id'] and routingPlan[0]['depot_id'] and routingPlan[0]['company_id']:
                    query = """
                        SELECT res.id  FROM public.res_users res where res.company_id = %s and active = True
                            """
                    self.env.cr.execute(query, (routingPlan[0]['company_id'],))
                    users = self._cr.dictfetchall()
                    for user in users:
                        user_ids.append(user['id'])
                elif not routingPlan[0]['warehouse_id'] and routingPlan[0]['depot_id'] and routingPlan[0]['company_id']:
                    query = """
                        SELECT user_id  FROM public.sharevan_employee_warehouse res 
                            where place_id = %s 
                                and place_type ='1' and date_assign = CURRENT_DATE;
                                                """
                    self.env.cr.execute(query, (routingPlan[0]['depot_id'],))
                    users = self._cr.dictfetchall()
                    for user in users:
                        user_ids.append(user['user_id'])
                title = 'Driver is comming ' + routingPlan[0]['warehouse_name']
                body = 'Driver is comming ' + routingPlan[0]['warehouse_name'] + ' for ' + routingPlan[0][
                    'routing_plan_day_code']
                item_id = routingPlan[0]['routing_plan_day_code']
                try:
                    val = {
                        'user_id': user_ids,
                        'title': title,
                        'content': body,
                        'click_action': ClickActionType.routing_plan_day_customer.value,
                        'message_type': MessageType.success.value,
                        'type': NotificationType.RoutingMessage.value,
                        'object_status': RoutingDetailStatus.Unconfimred.value,
                        'item_id': item_id,
                    }
                    http.request.env['sharevan.notification'].create(val)
                    return 200
                except:
                    logger.warn(
                        "Send message fail",
                        RoutingPlanDay._name, item_id,
                        exc_info=True)
                    return 200
            elif routingPlan[0]['so_type'] == True:
                url = config['security_url'] + config['mstore_server_url'] + '/notification/push/order-dlp'
                try:
                    payload = {
                        'username': http.request.session['login'],
                        'orderCode': routingPlan[0]['qr_so']
                    }
                    # 'orderCode' : 108518265905870
                    headers = {
                        'Authorization': 'Bearer ' + http.request.session['access_token']
                    }
                    resps = requests.get(url, params=payload, headers=headers, timeout=3)
                    print('mstore send message', resps.status_code)
                except:
                    logger.warn(
                        "Send message fail to mstore",
                        RoutingPlanDay._name, routingPlan[0]['qr_so'],
                        exc_info=True)
                    return 500
                return 200
        else:
            return 500

    def notify_change_routing_plan(self, vehicle_id, driver_id, new_driver_id):
        try:
            vehicle = self.env['fleet.vehicle'].search_read(domain=[('id', '=', vehicle_id)])
            dlp_employee = BaseMethod.get_dlp_employee()
            if dlp_employee:
                notice = 'Changing of routing is cancel. Customer have cancel routing !'
                content = {
                    'title': 'Routing cancel for change',
                    'content': notice,
                    'type': NotificationType.SOS.value,
                    'res_id': '',
                    'res_model': 'fleet.vehicle',
                    'click_action': ClickActionType.routing_plan_day_driver.value,
                    'message_type': MessageType.warning.value,
                    'user_id': dlp_employee,
                }
                self.env['sharevan.notification'].sudo().create(content)
                list_employee = self.env['res.users'].search([('id', 'in', dlp_employee)])
                for emp in list_employee:
                    emp.notify_info(message=notice, title=NotificationSocketType.NOTIFICATION.value)
            f_manager = BaseMethod.get_fleet_manager(driver_id)
            if f_manager:
                notice = 'Changing of routing is cancel. Customer have cancel routing!'
                content = {
                    'title': 'Routing cancel for change',
                    'content': notice,
                    'type': NotificationType.SOS.value,
                    'res_id': '',
                    'res_model': 'fleet.vehicle',
                    'click_action': ClickActionType.routing_plan_day_driver.value,
                    'message_type': MessageType.warning.value,
                    'user_id': f_manager,
                }
                self.env['sharevan.notification'].sudo().create(content)
                manager = self.env['res.users'].search([('id', 'in', f_manager)])
                for mng in manager:
                    mng.notify_info(message=notice, title=NotificationSocketType.NOTIFICATION.value)
            driver = self.env['fleet.driver'].search_read(domain=[('id', '=', driver_id)])
            if driver and len(driver) > 0:
                content = {
                    'title': 'Routing cancel for change',
                    'content': "Your routing is changed",
                    'type': NotificationType.SOS.value,
                    'res_id': '',
                    'res_model': 'fleet.vehicle',
                    'click_action': ClickActionType.routing_plan_day_driver.value,
                    'message_type': MessageType.warning.value,
                    'user_id': driver.user_id,
                }
                self.env['sharevan.notification'].sudo().create(content)
            new_driver = self.env['fleet.driver'].search_read(domain=[('id', '=', new_driver_id)], fields=['user_id'])
            if new_driver and len(new_driver) > 0:
                content = {
                    'title': 'Routing cancel for change',
                    'content': "A routing was changed and assigned to you",
                    'type': NotificationType.SOS.value,
                    'res_id': '',
                    'res_model': 'fleet.vehicle',
                    'click_action': ClickActionType.routing_plan_day_driver.value,
                    'message_type': MessageType.warning.value,
                    'user_id': new_driver.user_id,
                }
                self.env['sharevan.notification'].sudo().create(content)
            return 200
        except:
            return 500

    def notify_customer_change_routing(self, order_code, vehicle_id, new_driver_id, company_id, type, title, body):
        if type == 'mfunction':
            url = config['security_url'] + config['mstore_server_url'] + 'notification/changeDriver'
            new_driver = self.env['fleet.driver'].search(args=[('id', '=', new_driver_id)])
            if not new_driver:
                raise ValidationError("Invalid driver")
            vehicle = self.env['fleet.vehicle'].search(args=[('id', '=', vehicle_id)])
            if not vehicle:
                raise ValidationError("Invalid vehicle")
            try:
                payload = {
                    "driverName": new_driver.name,
                    'phone': new_driver.phone,
                    'licensePlate': vehicle.license_plate,
                    'orderCodes': order_code
                }
                headers = {
                    'Authorization': 'Bearer ' + http.request.session['access_token']
                }
                resps = requests.get(url, json=payload, headers=headers, timeout=3)
                print('mstore send message', resps.status_code)
            except:
                logger.warn(
                    "Send message fail to mstore delay time",
                    RoutingPlanDay._name, new_driver['name'],
                    exc_info=True)
        else:
            list_ids = http.request.env['res.users'].search_read([('company_id', '=', company_id)], fields=['id'])
            if len(list_ids) == 0:
                raise ValidationError("Invalid company")
            http.request.env['res.users'].send_notis_web(list_ids, title, body)

    def notify_no_routing_replacement(self):
        pass
    def get_location(self,code, locationLst):
        for item in locationLst:
            if item['code'] == code:
                return item
        return None

    def routing_mstore_new(self, date_plan):
        time_now = datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")
        # get routing plan day
        query = """(select * from sharevan_routing_plan_day
                           where date_plan = to_date(%s,'dd/mm/yyyy')
                           and so_type = %s
                           and ship_type = %s
                           and status = %s
                           and type = %s limit 1)
                       union all
                       (select * from sharevan_routing_plan_day
                       where date_plan = to_date(%s,'dd/mm/yyyy')
                       and so_type = %s
                       and ship_type = %s
                       and status = %s
                       and type = %s) """
        self._cr.execute(query, (
        date_plan, False, ShipType.IN_ZONE.value, RoutingDetailStatus.Unconfimred.value, WarehouseType.Import.value,
        date_plan, False, ShipType.IN_ZONE.value, RoutingDetailStatus.Unconfimred.value, WarehouseType.Export.value,))
        routingPlanList = self._cr.dictfetchall()
        if routingPlanList is None or len(routingPlanList) == 0:
            return None
        matrixDistance = list()
        demandArr = list()
        capacityArr = list()
        matrixMaxTonage = list()
        latitudeStr = ''
        longitudeStr = ''
        for item1 in routingPlanList:
            print(item1)
            latitudeStr += str(round(item1['latitude'], 3)) + ','
            longitudeStr += str(round(item1['longitude'], 3)) + ','
            capacity = item1['capacity_expected']
            if item1['type'] == WarehouseType.Import.value:
                capacity = 0
            if capacity < 0:
                capacity = capacity * (-1)
            demandArr.append(capacity)
        print('################################################')
        latitudeStr = latitudeStr[:-1]
        longitudeStr = longitudeStr[:-1]
        lstLocation = http.request.env['location.data'].get_lstLocation_by_lstlat_and_lstlng(latitudeStr, longitudeStr)
        for item1 in routingPlanList:
            row = list()
            for item2 in routingPlanList:
                f_lat = round(item1['latitude'], 3)
                f_lon = round(item1['longitude'], 3)
                t_lat = round(item2['latitude'], 3)
                t_lon = round(item2['longitude'], 3)
                code = 'FLAT' + str(f_lat) + '-FLON' + str(f_lon) + 'TLAT' + str(t_lat) + '-TLON' + str(t_lon)
                location = self.get_location(code, lstLocation)
                if location is None:
                    location = FileApi.get_distance_time(f_lat, f_lon, t_lat, t_lon, None)
                    if location is not None:
                        lstLocation.append(location)
                if location is not None:
                    row.append(location['cost'])
                else:
                    row.append(0.0)
            matrixDistance.append(row)
        print(matrixDistance)
        # get list fleet
        query = """select fv.*   
                        from Fleet_Vehicle fv  
                        join Fleet_Vehicle_State fvs on fvs.id = fv.state_Id  
                        where fv.active = true and fvs.code  in ('AVAILABLE')  
                        and fv.capacity > 0 and fv.capacity is not null and fv.company_Id = 1 and fv.active_Type = 'fleet'  
                        and fv.capacity < 10000
                        AND  EXISTS (select 1  
                              from Fleet_Vehicle_Assignation_Log al  
                              where al.vehicle_Id = fv.id  
                             and al.status = %s  
                           --  and al.driver_Status = '1'  
                             and al.date_start = to_date(%s,'dd/mm/yyyy'))  
                        AND NOT EXISTS (select 1   
                              from sharevan_Routing_Plan_Day rpd  
                              where rpd.vehicle_Id = fv.id  
                              and rpd.status in ('0','5')  
                              and rpd.date_Plan = to_date(%s,'dd/mm/yyyy'))"""
        self._cr.execute(query, (StatusType.Running.value, date_plan, date_plan,))
        vehicleLst = self._cr.dictfetchall()
        if vehicleLst is None or len(vehicleLst) == 0:
            return None
        for v in vehicleLst:
            capacityArr.append(v['capacity'])
        max_value = np.max(capacityArr)
        for i in range(len(matrixDistance)):
            row = list()
            for j in range(len(matrixDistance)):
                row.append(max_value)
            matrixMaxTonage.append(row)

        # call mvr
        matrixMaxTonage = np.array(matrixMaxTonage)
        matrixDistance = np.array(matrixDistance)
        demandArr = np.array(demandArr)
        capacityArr = np.array(capacityArr)
        print('-----------------------------------------------')
        print(capacityArr)
        print('-----------------------------------------------')
        print('demandArr')
        print(demandArr)
        print('--------------------------------')
        print(matrixMaxTonage)
        lstRouting, noise, noiseSaving  = NewRouting.main(self, matrixDistance, matrixMaxTonage, demandArr, capacityArr)
        print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^')

        for item in lstRouting:
            print('//',item['rout'])
            rout = item['rout']
            j = 1
            for i in rout:
                path = '{lat: ' + str(routingPlanList[i]['latitude']) + ', lng: ' + str(routingPlanList[i]['longitude']) + ', name: "' + str(j) +  '", capacity: "'+ str(demandArr[i])  +', vehicle: ' + str(item['vehicle']) + ', cap: ' +str(item['capacity'])+ ',lat:' + str(routingPlanList[i]['latitude']) + ', lng:' + str(routingPlanList[i]['longitude'])  + '"},'
                j = j + 1
                print(path)

        print('noise dbscan: ', noise)
        j = 1;

        for i in noise:
            path = '{lat: ' + str(routingPlanList[i]['latitude']) + ', lng: ' + str(routingPlanList[i]['longitude']) + ', name: "' + str(j) + '", capacity: "' + str(demandArr[i]) + ',lat:' + str(routingPlanList[i]['latitude']) + ', lng:' + str(routingPlanList[i]['longitude']) + '"},'
            j = j + 1
            print(path)
        print('noise saving: ', noiseSaving)
        j = 1
        for i in noiseSaving:
            path = '{lat: ' + str(routingPlanList[i]['latitude']) + ', lng: ' + str(routingPlanList[i]['longitude']) + ', name: "' + str(j) + '", capacity: "' + str(demandArr[i]) + ',lat:' + str(routingPlanList[i]['latitude']) + ', lng:' + str(routingPlanList[i]['longitude']) + '"},'
            j = j + 1
            print(path)
    def routing_mstore(self,date_plan):
        time_now = datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")
        #get routing plan day
        query = """(select * from sharevan_routing_plan_day
                        where date_plan = to_date(%s,'dd/mm/yyyy')
                        and so_type = %s
                        and ship_type = %s
                        and status = %s
                        and type = %s limit 1)
                    union all
                    (select * from sharevan_routing_plan_day
                    where date_plan = to_date(%s,'dd/mm/yyyy')
                    and so_type = %s
                    and ship_type = %s
                    and status = %s
                    and type = %s) """
        self._cr.execute(query,(date_plan,False,ShipType.IN_ZONE.value,RoutingDetailStatus.Unconfimred.value,WarehouseType.Import.value,
                                date_plan,False,ShipType.IN_ZONE.value,RoutingDetailStatus.Unconfimred.value,WarehouseType.Export.value,))
        routingPlanList = self._cr.dictfetchall()
        if routingPlanList is None or len(routingPlanList) == 0:
            return None
        matrixDistance = list()
        demandArr = list()
        capacityArr = list()
        matrixMaxTonage = list()
        latitudeStr = ''
        longitudeStr = ''
        for item1 in routingPlanList:
            print(item1)
            latitudeStr += str(round(item1['latitude'],3)) + ','
            longitudeStr += str(round(item1['longitude'],3)) + ','
            capacity = item1['capacity_expected']
            if item1['type'] == WarehouseType.Import.value:
                capacity = 0
            if capacity < 0:
                capacity = capacity*(-1)
            demandArr.append(capacity)
        print('################################################')
        latitudeStr = latitudeStr[:-1]
        longitudeStr = longitudeStr[:-1]
        lstLocation = http.request.env['location.data'].get_lstLocation_by_lstlat_and_lstlng(latitudeStr,longitudeStr)
        for item1 in routingPlanList:
            row = list()
            for item2 in routingPlanList:
                f_lat = round(item1['latitude'],3)
                f_lon = round(item1['longitude'],3)
                t_lat = round(item2['latitude'],3)
                t_lon = round(item2['longitude'],3)
                code = 'FLAT' + str(f_lat) + '-FLON' + str(f_lon) + 'TLAT' + str(t_lat) + '-TLON' + str(t_lon)
                location = self.get_location(code,lstLocation)
                if location is None:
                    location = FileApi.get_distance_time(f_lat,f_lon,t_lat,t_lon, None)
                    if location is not None:
                        lstLocation.append(location)
                if location is not None:
                    row.append(location['cost'])
                else:
                    row.append(0.0)
            matrixDistance.append(row)
        print(matrixDistance)
        #get list fleet
        query = """select fv.*   
                     from Fleet_Vehicle fv  
                     join Fleet_Vehicle_State fvs on fvs.id = fv.state_Id  
                     where fv.active = true and fvs.code  in ('AVAILABLE')  
                     and fv.capacity > 0 and fv.capacity is not null and fv.company_Id = 1 and fv.active_Type = 'fleet'  
                     and fv.capacity < 10000
                     AND  EXISTS (select 1  
                           from Fleet_Vehicle_Assignation_Log al  
                           where al.vehicle_Id = fv.id  
                          and al.status = %s  
                       --   and al.driver_Status = '1'  
                          and al.date_start = to_date(%s,'dd/mm/yyyy'))  
                     AND NOT EXISTS (select 1   
                           from sharevan_Routing_Plan_Day rpd  
                           where rpd.vehicle_Id = fv.id  
                           and rpd.status in ('0','5')  
                           and rpd.date_Plan = to_date(%s,'dd/mm/yyyy'))"""
        self._cr.execute(query,(StatusType.Running.value,date_plan,date_plan,))
        vehicleLst = self._cr.dictfetchall()
        if vehicleLst is None or len(vehicleLst) == 0:
            return None
        for v in vehicleLst:
            capacityArr.append(v['capacity'])
        max_value = np.max(capacityArr)
        for i in range(len(matrixDistance)):
            row = list()
            for j in range(len(matrixDistance)):
                row.append(max_value)
            matrixMaxTonage.append(row)

        #call mvr
        matrixMaxTonage = np.array(matrixMaxTonage)
        matrixDistance = np.array(matrixDistance)
        demandArr = np.array(demandArr)
        capacityArr = np.array(capacityArr)
        print('-----------------------------------------------')
        print(capacityArr)
        print('-----------------------------------------------')
        print('demandArr')
        print(demandArr)
        print('--------------------------------')
        print(matrixMaxTonage)
        lstRouting,noise,noiseSaving = Routing.main(self,matrixDistance,matrixMaxTonage,demandArr,capacityArr)
        print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^')

        for item in lstRouting:
            print('//',item['rout'])
            rout = item['rout']
            j = 1
            for i in rout:
                path = '{lat: ' + str(routingPlanList[i]['latitude']) + ', lng: ' + str(routingPlanList[i]['longitude']) + ', name: "' + str(j) +  '", capacity: "'+ str(demandArr[i])  +', vehicle: ' + str(item['vehicle']) + ', cap: ' +str(item['capacity'])+ ',lat:' + str(routingPlanList[i]['latitude']) + ', lng:' + str(routingPlanList[i]['longitude'])  + '"},'
                j = j + 1
                print(path)

        print('noise dbscan: ', noise)
        j = 1;
        for i in noise:
            path = '{lat: ' + str(routingPlanList[i]['latitude']) + ', lng: ' + str(routingPlanList[i]['longitude']) + ', name: "' + str(j) + '", capacity: "' + str(demandArr[i]) + ',lat:' + str(routingPlanList[i]['latitude']) + ', lng:' + str(routingPlanList[i]['longitude']) + '"},'
            j = j + 1
            print(path)
        print('noiseSaving: ', noiseSaving)
        j = 1;
        for i in noiseSaving:
            path = '{lat: ' + str(routingPlanList[i]['latitude']) + ', lng: ' + str(
                routingPlanList[i]['longitude']) + ', name: "' + str(j) + '", capacity: "' + str(
                demandArr[i]) + ',lat:' + str(routingPlanList[i]['latitude']) + ', lng:' + str(
                routingPlanList[i]['longitude']) + '"},'
            j = j + 1
            print(path)
class RoutingPlanDayService(models.Model):
    _name = 'sharevan.routing.plan.day.service'
    _description = ' routing plan day service'

    billading_detail_id = fields.Many2one('sharevan.bill.lading.detail', 'Bill of lading detail')
    routing_plan_day_id = fields.Many2one('sharevan.routing.plan.day', 'Routing plan day')
    service_id = fields.Many2one('sharevan.service.type', 'service')
    name = fields.Char('Services', related="service_id.name")
    assign_partner_id = fields.Many2one('res.partner', 'Assign Employee')
    type = fields.Selection([('0', 'Kế hoạch'),
                             ('1', 'Phát sinh')], default='0')


class Rating(models.Model):
    _name = 'sharevan.rating'
    _description = 'Routing rate driver'
    MODEL = 'sharevan.rating'


    rating_place_id = fields.Integer('rating_place_id')
    # fix
    driver_id = fields.Many2one('fleet.driver', string='Bidding Order')
    num_rating = fields.Integer('num_rating')
    employee_id = fields.Many2one('res.partner', ' infor rating person')
    note = fields.Text('note')
    rating_badges_id = fields.Many2many('sharevan.rating.badges', string='Rating badges')
    bidding_vehicle_id = fields.Many2one(Constants.SHAREVAN_BIDDING_VEHICLE, string='Bidding vehicle')
    bidding_order_id = fields.Many2one(Constants.SHAREVAN_BIDDING_ORDER, string='Bidding Order')
    type = fields.Selection(
        [('ROUTING', 'Routing'),
         ('BIDDING', 'Bidding')
         ],
        string='Type', default='ROUTING', required=True)


class AwardLevel(models.Model):
    _name = 'sharevan.awards.level'
    _description = 'sharevan awards level'
    MODEL = 'sharevan.awards.level'

    name = fields.Char('Name')
    code = fields.Char(string='Code', required=True, copy=False, readonly=True,
                       index=True,
                       default=lambda self: _('New'))
    status = fields.Selection(
        [('running', 'Running'),
         ('deleted', 'Deleted')
         ],
        string='Status', context={'status': 'running'}, default='running', required=True)
    image_128 = fields.Image("Logo", max_width=128, max_height=128, required=True)
    title_ward_id = fields.Many2one('sharevan.title.award', string='Title ward id')
    amount = fields.Float('Amount')
    vendor_id = fields.Many2one('sharevan.vendor', string='Vendor', required=True,
                                domain=lambda self: "[('status','=','running')]", )

    @api.model
    def create(self, vals):
        if vals.get('name_seq', 'New') == 'New':
            seq = BaseMethod.get_new_sequence('sharevan.awards.level', 'SAL', 6, 'code')
            vals['code'] = seq
        # name_check = vals['name'].upper()
        # code_array = name_check.split(' ')
        # s = "_"
        # s = s.join(code_array)
        # vals['code'] = s
        result = super(AwardLevel, self).create(vals)
        return result

    @api.constrains('amount')
    def onchange_amount(self):
        for record in self:
            if record['amount'] <= 0:
                raise ValidationError('Amount is bigger than 0 !')


class TitleAward(models.Model):
    _name = 'sharevan.title.award'
    _description = 'title award driver'
    MODEL = _name

    @api.onchange('percent_commission_value')
    def onchange_percent_commission_value(self):
        for record in self:
            if record['percent_commission_value'] != 0.0:
                if record['percent_commission_value'] >= 1:
                    raise ValidationError('percent commission value is smaller than 1 !')
                if record['percent_commission_value'] <= 0:
                    raise ValidationError('percent commission value is greater than 0 !')

    @api.onchange('from_point', 'title_award_type')
    def onchange_from_point(self):
        for record in self:
            check = True
            lst_award = self.env['sharevan.title.award'].search(
                [('status', '=', 'running'), ('title_award_type', '=', record['title_award_type'])])
            mapp_level_string = ''
            if record['from_point'] < 0:
                record.update({'from_point': 0})
                notice = "From point is not small than 0 !"
                # user = self.env['res.users'].search(
                #     [('id', '=', self.env.uid)])
                self.env.user.notify_danger(message=notice, title=NotificationSocketType.NOTIFICATION.value)
            for award in lst_award:
                if record['id'].origin != award['id']:
                    if record['from_point'] >= award['from_point'] and record['from_point'] <= award['to_point']:
                        check = False
                    mapp_level_string += award['name'] + ' ' + str(award['from_point']) + '-' + str(
                        award['to_point']) + ', '
            if check == False:
                record.update({'from_point': 0})
                record.update({'to_point': 0})
                record.update({'title_award_type': False})
                notice = 'Title award mapping does not matching: ' + mapp_level_string + ' check againt please!'
                # user = self.env['res.users'].search(
                #     [('id', '=', self.env.uid)])
                self.env.user.notify_danger(message=notice, title=NotificationSocketType.NOTIFICATION.value)

    @api.onchange('to_point', 'title_award_type')
    def onchange_to_point(self):
        for record in self:
            check = True
            if record['to_point'] and record['to_point'] < 0:
                record.update({'to_point': 0})
                notice = "To point is not small than 0 !"
                # user = self.env['res.users'].search(
                #     [('id', '=', self.env.uid)])
                self.env.user.notify_danger(message=notice, title=NotificationSocketType.NOTIFICATION.value)
            if record['to_point'] > 0:
                if record['from_point'] >= record['to_point']:
                    record.update({'to_point': 0})
                    notice = "From point is smaller than to point !"
                    # user = self.env['res.users'].search(
                    #     [('id', '=', self.env.uid)])
                    self.env.user.notify_danger(message=notice, title=NotificationSocketType.NOTIFICATION.value)
                lst_award = self.env['sharevan.title.award'].search(
                    [('status', '=', 'running'), ('title_award_type', '=', record['title_award_type'])])
                mapp_level_string = ''
                for award in lst_award:
                    if record['id'].origin != award['id']:
                        if record['from_point'] >= award['from_point'] and record['from_point'] <= award['to_point']:
                            check = False
                        elif record['to_point'] >= award['from_point'] and record['to_point'] <= award['to_point']:
                            check = False
                        mapp_level_string += award['name'] + ' ' + str(award['from_point']) + '-' + str(
                            award['to_point']) + ', '
                if check == False:
                    record.update({'to_point': 0})
                    record.update({'title_award_type': False})
                    notice = 'Title award mapping does not matching: ' + mapp_level_string + ' check againt please!'
                    # user = self.env['res.users'].search(
                    #     [('id', '=', self.env.uid)])
                    self.env.user.notify_danger(message=notice, title=NotificationSocketType.NOTIFICATION.value)

    name = fields.Char('Name', required=True)
    code = fields.Char(string='Rating code', required=True, copy=False, readonly=True,
                       index=True,
                       default=lambda self: _('New'))
    status = fields.Selection(
        [('running', 'Running'),
         ('deleted', 'Deleted')
         ],
        string='Status', context={'status': 'running'}, default='running', required=True)
    title_award_type = fields.Selection(
        [('driver', 'Driver'),
         ('employee', 'Employee'),
         ('customer', 'Customer')
         ],
        string='Title award type', required=True)
    percent_commission_value = fields.Float(string='Percent commission', required=True)
    description = fields.Html('Body', default=' ')
    image_128 = fields.Image("Logo", max_width=128, max_height=128, required=True)
    from_point = fields.Integer('From point', default=0, required=True)
    to_point = fields.Integer('To point', default=0, required=True)
    awards_level_line = fields.Many2many('sharevan.awards.level', string='Awards level',
                                         domain=lambda self: "[('status','=','running')]",
                                         copy=True)

    @api.model
    def create(self, vals):
        if vals['percent_commission_value'] >= 1:
            raise ValidationError('percent commission value is smaller than 1 !')
        if vals.get('code', 'New') == 'New':
            vals['code'] = self.env['ir.sequence'].next_by_code(
                'self.sharevan.title.award') or 'New'
        result = super(TitleAward, self).create(vals)
        return result

    def write(self, vals):
        if 'percent_commission_value' in vals and vals['percent_commission_value'] >= 1:
            raise ValidationError('percent commission value is smaller than 1 !')
        elif self['percent_commission_value'] >= 1 and 'percent_commission_value' in vals and vals[
            'percent_commission_value'] >= 1:
            raise ValidationError('percent commission value is smaller than 1 !')
        else:
            res = super(TitleAward, self).write(vals)
            return res

    def unlink(self):
        raise ValidationError('Active award not allow to delete')

    @api.constrains('from_point', 'to_point')
    def point_check(self):
        for record in self:
            if record.from_point >= record.to_point:
                raise ValidationError("To point must be larger than from point")


class RatingBadgesDriver(models.Model):
    _name = 'sharevan.rating.driver.badges'
    _description = 'Rating driver badges'
    MODEL = _name

    name = fields.Char(string='Name', related="rating_badges_id.name")
    driver_id = fields.Many2one('fleet.driver', 'driver_id')
    rating_badges_id = fields.Many2one('sharevan.rating.badges', 'Rating badges id', readonly=True)
    rating_count = fields.Integer(compute="_compute_rating", string="Rating", store=False)
    status = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted')], 'Status', default="running")
    note = fields.Text('note')

    def _compute_rating(self):
        for record in self:
            self.env.cr.execute(""" SELECT count(id) FROM public.sharevan_rating_sharevan_rating_badges_rel rel
                                join sharevan_rating rating on rating.id = rel.sharevan_rating_id
                                where rating.driver_id = %s and sharevan_rating_badges_id = %s """,
                                (record['driver_id']['id'], record['rating_badges_id']['id']))
            result = self._cr.dictfetchall()
            record.rating_count = result[0]['count']


class RatingBadgesCustomer(models.Model):
    _name = 'sharevan.rating.customer'
    _description = 'Rating customer'
    MODEL = _name

    rating_place_id = fields.Integer('Rating Place')
    driver_id = fields.Many2one('fleet.driver', 'driver')
    rating_badge_ids = fields.Many2many('sharevan.rating.badges', string='rating badges')
    employee_id = fields.Many2one('res.partner', 'Employee')
    note = fields.Text('note')
    rating = fields.Integer('Rating')
    type = fields.Selection(
        [('ROUTING', 'Routing'),
         ('BIDDING', 'Bidding')
         ],
        string='Type', default='ROUTING', required=True)


class RatingBadges(models.Model):
    _name = 'sharevan.rating.badges'
    _description = 'rating badges'
    MODEL = _name

    name = fields.Char(string='Name')
    code = fields.Char(string='Rating code', required=True, copy=False, readonly=True,
                       index=True,
                       default=lambda self: _('New'))
    image_256 = fields.Image("Logo", max_width=256, max_height=256, required=True)
    description = fields.Text(string='Description')
    status = fields.Selection(
        [('running', 'Running'),
         ('deleted', 'Deleted')
         ],
        string='Status', default='running', required=True)
    image = fields.Binary("Image", help="This field holds the image used as avatar for \
            this badge, limited to 1024x1024px", )
    type = fields.Selection(
        [('CUSTOMER', 'Customer'),
         ('DRIVER', 'Driver')
         ],
        string='Type', default='CUSTOMER', required=True)

    rating_level = fields.Selection(
        [('1', 'Very bad'),
         ('2', 'Bad'),
         ('3', 'Normal'),
         ('4', 'Good'),
         ('5', 'Very good')
         ],
        string='Rating level', default='3', required=True)

    @api.model
    def create(self, vals):
        seq = BaseMethod.get_new_sequence('sharevan.rating.badges', 'RB', 6, 'code')
        vals['code'] = seq
        result = super(RatingBadges, self).create(vals)

        list_driver = self.env['fleet.driver'].search([('status', '=', 'running'), ('employee_type', '=', 'driver')])

        for driver in list_driver:
            v = {
                'driver_id': driver['id'],
                'rating_badges_id': result['id'],
                'status': 'running'
            }
            badges_driver = self.env['sharevan.rating.driver.badges'].sudo().create(v)

        return result

    def unlink(self):

        for id in self.ids:
            record = self.env['sharevan.rating.badges'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })

            list_driverBadges = self.env['sharevan.rating.driver.badges'].search(
                [('status', '=', 'running'), ('rating_badges_id', '=', id)])
            for driverBadges in list_driverBadges:
                driverBadges.write({
                    'status': 'deleted'
                })
        return self


class RewardPoint(models.Model):
    _name = 'sharevan.reward.point'
    _description = 'DLP reward point'
    MODEL = _name

    name = fields.Char(string='Name')
    code_seq = fields.Char(string='Code', required=True, copy=False, readonly=True, index=True,
                           default=lambda self: _('New'))
    code = fields.Selection(
        [('order', 'Success Order'),
         ('routing', 'Success Routing'),
         ('ranking_silver', 'Silver'),
         ('ranking_gold', 'Gold'),
         ('ranking_platinum', 'Platinum'),
         ],
        string='Code', required=True)
    image_256 = fields.Image("Image", max_width=256, max_height=256, required=True)

    type_reward_point = fields.Selection(
        [('customer', 'Customer'),
         ('driver', 'Driver')
         ],
        string='Type', required=True)
    status = fields.Selection(
        [('running', 'Running'),
         ('deleted', 'Deleted')
         ],
        string='Status', default='running', required=True)
    point = fields.Integer(string='Point', required=True)

    _sql_constraints = [
        ('name', 'unique (name)', 'Name already exists !'),
    ]

    @api.onchange('point')
    def _onchange_point(self):
        if self.point < 0:
            raise UserError(_("Reward points must be greater than 0 !"))

    @api.model
    def create(self, vals):
        seq = BaseMethod.get_new_sequence('sharevan.reward.point', 'SRP', 6, 'code_seq')
        vals['code_seq'] = seq
        result = super(RewardPoint, self).create(vals)
        return result

    def unlink(self):

        for id in self.ids:
            record = self.env['sharevan.reward.point'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })


class RewardPointCustomer(models.Model):
    _name = 'sharevan.reward.point.customer'
    _description = 'reward point customer'
    MODEL = _name

    user_id = fields.Many2one('res.users', 'User')
    bill_lading_id = fields.Many2one('sharevan.bill.lading', 'Bill of lading')
    routing_plan_day_id = fields.Many2one('sharevan.routing.plan.day', 'Routing plan day')
    reward_point_id = fields.Many2one('sharevan.reward.point', 'Reward point')
    point = fields.Integer(string='Point', required=True)


class RatingCompany(models.Model):
    _name = 'sharevan.rating.company'
    _description = 'Routing rate company'
    MODEL = 'sharevan.rating.company'

    rating_place_id = fields.Integer('rating_place_id')
    company_id = fields.Many2one('res.company', 'Company')
    num_rating = fields.Integer('num_rating')
    driver_id = fields.Integer('driver_id')
    note = fields.Text('note')
    reward_point_id = fields.Many2one('sharevan.reward.point', 'Reward point')


class RoutingRequest(models.Model):
    _name = 'sharevan.routing.request'
    _description = 'routing request'

    user_id = fields.Many2one('res.users', 'User')
    bill_routing_id = fields.Many2one('sharevan.bill.routing', 'Bill routing')
    routing_plan_day_id = fields.Many2one('sharevan.routing.plan.day', 'Routing plan day')
    note = fields.Text('note')
    type = fields.Boolean('Type',
        help='True is export warehouse,which does not have return day, False is import warehouse')
    retry_date = fields.Date('Retry date', default=datetime.today())
    return_date = fields.Date('Return date', default=datetime.today())
    on_request = fields.Boolean('On request', default=True)
    retry_other_day = fields.Boolean('Other day', default=False, help='Customer request retry on other day.')
    on_request_by_user = fields.Char('Checking user', related='user_id.partner_id.name')
    hidden_end_button = fields.Boolean('Hidden button', store=False, compute='compute_on_load')
    hidden_start_button = fields.Boolean('Hidden button', store=False, compute='compute_on_load')
    hidden_retry_button = fields.Boolean('Hidden button', store=False, compute='compute_on_load')
    hidden_return_button = fields.Boolean('Hidden button', store=False, compute='compute_on_load')
    reason = fields.Selection(
        [('1', 'Customer not found'), ('2', 'Order package change'),
         ('3', 'Customer cancel'), ('4', 'System not satisfy')],
        string='Reason')
    date_plan = fields.Date('Date plan', default=datetime.today())
    routing_vehicle_id = fields.Many2one('sharevan.routing.vehicle', 'Routing vehicle')
    claim_type = fields.Selection(
        [   ('cancel', 'Cancel'),
            ('return', 'Return'),
         ('retry', 'Retry')
         ],
        string='Claim type')

    def compute_on_load(self):
        for record in self:
            if not record['on_request']:
                record.hidden_end_button = True
                record.hidden_start_button = False
                record.hidden_retry_button = True
                record.hidden_return_button = True
            elif self.env.uid == record['user_id'].id and record['on_request']:
                record.hidden_end_button = False
                record.hidden_start_button = True
                record.hidden_retry_button = False
                if record['type'] == True:
                    record.hidden_return_button = True
                else:
                    record.hidden_return_button = False
            else:
                record.hidden_end_button = True
                record.hidden_start_button = True
                record.hidden_retry_button = True
                record.hidden_return_button = True

    def on_request_check_end(self):
        query = """
            update sharevan_routing_request set on_request = false where id = %s
        """
        self._cr.execute(query, (self.id,))
        notice = "You check out of request for this bill: " + self.bill_routing_id.name
        self.env.user.notify_warning(message=notice, title=NotificationSocketType.NOTIFICATION.value)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bill routing',
            'view_mode': 'tree',
            'res_model': 'sharevan.bill.routing',
            'target': 'current'
        }

    def on_request_check_start(self):
        query = """
            update sharevan_routing_request set on_request = true , user_id =%s where id = %s
                """
        self._cr.execute(query, (self.env.uid, self.id,))
        notice = "You have started check bill: " + self.bill_routing_id.name
        self.env.user.notify_info(message=notice, title=NotificationSocketType.NOTIFICATION.value)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Check bill',
            'view_mode': 'form',
            'res_model': 'sharevan.routing.request',
            'res_id': self.id,
            'target': 'new',
            'context': {
                'form_view_initial_mode': 'edit',
            },
        }

    def write(self, vals):
        if self.user_id:
            if self.user_id.id != self.env.uid:
                raise ValidationError(self.user_id.partner_id.name + ' is checking this bill! You are not authorized to '
                                                                     'check it')
            else:
                res = super(RoutingRequest, self).write(vals)
                return res
        else:
            res = super(RoutingRequest, self).write(vals)
            return res


    # create routing plan day ,update bill routing vào routing plan day
    # tương ứng thêm bill package routing plan import / export theo bill package routing plan tương ứng
    # thêm bill package routing plan
    # update all routing plan day => cancel trouble_type = retry
    # tương ứng thêm bill package routing plan import / export theo bill package routing plan tương ứng
    def mapping_routing_plan_day(self, from_routing_plan,solution_id,date_plan):
        print(from_routing_plan)
        new_routing_plan = {
            'routing_plan_day_code': from_routing_plan['routing_plan_day_code'] + '_RETRY',
            'date_plan': self.retry_date,
            # 'driver_id': from_routing_plan['driver_id'],
            # 'vehicle_id': from_routing_plan['vehicle_id'],
            'latitude': from_routing_plan['latitude'],
            'longitude': from_routing_plan['longitude'],
            'address': from_routing_plan['address'],
            # 'order_number': from_routing_plan['order_number'],
            'status': RoutingDetailStatus.AssignCarWorking.value,
            'depot_id': from_routing_plan['depot_id'],
            'zone_area_id': from_routing_plan['zone_area_id'],
            'type': from_routing_plan['type'],
            'capacity_expected': from_routing_plan['capacity_expected'],
            'stock_man_id': from_routing_plan['stock_man_id'],
            'insurance_id': from_routing_plan['insurance_id'],
            'assess_amount': from_routing_plan['assess_amount'],
            'total_volume': from_routing_plan['total_volume'],
            'total_package': from_routing_plan['total_package'],
            'capacity_actual': from_routing_plan['capacity_actual'],
            'hub_id': from_routing_plan['hub_id'],
            'warehouse_id': from_routing_plan['warehouse_id'],
            'warehouse_name': from_routing_plan['warehouse_name'],
            'bill_lading_detail_code': from_routing_plan['bill_lading_detail_code'],
            'phone': from_routing_plan['phone'],
            'trouble_type': RoutingTroubleType.Retry.value,
            'partner_id': from_routing_plan['partner_id'],
            'max_tonnage_shipping': from_routing_plan['max_tonnage_shipping'],
            'company_id': from_routing_plan['company_id'],
            'description': from_routing_plan['description'],
            'ship_type': from_routing_plan['ship_type'],
            'bill_lading_detail_id': from_routing_plan['bill_lading_detail_id'],
            'from_routing_plan_day_id': from_routing_plan['id'],
            'qr_so': from_routing_plan['qr_so'],
            'solution_day_id': solution_id,
            'so_type': from_routing_plan['so_type'],
            'num_receive': from_routing_plan['num_receive'],
            'bill_routing_id': from_routing_plan['bill_routing_id']
        }
        print('_SOS_EXPORT', new_routing_plan)
        routing_record = http.request.env['sharevan.routing.plan.day'].create(new_routing_plan)
        if routing_record:
            package_plan_query = """
                select * from sharevan_bill_package_routing_plan where routing_plan_day_id =%s
            """
            self._cr.execute(package_plan_query, (from_routing_plan['id'],))
            package_plans = self._cr.dictfetchall()
            if package_plans:
                if from_routing_plan['type']== WarehouseType.Import.value:
                    for plan in package_plans:
                        package_import_query = """
                            select * from sharevan_bill_package_routing_import
                                where routing_plan_day_id =%s and routing_package_plan =%s
                                        """
                        self._cr.execute(package_import_query, (from_routing_plan['id'],plan['id'],))
                        package_imports = self._cr.dictfetchall()
                        if package_imports:
                            plan.pop('id')
                            plan['routing_plan_day_id']= from_routing_plan['id']
                            plan_new = http.request.env['sharevan.bill.package.routing.plan'].create(plan)
                            if plan_new:
                                for import_record in package_imports:
                                    import_record.pop('id')
                                    import_record['routing_plan_day_id']=routing_record['id']
                                    import_record['routing_package_plan']=plan_new['id']
                                    import_record_new = http.request.env['sharevan.bill.package.routing.import'].create(import_record)
                            else:
                                raise ValidationError('Can not create new bill package plan')
                        else:
                            raise ValidationError('Bill package import not found')
                else:
                    for plan in package_plans:
                        package_export_query = """
                            select * from sharevan_bill_package_routing_export
                                where routing_plan_day_id =%s and routing_package_plan =%s
                                        """
                        self._cr.execute(package_export_query, (from_routing_plan['id'],plan['id'],))
                        package_exports = self._cr.dictfetchall()
                        if package_exports:
                            plan.pop('id')
                            plan['routing_plan_day_id']= from_routing_plan['id']
                            plan_new = http.request.env['sharevan.bill.package.routing.plan'].create(plan)
                            if plan_new:
                                for export_record in package_exports:
                                    export_record.pop('id')
                                    export_record['routing_plan_day_id']=routing_record['id']
                                    export_record['routing_package_plan']=plan_new['id']
                                    export_record_new = http.request.env['sharevan.bill.package.routing.export'].create(
                                        export_record)
                            else:
                                raise ValidationError('Can not create new bill package plan')
                        else:
                            raise ValidationError('Bill package import not found')
            else:
                raise ValidationError('Bill package plan not found')
        else:
            raise ValidationError('Can not create new routing')

    def on_retry_bill(self):
        driver_users=[]
        if not self.reason or not self.note:
            raise ValidationError('You have to registration the reason and note!')
        else:
            pass
        if self.type:
            print('retry all bill', self.bill_routing_id.name)
            bill_routing_record = http.request.env['sharevan.bill.routing'].search(
                [('id', '=', self.bill_routing_id.id)])
            bill_routing_record.write({
                'trouble_type':RoutingTroubleType.Retry.value,
                'reason':self.reason,
                'description':self.note
            })
            # update all bill_routing => retry
            #     create solution day
            vals = {
                'name': 'date_plan',
                'date_plan': self.retry_date,
                'status': '0',
                'group_code': 'default',
            }
            solution_record = http.request.env['solution.day'].sudo().create(vals)
            if solution_record:
                print(solution_record)
                now_routing_query = """
                    select * from sharevan_routing_plan_day where bill_routing_id =%s
                """
                self._cr.execute(now_routing_query, (self.bill_routing_id.id,))
                rpd = self._cr.dictfetchall()
                if rpd:
                    for routing in rpd:
                        routing_record = http.request.env['sharevan.routing.plan.day'].search(
                            [('id', '=', routing['id'])])
                        if routing_record['driver_id']:
                            if len(driver_users)>0:
                                for driver in driver_users:
                                    if driver!= routing_record['driver_id']['user_id']['id']:
                                        driver_users.append(routing_record['driver_id']['user_id']['id'])
                            else:
                                driver_users.append(routing_record['driver_id']['user_id']['id'])
                        routing_record.write({
                            'trouble_type': RoutingTroubleType.Retry.value,
                            'reason': self.reason,
                            'status': RoutingDetailStatus.Cancel.value,
                            'description': self.note
                        })
                        self.mapping_routing_plan_day(routing,solution_record['id'],self.retry_date)
                    # thông báo cho driver, customer và DLP employee về việc xác nhận thay đổi ngày đi đơn
                    dlp_employee = BaseMethod.get_dlp_employee()
                    title='Customer have change day retry for bill'
                    body = 'Customer have change day retry for bill !' + self.bill_routing_id.name
                    if dlp_employee:
                        content = {
                            'title': title ,
                            'content': body,
                            'type': NotificationType.RoutingMessage.value,
                            'res_id': self.bill_routing_id.id,
                            'res_model': 'sharevan.bill.routing',
                            'click_action': ClickActionType.routing_plan_day_driver.value,
                            'message_type': MessageType.warning.value,
                            'user_id': dlp_employee,
                        }
                        self.env['sharevan.notification'].sudo().create(content)
                        list_employee = self.env['res.users'].search([('id', 'in', dlp_employee)])
                        for emp in list_employee:
                            emp.notify_info(message=body, title=NotificationSocketType.NOTIFICATION.value)
                    # send message for customer
                    users = BaseMethod.get_customer_employee(self.bill_routing_id.company_id.id, 'all')
                    if len(users) > 0:
                        try:
                            content = {
                                'title': title,
                                'content': body,
                                'type': 'routing',
                                'res_id': self.bill_routing_id.id,
                                'res_model': 'sharevan.bill.routing',
                                'click_action': ClickActionType.bill_routing_detail.value,
                                'message_type': MessageType.warning.value,
                                'user_id': users,
                                'item_id': str(self.bill_routing_id.id),
                            }
                            self.env['sharevan.notification'].sudo().create(content)
                        except:
                            logger.warn(
                                "Register retry Successful! But send message for customer fail",
                                'sharevan.bill.routing', self.bill_routing_id.id,
                                exc_info=True)
                    else:
                        logger.warn(
                            "Register retry Successful! But can not send message for customer because not found user",
                            'sharevan.bill.routing', self.bill_routing_id.id,
                            exc_info=True)

                    type = NotificationType.RoutingMessage.value
                    item_id = self.bill_routing_id.code
                    message_type = MessageType.warning.value
                    object_status = ObjectStatus.UpdateInformation.value
                    click_action = ClickActionType.driver_history_activity.value
                    BaseMethod.send_notification_driver(driver_users, 'sharevan.routing.plan.day',
                                                        self.routing_plan_day_id.id, click_action, message_type, title,
                                                        body, type, item_id, object_status)
                    return {'type': 'ir.actions.act_window', 'name': 'Bill routing', 'res_model': 'sharevan.bill.routing',
                        'view_type': 'form', 'view_mode': 'tree,form', 'target': '', }

                else:
                    raise ValidationError('Routing plan day list not found')
            else:
                raise ValidationError('Can not create solution day record')
        else:
            print('retry drop down other day', self.bill_routing_id.name)
            # bên routing xử lý nên không update state của bill và rpd
            try:
                url = config['security_url'] + config['routing_host'] + ':' + config[
                    'routing_port'] + '/location/retry_other_day'
                payload = {
                    'retry_date': self.retry_date,
                    'routing_plan_day_id': self.routing_plan_day_id.id
                }
                print(payload)
                payloadjson = json.dumps(payload, default=date_utils.json_default, skipkeys=True)
                resps = requests.get(url, params=payload,
                                     headers={'Content-Type': 'application/json'}).json()
            except:
                logger.error("There was problem requesting routing!")
                raise ValidationError('There was problem requesting routing')
            logger.warn(
                "return routing response on register day",
                RoutingPlanDay._name, resps,
                exc_info=True)
            if 'error' in resps:
                raise ValidationError('There was problem requesting routing')
    #         send message for routing trả hàng về kho gần nhất và trả vào ngày khách hàng định trước
            else:
                # thông báo cho driver, customer và DLP employee về việc xác nhận thay đổi ngày nhận hàng
                dlp_employee = BaseMethod.get_dlp_employee()
                title = 'Customer have change day retry for bill'
                body = 'Customer have change day retry for bill !' + self.bill_routing_id.name
                if dlp_employee:
                    content = {
                        'title': title,
                        'content': body,
                        'type': NotificationType.RoutingMessage.value,
                        'res_id': self.bill_routing_id.id,
                        'res_model': 'sharevan.bill.routing',
                        'click_action': ClickActionType.routing_plan_day_driver.value,
                        'message_type': MessageType.warning.value,
                        'user_id': dlp_employee,
                    }
                    self.env['sharevan.notification'].sudo().create(content)
                    list_employee = self.env['res.users'].search([('id', 'in', dlp_employee)])
                    for emp in list_employee:
                        emp.notify_info(message=body, title=NotificationSocketType.NOTIFICATION.value)
                # send message for customer
                users = BaseMethod.get_customer_employee(self.bill_routing_id.company_id.id, 'all')
                if len(users) > 0:
                    try:
                        content = {
                            'title': title,
                            'content': body,
                            'type': 'routing',
                            'res_id': self.bill_routing_id.id,
                            'res_model': 'sharevan.bill.routing',
                            'click_action': ClickActionType.bill_routing_detail.value,
                            'message_type': MessageType.warning.value,
                            'user_id': users,
                            'item_id': str(self.bill_routing_id.id),
                        }
                        self.env['sharevan.notification'].sudo().create(content)
                    except:
                        logger.warn(
                            "Register retry Successful! But send message for customer fail",
                            'sharevan.bill.routing', self.bill_routing_id.id,
                            exc_info=True)
                else:
                    logger.warn(
                        "Register retry Successful! But can not send message for customer because not found user",
                        'sharevan.bill.routing', self.bill_routing_id.id,
                        exc_info=True)
                driver_users.append(self.routing_plan_day_id.driver_id.id)
                type = NotificationType.RoutingMessage.value
                item_id = self.bill_routing_id.code
                message_type = MessageType.warning.value
                object_status = ObjectStatus.UpdateInformation.value
                click_action = ClickActionType.driver_history_activity.value
                BaseMethod.send_notification_driver(driver_users, 'sharevan.routing.plan.day',
                            self.routing_plan_day_id.id, click_action, message_type, title,
                            body, type, item_id, object_status)
                return {'type': 'ir.actions.act_window', 'name': 'Bill routing', 'res_model': 'sharevan.bill.routing',
                        'view_type': 'form', 'view_mode': 'tree,form', 'target': '', }

    def on_return_bill(self):
        if not self.reason or not self.note:
            raise ValidationError('You have to registration the reason and note!')
        else:
            driver_users=[]
            print('return bill', self.bill_routing_id.name)
            # bên routing xử lý nên không update state của bill và rpd
            try:
                url = config['security_url'] + config['routing_host'] + ':' + config[
                    'routing_port'] + '/location/return_order'
                payload = {
                    'return_date': self.return_date,
                    'routing_plan_day_id': self.routing_plan_day_id.id
                }
                print(payload)
                payloadjson = json.dumps(payload, default=date_utils.json_default, skipkeys=True)
                resps = requests.get(url, params=payload,
                                     headers={'Content-Type': 'application/json'}).json()
            except:
                logger.error("There was problem requesting routing!")
                raise ValidationError('There was problem requesting routing')
            logger.warn(
                "Register return routing",
                RoutingPlanDay._name, resps,
                exc_info=True)
            if 'error' in resps:
                raise ValidationError('There was problem requesting routing')
            #         send message for routing trả hàng về kho gần nhất và trả vào ngày khách hàng định trước
            else:
                # thông báo cho driver, customer và DLP employee về việc xác nhận thay đổi ngày nhận hàng
                dlp_employee = BaseMethod.get_dlp_employee()
                title = 'Customer have assign day return day for bill'
                body = 'Customer have assign day return for bill !' + self.bill_routing_id.name
                if dlp_employee:
                    content = {
                        'title': title,
                        'content': body,
                        'type': NotificationType.RoutingMessage.value,
                        'res_id': self.bill_routing_id.id,
                        'res_model': 'sharevan.bill.routing',
                        'click_action': ClickActionType.routing_plan_day_driver.value,
                        'message_type': MessageType.warning.value,
                        'user_id': dlp_employee,
                    }
                    self.env['sharevan.notification'].sudo().create(content)
                    list_employee = self.env['res.users'].search([('id', 'in', dlp_employee)])
                    for emp in list_employee:
                        emp.notify_info(message=body, title=NotificationSocketType.NOTIFICATION.value)
                # send message for customer
                users = BaseMethod.get_customer_employee(self.bill_routing_id.company_id.id, 'all')
                if len(users) > 0:
                    try:
                        content = {
                            'title': title,
                            'content': body,
                            'type': 'routing',
                            'res_id': self.bill_routing_id.id,
                            'res_model': 'sharevan.bill.routing',
                            'click_action': ClickActionType.bill_routing_detail.value,
                            'message_type': MessageType.warning.value,
                            'user_id': users,
                            'item_id': str(self.bill_routing_id.id),
                        }
                        self.env['sharevan.notification'].sudo().create(content)
                    except:
                        logger.warn(
                            "Register return Successful! But send message for customer fail",
                            'sharevan.bill.routing', self.bill_routing_id.id,
                            exc_info=True)
                else:
                    logger.warn(
                        "Register return Successful! But can not send message for customer because not found user",
                        'sharevan.bill.routing', self.bill_routing_id.id,
                        exc_info=True)
                driver_users.append(self.routing_plan_day_id.driver_id.id)
                type = NotificationType.RoutingMessage.value
                item_id = self.bill_routing_id.code
                message_type = MessageType.warning.value
                object_status = ObjectStatus.UpdateInformation.value
                click_action = ClickActionType.driver_history_activity.value
                BaseMethod.send_notification_driver(driver_users, 'sharevan.routing.plan.day',
                                                    self.routing_plan_day_id.id, click_action, message_type, title,
                                                    body, type, item_id, object_status)
                return {'type': 'ir.actions.act_window', 'name': 'Bill routing', 'res_model': 'sharevan.bill.routing',
                        'view_type': 'form', 'view_mode': 'tree,form', 'target': '', }

    def cancel_routing_send(self):
        for record in self:
            print(record.reason)
        if not self.reason:
            raise ValidationError('You have to set reason')
        if not self.note:
            raise ValidationError('You have to fill note')
        if self.type == True:
            routing_query = """
                select id , driver_id,routing_plan_day_code, status, type from sharevan_routing_plan_day 
                    where id in (
                WITH RECURSIVE c AS (
                    SELECT ( %s ) AS id
                    UNION ALL
                    SELECT sa.id
                    FROM sharevan_routing_plan_day AS sa
                    JOIN c ON c.id = sa.from_routing_plan_day_id
                    )
                SELECT id FROM c ) order by type
                    """
            self._cr.execute(routing_query, (self.routing_plan_day_id.id,))
            rpd = self._cr.dictfetchall()
            if rpd is None or len(rpd) == 0:
                raise ValidationError("No routing found")
            time_now = datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")
            BaseMethod.check_role_access(http.request.env.user, 'sharevan.routing.plan.day',
                                         rpd[0]['id'])
            driver_lst = []
            description = self.note
            reason = self.reason
            update_query = """
                update sharevan_routing_plan_day set status = %s ,accept_time =%s
                    , description = %s,  reason = %s, trouble_type = %s where id ::integer in (
            """
            for rec in rpd:
                if (rec['type'] == '0'):
                    if rec['status'] == RoutingDetailStatus.Done.value:
                        raise ValidationError('Driver have pick up date export warehouse bill not allow to cancel!')
                driver_id = rec['driver_id']
                if len(driver_lst) > 0:
                    for d_id in driver_lst:
                        if d_id != driver_id:
                            driver_lst.append(driver_id)
                else:
                    driver_lst.append(driver_id)
                update_query += str(rec['id']) + ","
            update_query = update_query[:-1]
            update_query += ")"
            self._cr.execute(update_query, (
                RoutingDetailStatus.Cancel.value, time_now, description, reason, RoutingTroubleType.Normal.value,))
            bill_routing_record = http.request.env['sharevan.bill.routing'].search(
                [('id', '=', self.bill_routing_id.id)])
            cancel_check = False
            if self.reason == ReasonType.SystemNotSatisfy.value:
                cancel_check = True
            if bill_routing_record:
                bill_routing_record.write({
                    'status_routing': BillRoutingStatus.Cancel.value,
                    'description': self.note,
                    'cancel_check': cancel_check,
                    'reason': self.reason,
                    'trouble_type': RoutingTroubleType.Normal.value,
                    'end_date':datetime.now()

                })
            else:
                raise ValidationError('bill routing not found')

            # send message for customer
            users = BaseMethod.get_customer_employee(self.bill_routing_id.company_id.id, 'all')
            if len(users) > 0:
                try:
                    content = {
                        'title': 'Routing cancel for change. ' + self.bill_routing_id.code,
                        'content': description,
                        'type': 'routing',
                        'res_id': self.bill_routing_id.id,
                        'res_model': 'sharevan.bill.routing',
                        'click_action': ClickActionType.bill_routing_detail.value,
                        'message_type': MessageType.warning.value,
                        'user_id': users,
                        'item_id': str(self.bill_routing_id.id),
                    }
                    self.env['sharevan.notification'].sudo().create(content)
                except:
                    logger.warn(
                        "Cancel Successful! But send message for customer fail",
                        'sharevan.bill.routing', self.bill_routing_id.id,
                        exc_info=True)
            else:
                logger.warn(
                    "Cancel Successful! But can not send message for customer because not found user",
                    'sharevan.bill.routing', self.bill_routing_id.id,
                    exc_info=True)
            driver_users = []
            for id in driver_lst:
                routing_query = """
                    select user_id from fleet_driver where id =%s
                                    """
                self._cr.execute(routing_query, (id,))
                driver = self._cr.dictfetchall()
                if driver:
                    if len(driver_users) > 0:
                        for d_id in driver_users:
                            if d_id != driver[0]['user_id']:
                                driver_users.append(d_id)
                    else:
                        driver_users.append(driver[0]['user_id'])
            if self.routing_plan_day_id.vehicle_id:

                ordereddState = self.env['fleet.vehicle.state'].search([('code', '=', VehicleStateStatus.Ordered.value)],
                                                                       limit=1).id
                availableState = self.env['fleet.vehicle.state'].search([('code', '=', VehicleStateStatus.Available.value)],
                                                                        limit=1).id
                check_update_vehicle_query = """
                    select plan.* from sharevan_routing_plan_day plan
                        join fleet_vehicle vehicle on vehicle.id = plan.vehicle_id
                        where vehicle_id =%s and vehicle.state_id = %s and plan.routing_vehicle_id = %s and plan.status::integer in(0,1,2,4,5)
                """
                self._cr.execute(check_update_vehicle_query, (self.routing_plan_day_id.vehicle_id.id, ordereddState,self.routing_plan_day_id.routing_vehicle_id.id))
                check_vehicle = self._cr.dictfetchall()
                if len(check_vehicle) > 0:
                    pass
                else:
                    # Update vehicle ve Availble
                    self.env.cr.execute(""" 
                                                            UPDATE fleet_vehicle
                                                            SET state_id= %s 
                                                            WHERE id = %s;  
                                                                            """,
                                        (availableState, self.routing_plan_day_id.vehicle_id.id,))
                    # Neu la don di 1 lan thi update bill_lading ve cancel
                    check_cycle_type_bill_lading = """
                                                                select bill_lading.id ,bill_lading.cycle_type  
                                                                from sharevan_routing_plan_day plan
                                                                join sharevan_bill_lading_detail lading_detail  on plan.bill_lading_detail_id = lading_detail.id
                                                                join sharevan_bill_lading bill_lading  on bill_lading.id = lading_detail.bill_lading_id
                                                                where plan.id = %s
                                                            """
                    self._cr.execute(check_cycle_type_bill_lading, (self.routing_plan_day_id.id,))
                    check_cycle_type = self._cr.dictfetchall()
                    if check_cycle_type[0]['cycle_type'] == '5':
                        self.env.cr.execute(""" 
                                                                UPDATE sharevan_bill_lading
                                                                SET status= 'deleted' ,reason = %s
                                                                WHERE id = %s;  
                                                                                """,
                                            (check_cycle_type[0]['id'], reason,))
            # send for driver
            if len(driver_users) > 0:
                title = 'Routing cancel for change. ' + self.bill_routing_id.code
                body = description
                type = NotificationType.RoutingMessage.value
                item_id = self.bill_routing_id.code
                message_type = MessageType.warning.value
                object_status = ObjectStatus.UpdateInformation.value
                click_action = ClickActionType.driver_history_activity.value
                BaseMethod.send_notification_driver(driver_users, 'sharevan.routing.plan.day',
                                                    self.routing_plan_day_id.id, click_action, message_type, title,
                                                    body, type, item_id, object_status)
                return {'type': 'ir.actions.act_window', 'name': 'Bill routing', 'res_model': 'sharevan.bill.routing',
                        'view_type': 'form', 'view_mode': 'tree,form', 'target': '', }
        else:
            raise ValidationError('Export routing can not cancel')

    def check_out_request_for_normal(self):
        time_now = datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")
        if not self.note:
            raise ValidationError('You have to write the note')
        if self.type == True:
            routing_query = """
                select id , driver_id,routing_plan_day_code, status, type from sharevan_routing_plan_day 
                    where id in (
                WITH RECURSIVE c AS (
                    SELECT ( %s ) AS id
                    UNION ALL
                    SELECT sa.id
                    FROM sharevan_routing_plan_day AS sa
                    JOIN c ON c.id = sa.from_routing_plan_day_id
                    )
                SELECT id FROM c ) order by type
                    """
            self._cr.execute(routing_query, (self.routing_plan_day_id.id,))
            rpd = self._cr.dictfetchall()
            if rpd is None or len(rpd) == 0:
                raise ValidationError("No routing found")
            BaseMethod.check_role_access(http.request.env.user, 'sharevan.routing.plan.day',
                                         rpd[0]['id'])
            driver_lst = []
            description = self.note
            reason = self.reason
            update_query = """
                update sharevan_routing_plan_day set status = %s ,accept_time =%s
                    , description = %s,  trouble_type = %s where id ::integer in (
            """
            for rec in rpd:
                driver_id = rec['driver_id']
                if len(driver_lst) > 0:
                    for d_id in driver_lst:
                        if d_id != driver_id:
                            driver_lst.append(driver_id)
                else:
                    driver_lst.append(driver_id)
                update_query += str(rec['id']) + ","
            update_query = update_query[:-1]
            update_query += ")"
            self._cr.execute(update_query, (
                RoutingDetailStatus.Unconfimred.value, time_now, description, RoutingTroubleType.Normal.value,))
            bill_routing_record = http.request.env['sharevan.bill.routing'].search(
                [('id', '=', self.bill_routing_id.id)])
            if bill_routing_record:
                bill_routing_record.write({
                    'status_routing': BillRoutingStatus.Waiting.value,
                    'description': self.note,
                    'trouble_type': RoutingTroubleType.Normal.value,
                })
            else:
                raise ValidationError('bill routing not found')

            # send message for customer
            users = BaseMethod.get_customer_employee(self.bill_routing_id.company_id.id, 'all')
            if len(users) > 0:
                try:
                    content = {
                        'title': 'Routing is allowed to continue : ' + self.bill_routing_id.code,
                        'content': description,
                        'type': 'routing',
                        'res_id': self.bill_routing_id.id,
                        'res_model': 'sharevan.bill.routing',
                        'click_action': ClickActionType.bill_routing_detail.value,
                        'message_type': MessageType.warning.value,
                        'user_id': users,
                        'item_id': str(self.bill_routing_id.id),
                    }
                    self.env['sharevan.notification'].sudo().create(content)
                except:
                    logger.warn(
                        "Continue Successful! But send message for customer fail",
                        'sharevan.bill.routing', self.bill_routing_id.id,
                        exc_info=True)
            else:
                logger.warn(
                    "Continue Successful! But can not send message for customer because not found user",
                    'sharevan.bill.routing', self.bill_routing_id.id,
                    exc_info=True)
            driver_users = []
            for id in driver_lst:
                routing_query = """
                    select user_id from fleet_driver where id =%s
                                    """
                self._cr.execute(routing_query, (id,))
                driver = self._cr.dictfetchall()
                if driver:
                    if len(driver_users) > 0:
                        for d_id in driver_users:
                            if d_id != driver[0]['user_id']:
                                driver_users.append(d_id)
                    else:
                        driver_users.append(driver[0]['user_id'])
            # send for driver
            if len(driver_users) > 0:
                title = 'Routing is allowed to continue : ' + self.bill_routing_id.code,
                body = description
                type = NotificationType.RoutingMessage.value
                item_id = self.bill_routing_id.code
                message_type = MessageType.warning.value
                object_status = ObjectStatus.UpdateInformation.value
                click_action = ClickActionType.driver_history_activity.value
                BaseMethod.send_notification_driver(driver_users, 'sharevan.routing.plan.day',
                                                    self.routing_plan_day_id.id, click_action, message_type, title,
                                                    body, type, item_id, object_status)
                return {'type': 'ir.actions.act_window', 'name': 'Bill routing', 'res_model': 'sharevan.bill.routing',
                        'view_type': 'form', 'view_mode': 'tree,form', 'target': '', }
        else:
            description = self.note
            reason = self.reason
            update_query = """
                            update sharevan_routing_plan_day set status = %s ,accept_time =%s
                                , description = %s,  trouble_type = %s where id =%s
                        """
            self._cr.execute(update_query, (
                RoutingDetailStatus.Unconfimred.value, time_now, description, reason, RoutingTroubleType.Normal.value,
                self.routing_plan_day_id.id))
            bill_routing_record = http.request.env['sharevan.bill.routing'].search(
                [('id', '=', self.bill_routing_id.id)])
            if bill_routing_record:
                bill_routing_record.write({
                    'status_routing': BillRoutingStatus.Waiting.value,
                    'description': self.note,
                    'trouble_type': RoutingTroubleType.Normal.value,
                })
            else:
                raise ValidationError('bill routing not found')

            # send message for customer
            users = BaseMethod.get_customer_employee(self.bill_routing_id.company_id.id, 'all')
            if len(users) > 0:
                try:
                    content = {
                        'title': 'Routing is allowed to continue : ' + self.bill_routing_id.code,
                        'content': description,
                        'type': 'routing',
                        'res_id': self.bill_routing_id.id,
                        'res_model': 'sharevan.bill.routing',
                        'click_action': ClickActionType.bill_routing_detail.value,
                        'message_type': MessageType.warning.value,
                        'user_id': users,
                        'item_id': str(self.bill_routing_id.id),
                    }
                    self.env['sharevan.notification'].sudo().create(content)
                except:
                    logger.warn(
                        "Continue Successful! But send message for customer fail",
                        'sharevan.bill.routing', self.bill_routing_id.id,
                        exc_info=True)
            else:
                logger.warn(
                    "Continue Successful! But can not send message for customer because not found user",
                    'sharevan.bill.routing', self.bill_routing_id.id,
                    exc_info=True)
            driver_users = []
            routing_query = """
                            select user_id from fleet_driver where id =%s
                                            """
            self._cr.execute(routing_query, (self.routing_plan_day_id.driver_id.id,))
            driver = self._cr.dictfetchall()
            if driver:
                driver_users.append(driver[0]['user_id'])
            # send for driver
            if len(driver_users) > 0:
                try:
                    content = {
                        'title': 'Routing is allowed to continue : ' + self.bill_routing_id.code,
                        'content': description,
                        'type': 'routing',
                        'res_id': self.routing_plan_day_id.id,
                        'res_model': 'sharevan.routing.plan.day',
                        'click_action': ClickActionType.driver_history_activity.value,
                        'message_type': MessageType.warning.value,
                        'user_id': driver_users,
                        'item_id': self.bill_routing_id.code,
                    }
                    http.request.env['sharevan.notification'].sudo().create(content)
                except:
                    logger.warn(
                        "Continue Successful! But can not send message for driver",
                        'sharevan.bill.routing', self.bill_routing_id.id,
                        exc_info=True)
                return {'type': 'ir.actions.act_window', 'name': 'Bill routing', 'res_model': 'sharevan.bill.routing',
                        'view_type': 'form', 'view_mode': 'tree,form', 'target': '', }
