from odoo import models

class FleetReport(models.Model):
    _description = "Fleet Report"
    _name = 'fleet.report'
    _inherit = 'sharevan.report'
