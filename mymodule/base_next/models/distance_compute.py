from datetime import datetime, timedelta

from mymodule.enum.MessageType import NotificationSocketType
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class DistanceCompute(models.Model):
    _name = 'sharevan.distance.compute'
    _description = 'distance compute'
    MODEL = 'sharevan.distance.compute'

    name = fields.Char('Name', index=True, required=True)
    distance = fields.Float('Distance', required=True, default=0.0)
    time = fields.Float('Time', required=True, default=0.0)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    min_price = fields.Float('Min Price', required=True, help='1 kg / 1 km')
    max_price = fields.Float('Max Price', required=True, help='1 kg / 1 km')
    from_seq = fields.Char('From Code', index=True, required=True)
    sync_check = fields.Boolean('Sync', index=True, default=False)
    to_seq = fields.Char('To Code', index=True, required=True)
    from_depot_id = fields.Many2one('sharevan.depot', 'From Depot',
                                    domain=lambda self: "[('id', '!=', to_depot_id),('main_type','=',True),('status','=','running')]")
    from_hub_id = fields.Many2one('sharevan.hub', 'From Hub',
                                  domain=lambda self: "[('id', '!=', to_hub_id),('status','=','running')]")
    to_hub_id = fields.Many2one('sharevan.hub', 'To Hub',
                                domain=lambda self: "[('id', '!=', from_hub_id),('status','=','running')]")
    to_depot_id = fields.Many2one('sharevan.depot', 'To Depot',
                                  domain=lambda self: "[('id', '!=', from_depot_id),('main_type','=',True),('status','=','running')]")
    status = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted'),
                               ('draft', 'Draft')], 'Status', help='Status', default="running")
    type = fields.Selection([('0', 'Depot-depot'), ('1', 'Depot-hub'),
                             ('2', 'Hub-hub'), ('3', 'Hub-depot')], 'Type', help='type of distance fee',
                            default="1")
    name_seq = fields.Char(string='Distance Reference', required=True, copy=False, readonly=True,
                           index=True,
                           default=lambda self: _('New'))
    description = fields.Text(string='Description')

    @api.model
    def create(self, vals):
        if vals.get('name_seq', 'New') == 'New':
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('self.share.van.depot') or 'New'
        result = super(DistanceCompute, self).create(vals)
        return result


class EmployeeWorkingCalendar(models.Model):
    _name = 'sharevan.employee.warehouse'
    _description = 'employee warehouse calendar'
    MODEL = 'sharevan.employee.warehouse'

    name = fields.Char(string='Name', related='employee_id.name')
    employee_id = fields.Many2one('res.partner', 'Employee',
                                  domain=lambda self: "[('status', '=', 'running'),('company_id','=',company_id)]",
                                  required=True)
    place_id = fields.Integer('Place id')
    code = fields.Char(string='Distance Reference', required=True, copy=False, readonly=True,
                       index=True,
                       default=lambda self: _('New'))
    company_id = fields.Many2one('res.company', 'Company',
                                 domain=lambda self: "[('company_type', '!=', '0'),('status','=','running')]", required=True)
    status = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted')], 'Status', default="running")
    warehouse_id = fields.Many2one('sharevan.warehouse', 'Warehouse',
                                   domain=lambda self: "[('status', '=', 'running'),('company_id','=',company_id)]")
    depot_id = fields.Many2one('sharevan.depot', 'Depot',
                               domain=lambda self: "[('status', '=', 'running'),('company_id','=',company_id)]")
    place_type = fields.Selection([('0', 'Warehouse'),
                                   ('1', 'Depot')],
                                  'Place Type', help='Place Type', default="0", required=True)
    date_assign = fields.Date('Date assign', index=True, required=True)
    user_id = fields.Many2one('res.users', 'User',
                              domain=lambda self: "[('status', '=', 'running'),('company_id','=',company_id)]")

    @api.onchange('warehouse_id')
    def onchange_warehouse(self):
        for record in self:
            if record['warehouse_id']:
                record.update({'place_id': record['warehouse_id'][0]})

    @api.onchange('company_id')
    def onchange_company_id(self):
        for record in self:
            record.update({'place_id': False})
            record.update({'employee_id': False})
            record.update({'warehouse_id': False})
            record.update({'depot_id': False})
            record.update({'user_id': False})

    @api.onchange('depot_id')
    def onchange_depot(self):
        for record in self:
            if record['depot_id']:
                record.update({'place_id': record['depot_id'][0]})

    @api.model
    def create(self, vals):
        if vals.get('code', 'New') == 'New':
            vals['code'] = self.env['ir.sequence'].next_by_code('self.sharevan.employee.warehouse') or 'New'
        result = super(EmployeeWorkingCalendar, self).create(vals)
        return result

    def unlink(self):
        for id in self.ids:
            record = self.env['sharevan.employee.warehouse'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })
        return self

    @api.onchange('employee_id')
    def onchange_employee(self):
        for record in self:
            if record['employee_id'].user_id:
                record.update({'user_id': record['employee_id'].user_id.id})

    @api.onchange('date_assign')
    def onchange_date(self):
        for record in self:
            if record['date_assign']:
                date_assign = datetime.strptime(str(record['date_assign']), '%Y-%m-%d')
                if date_assign < datetime.now() - timedelta(days=1):
                    record['date_assign'] = False
                    notice = "Date assign is not small than today !"
                    self.env.user.notify_danger(message=notice, title=NotificationSocketType.NOTIFICATION.value)
