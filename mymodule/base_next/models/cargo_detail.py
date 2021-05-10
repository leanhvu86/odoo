from mymodule.constants import Constants
from odoo import models, fields, api, _

class CargoDetail(models.Model):
    _name = Constants.SHAREVAN_CARGO_DETAIL
    _description = 'Cargo detail'
    cargo_id = fields.Many2one(Constants.SHAREVAN_CARGO, string='Cargo')
    routing_plan_day_id = fields.Many2one(Constants.SHAREVAN_ROUTING_PLAN_DAY, 'Routing plan day')