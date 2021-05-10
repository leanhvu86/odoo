# (c) 2015 ACSONE SA/NV, Dhinesh D

# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import json
import logging
from datetime import datetime
from os import utime
from os.path import getmtime
from time import time

import pytz

from addons.website.controllers.main import logger
from mymodule.base_next.controllers.api.firebase_messaging import FirebaseMessagingAPI
from mymodule.base_next.models.notification import Notification
from mymodule.enum.ClickActionType import ClickActionType
from mymodule.enum.MessageType import NotificationSocketType, MessageType
from mymodule.enum.RoutingDetailStatus import RoutingDetailStatus
from odoo import api, http, models
from odoo.exceptions import ValidationError
from odoo.http import SessionExpiredException

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    # TO DO - test log in for second janus
    @api.model
    def _auth_timeout_get_ignored_urls(self):
        """Pluggable method for calculating ignored urls
        Defaults to stored config param
        """
        params = self.env["ir.config_parameter"]
        return params._auth_timeout_get_parameter_ignored_urls()

    # TO DO - test log out for second janus
    @api.model
    def _auth_timeout_deadline_calculate(self):
        """Pluggable method for calculating timeout deadline
        Defaults to current time minus delay using delay stored as config
        param.
        """
        params = self.env["ir.config_parameter"]
        delay = params._auth_timeout_get_parameter_delay()
        if delay <= 0:
            return False
        return time() - delay

    @api.model
    def _auth_timeout_session_terminate(self, session):
        """Pluggable method for terminating a timed-out session

        This is a late stage where a session timeout can be aborted.
        Useful if you want to do some heavy checking, as it won't be
        called unless the session inactivity deadline has been reached.

        Return:
            True: session terminated
            False: session timeout cancelled
        """
        if session.db and session.uid:
            session.logout(keep_db=True)
        return True

    @api.model
    def _auth_timeout_check(self):
        """Perform session timeout validation and expire if needed."""

        if not http.request:
            return

        session = http.request.session

        # Calculate deadline
        deadline = self._auth_timeout_deadline_calculate()
        # Check if past deadline
        expired = False
        if deadline is not False:
            path = http.root.session_store.get_session_filename(session.sid)
            try:
                expired = getmtime(path) < deadline
            except OSError:
                _logger.exception("Exception reading session file modified time.", )
                # Force expire the session. Will be resolved with new session.
                expired = True

        # Try to terminate the session
        terminated = False
        if expired:
            terminated = self._auth_timeout_session_terminate(session)

        # If session terminated, all done
        if terminated:
            raise SessionExpiredException("Session expired")

        # Else, conditionally update session modified and access times
        ignored_urls = self._auth_timeout_get_ignored_urls()

        if http.request.httprequest.path not in ignored_urls:
            if "path" not in locals():
                path = http.root.session_store.get_session_filename(session.sid, )
            try:
                utime(path, None)
            except OSError:
                _logger.exception(
                    "Exception updating session file access/modified times.",
                )

    def send_notis_web(self, user_ids, title, body):
        if not isinstance(user_ids, list) or not user_ids:
            raise ValidationError("User ids is invalid")
        if not body:
            raise ValidationError("Body must have content")
        users = self.search(args=[('id', 'in', user_ids)])
        if not users:
            raise ValidationError("User id invalid")
        list_ids = []
        for us in users:
            list_ids.append(us.id)
            # us.notify_info(message=body, title=NotificationSocketType.NOTIFICATION.value)
        try:
            objct_val = {
                "title": title,
                "name": title,
                "content": body,
                "create_date": datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S"),
                "type": 'routing',
                "image_256": '',
                "click_action": ClickActionType.driver_main_activity.value,
                "message_type": MessageType.success.value,
                "item_id": '',
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
                title, body, sent_date, 'routing', RoutingDetailStatus.Unconfimred.value,
                ClickActionType.driver_main_activity.value, MessageType.success.value, '', 1, sent_date, 'status',))
            result = http.request.env[Notification._name]._cr.fetchall()
            if result[0][0]:
                for rec in user_ids:
                    INSERT_NOTIFICATION_REL_QUERY = """
                            INSERT INTO public.sharevan_notification_user_rel(
                                notification_id, user_id, is_read)
                                VALUES (%s, %s, %s) RETURNING id 
                        """
                    http.request.cr.execute(INSERT_NOTIFICATION_REL_QUERY, (result[0][0], rec, False,))
            FirebaseMessagingAPI. \
                send_message_for_all_normal(ids=user_ids, title=title, body=str(objct_val), short_body=body,
                                            item_id=item_id,
                                            click_action=click_action, message_type=message_type)
            return 200
        except:
            logger.warn(
                "Not send message",
                ResUsers._name,
                exc_info=True)
            return 500
