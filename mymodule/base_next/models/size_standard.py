from mymodule.base_next.controllers.api.base_method import BaseMethod
from mymodule.constants import Constants
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SizeStandard(models.Model):
    _name = Constants.SHAREVAN_SIZE_STANDARD
    _description = 'size standard for cargo'

    type = fields.Char('Size type')
    name = fields.Char('Name')
    length = fields.Float('Length')
    width = fields.Float('Width')
    height = fields.Float('Height')
    long_unit = fields.Many2one(Constants.DISTANCE_UNIT, string='Long unit')
    weight_unit = fields.Many2one(Constants.WEIGHT_UNIT, string='Weight unit')
    from_weight = fields.Float('From weight')
    to_weight = fields.Float('To weight')
    price_id = fields.Many2one(Constants.SHAREVAN_CARGO_PRICE, 'price')
    price = fields.Float('Price')
    size_standard_seq = fields.Char(string='Size standard Reference', required=True, copy=False, readonly=True,
                                    index=True,
                                    default=lambda self: _('New'))
    cargo_price_ids = fields.Many2one(Constants.SHAREVAN_CARGO_PRICE, string='Cargo price', required=True)

    @api.model
    def create(self, vals):
        if vals.get('size_standard_seq', 'New') == 'New':
            vals['size_standard_seq'] = self.env['ir.sequence'].next_by_code(
                'self.sharevan.size.standard') or 'New'
        print(vals.get('cargo_price_ids'))
        vals['name'] = str(vals['length']) + 'x' + str(vals['width']) + 'x' + str(vals['height'])
        cargo_price = self.env[Constants.SHAREVAN_CARGO_PRICE].search([('id', '=', vals.get('cargo_price_ids'))])
        vals['price'] = cargo_price.price
        result = super(SizeStandard, self).create(vals)
        return result

    def write(self, vals):
        cargo_price = self.env[Constants.SHAREVAN_CARGO_PRICE].search([('id', '=', vals.get('cargo_price_ids'))])
        vals['price'] = cargo_price.price
        if 'length' in vals:
            length = vals['length']
        else:
            length = self.length
        if 'width' in vals:
            width = vals['width']
        else:
            width = self.width
        if 'height' in vals:
            height = vals['height']
        else:
            height = self.height
        vals['name'] = str(length) + 'x' + str(width) + 'x' + str(height)
        res = super(SizeStandard, self).write(vals)
        return res


class CompanyCareer(models.Model):
    _name = 'sharevan.career'
    _description = 'customer career'

    name = fields.Char('Career')
    code = fields.Char('Code')
    level = fields.Integer('Level')
    status = fields.Selection([('running', 'Running'), ('deleted', 'Deleted')], 'Status', default='running')

    @api.onchange('level')
    def onchange_amount(self):
        for record in self:
            if record['level'] < 0:
                record.update({'level': 0})
                notice = "Level must have a value greater than 0!"
                self.env.user.notify_danger(message=notice)

    @api.model
    def create(self, vals):
        seq = BaseMethod.get_new_sequence('sharevan.career', 'SC', 6, 'code')
        vals['code'] = seq
        result = super(CompanyCareer, self).create(vals)
        return result

    def unlink(self):
        for id in self.ids:
            record = self.env['sharevan.career'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })
        return self
