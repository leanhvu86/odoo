import json
import logging
from collections import defaultdict

import requests
from pyfcm import FCMNotification

from mymodule.enum.MessageType import MessageType
from odoo import http

FCM_SERVER = "https://fcm.googleapis.com/fcm/send"


class FirebaseMessagingAPI:

    @staticmethod
    def send_message_for_all_normal(ids, title, body, short_body, click_action, message_type, item_id):
        global token
        fcm_token_api = http.request.env['ir.config_parameter'].sudo().get_param('firebase.api_key')
        registration_id = []

        user_res = http.request.env['res.users'].search([('id', 'in', ids)])
        for user in user_res:
            if 'fcm_token' in user and user['fcm_token']:
                registration_id.append(user['fcm_token'])
        push_service = FCMNotification(api_key=fcm_token_api)
        message_title = title
        message_body = short_body
        color = MessageType.success.value
        if message_type:
            color = message_type
        # mobile luon can 2 tham so nay
        extra_notification_kwargs = {
            'android_channel_id': 2,
            'click_action': click_action
        }
        data = {
            'click_action': click_action,
            'title': title,
            'body': short_body,
            'item_id': item_id,
            'mess_object': body,
            "badge": "1"
        }
        extra_kwargs = {'mutable_content': True, 'notification': data}

        # count_id = registration_id.count(True)
        # if count_id == 0:
        #     raise ValidationError("No receiver have token")
        push_service.notify_multiple_devices(registration_ids=registration_id, message_title=message_title,
                                             message_body=message_body, data_message=data, color=color, badge='1',
                                             click_action=click_action, low_priority=False, extra_kwargs=extra_kwargs,
                                             extra_notification_kwargs=extra_notification_kwargs)

    @staticmethod
    def send_message_for_all_with_fcm_token(tokens, title, body, short_body, click_action, message_type, item_id):
        global token
        fcm_token_api = http.request.env['ir.config_parameter'].sudo().get_param('firebase.api_key')
        registration_id = []
        for user in tokens:
            registration_id.append(user)
        push_service = FCMNotification(api_key=fcm_token_api)
        message_title = title
        message_body = short_body
        color = MessageType.success.value
        if message_type:
            color = message_type
        # mobile luon can 2 tham so nay
        extra_notification_kwargs = {
            'android_channel_id': 2,
            'click_action': click_action
        }
        # extra_notification_kwargs = {
        #     'android_channel_id': 2,
        #     'click_action': click_action,
        #     'priority': 'high',
        #     'android': {
        #         'priority': 'high'
        #     },
        #     'aps': {
        #         'priority': 'high'
        #     }
        # }
        data = {
            'click_action': click_action,
            'title': title,
            'body': short_body,
            'item_id': item_id,
            'mess_object': body,
            "badge": "1"
        }
        extra_kwargs = {'mutable_content': True, 'notification': data}

        # count_id = registration_id.count(True)
        # if count_id == 0:
        #     raise ValidationError("No receiver have token")
        push_service.notify_multiple_devices(registration_ids=registration_id, message_title=message_title,
                                             message_body=message_body, data_message=data, color=color, badge='1',
                                             click_action=click_action, low_priority=False, extra_kwargs=extra_kwargs,
                                             extra_notification_kwargs=extra_notification_kwargs)
        # message = messaging.Message(
        #     data={
        #         'score': '850',
        #         'time': '2:45',
        #         'click_action': 'com.ts.sharevandriver.TARGET_ROUTING_DETAIL',
        #     },
        #     notification=messaging.Notification(
        #         title='$GOOG up 1.43% on the day',
        #         body='$GOOG gained 11.80 points to close at 835.67, up 1.43% on the day.',
        #     ),
        #     android=messaging.AndroidConfig(
        #         # ttl=datetime.timedelta(seconds=3600),
        #         priority='normal',
        #         notification=messaging.AndroidNotification(
        #             color='#f45342'
        #         ),
        #     ),
        #     apns=messaging.APNSConfig(
        #         payload=messaging.APNSPayload(
        #             aps=messaging.Aps(badge=42),
        #         ),
        #     ),
        #     token=token,
        # )
        #
        # # Send a message to the device corresponding to the provided
        # # registration token.
        # response = messaging.send(message)
        # # Response is a message ID string.
        # print('Successfully sent message:', response)
        # print(result)


class FirebaseMessaging(object):
    logger = None
    logging_handler = None

    def __init__(self, api_key, timeout=None, debug=False):
        self.url = FCM_SERVER
        self.api_key = api_key
        self.timeout = timeout
        if debug:
            self.enable_logger()

    def sendPlainText(self, **kwargs):
        payload = self.createPayLoad(is_json=False, **kwargs)
        self.makeRequest(payload, is_json=False)
        pass

    def sendNotification(self, **kwargs):
        return self.sendData(**kwargs)

    def sendData(self, **kwargs):
        self.log("Sending data to devices")
        payload = self.createPayLoad(**kwargs)
        response = self.makeRequest(payload, is_json=True)
        return self.handleJSONResponse(response, **kwargs)

    def makeRequest(self, payload, is_json=False):
        headers = {
            "Authorization": "key=%s" % self.api_key,
            "Content-type": "application/json" if is_json else "application/x-www-form-urlencoded;charset=UTF-8"
        }
        response = requests.post(self.url, data=payload, headers=headers, timeout=self.timeout)

        if response.status_code == 200:
            self.log("Request success : 200")
            return response.json() if is_json else response.content

        if response.status_code == 400:
            msg = "Error 400: The request could not be parsed as JSON, or it contained invalid fields."
            self.log(msg)
            raise FCMMalformedJsonException(msg)

        if response.status_code == 401:
            msg = "Error 401: There was an error authenticating the sender account."
            self.log(msg)
            raise FCMAuthenticationException(msg)

        if response.status_code == 503:
            msg = "The Firebsase Messaging server is temporarily unavailable"
            self.log("Error 503: %s" % msg)
            raise FCMInternalException(msg)
        else:
            msg = "There was an internal error in the FCM connection server while trying to process the request"
            self.log("Error %s: %s" % (response.status_code, msg))
            raise FCMInternalException(msg)

    def createPayLoad(self, **kwargs):
        is_json = kwargs.pop("is_json", True)
        payloadObj = JsonPayload(**kwargs) if is_json else PlainTextPayload(**kwargs)
        return payloadObj.body

    def handleJSONResponse(self, response, **kwargs):
        reg_ids = kwargs.get('registration_ids', None)
        to = kwargs.get('to', None)
        if to and not reg_ids:
            reg_ids = [to]

        errors = self.groupResponseResult(response, reg_ids, 'error')
        canonical = self.groupResponseResult(response, reg_ids, 'registration_id')
        success = self.groupResponseResult(response, reg_ids, 'message_id')
        result = {}
        if errors:
            result.update({'errors': errors})

        if canonical:
            result.update({'canonical': canonical})

        if success:
            result.update({'success': success})
        return result

    def groupResponseResult(self, response, reg_ids, key):
        mapping = zip(reg_ids, response['results'])
        filtered = ((reg_id, res[key]) for reg_id, res in mapping if key in res)
        if key in ['registration_id', 'message_id']:
            grouping = dict(filtered)
        else:
            grouping = defaultdict(list)
            for k, v in filtered:
                grouping[v].append(k)
            grouping = grouping.items()
        return grouping or None

    def enable_logger(self, level=logging.DEBUG, handler=None):
        if not handler:
            if self.logging_handler is None:
                self.logging_handler = logging.StreamHandler()
                self.logging_handler.setFormatter(logging.Formatter(
                    '%(asctime)s ' + bcolors.OKGREEN + bcolors.BOLD + "DEBUG" + bcolors.ENDC + ' %(message)s'))
            handler = self.logging_handler

        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(handler)
        self.logger.setLevel(level)

    def log(self, message, *data):
        if self.logger:
            self.logger.debug(message.format(data))


class Payload(object):

    def __init__(self, **kwargs):
        self.validate(kwargs)
        self.__dict__.update(kwargs)

    def validate(self, options):
        for key, value in options.items():
            validate_method = getattr(self, 'validate_%s' % key, None)
            if validate_method:
                validate_method(value)

    def validate_registration_ids(self, registration_ids):
        if len(registration_ids) > 1000:
            raise FCMTooManyRegIdsException("Exceded number of reigstration ids. Only 1000 per request allowed")

    @property
    def body(self):
        raise NotImplementedError


class JsonPayload(Payload):
    @property
    def body(self):
        return json.dumps(self.__dict__)


class PlainTextPayload(Payload):
    @property
    def body(self):
        if 'registration_ids' not in self.__dict__:
            self.__dict__['registration_ids'] = self.__dict__.pop('registration_ids', None)
        data = self.__dict__.pop("data")

        for key, value in data.items():
            self.__dict__['data.%s' % key] = value
        return self.__dict__


class FCMException(Exception):
    pass


class FCMTooManyRegIdsException(FCMException):
    pass


class FCMMalformedJsonException(FCMException):
    pass


class FCMAuthenticationException(FCMException):
    pass


class FCMInternalException(FCMException):
    pass


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
