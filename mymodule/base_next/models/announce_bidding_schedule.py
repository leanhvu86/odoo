from datetime import datetime, timedelta

import simplejson

from mymodule.constants import Constants
from odoo import models, api, fields, http
from odoo.exceptions import ValidationError


class AnnounceBiddingSchedule(models.Model):
    _name = Constants.SHAREVAN_ANNOUNCE_BIDDING_SCHEDULE
    _description = 'Announce bidding schedule'

    company_id = fields.Many2one(Constants.RES_COMPANY, string='Company')
    bidding_package_id = fields.Many2one(Constants.SHAREVAN_BIDDING_PACKAGE, string='Bidding package')
    announce_time = fields.Datetime('Announce time')
    status = fields.Selection([('0', 'Chưa nhắc nhở'),
                               ('1', 'Đã nhắc nhở')], string='status', default='0')
    # + company_id
    # + bidding_package_id
    # + announce_time:
    # + status: 0: chưa
    # nhắc
    # nhở
    # 1: đã
    # nhắc
    # nhở


class DriverAssignRouting(models.Model):
    _name = 'sharevan.driver.assign.routing'
    _description = 'Driver assign routing in market place'

    from_area_id = fields.Many2one(Constants.SHAREVAN_AREA, string='From province')
    to_area_id = fields.Many2one(Constants.SHAREVAN_AREA, string='To province')
    from_address = fields.Char('From address')
    to_address = fields.Char('To address')
    available_capacity = fields.Float('Available capacity')
    available_weight = fields.Float('Available weight')
    from_date_assign = fields.Date('From date assign', default=fields.Date.context_today,
                                   help='date driver assign for available capacity')
    to_date_assign = fields.Date('To date assign', default=fields.Date.context_today,
                                 help='date driver assign for available capacity')
    driver_id = fields.Many2one('fleet.driver', string='Driver')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    status = fields.Selection([('running', 'Running'),
                               ('delete', 'Delete')], string='status', default='running')

    def assign_routing_driver(self, routingDriver):
        print(routingDriver)
        driver = self.env['fleet.driver'].search([('user_id', '=', self.env.uid)])
        if routingDriver['driver_id'] == driver['id']:
            now = datetime.now() - timedelta(days=1)
            if 'from_date_assign' not in routingDriver:
                raise ValidationError('From date assign not found')
            from_date_assign = datetime.strptime(routingDriver['from_date_assign'], '%Y-%m-%d')
            if from_date_assign < now:
                raise ValidationError('From date assign must not lower than now ')
            if 'to_date_assign' not in routingDriver:
                raise ValidationError('To date assign not found')
            to_date_assign = datetime.strptime(routingDriver['to_date_assign'], '%Y-%m-%d')
            if to_date_assign < now:
                raise ValidationError('To date assign must not lower than now ')
            vals = {
                "driver_id": routingDriver['driver_id'],
                "from_area_id": routingDriver['from_area']['id'],
                "to_area_id": routingDriver['to_area']['id'],
                "available_capacity": routingDriver['available_capacity'],
                "available_weight": routingDriver['available_weight'],
                "from_date_assign": routingDriver['from_date_assign'],
                "to_date_assign": routingDriver['to_date_assign']
            }
            http.request.env['res.users']. \
                browse(self.env.uid).write(
                {'accept_firebase_notification': True})
            record = super(DriverAssignRouting, self).create(vals)
            return record['id']
        else:
            raise ValidationError('Driver not found!')

    def get_driver_assign(self):
        query = """
            select routing.id, routing.driver_id, routing.available_capacity, routing.available_weight,routing.from_date_assign,
                routing.to_date_assign,from_area.name from_area_name ,from_area.code from_area_code,
                from_area.id from_area_id,to_area.id to_area_id,to_area.name to_area_name,to_area.code to_area_code
            from sharevan_driver_assign_routing routing
                join fleet_driver driver on driver.id = routing.driver_id
                join sharevan_area from_area on routing.from_area_id = from_area.id
                join sharevan_area to_area on routing.from_area_id = to_area.id 
            where routing.from_date_assign >= CURRENT_DATE or routing.to_date_assign >= CURRENT_DATE
                and driver.user_id = %s  order by routing.id
        """
        self.env.cr.execute(query, (self.env.uid,))
        routing_assgin = self._cr.dictfetchall()
        if routing_assgin:
            jsonRe = []
            for routing in routing_assgin:
                vals = {
                    "driver_id": routing['driver_id'],
                    "from_area": {
                        'id': routing['from_area_id'],
                        'name': routing['from_area_name'],
                        'code': routing['from_area_code']
                    },
                    "to_area": {
                        'id': routing['to_area_id'],
                        'name': routing['to_area_name'],
                        'code': routing['to_area_code']
                    },
                    "available_capacity": routing['available_capacity'],
                    "available_weight": routing['available_weight'],
                    "from_date_assign": routing['from_date_assign'],
                    "to_date_assign": routing['to_date_assign']
                }
                jsonRe.append(vals)
            records = {
                'length': len(routing_assgin),
                'records': jsonRe
            }
            simplejson.dumps(records, indent=4, sort_keys=True, default=str)
            return records
        return {
            'records': routing_assgin
        }
