# -*- coding: utf-8 -*-
import datetime
import json
import json as simplejson
import logging
from datetime import datetime, timedelta

import pytz
import requests

from mymodule.base_next.models.bidding_vehicle import BiddingVehicle
from mymodule.base_next.models.cargo import Cargo
from mymodule.constants import Constants
from mymodule.enum.BiddingPackageStatus import BiddingPackageStatus
from mymodule.enum.BiddingStatus import BiddingStatus
from mymodule.enum.BiddingStatusType import BiddingStatusType
from mymodule.enum.ClickActionType import ClickActionType
from mymodule.enum.MessageType import MessageType
from mymodule.enum.NotificationType import NotificationType
from mymodule.share_van_order.models.bidding_order import BiddingOrder
from mymodule.share_van_order.models.sharevan_notification import Notification
from odoo import http
from odoo import models, _, fields
from odoo.exceptions import ValidationError
from odoo.tools import config

logger = logging.getLogger(__name__)
utc = pytz.UTC


class BiddingPackage(models.Model):
    _name = Constants.SHAREVAN_BIDDING_PACKAGE
    _description = 'Bidding order'
    _inherit = Constants.SHAREVAN_BIDDING_PACKAGE

    cargo_ids = fields.Many2many(Constants.SHAREVAN_CARGO, string='Cargo', required=True,
                                 domain=lambda self: "[('bidding_package_id', '=', False)]")

    def get_bidding_package_time(self):
        # query = """
        #        select bidding_time from sharevan_bidding_package where status = %s and bidding_time > CURRENT_DATE
        #    """
        query = """
            select distinct to_char(bidding_time,'yyyy-mm-dd HH24:00:00') 
                from sharevan_bidding_package 
            where status = %s 
                and to_char(bidding_time,'yyyy-mm-dd HH24:00:00') >=  to_char(now() at time zone 'UTC','yyyy-mm-dd HH24') 
                order by to_char(bidding_time,'yyyy-mm-dd HH24:00:00') ASC
                  """
        self.env.cr.execute(query, (BiddingStatus.NotConfirm.value,))
        records = self._cr.fetchall()
        jsonRe = []
        for rec in records:
            jsonRe.append(rec[0])
        return {
            'records': jsonRe
        }

    def accept_driver_order(self, driver_id, bidding_package_id):
        print(driver_id, bidding_package_id)

    def request_driver_order(self, driver_id, bidding_package_id):
        print(driver_id, bidding_package_id)
        query_get_bidding_package_infor = """ 
            SELECT bidding_package.id, bidding_package.bidding_order_id, bidding_package.bidding_package_number, 
                bidding_package.status, bidding_package.total_weight, bidding_package.distance, 
                to_char(from_receive_time,'yyyy-mm-dd HH24:00:00') from_receive_time, 
                to_char(to_receive_time,'yyyy-mm-dd HH24:00:00') to_receive_time, 
                to_char(from_return_time,'yyyy-mm-dd HH24:00:00') from_return_time, 
                to_char(to_return_time,'yyyy-mm-dd HH24:00:00') to_return_time, bidding_package.price_origin, 
                bidding_package.price ,from_depot.name from_depot_name, 
                to_char(bidding_package.create_date,'yyyy-mm-dd HH24:00:00') create_date,
                from_depot.address from_depot_address,to_depot.name to_depot_name,
                to_depot.address to_depot_address
            FROM public.sharevan_bidding_package bidding_package 
                join sharevan_depot from_depot on from_depot.id = bidding_package.from_depot_id
                join sharevan_depot to_depot on to_depot.id = bidding_package.to_depot_id
                where 1=1 and bidding_package.id = %s"""

        self.env.cr.execute(query_get_bidding_package_infor, (bidding_package_id,))
        result = self._cr.dictfetchall()
        if result:
            for re in result:
                total_cargos = []
                cargo_info_dtl = []
                query_count_cargo = """ 
                    SELECT json_agg(t) FROM ( 
                        select count(cargo.id) from sharevan_cargo cargo
                            join sharevan_bidding_package bidding_package 
                                on bidding_package.id = cargo.bidding_package_id 
                        where bidding_package.id = %s ) t """
                self.env.cr.execute(query_count_cargo, (re['id'],))
                result_count_cargo = self._cr.fetchall()
                total_cargos = result_count_cargo[0][0][0]
                query_get_cargo_info = """ 
                    SELECT sharevan_cargo.id, sharevan_cargo.cargo_number, sharevan_cargo.from_depot_id, 
                        sharevan_cargo.to_depot_id, sharevan_cargo.distance, sharevan_cargo.size_id, 
                        sharevan_cargo.weight, sharevan_cargo.description,  sharevan_cargo.price, 
                        sharevan_cargo.from_latitude, sharevan_cargo.to_latitude, sharevan_cargo.bidding_package_id, 
                        sharevan_cargo.from_longitude, sharevan_cargo.to_longitude,size_standard,
                        size_standard.length, size_standard.width, size_standard.height, size_standard.type,
                        size_standard.from_weight, 
                        size_standard.to_weight, size_standard.price_id, size_standard.price,
                        size_standard.size_standard_seq, size_standard.long_unit, size_standard.weight_unit
                    FROM public.sharevan_cargo 
                        join sharevan_size_standard  size_standard on size_standard.id = sharevan_cargo.size_id
                        join sharevan_bidding_package_sharevan_cargo_rel rel 
                        on rel.sharevan_cargo_id=sharevan_cargo.id
                    where rel.sharevan_bidding_package_id = %s """
                self.env.cr.execute(query_get_cargo_info, (re['id'],))
                result_query_get_cargo_info = self._cr.dictfetchall()
                cargo_ids = []
                if result_query_get_cargo_info:
                    for cargo in result_query_get_cargo_info:
                        cargo_ids.append(cargo['id'])
                        data = {
                            'id': cargo['id'],
                            'cargo_number': cargo['cargo_number'],
                            'from_depot_id': cargo['from_depot_id'],
                            'to_depot_id': cargo['to_depot_id'],
                            'distance': cargo['distance'],
                            'size_id': cargo['size_id'],
                            'weight': cargo['weight'],
                            'description': cargo['description'],
                            'price': cargo['price'],
                            'from_latitude': cargo['from_latitude'],
                            'to_latitude': cargo['to_latitude'],
                            'bidding_package_id': cargo['bidding_package_id'],
                            'from_longitude': cargo['from_longitude'],
                            'to_longitude': cargo['to_longitude'],
                            'size_standard': {
                                'length': cargo['length'],
                                'width': cargo['width'],
                                'height': cargo['height'],
                                'type': cargo['id'],
                                'from_weight': cargo['from_weight'],
                                'to_weight': cargo['to_weight'],
                                'price_id': cargo['price_id'],
                                'price': cargo['price'],
                                'long_unit': cargo['long_unit'],
                                'weight_unit': cargo['weight_unit']
                            }

                        }
                        cargo_info_dtl.append(data)
                else:
                    cargo_info_dtl = []

                query_get_size_standard = """
                    SELECT json_agg(t) FROM (  
                        select distinct  id, length, width, height, type, from_weight, to_weight, price_id, price,
                            size_standard_seq, cargo_price_ids, long_unit, weight_unit 
                        from sharevan_size_standard size_stand
                            where size_stand.id in 
                        (select cargo.size_id from sharevan_cargo cargo where cargo.id  ::integer in ( """
                if cargo_ids:
                    for cargo_id in cargo_ids:
                        query_get_size_standard += str(cargo_id) + ","
                    query_get_size_standard = query_get_size_standard[:-1]
                    query_get_size_standard += "))) t"

                self.env.cr.execute(query_get_size_standard, (cargo_ids))
                result_get_size_standard = self._cr.fetchall()
                size_standard_arr = []
                if result_get_size_standard[0][0]:
                    for rec in result_get_size_standard[0][0]:
                        query_count_cargo_map_with_size_standard = """ 
                            select count(*) from sharevan_cargo cargo 
                                where cargo.id  ::integer in ( """
                        for cargo_id in cargo_ids:
                            query_count_cargo_map_with_size_standard += str(cargo_id) + ","
                        query_count_cargo_map_with_size_standard = query_count_cargo_map_with_size_standard[:-1]
                        query_count_cargo_map_with_size_standard += """ ) and cargo.size_id = %s  """
                        self.env.cr.execute(query_count_cargo_map_with_size_standard, (rec['id'],))
                        result_count_cargo_map_with_size_standard = self._cr.dictfetchall()

                        query_caculate_cargo_total_weight = """ 
                            select sum(weight) sum from sharevan_cargo cargo 
                                where cargo.id  ::integer in ( """
                        for cargo_id in cargo_ids:
                            query_caculate_cargo_total_weight += str(cargo_id) + ","
                        query_caculate_cargo_total_weight = query_caculate_cargo_total_weight[:-1]
                        query_caculate_cargo_total_weight += """ ) and cargo.size_id = %s  """
                        self.env.cr.execute(query_caculate_cargo_total_weight, (rec['id'],))
                        result_query_caculate_cargo_total_weight = self._cr.dictfetchall()
                        total_weight = 0
                        if result_query_caculate_cargo_total_weight:
                            total_weight = result_query_caculate_cargo_total_weight[0]['sum']
                        if result_count_cargo_map_with_size_standard:
                            size_standard_data = {
                                'id': rec['id'],
                                'length': rec['length'],
                                'width': rec['width'],
                                'height': rec['height'],
                                'type': rec['type'],
                                'from_weight': rec['from_weight'],
                                'to_weight': rec['to_weight'],
                                'price_id': rec['price_id'],
                                'price': rec['price'],
                                'size_standard_seq': rec['size_standard_seq'],
                                'long_unit': rec['long_unit'],
                                'weight_unit': rec['weight_unit'],
                                'cargo_quantity': result_count_cargo_map_with_size_standard[0]['count'],
                                'total_weight': total_weight
                            }
                            size_standard_arr.append(size_standard_data)
                url = config['security_url'] + config['socket_link'] + "request_driver"
                # data to be sent to api
                headers = {'Content-Type': 'application/json'}
                # Can do the same for data, allowing you to store it as a map.
                infor = []
                record_socket = []

                vals = {
                    'id': re['id'],
                    'bidding_order_id': re['bidding_order_id'],
                    'bidding_package_number': re['bidding_package_number'],
                    'status': re['status'],
                    'total_weight': re['total_weight'],
                    'distance': re['distance'],
                    'from_receive_time': re['from_receive_time'],
                    'from_depot': {
                        'name': re['from_depot_name'],
                        'address': re['from_depot_address']
                    },
                    'to_depot': {
                        'name': re['to_depot_name'],
                        'address': re['to_depot_address']
                    },
                    'to_receive_time': re['to_receive_time'],
                    'from_return_time': re['from_return_time'],
                    'to_return_time': re['to_return_time'],
                    'price_origin': re['price_origin'],
                    'price': re['price'],
                    'create_date': re['create_date'],
                    'total_cargo': total_cargos['count'],
                    'cargo_types': size_standard_arr
                }
                query_driver = """
                    select user_id  from fleet_driver where id =%s
                                """
                self.env.cr.execute(query_driver, (driver_id,))
                driver = self._cr.dictfetchall()
                if driver:
                    data_to_send = {
                        'result': {
                            'records': [vals]
                        },
                        'user_id': driver[0]['user_id']
                    }
                    body = {'data': data_to_send}

                    # sending post request and saving response as response object
                    r = requests.post(url, json=body, headers=headers)
                    pastebin_url = json.loads(r.text)
                    if pastebin_url['status'] == 200:
                        logger.debug("Log for debug xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
                        logger.debug(pastebin_url)
                        return vals
                    else:
                        logger.debug(pastebin_url)
                        raise ValidationError('Driver not online')
        else:
            raise ValidationError('BillPackage not found')

    def get_area(self, location_type, parent_id):
        query_area = """  
            Select id , name, code,parent_id 
            from sharevan_area
                where location_type = %s and status = 'running' 
                               """
        param = []
        param.append(location_type)
        if parent_id and parent_id > 0:
            query_area += """ and parent_id = %s """
            param.append(parent_id)
        query_area += """ order by name asc """
        self.env.cr.execute(query_area, (param))
        result_area = self._cr.dictfetchall()
        return {
            'records': result_area
        }

    def create_bidding_order(self, bidding_package_id, confirm_time):
        list_user_id = []
        user = self.env['res.users'].search([('id', '=', self.env.uid)])
        if user:
            if bidding_package_id:
                query_get_bidding_package = """  
                    SELECT id, bidding_order_id, bidding_package_number, status, confirm_time, release_time, 
                        bidding_time, max_count, from_depot_id, to_depot_id, total_weight, distance, from_latitude,
                        to_latitude, to_char(from_receive_time,'yyyy-mm-dd HH24:00:00') from_receive_time, 
                        to_char(to_receive_time,'yyyy-mm-dd HH24:00:00') to_receive_time, 
                        to_char(from_return_time,'yyyy-mm-dd HH24:00:00') from_return_time, 
                        to_char(to_return_time,'yyyy-mm-dd HH24:00:00') to_return_time, price_origin, 
                        price, create_date, countdown_time, price_time_change, 
                        price_level_change, from_longitude, to_longitude, 
                        to_char(max_confirm_time,'yyyy-mm-dd HH24:00:00') max_confirm_time, change_price_time 
                    FROM public.sharevan_bidding_package bidding_package where bidding_package.id = %s 
                       """
                self.env.cr.execute(query_get_bidding_package, (bidding_package_id,))
                result_get_bidding_package = self._cr.fetchall()
                if result_get_bidding_package:
                    query_get_bidding_order = """ 
                                            SELECT json_agg(t) FROM ( 
                                                select id from sharevan_bidding_order bidding_order 
                                            where  bidding_order.bidding_package_id = %s and bidding_order.type != %s) t """
                    self.env.cr.execute(query_get_bidding_order, (bidding_package_id, BiddingStatus.Cancel.value))
                    result_get_bidding_order = self._cr.fetchall()
                    bidding_order = result_get_bidding_order[0][0]
                    if bidding_order:
                        raise ValidationError(
                            _('Bidding package has already been bidded! Bidding package id: ' + bidding_package_id))
                    record_bidding_package = result_get_bidding_package[0]
                    total_cargos = []
                    query_count_cargo = """ SELECT json_agg(t) FROM ( select count(cargo.id) from sharevan_cargo cargo
                                                                                   join sharevan_bidding_package bidding_package on bidding_package.id = cargo.bidding_package_id 
                                                                                   where bidding_package.id = %s ) t """
                    self.env.cr.execute(query_count_cargo, (bidding_package_id,))
                    result_count_cargo = self._cr.fetchall()
                    total_cargos = result_count_cargo[0][0][0]

                    max_confirm_time_old = datetime.datetime.strptime(confirm_time, "%Y-%m-%d %H:%M:%S")
                    max_confirm_time_new = max_confirm_time_old + timedelta(minutes=record_bidding_package[21])
                    jsonRe = []
                    if record_bidding_package:
                        bidding_order = {
                            'company_id': user.company_id.id,
                            'bidding_order_number': 'New',
                            'from_depot_id': record_bidding_package[8],
                            'to_depot_id': record_bidding_package[9],
                            'total_weight': record_bidding_package[10],
                            'total_cargo': total_cargos['count'],
                            'price': record_bidding_package[19],
                            'distance': record_bidding_package[11],
                            'type': '0',
                            'status': '0',
                            'bidding_package_id': int(bidding_package_id),
                            'from_receive_time': record_bidding_package[14],
                            'to_receive_time': record_bidding_package[15],
                            'to_return_time': record_bidding_package[17],
                            'max_confirm_time': max_confirm_time_new,
                            'bidded_user_id': user.partner_id.id
                        }
                        result = self.env[BiddingOrder._name].sudo().create(bidding_order)
                        bidding_order_id = result.id

                        content = {
                            'max_confirm_time': max_confirm_time_new,
                            'bidding_order_id': result.id
                        }
                        jsonRe.append(content)
                        if result:
                            http.request.env[BiddingPackage._name]. \
                                browse(bidding_package_id).write(
                                {'max_confirm_time': max_confirm_time_new,
                                 'status': BiddingPackageStatus.WaitingAccept.value,
                                 'bidding_order_id': result.id})
                        list_user_id.append(user.id)
                        list_package = []
                        list_package.append(result_get_bidding_package)
                        record_socket = []
                        self.send_bidding_information_success(list_user_id, result.id)
                        records = {
                            'length': len(result),
                            'records': jsonRe
                        }
                        simplejson.dumps(records, indent=4, sort_keys=True, default=str)

                        self.env[BiddingPackage._name].sudo().write({
                            'max_confirm_time': max_confirm_time_new,
                            'confirm_time': max_confirm_time_old
                        })
                        print('send socket')
                        self.push_notification_socket(None, bidding_order_id, bidding_package_id)
                        return records
                    else:
                        raise ValidationError(_('Bidding package does not existed!'))
                else:
                    raise ValidationError(_('Bidding package does not existed!'))
            else:
                raise ValidationError(_('Bidding package does not existed!'))
        else:
            raise ValidationError(_('User not does existed!'))

    def create_bidding_orderv3(self, bidding_package_id):
        user = self.env['res.users'].search([('id', '=', self.env.uid)])
        if user:
            if bidding_package_id:
                query_get_bidding_package = """  
                           SELECT id, bidding_order_id, bidding_package_number, status, confirm_time, release_time, 
                           bidding_time, max_count, from_depot_id, to_depot_id, total_weight, distance, from_latitude,
                           to_latitude, to_char(from_receive_time,'yyyy-mm-dd HH24:00:00') from_receive_time, 
                           to_char(to_receive_time,'yyyy-mm-dd HH24:00:00') to_receive_time, 
                           to_char(from_return_time,'yyyy-mm-dd HH24:00:00') from_return_time, 
                           to_char(to_return_time,'yyyy-mm-dd HH24:00:00') to_return_time, price_origin, 
                           price, create_date, countdown_time, price_time_change, 
                           price_level_change, from_longitude, to_longitude, 
                           limit_publish_time limit_publish_time,
                           to_char(max_confirm_time,'yyyy-mm-dd HH24:00:00') max_confirm_time, change_price_time 
                       FROM public.sharevan_bidding_package bidding_package where bidding_package.id = %s
                        and bidding_package.status = '0' and bidding_package.is_publish = TRUE 
                          """
                self.env.cr.execute(query_get_bidding_package, (bidding_package_id,))
                result_get_bidding_package = self._cr.dictfetchall()
                bidding_package = result_get_bidding_package[0]
                if bidding_package:
                    timenow = datetime.utcnow()
                    max_bidding_time = bidding_package.get('limit_publish_time')
                    if utc.localize(timenow) > utc.localize(max_bidding_time):  # check xem còn thời gian bidding không
                        raise ValidationError(_('Bidding package time has expired!'))

                    # xử lý tạo bidding order
                    total_cargos = []
                    query_count_cargo = """select count(cargo.id) from sharevan_cargo cargo
                                           join sharevan_bidding_package bidding_package on bidding_package.id = cargo.bidding_package_id 
                                           where bidding_package.id = %s """ % (bidding_package_id)
                    self.env.cr.execute(query_count_cargo, ())
                    result_count_cargo = self._cr.dictfetchall()
                    total_cargos = result_count_cargo[0]
                    bidding_order = {
                        'company_id': user.company_id.id,
                        'bidding_order_number': 'New',
                        'from_depot_id': bidding_package.get('from_depot_id'),
                        'to_depot_id': bidding_package.get('to_depot_id'),
                        'total_weight': bidding_package.get('total_weight'),
                        'total_cargo': total_cargos.get('count'),
                        'price': bidding_package.get('price'),
                        'distance': bidding_package.get('distance'),
                        'type': '0',
                        'status': '0',
                        'bidding_package_id': int(bidding_package_id),
                        'from_receive_time': bidding_package.get('from_receive_time'),
                        'to_receive_time': bidding_package.get('to_receive_time'),
                        'to_return_time': bidding_package.get('to_return_time'),
                        'bidded_user_id': user.partner_id.id
                    }
                    result = self.env[BiddingOrder._name].sudo().create(bidding_order)
                    if result:
                        return {
                            "records": ['Successful!']
                        }
                    raise ValidationError(_('Error, please contact to admin!'))
            else:
                raise ValidationError(_('Bidding package does not existed!'))
        else:
            raise ValidationError(_('User not does existed!'))

    def send_bidding_information_success(self, list_user_id, item_id):
        try:
            title = 'Systems notification'
            body = 'Bidding Order'
            val = {
                'user_id': list_user_id,
                'title': title,
                'content': body,
                'click_action': ClickActionType.bidding_company.value,
                'message_type': MessageType.success.value,
                'type': NotificationType.BiddingOrder.value,
                'object_status': BiddingStatus.NotConfirm.value,
                'item_id': item_id,
            }
            http.request.env[Notification._name].create(val)
        except:
            logger.warn(
                "Something wrong when send message to user!",
                Notification._name, item_id,
                exc_info=True)

    def push_notification_socket(self, data_send_socket, bidding_order_id, bidding_package_id):
        # defining the api-endpoint
        print(data_send_socket)
        url = config['security_url'] + config['socket_link'] + "pushAll"
        # data to be sent to api
        headers = {'Content-Type': 'application/json'}
        # Can do the same for data, allowing you to store it as a map.
        infor = []
        record_socket = []

        query_get_bidding_package = """  SELECT json_agg(t) FROM ( 
                          SELECT id, bidding_order_id, bidding_package_number, status, confirm_time, release_time, 
                          bidding_time, max_count, from_depot_id, to_depot_id, total_weight, distance, from_latitude,
                          to_latitude, to_char(from_receive_time,'yyyy-mm-dd HH24:00:00') from_receive_time, to_char(to_receive_time,'yyyy-mm-dd HH24:00:00') to_receive_time, to_char(from_return_time,'yyyy-mm-dd HH24:00:00') from_return_time, to_char(to_return_time,'yyyy-mm-dd HH24:00:00') to_return_time, price_origin, 
                          price, create_date,  countdown_time, price_time_change, 
                          price_level_change, from_longitude, to_longitude, max_confirm_time, change_price_time
                          FROM public.sharevan_bidding_package bidding_package where bidding_package.id = %s ) t
                          """
        self.env.cr.execute(query_get_bidding_package, (bidding_package_id,))
        result_get_bidding_package = self._cr.fetchall()
        print(result_get_bidding_package[0][0][0])

        query_get_from_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.latitude,depot.longitude,depot.depot_code,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                           join sharevan_bidding_package bidding_package on depot.id = %s ) t"""
        self.env.cr.execute(query_get_from_depot, (result_get_bidding_package[0][0][0]['from_depot_id'],))
        result_get_from_depot = self._cr.fetchall()

        array_length = len(result_get_from_depot)
        if array_length > 0:
            if result_get_from_depot[0][0]:
                val = {
                    'id': result_get_from_depot[0][0][0]['id'],
                    'address': result_get_from_depot[0][0][0]['address']
                }
                get_from_depot = val

        query_get_to_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.latitude,depot.longitude,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                                                  join sharevan_bidding_package bidding_package on depot.id = %s ) t"""
        self.env.cr.execute(query_get_to_depot, (result_get_bidding_package[0][0][0]['to_depot_id'],))
        result_get_to_depot = self._cr.fetchall()
        get_to_depot = []
        array_length = len(result_get_to_depot)
        if array_length > 0:
            if result_get_to_depot[0][0]:
                val = {
                    'id': result_get_from_depot[0][0][0]['id'],
                    'address': result_get_from_depot[0][0][0]['address']
                }
                get_to_depot = val
        vals = {
            'id': result_get_bidding_package[0][0][0]['id'],
            'bidding_order_id': bidding_order_id,
            'bidding_package_number': result_get_bidding_package[0][0][0]['bidding_package_number'],
            'status': result_get_bidding_package[0][0][0]['status'],
            'confirm_time': result_get_bidding_package[0][0][0]['confirm_time'],
            'release_time': result_get_bidding_package[0][0][0]['release_time'],
            'bidding_time': result_get_bidding_package[0][0][0]['bidding_time'],
            'max_count': result_get_bidding_package[0][0][0]['max_count'],
            'total_weight': result_get_bidding_package[0][0][0]['total_weight'],
            'distance': result_get_bidding_package[0][0][0]['distance'],
            'from_latitude': result_get_bidding_package[0][0][0]['from_latitude'],
            'price_origin': result_get_bidding_package[0][0][0]['price_origin'],
            'price': result_get_bidding_package[0][0][0]['price'],
            'change_price_time': result_get_bidding_package[0][0][0]['change_price_time'],
            'max_confirm_time': result_get_bidding_package[0][0][0]['max_confirm_time'],
            'price_level_change': result_get_bidding_package[0][0][0]['price_level_change'],
            'from_depot': get_from_depot,
            'to_depot': get_to_depot,
            'total_cargo': ''
        }
        # data_send_socket = {
        #     'actionType': 'biddingPackage',
        #     'lstBiddingPackages':vals,
        #     'bidding_order_id': bidding_order_id,
        #     'bidding_package_id':bidding_package_id
        # }

        data_send_socket = {
            'actionType': 'biddingPackage',
            'lstBiddingPackages': [vals]
        }

        # data_send_socket = simplejson.dumps(data_send_socket)
        # record_socket.append(data_send_socket)

        infor.append(data_send_socket)
        # data_send_socket = simplejson.dumps(data_send_socket)
        data_to_send = {
            'result': {
                'records': [data_send_socket]
            }

        }
        # data_to_send = simplejson.dumps(data_to_send)
        # data = json.dumps(data_to_send)
        # print(data)
        # body = data

        # datat = json.dumps(data_to_send)
        # print(datat)
        # datat = json.dumps(data)
        # data_to_send = simplejson.dumps(data_to_send)
        body = {'data': data_to_send}

        # sending post request and saving response as response object
        r = requests.post(url, json=body, headers=headers)
        # r = requests.post(url=API_ENDPOINT, data=data, headers)
        # extracting response text
        pastebin_url = r.text
        logger.debug("Log for debug xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        logger.debug(pastebin_url)
        print("The pastebin URL is:%s" % pastebin_url)

    def confirm_bidding_vehicle_for_bidding_order(self, bidding_order_id, bidding_vehicle_ids):

        bidding_order_id = int(bidding_order_id)
        bidding_vehicle_id_valid = []
        list_user_id = []
        bidding_order_number = ''
        if int(bidding_order_id) and bidding_vehicle_ids:
            record_bidding_order = http.request.env[BiddingOrder._name]. \
                web_search_read([['id', '=', bidding_order_id]], fields=None,
                                offset=0, limit=10, order='')
            if record_bidding_order['records']:
                # bidding_order_number = record_bidding_order.bidding_order_number
                query_get_order_bidding_vehicle = """ SELECT json_agg(t) FROM ( SELECT sharevan_bidding_order_id, sharevan_bidding_vehicle_id
                	                                                              FROM public.sharevan_bidding_order_sharevan_bidding_vehicle_rel rel where rel.sharevan_bidding_order_id = %s ) t"""
                self.env.cr.execute(query_get_order_bidding_vehicle, (bidding_order_id,))
                result_get_order_bidding_vehicle = self._cr.fetchall()
                if result_get_order_bidding_vehicle[0][0]:
                    for rec in result_get_order_bidding_vehicle[0][0]:
                        query_delete_order_bidding_vehicle = """ delete from sharevan_bidding_order_sharevan_bidding_vehicle_rel rel where rel.sharevan_bidding_order_id = %s  and rel.sharevan_bidding_vehicle_id = %s """
                        self.env.cr.execute(query_delete_order_bidding_vehicle,
                                            (rec['sharevan_bidding_order_id'], rec['sharevan_bidding_vehicle_id'],))
                if bidding_vehicle_ids:
                    bidding_vehicle_id_arr = bidding_vehicle_ids.split(",")
                    for bidding_vehicle_id in bidding_vehicle_id_arr:

                        record_bidding_vehicle = http.request.env[BiddingVehicle._name]. \
                            web_search_read([['id', '=', bidding_vehicle_id]], fields=None,
                                            offset=0, limit=10, order='')

                        if record_bidding_vehicle['records']:
                            user = self.env['res.users'].search(
                                [('id', '=', record_bidding_vehicle['records'][0]['res_user_id'][0])])
                            if user:
                                list_user_id.append(user.id)
                            http.request.env[BiddingVehicle._name]. \
                                browse(bidding_vehicle_id).write(
                                {'status': '1'})
                            bidding_vehicle_id_valid.append(bidding_vehicle_id)
                            # list_user_id.append(record_bidding_vehicle.res_user_id)
                        else:
                            raise ValidationError(_('Bidding Vehicle does not existed with id ' + bidding_vehicle_id))

                    http.request.env[BiddingOrder._name]. \
                        browse(bidding_order_id).write(
                        {
                            'type': BiddingStatusType.Waiting.value,
                            'mobile': True})

                    for re in bidding_vehicle_id_valid:
                        query = """ INSERT INTO public.sharevan_bidding_order_sharevan_bidding_vehicle_rel(sharevan_bidding_order_id, sharevan_bidding_vehicle_id) VALUES(%s, %s)"""
                        self.env.cr.execute(query, (bidding_order_id, re,))
                    self.send_order_infor_to_driver(list_user_id, bidding_order_id)

                    return True
                else:
                    raise ValidationError(_('bidding_vehicle_ids is null!'))
            else:
                raise ValidationError(_('Bidding Order does not existed!'))
        else:
            raise ValidationError(_('Parameters are invalid!'))

    def confirm_bidding_vehicle_for_bidding_order_origin(self, bidding_order_id, bidding_vehicle_ids):
        bidding_order_id = int(bidding_order_id)
        bidding_vehicle_id_valid = []
        list_user_id = []
        if int(bidding_order_id) and bidding_vehicle_ids:
            record_bidding_order = http.request.env[BiddingOrder._name]. \
                web_search_read([['id', '=', bidding_order_id]], fields=None,
                                offset=0, limit=10, order='')
            if record_bidding_order['records']:
                # bidding_order_number = record_bidding_order.bidding_order_number
                query_get_order_bidding_vehicle = """ 
                    SELECT json_agg(t) FROM ( 
                        SELECT sharevan_bidding_order_id, sharevan_bidding_vehicle_id
                	        FROM public.sharevan_bidding_order_sharevan_bidding_vehicle_rel rel 
                	    where rel.sharevan_bidding_order_id = %s ) t"""
                self.env.cr.execute(query_get_order_bidding_vehicle, (bidding_order_id,))
                result_get_order_bidding_vehicle = self._cr.fetchall()
                if result_get_order_bidding_vehicle[0][0]:
                    for rec in result_get_order_bidding_vehicle[0][0]:
                        query_delete_order_bidding_vehicle = """ 
                            delete from sharevan_bidding_order_sharevan_bidding_vehicle_rel rel 
                                where rel.sharevan_bidding_order_id = %s  and rel.sharevan_bidding_vehicle_id = %s """
                        self.env.cr.execute(query_delete_order_bidding_vehicle,
                                            (rec['sharevan_bidding_order_id'], rec['sharevan_bidding_vehicle_id'],))
                if len(bidding_vehicle_ids) > 0:
                    user = self.env['res.partner'].search(
                        [('user_id', '=', http.request.env.uid)])
                    for bidding_vehicle_id in bidding_vehicle_ids:
                        query_vehicle_driver = """
                            select veh.license_plate lisence_plate , tonnage.max_tonnage tonnage,
                                driver.phone driver_phone_number,
                                veh.company_id,driver.ssn id_card,driver.user_id res_user_id, 
                                veh.vehicle_type,tonnage.type_unit weight_unit
                            from fleet_vehicle veh 
                                join fleet_driver driver on driver.company_id = veh.company_id
                                join sharevan_tonnage_vehicle tonnage on tonnage.id = veh.tonnage_id
                            where veh.id = %s and driver.id= %s ;
                        """
                        self.env.cr.execute(query_vehicle_driver,
                                            (bidding_vehicle_id['vehicle_id'], bidding_vehicle_id['driver_id'],))
                        vehicle_drive = self._cr.dictfetchall()
                        if vehicle_drive:
                            vals = {
                                'res_user_id': vehicle_drive[0]['res_user_id'],
                                'res_partner_id': user['id'],
                                'lisence_plate': vehicle_drive[0]['lisence_plate'],
                                'driver_phone_number': vehicle_drive[0]['driver_phone_number'],
                                'company_id': vehicle_drive[0]['company_id'],
                                'image_128': '',
                                'status': '1',
                                'active_deactive': 'running',
                                'id_card': vehicle_drive[0]['id_card'],
                                'tonnage': vehicle_drive[0]['tonnage'],
                                'weight_unit': vehicle_drive[0]['weight_unit'],
                                'vehicle_type': vehicle_drive[0]['vehicle_type'],
                                'vehicle_id': bidding_vehicle_id['vehicle_id'],
                                'driver_id': bidding_vehicle_id['driver_id']
                            }
                            vals['bidding_vehicle_seq'] = self.env['ir.sequence'].next_by_code(
                                'self.sharevan.bidding.vehicle') or 'New'
                            vals['code'] = vals['bidding_vehicle_seq']
                            if vehicle_drive[0]['res_user_id']:
                                list_user_id.append(int(vehicle_drive[0]['res_user_id']))
                            result = http.request.env['sharevan.bidding.vehicle'].create(vals)
                            bidding_vehicle_id_valid.append(result['id'])
                        else:
                            raise ValidationError(
                                _('Bidding Vehicle does not existed with id ' + bidding_vehicle_id['vehicle_id']))

                    http.request.env[BiddingOrder._name]. \
                        browse(bidding_order_id).write(
                        {
                            'type': BiddingStatusType.Waiting.value,
                            'mobile': True})

                    for re in bidding_vehicle_id_valid:
                        query = """ INSERT INTO public.sharevan_bidding_order_sharevan_bidding_vehicle_rel(sharevan_bidding_order_id, sharevan_bidding_vehicle_id) VALUES(%s, %s)"""
                        self.env.cr.execute(query, (bidding_order_id, re,))
                    self.send_order_infor_to_driver(list_user_id, bidding_order_id)

                    return True
                else:
                    raise ValidationError(_('bidding_vehicle_ids is null!'))
            else:
                raise ValidationError(_('Bidding Order does not existed!'))
        else:
            raise ValidationError(_('Parameters are invalid!'))

    def send_order_infor_to_driver(self, user_ids, bidding_order_id):
        try:
            title = 'Systems notification'
            body = 'You has been assigned to new bidding order'
            val = {
                'user_id': user_ids,
                'title': title,
                'content': body,
                'click_action': ClickActionType.bill_lading_detail.value,
                'message_type': MessageType.danger.value,
                'type': NotificationType.BiddingVehicle.value,
                'object_status': BiddingStatus.NotConfirm.value,
                'item_id': bidding_order_id,
            }
            http.request.env[Notification._name].create(val)

        except:
            logger.warn(
                "Save sos warning Successful! But can not send message",
                Notification._name, bidding_order_id,
                exc_info=True)

    def get_bidding_package_information(self, bidding_time, order_by, offset, limit):
        params = []
        offset_check = 0
        limit_check = 10
        hour = bidding_time.split(" ")[1][0:2]  # get hours
        query_get_bidding_package_infor = """ 
            SELECT id, bidding_order_id, bidding_package_number, status, confirm_time, release_time, 
                bidding_time, max_count,from_depot_id, to_depot_id, total_weight, 
                distance, from_latitude, from_longitude, to_latitude, to_longitude, from_receive_time, 
                to_receive_time,from_return_time, to_return_time, price_origin, price, create_date, 
                countdown_time, price_time_change, price_level_change , max_confirm_time
    	    FROM public.sharevan_bidding_package bidding_package where 1=1 
    	        and bidding_package.status ='%s'""" % (
            BiddingPackageStatus.NotBidding.value) + """
    	                                         and ( CAST(bidding_package.bidding_time  AS VARCHAR) like '% """ + """%s""" % (
                                              hour) + """:%'"""
        for i in range(int(hour)):
            if i < 10:
                hour_str = '0' + str(i)
            else:
                hour_str = str(i)
            query_get_bidding_package_infor += """ or CAST(bidding_package.bidding_time  AS VARCHAR) like '% """ + """%s""" % (
                hour_str) + """:%'"""
        query_get_bidding_package_infor += """ )  and id not in (
            select bidding_package_id from sharevan_bidding_order 
			    where type = '-1' and company_id = """
        query_get_bidding_package_infor += str(http.request.env.company.id)
        query_get_bidding_package_infor += """ and bidding_package_id is not null)  """
        print(query_get_bidding_package_infor)

        # Order by = 0 : không order by
        # Order by = 1: create_date ASC
        # Order by = 2 : create order by DESC
        # Order by = 3: distance ASC
        # Order by = 4 : distance order by DESC
        # Order by = 5: price ASC
        # Order by = 6 : create order by DESC

        if order_by == '1':
            query_get_bidding_package_infor += """ order by  bidding_package.create_date DESC """
        if order_by == '2':
            query_get_bidding_package_infor += """ order by  bidding_package.create_date DESC """
        if order_by == '3':
            query_get_bidding_package_infor += """ order by bidding_package.distance DESC """
        if order_by == '4':
            query_get_bidding_package_infor += """ order by bidding_package.distance ASC """
        if order_by == '5':
            query_get_bidding_package_infor += """ order by bidding_package.price DESC """
        if order_by == '6':
            query_get_bidding_package_infor += """ order by bidding_package.price ASC """

        total_records = """ SELECT
                                   COUNT(*)
                                   FROM (  """
        total_records += query_get_bidding_package_infor
        total_records += """ ) t """

        self.env.cr.execute(total_records, ())
        result_get_total_records = self._cr.fetchall()
        if result_get_total_records[0]:
            if result_get_total_records[0][0]:
                total = result_get_total_records[0][0]
            else:
                total = 0

        if offset is not None and limit is not None:
            if offset > 0:
                offset_check = offset * limit
                query_get_bidding_package_infor += """  OFFSET %s LIMIT %s """ % (offset_check, limit)
                query_has_offset_limit = query_get_bidding_package_infor
                # params.append(offset_check)
                # params.append(limit)
            else:
                query_get_bidding_package_infor += """  OFFSET %s LIMIT %s """ % (offset, limit)
                query_has_offset_limit = query_get_bidding_package_infor
                # params.append(offset)
                # params.append(limit)
        else:
            query_get_bidding_package_infor += """  OFFSET 0 LIMIT 10 """
            query_has_offset_limit = query_get_bidding_package_infor

        self.env.cr.execute(query_get_bidding_package_infor, ())
        jsonRe = []
        result = self._cr.fetchall()
        if result:
            for re in result:
                total_cargos = []
                cargo_info_dtl = []
                query_count_cargo = """ SELECT json_agg(t) FROM ( select count(cargo.id) from sharevan_cargo cargo
                                                join sharevan_bidding_package bidding_package on bidding_package.id = cargo.bidding_package_id 
                                                                                 where bidding_package.id = %s ) t """
                self.env.cr.execute(query_count_cargo, (re[0],))
                result_count_cargo = self._cr.fetchall()
                total_cargos = result_count_cargo[0][0][0]

                query_get_cargo_info = """ SELECT json_agg(t) FROM ( 
                    SELECT sharevan_cargo.id, sharevan_cargo.cargo_number, sharevan_cargo.from_depot_id, sharevan_cargo.to_depot_id, 
                        sharevan_cargo.distance, sharevan_cargo.size_id, sharevan_cargo.weight, sharevan_cargo.description, 
                        sharevan_cargo.price, sharevan_cargo.from_latitude, sharevan_cargo.to_latitude, sharevan_cargo.bidding_package_id, 
                        sharevan_cargo.from_longitude, sharevan_cargo.to_longitude,size_standard,
                        size_standard.length, size_standard.width, size_standard.height, size_standard.type, size_standard.from_weight, 
                        size_standard.to_weight, size_standard.price_id, size_standard.price,
                        size_standard.size_standard_seq, size_standard.long_unit, size_standard.weight_unit
                    FROM public.sharevan_cargo 
                        join sharevan_size_standard  size_standard on size_standard.id = sharevan_cargo.size_id
                        join sharevan_bidding_package_sharevan_cargo_rel rel on rel.sharevan_cargo_id=sharevan_cargo.id
                    where rel.sharevan_bidding_package_id = %s ) t """
                self.env.cr.execute(query_get_cargo_info, (re[0],))
                result_query_get_cargo_info = self._cr.fetchall()
                cargo_ids = []
                if result_query_get_cargo_info[0][0]:
                    for cargo in result_query_get_cargo_info[0][0]:
                        cargo_ids.append(cargo['id'])
                        data = {
                            'id': cargo['id'],
                            'cargo_number': cargo['cargo_number'],
                            'from_depot_id': cargo['from_depot_id'],
                            'to_depot_id': cargo['to_depot_id'],
                            'distance': cargo['distance'],
                            'size_id': cargo['size_id'],
                            'weight': cargo['weight'],
                            'description': cargo['description'],
                            'price': cargo['price'],
                            'from_latitude': cargo['from_latitude'],
                            'to_latitude': cargo['to_latitude'],
                            'bidding_package_id': cargo['bidding_package_id'],
                            'from_longitude': cargo['from_longitude'],
                            'to_longitude': cargo['to_longitude'],
                            'size_standard': {
                                'length': cargo['length'],
                                'width': cargo['width'],
                                'height': cargo['height'],
                                'type': cargo['id'],
                                'from_weight': cargo['from_weight'],
                                'to_weight': cargo['to_weight'],
                                'price_id': cargo['price_id'],
                                'price': cargo['price'],
                                'long_unit': cargo['long_unit'],
                                'weight_unit': cargo['weight_unit']
                            }

                        }
                        cargo_info_dtl.append(data)
                else:
                    cargo_info_dtl = []

                query_get_size_standard = """ SELECT json_agg(t) FROM (  
                    select distinct  id, length, width, height, type, from_weight, to_weight, price_id, price,
                        size_standard_seq, cargo_price_ids, long_unit, weight_unit from sharevan_size_standard size_stand
                    where size_stand.id in (select cargo.size_id from sharevan_cargo cargo where cargo.id  ::integer in ( """

                if cargo_ids:
                    for cargo_id in cargo_ids:
                        query_get_size_standard += str(cargo_id) + ","
                    query_get_size_standard = query_get_size_standard[:-1]
                    query_get_size_standard += "))) t"

                self.env.cr.execute(query_get_size_standard, (cargo_ids))
                result_get_size_standard = self._cr.fetchall()
                size_standard_arr = []
                if result_get_size_standard[0][0]:
                    for rec in result_get_size_standard[0][0]:
                        query_count_cargo_map_with_size_standard = """ SELECT json_agg(t) FROM ( select count(*) from sharevan_cargo cargo where cargo.id  ::integer in ( """
                        for cargo_id in cargo_ids:
                            query_count_cargo_map_with_size_standard += str(cargo_id) + ","
                        query_count_cargo_map_with_size_standard = query_count_cargo_map_with_size_standard[:-1]
                        query_count_cargo_map_with_size_standard += """ ) and cargo.size_id = %s  """
                        query_count_cargo_map_with_size_standard += " ) t"
                        self.env.cr.execute(query_count_cargo_map_with_size_standard, (rec['id'],))
                        result_count_cargo_map_with_size_standard = self._cr.fetchall()

                        query_caculate_cargo_total_weight = """ SELECT json_agg(t) FROM ( select sum(weight) from sharevan_cargo cargo where cargo.id  ::integer in ( """
                        for cargo_id in cargo_ids:
                            query_caculate_cargo_total_weight += str(cargo_id) + ","
                        query_caculate_cargo_total_weight = query_caculate_cargo_total_weight[:-1]
                        query_caculate_cargo_total_weight += """ ) and cargo.size_id = %s  """
                        query_caculate_cargo_total_weight += " ) t"
                        self.env.cr.execute(query_caculate_cargo_total_weight, (rec['id'],))
                        result_query_caculate_cargo_total_weight = self._cr.fetchall()

                        if result_count_cargo_map_with_size_standard[0][0]:
                            size_standard_data = {
                                'id': rec['id'],
                                'length': rec['length'],
                                'width': rec['width'],
                                'height': rec['height'],
                                'type': rec['type'],
                                'from_weight': rec['from_weight'],
                                'to_weight': rec['to_weight'],
                                'price_id': rec['price_id'],
                                'price': rec['price'],
                                'size_standard_seq': rec['size_standard_seq'],
                                'long_unit': rec['long_unit'],
                                'weight_unit': rec['weight_unit'],
                                'cargo_quantity': result_count_cargo_map_with_size_standard[0][0][0]['count'],
                                'total_weight': result_query_caculate_cargo_total_weight[0][0][0]['sum']

                            }
                            size_standard_arr.append(size_standard_data)

                query_get_from_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.latitude,depot.longitude,depot.depot_code,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                        join sharevan_bidding_package bidding_package on depot.id = %s ) t"""
                self.env.cr.execute(query_get_from_depot, (re[8],))
                result_get_from_depot = self._cr.fetchall()

                array_length = len(result_get_from_depot)
                if array_length > 0:
                    if result_get_from_depot[0][0]:
                        get_from_depot = result_get_from_depot[0][0][0]

                query_get_to_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.latitude,depot.longitude,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                                               join sharevan_bidding_package bidding_package on depot.id = %s ) t"""
                self.env.cr.execute(query_get_to_depot, (re[9],))
                result_get_to_depot = self._cr.fetchall()
                get_to_depot = []
                array_length = len(result_get_to_depot)
                if array_length > 0:
                    if result_get_to_depot[0][0]:
                        get_to_depot = result_get_to_depot[0][0][0]

                content = {
                    'id': re[0],
                    'bidding_order_id': re[1],
                    'bidding_package_number': re[2],
                    'status': re[3],
                    'confirm_time': re[4],
                    'release_time': re[5],
                    'bidding_time': re[6],
                    'max_count': re[7],
                    'from_depot': get_from_depot,
                    'to_depot': result_get_to_depot[0][0][0],
                    'total_weight': re[10],
                    'distance': re[11],
                    'from_latitude': re[12],
                    'from_longitude': re[13],
                    'to_latitude': re[14],
                    'to_longitude': re[15],
                    'from_receive_time': re[16],
                    'to_receive_time': re[17],
                    'from_return_time': re[18],
                    'to_return_time': re[19],
                    'price_origin': re[20],
                    'price': re[21],
                    'create_date': re[22],
                    'countdown_time': re[23],
                    'price_time_change': re[24],
                    'price_level_change': re[25],
                    'total_cargos': total_cargos['count'],
                    'max_confirm_time': re[26],
                    'cargo_types': size_standard_arr

                }
                jsonRe.append(content)
            records = {
                'length': len(result),
                'total': total,
                'records': jsonRe
            }
            simplejson.dumps(records, indent=4, sort_keys=True, default=str)
            return records

        return {
            'records': []
        }

    def get_bidding_package_information_v2(self, bidding_time, search_code, order_by, offset, limit):
        params = []
        offset_check = 0
        limit_check = 10
        hour = bidding_time.split(" ")[1][0:2]  # get hours
        search_code = search_code.lower()

        query_get_bidding_package_infor = """ SELECT distinct  bidding_package.id, bidding_package.bidding_order_id, bidding_package.bidding_package_number, bidding_package.status, bidding_package.confirm_time, bidding_package.release_time, bidding_package.bidding_time, bidding_package.max_count,
                                                    bidding_package.from_depot_id, bidding_package.to_depot_id, bidding_package.total_weight, 
                                                    bidding_package.distance, bidding_package.from_latitude, bidding_package.from_longitude, bidding_package.to_latitude, bidding_package.to_longitude, bidding_package.from_receive_time, bidding_package.to_receive_time,
                                                    bidding_package.from_return_time, bidding_package.to_return_time, bidding_package.price_origin, bidding_package.price, bidding_package.create_date, 
                                                    bidding_package.countdown_time, bidding_package.price_time_change, bidding_package.price_level_change , bidding_package.max_confirm_time
       	                                         FROM public.sharevan_bidding_package bidding_package 
       	                                         left join sharevan_depot sd on sd.id =  bidding_package.from_depot_id or bidding_package.to_depot_id = sd.id 
       	                                         where 1=1 """
        if search_code:
            query_get_bidding_package_infor += """ and LOWER(bidding_package.bidding_package_number)like LOWER('%s%%') or LOWER(sd.address)like LOWER('%s%%') """ % (
                search_code, search_code,)

        query_get_bidding_package_infor += """ and bidding_package.status ='%s'""" % (
            BiddingPackageStatus.NotBidding.value) + """
                                                        and ( CAST(bidding_package.bidding_time  AS VARCHAR) like '% """ + """%s""" % (
                                               hour) + """:%'"""

        for i in range(int(hour)):
            if i < 10:
                hour_str = '0' + str(i)
            else:
                hour_str = str(i)
            query_get_bidding_package_infor += """ or CAST(bidding_package.bidding_time  AS VARCHAR) like '% """ + """%s""" % (
                hour_str) + """:%'"""
        query_get_bidding_package_infor += """ ) """

        print(query_get_bidding_package_infor)

        # Order by = 0 : không order by
        # Order by = 1: create_date ASC
        # Order by = 2 : create order by DESC
        # Order by = 3: distance ASC
        # Order by = 4 : distance order by DESC
        # Order by = 5: price ASC
        # Order by = 6 : create order by DESC

        if order_by == '1':
            query_get_bidding_package_infor += """ order by  bidding_package.create_date DESC """
        if order_by == '2':
            query_get_bidding_package_infor += """ order by  bidding_package.create_date DESC """
        if order_by == '3':
            query_get_bidding_package_infor += """ order by bidding_package.distance DESC """
        if order_by == '4':
            query_get_bidding_package_infor += """ order by bidding_package.distance ASC """
        if order_by == '5':
            query_get_bidding_package_infor += """ order by bidding_package.price DESC """
        if order_by == '6':
            query_get_bidding_package_infor += """ order by bidding_package.price ASC """

        total_records = """ SELECT
                                      COUNT(*)
                                      FROM (  """
        total_records += query_get_bidding_package_infor
        total_records += """ ) t """
        self.env.cr.execute(total_records, ())
        result_get_total_records = self._cr.fetchall()
        if result_get_total_records[0]:
            if result_get_total_records[0][0]:
                total = result_get_total_records[0][0]
            else:
                total = 0

        if offset is not None and limit is not None:
            if offset > 0:
                offset_check = offset * limit
                query_get_bidding_package_infor += """  OFFSET %s LIMIT %s """ % (offset_check, limit)
                query_has_offset_limit = query_get_bidding_package_infor
                # params.append(offset_check)
                # params.append(limit)
            else:
                query_get_bidding_package_infor += """  OFFSET %s LIMIT %s """ % (offset, limit)
                query_has_offset_limit = query_get_bidding_package_infor
                # params.append(offset)
                # params.append(limit)
        else:
            query_get_bidding_package_infor += """  OFFSET 0 LIMIT 10 """
            query_has_offset_limit = query_get_bidding_package_infor

        self.env.cr.execute(query_get_bidding_package_infor, ())
        jsonRe = []
        result = self._cr.fetchall()
        if result:
            for re in result:
                total_cargos = []
                query_count_cargo = """ SELECT json_agg(t) FROM ( select count(cargo.id) from sharevan_cargo cargo
                                                            join sharevan_bidding_package bidding_package on bidding_package.id = cargo.bidding_package_id 
                                                            where bidding_package.id = %s ) t """
                self.env.cr.execute(query_count_cargo, (re[0],))
                result_count_cargo = self._cr.fetchall()
                total_cargos = result_count_cargo[0][0][0]

                query_get_from_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.latitude,depot.longitude,depot.depot_code,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                           join sharevan_bidding_package bidding_package on depot.id = %s ) t"""
                self.env.cr.execute(query_get_from_depot, (re[8],))
                result_get_from_depot = self._cr.fetchall()

                array_length = len(result_get_from_depot)
                if array_length > 0:
                    if result_get_from_depot[0][0]:
                        get_from_depot = result_get_from_depot[0][0][0]

                query_get_to_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.latitude,depot.longitude,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                                                  join sharevan_bidding_package bidding_package on depot.id = %s ) t"""
                self.env.cr.execute(query_get_to_depot, (re[9],))
                result_get_to_depot = self._cr.fetchall()
                get_to_depot = []
                array_length = len(result_get_to_depot)
                if array_length > 0:
                    if result_get_to_depot[0][0]:
                        get_to_depot = result_get_to_depot[0][0][0]

                content = {
                    'id': re[0],
                    'bidding_order_id': re[1],
                    'bidding_package_number': re[2],
                    'status': re[3],
                    'confirm_time': re[4],
                    'release_time': re[5],
                    'bidding_time': re[6],
                    'max_count': re[7],
                    'from_depot': get_from_depot,
                    'to_depot': result_get_to_depot[0][0][0],
                    'total_weight': re[10],
                    'distance': re[11],
                    'from_latitude': re[12],
                    'from_longitude': re[13],
                    'to_latitude': re[14],
                    'to_longitude': re[15],
                    'from_receive_time': re[16],
                    'to_receive_time': re[17],
                    'from_return_time': re[18],
                    'to_return_time': re[19],
                    'price_origin': re[20],
                    'price': re[21],
                    'create_date': re[22],
                    'countdown_time': re[23],
                    'price_time_change': re[24],
                    'price_level_change': re[25],
                    'total_cargos': total_cargos['count'],
                    'max_confirm_time': re[26]

                }
                jsonRe.append(content)
            records = {
                'length': len(result),
                'total': total,
                'records': jsonRe
            }
            simplejson.dumps(records, indent=4, sort_keys=True, default=str)
            return records

        return {
            'records': []
        }

    def get_bidding_package_detail(self, bidding_package_id):
        user = self.env['res.users'].search([('id', '=', self.env.uid)])
        params = []
        if bidding_package_id is not None:
            query_get_bidding_package_infor = """ SELECT id, bidding_order_id, bidding_package_number, status, TO_CHAR(confirm_time,'YYYY-MM-DD HH24:MI:SS') confirm_time , TO_CHAR(release_time,'YYYY-MM-DD HH24:MI:SS') release_time, TO_CHAR(bidding_time,'YYYY-MM-DD HH24:MI:SS') bidding_time, max_count,
                                                         from_depot_id, to_depot_id, total_weight,
                                                         distance, from_latitude, from_longitude, to_latitude, to_longitude, TO_CHAR(from_receive_time,'YYYY-MM-DD HH24:MI:SS') from_receive_time, TO_CHAR(to_receive_time,'YYYY-MM-DD HH24:MI:SS') to_receive_time,
                                                         TO_CHAR(from_return_time,'YYYY-MM-DD HH24:MI:SS') from_return_time,  TO_CHAR(to_return_time,'YYYY-MM-DD HH24:MI:SS') to_return_time, price_origin, price,  TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS') create_date,
                                                         countdown_time,  price_time_change, price_level_change
                                                         FROM public.sharevan_bidding_package bidding_package where 1=1 
                                                         and bidding_package.id = %s """
            params.append(bidding_package_id)
            self.env.cr.execute(query_get_bidding_package_infor, params)
            jsonRe = []
            result = self._cr.fetchall()
            if result:
                for re in result:
                    total_cargos = []
                    cargo_info_dtl = []
                    query_count_cargo = """ SELECT json_agg(t) FROM ( select count(cargo.id) from sharevan_cargo cargo
                                                                 join sharevan_bidding_package bidding_package on bidding_package.id = cargo.bidding_package_id 
                                                                 where bidding_package.id = %s ) t """
                    self.env.cr.execute(query_count_cargo, (re[0],))
                    result_count_cargo = self._cr.fetchall()
                    total_cargos = result_count_cargo[0][0][0]

                    query_get_cargo_info = """ SELECT json_agg(t) FROM (
                        SELECT sharevan_cargo.id, sharevan_cargo.cargo_number, sharevan_cargo.from_depot_id, 
                            sharevan_cargo.to_depot_id, sharevan_cargo.distance, sharevan_cargo.size_id, 
                            sharevan_cargo.weight, sharevan_cargo.description, sharevan_cargo.price, 
                            sharevan_cargo.from_latitude, sharevan_cargo.to_latitude, sharevan_cargo.bidding_package_id, 
                            sharevan_cargo.from_longitude, sharevan_cargo.to_longitude,size_standard,
                            size_standard.length, size_standard.width, size_standard.height
                            , size_standard.type, size_standard.from_weight, size_standard.to_weight, size_standard.price_id, size_standard.price,
                            size_standard.size_standard_seq, size_standard.long_unit, size_standard.weight_unit
                            FROM public.sharevan_cargo 
                            join sharevan_size_standard  size_standard on size_standard.id = sharevan_cargo.size_id
                            join sharevan_bidding_package_sharevan_cargo_rel rel on rel.sharevan_cargo_id=sharevan_cargo.id
                            where rel.sharevan_bidding_package_id = %s
                                                                               ) t """
                    self.env.cr.execute(query_get_cargo_info, (re[0],))
                    result_query_get_cargo_info = self._cr.fetchall()
                    cargo_ids = []
                    if result_query_get_cargo_info[0][0]:
                        for cargo in result_query_get_cargo_info[0][0]:
                            cargo_ids.append(cargo['id'])
                            data = {
                                'id': cargo['id'],
                                'cargo_number': cargo['cargo_number'],
                                'from_depot_id': cargo['from_depot_id'],
                                'to_depot_id': cargo['to_depot_id'],
                                'distance': cargo['distance'],
                                'size_id': cargo['size_id'],
                                'weight': cargo['weight'],
                                'description': cargo['description'],
                                'price': cargo['price'],
                                'from_latitude': cargo['from_latitude'],
                                'to_latitude': cargo['to_latitude'],
                                'bidding_package_id': cargo['bidding_package_id'],
                                'from_longitude': cargo['from_longitude'],
                                'to_longitude': cargo['to_longitude'],
                                'size_standard': {
                                    'length': cargo['length'],
                                    'width': cargo['width'],
                                    'height': cargo['height'],
                                    'type': cargo['id'],
                                    'from_weight': cargo['from_weight'],
                                    'to_weight': cargo['to_weight'],
                                    'price_id': cargo['price_id'],
                                    'price': cargo['price'],
                                    'long_unit': cargo['long_unit'],
                                    'weight_unit': cargo['weight_unit']
                                }

                            }
                            cargo_info_dtl.append(data)
                    else:
                        cargo_info_dtl = []

                    query_get_size_standard = """ 
                        SELECT json_agg(t) FROM (  
                            select distinct  id, length, width, height, type,
                                from_weight, to_weight, price_id, price, size_standard_seq, cargo_price_ids, 
                                long_unit, weight_unit from sharevan_size_standard size_stand
                            where size_stand.id in (select cargo.size_id from sharevan_cargo cargo where cargo.id  ::integer in ( """

                    if cargo_ids:
                        for cargo_id in cargo_ids:
                            query_get_size_standard += str(cargo_id) + ","
                        query_get_size_standard = query_get_size_standard[:-1]
                        query_get_size_standard += "))) t"

                    self.env.cr.execute(query_get_size_standard, (cargo_ids))
                    result_get_size_standard = self._cr.fetchall()
                    size_standard_arr = []
                    if result_get_size_standard[0][0]:
                        for rec in result_get_size_standard[0][0]:
                            query_count_cargo_map_with_size_standard = """ SELECT json_agg(t) FROM ( select count(*) from sharevan_cargo cargo where cargo.id  ::integer in ( """
                            for cargo_id in cargo_ids:
                                query_count_cargo_map_with_size_standard += str(cargo_id) + ","
                            query_count_cargo_map_with_size_standard = query_count_cargo_map_with_size_standard[:-1]
                            query_count_cargo_map_with_size_standard += """ ) and cargo.size_id = %s  """
                            query_count_cargo_map_with_size_standard += " ) t"
                            self.env.cr.execute(query_count_cargo_map_with_size_standard, (rec['id'],))
                            result_count_cargo_map_with_size_standard = self._cr.fetchall()

                            query_caculate_cargo_total_weight = """ SELECT json_agg(t) FROM ( select sum(weight) from sharevan_cargo cargo where cargo.id  ::integer in ( """
                            for cargo_id in cargo_ids:
                                query_caculate_cargo_total_weight += str(cargo_id) + ","
                            query_caculate_cargo_total_weight = query_caculate_cargo_total_weight[:-1]
                            query_caculate_cargo_total_weight += """ ) and cargo.size_id = %s  """
                            query_caculate_cargo_total_weight += " ) t"
                            self.env.cr.execute(query_caculate_cargo_total_weight, (rec['id'],))
                            result_query_caculate_cargo_total_weight = self._cr.fetchall()

                            if result_count_cargo_map_with_size_standard[0][0]:
                                size_standard_data = {
                                    'id': rec['id'],
                                    'length': rec['length'],
                                    'width': rec['width'],
                                    'height': rec['height'],
                                    'type': rec['type'],
                                    'from_weight': rec['from_weight'],
                                    'to_weight': rec['to_weight'],
                                    'price_id': rec['price_id'],
                                    'price': rec['price'],
                                    'size_standard_seq': rec['size_standard_seq'],
                                    'long_unit': rec['long_unit'],
                                    'weight_unit': rec['weight_unit'],
                                    'cargo_quantity': result_count_cargo_map_with_size_standard[0][0][0]['count'],
                                    'total_weight': result_query_caculate_cargo_total_weight[0][0][0]['sum']

                                }
                                size_standard_arr.append(size_standard_data)

                    query_get_from_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.latitude,depot.longitude,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                                join sharevan_bidding_package bidding_package on depot.id = %s ) t"""
                    self.env.cr.execute(query_get_from_depot, (re[8],))
                    result_get_from_depot = self._cr.fetchall()

                    array_length = len(result_get_from_depot)
                    if array_length > 0:
                        if result_get_from_depot[0][0]:
                            get_from_depot = result_get_from_depot[0][0][0]

                    query_get_to_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.latitude,depot.longitude,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                                                       join sharevan_bidding_package bidding_package on depot.id = %s ) t"""
                    self.env.cr.execute(query_get_to_depot, (re[9],))
                    result_get_to_depot = self._cr.fetchall()
                    get_to_depot = []
                    array_length = len(result_get_to_depot)
                    if array_length > 0:
                        if result_get_to_depot[0][0]:
                            get_to_depot = result_get_to_depot[0][0][0]

                    # record_bidding_order = http.request.env[BiddingOrder._name]. \
                    #     web_search_read([['bidding_package_id', '=', bidding_package_id]], fields=None,
                    #                     offset=0, limit=10, order='')
                    #
                    # if record_bidding_order['records']:
                    #     bidding_order_id = record_bidding_order['records'][0]['id']
                    #     record_bidding_order_vehicle = http.request.env[BiddingOrderVehicle._name]. \
                    #         web_search_read([['bidding_order_id', '=', bidding_order_id]], fields=None,
                    #                         offset=0, limit=10, order='')
                    query_get_bidding_vehicle = """ SELECT json_agg(t) FROM (  SELECT id, code, res_user_id,status, lisence_plate, driver_phone_number, driver_name, TO_CHAR(expiry_time,'YYYY-MM-DD HH24:MI:SS') expiry_time,
                                                                                                        company_id, status, description, TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS') create_date, TO_CHAR(write_date,'YYYY-MM-DD HH24:MI:SS') write_date, id_card,
                                                                                                        res_partner_id, tonnage, vehicle_type, weight_unit, bidding_vehicle_seq
                                                                                                       FROM public.sharevan_bidding_vehicle  bidding_vehicle
                                                                                                        where bidding_vehicle.company_id = %s ) t"""
                    self.env.cr.execute(query_get_bidding_vehicle, (user.company_id.id,))
                    result_get_bidding_vehicle = self._cr.fetchall()
                    bidding_vehicle_arr = []
                    if result_get_bidding_vehicle[0][0]:
                        for bidding_vehicle in result_get_bidding_vehicle[0][0]:
                            query_get_action_log = """ SELECT json_agg(t) FROM ( select ac.van_id, ac.latitude, ac.longitude from action_log ac
                                                                                    where ac.van_id =  %s order by id limit 1 ) t"""
                            self.env.cr.execute(query_get_action_log, (bidding_vehicle['id'],))
                            result_get_action_log = self._cr.fetchall()

                            bidding_vehicle_data = {
                                'id': bidding_vehicle['id'],
                                'code': bidding_vehicle['code'],
                                'res_user_id': bidding_vehicle['res_user_id'],
                                'status': bidding_vehicle['status'],
                                'lisence_plate': bidding_vehicle['lisence_plate'],
                                'driver_phone_number': bidding_vehicle['driver_phone_number'],
                                'driver_name': bidding_vehicle['driver_name'],
                                'expiry_time': bidding_vehicle['expiry_time'],
                                'company_id': bidding_vehicle['company_id'],
                                'status': bidding_vehicle['status'],
                                'create_date': bidding_vehicle['create_date'],
                                'write_date': bidding_vehicle['write_date'],
                                'id_card': bidding_vehicle['id_card'],
                                'res_partner_id': bidding_vehicle['res_partner_id'],
                                'tonnage': bidding_vehicle['tonnage'],
                                'weight_unit': bidding_vehicle['weight_unit'],
                                'bidding_vehicle_seq': bidding_vehicle['bidding_vehicle_seq'],
                                'action_log': result_get_action_log[0][0]
                            }
                            bidding_vehicle_arr.append(bidding_vehicle_data)
                    content = {
                        'id': re[0],
                        'bidding_order_id': re[1],
                        'bidding_package_number': re[2],
                        'status': re[3],
                        'confirm_time': re[4],
                        'release_time': re[5],
                        'bidding_time': re[6],
                        'max_count': re[7],
                        'from_depot': get_from_depot,
                        'to_depot': get_to_depot,
                        'total_weight': re[10],
                        'distance': re[11],
                        'from_latitude': re[12],
                        'from_longitude': re[13],
                        'to_latitude': re[14],
                        'to_longitude': re[15],
                        'from_receive_time': re[16],
                        'to_receive_time': re[17],
                        'from_return_time': re[18],
                        'to_return_time': re[19],
                        'price_origin': re[20],
                        'price': re[21],
                        'create_date': re[22],
                        'countdown_time': re[23],
                        'price_time_change': re[24],
                        'price_level_change': re[25],
                        'total_cargo': total_cargos['count'],
                        'cargos': cargo_info_dtl,
                        'bidding_vehicles': bidding_vehicle_arr,
                        'cargo_types': size_standard_arr

                    }
                    jsonRe.append(content)
                records = {
                    'length': len(result),
                    'records': jsonRe
                }
                simplejson.dumps(records, indent=4, sort_keys=True, default=str)
                return records

            else:
                raise ValidationError(_('Bidding Package does not existed!'))
        else:
            raise ValidationError(_('bidding_package_id can not null!'))

    def create_cargo_data_for_test(self):
        for rec in range(100):
            for size_id in range(7):
                cargo = {
                    'cargo_number': 'New',
                    'code': 'HN_BG',
                    'from_depot_id': '2',
                    'to_depot_id': '4',
                    'code': 'ABCD123123',
                    'size_id': size_id + 1,
                    'distance': 123,
                    'weight': 123.123,
                    'from_latitude': '21.01990',
                    'to_latitude': '21.36210',
                    'from_longitude': '105.74386',
                    'to_longitude': '106.05755',
                    'pack_plant_day': '2020-08-31 09:00:00',
                    'status': '1'
                }

                result_cargo = self.env[Constants.SHAREVAN_CARGO].sudo().create(cargo)

    def create_bidding_package_for_test(self):

        start_id = 7000
        bidding_time = '2020-09-17 02:10:46'
        for rec in range(100, 200):
            cargo_id = []
            for re in range(5):
                cargo_id.append(start_id)
                start_id += 1
            if rec == 20:
                bidding_time = '2020-09-04 02:10:46'
            elif rec >= 40 and rec <= 50:
                bidding_time = '2020-09-05 03:10:46'
            elif rec >= 51 and rec <= 60:
                bidding_time = '2020-09-05 04:10:46'
            elif rec >= 61 and rec <= 70:
                bidding_time = '2020-09-05 05:10:46'
            elif rec >= 71 and rec <= 80:
                bidding_time = '2020-09-05 06:10:46'
            elif rec >= 81 and rec <= 90:
                bidding_time = '2020-09-05 07:10:46'
            elif rec >= 91 and rec <= 100:
                bidding_time = '2020-09-05 08:10:46'
            elif rec >= 101 and rec <= 110:
                bidding_time = '2020-09-05 09:10:46'
            elif rec >= 111 and rec <= 120:
                bidding_time = '2020-09-05 10:10:46'
            elif rec >= 121 and rec <= 130:
                bidding_time = '2020-09-05 11:10:46'
            elif rec >= 131 and rec <= 140:
                bidding_time = '2020-09-05 12:10:46'
            elif rec >= 141 and rec <= 150:
                bidding_time = '2020-09-05 13:10:46'
            elif rec >= 151 and rec <= 160:
                bidding_time = '2020-09-05 14:10:46'
            elif rec >= 161 and rec <= 170:
                bidding_time = '2020-09-05 15:10:46'
            elif rec >= 171 and rec <= 180:
                bidding_time = '2020-09-05 16:10:46'
            elif rec >= 181 and rec <= 190:
                bidding_time = '2020-09-05 17:10:46'
            elif rec >= 191 and rec <= 200:
                bidding_time = '2020-09-05 18:10:46'
            elif rec >= 201 and rec <= 210:
                bidding_time = '2020-09-05 19:10:46'
            elif rec >= 211 and rec <= 220:
                bidding_time = '2020-09-05 20:10:46'
            elif rec >= 221 and rec <= 230:
                bidding_time = '2020-09-05 21:10:46'
            elif rec >= 231 and rec <= 240:
                bidding_time = '2020-09-05 22:10:46'
            elif rec >= 241 and rec <= 250:
                bidding_time = '2020-09-05 23:10:46'
            elif rec >= 251 and rec <= 260:
                bidding_time = '2020-09-05 01:10:46'
            else:
                bidding_time = '2020-09-04 02:10:46'

            val = {
                'release_time': '2020-09-03 02:10:46',
                'bidding_time': bidding_time,
                'countdown_time': 123123,
                'max_count': 123123,
                'from_depot_id': 2,
                'to_depot_id': 4,
                'distance': 123123,
                'from_latitude': 21.014110000000002,
                'from_longitude': 105.78091,
                'to_latitude': 20.931880000000003,
                'to_longitude': 106.05756000000001,
                'from_receive_time': '2020-09-03 02:10:46',
                'to_receive_time': '2020-09-03 02:10:46',
                'from_return_time': '2020-09-03 02:10:46',
                'to_return_time': '2020-09-03 02:10:46',
                'price_time_change': 123123,
                'price_level_change': 123123,
                'max_confirm_time': '2020-09-03 02:10:46',
                'cargo_ids': cargo_id,
                'bidding_package_number': 'New'

            }
            result_bidding_package = self.env[Constants.SHAREVAN_BIDDING_PACKAGE].sudo().create(val)

            for cargo_id in cargo_id:
                http.request.env[Cargo._name]. \
                    browse(cargo_id).write(
                    {'bidding_package_id': result_bidding_package['id']})

    def get_bidding_package_information_test(self, searchInfo, offset, limit):
        print(searchInfo)
        params = []
        offset_check = 0
        limit_check = 10
        textSearch = searchInfo['text_search']
        fromCost = searchInfo['from_cost']
        toCost = searchInfo['to_cost']
        fromDate = searchInfo['from_date']
        toDate = searchInfo['to_date']
        fromDistance = searchInfo['from_distance']
        toDistance = searchInfo['to_distance']
        fromWeight = searchInfo['from_weight']
        toWeight = searchInfo['to_weight']
        query = """ SELECT distinct  bidding_package.id, bidding_package.bidding_order_id, bidding_package.bidding_package_number, bidding_package.status, bidding_package.confirm_time, bidding_package.is_publish, bidding_package.publish_time, bidding_package.duration_time,
                                                    bidding_package.from_depot_id, bidding_package.to_depot_id, bidding_package.total_weight, 
                                                    bidding_package.distance, bidding_package.from_latitude, bidding_package.from_longitude, bidding_package.to_latitude, bidding_package.to_longitude, bidding_package.from_receive_time, bidding_package.to_receive_time,
                                                    bidding_package.from_return_time, bidding_package.to_return_time, bidding_package.price_origin, bidding_package.price, bidding_package.create_date, 
                                                    bidding_package.countdown_time, bidding_package.is_real, bidding_package.max_confirm_time, bidding_package.limit_publish_time, from_depot.address from_address, to_depot.address to_address
       	                                         FROM public.sharevan_bidding_package bidding_package 
       	                                         left join sharevan_depot from_depot on from_depot.id =  bidding_package.from_depot_id 
												 left join sharevan_depot to_depot on bidding_package.to_depot_id = to_depot.id 
       	                                         where  bidding_package.is_publish = %s and bidding_package.status = %s and  bidding_package.limit_publish_time <= now() at time zone 'UTC' """ % (
            True, BiddingPackageStatus.NotBidding.value,)

        if textSearch:
            textSearch = textSearch.lower()
            query += """ and (lower(bidding_package.bidding_package_number) like '%%s%' or lower(from_depot.address) like '%%s%' or lower(to_depot.address) like '%%s%') """ % (
                textSearch, textSearch,)
        if fromCost:
            query += """ and bidding_package.price >= %s  """ % (fromCost,)
        if toCost:
            query += """ and bidding_package.price <= %s """ % (toCost,)
        if fromDate:
            query += """ and bidding_package.from_receive_time >= to_date(%s,'dd/mm/yyyy') and bidding_package.to_receive_time >= to_date(%s,'dd/mm/yyyy') """ % (
                fromDate, fromDate,)
        if toDate:
            query += """ and bidding_package.from_return_time >= to_date(%s,'dd/mm/yyyy') and bidding_package.to_return_time >= to_date(%s,'dd/mm/yyyy') """ % (
                toDate, toDate,)
        if fromDistance:
            query += """ and bidding_package.distance >= %s """ % (fromDistance,)
        if toDistance:
            query += """ and bidding_package.distance <= %s """ % (toDistance,)
        if fromWeight:
            query += """ and bidding_package.total_weight >= %s """ % (fromWeight,)
        if toWeight:
            query += """ and bidding_package.total_weight <= %s""" % (toWeight,)

        total_record_query = """ select count(1) from (""" + query + """)t"""
        self.env.cr.execute(total_record_query, ())
        total_record = self._cr.fetchall()
        print(total_record)
        return {
            'records': []
        }
