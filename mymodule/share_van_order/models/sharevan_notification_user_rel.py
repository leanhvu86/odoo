from odoo import models, _, http


class NotificationUser(models.Model):
    _name = 'sharevan.notification.user.rel'
    _description = 'Show the individual receiver and if they have read or not'
    _inherit = 'sharevan.notification.user.rel'
