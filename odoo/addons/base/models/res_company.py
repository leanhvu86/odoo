# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import logging
import os
import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError
from odoo.modules.module import get_resource_path

from random import randrange
from PIL import Image
from .utils import validate_utils as validate

_logger = logging.getLogger(__name__)


class WeightUnit(models.Model):
    _name = "weight.unit"
    MODEL = "weight.unit"
    _description = 'Unit measuring weight'
    _order = 'code'

    name = fields.Char(string='Name',required=True)
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
    status = fields.Selection([('running', 'Running'), ('deleted', 'deleted')], string='Status',
                              default='running')


class VolumeUnit(models.Model):
    _name = "volume.unit"
    MODEL = "volume.unit"

    name = fields.Char(string='Volume Name',required=True)
    volume_code = fields.Char(string='Volume Code')
    length_unit_name = fields.Char(string='Length Name')
    length_unit_code = fields.Char(string='Length Code')
    description = fields.Text(string='Description')
    status = fields.Selection([('running', 'Running'), ('deleted', 'deleted')], string='Status',
                              default='running')


class ParcelUnit(models.Model):
    _name = "parcel.unit"
    MODEL = "parcel.unit"

    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
    status = fields.Selection([('running', 'Running'), ('deleted', 'deleted')], string='Status',
                              default='running')


class Company(models.Model):
    _name = "res.company"
    _description = 'Companies'
    _order = 'sequence, name'

    def copy(self, default=None):
        raise UserError(_('Duplicating a company is not allowed. Please create a new company instead.'))

    def _get_logo(self):
        return base64.b64encode(
            open(os.path.join(tools.config['root_path'], 'addons', 'base', 'static', 'img', 'res_company_logo.png'),
                 'rb').read())

    @api.model
    def _get_euro(self):
        return self.env['res.currency.rate'].search([('rate', '=', 1)], limit=1).currency_id

    # @api.constrains('phone')
    # def check_phone_number(self):
    #     return validate.validate_phone_number(self)

    @api.constrains('mail')
    def check_mail(self):
        return validate.validate_mail(self)

    @api.constrains('street')
    def validate_street_field(self):
        for rec in self:
            if rec.street != False:
                return validate.check_string_contain_special_character(rec.street, 'Street')

    @api.constrains('street2')
    def validate_street2_field(self):
        for rec in self:
            if rec.street2 != False:
                return validate.check_string_contain_special_character(rec.street2, 'Street2')

    @api.constrains('city')
    def validate_city(self):
        for rec in self:
            if rec.city != False:
                return validate.check_string_contain_special_character(rec.city, 'City')

    @api.model
    def _get_user_currency(self):
        currency_id = self.env['res.users'].browse(self._uid).company_id.currency_id
        return currency_id or self._get_euro()

    def _get_default_favicon(self, original=False):
        img_path = get_resource_path('web', 'static/src/img/favicon.ico')
        with tools.file_open(img_path, 'rb') as f:
            if original:
                return base64.b64encode(f.read())
            # Modify the source image to add a colored bar on the bottom
            # This could seem overkill to modify the pixels 1 by 1, but
            # Pillow doesn't provide an easy way to do it, and this 
            # is acceptable for a 16x16 image.
            color = (randrange(32, 224, 24), randrange(32, 224, 24), randrange(32, 224, 24))
            original = Image.open(f)
            new_image = Image.new('RGBA', original.size)
            height = original.size[1]
            width = original.size[0]
            bar_size = 1
            for y in range(height):
                for x in range(width):
                    pixel = original.getpixel((x, y))
                    if height - bar_size <= y + 1 <= height:
                        new_image.putpixel((x, y), (color[0], color[1], color[2], 255))
                    else:
                        new_image.putpixel((x, y), (pixel[0], pixel[1], pixel[2], pixel[3]))
            stream = io.BytesIO()
            new_image.save(stream, format="ICO")
            return base64.b64encode(stream.getvalue())

    # name = fields.Char(related='partner_id.name', string='Company Name', required=True, store=True, readonly=False)
    name = fields.Char(string='Company Name', required=True, store=True, readonly=False)
    sequence = fields.Integer(help='Used to order Companies in the company switcher', default=10)
    parent_id = fields.Many2one('res.company', string='Parent Company', index=True)
    child_ids = fields.One2many('res.company', 'parent_id', string='Child Companies')
    partner_id = fields.Many2one('res.partner', string='Partner')
    report_header = fields.Text(string='Company Tagline',
                                help="Appears by default on the top right corner of your printed documents (report header).")
    report_footer = fields.Text(string='Report Footer', translate=True,
                                help="Footer text displayed at the bottom of all reports.")
    logo = fields.Image("Image", max_width=128, max_height=128)
    # logo_web: do not store in attachments, since the image is retrieved in SQL for
    # performance reasons (see addons/web/controllers/main.py, Binary.company_logo)
    logo_web = fields.Binary(store=True, attachment=False)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self._get_user_currency())
    user_ids = fields.Many2many('res.users', 'res_company_users_rel', 'cid', 'user_id', string='Accepted Users')
    account_no = fields.Char(string='Account No.')
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street2')
    zip = fields.Char(string='Zip')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string="Fed. State")
    bank_ids = fields.One2many('res.partner.bank', 'company_id', string='Bank Accounts',
                               help='Bank accounts related to this company')
    country_id = fields.Many2one('res.country', string="Country")
    email = fields.Char(store=True, readonly=False)
    phone = fields.Char(store=True, readonly=False)
    website = fields.Char(readonly=False)
    vat = fields.Char(string="Tax ID", readonly=False)
    company_registry = fields.Char()
    paperformat_id = fields.Many2one('report.paperformat', 'Paper format',
                                     default=lambda self: self.env.ref('base.paperformat_euro',
                                                                       raise_if_not_found=False))
    external_report_layout_id = fields.Many2one('ir.ui.view', 'Document Template')
    base_onboarding_company_state = fields.Selection([
        ('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")],
        string="State of the onboarding company step", default='not_done')
    favicon = fields.Binary(string="Company Favicon",
                            help="This field holds the image used to display a favicon for a given company.",
                            default=_get_default_favicon)
    font = fields.Selection(
        [("Lato", "Lato"), ("Roboto", "Roboto"), ("Open_Sans", "Open Sans"), ("Montserrat", "Montserrat"),
         ("Oswald", "Oswald"), ("Raleway", "Raleway")], default="Lato")
    primary_color = fields.Char()
    secondary_color = fields.Char()
    sale = fields.Float('Sale')
    status = fields.Selection([('running', 'Active'),
                               ('deleted', 'Deactivate')], 'Status', help='Status', default="running")
    priority = fields.Selection([
        ('1', 'Bad'),
        ('2', 'Low'),
        ('3', 'Normal'),
        ('4', 'Good'),
        ('5', 'Perfect')
    ], 'Priority', default='3', help='Priority', required=True)
    weight_unit_id = fields.Many2one('weight.unit', string='Weight Unit', required=True,
                                     default=lambda self: self._get_weight_unit())
    volume_unit_id = fields.Many2one('volume.unit', string='Volume Unit', required=True,
                                     default=lambda self: self._get_volume_unit())
    parcel_unit_id = fields.Many2one('parcel.unit', string='Parcel Unit', required=True,
                                     default=lambda self: self._get_parcel_unit())
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The company name must be unique !')
    ]

    @api.model
    def _get_weight_unit(self):
        weight_unit_id = self.env['res.users'].browse(self._uid).company_id.weight_unit_id
        return weight_unit_id or self._get_none_weight_unit()

    @api.model
    def _get_none_weight_unit(self):
        return self.env['weight.unit'].search([('id', '=', 1)], limit=1).id

    @api.model
    def _get_volume_unit(self):
        volume_unit_id = self.env['res.users'].browse(self._uid).company_id.volume_unit_id
        return volume_unit_id or self._get_none_volume_unit()

    @api.model
    def _get_none_volume_unit(self):
        return self.env['volume.unit'].search([('id', '=', 1)], limit=1).id

    @api.model
    def _get_parcel_unit(self):
        parcel_unit_id = self.env['res.users'].browse(self._uid).company_id.parcel_unit_id
        return parcel_unit_id or self._get_none_parcel_unit()

    @api.model
    def _get_none_parcel_unit(self):
        return self.env['parcel.unit'].search([('id', '=', 1)], limit=1).id

    def init(self):
        for company in self.search([('paperformat_id', '=', False)]):
            paperformat_euro = self.env.ref('base.paperformat_euro', False)
            if paperformat_euro:
                company.write({'paperformat_id': paperformat_euro.id})
        sup = super(Company, self)
        if hasattr(sup, 'init'):
            sup.init()

    @api.onchange('state_id')
    def _onchange_state(self):
        if self.state_id.country_id:
            self.country_id = self.state_id.country_id

    def on_change_country(self, country_id):
        # This function is called from account/models/chart_template.py, hence decorated with `multi`.
        self.ensure_one()
        currency_id = self._get_user_currency()
        if country_id:
            currency_id = self.env['res.country'].browse(country_id).currency_id
        return {'value': {'currency_id': currency_id.id}}

    @api.onchange('country_id')
    def _onchange_country_id_wrapper(self):
        res = {'domain': {'state_id': []}}
        if self.country_id:
            res['domain']['state_id'] = [('country_id', '=', self.country_id.id)]
        values = self.on_change_country(self.country_id.id)['value']
        for fname, value in values.items():
            setattr(self, fname, value)
        return res

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        context = dict(self.env.context)
        newself = self
        if context.pop('user_preference', None):
            # We browse as superuser. Otherwise, the user would be able to
            # select only the currently visible companies (according to rules,
            # which are probably to allow to see the child companies) even if
            # she belongs to some other companies.
            companies = self.env.user.company_ids
            args = (args or []) + [('id', 'in', companies.ids)]
            newself = newself.sudo()
        return super(Company, newself.with_context(context))._name_search(name=name, args=args, operator=operator,
                                                                          limit=limit, name_get_uid=name_get_uid)

    @api.model
    @api.returns('self', lambda value: value.id)
    def _company_default_get(self, object=False, field=False):
        """ Returns the user's company
            - Deprecated
        """
        _logger.warning(
            _("The method '_company_default_get' on res.company is deprecated and shouldn't be used anymore"))
        return self.env.company

    # deprecated, use clear_caches() instead
    def cache_restart(self):
        self.clear_caches()

    @api.model
    def create(self, vals):
        if not vals.get('favicon'):
            vals['favicon'] = self._get_default_favicon()
        # if not vals.get('name') or vals.get('partner_id'):
        if not vals.get('name'):
            self.clear_caches()
            return super(Company, self).create(vals)
        # partner = self.env['res.partner'].create({
        #     'name': vals['name'],
        #     'is_company': True,
        #     'image_1920': vals.get('logo'),
        #     'email': vals.get('email'),
        #     'phone': vals.get('phone'),
        #     'website': vals.get('website'),
        #     'vat': vals.get('vat'),
        # })
        # compute stored fields, for example address dependent fields
        # partner.flush()
        # vals['partner_id'] = partner.id
        self.clear_caches()
        company = super(Company, self).create(vals)
        # The write is made on the user to set it automatically in the multi company group.
        self.env.user.write({'company_ids': [(4, company.id)]})

        # Make sure that the selected currency is enabled
        if vals.get('currency_id'):
            currency = self.env['res.currency'].browse(vals['currency_id'])
            if not currency.active:
                currency.write({'active': True})
        return company

    def write(self, values):
        self.clear_caches()
        # Make sure that the selected currency is enabled
        if values.get('currency_id'):
            currency = self.env['res.currency'].browse(values['currency_id'])
            if not currency.active:
                currency.write({'active': True})

        return super(Company, self).write(values)

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive companies.'))

    def open_company_edit_report(self):
        self.ensure_one()
        return self.env['res.config.settings'].open_company()

    def write_company_and_print_report(self):
        context = self.env.context
        report_name = context.get('default_report_name')
        active_ids = context.get('active_ids')
        active_model = context.get('active_model')
        if report_name and active_ids and active_model:
            docids = self.env[active_model].browse(active_ids)
            return (self.env['ir.actions.report'].search([('report_name', '=', report_name)], limit=1)
                    .report_action(docids))

    @api.model
    def action_open_base_onboarding_company(self):
        """ Onboarding step for company basic information. """
        action = self.env.ref('base.action_open_base_onboarding_company').read()[0]
        action['res_id'] = self.env.company.id
        return action

    def set_onboarding_step_done(self, step_name):
        if self[step_name] == 'not_done':
            self[step_name] = 'just_done'

    def get_and_update_onbarding_state(self, onboarding_state, steps_states):
        """ Needed to display onboarding animations only one time. """
        old_values = {}
        all_done = True
        for step_state in steps_states:
            old_values[step_state] = self[step_state]
            if self[step_state] == 'just_done':
                self[step_state] = 'done'
            all_done = all_done and self[step_state] == 'done'

        if all_done:
            if self[onboarding_state] == 'not_done':
                # string `onboarding_state` instead of variable name is not an error
                old_values['onboarding_state'] = 'just_done'
            else:
                old_values['onboarding_state'] = 'done'
            self[onboarding_state] = 'done'
        return old_values

    def action_save_onboarding_company_step(self):
        if bool(self.street):
            self.set_onboarding_step_done('base_onboarding_company_state')

    @api.model
    def _get_main_company(self):
        try:
            main_company = self.sudo().env.ref('base.main_company')
        except ValueError:
            main_company = self.env['res.company'].sudo().search([], limit=1, order="id")

        return main_company

    def update_scss(self):
        # Deprecated, to be deleted in master
        return ''
