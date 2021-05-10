from odoo import models, _, http, fields


class ShareVanWarningType(models.Model):
    _description = "Warning type"
    _name = 'sharevan.warning.type'
    _inherit = 'sharevan.warning.type'
