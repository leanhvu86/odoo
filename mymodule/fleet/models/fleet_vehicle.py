# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import datetime, timedelta, date, timezone

import pytz
from dateutil.relativedelta import relativedelta

from mymodule.enum.ClickActionType import ClickActionType
from mymodule.enum.StageMaintenanceType import StageMaintenanceType
from mymodule.enum.StatusType import StatusType
from mymodule.enum.VehicleStateStatus import VehicleStateStatus
from odoo import api, fields, models, _, http
from odoo.exceptions import ValidationError
from odoo.osv import expression
from .utils import validate_utils as validate
from ...base_next.controllers.api.base_method import BaseMethod
from ...base_next.models.notification import Notification
from ...base_next.models.utils import fleet_util
from ...constants import Constants
from ...enum.MessageType import MessageType, NotificationSocketType
from ...enum.NotificationType import NotificationType
from ...enum.RoutingDetailStatus import RoutingDetailStatus
from ...enum.ObjectStatus import ObjectStatus
from ...enum.VehicleConfirmStatus import VehicleConfirmStatus
from ...enum.VehicleSosType import VehicleSosType

logger = logging.getLogger(__name__)


class FleetVehicleHistory(models.Model):
    _name = 'fleet.vehicle.history'
    _description = 'Vehicle'

    name = fields.Char(compute="_compute_vehicle_name", store=True)
    active = fields.Boolean('Active', default=True, tracking=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company,
                                 domain=lambda self: [('company_type', '=', 0), ('id', 'in', self.env.companies.ids)])
    parking_point_id = fields.Many2one('parking.point', 'Parking point',
                                       domain="[('status', '=', 'running')]", required=True)

    license_plate = fields.Char(tracking=True, required=True,
                                help='License plate number of the vehicle (i = plate number for a car)')
    vin_sn = fields.Char('Chassis Number', help='Unique number written on the vehicle motor (VIN/SN number)',
                         copy=False, required=True)
    attach_File = fields.Many2many('ir.attachment', string="Attach File")
    uniqueid = fields.Char('IMEI', help='Uniqueid number imei hub iot', required=True)
    cost_per_unit = fields.Float('Cost per distance', required=True)
    model_id = fields.Many2one('fleet.vehicle.model', 'Model',
                               tracking=True, required=True, help='Model of the vehicle')
    manager_id = fields.Many2one('res.users', related='model_id.manager_id')
    brand_id = fields.Many2one('fleet.vehicle.model.brand', 'Brand', related="model_id.brand_id", store=True,
                               readonly=False)

    tonnage_id = fields.Many2one('sharevan.tonnage.vehicle', 'Vehicle tonnage',
                                 help='Tonnage of the vehicle', store=True)
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle tonnage',
                                 help='Tonnage of the vehicle', store=True)
    state_id = fields.Integer(string="State")
    max_tonnage_id = fields.Float('Vehicle tonnage', related='model_id.tonnage_id.max_tonnage')
    # ,copy=True,

    # auto_join=True)

    cost_count = fields.Integer( string="Costs")
    contract_count = fields.Integer(string='Contract Count')
    route_count = fields.Integer(string='Route Count', default=0)
    service_count = fields.Integer( string='Services')
    fuel_logs_count = fields.Integer( string='Fuel Log Count')
    equipment_part_count = fields.Integer( string='Equipment Part Count')
    odometer_count = fields.Integer( string='Odometer count')
    history_count = fields.Integer(string="Drivers History Count")
    maintenance_count = fields.Integer( string="Maintenance Count")
    maintenance_level = fields.Integer( string="Maintenance Level", default=0)
    maintenance_priority = fields.Boolean( string="Maintenance Priority", default=False)
    location_log = fields.Char(string='Location log')
    next_assignation_date = fields.Date('Next available date',
                                        help='This is the date at which the car will be available, '
                                             'if not set it means currently available')
    line_vehicle_insurance = fields.One2many('fleet.vehicle.paper.log', 'vehicle', string='Paper',
                                             copy=True, readonly=False,
                                             domain=[('status', '=', 'running')])
    acquisition_date = fields.Date('Acquisition Date', required=False,
                                   default=fields.Date.today, help='Date when the vehicle has been acquired')
    first_contract_date = fields.Date(string="First Contract Date", default=fields.Date.today)
    from_date = fields.Date(string="First Contract Date", default=fields.Date.today)
    to_date = fields.Date(string="First Contract Date", default=fields.Date.today)
    last_maintenance = fields.Date(string='Date of last maintenance', default=fields.Date.today)
    maintenance_schedule = fields.Many2one('fleet.maintenance.schedule', 'Maintenance schedule',
                                           domain=[('status', '=', '1')])
    sos_status = fields.Selection([
        ('0', 'No sos'),
        ('1', 'Low sos'),
        ('2', 'High sos')
    ], 'Sos type', default='0', help='Sos level', required=True)
    sim_number = fields.Char('SIM number')
    update_description = fields.Char('update description')
    amortization_period = fields.Float('Amortization period', help='Time using car', default=0.0)
    activity_duration_average = fields.Float('Amortization period', help='Activity duration car average per day',
                                              default=0.0)
    priority = fields.Selection([
        ('1', 'Bad'),
        ('2', 'Low'),
        ('3', 'Normal'),
        ('4', 'Good'),
        ('5', 'Perfect')
    ], 'Company type', default='3', help='Priority', required=True)
    active_type = fields.Selection([
        ('fleet', 'Fleet'),
        ('code_share', 'Code share'),
        ('market_place', 'Market place')
    ], 'Active type', default='fleet', help='Active type', required=True)

    approved_check = fields.Selection([
        ('waiting', 'Waiting'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected')
    ], 'Approved', default='waiting', help='Approved type', required=True)


class FleetVehicle(models.Model):
    _inherit = ['fleet.vehicle', 'mail.thread', 'mail.activity.mixin']
    _name = 'fleet.vehicle'
    _description = 'Vehicle'
    _order = 'license_plate asc, acquisition_date asc'

    name = fields.Char(compute="_compute_vehicle_name", store=True)
    att_line = fields.One2many('vehicle.att.line', 'vehicle_id', string='Attribute Lines',
                               domain=[('status', '=', 'running')], copy=True, readonly=False)
    active = fields.Boolean('Active', default=True, tracking=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company,
                                 domain=lambda self: [('company_type', '=', 0), ('id', 'in', self.env.companies.ids)])
    parking_point_id = fields.Many2one('parking.point', 'Parking point',
                                       domain="[('status', '=', 'running')]", required=True)

    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    license_plate = fields.Char(tracking=True, required=True,
                                help='License plate number of the vehicle (i = plate number for a car)')
    vin_sn = fields.Char('Chassis Number', help='Unique number written on the vehicle motor (VIN/SN number)',
                         copy=False, required=True)
    attach_File = fields.Many2many('ir.attachment', string="Attach File")
    uniqueid = fields.Char('IMEI', help='Uniqueid number imei hub iot', required=True)
    cost_per_unit = fields.Float('Cost per distance', required=True)
    model_id = fields.Many2one('fleet.vehicle.model', 'Model',
                               tracking=True, required=True, help='Model of the vehicle')
    manager_id = fields.Many2one('res.users', related='model_id.manager_id')
    brand_id = fields.Many2one('fleet.vehicle.model.brand', 'Brand', related="model_id.brand_id", store=True,
                               readonly=False)

    equipmentPart_line = fields.One2many('fleet.vehicle.equipment.part', 'vehicle_id', string='equiment part',
                                         domain=[('status', '=', 'running')], copy=True)
    insurance_line = fields.One2many('sharevan.insurance', 'vehicle_id', string='Insurance',
                                     domain=[('status', '=', 'running')], copy=True)
    tonnage_id = fields.Many2one('sharevan.tonnage.vehicle', 'Vehicle tonnage',
                                 help='Tonnage of the vehicle', store=True)
    max_tonnage_id = fields.Float('Vehicle tonnage', related='model_id.tonnage_id.max_tonnage')
    # ,copy=True,

    # auto_join=True)

    tires = fields.Many2one('fleet.vehicle.equipment.part', string='Tires')
    lazang = fields.Many2one('fleet.vehicle.equipment.part', string='LaZang')
    airCleaner = fields.Many2one('fleet.vehicle.equipment.part', string='Air cleaner')

    log_drivers = fields.One2many('fleet.vehicle.assignation.log', 'vehicle_id', string='Assignation Logs')
    log_fuel = fields.One2many('fleet.vehicle.log.fuel', 'vehicle_id', 'Fuel Logs')
    log_services = fields.One2many('fleet.vehicle.log.services', 'vehicle_id', 'Services Logs')
    log_contracts = fields.One2many('fleet.vehicle.log.contract', 'vehicle_id', 'Contracts')
    cost_count = fields.Integer(compute="_compute_count_all", string="Costs")
    contract_count = fields.Integer(compute="_compute_count_all", string='Contract Count')
    route_count = fields.Integer(compute="_compute_count_all", string='Route Count', default=0)
    service_count = fields.Integer(compute="_compute_count_all", string='Services')
    fuel_logs_count = fields.Integer(compute="_compute_count_all", string='Fuel Log Count')
    equipment_part_count = fields.Integer(compute="_compute_count_all", string='Equipment Part Count')
    odometer_count = fields.Integer(compute="_compute_count_all", string='Odometer count')
    history_count = fields.Integer(compute="_compute_count_all", string="Drivers History Count")
    maintenance_count = fields.Integer(compute="_compute_count_all", string="Maintenance Count")
    maintenance_level = fields.Integer(compute="_compute_count_all", string="Maintenance Level", default=0)
    maintenance_priority = fields.Boolean(compute="_compute_count_all", string="Maintenance Priority", default=False)
    location_log = fields.Char(string='Location log')
    next_assignation_date = fields.Date('Next available date',
                                        help='This is the date at which the car will be available, '
                                             'if not set it means currently available')
    line_vehicle_insurance = fields.One2many('fleet.vehicle.paper.log', 'vehicle', string='Paper',
                                             copy=True, readonly=False,
                                             domain=[('status', '=', 'running')])
    acquisition_date = fields.Date('Acquisition Date', required=False,
                                   default=fields.Date.today, help='Date when the vehicle has been acquired')
    first_contract_date = fields.Date(string="First Contract Date", default=fields.Date.today)
    last_maintenance = fields.Date(string='Date of last maintenance', default=fields.Date.today)
    maintenance_schedule = fields.Many2one('fleet.maintenance.schedule', 'Maintenance schedule',
                                           domain=[('status', '=', '1')])
    sos_status = fields.Selection([
        ('0', 'No sos'),
        ('1', 'Low sos'),
        ('2', 'High sos')
    ], 'Sos type', default='0', help='Sos level', required=True)

    # Thom bo sung
    manager_parent_id = fields.One2many(Constants.PARTNER_VEHICLE, 'vehicle_id',
                                        domain=lambda self: [("company_id", "=", self.env.company.id)])
    sim_number = fields.Char('SIM number')
    update_description = fields.Char('update description')
    amortization_period = fields.Float('Amortization period', help='Time using car', default=0.0)
    activity_duration_average = fields.Float('Amortization period', help='Activity duration car average per day',
                                             compute="_compute_count_all", default=0.0)
    priority = fields.Selection([
        ('1', 'Bad'),
        ('2', 'Low'),
        ('3', 'Normal'),
        ('4', 'Good'),
        ('5', 'Perfect')
    ], 'Company type', default='3', help='Priority', required=True)
    active_type = fields.Selection([
        ('fleet', 'Fleet'),
        ('code_share', 'Code share'),
        ('market_place', 'Market place')
    ], 'Active type', default='fleet', help='Active type', required=True)

    approved_check = fields.Selection([
        ('waiting', 'Waiting'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected')
    ], 'Approved', default='waiting', help='Approved type', required=True)

    def accept_vehicle(self):
        create_user = 0
        vehicle_id = 0
        for record in self:
            create_user = record['create_uid']
            vehicle_id = record['id']
            record.write({'approved_check': VehicleConfirmStatus.Accepted.value})
        test_msg = {"message": "Accept vehicle successfully! ", "title": "Accept vehicle to join Code share system",
                    "sticky": True}
        self.env.user.notify_success(**test_msg)
        val = {
            'user_id': [create_user.id],
            'title': 'Accept vehicle to join Code share system',
            'content': 'Accept vehicle successfully!',
            'click_action': ClickActionType.routing_plan_day_driver.value,
            'message_type': MessageType.success.value,
            'type': NotificationType.RoutingMessage.value,
            'object_status': RoutingDetailStatus.Done.value,
            'item_id': vehicle_id,
        }
        http.request.env['sharevan.notification'].create(val)
        return self

    def reject_vehicle(self):
        create_user = 0
        vehicle_id = 0
        for record in self:
            create_user = record['create_uid']
            vehicle_id = record['id']
            record.write({'approved_check': VehicleConfirmStatus.Reject.value})
        test_msg = {"message": "Reject vehicle successfully! ", "title": "Reject vehicle to join Code share system",
                    "sticky": True}
        self.env.user.notify_success(**test_msg)
        val = {
            'user_id': [create_user.id],
            'title': 'Reject vehicle to join Code share system',
            'content': 'Vehicle has been reject to join system!',
            'click_action': ClickActionType.routing_plan_day_driver.value,
            'message_type': MessageType.success.value,
            'type': NotificationType.RoutingMessage.value,
            'object_status': RoutingDetailStatus.Done.value,
            'item_id': vehicle_id,
        }
        http.request.env['sharevan.notification'].create(val)
        return self

    _sql_constraints = [
        ('license_plate', 'unique (license_plate)', 'License plate must be unique!'),
        ('vin_sn', 'UNIQUE (vin_sn)', 'Chassis Number already exists'),
        ('uniqueid', 'UNIQUE (uniqueid)', 'IMEI already exists'),
        ('sim_number', 'UNIQUE (sim_number)', 'SIM number already exists!')
    ]

    @api.onchange('iot_type')
    def _onchange_iot(self):
        if not self.iot_type:
            self.uniqueid = fleet_util.get_imei()
        else:
            self.uniqueid = None

    @api.onchange('equipment_part_count')
    def _change_equip(self):
        return {'domain': {'state_id': [('name', 'in', ('Available',))]}}

    # def _domain_color(self):
    #     appParamId = 0
    #     paramGroups = self.env['fleet.param.group']
    #     appParams = self.env['fleet.app.param']
    #     paramGroup = paramGroups.search([('name', '=', 'VEHICLE')], limit=1)
    #     if paramGroup:
    #         appParam = appParams.search([('group_id', '=', paramGroup.id), ('name', '=', 'COLOR')], limit=1)
    #         if appParam:
    #             appParamId = appParam.id
    #     return [('param_id', '=', appParamId)]

    color = fields.Many2one('fleet.color', string='Color', store=True)

    state_id = fields.Many2one('fleet.vehicle.state', 'Vehicle status',
                               compute="_compute_state_id",
                               help='Current status of the vehicle', store=True, require=True)

    def is_equipmentpart_exist(self, vehicle):
        equipmentCount = self.env['fleet.vehicle.equipment.part'].search_count(
            [('vehicle_id', '=', vehicle.id), ('status', '=', StatusType.Running.value)])
        return equipmentCount

    location = fields.Char(help='Location of the vehicle (garage, ...)')
    seats = fields.Integer('Seats Number', help='Number of seats of the vehicle')
    model_year = fields.Integer('Model Year', help='Year of the model')
    doors = fields.Integer('Doors Number', help='Number of doors of the vehicle', default=5)
    tag_ids = fields.Many2many('fleet.vehicle.tag', 'fleet_vehicle_vehicle_tag_rel', 'vehicle_tag_id', 'tag_id', 'Tags',
                               copy=False)
    odometer = fields.Float(compute='_get_odometer', inverse='_set_odometer', string='Odometer',
                            help='Odometer measure of the vehicle at the moment of this log', digits=(12, 2))
    last_odometer = fields.Float(string='Last odometer',
                                 help='Odometer since last maintenance', digits=(12, 2), default='0.0')
    odometer_unit = fields.Selection([
        ('kilometers', 'Kilometers'),
        ('miles', 'Miles')
    ], 'Odometer Unit', default='kilometers', help='Unit of the odometer ', required=True)
    transmission = fields.Selection([('manual', 'Manual'), ('automatic', 'Automatic')], 'Transmission',
                                    help='Transmission Used by the vehicle')
    fuel_type = fields.Selection([
        ('gasoline', 'Gasoline'),
        ('diesel', 'Diesel'),
        ('lpg', 'LPG'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid')
    ], 'Fuel Type', help='Fuel Used by the vehicle')
    horsepower = fields.Integer()

    horsepower_tax = fields.Float('Horsepower Taxation')
    power = fields.Integer('Power', help='Power in kW of the vehicle')
    co2 = fields.Float('CO2 Emissions', help='CO2 emissions of the vehicle')

    image_128 = fields.Char("Image massage", max_width=256, max_height=256, compute='_compute_count_all')
    image_1920 = fields.Image("License Plate Image ", max_width=256, max_height=256, required=True)
    driver_name = fields.Char("String", compute='_compute_count_all')

    vehicle_registration_front_image = fields.Image("Vehicle registration front", max_width=128, max_height=128)
    vehicle_registration_after_image = fields.Image("Vehicle registration after", max_width=128, max_height=128)
    certificate_of_registry_after_image = fields.Image("Registration of certificate (back)", max_width=128,
                                                       max_height=128)
    certificate_of_registry_front_image = fields.Image("Registration of certificate (front)", max_width=128,
                                                       max_height=128)
    contract_renewal_due_soon = fields.Boolean(compute='_compute_contract_reminder',
                                               search='_search_contract_renewal_due_soon',
                                               string='Has Contracts to renew', multi='contract_info')
    contract_renewal_overdue = fields.Boolean(compute='_compute_contract_reminder',
                                              search='_search_get_overdue_contract_reminder',
                                              string='Has Contracts Overdue', multi='contract_info')
    contract_renewal_name = fields.Text(compute='_compute_contract_reminder', string='Name of contract to renew soon',
                                        multi='contract_info')
    contract_renewal_total = fields.Text(compute='_compute_contract_reminder',
                                         string='Total of contracts due or overdue minus one',
                                         multi='contract_info')
    car_value = fields.Float(string="Catalog Value (VAT Incl.)", help='Value of the bought vehicle')
    net_car_value = fields.Float(string="Purchase Value", help="Purchase Value of the car")
    residual_value = fields.Float()
    plan_to_change_car = fields.Boolean(store=True, readonly=False)
    latitude = fields.Float(string='Latitude', digits=(9, 6))
    longitude = fields.Float(string='Longitude', digits=(9, 6))
    warranty_name1 = fields.Char(string='Warranty name 1')
    warranty_date1 = fields.Date(string='Warranty date 1', help='Date when the cost has been executed')
    warranty_meter1 = fields.Float()
    warranty_name2 = fields.Char(string='Warranty name 2')
    warranty_date2 = fields.Date(string='Warranty date 2')
    warranty_meter2 = fields.Float()
    vehicle_inspection = fields.Char(string='Vehicle inspection')
    inspection_date = fields.Date(string='Inspection date')
    inspection_due_date = fields.Date(string='Inspection due date')
    available_capacity = fields.Float("Available capacity")
    # status_available = fields.Selection(
    #     [('unavailable', 'Unavailable'),
    #      ('available', 'Available')],
    #     string='Available status')
    vehicle_registration = fields.Char()
    registration_date = fields.Date(string='Registration date')
    description = fields.Text(string="Description")
    create_user = fields.Char()
    update_date = fields.Date()
    update_user = fields.Char()
    min_capacity = fields.Float("Min capacity")
    capacity = fields.Float("Maximum capacity")
    cost = fields.Float('Operating cost')
    cost_center = fields.Integer()
    maintenance_template_id = fields.Integer()
    axle = fields.Float()
    tire_front_size = fields.Float()
    tire_front_pressure = fields.Float()
    tire_rear_size = fields.Float()
    tire_rear_pressure = fields.Float()
    body_length = fields.Float()
    body_width = fields.Float()
    height = fields.Float()
    vehicle_type = fields.Many2one('fleet.vehicle.type', string='Vehicle type',
                                   domain=lambda self: "[('status','=','running')]", required=True)
    engine_size = fields.Float()

    positionid = fields.Integer('Poisition Id')
    attributes = fields.Char('Attribute')

    overall_dimensions = fields.Char(String='Overall dimensions')
    dimensions_inside_box = fields.Char(String='Dimensions inside the box')
    standard_long = fields.Char(String='The standard long')
    engine_name = fields.Char(String='Engine name')
    number_cylinders = fields.Char(String='Number cylinders')

    @api.onchange('capacity')
    def onchange_capacity(self):
        self.available_capacity = self.capacity

    @api.onchange('vehicle_registration_front_image')
    def _onchange_vehicle_registration_front_image(self):
        for record in self:
            print(record)

    @api.onchange('vehicle_registration_after_image')
    def _onchange_vehicle_registration_after_image(self):
        for record in self:
            print(record)

    @api.onchange('image_1920')
    def _onchange_image_1920(self):
        for record in self:
            print(record)

    @api.onchange('registration_date')
    def onchange_registration_date(self):
        for record in self:
            if record['registration_date']:
                from_date = datetime.strptime(str(record['registration_date']), '%Y-%m-%d')
                to_date = datetime.now()
                if int((to_date - from_date).days) > 7300:
                    notice = 'registration date is longer than 20 years'
                    record.update({'registration_date': False})
                    self.env.user.notify_danger(message=notice, title=NotificationSocketType.NOTIFICATION.value)

    @api.onchange('model_id')
    def onchange_model_id(self):
        self.seats = self.model_id.seats
        self.capacity = self.model_id.capacity
        self.min_capacity = self.model_id.capacity
        self.tonnage_id = self.model_id.tonnage_id
        self.horsepower = self.model_id.horsepower
        self.engine_size = self.model_id.engine_size
        self.overall_dimensions = self.model_id.overall_dimensions
        self.dimensions_inside_box = self.model_id.dimensions_inside_box
        self.standard_long = self.model_id.standard_long
        self.engine_name = self.model_id.engine_name
        self.number_cylinders = self.model_id.number_cylinders
        self.color = self.model_id.color['id']
        self.model_year = self.model_id.model_year
        self.vehicle_type = self.model_id.vehicle_type['id']
        self.fuel_type = self.model_id.fuel_type

    @api.onchange('odometer_unit')
    def onchange_odometer_unit(self):
        if self.odometer == 0:
            return 0
        if self.odometer_unit == 'miles':
            self.odometer = self.odometer * 1.609344
        if self.odometer_unit == 'kilometers':
            self.odometer = self.odometer * 0.621371192

    @api.depends('model_id.brand_id.name', 'model_id.name', 'license_plate')
    def _compute_vehicle_name(self):
        for record in self:
            record.name = (record.model_id.brand_id.name or '') + '/' + (record.model_id.name or '') + '/' + (
                    record.license_plate or _('No Plate'))

    @api.onchange('acquisition_date')
    def _onchange_acquisition_date(self):
        for record in self:
            if record.acquisition_date > datetime.today().date():
                record.acquisition_date = datetime.today().date()

    @api.onchange('model_year')
    def _onchange_model_year(self):
        for record in self:
            if record.model_year and record.model_year > datetime.today().year:
                record.model_year = datetime.today().year

    # @api.depends('equipmentPart_line')
    # def _set_default_equipment(self):

    # def unlink(self):
    #     for FleetVehicleEquipmentPart in self:
    #         equitmentPart = self.env['fleet.vehicle.equipment.part'].search(['id', '=', self.id])
    #         equitmentPart.unlink()
    #     return super(FleetVehicleEquipmentPart, self).unlink()

    def _get_odometer(self):
        FleetVehicalOdometer = self.env['fleet.vehicle.odometer']
        for record in self:
            vehicle_odometer = FleetVehicalOdometer.search([('vehicle_id', '=', record.id)], limit=1,
                                                           order='value desc')
            if vehicle_odometer:
                record.odometer = vehicle_odometer.value
            else:
                record.odometer = 0

    def _set_odometer(self):
        for record in self:
            if record.odometer:
                date = fields.Date.context_today(record)
                data = {'value': record.odometer, 'date': date, 'vehicle_id': record.id}
                self.env['fleet.vehicle.odometer'].create(data)

    def _compute_count_all(self):
        # stage maintenance
        newStage = self.env['sharevan.maintenance.stage'].search([('code', '=', StageMaintenanceType.New.value)],
                                                                 limit=1).id
        progressStage = self.env['sharevan.maintenance.stage'].search(
            [('code', '=', StageMaintenanceType.Progress.value)], limit=1).id
        repairedStage = self.env['sharevan.maintenance.stage'].search(
            [('code', '=', StageMaintenanceType.Repaired.value)], limit=1).id
        scrapStage = self.env['sharevan.maintenance.stage'].search([('code', '=', StageMaintenanceType.Scrap.value)],
                                                                   limit=1).id
        # state vehicle

        availableState = self.env['fleet.vehicle.state'].search([('code', '=', VehicleStateStatus.Available.value)],
                                                                limit=1).id
        downgradedState = self.env['fleet.vehicle.state'].search([('code', '=', VehicleStateStatus.Downgraded.value)],
                                                                 limit=1).id
        maintenanceState = self.env['fleet.vehicle.state'].search([('code', '=', VehicleStateStatus.Maintenance.value)],
                                                                  limit=1).id

        Odometer = self.env['fleet.vehicle.odometer']
        LogFuel = self.env['fleet.vehicle.log.fuel']
        LogService = self.env['fleet.vehicle.log.services']
        LogContract = self.env['fleet.vehicle.log.contract']
        Cost = self.env['fleet.vehicle.cost']
        EquipmentPart = self.env['fleet.vehicle.equipment.part']
        Maintance = self.env['sharevan.maintenance.request']
        Route = self.env['fleet.vehicle.odometer']
        for record in self:
            record.odometer_count = Odometer.search_count([('vehicle_id', '=', record.id)])
            record.fuel_logs_count = LogFuel.search_count([('vehicle_id', '=', record.id)])
            record.service_count = LogService.search_count([('vehicle_id', '=', record.id)])
            record.equipment_part_count = EquipmentPart.search_count(
                [('vehicle_id', '=', record.id), ('status', '=', 'running')])
            record.contract_count = LogContract.search_count(
                [('vehicle_id', '=', record.id), ('state', '!=', 'closed'), ('status', '=', 'active'),
                 ('status', '=', 'running')])
            record.route_count = Route.search_count([('vehicle_id', '=', record.id)])
            record.cost_count = Cost.search_count(
                [('vehicle_id', '=', record.id), ('status', '=', 'running')])
            record.history_count = self.env['fleet.vehicle.assignation.log'].search_count(
                [('vehicle_id', '=', record.id)])
            record.maintenance_count = Maintance.search_count(
                [('vehicle_id', '=', record.id),
                 ('stage_id', 'in', (newStage, progressStage))
                    , ('status', '=', StatusType.Running.value)])
            maintenance = Maintance.search(
                [('vehicle_id', '=', record.id),
                 ('stage_id', 'in', (newStage, progressStage)),
                 ('status', '=', StatusType.Running.value)])

            if maintenance:
                for req in maintenance:
                    record.maintenance_level = record.maintenance_level + int(req.priority)
                record.maintenance_level = round(record.maintenance_level / record.maintenance_count)
                if record.maintenance_level > 2:
                    record.maintenance_priority = True
            else:
                record.maintenance_level = 0
                record.maintenance_priority = False
            date_start = record['create_date']
            date_current = datetime.utcnow()
            time_delta = (date_current - date_start)
            total_seconds = time_delta.total_seconds()
            minutes = total_seconds / (60 * 60 * 24)
            record.activity_duration_average = record.amortization_period / minutes

            # view image driver today
            query = """
                            select driver.id,driver.name,att.uri_path from fleet_driver driver
                                left join ir_attachment att on att.res_id = driver.id 
                                    and att.res_model = 'fleet.driver'
                            where driver.id = (select distinct driver_id
                                from sharevan_routing_plan_day where date_plan = current_date
                            and vehicle_id = %s and status != '-1' order by driver_id desc limit 1) 
                        """ % (record.id)
            self.env.cr.execute(query, ())
            list_user = self._cr.dictfetchall()
            if len(list_user) > 0:
                record.driver_name = list_user[0]['name']
                record.image_128 = list_user[0]['uri_path']
            else:
                record.driver_name = ''

            print('_compute_count_all', record.maintenance_count, record.model_id.name, record.maintenance_level,
                  record.maintenance_priority, record.equipment_part_count, record.image_128, record.driver_name)

    @api.depends('log_contracts')
    def _compute_contract_reminder(self):
        params = self.env['ir.config_parameter'].sudo()
        delay_alert_contract = int(params.get_param('hr_fleet.delay_alert_contract', default=30))
        for record in self:
            overdue = False
            due_soon = False
            total = 0
            name = ''
            for element in record.log_contracts:
                if element.state in ('open', 'diesoon', 'expired') and element.expiration_date:
                    current_date_str = fields.Date.context_today(record)
                    due_time_str = element.expiration_date
                    current_date = fields.Date.from_string(current_date_str)
                    due_time = fields.Date.from_string(due_time_str)
                    diff_time = (due_time - current_date).days
                    if diff_time < 0:
                        overdue = True
                        total += 1
                    if diff_time < delay_alert_contract:
                        due_soon = True
                        total += 1
                    if overdue or due_soon:
                        log_contract = self.env['fleet.vehicle.log.contract'].search([
                            ('vehicle_id', '=', record.id),
                            ('state', 'in', ('open', 'diesoon', 'expired'))
                        ], limit=1, order='expiration_date asc')
                        if log_contract:
                            # we display only the name of the oldest overdue/due soon contract
                            name = log_contract.cost_subtype_id.name

            record.contract_renewal_overdue = overdue
            record.contract_renewal_due_soon = due_soon
            record.contract_renewal_total = total - 1  # we remove 1 from the real total for display purposes
            record.contract_renewal_name = name

    def _search_contract_renewal_due_soon(self, operator, value):
        params = self.env['ir.config_parameter'].sudo()
        delay_alert_contract = int(params.get_param('hr_fleet.delay_alert_contract', default=30))
        res = []
        assert operator in ('=', '!=', '<>') and value in (True, False), 'Operation not supported'
        if (operator == '=' and value is True) or (operator in ('<>', '!=') and value is False):
            search_operator = 'in'
        else:
            search_operator = 'not in'
        today = fields.Date.context_today(self)
        datetime_today = fields.Datetime.from_string(today)
        limit_date = fields.Datetime.to_string(datetime_today + relativedelta(days=+delay_alert_contract))
        self.env.cr.execute("""SELECT cost.vehicle_id,
                        count(contract.id) AS contract_number
                        FROM fleet_vehicle_cost cost
                        LEFT JOIN fleet_vehicle_log_contract contract ON contract.cost_id = cost.id
                        WHERE contract.expiration_date IS NOT NULL
                          AND contract.expiration_date > %s
                          AND contract.expiration_date < %s
                          AND contract.state IN ('open', 'diesoon', 'expired')
                        GROUP BY cost.vehicle_id""", (today, limit_date))
        res_ids = [x[0] for x in self.env.cr.fetchall()]
        res.append(('id', search_operator, res_ids))
        return res

    def _search_get_overdue_contract_reminder(self, operator, value):
        res = []
        assert operator in ('=', '!=', '<>') and value in (True, False), 'Operation not supported'
        if (operator == '=' and value is True) or (operator in ('<>', '!=') and value is False):
            search_operator = 'in'
        else:
            search_operator = 'not in'
        today = fields.Date.context_today(self)
        self.env.cr.execute('''SELECT cost.vehicle_id,
                        count(contract.id) AS contract_number
                        FROM fleet_vehicle_cost cost
                        LEFT JOIN fleet_vehicle_log_contract contract ON contract.cost_id = cost.id
                        WHERE contract.expiration_date IS NOT NULL
                          AND contract.expiration_date < %s
                          AND contract.state IN ('open', 'diesoon', 'expired')
                        GROUP BY cost.vehicle_id ''', (today,))
        res_ids = [x[0] for x in self.env.cr.fetchall()]
        res.append(('id', search_operator, res_ids))
        return res

    @api.model
    def create(self, vals):
        if not BaseMethod.reject_dlp_employee_on_data(self.env.user):
            raise ValidationError('DLP employee not allow to create or update data of fleet companies')
        availableState = self.env['fleet.vehicle.state'].search([('code', '=', VehicleStateStatus.Available.value)],
                                                                limit=1).id
        if self.env.company.priority:
            vals['priority'] = self.env.company.priority
        else:
            vals['priority'] = "3"
        vals['state_id'] = availableState
        res = super(FleetVehicle, self).create(vals)
        return res

    def write(self, vals):
        if not BaseMethod.reject_dlp_employee_on_data(self.env.user) and 'state_id' not in vals:
            raise ValidationError('DLP employee not allow to create or update data of fleet companies')
        availableState = self.env['fleet.vehicle.state'].search([('code', '=', VehicleStateStatus.Available.value)],
                                                                limit=1).id
        downgradeState = self.env['fleet.vehicle.state'].search([('code', '=', VehicleStateStatus.Downgraded.value)],
                                                                limit=1).id
        newStage = self.env['sharevan.maintenance.stage'].search([('code', '=', StageMaintenanceType.New.value)],
                                                                 limit=1).id
        progressStage = self.env['sharevan.maintenance.stage'].search(
            [('code', '=', StageMaintenanceType.Progress.value)], limit=1).id

        if 'uniqueid' in vals:
            if 'state_id' in vals and vals['state_id'] != downgradeState:
                pass
            elif 'state_id' in self and self.state_id != downgradeState:
                pass
            else:
                maintain_newStage = self.env['sharevan.maintenance.request'].search_count(
                    [('vehicle', '=', self['id']), ('stage_id', '=', newStage)])
                maintain_progressStage = self.env['sharevan.maintenance.request'].search_count(
                    [('vehicle', '=', self['id']), ('stage_id', '=', progressStage)])
                vals['state_id'] = availableState

        if 'from_date' in vals and 'to_date' in vals:
            validate.check_from_date_greater_than_to_date(vals['from_date'], vals['to_date'])
        elif 'from_date' in vals and self['to_date']:
            validate.check_from_date_greater_than_to_date(vals['from_date'], self['to_date'])
        elif 'to_date' in vals and self['from_date']:
            validate.check_from_date_greater_than_to_date(self['from_date'], vals['to_date'])

        res = super(FleetVehicle, self).write(vals)
        if 'active' in vals and not vals['active']:
            self.mapped('log_contracts').write({'active': False})
        check_notify = False
        if 'name' in vals:
            check_notify = True
        if 'license_plate' in vals:
            check_notify = True
        if 'vehicle_type' in vals:
            check_notify = True
        if 'parking_point_id' in vals:
            check_notify = True
        if check_notify:
            today = datetime.today()
            self.env.cr.execute("""
                select driver.user_id, log.date_start,log.date_end from fleet_vehicle_assignation_log log
                    join fleet_driver driver on driver.id = log.driver_id
                where log.date_start <= %s and log.date_end >= %s and log.vehicle_id = %s 
                    and log.driver_status = '1' and driver.status ='running'
                ORDER BY log.date_start ASC   """,
                                (today, today, self.id,))
            driver_log = self.env.cr.dictfetchall()
            if driver_log:
                user_id = [driver_log[0]['user_id']]
                title = 'Vehicle assign for you has been change infomation'
                body = 'Vehicle assign for you has been change infomation'
                type = NotificationType.RoutingMessage.value
                message_type = MessageType.warning.value
                object_status = ObjectStatus.UpdateInformation.value
                BaseMethod.send_notification_driver(user_id, 'fleet.vehicle', self.id,
                                                    ClickActionType.driver_main_activity.value, message_type, title,
                                                    body, type, '', object_status)
        return res

    def _close_driver_history(self):
        self.env['fleet.vehicle.assignation.log'].search([
            ('vehicle_id', 'in', self.ids),
            # ('driver_id', 'in', self.mapped('driver_id').ids),
            ('date_end', '=', False)
        ]).write({'date_end': fields.Date.today()})

    def create_driver_history(self):
        for vehicle in self:
            self.env['fleet.vehicle.assignation.log'].create({
                'vehicle_id': vehicle.id,
                # 'driver_id': driver_id,
                'date_start': fields.Date.today(),
            })

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):

        return self.env['fleet.vehicle.state'].search([('name', '=', 'Waiting List')], order=order)

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            domain = []
        #     domain = ['|', ('name', operator, name), ('driver_id.name', operator, name)]
        rec = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
        return models.lazy_name_get(self.browse(rec).with_user(name_get_uid))

    def return_action_to_open(self):
        """ This opens the xml view specified in xml_id for the current vehicle """
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        if xml_id:
            res = self.env['ir.actions.act_window'].for_xml_id('fleet', xml_id)
            res.update(
                context=dict(self.env.context, default_vehicle_id=self.id, group_by=False,
                             search_default_status='running'),
                domain=[('vehicle_id', '=', self.id)]
            )
            return res
        return False

    def act_show_log_cost(self):
        """ This opens log view to view and add new log for this vehicle, groupby default to only show effective costs
            @return: the costs log view
        """
        self.ensure_one()
        copy_context = dict(self.env.context)
        copy_context.pop('group_by', None)
        res = self.env['ir.actions.act_window'].for_xml_id('fleet', 'fleet_vehicle_costs_action')
        res.update(
            context=dict(copy_context, default_vehicle_id=self.id, search_default_parent_false=True,
                         search_default_status='running'),
            domain=[('vehicle_id', '=', self.id)]
        )
        return res

    def _track_subtype(self, init_values):
        self.ensure_one()
        # if 'driver_id' in init_values:
        #     return self.env.ref('fleet.mt_fleet_driver_updated')
        return super(FleetVehicle, self)._track_subtype(init_values)

    def open_assignation_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assignation Logs',
            'view_mode': 'tree,kanban,form,graph,calendar',
            'res_model': 'fleet.vehicle.assignation.log',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {"search_default_groupby_vehicle": True}

        }

    def unlink(self):
        current_date = date.today()
        fleet_vehicle_ids = self.ids
        for id in fleet_vehicle_ids:
            vehicle = self.env['fleet.vehicle'].search([('id', '=', id)])
            print('state_id', type(vehicle['state_id']['id']))
            vehicle_state = http.request.env['fleet.vehicle.state']. \
                web_search_read([['id', '=', vehicle['state_id']['id']]], fields=None,
                                offset=0, limit=10, order='')
            if vehicle_state['records'][0]['code'] == 'SHIPPING' or vehicle_state['records'][0]['code'] == 'ORDERED':
                raise ValidationError(
                    _('Vehicle can not delete or change status when vehicle status is SHIPPING or ORDERED !'))
            else:
                vehicle_state = http.request.env['fleet.vehicle.state']. \
                    web_search_read([['code', '=', 'DOWNGRADED']], fields=None,
                                    offset=0, limit=10, order='')
                if vehicle_state:
                    http.request.env['fleet.vehicle']. \
                        browse(id).write(
                        {'active': False, 'fleet_management_id': False, 'is_selected': False,
                         'state_id': vehicle_state['records'][0]['id']})
                else:
                    http.request.env['fleet.vehicle']. \
                        browse(id).write(
                        {'active': False, 'fleet_management_id': False, 'is_selected': False})
                # change status of record in fleet_management_vehicle_temp to deactive
                fleet_vehicle_temp = self.env['fleet.management.vehicle.temp'].search(
                    [('fleet_vehicle_id', '=', id), ('status', '=', 'active')])
                if fleet_vehicle_temp:
                    record = self.env['fleet.management.vehicle.temp'].search(
                        [('id', '=', fleet_vehicle_temp['id']), ('status', '=', 'active')])
                    record.write({
                        'status': 'deactive',
                        'to_date': current_date
                    })
        return self

        """ unlink()

        Deletes the records of the current set

        update res_partner active = False
        """
        # stage maintenance

        # newStage = self.env['sharevan.maintenance.stage'].search([('code', '=', StageMaintenanceType.New.value)],
        #                                                          limit=1).id
        # progressStage = self.env['sharevan.maintenance.stage'].search(
        #     [('code', '=', StageMaintenanceType.Progress.value)], limit=1).id

        # # repairedStage = MaintenanceStage.get_id_by_code(self, StageMaintenanceType.Repaired.value)
        # # scrapStage = MaintenanceStage.get_id_by_code(self, StageMaintenanceType.Scrap.value)
        # if not self:
        #     return True
        #
        # self.check_access_rights('unlink')
        # self._check_concurrency()
        #
        # # mark fields that depend on 'self' to recompute them after 'self' has
        # # been deleted (like updating a sum of lines after deleting one line)
        # self.flush()
        # self.modified(self._fields)
        #
        # with self.env.norecompute():
        #     self.check_access_rule('unlink')
        #
        #     cr = self._cr
        #     data = self.env['ir.model.data'].sudo().with_context({})
        #     attachment = self.env['ir.attachment'].sudo()
        #     ir_model_data_unlink = data
        #     ir_attachment_unlink = attachment
        #
        #     # TOFIX: this avoids an infinite loop when trying to recompute a
        #     # field, which triggers the recomputation of another field using the
        #     # same compute function, which then triggers again the computation
        #     # of those two fields
        #     for field in self._fields.values():
        #         self.env.remove_to_compute(field, self)
        #
        #     for sub_ids in cr.split_for_in_conditions(self.ids):
        #         query = "UPDATE %s SET active = False WHERE id IN %%s" % self._table
        #         cr.execute(query, (sub_ids,))
        #         # inactive all maintenance request that stage in (new, progress) of this vehicle
        #         all_maintenance_request = self.env['sharevan.maintenance.request'].search(
        #             [('vehicle_id', '=', sub_ids), ('status', '=', 'running')
        #                 , ('stage_id', 'in', (newStage, progressStage))])
        #         for maintenance_re in all_maintenance_request:
        #             maintenance_re.unlink()
        #
        #     # invalidate the *whole* cache, since the orm does not handle all
        #     # changes made in the database, like cascading delete!
        #     self.invalidate_cache()
        #     if ir_model_data_unlink:
        #         ir_model_data_unlink.unlink()
        #     if ir_attachment_unlink:
        #         ir_attachment_unlink.unlink()
        #     # DLE P93: flush after the unlink, for recompute fields depending on
        #     # the modified of the unlink
        #     self.flush()

        # auditing: deletions are infrequent and leave no trace in the database

        return True

    # @api.constrains('sim_number')
    # def check_sim_number(self):
    #     for record in self:
    #         if not record.sim_number or not validate.validate_phone_number_v2(record.sim_number):
    #             return False
    #     return True

    @api.constrains('inspection_due_date')
    def _check_due_date(self):
        for record in self:
            if record.inspection_due_date and record.inspection_due_date < datetime.today().date():
                raise ValidationError("Inspection due date must be after today!")
        return True

    @api.constrains('seats')
    def _check_seats(self):
        for record in self:
            if record.seats and record.seats < 0:
                raise ValidationError("Seat number must be a positive number!")

    @api.constrains('capacity')
    def _check_capacity(self):
        for record in self:
            if record.capacity < 0:
                raise ValidationError("Capacity must be a positive number")

    @api.constrains('horsepower')
    def _check_horsepower(self):
        for record in self:
            if record.horsepower < 0:
                raise ValidationError("Horsepower must be a positive number")

    @api.constrains('engine_size')
    def _check_engine_size(self):
        for record in self:
            if record.engine_size < 0:
                raise ValidationError("Engine size must be a positive number")

    @api.constrains('cost')
    def _check_cost(self):
        for record in self:
            if record.cost < 0:
                raise ValidationError("Operating cost must be a positive number")

    @api.constrains('residual_value')
    def _check_res_value(self):
        for record in self:
            if record.residual_value < 0:
                raise ValidationError("Residual value must be a positive number")

    @api.constrains('car_value')
    def _check_value(self):
        for record in self:
            if record.car_value < 0:
                raise ValidationError("Catalog value must be a positive number")

    @api.constrains('net_car_value')
    def _check_net_value(self):
        for record in self:
            if record.net_car_value < 0:
                raise ValidationError("Purchase value must be a positive number")

    def update_vehicle_sos_status(self, vehicle_id):
        driver_query = """
            select veh.id 
                 FROM  fleet_driver veh
                    LEFT JOIN fleet_vehicle_assignation_log vehlog on vehlog.driver_id = veh.id 
            where vehlog.give_car_back IS NULL and veh.user_id = %s and vehlog.vehicle_id = %s
        """
        self._cr.execute(driver_query, (http.request.env.uid, vehicle_id,))
        check = self._cr.dictfetchall()
        if check:
            vehicle = http.request.env['fleet.vehicle'].search(
                [('id', '=', vehicle_id)])
            update_check = vehicle.write({
                'sos_status': VehicleSosType.NORMAL.value
            })
            if update_check:
                # Gửi thông báo đến nhà xe
                fleet_ids = BaseMethod.get_fleet_manager(check[0]['id'])
                dlp_ids = BaseMethod.get_dlp_employee()
                if len(dlp_ids) > 0:
                    fleet_ids.extend(dlp_ids)
                print(fleet_ids)
                if len(fleet_ids) > 0:
                    title = 'Van start running!'
                    body = 'Van have start running after sos! ' \
                           + str(vehicle_id)
                    item_id = str(vehicle_id)
                    try:
                        val = {
                            'user_id': fleet_ids,
                            'title': title,
                            'content': body,
                            'res_id': item_id,
                            'res_model': 'fleet.vehicle',
                            'click_action': ClickActionType.routing_plan_day_customer.value,
                            'message_type': MessageType.success.value,
                            'type': NotificationType.RoutingMessage.value,
                            'object_status': RoutingDetailStatus.Done.value,
                            'item_id': item_id,
                        }
                        http.request.env[Notification._name].create(val)
                        notice = "Van have start running after sos!"
                        for user in fleet_ids:
                            users = self.env['res.users'].search(
                                [('id', '=', user)])
                            users.notify_info(message=notice, title=NotificationSocketType.NOTIFICATION.value)
                    except:
                        logger.warn(
                            "Van have start running after sos! But can not send message",
                            FleetVehicle._name, item_id,
                            exc_info=True)
                return '200'
            else:
                return '500'
        else:
            return '500'


class FleetVehicleOdometer(models.Model):
    _name = 'fleet.vehicle.odometer'
    _description = 'Odometer log for a vehicle'
    _order = 'date desc'

    @api.constrains('value')
    def check_odometer(self):
        return validate.check_number_bigger_than_zero(self.value, 'value')

    name = fields.Char(compute='_compute_vehicle_log_name', store=True)
    date = fields.Date(default=fields.Date.context_today)
    value = fields.Float('Odometer Value', group_operator="max")
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', required=True)
    unit = fields.Selection(related='vehicle_id.odometer_unit', string="Unit", readonly=True)
    status = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted')], 'Status', default="running")

    # driver_id = fields.Many2one(related="vehicle_id.driver_id", string="Driver", readonly=False)

    def unlink(self):
        record_ids = self.env['fleet.vehicle.odometer'].search([('id', '=', self.id)])
        for record in record_ids:
            record.write({
                'status': 'deleted'
            })
        return self

    @api.depends('vehicle_id', 'date')
    def _compute_vehicle_log_name(self):
        for record in self:
            name = record.vehicle_id.name
            if not name:
                name = str(record.date)
            elif record.date:
                name += ' / ' + str(record.date)
            record.name = name

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
        if self.vehicle_id:
            self.unit = self.vehicle_id.odometer_unit


class FleetVehicleTag(models.Model):
    _name = 'fleet.vehicle.tag'
    _description = 'Vehicle Tag'

    name = fields.Char('Tag Name', required=True, translate=True)
    color = fields.Integer('Color Index')

    _sql_constraints = [('name_uniq', 'unique (name)', "Tag name already exists !")]


class FleetVehicleCategoryName(models.Model):
    _name = 'fleet.vehicle.category.name'
    _description = 'Vehicle Category Name'

    sequence = fields.Integer(help="Used to order the note category")
    name = fields.Char('Category Name', required=True, translate=True)
    code = fields.Char('Category Code')

    _sql_constraints = [('name_uniq', 'unique (name)', "Category name already exists !")]


class FleetVehicleCategoryType(models.Model):
    _name = 'fleet.vehicle.category.type'
    _description = 'Vehicle Category Type'

    sequence = fields.Integer(help="Used to order the note category")
    name = fields.Char('Category Type', required=True, translate=True)
    code = fields.Char('Category Type Code')

    _sql_constraints = [('name_uniq', 'unique (name)', "Category Type already exists !")]


class FleetServiceType(models.Model):
    _name = 'fleet.service.type'
    _description = 'Fleet Service Type'

    name = fields.Char(required=True, translate=True)
    category = fields.Selection([
        ('contract', 'Contract'),
        ('service', 'Service'),
        ('maintenance', 'Maintenance')
    ], 'Category', required=True, help='Choose whether the service refer to contracts, vehicle services or both')
    price = fields.Float('price')

    status = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted')], 'Status', default="running")

    def unlink(self):
        print(self)
        for record in self.ids:
            record_id = self.env['fleet.service.type'].search([('id', '=', record)])
            record_id.write({
                'status': 'deleted'
            })
        return self


class FleetVehicleAssignationLog(models.Model):
    _name = "fleet.vehicle.assignation.log"
    _description = "Drivers history on a vehicle"
    _order = "create_date desc, date_start desc"

    current_date = date.today()
    name = fields.Char(string="Name", related='driver_id.name')
    assignation_log_code = fields.Char(string='Assignation_log_code', copy=False, readonly=True,
                                       index=True,
                                       default=lambda self: _('New'))
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle", required=True)
    driver_id = fields.Many2one('fleet.driver', string="Driver", required=True,
                                domain="[('status', '=', 'running'),('employee_type', '=', 'driver'),('expires_date','>',current_date)]")
    attach_File = fields.Many2many('ir.attachment', string="Attach File")
    equipment_log_line = fields.One2many('fleet.driver.equipment.log', 'assignation_log_id', string="Attach File",
                                         readonly=True)
    routing_plan_day_ids = fields.One2many('sharevan.routing.plan.day', 'vehicle_id', string="Routing",
                                           compute="compute_on_load", store=False)

    date_start = fields.Datetime(string="Start Date", required=True,
                                 default=datetime.combine(datetime.today(), datetime.min.time()))
    date_start_idr = fields.Datetime(related='date_start', readonly=True)
    date_end = fields.Datetime(string="End Date", required=True)
    receive_car = fields.Datetime(string="Receive Car", readonly=True)
    give_car_back = fields.Datetime(string="Give car back", readonly=True)
    description = fields.Char(string="Description")
    status = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted')], 'Status', default="running")
    driver_status = fields.Selection([('1', 'Working'),
                                      ('0', 'Off')], 'Driver Status', default="1", required=True)

    company_id = fields.Many2one('res.company', 'Company', index=True, required=True, readonly=True,
                                 default=lambda self: self.env.company.id)

    fleet_management_id = fields.Many2one('fleet.management', string='Fleet management', required=True)

    def compute_on_load(self):
        for record in self:
            date_plan = datetime.strptime(str(record['date_start']), "%Y-%m-%d %H:%M:%S").date()
            records = http.request.env['sharevan.routing.plan.day'].search(
                [('vehicle_id', '=', record['vehicle_id'].id), ('driver_id', '=', record['driver_id'].id)
                    , ('date_plan', '=', date_plan)
                 ])
            if records:
                record.routing_plan_day_ids = records
            else:
                record.routing_plan_day_ids = False

    @api.onchange('driver_id')
    def _onchange_driver_id(self):
        for record in self:
            if not record.vehicle_id:
                record.driver_id = False

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
        for record in self:
            record.update({
                'driver_id': False
            })
            if record['vehicle_id']['id']:
                if record['vehicle_id']['tonnage_id']['max_tonnage']:
                    query_driver_license_tonnage = """ SELECT * FROM public.sharevan_driver_license
                                                           Where max_tonnage >= %s"""
                    self.env.cr.execute(query_driver_license_tonnage,
                                        (record['vehicle_id']['tonnage_id']['max_tonnage'],))
                    ardata = self.env.cr.fetchall()
                    array_id_driver_license = []
                    for data in ardata:
                        array_id_driver_license.append(data[0])
                    if record['date_start'] and record['date_end']:
                        list_driver_assignment = []
                        list_driver_assignment_id = []
                        query_driver = ''
                        filter_querry = """
                                                                        select fleet_team.*,(select coalesce( us.id, 0) count from res_users us
                                                                        where us.is_admin = true and us.id = %s) from (WITH RECURSIVE c AS (
                                                                            SELECT (select fleet_management_id from fleet_driver
                                                                        where employee_type in ('manager','employee') and user_id = %s) AS id
                                                                            UNION ALL
                                                                                SELECT sa.id
                                                                            FROM fleet_management AS sa
                                                                                JOIN c ON c.id = sa.parent_id
                                                                            )
                                                                        SELECT id FROM c ) fleet_team
                                                                    """

                        http.request.env.cr.execute(filter_querry,
                                                    (http.request.env.uid, http.request.env.uid,))
                        result = http.request._cr.dictfetchall()
                        if result[0]['id']:
                            # Id tổ đội của account
                            mamagement_id = result[0]['id']
                            fleet_mamagement_team_check = self.env['fleet.management'].search(
                                [('id', '=', mamagement_id)]).team_check
                            if fleet_mamagement_team_check:
                                query_sub_manager = """ Select id , team_check from fleet_management 
                                                        Where parent_id = %s and status = 'active'  """
                                self.env.cr.execute(query_sub_manager, (mamagement_id,))
                                ardata = self.env.cr.fetchall()
                                if ardata[0][1]:
                                    query_driver += """ SELECT id FROM public.fleet_driver
                                                        Where status = 'running' and company_id = %s and  class_driver in (""" % (
                                        http.request.env.company.id)

                                    for id in array_id_driver_license:
                                        query_driver += str(id) + ","
                                    query_driver = query_driver.rstrip(',')
                                    query_driver += " )"

                                else:
                                    query_driver = """Select fleet_driver_id from fleet_management_driver_temp
                                                      Where type = 'Driver' and status = 'active' and fleet_management_id in  ( """
                                    for id in ardata:
                                        query_driver += str(id[0]) + ","
                                    query_driver = query_driver.rstrip(',')
                                    query_driver += " )"
                            else:
                                query_driver = """Select fleet_driver_id from fleet_management_driver_temp
                                                  Where type = 'Driver' and status = 'active' and fleet_management_id  = %s """ % (
                                    result[0]['id'])
                        else:
                            query_driver += """ SELECT id FROM public.fleet_driver
                                                Where status = 'running' and company_id = %s and  class_driver in (""" % (
                                http.request.env.company.id)

                            for id in array_id_driver_license:
                                query_driver += str(id) + ","
                            query_driver = query_driver.rstrip(',')
                            query_driver += " )"

                        self.env.cr.execute(query_driver)
                        ardata = self.env.cr.fetchall()

                        for driver_id in ardata:
                            list_driver_assignment.append(driver_id[0])

                        for driver_id in list_driver_assignment:
                            self.env.cr.execute("""select date_start,date_end from fleet_vehicle_assignation_log
                                              where ((give_car_back IS NULL and receive_car IS NULL ) or (date_start >= CURRENT_DATE)) and driver_id = %s and status = 'running' and driver_status = '1'
                                                                                        ORDER BY date_start ASC   """,
                                                (driver_id,))

                            ardata = self.env.cr.fetchall()
                            ardata_length = len(ardata)

                            if ardata_length > 0:
                                check = 0
                                if record['date_start'] > ardata[ardata_length - 1][0]:
                                    if record['date_start'] <= ardata[ardata_length - 1][1]:
                                        continue
                                else:
                                    for data in ardata:
                                        if record['date_start'] >= data[0] and record['date_start'] <= data[1]:
                                            check = 1
                                    if check == 1:
                                        continue
                                    count = 0
                                    for data in ardata:
                                        if record['date_start'] > data[0]:
                                            count += 1
                                        elif record['date_start'] < data[0]:
                                            break

                                    if record['date_end'] > ardata[count][0]:
                                        continue
                            list_driver_assignment_id.append(driver_id)

                        # Check trong thời gian này có lái xe nào nghỉ k
                        driver_id_not_calendar_yet = []
                        status_accept = '2'
                        date_request_off = str(record['date_start'].year) + '-' + str(
                            record['date_start'].month) + '-' + str(record['date_start'].day)

                        query_driver_request_off = "select driver_id from fleet_request_time_off where status = '%s' and request_day = '%s' and driver_id IN (" % (
                            status_accept, date_request_off)
                        for id in list_driver_assignment_id:
                            query_driver_request_off += str(id) + ","
                        query_driver_request_off_rs = query_driver_request_off.rstrip(',')
                        query_driver_request_off_rs += ")"

                        http.request.env.cr.execute(query_driver_request_off_rs)
                        ardata_data_request_off = http.request.env.cr.fetchall()
                        driver_id_requets_off = []
                        for idd in ardata_data_request_off:
                            driver_id_requets_off.append(idd[0])
                        if len(ardata_data_request_off) > 0:
                            for id in list_driver_assignment_id:
                                if len(driver_id_requets_off) > 0:
                                    for ids in driver_id_requets_off:
                                        if id != ids:
                                            driver_id_not_calendar_yet.append(id)
                                        else:
                                            driver_id_requets_off.remove(ids)
                                else:
                                    driver_id_not_calendar_yet.append(id)

                            date_plan = datetime.strptime(str(record['date_start']), "%Y-%m-%d %H:%M:%S").date()
                            records = http.request.env['sharevan.routing.plan.day'].search(
                                [('vehicle_id', '=', record['vehicle_id'].id), ('date_plan', '=', date_plan)
                                 ])
                            if records:
                                record.routing_plan_day_ids = records
                            else:
                                record.routing_plan_day_ids = False
                            return {'domain': {
                                'driver_id': [('id', 'in', driver_id_not_calendar_yet)]}}

                        date_plan = datetime.strptime(str(record['date_start']), "%Y-%m-%d %H:%M:%S").date()
                        records = http.request.env['sharevan.routing.plan.day'].search(
                            [('vehicle_id', '=', record['vehicle_id'].id), ('date_plan', '=', date_plan)
                             ])
                        if records:
                            record.update({'routing_plan_day_ids': records})
                        else:
                            record.routing_plan_day_ids = False
                        return {'domain': {
                            'driver_id': [('id', 'in', list_driver_assignment_id)]}}
                    else:
                        return {'domain': {
                            'driver_id': [('status', '=', 'running'), ('class_driver', 'in', array_id_driver_license)]}}

    @api.onchange('date_start')
    def _onchange_date_start(self):
        offset = self.env.user.tz_offset
        plus = offset[:1]
        hour = int((offset[1:])[:2])
        for record in self:
            record.update({
                'vehicle_id': False,
                'driver_id': False
            })

            if record['date_start']:
                if plus == '+':
                    date_start = datetime.combine(datetime.strptime(str(record['date_start']), "%Y-%m-%d %H:%M:%S"),
                                                  datetime.min.time()) + timedelta(hours=hour)
                else:
                    date_start = datetime.combine(datetime.strptime(str(record['date_start']), "%Y-%m-%d %H:%M:%S"),
                                                  datetime.min.time()) - timedelta(hours=hour)
                # Thoi gian bat dau phai lon hon thoi gian hien tai
                if date_start < datetime.combine(datetime.today(), datetime.min.time()):
                    record.update({
                        'date_start': False,
                        'date_end': False
                    })
                    test_msg = {"message": "The time must be greater than the current date! "
                                }
                    self.env.user.notify_danger(**test_msg)

    @api.onchange('date_end')
    def _onchange_date_end(self):
        offset = self.env.user.tz_offset
        plus = offset[:1]
        hour = int((offset[1:])[:2])
        for record in self:
            if record['date_end'] and record['date_start']:
                if plus == '+':
                    date_start = datetime.combine(datetime.strptime(str(record['date_start']), "%Y-%m-%d %H:%M:%S"),
                                                  datetime.min.time())
                    # + timedelta(hours=hour)
                    date_end = datetime.combine(datetime.strptime(str(record['date_end']), "%Y-%m-%d %H:%M:%S"),
                                                datetime.min.time()) + timedelta(hours=(24)) - timedelta(minutes=1)
                    # datetime.min.time()) + timedelta(hours=(24+hour)) - timedelta(minutes=1)
                else:
                    date_start = datetime.combine(datetime.strptime(str(record['date_start']), "%Y-%m-%d %H:%M:%S"),
                                                  datetime.min.time())
                    # - timedelta(hours=hour)
                    date_end = datetime.combine(datetime.strptime(str(record['date_end']), "%Y-%m-%d %H:%M:%S"),
                                                datetime.min.time()) + timedelta(hours=(24)) - timedelta(minutes=1)
                    # datetime.min.time()) + timedelta(hours=(24-hour)) - timedelta(minutes=1)

                # Thoi gian bat dau phai lon hon thoi gian hien tai
                if date_start < datetime.combine(datetime.today(), datetime.min.time()):
                    record.update({
                        'date_end': False,
                        'date_start': False
                    })
                    test_msg = {"message": "The time must be greater than the current time! "
                                }
                    self.env.user.notify_danger(**test_msg)
                if date_end < date_start:
                    record.update({
                        'date_end': False,
                        'date_start': False
                    })
                    test_msg = {"message": "End_date must be greater than start_date! "}
                    self.env.user.notify_danger(**test_msg)

                    # check vehicle đã có lịch hay chưa
                else:
                    record.date_start = date_start
                    record.date_end = date_end
                    query_vehicle = ""

                    query_downgraded_state_id = """ Select id  from fleet_vehicle_state 
                                                    Where name = %s  """
                    self.env.cr.execute(query_downgraded_state_id, (VehicleStateStatus.DOWNGRADED.value,))
                    ardata = self.env.cr.fetchall()
                    if ardata[0][0]:
                        downgraded_state_id = ardata[0][0]

                    # Xem account thuộc tổ đội  nào
                    filter_querry = """
                                                select fleet_team.*,(select coalesce( us.id, 0) count from res_users us
                                                where us.is_admin = true and us.id = %s) from (WITH RECURSIVE c AS (
                                                    SELECT (select fleet_management_id from fleet_driver
                                                where employee_type in ('manager','employee') and user_id = %s) AS id
                                                    UNION ALL
                                                        SELECT sa.id
                                                    FROM fleet_management AS sa
                                                        JOIN c ON c.id = sa.parent_id
                                                    )
                                                SELECT id FROM c ) fleet_team
                                            """

                    http.request.env.cr.execute(filter_querry,
                                                (http.request.env.uid, http.request.env.uid,))
                    result = http.request._cr.dictfetchall()
                    if result[0]['id']:
                        # Id tổ đội của account
                        mamagement_id = result[0]['id']
                        fleet_mamagement_team_check = self.env['fleet.management'].search(
                            [('id', '=', mamagement_id)]).team_check
                        if fleet_mamagement_team_check:
                            query_sub_manager = """ Select id , team_check from fleet_management 
                                                    Where parent_id = %s and status = 'active'  """
                            self.env.cr.execute(query_sub_manager, (mamagement_id,))
                            ardata = self.env.cr.fetchall()
                            if ardata[0][1]:
                                query_vehicle += """ SELECT id FROM public.fleet_vehicle 
                                                     where active = True and company_id = %s and   state_id not in (%s)""" % (
                                    http.request.env.company.id, downgraded_state_id)
                            else:
                                query_vehicle = """Select fleet_vehicle_id from fleet_management_vehicle_temp
                                                 Where status = 'active' and fleet_management_vehicle_id in  ( """
                                for id in ardata:
                                    query_vehicle += str(id[0]) + ","
                                query_vehicle = query_vehicle.rstrip(',')
                                query_vehicle += " )"
                        else:
                            query_vehicle = """Select fleet_vehicle_id from fleet_management_vehicle_temp
                                               Where status = 'active' and fleet_management_vehicle_id  = %s """ % (
                                result[0]['id'])
                    else:
                        query_vehicle += """ SELECT id FROM public.fleet_vehicle 
                                                                             where active = True and company_id = %s and   state_id not in (%s)""" % (
                            http.request.env.company.id, downgraded_state_id)
                    self.env.cr.execute(query_vehicle)
                    ardata = self.env.cr.fetchall()

                    array_vehicle_id = []
                    list_vehicle_assignment_id = []
                    for data in ardata:
                        array_vehicle_id.append(data[0])

                    for vehicle_id in array_vehicle_id:

                        self.env.cr.execute("""
                            select date_start,date_end 
                                from fleet_vehicle_assignation_log
                            where date_start >= CURRENT_DATE and vehicle_id = %s 
                                and status = 'running' and driver_status = '1'
                            ORDER BY date_start ASC   """,
                                            (vehicle_id,))
                        ardata = self.env.cr.fetchall()
                        ardata_length = len(ardata)

                        if ardata_length > 0:
                            check = 0
                            if record['date_start'] > ardata[ardata_length - 1][0]:
                                if record['date_start'] <= ardata[ardata_length - 1][1]:
                                    continue
                            else:
                                for data in ardata:
                                    if record['date_start'] >= data[0] and record['date_start'] <= data[1]:
                                        check = 1
                                if check == 1:
                                    continue
                                count = 0
                                for data in ardata:
                                    if record['date_start'] > data[0]:
                                        count += 1
                                    elif record['date_start'] < data[0]:
                                        break

                                if record['date_end'] > ardata[count][0]:
                                    continue
                        list_vehicle_assignment_id.append(vehicle_id)
                    return {'domain': {
                        'vehicle_id': [('id', 'in', list_vehicle_assignment_id)]
                    }}

    # def compute_all(self):
    #     for record in self:
    #         record.toogle_cancel = False

    def create_vehicle_assignation_log(self):
        name_vehicle = ''
        if self.vehicle_id:
            name_vehicle = self.vehicle_id.name
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assign new calendar for ' + name_vehicle,
            'view_mode': 'form',
            'res_model': 'fleet.vehicle.assignation.log',
            'target': 'new',
            'context': {
                'form_view_initial_mode': 'edit',
            },
        }

    def cancel_vehicle_assignation_log(self):
        print('log khi cancel_vehicle_assignation_log')
        if self.receive_car:
            raise ValidationError(_('Driver has received car! You are not authorized to off ! '))
        else:
            date_plan = datetime.strptime(str(self.date_start), "%Y-%m-%d %H:%M:%S").date()
            records = http.request.env['sharevan.routing.plan.day'].search(
                [('vehicle_id', '=', self.vehicle_id.id)
                    , ('date_plan', '=', date_plan)
                 ])
            if records:
                check_warning = False
                for rec in records:
                    if rec['status'] == '3' or rec['status'] == '-1':
                        pass
                    else:
                        check_warning = True
                        break
                if check_warning:
                    notice = "You have to register new driver for this car, because this car has been assigned routing"
                    self.env.user.notify_warning(message=notice, title=NotificationSocketType.NOTIFICATION.value)
                    dlp_employee = BaseMethod.get_dlp_employee()
                    if dlp_employee:
                        notice = 'Fleet manager has cancel driver calendar for ' + self.vehicle_id.name + '! Please check for assigning new driver! '
                        content = {
                            'title': 'Fleet manager has cancel driver calendar',
                            'content': notice,
                            'type': NotificationType.RoutingMessage.value,
                            'res_id': self.id,
                            'res_model': 'fleet.vehicle.assignation.log',
                            'click_action': ClickActionType.routing_plan_day_driver.value,
                            'message_type': MessageType.warning.value,
                            'user_id': dlp_employee,
                        }
                        self.env['sharevan.notification'].sudo().create(content)
                        list_employee = self.env['res.users'].search([('id', 'in', dlp_employee)])
                        for emp in list_employee:
                            emp.notify_info(message=notice, title=NotificationSocketType.NOTIFICATION.value)
            list_driver = self.env['fleet.vehicle.assignation.log'].search([('id', '=', self.id)])
            list_driver.write({
                'driver_status': '0'
            })
            user_id = [self.driver_id.user_id.id]
            title = 'Manager has been change information!'
            body = 'Manager has been cancel you working calendar '
            type = NotificationType.RoutingMessage.value
            message_type = MessageType.warning.value
            object_status = ObjectStatus.UpdateInformation.value
            BaseMethod.send_notification_driver(user_id, 'fleet.vehicle.assignation.log', self.id,
                                                ClickActionType.driver_main_activity.value, message_type, title,
                                                body, type, '', object_status)

    # def compute_all(self):
    #     for record in self:
    #         record.toogle_cancel = False

    def unlink(self):
        print('log khi unlink')
        date_start_ck = self.date_start + timedelta(hours=7)
        dateCurrent = datetime.now()

        # if date_start_ck.year == dateCurrent.year and date_start_ck.month == dateCurrent.month and date_start_ck.day == dateCurrent.day:
        #     raise ValidationError(_('You are not authorized to delete ! '))

        if self.receive_car and self.give_car_back:
            raise ValidationError(_('This log cannot be deleted'))

        vehicle_id = int(self.vehicle_id)
        driver_id = int(self.driver_id)
        assignation_id = self.id

        veh_id = self.env['fleet.vehicle.status'].search([('assignation_log_id', '=', assignation_id)]).id

        record_ids = self.env['fleet.vehicle.assignation.log'].search([('id', '=', self.id)])
        for record in record_ids:
            super(FleetVehicleAssignationLog, record).write({'status': 'deleted'})

        self.env.cr.execute("""Update fleet_vehicle_status Set status = %s where id = %s  """,
                            ('deleted', str(veh_id),))

    @api.model
    def create(self, vals):
        print('log khi tạo lịch')
        if vals.get('assignation_log_code', 'New') == 'New':
            vals['assignation_log_code'] = self.env['ir.sequence'].next_by_code(
                'fleet.vehicle.assignation.log') or 'New'
        vehicle_id = str(vals['vehicle_id'])
        driver_id = str(vals['driver_id'])
        # date_start = datetime.strptime(vals['date_start'], '%Y-%m-%d %H:%M:%S')
        # date_end = datetime.strptime(vals['date_end'], '%Y-%m-%d %H:%M:%S')

        # Lấy id tổ đội của lái xe
        fleet_management_id = """ select fleet_management_id from fleet_management_driver_temp
                                  where fleet_driver_id = %s and status = 'active'  """
        self.env.cr.execute(fleet_management_id, (vals['driver_id'],))
        ardata = self.env.cr.fetchall()
        if ardata[0][0]:
            vals['fleet_management_id'] = ardata[0][0]

        date_start = datetime.combine(datetime.strptime(str(vals['date_start']), "%Y-%m-%d %H:%M:%S"),
                                      datetime.min.time())
        date_end = datetime.combine(datetime.strptime(str(vals['date_end']), "%Y-%m-%d %H:%M:%S"),
                                    datetime.min.time()) + timedelta(hours=(24)) - timedelta(minutes=1)

        veh = self.env['fleet.vehicle'].search([('id', '=', int(vehicle_id))])
        state_id = int(veh.state_id)
        status = self.env['fleet.vehicle.state'].search([('id', '=', state_id)])

        if status.name == 'Downgraded':
            raise ValidationError(_('vehicle in a state of downgraded '))

        # Thoi gian bat dau phai lon hon hoặc bằng ngày hiện tại
        if date_start < (datetime.combine(datetime.today(), datetime.min.time())):
            raise ValidationError(_(' Start Date must not be smaller than today'))

        # check date_end > date_start
        if (date_end <= date_start):
            raise ValidationError(_('End time must be greater than start time'))

        # # check trong thoi gian nay lai xe co trong lich k
        self.env.cr.execute("""select date_start,date_end from fleet_vehicle_assignation_log
                where date_start >= CURRENT_DATE and driver_id = %s and status = 'running' and driver_status = '1'
                                                        ORDER BY date_start ASC   """, (driver_id,))
        # self.env.cr.execute(sql_driver)
        ardata = self.env.cr.fetchall()
        ardata_length = len(ardata)

        if ardata_length > 0:
            if date_start > ardata[ardata_length - 1][0]:
                if date_start <= ardata[ardata_length - 1][1]:
                    raise ValidationError(_('During that time the driver has a running schedule'))

            else:
                for data in ardata:
                    if date_start >= data[0] and date_start <= data[1]:
                        raise ValidationError(_('During that time the driver has a running schedule'))
                count = 0
                for data in ardata:
                    if date_start > data[0]:
                        count += 1
                    elif date_start < data[0]:
                        break

                if date_end > ardata[count][0]:
                    raise ValidationError(_('There is a schedule in this time frame'))

        # # check trong khoang thoi gian fleet/receive_return_vehicle nay xe da co lich chay chua bỏ trường hợp cùng 1 lái xe
        self.env.cr.execute("""
            select date_start,date_end from fleet_vehicle_assignation_log
                where date_start >= CURRENT_DATE and vehicle_id = %s and driver_id != %s  and status = 'running' and driver_status = '1'
                                                                ORDER BY date_start ASC   """, (vehicle_id, driver_id,))
        # self.env.cr.execute(sql_driver)

        ardata = self.env.cr.fetchall()
        ardata_length = len(ardata)

        if ardata_length > 0:
            if date_start > ardata[ardata_length - 1][0]:
                if date_start <= ardata[ardata_length - 1][1]:
                    raise ValidationError(_('During this time the car had a running schedule'))

            else:
                for data in ardata:
                    if date_start >= data[0] and date_start <= data[1]:
                        raise ValidationError(_('During this time the car had a running schedule'))
                        break
                count = 0
                for data in ardata:
                    if date_start > data[0]:
                        count += 1
                    elif date_start < data[0]:
                        break
                if date_end > ardata[count][0]:
                    raise ValidationError(_('There is a schedule in this time frame'))
        vals['date_start'] = date_start
        vals['date_end'] = date_end
        res = super(FleetVehicleAssignationLog, self).create(vals)
        title = 'You have working calendar assgin: ' + veh.name
        body = 'You have working calendar assgin: ' + veh.name
        driver = self.env['fleet.driver'].search([('id', '=', driver_id)])
        # today = str(date.today())
        if driver['expires_date'] < date.today():
            raise ValidationError(_('The license of driver was expired!'))

        # Tạo thông báo cho lái xe sau khi có lịch
        val = {
            'user_id': [driver['user_id'].id],
            'title': title,
            'content': body,
            'type': NotificationType.RoutingMessage.value,
            'object_status': ObjectStatus.AssignCarWorking.value,
            'click_action': ClickActionType.driver_vehicle_check_point.value,
            'item_id': res['id'],
        }
        http.request.env['sharevan.notification'].create(val)
        v = {
            'vehicle_id': vehicle_id,
            'driver_id': driver_id,
            'assignation_log_id': res['id'],
            'toogle': True,
            'date_start': date_start,
            'date_end': date_end,
        }
        receive_return_vehicle = self.env['fleet.vehicle.status'].sudo().create(v)

        date_plan = datetime.strptime(str(date_start), "%Y-%m-%d %H:%M:%S").date()
        records = http.request.env['sharevan.routing.plan.day'].search(
            [('vehicle_id', '=', int(vehicle_id))
                , ('date_plan', '=', date_plan)])
        if records:
            check_warning = False
            for rec in records:
                if rec['status'] == '3' or rec['status'] == '-1':
                    pass
                else:
                    check_warning = True
                    break
            if check_warning:
                for rec in records:
                    if rec['status'] == '2':
                        pass
                    else:
                        rec.write({'driver_id': driver_id,
                                   'description': ' thay đổi lái xe mới ' + str(driver_id) + 'Lịch mới: ' + res[
                                       'assignation_log_code']})
                dlp_employee = BaseMethod.get_dlp_employee()
                if dlp_employee:
                    notice = 'Fleet manager has assign a new driver: ' + res.driver_id.full_name + ' for ' + res.vehicle_id.name + '! Please check for assigning new driver! '
                    content = {
                        'title': 'Fleet manager has assign a new driver calendar',
                        'content': notice,
                        'type': NotificationType.RoutingMessage.value,
                        'res_id': res.id,
                        'res_model': 'fleet.vehicle.assignation.log',
                        'click_action': ClickActionType.routing_plan_day_driver.value,
                        'message_type': MessageType.warning.value,
                        'user_id': dlp_employee,
                    }
                    self.env['sharevan.notification'].sudo().create(content)
                    list_employee = self.env['res.users'].search([('id', 'in', dlp_employee)])
                    for emp in list_employee:
                        emp.notify_info(message=notice, title=NotificationSocketType.NOTIFICATION.value)
        return res

    def write(self, vals):
        print('log khi update lịch')
        if not BaseMethod.reject_dlp_employee_on_data(self.env.user):
            raise ValidationError('DLP employee not allow to create or update data of fleet companies')
        date_end = datetime.today()
        date_start = datetime.combine(datetime.today(), datetime.min.time())
        status_id = self.env['fleet.vehicle.status'].search([('assignation_log_id', '=', self.id)]).id

        # date_start_ck = self.date_start + timedelta(hours=7)
        # dateCurrent = datetime.now()
        # if date_start_ck.year == dateCurrent.year and date_start_ck.month == dateCurrent.month and date_start_ck.day == dateCurrent.day :
        #     raise ValidationError(_('You are not authorized to edit ! '))

        if 'driver_id' in vals:
            driver = self.env['fleet.driver'].search([('id', '=', vals['driver_id'])])
            if driver['expires_date'] < date.today():
                raise ValidationError(_('The license of driver was expired!'))

        if self.receive_car:
            raise ValidationError(_('You are not authorized to edit ! '))

        listFieldUpdate = []
        listField = ['vehicle_id', 'driver_id', 'date_start', 'date_end']

        for val in vals:
            listFieldUpdate.append(val)

        for val in listFieldUpdate:
            for val1 in listField:
                if val == val1:
                    listField.remove(val1)
                    break
        vehicle_id = 0
        driver_id = 0
        for val in listFieldUpdate:
            if val == 'vehicle_id':
                vehicle_id = vals['vehicle_id']
            elif val == 'driver_id':
                driver_id = vals['driver_id']
            elif val == 'date_start':
                date_start = datetime.combine(datetime.strptime(str(vals['date_start']), "%Y-%m-%d %H:%M:%S"),
                                              datetime.min.time())
            elif val == 'date_end':
                date_end = datetime.combine(datetime.strptime(str(vals['date_end']), "%Y-%m-%d %H:%M:%S"),
                                            datetime.min.time()) + timedelta(hours=24) - timedelta(minutes=1)
        for val in listField:
            if val == 'vehicle_id':
                vehicle_id = int(self.vehicle_id)
            elif val == 'driver_id':
                driver_id = int(self.driver_id)
            elif val == 'date_start':
                date_start = self.date_start
            elif val == 'date_end':
                date_end = self.date_end

        assignation_id = int(self.id)

        # Thoi gian bat dau phai lon hon thoi gian hien tai
        if 'driver_status' in vals and vals['driver_status'] is '1':
            if date_start < datetime.combine(datetime.today(), datetime.min.time()):
                raise ValidationError(_('Date start must be greater than current time'))

        # # Thoi gian bat dau phai lon hon thoi gian hien tai
        # if 'driver_status' in vals and vals['driver_status'] is '0':
        #     if self['receive_car'] is not False:
        #         raise ValidationError(_('You cannot turn off the calendar once it has started running'))

        veh = self.env['fleet.vehicle'].search([('id', '=', int(vehicle_id))])
        state_id = int(veh.state_id)
        status = self.env['fleet.vehicle.state'].search([('id', '=', state_id)])

        # if status.name == 'Maintenance':
        #     raise ValidationError(_('Vehicle in a state of maintenance '))
        if status.name == 'Downgraded':
            raise ValidationError(_('Vehicle in a state of downgraded '))

        if 'driver_status' in vals and vals['driver_status'] == '1' and not self.receive_car:
            return super(FleetVehicleAssignationLog, self).write(vals)
        else:
            # # check trong thoi gian nay lai xe co trong lich k
            self.env.cr.execute("""
                select date_start,date_end from fleet_vehicle_assignation_log
                    where give_car_back IS NULL and receive_car IS NULL and driver_id = %s and id != %s and status = 'running' and driver_status = '1'
                ORDER BY date_start ASC   """,
                                (driver_id, str(assignation_id),))
            # self.env.cr.execute(sql_driver)
            ardata = self.env.cr.fetchall()
            ardata_length = len(ardata)

            if ardata_length > 0:
                if date_start > ardata[ardata_length - 1][0]:
                    if date_start <= ardata[ardata_length - 1][1]:
                        raise ValidationError(_('During that time the driver has a running schedule'))

                else:
                    for data in ardata:
                        if data[0] <= date_start <= data[1]:
                            raise ValidationError(_('During that time the driver has a running schedule'))
                    count = 0
                    for data in ardata:
                        if date_start > data[0]:
                            count += 1
                        elif date_start < data[0]:
                            break

                    if date_end > ardata[count][0]:
                        raise ValidationError(_('There is a schedule in this time frame'))

            # # check trong khoang thoi gian nay xe da co lich chay chua
            self.env.cr.execute("""
                select date_start,date_end from fleet_vehicle_assignation_log
                    where give_car_back IS NULL and receive_car IS NULL 
                and vehicle_id = %s and driver_id = %s and id != %s and status = 'running' and driver_status = '1'
                    ORDER BY date_start ASC   """,
                                (vehicle_id, driver_id, str(assignation_id),))
            # self.env.cr.execute(sql_driver)

            ardata = self.env.cr.fetchall()
            ardata_length = len(ardata)

            if ardata_length > 0:
                if date_start > ardata[ardata_length - 1][0]:
                    if date_start <= ardata[ardata_length - 1][1]:
                        raise ValidationError(_('During this time the car had a running schedule'))

                else:
                    for data in ardata:
                        if date_start >= data[0] and date_start <= data[1]:
                            raise ValidationError(_('During this time the car had a running schedule'))
                            break
                    count = 0
                    for data in ardata:
                        if date_start > data[0]:
                            count += 1
                        elif date_start < data[0]:
                            break

                    if date_end > ardata[count][0]:
                        raise ValidationError(_('There is a schedule in this time frame'))

            self.env.cr.execute(
                """Update fleet_vehicle_status Set vehicle_id = %s  , driver_id =%s , 
                    date_start = %s , date_end = %s  where id = %s  """,
                (str(vehicle_id), str(driver_id), str(date_start), str(date_end), str(status_id)))
            vals['date_start'] = date_start
            vals['date_end'] = date_end
            return super(FleetVehicleAssignationLog, self).write(vals)


class VehicleAttLine(models.Model):
    _name = 'vehicle.att.line'
    _description = 'Vehicle Atribute Line'
    _order = ' sequence'

    vehicle_id = fields.Many2one('fleet.vehicle', string='Order Reference', index=True, required=True,
                                 ondelete='cascade')
    name = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)

    app_param_group_id = fields.Many2one('fleet.param.group', string='Appparam Group', change_default=True)
    app_param_id = fields.Many2one('fleet.app.param', string='Appparam',
                                   change_default=True)
    app_param_value_id = fields.Many2one('fleet.app.param.value', string='Apppram Value',
                                         change_default=True)
    is_selectedGroup = fields.Boolean(string='Is selected', default=False)
    is_selectedAppParam = fields.Boolean(string='Is selected appparam', default=False)
    status = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted')], 'Status', default='running')

    @api.onchange('app_param_group_id')
    def onchange_app_param_group_id(self):
        for rec in self:
            rec.is_selectedGroup = True
            return {'domain': {'app_param_id': [('group_id', '=', rec.app_param_group_id.id)]}}

    @api.onchange('app_param_id')
    def onchange_app_param_value_id(self):
        for rec in self:
            rec.is_selectedAppParam = True
            return {'domain': {'app_param_value_id': [('param_id', '=', rec.app_param_id.id)]}}

    def unlink(self):
        for id in self.ids:
            check = self.env['vehicle.att.line'].search([('id', '=', id)], limit=1)
            if check:
                check.write({'status': StatusType.Deleted.value})
        return self


class FleetLocationLog(models.Model):
    _name = 'tc.positions'
    _description = 'Fleet location'
    _order = 'devicetime asc'

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    latitude = fields.Float(string='Latitude', digits=(9, 6))
    longitude = fields.Float(string='Longitude', digits=(9, 6))
    assign_date_time = fields.Datetime(string="Assign Date", default=datetime.now())
    stop_time = fields.Integer(string='Stop Time', default=0)
    status = fields.Selection([
        ('0', 'Stopped'),
        ('1', 'Running')
    ], 'Vehicle status', default='1')
    isCheckPush = fields.Boolean(store=False)
    protocol = fields.Char()
    deviceid = fields.Integer()
    servertime = fields.Datetime()
    devicetime = fields.Datetime()
    fixtime = fields.Datetime()
    valid = fields.Boolean()
    altitude = fields.Float()
    speed = fields.Float()
    course = fields.Float()
    address = fields.Char()
    attributes = fields.Char()
    accuracy = fields.Float()
    network = fields.Char()

    @api.model
    def create_multiple(self, vals):
        for val in vals:
            if val['vehicle_id']:
                super(FleetLocationLog, self).create(val)
            else:
                raise ValidationError('Vehicle id not found')
        return {
            "records": ['Successful!']
        }


class SosRegisterDriver(models.Model):
    _name = 'sharevan.driver.sos'
    _inherit = 'sharevan.driver.sos'
    _description = 'Driver sos register'

    continue_check = fields.Boolean(string='Continue routing')
    delay_time = fields.Integer('Delay Time')
    address = fields.Char('Address')


class FleetVehicleResPartnerRel(models.Model):
    _name = Constants.PARTNER_VEHICLE
    _inherit = Constants.PARTNER_VEHICLE
    _description = 'table many2many of fleet_vehicle and res_partner'


class Color(models.Model):
    _name = 'fleet.color'

    name = fields.Char(string='Color')
