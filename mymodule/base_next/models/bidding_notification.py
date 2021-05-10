# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from mymodule.base_next.controllers.api.firebase_messaging import FirebaseMessagingAPI
from mymodule.enum.ClickActionType import ClickActionType
from mymodule.enum.MessageType import MessageType
from odoo import fields, models, api, _, http

logger = logging.getLogger(__name__)


class NotificationBiddingUser(models.Model):
    _name = 'bidding.notification.user.rel'
    _description = 'Show the individual receiver and if they have read or not'

    bidding_notification_id = fields.Many2one('bidding.notification', string="Notification")
    bidding_user_id = fields.Many2one('res.users', string='Receiver')
    is_read = fields.Boolean(string='Check if user have read notification or not', default=False)
    title = fields.Char(string='Title', related='bidding_notification_id.title')
    name = fields.Char(related='title', store=False)
    content = fields.Char(string='Content', related='bidding_notification_id.content')
    type = fields.Selection(related='bidding_notification_id.type')
    click_action = fields.Char(related='bidding_notification_id.click_action')

    def get_notification_all(self, **kwargs):
        user_id = http.request.session['uid']
        domain = [['bidding_user_id', '=', user_id]]
        offset = '0'
        limit = '10'
        param = []
        param.append(user_id)
        n_type = None
        if 'offset' in kwargs:
            offset = (kwargs.get('offset'))
        if 'type' in kwargs:
            n_type = kwargs.get('type')
            param.append(kwargs.get('type'))
            domain.append(['type', '=', n_type])
        query = """
            SELECT json_agg(t)
                FROM (
            SELECT rel.id, rel.bidding_notification_id, COALESCE(rel.is_read, FALSE) is_read,bidding_notification.id bidding_order_id, bidding_notification.title, bidding_notification.content, bidding_notification.sent_date, bidding_notification.type, bidding_notification.object_status, bidding_notification.click_action,
                   bidding_notification.message_type, bidding_notification.item_id, bidding_notification.description,bidding_notification.create_date,
                   ir.store_fname image_256
                   FROM public.bidding_notification bidding_notification
                   JOIN bidding_notification_user_rel rel on rel.bidding_notification_id = bidding_notification.id
                   LEFT JOIN ir_attachment ir on ir.res_id = bidding_notification.id  and ir.res_model = 'bidding.notification' 
                   where 1=1 and   rel.bidding_user_id = %s
        """
        if n_type:
            query += """ and bidding_notification.type = %s """
        page = ' offset ' + str(offset)
        page += ' limit ' + str(limit) + ' )t '
        query += page
        self.env.cr.execute(query, (param))
        result = self._cr.fetchall()
        records = []
        if len(result):
            if result[0][0]:
                records = result[0][0]

        count  = 0
        result = http.request.env[NotificationBiddingUser._name]. \
            search_count(domain)
        if result is not None:
            count = result
        return {
            'length': len(records),
            'total_record': count,
            'records': records
        }


class BiddingNotification(models.Model):
    _name = 'bidding.notification'
    _description = 'Notification send to users'

    user_id = fields.Many2many('res.users', 'bidding_notification_user_rel', 'bidding_notification_id', 'bidding_user_id',
                               'User', required=True)
    title = fields.Char(string='Title', required=True)
    name = fields.Char(related='title', store=False)
    content = fields.Char(string='Content', required=True)
    sent_date = fields.Datetime(string='Sent time', default=datetime.today())
    type = fields.Selection([('routing', 'Routing Message'),
                             ('order', 'Order Message'),
                             ('bidding_order', 'Order Message'),
                             ('system', 'System Message')],
                             'Message Type', help='Message Type', default="system", required=True)
    object_status = fields.Char(default='running')
    click_action = fields.Char(default='')
    message_type = fields.Char(default='success')
    item_id = fields.Char(default=' ')
    image_256 = fields.Image("Image massage", max_width=256, max_height=256)
    description = fields.Html('body', default=' ')

    @api.model
    def create(self, vals):
        new_obj = super(BiddingNotification, self).create(vals)
        ids = [106]
        title = new_obj.title
        body = new_obj.content
        click_action = ClickActionType.driver_confirm_order.value
        message_type = MessageType.success.value
        item_id = ''
        if 'click_action' in vals:
            click_action = vals['click_action']
        if 'message_type' in vals:
            message_type = vals['message_type']
        if 'item_id' in vals:
            item_id = vals['item_id']
        FirebaseMessagingAPI. \
            send_message_for_all_normal(ids=ids, title=title, body=body, item_id=item_id,
                                        click_action=click_action, message_type=message_type)
        return new_obj

    def create_only(self, vals):
        return super(BiddingNotification, self).create(vals)


class NotificationBiddingChannel(models.Model):
    _name = 'bidding.channel'
    _description = 'bidding channel'

    name = fields.Char('Name', required=True)
    channel_code = fields.Char(string='Channel Reference', required=True, copy=False, readonly=True, index=True,
                               default=lambda self: _('New'))
    description = fields.Text(string='Description')
    status = fields.Selection([('running', 'Running'), ('deleted', 'Deleted')], string='Status',
                              default='running', required=True)


    def create(self, vals):
        if vals.get('channel_code', 'New') == 'New':
            vals['channel_code'] = self.env['ir.sequence'].next_by_code('self.bidding.notification.channel') or 'New'
        result = super(NotificationBiddingChannel, self).create(vals)
        return result



