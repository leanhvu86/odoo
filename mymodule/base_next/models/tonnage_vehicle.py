# -*- coding: utf-8 -*-
from mymodule.base_next.controllers.api.base_method import BaseMethod
from odoo import _, fields, models, api
from odoo.exceptions import ValidationError, UserError


class ShareVanTonnageVehicle(models.Model):
    _name = 'sharevan.tonnage.vehicle'
    MODEL = 'sharevan.tonnage.vehicle'
    _description = 'ShareVan Tonnage Vehicle'

    code = fields.Char(string='Code', required=True)
    name = fields.Char(string='Name', required=True)
    max_tonnage = fields.Float(string='Max tonnage', required=True)
    status = fields.Selection([('running', 'Running'), ('deleted', 'Deleted')], string='Status',
                              default='running')

    type_unit = fields.Many2one('weight.unit', string='Weight Unit', required=True)

    description = fields.Text(string='Description')

    _sql_constraints = [
        ('code', 'unique (code)', 'Code must be unique!')
    ]



    @api.constrains('max_tonnage')
    def check_max_tonnage(self):
        for record in self:
            message = ""
            if record.max_tonnage < 0:
                notice = "Max tonnage must be greater than 0! "
                message += notice + "\n"
            message = message.strip()
            if message:
                raise ValidationError(message)

    def unlink(self):
        for id in self.ids:
            record = self.env['sharevan.tonnage.vehicle'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })
        return self


class ShareVanDriverReceived(models.Model):
    _name = 'sharevan.driver.received'
    MODEL = 'sharevan.driver.received'
    _description = 'ShareVan driver received'

    code = fields.Char(string='Code', required=True)
    name = fields.Char(string='Order code', required=True)
    driver_level_id = fields.Many2one('sharevan.title.award', string='Account level', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    order_id = fields.Integer(string='Order')
    order_type = fields.Selection([('0', 'In Zone'), ('1', 'Code Share'), ('2', 'Market place')],
                                  string='Order type',
                                  default='2')
    percent_commission = fields.Float(string='Percent commission')
    commission = fields.Float(string='Commission')
    coupon_id = fields.Integer(string='Coupon')
    amount = fields.Float(string='Amount', required=True)
    total_amount = fields.Float(string='Total Amount', required=True)
    status = fields.Selection([('running', 'Running'), ('deleted', 'Deleted')], string='Status',
                              default='running')

    @api.model
    def create(self, vals):
        if vals.get('code', 'New') == 'New':
            vals['code'] = self.env['ir.sequence'].next_by_code(
                'self.sharevan.driver.recieved') or 'New'
        result = super(ShareVanDriverReceived, self).create(vals)
        return result
