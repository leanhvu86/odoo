from mymodule.constants import Constants
from mymodule.enum.MessageType import NotificationSocketType
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CargoPrice(models.Model):
    _name = Constants.SHAREVAN_CARGO_PRICE
    _description = 'Cargo price'

    name = fields.Char('name')
    price = fields.Float('Price')
    status = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted')],
                              string='Status',
                              default='running')
    from_date = fields.Datetime('From date')
    to_date = fields.Datetime('To date')

    @api.model
    def create(self, vals):
        if vals.get('price'):
            vals['name'] = str(vals.get('price'))
        res = super(CargoPrice, self).create(vals)
        return res

    def write(self, vals):
        if vals.get('price'):
            vals['name'] = str(vals.get('price'))
        res = super(CargoPrice, self).write(vals)
        return res

    @api.constrains('price')
    def _check_price(self):
        for record in self:
            if record.price < 0:
                notice = "Price value is invalid, must be greater than 0"
                raise ValidationError(notice)
