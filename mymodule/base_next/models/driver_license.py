# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ShareVanDriverLicense(models.Model):
    _name = 'sharevan.driver.license'
    MODEL = 'sharevan.driver.license'

    _description = 'DLP driver license'

    name = fields.Char(string='Name', required=True)
    max_tonnage = fields.Float(string='Max Tonnage', required=True)
    type_unit = fields.Many2one('weight.unit', string='Weight Unit', required=True)
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict', required=True)
    status = fields.Selection([('running', 'Running'), ('deleted', 'Deleted')], string='Status',
                              default='running')
    description = fields.Text(string='Description')

    _sql_constraints = [
        ('name', 'unique (name)', 'Name must be unique!')
    ]

    def unlink(self):
        for id in self.ids:
            record = self.env['sharevan.driver.license'].search([('id', '=', id), ('status', '=', 'running')])
            record.write({
                'status': 'deleted'
            })
        return self

    @api.constrains('max_tonnage')
    def check_tonnage(self):
        for record in self:
            if record.max_tonnage <= 0:
                raise ValidationError("Max tonnage must be more than 0")


    def unlink(self):

        for selfId in self.ids:
            record_ids = self.env['sharevan.driver.license'].search([('id', '=', selfId)])
            record_ids.write({
                'status': 'deleted'
            })
