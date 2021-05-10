import json
import logging
from ast import literal_eval
from datetime import datetime, timedelta

import pytz
import requests

from mymodule.base_next.controllers.api.firebase_messaging import FirebaseMessagingAPI
from mymodule.base_next.models.notification import Notification
from mymodule.enum.ClickActionType import ClickActionType
from mymodule.enum.MessageType import NotificationSocketType, MessageType
from mymodule.enum.ObjectStatus import ObjectStatus
from mymodule.enum.RoutingDetailStatus import RoutingDetailStatus
from mymodule.enum.ShipType import ShipType
from mymodule.enum.VehicleStateStatus import VehicleStateStatus
from odoo import models, fields, http, api
from odoo.exceptions import ValidationError
from odoo.http import Response
from odoo.tools import config, date_utils

logger = logging.getLogger(__name__)


class ProductType(models.Model):
    _name = 'sharevan.product.type'
    _description = 'product type'
    _inherit = 'sharevan.product.type'


class RoutingVehicleMany2Many(models.Model):
    _name = 'sharevan.routing.vehicle.temp'
    _description = 'sharevan.routing.vehicle.temp'

    routing_vehicle_id = fields.Many2one('sharevan.routing.vehicle', string='Routing Vehicle')
    routing_id = fields.Many2one('sharevan.routing.plan.day', string='Routing plan day', domain=lambda
        self: "[('vehicle_id', '=', False),('date_plan','>=',date_plan),('ship_type','=','0')]")


INSERT_QUERY = "INSERT INTO SHAREVAN_ROUTING_VEHICLE_TEMP (ROUTING_VEHICLE_ID,ROUTING_ID) " \
               " VALUES ( %s , %s ) "


class RoutingVehicle(models.Model):
    _name = 'sharevan.routing.vehicle'
    _description = 'sharevan.routing.vehicle'

    routing_code = fields.Char('Code', default='New', readonly=True)
    name = fields.Char('Name', default='New', readonly=True)
    date_plan = fields.Date('Plan date')
    start_routing = fields.Datetime('Start routing')
    end_routing = fields.Datetime('End routing')
    redirect_routing = fields.Boolean('Redirect routing')
    latitude = fields.Float('Latitude', related='vehicle_id.latitude', store=False)
    longitude = fields.Float('Longitude', related='vehicle_id.longitude', store=False)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    checking_user_id = fields.Many2one('res.users', string='Checking User')
    parent_id = fields.Many2one('sharevan.routing.vehicle', string='Parent')
    driver_id = fields.Many2one('fleet.driver', string='Driver')
    depot_id = fields.Many2one('sharevan.depot', string='Depot')
    company_id = fields.Many2one('res.company', string='Company', domain=lambda
        self: "[('status', '=', 'running'),('company_type','=','0')]")
    routing_id = fields.Many2many('sharevan.routing.plan.day', 'sharevan_routing_vehicle_temp', 'routing_vehicle_id',
                                  'routing_id', 'Routing plan day direct', domain=lambda
            self: "[('depot_id', '=', depot_id),('vehicle_id', '=', False),('date_plan','=',date_plan),('ship_type','=','0')]")
    toogle = fields.Boolean('Toogle', compute='compute_button', default=True)
    routing_check = fields.Boolean('routing_check', default=True)
    routing_scanning = fields.Boolean('Routing system scanning', default=False)
    routing_note = fields.Char('routing note')
    create_driver_calendar = fields.Boolean('Create driver calendar', compute='compute_button', store=False,
                                            default=True)
    solution_day_id = fields.Many2one('solution.day', 'Solution day')
    routing_vehicle_ids = fields.One2many('sharevan.routing.request', 'routing_vehicle_id', 'Routing request')

    def compute_button(self):
        for record in self:
            if record.redirect_routing:
                if record.checking_user_id.id != self.env.uid:
                    record.toogle = True
                else:
                    record.toogle = False
            else:
                record.toogle = False
            record.create_driver_calendar = True

    @api.onchange('date_plan')
    def on_change_date_plan(self):
        time_now = datetime.today().date()
        for record in self:
            if record['date_plan'] and record['date_plan'] < time_now:
                record['date_plan'] = datetime.today()
                notice = "Date plan is not lower than today! "
                self.env.user.notify_info(message=notice, title=NotificationSocketType.NOTIFICATION.value)

    @api.onchange('start_routing')
    def on_change_start_routing(self):
        time_now = datetime.today()
        for record in self:
            if record['start_routing'] and record['start_routing'] < time_now:
                record['start_routing'] = False
                notice = "Date plan is not lower than now! "
                self.env.user.notify_info(message=notice, title=NotificationSocketType.NOTIFICATION.value)

    @api.onchange('company_id')
    def on_change_company_id(self):
        time_now = datetime.today().date()
        for record in self:
            if record['company_id']:
                if record['date_plan'] <= time_now:
                    available = self.env['fleet.vehicle.state'].search(
                        [('name', '=', VehicleStateStatus.AVAILABLE.value)]).id
                    query_vehicle_available = """ 
                                SELECT id FROM public.fleet_vehicle 
                                    where active = True and  company_id =%s and state_id = %s """
                    self.env.cr.execute(query_vehicle_available, (record['company_id'].id, available,))
                    ardata = self.env.cr.dictfetchall()
                    list_vehicle_assignment_id = []
                    for data in ardata:
                        list_vehicle_assignment_id.append(data['id'])
                    return {'domain': {
                        'vehicle_id': [('id', 'in', list_vehicle_assignment_id)]
                    }}
                else:
                    downgraded_state = self.env['fleet.vehicle.state'].search(
                        [('name', '=', VehicleStateStatus.DOWNGRADED.value)]).id
                    query_vehicle_available = """ 
                                SELECT id FROM public.fleet_vehicle 
                                    where active = True and company_id=%s and state_id not in (%s) """
                    self.env.cr.execute(query_vehicle_available, (record['company_id'].id, downgraded_state,))
                    ardata = self.env.cr.dictfetchall()
                    array_vehicle_id = []
                    list_vehicle_assignment_id = []
                    for data in ardata:
                        list_vehicle_assignment_id.append(data['id'])
                    return {'domain': {
                        'vehicle_id': [('id', 'in', list_vehicle_assignment_id)]
                    }}

    @api.onchange('vehicle_id')
    def on_change_vehicle_id(self):
        for record in self:
            if record['vehicle_id']:
                get_driver_query = """
                    select * from fleet_vehicle_assignation_log 
                        where vehicle_id = %s and date_start <= %s and date_end > %s and driver_status = '1'
                """
                self.env.cr.execute(get_driver_query, (record.vehicle_id.id, record.date_plan, record.date_plan,))
                driver = self._cr.dictfetchall()
                if driver:
                    record.driver_id = driver[0]['driver_id']
                    record.create_driver_calendar = True
                else:
                    notice = "You have to create driver calendar before assign routing for vehicle and driver! "
                    self.env.user.notify_info(message=notice, title=NotificationSocketType.NOTIFICATION.value)
                    record.driver_id = False
                    record.create_driver_calendar = False
                    query_driver_available = """ 
                        SELECT id FROM public.fleet_driver
                            where status = 'running' and company_id=%s and employee_type = 'driver'  """
                    self.env.cr.execute(query_driver_available, (record['company_id'].id,))
                    ardata = self.env.cr.dictfetchall()
                    list_driver = []
                    for data in ardata:
                        list_driver.append(data['id'])
                    return {'domain': {
                        'driver_id': [('id', 'in', list_driver)]
                    }}

    @api.onchange('routing_id')
    def _compute_total(self):
        for record in self:
            if record['checking_user_id'] and record['checking_user_id']['id'] != self.env.uid:
                raise ValidationError('You are not authorized this record!')
            if record['id'].origin:
                query = """
                    UPDATE public.sharevan_routing_plan_day set vehicle_id = null, driver_id = null
                        ,routing_vehicle_id = null  
	                WHERE routing_vehicle_id = %s"""
                self.env.cr.execute(query, (self.id.origin,))
                update_list = []
                old_list = []
                remove_list = []
                now_list = []
                if record.routing_note and record.routing_note != '':
                    old_list = record.routing_note.split(',')
                routing_note = ''
                for line in record.routing_id:  # get list now
                    update_list.append(line.id.origin)
                if len(old_list) > 0:  # check old list if exist
                    for old_id in old_list:
                        if int(old_id) not in update_list:
                            remove_list.append(int(old_id))
                for now_id in update_list:
                    get_all_routing_in_zone = """
                        select id from sharevan_routing_plan_day 
                            where id in 
                        (select id from sharevan_routing_plan_day 
                            where id != %s and ship_type = %s and bill_routing_id = 
                        (select bill_routing_id from sharevan_routing_plan_day where id = %s) 
                            and depot_id = %s)     
                    """
                    self.env.cr.execute(get_all_routing_in_zone,
                                        (now_id, ShipType.IN_ZONE.value, now_id,
                                         record['depot_id'].id,))
                    routing_ids = self.env.cr.dictfetchall()
                    if routing_ids:
                        delete_check = False
                        if len(old_list) > 0:
                            for rec in routing_ids:
                                if rec['id'] in remove_list:  # check 1 RPD exist in remove list so remove all bill
                                    delete_check = True
                        if not delete_check:
                            now_list.append(now_id)
                            routing_note += str(now_id) + ','
                            for rec in routing_ids:
                                if rec['id'] not in now_list:
                                    now_list.append(rec['id'])
                                    routing_note += str(rec['id']) + ','
                if routing_note != '':
                    routing_note = routing_note[:-1]
                if len(now_list) > 0:
                    query = """
                        UPDATE public.sharevan_routing_plan_day set routing_vehicle_id = %s,
                            vehicle_id = %s, driver_id = %s ,solution_day_id =%s
                            WHERE date_plan = %s and id ::integer in ("""
                    for id in now_list:
                        query += str(id) + ","
                    query = query[:-1]
                    query += ")"
                    self.env.cr.execute(query,
                                        (self.id.origin, record.vehicle_id.id, record.driver_id.id,
                                         record.solution_day_id.id, record.date_plan,))
                    routing_record = http.request.env['sharevan.routing.plan.day'].search([('id', 'in', now_list)])
                    record.routing_id = routing_record
                else:
                    record.routing_id = False
                record.routing_note = routing_note
        self.env.user.notify_info(message='load_map', title=NotificationSocketType.NOTIFICATION.value)

    @api.model
    def create(self, vals):
        vehicle = self.env['fleet.vehicle'].search([('id', '=', vals['vehicle_id'])])
        vals['routing_code'] = str(vals['date_plan']) + " - " + vehicle['license_plate']
        vals['name'] = vals['routing_code']
        res = super(RoutingVehicle, self).create(vals)
        return res

    def write(self, vals):
        if self.checking_user_id and self.checking_user_id.id != self.env.uid:
            raise ValidationError('You are not authorized this record!')
        # if self.routing_check== True and 'routing_check' not in vals:
        #     raise ValidationError('You have to end check routing before save')
        return super(RoutingVehicle, self).write(vals)

    def send_routing_request_customer_not_found(self):
        record = self.env['sharevan.routing.request'].search([('routing_vehicle_id', '=', self.id)])
        # CREATE NEW SOLUTION DAY TO WAIT FOR SCANNING REQUEST (THE RPD PACKAGE SUCCESS)
        # AND UPDATE SOLUTION DAY OLD ABOUT START ROUTING FOR SCANNED (THE RPD PACKAGE FAIL)
        solution = {
            'name': 'date_plan',
            'date_plan': record['date_plan'],
            'status': '2',
            'group_code': 'default',
        }

    def send_routing_request(self):
        record = self.env['sharevan.routing.vehicle'].search([('id', '=', self.id)])
        # CREATE NEW SOLUTION DAY TO WAIT FOR SCANNING REQUEST (THE RPD PACKAGE SUCCESS)
        # AND UPDATE SOLUTION DAY OLD ABOUT START ROUTING FOR SCANNED (THE RPD PACKAGE FAIL)
        solution = {
            'name': 'date_plan',
            'date_plan': record['date_plan'],
            'status': '2',
            'group_code': 'default',
        }
        solution_record = http.request.env['solution.day'].sudo().create(solution)
        query = """
            update sharevan_routing_plan_day set solution_day_id =%s
                where routing_vehicle_id=%s """
        self.env.cr.execute(query, (solution_record['id'], self.id,))
        update_solution_query = """
            update solution_day set  status = '0'  where id=%s """
        self.env.cr.execute(update_solution_query, (self.solution_day_id.id,))
        record.write({
            'redirect_routing': False,
            'routing_check': False,
            'routing_scanning': True,
            'solution_day_id': solution_record['id']
        })
        url = config['security_url'] + config['routing_host'] + ':' + config[
            'routing_port'] + '/location/assign_routing/nocustomer'
        # payload = {
        #     'routing_vehicle_id': self.id
        # }
        # print(payload)
        # payloadjson = json.dumps(payload, default=date_utils.json_default, skipkeys=True)
        # resps = requests.get(url, params=payload,
        #                      headers={'Content-Type': 'application/json'}).json()
        payload = 'routing_vehicle_id=' + str(self.id)
        resps = requests.post(url, data=payload, headers={'Content-Type': 'application/json'})
        logger.error("Send Routing system for routing vehicle:" + self.name)
        notice = "Please wait for routing scan"
        self.env.user.notify_info(message=notice, title=NotificationSocketType.NOTIFICATION.value)
        self.env.user.notify_info(message='load_map_success', title=NotificationSocketType.NOTIFICATION.value)

    def end_check_routing(self):
        record = self.env['sharevan.routing.vehicle'].search([('id', '=', self.id)])
        solution = {
            'name': 'date_plan',
            'date_plan': record['date_plan'],
            'status': '1',
            'group_code': 'default',
        }
        solution_record = http.request.env['solution.day'].sudo().create(solution)
        query = """
            update sharevan_routing_plan_day set  status = '0', solution_day_id =%s
                where routing_vehicle_id=%s """
        self.env.cr.execute(query, (solution_record['id'], self.id,))
        update_solution_query = """
                    update solution_day set  status = '0'  where id=%s """
        self.env.cr.execute(update_solution_query, (self.solution_day_id.id,))
        record.write({
            'redirect_routing': False,
            'routing_check': False,
            'checking_user_id': False,
            'solution_day_id': solution_record['id']
        })
        self.env.user.notify_info(message='load_map_success', title=NotificationSocketType.NOTIFICATION.value)

    def create_new_calendar_for_vehicle(self):
        for record in self:
            offset = self.env.user.tz_offset
            plus = offset[:1]
            hour = int((offset[1:])[:2])
            date_start = datetime.combine(
                datetime.strptime(str(record['date_plan']) + " 00:00:00", "%Y-%m-%d %H:%M:%S"),
                datetime.min.time()) + timedelta(hours=hour)
            date_end = datetime.combine(datetime.strptime(str(record['date_plan']) + " 00:00:00", "%Y-%m-%d %H:%M:%S"),
                                        datetime.min.time()) + timedelta(hours=(24)) - timedelta(minutes=1)
            rec = self.env['fleet.vehicle.assignation.log'].sudo().create({
                'date_start': date_start,
                'date_end': date_end,
                'driver_id': record['driver_id'].id,
                'vehicle_id': record['vehicle_id'].id,
                'company_id': record['driver_id']['company_id'].id

            })
            if rec:
                notice = "You have created driver calendar successful! "
                self.env.user.notify_info(message=notice, title=NotificationSocketType.NOTIFICATION.value)
            else:
                raise ValidationError('You have create driver calendar fail!')

    #       ẩn nút tạo lịch đi
    @api.depends('toogle')
    def redirect_routing_check(self):
        if self.routing_scanning:
            raise ValidationError('This routing has been scanning! Please waiting response for some minutes')
        if self.redirect_routing:
            result = self.write({
                'redirect_routing': True,
                'routing_check': True,
                'checking_user_id': self.env.uid,
            })
            if result:
                routing_plan_day_records = http.request.env['sharevan.routing.plan.day'].search(
                    [('routing_vehicle_id', '=', self.id)])
                for record in routing_plan_day_records:
                    record.write({'status': RoutingDetailStatus.WaitingApprove.value})
        else:
            solution = {
                'name': self['date_plan'],
                'date_plan': self['date_plan'],
                'status': '2',
                'group_code': 'default',
            }
            solution_record = http.request.env['solution.day'].sudo().create(solution)
            result = self.write({
                'redirect_routing': True,
                'routing_check': True,
                'checking_user_id': self.env.uid,
                'solution_day_id': solution_record['id']
            })
            if result:
                routing_plan_day_records = http.request.env['sharevan.routing.plan.day'].search(
                    [('routing_vehicle_id', '=', self.id)])
                for record in routing_plan_day_records:
                    record.write({
                        'status': RoutingDetailStatus.WaitingApprove.value,
                        'solution_day_id': solution_record['id']
                    })
        self.env.user.notify_info(message='load_map', title=NotificationSocketType.NOTIFICATION.value)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Checking routing ' + self.routing_code,
            'view_mode': 'form',
            'res_model': 'sharevan.routing.vehicle',
            'res_id': self.id,
            'target': 'current',
            'context': {
                'form_view_initial_mode': 'edit',
            },
        }

    # def redirect_routing_request_check(self):
    #     if self.routing_scanning:
    #         raise ValidationError('This routing has been scanning! Please waiting response for some minutes')
    #     routing_request_records = http.request.env['sharevan.routing.request'].search(
    #         [('routing_vehicle_id', '=', self.id)])
    #     for record in routing_request_records:
    #         record.write({
    #             'user_id': self.env.uid
    #         })
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Checking routing vehicle ' + self.name,
    #         'view_mode': 'form',
    #         'res_model': 'sharevan.routing.vehicle',
    #         'res_id': self.id,
    #         'target': 'current',
    #         'context': {
    #             'form_view_initial_mode': 'edit',
    #         },
    #     }


    def reload_routing(self, routing_vehicle_id):
        user_ids = []
        routing_vehicle = http.request.env['sharevan.routing.vehicle'].search(args=[('id', '=', routing_vehicle_id)])

        if not routing_vehicle or not routing_vehicle.routing_scanning:
            logger.warn(
                "Not send message",
                'res.users',
                exc_info=True)
            return Response(response=str('Routing not found'), status=500)
        if routing_vehicle.checking_user_id:
            routing_vehicle.checking_user_id.notify_info(message='load_map',
                                                         title=NotificationSocketType.NOTIFICATION.value)
            user_ids.append(routing_vehicle.checking_user_id.id)
        if routing_vehicle.driver_id:
            user_ids.append(routing_vehicle.driver_id.user_id.id)

        title = "Routing system have scanned routing vehicle successfully!"
        body = "Routing system have scanned routing vehicle successfully! Routing id: " + routing_vehicle.name
        try:
            objct_val = {
                "title": title,
                "name": title,
                "content": body,
                "create_date": datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S"),
                "type": 'routing',
                "image_256": '',
                "click_action": ClickActionType.driver_main_activity.value,
                "message_type": MessageType.success.value,
                "item_id": '',
                "is_read": False
            }
            objct_val = json.dumps(objct_val)
            click_action = ClickActionType.notification_driver.value
            message_type = MessageType.success.value
            item_id = ''
            INSERT_NOTIFICATION_QUERY = """INSERT INTO public.sharevan_notification( title, content, sent_date, type, 
                object_status, click_action, message_type, item_id, create_uid, create_date,status) VALUES ( 
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s) RETURNING id """
            sent_date = datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")
            http.request.cr.execute(INSERT_NOTIFICATION_QUERY, (
                title, body, sent_date, 'routing', ObjectStatus.ReloadRouting.value,
                ClickActionType.driver_main_activity.value, MessageType.success.value, '', 1, sent_date, 'status',))
            result = http.request.env[Notification._name]._cr.fetchall()
            if result[0][0]:
                for rec in user_ids:
                    INSERT_NOTIFICATION_REL_QUERY = """
                            INSERT INTO public.sharevan_notification_user_rel(
                                notification_id, user_id, is_read)
                                VALUES (%s, %s, %s) RETURNING id 
                        """
                    http.request.cr.execute(INSERT_NOTIFICATION_REL_QUERY, (result[0][0], rec, False,))
            FirebaseMessagingAPI. \
                send_message_for_all_normal(ids=user_ids, title=title, body=str(objct_val), short_body=body,
                                            item_id=item_id,
                                            click_action=click_action, message_type=message_type)
            routing_vehicle.write({
                'checking_user_id': False,
                'redirect_routing': False,
                'routing_check': False,
                'routing_scanning': True,
            })
            return Response(response=str('Success'), status=200)
        except:
            logger.warn(
                "Not send message",
                'res.users',
                exc_info=True)
            return Response(response=str('Fail'), status=500)
