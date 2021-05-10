# -*- coding: utf-8 -*-
from mymodule.share_van_order.controllers.api.base import BaseApi
from odoo import http
from odoo.exceptions import ValidationError


class RecurrentApi:
    MODEL = 'sharevan.recurrent'

    @staticmethod
    def create_bill_recurrent(recurrent):
        subscribe_id = 0
        if 'subscribe' not in recurrent:
            raise ValidationError("Validation error subscribe")
        for key in recurrent.keys():
            if key == 'subscribe':
                subscribe = recurrent[key]
                subscribe_id = subscribe['id']
                break
        instance = BaseApi.getInstance(RecurrentApi.MODEL, recurrent)
        instance['subscribe_id'] = subscribe_id
        # instance['bill_lading_id'] = billLadingId
        return http.request.env[RecurrentApi.MODEL].create(instance)
