# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta, datetime, date

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError

from dateutil.relativedelta import relativedelta
from .utils import validate_utils as validate
from ...base_next.controllers.api.base_method import BaseMethod
from ...enum.MessageType import NotificationSocketType
from ...enum.StageMaintenanceType import StageMaintenanceType
from ...enum.VehicleStateStatus import VehicleStateStatus, VehicleEquipmentPart


class FleetVehicleCost(models.Model):
    _name = 'fleet.vehicle.cost'
    _description = 'Cost related to a vehicle'
    _order = 'date desc, vehicle_id asc'

    name = fields.Char(related='vehicle_id.name', string='Name', store=True, readonly=False)
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', required=True, help='Vehicle concerned by this log')
    cost_subtype_id = fields.Many2one('fleet.service.type', 'Type', help='Cost type purchased with this cost')
    amount = fields.Float('Total Price', required=True)
    cost_type = fields.Selection([
        ('contract', 'Contract'),
        ('services', 'Services'),
        ('fuel', 'Fuel'),
        ('equipmentPart', 'Equipment Part'),
        ('other', 'Other'),
        ('maintenance', 'Maintenance')
    ], 'Category of the cost', default="other", help='For internal purpose only', required=True)
    parent_id = fields.Many2one('fleet.vehicle.cost', 'Parent', help='Parent cost to this current cost')
    cost_ids = fields.One2many('fleet.vehicle.cost', 'parent_id', 'Included Services', copy=True)
    odometer_id = fields.Many2one('fleet.vehicle.odometer', 'Odometer',
                                  help='Odometer measure of the vehicle at the moment of this log')
    odometer = fields.Float(compute="_get_odometer", inverse='_set_odometer', string='Odometer Value',
                            help='Odometer measure of the vehicle at the moment of this log')
    odometer_unit = fields.Selection(related='vehicle_id.odometer_unit', string="Unit", readonly=True)
    date = fields.Date(help='Date when the cost has been executed')
    contract_id = fields.Many2one('fleet.vehicle.log.contract', 'Contract', help='Contract attached to this cost')
    auto_generated = fields.Boolean('Automatically Generated', readonly=True)

    description = fields.Char("Description of vehicle")
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    maintenance_id = fields.Many2one('sharevan.maintenance.request', 'Maintenance', help='The cost for maintenance')
    status = fields.Selection([('draft', 'Draft'),
                               ('running', 'Running'),
                               ('deleted', 'Deleted')], 'Status', default="running")

    @api.constrains("amount")
    def validate_amount(self):
        for record in self:
            if record.amount < 0:
                raise ValidationError(" Total Price must be greater than 0")

    def _get_odometer(self):
        self.odometer = 0.0
        for record in self:
            record.odometer = False
            if record.odometer_id:
                record.odometer = record.odometer_id.value

    def unlink(self):
        for id in self.ids:
            record = self.env['fleet.vehicle.cost'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })

            record_Eqpart = self.env['fleet.vehicle.equipment.part'].search([('cost_id', '=', id)])
            record_Eqpart.write({
                'status': 'deleted'
            })

        return self

    def _set_odometer(self):
        for record in self:
            if not record.odometer:
                raise UserError(_('Emptying the odometer value of a vehicle is not allowed.'))
            odometer = self.env['fleet.vehicle.odometer'].create({
                'value': record.odometer,
                'date': record.date or fields.Date.context_today(record),
                'vehicle_id': record.vehicle_id.id
            })
            self.odometer_id = odometer

    @api.model_create_multi
    def create(self, vals_list):
        for data in vals_list:
            # make sure that the data are consistent with values of parent and contract records given
            if 'parent_id' in data and data['parent_id']:
                parent = self.browse(data['parent_id'])
                data['vehicle_id'] = parent.vehicle_id.id
                data['date'] = parent.date
                data['cost_type'] = parent.cost_type
            if 'contract_id' in data and data['contract_id']:
                contract = self.env['fleet.vehicle.log.contract'].browse(data['contract_id'])
                data['vehicle_id'] = contract.vehicle_id.id
                data['cost_subtype_id'] = contract.cost_subtype_id.id
                data['cost_type'] = contract.cost_type
            if 'odometer' in data and not data['odometer']:
                # if received value for odometer is 0, then remove it from the
                # data as it would result to the creation of a
                # odometer log with 0, which is to be avoided
                del data['odometer']
            if 'maintenance_id' in data and data['maintenance_id']:
                maintenance = self.env['sharevan.maintenance.request'].browse(data['maintenance_id'])
                data['vehicle_id'] = maintenance.vehicle_id.id
                data['cost_subtype_id'] = maintenance.cost_subtype_id.id
                data['cost_type'] = maintenance.cost_type
        return super(FleetVehicleCost, self).create(vals_list)


class FleetVehicleLogContract(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _inherits = {'fleet.vehicle.cost': 'cost_id'}
    _name = 'fleet.vehicle.log.contract'
    _description = 'Contract information on a vehicle'
    _order = 'state desc,expiration_date'

    def compute_next_year_date(self, strdate):
        oneyear = relativedelta(years=1)
        start_date = fields.Date.from_string(strdate)
        return fields.Date.to_string(start_date + oneyear)

    @api.model
    def default_get(self, default_fields):
        res = super(FleetVehicleLogContract, self).default_get(default_fields)
        contract = self.env.ref('fleet.type_contract_leasing', raise_if_not_found=False)
        res.update({
            'date': fields.Date.context_today(self),
            'cost_subtype_id': contract and contract.id or False,
            'cost_type': 'contract'
        })
        return res

    @api.constrains('start_date', 'expiration_date')
    def check_start_date_expiration_date(self):
        for rec in self:
            if rec.start_date:
                if rec.expiration_date:
                    if rec.expiration_date < rec.start_date:
                        raise ValidationError(_('Contact expiration date must greater than Contact start date!'))

    name = fields.Text(compute='_compute_contract_name', store=True)
    active = fields.Boolean(default=True)
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user, index=True)
    start_date = fields.Date('Contract Start Date', default=fields.Date.context_today,
                             help='Date when the coverage of the contract begins')
    expiration_date = fields.Date('Contract Expiration Date', default=lambda self:
    self.compute_next_year_date(fields.Date.context_today(self)),
                                  help='Date when the coverage of the contract expirates (by default, one year after begin date)')
    days_left = fields.Integer(compute='_compute_days_left', string='Warning Date')
    insurer_id = fields.Many2one('sharevan.vendor', 'Vendor', domain=[('status', '=', 'running')])
    purchaser_id = fields.Many2one('res.partner', 'Driver', default=lambda self: self.env.user.partner_id.id,
                                   help='Person to which the contract is signed for')
    ins_ref = fields.Char('Contract Reference', size=64, copy=False)
    state = fields.Selection([
        ('futur', 'Incoming'),
        ('open', 'In Progress'),
        ('diesoon', 'Expiring Soon'),
        ('expired', 'Expired'),
        ('closed', 'Closed')
    ], 'State', default='open', readonly=True,
        help='Choose whether the contract is still valid or not',
        tracking=True,
        copy=False)
    notes = fields.Text('Terms and Conditions',
                        help='Write here all supplementary information relative to this contract', copy=False)
    cost_generated = fields.Float('Recurring Cost Amount', tracking=True,
                                  help="Costs paid at regular intervals, depending on the cost frequency. "
                                       "If the cost frequency is set to unique, the cost will be logged at the start date")
    cost_frequency = fields.Selection([
        ('no', 'No'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly')
    ], 'Recurring Cost Frequency', default='no', help='Frequency of the recuring cost', required=True)
    generated_cost_ids = fields.One2many('fleet.vehicle.cost', 'contract_id', 'Generated Costs')
    sum_cost = fields.Float(compute='_compute_sum_cost', string='Indicative Costs Total')
    cost_id = fields.Many2one('fleet.vehicle.cost', 'Cost', required=True, ondelete='cascade')
    # we need to keep this field as a related with store=True because the graph view doesn't support
    # (1) to address fields from inherited table
    # (2) fields that aren't stored in database
    cost_amount = fields.Float(related='cost_id.amount', string='Amount', store=True, readonly=False)
    odometer = fields.Float(string='Creation Contract Odometer',
                            help='Odometer measure of the vehicle at the moment of the contract creation')
    status = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted')], 'Status', default="running")

    @api.model
    def create(self, vals):
        if vals['start_date'] and vals['expiration_date']:
            if vals['expiration_date'] < vals['start_date']:
                raise ValidationError(_('Contact expiration date must greater than Contact start date!'))
        result = super(FleetVehicleLogContract, self).create(vals)
        return result

    def unlink(self):
        for id in self.ids:
            record = self.env['fleet.vehicle.log.contract'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })

            recordCost = self.env['fleet.vehicle.cost'].search([('id', '=', record.cost_id.id)])
            recordCost.write({
                'status': 'deleted'
            })
        return self

    @api.depends('vehicle_id', 'cost_subtype_id', 'date')
    def _compute_contract_name(self):
        for record in self:
            name = record.vehicle_id.name
            if record.cost_subtype_id.name:
                name += ' / ' + record.cost_subtype_id.name
            if record.date:
                name += ' / ' + str(record.date)
            record.name = name

    @api.depends('expiration_date', 'state')
    def _compute_days_left(self):
        """return a dict with as value for each contract an integer
        if contract is in an open state and is overdue, return 0
        if contract is in a closed state, return -1
        otherwise return the number of days before the contract expires
        """
        for record in self:
            if record.expiration_date and record.state in ['open', 'diesoon', 'expired']:
                today = fields.Date.from_string(fields.Date.today())
                renew_date = fields.Date.from_string(record.expiration_date)
                diff_time = (renew_date - today).days
                record.days_left = diff_time > 0 and diff_time or 0
            else:
                record.days_left = -1

    @api.depends('cost_ids.amount')
    def _compute_sum_cost(self):
        for contract in self:
            contract.sum_cost = sum(contract.cost_ids.mapped('amount'))

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
        if self.vehicle_id:
            self.odometer_unit = self.vehicle_id.odometer_unit

    def write(self, vals):
        res = super(FleetVehicleLogContract, self).write(vals)
        if vals.get('expiration_date') or vals.get('user_id'):
            self.activity_reschedule(['fleet.mail_act_fleet_contract_to_renew'],
                                     date_deadline=vals.get('expiration_date'), new_user_id=vals.get('user_id'))
        return res

    def contract_close(self):
        for record in self:
            record.state = 'closed'

    def contract_open(self):
        for record in self:
            record.state = 'open'

    def act_renew_contract(self):
        assert len(
            self.ids) == 1, "This operation should only be done for 1 single contract at a time, as it it suppose to open a window as result"
        for element in self:
            # compute end date
            startdate = fields.Date.from_string(element.start_date)
            enddate = fields.Date.from_string(element.expiration_date)
            diffdate = (enddate - startdate)
            default = {
                'date': fields.Date.context_today(self),
                'start_date': fields.Date.to_string(
                    fields.Date.from_string(element.expiration_date) + relativedelta(days=1)),
                'expiration_date': fields.Date.to_string(enddate + diffdate),
            }
            newid = element.copy(default).id
        return {
            'name': _("Renew Contract"),
            'view_mode': 'form',
            'view_id': self.env.ref('fleet.fleet_vehicle_log_contract_view_form').id,
            'res_model': 'fleet.vehicle.log.contract',
            'type': 'ir.actions.act_window',
            'domain': '[]',
            'res_id': newid,
            'context': {'active_id': newid},
        }

    @api.model
    def scheduler_manage_auto_costs(self):
        # This method is called by a cron task
        # It creates costs for contracts having the "recurring cost" field setted, depending on their frequency
        # For example, if a contract has a reccuring cost of 200 with a weekly frequency, this method creates a cost of 200 on the
        # first day of each week, from the date of the last recurring costs in the database to today
        # If the contract has not yet any recurring costs in the database, the method generates the recurring costs from the start_date to today
        # The created costs are associated to a contract thanks to the many2one field contract_id
        # If the contract has no start_date, no cost will be created, even if the contract has recurring costs
        VehicleCost = self.env['fleet.vehicle.cost']
        deltas = {
            'yearly': relativedelta(years=+1),
            'monthly': relativedelta(months=+1),
            'weekly': relativedelta(weeks=+1),
            'daily': relativedelta(days=+1)
        }
        contracts = self.env['fleet.vehicle.log.contract'].search([('state', '!=', 'closed')], offset=0, limit=None,
                                                                  order=None)
        for contract in contracts:
            if not contract.start_date or contract.cost_frequency == 'no':
                continue
            found = False
            startdate = contract.start_date
            if contract.generated_cost_ids:
                last_autogenerated_cost = VehicleCost.search([
                    ('contract_id', '=', contract.id),
                    ('auto_generated', '=', True)
                ], offset=0, limit=1, order='date desc')
                if last_autogenerated_cost:
                    found = True
                    startdate = last_autogenerated_cost.date
            if found:
                startdate += deltas.get(contract.cost_frequency)
            today = fields.Date.context_today(self)
            while (startdate <= today) & (startdate <= contract.expiration_date):
                data = {
                    'amount': contract.cost_generated,
                    'date': fields.Date.context_today(self),
                    'vehicle_id': contract.vehicle_id.id,
                    'cost_subtype_id': contract.cost_subtype_id.id,
                    'contract_id': contract.id,
                    'auto_generated': True
                }
                self.env['fleet.vehicle.cost'].create(data)
                startdate += deltas.get(contract.cost_frequency)
        return True

    @api.model
    def scheduler_manage_contract_expiration(self):
        # This method is called by a cron task
        # It manages the state of a contract, possibly by posting a message on the vehicle concerned and updating its status
        params = self.env['ir.config_parameter'].sudo()
        delay_alert_contract = int(params.get_param('hr_fleet.delay_alert_contract', default=30))
        date_today = fields.Date.from_string(fields.Date.today())
        outdated_days = fields.Date.to_string(date_today + relativedelta(days=+delay_alert_contract))
        nearly_expired_contracts = self.search([('state', '=', 'open'), ('expiration_date', '<', outdated_days)])

        nearly_expired_contracts.write({'state': 'diesoon'})
        for contract in nearly_expired_contracts.filtered(lambda contract: contract.user_id):
            contract.activity_schedule(
                'fleet.mail_act_fleet_contract_to_renew', contract.expiration_date,
                user_id=contract.user_id.id)

        expired_contracts = self.search(
            [('state', 'not in', ['expired', 'closed']), ('expiration_date', '<', fields.Date.today())])
        expired_contracts.write({'state': 'expired'})

        futur_contracts = self.search(
            [('state', 'not in', ['futur', 'closed']), ('start_date', '>', fields.Date.today())])
        futur_contracts.write({'state': 'futur'})

        now_running_contracts = self.search([('state', '=', 'futur'), ('start_date', '<=', fields.Date.today())])
        now_running_contracts.write({'state': 'open'})

    def run_scheduler(self):
        self.scheduler_manage_auto_costs()
        self.scheduler_manage_contract_expiration()


class FleetVehicleEquipmentPart(models.Model):
    _name = 'fleet.vehicle.equipment.part'
    _description = 'Equipment part for vehicles'
    _inherits = {'fleet.vehicle.cost': 'cost_id'}

    @api.model
    def default_get(self, default_fields):
        res = super(FleetVehicleEquipmentPart, self).default_get(default_fields)
        service = self.env.ref('fleet.type_service_equipment_part', raise_if_not_found=False)
        res.update({
            'date': fields.Date.context_today(self),
            'cost_subtype_id': service and service.id or False,
            'cost_type': 'equipmentPart'
        })
        return res

    name = fields.Char('Name', size=255, required=True)
    equipmentPart_code = fields.Char(string='EquipmentPart Code', required=True, copy=False, readonly=True, index=True,
                                     default=lambda self: _('New'))
    liter = fields.Float()
    price_per_liter = fields.Float()

    unit_measure = fields.Selection([
        ('other', 'Other'),
        ('piece', 'Piece'),
        ('set', 'Set'),
        ('module', 'Module')
    ], 'Measure Category', required=True)
    part_no = fields.Integer('Unique code', default=1)
    vehicle = fields.Many2one('fleet.vehicle', string='vehicle', domain="[('active','=',True)]")
    purchaser_id = fields.Many2one('fleet.vehicle.equipment.part', 'Parent Part')
    category_name = fields.Many2one('fleet.vehicle.category.name', 'Category Name')
    category_type = fields.Many2one('fleet.vehicle.category.type', 'Category Type')
    universal_product_code = fields.Char('Universal Code', requried=True)
    vendor_id = fields.Many2one('sharevan.vendor', 'Vendor', required=True, domain=[('type', '=', 'vendor_equipment'),
                                                                                    ('status', '=', 'running')])
    description = fields.Text()
    cost_id = fields.Many2one('fleet.vehicle.cost', 'Cost', required=True, ondelete='cascade')
    image_1920 = fields.Image("Image", max_width=128, max_height=128)
    attach_File = fields.Many2many('ir.attachment', string="Attach File")
    # we need to keep this field as a related with store=True because the graph view doesn't support
    # (1) to address fields from inherited table
    # (2) fields that aren't stored in database
    cost_amount = fields.Float(related='cost_id.amount', string='Amount', store=True, readonly=False)
    type_device = fields.Selection(
        [('0', 'IOT'),
         ('1', 'Vehicle')
         ],
        string='Type device', default="0", required=True)
    device_vehicle = fields.Selection(
        [('deviceOrther', 'Device orther'),
         ('tires', 'Tires'),
         ('lazang', 'Lazang'),
         ('airCleaner', 'Air cleaner')
         ],
        string='Name device')
    size = fields.Float(string='Size')
    mainten_schedule = fields.Many2one('fleet.maintenance.schedule', 'Maintence schedule')
    status = fields.Selection(
        [('running', 'Running'),
         ('deleted', 'Deleted')
         ],
        string='Status', required=True, default='running')

    @api.onchange('type_device')
    def _onchange_type_device(self):
        if self.type_device == '0':
            self.device_vehicle = 'deviceOrther'

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
        if self.vehicle_id:
            self.odometer_unit = self.vehicle_id.odometer_unit
            # self.purchaser_id = self.vehicle_id.driver_id.id

    @api.constrains('cost_amount')
    def _check_cost_amount(self):
        for wizard in self:
            if not wizard.amount > 0.0:
                raise ValidationError(_('The payment amount must be strictly positive.'))

    @api.constrains('part_no')
    def _check_part_no(self):
        for wizard in self:
            if not wizard.part_no > 0.0:
                raise ValidationError(_('The payment part no must be strictly positive.'))

    @api.constrains('universal_product_code')
    def validate_universal_product_code(self):
        for rec in self:
            if rec.universal_product_code != False:
                return validate.check_string_contain_special_character(rec.universal_product_code, 'Universal Code ')

    @api.onchange('liter', 'price_per_liter', 'amount')
    def _onchange_liter_price_amount(self):
        # need to cast in float because the value receveid from web client maybe an integer (Javascript and JSON do not
        # make any difference between 3.0 and 3). This cause a problem if you encode, for example, 2 liters at 1.5 per
        # liter => total is computed as 3.0, then trigger an onchange that recomputes price_per_liter as 3/2=1 (instead
        # of 3.0/2=1.5)
        # If there is no change in the result, we return an empty dict to prevent an infinite loop due to the 3 intertwine
        # onchange. And in order to verify that there is no change in the result, we have to limit the precision of the
        # computation to 2 decimal
        liter = float(self.liter)
        price_per_liter = float(self.price_per_liter)
        amount = float(self.amount)
        if liter > 0 and price_per_liter > 0 and round(liter * price_per_liter, 2) != amount:
            self.amount = round(liter * price_per_liter, 2)
        elif amount > 0 and liter > 0 and round(amount / liter, 2) != price_per_liter:
            self.price_per_liter = round(amount / liter, 2)
        elif amount > 0 and price_per_liter > 0 and round(amount / price_per_liter, 2) != liter:
            self.liter = round(amount / price_per_liter, 2)

    @api.model
    def create(self, vals):
        availableState = self.env['fleet.vehicle.state'].search([('code', '=', VehicleStateStatus.Available.value)],
                                                                limit=1).id

        iot = VehicleEquipmentPart.IOT.value

        vals['vehicle'] = vals['vehicle_id']

        # self.env.cr.execute(
        #     """select COUNT(vehicle) from fleet_vehicle_equipment_part where  vehicle = %s  and type_device  = %s and  status = 'running' """,
        #     (vals['vehicle_id'],iot))
        # self.env.cr.execute(sql_driver)
        # equipmentCount = self.env.cr.fetchall()
        # for count in equipmentCount[0]:
        #     count_eq = count
        # if count_eq == 0 and vals['type_device'] == iot :
        #     self.env.cr.execute(
        #         """update  fleet_vehicle
        #             set state_id = %s
        #             where id = %s """,
        #         (availableState, vals['vehicle_id'],))
        if vals.get('equipmentPart_code', 'New') == 'New':
            seq = BaseMethod.get_new_sequence('fleet.vehicle.equipment.part', 'FVEP', 6, 'equipmentPart_code')
            vals['equipmentPart_code'] = seq
            result = super(FleetVehicleEquipmentPart, self).create(vals)
            vehicle = self.env['fleet.vehicle'].search(
                [('id', '=', vals['vehicle'])])
            if vals['device_vehicle'] == 'tires':
                vehicle.write({
                    'tires': result['id']
                })
            elif vals['device_vehicle'] == 'lazang':
                vehicle.write({
                    'tires': result['id']
                })
            elif vals['device_vehicle'] == 'airCleaner':
                vehicle.write({
                    'tires': result['id']
                })
            return result

    def write(self, vals):
        if 'vehicle_id' in vals:
            vals['vehicle'] = vals['vehicle_id']
        res = super(FleetVehicleEquipmentPart, self).write(vals)

    def unlink(self):

        newStage = self.env['sharevan.maintenance.stage'].search(
            [('code', '=', StageMaintenanceType.New.value)], limit=1).id

        progressStage = self.env['sharevan.maintenance.stage'].search(
            [('code', '=', StageMaintenanceType.Progress.value)], limit=1).id

        # availableState = self.env['fleet.vehicle.state'].search([('code', '=', VehicleStateStatus.Available.value)],
        #                                                         limit=1).id
        # iot = VehicleEquipmentPart.IOT.value

        for id_value in self.ids:
            record = self.env['fleet.vehicle.equipment.part'].search([('id', '=', id_value)])
            record.write({
                'status': 'deleted'
            })

            # cost
            record_Cost = self.env['fleet.vehicle.cost'].search([('id', '=', record.cost_id.id)])
            record_Cost.write({
                'status': 'deleted'
            })
        # for record in self:
        # self.env.cr.execute(
        #     """select COUNT(vehicle) from fleet_vehicle_equipment_part where  vehicle = %s and type_device  = %s and id != %s and status = 'running' """,
        #     (record.vehicle['id'],iot, record['id']))
        # # self.env.cr.execute(sql_driver)
        # equipmentCount = self.env.cr.fetchall()
        # for count in equipmentCount[0]:
        #     count_eq = count

        # vehicle = self.env['fleet.vehicle'].search([('id', '=', record.vehicle['id'])])
        # maintain_newStage = self.env['sharevan.maintenance.request'].search_count(
        #     [('vehicle', '=', record.vehicle['id']), ('stage_id', '=', newStage)])
        # maintain_progressStage = self.env['sharevan.maintenance.request'].search_count(
        #     [('vehicle', '=', record.vehicle['id']), ('stage_id', '=', progressStage)])
        # if maintain_newStage == 0 and maintain_progressStage == 0:
        #     if count_eq == 0:
        #         vehicle.write({
        #             'state_id': waitingState
        #         })

        return self


class FleetVehicleLogFuel(models.Model):
    _name = 'fleet.vehicle.log.fuel'
    _description = 'Fuel log for vehicles'
    _inherits = {'fleet.vehicle.cost': 'cost_id'}

    @api.model
    def default_get(self, default_fields):
        res = super(FleetVehicleLogFuel, self).default_get(default_fields)
        service = self.env.ref('fleet.type_service_refueling', raise_if_not_found=False)
        res.update({
            'date': fields.Date.context_today(self),
            'cost_subtype_id': service and service.id or False,
            'cost_type': 'fuel'
        })
        return res

    liter = fields.Float()
    price_per_liter = fields.Float()
    purchaser_id = fields.Many2one('fleet.driver', 'Purchaser', domain=lambda
        self: [('status', '=', 'running'), ('company_id', '=', self.env.company.id)])
    inv_ref = fields.Char('Invoice Reference', size=64)
    vendor_id = fields.Many2one('sharevan.vendor', 'Vendor',
                                domain=lambda self: "[('status','=','running'),('type', '=', 'vendor_energy')]")
    notes = fields.Text()
    cost_id = fields.Many2one('fleet.vehicle.cost', 'Cost', required=True, ondelete='cascade')
    # we need to keep this field as a related with store=True because the graph view doesn't support
    # (1) to address fields from inherited table
    # (2) fields that aren't stored in database
    cost_amount = fields.Float(related='cost_id.amount', string='Amount', store=True, readonly=False)
    status = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted')], 'Status', default="running")

    def unlink(self):
        for id in self.ids:
            record = self.env['fleet.vehicle.log.fuel'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })

            recordCost = self.env['fleet.vehicle.cost'].search([('id', '=', record.cost_id.id)])
            recordCost.write({
                'status': 'deleted'
            })

        return self

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
        if self.vehicle_id:
            self.odometer_unit = self.vehicle_id.odometer_unit
            # self.purchaser_id = self.vehicle_id.driver_id.id

    @api.onchange('date')
    def _onchange_date(self):
        if self.date:
            if self.date > date.today():
                raise ValidationError('Assign date can not be greater than today !')

    @api.onchange('liter', 'price_per_liter', 'amount')
    def _onchange_liter_price_amount(self):
        # need to cast in float because the value receveid from web client maybe an integer (Javascript and JSON do not
        # make any difference between 3.0 and 3). This cause a problem if you encode, for example, 2 liters at 1.5 per
        # liter => total is computed as 3.0, then trigger an onchange that recomputes price_per_liter as 3/2=1 (instead
        # of 3.0/2=1.5)
        # If there is no change in the result, we return an empty dict to prevent an infinite loop due to the 3 intertwine
        # onchange. And in order to verify that there is no change in the result, we have to limit the precision of the
        # computation to 2 decimal
        liter = float(self.liter)
        price_per_liter = float(self.price_per_liter)
        amount = float(self.amount)
        if liter > 0 and price_per_liter > 0 and round(liter * price_per_liter, 2) != amount:
            self.amount = round(liter * price_per_liter, 2)
        elif amount > 0 and liter > 0 and round(amount / liter, 2) != price_per_liter:
            self.price_per_liter = round(amount / liter, 2)
        elif amount > 0 and price_per_liter > 0 and round(amount / price_per_liter, 2) != liter:
            self.liter = round(amount / price_per_liter, 2)

    @api.constrains('liter')
    def _check_liter(self):
        for record in self:
            if record.liter < 0:
                raise ValidationError("Liter value must be a positive number")

    @api.constrains('price_per_liter')
    def _check_per_liter(self):
        for record in self:
            if record.price_per_liter < 0:
                raise ValidationError("Price per liter value must be a positive number")


class FleetVehicleLogServices(models.Model):
    _name = 'fleet.vehicle.log.services'
    _inherits = {'fleet.vehicle.cost': 'cost_id'}
    _description = 'Services for vehicles'

    @api.model
    def default_get(self, default_fields):
        res = super(FleetVehicleLogServices, self).default_get(default_fields)
        service = self.env.ref('fleet.type_service_service_8', raise_if_not_found=False)
        res.update({
            'date': fields.Date.context_today(self),
            'cost_subtype_id': service and service.id or False,
            'cost_type': 'services'
        })
        return res

    purchaser_id = fields.Many2one('res.partner', 'Purchaser', domain=lambda
        self: [('status', '=', 'running'), ('company_id', '=', self.env.company.id)])
    inv_ref = fields.Char('Invoice Reference')
    vendor_id = fields.Many2one('sharevan.vendor', 'Vendor',
                                domain=[('status', '=', 'running'), ('type', '=', 'vendor_service')])
    # we need to keep this field as a related with store=True because the graph view doesn't support
    # (1) to address fields from inherited table and (2) fields that aren't stored in database
    cost_amount = fields.Float(related='cost_id.amount', string='Amount', store=True, readonly=False)
    notes = fields.Text()
    cost_id = fields.Many2one('fleet.vehicle.cost', 'Cost', required=True, ondelete='cascade')

    status = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted')], 'Status', default="running")

    # driver_id = fields.Many2one(related="vehicle_id.driver_id", string="Driver", readonly=False)

    def unlink(self):
        for id in self.ids:
            record = self.env['fleet.vehicle.log.services'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })

            recordCost = self.env['fleet.vehicle.cost'].search([('id', '=', record.cost_id.id)])
            recordCost.write({
                'status': 'deleted'
            })

        return self

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
        if self.vehicle_id:
            self.odometer_unit = self.vehicle_id.odometer_unit
            # self.purchaser_id = self.vehicle_id.driver_id.id


class FleetDriverEquipmentPart(models.Model):
    _name = 'fleet.driver.equipment.part'
    _description = 'Equipment part for driver'

    name = fields.Char('Name', size=255, required=True)
    equipment_part_code = fields.Char(string='EquipmentPart Code', required=True, copy=False, readonly=True, index=True,
                                      default=lambda self: _('New'))

    unit_measure = fields.Selection([
        ('other', 'Other'),
        ('piece', 'Piece'),
        ('set', 'Set'),
        ('module', 'Module')
    ], 'Measure Category', required=True)
    category_type = fields.Many2one('fleet.vehicle.category.type', 'Category Type')
    universal_product_code = fields.Char('Universal Code', requried=True, constraint='check_code')
    vendor_id = fields.Many2one('sharevan.vendor', 'Vendor', required=True, domain=[('type', '=', 'vendor_equipment'),
                                                                                    ('status', '=', 'running')])
    description = fields.Text()
    image_1920 = fields.Image("Image", max_width=128, max_height=128)
    attach_File = fields.Many2many('ir.attachment', string="Attach File")
    amount = fields.Float(string='Amount', store=True)
    status = fields.Selection(
        [('running', 'Running'),
         ('deleted', 'Deleted')
         ],
        string='Status', required=True, default='running')

    @api.constrains("amount")
    def validate_amount(self):
        for record in self:
            if record.amount < 0:
                raise ValidationError("Equipment cost must be a positive value: %s" % record.amount)

    _sql_constraints = [
        ('check_code', 'unique (universal_product_code)', 'Code must be unique!')
    ]

    @api.model
    def create(self, vals):
        if vals.get('equipment_part_code', 'New') == 'New':
            vals['equipment_part_code'] = self.env['ir.sequence'].next_by_code(
                'self.fleet.driver.equipment.part') or 'New'

        result = super(FleetDriverEquipmentPart, self).create(vals)
        return result


class FleetVehiclePaperLog(models.Model):
    _name = 'fleet.vehicle.paper.log'
    _description = 'Fleet vehicle paper log'
    # _inherits = {'fleet.vehicle.cost': 'cost_id'}

    name = fields.Char('Name', size=255, required=True)
    type = fields.Selection([
        ('inspection', 'Inspection'),
        ('insurance', 'Insurance'),
        ('orther', 'Orther')
    ], 'Type', default='orther', required=True)

    code = fields.Char(string='Code', copy=False, readonly=True,
                       index=True,
                       default=lambda self: _('New'))
    from_date = fields.Date(string="From Date", required=True)
    to_date = fields.Date(string="To Date", required=True)
    # cost_id = fields.Many2one('fleet.vehicle.cost', 'Cost', required=True, ondelete='cascade')
    insurance_id = fields.Many2one('sharevan.insurance', 'Insurance')
    status = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted')], 'Status', default="running")
    vehicle = fields.Many2one('fleet.vehicle', 'Vehicle')

    registration_code = fields.Char(string='Inspection code')

    @api.onchange('from_date','to_date')
    def _onchange_to_date(self):
        for record in self:
            if record['from_date'] and  record['to_date']:
                from_date = datetime.strptime(str(record['from_date']), '%Y-%m-%d')
                to_date = datetime.strptime(str(record['to_date']), '%Y-%m-%d')
                if int(from_date.year) - int(to_date.year) > 0:
                    notice = 'From date is not bigger than to date'
                    record.update({'to_date': False})
                    self.env.user.notify_danger(message=notice, title=NotificationSocketType.NOTIFICATION.value)
                elif  record['type']== 'inspection':
                    if int ((to_date - from_date ).days)< 180 :
                        notice = 'From date is smaller than to date at least 6 months'
                        record.update({'to_date': False})
                        self.env.user.notify_danger(message=notice, title=NotificationSocketType.NOTIFICATION.value)

    @api.model
    def create(self, vals):
        if vals.get('equipmentPart_code', 'New') == 'New':
            seq = BaseMethod.get_new_sequence('fleet.vehicle.paper.log', 'FVPL', 6, 'code')
            vals['code'] = seq
            result = super(FleetVehiclePaperLog, self).create(vals)

            if vals['type'] == 'inspection':
                vehicle = self.env['fleet.vehicle'].search([('id', '=', vals['vehicle'])])
                vehicle.write({
                    'inspection_date': vals['from_date'],
                    'inspection_due_date': vals['to_date'],
                    'vehicle_inspection': vals['registration_code']
                })
            return result

    def write(self,vals):
        param={}
        if 'from_date' in vals:
            param['inspection_date']=vals['from_date']
        if 'to_date' in vals:
            param['inspection_due_date']=vals['to_date']
        if 'registration_code' in vals:
            param['vehicle_inspection']=vals['registration_code']
        if 'type' in vals and vals['type']== 'inspection':
            if vals['type'] == 'inspection':
                vehicle = self.env['fleet.vehicle'].search([('id', '=', vals['vehicle'])])
                vehicle.write(param)
        res = super(FleetVehiclePaperLog, self).write(vals)
