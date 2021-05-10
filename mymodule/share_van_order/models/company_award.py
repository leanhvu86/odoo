from mymodule.constants import Constants
from odoo import models, fields, api, _

class CompanyAward(models.Model):
    _name = 'company.award'
    _description = 'Company award'

    code = fields.Char(string='Cargo code', required=True, copy=False, readonly=True,
                       index=True,
                       default=lambda self: _('New'))
    name = fields.Char(string='Award')
    status = fields.Selection([
        ('0', 'deleted'),
        ('1', 'active')], string='Status', default='1', required=True)


