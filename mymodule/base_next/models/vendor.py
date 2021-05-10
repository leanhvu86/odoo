# -*- coding: utf-8 -*-
from mymodule.base_next.controllers.api.base_method import BaseMethod
from mymodule.base_next.controllers.api.validation import ValidationApi
from mymodule.base_next.models.utils import validate_utils
from mymodule.constants import Constants
from mymodule.enum.MessageType import NotificationSocketType
from odoo import api, models, fields, _, http
import base64
import collections
import datetime
import hashlib
import pytz
import threading
import re
from mymodule.share_van_order.models.utils import validate_utils as validate

from dateutil.relativedelta import relativedelta

from odoo.osv import expression
from odoo.exceptions import AccessError, ValidationError

import requests
from lxml import etree
from werkzeug import urls

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.modules import get_module_resource
from odoo.osv.expression import get_unaccent_wrapper
from odoo.exceptions import UserError, ValidationError

# Global variables used for the warning fields declared on the res.partner
# in the following modules : sale, purchase, account, stock
WARNING_MESSAGE = [
    ('no-message', 'No Message'),
    ('warning', 'Warning'),
    ('block', 'Blocking Message')
]
WARNING_HELP = 'Selecting the "Warning" option will notify user with the message, Selecting "Blocking Message" will throw an exception with the message and block the flow. The Message has to be written in the next field.'

ADDRESS_FIELDS = ('street', 'street2', 'zip', 'city_name', 'state_id', 'country_id')


@api.model
def _lang_get(self):
    return self.env['res.lang'].get_installed()


# put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
_tzs = [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]


def _tz_get(self):
    return _tzs


class Vendor(models.Model):
    _name = 'sharevan.vendor'
    _description = 'Vendor'

    def _default_category(self):
        return self.env['res.partner.category'].browse(self._context.get('category_id'))

    @api.constrains('email')
    def check_mail(self):
        for rec in self:
            if rec.email != False:
                match = re.search(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9]+\.[a-zA-Z0-9.]*\.*[vn|com|org|edu]{2}$)", rec.email)
                if match:
                    return True
                raise ValidationError(_('Format email address "Name <email@domain>'))
        return True

    @api.constrains('website')
    def check_website(self):
        for rec in self:
            if rec.website != False:
                match = re.search(r'[(http://)|\w]*?[\w]*\.[-/\w]*\.\w*[(/{1})]?[#-\./\w]*[(/{1,})]?', rec.website)
                if match:
                    return True
                raise ValidationError(_('Format email address "Name <https://www.odoo.com>'))
        return True


    # @api.onchange('country_id')
    # def check_country(self):
    #     for rec in self:
    #         if rec['country_id']['id']:
    #             if rec['state_id']['id']:
    #                 state = self.env['res.country.state'].search([('id', '=', rec['state_id']['id'])])
    #                 country = self.env['res.country'].search([('id', '=', rec['country_id']['id'])])
    #                 if country:
    #                     if state:
    #                         if state['country_id']['id'] != rec['country_id']['id']:
    #                             raise ValidationError(
    #                                 _(state['name'] + '  does not exist in ' + country['name']))
    #                 else:
    #                     raise ValidationError('Country does not exist!')

                # match = re.search(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9]+\.[a-zA-Z0-9.]*\.*[com|org|edu]{3}$)", rec.email)
                # if match:
                #     return True
                # raise ValidationError(_('Format email address "Name <email@domain>'))

    @api.constrains('vat')
    def check_vat_contain_special_character(self):
        if self:
            for rec in self:
                if rec.vat:
                    validate.check_string_contain_special_character(rec.vat, 'Tax ID')

    # @api.constrains('phone')
    # def check_phone(self):
    #     for rec in self:
    #         return validate_utils.validate_phone_number_v2(rec.phone)

    # @api.constrains('mobile')
    # def validate_mobile_field(self):
    #     for rec in self:
    #         if rec.mobile:
    #             if validate.check_string_contrain_special_character(rec.mobile, 'Mobile'):
    #                 if len(rec.mobile) != 11:
    #                     raise ValidationError(_('The mobile number must be equals 11 numbers'))
    #                 match = re.search(r"(^[+0-9]{1,3})*([0-9]{10,11}$)", rec.mobile)
    #                 if match:
    #                     pass
    #                 else:
    #                     raise ValidationError(_('The mobile number is wrong format.(eg. 0123456789)'))
    #                 return True

    @api.constrains('address')
    def validate_address_field(self):
        for rec in self:
            if rec.address != False:
                return validate.check_string_contain_special_character(rec.address, 'Address ')

    name = fields.Char(index=True, required=True)
    display_name = fields.Char(compute='_compute_display_name', store=True, index=True)
    date = fields.Date(index=True)
    title = fields.Many2one('res.partner.title')
    parent_id = fields.Many2one('res.partner', string='Related Company', index=True)
    parent_name = fields.Char(related='parent_id.name', readonly=True, string='Parent name')
    child_ids = fields.One2many('res.partner', 'parent_id', string='Contact', domain=[
        ('active', '=', True)])  # force "active_test" domain to bypass _search() override
    ref = fields.Char(string='Reference', index=True)
    tz = fields.Selection(_tz_get, string='Timezone', default=lambda self: self._context.get('tz'),
                          help="When printing documents and exporting/importing data, time values are computed according to this timezone.\n"
                               "If the timezone is not set, UTC (Coordinated Universal Time) is used.\n"
                               "Anywhere else, time values are computed according to the time offset of your web client.")
    lang = fields.Selection(_lang_get, string='Language', default=lambda self: self.env.lang,
                            help="All the emails and documents sent to this contact will be translated in this language.")
    active_lang_count = fields.Integer(compute='_compute_active_lang_count')
    tz_offset = fields.Char(compute='_compute_tz_offset', string='Timezone offset', invisible=True)
    user_id = fields.Many2one('res.users', string='Salesperson',
                              help='The internal user in charge of this contact.')
    vat = fields.Char(string='Tax ID',
                      help="The Tax Identification Number. Complete it if the contact is subjected to government taxes. Used in some legal statements.")

    bank_ids = fields.One2many('res.partner.bank', 'partner_id', string='Banks')
    website = fields.Char('Website Link')
    comment = fields.Text(string='Notes')

    category_id = fields.Many2many('res.partner.category', column1='partner_id',
                                   column2='category_id', string='Tags', default=_default_category)
    image_1920 = fields.Image("Image", max_width=128, max_height=128)
    credit_limit = fields.Float(string='Credit Limit')
    active = fields.Boolean(default=True)
    employee = fields.Boolean(help="Check this box if this contact is an Employee.")
    function = fields.Char(string='Job Position')
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city_name = fields.Char()
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict',
                               domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict')
    partner_latitude = fields.Float(string='Geo Latitude', digits=(16, 5))
    partner_longitude = fields.Float(string='Geo Longitude', digits=(16, 5))
    email = fields.Char()
    name_seq = fields.Char(string='Vendor Reference', required=True, copy=False, readonly=True, index=True,
                           default=lambda self: _('New'))
    email_formatted = fields.Char(
        'Formatted Email', compute='_compute_email_formatted',
        help='Format email address "Name <email@domain>"')
    phone = fields.Char()
    mobile = fields.Char()
    is_company = fields.Boolean(string='Is a Company', default=False,
                                help="Check if the contact is a company, otherwise it is a person")
    industry_id = fields.Many2one('res.partner.industry', 'Industry')
    # company_type is only an interface field, do not use it in business logic

    company_type = fields.Selection(string='Company Type',
                                    selection=[('company', 'Company')],
                                    compute='_compute_company_type', inverse='_write_company_type')
    company_id = fields.Many2one('res.company', 'Company', index=True, required=True, readonly=True,
                                 default=lambda self: self.env.company.id)
    color = fields.Integer(string='Color Index', default=0)
    user_ids = fields.One2many('res.users', 'partner_id', string='Users', auto_join=True)
    partner_share = fields.Boolean(
        'Share Partner', compute='_compute_partner_share', store=True,
        help="Either customer (not a user), either shared user. Indicated the current partner is a customer without "
             "access or with a limited access created for sharing data.")
    contact_address = fields.Char(compute='_compute_contact_address', string='Complete Address')
    commercial_partner_id = fields.Many2one('res.partner', compute='_compute_commercial_partner',
                                            string='Commercial Entity', store=True, index=True)
    commercial_company_name = fields.Char('Company Name Entity', compute='_compute_commercial_company_name',
                                          store=True)
    company_name = fields.Char('Company Name')
    district = fields.Char('District Name')
    attach_file = fields.Many2many('ir.attachment', string='Attach file')
    status = fields.Selection([('running', 'Active'),
                               ('deleted', 'Deactivate')
                               ], 'Status', help='Status', default="running")

    type = fields.Selection(
        [('vendor_service', 'Vendor service'),
         ('vendor_insurance', 'Vendor insurance'),
         ('vendor_equipment', 'Vendor equipment'),
         ('vendor_energy', 'Vendor energy'),
         ('maintenance_service', 'Maintenance service'),
         ('sos', 'Sos service'),
         ('another_type', 'Another type')],
        string='Type', default='vendor_service', required=True)

    _sql_constraints = [
        ('vat', 'UNIQUE (vat)', 'Tax ID already exists !'),
        ('website', 'UNIQUE (website)', 'Website already exists !'),
        ('email', 'UNIQUE (email)', 'Email already exists !'),
        ('phone', 'UNIQUE (phone)', 'Phone already exists !'),
        ('mobile', 'UNIQUE (mobile)', 'Mobile already exists !'),
    ]

    def unlink(self):

        for selfId in self.ids:
            record_ids = self.env['sharevan.vendor'].search([('id', '=', selfId)])
            record_ids.write({
                'status': 'deleted'
            })
            self.env.cr.execute(""" 
                                    UPDATE sharevan_insurance
                                    SET status= 'deleted'
                                    WHERE vendor_id = %s;  """, (selfId,))



        return self

    @api.model
    def _formatting_address_fields(self):
        """Returns the list of address fields usable to format addresses."""
        return self._address_fields()

    @api.model
    def _address_fields(self):
        """Returns the list of address fields that are synced from the parent."""
        return list(ADDRESS_FIELDS)

    @api.model
    def _lang_get(self):
        return self.env['res.lang'].get_installed()

    @api.onchange('phone')
    def check_phone_number(self):
        for rec in self:
            if rec.phone != False:
                if ValidationApi.validate_phone_number_v2(rec.phone) != True:
                    notice = "The phone number is wrong format.(eg. 0123456789)"
                    self.env.user.notify_danger(message=notice, title=NotificationSocketType.NOTIFICATION.value)
                    rec.update({'phone': False})

    @api.onchange('mobile')
    def check_mobile(self):
        for rec in self:
            if rec.mobile != False:
                if ValidationApi.validate_phone_number_v2(rec.mobile) != True:
                    notice = "The phone number is wrong format.(eg. 0123456789)"
                    self.env.user.notify_danger(message=notice, title=NotificationSocketType.NOTIFICATION.value)
                    rec.update({'mobile': False})

    @api.model
    def create(self, vals):
        if vals.get('name_seq', 'New') == 'New':
            vals['name_seq'] = BaseMethod.get_new_sequence('sharevan.vendor', 'VD', 12, 'name_seq')
        if vals['country_id']:
            if vals['state_id']:
                state = self.env['res.country.state'].search([('id', '=', vals['state_id'])])
                country = self.env['res.country'].search([('id', '=', vals['country_id'])])
                if country:
                    if state:
                        if state['country_id']['id'] != vals['country_id']:
                            raise ValidationError(
                                _(state['name']+ '  does not exist in '+ country['name']))
                else:
                    raise ValidationError('Country does not exist!')
        result = super(Vendor, self).create(vals)
        return result

    def write(self, vals):
            # if 'email' in vals:
            #     records = self.env['sharevan.vendor'].search([('email', '=', vals['email'])])
            #     if len(records.ids):
            #         raise ValidationError(
            #             _('Email existed!'))
        if 'country_id' in vals:
            country = self.env['res.country'].search([('id', '=', vals['country_id'])])
            if 'state_id' in vals:
                state = self.env['res.country.state'].search([('id', '=', vals['state_id'])])
                if country:
                    if state:
                        if state['country_id']['id'] != vals['country_id']:
                            raise ValidationError(
                                _(state['name'] + '  does not exist in ' + country['name']))
                else:
                    raise ValidationError('Country does not exist!')
            else:
                state = self.env['res.country.state'].search([('id', '=', self['state_id']['id'])])
                if country:
                    if state:
                        if state['country_id']['id'] != vals['country_id']:
                            raise ValidationError(
                                _(state['name'] + '  does not exist in ' + country['name']))
                else:
                    raise ValidationError('Country does not exist!')

        result = super(Vendor, self).write(vals)
        return result

    @api.depends(lambda self: self._display_address_depends())
    def _compute_contact_address(self):
        for partner in self:
            partner.contact_address = partner._display_address()

    def _compute_get_ids(self):
        for partner in self:
            partner.self = partner.id

    def _display_address_depends(self):
        # field dependencies of method _display_address()
        return self._formatting_address_fields() + [
            'country_id.address_format', 'country_id.code', 'country_id.name',
            'company_name', 'state_id.code', 'state_id.name',
        ]

    @api.model
    def _get_default_address_format(self):
        return "%(street)s\n%(street2)s\n%(city_name)s %(state_code)s %(zip)s\n%(country_name)s"

    @api.model
    def _get_address_format(self):
        return self.country_id.address_format or self._get_default_address_format()

    def _display_address(self, without_company=False):

        '''
        The purpose of this function is to build and return an address formatted accordingly to the
        standards of the country where it belongs.

        :param address: browse record of the res.partner to format
        :returns: the address formatted in a display that fit its country habits (or the default ones
            if not country is specified)
        :rtype: string
        '''
        # get the information that will be injected into the display format
        # get the address format
        address_format = self._get_address_format()
        args = {
            'state_code': self.state_id.code or '',
            'state_name': self.state_id.name or '',
            'country_code': self.country_id.code or '',
            'country_name': self._get_country_name(),
            'company_name': self.commercial_company_name or '',
        }
        for field in self._formatting_address_fields():
            args[field] = getattr(self, field) or ''
        if without_company:
            args['company_name'] = ''
        elif self.commercial_company_name:
            address_format = '%(company_name)s\n' + address_format
        return address_format % args

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Customers'),
            'template': '/base/static/xls/res_partner.xls'
        }]

    @api.model
    def _check_import_consistency(self, vals_list):
        """
        The values created by an import are generated by a name search, field by field.
        As a result there is no check that the field values are consistent with each others.
        We check that if the state is given a value, it does belong to the given country, or we remove it.
        """
        States = self.env['res.country.state']
        states_ids = {vals['state_id'] for vals in vals_list if vals.get('state_id')}
        state_to_country = States.search([('id', 'in', list(states_ids))]).read(['country_id'])
        for vals in vals_list:
            if vals.get('state_id'):
                country_id = next(c['country_id'][0] for c in state_to_country if c['id'] == vals.get('state_id'))
                state = States.browse(vals['state_id'])
                if state.country_id.id != country_id:
                    state_domain = [('code', '=', state.code),
                                    ('country_id', '=', country_id)]
                    state = States.search(state_domain, limit=1)
                    vals['state_id'] = state.id  # replace state or remove it if not found

    def _get_country_name(self):
        return self.country_id.name or ''

    @api.depends('lang')
    def _compute_active_lang_count(self):
        lang_count = len(self.env['res.lang'].get_installed())
        for partner in self:
            partner.active_lang_count = lang_count

    def get_sos_type(self):
        query = """
            SELECT json_agg(t)
                from
                (select id, name, code, description, status
                    from  sharevan_warning_type 
                    where status = 'running' )t;
                    """
        self.env.cr.execute(query, ())
        result = self._cr.fetchall()
        if result[0]:
            if result[0][0]:
                return {
                    'length': len(result[0][0]),
                    'records': result[0][0]
                }
        return {
            'length': 0,
            'records': []
        }

    def get_sos_number(self):
        query = """
            select vendor.name,vendor.phone
                    from  sharevan_vendor vendor
                    where vendor.status = 'running' and vendor.type ='sos' and (company_id in (
                        (select id from res_company where company_type ='2') , %s));
                    """
        self.env.cr.execute(query, (self.env.company.id,))
        result = self._cr.dictfetchall()
        if result:
            json = result
            content = {
                'name': 'Sharevan center',
                'phone': http.request.env['ir.config_parameter'].sudo().get_param('sharevan.sos')
            }
            json.append(content)
            return {
                'length': len(json),
                'records': json
            }
        else:
            json = []
            content = {
                'name': 'Sharevan center',
                'phone': http.request.env['ir.config_parameter'].sudo().get_param('sharevan.sos')
            }
            json.append(content)
            return {
                'length': len(json),
                'records': json
            }


class Partner(models.Model):
    _name = "res.partner"
    _inherit = "res.partner"

    code = fields.Char(default='/', readonly=True)

    # name_seq = fields.Char(string='ResPartner Reference', required=True, copy=False, readonly=True, index=True,
    #                        default=lambda self: _('New'))

    @api.model
    def create(self, vals):
        # if vals.get('name_seq', 'New') == 'New':
        #     vals['name_seq'] = self.env['ir.sequence'].next_by_code(
        #         'self.customer') or 'New'
        result = super(Partner, self).create(vals)
        # if result.code == '/':
        #     seq = self.env['ir.sequence'].get('self.res.employee') or '/'
        #     result.write({'code': seq})
        #     user = self.env['res.users'].sudo().create({
        #         'login': seq,
        #         'company_id': result.company_id.id,
        #         'company_ids': [(4, result.company_id.id)],
        #         'partner_id': result.id,
        #         'password': Constants.DEFAULT_PASS,
        #         'active': True,
        #     })
        #     result.write({
        #         'user_id': user.id
        #     })

        return result
