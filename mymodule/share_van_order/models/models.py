# -*- coding: utf-8 -*-

import re

from mymodule.share_van_order.models.base import Base
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from .utils import validate_utils as validate
from ...constants import Constants
from ...enum.MessageType import NotificationSocketType


class ShareVanInsurance(models.Model, Base):
    _name = 'sharevan.insurance'
    _description = 'Insurance'
    _inherit = 'sharevan.insurance'


class Company(models.Model, Base):
    _name = "res.company"
    _description = 'Companies'
    _order = 'sequence, name'
    _inherit = "res.company"

    point = fields.Float()
    province_id = fields.Many2one('sharevan.area', string="Province", domain=lambda
        self: "[('country_id', '=', country_id),('location_type','=','province'),('status','=','running')]")
    city_name = fields.Char('City name')
    district = fields.Char('District')
    ward = fields.Char('Ward')
    latitude = fields.Float(string='Geo Latitude', digits=(16, 5))
    longitude = fields.Float(string='Geo Longitude', digits=(16, 5))
    company_type = fields.Selection([
        ('0', 'Fleet'),
        ('1', 'Customer'),
        ('2', 'DLP')
    ], 'Company type', default='0', help='Company Type', required=True)
    customer_type = fields.Selection([
        ('1', 'Business'),
        ('2', 'Individual'),
        ('3', 'Logistics'),
        ('4', 'Transportation company'),
        ('5', 'Truck Group'),
        ('6', 'Individual fleet')
    ], 'Customer type', default='1', help='Customer Type', required=True)
    code = fields.Char(default='/', readonly=True)
    company_ranking = fields.Integer(string='Company ranking', compute='compute_sale')

    def reload(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def compute_sale(self):
        for record in self:
            result = None
            # customer company and personal
            if record['company_type'] == '1':
                sum_query = """
                    select sum(price_actual) sale from sharevan_bill_routing where company_id = %s and status_routing != '-1'
                """
                self.env.cr.execute(sum_query, (record['id'],))
                result = self._cr.dictfetchall()
            # fleet company
            elif record['company_type'] == '0':
                record.sale = 1000
            if result:
                record.sale = result[0]['sale']
            else:
                record.sale = 0
            record.company_ranking = record.company_ranking

    @api.model
    def create(self, vals):
        check_query = """
                    select * from res_company where company_type = '2'
                                                """
        self.env.cr.execute(check_query,
                            ())
        check_record = self._cr.dictfetchall()
        if check_record and self.company_type == '2':
            raise ValidationError('Only one DLP system company allowed')
        if 'email' in vals and vals['email'] != False:
            match = re.search(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9]+\.[a-zA-Z0-9.]*\.*[com|org|edu]{3}$)", vals['email'])
            if match:
                pass
            else:
                raise ValidationError(_('Format email address "Name <email@domain>'))
        if 'website' in vals:
            validate.validate_website_link(vals['website'])
        if 'zip' in vals:
            validate.validate_zip_code(vals['zip'])
        seq = self.env['ir.sequence'].get('self.res.company') or '/'
        vals['code'] = seq
        if 'award_company_id' not in vals:
            award_query = """
                select * from sharevan_title_award where title_award_type ='customer' order by from_point limit 1
                                """
            self.env.cr.execute(award_query,
                                ())
            award_lower = self._cr.dictfetchall()
            if award_lower:
                vals['award_company_id'] = award_lower[0]['id']
            else:
                raise ValidationError('Customer award not create')
        current_query = """
            select currency_id,weight_unit_id,volume_unit_id,parcel_unit_id from res_company where company_type ='2'
                                        """
        self.env.cr.execute(current_query,
                            ())
        current_record = self._cr.dictfetchall()
        if current_record:
            currency_id = current_record[0]['currency_id']
            volume_unit_id = current_record[0]['volume_unit_id']
            weight_unit_id = current_record[0]['weight_unit_id']
            parcel_unit_id = current_record[0]['parcel_unit_id']
        else:
            raise ValidationError('DLP company currency_id not found!')
        vals['currency_id'] = currency_id
        vals['weight_unit_id'] = weight_unit_id
        vals['volume_unit_id'] = volume_unit_id
        vals['parcel_unit_id'] = parcel_unit_id
        result = super(Company, self).create(vals)
        if result.customer_type == '2':
            seq = self.env['ir.sequence'].get('self.res.company') or '/'

            partner = self.env['res.partner'].sudo().create({
                'name': result.name,
                'code': result.code,
                'company_id': result.id,
                'phone': result.phone,
                'email': result.email,
                'street': result.street,
                'street2': result.street2,
                'zip': result.zip,
                'website': result.website
            }).sudo()
            query = """
                select id from sharevan_channel where name = 'customer' and channel_type ='manager' LIMIT 1
                    """
            self.env.cr.execute(query,
                                ())
            channel = self._cr.dictfetchall()
            channel_id = 0
            if not channel:
                raise ValidationError('Customer notification channel not create')
            else:
                channel_id = channel[0]['id']
            poisition_query = """
                            select id from sharevan_channel where name = 'customer' and channel_type ='manager' LIMIT 1
                                """
            self.env.cr.execute(poisition_query,
                                ())
            poisition_record = self._cr.dictfetchall()
            if not poisition_record:
                raise ValidationError('Position not create')
            else:
                channel_id = channel[0]['id']
            # SỬ dụng account_fleet_type để check tài khoản tồn tại rồi. nếu tk active = False thì k tạo bên sso nữa.
            # update tk cũ là login+deactivate và tài khoản mới sử dụng sso cũ.
            user = self.env['res.users'].sudo().create({
                'login': vals['phone'],
                'company_id': result.id,
                'account_fleet_type': True,
                'company_ids': [(4, result.id)],
                'partner_id': partner.id,
                'password': Constants.DEFAULT_PASS,
                'active': True,
                'channel_id': channel_id
            })
            partner.write({
                'user_id': user.id
            })
            result.write({
                'partner_id': partner.id
            })
        # self.reload()
        return result

    def write(self, values):
        update_param = {}
        if 'company_type' in values:
            check_query = """
                select * from res_company where company_type = '2'
                                                            """
            self.env.cr.execute(check_query,
                                ())
            check_record = self._cr.dictfetchall()
            if check_record and values['company_type'] == '2':
                if self.id != check_record[0]['id']:
                    raise ValidationError('Only one DLP system company allowed')
        if self.company_type == '2':
            if 'currency_id' in values:
                update_param['currency_id'] = values['currency_id']
            if 'weight_unit_id' in values:
                update_param['weight_unit_id'] = values['weight_unit_id']
            if 'volume_unit_id' in values:
                update_param['volume_unit_id'] = values['volume_unit_id']
            if 'parcel_unit_id' in values:
                update_param['parcel_unit_id'] = values['parcel_unit_id']
            if update_param:
                company_query = """
                    select id from res_company where id != %s
                """
                self.env.cr.execute(company_query,
                                    (self.id,))
                company_ids = self._cr.dictfetchall()
                for company in company_ids:
                    company_rec = self.env['res.company'].search([('id', '=', company['id'])])
                    company_rec.write(update_param)
        return super(Company, self).write(values)

    @api.constrains('email')
    def check_mail(self):
        if self.email:
            return validate.validate_mail_v2(self.email)

    @api.constrains('zip')
    def check_zip_code(self):
        if self.check_zip_code:
            return validate.validate_zip_code(self.zip)

    @api.constrains('website')
    def check_website_link(self):
        if self.website:
            return validate.validate_website_link(self.website)

    @api.onchange('company_type')
    def check_company_type(self):
        for record in self:
            record.update({'customer_type': False})

    @api.onchange('customer_type')
    def check_customer_type(self):
        for record in self:
            if not record['customer_type']:
                record.update({'customer_type': False})
            else:
                if record['company_type']=='0':
                    if int(record['customer_type'])<3:
                        notice = "Fleet customer type is not in list( Business , Individual)"
                        self.env.user.notify_danger(message=notice, title=NotificationSocketType.NOTIFICATION.value)
                        record.update({'customer_type': False})
                else:
                    if int(record['customer_type'])>2:
                        notice = "Order customer type is in list( Business , Individual)"
                        self.env.user.notify_danger(message=notice, title=NotificationSocketType.NOTIFICATION.value)
                        record.update({'customer_type': False})


class AwardCompany(models.Model, Base):
    _name = 'sharevan.award.company'
    _description = 'Award company '

    code = fields.Char()
    total_point = fields.Float()

