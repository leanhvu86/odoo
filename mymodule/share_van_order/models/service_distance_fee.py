# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ShareVanServiceDistanceFee(models.Model):
    MODEL = 'sharevan.service.distance.fee'
    _name = 'sharevan.service.distance.fee'
    _description = 'Service fee'

    unit = fields.Many2one('distance.unit', string='Unit')
    fromD = fields.Float(string="From", copy=True)
    toD = fields.Float(string="To", copy=True)
    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    fee = fields.Float(string='Shipment fee', digits=(12, 3))
    status = fields.Selection([('running', 'Running'), ('deleted', 'Deleted')], string='Status',
                              default='running')


