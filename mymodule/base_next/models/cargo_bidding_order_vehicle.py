from mymodule.constants import Constants
from odoo import models, fields, api, _


class CargoBiddingOrderVehicle(models.Model):
    _name = Constants.SHAREVAN_CARGO_BIDDING_ORDER_VEHICLE
    _description = 'Cargo bidding order vehicle'
    cargo_id = fields.Many2one(Constants.SHAREVAN_CARGO, string='Cargo')
    bidding_vehicle_id = fields.Integer()
    bidding_order_id = fields.Integer()
    status = fields.Selection([
        ('0', 'deleted'),
        ('1', 'running')])
