from odoo import models


class NotificationBiddingChannel(models.Model):
    _name = 'bidding.channel'
    _description = 'bidding channel'
    _inherit = 'bidding.channel'