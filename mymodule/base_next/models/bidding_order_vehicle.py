from mymodule.constants import Constants
from odoo import models, fields, api, _


class BiddingOrderVehicle(models.Model):
    _name = Constants.SHAREVAN_BIDDING_ORDER_VEHICLE
    _description = 'Bidding order vehicle'
    bidding_order_id = fields.Many2one(Constants.SHAREVAN_BIDDING_ORDER, string='Bidding order')
    bidding_vehicle_id = fields.Many2one(Constants.SHAREVAN_BIDDING_VEHICLE, string='Bidding vehicle')


