from datetime import datetime

from mymodule.base_next.models.bidding import BiddingOrder
from mymodule.constants import Constants
from mymodule.enum.BiddingOrderReturnStatus import BiddingOrderReturnStatus
from mymodule.enum.BiddingStatus import BiddingStatus
from mymodule.enum.BiddingStatusType import BiddingStatusType
from odoo import models, _, http
from odoo.exceptions import ValidationError


class BiddingOrderReturn(models.Model):
    _name = 'sharevan.bidding.order.return'
    _description = 'Bidding order return'
    _inherit = 'sharevan.bidding.order.return'

    def confirm_return_items(self, bidding_order_id, bidding_return_id):
        user = self.env['res.users'].search([('id', '=', self.env.uid)])
        company_id = user.company_id.id
        if user:
            if bidding_order_id:
                record_bididng_order = http.request.env[BiddingOrder._name]. \
                    web_search_read([['id', '=', bidding_order_id]], fields=None,
                                    offset=0, limit=10, order='')
                if record_bididng_order['records']:
                    if bidding_return_id:
                        record_bidding_order_return = http.request.env[BiddingOrderReturn._name]. \
                            web_search_read([['id', '=', bidding_return_id]], fields=None,
                                            offset=0, limit=10, order='')
                        if record_bidding_order_return['records']:
                            if record_bididng_order['records'][0]['status']:
                                if record_bididng_order['records'][0]['type']:
                                    if record_bididng_order['records'][0]['status'] == BiddingStatus.Returned.value and record_bidding_order_return['records'][0]['status'] == BiddingOrderReturnStatus.has_returned_the_item.value:
                                        if record_bididng_order['records'][0]['status'] == BiddingStatus.Received.value and record_bididng_order['records'][0]['type'] == BiddingStatusType.Approved.value:
                                            datetime.today().strftime('YYYY-MM-DD HH24:MI:SS')
                                            current_date = datetime.today()
                                            http.request.env[BiddingOrderReturn._name]. \
                                                browse(record_bididng_order['records'][0]['id']).write(
                                                {'actual_time': current_date,
                                                 'status': BiddingOrderReturnStatus.has_returned_the_item.value})

                                            http.request.env[BiddingOrder._name]. \
                                                browse(record_bidding_order_return['records'][0]['id']).write(
                                                {'status': BiddingStatus.Returned.value})

                                            if company_id:
                                                # record_res_company = http.request.env[ResCompany._name]. \
                                                #     web_search_read([['id', '=', company_id]], fields=None,
                                                #                     offset=0, limit=10, order='')

                                                record_res_company = http.request.env['res.company']. \
                                                    web_search_read([['id', '=', company_id]], fields=None,
                                                                    offset=0, limit=10, order='')

                                                if record_res_company['records']:
                                                    if record_res_company['records'][0]['point'] is None or record_res_company['records'][0]['point']== 0:
                                                        company_point = Constants.COMPANY_POINT
                                                        http.request.env['res.company']. \
                                                            browse(record_res_company['records'][0]['id']).write(
                                                            {'point':company_point})
                                                        return True
                                                    else:
                                                        company_point = Constants.COMPANY_POINT
                                                        company_point += record_res_company['records'][0]['point']
                                                        http.request.env['res.company']. \
                                                            browse(record_res_company['records'][0]['id']).write(
                                                            {'point': company_point})
                                                        return True
                                                else:
                                                    raise ValidationError(_("Company's driver does not existed!"))
                                            else:
                                                raise ValidationError(_("Company's driver does not existed!"))
                                        else:
                                            raise ValidationError(_("You cannot confirm return order number because the bidding order number is not approved!"))
                                    else:
                                        raise ValidationError(_("Order has been confirmed to received !"))

                                else:
                                    raise ValidationError(_('Bidding order type null!'))
                            else:
                                raise ValidationError(_('Bidding order status null!'))

                        else:
                            raise ValidationError(_('Bidding order return  does not existed!'))

                    else:
                        raise ValidationError(_('bidding_return_id parameter can not null!'))
                else:
                    raise ValidationError(_('Bidding order does not existed!'))
            else:
                raise ValidationError(_('biddng_id parameter can not null!'))
        else:
            raise ValidationError(_('Authentication failed!'))
