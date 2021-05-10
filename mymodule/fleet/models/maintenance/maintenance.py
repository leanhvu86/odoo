# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

import pytz

from mymodule.enum.VehicleSosType import VehicleSosType
from odoo import _, api, exceptions, fields, models, modules
from mymodule.enum.StageMaintenanceType import StageMaintenanceType
from mymodule.enum.StatusType import StatusType
from mymodule.enum.VehicleStateStatus import VehicleStateStatus, VehicleEquipmentPart
from mymodule.enum.VehicleStatusAvailable import VehicleStatusAvailable
from mymodule.fleet.models.utils import validate_utils
from mymodule.fleet.models.utils.fleet_util import FleetVehicleState
from odoo import api, fields, models, SUPERUSER_ID, _, http
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta, date, timezone


class MaintenanceStage(models.Model):
    """ Model for case stages. This models the main stages of a Maintenance Request management flow. """

    _name = 'sharevan.maintenance.stage'
    _description = 'Maintenance Stage'
    _order = 'sequence, id'

    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=20)
    code = fields.Char()
    fold = fields.Boolean('Folded in Maintenance Pipe')
    done = fields.Boolean('Request Done')

    @staticmethod
    def get_id_by_code(self, code):
        stage = self.env['sharevan.maintenance.stage'].search([('code', '=', code)], limit=1)
        if stage:
            return stage.id


# class MaintenanceEquipmentCategory(models.Model):
#     _name = 'maintenance.equipment.category'
#     _inherit = ['mail.alias.mixin', 'mail.thread']
#     _description = 'Maintenance Equipment Category'
#
#     @api.depends('equipment_ids')
#     def _compute_fold(self):
#         # fix mutual dependency: 'fold' depends on 'equipment_count', which is
#         # computed with a read_group(), which retrieves 'fold'!
#         self.fold = False
#         for category in self:
#             category.fold = False if category.equipment_count else True
#
#     name = fields.Char('Category Name', required=True, translate=True)
#     company_id = fields.Many2one('res.company', string='Company',
#         default=lambda self: self.env.company)
#     technician_user_id = fields.Many2one('res.users', 'Responsible', tracking=True, default=lambda self: self.env.uid)
#     color = fields.Integer('Color Index')
#     note = fields.Text('Comments', translate=True)
#     equipment_ids = fields.One2many('maintenance.equipment', 'category_id', string='Equipments', copy=False)
#     equipment_count = fields.Integer(string="Equipment", compute='_compute_equipment_count')
#     maintenance_ids = fields.One2many('maintenance.request', 'category_id', copy=False)
#     maintenance_count = fields.Integer(string="Maintenance Count", compute='_compute_maintenance_count')
#     alias_id = fields.Many2one(
#         'mail.alias', 'Alias', ondelete='restrict', required=True,
#         help="Email alias for this equipment category. New emails will automatically "
#         "create a new equipment under this category.")
#     fold = fields.Boolean(string='Folded in Maintenance Pipe', compute='_compute_fold', store=True)
#
#     def _compute_equipment_count(self):
#         equipment_data = self.env['maintenance.equipment'].read_group([('category_id', 'in', self.ids)], 
#                   ['category_id'], ['category_id'])
#         mapped_data = dict([(m['category_id'][0], m['category_id_count']) for m in equipment_data])
#         for category in self:
#             category.equipment_count = mapped_data.get(category.id, 0)
#
#     def _compute_maintenance_count(self):
#         maintenance_data = self.env['maintenance.request'].read_group([('category_id', 'in', self.ids)], 
#                   ['category_id'], ['category_id'])
#         mapped_data = dict([(m['category_id'][0], m['category_id_count']) for m in maintenance_data])
#         for category in self:
#             category.maintenance_count = mapped_data.get(category.id, 0)
#
#     @api.model
#     def create(self, vals):
#         self = self.with_context(alias_model_name='maintenance.request', alias_parent_model_name=self._name)
#         if not vals.get('alias_name'):
#             vals['alias_name'] = vals.get('name')
#         category_id = super(MaintenanceEquipmentCategory, self).create(vals)
#         category_id.alias_id.write({'alias_parent_thread_id': category_id.id, 'alias_defaults': 
#                       {'category_id': category_id.id}})
#         return category_id
#
#     def unlink(self):
#         MailAlias = self.env['mail.alias']
#         for category in self:
#             if category.equipment_ids or category.maintenance_ids:
#                 raise UserError(_("You cannot delete an equipment category containing equipments or maintenance requests."))
#             MailAlias += category.alias_id
#         res = super(MaintenanceEquipmentCategory, self).unlink()
#         MailAlias.unlink()
#         return res
#
#     def get_alias_model_name(self, vals):
#         return vals.get('alias_model', 'maintenance.request')
#
#     def get_alias_values(self):
#         values = super(MaintenanceEquipmentCategory, self).get_alias_values()
#         values['alias_defaults'] = {'category_id': self.id}
#         return values
#
#
# class MaintenanceEquipment(models.Model):
#     _name = 'maintenance.equipment'
#     _inherit = ['mail.thread', 'mail.activity.mixin']
#     _description = 'Maintenance Equipment'
#     _check_company_auto = True
#
#     def _track_subtype(self, init_values):
#         self.ensure_one()
#         if 'owner_user_id' in init_values and self.owner_user_id:
#             return self.env.ref('maintenance.mt_mat_assign')
#         return super(MaintenanceEquipment, self)._track_subtype(init_values)
#
#     def name_get(self):
#         result = []
#         for record in self:
#             if record.name and record.serial_no:
#                 result.append((record.id, record.name + '/' + record.serial_no))
#             if record.name and not record.serial_no:
#                 result.append((record.id, record.name))
#         return result
#
#     @api.model
#     def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
#         args = args or []
#         equipment_ids = []
#         if name:
#             equipment_ids = self._search([('name', '=', name)] + args, limit=limit, access_rights_uid=name_get_uid)
#         if not equipment_ids:
#             equipment_ids = self._search([('name', operator, name)] + args, limit=limit, access_rights_uid=name_get_uid)
#         return models.lazy_name_get(self.browse(equipment_ids).with_user(name_get_uid))
#
#     name = fields.Char('Equipment Name', required=True, translate=True)
#     company_id = fields.Many2one('res.company', string='Company',
#         default=lambda self: self.env.company)
#     active = fields.Boolean(default=True)
#     technician_user_id = fields.Many2one('res.users', string='Technician', tracking=True)
#     owner_user_id = fields.Many2one('res.users', string='Owner', tracking=True)
#     category_id = fields.Many2one('maintenance.equipment.category', string='Equipment Category',
#                                   tracking=True, group_expand='_read_group_category_ids')
#     partner_id = fields.Many2one('res.partner', string='Vendor', check_company=True)
#     partner_ref = fields.Char('Vendor Reference')
#     location = fields.Char('Location')
#     model = fields.Char('Model')
#     serial_no = fields.Char('Serial Number', copy=False)
#     assign_date = fields.Date('Assigned Date', tracking=True)
#     effective_date = fields.Date('Effective Date', default=fields.Date.context_today, required=True, help="Date at which the equipment became effective. This date will be used to compute the Mean Time Between Failure.")
#     cost = fields.Float('Cost')
#     note = fields.Text('Note')
#     warranty_date = fields.Date('Warranty Expiration Date')
#     color = fields.Integer('Color Index')
#     scrap_date = fields.Date('Scrap Date')
#     maintenance_ids = fields.One2many('maintenance.request', 'equipment_id')
#     maintenance_count = fields.Integer(compute='_compute_maintenance_count', string="Maintenance Count", store=True)
#     maintenance_open_count = fields.Integer(compute='_compute_maintenance_count', string="Current Maintenance", store=True)
#     period = fields.Integer('Days between each preventive maintenance')
#     next_action_date = fields.Date(compute='_compute_next_maintenance', string='Date of the next preventive maintenance', store=True)
#     maintenance_team_id = fields.Many2one('maintenance.team', string='Maintenance Team', check_company=True)
#     maintenance_duration = fields.Float(help="Maintenance Duration in hours.")
#
#     @api.depends('effective_date', 'period', 'maintenance_ids.request_date', 'maintenance_ids.close_date')
#     def _compute_next_maintenance(self):
#         date_now = fields.Date.context_today(self)
#         equipments = self.filtered(lambda x: x.period > 0)
#         for equipment in equipments:
#             next_maintenance_todo = self.env['maintenance.request'].search([
#                 ('equipment_id', '=', equipment.id),
#                 ('maintenance_type', '=', 'preventive'),
#                 ('stage_id.done', '!=', True),
#                 ('close_date', '=', False)], order="request_date asc", limit=1)
#             last_maintenance_done = self.env['maintenance.request'].search([
#                 ('equipment_id', '=', equipment.id),
#                 ('maintenance_type', '=', 'preventive'),
#                 ('stage_id.done', '=', True),
#                 ('close_date', '!=', False)], order="close_date desc", limit=1)
#             if next_maintenance_todo and last_maintenance_done:
#                 next_date = next_maintenance_todo.request_date
#                 date_gap = next_maintenance_todo.request_date - last_maintenance_done.close_date
#                 # If the gap between the last_maintenance_done and the next_maintenance_todo one is bigger than 2 times the period and next request is in the future
#                 # We use 2 times the period to avoid creation too closed request from a manually one created
#                 if date_gap > timedelta(0) and date_gap > timedelta(days=equipment.period) * 2 and next_maintenance_todo.request_date > date_now:
#                     # If the new date still in the past, we set it for today
#                     if last_maintenance_done.close_date + timedelta(days=equipment.period) < date_now:
#                         next_date = date_now
#                     else:
#                         next_date = last_maintenance_done.close_date + timedelta(days=equipment.period)
#             elif next_maintenance_todo:
#                 next_date = next_maintenance_todo.request_date
#                 date_gap = next_maintenance_todo.request_date - date_now
#                 # If next maintenance to do is in the future, and in more than 2 times the period, we insert an new request
#                 # We use 2 times the period to avoid creation too closed request from a manually one created
#                 if date_gap > timedelta(0) and date_gap > timedelta(days=equipment.period) * 2:
#                     next_date = date_now + timedelta(days=equipment.period)
#             elif last_maintenance_done:
#                 next_date = last_maintenance_done.close_date + timedelta(days=equipment.period)
#                 # If when we add the period to the last maintenance done and we still in past, we plan it for today
#                 if next_date < date_now:
#                     next_date = date_now
#             else:
#                 next_date = equipment.effective_date + timedelta(days=equipment.period)
#             equipment.next_action_date = next_date
#         (self - equipments).next_action_date = False
#
#     @api.depends('maintenance_ids.stage_id.done')
#     def _compute_maintenance_count(self):
#         for equipment in self:
#             equipment.maintenance_count = len(equipment.maintenance_ids)
#             equipment.maintenance_open_count = len(equipment.maintenance_ids.filtered(lambda x: not x.stage_id.done))
#
#     @api.onchange('company_id')
#     def _onchange_company_id(self):
#         if self.company_id and self.maintenance_team_id:
#             if self.maintenance_team_id.company_id and not self.maintenance_team_id.company_id.id == self.company_id.id:
#                 self.maintenance_team_id = False
#
#     @api.onchange('category_id')
#     def _onchange_category_id(self):
#         self.technician_user_id = self.category_id.technician_user_id
#
#     _sql_constraints = [
#         ('serial_no', 'unique(serial_no)', "Another asset already exists with this serial number!"),
#     ]
#
#     @api.model
#     def create(self, vals):
#         equipment = super(MaintenanceEquipment, self).create(vals)
#         if equipment.owner_user_id:
#             equipment.message_subscribe(partner_ids=[equipment.owner_user_id.partner_id.id])
#         return equipment
#
#     def write(self, vals):
#         if vals.get('owner_user_id'):
#             self.message_subscribe(partner_ids=self.env['res.users'].browse(vals['owner_user_id']).partner_id.ids)
#         return super(MaintenanceEquipment, self).write(vals)
#
#     @api.model
#     def _read_group_category_ids(self, categories, domain, order):
#         """ Read group customization in order to display all the categories in
#             the kanban view, even if they are empty.
#         """
#         category_ids = categories._search([], order=order, access_rights_uid=SUPERUSER_ID)
#         return categories.browse(category_ids)
#
#     def _create_new_request(self, date):
#         self.ensure_one()
#         self.env['maintenance.request'].create({
#             'name': _('Preventive Maintenance - %s') % self.name,
#             'request_date': date,
#             'schedule_date': date,
#             'category_id': self.category_id.id,
#             'equipment_id': self.id,
#             'maintenance_type': 'preventive',
#             'owner_user_id': self.owner_user_id.id,
#             'user_id': self.technician_user_id.id,
#             'maintenance_team_id': self.maintenance_team_id.id,
#             'duration': self.maintenance_duration,
#             'company_id': self.company_id.id or self.env.company.id
#             })
#
#     @api.model
#     def _cron_generate_requests(self):
#         """
#             Generates maintenance request on the next_action_date or today if none exists
#         """
#         for equipment in self.search([('period', '>', 0)]):
#             next_requests = self.env['maintenance.request'].search([('stage_id.done', '=', False),
#                                                     ('equipment_id', '=', equipment.id),
#                                                     ('maintenance_type', '=', 'preventive'),
#                                                     ('request_date', '=', equipment.next_action_date)])
#             if not next_requests:
#                 equipment._create_new_request(equipment.next_action_date)
#

class MaintenanceRequest(models.Model):
    _name = 'sharevan.maintenance.request'
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']
    _inherits = {'fleet.vehicle.cost': 'cost_id'}
    _description = 'Maintenance Request'
    _order = "id desc"
    _check_company_auto = True

    # vehicle_id = fields.Many2one('fleet.vehicle', 'vehicle',domain="[('state_id','!='," + str(VehicleStateStatus.Downgraded.value) + ")]")
    vehicle = fields.Float(help="Vehicle_id")
    status = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted'),
                               ('draft', 'Draft')
                               ], 'Status', default="running")

    cost_id = fields.Many2one('fleet.vehicle.cost', 'Cost', required=True, ondelete='cascade')

    @api.model
    def default_get(self, default_fields):
        res = super(MaintenanceRequest, self).default_get(default_fields)
        maintenance = self.env.ref('fleet.type_maintenance_repairing', raise_if_not_found=False)
        res.update({
            'date': fields.Date.context_today(self),
            'cost_subtype_id': maintenance and maintenance.id or False,
            'cost_type': 'maintenance'
        })
        return res

    @api.returns('self')
    def _default_stage(self):
        return self.env['sharevan.maintenance.stage'].search([], limit=1)

    @api.returns('self')
    def _default_vehicle(self):
        # fix
        downgradedState = http.request[FleetVehicleState._name].get_id_by_code(VehicleStateStatus.Downgraded.value)
        return self.env['fleet.vehicle'].search(
            [('active', '=', True), ('state_id', '!=', downgradedState)])

    def _creation_subtype(self):

        return self.env.ref('fleet.mt_req_created')

    # @api.onchange('vehicle_id')
    # def onChangeVehicle(self):
    #     for id in self:
    #         print(id)

    def _track_subtype(self, init_values):
        print('_track_subtype_self: ', self)
        self.ensure_one()
        print('init_values: ', init_values)
        if 'stage_id' in init_values:
            return self.env.ref('fleet.mt_req_status')
        return super(MaintenanceRequest, self)._track_subtype(init_values)

    def _get_default_team_id(self):
        MT = self.env['sharevan.maintenance.team']
        team = MT.search([('company_id', '=', self.env.company.id)], limit=1)
        if not team:
            team = MT.search([], limit=1)
        return team.id

    name = fields.Char('Subjects', required=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    description = fields.Text('Description')
    request_date = fields.Date('Request Date', tracking=True, default=fields.Date.context_today,
                               help="Date requested for the maintenance to happen")
    owner_user_id = fields.Many2one('res.users', string='Created by User', default=lambda s: s.env.uid)
    # category_id = fields.Many2one('maintenance.equipment.category', related='equipment_id.category_id', string='Category', store=True, readonly=True)
    # equipment_id = fields.Many2one('maintenance.equipment', string='Equipment',
    #                               ondelete='restrict', index=True, check_company=True)
    user_id = fields.Many2one('res.users', string='Technician', tracking=True, required=True,
                              domain=lambda self: [('user_id.company_id.id', '=', self.env.company.id)])
    stage_id = fields.Many2one('sharevan.maintenance.stage', string='Stage', ondelete='restrict', tracking=True,
                               group_expand='_read_group_stage_ids', default=_default_stage, copy=False)
    priority = fields.Selection([('0', 'Very Low'), ('1', 'Low'), ('2', 'Normal'), ('3', 'High')], string='Priority')
    color = fields.Integer('Color Index')
    close_date = fields.Date('Close Date', help="Date the maintenance was finished. ")
    kanban_state = fields.Selection(
        [('normal', 'In Progress'), ('blocked', 'Blocked'), ('done', 'Ready for next stage')],
        string='Kanban State', required=True, default='normal', tracking=True)
    # active = fields.Boolean(default=True, help="Set active to false to hide the maintenance request without deleting it.")
    archive = fields.Boolean(default=False,
                             help="Set archive to true to hide the maintenance request without deleting it.")
    maintenance_type = fields.Selection([('corrective', 'Corrective'), ('preventive', 'Preventive')],
                                        string='Maintenance Type', default="corrective")
    schedule_date = fields.Datetime('Scheduled Date', required=True,
                                    help="Date the maintenance team plans the maintenance. "
                                         "It should not differ much from the Request Date. ")
    maintenance_team_id = fields.Many2one('sharevan.maintenance.team', string='Team',
                                          default=_get_default_team_id, check_company=True,
                                          domain=[('status', '=', 'running'), ])
    maintenance_partner_id = fields.Many2one('sharevan.vendor', 'Vendor',
                                             domain=[('status', '=', 'running'), ('type', '=', 'maintenance_service')])
    duration = fields.Float(help="Duration in hours.")
    done = fields.Boolean(related='stage_id.done')
    cost_amount = fields.Float(related='cost_id.amount', string='Amount', store=True, readonly=False)

    # def archive_equipment_request(self):
    #     self.write({'archive': True})
    #
    # def reset_equipment_request(self):
    #     """ Reinsert the maintenance request into the maintenance pipe in the first stage"""
    #     first_stage_obj = self.env['sharevan.maintenance.stage'].search([], order="sequence asc", limit=1)
    #     # self.write({'active': True, 'stage_id': first_stage_obj.id})
    #     self.write({'archive': False, 'stage_id': first_stage_obj.id})

    @api.constrains("duration")
    def validate_duration(self):
        for record in self:
            if record.duration < 0:
                raise ValidationError("Maintenance duration must be a positive value: %s" % record.duration)

    # @api.onchange('company_id')
    # def _onchange_company_id(self):
    #     if self.company_id and self.maintenance_team_id:
    #         if self.maintenance_team_id.company_id and not self.maintenance_team_id.company_id.id == self.company_id.id:
    #             self.maintenance_team_id = False

    @api.onchange('schedule_date')
    def schedule_date_validate(self):
        for record in self:
            if record.duration < 0:
                raise ValidationError("Maintenance duration must be a positive value: %s" % record.duration)
            utc_dt = datetime.now(timezone.utc)
            time_zone_str = format(utc_dt.astimezone().isoformat())
            time_utc_str = ""
            for element in range(0, len(time_zone_str)):
                if element == 26 or element == 27 or element == 28  :
                    time_utc_str +=  time_zone_str[element]
            if datetime.now() > record['schedule_date'] + timedelta(hours= int(time_utc_str)):
                raise ValidationError(_('Sorry, Schedule Date Must be greater Than Request Date...'))


    @api.model
    def create(self, vals):
        vals['vehicle'] = vals['vehicle_id']
        # stage maintenance
        newStage = self.env['sharevan.maintenance.stage'].search([('code', '=', StageMaintenanceType.New.value)],
                                                                 limit=1).id
        progressStage = self.env['sharevan.maintenance.stage'].search(
            [('code', '=', StageMaintenanceType.Progress.value)], limit=1).id
        repairedStage = self.env['sharevan.maintenance.stage'].search(
            [('code', '=', StageMaintenanceType.Repaired.value)], limit=1).id
        scrapStage = self.env['sharevan.maintenance.stage'].search([('code', '=', StageMaintenanceType.Scrap.value)],
                                                                   limit=1).id
        # state vehicle

        availableState = self.env['fleet.vehicle.state'].search([('code', '=', VehicleStateStatus.Available.value)],
                                                                limit=1).id

        downgradedState = self.env['fleet.vehicle.state'].search([('code', '=', VehicleStateStatus.Downgraded.value)],
                                                                 limit=1).id
        maintenanceState = self.env['fleet.vehicle.state'].search([('code', '=', VehicleStateStatus.Maintenance.value)],
                                                                  limit=1).id
        # context: no_log, because subtype already handle this
        # if vals.get('schedule_date'):
        #     schedule_date = datetime.strptime(vals.get('schedule_date'), "%Y-%m-%d %H:%M:%S")


        if vals.get('vehicle_id') and vals.get('stage_id'):
            vehicle_update = self.env['fleet.vehicle'].search([('id', '=', vals.get('vehicle_id'))], limit=1)
            if (vals.get('stage_id') == newStage or
                    vals.get('stage_id') == progressStage):
                vals['status'] = StatusType.Running.value
                vehicle_update.write({'state_id': maintenanceState})
            else:
                vals['status'] = StatusType.Running.value
                if vals.get('stage_id') == repairedStage:
                    count = self.env['sharevan.maintenance.request'].search_count(
                        [('vehicle_id', '=', vals.get('vehicle_id')),
                         ('stage_id', 'in', (
                             newStage,
                             progressStage)),
                         ('status', '=', 'running')])
                    if count == 0:
                        vehicle_update.write({'state_id': availableState})
                else:
                    vehicle_update.write({'state_id': downgradedState})

                    lst_maintenance_vehicle_upd = self.env['sharevan.maintenance.request'].search(
                        [('vehicle_id', '=', vehicle_update.id),
                         ('status', '=', 'running'),
                         ('stage_id', 'in', (newStage, progressStage))])

                    for i in lst_maintenance_vehicle_upd:
                        i.write({'running': 'deleted'})

        request = super(MaintenanceRequest, self).create(vals)
        if request.owner_user_id or request.user_id:
            request._add_followers()
        # if request.vehicle_id and not request.maintenance_team_id:
        #     request.maintenance_team_id = request.equipment_id.maintenance_team_id
        request.activity_update()
        return request

    def write(self, vals):
        # Overridden to reset the kanban_state to normal whenever
        # the stage (stage_id) of the Maintenance Request changes.
        # stage maintenance
        if 'vehicle_id' in vals:
            vals['vehicle'] = vals['vehicle_id']
        newStage = self.env['sharevan.maintenance.stage'].search([('code', '=', StageMaintenanceType.New.value)],
                                                                 limit=1).id
        progressStage = self.env['sharevan.maintenance.stage'].search(
            [('code', '=', StageMaintenanceType.Progress.value)], limit=1).id
        repairedStage = self.env['sharevan.maintenance.stage'].search(
            [('code', '=', StageMaintenanceType.Repaired.value)], limit=1).id
        scrapStage = self.env['sharevan.maintenance.stage'].search([('code', '=', StageMaintenanceType.Scrap.value)],
                                                                   limit=1).id
        # state vehicle

        availableState = self.env['fleet.vehicle.state'].search([('code', '=', VehicleStateStatus.Available.value)],
                                                                limit=1).id
        downgradedState = self.env['fleet.vehicle.state'].search([('code', '=', VehicleStateStatus.Downgraded.value)],
                                                                 limit=1).id
        maintenanceState = self.env['fleet.vehicle.state'].search([('code', '=', VehicleStateStatus.Maintenance.value)],
                                                                  limit=1).id
        # iot = VehicleEquipmentPart.IOT.value

        if self.id > 0 and self.status == 'deleted':
            raise ValidationError(_('You cannot edit maintenance request that has been deleted!!!!!'))
        if self.stage_id.id in (repairedStage, scrapStage):
            raise ValidationError(_('You cannot edit maintenance request that has been Repaired or Scrapped!'))
            # validate time
        # if datetime.datetime.now() > self.schedule_date:
        #     raise ValidationError(_('Sorry, Schedule Date Must be greater Than Request Date...'))

        if vals and 'kanban_state' not in vals and 'stage_id' in vals:
            vals['kanban_state'] = 'normal'
        if self.cost_id.vehicle_id.id > 0 and vals.get('stage_id'):
            vehicle_update = self.env['fleet.vehicle'].search([('id', '=', self.cost_id.vehicle_id.id)], limit=1)
            if vehicle_update:
                if (vals.get('stage_id') == newStage or vals.get(
                        'stage_id') == progressStage):

                    vehicle_update.write({'state_id': maintenanceState})
                else:
                    vals['close_date'] = fields.Date.today()
                    self.activity_feedback(['fleet.mail_act_maintenance_request'])
                    if vals.get('stage_id') == repairedStage:
                        count = self.env['sharevan.maintenance.request'].search_count(
                            [('vehicle_id', '=', self.vehicle_id.id),
                             ('stage_id', 'in', (
                                 newStage,
                                 progressStage)),
                             ('status', '=', 'running')])
                        update_param = {}
                        update_param['sos_status'] = VehicleSosType.NORMAL.value
                        if ('maintenance_type' in vals and vals['maintenance_type'] == 'preventive') \
                                or self.maintenance_type == 'preventive':
                            update_param = {
                                'last_odometer': vehicle_update.odometer,
                                'last_maintenance': str(datetime.utcnow())
                            }
                        if count == 1:
                            update_param['state_id'] = availableState
                            vehicle_update.write(update_param)
                    else:

                        vehicle_update.write({'state_id': downgradedState})

                        lst_maintenance_vehicle_upd = self.env['sharevan.maintenance.request'].search(
                            [('vehicle_id', '=', vehicle_update.id),
                             ('status', '=', 'running'),
                             ('stage_id', 'in', (newStage, progressStage)),
                             ('id', '!=', self.id)])
                        for i in lst_maintenance_vehicle_upd:
                            i.write({'status': 'deleted'})
        res = super(MaintenanceRequest, self).write(vals)
        if vals.get('owner_user_id') or vals.get('user_id'):
            self._add_followers()
        if vals.get('user_id') or vals.get('schedule_date'):
            self.activity_update()
        # if vals.get('equipment_id'):
        #     # need to change description of activity also so unlink old and create new activity
        #     self.activity_unlink(['maintenance.mail_act_maintenance_request'])
        #     self.activity_update()
        self.flush()
        return self

    def activity_update(self):
        """ Update maintenance activities based on current record set state.
        It reschedule, unlink or create maintenance request activities. """
        self.filtered(lambda request: not request.schedule_date).activity_unlink(
            ['maintenance.mail_act_maintenance_request'])
        for request in self.filtered(lambda request: request.schedule_date):
            date_dl = fields.Datetime.from_string(request.schedule_date).date()
            updated = request.activity_reschedule(
                ['fleet.mail_act_maintenance_request'],
                date_deadline=date_dl,
                new_user_id=request.user_id.id or request.owner_user_id.id or self.env.uid)
            if not updated:
                if request.vehicle_id:
                    note = _('Request planned for <a href="#" data-oe-model="%s" data-oe-id="%s"></a>') % (
                        request.vehicle_id._name, request.vehicle_id.id)
                else:
                    note = False
                request.activity_schedule(
                    'fleet.mail_act_maintenance_request',
                    fields.Datetime.from_string(request.schedule_date).date(),
                    note=note, user_id=request.user_id.id or request.owner_user_id.id or self.env.uid)

    def _add_followers(self):
        for request in self:
            partner_ids = (request.owner_user_id.partner_id + request.user_id.partner_id).ids
            request.message_subscribe(partner_ids=partner_ids)

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        """ Read group customization in order to display all the stages in the
            kanban view, even if they are empty
        """
        stage_ids = stages._search([], order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)

    def unlink(self):
        availableState = self.env['fleet.vehicle.state'].search([('code', '=', VehicleStateStatus.Available.value)],
                                                                limit=1).id
        iot = VehicleEquipmentPart.IOT.value
        for id_value in self.ids:
            maintenance = self.env['sharevan.maintenance.request'].search([('id', '=', id_value)])
            if maintenance.stage_id.id == StageMaintenanceType.Repaired.value \
                    or maintenance.stage_id.id == StageMaintenanceType.Scrap.value:
                raise ValidationError(
                    _('You cannot delete maintenance request that has been Repaired or Scraped!' + maintenance.name))
            maintenance.write({'status': 'deleted'})
            vehicle_update = self.env['fleet.vehicle'].search([('id', '=', maintenance.vehicle_id.id)])

            # self.env.cr.execute(
            #     """select COUNT(vehicle) from fleet_vehicle_equipment_part where  vehicle = %s 
            #     and type_device  = %s  and status = 'running' """,
            #     (vehicle_update.id,iot))
            # equipmentCount = self.env.cr.fetchall()
            #
            # for count in equipmentCount[0]:
            #     count_eq = count
            vehicle_update.write({'state_id': availableState})
            cost_maintenance = self.env['fleet.vehicle.cost'].search(
                [('id', '=', maintenance.cost_id.id), ('vehicle_id', '=', maintenance.vehicle_id.id)])
            cost_maintenance.write({'status': StatusType.Deleted.value})
        return self


class MaintenanceTeam(models.Model):
    _name = 'sharevan.maintenance.team'
    _description = 'Maintenance Teams'

    name = fields.Char('Team Name', required=True, translate=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    member_ids = fields.Many2many(
        'res.users', 'sharevan_maintenance_team_users_rel', string="Team Members",
        domain="[('company_ids', 'in', company_id)]")
    color = fields.Integer("Color Index", default=0)
    request_ids = fields.One2many('sharevan.maintenance.request', 'maintenance_team_id', copy=False)
    # equipment_ids = fields.One2many('maintenance.equipment', 'maintenance_team_id', copy=False)
    # vehicle_id = fields.One2many('fleet.vehicle','maintenance_team_id', copy=False)
    # For the dashboard only
    todo_request_ids = fields.One2many('sharevan.maintenance.request', string="Requests", copy=False,
                                       compute='_compute_todo_requests')
    todo_request_count = fields.Integer(string="Number of Requests", compute='_compute_todo_requests')
    todo_request_count_date = fields.Integer(string="Number of Requests Scheduled", compute='_compute_todo_requests')
    todo_request_count_high_priority = fields.Integer(string="Number of Requests in High Priority",
                                                      compute='_compute_todo_requests')
    todo_request_count_block = fields.Integer(string="Number of Requests Blocked", compute='_compute_todo_requests')
    todo_request_count_unscheduled = fields.Integer(string="Number of Requests Unscheduled",
                                                    compute='_compute_todo_requests')
    status = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted')], 'Status', default="running")

    def unlink(self):
        for id in self.ids:
            record = self.env['sharevan.maintenance.team'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })
        return self

    @api.depends('request_ids.stage_id.done')
    def _compute_todo_requests(self):
        for team in self:
            team.todo_request_ids = team.request_ids.filtered(lambda e: e.stage_id.done == False)
            team.todo_request_count = len(team.todo_request_ids)
            team.todo_request_count_date = len(team.todo_request_ids.filtered(lambda e: e.schedule_date != False))
            team.todo_request_count_high_priority = len(team.todo_request_ids.filtered(lambda e: e.priority == '3'))
            team.todo_request_count_block = len(team.todo_request_ids.filtered(lambda e: e.kanban_state == 'blocked'))
            team.todo_request_count_unscheduled = len(team.todo_request_ids.filtered(lambda e: not e.schedule_date))

    # @api.depends('equipment_ids')
    # def _compute_equipment(self):
    #     for team in self:
    #         team.equipment_count = len(team.equipment_ids)


class MaintenanceSchedule(models.Model):
    _name = 'fleet.maintenance.schedule'
    _description = 'Fleet maintenance schedule'
    _inherit = 'mail.thread'

    name = fields.Char('Schedule name', required="True")
    start_date = fields.Date('Start date')
    day_interval = fields.Integer(string='Interval (days)', help='Number of days between maintenance')
    odometer_interval = fields.Float(string='Odometer interval', help='Number in odometer between maintenance')
    odometer_unit = fields.Selection([
        ('kilometers', 'Kilometers'),
        ('miles', 'Miles')
    ], 'Odometer Unit', default='kilometers', help='Unit of the odometer ', required=True)
    notify_date_before = fields.Integer(string='Warning before (days)', help='Number of days before need maintenance')
    notify_odometer_before = fields.Float(string='Warning before (Odometer)',
                                          help='Odometer value before need maintenance')
    status = fields.Selection([
        ('0', 'disabled'),
        ('1', 'enabled')
    ], 'Status', default='1', required=True)
    activity_user_id = fields.Integer()

    @api.model
    def create(self, vals):
        if 'start_date' in vals:
            startTime = datetime.strptime(str(vals['start_date']), '%Y-%m-%d')
            current_date = datetime.strptime(str(date.today()), '%Y-%m-%d')
            if startTime < current_date:
                raise ValidationError('Start date must be greater than current date!')

            if 'day_interval' in vals:
                validate_utils.check_number_smaller_than_0('Day interval',vals['day_interval'])

            if 'odometer_interval' in vals:
                validate_utils.check_number_smaller_than_0('Odometer interval',vals['odometer_interval'])

            if 'notify_date_before' in vals:
                validate_utils.check_number_smaller_than_0('Notify date before',vals['notify_date_before'])

            if 'notify_odometer_before' in vals:
                validate_utils.check_number_smaller_than_0('Notify odometer before', vals['notify_odometer_before'])

        result = super(MaintenanceSchedule, self).create(vals)
        return result

    def write(self, vals):
        if 'start_date' in vals:
            startTime = datetime.strptime(str(vals['start_date']), '%Y-%m-%d')
            current_date = datetime.strptime(str(date.today()), '%Y-%m-%d')
            if startTime < current_date:
                raise ValidationError('Start date must be greater than current date!')
        if 'day_interval' in vals:
            validate_utils.check_number_smaller_than_0('Day interval', vals['day_interval'])

        if 'odometer_interval' in vals:
            validate_utils.check_number_smaller_than_0('Odometer interval', vals['odometer_interval'])

        if 'notify_date_before' in vals:
            validate_utils.check_number_smaller_than_0('Notify date before', vals['notify_date_before'])

        if 'notify_odometer_before' in vals:
            validate_utils.check_number_smaller_than_0('Notify odometer before', vals['notify_odometer_before'])
        result = super(MaintenanceSchedule, self).write(vals)
        return result

    @api.onchange('odometer_unit')
    def onchange_odometer_unit(self):
        if self.odometer_interval == 0 and self.notify_odometer_before == 0:
            return 0
        if self.odometer_unit == 'miles':
            self.odometer_interval = self.odometer_interval * 1.609344
            self.notify_odometer_before = self.notify_odometer_before * 1.609344
        if self.odometer_unit == 'kilometers':
            self.odometer_interval = self.odometer_interval * 0.621371192
            self.notify_odometer_before = self.notify_odometer_before * 0.621371192

    def _scan_vehicle_need_maintenance(self):
        self.env.cr.execute("""
            select fv.id, fv.name, fv.last_maintenance, (fv.last_maintenance + mtn.day_interval) as maintenance_day,
            od1.value as odometer, (fv.last_odometer + mtn.odometer_interval) maintenance_odometer, mtn.id res_id,
            (od1.value - mtn.odometer_interval - mtn.notify_meter_before - fv.last_odometer) over_meter
            from fleet_vehicle fv
            inner join fleet_maintenance_schedule mtn on fv.maintenance_schedule = mtn.id
            JOIN fleet_vehicle_odometer od1 ON (fv.id = od1.vehicle_id)
            LEFT OUTER JOIN fleet_vehicle_odometer od2 ON (fv.id = od2.vehicle_id AND
                (od1.date < od2.date OR (od1.date = od2.date AND od1.id < od2.id)))
            where od2.id IS NULL and
            ((current_date - mtn.day_interval - mtn.notify_date_before > fv.last_maintenance) -- Near maintenance date
            or (od1.value - mtn.odometer_interval - mtn.notify_meter_before > fv.last_odometer)) -- Near odometer value that need maintenance
        """)
        list_res = self.env.cr.dictfetchall()
        activity_type = self.env['mail.activity.type'].search([('name', '=', 'Warn of vehicles need maintenance')])
        res_model = self.env['ir.model'].search([('model', '=', 'fleet.maintenance.schedule')], limit=1).id
        for record in list_res:
            if record['over_meter'] > 0:
                date_deadline = datetime.now() - timedelta(1)
            else:
                date_deadline = record['maintenance_day']
            self.env['mail.activity'].create({
                'summary': 'Warn of vehicles need maintenance',
                'activity_type_id': activity_type.id,
                'automated': True,
                'note': activity_type.default_description,
                'date_deadline': date_deadline,
                'res_model_id': res_model,
                'res_id': record['res_id'],
                'user_id': self.env.uid
            })

    @api.model
    def get_vehicles_need_maintenance(self):
        self.env.cr.execute("""
            select fv.id
            from fleet_vehicle fv
            inner join fleet_maintenance_schedule mtn on fv.maintenance_schedule = mtn.id
            JOIN fleet_vehicle_odometer od1 ON (fv.id = od1.vehicle_id)
            LEFT OUTER JOIN fleet_vehicle_odometer od2 ON (fv.id = od2.vehicle_id AND
                (od1.date < od2.date OR (od1.date = od2.date AND od1.id < od2.id)))
            where od2.id IS NULL and
            ((current_date - mtn.day_interval - mtn.notify_date_before > fv.last_maintenance) -- Near maintenance date
            or (od1.value - mtn.odometer_interval - mtn.notify_odometer_before > fv.last_odometer)) -- Near odometer value that need maintenance
        """)
        list_id = self.env.cr.fetchall()
        return tuple([item[0] for item in list_id])

    @api.model
    def get_vehicles_need_abc(self):
        abc = 212
        fd = 312
        self.env['mail.activity'].sudo().search(
            [('res_model', '=', self._name), ('id', '=', 5)]
        ).unlink()
        # query = """SELECT m.id, count(*), act.res_model as model,
        #                                     CASE
        #                                         WHEN %(today)s::date - act.date_deadline::date = 0 Then 'today'
        #                                         WHEN %(today)s::date - act.date_deadline::date > 0 Then 'overdue'
        #                                         WHEN %(today)s::date - act.date_deadline::date < 0 Then 'planned'
        #                                     END AS states,
        #                                     act.summary
        #                                 FROM mail_activity AS act
        #                                 JOIN ir_model AS m
        #                                     ON act.res_model_id = m.id
        #                                 LEFT OUTER JOIN mail_activity act2
        #                                     ON (act.id < act2.id AND act.res_id = act2.res_id AND act.res_model_id = act2.res_model_id)
        #                                 WHERE act.user_id = %(user_id)s AND act2.id is NULL
        #                                 GROUP BY m.id, states, act.res_id, act.res_model, act.summary;
        #                                 """
        # self.env.cr.execute(query, {
        #     'today': fields.Date.context_today(self),
        #     'user_id': self.env.uid,
        # })
        # activity_data = self.env.cr.dictfetchall()
        # model_ids = [a['id'] for a in activity_data]
        # model_names = {n[0]: n[1] for n in self.env['ir.model'].browse(model_ids).name_get()}
        #
        # user_activities = {}
        # for activity in activity_data:
        #     if not user_activities.get(activity['model']):
        #         module = self.env[activity['model']]._original_module
        #         icon = module and modules.module.get_module_icon(module)
        #         user_activities[activity['model']] = {
        #             'name': activity['summary'] if activity['model'] == 'fleet.maintenance.schedule' else model_names[
        #                 activity['id']],
        #             'model': activity['model'],
        #             'type': 'activity',
        #             'icon': icon,
        #             'total_count': 0, 'today_count': 0, 'overdue_count': 0, 'planned_count': 0,
        #         }
        #     user_activities[activity['model']]['%s_count' % activity['states']] += activity['count']
        #     if activity['states'] in ('today', 'overdue'):
        #         user_activities[activity['model']]['total_count'] += activity['count']
        #
        #     user_activities[activity['model']]['actions'] = [{
        #         'icon': 'fa-clock-o',
        #         'name': 'Summary',
        #     }]
        # return list(user_activities.values())
