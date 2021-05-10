# -*- coding: utf-8 -*-
from mymodule.base_next.models.bidding_vehicle import BiddingVehicle
from odoo import api, fields, models, _
from odoo import http
from odoo.exceptions import ValidationError


class ShareVanActionLog(models.Model):
    _name = 'action.log'
    MODEL = 'action.log'
    _description = 'Action Log'

    van_id = fields.Many2one('sharevan.bidding.vehicle', string='Van')
    latitude = fields.Float(string='Geo Latitude', digits=(16, 5))
    longitude = fields.Float(string='Geo Longitude', digits=(16, 5))
    create_time = fields.Date('Start Date', default=fields.Date.today())

    @api.model
    def create_action_log(self, action_logs):
        if action_logs:
            for action_log in action_logs:
                if action_log['van_id']:
                    record_bidding_vehicle = http.request.env[BiddingVehicle._name]. \
                        web_search_read([['id', '=', action_log['van_id']]], fields=None,
                                        offset=0, limit=10, order='')
                    if record_bidding_vehicle['records']:
                        result = super(ShareVanActionLog, self).create(action_log)
                    else:
                        raise ValidationError(_('Bidding_vehicle does not existed!'))

                else:
                    raise ValidationError(_('Van id can not null!'))
            return True
        else:
            raise ValidationError("action_logs can not null!")
