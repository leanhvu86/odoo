# -*- coding: utf-8 -*-
import logging
from datetime import datetime

import pytz

from mymodule.base_next.controllers.api.base_method import BaseMethod
from mymodule.base_next.controllers.api.firebase_messaging import FirebaseMessagingAPI
from mymodule.base_next.models.routing_plan_day import RoutingPlanDay
from mymodule.enum.ClickActionType import ClickActionType
from mymodule.enum.MessageType import MessageType
from mymodule.enum.NotificationType import NotificationType
from mymodule.enum.ObjectStatus import ObjectStatus
from mymodule.enum.RoutingDetailStatus import RoutingDetailStatus
from odoo import fields, models, api, _, http
import json
from odoo import api, models, fields, _
from odoo import models, _, http
from odoo.exceptions import ValidationError
import json as simplejson
# from mymodule.biding_order.models.base import Base
from datetime import datetime
import logging
from operator import itemgetter

from odoo.http import Response
from odoo.tools import config

logger = logging.getLogger(__name__)


class NotificationUser(models.Model):
    _name = 'sharevan.notification.user.rel'
    _description = 'Show the individual receiver and if they have read or not'

    notification_id = fields.Many2one('sharevan.notification', string="Notification")
    user_id = fields.Many2one('res.users', string='Receiver')
    is_read = fields.Boolean(string='Check if user have read notification or not', default=False)
    title = fields.Char(string='Title', related='notification_id.title')
    name = fields.Char(related='title', string='Name', store=False)
    content = fields.Char(string='Content', related='notification_id.content')
    res_id = fields.Integer('New Value Integer', readonly=1)
    type = fields.Selection(related='notification_id.type')
    click_action = fields.Char(related='notification_id.click_action')

    def get_notification_web(self):
        bill_state = None
        session, data_json = BaseMethod.check_authorized()
        if not session:
            return Response(json.dumps('UN_AUTHORIZED'), content_type="application/json", status=403)
        user_id = session['uid']
        domain = [['user_id', '=', user_id]]
        offset = '0'
        limit = '10'
        param = []
        param.append(user_id)
        n_type = None
        id = None
        offset = data_json['offset']
        limit = data_json['limit']
        if 'type' in data_json:
            n_type = data_json['type']
            param.append(data_json['type'])
            domain.append(['type', '=', n_type])
        if 'id' in data_json:
            id = data_json['id']
            param.append(data_json['id'])
            domain.append(['id', '=', id])

        query = """
                    SELECT json_agg(t)
                        FROM (
                    SELECT user_mess.id, user_mess.notification_id, COALESCE(user_mess.is_read, FALSE) is_read,
                        noti.create_uid, 
                        TO_CHAR(noti.create_date, 'YYYY-MM-DD HH24:MI:SS') create_date,
                        TO_CHAR(noti.sent_date, 'YYYY-MM-DD HH24:MI:SS') sent_date,
                        noti.title, noti.content,noti.type, 
                        noti.click_action, noti.message_type, noti.item_id, 
                        noti.object_status, att.uri_path image_256, noti.description,partner.name
                    FROM public.sharevan_notification_user_rel  user_mess
                        join public.sharevan_notification noti on noti.id = user_mess.notification_id
                        left join res_users us on us.id = noti.create_uid 
                        left join res_partner partner on partner.id = us.partner_id
                        left join ir_attachment att on att.res_id = noti.id 
                            and att.res_model = 'sharevan.notification' 
                            and att.res_field = 'image_256' 
                    WHERE 1 = 1 and
                        user_mess.user_id = %s 
                """
        if n_type:
            query += """ and noti.type = %s  """
        if id:
            query += """ and noti.id = %s  """
        query += """ order by id DESC """
        page = ' offset ' + str(offset)
        page += ' limit ' + str(limit) + ' )t '
        query += page
        self.env.cr.execute(query, (param))
        result = self._cr.fetchall()
        count_query = """
            SELECT count(user_mess.id)
                FROM public.sharevan_notification_user_rel  user_mess
            WHERE 1 = 1 and
                user_mess.user_id = %s 
        """
        self.env.cr.execute(count_query, (user_id,))
        count_result = self._cr.dictfetchall()
        records = []
        if len(result):
            if result[0][0]:
                for rec in result[0][0]:
                    if id:
                        if 'description' in rec and rec['description']:
                            start = 0
                            end = 0
                            for i, _ in enumerate(rec['description']):
                                if rec['description'][i:i + len('src=\"/web/image/')] == 'src=\"/web/image/':
                                    start = i
                                if rec['description'][i:i + len('\">')] == '\">' and start != 0:
                                    end = i
                                    image_url = rec['description'][int(start):int(end)]
                                    array_temp = image_url.split('/')
                                    id = array_temp[3]
                                    image_query = """
                                                select uri_path from ir_attachment where id = %s
                                            """
                                    self.env.cr.execute(image_query, (id,))
                                    image = self._cr.dictfetchall()
                                    # To do  http type config
                                    if image[0] and 'uri_path' in image[0]:
                                        new_url = 'src=\"' + 'http://' + image[0]['uri_path'] + '\"'
                                        rec['description'] = rec['description'][:start] + new_url + rec['description'][
                                                                                                    end + 1:]
                                    start = 0
                            records.append(rec)
                        else:
                            records.append(rec)
                    else:
                        rec.pop('description')
                        records.append(rec)
        records.sort(key=itemgetter("id"), reverse=True)

        response = {
            'length': len(records),
            'total_record': count_result[0]['count'],
            'records': records
        }
        return Response(json.dumps(response), content_type="application/json", status=200)

    def get_notification_all(self, **kwargs):
        user_id = http.request.session['uid']
        domain = [['user_id', '=', user_id]]
        offset = '0'
        limit = '10'
        param = []
        param.append(user_id)
        n_type = None
        id = None
        if 'offset' in kwargs:
            offset = (kwargs.get('offset'))
        if 'type' in kwargs:
            n_type = kwargs.get('type')
            param.append(kwargs.get('type'))
            domain.append(['type', '=', n_type])
        if 'id' in kwargs:
            id = kwargs.get('id')
            param.append(kwargs.get('id'))
            domain.append(['id', '=', id])

        query = """
            SELECT json_agg(t)
                FROM (
            SELECT user_mess.id, user_mess.notification_id, COALESCE(user_mess.is_read, FALSE) is_read,
                noti.create_uid, 
                TO_CHAR(noti.create_date, 'YYYY-MM-DD HH24:MI:SS') create_date,
                TO_CHAR(noti.sent_date, 'YYYY-MM-DD HH24:MI:SS') sent_date,
                noti.title, noti.content,noti.type, 
                noti.click_action, noti.message_type, noti.item_id, 
                noti.object_status, att.uri_path image_256, noti.description
            FROM public.sharevan_notification_user_rel  user_mess
                join public.sharevan_notification noti on noti.id = user_mess.notification_id
                left join ir_attachment att on att.res_id = noti.id 
                    and att.res_model = 'sharevan.notification' 
                    and att.res_field = 'image_256' 
            WHERE 1 = 1 and
                user_mess.user_id = %s 
        """
        if n_type:
            query += """ and noti.type = %s  """
        if id:
            query += """ and noti.id = %s  """
        query += """ order by id DESC """
        page = ' offset ' + str(offset)
        page += ' limit ' + str(limit) + ' )t '
        query += page
        self.env.cr.execute(query, (param))
        result = self._cr.fetchall()
        records = []
        if len(result):
            if result[0][0]:
                for rec in result[0][0]:
                    if id:
                        if 'description' in rec and rec['description']:
                            start = 0
                            end = 0
                            for i, _ in enumerate(rec['description']):
                                if rec['description'][i:i + len('src=\"/web/image/')] == 'src=\"/web/image/':
                                    start = i
                                if rec['description'][i:i + len('\">')] == '\">' and start != 0:
                                    end = i
                                    image_url = rec['description'][int(start):int(end)]
                                    array_temp = image_url.split('/')
                                    id = array_temp[3]
                                    image_query = """
                                        select uri_path from ir_attachment where id = %s
                                    """
                                    self.env.cr.execute(image_query, (id,))
                                    image = self._cr.dictfetchall()
                                    # To do  http type config
                                    if image[0] and 'uri_path' in image[0]:
                                        new_url = 'src=\"' + 'http://' + image[0]['uri_path'] + '\"'
                                        rec['description'] = rec['description'][:start] + new_url + rec['description'][
                                                                                                    end + 1:]
                                    start = 0
                            records.append(rec)
                        else:
                            records.append(rec)
                    else:
                        rec.pop('description')
                        records.append(rec)
        records.sort(key=itemgetter("id"), reverse=True)
        count = http.request.env[NotificationUser._name]. \
            search_count(domain)
        return {
            'length': len(records),
            'total_record': count,
            'records': records
        }

    def notification_outdate_license(self, list_driver, secret_key):
        if secret_key == config['client_secret']:
            query = """select user_id, (expires_date - current_date) num_outdate from fleet_driver driver
                        where driver.id ::integer in("""
            for id in list_driver:
                query += str(id) + ","
            query = query[:-1]
            query += ")"
            self.env.cr.execute(query, ())
            list_user = self._cr.dictfetchall()
            ids = []
            for id in list_user:
                ids.append(id['user_id'])
            title = 'Your Driver License is on expired time!'
            body = 'Your Driver license is on expired time! Please update it!!!'
            item_id = ''
            try:
                objct_val = {
                    "title": title,
                    "name": title,
                    "content": body,
                    "create_date": datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S"),
                    "type": 'system',
                    "image_256": '',
                    "object_status": RoutingDetailStatus.Unconfimred.value,
                    "click_action": '',
                    "message_type": MessageType.warning.value,
                    "item_id": item_id,
                    "is_read": False
                }
                objct_val = json.dumps(objct_val)
                click_action = ClickActionType.driver_main_activity.value
                message_type = MessageType.success.value
                item_id = ''
                INSERT_NOTIFICATION_QUERY = """INSERT INTO public.sharevan_notification( title, content, sent_date, type, 
                                object_status, click_action, message_type, item_id, create_uid, create_date,status) VALUES ( 
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s) RETURNING id """
                sent_date = datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")
                http.request.cr.execute(INSERT_NOTIFICATION_QUERY, (
                    title, body, sent_date, 'routing', RoutingDetailStatus.Unconfimred.value,
                    ClickActionType.driver_main_activity.value, MessageType.success.value, '', 1, sent_date, 'status',))
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
                return 200

            except:
                logger.warn(
                    "Not send message",
                    RoutingPlanDay._name, '',
                    exc_info=True)
                return 500

    def notification_routing(self, list_driver, secret_key):
        if secret_key == config['client_secret']:
            query = """
                select user_id from fleet_driver driver
                    where driver.id ::integer in (
            """
            for id in list_driver:
                query += str(id) + ","
            query = query[:-1]
            query += ")"
            self.env.cr.execute(query, ())
            list_user = self._cr.dictfetchall()
            ids = []
            for id in list_user:
                ids.append(id['user_id'])
            title = 'You have been assigned a new routing already!'
            body = 'You have been assigned a new routing already! Please check app! '
            item_id = ''
            try:
                objct_val = {
                    "title": title,
                    "name": title,
                    "content": body,
                    "create_date": datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S"),
                    "type": 'routing',
                    "image_256": '',
                    "object_status": ObjectStatus.ReloadRouting.value,
                    "click_action": ClickActionType.driver_main_activity.value,
                    "message_type": MessageType.success.value,
                    "item_id": item_id,
                    "is_read": False
                }
                objct_val = json.dumps(objct_val)
                click_action = ClickActionType.notification_driver.value
                message_type = MessageType.success.value
                item_id = ''
                INSERT_NOTIFICATION_QUERY = """INSERT INTO public.sharevan_notification( title, content, sent_date, type, 
                object_status, click_action, message_type, item_id, create_uid, create_date,status) VALUES ( 
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s) RETURNING id """
                sent_date = datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")
                http.request.cr.execute(INSERT_NOTIFICATION_QUERY, (
                    title, body, sent_date, 'routing', ObjectStatus.ReloadRouting.value,
                    ClickActionType.driver_main_activity.value, MessageType.success.value, '', 1, sent_date, 'status',))
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
                return 200
            except:
                logger.warn(
                    "Not send message",
                    RoutingPlanDay._name, item_id,
                    exc_info=True)
                return 500
        else:
            logger.warn(
                "Not send message because wrong client secret",
                RoutingPlanDay._name, '',
                exc_info=True)
            return 500

    def notification_drivers(self, vehicle):
        query = """
                select user_id from fleet_driver driver
                    where driver.id = (select distinct driver_id 
                from sharevan_routing_plan_day where date_plan = current_date and vehicle_id = %s)
            """ % vehicle
        self.env.cr.execute(query, ())
        list_user = self._cr.dictfetchall()
        ids = []
        for id in list_user:
            ids.append(id['user_id'])
        title = 'Warning: Overspeed!'
        body = 'You have exceeded the speed limit!! The allowed speed is 30km/h'
        item_id = ''
        try:
            objct_val = {
                "title": title,
                "name": title,
                "content": body,
                "create_date": datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S"),
                "type": 'routing',
                "image_256": '',
                "object_status": ObjectStatus.ManagerApprovedCar.value,
                "click_action": ClickActionType.share_van_inbox_driver.value,
                "message_type": MessageType.danger.value,
                "item_id": item_id,
                "is_read": False
            }
            objct_val = json.dumps(objct_val)
            click_action = ClickActionType.notification_driver.value
            message_type = MessageType.success.value
            item_id = ''
            INSERT_NOTIFICATION_QUERY = """INSERT INTO public.sharevan_notification( title, content, sent_date, type,
                object_status, click_action, message_type, item_id, create_uid, create_date,status) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s) RETURNING id """
            sent_date = datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")
            http.request.cr.execute(INSERT_NOTIFICATION_QUERY, (
                title, body, sent_date, 'Driver', RoutingDetailStatus.Unconfimred.value,
                ClickActionType.driver_main_activity.value, MessageType.success.value, '', 1, sent_date, 'new',))
            result = http.request.env[Notification._name]._cr.fetchall()
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
            return 200
        except:
            logger.warn(
                "Not send message",
                RoutingPlanDay._name, item_id,
                exc_info=True)
            return 500


class Notification(models.Model):
    _name = 'sharevan.notification'
    _description = 'Notification send to users'

    user_id = fields.Many2many('res.users', 'sharevan_notification_user_rel', 'notification_id', 'user_id',
                               'User', domain=lambda self: [('active', '=', True)], required=True)

    title = fields.Char(string='Title', required=True)
    name = fields.Char(related='title', string='Name', store=False)
    content = fields.Char(string='Content', required=True)
    notification_type = fields.Many2one('sharevan.notification.type', 'Notification type')
    sent_date = fields.Datetime(string='Sent time', default=datetime.today())
    type = fields.Selection([('routing', 'Routing Message'),
                             ('order', 'Order Message'),
                             ('bidding_order', 'Order Message'),
                             ('bidding_company', 'Company Message'),
                             ('bidding_vehicle', 'Vehicle Message'),
                             ('sos', 'Sos Message'),
                             ('system', 'System Message')],
                            'Message Type', help='Message Type', default="system", required=True)
    company_id = fields.Many2one('res.company', 'Company', index=True, readonly=True,
                                 default=lambda self: self.env.company.id)
    object_status = fields.Char(default='running')
    res_id = fields.Integer(string='Res id')
    res_model = fields.Char(string='Res model')
    status = fields.Selection([('new', 'New'),
                               ('watched', 'Watched'),
                               ('deleted', 'Deleted')
                               ],
                              'Status', help='Status', default="new", required=True)
    click_action = fields.Char(default='')
    message_type = fields.Char(default='success')
    item_id = fields.Char(default=' ')
    click_action_type = fields.Selection(
        [('com.ts.sharevandriver.TARGET_NOTIFICATION_SYSTEM', 'Driver'),
         ('com.nextsolutions.sharevancustomer.TARGET_NOTIFICATION_SYSTEM', 'Customer')],
        'Click Action Type', default='com.nextsolutions.sharevancustomer.TARGET_NOTIFICATION_SYSTEM',
        required=True, store=False)
    image_256 = fields.Image("Image massage", max_width=256, max_height=256)
    description = fields.Html('Body', default=' ')

    @api.onchange('click_action_type')
    def _onchange_click_action_type(self):
        for record in self:
            record.update({'user_id': False})
            if record.click_action_type == 'com.nextsolutions.sharevancustomer.TARGET_NOTIFICATION_SYSTEM':
                domain = [('channel_id.channel_code', '=', 'CUSTOMER')]
                return {'domain': {'user_id': domain}}
            elif record.click_action_type == 'com.ts.sharevandriver.TARGET_NOTIFICATION_SYSTEM':
                domain = [('channel_id.channel_code', '=', 'DRIVER')]
                return {'domain': {'user_id': domain}}

    @api.model
    def create(self, vals):
        if 'click_action' not in vals or vals['click_action'] == '':
            vals['click_action'] = vals['click_action_type']
        vals['sent_date'] = datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")
        new_obj = super(Notification, self).create(vals)
        # TO DO
        # ids = new_obj.ids tại sao lại thay đổi thông số gửi tin nhắn hệ thống thế này
        ids = new_obj['user_id'].ids
        title = new_obj.title
        body = new_obj.content
        image_256 = ''
        image = http.request.env['ir.attachment'].search(
            [('res_id', '=', new_obj['id']), ('res_model', '=', 'sharevan.notification')])
        if image:
            image_256 = image['uri_path']
        val = {
            "title": new_obj.title,
            "id": new_obj.id,
            "name": new_obj.name,
            "content": new_obj.content,
            "create_date": datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S"),
            "type": new_obj.type,
            "image_256": image_256,
            "object_status": new_obj.object_status,
            "click_action": vals['click_action'],
            "message_type": new_obj.message_type,
            "item_id": new_obj.item_id,
            "is_read": False
        }
        val = json.dumps(val)
        click_action = ClickActionType.notification_driver.value
        message_type = MessageType.success.value
        item_id = ''
        if 'click_action' in vals:
            click_action = vals['click_action']
        if 'message_type' in vals:
            message_type = vals['message_type']
        if 'item_id' in vals:
            item_id = vals['item_id']
        else:
            item_id = new_obj['id']
            new_obj.write({'item_id': new_obj['id']})

        # query = """ INSERT INTO public.sharevan_bidding_order_sharevan_bidding_vehicle_rel(notification_id, sharevan_bidding_vehicle_id) VALUES(%s, %s)"""
        # self.env.cr.execute(query, (bidding_order_id, re,))
        FirebaseMessagingAPI. \
            send_message_for_all_normal(ids=ids, title=title, body=str(val), short_body=new_obj.content,
                                        item_id=item_id,
                                        click_action=click_action, message_type=message_type)
        return new_obj

    def unlink(self):
        for id in self.ids:
            record = self.env['sharevan.notification'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })
        return self

    def create_only(self, vals):
        return super(Notification, self).create(vals)

    @api.onchange('click_action_type')
    def onchange_click_action_type(self):
        for record in self:
            if record['click_action_type']:
                record.update({'click_action': record['click_action_type']})

    def check_user_read_message(self):
        params = []
        total_message_not_seen = 0
        user = self.env['res.users'].search([('id', '=', self.env.uid)])
        if user:
            user_id = user.id
            query_get_user_noti = """ SELECT json_agg(t)
                                    FROM (  SELECT count(*)
                                    FROM public.sharevan_notification_user_rel  user_mess
                                    join public.sharevan_notification noti on noti.id = user_mess.notification_id
                                    where user_mess.is_read = False and user_mess.user_id = %s ) t """
            params.append(user_id)
            self.env.cr.execute(query_get_user_noti, params)
            result = self._cr.fetchall()
            if result[0][0]:
                for rec in result[0][0]:
                    total_message_not_seen = rec['count']
            val = {'total_message_not_seen': total_message_not_seen}
            json_arr = []
            json_arr.append(val)

            records = {
                'length': len(result),
                'records': json_arr
            }
            simplejson.dumps(records, indent=4, sort_keys=True, default=str)
            return records
        else:
            raise ValidationError(_('User does not existed!'))

    def accept_firebase_notification(self, accept_firebase):
        user = self.env['res.users'].search([('id', '=', self.env.uid)])
        bool_val = False
        if user:
            if accept_firebase == '1':
                bool_val = True
            http.request.env['res.users']. \
                browse(user.id).write(
                {'accept_firebase_notification': bool_val})
            return True
        else:
            raise ValidationError(_('User does not existed!'))


class NotificationChannel(models.Model):
    _name = 'sharevan.channel'
    _description = 'Sharevan channel'
    _inherit = 'sharevan.channel'

    @api.model
    def create(self, vals):
        if vals['name'] == 'fleet' and vals['channel_type'] == 'manager':
            vals['channel_code'] = 'FLEET_MANAGER'
        elif vals['name'] == 'fleet' and vals['channel_type'] == 'employee':
            vals['channel_code'] = 'DRIVER'
        elif vals['name'] == 'customer':
            vals['channel_code'] = 'CUSTOMER'
        elif vals['name'] == 'dlp':
            vals['channel_code'] = 'ADMINISTRATOR'
        result = super(NotificationChannel, self).create(vals)
        return result

    def write(self, vals):
        name = self.name
        channel_type = self.channel_type
        change_role = False
        if 'name' in vals:
            name = vals['name']
            change_role = True
        if 'channel_type' in vals:
            channel_type = vals['channel_type']
            change_role = True
        if change_role:
            if name == 'fleet' and channel_type == 'manager':
                vals['channel_code'] = 'FLEET_MANAGER'
            elif name == 'fleet' and channel_type == 'employee':
                vals['channel_code'] = 'DRIVER'
            elif name == 'customer':
                vals['channel_code'] = 'CUSTOMER'
            elif name == 'dlp':
                vals['channel_code'] = 'ADMINISTRATOR'
        result = super(NotificationChannel, self).write(vals)
        return result


class SosRegisterDriver(models.Model):
    _name = 'sharevan.driver.sos'
    _description = 'Driver sos register'
    code = fields.Char(name='code')
    name = fields.Char('Named', related='warning_type_id.name', store=False)
    driver_id = fields.Many2one('fleet.driver', 'Driver', required=True)
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle id', required=True)
    routing_plan_day_id = fields.Many2one('sharevan.routing.plan.day', 'Routing Plan Day')
    routing_plan_day_name = fields.Char('Routing Plan Day', related="routing_plan_day_id.routing_plan_day_code")
    warning_type_id = fields.Many2one('sharevan.warning.type', string='Warning type', required=True)
    status = fields.Selection([('running', 'Running'), ('deleted', 'Deleted')], string='Status',
                              default='running', required=True)
    note = fields.Text(string='Description')
    attach_image = fields.Many2many('ir.attachment', string="Attach Image")
    latitude = fields.Float('Latitude', digits=(16, 5))
    longitude = fields.Float('Longitude', digits=(16, 5))
    date_plan = fields.Date()
    routing_plan_day_ids = fields.One2many('sharevan.routing.plan.day', 'driver_sos_id', string='List routing',
                                           domain=[('status', 'in', ['0', '1', '2', '5'])])
    # position_sos = fields.Many2one('sharevan.routing.plan.day', 'Routing Plan Day', store= False)


class NotificationType(models.Model):
    _name = 'sharevan.notification.type'
    _description = 'Notification type'

    name = fields.Char(string='Name', required=True)
    status = fields.Selection([('running', 'Running'), ('deleted', 'Deleted')], string='Status',
                              default='running', required=True)
    image_256 = fields.Image("Image massage", max_width=256, max_height=256)

    def unlink(self):
        for id in self.ids:
            record = self.env['sharevan.notification.type'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })
        return self
