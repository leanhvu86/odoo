from odoo import models


class CargoPrice(models.Model):
    _name = 'sharevan.cargo.price'
    _description = 'Cargo price'
    _inherit = 'sharevan.cargo.price'
