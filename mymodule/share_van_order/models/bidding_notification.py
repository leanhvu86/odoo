from odoo import models


class BiddingOrderReceive(models.Model):
    _name = 'bidding.notification'
    _description = 'Bidding order notification'
    _inherit = 'bidding.notification'