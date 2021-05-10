from odoo import models, fields, api

# class Insurance(models.Model):
#     _name = 'sharevan.insurance'
#     _description = 'insurance'
#     insurance_code = fields.Char('insurance code')
#     insurance_name = fields.Char('insurance name')
#     vendor_id = fields.Many2one('fleet.vehicle.model.brand', 'vendor')
#     price = fields.Float(string='Cost', digits=(12, 3))
from odoo.exceptions import ValidationError


class SharevanServiceType(models.Model):
    _name = 'sharevan.service.type'
    MODEL = 'sharevan.service.type'
    _description = 'Sharevan Service Type'
    _inherit = 'sharevan.service.type'

    max_person = fields.Integer(string='Max person')
    max_weight = fields.Integer(string='Max weight')
    vendor_service_code = fields.Char(string='Vendor service code')



    @api.onchange('max_person', 'max_weight')
    def _onchange_state_id(self):
        if self.max_weight < 0.0:
            raise ValidationError('Max weight must be greater than 0')
        if self.max_person < 0.0:
            raise ValidationError('Max person must be greater than 0')
