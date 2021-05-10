import logging

from odoo import models, _, fields, api
from odoo.exceptions import ValidationError

logger = logging.getLogger(__name__)


class ShareVanServiceWeightFee(models.Model):
    _name = 'sharevan.price.quotation'
    MODEL = 'sharevan.price.quotation'
    _description = 'Price Quotation'
    _order = "name"

    name = fields.Char(string='Price Quotation Name')
    net_weight = fields.Float(string='Net weight level', digits=(12, 3), required=True,
                              help='Weight level change price limit')
    in_province_price = fields.Float(string='100 km', digits=(12, 3), required=True,
                                     help='In province price')
    in_zone_price = fields.Float(string='300 km', digits=(12, 3), required=True, help='In zone price')
    out_zone_price = fields.Float(string='> 300 km', digits=(12, 3), required=True, help='Out zone price')
    good_transport_price = fields.Float(string='Good transport area', digits=(12, 3), required=True,
                                        help='Good transport price, province have a lot of trading and good price. For example: Ha Noi, HCM, Da Nang ')

    description = fields.Text(string='Description')
    status = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted')], 'Status', default="running")
    level = fields.Selection([('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], 'Level',
                             required=True)
    type = fields.Selection([('express', 'Express'), ('economy', 'Economy'), ('just_in_time', 'Just In Time'),
                             ('normal', 'Normal')], string='Type Package', required=True)
    extra_weight_cost = fields.Float(string='Extra weight cost', digits=(12, 3), required=True,help='weight cost unit')
    extra_weight_price = fields.Float(string='Extra weight price', digits=(12, 3), required=True,help='extra weight per weight cost')
    parity_price = fields.Float(string='Parity price', digits=(12, 3),help='parity price with express package only')
    fee_one = fields.Float(string='Fee one', digits=(12, 3),help='parity price with express package only')
    fee_two = fields.Float(string='Fee two', digits=(12, 3),help='parity price with express package only')
    fee_three = fields.Float(string='Fee three', digits=(12, 3),help='parity price with express package only')
    fee_zero = fields.Float(string='Fee zero', digits=(12, 3),help='parity price with express package only')


    @api.model
    def create(self, vals):
        result = super(ShareVanServiceWeightFee, self).create(vals)
        return result

    @api.onchange('type')
    def _on_change_type(self):
        for record in self:
            if record.level and record.type:
                price_record = self.env[ShareVanServiceWeightFee._name].search(
                    [('status', '=', 'running'), ('type', '=', record.type)])
                if price_record:
                    for price in price_record:
                        if price.id != record.id and price.type == record.type and price.level == record.level:
                            raise ValidationError('Level package have been exist already!')
                name = record.type + '-' + record.level
                name = name.upper()
                record.update({'name': name})
            else:
                raise ValidationError('You have to register level')

    @api.onchange('level')
    def _on_change_level(self):
        for record in self:
            if record.type and record.level:
                price_record = self.env[ShareVanServiceWeightFee._name].search(
                    [('status', '=', 'running'), ('type', '=', record.type)])
                if price_record:
                    for price in price_record:
                        if price.id != record.id and price.type == record.type and price.level == record.level:
                            raise ValidationError('Level package have been exist already!')
                name = record.type + '-' + record.level
                name = name.upper()
                record.update({'name': name})
            else:
                raise ValidationError('You have to register type')

    @api.onchange('parity_price')
    def _on_change_parity_price(self):
        for record in self:
            if record.parity_price:
                if record.parity_price <= 0:
                    record.update({'parity_price': 1})
                    raise ValidationError('net_weight is bigger than zero')
            else:
                raise ValidationError('You have to register type')

    @api.onchange('extra_weight_price', 'net_weight', 'in_province_price', 'in_zone_price', 'out_zone_price',
                  'good_transport_price', 'extra_weight_cost')
    def _on_change_net_weight(self):
        for record in self:
            if record.extra_weight_price:
                if record.extra_weight_price < 0:
                    record.update({'extra_weight_price': 0.0})
                    raise ValidationError('extra_weight_price is bigger than zero')
            if record.net_weight:
                if record.net_weight < 0:
                    record.update({'net_weight': 0})
                    raise ValidationError('net_weight is bigger than zero')
            if record.in_province_price:
                if record.in_province_price < 0:
                    record.update({'in_province_price': 0.0})
                    raise ValidationError('in_province_price is bigger than zero')
            if record.in_zone_price:
                if record.in_zone_price < 0:
                    record.update({'in_zone_price': 0.0})
                    raise ValidationError('in_zone_price is bigger than zero')
            if record.out_zone_price:
                if record.out_zone_price < 0:
                    record.update({'out_zone_price': 0.0})
                    raise ValidationError('out_zone_price is bigger than zero')
            if record.good_transport_price:
                if record.good_transport_price < 0:
                    record.update({'good_transport_price': 0.0})
                    raise ValidationError('good_transport_price is bigger than zero')
            if record.extra_weight_cost:
                if record.extra_weight_cost < 0:
                    record.update({'extra_weight_cost': 0})
                    raise ValidationError('extra_weight_cost is bigger than zero')
