from mymodule.constants import Constants
from odoo import fields, api,models
class MaintenanceSchedule(models.Model):
    _name = Constants.SHAREVAN_MAINTENANCE_SCHEDULE
    _description = 'Maintenance schedule'
    name = fields.Char('name')
    type = fields.Selection([('1','Định kì thời gian'),
                             ('2','Định kì quãng đường')],string='Maintenance type',default='1',required=True)
    priority = fields.Integer('Priority')
    start_date = fields.Date('Start date')
    next_date = fields.Date('Next date')
    notify_date_before = fields.Integer('Notify date before')
    start_meter = fields.Integer('Start meter')
    next_meter = fields.Integer('Next meter')
    unit_meter = fields.Many2one(Constants.DISTANCE_UNIT,string='Unit odometer')
    notify_meter_before = fields.Integer('Notify meter before')
    equipment_part_id = fields.Many2one(Constants.FLEET_VEHICLE_EQUIPMENT_PART, string='Equitment part')
    vehicle_id = fields.Many2one(Constants.FLEET_VEHILCE,string='Vehicle')
    # +id
    # +maintenance_template_id
    # +name
    # +type
    # +priority
    # +enabled
    # +start_date
    # +end_date
    # +date_type
    # +notify_date_before
    # +start_meter
    # +end_meter
    # +meter_type
    # +notify_meter_before
    # +start_hour
    # +end_hour
    # +hour_type
    # +notify_hour_before