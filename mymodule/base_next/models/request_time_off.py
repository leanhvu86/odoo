from datetime import datetime, timedelta

from odoo import api, fields, models


class RequestTimeOff(models.Model):
    _name = 'fleet.request.time.off'
    _description = 'Fleet request time off'
    _order = 'request_day desc'

    name = fields.Char('Name', related='driver_name')
    group_request_id = fields.Many2one('fleet.group.request.to')
    request_day = fields.Date("Day off ", default=datetime.today(), required=True)
    driver_id = fields.Many2one('fleet.driver', 'Driver')
    can_approve = fields.Boolean('Can approve', compute='_check_can_approve', store=False)
    all_day = fields.Boolean(compute='_check_all_day', store=False)
    driver_name = fields.Char(related='driver_id.name', string="Driver name")
    company_id = fields.Many2one(string="Company", related='driver_id.company_id')
    reason = fields.Char(string='Reason', related='group_request_id.reason')
    approver_id = fields.Many2one('res.users', 'Approver', related='group_request_id.approver_id')
    create_date = fields.Datetime('Request date', readonly="1")
    type = fields.Selection(
        [('1', 'Whole day'),
         ('2', 'Morning'),
         ('3', 'Afternoon')
         ],
        string='Type', context={'status': '1'}, default='1', required=True)
    status = fields.Selection(
        [('1', 'Waiting'),
         ('2', 'Accepted'),
         ('3', 'Denied'),
         ('4', 'Canceled')
         ],
        string='Status', context={'status': '1'}, default='1', related='group_request_id.status', store=True)


class GroupRequestTO(models.Model):
    # 'to' = time off
    _name = 'fleet.group.request.to'

    list_day_request = fields.One2many(comodel_name='fleet.request.time.off', inverse_name='group_request_id')
    driver_id = fields.Many2one('fleet.driver', 'Driver')
    driver_name = fields.Char(related='driver_id.name', string="Driver name")
    company_id = fields.Many2one(string="Company", related='driver_id.company_id')
    reason = fields.Char(string='Reason', required=True)
    approver_id = fields.Many2one('res.users', 'Approver')
    start_day = fields.Date('Start day')
    end_day = fields.Date('End day')
    status = fields.Selection(
        [('1', 'Waiting'),
         ('2', 'Accepted'),
         ('3', 'Denied'),
         ('4', 'Canceled')
         ],
        string='Status', context={'status': '1'}, default='1', required=True)
