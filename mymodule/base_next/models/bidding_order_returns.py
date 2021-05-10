from mymodule.constants import Constants
from odoo import models, fields, api, _


class BiddingOrderReturn(models.Model):
    _name = Constants.SHAREVAN_BIDDING_ORDER_RETURN
    _description = 'Bidding order return'

    code = fields.Char(string='Bidding Order Return Reference', required=True, copy=False, readonly=True,
                       index=True,
                       default=lambda self: _('New'))
    bidding_order_id = fields.Many2one(Constants.SHAREVAN_BIDDING_ORDER, string='Bidding order')
    bidding_order_vehicle_id = fields.Many2one(Constants.SHAREVAN_BIDDING_ORDER_VEHICLE, string='Bidding order vehicle')
    from_expected_time = fields.Datetime('From expected time')
    to_expected_time = fields.Datetime('To expected time')
    depot_id = fields.Many2one(Constants.SHAREVAN_DEPOT, string='Depot')
    actual_time = fields.Datetime('Actual time')
    stock_man_id = fields.Many2one(Constants.RES_PARTNER, 'Employee')
    status = fields.Selection([('-1', 'Hủy'),
                               ('0', 'Chưa nhận'),
                               ('2', 'Đã trả hàng')],default='0')
    description = fields.Html(string="Default Description", translate=True)
    bidding_vehicle_id = fields.Many2one(Constants.SHAREVAN_BIDDING_VEHICLE, string='Bidding vehicle')

    @api.model
    def create(self, vals):
        if vals.get('code', 'New') == 'New':
            vals['code'] = self.env['ir.sequence'].next_by_code(
                'self.bidding.order.return') or 'New'
        result = super(BiddingOrderReturn, self).create(vals)
        return result

