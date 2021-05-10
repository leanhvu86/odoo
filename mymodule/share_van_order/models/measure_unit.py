# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class DistanceUnit(models.Model):
    _name = "distance.unit"
    _description = 'Unit measuring distance'
    _order = 'code'
    _inherit = "distance.unit"


class WeightUnit(models.Model):
    _name = "weight.unit"
    _description = 'Unit measuring weight'
    _order = 'code'
    _inherit = "weight.unit"
