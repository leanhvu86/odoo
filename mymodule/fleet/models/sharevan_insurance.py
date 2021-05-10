from odoo import api, models, fields,_
class Insurance (models.Model):
    _name = 'sharevan.insurance.fleet'
    _description = 'insurance'
    insurance_code = fields.Char('insurance code')
    insurance_name = fields.Char('insurance name')
    vendor_id = fields.Many2one('fleet.vehicle.model.brand','vendor')
    price = fields.Float('price')


