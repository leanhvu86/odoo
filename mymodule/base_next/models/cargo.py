from mymodule.constants import Constants
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class Cargo(models.Model):
    _name = Constants.SHAREVAN_CARGO
    _description = 'cargo'

    code = fields.Char(string='Cargo code', required=True, copy=False, readonly=True,
                       index=True,
                       default=lambda self: _('New'))
    cargo_number = fields.Char(string='Cargo code', help=' HN-HCM : HNTHCM01 or HN_HCM_01', default='New')
    from_depot_id = fields.Many2one(Constants.SHAREVAN_DEPOT,
                                    string='From Depot', required=True,
                                    domain=lambda
                                        self: "[('id', '!=', to_depot_id),"
                                              "('main_type','=',True),('status','=','running')]")
    to_depot_id = fields.Many2one(Constants.SHAREVAN_DEPOT, string='To Depot', required=True,
                                  domain=lambda self: "[('id', '!=', from_depot_id)"
                                                      ",('status','=','running'),('main_type','=',True)]")
    distance = fields.Float('Distance', required=True)
    size_id = fields.Many2one(Constants.SHAREVAN_SIZE_STANDARD, string='Size standard', required=True)
    from_latitude = fields.Float('From latitude', digits=(16, 5))
    from_longitude = fields.Float('From longitude', digits=(16, 5))
    to_latitude = fields.Float('To latitude', digits=(16, 5))
    to_longitude = fields.Float('To longitude', digits=(16, 5))
    bidding_package_id = fields.Many2one(Constants.SHAREVAN_BIDDING_PACKAGE, string='Bidding package')
    weight = fields.Float('Total Weight', required=True)
    price = fields.Float('price', readonly=True)
    description = fields.Html(string="Default Description", translate=True)
    routing_plan_day_check_ids = fields.Char('check routing day add', store=False)
    # routing_plan_day_id = fields.Many2many('sharevan.routing.plan.day', 'sharevan_cargo_routing_plan_day_package',
    #                                        'cargo_id', 'routing_plan_day_id', string='Routing plan day',
    #                                        domain="[('status','=','0'),('ship_type','=','1'),('type','=','0'),('packaged_cargo','=','1')]")
    routing_plan_day_id = fields.Many2many('sharevan.routing.plan.day',
                                           domain="[('status','=','0'),('ship_type','=','1'),('type','=','0'),('packaged_cargo','=','1')]")

    # @api.depends()
    # def _filter_routing_plan_day(self):
    #
    #     # self.inherited_model_ids = False
    #     for model in self:
    #         print('xxxxxxxxxx')
    #         print('xxxxxxxxxx')
    #         print('xxxxxxxxxx')

    # parent_names = list(self.env[model.model]._inherits)
    # if parent_names:
    #     model.inherited_model_ids = self.search([('model', 'in', parent_names)])
    # else:
    #     model.inherited_model_ids = False

    # user_id = fields.Many2many('res.users', 'sharevan_notification_user_rel', 'notification_id', 'user_id',
    #                            'User', domain=lambda self: [('active', '=', True)], required=True)

    pack_plant_day = fields.Datetime('Pack plant day')
    status = fields.Selection([
        ('0', 'Chưa đóng gói'),
        ('1', 'Đã đóng gói')], string='Status', default='0', required=True)
    status_cargo = fields.Selection([
        ('running', 'Running'),
        ('deleted', 'Delete')], string='Status cargo', default='running', required=True)

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

    @api.onchange('routing_plan_day_id')
    def onchange_routing_plan_day_id(self):
        weight = 0
        for record in self:
            for rpd in record.routing_plan_day_id:
                weight += rpd.capacity_actual
        record.update({'weight': weight})

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

    @api.onchange('size_id')
    def onchange_size(self):
        for record in self:
            routing_add = ''
            record.update({'price': record['size_id'].price})
            # record.update({'routing_plan_day_ids': [9352, 9354, 9356]})
            # routing_add += '9352,9354,9356'
            # record.update({'routing_plan_day_check_ids': routing_add})

    def unlink(self):
        for record in self:
            record.write({
                'status_cargo': 'deleted'
            })
        return self


class CargoRouting(models.Model):
    _name = 'sharevan.cargo.routing.plan.day.package'
    _description = 'cargo routing plan day package'

    cargo_id = fields.Many2one(Constants.SHAREVAN_CARGO, string='Cargo')
    routing_plan_day_id = fields.Many2one(Constants.SHAREVAN_ROUTING_PLAN_DAY, string='Routing plan day')
    # domain="[('status','=','0'),('ship_type','=','1'),('type','=','0'),('packaged_cargo','=','1')]")
    to_routing_plan_day_id = fields.Integer('From Routing plan day', compute='compute_to_routing_plan_day_id',
                                            readonly=True)
    status = fields.Selection([
        ('running', 'Running'),
        ('delete', 'Delete')], string='Status', default='running')

    def compute_to_routing_plan_day_id(self):
        record = self
        if record['routing_plan_day_id']:
            rec = self.env['sharevan.routing.plan.day'].search(
                [('from_routing_plan_day_id', '=', record['routing_plan_day_id'].id)])
            if rec:
                record.update({'to_routing_plan_day_id': rec[0]['id']})
