from mymodule.constants import Constants
from odoo import api, fields, models, _, http


class BiddingVehicle(models.Model):
    _name = Constants.SHAREVAN_BIDDING_VEHICLE
    _description = 'Bidding vehicle'

    code = fields.Char(string='Code')
    res_user_id = fields.Many2one('res.users', string='User')
    res_partner_id = fields.Many2one('res.partner', string='Management employee',
                                     domain=lambda self: "[('company_id', '=', company_id),('status','=','running')]")
    lisence_plate = fields.Char(string='License plate')
    driver_phone_number = fields.Char(string='Driver phone number')
    driver_name = fields.Char(string='Driver name')
    expiry_time = fields.Datetime(string='Expiry  time')
    company_id = fields.Many2one(Constants.RES_COMPANY, string='Company')
    image_128 = fields.Image("Image", max_width=128, max_height=128)
    status = fields.Selection([('1', 'Đã có đơn'),
                               ('0', 'Không có đơn')
                               ], string='Status biding', default='0')
    active_deactive = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted')], 'Status', default="running")
    id_card = fields.Char(string='Identity document')
    tonnage = fields.Float(string='Tonnage')
    weight_unit = fields.Many2one(Constants.WEIGHT_UNIT, string='Weight unit')
    description = fields.Char()

    bidding_vehicle_seq = fields.Char(string='Bidding vehicle sequence', required=True, copy=False,
                                                         readonly=True,
                                                         index=True,
                                                         default=lambda self: _('New'))

    tonnage = fields.Float()
    vehicle_type = fields.Many2one(Constants.FLEET_VEHICLE_TYPE, string='Vehicle type',domain=lambda self: "[('status', '=', 'running')]")
    latitude = fields.Float(string='latitude')
    longitude= fields.Float(string= 'longitude')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    driver_id = fields.Many2one('fleet.driver', string='Driver')

    @api.model
    def create(self, vals):
        if vals.get('bidding_vehicle_seq', 'New') == 'New':
            vals['bidding_vehicle_seq'] = self.env['ir.sequence'].next_by_code(
                'self.sharevan.bidding.vehicle') or 'New'
        # FIXME: yeu cau ly giai vi sao gan bang 0
        # vals['res_user_id'] = 0
        # if vals['lisence_plate']:
        #     partner = self.env['res.partner'].sudo().create({
        #         'name': 'bidding vehicle',
        #         'company_id': vals['company_id']
        #     }).sudo()
        #
        #     v = {
        #         'active': True,
        #         'login': vals['lisence_plate'],
        #         'password': 'admin',
        #         'partner_id': partner.id,
        #         'company_id': vals['company_id']
        #     }
        #     user_id = self.env['res.users'].sudo().create(v)
        #     vals['res_user_id'] = user_id.id
        result = super(BiddingVehicle, self).create(vals)
        return result
