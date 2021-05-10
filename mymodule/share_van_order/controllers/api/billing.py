# -*- coding: utf-8 -*-
import json
import logging

import requests

from odoo import http
from odoo.tools import date_utils, config

_logger = logging.getLogger(__name__)


class BillingApi:
    @staticmethod
    def calc_price(bill_lading):
        i = 0
        dict_billLadings = {}
        billL_details = bill_lading['bill_lading_detail_ids']
        for bill_detail in billL_details:
            bill_detail['billLadingId'] = bill_lading['id']
            bill_detail['trans_id'] = i
            packages = bill_detail['billPackages']
            zone_id = 0
            for pg in packages:
                pg['productType'] = {'id': pg['product_type_id'][0]}
                zone_id = pg['zone_area_id'][0] if len(pg['zone_area_id']) > 1 else 0
                pg['item_name'] = "" if not pg['item_name'] else pg['item_name']
                if not pg['description']:
                    del pg['description']
                del pg['product_type_id']
                # del pg['bill_lading_detail_id']
                del pg['product_type_name']
                del pg['zone_area_id']
            bill_detail['billPackages'] = packages
            # bill_detail['warehouse'] = bill_detail['warehouse'][0]
            del bill_detail['warehouse']
            if zone_id != 0:
                bill_detail['zone_area_id'] = zone_id
            dict_billLadings[i] = bill_detail
            i = i + 1
        if bill_lading['insurance_id']:
            bill_lading['insurance'] = {'id': bill_lading['insurance_id']}
        bill_lading['arrBillLadingDetail'] = billL_details
        bill_lading['order_package'] = {'id': bill_lading['order_package_id']}
        del bill_lading['bill_lading_detail_ids']
        arrBillLadingDetail = json.dumps(bill_lading, default=date_utils.json_default, skipkeys=True)
        try:
            headers = {
                'Authorization': 'Bearer ' + http.request.session.access_token,
                'Accept-Language': 'en',
                'Content-Type': 'application/json'
            }
            url = config['security_url'] + config['cal_price_host'] + ':' + config['cal_price_port']+"/app/v1/price/calc/bill"
            resps = requests.post(url, data=arrBillLadingDetail,
                                  headers=headers)
        except:
            _logger.error("There was problem requesting price!")
            return [], 0

        if not resps:
            return resps, 0
        resps = resps.json()
        for resp in resps['arrBillLadingDetail']:
            bill_detail = dict_billLadings[resp['trans_id']]
            bill_detail['price'] = resp['price']
            del bill_detail['trans_id']
        return billL_details, resps
