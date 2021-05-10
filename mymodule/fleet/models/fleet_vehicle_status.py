import logging
from datetime import datetime, timedelta

import pytz

from mymodule.enum.ClickActionType import ClickActionType
from mymodule.enum.MessageType import MessageType
from mymodule.enum.NotificationType import NotificationType
from mymodule.enum.ObjectStatus import ObjectStatus
from mymodule.enum.RoutingDetailStatus import RoutingDetailStatus
from mymodule.enum.VehicleStateStatus import VehicleStateStatus
from odoo import api, models, fields, _, http
from odoo.addons.base.models.ir_attachment import IrAttachment
from odoo.exceptions import ValidationError

logger = logging.getLogger(__name__)


class FleetVehicleStatus(models.Model):
    _name = 'fleet.vehicle.status'
    _description = 'Fleet vehicle status'
    _order = "create_date desc"

    # name = fields.Many2one('fleet.vehicle', string="Name", required=True)
    code_name = fields.Char(string='Code name', copy=False, readonly=True, index=True,
                            default=lambda self: _('New'))
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle", required=True)
    name = fields.Char(string="name", related='vehicle_id.name')
    driver_id = fields.Many2one('fleet.driver', string="Driver", required=True)
    assignation_log_id = fields.Many2one('fleet.vehicle.assignation.log', string="Assign log", required=True)
    company_id = fields.Many2one('res.company_id', string="Company")
    equipment_log_line = fields.One2many('fleet.driver.equipment.log', 'assignation_log_id', string="Attach File",
                                         readonly=True)
    toogle = fields.Boolean('toogle', default=True)
    status_domain = fields.Boolean('status', default=True)
    status = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted')], 'Status', default="deleted")
    attach_File = fields.Many2many('ir.attachment', string="Attach File")

    delivery_receipt_vehicles = fields.Selection([('Confirm vehicle handing', 'Confirm vehicle handing'),
                                                  ('Confirm receive the car', 'Confirm receive the car')])
    description = fields.Char(string="Description")
    date_start = fields.Datetime(string="Start Date")
    date_end = fields.Datetime(string="End Date")
    date_driver_receives = fields.Datetime(string="Date driver receives")
    date_driver_returns = fields.Datetime(string="Date driver return")

    @api.model
    def create(self, vals):

        if vals.get('code_name', 'New') == 'New':
            vals['code_name'] = self.env['ir.sequence'].next_by_code(
                'fleet.vehicle.status') or 'New'

        res = super(FleetVehicleStatus, self).create(vals)
        return res

    def check_driver_assign_log_confirm_receive_allow(self, assignation_log_id):
        self.env.cr.execute("""
            select log_all.assignation_log_code, log_all.date_start,log_all.date_end, driver.name from fleet_vehicle_assignation_log log_all
                join (select * from fleet_vehicle_assignation_log where id = %s) now_log
                    on now_log.vehicle_id = log_all.vehicle_id
                join fleet_driver driver on driver.id = log_all.driver_id 
            where log_all.driver_status ='1' and log_all.give_car_back is  null 
                and log_all.id != %s and log_all.date_start < CURRENT_DATE +1 
                """, (str(assignation_log_id), str(assignation_log_id),))
        result = self._cr.dictfetchall()
        if result:
            first_message = "Please finish driver calendar code: "
            message=''
            for rec in result:
                message += rec['assignation_log_code'] + " ( Driver: " + \
                           rec['name'] + ", start date: " + str(rec['date_start']) + ", end date: " + str(
                    rec['date_end']) + ")"
            print(first_message + message)
            logger.warn(
                first_message + message,
                self._name, assignation_log_id,
                exc_info=True)
            return {
                'status': 1001,
                'message': message
            }
        else:
            return {
                'status': 200,
                'message': ''
            }

    @api.depends('toogle')
    def vehicle_handing(self):
        vehicle_id = int(self.vehicle_id)
        driver_id = int(self.driver_id)
        date_start = self.date_start
        date_end = self.date_end
        check_result = self.check_driver_assign_log_confirm_receive_allow(self.assignation_log_id.id)
        if check_result['status'] != 200:
            raise ValidationError(check_result['message'])
        self.env.cr.execute("""Update fleet_vehicle_status Set toogle = false , status = 'deleted' where id = %s  """,
                            (str(self.id),))

        date_current = datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")
        veh_id = self.env['fleet.vehicle.state'].search([('code', '=', VehicleStateStatus.Shipping.value)]).id
        self.env.cr.execute("""UPDATE fleet_vehicle SET state_id = %s  WHERE id = %s """,
                            (veh_id, str(vehicle_id),))
        self.env.cr.execute("""UPDATE fleet_vehicle_assignation_log SET receive_car = %s  WHERE id = %s 
        """,
                            (str(date_current)[:19], self.assignation_log_id.id,))
        self.env.cr.execute("""
                    select user_id from fleet_driver where id = %s
                    """, (driver_id,))
        driver = self._cr.dictfetchall()
        title = 'You have received the car successfully!'
        body = 'The manage have accept your request!'
        if driver:
            try:
                val = {
                    'user_id': [driver[0]['user_id']],
                    'title': title,
                    'content': body,
                    'click_action': ClickActionType.driver_vehicle_check_point.value,
                    'message_type': MessageType.danger.value,
                    'type': NotificationType.RoutingMessage.value,
                    'object_status': ObjectStatus.ManagerApprovedCar.value,
                    'item_id': self['id'],
                }
                http.request.env['sharevan.notification'].create(val)
                return {'type': 'ir.actions.act_window', 'name': 'Vehicle status', 'res_model': 'fleet.vehicle.status',
                        'view_type': 'form', 'view_mode': 'tree,form', 'target': '', }
            except:
                logger.warn(
                    "Accept handling car successful! But can not send message",
                    'fleet.vehicle.status', self['id'],
                    exc_info=True)
                return {'type': 'ir.actions.act_window', 'name': 'Vehicle status', 'res_model': 'fleet.vehicle.status',
                        'view_type': 'form', 'view_mode': 'tree,form', 'target': '', }
        else:
            logger.warn(
                "Accept handling car successful! But can not send message",
                'fleet.vehicle.status', self['id'],
                exc_info=True)
            return {'type': 'ir.actions.act_window', 'name': 'Vehicle status', 'res_model': 'fleet.vehicle.status',
                    'view_type': 'form', 'view_mode': 'tree,form', 'target': '', }

    @api.depends('toogle')
    def receive_the_car(self):
        vehicle_id = int(self.vehicle_id)
        driver_id = int(self.driver_id)
        date_start = self.date_start
        date_end = self.date_end
        self.env.cr.execute("""Update fleet_vehicle_status Set toogle = true ,  status = 'deleted'   where id = %s  """,
                            (str(self.id),))

        assig_id = self.env['fleet.vehicle.assignation.log'].search(
            [('id', '=', self.assignation_log_id.id)])

        self.env.cr.execute(""" 
            SELECT json_agg(t)
              FROM (SELECT ir_attachment_id
                    FROM fleet_vehicle_status_ir_attachment_rel
                    WHERE fleet_vehicle_status_id = %s
                ) t ;""", (self['id'],))
        result = self._cr.fetchall()
        res = result[0][0]
        id_image = []
        if res:
            for re in res:
                id_image.append(re['ir_attachment_id'])
            for image in id_image:
                image_obj = self.env[IrAttachment._name].search([('id', '=', assig_id['id'])])
                image_obj.write({
                    'res_model': 'fleet.vehicle.assignation.log'
                })
                INSERT_QUERY = """INSERT INTO fleet_vehicle_assignation_log_ir_attachment_rel
                                                           VALUES ( %s , %s ) """
                http.request.cr.execute(INSERT_QUERY, (self.assignation_log_id.id, image,))

        self.env.cr.execute(""" 
            DELETE FROM
                fleet_vehicle_status_ir_attachment_rel
            WHERE fleet_vehicle_status_id = %s;
                """, (self['id'],))
        date_start =assig_id['date_start']
        date_current = datetime.utcnow()
        time_delta = (date_current - date_start)
        total_seconds = time_delta.total_seconds()
        minutes = total_seconds / 60
        veh_id = self.env['fleet.vehicle.state'].search([('code', '=', VehicleStateStatus.Available.value)]).id
        vehicle_record= self.env['fleet.vehicle'].search([('id', '=', vehicle_id)])
        running_time = vehicle_record['amortization_period']
        running_time+= minutes
        vehicle_record.write({
            'state_id': veh_id,
            'amortization_period':running_time
        })
        # self.env.cr.execute("""UPDATE fleet_vehicle SET state_id = %s ,  WHERE id = %s """,
        #                     (veh_id, str(vehicle_id),))
        self.env.cr.execute("""UPDATE fleet_vehicle_assignation_log SET give_car_back = %s ,date_end = %s WHERE 
                            id = %s  
                """,
                            (str(date_current)[:19], str(date_current)[:19], self.assignation_log_id.id,))
        self.env.cr.execute("""
                            select user_id from fleet_driver where id = %s
                            """, (driver_id,))
        driver = self._cr.dictfetchall()
        title = 'You have returned the car successfully!'
        body = 'The manage have accept your request!'
        if driver:
            try:
                val = {
                    'user_id': [driver[0]['user_id']],
                    'title': title,
                    'content': body,
                    'click_action': ClickActionType.driver_main_activity.value,
                    'message_type': MessageType.danger.value,
                    'type': NotificationType.RoutingMessage.value,
                    'object_status': ObjectStatus.ManagerApprovedCar.value,
                    'item_id': assig_id['id'],
                }
                http.request.env['sharevan.notification'].create(val)
                return {'type': 'ir.actions.act_window', 'name': 'Vehicle status', 'res_model': 'fleet.vehicle.status',
                        'view_type': 'form', 'view_mode': 'tree,form', 'target': '', }
            except:
                logger.warn(
                    "Accept return car successful! But can not send message",
                    'fleet.vehicle.status', assig_id,
                    exc_info=True)
                return {'type': 'ir.actions.act_window', 'name': 'Vehicle status', 'res_model': 'fleet.vehicle.status',
                        'view_type': 'form', 'view_mode': 'tree,form', 'target': '', }
        else:
            logger.warn(
                "Accept return car successful! But can not send message",
                'fleet.vehicle.status', assig_id,
                exc_info=True)
            return {'type': 'ir.actions.act_window', 'name': 'Vehicle status', 'res_model': 'fleet.vehicle.status',
                    'view_type': 'form', 'view_mode': 'tree,form', 'target': '', }


class VehicleEquipmentDriver(models.Model):
    _name = 'fleet.driver.equipment.log'
    _description = 'Driver equipment'

    assignation_log_id = fields.Many2one('fleet.vehicle.assignation.log', string='Assignation Logs')
    equipment_id = fields.Many2one('fleet.driver.equipment.part', string='Equipment')
    quantity_take = fields.Integer('Quantity received', default=0)
    quantity_return = fields.Integer('Quantity return', default=0)
    equipment_part_code = fields.Char('code', related="equipment_id.equipment_part_code")
    unit_measure = fields.Selection('unit measure', related="equipment_id.unit_measure")
    name = fields.Char('name', related="equipment_id.name")
    uri_path = fields.Char('name', store=False)
    isselect = fields.Char('isselect', store=False)
