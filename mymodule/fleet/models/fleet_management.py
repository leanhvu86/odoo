# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-
import json as simplejson

from odoo import models, _, fields
from odoo.exceptions import ValidationError


class FleetManagement(models.Model):
    _name = 'fleet.management'
    _inherit = 'fleet.management'
    _description = 'fleet.management'








class FleetManagementDriverTemp(models.Model):
    _name = 'fleet.management.driver.temp'
    _inherit = 'fleet.management.driver.temp'
    _description = 'fleet.management.driver.temp'



class FleetManagementVehicleTemp(models.Model):
    _name = 'fleet.management.vehicle.temp'
    _inherit = 'fleet.management.vehicle.temp'
    _description = 'fleet.management.vehicle.temp'

    fleet_vehicle_id = fields.Many2one('fleet.vehicle', string="Fleet vehicle",
                                       domain=[('active', '=', True),('fleet_management_id','=',False)])
    name = fields.Char(related="fleet_vehicle_id.name")
    fleet_vehicle_type = fields.Char(related="fleet_vehicle_id.vehicle_type.name", string = "Vehicle type")
    state_vehicle = fields.Char(related="fleet_vehicle_id.state_id.name", string = "state vehicle")
    activity_duration_average = fields.Float(related="fleet_vehicle_id.activity_duration_average", string = "Activity duration average")
    amortization_period = fields.Float(related="fleet_vehicle_id.amortization_period", string = "Amortization period")
    tonnage_id = fields.Many2one('sharevan.tonnage.vehicle', 'Vehicle tonnage',
                                 help='Tonnage of the vehicle', related='fleet_vehicle_id.tonnage_id', store=False)