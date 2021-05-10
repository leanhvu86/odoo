import logging
from datetime import datetime

from mymodule.base_next.controllers.api.base_method import BaseMethod
from odoo import fields, api
from odoo import models, _
from odoo.exceptions import UserError, ValidationError

logger = logging.getLogger(__name__)


class Recurrent(models.Model):
    _name = "sharevan.recurrent"
    MODEL = "sharevan.recurrent"
    _description = 'Recurrent description'
    _order = 'recurrent_code'

    name = fields.Char(string='name', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))
    subscribe_id = fields.Many2one('sharevan.subscribe', 'Subscribe', required=True)
    recurrent_code = fields.Char(string='Recurrent code', required=True, copy=False, readonly=True, index=True,
                                 default=lambda self: _('New'))
    # field for view
    cycle_type = fields.Selection(
        [('1', 'Hàng ngày'), ('2', 'Hàng tuần'), ('3', 'Hàng tháng')], 'Cycle type',
        default='1', store=False)
    week_choose = fields.Selection(
        [('1', 'Chủ nhật'), ('2', 'Thứ hai'), ('3', 'Thứ ba'),
         ('4', 'Thứ tư'), ('5', 'Thứ năm'), ('6', 'Thứ sáu'), ('7', 'Thứ bảy')], 'Week choose',
        default='1', store=False)
    chooseDay = fields.Date(default=datetime.today(), string="Choose Date", store=False)
    # end declare for view

    frequency = fields.Integer(string='Frequency', default=1)
    day_of_week = fields.Integer(string='Day Of Week')
    day_of_month = fields.Integer(string='Day In Month')
    description = fields.Html('Description', sanitize_style=True)
    status = fields.Selection([('running', 'Running'), ('deleted', 'Deleted'),
                               ('draft', 'Draft')], string='Status',
                              default='running')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('self.sharevan.recurrent') or 'New'
            vals['recurrent_code'] = vals['name']
            if vals.get('cycle_type') == '1':
                vals['frequency'] = 1
                vals['day_of_week'] = 0
                vals['day_of_month'] = 0
            if vals.get('cycle_type') == '2':
                vals['frequency'] = 2
                vals['day_of_week'] = int(vals.get('week_choose'))
                vals['day_of_month'] = 0
            if vals.get('cycle_type') == '3':
                vals['frequency'] = 3
                vals['day_of_week'] = 0
                # choose_day = vals['chooseDay']
                # vals['day_of_month'] = choose_day.day
            result = super(Recurrent, self).create(vals)
            return result

    @api.onchange('chooseDay')
    def _onchange_chooseDay(self):
        choose_day = self['chooseDay']
        if choose_day:
            self['day_of_month'] = choose_day.day

    @api.onchange('cycle_type')
    def _onchange_cycle_type(self):
        if self['cycle_type'] == '1':
            self['frequency'] = 1
            self['day_of_week'] = 0
            self['day_of_month'] = 0
        if self['cycle_type'] == '2':
            self['frequency'] = 2
            self['day_of_week'] = int(self['week_choose'])
            self['day_of_month'] = 0
        if self['cycle_type'] == '3':
            self['frequency'] = 3
            self['day_of_week'] = 0

    def get_data_on_load(self):
        today = datetime.today()
        if self.day_of_month:
            d = datetime(today.year, today.month, int(self.day_of_month), today.hour, today.minute)
            self.chooseDay = d
        else:
            self.chooseDay = today


class OrderPackage(models.Model):
    _name = "sharevan.bill.order.package"
    MODEL = "sharevan.bill.order.package"
    _description = 'bill order package description'

    name = fields.Char(string='Name', required=True)
    description = fields.Html('Description', sanitize_style=True)
    status = fields.Selection(
        [('running', 'Running'),
         ('deleted', 'Deleted')
         ],
        default='running',
        string='Status', required=True)
    extra_cost = fields.Float(string='Extra cost', digits=(12, 3), requmired=True)
    extra_amount_percent = fields.Float(string='Extra amount percent', digits=(12, 3), required=True)
    type = fields.Selection([('express', 'Express'), ('economy', 'Economy'), ('just_in_time', 'Just In Time'),
                             ('normal', 'Normal')], string='Type',
                            default='normal')
    code = fields.Char(string='Code', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))

    @api.constrains('extra_cost')
    def onchange_extra_cost(self):
        for record in self:
            if record['extra_cost'] < 0:
                raise ValidationError('Extra_cost must not smaller than 0 !')

    @api.constrains('extra_amount_percent')
    def onchange_extra_amount_percent(self):
        for record in self:
            if record['extra_amount_percent'] < 0:
                raise ValidationError('Extra_amount_percent must not smaller than 0 !')

    def get_bill_order_package(self):
        query = """
            select id,name,type,extra_cost,extra_amount_percent,type 
                from sharevan_bill_order_package
            where status = 'running'
                """
        self.env.cr.execute(query,
                            ())
        result = self._cr.dictfetchall()
        return {
            'records': result
        }

    @api.model
    def create(self, vals):
        seq = BaseMethod.get_new_sequence('sharevan.bill.order.package', 'BOP', 6, 'code')
        vals['code'] = seq
        result = super(OrderPackage, self).create(vals)
        return result

    def unlink(self):
        for id in self.ids:
            record = self.env['sharevan.bill.order.package'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })

        return self
