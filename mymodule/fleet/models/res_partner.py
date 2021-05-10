# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

# class DriverLicense(models.TransientModel):
#     _name = 'driver.licence'

# class ResPartner(models.Model):
#     _inherit = _inherit = ['res.partner']
#
#     plan_to_change_car = fields.Boolean('Plan To Change Car', default=False)
#     company_type = fields.Selection(selection_add=[('driver', 'Driver')])
#     is_driver = fields.Boolean(string='Is a driver', default=False)
#     account_driver = fields.Char()
#     user_driver = fields.Char(string="User Driver")
#     ssn = fields.Char(string="Card Id")
#     birth_date = fields.Date(string="Birth Day")
#     hire_date = fields.Date(string="Hire Date")
#     leave_date = fields.Date(string="Leave Date")
#     driver_code = fields.Char()
#     # image = fields.Many2many('ir.attachment', string="Image")
#     attach_File = fields.Many2many('ir.attachment',string="Attach File")
#
#     @api.model
#     @api.returns('self', lambda rec: rec.id)
#     def create(self, vals):
#         res = super(ResPartner,self).create(vals)
#         if res.is_driver:
#             v = {
#                 'active': True,
#                 'login': res.user_driver,
#                 'partner_id': res.id
#             }
#             user_id = self.env['res.users'].sudo().create(v)
#         return res
#
#         # if vals.get('user_id', False):
#         #     user_id = self.env['res.users'].browse(vals.get('user_id', False))
#         #     vals.update({'department_id': user_id.department_id and user_id.department_id.id or False})
#         #     print(super(ResPartner, self).create(vals))
#         # return None
#
#     @api.depends('is_company')
#     def _compute_company_type(self):
#         for partner in self:
#             if partner.is_driver == True:
#                 partner.company_type = 'driver'
#             else:
#                 partner.company_type = 'company' if partner.is_company else 'driver'
#
#     def _write_company_type(self):
#         for partner in self:
#             if partner.company_type == 'driver':
#                 self.is_driver = True
#                 self.is_company = False
#             else:
#                 self.is_driver = False
#                 partner.is_company = partner.company_type == 'company'
#
#     @api.onchange('company_type')
#     def onchange_company_type(self):
#         for partner in self:
#             if self.company_type == 'driver':
#                 self.is_driver = True
#                 self.is_company = False
#             else:
#                 self.is_driver = False
#                 self.is_company = (self.company_type == 'company')