import base64
import json
import json as simplejson
import logging

from werkzeug import Response

from mymodule.base_next.controllers.api.validation import ValidationApi
from odoo import models, fields, _, http
from odoo.addons.base.models.ir_attachment import IrAttachment
from odoo.addons.base.models.res_partner import _lang_get
from odoo.api import onchange
from odoo.exceptions import ValidationError
from odoo.tools import datetime, timedelta, api
from ...base_next.controllers.api.base_method import BaseMethod
from ...enum.ClickActionType import ClickActionType
from ...enum.MessageType import NotificationSocketType
from ...enum.NotificationType import NotificationType
from ...enum.ObjectStatus import ObjectStatus

logger = logging.getLogger(__name__)


class ResPartnerLog(models.Model):
    _name = 'res.partner.log'
    _description = 'Res partner log'

    staff_type = fields.Many2one('res.staff.type', string="Position")
    # warehouse_ids = fields.One2many('sharevan.employee.warehouse', 'employee_id', string='Warehouses')
    lang = fields.Selection(_lang_get, string='Language',
                            help="All the emails and documents sent to this contact will be translated in this "
                                 "language.")
    company_id = fields.Many2one('res.company', string="Company")
    partner_id = fields.Many2one('res.partner', string="Company")
    province_id = fields.Many2one('sharevan.area', string="Province", domain=lambda
        self: "[('country_id', '=', country_id),('location_type','=','province'),('status','=','running')]")
    user_id = fields.Many2one('res.users', string="User login from app", domain=lambda
        self: "[('company_id', '=', company_id)]")
    city_name = fields.Char('City name')
    vat = fields.Char('Vat')
    name = fields.Char('City name')
    phone = fields.Char('Phone')
    status = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted')], 'Status', default="running")
    birthday = fields.Date('Birthday')
    rating_count = fields.Integer('Rating')
    rating_point = fields.Integer('Rating point')
    point_expiration_date = fields.Date(string='Point expiration date',
                                        default=datetime.today() + timedelta(days=365))
    active = fields.Boolean(default=True)
    street = fields.Char()
    nationality = fields.Many2one('res.country', string='Nationality')
    identify_number = fields.Integer()
    department_name = fields.Char()
    gender = fields.Selection([('male', 'Male'), ('other', 'Other'),
                               ('female', 'Female')], 'Gender', default="male")
    hire_date = fields.Date(string="Hire Date")
    leave_date = fields.Date(string="Leave Date")
    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'
    MODEL = 'res.partner'
    title = fields.Many2one('res.partner.title')

    staff_type = fields.Many2one('res.staff.type', string="Position")
    # warehouse_ids = fields.One2many('sharevan.employee.warehouse', 'employee_id', string='Warehouses')
    lang = fields.Selection(_lang_get, string='Language', default=lambda self: self.env.lang,
                            help="All the emails and documents sent to this contact will be translated in this "
                                 "language.")
    company_id = fields.Many2one('res.company', string="Company")
    province_id = fields.Many2one('sharevan.area', string="Province", domain=lambda
        self: "[('country_id', '=', country_id),('location_type','=','province'),('status','=','running')]")
    user_id = fields.Many2one('res.users', string="User login from app", domain=lambda
        self: "[('company_id', '=', company_id)]")
    city_name = fields.Char('City name')
    status = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted')], 'Status', default="running")
    birthday = fields.Date('Birthday')
    rating_count = fields.Integer('Rating')
    rating_point = fields.Integer('Rating point')
    point_expiration_date = fields.Date(string='Point expiration date', required=True,
                                        default=datetime.today() + timedelta(days=365))
    image_identify_frontsite = fields.Image("Image identify front side", max_width=128, max_height=128)
    image_identify_backsite = fields.Image("Image identify back side", max_width=128, max_height=128)
    credit_limit = fields.Float(string='Credit Limit')
    active = fields.Boolean(default=True)
    function = fields.Char(string='Job Position')
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    nationality = fields.Many2one('res.country', string='Nationality', required=True)
    identify_number = fields.Integer()
    department_name = fields.Char()
    gender = fields.Selection([('male', 'Male'), ('other', 'Other'),
                               ('female', 'Female')], 'Gender', default="male")
    hire_date = fields.Date(string="Hire Date", required=True, default=datetime.today())
    leave_date = fields.Date(string="Leave Date")

    @api.onchange('image_256')
    def _onchange_image_256(self):
        for record in self:
            print(record)

    @api.onchange('staff_type')
    def _onchange_staff_type(self):
        for record in self:
            if record['company_id']:
                if record['company_id']['company_type'] == '1':
                    if record['staff_type']['type'] != 'customer':
                        record.update(({'staff_type': False}))
                        notice = "Wrong type of staff !"
                        self.env.user.notify_warning(message=notice, title=NotificationSocketType.NOTIFICATION.value)
                    return {'domain': {
                        'staff_type': [('type', '=', 'customer')]
                    }}
                elif record['company_id']['company_type'] == '0':
                    if record['staff_type']['type'] != 'fleet':
                        record.update(({'staff_type': False}))
                        notice = "Wrong type of staff !"
                        self.env.user.notify_warning(message=notice, title=NotificationSocketType.NOTIFICATION.value)
                    return {'domain': {
                        'staff_type': [('type', '=', 'fleet')]
                    }}
                elif record['company_id']['company_type'] == '2':
                    if record['staff_type']['type'] != 'dlp':
                        record.update(({'staff_type': False}))
                        notice = "Wrong type of staff !"
                        self.env.user.notify_warning(message=notice, title=NotificationSocketType.NOTIFICATION.value)
                    return {'domain': {
                        'staff_type': [('type', '=', 'dlp')]
                    }}

    @api.onchange('image_identify_frontsite')
    def _onchange_image_identify_frontsite(self):
        for record in self:
            print(record)

    @api.onchange('image_identify_backsite')
    def _onchange_image_identify_backsite(self):
        for record in self:
            print(record)

    @api.onchange('country_id')
    def _onchange_country_id(self):
        for record in self:
            record.update({
                'province_id': False,
                'street': False,
                'city': False,
                'zip': False
            })

    @api.onchange('company_id')
    def _onchange_company_id(self):
        for record in self:
            if record['company_id']:
                if record['company_id']['company_type'] == '1':
                    record.update(({'staff_type': False}))
                    return {'domain': {
                        'staff_type': [('type', '=', 'customer')]
                    }}
                elif record['company_id']['company_type'] == '0':
                    record.update(({'staff_type': False}))
                    return {'domain': {
                        'staff_type': [('type', '=', 'fleet')]
                    }}
                elif record['company_id']['company_type'] == '2':
                    record.update(({'staff_type': False}))
                    return {'domain': {
                        'staff_type': [('type', '=', 'dlp')]
                    }}

    @api.onchange('birthday')
    def onchange_birthday(self):
        for record in self:
            if record['birthday']:
                date_assign = datetime.strptime(str(record['birthday']), '%Y-%m-%d')
                if date_assign > datetime.now() - timedelta(days=6570):
                    record['birthday'] = False
                    notice = "Age of employee is bigger than 18 year old !"
                    self.env.user.notify_danger(message=notice, title=NotificationSocketType.NOTIFICATION.value)

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

    @api.onchange('leave_date', 'hire_date')
    def _onchange_date_end(self):
        for record in self:
            if record['hire_date'] and record['leave_date']:
                if record['hire_date'] > record['leave_date']:
                    record.update({
                        'leave_date': False
                    })
                    test_msg = {"message": "Leave date must be greater than hire date! "}
                    self.env.user.notify_danger(**test_msg)

    @api.onchange('user_id')
    def _onchange_user_id(self):
        for record in self:
            if record.user_id.id:
                check_query = """
                select * from res_partner where user_id = %s """
                self.env.cr.execute(check_query, (record['user_id'].id,))
                check = self._cr.dictfetchall()
                if check:
                    record['user_id'] = False
                    notice = "user_id is unique for one partner ! You have added for account: " + check[0]['name']
                    self.env.user.notify_danger(message=notice, title=NotificationSocketType.NOTIFICATION.value,
                                                sticky=True)

    # def unlink(self):
    #     """ unlink()
    #     Deletes the records of the current set
    #     update res_partner active = False
    #     """
    #     raise ValidationError('You are not allow delete User information')

    def get_list_rating_badges(self, type):

        self.env.cr.execute(""" 
           SELECT json_agg(t)
               FROM (
                     SELECT srb.id,srb.name, srb.description , ir.uri_path as image ,rating_level
                         FROM  sharevan_rating_badges srb 
                         LEFT JOIN ir_attachment ir  on srb.id = ir.res_id
                         Where ir.res_model = 'sharevan.rating.badges' and srb.status = 'running' and srb.type  =%s
                     				) t ;""", (type,))
        result = self._cr.fetchall()
        if result[0][0] != None:
            re = result[0][0]

            content = re

            records = {
                'records': content
            }
        else:
            records = []
        simplejson.dumps(records, indent=4, sort_keys=True, default=str)
        return records

    def driver_rating_start(self, rating):

        routing_plan_day_id = rating['routing_plan_day_id']
        driver_id = rating['driver_id']
        num_rating = rating['num_rating']
        rating_badges = rating['rating_badges']
        employee_id = rating['employee_id']
        description = rating['description']

        check_query = """
            select distinct driver.trip_number from sharevan_routing_plan_day plan
                join fleet_driver driver on driver.id = plan.driver_id
                join res_partner partner on partner.id = plan.stock_man_id
                where plan.driver_id = %s and partner.user_id = %s 
        """
        self.env.cr.execute(check_query, (driver_id, http.request.env.uid,))
        check = self._cr.dictfetchall()
        if not check:
            raise ValidationError(_('You are not allow rating for driver !'))
        routing_plan_day = http.request.env['sharevan.routing.plan.day'].search([('id', '=', routing_plan_day_id)])
        if routing_plan_day.id == False:
            raise ValidationError(_('Routing plan day not exits !'))
        if num_rating > 5 and num_rating < 0:
            raise ValidationError(_('Star rating must be less than 5 and greater than 0 !'))

        rating_routing_plan_day = http.request.env['sharevan.rating'].search(
            [('rating_place_id', '=', routing_plan_day_id)])
        if len(rating_routing_plan_day) > 0:
            raise ValidationError(_('Routing plan day be evaluated !'))

        vals = {
            'rating_place_id': routing_plan_day_id,
            'driver_id': driver_id,
            'rating_badges_id': rating_badges,
            'employee_id': employee_id,
            'num_rating': num_rating,
            'note': description
        }
        obj_rating_badges = http.request.env['sharevan.rating'].sudo().create(vals)
        trip_number = check[0]['trip_number']
        trip_number = int(trip_number) + 1
        check_query = """
            update fleet_driver driver set trip_number=%s
                where id = %s
                """
        self.env.cr.execute(check_query, (str(trip_number), driver_id,))

        title = 'Rating'
        body = 'You are appreciated by your customers'

        val = {
            'user_id': [obj_rating_badges.driver_id.user_id.id],
            'title': title,
            'content': body,
            'type': NotificationType.RoutingMessage.value,
            'object_status': ObjectStatus.AssignCarWorking.value,
            'click_action': ClickActionType.customer_rating_driver.value,
        }
        http.request.env['sharevan.notification'].create(val)

        return {
            'id': obj_rating_badges['id']
        }

    def edit_customer_information_detail(self, customerInfo):
        id = http.request.env.uid
        checkString = isinstance(id, str)
        if checkString is True:
            raise ValidationError('Customer Id must Integer!')
        if id and 'id' in customerInfo:
            record = http.request.env[ResPartner.MODEL]. \
                web_search_read([['user_id', '=', id], ['id', '=', customerInfo['id']]], fields=None,
                                offset=0, limit=10, order='')
            if record['records']:
                company_rec = http.request.env['res.company'].search([('id', '=', http.request.env.company.id)])
                if not company_rec:
                    raise ValidationError('Customer not Exist!')
                if company_rec['customer_type'] != '2' and 'email' in customerInfo:
                    raise ValidationError('You do not have permission to update email!')
                if company_rec['customer_type'] != '2':
                    new_info = http.request.env[ResPartner._name]. \
                        browse(record['records'][0]['id']).write({
                        'city': customerInfo['city'], 'street': customerInfo['street'],
                        'zip': customerInfo['zip']})
                    result = http.request.env[ResPartner._name].get_customer_information_detail()
                    record = result['records'][0]
                    record['city'] = customerInfo['city']
                    record['street'] = customerInfo['street']
                    record['zip'] = customerInfo['zip']
                else:
                    new_info = http.request.env[ResPartner._name]. \
                        browse(record['records'][0]['id']).write({
                        'city': customerInfo['city'], 'street': customerInfo['street'], 'email': customerInfo['email'],
                        'zip': customerInfo['zip']})
                    result = http.request.env[ResPartner._name].get_customer_information_detail()
                    record = result['records'][0]
                    record['city'] = customerInfo['city']
                    record['street'] = customerInfo['street']
                    record['email'] = customerInfo['email']
                    record['zip'] = customerInfo['zip']
                records = {
                    'length': 1,
                    'records': [record]
                }
                simplejson.dumps(records, indent=4, sort_keys=True, default=str)
                return records
            else:
                raise ValidationError('Customer not Exist!')
        else:
            raise ValidationError('Customer Id not found!')

    def update_image_user_web(self, file):

        check_user = self.env['res.partner'].search(
            [('user_id', '=', http.request.env.uid,)])

        image_querry = """
                           SELECT ir.id
                           FROM ir_attachment ir
                           where res_model = 'res.partner' and  res_id = %s and status = 'running'
                         """
        self.env.cr.execute(image_querry, (check_user.id,))
        result = self._cr.fetchall()
        if len(result) > 0:
            id_image = result[0]
            len(id_image)
            if len(id_image):
                update_status = """ Update ir_attachment
                                                                               Set status = 'deleted'
                                                                               where id = %s
                                                                                   """
                self.env.cr.execute(update_status, (id_image,))
            val = {
                'res_model': 'res.partner',
                'mimetype': file.mimetype,
                'name': file.filename,
                'res_id': check_user.id,
                'type': 'binary',
                'status': 'running',
                'datas': base64.b64encode(file.read())
            }
            rec = http.request.env[IrAttachment._name].create(val)
            rec.write({'uri_path': rec['store_fname'],
                       'res_field': 'image_256'})
        response_data = {}
        response_data['result'] = 'Update success'
        return Response(json.dumps(response_data), content_type="application/json", status=200)

    def get_customer_information_detail_web(self):
        # session, data_json = BaseMethod.check_authorized()
        # if not session:
        #     return Response(json.dumps('UN_AUTHORIZED'), content_type="application/json", status=403)

        query = """
                  select distinct rs.id,rs.name,rs.code,rs.phone,rs.city,rs.street,rs.zip , rs.display_name, rs.date, 
                     rc.id company_id,rc.code  company_code,rs.birthday,
                     rs.gender,rs.vat,
                     rc.name  company_name ,rc.vat  company_vat ,rc.status  company_status,
                     rc.province_id company_province_id, rc.company_ranking
                     ,rc.phone  company_phone,rc.point company_point,rc.company_type company_type,
                     rc.customer_type company_customer_type,
                     rc.district  company_district,rc.ward  company_ward,rc.street  company_street,
                     rc.city  company_city,
                     rs.title, rs.parent_id,  rs.lang, rs.tz, 
                     rs.user_id, rs.employee,rs.type, rs.street, 
                     rs.state_id, rs.country_id, rs.email,rs.phone, rs.mobile, 
                     rs.color, rs.code, rs.staff_type, rs.city_name,
                     type.code staff_type_name,att.uri_path
                     from res_users s 
                        left join res_company rc on s.company_id = rc.id
                         left join res_partner rs on s.partner_id = rs.id
                         left join ir_attachment att on att.res_id = rs.id and att.res_model = 'res.partner' 
                             and att.res_field = 'image_256' and att.status =  'running'
                         left join res_staff_type type  on type.id = rs.staff_type
                     where rs.user_id = %s
                 """
        self._cr.execute(query, (http.request.env.uid,))
        result = self.env.cr.dictfetchall()  # user
        if result:
            company = {
                'id': result[0]['company_id'],
                'code': result[0]['company_code'],
                'name': result[0]['company_name'],
                'phone': result[0]['company_phone'],
                'status': result[0]['company_status'],
                'company_ranking': result[0]['company_ranking'],
                'province_id': result[0]['company_province_id'],
                'tax_id': result[0]['company_vat'],
                'street': result[0]['company_street'],
                'district': result[0]['company_district'],
                'ward': result[0]['company_ward'],
                'point': result[0]['company_point'],
                'country_id': result[0]['country_id']
            }
            user = {
                'id': result[0]['id'],
                'name': result[0]['name'],
                'company': company,
                'birthday': result[0]['birthday'],
                'phone': result[0]['phone'],
                'mobile': result[0]['mobile'],
                'city': result[0]['city'],
                'street': result[0]['street'],
                'zip': result[0]['zip'],
                'display_name': result[0]['display_name'],
                'lang': result[0]['lang'],
                'country_id': result[0]['country_id'],
                'email': result[0]['email'],
                'uri_path': result[0]['uri_path'],
                'code': result[0]['code'],
                'user_id': result[0]['user_id'],
                'gender': result[0]['gender'],
                'vat': result[0]['vat'],
            }
            simplejson.dumps(user, indent=4, sort_keys=True, default=str)
            return user
        else:
            raise ValidationError('User id  not found!')

    def edit_customer_information_detail_web(self, customerInfo):
        id = http.request.env.uid
        checkString = isinstance(id, str)
        if checkString is True:
            raise ValidationError('Customer Id must Integer!')
        # if carrier._is_mobile(number_type(phonenumbers.parse(customerInfo['phone']))) is False:
        #     response_data = {
        #         'result': 'Phone error!',
        #         'status': 500
        #     }
        #     return Response(json.dumps(response_data), status=500)
        if id:
            record = http.request.env[ResPartner.MODEL]. \
                web_search_read([['user_id', '=', id]])
            if record['records']:
                company_rec = http.request.env['res.company'].search([('id', '=', http.request.env.company.id)])
                if not company_rec:
                    raise ValidationError('Customer not Exist!')
                new_info = http.request.env[ResPartner._name]. \
                    browse(record['records'][0]['id']).write({
                    'phone': customerInfo['phone'],
                    'mobile': customerInfo['mobile'],
                    'lang': customerInfo['lang'],
                    'gender': customerInfo['gender'],
                    'vat': customerInfo['vat'],
                    'street': customerInfo['street'], 'email': customerInfo['email'],
                    'birthday': customerInfo['birthday']})
                result = http.request.env[ResPartner._name].get_customer_information_detail_web()
                record = result
                record['phone'] = customerInfo['phone']
                record['mobile'] = customerInfo['mobile']
                record['street'] = customerInfo['street']
                record['lang'] = customerInfo['lang']
                record['email'] = customerInfo['email']
                record['birthday'] = customerInfo['birthday']
                record['gender'] = customerInfo['gender']
                record['vat'] = customerInfo['vat']
                records = {
                    'length': 1,
                    'records': [record]
                }
                simplejson.dumps(records, indent=4, sort_keys=True, default=str)
                return records
            else:
                raise ValidationError('Customer not Exist!')
        else:
            raise ValidationError('Customer Id not found!')

    def get_customer_information_detail(self):
        query = """
                SELECT json_agg(t)
                    FROM (
                 select distinct rs.id,rs.name,rs.phone,rs.city,rs.street,rs.zip ,
                    s.company_id, rs.display_name, rs.date, 
                    rs.title, rs.parent_id,  rs.lang, rs.tz, 
                    rs.user_id, rs.employee,rs.type, rs.street, 
                    rs.state_id, rs.country_id, rs.email,rs.phone, rs.mobile, 
                    rs.color, rs.code, rs.staff_type, rs.city_name,depot.place_id depot_id, depot.depot_code,
                    type.code staff_type_name,att.uri_path,company.point point,company.point company_num_rate,
                    company.name company_name,att.uri_path,company.company_type,company.customer_type
                    from res_users s 
                        left join res_partner rs on s.partner_id = rs.id
                        left join ir_attachment att on att.res_id = rs.id and att.res_model = 'res.partner' 
                            and att.res_field = 'image_256' and att.status =  'running'
                        left join res_company company on company.id = s.company_id
                        left join res_staff_type type  on type.id = rs.staff_type
                        left join (select employee_id, place_id,depot.depot_code
                                        from sharevan_employee_warehouse cal 
                                    join sharevan_depot depot on depot.id = cal.place_id
                                where cal.user_id = %s and cal.date_assign = current_date) depot on depot.employee_id = rs.id
                    where rs.user_id = %s and company.company_type ::integer in (1,2)
                ) t
                """
        self._cr.execute(query, (http.request.env.uid, http.request.env.uid,))
        result = self._cr.fetchall()
        if result[0]:
            if result[0][0]:
                re = result[0][0]
                records = {
                    'length': len(re),
                    'records': re
                }
                simplejson.dumps(records, indent=4, sort_keys=True, default=str)
                return records
            else:
                raise ValidationError('User id  not found!')
        else:
            raise ValidationError('User id  not found!')

    def update_account_long_haul(self, longHaulInfo, files):
        longHaulInfoJson = json.loads(longHaulInfo)

        name = longHaulInfoJson['name']
        phone = longHaulInfoJson['phone']

        uid = http.request.session['uid']

        check_user = self.env['res.partner'].search(
            [('user_id', '=', uid)])

        if len(check_user) == 0:
            logger.warn(
                "Account does not exist !",
                exc_info=True)
            response_data = {}
            response_data['result'] = 'error: Account already exists'
            return Response(json.dumps(response_data), content_type="application/json", status=200)

        if isinstance(name, int) or isinstance(phone, int):
            logger.warn(
                "Phone,name is of type string",
                exc_info=True)
            response_data = {}
            response_data['result'] = 'error: Phone,name,id_card is of type string'
            return Response(json.dumps(response_data), content_type="application/json", status=200)

        check_phone_number = self.env['res.partner'].search(
            [('phone', '=', phone), ('id', '!=', check_user['id'])])
        v = {
            'phone': phone
        }
        # validate.validate_phone_number_v3(v)
        if len(check_phone_number) > 0:
            logger.warn(
                "Phone number already exists  !",
                exc_info=True)
            response_data = {}
            response_data['result'] = 'error_driver_phone_number'
            return Response(json.dumps(response_data), content_type="application/json", status=200)

        context = self._context
        current_uid = context.get('uid')

        check_user.write({
            'name': name,
            'phone': phone,
        })

        for file in files:
            if file.filename:
                image_querry = """
                      SELECT ir.id
                      FROM ir_attachment ir
                      where res_model = 'res.partner' and  res_id = %s and status = 'running'
                    """
                self.env.cr.execute(image_querry, (check_user['id'],))
                result = self._cr.fetchall()
                if len(result) > 0:
                    id_image = result[0]
                    len(id_image)
                    if len(id_image):
                        update_status = """ Update ir_attachment
                                                                          Set status = 'deleted'
                                                                          where id = %s
                                                                              """
                        self.env.cr.execute(update_status, (id_image,))
                val = {
                    'res_model': 'res.partner',
                    'mimetype': file.mimetype,
                    'name': file.filename,
                    'res_id': check_user['id'],
                    'type': 'binary',
                    'datas': base64.b64encode(file.read())
                }
                rec = http.request.env[IrAttachment._name].create(val)
                rec.write({'uri_path': rec['store_fname'],
                           'res_field': 'image_128'
                           })
                break
        response_data = {}
        response_data['result'] = 'Update success'
        return Response(json.dumps(response_data), content_type="application/json", status=200)

    def rating_customer(self, rating):
        print(rating)
        INSERT_QUERY = """INSERT INTO sharevan_rating_badges_sharevan_rating_customer_rel
                                       VALUES ( %s , %s ) """
        if rating['type'] == 'ROUTING':
            check_query = """ 
                    select plan.driver_id ,plan.stock_man_id,  plan.id ,plan.rating_customer,plan.status
                        from sharevan_routing_plan_day plan
                    join fleet_driver driver on driver.id = plan.driver_id
                        where plan.id =%s and driver.user_id = %s
                    """
            self._cr.execute(check_query, (rating['rating_place_id'], http.request.env.uid,))
            result = self._cr.dictfetchall()
            if result:
                if result[0]['status'] != '2':
                    raise ValidationError('You have not finish this routing')
                if result[0]['rating_customer'] == None or result[0]['rating_customer'] == False:
                    plan = self.env['sharevan.routing.plan.day'].search([('id', '=', result[0]['id'])])
                    stock_man = self.env['res.partner'].search([('id', '=', result[0]['stock_man_id'])])
                    rating_badges = {
                        'rating_place_id': result[0]['id'],
                        'driver_id': result[0]['driver_id'],
                        'employee_id': result[0]['stock_man_id'],
                        'note': rating['note'],
                        'rating': int(rating['rating'])
                    }
                    record = self.env['sharevan.rating.customer'].sudo().create(rating_badges)
                    if record:
                        list_badges = rating['list_badges']
                        for rec in list_badges:
                            http.request.cr.execute(INSERT_QUERY, (record[0]['id'], rec,))
                        plan.write({
                            'rating_customer': True,
                            'rating_customer_id': record[0]['id']
                        })
                        stock_man.write({
                            'rating_count': int(stock_man['rating_count']) + 1,
                            'rating_point': int(stock_man['rating_point']) + int(rating['rating'])
                        })
                        return True
                    else:
                        return 500
                else:
                    raise ValidationError('Driver had rated customer already!')
            else:
                raise ValidationError('You are not running this routing!')

    def get_rating_customer_info(self, routing_plan_day_id):
        query = """
                select partner.display_name, partner.phone,ir.uri_path,partner.id
                    from res_partner partner
                JOIN sharevan_routing_plan_day rpd on rpd.stock_man_id = partner.id
                JOIN fleet_driver driver on driver.id = rpd.driver_id
                LEFT JOIN ir_attachment ir on ir.res_id = partner.id and ir.res_model ='res.partner' and ir.name='image_256'
                    where rpd.id = %s and driver.user_id = %s
            """
        self._cr.execute(query, (routing_plan_day_id, http.request.env.uid,))
        result = self._cr.dictfetchall()
        if result:
            return result[0]
        else:
            raise ValidationError('Stock man not found!')


class ResStaffType(models.Model):
    _name = 'res.staff.type'
    MODEL = 'res.staff.type'
    _order = 'name'
    _description = 'Staff Type'

    code = fields.Selection([('CUSTOMER_MANAGER', 'CUSTOMER_MANAGER'),
                             ('CUSTOMER_STOCKMAN', 'CUSTOMER_STOCKMAN'),
                             ('FLEET_MANAGER', 'FLEET_MANAGER'),
                             ('FLEET_DRIVER', 'FLEET_DRIVER'),
                             ('SHAREVAN_MANAGER', 'SHAREVAN_MANAGER'),
                             ('SHAREVAN_STOCKMAN', 'SHAREVAN_STOCKMAN')],
                            string='Code', required=True, translate=True)
    name = fields.Char(string='Name', required=True, translate=True)
    description = fields.Char(string='Description')
    status = fields.Selection([('running', 'Running'), ('deleted', 'Deleted')], string='Status',
                              default='running')
    type = fields.Selection([('customer', 'Customer'),
                             ('fleet', 'Fleet'),
                             ('dlp', 'DLP')],
                            string='Type', translate=True)

    @onchange('code')
    def _onchange_code(self):
        for record in self:
            query = """
                select * from res_staff_type where code = %s
                    """
            self._cr.execute(query, (record['code'] or '',))
            result = self._cr.dictfetchall()
            if result and result[0]['id'] != record['id'].origin:
                record['code'] = False
                notice = "code is unique for staff type ! You have added for code: " + str(result[0]['id'])
                self.env.user.notify_danger(message=notice, title=NotificationSocketType.NOTIFICATION.value,
                                            sticky=True)
            if record['code'] == 'CUSTOMER_MANAGER' or record['code'] == 'CUSTOMER_STOCKMAN':
                record['type'] = 'customer'
            elif record['code'] == 'FLEET_MANAGER' or record['code'] == 'FLEET_DRIVER':
                record['type'] = 'fleet'
            elif record['code'] == 'SHAREVAN_MANAGER' or record['code'] == 'SHAREVAN_STOCKMAN':
                record['type'] = 'dlp'

    def unlink(self):
        raise ValidationError('You not allow to delete record')


class ResCompany(models.Model):
    _inherit = 'res.company'

    _name = 'res.company'

    warehouse_ids = fields.One2many('sharevan.warehouse', 'company_id', string='Warehouses',
                                    domain=[('status', '=', 'running')])

    career_ids = fields.Many2many('sharevan.career', string='Industry',
                                  domain=lambda self: "[('status', '=', 'running')]")
    province = fields.Many2one('sharevan.area', string='Province', domain=lambda
        self: "[('country_id', '=', country_id),('location_type','=','province'),('status','=','running')]")
    attach_image = fields.Many2many('ir.attachment', string="Attach Image")
    vehicle_supply = fields.Integer('Vehicle Supply', compute='_compute_supply', store=False)
    driver_supply = fields.Integer('Driver Supply', compute='_compute_supply', store=False)
    warehouse_supply = fields.Integer('Warehouse Supply', compute='_compute_supply', store=False)
    depot_supply = fields.Integer('Depot Supply', compute='_compute_supply', store=False)
    engagement_point = fields.Integer('Engagement point', default=1)

    def unlink(self):
        """ unlink()

        Deletes the records of the current set

        update res_partner active = False
        """
        if not self:
            return True

        self.check_access_rights('unlink')
        self._check_concurrency()

        # mark fields that depend on 'self' to recompute them after 'self' has
        # been deleted (like updating a sum of lines after deleting one line)
        self.flush()
        self.modified(self._fields)

        with self.env.norecompute():
            self.check_access_rule('unlink')

            cr = self._cr
            data = self.env['ir.model.data'].sudo().with_context({})
            attachment = self.env['ir.attachment'].sudo()
            ir_model_data_unlink = data
            ir_attachment_unlink = attachment

            # TOFIX: this avoids an infinite loop when trying to recompute a
            # field, which triggers the recomputation of another field using the
            # same compute function, which then triggers again the computation
            # of those two fields
            for field in self._fields.values():
                self.env.remove_to_compute(field, self)

            for sub_ids in cr.split_for_in_conditions(self.ids):
                query = "UPDATE %s SET status = 'deleted' WHERE id IN %%s" % self._table
                cr.execute(query, (sub_ids,))
            # invalidate the *whole* cache, since the orm does not handle all
            # changes made in the database, like cascading delete!
            self.invalidate_cache()
            if ir_model_data_unlink:
                ir_model_data_unlink.unlink()
            if ir_attachment_unlink:
                ir_attachment_unlink.unlink()
            # DLE P93: flush after the unlink, for recompute fields depending on
            # the modified of the unlink
            self.flush()

        # auditing: deletions are infrequent and leave no trace in the database

        return True

    def get_career(self):
        query = """
            select id,name,code from sharevan_career
                where status = 'running'
        """
        self.env.cr.execute(query,
                            ())
        result = self._cr.dictfetchall()
        return {
            'records': result
        }

    def _compute_supply(self):
        for record in self:
            if record.company_type == '0':
                query = """ 
                    select count( distinct driver.id) driver_count,count( distinct vehicle.id) vehicle_count
                        from fleet_vehicle vehicle
                    join fleet_driver driver on driver.company_id = vehicle.company_id
                    join fleet_vehicle_state state on state.id = vehicle.state_id
                        where state.code != 'DOWNGRADED' and driver.status='running' and vehicle.company_id = %s
                """
                http.request.env['fleet.vehicle']._cr.execute(query, (record.id,))
                records = http.request.env['fleet.vehicle']._cr.dictfetchall()
                if records:
                    record.vehicle_supply = records[0]['vehicle_count']
                    record.driver_supply = records[0]['driver_count']
                    record.warehouse_supply = 0
                    record.depot_supply = 0
                else:
                    record.vehicle_supply = 0
                    record.driver_supply = 0
                    record.warehouse_supply = 0
                    record.depot_supply = 0
            elif record.company_type == '1':
                query = """ 
                    select count( distinct id) warehouse_supply
                        from sharevan_warehouse 
                    where status='running' and company_id = %s
                        """
                http.request.env['sharevan.warehouse']._cr.execute(query, (record.id,))
                records = http.request.env['sharevan.warehouse']._cr.dictfetchall()
                if records:
                    record.warehouse_supply = records[0]['warehouse_supply']
                    record.vehicle_supply = 0
                    record.driver_supply = 0
                    record.depot_supply = 0
                else:
                    record.warehouse_supply = 0
                    record.vehicle_supply = 0
                    record.driver_supply = 0
                    record.depot_supply = 0

            else:
                query = """ 
                    select count( distinct id) depot_supply
                        from sharevan_depot
                    where status='running' and company_id = %s
                        """
                http.request.env['sharevan.depot']._cr.execute(query, (record.id,))
                records = http.request.env['sharevan.depot']._cr.dictfetchall()
                if records:
                    record.depot_supply = records[0]['depot_supply']
                    record.warehouse_supply = 0
                    record.vehicle_supply = 0
                    record.driver_supply = 0
                else:
                    record.warehouse_supply = 0
                    record.vehicle_supply = 0
                    record.driver_supply = 0
                    record.depot_supply = 0

    def get_country(self):
        query = """
            select country.id,country.name,country.code,att.uri_path from res_country country
                left join ir_attachment att on att.res_id = country.id and att.res_model ='res.country'
                where country.status = 'running'
        """
        self.env.cr.execute(query,
                            ())
        result = self._cr.dictfetchall()
        return {
            'records': result
        }
