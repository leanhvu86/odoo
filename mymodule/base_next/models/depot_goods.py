import json
import logging
import time

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DepotGoods(models.Model):
    _name = 'sharevan.depot.goods'
    _description = 'Keep track of the good stored in warehouse'

    depot_id = fields.Many2one('sharevan.depot', string='Depot')
    routing_plan_day_id = fields.Many2one('sharevan.routing.plan.day')
    routing_plan_name = fields.Char(related='routing_plan_day_id.routing_plan_day_code', string='Routing plan day')
    bill_lading_detail_id = fields.Many2one('sharevan.bill.lading.detail')
    capacity = fields.Float(string='Capacity', help='Calculate from dimension from bill of lading detail')
    total_weight = fields.Float(string='Total weight')
    total_amount = fields.Float(string='Total amount')
    price = fields.Float(string='Price')

    def import_goods(self, vals):
        try:
            force_save = vals['force_save'] if 'force_save' in vals else False
            routing_plan_day_id = vals['routing_plan_day_id']
            depot_id = vals['depot_id']
            rpd = self.env['sharevan.routing.plan.day']. \
                search([('id', '=', routing_plan_day_id)])
            search_model = ''
            if rpd.type == '0':
                search_model = 'sharevan.bill.package.routing.import'
            elif rpd.type == '1':
                search_model = 'sharevan.bill.package.routing.export'
            domain = [('routing_plan_day_id', '=', rpd.id)]
            lst_pk = self.env[search_model].search(domain)
            total_weight = 0.0
            capacity = vals['total_volume']
            if capacity <= 0:
                logger.warn(
                    "totan_volume must be a positive number",
                    'sharevan.depot.goods', 'Wrong value total_vulome',
                    exc_info=True)
            total_amount = 0
            for pk in lst_pk:
                total_weight += pk.total_weight
                if 'quantity_import' in pk:
                    total_amount += pk.quantity_import
                elif 'quantity_export' in pk:
                    total_amount += pk.quantity_export
            check_dup = self.search([('routing_plan_day_id', '=', routing_plan_day_id)])
            if len(check_dup) > 0:
                raise UserError("This routing plan is already imported!")
            vals = {
                "depot_id": depot_id,
                "routing_plan_day_id": routing_plan_day_id,
                'bill_lading_detail_id': rpd.bill_lading_detail_id.id,
                "capacity": - capacity,
                "total_weight": total_weight,
                "total_amount": total_amount,
                "type": "0"
            }
            res = super(DepotGoods, self).create([vals])
            if res:
                res.update_depot_capacity(force_save)
            return res.copy_data()[0]
        except TypeError:
            logger.warn(
                "Can not update depot because record not found!",
                'sharevan.depot.goods', 'not found routing plan day',
                exc_info=True)

    def export_goods(self, vals):
        try:
            routing_plan_day_id = vals['routing_plan_day_id']
            depot_id = vals['depot_id']
            force_save = vals['force_save'] if 'force_save' in vals else False
            rpd = self.env['sharevan.routing.plan.day'].search([('id', '=', routing_plan_day_id)])
            if len(rpd) < 1:
                raise UserError("Depot goods is not imported yet or routing plan doesn't exist!")
            dpg = self.search([('routing_plan_day_id', '=', routing_plan_day_id), ('depot_id', '=', depot_id)])
            if len(dpg) == 1:
                vals = {
                    "depot_id": depot_id,
                    "routing_plan_day_id": routing_plan_day_id,
                    'bill_lading_detail_id': dpg.bill_lading_detail_id.id,
                    "capacity": - dpg.capacity,
                    "total_weight": dpg.total_weight,
                    "total_amount": dpg.total_amount,
                    "type": "1"
                }
                res = super(DepotGoods, self).create([vals])
                if res:
                    res.update_depot_capacity(force_save)
                return res.copy_data()[0]
            else:
                logger.warn(
                    "Record not found or already exported!",
                    'sharevan.depot.goods', routing_plan_day_id,
                    exc_info=True)
        except TypeError:
            logger.warn(
                "Can not update depot because record not found!",
                'sharevan.depot.goods', 'not found routing plan day',
                exc_info=True)

    def update_depot_capacity(self, force_save):
        depot = self.depot_id
        if depot.available_capacity - self.capacity <= 0 and not force_save:
            raise ValidationError("Exceed depot capacity")
        depot.available_capacity += self.capacity

    # placeholder for calculating depot price
    def _cal_price(self):
        start = int(self.start_time.timestamp())
        end = int(self.end_time.timestamp())
        # get time passed, unit is hour
        # duration_hour = (end - start) / 60 / 60
        duration_hour = 10
        extra_fee = 0
        discount = 0
        price = self.env['sharevan.depot.pricing']. \
            get_price(self.depot_id.id, self.total_weight, duration_hour, self.capacity)
        self.price = price + extra_fee - discount


class DepotPricing(models.Model):
    _name = 'sharevan.depot.pricing'

    default_domain = [('from_date', '<', 'now'), ('to_date', '>', 'now')]
    name = code = fields.Char('Pricing code')
    type = fields.Selection([('0', 'Import'),
                             ('1', 'Export')], required=True)
    storage_type = fields.Selection([('1', 'Normal'), ('2', 'Refrigerated'), ('3', 'Liquid')])
    depot_id = fields.Many2one('sharevan.depot', string='Depot', required=True)
    duration = fields.Integer(string='Duration')
    weight = fields.Float(string="Package weight")
    capacity = fields.Float(string="Capacity")
    from_date = fields.Date(string="Effective date", required=True, default=datetime.today())
    to_date = fields.Date(string="Expired date")

    @api.model
    def create(self, vals):
        if vals.get('name_seq', 'New') == 'New':
            vals['code'] = self.env['ir.sequence'].next_by_code(
                'self.sharevan.depot.pricing') or 'New'
        result = super(DepotPricing, self).create(vals)
        return result

    @api.onchange('from_date', 'to_date')
    def _onchange_date(self):
        for record in self:
            if record.from_date and record.to_date:
                if record.from_date > record.to_date:
                    raise ValidationError("Effective date must be before expire date")
                if record.to_date < datetime.today().date():
                    record.to_date = datetime.today().date() + timedelta(days=1)
                    raise ValidationError("Expire date must be after today")

    def get_price(self, depot_id, weight, duration_hour, capacity):
        domain = [('depot_id', '=', depot_id)]
        domain.extend(self.default_domain)

        res = self.search(domain)

        if res:
            cal_price = weight / res.weight + capacity * duration_hour
            return cal_price
        else:
            raise ValidationError("There's no pricing for this depot!")
