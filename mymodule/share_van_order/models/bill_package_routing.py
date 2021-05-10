import json
import logging
from datetime import datetime

import geopy
import pytz
import requests

from addons.mail.models.ir_attachment import IrAttachment
from addons.web.controllers.auth import AuthSsoApi
from mymodule.base_next.controllers.api.base_method import BaseMethod
from mymodule.base_next.controllers.api.firebase_messaging import FirebaseMessagingAPI
from mymodule.base_next.models.notification import Notification
from mymodule.base_next.models.routing_plan_day import RoutingPlanDay
from mymodule.enum.BillRoutingStatus import BillRoutingStatus
from mymodule.enum.ClickActionType import ClickActionType
from mymodule.enum.MessageType import MessageType, NotificationSocketType
from mymodule.enum.NotificationType import NotificationType
from mymodule.enum.ObjectStatus import ObjectStatus
from mymodule.enum.RoutingDetailStatus import RoutingDetailStatus
from mymodule.enum.RoutingTroubleType import RoutingTroubleType
from odoo import models, fields, http, _
from odoo.exceptions import ValidationError
from odoo.http import Response, request
from odoo.tools import config, base64, api, date_utils

logger = logging.getLogger(__name__)

INSERT_QUERY = "INSERT INTO ir_attachment_sharevan_routing_plan_day_rel " \
               " VALUES ( %s , %s ) "


class BillPackageRoutingPlan(models.Model):
    _name = 'sharevan.bill.package.routing.plan'
    _description = 'bill package routing by plan '
    _inherit = 'sharevan.bill.package.routing.plan'

    qr_code = fields.Image("Image", max_width=512, max_height=512)
    attach_image = fields.Many2many('ir.attachment', string="Attach Image")
    name = fields.Char('Name code')


class BillRouting(models.Model):
    _name = 'sharevan.bill.routing'
    MODEL = 'sharevan.bill.routing'
    _description = 'bill routing'

    code = fields.Char(string='Bill Lading Code', required=True, copy=False, readonly=True,
                       index=True,
                       default=lambda self: _('New'))
    insurance_id = fields.Many2one('sharevan.insurance', 'Insurance')
    total_weight = fields.Float('Total weight')
    total_amount = fields.Float('Temporary amount', default=0)
    tolls = fields.Float('Tolls')
    surcharge = fields.Float('Surcharge')
    total_volume = fields.Float('Total volume')
    vat = fields.Float('VAT(%)', digits=(2, 1))
    promotion_code = fields.Float('Promotion code')
    release_type = fields.Integer('Release type')
    cancel_check = fields.Boolean('Cancel check', help="True: DLP employee cancel, False: Customer cancel")
    total_parcel = fields.Integer('Total package')
    toogle = fields.Boolean('Cancel check', store=False, compute="compute_all")
    company_id = fields.Many2one('res.company', 'Customer', default=lambda self: self.env.company.id,
                                 domain=[('company_type', 'in', ('1', '2'))])
    award_company_id = fields.Many2one('sharevan.title.award')
    routing_plan_day_ids = fields.One2many('sharevan.routing.plan.day', 'bill_routing_id',
                                           string='Routing plan day')
    start_date = fields.Date('Start Date', default=fields.Date.today(), required=True)
    end_date = fields.Date('End Date')

    subscribe_id = fields.Many2one('sharevan.subscribe', 'Subscribe', index=True)
    cycle_type = fields.Selection(
        [('1', 'Hàng ngày'), ('2', 'Hàng tuần'), ('3', 'Hàng tháng'), ('4', 'Giao nhanh'),
         ('5', 'Một lần')], 'Cycle type',
        default='5')
    week_choose = fields.Selection(
        [('0', 'Chủ nhật'), ('1', 'Thứ hai'), ('2', 'Thứ ba'),
         ('3', 'Thứ tư'), ('4', 'Thứ năm'), ('5', 'Thứ sáu'), ('6', 'Thứ bảy')], 'Week choose',
        default='1')
    chooseDay = fields.Integer("Choose Date")
    # end declare for view
    qr_code = fields.Char(string='QR Code')
    routing_scan = fields.Boolean(string='Routing scan')
    price_actual = fields.Float(string='Price actual')
    sbl_type = fields.Selection(
        [('DLP', 'DLP'), ('SO', 'SO')], 'Sbl type',
        default='DLP')
    status_routing = fields.Selection(
        [('-1', 'Cancel'), ('0', 'In Claim'),
             ('1', 'Shipping'), ('2', 'Finished'), ('3', 'Waiting')],
        string='Status', default='3', required=True)
    reason = fields.Selection(
        [('1', 'Customer not found'), ('2', 'Order package change'),
         ('3', 'Customer cancel'), ('4', 'System not satisfy')],
        string='Reason', required=True)
    trouble_type = fields.Selection(
        [('0', 'Normal'), ('1', 'Sos'),
         ('2', 'Retry'), ('3', 'Return'), ('4', 'Pick up fail'), ('5', 'Waiting confirm')],
        string='Trouble type', default='0', required=True)
    description = fields.Text('Description', default=' ')

    name = fields.Char(string='Bill Routing Code', required=True, copy=False, readonly=True,
                       index=True,
                       default=lambda self: _('New'))
    from_bill_lading_id = fields.Many2one('sharevan.bill.lading', 'From bill of lading', index=True)
    export_weight = 0.0
    export_volume = 0.0
    change_bill_lading_detail_id = fields.Many2one('sharevan.bill.lading.detail', 'Bill detail change')
    order_package_id = fields.Many2one('sharevan.bill.order.package', string='Order package',
                                       domain=[('status', '=', 'running')],
                                       required=True)
    problem_image = fields.Many2many('ir.attachment', string="Problem image")
    create_bol = fields.Datetime('Create BOL')
    # doninzone||outzone
    inzone_num = fields.Integer('total bill of lading type inzone', default=0)
    outzone_num = fields.Integer('total bill of lading type outzone', default=0)

    @api.model
    def create(self, vals):
        raise ValidationError('You not allow to create this data record')

    def create_bill_routings(self, bill_lading_ids):
        if len(bill_lading_ids) == 0:
            raise ValidationError('Bill of lading ids id empty')
        bill_lading_query = """
            select distinct STRING_AGG( code::text, ',') OVER(PARTITION BY company_id) order_code,company_id
                from sharevan_bill_routing 
            where   id ::integer in (
        """
        for id in bill_lading_ids:
            bill_lading_query += str(id) + ","
        bill_lading_query = bill_lading_query[:-1]
        bill_lading_query += ") group by company_id,code"
        self.env.cr.execute(bill_lading_query, ())
        list_bill = self._cr.dictfetchall()
        if list_bill:
            company_list = []
            for bill in list_bill:
                info = {
                    'company_id': bill['company_id'],
                    'bill_code': bill['order_code']
                }
                company_list.append(info)

            for company in company_list:
                user_query = """
                    select id from res_users
                        where active = true and company_id = %s
                """
                company['bill_code'] = company['bill_code'][:-1]
                self.env.cr.execute(user_query, (company['company_id'],))
                list_user = self._cr.dictfetchall()
                ids = []
                if list_user:
                    for user in list_user:
                        ids.append(user['id'])
                    if list_user:
                        title = 'New routing play have been scan!'
                        body = 'New routing play have been scan. Please check order! ' \
                               + company['bill_code']
                        item_id = ''
                        try:
                            objct_val = {
                                "title": title,
                                "name": title,
                                "content": body,
                                "create_date": datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S"),
                                "type": 'routing',
                                "image_256": '',
                                "object_status": RoutingDetailStatus.Unconfimred.value,
                                "click_action": ClickActionType.driver_main_activity.value,
                                "message_type": MessageType.success.value,
                                "item_id": item_id,
                                "is_read": False
                            }
                            objct_val = json.dumps(objct_val)
                            click_action = ClickActionType.notification_driver.value
                            message_type = MessageType.success.value
                            item_id = ''
                            INSERT_NOTIFICATION_QUERY = """
                                INSERT INTO public.sharevan_notification( title, content, sent_date, type, 
                                    object_status, click_action, message_type, item_id, create_uid, create_date,status) 
                                VALUES ( 
                                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id """
                            sent_date = datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")
                            http.request.cr.execute(INSERT_NOTIFICATION_QUERY, (
                                title, body, sent_date, 'order', RoutingDetailStatus.Unconfimred.value,
                                ClickActionType.driver_main_activity.value, MessageType.success.value, '', 1,
                                sent_date, 'status',))
                            result = http.request.env[Notification._name]._cr.fetchall()
                            print(result[0][0])
                            if result[0][0]:
                                for id in ids:
                                    INSERT_NOTIFICATION_REL_QUERY = """
                                        INSERT INTO public.sharevan_notification_user_rel(
                                            notification_id, user_id, is_read)
                                            VALUES (%s, %s, %s) RETURNING id 
                                                """
                                    http.request.cr.execute(INSERT_NOTIFICATION_REL_QUERY, (result[0][0], id, False,))
                            FirebaseMessagingAPI. \
                                send_message_for_all_normal(ids=ids, title=title, body=str(objct_val), short_body=body,
                                                            item_id=item_id,
                                                            click_action=click_action, message_type=message_type)
                            return {
                                'status': 200,
                                'message': 'Send notification Successful'
                            }
                        except:
                            logger.warn(
                                "Not send message",
                                RoutingPlanDay._name, item_id,
                                exc_info=True)
                            return {
                                'status': 200,
                                'message': 'Send notification type'
                            }
                    else:
                        logger.warn(
                            "Bill routing create success! send message fail",
                            RoutingPlanDay._name, company['bill_code'],
                            exc_info=True)
                        return {
                            'status': 200,
                            'message': 'Send notification type'
                        }
                else:
                    logger.warn(
                        "Bill routing create success! send message fail because user not found!",
                        RoutingPlanDay._name, company['bill_code'],
                        exc_info=True)
                    return {
                        'status': 200,
                        'message': 'Send notification fail'
                    }
            return {
                'status': 200,
                'message': 'Send notification Successful'
            }
        else:
            logger.warn(
                "Bill of lading not found !",
                exc_info=True)
            return Response(response=str('Bill of lading not found'), status=500)

    def create_bill_routings_old(self, bill_lading_ids):
        if len(bill_lading_ids) == 0:
            raise ValidationError('Bill of lading ids id empty')
        bill_lading_query = """
            select distinct bill.*,plan.date_plan,plan.bill_routing_id from sharevan_routing_plan_day plan 
                join sharevan_bill_lading_detail detail on plan.bill_lading_detail_id = detail.id
                join sharevan_bill_lading bill on bill.id = detail.bill_lading_id
            where TO_CHAR(plan.create_date, 'YYYY-MM-DD')  = TO_CHAR( current_date, 'YYYY-MM-DD')
                and detail.bill_lading_id ::integer in (
        """
        for id in bill_lading_ids:
            bill_lading_query += str(id) + ","
        bill_lading_query = bill_lading_query[:-1]
        bill_lading_query += ")"
        self.env.cr.execute(bill_lading_query, ())
        list_bill = self._cr.dictfetchall()
        update_bill_routing_old = []
        if list_bill:
            company_list = []
            for bill in list_bill:
                update_bill_routing_old.append(bill['bill_routing_id'])
                if len(company_list) == 0:
                    info = {
                        'company_id': bill['company_id'],
                        'bill_code': bill['name']
                    }
                    company_list.append(info)
                else:
                    for company in company_list:
                        if bill['company_id'] == company['company_id']:
                            company['bill_code'] += bill['name'] + ', '
                        else:
                            info = {
                                'company_id': bill['company_id'],
                                'bill_code': bill['name']
                            }
                            company_list.append(info)
                bill_routing = {
                    'code': bill['name'],
                    'insurance_id': bill['insurance_id'],
                    'total_weight': bill['total_weight'],
                    'total_amount': bill['total_amount'],
                    'price_actual': bill['total_amount'],
                    'routing_scan': False,
                    'order_package_id': bill['order_package_id'],
                    'tolls': bill['tolls'],
                    'surcharge': bill['surcharge'],
                    'total_volume': bill['total_volume'],
                    'vat': bill['vat'],
                    'promotion_code': bill['promotion_code'],
                    'release_type': bill['release_type'],
                    'total_parcel': bill['total_parcel'],
                    'company_id': bill['company_id'],
                    'start_date': bill['date_plan'],
                    'subscribe_id': bill['subscribe_id'],
                    'cycle_type': str(bill['frequency']),
                    'week_choose': str(bill['day_of_week']),
                    'chooseDay': bill['day_of_month'],
                    'qr_code': bill['qr_code'],
                    'sbl_type': bill['sbl_type'],
                    'status_routing': '1',
                    'description': bill['description'],
                    'name': bill['name'] + '_' + str(datetime.today().year) + '_' + str(
                        datetime.today().month) + '_' + str(datetime.today().day),
                    'from_bill_lading_id': bill['id']
                }
                record = super(BillRouting, self).create(bill_routing)
                if record:
                    routing_query = """
                        select plan.id from sharevan_routing_plan_day plan 
                            join sharevan_bill_lading_detail detail 
                            on plan.bill_lading_detail_id = detail.id
                        where  plan.create_date  > timezone('GMT', current_date) and detail.bill_lading_id = %s
                    """
                    self.env.cr.execute(routing_query, (bill['id'],))
                    list_routing = self._cr.dictfetchall()
                    if list_routing:
                        for rec in list_routing:
                            routing = http.request.env[RoutingPlanDay._name].search(
                                [('id', '=', rec['id'])])
                            routing.write({'bill_routing_id': record['id']})
                    else:
                        raise ValidationError('routing not found')
            delete_string = ''
            for delete_record in update_bill_routing_old:
                query_delete = """
                    delete from  sharevan_bill_routing where id = %s
                """
                self.env.cr.execute(query_delete, (delete_record,))
                delete_string += str(delete_record)
            logger.warn(
                "Delete bill routing record: " + delete_string,
                BillRouting._name, '',
                exc_info=True)
            for company in company_list:
                user_query = """
                    select id from res_users
                        where active = true and company_id = %s
                """
                company['bill_code'] = company['bill_code'][:-1]
                self.env.cr.execute(user_query, (company['company_id'],))
                list_user = self._cr.dictfetchall()
                ids = []
                if list_user:
                    for user in list_user:
                        ids.append(user['id'])
                    if list_user:
                        title = 'New routing play have been scan!'
                        body = 'New routing play have been scan. Please check order! ' \
                               + company['bill_code']
                        item_id = ''
                        try:
                            objct_val = {
                                "title": title,
                                "name": title,
                                "content": body,
                                "create_date": datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S"),
                                "type": 'routing',
                                "image_256": '',
                                "object_status": RoutingDetailStatus.Unconfimred.value,
                                "click_action": ClickActionType.driver_main_activity.value,
                                "message_type": MessageType.success.value,
                                "item_id": item_id,
                                "is_read": False
                            }
                            objct_val = json.dumps(objct_val)
                            click_action = ClickActionType.notification_driver.value
                            message_type = MessageType.success.value
                            item_id = ''
                            INSERT_NOTIFICATION_QUERY = """
                                INSERT INTO public.sharevan_notification( title, content, sent_date, type, 
                                    object_status, click_action, message_type, item_id, create_uid, create_date,status) 
                                VALUES ( 
                                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id """
                            sent_date = datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")
                            http.request.cr.execute(INSERT_NOTIFICATION_QUERY, (
                                title, body, sent_date, 'order', RoutingDetailStatus.Unconfimred.value,
                                ClickActionType.driver_main_activity.value, MessageType.success.value, '', 1,
                                sent_date, 'status',))
                            result = http.request.env[Notification._name]._cr.fetchall()
                            print(result[0][0])
                            if result[0][0]:
                                for id in ids:
                                    INSERT_NOTIFICATION_REL_QUERY = """
                                        INSERT INTO public.sharevan_notification_user_rel(
                                            notification_id, user_id, is_read)
                                            VALUES (%s, %s, %s) RETURNING id 
                                                """
                                    http.request.cr.execute(INSERT_NOTIFICATION_REL_QUERY, (result[0][0], id, False,))
                            FirebaseMessagingAPI. \
                                send_message_for_all_normal(ids=ids, title=title, body=str(objct_val), short_body=body,
                                                            item_id=item_id,
                                                            click_action=click_action, message_type=message_type)
                            return {
                                'status': 200,
                                'message': 'Send notification Successful'
                            }
                        except:
                            logger.warn(
                                "Not send message",
                                RoutingPlanDay._name, item_id,
                                exc_info=True)
                            return {
                                'status': 200,
                                'message': 'Send notification type'
                            }
                    else:
                        logger.warn(
                            "Bill routing create success! send message fail",
                            RoutingPlanDay._name, company['bill_code'],
                            exc_info=True)
                        return {
                            'status': 200,
                            'message': 'Send notification type'
                        }
                else:
                    logger.warn(
                        "Bill routing create success! send message fail because user not found!",
                        RoutingPlanDay._name, company['bill_code'],
                        exc_info=True)
                    return {
                        'status': 200,
                        'message': 'Send notification fail'
                    }
            return {
                'status': 200,
                'message': 'Send notification Successful'
            }
        else:
            logger.warn(
                "Bill of lading not found !",
                exc_info=True)
            return Response(response=str('Bill of lading not found'), status=500)

    def compute_all(self):
        for record in self:
            if record.status_routing == BillRoutingStatus.Waiting.value or record.status_routing == BillRoutingStatus.InClaim.value:
                record.update({'toogle': False})
            else:
                record.update({'toogle': True})

    @api.depends('toogle')
    def cancel_routing_dlp(self):
        if self.trouble_type == RoutingTroubleType.Normal.value:
            code = ''
            routing_plan_day_id = False
            driver_id = False
            routing_query = """
                select id , driver_id,routing_plan_day_code, status, type from sharevan_routing_plan_day 
                    where id in (
                WITH RECURSIVE c AS (
                    SELECT (select plan.id from sharevan_routing_plan_day plan
                        join sharevan_bill_lading_detail detail on detail.id = plan.bill_lading_detail_id
                        where bill_routing_id = %s and detail.warehouse_type = '0'
                           ) AS id
                    UNION ALL
                    SELECT sa.id
                    FROM sharevan_routing_plan_day AS sa
                    JOIN c ON c.id = sa.from_routing_plan_day_id
                    )
                SELECT id FROM c ) order by type
                    """
            self._cr.execute(routing_query, (self.id,))
            rpd = self._cr.dictfetchall()
            if rpd is None or len(rpd) == 0:
                raise ValidationError("No routing found")
            BaseMethod.check_role_access(http.request.env.user, 'sharevan.routing.plan.day',
                                         rpd[0]['id'])
            driver_lst = []
            update_query = """
                update sharevan_routing_plan_day set status = %s ,trouble_type = %s 
                    where id ::integer in (
            """
            for rec in rpd:
                if (rec['type'] == '0'):
                    code = rec['routing_plan_day_code']
                    routing_plan_day_id = rec['id']
                    if rec['status'] == RoutingDetailStatus.Done.value:
                        raise ValidationError('Driver have pick up date export warehouse bill not allow to cancel!')
                driver_id = rec['driver_id']
                update_query += str(rec['id']) + ","
            update_query = update_query[:-1]
            update_query += ")"
            self._cr.execute(update_query,
                             (RoutingDetailStatus.WaitingApprove.value, RoutingTroubleType.WaitingConfirm.value,))
            self.write(
                {
                    'status_routing': BillRoutingStatus.Waiting.value,
                    'trouble_type': RoutingTroubleType.WaitingConfirm.value
                }
            )
            # send message for customer
            users = BaseMethod.get_customer_employee(self.company_id.id, 'all')
            if len(users) > 0:
                try:
                    content = {
                        'title': 'Bill is being check: ' + self.code,
                        'content': 'Bill is being check: ' + self.code + ' by ' + self.env.user.partner_id.name,
                        'type': 'routing',
                        'res_id': routing_plan_day_id,
                        'res_model': 'sharevan.routing.plan.day',
                        'click_action': ClickActionType.routing_plan_day_customer.value,
                        'message_type': MessageType.warning.value,
                        'user_id': users,
                        'item_id': code,
                    }
                    self.env['sharevan.notification'].sudo().create(content)
                except:
                    logger.warn(
                        "Start check Successful! But can not send message for customer",
                        BillRouting._name, self.id,
                        exc_info=True)
            else:
                logger.warn(
                    "Start check Successful! But can not send message for customer",
                    BillRouting._name, self.id,
                    exc_info=True)
            driver_users = []
            routing_query = """
                select user_id from fleet_driver where id =%s
                                """
            self._cr.execute(routing_query, (driver_id,))
            driver = self._cr.dictfetchall()
            if driver:
                driver_users.append(driver[0]['user_id'])
            # send for driver
            if len(driver_users) > 0:
                try:
                    content = {
                        'title': 'Bill is being check: ' + self.code,
                        'content': 'Bill is being check: ' + self.code + ' by ' + self.env.user.partner_id.name,
                        'type': 'routing',
                        'res_id': routing_plan_day_id,
                        'res_model': 'sharevan.routing.plan.day',
                        'click_action': ClickActionType.routing_plan_day_driver.value,
                        'message_type': MessageType.warning.value,
                        'user_id': driver_users,
                        'object_status': ObjectStatus.ReloadRouting.value,
                        'item_id': code,
                    }
                    http.request.env[Notification._name].create(content)
                except:
                    logger.warn(
                        "Start check Successful! But can not send message for driver",
                        BillRouting._name, self.id,
                        exc_info=True)
            vals = {
                'user_id': self.env.uid,
                'routing_plan_day_id': routing_plan_day_id,
                'bill_routing_id': self.id,
                'type': type,
            }
            result = self.env['sharevan.routing.request'].create(vals)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Check bill',
                'view_mode': 'form',
                'res_model': 'sharevan.routing.request',
                'res_id': result.id,
                'target': 'new',
                'context': {
                    'form_view_initial_mode': 'edit',
                },
            }
        elif self.trouble_type == RoutingTroubleType.WaitingConfirm.value:
            result = self.env['sharevan.routing.request'].search([('bill_routing_id', '=', self.id)], limit=1)
            if result:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Check bill',
                    'view_mode': 'form',
                    'res_model': 'sharevan.routing.request',
                    'res_id': result.id,
                    'target': 'new',
                    'context': {
                        'form_view_initial_mode': 'read',
                    },
                }

    def cancel_routing_SO(self, soInfor, access_token):
        so_info = json.loads(soInfor)
        access_token = 'Bearer ' + access_token
        me = AuthSsoApi.get(self, access_token, 'en', "/user/me", None)
        response_data = {}
        bytesThing = str(me, 'utf-8')
        data_json = json.dumps(bytesThing)
        code = ''
        if 'error' not in data_json:
            bill_routing_id = 0
            for id in so_info:
                routing_query = """
                    select id , driver_id,routing_plan_day_code, status, type,bill_routing_id from sharevan_routing_plan_day 
                        where id in (
                    WITH RECURSIVE c AS (
                        SELECT (select distinct plan.id from sharevan_routing_plan_day plan
                            join sharevan_bill_lading_detail detail on detail.id = plan.bill_lading_detail_id
                            join sharevan_bill_lading bill on bill.id = detail.bill_lading_id
                            where qr_code = %s and detail.warehouse_type = '0'
                               ) AS id
                        UNION ALL
                        SELECT sa.id
                        FROM sharevan_routing_plan_day AS sa
                        JOIN c ON c.id = sa.from_routing_plan_day_id
                        )
                    SELECT id FROM c ) order by type
                        """
                self._cr.execute(routing_query, (id,))
                rpd = self._cr.dictfetchall()
                if rpd is None or len(rpd) == 0:
                    response_data = {
                        'sttatus': 500,
                        'message': 'Cancel order fail! Bill not found!'
                    }
                    return Response(json.dumps(response_data), content_type="application/json", status=500)
                time_now = datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")
                driver_lst = []
                code += str(id)
                description = """Mstore employee cancel because not enough quantity package"""
                for rec in rpd:
                    bill_routing_id = rec['bill_routing_id']

                    if (rec['type'] == '0'):
                        if rec['status'] == RoutingDetailStatus.Done.value:
                            raise ValidationError('Driver have pick up date export warehouse bill not allow to cancel!')
                    update_query = """
                        update sharevan_routing_plan_day set status = %s , trouble_type = %s ,accept_time =%s
                            , description = %s where id = %s
                    """
                    self._cr.execute(update_query, (
                        RoutingDetailStatus.Cancel.value, RoutingTroubleType.PickUpFail.value, time_now, description,
                        rec['id'],))
                    if rec['driver_id']:
                        driver_id = rec['driver_id']
                        driver_lst.append(driver_id)
                update_query = """
                    update sharevan_bill_routing set status_routing = %s , trouble_type = %s , description = %s
                        , cancel_check = %s
                        where qr_code = %s
                                """
                self._cr.execute(update_query,
                                 (BillRoutingStatus.Cancel.value, RoutingTroubleType.PickUpFail.value, description,
                                  False,
                                  str(id),))
                driver_users = []
                driver_manager_users = []
                uid = request.session.post_sso_authenticate(config['database'], config['account_admin'])
                request.env['ir.http'].session_info()['uid'] = uid
                request.env['ir.http'].session_info()['login_success'] = True
                request.env['ir.http'].session_info()
                for id in driver_lst:
                    routing_query = """
                        select user_id from fleet_driver where id =%s
                                        """
                    self._cr.execute(routing_query, (id,))
                    driver = self._cr.dictfetchall()
                    if driver:
                        driver_users.append(driver[0]['user_id'])
                        driver_manager = BaseMethod.get_fleet_manager(id)
                        driver_manager_users.append(driver_manager)
                dlp_employee = BaseMethod.get_dlp_employee()
                if len(dlp_employee) > 0:
                    content = {
                        'title': 'Routing cancel for change. ' + code,
                        'content': 'Changing of routing is cancel. Mstore employee have cancel routing !',
                        'type': 'routing',
                        'res_id': bill_routing_id,
                        'res_model': 'sharevan.bill.routing',
                        'click_action': ClickActionType.routing_plan_day_driver.value,
                        'message_type': MessageType.warning.value,
                        'user_id': dlp_employee,
                    }
                    self.env['sharevan.notification'].sudo().create(content)
                    for manager in dlp_employee:
                        notice = "Changing of routing is cancel. Customer have cancel routing !"
                        user = self.env['res.users'].search(
                            [('id', '=', manager)])
                        user.notify_info(message=notice, title=NotificationSocketType.NOTIFICATION.value)
                # send for driver
                try:
                    content = {
                        'title': 'Routing cancel for change. ' + code,
                        'content': 'Changing of routing is cancel. DLP employee have cancel routing !',
                        'type': 'routing',
                        'res_id': id,
                        'res_model': 'sharevan.routing.plan.day',
                        'click_action': ClickActionType.driver_history_activity.value,
                        'message_type': MessageType.warning.value,
                        'user_id': driver_users,
                        'item_id': code,
                    }
                    self.env['sharevan.notification'].sudo().create(content)
                except:
                    logger.warn(
                        "Cancel Successful! But can not send message for customer",
                        BillRouting._name, id,
                        exc_info=True)
                response_data = {
                    'sttatus': 200,
                    'message': 'Cancel order successful'
                }
            return Response(json.dumps(response_data), content_type="application/json", status=200)
        else:
            response_data = {
                'status': 401,
                'message': 'You are not allow'
            }
            return Response(json.dumps(response_data), content_type="application/json", status=401)

    def get_bill_routing_by_day(self, **kwargs):
        offset = 0
        limit = 10
        uID = http.request.env.uid
        param = []
        name = None
        status_routing = None
        date = None
        for arg in kwargs:
            if arg == 'date':
                date = kwargs.get(arg)
            if arg == 'bill_transport_code':
                name = kwargs.get(arg)
            if arg == 'status_routing':
                status_routing = kwargs.get(arg)
            if arg == 'offset':
                offset = kwargs.get(arg)
            if arg == 'limit':
                limit = kwargs.get(arg)
        page = " offset " + str(offset) + " limit " + str(limit)
        query = """
            SELECT distinct bill.id,  bill.total_weight, bill.total_amount, bill.tolls, bill.surcharge, 
                bill.total_volume, bill.vat, bill.promotion_code, release_type, bill.name,bill.code,
                bill.total_parcel, bill.company_id, bill.order_package_id,pack.name package_name ,
                TO_CHAR(bill.start_date, 'YYYY-MM-DD HH24:MI:SS') start_date , 
                TO_CHAR(bill.end_date, 'YYYY-MM-DD HH24:MI:SS') end_date,
                bill.change_bill_lading_detail_id,
                bill.cycle_type, bill.week_choose, bill.qr_code, 
                bill.sbl_type,  bill.status_routing status_routing, bill.description, bill.name, 
                bill.from_bill_lading_id,bill.trouble_type,
                TO_CHAR(bill.create_date, 'YYYY-MM-DD HH24:MI:SS') create_date, bill.code,
                insurance.name insurance_name,insurance.insurance_code,sub.name subscribe_name
                FROM public.sharevan_bill_routing bill
            left join sharevan_insurance  insurance on insurance.id = bill.insurance_id
            join sharevan_routing_plan_day plan on plan.bill_routing_id = bill.id
            left join sharevan_bill_order_package pack on pack.id = bill.order_package_id
            left join sharevan_subscribe sub on sub.id = bill.subscribe_id
            join res_users us on us.company_id = bill.company_id
                where  us.id = %s and bill.start_date = %s
        """
        count_query = """
            SELECT distinct count(bill.id)
                FROM public.sharevan_bill_routing bill
            left join sharevan_insurance  insurance on insurance.id = bill.insurance_id
            left join sharevan_subscribe sub on sub.id = bill.subscribe_id
            left join sharevan_bill_order_package pack on pack.id = bill.order_package_id
            join res_users us on us.company_id = bill.company_id
                where  us.id = %s and bill.start_date = %s
        """
        param.append(uID)
        param.append(date)
        if status_routing == 'all':
            query += " and bill.status_routing ::integer in (-1, 0, 1, 2, 3) "
            count_query += " and bill.status_routing ::integer in (-1, 0, 1, 2, 3) "
        if status_routing == '-1':
            query += " and bill.status_routing ::integer = -1 "
            count_query += " and bill.status_routing ::integer = 0 "
        if status_routing == '0':
            query += " and bill.status_routing ::integer = 0 "
            count_query += " and bill.status_routing ::integer = 0 "
        if status_routing == '1':
            query += " and bill.status_routing ::integer =1 "
            count_query += " and bill.status_routing ::integer =1 "
        if status_routing == '2':
            query += " and bill.status_routing ::integer = 2 "
            count_query += " and bill.status_routing ::integer = 2 "
        if status_routing == '3':
            query += " and bill.status_routing ::integer = 3 "
            count_query += " and bill.status_routing ::integer = 3 "
        if name:
            query += " and  bill.code like %s "
            count_query += " and  bill.code like %s "
            param.append(name)
        query += " order by status_routing " + page
        self.env.cr.execute(count_query, (param))
        count_result = self._cr.dictfetchall()
        if count_result:
            self.env.cr.execute(query, (param))
            result = self._cr.dictfetchall()
            if result:
                jsonRe = []
                for rec in result:
                    routing_query = """
                        select distinct id, address,phone ,warehouse_name ,warehouse_type,status
                            from sharevan_bill_lading_detail 
                        where bill_lading_id = %s and status_order ='running' order by id
                    """
                    self.env.cr.execute(routing_query, (rec['from_bill_lading_id'],))
                    routing_result = self._cr.dictfetchall()
                    if routing_result:
                        rec['arrBillLadingDetail'] = routing_result
                return {
                    'total_record': count_result[0]['count'],
                    'records': result
                }
            else:
                return {
                    'total_record': 0,
                    'records': []
                }
        else:
            return {
                'total_record': 0,
                'records': []
            }

    def get_bill_routing_detail(self, bill_routing_id):
        session, data_json = BaseMethod.check_authorized()
        uid = http.request.env.uid
        if not session and not uid:
            return Response(json.dumps('UN_AUTHORIZED'), content_type="application/json", status=403)
        routing_query = """
            SELECT distinct bill.id,  bill.total_weight, bill.total_amount, bill.tolls, bill.surcharge, 
                bill.total_volume, bill.vat, bill.promotion_code, release_type, bill.name,bill.code,
                bill.total_parcel, bill.company_id, pack.name order_package_name ,
                TO_CHAR(bill.start_date, 'YYYY-MM-DD HH24:MI:SS') start_date , 
                TO_CHAR(bill.end_date, 'YYYY-MM-DD HH24:MI:SS') end_date,
                bill.change_bill_lading_detail_id,
                bill.cycle_type, bill.week_choose, bill.qr_code, bill.trouble_type,
                bill.sbl_type, bill.status_routing status_routing, bill.description, bill.name, 
                bill.from_bill_lading_id,COALESCE(routing_scan,false) routing_scan,
                TO_CHAR(bill.create_date, 'YYYY-MM-DD HH24:MI:SS') create_date, bill.code,
                insurance.name insurance_name,insurance.insurance_code,sub.name subscribe_name
            FROM public.sharevan_bill_routing bill
                left join sharevan_insurance  insurance on insurance.id = bill.insurance_id
                left join sharevan_subscribe sub on sub.id = bill.subscribe_id
                left join sharevan_bill_order_package pack on pack.id = bill.order_package_id
                join res_users us on us.company_id = bill.company_id
            where bill.id = %s
                            """
        self.env.cr.execute(routing_query, (bill_routing_id,))
        routing_result = self._cr.dictfetchall()
        if routing_result:
            routingResult = None
            tracking_lst = []
            routingResult = routing_result[0]
            bill_lading_detail_query = """
                select distinct id, address,phone ,warehouse_name, warehouse_type 
                    from sharevan_bill_lading_detail 
                where bill_lading_id = %s and status_order = 'running' order by id
                                """
            self.env.cr.execute(bill_lading_detail_query, (routingResult['from_bill_lading_id'],))
            bill_lading_detail_result = self._cr.dictfetchall()
            arr_bill_detail = []
            if bill_lading_detail_result:
                jsonListUrl = []
                for rec in bill_lading_detail_result:
                    plan_query = """
                        select plan.id, plan.status ,plan.driver_id,plan.vehicle_id,plan.latitude,
                            plan.longitude,plan.warehouse_name ,plan.from_routing_plan_day_id,plan.ship_type,
                            driver.name driver_name , driver.phone driver_phone,vehicle.license_plate ,
                            vehicle.name vehicle_name,plan.type,plan.claim_type,plan.routing_plan_day_code,
                            TO_CHAR(plan.accept_time, 'YYYY-MM-DD HH24:MI:SS') accept_time
                        from sharevan_routing_plan_day plan
                            left join fleet_driver driver on driver.id = plan.driver_id
                            left join fleet_vehicle vehicle on vehicle.id = plan.vehicle_id
                        where bill_lading_detail_id =%s and bill_routing_id =%s  order by plan.id
                    """
                    self.env.cr.execute(plan_query, (rec['id'], bill_routing_id,))
                    plan_result = self._cr.dictfetchall()
                    if plan_result:
                        success = False
                        rec['routing'] = plan_result
                        for plan in plan_result:
                            if plan['status'] == '2':
                                success = True
                            else:
                                success = False

                            getUrl_query = """
                                SELECT json_agg(t) FROM (
                                    select irc.uri_path from ir_attachment irc
                                        join public.ir_attachment_sharevan_routing_plan_day_rel pi on pi.ir_attachment_id = irc.id
                                        join sharevan_routing_plan_day srpd on pi.sharevan_routing_plan_day_id = srpd.id and srpd.id= %s ) t """
                            self.env.cr.execute(getUrl_query, (plan['id'],))
                            get_list_images_or_attachment_url = self._cr.fetchall()
                            if get_list_images_or_attachment_url:
                                if get_list_images_or_attachment_url[0][0]:
                                    for rec_image in get_list_images_or_attachment_url[0][0]:
                                        jsonListUrl.append(rec_image['uri_path'])
                        if success == True:
                            rec['status'] = '2'
                        else:
                            rec['status'] = '1'
                    else:
                        rec['status'] = '1'
                    package_query = """
                        SELECT package.id, package.quantity_package quantity_package, package.length, package.width, package.height,
                            package.net_weight, package.capacity, package.item_name,  
                            package.name,type.name product_type_name
                            FROM public.sharevan_bill_package package
                        Join sharevan_product_type type on type.id = package.product_type_id
                            where package.bill_lading_detail_id = %s and package.status = 'running' 
                    """
                    self.env.cr.execute(package_query, (rec['id'],))
                    package_result = self._cr.dictfetchall()
                    if package_result:
                        rec['billPackages'] = package_result
                    else:
                        rec['billPackages'] = []
                    rec['image_urls'] = jsonListUrl
                    get_sharevan_bill_lading_detail_sharevan_service_type_rel = """  
                        SELECT json_agg(t) from
                            ( SELECT sharevan_bill_lading_detail_id, sharevan_service_type_id
                                FROM public.sharevan_bill_lading_detail_sharevan_service_type_rel rel 
                                    where rel.sharevan_bill_lading_detail_id = %s ) t  """
                    self.env.cr.execute(get_sharevan_bill_lading_detail_sharevan_service_type_rel,
                                        (rec['id'],))
                    result_service_rel = self._cr.fetchall()

                    result_service_rel_arr = []
                    if result_service_rel[0][0]:
                        for rec1 in result_service_rel[0][0]:
                            get_sharevan_service_type = """ 
                                SELECT json_agg(t) from( 
                                    SELECT id, name, price, vendor_id, service_code, status, description, 
                                        create_uid, TO_CHAR(create_date, 'YYYY-MM-DD HH24:MI:SS') create_date, 
                                        write_uid,TO_CHAR(write_date, 'YYYY-MM-DD HH24:MI:SS') write_date
                                    FROM public.sharevan_service_type service_type where service_type.id = %s ) t """
                            self.env.cr.execute(get_sharevan_service_type, (rec1['sharevan_service_type_id'],))
                            result_get_sharevan_service_type = self._cr.fetchall()
                            result_service_rel_arr.append(result_get_sharevan_service_type[0][0][0])
                    rec['billService'] = result_service_rel_arr
                    arr_bill_detail.append(rec)
                routingResult['tracking_lst'] = tracking_lst
                routingResult['arrBillLadingDetail'] = arr_bill_detail

                return routingResult
        else:
            return {
                'records': []
            }

    def get_bill_routing_detail_by_code(self, pageNumber, pageSize):
        session, data_json = BaseMethod.check_authorized()
        if not session:
            return Response(json.dumps('UN_AUTHORIZED'), content_type="application/json", status=403)
        bill_routing_name = None
        for arg in data_json:
            if arg == 'bill_routing_name' and data_json.get(arg) is not '':
                bill_routing_name = data_json.get(arg)
            else:
                bill_routing_name = 'None'

        if bill_routing_name is not None:
            routing_query = """
                SELECT distinct bill.id,  bill.total_weight, bill.total_amount, bill.tolls, bill.surcharge, 
                    bill.total_volume, bill.vat, bill.promotion_code, release_type, bill.name,bill.code,
                    bill.total_parcel, bill.company_id, pack.name order_package_name ,
                    TO_CHAR(bill.start_date, 'YYYY-MM-DD HH24:MI:SS') start_date , 
                    TO_CHAR(bill.end_date, 'YYYY-MM-DD HH24:MI:SS') end_date,
                    bill.change_bill_lading_detail_id,
                    bill.cycle_type, bill.week_choose, bill.qr_code, bill.trouble_type,
                    bill.sbl_type, bill.status_routing status_routing, bill.description, bill.name, 
                    bill.from_bill_lading_id,COALESCE(routing_scan,false) routing_scan,
                    TO_CHAR(bill.create_date, 'YYYY-MM-DD HH24:MI:SS') create_date, bill.code,
                    insurance.name insurance_name,insurance.insurance_code,sub.name subscribe_name
                FROM public.sharevan_bill_routing bill
                    left join sharevan_insurance  insurance on insurance.id = bill.insurance_id
                    left join sharevan_subscribe sub on sub.id = bill.subscribe_id
                    left join sharevan_bill_order_package pack on pack.id = bill.order_package_id
                    join res_users us on us.company_id = bill.company_id
                where bill.name like '%s'
                                """ % (bill_routing_name)
            offset = str((int(pageNumber) - 1) * int(pageSize))
            limit = pageSize
            routing_query += ' offset ' + str(offset) + ' limit ' + str(limit)

            http.request.env.cr.execute(routing_query, ())
            routing_result = http.request._cr.dictfetchall()
            count_query = """select count(id) from (%s) t """ % routing_query
            http.request.env.cr.execute(count_query, ())
            count = http.request._cr.fetchall()
            if routing_result:
                routingResult = None
                tracking_lst = []
                routingResult = routing_result[0]
                bill_lading_detail_query = """
                    select distinct id, address,phone ,warehouse_name, warehouse_type 
                        from sharevan_bill_lading_detail 
                    where bill_lading_id = %s and status_order = 'running' order by id
                                    """
                http.request.env.cr.execute(bill_lading_detail_query, (routingResult['from_bill_lading_id'],))
                bill_lading_detail_result = http.request._cr.dictfetchall()
                arr_bill_detail = []
                if bill_lading_detail_result:
                    jsonListUrl = []
                    for rec in bill_lading_detail_result:
                        plan_query = """
                            select plan.id, plan.status ,plan.driver_id,plan.vehicle_id,plan.latitude,
                                plan.longitude,plan.warehouse_name ,plan.from_routing_plan_day_id,plan.ship_type,
                                driver.name driver_name , driver.phone driver_phone,vehicle.license_plate ,
                                vehicle.name vehicle_name,plan.type,plan.claim_type,
                                TO_CHAR(plan.accept_time, 'YYYY-MM-DD HH24:MI:SS') accept_time
                            from sharevan_routing_plan_day plan
                                left join fleet_driver driver on driver.id = plan.driver_id
                                left join fleet_vehicle vehicle on vehicle.id = plan.vehicle_id
                            where bill_lading_detail_id =%s and bill_routing_id =%s  order by plan.id
                        """
                        http.request.env.cr.execute(plan_query, (rec['id'], routingResult['from_bill_lading_id'],))
                        plan_result = http.request._cr.dictfetchall()
                        if plan_result:
                            success = False
                            rec['routing'] = plan_result
                            for plan in plan_result:
                                if plan['status'] == '2':
                                    success = True
                                else:
                                    success = False

                                getUrl_query = """
                                    SELECT json_agg(t) FROM (
                                        select irc.uri_path from ir_attachment irc
                                            join public.ir_attachment_sharevan_routing_plan_day_rel pi on pi.ir_attachment_id = irc.id
                                            join sharevan_routing_plan_day srpd on pi.sharevan_routing_plan_day_id = srpd.id and srpd.id= %s ) t """
                                self.env.cr.execute(getUrl_query, (plan['id'],))
                                get_list_images_or_attachment_url = self._cr.fetchall()
                                if get_list_images_or_attachment_url:
                                    if get_list_images_or_attachment_url[0][0]:
                                        for rec_image in get_list_images_or_attachment_url[0][0]:
                                            jsonListUrl.append(rec_image['uri_path'])
                            if success == True:
                                rec['status'] = '2'
                            else:
                                rec['status'] = '1'
                        else:
                            rec['status'] = '1'
                        package_query = """
                            SELECT package.id, package.quantity_package quantity_package, package.length, package.width, package.height,
                                package.net_weight, package.capacity, package.item_name,  
                                package.name,type.name product_type_name
                                FROM public.sharevan_bill_package package
                            Join sharevan_product_type type on type.id = package.product_type_id
                                where package.bill_lading_detail_id = %s and package.status = 'running' 
                        """
                        http.request.env.cr.execute(package_query, (rec['id'],))
                        package_result = http.request._cr.dictfetchall()
                        if package_result:
                            rec['billPackages'] = package_result
                        else:
                            rec['billPackages'] = []
                        rec['image_urls'] = jsonListUrl
                        get_sharevan_bill_lading_detail_sharevan_service_type_rel = """  
                            SELECT json_agg(t) from
                                ( SELECT sharevan_bill_lading_detail_id, sharevan_service_type_id
                                    FROM public.sharevan_bill_lading_detail_sharevan_service_type_rel rel 
                                        where rel.sharevan_bill_lading_detail_id = %s ) t  """
                        http.request.env.cr.execute(get_sharevan_bill_lading_detail_sharevan_service_type_rel,
                                                    (rec['id'],))
                        result_service_rel = http.request._cr.fetchall()

                        result_service_rel_arr = []
                        if result_service_rel[0][0]:
                            for rec1 in result_service_rel[0][0]:
                                get_sharevan_service_type = """ 
                                    SELECT json_agg(t) from( 
                                        SELECT id, name, price, vendor_id, service_code, status, description, 
                                            create_uid, TO_CHAR(create_date, 'YYYY-MM-DD HH24:MI:SS') create_date, 
                                            write_uid,TO_CHAR(write_date, 'YYYY-MM-DD HH24:MI:SS') write_date
                                        FROM public.sharevan_service_type service_type where service_type.id = %s ) t """
                                self.env.cr.execute(get_sharevan_service_type, (rec1['sharevan_service_type_id'],))
                                result_get_sharevan_service_type = self._cr.fetchall()
                                result_service_rel_arr.append(result_get_sharevan_service_type[0][0][0])
                        rec['billService'] = result_service_rel_arr
                        arr_bill_detail.append(rec)
                    routingResult['tracking_lst'] = tracking_lst
                    routingResult['arrBillLadingDetail'] = arr_bill_detail
            result = {
                'totalElements': count,
                'size': int(pageSize),
                'number': int(pageNumber) - 1,
                'content': routing_result
            }
            return Response(json.dumps(result), content_type="application/json", status=200)

    def get_total_resutl_routing_plan(self, **kwargs):
        uID = http.request.env.uid
        param = []
        warehouse_code = None
        for arg in kwargs:
            if arg == 'date':
                date = kwargs.get(arg)
                param.append(date)
            if arg == 'warehouse_code':
                warehouse_code = kwargs.get(arg)
        user = http.request.env.uid
        user_record = http.request.env['res.users'].search([('id', '=', user)])
        # lấy tất cả các kho và depot của khách hàng có tuyến ngày chon
        query = """
            select distinct(srpd.routing_plan_day_code),srpd.id,
                TO_CHAR(srpd.actual_time, 'YYYY-MM-DD HH24:MI:SS')        actual_time,
                TO_CHAR(srpd.expected_from_time, 'YYYY-MM-DD HH24:MI:SS') expected_from_time,
                TO_CHAR(srpd.expected_to_time, 'YYYY-MM-DD HH24:MI:SS')   expected_to_time,
                srpd.warehouse_name,
                srpd.status, srpd.so_type,
                CASE WHEN srpd.status = '4' THEN '-1'
                WHEN srpd.status = '1' THEN '0'
                WHEN srpd.status = '0' THEN '1'
                 ELSE srpd.status END
                 AS status_order,
                COALESCE(srpd.check_point,false) check_point,
                COALESCE(srpd.first_rating_customer,false) first_rating_customer,
                COALESCE(srpd.arrived_check,false) arrived_check,
                part.name booked_employee,
                TO_CHAR(srpd.date_plan, 'YYYY-MM-DD HH24:MI:SS')          date_plan,
                srpd.id routing_plan_day_id,
                srpd.type,srpd.order_number,
                srpd.vehicle_id,
                srpd.qr_gen_check,
                srpd.rating_customer,srpd.change_bill_lading_detail_id,
                veh.license_plate,
                driver.name driver_name,
                driver.phone driver_phone,
                TO_CHAR(srpd.confirm_time, 'YYYY-MM-DD HH24:MI:SS')  confirm_time,
                TO_CHAR(srpd.accept_time, 'YYYY-MM-DD HH24:MI:SS')  accept_time
            from sharevan_routing_plan_day srpd
                join fleet_driver driver on driver.id = srpd.driver_id
                join fleet_vehicle veh on veh.id = srpd.vehicle_id
                join res_partner part on part.id = srpd.partner_id
            where 1 = 1
                and srpd.date_plan = %s
                 """
        if user_record['channel_id'].name == 'customer':
            query += """ and ( srpd.warehouse_id in 
                     ( select distinct(sw.id) id
                        from sharevan_warehouse sw
                    join res_company rsc on rsc.id = sw.company_id
                    join res_users rus on rus.company_id = rsc.id and rus.id = %s 
                        where sw.status = 'running' and srpd.company_id = %s  
                        """
            param.append(uID)
            param.append(user_record['company_id'].id)
            if warehouse_code:
                query += " and sw.warehouse_code = %s "
                param.append(warehouse_code)
            query += """) or srpd.depot_id in 
                        (select distinct(sw.id) id
                            from sharevan_depot sw
                        join res_company rsc on rsc.id = sw.company_id
                        join res_users rus on rus.company_id = rsc.id and rus.id = %s 
                            where sw.status = 'running' """
            param.append(uID)
            if warehouse_code:
                query += " and sw.depot_code = %s "
                param.append(warehouse_code)
            query += """ )) """
        elif user_record['channel_id'].name == 'dlp' and user_record['channel_id'].channel_type == 'manager':
            query += """ and ( srpd.warehouse_id in 
                                 ( select distinct(sw.id) id
                                    from sharevan_warehouse sw
                                    where sw.status = 'running' 
                                    """
            if warehouse_code:
                query += " and sw.warehouse_code = %s "
                param.append(warehouse_code)
            query += """) or srpd.depot_id in 
                                    (select distinct(sw.id) id
                                        from sharevan_depot sw
                                        where sw.status = 'running' """
            if warehouse_code:
                query += " and sw.depot_code = %s "
                param.append(warehouse_code)
            query += """ )) """
        elif user_record['channel_id'].name == 'dlp' and user_record['channel_id'].channel_type == 'employee':
            query += """
                 and srpd.depot_id in ( select place_id from sharevan_employee_warehouse ru
                       WHERE ru.user_id =%s and ru.date_assign = CURRENT_DATE  
            """
            param.append(uID)
            if warehouse_code:
                query += " and sw.depot_code = %s "
                param.append(warehouse_code)
            query += " ) and srpd.warehouse_id is null "
        self.env.cr.execute(query,
                            (param))
        result = self._cr.dictfetchall()
        not_confirm_count = 0
        driver_confirm_count = 0
        customer_confirm_count = 0
        waiting_confirm_count = 0
        cancel_count = 0
        total_count = 0
        if result:
            total_count = len(result)
            for rec in result:
                if rec['status'] == '0':
                    not_confirm_count += 1
                elif rec['status'] == '1':
                    driver_confirm_count += 1
                elif rec['status'] == '2':
                    customer_confirm_count += 1
                elif rec['status'] == '3':
                    waiting_confirm_count += 1
                elif rec['status'] == '4':
                    cancel_count += 1
            return {
                'records': [
                    not_confirm_count
                    ,
                    driver_confirm_count
                    ,
                    customer_confirm_count
                    ,
                    waiting_confirm_count
                    ,
                    cancel_count
                    ,
                    total_count
                ]
            }
        else:
            return {
                'records': [
                    not_confirm_count
                    ,
                    driver_confirm_count
                    ,
                    customer_confirm_count
                    ,
                    waiting_confirm_count
                    ,
                    cancel_count
                    ,
                    total_count
                ]
            }

    def check_routing_update(self, bill_routing_id):
        query = """
            select * from sharevan_routing_plan_day 
                where bill_routing_id = %s and date_plan= CURRENT_DATE and status != '2'
            order by order_number
        """
        self.env.cr.execute(query,
                            (bill_routing_id,))
        result = self._cr.dictfetchall()
        if result:
            record = http.request.env['sharevan.bill.routing'].search([('id', '=', bill_routing_id)])
            if record:
                record.write({'status_routing': BillRoutingStatus.Shipping.value})
            return True
        else:
            record = http.request.env['sharevan.bill.routing'].search([('id', '=', bill_routing_id)])
            if record:
                time_now = datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")
                record.write({'status_routing': BillRoutingStatus.Success.value, 'end_date': time_now})
                return True
            else:
                return True

    def customer_not_found(self, routingPlan, type, time_pay_back, files):
        print(routingPlan, type, time_pay_back)
        logger.warn(
            "Customer_not found info",
            RoutingPlanDay._name, routingPlan,
            exc_info=True)
        routing_plan_day_id = json.loads(routingPlan)
        code = ''
        query = """
            SELECT rpd.id,rpd.type, rpd.warehouse_id, rpd.date_plan ,rpd.driver_id ,rpd.status ,rpd.company_id,rpd.so_type,
                    rpd.latitude,rpd.longitude,rpd.ship_type,rpd.depot_id,rpd.total_volume,rpd.type,rpd.bill_routing_id,
                    veh.latitude vehicle_latitude,veh.longitude vehicle_longitude,rpd.capacity_expected,rpd.vehicle_id,
                    routing.code,routing.id bill_routing_id,rpd.routing_plan_day_code,rpd.routing_vehicle_id
                FROM public.sharevan_routing_plan_day rpd
                    join sharevan_bill_routing routing on routing.id = rpd.bill_routing_id
                    JOIN fleet_vehicle veh on veh.id = rpd.vehicle_id 
                    JOIN fleet_driver driver on driver.id =rpd.driver_id
                WHERE driver.user_id =%s and rpd.id ::integer in (
            """
        for routing in routing_plan_day_id:
            query += str(routing) + ","
        query = query[:-1]
        query += ")"
        http.request.env[RoutingPlanDay._name]._cr.execute(query, (str(http.request.env.uid),))
        record = http.request.env[RoutingPlanDay._name]._cr.dictfetchall()
        vehicle_id = 0
        if record:
            distance_allow = http.request.env['ir.config_parameter'].sudo().get_param(
                'distance.mobile.check.point.key')
            type = ''
            list_so_routing = []
            list_dlp_routing = []
            list_bill_routing_id = []
            list_routing_vehicle_id = []
            item_id = ''
            for rec in record:
                code += rec['code']
                if item_id == '':
                    item_id = rec['routing_plan_day_code']
                list_bill_routing_id.append(rec['bill_routing_id'])
                type = 'SO' if rec['so_type'] == True else 'DLP'
                vehicle_id = rec['vehicle_id']
                coords_1 = (rec['latitude'], rec['longitude'])
                coords_2 = (rec['vehicle_latitude'], rec['vehicle_longitude'])
                distance = geopy.distance.distance(coords_1, coords_2).m
                if int(distance) > int(distance_allow):
                    response_data = {
                        'status': 204,
                        'message': 'You are so far from warehouse'
                    }
                    return Response(json.dumps(response_data), content_type="application/json", status=500)
                if type == 'SO':
                    list_so_routing.append(rec['id'])
                else:
                    list_dlp_routing.append(rec['id'])
                    list_routing_vehicle_id.append(rec['routing_vehicle_id'])
            if len(list_so_routing) > 0:
                try:
                    url = config['security_url'] + config['routing_host'] + ':' + config[
                        'routing_port'] + '/location/assign_routing/nocustomer'
                    payload = {
                        'lstIdRouting': routing_plan_day_id,
                        'type': type
                    }
                    print(payload)
                    payloadjson = json.dumps(payload, default=date_utils.json_default, skipkeys=True)
                    resps = requests.get(url, params=payload,
                                         headers={'Content-Type': 'application/json'}).json()
                except:
                    logger.error("There was problem requesting routing!")
                    response_data = {
                        'status': 500,
                        'message': 'There was problem requesting routing'
                    }
                    return Response(json.dumps(response_data), content_type="application/json", status=500)
                logger.warn(
                    "Customer_not found info routing response",
                    RoutingPlanDay._name, resps,
                    exc_info=True)
                if 'error' in resps:
                    response_data = {
                        'status': 500,
                        'message': 'There was problem requesting routing'
                    }
                    return Response(json.dumps(response_data), content_type="application/json", status=500)
            else:
                update_query = """
                    update sharevan_routing_plan_day 
                        set trouble_type = '5',status = '4' where id::integer in(
                    """
                for id in list_dlp_routing:
                    update_query += str(id) + ","
                update_query = update_query[:-1]
                update_query += ")"
                self._cr.execute(update_query, ())
                update_bill_routing_query = """
                    update sharevan_bill_routing set trouble_type = '5' where id::integer in(
                    """
                for id in list_bill_routing_id:
                    update_bill_routing_query += str(id) + ","
                update_bill_routing_query = update_bill_routing_query[:-1]
                update_bill_routing_query += ")"
                self._cr.execute(update_bill_routing_query, ())

                # thêm vào routing request
                for i in range(len(list_dlp_routing)):
                    vals = {
                        'routing_plan_day_id': list_dlp_routing[i],
                        'bill_routing_id': list_bill_routing_id[i],
                        'routing_vehicle_id': list_routing_vehicle_id[i]
                    }
                    result = self.env['sharevan.routing.request'].create(vals)
            dlp_ids = BaseMethod.get_dlp_employee()
            title = 'Customer not found! Please check bill list'
            body = 'Customer not found! Please check bill list: ' + code
            if len(dlp_ids) > 0:
                item_id = ''
                try:
                    val = {
                        'user_id': dlp_ids,
                        'title': title,
                        'content': body,
                        'res_id': item_id,
                        'res_model': 'sharevan.bill.routing',
                        'click_action': ClickActionType.bill_routing_detail.value,
                        'message_type': MessageType.danger.value,
                        'type': NotificationType.RoutingMessage.value,
                        'object_status': RoutingDetailStatus.Done.value,
                        'item_id': item_id,
                    }
                    http.request.env[Notification._name].create(val)
                    notice = body
                    print(len(dlp_ids))
                    for user in dlp_ids:
                        users = http.request.env['res.users'].search(
                            [('id', '=', user)])
                        users.notify_info(message=notice, title=NotificationSocketType.NOTIFICATION.value)
                except:
                    logger.warn(
                        "Scan Successful! But can not send message",
                        RoutingPlanDay._name, vehicle_id,
                        exc_info=True)

            try:
                val = {
                    'user_id': [self.env.uid],
                    'title': title,
                    'content': body,
                    'click_action': ClickActionType.routing_plan_day_driver.value,
                    'message_type': MessageType.success.value,
                    'type': NotificationType.RoutingMessage.value,
                    'object_status': ObjectStatus.ReloadRouting.value,
                    'item_id': item_id,
                }
                http.request.env['sharevan.notification'].create(val)
            except:
                logger.warn(
                    "Scan Successful! But can not send message",
                    RoutingPlanDay._name, vehicle_id,
                    exc_info=True)

            for file in files:
                if file.filename:

                    val = {
                        'res_model': 'sharevan.routing.plan.day',
                        'mimetype': file.mimetype,
                        'name': file.filename,
                        'res_id': routing_plan_day_id[0],
                        'status': 'running',
                        'type': 'binary',
                        'datas': base64.b64encode(file.read())
                    }
                    rec = http.request.env['ir.attachment'].create(val)
                    for routing in routing_plan_day_id:
                        http.request.cr.execute(INSERT_QUERY, (routing, rec['id'],))
            response_data = {
                'status': 200,
                'message': 'Success'
            }
            return Response(json.dumps(response_data), content_type="application/json", status=200)
        else:
            response_data = {
                'status': 500,
                'message': 'Routing not found'
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
