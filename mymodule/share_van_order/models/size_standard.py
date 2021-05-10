from odoo import models


class SizeStandard(models.Model):
    _name = 'sharevan.size.standard'
    _description = 'size standard for cargo'
    _inherit = 'sharevan.size.standard'


class CompanyCareer(models.Model):
    _name = 'sharevan.career'
    _inherit = 'sharevan.career'
    _description = 'customer career'
