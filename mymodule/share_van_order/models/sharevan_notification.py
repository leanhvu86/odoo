from odoo import models, _, http

class Notification(models.Model):
    _name = 'sharevan.notification'
    _description = 'Notification send to users'
    _inherit = 'sharevan.notification'