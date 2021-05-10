from odoo import models, fields, api, _, http

class BiddingDriver(models.Model):
    _name = 'sharevan.bidding.driver'
    _inherit = 'sharevan.bidding.driver'
    _description = 'Sharevan Bidding Driver'

    # def driver_market_place_confirm_order(self):
    #     abc =123
    #     return 'abc'