# -*- coding: utf-8 -*-
import json
import logging
import re
from datetime import date, timedelta
from datetime import datetime

import pytz

from addons.web.controllers.auth import AuthSsoApi
from addons.web.controllers.main import auth_api
from odoo import api, fields, models, tools, _, http
from odoo.exceptions import ValidationError
from odoo.http import request
from .utils import validate_utils as validate

# Global variables used for the warning fields declared on the res.partner
# in the following modules : sale, purchase, account, stock
from ..controllers.api.base_method import BaseMethod
from ..controllers.api.firebase_messaging import FirebaseMessagingAPI
from ...constants import Constants
from ...enum.ClickActionType import ClickActionType
from ...enum.EmployeeRoleName import EmployeeRoleName
from ...enum.FleetSystemType import FleetSystemType
from ...enum.MessageType import MessageType, NotificationSocketType
from ...enum.NotificationType import NotificationType
from ...enum.ObjectStatus import ObjectStatus
from ...enum.RoutingDetailStatus import RoutingDetailStatus
from ...enum.VehicleConfirmStatus import VehicleConfirmStatus

logger = logging.getLogger(__name__)
WARNING_MESSAGE = [
    ('no-message', 'No Message'),
    ('warning', 'Warning'),
    ('block', 'Blocking Message')
]
WARNING_HELP = 'Selecting the "Warning" option will notify user with the message, Selecting "Blocking Message" will throw an exception with the message and block the flow. The Message has to be written in the next field.'

ADDRESS_FIELDS = ('street', 'street2', 'zip', 'city_name', 'state_id', 'country_id')
auth_api = AuthSsoApi()


@api.model
def _lang_get(self):
    return self.env['res.lang'].get_installed()


# put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
_tzs = [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]


def _tz_get(self):
    return _tzs


# class User(models.Model):
#     _description = 'Users'
#     _inherit = _inherit = ['res.users']
#
#     driver_id = fields.Integer('Driver id')
MODEL_FLEET_VEHICLE_MODEL_BRAND = 'fleet.vehicle.model.brand'
MODEL_FLEET_DRIVER = 'fleet.driver'


class FleetDriver(models.Model):
    _name = 'fleet.driver'
    MODEL = 'fleet.driver'
    _description = 'Fleet driver'

    def _default_category(self):
        return self.env['res.partner.category'].browse(self._context.get('category_id'))

    @api.constrains('birth_date')
    def check_birth_date(self):
        today = date.today()
        if self:
            for rec in self:
                if rec.birth_date:
                    if rec.birth_date > today - timedelta(days=6570):
                        raise ValidationError("You must be 18 years old to be a driver!")
        return True

    @api.constrains('driver_license_date')
    def check_driver_license_date(self):
        today = date.today()
        if self:
            for rec in self:
                if rec.driver_license_date:
                    if rec.driver_license_date < rec.birth_date + timedelta(days=6570):
                        raise ValidationError("You are not old enough to take the driver's license test!")
                    if rec.driver_license_date > today:
                        raise ValidationError("The period of the license must be less than the current date!")
        return True

    @api.constrains('vat')
    def check_vat_contain_special_character(self):
        if self:
            for rec in self:
                if rec.vat:
                    validate.check_string_contain_special_character(rec.vat, ' ID')

    @api.constrains('zip')
    def check_zip_code(self):
        if self:
            for rec in self:
                if rec.zip:
                    validate.validate_zip_code(rec.zip)
            return True

    @api.constrains('email')
    def check_mail(self):
        for rec in self:
            if rec.email != False:
                match = re.search(
                    r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9]+\.[a-zA-Z0-9.]*\.*[COM|ORG|EDU|VN|com|org|edu|vn]{2}$)", rec.email)
                if match:
                    return True
                raise ValidationError(_('Format email address "Name <email@domain>'))
            return True

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

    @api.constrains('city_name')
    def validate_city_name_field(self):
        for rec in self:
            if rec.city_name != False:
                return validate.check_string_contain_special_character(rec.city_name, 'City ')

    @api.constrains('address')
    def validate_address_field(self):
        for rec in self:
            if rec.address != False:
                return validate.check_address_contain_special_character(rec.address, 'Address ')

    @api.constrains('full_name')
    def validate_full_name_field(self):
        for rec in self:
            if rec.full_name != False:
                return validate.check_string_contain_special_character(rec.full_name, 'Full name ')

    @api.constrains('mobile')
    def validate_mobile_field(self):
        for rec in self:
            if rec.mobile != False:
                return validate.check_string_contain_special_character(rec.mobile, 'Mobile ')

    # @api.constrains('class_driver')
    # def validate_class_driver_field(self):
    #     for rec in self:
    #         if rec.class_driver != False:
    #             return validate.check_string_contrain_special_character(rec.class_driver, 'Class driver')

    @api.onchange('card_type')
    def onchange_card_type_field(self):
        for rec in self:
            rec.update({
                'ssn': False
            })

    @api.constrains('ssn')
    def validate_ssn_field(self):
        for rec in self:
            if rec.ssn != False:
                return validate.check_string_contain_special_character(rec.ssn, 'Card Id')

    display_name = fields.Char(compute='_compute_display_name', store=True, index=True)
    name = fields.Char(index=True, required=True)
    date = fields.Date(index=True)
    title = fields.Many2one('res.partner.title')
    parent_id = fields.One2many(Constants.PARTNER_DRIVER, 'driver_id', string='Manager',
                                domain=lambda self: [("company_id", "=", self.env.company.id)])
    account_sso_active = fields.Boolean('Account sso active', default=True)
    account_sso_create = fields.Boolean('Account sso create', default=True)
    # parent_name = fields.Char(related='parent_id.name', readonly=True, string='Parent name')
    child_ids = fields.One2many('res.partner', 'parent_id', string='Contact', domain=[
        ('active', '=', True)])  # force "active_test" domain to bypass _search() override
    ref = fields.Char(string='Reference', index=True)
    tz = fields.Selection(_tz_get, string='Timezone', default=lambda self: self._context.get('tz'),
                          help="When printing documents and exporting/importing data, time values are computed according to this timezone.\n"
                               "If the timezone is not set, UTC (Coordinated Universal Time) is used.\n"
                               "Anywhere else, time values are computed according to the time offset of your web client.")
    lang = fields.Selection(_lang_get, string='Language', default=lambda self: self.env.lang,
                            help="All the emails and documents sent to this contact will be translated in this language.")
    line_rating_badges_driver = fields.One2many('sharevan.rating.driver.badges', 'driver_id', string='Lines',
                                                copy=True, readonly=False,
                                                domain=[('status', '=', 'running')])
    fleet_management_id = fields.Many2one('fleet.management', string='Fleet management')
    role_id = fields.Many2one('res.groups', string='Role group', domain="[('active_fleet', '=',True)]", required=True)
    tz_offset = fields.Char(compute='_compute_tz_offset', string='Timezone offset', invisible=True)
    user_id = fields.Many2one('res.users', string='Salesperson',
                              help='The internal user in charge of this contact.')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    vat = fields.Char(string='Tax ID',
                      help="The  Identification Number. Complete it if the contact is subjected to government taxes. Used in some legal statements.")

    bank_ids = fields.One2many('res.partner.bank', 'partner_id', string='Banks')
    website = fields.Char('Website Link')
    comment = fields.Text(string='Notes')
    award_id = fields.Many2one('sharevan.title.award', 'award_id')
    point = fields.Integer('point', default=0)
    trip_number = fields.Integer('Trip count', help="Tổng số chuyến đi đã trở ", default=0)
    category_id = fields.Many2many('res.partner.category', column1='partner_id',
                                   column2='category_id', string='Tags', default=_default_category)
    image_license_frontsite = fields.Image("Image license front side", maxsharevan_title_award_width=128,
                                           max_height=128, required=True)
    image_license_backsite = fields.Image("Image license back side", max_width=128, max_height=128, required=True)
    credit_limit = fields.Float(string='Credit Limit')
    active = fields.Boolean(default=True)
    employee = fields.Boolean(help="Check this box if this contact is an Employee.")
    function = fields.Char(string='Job Position')
    employee_type = fields.Selection(
        [('driver', 'Driver'),
         ('manager', 'Manager'),
         ], string='Job Position',
        default='manager',
        help="")
    street = fields.Char()
    street2 = fields.Char()
    ward = fields.Char('Ward')
    zip = fields.Char(change_default=True)
    city_name = fields.Char()
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict',
                               domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one('res.country', 'Country', required=True)
    partner_latitude = fields.Float(string='Geo Latitude', digits=(16, 5))
    partner_longitude = fields.Float(string='Geo Longitude', digits=(16, 5))
    email = fields.Char('Email', required=True)
    name_seq = fields.Char(string='Driver Reference', required=True, copy=False, readonly=True, index=True,
                           default=lambda self: _('New'))
    email_formatted = fields.Char(
        'Formatted Email', compute='_compute_email_formatted',
        help='Format email address "Name <email@domain>"')
    phone = fields.Char(String="Phone 1", required=True)

    # @api.constrains('phone')
    # def check_phone(self):
    #     for rec in self:
    #         message = ""
    #         if '' in rec.phone:
    #             notice = "Phone must not contain whitespace!"
    #             message += notice + "\n"
    #             # validate.validate_phone_number_v2(rec.phone)
    #         message = message.strip()
    #         if message:
    #             raise ValidationError(message)

    mobile = fields.Char(String="Phone 2")
    is_selected = fields.Boolean(default=False)
    industry_id = fields.Many2one('res.partner.industry', 'Industry')
    # company_type is only an interface field, do not use it in business logic

    company_type = fields.Selection(string='Company Type',
                                    selection=[('company', 'Company')], store=False)
    company_id = fields.Many2one('res.company', 'Company', index=True, default=lambda self: self.env.company.id)
    color = fields.Integer(string='Color Index', default=0)
    user_ids = fields.One2many('res.users', 'partner_id', string='Users', auto_join=True)
    partner_share = fields.Boolean(
        'Share Partner', store=True,
        help="Either customer (not a user), either shared user. Indicated the current partner is a customer without "
             "access or with a limited access created for sharing data.")
    contact_address = fields.Char(compute='_compute_contact_address', string='Complete Address')
    commercial_partner_id = fields.Many2one('res.partner', compute='_compute_commercial_partner',
                                            string='Commercial Entity', store=True, index=True)
    commercial_company_name = fields.Char('Company Name Entity', compute='_compute_commercial_company_name',
                                          store=True)
    company_name = fields.Char('Company Name')
    district = fields.Char('District Name')
    image_1920 = fields.Image("Image", max_width=128, max_height=128, required=True)
    nationality = fields.Many2one('res.country', string='Nationality', ondelete='restrict', required=True)
    status = fields.Selection([('running', 'Active'), ('deactivate', 'Deactivate')
                               ], 'Status', default="running", required=True)
    plan_to_change_car = fields.Boolean('Plan To Change Car', default=False)
    account_driver = fields.Char()
    user_driver = fields.Char(string="User Driver")
    card_type = fields.Selection([('card', 'Card'),
                                  ('passport', 'Passport')], 'Card type', default="passport", required=True)
    card_type = fields.Selection([('card', 'Card'), ('passport', 'Passport'), ], 'Card type', default="card",
                                 required=True)
    ssn = fields.Char(string="ID", required=True)
    birth_date = fields.Date(string="Birth Day", required=True)
    hire_date = fields.Date(string="Hire Date")
    leave_date = fields.Date(string="Leave Date")
    date_issue_card = fields.Date(string="Date issue card", required=True)
    expires_date_card = fields.Date(string="Expires date card", required=True)
    driver_code = fields.Char()
    gender = fields.Selection([('male', 'Male'), ('other', 'Other'),
                               ('female', 'Female')], 'Gender', default="male", required=True)
    from_date = fields.Date('from date')
    to_date = fields.Date('to date')
    manage_id = fields.Many2one('fleet.driver', string='Manegement employee ')

    full_name = fields.Char(String="Full name", required=True)
    # class_driver = fields.Char(String="Driver  class", required=True)
    class_driver = fields.Many2one('sharevan.driver.license', string='Driver License',
                                   domain=lambda self: "[('country_id', '=', country_id),('status','=','running')]")
    expires_date = fields.Date(string="Expries Day")
    address = fields.Char(String="Address")
    reason = fields.Char(String="Reason", store=False)
    no = fields.Char(String="No")

    driver_license_date = fields.Date(string="Driver's liscense date")
    # fleet_management_id = fields.Integer(default = 0)
    # image = fields.Many2many('ir.attachment', string="Image")
    attach_File = fields.Many2many('ir.attachment', string="Attach File")
    driver_type = fields.Selection([('fleet', 'Fleet'),
                                    ('code_share', 'Code share'), ('market_place', 'Market Place')],
                                   'Driver Type', default="fleet")
    approved_check = fields.Selection([('waiting', 'Waiting'),
                                       ('accepted', 'Accepted'), ('rejected', 'Rejected')],
                                      'Approve', default="waiting")
    toogle = fields.Boolean('Toogle', compute="compute_all", store=False)
    toogle_confirm = fields.Boolean('Toogle', compute="compute_all", store=False)
    login = fields.Char('Username')
    latitude = fields.Float(string='Latitude', digits=(16, 5))
    longitude = fields.Float(string='Longitude', digits=(16, 5))

    level_management_user = fields.Boolean('Level management user', compute="compute_level_management_users",
                                           store=False)

    def compute_level_management_users(self):
        for record in self:

            filter_querry_user_id = """
                                        Select manage.id , manage.organization_level from res_users users
                                        Join fleet_driver driver on driver.user_id = users.id
                                        Join fleet_management manage on manage.id = driver.fleet_management_id
                               where   users.id =%s
                                    """

            http.request.env.cr.execute(filter_querry_user_id,
                                        (http.request.env.uid,))
            result_user = http.request._cr.dictfetchall()

            http.request.env.cr.execute(filter_querry_user_id,
                                        (record['user_id']['id'],))
            result = http.request._cr.dictfetchall()

            if len(result_user) == 0:
                record.level_management_user = False
                return
            if result[0]['id'] and result_user[0]['id']:
                # Id tổ đội của account
                if int(result_user[0]['organization_level']) > int(result[0]['organization_level']):
                    raise ValidationError(_('You do not have permission to access !'))
                else:
                    record.level_management_user = False

    @api.onchange('image_license_frontsite')
    def _onchange_image_license_frontsite(self):
        for record in self:
            print(record)

    @api.onchange('image_license_backsite')
    def _onchange_image_license_backsite(self):
        for record in self:
            print(record)

    @api.onchange('image_1920')
    def _onchange_image_1920(self):
        for record in self:
            print(record)

    @api.onchange('date_issue_card')
    def onchange_date_issue_card(self):
        timenow = datetime.now().date() + timedelta(days=1)
        for record in self:
            if record['date_issue_card'] > timenow:
                record.update({'date_issue_card': None})
                record.update({'expires_date_card': None})
                notice = "Date Issue Card must be greater than Today !"
                self.env.user.notify_danger(message=notice, title=NotificationSocketType.NOTIFICATION.value)

    @api.onchange('expires_date_card')
    def onchange_expires_date_card(self):
        for record in self:
            if record['date_issue_card']:
                if record['date_issue_card'] > record['expires_date_card']:
                    record.update({'expires_date_card': None})
                    notice = "Expires_date_card must be greater than Date_issue_card !"
                    self.env.user.notify_danger(message=notice, title=NotificationSocketType.NOTIFICATION.value)

    @api.onchange('country_id')
    def onchange_country(self):
        for record in self:
            street = record.street
            district = record.district
            city_name = record.city_name
            state = record.state_id
            country = record.country_id
            ward = record.ward
            record.update({'district': False})
            record.update({'state_id': False})
            record.update({'address': ''})

    def accept_driver(self):
        create_user = 0
        driver_id = 0
        for record in self:
            create_user = record['create_uid']
            driver_id = record['id']
            record.write({'approved_check': VehicleConfirmStatus.Accepted.value})
        test_msg = {"message": "Accept driver successfully! ", "title": "Accept driver to join Code share system",
                    "sticky": True}
        self.env.user.notify_success(**test_msg)
        val = {
            'user_id': [create_user.id],
            'title': 'Accept driver to join Code share system',
            'content': 'Accept driver successfully!',
            'click_action': ClickActionType.routing_plan_day_driver.value,
            'message_type': MessageType.success.value,
            'type': NotificationType.RoutingMessage.value,
            'object_status': RoutingDetailStatus.Done.value,
            'item_id': driver_id,
        }
        http.request.env['sharevan.notification'].create(val)
        return self

    def reject_driver(self):
        create_user = 0
        driver_id = 0
        for record in self:
            create_user = record['create_uid']
            driver_id = record['id']
            record.write({'approved_check': VehicleConfirmStatus.Reject.value})
        test_msg = {"message": "Reject driver successfully! ", "title": "Reject driver to join Code share system",
                    "sticky": True}
        self.env.user.notify_success(**test_msg)
        val = {
            'user_id': [create_user.id],
            'title': 'Reject driver to join Code share system',
            'content': 'Driver has been rejected to join system!',
            'click_action': ClickActionType.routing_plan_day_driver.value,
            'message_type': MessageType.success.value,
            'type': NotificationType.RoutingMessage.value,
            'object_status': RoutingDetailStatus.Done.value,
            'item_id': driver_id,
        }
        http.request.env['sharevan.notification'].create(val)
        return self

    @api.onchange('street')
    def _onchange_street(self):
        for record in self:
            street = record.street
            district = record.district
            city_name = record.city_name
            state = record.state_id
            country = record.country_id
            ward = record.ward
            if ward is False:
                address = street
            else:
                address = street + ' - ' + ward
            if district is not False:
                address = address + ' - ' + district
            if city_name is not False:
                if city_name != '':
                    address = address + ' - ' + city_name
            if state:
                if city_name is False:
                    address = address + ' - ' + state.name
            if country:
                address = address + ' - ' + country.name
            record.update({'address': address})

    @api.onchange('state_id')
    def _onchange_state_id(self):
        for record in self:
            street = record.street
            if street:
                district = record.district
                city_name = record.city_name
                state = record.state_id
                country = record.country_id
                ward = record.ward
                if ward is False:
                    address = street
                else:
                    address = street + ' - ' + ward
                if district is not False:
                    address = address + ' - ' + district
                if city_name is not False:
                    if city_name != '':
                        address = address + ' - ' + city_name
                if state:
                    if state.name is not False:
                        if state.name != city_name:
                            address = address + ' - ' + state.name
                if country:
                    address = address + ' - ' + country.name
                record.update({'address': address})

    @api.constrains('hire_date')
    def constrains_hire_date(self):
        if self.hire_date:
            if self.hire_date > date.today():
                raise ValidationError(_('Hire date must be less than the current date.'))
            if self.leave_date and self.hire_date >= self.leave_date:
                raise ValidationError(_('Leave date must be after hire_date.'))

    @api.onchange('country_id')
    def onchange_country(self):
        for record in self:
            record.update({'class_driver': ''})

    # @api.constrains('driver_license_date')
    # def _constrains_driver_license_date(self):
    #     if self.driver_license_date:
    #         if 'driver_license_date' in self and self.driver_license_date > date.today():
    #             raise ValidationError('License date can not be greater than today !')
    #         if 'driver_license_date' in self and 'expires_date' in self and self.expires_date <= self.driver_license_date:
    #             raise ValidationError('Expires date must be greater than license date!')
    #
    # @api.constrains('expires_date')
    # def _constrains_expries_date(self):
    #     for record in self:
    #         if 'driver_license_date' in record and 'expires_date' in record and record['driver_license_date']:
    #             if record['expires_date'] <= record['driver_license_date']:
    #                 raise ValidationError('Expires date must be greater than license date!')

    def compute_all(self):
        for record in self:
            if record.status == 'running':
                record.toogle = False
            else:
                record.toogle = True
            if record.driver_type == FleetSystemType.CODE_SHARE.value and record.approved_check == VehicleConfirmStatus.Waiting.value:
                record.toogle_confirm = True
            else:
                record.toogle_confirm = False

    def unlink(self):
        raise ValidationError('Not allow to deleted record')

    @api.depends('toogle')
    def deactivate_driver(self):
        check_order_not_finish_query = """
            select distinct plan.routing_plan_day_code, plan.status,bid_order.bidding_order_number, return.status
                from fleet_driver driver
            left join sharevan_routing_plan_day plan on  plan.driver_id = %s and plan.status in ('0','1')
            left join sharevan_bidding_vehicle bid_veh on bid_veh.driver_id = %s
            left join sharevan_bidding_order_return return on return.bidding_vehicle_id = bid_veh.id 
                and return.status != '2'
            left join sharevan_bidding_order bid_order on bid_order.id = return.bidding_order_id
        """
        self.env.cr.execute(check_order_not_finish_query, (self.id, self.id,))
        check_record = self._cr.dictfetchall()
        if check_record:
            message = ''
            for record in check_record:
                if record['routing_plan_day_code']:
                    message += record['routing_plan_day_code'] + ', '
                if record['bidding_order_number']:
                    message += record['bidding_order_number'] + ', '
            if message != '':
                raise ValidationError('Driver have finish bill: ' + message)
        time_now = datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")
        self.write({
            'status': 'deactivate',
            'leave_date': time_now,
            'fleet_management_id': False,
            'account_sso_active': True
        })
        driver_temp = self.env['fleet.management.driver.temp'].search([('id', '=', self.id), ('status', '=', 'active')])
        driver_temp.write({
            'to_date': time_now,
            'status': 'deactive'
        })
        team_record = self.env['fleet.management'].search([('manager_id', '=', self.id), ('status', '=', 'active')])
        if team_record:
            team_record.write({
                'manager_id': False
            })
        user = self.env['res.users'].search([('id', '=', self['user_id']['id'])])
        user.write({
            'active': False
        })
        list_driver_badges = self.env['sharevan.rating.driver.badges'].search(
            [('status', '=', 'running'), ('driver_id', '=', self['id'])])
        for driver_badges in list_driver_badges:
            driver_badges.write({
                'status': 'deleted'
            })
        auth_api.deactive(request.session.access_token, request.session.context['lang'][:2], self.login)
        return self

    @api.depends('toogle')
    def active_driver(self):
        check_driver = """
            select emp_log.driver_id, emp_log.full_name ,emp_log.status,emp_log.ssn,emp_log.phone, company.id,company.name company_name 
                from fleet_employee_log emp_log
            join res_company company on company.id = emp_log.company_id
                where emp_log.phone = %s or emp_log.ssn = %s
                    and emp_log.card_type =%s and emp_log.to_date is null
                """
        self._cr.execute(check_driver, (self['phone'], self['ssn'], self['card_type'],))
        driver = self._cr.dictfetchall()
        if driver:
            for rec in driver:
                if rec['id'] == self.env.company.id and rec['status'] == 'running' and rec['driver_id'] != self.id:
                    raise ValidationError(
                        'Driver account with phone: ' + self['phone'] + ', Card id: ' + rec['ssn'] + ', name: ' + rec[
                            'full_name'] + 'is active now !')
                elif rec['status'] == 'running' and rec['driver_id'] != self.id:
                    raise ValidationError('Account is active in ' + rec['company_name'] + '. Infomation: phone: ' + rec[
                        'phone'] + ', Card id: ' + rec['ssn'] + ', name: ' + rec['full_name'] + 'is active now !')
        self.write({
            'status': 'running',
            'leave_date': False
        })
        query_check_acount_duplicate_querry = """
            select * from res_users where login like  LOWER('%%%s%%')  """ % (self.login,)
        self._cr.execute(query_check_acount_duplicate_querry, ())
        user_check = self._cr.dictfetchall()
        old_user_id = None
        last_active_user_id = None
        if user_check:
            for user in user_check:
                if user['id'] == self.user_id.id and user['login'] == self.phone and user[
                    'company_id'] == self.env.company.id:
                    old_user_id = user
                if user['id'] == self.user_id.id and user['login'] == self.phone and user[
                    'company_id'] != self.env.company.id:
                    last_active_user_id = user
                if user['id'] == self.user_id.id and user['company_id'] == self.env.company.id:
                    old_user_id = user
            if last_active_user_id:
                # update last_active_user_id account
                update_user = """
                    update res_users set login= %s where id = %s
                                """
                self._cr.execute(update_user,
                                 (last_active_user_id['login'] + '_deactivate', last_active_user_id['id'],))
                update_user = """
                    update res_users set login= %s,active = true where id = %s
                """
                self._cr.execute(update_user, (self.phone, self.user_id.id,))
            else:
                update_user = """
                update res_users set active = true where id = %s
                """
                self._cr.execute(update_user, (self.user_id.id,))
        else:
            raise ValidationError('Account not found please check customer care department !')
        list_driver_badges = self.env['sharevan.rating.driver.badges'].search(
            [('status', '=', 'deleted'), ('driver_id', '=', self['id'])])
        for driver_badges in list_driver_badges:
            driver_badges.write({
                'status': 'running'
            })
        auth_api.active(request.session.access_token, request.session.context['lang'][:2], self.login)
        return self

    @api.model
    def create(self, vals):
        if not BaseMethod.reject_dlp_employee_on_data(self.env.user):
            raise ValidationError('DLP employee not allow to create or update data of fleet companies')
        if vals['employee_type'] == 'manager':
            seq = BaseMethod.get_new_sequence('fleet.driver', 'FMN', 6, 'name_seq')
        else:
            seq = BaseMethod.get_new_sequence('fleet.driver', 'DRV', 6, 'name_seq')
        vals['name_seq'] = seq
        vals['login'] = vals['phone']
        vals['driver_code'] = vals['name_seq']
        vals['name'] = vals['name'] + '-' + seq

        # if vals['employee_type'] == 'driver':
        #     ex_year = datetime.strptime(str(vals['expires_date']), '%Y-%m-%d')
        #     dr_year = datetime.strptime(str(vals['driver_license_date']), '%Y-%m-%d')
        #     if int(ex_year.year) - int(dr_year.year) > 10:
        #         raise ValidationError('Driver is license validity is only valid for 10 years')
        if 'leave_date' in vals and vals['leave_date']:
            if vals['status'] != 'deactivate':
                raise ValidationError('Driver status must be deactivate!')
        query = """
            select id from sharevan_channel where name = 'fleet' and channel_type ='employee' LIMIT 1
        """
        self.env.cr.execute(query, ())
        channel = self._cr.dictfetchall()
        channel_id = 0
        if not channel:
            raise ValidationError('Driver notification channel not create')
        else:
            channel_id = channel[0]['id']
        # check xem đã tạo phân quyền lái xe chưa. ko cho đăng nhập
        role_query = """
            select groups.id,groups.name from ir_module_category category
                join res_groups groups on groups.category_id = category.id
            where category.name ='Fleet' and parent_id is not null;
        """
        self.env.cr.execute(role_query, ())
        role_record = self._cr.dictfetchall()
        check_driver_role = False
        user_role = 0
        if role_record:
            for rec in role_record:
                if vals['employee_type'] == 'driver' and rec['name'] == 'Driver':
                    check_driver_role = True
                    user_role = rec['id']
                elif vals['employee_type'] == 'manager' and rec['name'] == 'User':
                    user_role = rec['id']
                    check_driver_role = True
        if check_driver_role == False:
            raise ValidationError('Driver role have not create already')
        check_driver = """
            select emp_log.full_name ,emp_log.status,emp_log.ssn,emp_log.phone, company.id,company.name company_name 
                from fleet_employee_log emp_log
            join res_company company on company.id = emp_log.company_id
                where (emp_log.phone = %s or emp_log.ssn = %s
                    and emp_log.card_type =%s ) and emp_log.to_date is null
        """
        self._cr.execute(check_driver, (vals['phone'], vals['ssn'], vals['card_type'],))
        driver = self._cr.dictfetchall()
        if driver:
            for rec in driver:
                if rec['status'] == 'running':
                    raise ValidationError(
                        'Driver account with phone: ' + rec['phone'] + ', ssn: ' + rec['ssn'] + ', name: ' + rec[
                            'full_name'] + ' is active now')
                elif rec['status'] == 'running':
                    raise ValidationError(
                        'Driver infomation phone: ' + vals['phone'] + ', Card id: ' + vals[
                            'ssn'] + 'is exist in company' + rec[
                            'company_name'] + '! Please finish contract')
        result = super(FleetDriver, self).create(vals)
        # SỬ dụng account_fleet_type để check tài khoản tồn tại rồi. nếu tk active = False thì k tạo bên sso nữa.
        # update tk cũ là login+deactivate và tài khoản mới sử dụng sso cũ.
        v = {
            'active': True,
            'login': vals['login'],
            # 'partner_id': result.parent_id.id,
            'type': 'private',
            'name': vals['name'],
            'email': vals['email'],
            'account_fleet_type': True,
            'channel_id': channel_id
        }
        user_id = self.env['res.users'].sudo().create(v)
        update_partner_query = """
            update res_partner set phone = %s , user_id =%s ,company_id =%s,account_fleet_type = true where id = %s
                """
        self.env.cr.execute(update_partner_query,
                            (vals['phone'], user_id.id, user_id.company_id.id, user_id['partner_id'].id,))

        result.write({
            'user_id': user_id.id
        })

        list_badges = self.env['sharevan.rating.badges'].search([('status', '=', 'running')])

        for badges in list_badges:
            v = {
                'driver_id': result['id'],
                'rating_badges_id': badges['id'],
                'status': 'running'
            }
            badges_driver = self.env['sharevan.rating.driver.badges'].sudo().create(v)
        if 'role_id' in vals:
            # delete all role group
            update_role_query = """
                delete from res_groups_users_rel rel where  rel.uid = %s 
            """
            self.env.cr.execute(update_role_query, (user_id.id,))
            if vals['role_id']:
                # update role với loại nv tương ứng
                update_role_query = """
                    INSERT INTO public.res_groups_users_rel(gid, uid) VALUES (%s, %s)
                """
                self.env.cr.execute(update_role_query, (vals['role_id'], user_id.id,))
        return result

    def write(self, vals):
        if not BaseMethod.reject_dlp_employee_on_data(self.env.user):
            raise ValidationError('DLP employee not allow to create or update data of fleet companies')
        check_send_notify = False
        if 'role_id' in vals:
            # check search read is already exists
            self.env.cr.execute("select gid from res_groups_users_rel where uid = %s and gid = %s ",
                                (self.user_id.id, vals['role_id'],))
            role = self.env.cr.fetchall()
            if not role:
                # delete all role group
                update_role_query = """
                    delete from res_groups_users_rel rel where  rel.uid = %s and gid != %s and gid != 1
                """
                self.env.cr.execute(update_role_query, (self.user_id.id, vals['role_id'],))
                if vals['role_id']:
                    # update role với loại nv tương ứng
                    update_role_query = """
                        INSERT INTO public.res_groups_users_rel(gid, uid) VALUES (%s, %s)
                    """
                    self.env.cr.execute(update_role_query, (vals['role_id'], self.user_id.id,))
        if 'phone' in vals or 'ssn' in vals or 'card_type' in vals:
            card_type = self.card_type
            if 'card_type' in vals:
                card_type = vals['card_type']
            phone = self.phone
            if 'phone' in vals:
                if ' ' in vals['phone']:
                    raise ValidationError('Phone must not contain whitespace!')
                phone = vals['phone']
            ssn = self.ssn
            if 'ssn' in vals:
                ssn = vals['ssn']
            check_driver = """
                select emp_log.driver_id, emp_log.full_name ,emp_log.status,emp_log.ssn,emp_log.phone, company.id,company.name company_name 
                    from fleet_employee_log emp_log
                join res_company company on company.id = emp_log.company_id
                    where (emp_log.phone = %s or emp_log.ssn = %s
                        and emp_log.card_type =%s )and emp_log.to_date is null
            """
            self._cr.execute(check_driver, (phone, ssn, card_type,))
            driver = self._cr.dictfetchall()
            if driver:
                for dri in driver:
                    if dri['status'] == 'running' and dri['driver_id'] != self.id:
                        raise ValidationError(
                            'Driver account with phone: ' + dri['phone'] + ', Card id: ' + dri['ssn'] + ', name: ' +
                            dri['full_name'] + ' is exist already')
                    elif dri['status'] == 'running' and dri['id'] != self.company_id.id:
                        raise ValidationError(
                            'Driver infomation phone: ' + phone + ', Card id: ' + ssn + 'is exist in company' + dri[
                                'company_name'] + '! Please finish contract')
            if 'phone' in vals and self.status == 'running' and vals['phone'] != self.phone:
                tokens = []
                # nếu thay đổi phone thì deactivate tài khoản cũ và tạo tài khoản mới đăng nhập cho lái xe
                user = self.env['res.users'].search([('id', '=', self['user_id']['id'])])
                if user['fcm_token']:
                    tokens.append(user['fcm_token'])
                user.write({
                    'active': False
                })
                auth_api.deactive(request.session.access_token, self.env.user.lang[:2], user['login'])
                # check xem đã tạo phân quyền lái xe chưa. ko cho đăng nhập đối với lái xe
                role_query = """
                           select groups.id,groups.name from ir_module_category category
                               join res_groups groups on groups.category_id = category.id
                           where category.name ='Fleet' and parent_id is not null;
                       """
                self.env.cr.execute(role_query, ())
                role_record = self._cr.dictfetchall()
                check_driver_role = False
                user_role = 0
                if role_record:
                    employee_type = self.employee_type
                    if 'employee_type' in vals:
                        employee_type = vals['employee_type']
                    for rec in role_record:
                        if employee_type == 'driver' and rec['name'] == 'Driver':
                            check_driver_role = True
                            user_role = rec['id']
                        elif employee_type == 'manager' and rec['name'] == 'User':
                            user_role = rec['id']
                            check_driver_role = True
                if check_driver_role == False:
                    raise ValidationError('Driver role have not create already')
                name = self.name
                if 'name' in vals:
                    name = vals['name']
                email = self.email
                if 'email' in vals:
                    email = vals['email']
                v = {
                    'active': True,
                    'login': vals['phone'],
                    # 'partner_id': result.parent_id.id,
                    'type': 'private',
                    'name': name,
                    'email': email,
                    'account_fleet_type': True,
                    'channel_id': user.channel_id.id
                }
                user_id = self.env['res.users'].sudo().create(v)
                # update thông tin để đăng nhập chat trên web
                update_partner_query = """
                    update res_partner set phone = %s , user_id =%s ,company_id =%s,account_fleet_type = true where id = %s
                                """
                self.env.cr.execute(update_partner_query,
                                    (vals['phone'], user_id.id, user_id.company_id.id, user_id['partner_id'].id,))
                vals['user_id'] = user_id.id
                vals['login'] = vals['phone']
                logger.warn(
                    "create new account and deactivate old account successful !",
                    exc_info=True)
                if len(tokens) > 0:
                    title = 'Manager has been change information! Please log out by new account'
                    body = 'Manager has been change information! Please log out by new account: ' + vals['phone']
                    type = NotificationType.RoutingMessage.value
                    message_type = MessageType.warning.value
                    object_status = ObjectStatus.LogOutByAccount.value
                    check_send_notify = True
                    click_action = ClickActionType.notification_driver.value
                    message_type = MessageType.success.value
                    val = {
                        "title": title,
                        "name": 'fleet.driver',
                        "content": body,
                        "create_date": datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S"),
                        "type": type,
                        "object_status": object_status,
                        "click_action": click_action,
                        "message_type": message_type,
                        "item_id": '',
                        "is_read": False
                    }
                    val = json.dumps(val)
                    item_id = ''
                    FirebaseMessagingAPI. \
                        send_message_for_all_with_fcm_token(tokens=tokens, title=title, body=str(val), short_body=body,
                                                            item_id=item_id,
                                                            click_action=click_action, message_type=message_type)
        if 'from_date' in vals and 'to_date' in vals:
            validate.check_from_date_greater_than_to_date(vals['from_date'], vals['to_date'])
        elif 'from_date' in vals:
            validate.check_from_date_greater_than_to_date(vals['from_date'], self['to_date'])
        elif 'to_date' in vals:
            validate.check_from_date_greater_than_to_date(self['from_date'], vals['to_date'])
        if 'expires_date' in vals and self['driver_license_date']:
            ex_year = datetime.strptime(str(vals['expires_date']), '%Y-%m-%d')
            dr_year = datetime.strptime(str(self['driver_license_date']), '%Y-%m-%d')
            # if int(ex_year.year) - int(dr_year.year) > 10:
            #     raise ValidationError('Driver is license validity is only valid for 10 years')

        if 'expires_date' in vals and 'driver_license_date' in vals:
            ex_year = datetime.strptime(str(vals['expires_date']), '%Y-%m-%d')
            dr_year = datetime.strptime(str(vals['driver_license_date']), '%Y-%m-%d')
            # if int(ex_year.year) - int(dr_year.year) > 10:
            #     raise ValidationError('Driver is license validity is only valid for 10 years')
        elif 'driver_license_date' in vals:
            dr_year = datetime.strptime(str(vals['driver_license_date']), '%Y-%m-%d')
            ex_year = datetime.strptime(str(self['expires_date']), '%Y-%m-%d')
            num = int(ex_year.year) - int(dr_year.year)
            # if num > 10:
            #     raise ValidationError('Driver is license validity is only valid for 10 years')
        elif 'expires_date' in vals:
            ex_year = datetime.strptime(str(vals['expires_date']), '%Y-%m-%d')
            dr_year = datetime.strptime(str(self['driver_license_date']), '%Y-%m-%d')
            num = int(ex_year.year) - int(dr_year.year)
            # if num > 10:
            #     raise ValidationError('Driver is license validity is only valid for 10 years')
        if 'status' in vals:
            if vals['status'] == 'deactivate':
                vals['fleet_management_id'] = False
        result = super(FleetDriver, self).write(vals)
        if self.role_id:
            role_str = self.role_id.full_name.upper()
            role_e = ""
            for enum in EmployeeRoleName:
                if enum.value in role_str:
                    role_e = enum.value
                    break
            if role_e:
                if role_e == "ADMINISTRATOR":
                    role_e = "FLEET_MANAGER"
                username = self.login
                auth = request.session.access_token
                user_detail_b = auth_api.find_user_by_username(authorization=auth, username=username)
                user_detail = json.loads(user_detail_b)['content'][0]
                if not auth_api.update_user_role(auth, user_detail, role_e):
                    raise ValidationError("Could not update role")
        user_id = [self.user_id.id]
        if not check_send_notify:
            title = 'Manager has been change information!'
            body = 'Manager has been change information!'
            type = NotificationType.RoutingMessage.value
            message_type = MessageType.warning.value
            object_status = ObjectStatus.UpdateInformation.value
            BaseMethod.send_notification_driver(user_id, 'fleet.driver', self.id,
                                                ClickActionType.driver_main_activity.value, message_type, title,
                                                body, type, '', object_status)
        if 'status' in vals:
            if vals['status'] == 'deactivate':
                record = self.env['fleet.management.driver.temp'].search(
                    [('fleet_driver_id', '=', self['id']), ('status', '=', 'active')])
                if record:
                    current_date = date.today()
                    record.write({
                        'status': 'deactive',
                        'to_date': current_date
                    })
        return result

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

    # def _compute_rating(self):
    #     if self.line_rating_badges_driver.rating_badges_id == 5 :
    #         self.line_rating_badges_driver.rating_count = 3
    #     else :
    #         self.line_rating_badges_driver.rating_count = 2

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
            'city': self.city_name or '',
            'state_code': self.state_id.code or '',
            'state_name': self.state_id.name or '',
            'country_code': self.country_id.code or '',
            'country_name': self._get_country_name()
        }
        for field in self._formatting_address_fields():
            args[field] = getattr(self, field) or ''
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

    @api.depends('tz')
    def _compute_tz_offset(self):
        for partner in self:
            partner.tz_offset = datetime.datetime.now(pytz.timezone(partner.tz or 'GMT')).strftime('%z')

    @api.depends('name', 'email')
    def _compute_email_formatted(self):
        for partner in self:
            if partner.email:
                partner.email_formatted = tools.formataddr((partner.name or u"False", partner.email or u"False"))
            else:
                partner.email_formatted = ''

    #
    # @api.depends('user_ids.share', 'user_ids.active')
    # def _compute_partner_share(self):
    #     super_partner = self.env['res.users'].browse(SUPERUSER_ID).partner_id
    #     if super_partner in self:
    #         super_partner.partner_share = False
    #     for partner in self - super_partner:
    #         partner.partner_share = not partner.user_ids or not any(not user.share for user in partner.user_ids)

    @api.depends('vat')
    def _compute_same_vat_partner_id(self):
        for partner in self:
            # use _origin to deal with onchange()
            partner_id = partner._origin.id
            domain = [('vat', '=', partner.vat)]
            if partner_id:
                domain += [('id', '!=', partner_id), '!', ('id', 'child_of', partner_id)]
            partner.same_vat_partner_id = bool(partner.vat) and not partner.parent_id and self.env[
                'res.partner'].search(domain, limit=1)

    @api.depends(lambda self: self._display_address_depends())
    def _compute_contact_address(self):
        for partner in self:
            partner.contact_address = partner._display_address()

    # @api.constrains('parent_id')
    # def _check_parent_id(self):
    #     if not self._check_recursion():
    #         raise ValidationError(_('You cannot create recursive Partner hierarchies.'))

    # @api.onchange('parent_id')
    # def onchange_parent_id(self):
    #     # return values in result, as this method is used by _fields_sync()
    #     if not self.parent_id:
    #         return
    #     result = {}
    #     partner = self._origin
    #     if partner.parent_id and partner.parent_id != self.parent_id:
    #         result['warning'] = {
    #             'title': _('Warning'),
    #             'message': _('Changing the company of a contact should only be done if it '
    #                          'was never correctly set. If an existing contact starts working for a new '
    #                          'company then a new contact should be created under that new '
    #                          'company. You can use the "Discard" button to abandon this change.')}
    #     if partner.type == 'contact' or self.type == 'contact':
    #         # for contacts: copy the parent address, if set (aka, at least one
    #         # value is set in the address: otherwise, keep the one from the
    #         # contact)
    #         address_fields = self._address_fields()
    #         if any(self.parent_id[key] for key in address_fields):
    #             def convert(value):
    #                 return value.id if isinstance(value, models.BaseModel) else value
    #
    #             result['value'] = {key: convert(self.parent_id[key]) for key in address_fields}
    #     return result

    @api.onchange('email')
    def onchange_email(self):
        if not self.image_1920 and self._context.get('gravatar_image') and self.email:
            self.image_1920 = self._get_gravatar_image(self.email)

    # @api.onchange('parent_id', 'company_id')
    # def _onchange_company_id(self):
    #     if self.parent_id:
    #         self.company_id = self.parent_id.company_id.id

    @api.depends('name', 'email')
    def _compute_email_formatted(self):
        for partner in self:
            if partner.email:
                partner.email_formatted = tools.formataddr((partner.name or u"False", partner.email or u"False"))
            else:
                partner.email_formatted = ''

    def _update_fields_values(self, fields):
        """ Returns dict of write() values for synchronizing ``fields`` """
        values = {}
        for fname in fields:
            field = self._fields[fname]
            if field.type == 'many2one':
                values[fname] = self[fname].id
            elif field.type == 'one2many':
                raise AssertionError(
                    _('One2Many fields cannot be synchronized as part of `commercial_fields` or `address fields`'))
            elif field.type == 'many2many':
                values[fname] = [(6, 0, self[fname].ids)]
            else:
                values[fname] = self[fname]
        return values

    @api.model
    def _address_fields(self):
        """Returns the list of address fields that are synced from the parent."""
        return list(ADDRESS_FIELDS)

    @api.model
    def _formatting_address_fields(self):
        """Returns the list of address fields usable to format addresses."""
        return self._address_fields()

    @api.model
    def _commercial_fields(self):
        """ Returns the list of fields that are managed by the commercial entity
        to which a partner belongs. These fields are meant to be hidden on
        partners that aren't `commercial entities` themselves, and will be
        delegated to the parent `commercial entity`. The list is meant to be
        extended by inheriting classes. """
        return ['vat', 'credit_limit']

    def _commercial_sync_from_company(self):
        """ Handle sync of commercial fields when a new parent commercial entity is set,
        as if they were related fields """
        commercial_partner = self.commercial_partner_id
        if commercial_partner != self:
            sync_vals = commercial_partner._update_fields_values(self._commercial_fields())
            self.write(sync_vals)

    # def _fields_sync(self, values):
    #     """ Sync commercial fields and address fields from company and to children after create/update,
    #     just as if those were all modeled as fields.related to the parent """
    #     # 1. From UPSTREAM: sync from parent
    #     if values.get('parent_id') or values.get('type') == 'contact':
    #         # 1a. Commercial fields: sync if parent changed
    #         if values.get('parent_id'):
    #             self._commercial_sync_from_company()
    #         # 1b. Address fields: sync if parent or use_parent changed *and* both are now set
    #         if self.parent_id and self.type == 'contact':
    #             onchange_vals = self.onchange_parent_id().get('value', {})
    # #             self.update_address(onchange_vals)
    #
    #     # 2. To DOWNSTREAM: sync children
    #     self._children_sync(values)


class FleetDriverResPartnerRel(models.Model):
    _name = Constants.PARTNER_DRIVER
    _description = 'res_partner fleet_driver'
    driver_id = fields.Many2one(Constants.FLEET_DRIVER, string='Driver')
    partner_id = fields.Many2one(Constants.RES_PARTNER, string='Parent')
    company_id = fields.Many2one(Constants.RES_COMPANY, string='Company')
    from_date = fields.Date('from date')
    to_date = fields.Date('to date')
    role_id = fields.Integer('role')
    specific_type = fields.Integer('specific type')

    @api.onchange('partner_id')
    def _change_partner(self):
        for record in self:
            record.update({'company_id': record['partner_id'].company_id.id})


class FleetDriverLogCompany(models.Model):
    _name = 'fleet.employee.log'
    MODEL = 'fleet.employee.log'
    _description = 'Fleet employee log'

    driver_id = fields.Many2one(Constants.FLEET_DRIVER, string='Driver', index=True)
    user_id = fields.Many2one('res.users', string='User')
    company_id = fields.Many2one(Constants.RES_COMPANY, string='Company')
    from_date = fields.Datetime('from date', index=True)
    to_date = fields.Datetime('to date', index=True)
    phone = fields.Char('phone')
    ssn = fields.Char('ssn')
    employee_type = fields.Char('Employee type')
    card_type = fields.Char('Card type')
    account_sso_active = fields.Boolean('Account sso active', default=True)
    account_sso_create = fields.Boolean('Account sso create', default=True)
    award_id = fields.Many2one('sharevan.title.award', 'award_id')
    full_name = fields.Char(String="Full name", required=True)
    class_driver = fields.Many2one('sharevan.driver.license', string='Driver License',
                                   domain=lambda self: "[('country_id', '=', country_id),('status','=','running')]")
    expires_date = fields.Date(string="Expries Day")
    address = fields.Char(String="Address")
    no = fields.Char(String="No")
    status = fields.Char(String="status ")
    driver_license_date = fields.Date(string="Driver's liscense date")
