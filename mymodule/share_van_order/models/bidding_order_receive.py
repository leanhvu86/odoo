from mymodule.base_next.models.bidding import BiddingOrder
from mymodule.enum.BiddingOrderReceiveStatus import BiddingOrderReceivedStatus
from mymodule.enum.BiddingStatus import BiddingStatus
from mymodule.enum.BiddingStatusType import BiddingStatusType
from odoo import models, _, http
from datetime import datetime
from odoo.exceptions import ValidationError


class BiddingOrderReceive(models.Model):
    _name = 'sharevan.bidding.order.receive'
    _description = 'Bidding order receive'
    _inherit = 'sharevan.bidding.order.receive'

    def confirm_received_items(self, bidding_order_id, id):
        if bidding_order_id:
            record = http.request.env[BiddingOrder._name]. \
                web_search_read([['id', '=', bidding_order_id]], fields=None,
                                offset=0, limit=10, order='')
            if record['records']:
                if id:
                    record_bidding_order_received = http.request.env[BiddingOrderReceive._name]. \
                        web_search_read([['id', '=', id]], fields=None,
                                        offset=0, limit=10, order='')
                    if record_bidding_order_received['records']:
                        if record['records'][0]['type'] == BiddingStatus.Received.value and record_bidding_order_received['records'][0]['status'] == BiddingOrderReceivedStatus.received.value:

                            if record['records'][0]['type'] == BiddingStatusType.Approved.value and record['records'][0]['status'] == BiddingStatus.NotConfirm.value:
                                datetime.today().strftime('YYYY-MM-DD HH24:MI:SS')
                                current_date = datetime.today()
                                http.request.env[BiddingOrderReceive._name]. \
                                    browse(record_bidding_order_received['records'][0]['id']).write(
                                    {'actual_time': current_date,
                                     'status': BiddingOrderReceivedStatus.received.value})

                                http.request.env[BiddingOrder._name]. \
                                    browse(record['records'][0]['id']).write(
                                    {'status': BiddingStatus.Received.value})

                                return True
                            else:
                                raise ValidationError(_('You can not received item because bidding order number is not approved!'))
                        else:
                            raise ValidationError(_('Order has been confirmed!'))
                    else:
                        raise ValidationError(_('Bidding order received does not existed!'))
                else:
                    raise ValidationError(_('id paramater can not null!'))
            else:
                raise ValidationError(_('Bidding order does not existed!'))
        else:
            raise ValidationError(_('bidding_order_id can not null!'))
