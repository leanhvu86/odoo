import logging
from datetime import datetime

from mymodule.constants import Constants
from mymodule.enum.BiddingPackageStatus import BiddingPackageStatus
from mymodule.enum.BiddingStatus import BiddingStatus
from mymodule.enum.BiddingStatusType import BiddingStatusType
from mymodule.enum.ClickActionType import ClickActionType
from mymodule.enum.MessageType import MessageType
from mymodule.enum.NotificationType import NotificationType
from mymodule.share_van_order.models.sharevan_notification import Notification
from odoo import models, fields, api, _, http
from odoo.exceptions import ValidationError

logger = logging.getLogger(__name__)


class BiddingOrderVehicle(models.Model):
    _name = 'sharevan.bidding.order.sharevan.bidding.vehicle.rel'
    _description = 'Bidding order vehicle'
    sharevan_bidding_order_id = fields.Many2one('sharevan.bidding.order', string="Sharevan Bidding  Order")
    sharevan_bidding_vehicle_id = fields.Many2one('sharevan.bidding.vehicle', string="Sharevan Bidding  Vehicle")
    share_van_driver_id = fields.Many2one('sharevan.bidding.driver', string="Sharevan Bidding Driver")
    status = fields.Selection([
        ('0', 'deleted'),
        ('1', 'running')], string='Status', default='0')


class BiddingVehicleOrderRatingBadges(models.Model):
    _name = 'sharevan.bidding.vehicle.rating.badges'
    _description = 'Bidding order vehicle'
    sharevan_bidding_order_id = fields.Integer()
    sharevan_bidding_vehicle_id = fields.Integer()
    share_van_driver_id = fields.Integer()
    share_van_rating_badges_id = fields.Integer()


class BiddingOrder(models.Model):
    _name = Constants.SHAREVAN_BIDDING_ORDER
    _description = 'Bidding order'

    company_id = fields.Many2one(Constants.RES_COMPANY, string='Company', required=True)
    bidding_package_id = fields.Many2one(Constants.SHAREVAN_BIDDING_PACKAGE, string='Bidding package')
    bidding_package_type = fields.Boolean(string="Bidding Package Type Is Real", store=True,
                                          related="bidding_package_id.is_real")

    from_depot_id = fields.Many2one(Constants.SHAREVAN_DEPOT, string='From Depot', required=True,
                                    domain=lambda self: "[('id', '!=', to_depot_id),('status','=','running')]")
    to_depot_id = fields.Many2one(Constants.SHAREVAN_DEPOT, string='To Depot', required=True,
                                  domain=lambda self: "[('id', '!=', from_depot_id),('status','=','running')]")
    # product_type_id = fields.Many2one('sharevan.product.type', string='Product type', required=True)
    total_weight = fields.Float('Total weight', required=True)
    total_cargo = fields.Integer('Total cargo', required=True)
    from_latitude = fields.Float('From latitude', related='from_depot_id.latitude')
    from_longitude = fields.Float('From longitude', related='from_depot_id.longitude')
    to_latitude = fields.Float('To latitude', related='to_depot_id.latitude')
    to_longitude = fields.Float('To longitude', related='to_depot_id.longitude')
    price = fields.Float('Price', required=True)
    distance = fields.Float('Distance', required=True)
    # Thu tu trang thai 3/5 -> 0 -> 2 -> 1
    type = fields.Selection([('0', 'Phê duyệt chở thầu, thiếu thông tin xe-lái xe'),
                             ('1', 'Đã duyệt'),
                             ('2', 'Chờ duyệt, đã có thông tin xe, lái xe'),
                             ('3', 'Không trúng thầu'),
                             ('5', 'Đăng kí nhận thầu'),
                             ('-1', 'Hủy')], string='Type', default='0', required=True)
    status = fields.Selection([
        ('0', 'Chưa nhận'),
        ('1', 'Đã nhận hàng'),
        ('2', 'Đã trả hàng')], string='Status', default='0', required=True)
    note = fields.Text('Reason')
    # chi su dung tao data k join o truong nay
    bidding_order_receive_id = fields.Many2one(Constants.SHAREVAN_BIDDING_ORDER_RECEIVE, string='Order received')
    bidding_order_return_id = fields.Many2one(Constants.SHAREVAN_BIDDING_ORDER_RETURN, string='Order return')
    #######################################################################
    from_receive_time = fields.Datetime('Pick up from time', default=datetime.today())
    to_receive_time = fields.Datetime('Pick up to time', default=datetime.today())
    from_return_time = fields.Datetime('Drop from time', default=datetime.today())
    to_return_time = fields.Datetime('Drop to time', default=datetime.today())
    max_confirm_time = fields.Datetime('Max confirm time', default=datetime.today())

    actual_time = fields.Datetime('Actual from depot time', related='bidding_order_receive_id.actual_time')
    to_actual_time = fields.Datetime('Actual drop depot time', related='bidding_order_return_id.actual_time')

    # Biến này được sử dụng để đếm số lượng driver đã xác nhận số cargo của mình
    confirm_count = fields.Integer(default='0')

    bidding_order_number = fields.Char(string='Share Van Bidding Code', required=True, copy=False,
                                       readonly=True,
                                       index=True,
                                       default=lambda self: _('New'))

    # bidding_vehicle_id = fields.Many2many(Constants.SHAREVAN_BIDDING_VEHICLE, string='Bidding vehicle')
    cargo_ids = fields.Many2many(Constants.SHAREVAN_CARGO, string='Cargo', related='bidding_package_id.cargo_ids')
    bidded_user_id = fields.Many2one(Constants.RES_PARTNER, string='Employee bidded order')
    bidding_vehicle_id = fields.Many2many(Constants.SHAREVAN_BIDDING_VEHICLE,
                                          'sharevan_bidding_order_sharevan_bidding_vehicle_rel',
                                          'sharevan_bidding_order_id', 'sharevan_bidding_vehicle_id', 'Vehicle',
                                          required=True)

    @api.model
    def create(self, vals):
        if vals.get('bidding_order_number', 'New') == 'New':
            vals['bidding_order_number'] = self.env['ir.sequence'].next_by_code(
                'self.sharevan.bidding.order') or 'New'
        result = super(BiddingOrder, self).create(vals)

        return result

    def write(self, vals):
        user = self.env['res.users'].search([('partner_id', '=', self.bidded_user_id.id)])
        list_user = []
        if 'mobile' in vals:
            del vals['mobile']
            res = super(BiddingOrder, self).write(vals)
        else:
            res = super(BiddingOrder, self).write(vals)
            if self.type == BiddingStatusType.Approved.value:
                listBiddingVehicleId = self.bidding_vehicle_id.ids
                if listBiddingVehicleId:
                    for id in listBiddingVehicleId:
                        bidding_order_receive = {
                            'bidding_order_id': self.id,
                            'bidding_vehicle_id': id,
                            'status': '0',
                            'from_expected_time': self.from_receive_time,
                            'to_expected_time': self.to_receive_time,
                            'depot_id': self.from_depot_id.id
                        }
                        record_order_receive = self.env[Constants.SHAREVAN_BIDDING_ORDER_RECEIVE].search(
                            [('bidding_order_id', '=', self.id), ('bidding_vehicle_id', '=', id)])
                        if record_order_receive:
                            pass
                        else:
                            result_bidding_order_reviece = self.env[
                                Constants.SHAREVAN_BIDDING_ORDER_RECEIVE].sudo().create(
                                bidding_order_receive)

                            bidding_order_returns = {
                                'bidding_order_id': self.id,
                                'bidding_vehicle_id': id,
                                'status': '0',
                                'from_expected_time': self.from_return_time,
                                'to_expected_time': self.to_return_time,
                                'depot_id': self.to_depot_id.id
                            }
                            result_bidding_order_return = self.env[
                                Constants.SHAREVAN_BIDDING_ORDER_RETURN].sudo().create(
                                bidding_order_returns)
                else:
                    raise ValidationError(
                        _('Bidding can not approve! Because bidding company does not submit bidding vehicle infor!'))
                try:
                    list_user.append(106)
                    title = 'Systems notification'
                    body = 'Bidding Order has been approved!'
                    val = {
                        'user_id': [user.id],
                        'title': title,
                        'content': body,
                        'click_action': ClickActionType.bidding_company.value,
                        'message_type': MessageType.success.value,
                        'type': NotificationType.BiddingOrder.value,
                        'object_status': BiddingStatus.Received.value,
                        'item_id': self.id,
                    }
                    logger.info(
                        "Approved bidding order successful!",
                        Notification._name, self.id,
                        exc_info=True)
                    http.request.env[Notification._name].create(val)
                except:
                    logger.warn(
                        "Something wrong when send message to user!",
                        Notification._name, self.id,
                        exc_info=True)
            elif self.type == BiddingStatusType.NotApprove.value:
                if vals['bidding_vehicle_id'][0][2]:
                    vehicle_ids = ""
                    for id in vals['bidding_vehicle_id'][0][2]:
                        if vehicle_ids == "":
                            vehicle_ids += str(id)
                        else:
                            vehicle_ids += "," + str(id)
                    result = http.request.env[
                        Constants.SHAREVAN_BIDDING_PACKAGE].confirm_bidding_vehicle_for_bidding_order(
                        self.id, vehicle_ids)
            elif self.type == BiddingStatusType.Cancel.value:
                # if self.bidding_package_id.id:
                #     http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE]. \
                #         browse(self.bidding_package_id.id).write(
                #         {'status': BiddingPackageStatus.NotBidding.value})
                bidding_order = self.env[Constants.SHAREVAN_BIDDING_ORDER].search(
                    [('bidding_package_id', '=', self.bidding_package_id.id), ('type', '=', '5')],
                    order='create_date asc', limit=1)
                if bidding_order:
                    bidding_order.write({'type': '0'})
                    if self.bidding_package_id.id:
                        http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE]. \
                            browse(self.bidding_package_id.id).write(
                            {'status': BiddingPackageStatus.WaitingAccept.value})
                else:
                    if self.bidding_package_id.id:
                        http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE]. \
                            browse(self.bidding_package_id.id).write(
                            {'status': BiddingPackageStatus.OverTimeBidding.value})
                if user:
                    try:
                        list_user.append(106)
                        title = 'Systems notification'
                        body = 'Oops Bidding Order canceled'
                        val = {
                            'user_id': [user.id],
                            'title': title,
                            'content': body,
                            'click_action': ClickActionType.bidding_company.value,
                            'message_type': MessageType.warning.value,
                            'type': NotificationType.BiddingOrder.value,
                            'object_status': BiddingStatus.NotConfirm.value,
                            'item_id': self.id,
                        }
                        http.request.env[Notification._name].create(val)
                    except:
                        logger.warn("Something wrong when send message to user!", Notification._name, self.id,
                                    exc_info=True)
                    logger.warn(
                        "Order has been canceled!", Notification._name, self.id, exc_info=True)
                return res

    @api.onchange('from_depot_id')
    def onchange_from_depot(self):
        for record in self:
            record.update({'from_latitude': record['from_depot_id'].latitude})
            record.update({'from_longitude': record['from_depot_id'].longitude})

    @api.onchange('to_depot_id')
    def onchange_to_depot(self):
        for record in self:
            record.update({'to_latitude': record['to_depot_id'].latitude})
            record.update({'to_longitude': record['to_depot_id'].longitude})

    def is_approved_check(self):
        for record in self:
            record.bidding_package_id.status = BiddingPackageStatus.WaitingAccept.value
            record.update({'type': BiddingStatusType.Approved.value, 'bidding_package_id': record.bidding_package_id})

    def is_unapproved_check(self):
        for record in self:
            notice = ''
            if record.note is False:
                notice += "Reason is not empty !!!!"
                self.env.user.notify_danger(message=notice, title="Enter Reason")
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Bidding order',
                    'view_mode': 'form',
                    'res_model': 'sharevan.bidding.order',
                    'res_id': self.id,
                    'context': {
                        'form_view_initial_mode': 'edit',
                    },
                }
            record.bidding_package_id.confirm_time = False
            record.bidding_package_id.max_confirm_time = False
            record.update({'type': BiddingStatusType.Cancel.value})
