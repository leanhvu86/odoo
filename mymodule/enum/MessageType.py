from enum import Enum


class MessageType(Enum):
    warning = '#d4cd00'
    danger = '#f45342'
    success = '#2ad400'

class NotificationSocketType(Enum):
    NOTIFICATION = 'notifications'