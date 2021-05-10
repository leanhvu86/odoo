# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
import pytz
import math
import humanize
from odoo import _, api, exceptions, fields, models, modules,http
from odoo.addons.base.models.res_users import is_selection_groups


class Users(models.Model):
    """ Update of res.users class
        - add a preference about sending emails about notifications
        - make a new user follow itself
        - add a welcome message
        - add suggestion preference
        - if adding groups to a user, check mail.channels linked to this user
          group, and the user. This is done by overriding the write method.
    """
    _name = 'res.users'
    _inherit = ['res.users']
    _description = 'Users'

    alias_id = fields.Many2one('mail.alias', 'Alias', ondelete="set null", required=False,
            help="Email address internally associated with this user. Incoming "\
                 "emails will appear in the user's notifications.", copy=False, auto_join=True)
    alias_contact = fields.Selection([
        ('everyone', 'Everyone'),
        ('partners', 'Authenticated Partners'),
        ('followers', 'Followers only')], string='Alias Contact Security', related='alias_id.alias_contact', readonly=False)
    notification_type = fields.Selection([
        ('email', 'Handle by Emails'),
        ('inbox', 'Handle in Odoo')],
        'Notification', required=True, default='email',
        help="Policy on how to handle Chatter notifications:\n"
             "- Handle by Emails: notifications are sent to your email address\n"
             "- Handle in Odoo: notifications appear in your Odoo Inbox")
    # channel-specific: moderation
    is_moderator = fields.Boolean(string='Is moderator', compute='_compute_is_moderator')
    moderation_counter = fields.Integer(string='Moderation count', compute='_compute_moderation_counter')
    moderation_channel_ids = fields.Many2many(
        'mail.channel', 'mail_channel_moderator_rel',
        string='Moderated channels')
    out_of_office_message = fields.Char(string='Chat Status')

    @api.depends('moderation_channel_ids.moderation', 'moderation_channel_ids.moderator_ids')
    def _compute_is_moderator(self):
        moderated = self.env['mail.channel'].search([
            ('id', 'in', self.mapped('moderation_channel_ids').ids),
            ('moderation', '=', True),
            ('moderator_ids', 'in', self.ids)
        ])
        user_ids = moderated.mapped('moderator_ids')
        for user in self:
            user.is_moderator = user in user_ids

    def _compute_moderation_counter(self):
        self._cr.execute("""
SELECT channel_moderator.res_users_id, COUNT(msg.id)
FROM "mail_channel_moderator_rel" AS channel_moderator
JOIN "mail_message" AS msg
ON channel_moderator.mail_channel_id = msg.res_id
    AND channel_moderator.res_users_id IN %s
    AND msg.model = 'mail.channel'
    AND msg.moderation_status = 'pending_moderation'
GROUP BY channel_moderator.res_users_id""", [tuple(self.ids)])
        result = dict(self._cr.fetchall())
        for user in self:
            user.moderation_counter = result.get(user.id, 0)

    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights on notification_email_send
            and alias fields. Access rights are disabled by default, but allowed
            on some specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        init_res = super(Users, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        type(self).SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        type(self).SELF_WRITEABLE_FIELDS.extend(['notification_type', 'out_of_office_message'])
        # duplicate list to avoid modifying the original reference
        type(self).SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        type(self).SELF_READABLE_FIELDS.extend(['notification_type', 'out_of_office_message'])
        return init_res

    @api.model
    def create(self, values):
        if not values.get('login', False):
            action = self.env.ref('base.action_res_users')
            msg = _("You cannot create a new user from here.\n To create new user please go to configuration panel.")
            raise exceptions.RedirectWarning(msg, action.id, _('Go to the configuration panel'))

        user = super(Users, self).create(values)
        # Auto-subscribe to channels
        self.env['mail.channel'].search([('group_ids', 'in', user.groups_id.ids)])._subscribe_users()
        return user

    def write(self, vals):
        write_res = super(Users, self).write(vals)
        sel_groups = [vals[k] for k in vals if is_selection_groups(k) and vals[k]]
        if vals.get('groups_id'):
            # form: {'group_ids': [(3, 10), (3, 3), (4, 10), (4, 3)]} or {'group_ids': [(6, 0, [ids]}
            user_group_ids = [command[1] for command in vals['groups_id'] if command[0] == 4]
            user_group_ids += [id for command in vals['groups_id'] if command[0] == 6 for id in command[2]]
            self.env['mail.channel'].search([('group_ids', 'in', user_group_ids)])._subscribe_users()
        elif sel_groups:
            self.env['mail.channel'].search([('group_ids', 'in', sel_groups)])._subscribe_users()
        return write_res

    @api.model
    def systray_get_activities(self):
        query = """SELECT m.id, count(*), act.res_model as model,
                        CASE
                            WHEN %(today)s::date - act.date_deadline::date = 0 Then 'today'
                            WHEN %(today)s::date - act.date_deadline::date > 0 Then 'overdue'
                            WHEN %(today)s::date - act.date_deadline::date < 0 Then 'planned'
                        END AS states,
                        act.summary
                    FROM mail_activity AS act
                    JOIN ir_model AS m 
                        ON act.res_model_id = m.id
                    LEFT OUTER JOIN mail_activity act2 
                        ON (act.id < act2.id AND act.res_id = act2.res_id AND act.res_model_id = act2.res_model_id)
                    WHERE act.user_id = %(user_id)s AND act2.id is NULL
                    GROUP BY m.id, states, act.res_id, act.res_model, act.summary;
                    """
        self.env.cr.execute(query, {
            'today': fields.Date.context_today(self),
            'user_id': self.env.uid,
        })
        activity_data = self.env.cr.dictfetchall()
        model_ids = [a['id'] for a in activity_data]
        model_names = {n[0]: n[1] for n in self.env['ir.model'].browse(model_ids).name_get()}

        user_activities = {}
        for activity in activity_data:
            if not user_activities.get(activity['model']):
                module = self.env[activity['model']]._original_module
                icon = module and modules.module.get_module_icon(module)
                user_activities[activity['model']] = {
                    'name':  activity['summary'] if activity['model'] == 'fleet.maintenance.schedule' else model_names[activity['id']],
                    'model': activity['model'],
                    'type': 'activity',
                    'icon': icon,
                    'total_count': 0, 'today_count': 0, 'overdue_count': 0, 'planned_count': 0,
                }
            user_activities[activity['model']]['%s_count' % activity['states']] += activity['count']
            if activity['states'] in ('today', 'overdue'):
                user_activities[activity['model']]['total_count'] += activity['count']

            user_activities[activity['model']]['actions'] = [{
                'icon': 'fa-clock-o',
                'name': 'Summary',
            }]
        return list(user_activities.values())

    @api.model
    def get_rating_driver(self,id):
        sql_driver = """SELECT json_agg(t)
                        FROM ( select sum(num_rating),count(id) from sharevan_rating
                                where driver_id = %s )t"""
        self.env.cr.execute(sql_driver, (id,))
        result_driver = self._cr.fetchall()
        if result_driver[0][0][0] :
            if result_driver[0][0][0]['count'] == 0 :
                return 5
            else :
                return result_driver[0][0][0]['sum']/result_driver[0][0][0]['count']
        return id

    @api.model
    def systray_get_notifications(self,page, limit):

        uid = http.request.session['uid']
        offset_check = 0
        user_activities = []
        total_page = 1

        query = """SELECT no2.id,no2.title,no2.content,no2.status,no2.type,no2.res_model,no2.res_id ,no2.create_date
            FROM public.sharevan_notification no2
            join public.sharevan_notification_user_rel no_rel on  no2.id = no_rel.notification_id
            where no_rel.user_id = %s and no2.res_model IS NOT NULL and no2.res_id  IS NOT NULL
                  and ( no2.res_model != 'fleet.vehicle.status' or no2.status = 'new' )
                """

        total_records = """ select count(*) from (  """
        total_records += query
        total_records += " )t"

        if page is not None and limit is not None:
            if page > 0:
                offset_check = page * limit
                query += """ Order  by no2.id DESC OFFSET %s LIMIT %s """ % (
                    offset_check, limit)

            else:
                query += """ Order  by no2.id DESC OFFSET %s LIMIT %s """ % (
                    offset_check, limit)
        else:
            query += """ Order  by no2.id DESC OFFSET 0 LIMIT 10 """

        self.env.cr.execute(query,(uid,))
        activity_data = self.env.cr.dictfetchall()

        self.env.cr.execute(total_records,(uid,))
        result = self._cr.fetchall()
        total = result[0][0]

        if total > 0 :
            total_page =  math.ceil(total/limit)

        for data in activity_data :
            name = {
                'id':data['id'],
                'name':data['title'],
                'status':data['status'],
                'content':data['content'],
                'res_model':data['res_model'],
                'res_id': data['res_id'],
                'create_date': humanize.naturaltime(data['create_date']),
                'url':'/mail/static/img/cargo-truck.png',
                'noti_type' :data['type']
            }
            user_activities.append(name)
        object_result = {
            'data':list(user_activities),
            'total_page' :total_page
        }
        return object_result

    def test(self,second):
        ago = " ago"
        date = 0
        date_str = ""
        if second < 60:
            date_str = str(second) + " minutes" + ago
        elif second > 60:
            if second / 60 < 60:
                date = math.floor(second / 60)
                date_str = str(date) + " minutes" + ago
            if second / 3600 > 1 and second / 3600 < 24:
                date = math.floor(second / 3600)
                date_str = str(date) + " hour" + ago
            if second / 2592000 > 1 and second / 2592000 < 31:
                date = math.floor(second / second / 2592000)
                date_str = str(date) + " days" + ago
        return date_str
    @api.model
    def change_notifications(self,id):
        self.env.cr.execute("update public.sharevan_notification set status = 'watched' where id = %s",(id,))



class res_groups_mail_channel(models.Model):
    """ Update of res.groups class
        - if adding users from a group, check mail.channels linked to this user
          group and subscribe them. This is done by overriding the write method.
    """
    _name = 'res.groups'
    _inherit = 'res.groups'
    _description = 'Access Groups'

    def write(self, vals, context=None):
        write_res = super(res_groups_mail_channel, self).write(vals)
        if vals.get('users'):
            # form: {'group_ids': [(3, 10), (3, 3), (4, 10), (4, 3)]} or {'group_ids': [(6, 0, [ids]}
            user_ids = [command[1] for command in vals['users'] if command[0] == 4]
            user_ids += [id for command in vals['users'] if command[0] == 6 for id in command[2]]
            self.env['mail.channel'].search([('group_ids', 'in', self._ids)])._subscribe_users()
        return write_res
