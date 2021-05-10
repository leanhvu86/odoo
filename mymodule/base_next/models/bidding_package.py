from datetime import datetime, timedelta

import pytz

from odoo.exceptions import ValidationError
from mymodule.base_next.controllers.api.base_method import BaseMethod
from mymodule.base_next.models.cargo import Cargo
from mymodule.constants import Constants
from odoo import fields, api, http
from odoo import models, _


class BiddingPackage(models.Model):
    _name = Constants.SHAREVAN_BIDDING_PACKAGE
    _description = 'Bidding package'

    bidding_order_id = fields.Many2one(Constants.SHAREVAN_BIDDING_ORDER, string='Bidding order', readonly=True)
    bidding_package_number = fields.Char(string='Package Number', required=True, copy=False, readonly=True,
                                         index=True,
                                         default=lambda self: _('New'))
    name = fields.Char(related='bidding_package_number', store=False, string='Name')
    status = fields.Selection([('-1', 'Quá hạn bidding'),
                               ('0', 'Chưa bidding'),
                               ('1', 'Đã được bid'),
                               ('2', 'Chờ xác nhận')], string='Status bidding', default='0', required=True,
                              readonly=True)

    confirm_time = fields.Datetime('Confirm time', readonly=True)
    release_time = fields.Datetime('Release time')  # bỏ
    bidding_time = fields.Datetime('Bidding time')  # bỏ

    countdown_time = fields.Integer('Countdown time', required=True, help='Time to confirm information after bidding')

    max_confirm_time = fields.Datetime()

    max_count = fields.Integer('Max count', help='Max count for changing price')
    from_depot_id = fields.Many2one(Constants.SHAREVAN_DEPOT, string='From Depot', required=True,
                                    domain=lambda self: "[('id', '!=', to_depot_id),('status','=','running')]")
    to_depot_id = fields.Many2one(Constants.SHAREVAN_DEPOT, string='To Depot', required=True,
                                  domain=lambda self: "[('id', '!=', from_depot_id),('status','=','running')]")
    total_weight = fields.Float('Total weight')
    distance = fields.Float('Distance', required=True)
    from_latitude = fields.Float('From latitude', digits=(16, 5))
    from_longitude = fields.Float('From longitude', digits=(16, 5))
    to_latitude = fields.Float('To latitude', digits=(16, 5))
    to_longitude = fields.Float('To longitude', digits=(16, 5))
    from_receive_time = fields.Datetime('Pick up from time', required=True)
    to_receive_time = fields.Datetime('Pick up to time', required=True)
    from_return_time = fields.Datetime('Drop from time', required=True)
    to_return_time = fields.Datetime('Drop to time', required=True)
    price_origin = fields.Float('Price origin')
    price = fields.Float('Price', help='now price')
    price_time_change = fields.Integer('Time change price', help='Time to change price, unit=minute')  # Bỏ
    price_level_change = fields.Float('Level change price', help='Value to change price, unit=%')
    change_price_time = fields.Datetime('Change price time', help='Time final changing price')  # Bỏ
    cargo_ids = fields.Many2many(Constants.SHAREVAN_CARGO, string='Cargo', required=True,
                                 domain=lambda self: "[('bidding_package_id', '=', False)]")
    # max_confirm_time = fields.Datetime('Max confirm time',readonly=True)

    from_address = fields.Char(related='from_depot_id.address', store=False, string='From address')
    to_address = fields.Char(related='to_depot_id.address', store=False, string='To address')
    can_bid = fields.Boolean(store=False, compute='_compute_can_bid')
    is_real = fields.Boolean('Is real package', help='is Real Bidding package?', default=True, required=True)
    is_publish = fields.Boolean('Is publish package', help='is publish Bidding package', default=False)
    publish_time = fields.Datetime('Publish time', help='start time publish bidding package')
    duration_time = fields.Integer('Duration time', help='The time allowed to bid, unit=minute', required=True)
    time_published = fields.Integer(store=False, related='duration_time'); # view count down time duration
    limit_publish_time = fields.Datetime('Limit publish time', help='limit publish time bidding package')

    @api.model
    def create(self, vals):
        if vals.get('bidding_package_number', 'New') == 'New':
            vals['bidding_package_number'] = BaseMethod.get_new_sequence('sharevan.bidding.package', 'BP', 12,
                                                                         'bidding_package_number')
        # result = super(BiddingPackage, self).create(vals)
        if vals.get('bidding_time'):
            vals['change_price_time'] = vals.get('bidding_time')

        if vals.get('is_real') and len(vals.get("cargo_ids")[0][2]) > 0:
            cargo_ids = vals.get("cargo_ids")[0][2]
            from_depot_package = vals.get('from_depot_id')
            to_depot_package = vals.get('to_depot_id')
            if cargo_ids:
                dem = 0
                from_depot = None
                to_depot = None
                total_price = 0
                total_weight = 0
                distanceBidding = 0
                for cargo_id in cargo_ids:
                    cargo = self.env[Constants.SHAREVAN_CARGO].search([('id', '=', cargo_id)], limit=1)
                    if cargo:
                        if dem == 0:
                            from_depot = cargo.from_depot_id.id
                            to_depot = cargo.to_depot_id.id
                            if from_depot_package and from_depot_package != from_depot:
                                raise ValidationError("Not same from depot")
                            if to_depot_package and to_depot_package != to_depot:
                                raise ValidationError("Not same to depot")

                        dem = dem + 1
                        if (cargo.to_depot_id.id != to_depot or cargo.from_depot_id.id != from_depot):
                            raise ValidationError(_('Cargo not same from depot and to depot'))

                        if cargo.price:
                            total_price += cargo.price

                        if cargo.weight:
                            total_weight += cargo.weight

                        if cargo.price:
                            total_price += cargo.price
                        if cargo.distance:
                            distanceBidding = cargo.distance

                        # else:
                        #     try:
                        #         http.request.env[Cargo._name]. \
                        #             browse(cargo_id).write(
                        #             {'bidding_package_id': result.id})
                        #     except:
                        #         print("Error during create bidding package!")
                    else:
                        raise ValidationError("Cargo is not exists!")
                vals['total_weight'] = total_weight
                vals['price_origin'] = total_price
                vals['price'] = total_price
                vals['distance'] = distanceBidding
                result = super(BiddingPackage, self).create(vals)
                for cargo_id in cargo_ids:
                    try:
                        http.request.env[Cargo._name]. \
                            browse(cargo_id).write(
                            {'bidding_package_id': result.id})
                    except:
                        print("Error during create bidding package!")
            else:
                raise ValidationError("Must choose cargo")
            # PushNotification.push_notification()
            return result
        elif vals.get('is_real') and len(vals.get("cargo_ids")[0][2]) <= 0:
            raise ValidationError("Must choose cargo")
        else:
            result = super(BiddingPackage, self).create(vals)
            return result

    def write(self, vals):
        if vals.get('bidding_time'):
            vals['change_price_time'] = vals.get('bidding_time')
        if (vals.get("cargo_ids")):
            cargo_ids = vals.get("cargo_ids")[0][2]
            from_depot_package = vals.get('from_depot_id')
            to_depot_package = vals.get('to_depot_id')
            if cargo_ids:
                dem = 0
                from_depot = None
                to_depot = None
                total_price = 0
                total_weight = 0
                distanceBidding = 0
                for cargo_id in cargo_ids:
                    cargo = self.env[Constants.SHAREVAN_CARGO].search([('id', '=', cargo_id)], limit=1)
                    if cargo:
                        if dem == 0:
                            from_depot = cargo.from_depot_id.id
                            to_depot = cargo.to_depot_id.id
                            if from_depot_package and from_depot_package != from_depot:
                                raise ValidationError("Not same from depot")
                            if to_depot_package and to_depot_package != to_depot:
                                raise ValidationError("Not same to depot")

                        dem = dem + 1
                        if (cargo.to_depot_id.id != to_depot or cargo.from_depot_id.id != from_depot):
                            raise ValidationError(_('Cargo not same from depot and to depot'))

                        if cargo.price:
                            total_price += cargo.price

                        if cargo.weight:
                            total_weight += cargo.weight

                        if cargo.price:
                            total_price += cargo.price
                        if cargo.distance:
                            distanceBidding = cargo.distance

                        # else:
                        #     try:
                        #         http.request.env[Cargo._name]. \
                        #             browse(cargo_id).write(
                        #             {'bidding_package_id': result.id})
                        #     except:
                        #         print("Error during create bidding package!")
                    else:
                        raise ValidationError("Cargo is not exists!")
                vals['total_weight'] = total_weight
                vals['price_origin'] = total_price
                vals['price'] = total_price
                vals['distance'] = distanceBidding
                result = super(BiddingPackage, self).write(vals)
                for cargo_id in cargo_ids:
                    try:
                        http.request.env[Cargo._name]. \
                            browse(cargo_id).write(
                            {'bidding_package_id': result.id})
                    except:
                        print("Error during create bidding package!")
            else:
                raise ValidationError("Must choose cargo")
        res = super(BiddingPackage, self).write(vals)

    def getDistance(self, record):
        distance = self.env['sharevan.distance.compute'].search([
            ('from_seq', '=', record['from_depot_id'].depot_code),
            ('to_seq', '=', record['to_depot_id'].depot_code)
        ])
        if distance:
            distance_value = distance.distance
        else:
            distance_value = 0
        return distance_value

    def is_publish_check(self):
        for record in self:
            notice = ''
            if record.price <= 0:
                notice += 'Price '
            if record.duration_time <= 0:
                notice += 'Duration Time '
            if record.is_real == False and record.total_weight <= 0:
                notice += 'Total weight'
            if len(notice) > 0:
                notice += " must than 0 !!!!"
                self.env.user.notify_danger(message=notice, title="Total weight")
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Bidding package',
                    'view_mode': 'form',
                    'res_model': 'sharevan.bidding.package',
                    'res_id': self.id,
                    'context': {
                        'form_view_initial_mode': 'edit',
                    },
                }
            limit_time = datetime.now(pytz.timezone('GMT')) + timedelta(minutes=record.duration_time)
            record.update({
                'publish_time': datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S"),
                'is_publish': True,
                'limit_publish_time': limit_time.strftime("%Y-%m-%d %H:%M:%S")
            },)

    @api.onchange('cargo_ids')
    def onchange_cargo_ids(self):
        total_weight = 0
        for record in self:
            for cargo in record.cargo_ids:
                total_weight += cargo.weight
            record.update({'total_weight': total_weight})

    @api.onchange('from_depot_id')
    def onchange_from_depot(self):
        for record in self:
            record.update({'from_latitude': record['from_depot_id'].latitude})
            record.update({'from_longitude': record['from_depot_id'].longitude})
            if (record.from_depot_id and record.to_depot_id) is not None:
                distance = self.getDistance(record)
                record.update({'distance': distance})

    @api.onchange('to_depot_id')
    def onchange_to_depot(self):
        for record in self:
            record.update({'to_latitude': record['to_depot_id'].latitude})
            record.update({'to_longitude': record['to_depot_id'].longitude})
            if (record.from_depot_id and record.to_depot_id) is not None:
                distance = self.getDistance(record)
                record.update({'distance': distance})

    @api.depends('can_bid', 'bidding_time')
    def _compute_can_bid(self):
        for record in self:
            if record.bidding_time and record.countdown_time:
                time_limit = record.bidding_time + timedelta(minutes=record.countdown_time)
                now = datetime.now()
                if (record.bidding_order_id is None or not record.bidding_order_id.id) \
                        and record.bidding_time < now < time_limit:
                    record.can_bid = True
                    record.max_confirm_time = time_limit
                else:
                    record.can_bid = False
            else:
                record.can_bid = False
