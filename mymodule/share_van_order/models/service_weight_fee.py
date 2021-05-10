# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ShareVanServiceWeightFee(models.Model):
    _name = 'sharevan.service.weight.fee'
    MODEL = 'sharevan.service.weight.fee'
    _description = 'Fee by weight'

    unit = fields.Many2one('weight.unit', string='Unit',required=True)
    fromW = fields.Float(string='From', digits=(12, 3),required=True)
    toW = fields.Float(string='To', digits=(12, 3),required=True)
    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    fee = fields.Float(string='Fee by weight', digits=(12, 3))
    status = fields.Selection([('running', 'Running'), ('deleted', 'Deleted')], string='Status',
                              default='running')

    def unlink(self):
        for id in self.ids:
            record = self.env['sharevan.service.weight.fee'].search([('id', '=', id), ('status', '=', 'running')])
            record.write({
                'status': 'deleted'
            })
        return self