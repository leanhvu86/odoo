from odoo import models


class NotificationBiddingUser(models.Model):
    _name = 'bidding.notification.user.rel'
    _description = 'Show the individual receiver and if they have read or not'
    _inherit = 'bidding.notification.user.rel'