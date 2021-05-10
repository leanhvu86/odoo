from odoo import models, _, http, fields

class ShareVanZone(models.Model):
    _description = "Zone"
    _name = 'sharevan.zone'
    _inherit = 'sharevan.zone'
    _order = 'code'
