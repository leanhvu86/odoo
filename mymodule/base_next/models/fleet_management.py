import datetime
from datetime import datetime, date

from mymodule.base_next.models.cargo import Cargo
from odoo import api
from odoo import http
from odoo import models, _, fields
from odoo.exceptions import ValidationError
from .utils import validate_utils as validate
from ..controllers.api.base_method import BaseMethod
from ...enum.FleetEmployeeType import FleetEmployeeType
from ...enum.MessageType import NotificationSocketType


class FleetManagement(models.Model):
    _name = "fleet.management"
    _description = "Fleet management"
    _order = "create_date desc, update_date desc"

    parking_point_id = fields.Many2one('parking.point', 'Parking point',
                                       domain=lambda self: "[('status','=','running')]")
    # fleet_driver_id = fields.Many2many('fleet.driver', 'fleet_management_driver_relate', 'fleet_management_id', 'fleet_driver_id',
    #                            'Fleet driver')
    #
    # fleet_vehicle_id = fields.Many2many('fleet.vehicle',  'fleet_management_vehicle_relate', 'fleet_management_id', 'fleet_vehicle_id',
    #                            'Fleet vehicle')

    # fleet_driver_temp_id = fields.Many2many('fleet.management.driver.temp', 'fleet_management_id', string='Lines',
    #                                         copy=True, readonly=False, domain=[('to_date', '=',False)])
    # fleet_vehicle_temp_id = fields.Many2many('fleet.management.vehicle.temp', 'fleet_management_vehicle_id',
    #                                          string='Lines',
    #                                          copy=True, readonly=False)

    fleet_driver_lines = fields.One2many('fleet.management.driver.temp', 'fleet_management_id', required=True,
                                         domain=[('status', '=', 'active'),
                                                 ('fleet_driver_id.employee_type', '!=', 'manager')])
    #####################################################

    fleet_vehicle_lines = fields.One2many('fleet.management.vehicle.temp', 'fleet_management_vehicle_id', required=True,
                                          domain=[('status', '=', 'active')])
    fleet_management = fields.One2many('fleet.management', 'parent_id',
                                       domain=lambda self: [('company_id', '=', self.env.company.id),
                                                            ('status', '=', 'active')])
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)
    name = fields.Char(required=True)
    total_driver = fields.Integer('Total driver', compute='load_all', store=False)
    total_vehicle = fields.Integer('Total vehicle', compute='load_all', store=False)
    code = fields.Char(readonly=True)
    attach_File = fields.Many2many('ir.attachment', string="Attach File")
    status = fields.Selection(
        [('active', 'Active'),
         ('deactive', 'Deactive')
         ],
        string='Status', context={'status': 'running'}, default='active')
    organization_level = fields.Selection(
        [('1', 'Level 1'),
         ('2', 'Level 2'), ('3', 'Level 3'), ('4', 'Level 4'), ('5', 'Level 5'), ('6', 'Level 6'), ('7', 'Level 7'),
         ('8', 'Level 8'), ('9', 'Level 9'), ('10', 'Level 10')
         ],
        string='Organization level', default='1', help='Level 1 is highest level')
    parent_id = fields.Many2one('fleet.management', string="Parent",
                                domain=[('status', '=', 'active')])
    manager_id = fields.Many2one('fleet.driver', string="Manager", required=True,
                                 domain=lambda self: [('status', '=', 'running'), ('employee_type', '=', 'manager'),
                                                      ('fleet_management_id', '=', False)])
    create_user = fields.Char()
    update_date = fields.Date()
    from_date = fields.Date(required=True, default=date.today(), readonly=True)
    to_date = fields.Date()
    update_user = fields.Char()
    team_check = fields.Boolean('Group access', required=True, default=True)

    @api.model
    def create(self, vals):
        if not BaseMethod.reject_dlp_employee_on_data(self.env.user):
            raise ValidationError('DLP employee not allow to create or update data of fleet companies')
        vals['from_date'] = date.today()
        if vals['parent_id']:
            parent = http.request.env['fleet.management'].search([('id', '=', vals['parent_id'])])
            vals['organization_level'] = str(int(parent['organization_level']) + 1)
        company_id = self.env.company.id
        record = self.env['fleet.management'].search([('name', '=', vals['name'])])
        if record:
            raise ValidationError('Name was existed in company !')

        vals['code'] = BaseMethod.get_new_sequence('fleet.management', 'FM', 12, 'code')
        vals['company_id'] = company_id
        # if 'to_date' in vals and vals['to_date'] != False:
        #     validate.check_from_date_greater_than_to_date(vals['from_date'], vals['to_date'])
        # validate.check_start_date_greater_than_current_date(vals['from_date'])
        result = super(FleetManagement, self).create(vals)
        today = datetime.today()
        manager = http.request.env['fleet.driver'].search([('id', '=', vals['manager_id'])])
        # manager.write({'fleet_management_id': result['id']})
        log = {
            'fleet_management_id': result['id'],
            'fleet_driver_id': manager['id'],
            'company_id': manager['company_id'].id,
            'is_manager': True,
            'status': 'active',
            'from_date': today,
            'type': FleetEmployeeType.MANAGER.value
        }
        self.env['fleet.management.driver.temp'].create(log)
        return result

    def load_all(self):
        for record in self:
            team_query = """
                WITH RECURSIVE c AS (
                    SELECT (%s) AS id
                UNION ALL
                    SELECT sa.id
                FROM fleet_management AS sa
                    JOIN c ON c.id = sa.parent_id
                )
            SELECT id FROM c 
            """
            self.env.cr.execute(team_query, (record.id,), )
            team_tree = self._cr.dictfetchall()
            ids = []
            for team in team_tree:
                ids.append(team['id'])
            print(ids)
            drivers = self.env['fleet.driver'].search(
                [('fleet_management_id', 'in', ids), ('employee_type', '=', 'driver'), ('status', '=', 'running')])
            driver_count = 0
            if drivers:
                driver_count = len(drivers)
            record.total_driver = driver_count
            vehicles = self.env['fleet.vehicle'].search([('fleet_management_id', 'in', ids)])
            vehicle_count = 0
            if vehicles:
                vehicle_count = len(vehicles)
            print(record['name'] + ' driver count ' + str(driver_count))
            print(' vehicle count ' + str(vehicle_count))
            record.total_vehicle = vehicle_count
        return self

    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        for record in self:
            if int(record['organization_level']) - int(record.parent_id.organization_level) != 1:
                notice = "Parent must higer than one level !"
                self.env.user.notify_danger(message=notice, title=NotificationSocketType.NOTIFICATION.value)
                record.update({'parent_id': False})

    @api.onchange('organization_level')
    def _onchange_organization_level(self):
        for record in self:
            if record.organization_level:
                records = http.request.env['fleet.management'].search(
                    [('company_id', '=', record['company_id'].id), ('organization_level', '=', '1')])
                if not records and record.organization_level != '1':
                    notice = "You have choose parent level from 1 first !"
                    self.env.user.notify_danger(message=notice, title=NotificationSocketType.NOTIFICATION.value)
                    record.update({'organization_level': False})

    @api.onchange('team_check')
    def _onchange_team_check(self):
        for record in self:
            if record.team_check == False:
                records = http.request.env['fleet.management'].search([('company_id', '=', record['company_id'].id)])
                wrong_level = False
                level = False
                for rec in records:
                    if rec['organization_level'] != record['organization_level'] and rec['team_check'] == False:
                        wrong_level = True
                        level = rec['organization_level']
                if wrong_level:
                    notice = "Team level of your company is " + level
                    self.env.user.notify_danger(message=notice, title=NotificationSocketType.NOTIFICATION.value)
                    record.update({'team_check': True})
            else:
                record.update({'organization_level': '1'})

    def write(self, vals):
        if not BaseMethod.reject_dlp_employee_on_data(self.env.user):
            raise ValidationError('DLP employee not allow to create or update data of fleet companies')
        if 'team_check' in vals and vals['team_check'] == False:
            if 'parent_id' in vals and not vals['parent_id']:
                raise ValidationError('Team must belong to one group! ')
            if not self.parent_id:
                raise ValidationError('Team must belong to one group! ')
            if 'parking_point_id' in vals and not vals['parking_point_id']:
                raise ValidationError('Team must have at least one parking point! ')
            if not self.parking_point_id:
                raise ValidationError('Team must have at least one parking point! ')
        elif not self.team_check:
            if 'parent_id' in vals and not vals['parent_id']:
                raise ValidationError('Team must belong to one group! ')
            if not self.parent_id:
                raise ValidationError('Team must belong to one group! ')
            if 'parking_point_id' in vals and not vals['parking_point_id']:
                raise ValidationError('Team must have at least one parking point! ')
            if not self.parking_point_id:
                raise ValidationError('Team must have at least one parking point! ')
        if 'parent_id' in vals and not vals['parent_id']:
            if self.team_check == False:
                raise ValidationError('Team must belong to one group! ')
        if 'fleet_driver_lines' in vals:
            if len(vals['fleet_driver_lines']):
                fleet_driver_id = None
                for rec in vals['fleet_driver_lines']:
                    if rec[2] == False:
                        continue
                    print(' rec[2]', rec[2])
                    fleet_driver = rec[2]
                    print("fleet_driver['fleet_driver_id']", fleet_driver['fleet_driver_id'])
                    if fleet_driver_id == fleet_driver['fleet_driver_id']:
                        record = self.env['fleet.driver'].search([('id', '=', fleet_driver_id)])
                        print('What ', record['display_name'])
                        raise ValidationError('Duplicate driver with name  %s' % record['display_name'])
                    fleet_driver_id = rec[2]['fleet_driver_id']

        if 'fleet_vehicle_lines' in vals:
            if len(vals['fleet_vehicle_lines']):
                fleet_vehicle_id = None
                for rec in vals['fleet_vehicle_lines']:
                    if rec[2] == False:
                        continue
                    print(' rec[2]', rec[2])
                    fleet_vehicle = rec[2];
                    print("fleet_vehicle['fleet_vehicle_id']", fleet_vehicle['fleet_vehicle_id'])
                    if fleet_vehicle_id == fleet_vehicle['fleet_vehicle_id']:
                        record = self.env['fleet.vehicle'].search([('id', '=', fleet_vehicle_id)])
                        print('What ', record['name'])
                        raise ValidationError('Duplicate driver with name  %s' % record['name'])
                    fleet_vehicle_id = rec[2]['fleet_vehicle_id']

        if 'name' in vals:
            record = self.env['fleet.management'].search([('name', '=', vals['name'])])
            if record:
                raise ValidationError('Name was existed in company !')
        if 'from_date' in vals and 'to_date' in vals:
            validate.check_from_date_greater_than_to_date(vals['from_date'], vals['to_date'])
        elif 'from_date' in vals and vals['from_date'] != False:
            validate.check_from_date_greater_than_to_date(vals['from_date'], self['to_date'])
            validate.check_start_date_greater_than_current_date(vals['from_date'])
        elif 'to_date' in vals and vals['to_date'] != False:
            validate.check_from_date_greater_than_to_date(self['from_date'], vals['to_date'])
            t_date = datetime.strptime(str(vals['to_date']), '%Y-%m-%d')
            current = datetime.strptime(str(date.today()), '%Y-%m-%d')
            if t_date <= current:
                vals['status'] = 'deactive'
        if 'status' in vals:
            if vals['status'] == 'deactive':
                vals['to_date'] = date.today()
            else:
                vals['to_date'] = ''
        if 'manager_id' in vals:
            today = date.today()
            if self.manager_id:
                records = http.request.env['fleet.driver'].search(
                    [('id', '=', self.manager_id.id)])

                if records:
                    records.write({'fleet_management_id': False})
                    history_record = self.env['fleet.management.driver.temp'].search(
                        [('fleet_driver_id', '=', records['id']), ('status', '=', 'active')])
                    if history_record:
                        history_record.write(
                            {'to_date': today, 'status': 'deactive'})
            if vals['manager_id']:
                manager = http.request.env['fleet.driver'].search([('id', '=', vals['manager_id'])])
                # manager.write({'fleet_management_id': self.id})
                log = {
                    'fleet_management_id': self.id,
                    'fleet_driver_id': manager['id'],
                    'company_id': manager['company_id'].id,
                    'is_manager': True,
                    'status': 'active',
                    'from_date': today,
                    'type': FleetEmployeeType.MANAGER.value
                }
                self.env['fleet.management.driver.temp'].create(log)
        if 'parking_point_id' in vals:
            if vals['parking_point_id']:
                records_vehicle = self.env['fleet.vehicle'].search(
                    [('fleet_management_id', '=', self['id'])])
                for vehicle in records_vehicle:
                    vehicle.write({'parking_point_id': vals['parking_point_id']})
        result = super(FleetManagement, self).write(vals)
        if 'status' in vals and vals['status'] == 'deactive':
            vals['to_date'] = date.today()
            result = super(FleetManagement, self).write(vals)
            records_driver = self.env['fleet.management.driver.temp'].search(
                [('fleet_management_id', '=', self['id']), ('status', '=', 'active')])
            records_vehicle = self.env['fleet.management.vehicle.temp'].search(
                [('fleet_management_vehicle_id', '=', self['id']), ('status', '=', 'active')])
            today = date.today()
            for rec in records_driver:
                record = self.env['fleet.management.driver.temp'].search(
                    [('id', '=', rec['id']), ('status', '=', 'active')])
                if record:
                    http.request.env['fleet.management.driver.temp']. \
                        browse(record['id']).write(
                        {'to_date': today, 'status': 'deactive'})

                    http.request.env['fleet.driver']. \
                        browse(record['fleet_driver_id']['id']).write(
                        {'fleet_management_id': False})
            for rec in records_vehicle:
                record = self.env['fleet.management.vehicle.temp'].search(
                    [('id', '=', rec['id']), ('status', '=', 'active')])
                if record:
                    http.request.env['fleet.management.vehicle.temp']. \
                        browse(record['id']).write(
                        {'to_date': today, 'status': 'deactive'})

                    http.request.env['fleet.vehicle']. \
                        browse(record['fleet_vehicle_id']['id']).write(
                        {'fleet_management_id': False})
        return result

    def unlink(self):
        raise ValidationError('You are not allow to delete team on running')
        # current_date = date.today()
        # fleet_management_ids = self.ids
        # for id in fleet_management_ids:
        #     result = self.env['fleet.management'].search(
        #         [('id', '=', id), ('status', '=', 'active')])
        #     if result['status'] == 'active':
        #         child = self.env['fleet.management'].search(
        #             [('parent_id', '=', id)])
        #         child.write({'parent_id': False})
        #         http.request.env['fleet.management']. \
        #             browse(id).write(
        #             {'status': 'deactive', 'to_date': current_date})
        #         # update fleet_management_driver_temp and fleet driver
        #         query = """
        #                          SELECT id,fleet_driver_id,fleet_management_id FROM fleet_management_driver_temp
        #                         WHERE fleet_management_id = %s AND status  = 'active' ;
        #                        """
        #         self.env.cr.execute(query, (id,), )
        #         record = self._cr.dictfetchall()
        #         if record:
        #             for rec in record:
        #                 http.request.env['fleet.management.driver.temp']. \
        #                     browse(rec['id']).write(
        #                     {'status': 'deactive', 'to_date': current_date})
        #                 http.request.env['fleet.driver']. \
        #                     browse(rec['fleet_driver_id']).write(
        #                     {'is_selected': False, 'fleet_management_id': False})
        #
        #         # update fleet_management_vehicle_temp and fleet vehicle
        #         query = """
        #                          SELECT id,fleet_vehicle_id,fleet_management_vehicle_id FROM fleet_management_vehicle_temp
        #                         WHERE fleet_management_vehicle_id = %s AND status  = 'active' ;
        #                        """;
        #         self.env.cr.execute(query, (id,), )
        #         record = self._cr.dictfetchall()
        #         if record:
        #             for rec in record:
        #                 http.request.env['fleet.management.vehicle.temp']. \
        #                     browse(rec['id']).write(
        #                     {'status': 'deactive', 'to_date': current_date})
        #                 http.request.env['fleet.vehicle']. \
        #                     browse(rec['fleet_vehicle_id']).write(
        #                     {'is_selected': False, 'fleet_management_id': False})
        #     else:
        #         continue
        # return self


class FleetManagementDriverTemp(models.Model):
    _name = "fleet.management.driver.temp"
    _description = "Fleet management and driver"

    fleet_management_id = fields.Many2one('fleet.management', string="Fleet management")
    fleet_driver_id = fields.Many2one('fleet.driver', string="Fleet driver",
                                      domain=[('fleet_management_id', '=', False), ('status', '=', 'running'),
                                              ('employee_type', '!=', 'manager')])
    phone = fields.Char(related="fleet_driver_id.phone")
    address = fields.Char(related="fleet_driver_id.address")
    company_id = fields.Integer()
    code = fields.Char(readonly=True)
    is_manager = fields.Boolean(default=False)
    status = fields.Selection(
        [('active', 'Active'),
         ('deactive', 'Deactive')
         ],
        string='Status', context={'status': 'running'}, default='active')
    from_date = fields.Date(required=True, default=date.today())
    class_driver = fields.Char(related="fleet_driver_id.class_driver.name")
    point = fields.Integer(related="fleet_driver_id.point", store=False)
    award_id = fields.Many2one('sharevan.title.award', 'Title award', related="fleet_driver_id.award_id", store=False)
    to_date = fields.Date(readonly=True)
    type = fields.Text()

    @api.model
    def create(self, vals):
        today = date.today()
        current_date = datetime.strptime(str(today), '%Y-%m-%d')
        company_id = self.env.company.id
        vals['company_id'] = company_id
        query = """
           SELECT id, fleet_management_id, fleet_driver_id, is_manager, status,
                from_date, to_date, type, create_uid, create_date,
            write_uid, write_date, code, company_id
           FROM public.fleet_management_driver_temp where fleet_driver_id = %s and status = 'active'  order by id DESC LIMIT  1
               """
        self.env.cr.execute(query, (vals['fleet_driver_id'],), )
        record = self._cr.dictfetchall()
        if record:
            if len(record) > 0:
                for data in record:
                    result = self.env['fleet.management'].search(
                        [('id', '=', data['fleet_management_id']), ('status', '=', 'active')])
                    driver = self.env['fleet.driver'].search([('id', '=', data['fleet_driver_id'])])
                    if data['to_date'] is None:
                        raise ValidationError(
                            _(driver['name'].upper() + ' was joining team:  ' + result['name'].upper()))
                    else:
                        pass
                        # from_date_new = datetime.strptime(str(vals['from_date']), '%Y-%m-%d')
                        # to_date_old = datetime.strptime(str(data['to_date']), '%Y-%m-%d')
                        # if from_date_new < to_date_old:
                        #     raise ValidationError(_('From date must be greater than ' + str(to_date_old)))
        # Check driver'date when join fleet_management
        fleet_management = self.env['fleet.management'].search(
            [('id', '=', vals['fleet_management_id']), ('status', '=', 'active')])
        # driver = self.env['fleet.driver'].search([('id', '=', vals['fleet_driver_id'])])
        # from_date_create_fleet_management = datetime.strptime(str(fleet_management['from_date']), '%Y-%m-%d')
        # from_date_fleet_driver_join_team = datetime.strptime(str(vals['from_date']), '%Y-%m-%d')
        # if from_date_fleet_driver_join_team < from_date_create_fleet_management:
        #     raise ValidationError(_('From date of driver name ' + driver['name'] + ' must greater than ' + str(
        #         from_date_create_fleet_management)))
        # if 'to_date' in vals:
        #     if fleet_management['to_date']:
        #         to_date_create_fleet_management = datetime.strptime(str(fleet_management['to_date']), '%Y-%m-%d')
        #         to_date_fleet_driver_join_team = datetime.strptime(str(vals['to_date']), '%Y-%m-%d')
        #         if to_date_fleet_driver_join_team > to_date_create_fleet_management:
        #             raise ValidationError(_('to date of driver name ' + driver['name'] + ' must smaller than ' + str(
        #                 to_date_create_fleet_management)))

        vals['code'] = BaseMethod.get_new_sequence('fleet.management.driver.temp', 'FMDT', 12, 'code')
        # if vals['from_date'] and 'to_date' in vals:
        #     validate.check_from_date_greater_than_to_date(vals['from_date'], vals['to_date'])
        vals['company_id'] = self.env.company.id
        # validate.check_start_date_greater_than_current_date(vals['from_date'])
        driver = self.env['fleet.driver'].search([('id', '=', vals['fleet_driver_id'])])
        if driver['employee_type'] == 'driver':
            vals['type'] = FleetEmployeeType.DRIVER.value
        else:
            vals['type'] = FleetEmployeeType.MANAGER.value
        fleet_management_driver_temp = super(FleetManagementDriverTemp, self).create(vals)
        driver.write(
            {'fleet_management_id': fleet_management_driver_temp['fleet_management_id']['id'], 'is_selected': False})
        return fleet_management_driver_temp

    def write(self, vals):

        # check from_date and to_date when update record
        # if 'from_date' in vals and 'to_date' in vals:
        #     validate.check_from_date_greater_than_to_date(vals['from_date'], vals['to_date'])
        # elif 'from_date' in vals and vals['from_date'] != False:
        #     validate.check_start_date_greater_than_current_date(vals['from_date'])
        #     if self['to_date']:
        #         validate.check_from_date_greater_than_to_date(vals['from_date'], self['to_date'])
        # elif 'to_date' in vals and vals['to_date'] != False:
        #     validate.check_from_date_greater_than_to_date(self['from_date'], vals['to_date'])
        # check from_date and to_date in range of from_date and to_date fleet management
        fleet_management = self.env['fleet.management'].search(
            [('id', '=', self['fleet_management_id']['id']), ('status', '=', 'active')])
        driver = self.env['fleet.driver'].search([('id', '=', self['fleet_driver_id']['id'])])
        if 'from_date' in vals:
            f_date = datetime.strptime(str(vals['from_date']), '%Y-%m-%d')
            fm_date = datetime.strptime(str(fleet_management['from_date']), '%Y-%m-%d')

        #     if f_date < fm_date:
        #         raise ValidationError(_('to date of driver name ' + driver['name'] + ' must greater than ' + str(
        #             fm_date)))
        # if 'to_date' in vals and fleet_management['to_date']:
        #     t_date = datetime.strptime(str(vals['to_date']), '%Y-%m-%d')
        #     tm_date = datetime.strptime(str(fleet_management['to_date']), '%Y-%m-%d')
        #     if t_date > tm_date:
        #         raise ValidationError(_('to date of driver name ' + driver['name'] + ' must smaller than ' + str(
        #             tm_date)))
        if len(vals) == 1:
            vals['from_date'] = date.today()
            vals['fleet_management_id'] = self['fleet_management_id']['id']
            vals['company_id'] = self['company_id']
            vals['status'] = 'active'
            http.request.env['fleet.management.driver.temp'].create(vals)
            result = super(FleetManagementDriverTemp, self).write({'status': 'deactive', 'to_date': date.today()})
        else:
            result = super(FleetManagementDriverTemp, self).write(vals)
        return result

    def unlink(self):
        for id in self.ids:
            record = self.env['fleet.management.driver.temp'].search([('id', '=', id), ('status', '=', 'active')])
            current_date = date.today()
            record.write({
                'status': 'deactive',
                'to_date': current_date
            })
            fleet_driver = self.env['fleet.driver'].search(
                [('id', '=', record['fleet_driver_id']['id'])])
            fleet_driver.write(
                {'fleet_management_id': False})
        return self

    @api.onchange('fleet_driver_id')
    def onchange_fleet_driver(self):
        if self.fleet_driver_id:
            for record in self:
                if record['fleet_driver_id']:
                    result = self.env['fleet.driver'].search(
                        [('id', '=', self.fleet_driver_id.id), ('status', '=', 'running')])
                    if result['employee_type'] == 'driver':
                        record['type'] = FleetEmployeeType.DRIVER.value
                    else:
                        record['type'] = FleetEmployeeType.MANAGER.value
                    http.request.env['fleet.driver']. \
                        browse(self.fleet_driver_id.id).write(
                        {'is_selected': True})


class FleetManagementVehicleTemp(models.Model):
    _name = "fleet.management.vehicle.temp"
    _description = "Fleet management and vehicle"

    @api.onchange('fleet_vehicle_id')
    def onchange_fleet_driver(self):
        if self.fleet_vehicle_id:
            for record in self:
                if record['fleet_vehicle_id']:
                    result = self.env['fleet.driver'].search(
                        [('id', '=', self.fleet_vehicle_id.id)])
                    http.request.env['fleet.vehicle']. \
                        browse(self.fleet_vehicle_id.id).write(
                        {'is_selected': True})

    fleet_management_vehicle_id = fields.Many2one('fleet.management', string="Fleet management")
    company_id = fields.Integer()
    code = fields.Char(readonly=True)
    status = fields.Selection(
        [('active', 'Active'),
         ('deactive', 'Deactive')
         ],
        string='Status', context={'status': 'running'}, default='active')
    from_date = fields.Date(required=True, default=date.today())
    to_date = fields.Date(readonly=True)
    alert = fields.Boolean('alert', store=False, compute='load_all')
    available_driver = fields.Integer('Available driver', store=False, compute='load_all')

    def load_all(self):
        for record in self:
            drivers = self.env['fleet.driver'].search(
                [('fleet_management_id', '=', record.fleet_management_vehicle_id.id), ('employee_type', '=', 'driver'),
                 ('status', '=', 'running')])
            count = 0
            if drivers:
                for driver in drivers:
                    if record.fleet_vehicle_id.tonnage_id and driver.class_driver.max_tonnage:
                        if driver.class_driver.max_tonnage >= record.fleet_vehicle_id.tonnage_id.max_tonnage:
                            count += 1
            if count == 0:
                record.alert = True
            else:
                record.alert = False
            record.available_driver = count

    @api.model
    def create(self, vals):
        today = date.today()
        company_id = self.env.company.id
        vals['company_id'] = company_id

        query = """
               SELECT id, fleet_vehicle_id, status, from_date, to_date, create_uid, create_date, write_uid, write_date, fleet_management_vehicle_id, code, company_id
             FROM public.fleet_management_vehicle_temp WHERE fleet_vehicle_id = %s and status = 'active' order by id DESC LIMIT  1
           """
        self.env.cr.execute(query, (vals['fleet_vehicle_id'],), )
        record = self._cr.dictfetchall()
        if record:
            if len(record) > 0:
                for data in record:
                    if data['to_date'] is None:
                        result = self.env['fleet.management'].search(
                            [('id', '=', data['fleet_management_vehicle_id']), ('status', '=', 'active')])
                        vehicle = self.env['fleet.vehicle'].search([('id', '=', data['fleet_vehicle_id'])])

                        raise ValidationError(
                            _(vehicle['name'].upper() + ' was joining team:  ' + result['name'].upper()))
                    else:
                        pass
                        # from_date_new = datetime.strptime(str(vals['from_date']), '%Y-%m-%d')
                        # to_date_old = datetime.strptime(str(data['to_date']), '%Y-%m-%d')
                        # if from_date_new < to_date_old:
                        #     raise ValidationError(_('From date must be greater than ' + str(to_date_old)))

        fleet_management = self.env['fleet.management'].search(
            [('id', '=', vals['fleet_management_vehicle_id']), ('status', '=', 'active')])
        vehicle = self.env['fleet.vehicle'].search([('id', '=', vals['fleet_vehicle_id'])])
        from_date_create_fleet_management = datetime.strptime(str(fleet_management['from_date']), '%Y-%m-%d')
        from_date_fleet_vehicle_join_team = datetime.strptime(str(vals['from_date']), '%Y-%m-%d')
        # if from_date_fleet_vehicle_join_team < from_date_create_fleet_management:
        #     raise ValidationError(_('From date of driver name ' + vehicle['name'] + ' must greater than ' + str(
        #         from_date_create_fleet_management)))
        # if 'to_date' in vals:
        #     if fleet_management['to_date']:
        #         to_date_create_fleet_management = datetime.strptime(str(fleet_management['to_date']), '%Y-%m-%d')
        #         to_date_fleet_vehicle_join_team = datetime.strptime(str(vals['to_date']), '%Y-%m-%d')
        #         if to_date_fleet_vehicle_join_team > to_date_create_fleet_management:
        #             raise ValidationError(_('to date of vehicle name ' + vehicle['name'] + ' must smaller than ' + str(
        #                 to_date_create_fleet_management)))

        vals['code'] = BaseMethod.get_new_sequence('fleet.management.vehicle.temp', 'FMVT', 12, 'code')
        # if vals['from_date'] and 'to_date' in vals:
        #     validate.check_from_date_greater_than_to_date(vals['from_date'], vals['to_date'])
        vals['company_id'] = self.env.company.id
        # validate.check_start_date_greater_than_current_date(vals['from_date'])
        result = super(FleetManagementVehicleTemp, self).create(vals)

        fleet_vehicle = self.env['fleet.vehicle'].search(
            [('id', '=', result['fleet_vehicle_id']['id'])])
        http.request.env['fleet.vehicle']. \
            browse(fleet_vehicle['id']).write(
            {'fleet_management_id': result['fleet_management_vehicle_id']['id'], 'is_selected': True,
             'parking_point_id': fleet_management['parking_point_id'].id})

        return result

    def write(self, vals):
        # if 'from_date' in vals and 'to_date' in vals:
        #     validate.check_from_date_greater_than_to_date(vals['from_date'], vals['to_date'])
        # elif 'from_date' in vals and vals['from_date'] != False:
        #     validate.check_start_date_greater_than_current_date(vals['from_date'])
        #     if self['to_date']:
        #         validate.check_from_date_greater_than_to_date(vals['from_date'], self['to_date'])
        # elif 'to_date' in vals and vals['to_date'] != False:
        #     validate.check_from_date_greater_than_to_date(self['from_date'], vals['to_date'])

        # check from_date and to_date in range of from_date and to_date fleet management
        fleet_management = self.env['fleet.management'].search(
            [('id', '=', self['fleet_management_vehicle_id']['id']), ('status', '=', 'active')])
        vehicle = self.env['fleet.driver'].search([('id', '=', self['fleet_vehicle_id']['id'])])
        # if 'from_date' in vals:
        #     f_date = datetime.strptime(str(vals['from_date']), '%Y-%m-%d')
        #     fm_date = datetime.strptime(str(fleet_management['from_date']), '%Y-%m-%d')
        #     if f_date < fm_date:
        #         raise ValidationError(_('to date of driver name ' + vehicle['name'] + ' must greater than ' + str(
        #             fm_date)))
        if len(vals) == 1:
            vals['from_date'] = date.today()
            vals['fleet_management_vehicle_id'] = self['fleet_management_vehicle_id']['id']
            vals['company_id'] = self['company_id']
            vals['status'] = 'active'
            http.request.env['fleet.management.vehicle.temp'].create(vals)
            result = super(FleetManagementVehicleTemp, self).write({'status': 'deactive', 'to_date': date.today()})
        else:
            result = super(FleetManagementVehicleTemp, self).write(vals)
        return result

    def unlink(self):
        current_date = date.today()
        for id in self.ids:
            record = self.env['fleet.management.vehicle.temp'].search([('id', '=', id), ('status', '=', 'active')])
            record.write({
                'status': 'deactive',
                'to_date': current_date
            })

            fleet_vehicle = self.env['fleet.vehicle'].search(
                [('id', '=', record['fleet_vehicle_id']['id'])])
            http.request.env['fleet.vehicle']. \
                browse(fleet_vehicle['id']).write(
                {'fleet_management_id': False, 'parking_point_id': False, 'is_selected': False})
        return self
