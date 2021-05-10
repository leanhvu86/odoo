# -*- coding: utf-8 -*-

import json as simplejson
import logging
from datetime import datetime

import pytz

from mymodule.base_next.models.bidding_vehicle import BiddingVehicle
from mymodule.base_next.models.cargo import Cargo
from mymodule.base_next.models.depot_goods import DepotGoods
from mymodule.base_next.models.routing_plan_day import RoutingPlanDay
from mymodule.base_next.models.size_standard import SizeStandard
from mymodule.constants import Constants
from mymodule.enum.BiddingStatus import BiddingStatus
from mymodule.enum.BiddingStatusType import BiddingStatusType
from mymodule.enum.CargoBiddingOrderVehicleStatus import CargoBiddingOrderVehicleStatus
from mymodule.enum.CargoStatus import CargoStatus
from mymodule.enum.ClickActionType import ClickActionType
from mymodule.enum.FleetSystemType import FleetSystemType
from mymodule.enum.MessageType import MessageType
from mymodule.enum.NotificationType import NotificationType
from mymodule.enum.VehicleConfirmStatus import VehicleConfirmStatus
from mymodule.enum.VehicleStateStatus import VehicleStateStatus
from mymodule.enum.VehicleStatusAvailable import ProductType
from odoo import models, _, http
from odoo.exceptions import ValidationError
from odoo.tools import config

logger = logging.getLogger(__name__)


class BiddingOrder(models.Model):
    _name = 'sharevan.bidding.order'
    _description = 'Bidding order'
    _inherit = 'sharevan.bidding.order'

    def get_bidding_detail(self, **kwargs):
        param_id = 0
        param_name = ''
        type = 0
        param_type = None
        for arg in kwargs:
            if arg == 'bidding_order_id':
                query = """ sharevan_bidding_order.id  = %s   """
                param_id = kwargs.get(arg)
                check_cargo_id = self.env['sharevan.bidding.order'].search([('id', '=', param_id)])
                if len(check_cargo_id) == 0:
                    raise ValidationError("Not info id bidding order")
            elif arg == 'cargo_id':
                query = """ sharevan_cargo.id = %s   """
                param_id = kwargs.get(arg)
                check_biding_order_id = self.env['sharevan.cargo'].search([('id', '=', param_id)])
                if len(check_biding_order_id) == 0:
                    raise ValidationError("Not info id cargo")
            elif arg == 'status':
                status = kwargs.get(arg)
                if status == 2:
                    param_status = 2
            elif arg == 'type':
                type = kwargs.get(arg)
                if type == 0:
                    param_type = 0
                    context = self._context
                    current_uid = context.get('uid')

                    partnert = self.env['res.partner'].search([('user_id', '=', current_uid)])

                    query_driver = """ SELECT json_agg(t)
                                                                       FROM (
                                                                           SELECT bidding_vehicle.id,bidding_vehicle.driver_name,bidding_vehicle.driver_phone_number,bidding_vehicle.lisence_plate,bidding_vehicle.id_card as idCard
                                                                           FROM sharevan_bidding_vehicle bidding_vehicle
                                                                           where company_id = %s and status = 'running'
                                                                           ) t  """
                    self.env.cr.execute(query_driver, (partnert['company_id'].id,))

                    result1 = self._cr.fetchall()
                    list_driver = result1[0][0]

        query_bidding = """
        						select  sharevan_bidding_order.id , sharevan_bidding_vehicle.driver_name,
                                sharevan_bidding_vehicle.driver_phone_number,sharevan_bidding_vehicle.lisence_plate,
                                TO_CHAR(sharevan_bidding_order.create_date,'YYYY-MM-DD HH24:MI:SS') create_date_bidding 
                                ,sharevan_cargo_price.price,sharevan_cargo.weight,sharevan_cargo.quantity ,sharevan_cargo.distance,
                                sharevan_depot.name as name_from_depot,sharevan_depot.latitude as from_latitude,
                                sharevan_depot.longitude as from_longitude,TO_CHAR(sharevan_cargo.from_receive_time,'YYYY-MM-DD HH24:MI:SS') from_receive_time,
                                 depot2.name as name_to_depot ,depot2.latitude as to_latitude,depot2.longitude as to_longitude,TO_CHAR(sharevan_cargo.to_receive_time,'YYYY-MM-DD HH24:MI:SS') to_receive_time,
                                sharevan_size_standard.length,sharevan_size_standard.width,sharevan_size_standard.height,
                                sharevan_size_standard.long_unit,sharevan_size_standard.weight_unit,sharevan_cargo.status,
                                sharevan_bidding_order.status as status_bid ,sharevan_bidding_order.type,sharevan_bidding_vehicle.id_card,
                                sharevan_cargo.id as id_cargo,sharevan_bidding_vehicle.id as bidding_vehicle_id,
                                sharevan_bidding_order_return.actual_time
                                    FROM public.sharevan_cargo 
                                    LEFT JOIN public.sharevan_cargo_price  on  sharevan_cargo_price.id = sharevan_cargo.price_id
                                    LEFT JOIN public.sharevan_bidding_order  on  sharevan_cargo.bidding_order_id = sharevan_bidding_order.id
                                    LEFT JOIN public.sharevan_bidding_order_return  on  sharevan_bidding_order_return.id = sharevan_bidding_order.bidding_order_return_id
                                    LEFT JOIN public.sharevan_depot  on  sharevan_depot.id = sharevan_cargo.from_depot_id 
                                    LEFT JOIN public.sharevan_depot as depot2 on  depot2.id = sharevan_cargo.to_depot_id
                                    LEFT JOIN public.sharevan_size_standard  on  sharevan_size_standard.id = sharevan_cargo.size_id
                                    LEFT JOIN public.sharevan_product_type  on  sharevan_product_type.id = sharevan_cargo.product_type_id
                                    LEFT JOIN public.sharevan_bidding_vehicle  on  sharevan_bidding_vehicle.id = sharevan_bidding_order.bidding_vehicle_id

                                    WHERE 
                          				 """
        query_bidding += query

        self.env.cr.execute(query_bidding % (param_id), ())

        result = self._cr.fetchall()
        info_driver = {}
        if result:
            re = result[0]
            status = ''
            id = 0

            if param_name == 'cargo':
                status = re[22]
                id = re[26]
            else:
                status = re[23]

                id = re[0]

            content = {
                'id': id,
                'create_date_bidding': re[4],
                'driver_info': {
                    'id': re[27],
                    'driver_name': re[1],
                    'driver_phone_number': re[2],
                    'lisence_plate': re[3],
                    'idCard': re[25]
                },
                'price': re[5],
                'total_weight': re[6],
                'quantity': re[7],
                'distance': re[8],
                'from_depot': {
                    'name_from_depot': re[9],
                    'from_latitude': re[10],
                    'from_longitude': re[11],
                    'from_receive_time': re[12],
                },
                'to_depot': {
                    'name_to_depot': re[13],
                    'to_latitude': re[14],
                    'to_longitude': re[15],
                    'to_receive_time': re[16],
                },
                'size_cargo': {
                    'length': re[17],
                    'width': re[18],
                    'height': re[19],
                    'long_unit': re[20],
                    'weight_unit': re[21]
                },
                'actual_time': re[28],
                'status': status,
                'type': re[24]

            }
            if param_type == 0:
                content.update({'list_driver': list_driver})
            records = {
                'length': len(result),
                'records': [content]
            }
            simplejson.dumps(records, indent=4, sort_keys=True, default=str)
            return records

        return {
            'records': []
        }

    def bidding_approve(self, bidding_id):
        if bidding_id:
            record = http.request.env[BiddingOrder._name]. \
                web_search_read([['id', '=', bidding_id]], fields=None,
                                offset=0, limit=10, order='')

            if record['records']:
                bidding_status = record['records'][0]['status']
                bidding_type = record['records'][0]['type']
                if bidding_type != BiddingStatusType.Approved.value:
                    http.request.env[BiddingOrder._name]. \
                        browse(record['records'][0]['id']).write(
                        {'type': BiddingStatusType.Approved.value,
                         'status': BiddingStatus.NotConfirm.value})
                else:
                    raise ValidationError(_('Bidding has been approved'))
            else:
                raise ValidationError(_('Bidding id can not null!'))

            record_cargo = http.request.env[Cargo._name]. \
                web_search_read([['id', '=', record['records'][0]['cargo_id'][0]]], fields=None,
                                offset=0, limit=10, order='')

            record_size_standard = http.request.env[SizeStandard._name]. \
                web_search_read([['id', '=', record_cargo['records'][0]['size_id'][0]]], fields=None,
                                offset=0, limit=10, order='')

            cargo_id = record['records'][0]['cargo_id'][0]
            if record_cargo['records']:
                records = self.env['sharevan.cargo'].search([('id', '=', cargo_id)])
                records.write({
                    'status': CargoStatus.Confirmed.value
                })

            else:
                raise ValidationError(_('Bidding order must have Cargo!'))
            print(record['records'][0]['cargo_id'])
            biddingOrderReceive = {
                'bidding_order_id': record['records'][0]['id'],
                'cargo_id': record['records'][0]['cargo_id'][0],
                'quantity': record_cargo['records'][0]['quantity'],
                'weight': record_cargo['records'][0]['weight'],
                'height': record_size_standard['records'][0]['height'],
                'lenght': record_size_standard['records'][0]['length'],
                'from_expected_time': record_cargo['records'][0]['from_receive_time'],
                'to_expected_time': record_cargo['records'][0]['to_receive_time'],
                'actual_time': record['records'][0]['actual_time'],
                'status': '0',
            }
            result_bidding_order_receive = self.env['sharevan.bidding.order.receive'].sudo().create(biddingOrderReceive)

            biddingOrderReturn = {

                'bidding_order_id': record['records'][0]['id'],
                'cargo_id': record['records'][0]['cargo_id'][0],
                'quantity': record_cargo['records'][0]['quantity'],
                'weight': record_cargo['records'][0]['weight'],
                'height': record_size_standard['records'][0]['height'],
                'lenght': record_size_standard['records'][0]['length'],
                'from_expected_time': record_cargo['records'][0]['from_receive_time'],
                'to_expected_time': record_cargo['records'][0]['to_receive_time'],
                'actual_time': record['records'][0]['actual_time'],
                'status': '0',
            }

            result_bidding_order_return = self.env['sharevan.bidding.order.return'].sudo().create(biddingOrderReturn)

            return True

        else:
            raise ValidationError(_('Bidding order does not existed!'))

    def get_driver_biding_order_information(self, bidding_vehicle_id, from_date, to_date, category_item_type, order_by,
                                            offset, limit):
        params = []
        offset_check = 0
        limit_check = 10
        user = self.env['res.users'].search([('id', '=', self.env.uid)])

        if user:
            record_bidding_vehicle = http.request.env[BiddingVehicle._name]. \
                web_search_read([['res_user_id', '=', user.user_id.id]], fields=None,
                                offset=0, limit=10, order='')
            if record_bidding_vehicle['records']:
                query = """
                                                           select cargo.id,
                                                           cargo.cargo_number,
                                                           cargo.status,
                                                           cargo.confirm_time,
                                                           cargo.max_date,
                                                           cargo.from_depot_id,
                                                           cargo.to_depot_id,
                                                           cargo.distance,
                                                           cargo.size_id,
                                                           cargo.quantity,
                                                           cargo.from_receive_time,
                                                           cargo.to_receive_time,
                                                           cargo.from_return_time,
                                                           cargo.to_return_time,
                                                           cargo.bidding_order_id,
                                                           cargo.create_date,
                                                           cargo.product_type_id,
                                                           bidding.id,
                                                           bidding.company_id,
                                                           bidding.driver_name,
                                                           bidding.phone,
                                                           bidding.van_id,
                                                           bidding.total_weight,
                                                           bidding.total_cargo,
                                                           cargo.from_latitude,
                                                           cargo.from_longitude,
                                                           cargo.to_latitude,
                                                           cargo.to_longitude,
                                                           bidding.status,
                                                           bidding.type,
                                                           cargo.create_date
                                                    from sharevan_cargo cargo
                                                    left join sharevan_bidding_order bidding on bidding.id = cargo.bidding_order_id
                                                    left join sharevan_cargo_price price on price.cargo_id = cargo.id
                                                    left join sharevan_product_type product_type on product_type.id = cargo.product_type_id
                                                    left join sharevan_size_standard size_standard  on size_standard.id = cargo.size_id
                                                    where 1=1  """
            # Type = 1, đơn chưa vận chuyện, Cargo => status =1 , Bidding_order => status =1 , type =1
            # Type = 2 , đơn đang vận chuyển (nhận hàng xong),Cargo => status =1 , Bidding_Order => status = 2, type = 2
            # Type = 3 , Lịch sử vận chuyển đã tạo hàng xong , Cargo => status = 1, Bidding_Order => type =1 , status = 2
            # if status_cargo:
            #     query += """ and  cargo.status = %s """
            #     params.append(status_cargo)
            # if status_bidding:
            #     query += """ and  bidding.status = %s """
            #     params.append(status_bidding)
            # if type:
            #     query += """ and bidding.type = %s """
            #     params.append(type)

            if category_item_type and category_item_type == '1':
                query += """ and bidding.type =  """
                query += BiddingStatusType.Approved.value
                query += """ and bidding.status = %s """
                query += BiddingStatus.Received.value
                query += """ and cargo.status = """
                query += CargoStatus.Confirmed.value
            if category_item_type and category_item_type == '2':
                query += """ and bidding.type =  """
                query += BiddingStatusType.Waiting.value
                query += """ and bidding.status = %s """
                query += BiddingStatus.Returned.value
                query += """ and cargo.status = """
                query += CargoStatus.Confirmed.value

            if category_item_type and category_item_type == '3':
                query += """ and bidding.type =  """
                query += BiddingStatusType.Approved.value
                query += """ and bidding.status = %s """
                query += BiddingStatus.Returned.value
                query += """ and cargo.status = """
                query += CargoStatus.Confirmed.value
            if from_date:
                query += """ and bidding.create_date > %s  """
                params.append(from_date)

            if to_date:
                query += """ and bidding.create_date < %s  """
                params.append(to_date)

            query += """  group by cargo.create_date,cargo.id,cargo.confirm_time,
                                                       TO_CHAR(cargo.max_date,'YYYY-MM-DD HH24:MI:SS'),
                                                       cargo.from_depot_id,
                                                       cargo.to_depot_id,
                                                       cargo.distance,
                                                       cargo.size_id,
                                                       cargo.quantity,
                                                       TO_CHAR(cargo.from_receive_time, 'YYYY-MM-DD HH24:MI:SS') ,
                                                       TO_CHAR(cargo.to_receive_time, 'YYYY-MM-DD HH24:MI:SS'),
                                                       TO_CHAR( cargo.from_return_time, 'YYYY-MM-DD HH24:MI:SS'),
                                                       TO_CHAR( cargo.to_return_time, 'YYYY-MM-DD HH24:MI:SS'),
                                                       cargo.bidding_order_id,
                                                       cargo.create_date,
                                                       cargo.product_type_id,
                                                       bidding.id,
                                                       bidding.company_id,
                                                       bidding.driver_name,
                                                       bidding.phone,
                                                       bidding.van_id,
                                                       bidding.total_weight,
                                                       bidding.total_cargo,
                                                       cargo.from_latitude,
                                                       cargo.from_longitude,
                                                       cargo.to_latitude,
                                                       cargo.to_longitude,
                                                       bidding.status,
                                                       bidding.type,
                                                       price.price
                                                       """

            # order by = 1 : Sắp xếp theo giá tăng giần
            # order by = 2 : Sắp xếp theo giá giảm giần
            # order by = 3 : Sắp xếp theo quãng đường tăng dần
            # order by = 4 : Sắp xếp theo  quãng đường giảm dần
            # order by = 5 : Sắp xếp đơn mới nhất
            # order by = 6 : Sắp xếp đơn cũ nhất
            if order_by:
                if order_by == '1':
                    query += """ order by price.price ASC """

                if order_by == '2':
                    query += """ order by price.price DESC """

                if order_by == '3':
                    query += """ order by cargo.distance ASC """

                if order_by == '4':
                    query += """ order by cargo.distance DESC """

                if order_by == '5':
                    query += """ order by bidding.create_date ASC """

                if order_by == '6':
                    query += """ order by bidding.create_date DESC """
            else:
                query += """ order by bidding.create_date ASC """

            total_records = """ SELECT
                                         COUNT(*)
                                         FROM (  """
            total_records += query
            total_records += """ ) t """
            self.env.cr.execute(total_records, (params))
            result_get_total_records = self._cr.fetchall()
            if result_get_total_records[0]:
                if result_get_total_records[0][0]:
                    total = result_get_total_records[0][0]
                else:
                    total = 0

            if offset is not None and limit is not None:
                if offset > 0:
                    offset_check = offset * limit
                    query += """  OFFSET %s LIMIT %s """
                    query_has_offset_limit = query
                    params.append(offset_check)
                    params.append(limit)
                else:
                    query += """  OFFSET %s LIMIT %s """
                    query_has_offset_limit = query
                    params.append(offset)
                    params.append(limit)
            else:
                query += """  OFFSET 0 LIMIT 10 """
                query_has_offset_limit = query

            self.env.cr.execute(query, params)
            jsonRe = []
            result = self._cr.fetchall()

            context = self._context
            tz = context.get('tz')
            if result:
                for re in result:
                    if re:
                        query_get_size_standard = """ SELECT json_agg(t) FROM ( select distinct  size.id,size.length,size.width,size.height,size.long_unit from sharevan_size_standard size
                                                                            join sharevan_cargo  sCargo on size. id = %s ) t """
                        self.env.cr.execute(query_get_size_standard, (re[8],))
                        result_size_standard = self._cr.fetchall()
                        array_length = len(result_size_standard)
                        if array_length > 0:
                            if result_size_standard[0][0]:
                                size_standard = result_size_standard[0][0][0]

                        query_get_price = """ SELECT json_agg(t) FROM ( select distinct price.id,price.cargo_id,price.price, price.status from sharevan_cargo_price price
                                                                    join sharevan_cargo s on price.cargo_id =  %s ) t  """
                        self.env.cr.execute(query_get_price, (re[8],))
                        result_get_price = self._cr.fetchall()

                        array_length = len(result_get_price)
                        if array_length > 0:
                            if result_get_price[0][0]:
                                get_price = result_get_price[0][0][0]
                            else:
                                get_price = {}

                        query_get_product_type = """ SELECT json_agg(t) FROM (  select distinct pType.id,pType.name_seq,pType.net_weight,pType.name,pType.description,pType.status from sharevan_product_type pType
                                                                        join sharevan_cargo s on pType.id = %s ) t  """

                        self.env.cr.execute(query_get_product_type, (re[16],))
                        result_get_product_type = self._cr.fetchall()

                        array_length = len(result_get_product_type)
                        if array_length > 0:
                            if result_get_product_type[0][0]:
                                get_product_type = result_get_product_type[0][0][0]
                            else:
                                get_product_type = {}

                        query_get_from_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                        join sharevan_cargo cargo on depot.id = %s ) t"""
                        self.env.cr.execute(query_get_from_depot, (re[5],))
                        result_get_from_depot = self._cr.fetchall()

                        array_length = len(result_get_from_depot)
                        if array_length > 0:
                            if result_get_from_depot[0][0]:
                                get_from_depot = result_get_from_depot[0][0][0]

                        query_get_to_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                                               join sharevan_cargo cargo on depot.id = %s ) t"""
                        self.env.cr.execute(query_get_to_depot, (re[6],))
                        result_get_to_depot = self._cr.fetchall()
                        get_to_depot = []
                        array_length = len(result_get_to_depot)
                        if array_length > 0:
                            if result_get_to_depot[0][0]:
                                get_to_depot = result_get_to_depot[0][0][0]

                        query_get_bidding_order_receicve = """ SELECT json_agg(t) FROM ( SELECT id, bidding_order_id, cargo_id, quantity, weight, height, lenght, from_expected_time, to_expected_time, depot_id, actual_time, stock_man_id, status, description, create_uid, create_date, write_uid, write_date
	                                                            FROM public.sharevan_bidding_order_receive bor where  bor.bidding_order_id = %s ) t """
                        self.env.cr.execute(query_get_bidding_order_receicve, (re[17],))
                        result_get_bidding_order_receive = self._cr.fetchall()
                        get_bidding_order_receive_object = {}
                        array_length = len(result_get_bidding_order_receive)
                        if array_length > 0:
                            if result_get_bidding_order_receive[0][0]:
                                get_bidding_order_receive_object = result_get_bidding_order_receive[0][0][0]

                        query_get_bidding_order_returns = """SELECT json_agg(t) FROM ( SELECT id, bidding_order_id, cargo_id, quantity, weight, height, lenght, from_expected_time, to_expected_time, depot_id, actual_time, stock_man_id, status, description, create_uid, create_date, write_uid, write_date
	                                                            FROM public.sharevan_bidding_order_return  bOrderReturn where bOrderReturn.bidding_order_id = % s ) t    """
                        self.env.cr.execute(query_get_bidding_order_returns, (re[17],))
                        result_query_get_bidding_order_returns = self._cr.fetchall()
                        get_bidding_order_return_object = {}
                        array_length = len(result_query_get_bidding_order_returns)
                        if array_length > 0:
                            if result_query_get_bidding_order_returns[0][0]:
                                get_bidding_order_return_object = result_query_get_bidding_order_returns[0][0][0]

                        content = {
                            'id': re[0],
                            'cargo_number': re[1],
                            'cargo_status': re[2],
                            'confirm_time': re[3],
                            'max_date': re[4],
                            'from_depot_id': re[5],
                            'to_depot_id': re[6],
                            'distance': re[7],
                            'size_id': re[8],
                            'quantity': re[9],
                            'from_receive_time': re[10],
                            'to_receive_time': re[11],
                            'from_return_time': re[12],
                            'to_return_time': re[13],
                            'bidding_order_id': re[14],
                            'create_date': re[15],
                            'product_type_id': re[16],
                            'bidding_id': re[17],
                            'company_id': re[18],
                            'driver_name': re[19],
                            'phone': re[20],
                            'van_id': re[21],
                            'total_weight': re[22],
                            'total_cargo': re[23],
                            'from_latitude': re[24],
                            'from_longitude': re[25],
                            'to_latitude': re[26],
                            'to_longitude': re[27],
                            'size_standard': size_standard,
                            'price': get_price,
                            'product_type': get_product_type,
                            'from_depot': get_from_depot,
                            'to_depot': get_to_depot,
                            'bidding_status': re[28],
                            'bidding_type': re[29],
                            'bidding_order_receive': get_bidding_order_receive_object,
                            'bididng_order_return': get_bidding_order_return_object

                        }
                        jsonRe.append(content)
                records = {
                    'length': len(result),
                    'total': total,
                    'records': jsonRe
                }
                simplejson.dumps(records, indent=4, sort_keys=True, default=str)
                return records
            else:
                raise ValidationError(_('User does not existed!'))

        return {
            'records': []
        }

    def get_bidding_order_bidded(self, **kwargs):
        params = []
        params_for_count = []
        offset_check = 0
        limit_check = 10
        user = self.env['res.users'].search([('id', '=', self.env.uid)])
        type = ''
        search_code = ''
        from_depot_id = None
        to_depot_id = None
        status = None
        order_by = None
        offset = 0
        limit = 0
        for arg in kwargs:
            if arg == 'type':
                type = kwargs.get(arg)
            if arg == 'search_code':
                search_code = kwargs.get(arg)
            if arg == 'from_depot_id':
                from_depot_id = int(kwargs.get(arg))
            if arg == 'to_depot_id':
                to_depot_id = int(kwargs.get(arg))
            if arg == 'status':
                status = kwargs.get(arg)
            if arg == 'offset':
                offset = kwargs.get(arg)
            if arg == 'limit':
                limit = kwargs.get(arg)
            if arg == 'order':
                order_by = kwargs.get(arg)
        bidding_order_arr = []
        if user:
            record_bidding_vehicle = http.request.env[BiddingVehicle._name]. \
                web_search_read([['res_user_id', '=', user.id]], fields=None,
                                offset=0, limit=10, order='')

            if record_bidding_vehicle:
                params = []
                query_get_bidding_order_json = """ SELECT json_agg(t)
                                                  FROM ( """
                query_get_bidding_order = """ 
                         SELECT   distinct bidding_order.id,
                             bidding_order.company_id,
                             bidding_order.bidding_order_number,
                             bidding_order.from_depot_id,
                             bidding_order.to_depot_id,
                             bidding_order.total_weight,
                             bidding_order.total_cargo,
                             bidding_order.price,
                             bidding_order.distance,
                             bidding_order.type,
                             bidding_order.status,
                             bidding_order.note,
                             bidding_order.bidding_order_receive_id,
                             bidding_order.bidding_order_return_id,
                             TO_CHAR(bidding_order.create_date,'YYYY-MM-DD HH24:MI:SS') create_date,
                             TO_CHAR(bidding_order.write_date,'YYYY-MM-DD HH24:MI:SS') write_date,
                             bidding_order.bidding_package_id,
                             TO_CHAR(bidding_order.from_receive_time,'YYYY-MM-DD HH24:MI:SS') from_receive_time,
                             TO_CHAR(bidding_order.to_receive_time,'YYYY-MM-DD HH24:MI:SS') to_receive_time,
                             TO_CHAR(bidding_order.from_return_time,'YYYY-MM-DD HH24:MI:SS') from_return_time,
                             TO_CHAR(bidding_order.to_return_time,'YYYY-MM-DD HH24:MI:SS')  to_return_time,
                             TO_CHAR(bidding_order.max_confirm_time,'YYYY-MM-DD HH24:MI:SS') max_confirm_time
                     FROM public.sharevan_bidding_order bidding_order
                         LEFT JOIN sharevan_bidding_order_sharevan_bidding_vehicle_rel rel 
                             on bidding_order.id = rel.sharevan_bidding_order_id
                         LEFT JOIN sharevan_bidding_vehicle bidding_vehicle 
                             on bidding_vehicle.id = rel.sharevan_bidding_vehicle_id
                         LEFT JOIN sharevan_depot depot 
                             on depot.id = bidding_order.from_depot_id or depot.id = bidding_order.to_depot_id 
                     where 1 =1 and bidding_order.company_id = %s  """
                params.append(user.company_id.id)
                params_for_count.append(user.company_id.id)
                if search_code:
                    search_code = '%' + search_code + '%'

                    query_get_bidding_order += """ and LOWER(bidding_order.bidding_order_number) like LOWER(%s) """
                    params.append(search_code)
                    params_for_count.append(search_code)
                    query_get_bidding_order += """or LOWER(depot.address) like LOWER(%s)"""
                    params.append(search_code)
                    params_for_count.append(search_code)
                if from_depot_id:
                    query_get_bidding_order += """ and bidding_order.from_depot_id = %s  """
                    params.append(from_depot_id)
                    params_for_count.append(from_depot_id)
                if to_depot_id:
                    query_get_bidding_order += """ and  bidding_order.to_depot_id = %s """
                    params.append(to_depot_id)
                    params_for_count.append(to_depot_id)
                if status:
                    query_get_bidding_order += """ and bidding_order.status::integer in ( """
                    for sta in status:
                        query_get_bidding_order += str(sta) + ","
                    query_get_bidding_order = query_get_bidding_order[:-1]
                    query_get_bidding_order += ")"
                if type:
                    if type == '3':
                        query_get_bidding_order += """ and ( bidding_order.type = %s or   bidding_order.type = %s ) """
                        params.append(BiddingStatusType.Approved.value)
                        params_for_count.append(BiddingStatusType.Approved.value)
                        params.append(BiddingStatusType.Cancel.value)
                        params_for_count.append(BiddingStatusType.Cancel.value)
                    else:
                        query_get_bidding_order += """ and bidding_order.type = %s """
                        params.append(type)
                        params_for_count.append(type)

                # order by = 1 : Sắp xếp theo giá tăng giần
                # order by = 2 : Sắp xếp theo giá giảm giần
                # order by = 3 : Sắp xếp theo quãng đường tăng dần
                # order by = 4 : Sắp xếp theo  quãng đường giảm dần
                # order by = 5 : Sắp xếp đơn cũ nhất
                # order by = 6 : Sắp xếp đơn mới nhất

                if order_by:
                    if order_by == '1':
                        query_get_bidding_order += """ price ASC """

                    if order_by == '2':
                        query_get_bidding_order += """ order by price DESC """

                    if order_by == '3':
                        query_get_bidding_order += """ order by distance ASC """

                    if order_by == '4':
                        query_get_bidding_order += """ order by distance DESC """

                    if order_by == '5':
                        query_get_bidding_order += """ order by create_date ASC """

                    if order_by == '6':
                        query_get_bidding_order += """ order by create_date DESC """
                else:
                    query_get_bidding_order += """ order by create_date ASC """

                query_get_bidding_order_json += query_get_bidding_order

                if offset is not None and limit is not None:
                    if offset > 0:
                        offset_check = offset * limit
                        query_get_bidding_order_json += """  OFFSET %s LIMIT %s """
                        query_has_offset_limit = query_get_bidding_order_json
                        query_has_offset_limit += """ ) t """

                        params.append(offset_check)
                        params.append(limit)
                    else:
                        query_get_bidding_order_json += """  OFFSET %s LIMIT %s """
                        query_has_offset_limit = query_get_bidding_order_json
                        query_get_bidding_order_json += """ ) t """
                        query_has_offset_limit += """ ) t """
                        params.append(offset)
                        params.append(limit)
                else:
                    query_get_bidding_order_json += """  OFFSET 0 LIMIT 10 """
                    query_has_offset_limit = query_get_bidding_order_json
                    query_get_bidding_order_json += """ ) t """

                total_records = """ select count(*) from (  """

                total_records += query_get_bidding_order
                total_records += """ ) t """

                self.env.cr.execute(total_records, (params_for_count))
                result_get_total_records = self._cr.fetchall()
                if result_get_total_records[0]:
                    if result_get_total_records[0][0]:
                        total = result_get_total_records[0][0]

                    else:
                        return {
                            'records': []
                        }

                self.env.cr.execute(query_has_offset_limit, (params))
                result_get_bidding_order = self._cr.fetchall()

                if result_get_bidding_order[0][0]:
                    for bidding_order in result_get_bidding_order[0][0]:
                        query_get_bidding_package_infor = """ 
                                                 SELECT id, bidding_order_id, bidding_package_number, status, 
                                                     TO_CHAR(confirm_time,'YYYY-MM-DD HH24:MI:SS') confirm_time , 
                                                     TO_CHAR(release_time,'YYYY-MM-DD HH24:MI:SS') release_time, 
                                                     TO_CHAR(bidding_time,'YYYY-MM-DD HH24:MI:SS') bidding_time, max_count,
                                                     from_depot_id, to_depot_id, total_weight,
                                                     distance, from_latitude, from_longitude, to_latitude, to_longitude,
                                                     TO_CHAR(from_receive_time,'YYYY-MM-DD HH24:MI:SS') from_receive_time, 
                                                     TO_CHAR(to_receive_time,'YYYY-MM-DD HH24:MI:SS') to_receive_time,
                                                     TO_CHAR(from_return_time,'YYYY-MM-DD HH24:MI:SS') from_return_time,  
                                                     TO_CHAR(to_return_time,'YYYY-MM-DD HH24:MI:SS') to_return_time, price_origin, price,  
                                                     TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS') create_date,
                                                     countdown_time,  price_time_change, price_level_change
                                                     FROM public.sharevan_bidding_package bidding_package where 1=1 
                                                     and bidding_package.id = %s """
                        # print(result_get_bidding_order[0][0][0]['bidding_package_id'])
                        self.env.cr.execute(query_get_bidding_package_infor,
                                            (bidding_order['bidding_package_id'],))
                        jsonRe = []
                        result = self._cr.fetchall()
                        size_standard_arr = []
                        if result:
                            for re in result:
                                total_cargos = []
                                cargo_info_dtl = []
                                query_count_cargo = """ 
                                                     SELECT json_agg(t) FROM ( 
                                                         select count(cargo_rel.sharevan_cargo_id) 
                                                             from sharevan_bidding_package_sharevan_cargo_rel cargo_rel
                                                         where cargo_rel.sharevan_bidding_package_id = %s ) t """
                                self.env.cr.execute(query_count_cargo, (re[0],))
                                result_count_cargo = self._cr.fetchall()
                                total_cargos = result_count_cargo[0][0][0]

                                query_get_cargo_info = """ 
                                                         SELECT json_agg(t) FROM ( 
                                                             SELECT sharevan_cargo.id, sharevan_cargo.cargo_number, sharevan_cargo.from_depot_id,
                                                                 sharevan_cargo.to_depot_id, sharevan_cargo.distance, sharevan_cargo.size_id, 
                                                                 sharevan_cargo.weight, sharevan_cargo.description, sharevan_cargo.price, 
                                                                 sharevan_cargo.from_latitude, sharevan_cargo.to_latitude, 
                                                                 sharevan_cargo.bidding_package_id, 
                                                                 sharevan_cargo.from_longitude, sharevan_cargo.to_longitude,size_standard,
                                                                 size_standard.length, size_standard.width, size_standard.height, 
                                                                 size_standard.type, size_standard.from_weight, size_standard.to_weight, 
                                                                 size_standard.price_id, size_standard.price,
                                                                 size_standard.size_standard_seq, size_standard.long_unit, 
                                                                 size_standard.weight_unit
                                                             FROM public.sharevan_cargo 
                                                                 join sharevan_size_standard  size_standard 
                                                                     on size_standard.id = sharevan_cargo.size_id
                                                                 join sharevan_bidding_package_sharevan_cargo_rel rel 
                                                                     on rel.sharevan_cargo_id=sharevan_cargo.id
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

                                query_get_size_standard = """ 
                                                         SELECT json_agg(t) FROM (  
                                                             select distinct  id, length, width, height, type,from_weight, to_weight, price_id, price, 
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

                                if result_get_size_standard[0][0]:
                                    for rec in result_get_size_standard[0][0]:
                                        query_count_cargo_map_with_size_standard = """ 
                                                                 SELECT json_agg(t) FROM ( select count(*) 
                                                                     from sharevan_cargo cargo where cargo.id  ::integer in ( """
                                        for cargo_id in cargo_ids:
                                            query_count_cargo_map_with_size_standard += str(cargo_id) + ","
                                        query_count_cargo_map_with_size_standard = query_count_cargo_map_with_size_standard[
                                                                                   :-1]
                                        query_count_cargo_map_with_size_standard += """ ) and cargo.size_id = %s  """
                                        query_count_cargo_map_with_size_standard += " ) t"
                                        self.env.cr.execute(query_count_cargo_map_with_size_standard, (rec['id'],))
                                        result_count_cargo_map_with_size_standard = self._cr.fetchall()

                                        query_caculate_cargo_total_weight = """ 
                                                             SELECT json_agg(t) FROM ( select sum(weight) 
                                                                 from sharevan_cargo cargo where cargo.id  ::integer in ( """
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
                                                'cargo_quantity': result_count_cargo_map_with_size_standard[0][0][0][
                                                    'count'],
                                                'total_weight': result_query_caculate_cargo_total_weight[0][0][0]['sum']

                                            }
                                            size_standard_arr.append(size_standard_data)
                        bidding_vehicle_arr = []
                        query_get_bidding_vehicle_order_rel = """ 
                                 SELECT json_agg(t) FROM ( 
                                     SELECT sharevan_bidding_order_id, sharevan_bidding_vehicle_id
                             	        FROM public.sharevan_bidding_order_sharevan_bidding_vehicle_rel rel 
                             	    where rel.sharevan_bidding_order_id = %s ) t """
                        self.env.cr.execute(query_get_bidding_vehicle_order_rel, (bidding_order['id'],))
                        result_get_bidding_vehicle_order_rel = self._cr.fetchall()

                        query_get_from_depot = """ 
                                 SELECT json_agg(t) FROM (  
                                     select distinct  depot.id, depot.name,depot.depot_code,depot.latitude,
                                         depot.longitude,depot.address,depot.street,depot.street2,depot.city_name 
                                         from sharevan_depot depot
                                     where depot.id =  %s ) t"""
                        self.env.cr.execute(query_get_from_depot, (bidding_order['from_depot_id'],))
                        result_get_from_depot = self._cr.fetchall()

                        array_length = len(result_get_from_depot)
                        if array_length > 0:
                            if result_get_from_depot[0][0]:
                                get_from_depot = result_get_from_depot[0][0][0]

                        query_get_to_depot = """ 
                                 SELECT json_agg(t) FROM (  
                                     select distinct  depot.id, depot.name,depot.depot_code,depot.latitude,
                                         depot.longitude,depot.address,depot.street,depot.street2,
                                         depot.city_name from sharevan_depot depot
                                     where   depot.id = %s ) t"""
                        self.env.cr.execute(query_get_to_depot, (bidding_order['to_depot_id'],))
                        result_get_to_depot = self._cr.fetchall()
                        get_to_depot = []
                        array_length = len(result_get_to_depot)
                        if array_length > 0:
                            if result_get_to_depot[0][0]:
                                get_to_depot = result_get_to_depot[0][0][0]
                        if result_get_bidding_vehicle_order_rel[0][0]:
                            for rec in result_get_bidding_vehicle_order_rel[0][0]:
                                bidding_vehicle_param = []
                                query_get_bidding_vehicle = """ 
                                        SELECT bidding_vehicle.id, bidding_vehicle.code, bidding_vehicle.lisence_plate, 
                                                 bidding_vehicle.driver_phone_number, bidding_vehicle.driver_name,
                                                 TO_CHAR(bidding_vehicle.expiry_time,'YYYY-MM-DD HH24:MI:SS') expiry_time,
                                                 bidding_vehicle.company_id, bidding_vehicle.status, bidding_vehicle.description,
                                                 bidding_vehicle.id_card, bidding_vehicle.res_partner_id, bidding_vehicle.tonnage,
                                                 bidding_vehicle.vehicle_type, bidding_vehicle.weight_unit, 
                                                 bidding_vehicle.bidding_vehicle_seq, ia.store_fname
                                             FROM public.sharevan_bidding_vehicle  bidding_vehicle
                                                 left join public.ir_attachment ia 
                                                     on bidding_vehicle.id = ia.res_id and ia.res_model = 'sharevan.bidding.vehicle'   
                                                     and ia.res_field = 'image_128' and ia.status = 'running'
                                              where bidding_vehicle.id = %s """
                                bidding_vehicle_id = rec['sharevan_bidding_vehicle_id']
                                bidding_vehicle_param.append(bidding_vehicle_id)
                                self.env.cr.execute(query_get_bidding_vehicle, (bidding_vehicle_param))
                                result_get_bidding_vehicle = self._cr.dictfetchall()
                                bidding_vehicle_arr = result_get_bidding_vehicle
                        data = {
                            'id': bidding_order['id'],
                            'company_id': bidding_order['company_id'],
                            'bidding_order_number': bidding_order['bidding_order_number'],
                            'from_depot': get_from_depot,
                            'to_depot': get_to_depot,
                            'total_weight': bidding_order['total_weight'],
                            'total_cargo': bidding_order['total_cargo'],
                            'price': bidding_order['price'],
                            'distance': bidding_order['distance'],
                            'type': bidding_order['type'],
                            'status': bidding_order['status'],
                            'note': bidding_order['note'],
                            'bidding_order_receive_id': bidding_order['bidding_order_receive_id'],
                            'bidding_order_return_id': bidding_order['bidding_order_return_id'],
                            'create_date': bidding_order['create_date'],
                            'write_date': bidding_order['write_date'],
                            'bidding_package_id': bidding_order['bidding_package_id'],
                            'from_receive_time': bidding_order['from_receive_time'],
                            'to_receive_time': bidding_order['to_receive_time'],
                            'from_return_time': bidding_order['from_return_time'],
                            'to_return_time': bidding_order['to_return_time'],
                            'max_confirm_time': bidding_order['max_confirm_time'],
                            'bidding_vehicles': bidding_vehicle_arr,
                            'cargo_types': size_standard_arr
                        }

                        bidding_order_arr.append(data)
                else:
                    return {
                        'records': []
                    }

                records = {
                    'length': len(result_get_bidding_order[0][0]),
                    'total_record': total,
                    'records': bidding_order_arr
                }
                simplejson.dumps(records, indent=4, sort_keys=True, default=str)
                return records

            else:
                raise ValidationError(_('Bidding Vehicle does not existed!'))
        else:
            raise ValidationError(_('User does not existed!'))
        return {
            'records': []
        }

    # end of search bidding_order_number

    def get_bidding_order_bidded_stockman(self, **kwargs):
        params = []
        params_for_count = []
        offset_check = 0
        limit_check = 10
        type = ''
        search_code = ''
        from_depot_id = None
        to_depot_id = None
        status = None
        order_by = None
        offset = 0
        limit = 0
        for arg in kwargs:
            if arg == 'type':
                type = kwargs.get(arg)
            if arg == 'search_code':
                search_code = kwargs.get(arg)
            if arg == 'from_depot_id':
                from_depot_id = int(kwargs.get(arg))
            if arg == 'to_depot_id':
                to_depot_id = int(kwargs.get(arg))
            if arg == 'status':
                status = kwargs.get(arg)
            if arg == 'offset':
                offset = kwargs.get(arg)
            if arg == 'limit':
                limit = kwargs.get(arg)
            if arg == 'order':
                order_by = kwargs.get(arg)
        bidding_order_arr = []
        record_bidding_vehicle = http.request.env[BiddingVehicle._name]. \
            web_search_read([['res_user_id', '=', http.request.env.uid]], fields=None,
                            offset=0, limit=10, order='')

        if record_bidding_vehicle:
            params = []
            query_get_bidding_order_json = """ SELECT json_agg(t)
                                                          FROM ( """
            query_get_bidding_order = """ 
                                 SELECT   distinct bidding_order.id,
                                     bidding_order.company_id,
                                     bidding_order.bidding_order_number,
                                     bidding_order.from_depot_id,
                                     bidding_order.to_depot_id,
                                     bidding_order.total_weight,
                                     bidding_order.total_cargo,
                                     bidding_order.price,
                                     bidding_order.distance,
                                     bidding_order.type,
                                     bidding_order.status,
                                     bidding_order.note,
                                     bidding_order.bidding_order_receive_id,
                                     bidding_order.bidding_order_return_id,
                                     TO_CHAR(bidding_order.create_date,'YYYY-MM-DD HH24:MI:SS') create_date,
                                     TO_CHAR(bidding_order.write_date,'YYYY-MM-DD HH24:MI:SS') write_date,
                                     bidding_order.bidding_package_id,
                                     TO_CHAR(bidding_order.from_receive_time,'YYYY-MM-DD HH24:MI:SS') from_receive_time,
                                     TO_CHAR(bidding_order.to_receive_time,'YYYY-MM-DD HH24:MI:SS') to_receive_time,
                                     TO_CHAR(bidding_order.from_return_time,'YYYY-MM-DD HH24:MI:SS') from_return_time,
                                     TO_CHAR(bidding_order.to_return_time,'YYYY-MM-DD HH24:MI:SS')  to_return_time,
                                     TO_CHAR(bidding_order.max_confirm_time,'YYYY-MM-DD HH24:MI:SS') max_confirm_time
                             FROM public.sharevan_bidding_order bidding_order
                                 LEFT JOIN sharevan_bidding_order_sharevan_bidding_vehicle_rel rel 
                                     on bidding_order.id = rel.sharevan_bidding_order_id
                                 LEFT JOIN sharevan_bidding_vehicle bidding_vehicle 
                                     on bidding_vehicle.id = rel.sharevan_bidding_vehicle_id
                                 LEFT JOIN sharevan_depot depot 
                                     on depot.id = bidding_order.from_depot_id or depot.id = bidding_order.to_depot_id 
                             where 1 =1  """
            if search_code:
                search_code = '%' + search_code + '%'

                query_get_bidding_order += """ and LOWER(bidding_order.bidding_order_number) like LOWER(%s) """
                params.append(search_code)
                params_for_count.append(search_code)
                query_get_bidding_order += """or LOWER(depot.address) like LOWER(%s)"""
                params.append(search_code)
                params_for_count.append(search_code)
            if from_depot_id:
                query_get_bidding_order += """ and bidding_order.from_depot_id = %s  """
                params.append(from_depot_id)
                params_for_count.append(from_depot_id)
            if to_depot_id:
                query_get_bidding_order += """ and  bidding_order.to_depot_id = %s """
                params.append(to_depot_id)
                params_for_count.append(to_depot_id)
            if status:
                query_get_bidding_order += """ and bidding_order.status::integer in ( """
                for sta in status:
                    query_get_bidding_order += str(sta) + ","
                query_get_bidding_order = query_get_bidding_order[:-1]
                query_get_bidding_order += ")"
            if type:
                if type == '3':
                    query_get_bidding_order += """ and ( bidding_order.type = %s or   bidding_order.type = %s ) """
                    params.append(BiddingStatusType.Approved.value)
                    params_for_count.append(BiddingStatusType.Approved.value)
                    params.append(BiddingStatusType.Cancel.value)
                    params_for_count.append(BiddingStatusType.Cancel.value)
                else:
                    query_get_bidding_order += """ and bidding_order.type = %s """
                    params.append(type)
                    params_for_count.append(type)

            # order by = 1 : Sắp xếp theo giá tăng giần
            # order by = 2 : Sắp xếp theo giá giảm giần
            # order by = 3 : Sắp xếp theo quãng đường tăng dần
            # order by = 4 : Sắp xếp theo  quãng đường giảm dần
            # order by = 5 : Sắp xếp đơn cũ nhất
            # order by = 6 : Sắp xếp đơn mới nhất

            if order_by:
                if order_by == '1':
                    query_get_bidding_order += """ price ASC """

                if order_by == '2':
                    query_get_bidding_order += """ order by price DESC """

                if order_by == '3':
                    query_get_bidding_order += """ order by distance ASC """

                if order_by == '4':
                    query_get_bidding_order += """ order by distance DESC """

                if order_by == '5':
                    query_get_bidding_order += """ order by create_date ASC """

                if order_by == '6':
                    query_get_bidding_order += """ order by create_date DESC """
            else:
                query_get_bidding_order += """ order by create_date ASC """

            query_get_bidding_order_json += query_get_bidding_order

            if offset is not None and limit is not None:
                if offset > 0:
                    offset_check = offset * limit
                    query_get_bidding_order_json += """  OFFSET %s LIMIT %s """
                    query_has_offset_limit = query_get_bidding_order_json
                    query_has_offset_limit += """ ) t """

                    params.append(offset_check)
                    params.append(limit)
                else:
                    query_get_bidding_order_json += """  OFFSET %s LIMIT %s """
                    query_has_offset_limit = query_get_bidding_order_json
                    query_get_bidding_order_json += """ ) t """
                    query_has_offset_limit += """ ) t """
                    params.append(offset)
                    params.append(limit)
            else:
                query_get_bidding_order_json += """  OFFSET 0 LIMIT 10 """
                query_has_offset_limit = query_get_bidding_order_json
                query_get_bidding_order_json += """ ) t """

            total_records = """ select count(*) from (  """

            total_records += query_get_bidding_order
            total_records += """ ) t """

            self.env.cr.execute(total_records, (params_for_count))
            result_get_total_records = self._cr.fetchall()
            if result_get_total_records[0]:
                if result_get_total_records[0][0]:
                    total = result_get_total_records[0][0]

                else:
                    return {
                        'records': []
                    }

            self.env.cr.execute(query_has_offset_limit, (params))
            result_get_bidding_order = self._cr.fetchall()

            if result_get_bidding_order[0][0]:
                for bidding_order in result_get_bidding_order[0][0]:
                    query_get_bidding_package_infor = """ 
                                                         SELECT id, bidding_order_id, bidding_package_number, status, 
                                                             TO_CHAR(confirm_time,'YYYY-MM-DD HH24:MI:SS') confirm_time , 
                                                             TO_CHAR(release_time,'YYYY-MM-DD HH24:MI:SS') release_time, 
                                                             TO_CHAR(bidding_time,'YYYY-MM-DD HH24:MI:SS') bidding_time, max_count,
                                                             from_depot_id, to_depot_id, total_weight,
                                                             distance, from_latitude, from_longitude, to_latitude, to_longitude,
                                                             TO_CHAR(from_receive_time,'YYYY-MM-DD HH24:MI:SS') from_receive_time, 
                                                             TO_CHAR(to_receive_time,'YYYY-MM-DD HH24:MI:SS') to_receive_time,
                                                             TO_CHAR(from_return_time,'YYYY-MM-DD HH24:MI:SS') from_return_time,  
                                                             TO_CHAR(to_return_time,'YYYY-MM-DD HH24:MI:SS') to_return_time, price_origin, price,  
                                                             TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS') create_date,
                                                             countdown_time,  price_time_change, price_level_change
                                                             FROM public.sharevan_bidding_package bidding_package where 1=1 
                                                             and bidding_package.id = %s """
                    # print(result_get_bidding_order[0][0][0]['bidding_package_id'])
                    self.env.cr.execute(query_get_bidding_package_infor,
                                        (bidding_order['bidding_package_id'],))
                    jsonRe = []
                    result = self._cr.fetchall()
                    size_standard_arr = []
                    if result:
                        for re in result:
                            total_cargos = []
                            cargo_info_dtl = []
                            query_count_cargo = """ 
                                                             SELECT json_agg(t) FROM ( 
                                                                 select count(cargo_rel.sharevan_cargo_id) 
                                                                     from sharevan_bidding_package_sharevan_cargo_rel cargo_rel
                                                                 where cargo_rel.sharevan_bidding_package_id = %s ) t """
                            self.env.cr.execute(query_count_cargo, (re[0],))
                            result_count_cargo = self._cr.fetchall()
                            total_cargos = result_count_cargo[0][0][0]

                            query_get_cargo_info = """ 
                                                                 SELECT json_agg(t) FROM ( 
                                                                     SELECT sharevan_cargo.id, sharevan_cargo.cargo_number, sharevan_cargo.from_depot_id,
                                                                         sharevan_cargo.to_depot_id, sharevan_cargo.distance, sharevan_cargo.size_id, 
                                                                         sharevan_cargo.weight, sharevan_cargo.description, sharevan_cargo.price, 
                                                                         sharevan_cargo.from_latitude, sharevan_cargo.to_latitude, 
                                                                         sharevan_cargo.bidding_package_id, 
                                                                         sharevan_cargo.from_longitude, sharevan_cargo.to_longitude,size_standard,
                                                                         size_standard.length, size_standard.width, size_standard.height, 
                                                                         size_standard.type, size_standard.from_weight, size_standard.to_weight, 
                                                                         size_standard.price_id, size_standard.price,
                                                                         size_standard.size_standard_seq, size_standard.long_unit, 
                                                                         size_standard.weight_unit
                                                                     FROM public.sharevan_cargo 
                                                                         join sharevan_size_standard  size_standard 
                                                                             on size_standard.id = sharevan_cargo.size_id
                                                                         join sharevan_bidding_package_sharevan_cargo_rel rel 
                                                                             on rel.sharevan_cargo_id=sharevan_cargo.id
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

                            query_get_size_standard = """ 
                                                                 SELECT json_agg(t) FROM (  
                                                                     select distinct  id, length, width, height, type,from_weight, to_weight, price_id, price, 
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

                            if result_get_size_standard[0][0]:
                                for rec in result_get_size_standard[0][0]:
                                    query_count_cargo_map_with_size_standard = """ 
                                                                         SELECT json_agg(t) FROM ( select count(*) 
                                                                             from sharevan_cargo cargo where cargo.id  ::integer in ( """
                                    for cargo_id in cargo_ids:
                                        query_count_cargo_map_with_size_standard += str(cargo_id) + ","
                                    query_count_cargo_map_with_size_standard = query_count_cargo_map_with_size_standard[
                                                                               :-1]
                                    query_count_cargo_map_with_size_standard += """ ) and cargo.size_id = %s  """
                                    query_count_cargo_map_with_size_standard += " ) t"
                                    self.env.cr.execute(query_count_cargo_map_with_size_standard, (rec['id'],))
                                    result_count_cargo_map_with_size_standard = self._cr.fetchall()

                                    query_caculate_cargo_total_weight = """ 
                                                                     SELECT json_agg(t) FROM ( select sum(weight) 
                                                                         from sharevan_cargo cargo where cargo.id  ::integer in ( """
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
                                            'cargo_quantity': result_count_cargo_map_with_size_standard[0][0][0][
                                                'count'],
                                            'total_weight': result_query_caculate_cargo_total_weight[0][0][0]['sum']

                                        }
                                        size_standard_arr.append(size_standard_data)
                    bidding_vehicle_arr = []
                    query_get_bidding_vehicle_order_rel = """ 
                                         SELECT json_agg(t) FROM ( 
                                             SELECT sharevan_bidding_order_id, sharevan_bidding_vehicle_id
                                     	        FROM public.sharevan_bidding_order_sharevan_bidding_vehicle_rel rel 
                                     	    where rel.sharevan_bidding_order_id = %s ) t """
                    self.env.cr.execute(query_get_bidding_vehicle_order_rel, (bidding_order['id'],))
                    result_get_bidding_vehicle_order_rel = self._cr.fetchall()

                    query_get_from_depot = """ 
                                         SELECT json_agg(t) FROM (  
                                             select distinct  depot.id, depot.name,depot.depot_code,depot.latitude,
                                                 depot.longitude,depot.address,depot.street,depot.street2,depot.city_name 
                                                 from sharevan_depot depot
                                             where depot.id =  %s ) t"""
                    self.env.cr.execute(query_get_from_depot, (bidding_order['from_depot_id'],))
                    result_get_from_depot = self._cr.fetchall()

                    array_length = len(result_get_from_depot)
                    if array_length > 0:
                        if result_get_from_depot[0][0]:
                            get_from_depot = result_get_from_depot[0][0][0]

                    query_get_to_depot = """ 
                                         SELECT json_agg(t) FROM (  
                                             select distinct  depot.id, depot.name,depot.depot_code,depot.latitude,
                                                 depot.longitude,depot.address,depot.street,depot.street2,
                                                 depot.city_name from sharevan_depot depot
                                             where   depot.id = %s ) t"""
                    self.env.cr.execute(query_get_to_depot, (bidding_order['to_depot_id'],))
                    result_get_to_depot = self._cr.fetchall()
                    get_to_depot = []
                    array_length = len(result_get_to_depot)
                    if array_length > 0:
                        if result_get_to_depot[0][0]:
                            get_to_depot = result_get_to_depot[0][0][0]
                    if result_get_bidding_vehicle_order_rel[0][0]:
                        for rec in result_get_bidding_vehicle_order_rel[0][0]:
                            bidding_vehicle_param = []
                            query_get_bidding_vehicle = """ 
                                                SELECT bidding_vehicle.id, bidding_vehicle.code, bidding_vehicle.lisence_plate, 
                                                         bidding_vehicle.driver_phone_number, bidding_vehicle.driver_name,
                                                         TO_CHAR(bidding_vehicle.expiry_time,'YYYY-MM-DD HH24:MI:SS') expiry_time,
                                                         bidding_vehicle.company_id, bidding_vehicle.status, bidding_vehicle.description,
                                                         bidding_vehicle.id_card, bidding_vehicle.res_partner_id, bidding_vehicle.tonnage,
                                                         bidding_vehicle.vehicle_type, bidding_vehicle.weight_unit, 
                                                         bidding_vehicle.bidding_vehicle_seq, ia.store_fname
                                                     FROM public.sharevan_bidding_vehicle  bidding_vehicle
                                                         left join public.ir_attachment ia 
                                                             on bidding_vehicle.id = ia.res_id and ia.res_model = 'sharevan.bidding.vehicle'   
                                                             and ia.res_field = 'image_128' and ia.status = 'running'
                                                      where bidding_vehicle.id = %s """
                            bidding_vehicle_id = rec['sharevan_bidding_vehicle_id']
                            bidding_vehicle_param.append(bidding_vehicle_id)
                            self.env.cr.execute(query_get_bidding_vehicle, (bidding_vehicle_param))
                            result_get_bidding_vehicle = self._cr.dictfetchall()
                            bidding_vehicle_arr = result_get_bidding_vehicle
                    data = {
                        'id': bidding_order['id'],
                        'company_id': bidding_order['company_id'],
                        'bidding_order_number': bidding_order['bidding_order_number'],
                        'from_depot': get_from_depot,
                        'to_depot': get_to_depot,
                        'total_weight': bidding_order['total_weight'],
                        'total_cargo': bidding_order['total_cargo'],
                        'price': bidding_order['price'],
                        'distance': bidding_order['distance'],
                        'type': bidding_order['type'],
                        'status': bidding_order['status'],
                        'note': bidding_order['note'],
                        'bidding_order_receive_id': bidding_order['bidding_order_receive_id'],
                        'bidding_order_return_id': bidding_order['bidding_order_return_id'],
                        'create_date': bidding_order['create_date'],
                        'write_date': bidding_order['write_date'],
                        'bidding_package_id': bidding_order['bidding_package_id'],
                        'from_receive_time': bidding_order['from_receive_time'],
                        'to_receive_time': bidding_order['to_receive_time'],
                        'from_return_time': bidding_order['from_return_time'],
                        'to_return_time': bidding_order['to_return_time'],
                        'max_confirm_time': bidding_order['max_confirm_time'],
                        'bidding_vehicles': bidding_vehicle_arr,
                        'cargo_types': size_standard_arr
                    }

                    bidding_order_arr.append(data)
            else:
                return {
                    'records': []
                }

            records = {
                'length': len(result_get_bidding_order[0][0]),
                'total_record': total,
                'records': bidding_order_arr
            }
            simplejson.dumps(records, indent=4, sort_keys=True, default=str)
            return records
        else:
            raise ValidationError(_('Bidding Vehicle does not existed!'))

    # end of search bidding_order_number

    def get_bidding_vehicle_tonnage(self):

        query = """
                          SELECT json_agg(t) FROM (
                          SELECT stv.id, stv.code, stv.name, stv.status, stv.description, stv.create_date, 
                          stv.max_tonnage, wu.code, wu.name
	                      FROM public.sharevan_tonnage_vehicle stv join public.weight_unit wu on stv.type_unit = wu.id
	                      where stv.status = 'running'
	                      ) t """
        self._cr.execute(query, ())
        result = self._cr.fetchall()
        return {
            'records': result[0][0]
        }

    def get_bidding_order_detail(self, bidding_order_id):
        user = self.env['res.users'].search([('id', '=', self.env.uid)])
        params = []
        if bidding_order_id is not None:

            query_get_bidding_order = """ SELECT json_agg(t) FROM (  SELECT  distinct bidding_order.id,
                                                                            bidding_order.company_id,
                                                                            bidding_order.bidding_order_number,
                                                                            bidding_order.from_depot_id,
                                                                            bidding_order.to_depot_id,
                                                                            bidding_order.total_weight,
                                                                            bidding_order.total_cargo,
                                                                            bidding_order.price,
                                                                            bidding_order.distance,
                                                                            bidding_order.type,
                                                                            bidding_order.status,
                                                                            bidding_order.note,
                                                                            bidding_order.bidding_order_receive_id,
                                                                            bidding_order.bidding_order_return_id,
                                                                            TO_CHAR(bidding_order.create_date,'YYYY-MM-DD HH24:MI:SS') create_date,
                                                                            TO_CHAR(bidding_order.write_date,'YYYY-MM-DD HH24:MI:SS') write_date,
                                                                            bidding_order.bidding_package_id,
                                                                            TO_CHAR(bidding_order.from_receive_time,'YYYY-MM-DD HH24:MI:SS') from_receive_time,
                                                                            TO_CHAR(bidding_order.to_receive_time,'YYYY-MM-DD HH24:MI:SS') to_receive_time,
                                                                            TO_CHAR(bidding_order.from_return_time,'YYYY-MM-DD HH24:MI:SS') from_return_time,
                                                                            TO_CHAR(bidding_order.to_return_time,'YYYY-MM-DD HH24:MI:SS')  to_return_time,
                                                                            TO_CHAR(bidding_order.max_confirm_time,'YYYY-MM-DD HH24:MI:SS') max_confirm_time
                                                                    FROM public.sharevan_bidding_order bidding_order
                                                                             LEFT JOIN sharevan_bidding_order_sharevan_bidding_vehicle_rel rel on bidding_order.id = rel.sharevan_bidding_order_id
                                                                             LEFT JOIN sharevan_bidding_vehicle bidding_vehicle on bidding_vehicle.id = rel.sharevan_bidding_vehicle_id
                                                                    where  bidding_order.id = %s ) t """

            self.env.cr.execute(query_get_bidding_order, (str(bidding_order_id),))
            result_get_bidding_order = self._cr.fetchall()
            query_get_bidding_package_infor = """ SELECT id, bidding_order_id, bidding_package_number, status, TO_CHAR(confirm_time,'YYYY-MM-DD HH24:MI:SS') confirm_time , TO_CHAR(release_time,'YYYY-MM-DD HH24:MI:SS') release_time, TO_CHAR(bidding_time,'YYYY-MM-DD HH24:MI:SS') bidding_time, max_count,
                                                                                   from_depot_id, to_depot_id, total_weight,
                                                                                   distance, from_latitude, from_longitude, to_latitude, to_longitude, TO_CHAR(from_receive_time,'YYYY-MM-DD HH24:MI:SS') from_receive_time, TO_CHAR(to_receive_time,'YYYY-MM-DD HH24:MI:SS') to_receive_time,
                                                                                   TO_CHAR(from_return_time,'YYYY-MM-DD HH24:MI:SS') from_return_time,  TO_CHAR(to_return_time,'YYYY-MM-DD HH24:MI:SS') to_return_time, price_origin, price,  TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS') create_date,
                                                                                   countdown_time,  price_time_change, price_level_change
                                                                                   FROM public.sharevan_bidding_package bidding_package where 1=1 
                                                                                   and bidding_package.id = %s """
            self.env.cr.execute(query_get_bidding_package_infor,
                                (result_get_bidding_order[0][0][0]['bidding_package_id'],))
            jsonRe = []
            result = self._cr.fetchall()
            if result:
                bidding_package_id = None
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
                            sharevan_cargo.distance, sharevan_cargo.size_id, 
                            sharevan_cargo.weight, sharevan_cargo.description, sharevan_cargo.price, sharevan_cargo.from_latitude, sharevan_cargo.to_latitude, sharevan_cargo.bidding_package_id, 
                            sharevan_cargo.from_longitude, sharevan_cargo.to_longitude,size_standard,
                            size_standard.length, size_standard.width, size_standard.height, size_standard.type, size_standard.from_weight,
                            size_standard.to_weight, size_standard.price_id, size_standard.price,
                            size_standard.size_standard_seq, size_standard.long_unit, size_standard.weight_unit
                        FROM public.sharevan_cargo 
                            join sharevan_size_standard  size_standard on size_standard.id = sharevan_cargo.size_id
                            join sharevan_bidding_package_sharevan_cargo_rel rel on rel.sharevan_cargo_id=sharevan_cargo.id
                        where rel.sharevan_bidding_package_id = %s ) t """
                    self.env.cr.execute(query_get_cargo_info, (re[0],))
                    bidding_package_id = re[0]
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
                                from_weight, to_weight, price_id, price, size_standard_seq, cargo_price_ids, long_unit, weight_unit 
                                from sharevan_size_standard size_stand
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
                            cargo_info_dtl = []
                            # Lấy cargo theo từng size
                            query_get_cargo_info_new = """ 
                                SELECT json_agg(t) FROM ( 
                                    SELECT sharevan_cargo.id, sharevan_cargo.cargo_number, sharevan_cargo.from_depot_id, sharevan_cargo.to_depot_id, 
                                        sharevan_cargo.distance, sharevan_cargo.size_id, sharevan_cargo.weight, sharevan_cargo.description, 
                                        sharevan_cargo.price, sharevan_cargo.from_latitude, sharevan_cargo.to_latitude,
                                        sharevan_cargo.bidding_package_id,  sharevan_cargo.from_longitude, sharevan_cargo.to_longitude,
                                        size_standard,sharevan_cargo.code,size_standard.length, size_standard.width, 
                                        size_standard.height, size_standard.type, size_standard.from_weight, size_standard.to_weight,
                                        size_standard.price_id, size_standard.price, size_standard.size_standard_seq, size_standard.long_unit, 
                                        size_standard.weight_unit
                                    FROM public.sharevan_cargo 
                                        join sharevan_size_standard  size_standard on size_standard.id = sharevan_cargo.size_id
                                    where sharevan_cargo.bidding_package_id = %s and sharevan_cargo.size_id = %s ) t """
                            self.env.cr.execute(query_get_cargo_info_new,
                                                (bidding_package_id, rec['id'],))
                            result_query_get_cargo_info_new = self._cr.fetchall()
                            # danh sách cargo_id thuộc 1 size_standard
                            cargo_id_arr = []
                            if result_query_get_cargo_info_new[0][0]:
                                for cargo in result_query_get_cargo_info_new[0][0]:
                                    cargo_id_arr.append(cargo['id'])
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
                                        'size_standard': "",
                                        'qr_code': cargo['cargo_number']

                                    }
                                    cargo_info_dtl.append(data)
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
                                    'total_weight': result_query_caculate_cargo_total_weight[0][0][0]['sum'],
                                    'cargos': cargo_info_dtl
                                }
                                size_standard_arr.append(size_standard_data)
            if result_get_bidding_order[0][0]:
                bidding_order = result_get_bidding_order[0][0][0]
                bidding_package_id = bidding_order['bidding_package_id']
                bidding_order_json = {}

                if result_get_bidding_order[0][0]:
                    for bidding_order in result_get_bidding_order[0][0]:
                        bidding_vehicle_arr = []
                        query_get_bidding_vehicle_order_rel = """ SELECT json_agg(t) FROM ( SELECT sharevan_bidding_order_id, sharevan_bidding_vehicle_id
                                                                                FROM public.sharevan_bidding_order_sharevan_bidding_vehicle_rel rel 
                                                                                where rel.sharevan_bidding_order_id = %s ) t """
                        self.env.cr.execute(query_get_bidding_vehicle_order_rel, (bidding_order['id'],))
                        result_get_bidding_vehicle_order_rel = self._cr.fetchall()

                        query_get_from_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.latitude,depot.longitude,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                                            where depot.id =  %s ) t"""
                        self.env.cr.execute(query_get_from_depot, (bidding_order['from_depot_id'],))
                        result_get_from_depot = self._cr.fetchall()

                        array_length = len(result_get_from_depot)
                        if array_length > 0:
                            if result_get_from_depot[0][0]:
                                get_from_depot = result_get_from_depot[0][0][0]

                        query_get_to_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                                                              where     depot.id = %s ) t"""
                        self.env.cr.execute(query_get_to_depot, (bidding_order['to_depot_id'],))
                        result_get_to_depot = self._cr.fetchall()
                        get_to_depot = []
                        array_length = len(result_get_to_depot)
                        if array_length > 0:
                            if result_get_to_depot[0][0]:
                                get_to_depot = result_get_to_depot[0][0][0]
                        if result_get_bidding_vehicle_order_rel[0][0]:
                            for rec in result_get_bidding_vehicle_order_rel[0][0]:
                                bidding_order_receive = {}
                                bidding_order_return = {}
                                query_get_bidding_vehicle = """ 
                                    SELECT json_agg(t) FROM (
                                        SELECT bidding_vehicle.id, bidding_vehicle.code, bidding_vehicle.lisence_plate, bidding_vehicle.driver_phone_number,
                                            bidding_vehicle.driver_name,bidding_vehicle.vehicle_id,bidding_vehicle.driver_id,
                                            TO_CHAR(bidding_vehicle.expiry_time,'YYYY-MM-DD HH24:MI:SS') expiry_time, 
                                            bidding_vehicle.company_id, bidding_vehicle.status, bidding_vehicle.description,
                                            bidding_vehicle.id_card, bidding_vehicle.res_partner_id, bidding_vehicle.tonnage, bidding_vehicle.vehicle_type,
                                            bidding_vehicle.weight_unit, bidding_vehicle.bidding_vehicle_seq, ia.store_fname
                                        FROM public.sharevan_bidding_vehicle  bidding_vehicle
                                        left join public.ir_attachment ia on bidding_vehicle.id = ia.res_id and ia.res_model = 'sharevan.bidding.vehicle'   and ia.res_field = 'image_128' and ia.status = 'running'
                                            where bidding_vehicle.id = %s ) t """
                                bidding_vehicle_id = rec['sharevan_bidding_vehicle_id']
                                self.env.cr.execute(query_get_bidding_vehicle, (bidding_vehicle_id,))
                                result_get_bidding_vehicle = self._cr.fetchall()

                                bidding_vehicle_param = []
                                query_get_cargo_bidding_order_vehicle = """ 
                                    SELECT distinct cargo_id FROM public.sharevan_cargo_bidding_order_vehicle s 
                                        where s.bidding_order_id = """
                                query_get_cargo_bidding_order_vehicle += str(bidding_order_id)
                                query_get_cargo_bidding_order_vehicle += """ and s.bidding_vehicle_id = """
                                query_get_cargo_bidding_order_vehicle += str(bidding_vehicle_id)
                                query_get_cargo_bidding_order_vehicle += """ and s.status = '1' """
                                # query_get_cargo_bidding_order_vehicle += CargoBiddingOrderVehicleStatus.running.value
                                self.env.cr.execute(query_get_cargo_bidding_order_vehicle, ())
                                result_get_cargo_bidding_order_vehicle = self._cr.fetchall()
                                list_cargo_id = []
                                size_standard_arr = []
                                if result_get_cargo_bidding_order_vehicle:
                                    for id in result_get_cargo_bidding_order_vehicle:
                                        list_cargo_id.append(id[0])
                                    query_get_size_standard = """ 
                                    SELECT json_agg(t) FROM (  
                                        select distinct  id, length, width, height, type, from_weight, to_weight, 
                                            price_id, price, size_standard_seq, cargo_price_ids, long_unit, weight_unit 
                                        from sharevan_size_standard size_stand
                                            where size_stand.id in (select cargo.size_id from sharevan_cargo cargo where cargo.id  ::integer in ( """

                                    if list_cargo_id:
                                        for cargo_id in list_cargo_id:
                                            query_get_size_standard += str(cargo_id) + ","
                                        query_get_size_standard = query_get_size_standard[:-1]
                                        query_get_size_standard += "))) t"

                                    self.env.cr.execute(query_get_size_standard, (list_cargo_id))
                                    result_get_size_standard = self._cr.fetchall()
                                    if result_get_size_standard[0][0]:
                                        for rec in result_get_size_standard[0][0]:
                                            query_count_cargo_map_with_size_standard = """ 
                                                SELECT json_agg(t) FROM ( 
                                                    select count(*) from sharevan_cargo cargo where cargo.id  ::integer in ( """
                                            for cargo_id in list_cargo_id:
                                                query_count_cargo_map_with_size_standard += str(cargo_id) + ","
                                            query_count_cargo_map_with_size_standard = query_count_cargo_map_with_size_standard[
                                                                                       :-1]
                                            query_count_cargo_map_with_size_standard += """ ) and cargo.size_id = %s  """
                                            query_count_cargo_map_with_size_standard += " ) t"
                                            self.env.cr.execute(query_count_cargo_map_with_size_standard, (rec['id'],))
                                            result_count_cargo_map_with_size_standard = self._cr.fetchall()

                                            query_caculate_cargo_total_weight = """ 
                                            SELECT json_agg(t) FROM ( 
                                                select sum(weight) from sharevan_cargo cargo where cargo.id  ::integer in ( """
                                            for cargo_id in list_cargo_id:
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
                                                    'cargo_quantity':
                                                        result_count_cargo_map_with_size_standard[0][0][0][
                                                            'count'],
                                                    'total_weight': result_query_caculate_cargo_total_weight[0][0][0][
                                                        'sum'],
                                                    'cargos': cargo_info_dtl

                                                }
                                                size_standard_arr.append(size_standard_data)
                                        params_new = []
                                        query_get_bidding_order_receive = """ 
                                            SELECT json_agg(t) FROM ( 
                                                SELECT id, bidding_order_id,  TO_CHAR(from_expected_time,'YYYY-MM-DD HH24:MI:SS') from_expected_time, 
                                                    TO_CHAR(to_expected_time,'YYYY-MM-DD HH24:MI:SS') to_expected_time, depot_id, 
                                                    TO_CHAR(actual_time,'YYYY-MM-DD HH24:MI:SS') actual_time, stock_man_id, status, description, 
                                                    TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS') create_date, bidding_order_vehicle_id
                                    	        FROM public.sharevan_bidding_order_receive bidding_order_receive 
                                    	            where bidding_order_receive.bidding_order_id = %s   
                                    	                and bidding_order_receive.bidding_vehicle_id = %s  ) t """
                                        params_new.append(str(bidding_order_id))
                                        params_new.append(result_get_bidding_vehicle[0][0][0]['id'])
                                        self.env.cr.execute(query_get_bidding_order_receive, (params_new))
                                        result_get_bidding_order_receive = self._cr.fetchall()
                                        if result_get_bidding_order_receive[0][0]:
                                            bidding_order_receive = result_get_bidding_order_receive[0][0][0]

                                        query_get_bidding_order_return = """ 
                                            SELECT json_agg(t) FROM ( 
                                                SELECT id, bidding_order_id, TO_CHAR(from_expected_time,'YYYY-MM-DD HH24:MI:SS') from_expected_time,  
                                                    TO_CHAR(to_expected_time,'YYYY-MM-DD HH24:MI:SS') to_expected_time,
                                                    TO_CHAR(actual_time,'YYYY-MM-DD HH24:MI:SS') actual_time, depot_id,
                                                    TO_CHAR(actual_time,'YYYY-MM-DD HH24:MI:SS')  , stock_man_id, status, description,
                                                    TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS')   create_date, bidding_order_vehicle_id
                                                FROM public.sharevan_bidding_order_return  bidding_order_return 
                                                    where bidding_order_return.bidding_order_id = %s  
                                                    and bidding_order_return.bidding_vehicle_id = %s )  t """
                                        self.env.cr.execute(query_get_bidding_order_return, (params_new))
                                        result_get_bidding_order_return = self._cr.fetchall()
                                        if result_get_bidding_order_return[0][0]:
                                            bidding_order_return = result_get_bidding_order_return[0][0][0]

                                bidding_vehicle_json = {
                                    'id': result_get_bidding_vehicle[0][0][0]['id'],
                                    'code': result_get_bidding_vehicle[0][0][0]['code'],
                                    'lisence_plate': result_get_bidding_vehicle[0][0][0]['lisence_plate'],
                                    'driver_phone_number': result_get_bidding_vehicle[0][0][0]['driver_phone_number'],
                                    'driver_name': result_get_bidding_vehicle[0][0][0]['driver_name'],
                                    'expiry_time': result_get_bidding_vehicle[0][0][0]['expiry_time'],
                                    'company_id': result_get_bidding_vehicle[0][0][0]['company_id'],
                                    'vehicle_id': result_get_bidding_vehicle[0][0][0]['vehicle_id'],
                                    'driver_id': result_get_bidding_vehicle[0][0][0]['driver_id'],
                                    'status': result_get_bidding_vehicle[0][0][0]['status'],
                                    'description': result_get_bidding_vehicle[0][0][0]['description'],
                                    'vehicle_type': result_get_bidding_vehicle[0][0][0]['vehicle_type'],
                                    'weight_unit': result_get_bidding_vehicle[0][0][0]['weight_unit'],
                                    'store_fname': result_get_bidding_vehicle[0][0][0]['store_fname'],
                                    'cargo_types': size_standard_arr,
                                    'bidding_order_receive': bidding_order_receive,
                                    'bidding_order_return': bidding_order_return
                                }

                                bidding_vehicle_arr.append(bidding_vehicle_json)

                query_get_bidding_package_infor = """ SELECT bidding_package.id, bidding_package.bidding_order_id, bidding_package.bidding_package_number, bidding_package.status, TO_CHAR(bidding_package.confirm_time,'YYYY-MM-DD HH24:MI:SS') confirm_time , TO_CHAR(bidding_package.release_time,'YYYY-MM-DD HH24:MI:SS') release_time, TO_CHAR(bidding_package.bidding_time,'YYYY-MM-DD HH24:MI:SS') bidding_time, bidding_package.max_count,
                                                                bidding_package.from_depot_id, bidding_package.to_depot_id, bidding_package.total_weight,
                                                                bidding_package.distance, bidding_package.from_latitude, bidding_package.from_longitude, bidding_package.to_latitude, bidding_package.to_longitude, bidding_package.from_receive_time, bidding_package.to_receive_time,
                                                                bidding_package.from_return_time, bidding_package.to_return_time, bidding_package.price_origin, bidding_package.price, bidding_package.create_date, bidding_package.write_date,
                                                                bidding_package.countdown_time, bidding_package.price_time_change, bidding_package.price_level_change
                                                                FROM public.sharevan_bidding_package bidding_package 
                                                                join sharevan_bidding_order bidding_order on bidding_order.bidding_package_id  = bidding_package.id
                                                                where 1=1 
                                                                and bidding_package.id = %s """
                params.append(bidding_package_id)
                self.env.cr.execute(query_get_bidding_package_infor, params)
                jsonRe = []
                result = self._cr.fetchall()
                query_get_size_standard = """ 
                SELECT json_agg(t) FROM (  
                    select distinct  id, length, width, height, type,from_weight, to_weight, price_id, price, size_standard_seq,
                        cargo_price_ids, long_unit, weight_unit 
                    from sharevan_size_standard size_stand
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

                        query_get_cargo_info = """ 
                        SELECT json_agg(t) FROM ( 
                            SELECT sharevan_cargo.id, sharevan_cargo.cargo_number, sharevan_cargo.from_depot_id, 
                                sharevan_cargo.to_depot_id, sharevan_cargo.distance, sharevan_cargo.size_id, 
                                sharevan_cargo.weight, sharevan_cargo.description, sharevan_cargo.price, sharevan_cargo.from_latitude, 
                                sharevan_cargo.to_latitude, sharevan_cargo.bidding_package_id, 
                                sharevan_cargo.from_longitude, sharevan_cargo.to_longitude,size_standard,
                                size_standard.length, size_standard.width, size_standard.height, size_standard.type, 
                                size_standard.from_weight, size_standard.to_weight, size_standard.price_id, size_standard.price,
                                size_standard.size_standard_seq, size_standard.long_unit, size_standard.weight_unit
                            FROM public.sharevan_cargo 
                                join sharevan_size_standard  size_standard on size_standard.id = sharevan_cargo.size_id
                            where sharevan_cargo.bidding_package_id = %s ) t """
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

                        query_get_from_depot = """ 
                            SELECT json_agg(t) FROM (  
                                select distinct  depot.id, depot.name,depot.depot_code,depot.address,depot.street,
                                    depot.street2,depot.city_name ,phone
                                from sharevan_depot depot
                                    join sharevan_bidding_package bidding_package on depot.id = %s ) t"""
                        self.env.cr.execute(query_get_from_depot, (re[8],))
                        result_get_from_depot = self._cr.fetchall()

                        array_length = len(result_get_from_depot)
                        if array_length > 0:
                            if result_get_from_depot[0][0]:
                                get_from_depot = result_get_from_depot[0][0][0]

                        query_get_to_depot = """ 
                        SELECT json_agg(t) FROM (  
                            select distinct  depot.id, depot.name,depot.depot_code,depot.address,depot.street,
                                depot.street2,depot.city_name ,phone
                            from sharevan_depot depot
                                join sharevan_bidding_package bidding_package on depot.id = %s ) t"""
                        self.env.cr.execute(query_get_to_depot, (re[9],))
                        result_get_to_depot = self._cr.fetchall()
                        get_to_depot = []
                        array_length = len(result_get_to_depot)
                        if array_length > 0:
                            if result_get_to_depot[0][0]:
                                get_to_depot = result_get_to_depot[0][0][0]

                        data = {
                            'id': bidding_order['id'],
                            'company_id': bidding_order['company_id'],
                            'bidding_order_number': bidding_order['bidding_order_number'],
                            'from_depot': get_from_depot,
                            'to_depot': get_to_depot,
                            'total_weight': bidding_order['total_weight'],
                            'total_cargo': bidding_order['total_cargo'],
                            'price': bidding_order['price'],
                            'distance': bidding_order['distance'],
                            'type': bidding_order['type'],
                            'status': bidding_order['status'],
                            'note': bidding_order['note'],
                            'bidding_order_receive_id': bidding_order['bidding_order_receive_id'],
                            'bidding_order_return_id': bidding_order['bidding_order_return_id'],
                            'create_date': bidding_order['create_date'],
                            'write_date': bidding_order['write_date'],
                            'bidding_package_id': bidding_order['bidding_package_id'],
                            'from_receive_time': bidding_order['from_receive_time'],
                            'to_receive_time': bidding_order['to_receive_time'],
                            'from_return_time': bidding_order['from_return_time'],
                            'to_return_time': bidding_order['to_return_time'],
                            'max_confirm_time': bidding_order['max_confirm_time'],
                            'bidding_vehicles': bidding_vehicle_arr,
                            'total_cargo': total_cargos['count'],
                            'cargo_types': size_standard_arr

                        }
                        bidding_order_json = data

                        content = {
                            'id': re[0],
                            'bidding_package_number': re[2],
                            'status': re[3],
                            'confirm_time': re[4],
                            'release_time': re[5],
                            'bidding_time': re[6],
                            'max_count': re[7],
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
                            'write_date': re[23],
                            'countdown_time': re[24],
                            'price_time_change': re[25],
                            'price_level_change': re[26],
                            'bidding_order': bidding_order_json
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
                raise ValidationError(_('Bidding Order does not existed!'))
        else:
            raise ValidationError(_('Bidding Order does not existed!'))

    # type = 1 => update, type != 1 => create
    def driver_confirm_cargo_quantity(self, bidding_order_id, cargo_ids, type, confirm_time):
        confirm_count = 0
        list_cargo_id = cargo_ids.split(",")
        list_cargo_invalid = []

        query_get_bidding_vehicle = """ 
            SELECT json_agg(t) FROM (
                SELECT bidding_vehicle.id, bidding_vehicle.code, bidding_vehicle.lisence_plate, bidding_vehicle.driver_phone_number, 
                    bidding_vehicle.driver_name, TO_CHAR(bidding_vehicle.expiry_time,'YYYY-MM-DD HH24:MI:SS') expiry_time, 
                    bidding_vehicle.company_id, bidding_vehicle.status, bidding_vehicle.description,
                    bidding_vehicle.id_card, bidding_vehicle.res_partner_id, bidding_vehicle.tonnage, bidding_vehicle.vehicle_type,
                    bidding_vehicle.weight_unit, bidding_vehicle.bidding_vehicle_seq, ia.store_fname
                FROM public.sharevan_bidding_vehicle  bidding_vehicle
                    join sharevan_bidding_order_sharevan_bidding_vehicle_rel rel on rel.sharevan_bidding_vehicle_id = bidding_vehicle.id
                    left join public.ir_attachment ia on bidding_vehicle.id = ia.res_id 
                        and ia.res_model = 'sharevan.bidding.vehicle'   and ia.res_field = 'image_128' and ia.status = 'running'
                    where bidding_vehicle.res_user_id = %s  and rel.sharevan_bidding_order_id =%s ) t """

        res_user_id = http.request.env.uid
        self.env.cr.execute(query_get_bidding_vehicle, (res_user_id, bidding_order_id,))
        result_get_bidding_vehicle = self._cr.fetchall()
        if result_get_bidding_vehicle[0][0]:
            if bidding_order_id:
                bidding_order = self.env[Constants.SHAREVAN_BIDDING_ORDER].search([('id', '=', bidding_order_id)])
                if bidding_order:
                    confirm_count = bidding_order.confirm_count
                    if bidding_order.type != BiddingStatus.Received.value:
                        raise ValidationError(_('Admin has not approved the bidding order!'))
                    if list_cargo_id:
                        query_get_cargo_package = """ 
                            SELECT json_agg(t) FROM (
                                SELECT sharevan_bidding_package_id, sharevan_cargo_id 
                                    FROM public.sharevan_bidding_package_sharevan_cargo_rel rel 
                                where rel.sharevan_bidding_package_id = %s) t """

                        bidding_package_id = bidding_order.bidding_package_id.id
                        self.env.cr.execute(query_get_cargo_package, (bidding_package_id,))
                        result_get_cargo_package = self._cr.fetchall()
                        list_cargo_in_package = []
                        bidding_vehicle_id = result_get_bidding_vehicle[0][0][0]['id']
                        for rec in result_get_cargo_package[0][0]:
                            list_cargo_in_package.append(rec['sharevan_cargo_id'])
                        order_received_array = []
                        if type == '1':
                            # get list  cargo_bidding_order_vehicles ban đầu , rồi chuyển trạng thái sang 0
                            cargo_bidding_order_vehicles = self.env[
                                Constants.SHAREVAN_CARGO_BIDDING_ORDER_VEHICLE].search(
                                [('bidding_order_id', '=', bidding_order_id),
                                 ('bidding_vehicle_id', '=', bidding_vehicle_id),
                                 ('status', '=', CargoBiddingOrderVehicleStatus.running.value)])

                            for rec in cargo_bidding_order_vehicles.ids:
                                http.request.env[Constants.SHAREVAN_CARGO_BIDDING_ORDER_VEHICLE]. \
                                    browse(rec).write(
                                    {'status': CargoBiddingOrderVehicleStatus.deleted.value})
                            for cargo_id in list_cargo_id:
                                if int(cargo_id) in list_cargo_in_package:
                                    # check nếu cargo đã được driver khác confirm thì driver này sẽ không được confirm cargo đó nữa
                                    query_get_cargo_package = """ 
                                        SELECT json_agg(t) FROM (
                                            SELECT id, cargo_id, bidding_order_id, bidding_vehicle_id, status
                                                FROM public.sharevan_cargo_bidding_order_vehicle v 
                                            where v.cargo_id  = %s and v.bidding_order_id = %s and v.status = '1') t """
                                    self.env.cr.execute(query_get_cargo_package, (cargo_id, bidding_order_id,))
                                    result_get_cargo_package = self._cr.fetchall()
                                    if result_get_cargo_package[0][0]:
                                        for rec in result_get_cargo_package[0][0]:
                                            if rec['bidding_vehicle_id'] != bidding_vehicle_id:
                                                list_cargo_invalid.append(rec['cargo_id'])

                                    if not list_cargo_invalid:
                                        cargo_bidding_order_vehicle = {
                                            'bidding_order_id': bidding_order_id,
                                            'bidding_vehicle_id': bidding_vehicle_id,
                                            'cargo_id': cargo_id,
                                            'status': CargoBiddingOrderVehicleStatus.running.value
                                        }
                                        result = self.env[
                                            Constants.SHAREVAN_CARGO_BIDDING_ORDER_VEHICLE].sudo().create(
                                            cargo_bidding_order_vehicle)
                                else:
                                    raise ValidationError(
                                        _('Cargo with id ' + cargo_id + 'does not existed in Bidding Order!'))

                            # Trả về danh sách cargo_id không hợp lệ
                            if list_cargo_invalid:
                                val = {
                                    'list_cargo_invalid': list_cargo_invalid
                                }
                                records = {
                                    'records': [val]
                                }
                                simplejson.dumps(records, indent=4, sort_keys=True, default=str)
                                return records

                            self.check_quantity_cargo_confirmed(bidding_order_id, bidding_package_id,
                                                                list_cargo_in_package,
                                                                bidding_order.bidded_user_id.id, res_user_id)
                            query_bidding_order_receive = """ 
                            SELECT json_agg(t) FROM (
                                SELECT id, bidding_order_id, TO_CHAR(from_expected_time,'YYYY-MM-DD HH24:MI:SS') from_expected_time, 
                                    TO_CHAR(to_expected_time,'YYYY-MM-DD HH24:MI:SS') to_expected_time, depot_id, 
                                    TO_CHAR(actual_time,'YYYY-MM-DD HH24:MI:SS') actual_time, stock_man_id, status, description,   
                                    TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS') create_date, bidding_order_vehicle_id, bidding_vehicle_id
                                FROM public.sharevan_bidding_order_receive s 
                                    where s.bidding_order_id = %s and s.bidding_vehicle_id = %s) t """

                            self.env.cr.execute(query_bidding_order_receive,
                                                (bidding_order_id, bidding_vehicle_id,))
                            record_bidding_order_receive = self._cr.fetchall()

                            if record_bidding_order_receive[0][0]:
                                for rec in record_bidding_order_receive[0][0]:
                                    receive = http.request.env['sharevan.bidding.order.receive']. \
                                        browse(rec['id']).write(
                                        {'actual_time': confirm_time,
                                         'status': CargoBiddingOrderVehicleStatus.running.value})
                                    order_received_array.append(receive)
                                val = {
                                    'list_cargo_invalid': list_cargo_invalid
                                }
                                records = {
                                    'records': [val]
                                }
                                return records
                        else:
                            query_bidding_order_receive = """ 
                            SELECT json_agg(t) FROM (
                                SELECT id, bidding_order_id,status, 
                                    TO_CHAR(from_expected_time,'YYYY-MM-DD HH24:MI:SS') from_expected_time,
                                    TO_CHAR(to_expected_time,'YYYY-MM-DD HH24:MI:SS') to_expected_time, 
                                    depot_id, TO_CHAR(actual_time,'YYYY-MM-DD HH24:MI:SS') actual_time, 
                                    stock_man_id, status, description,   
                                    TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS') create_date,
                                    bidding_order_vehicle_id, bidding_vehicle_id
                                FROM public.sharevan_bidding_order_receive s 
                                    where s.bidding_order_id = %s and s.bidding_vehicle_id = %s) t """
                            self.env.cr.execute(query_bidding_order_receive,
                                                (bidding_order_id, bidding_vehicle_id,))
                            record_bidding_order_receive = self._cr.fetchall()
                            if record_bidding_order_receive[0][0]:
                                for rec in record_bidding_order_receive[0][0]:
                                    if rec['status'] == '1':
                                        raise ValidationError(_('You must update confirm, not create!'))
                            for cargo_id in list_cargo_id:
                                if int(cargo_id) in list_cargo_in_package:
                                    # check nếu cargo đã được driver khác confirm thì driver này sẽ không được confirm cargo đó nữa
                                    query_get_cargo_package = """ 
                                        SELECT json_agg(t) FROM (
                                            SELECT id, cargo_id, bidding_order_id, bidding_vehicle_id, status
                                                FROM public.sharevan_cargo_bidding_order_vehicle v 
                                            where v.cargo_id  = %s and v.bidding_order_id = %s and v.status = '1') t """
                                    self.env.cr.execute(query_get_cargo_package, (cargo_id, bidding_order_id,))
                                    result_get_cargo_package = self._cr.fetchall()
                                    if result_get_cargo_package[0][0]:
                                        for rec in result_get_cargo_package[0][0]:
                                            if rec['bidding_vehicle_id'] != bidding_vehicle_id:
                                                list_cargo_invalid.append(rec['cargo_id'])

                                    if not list_cargo_invalid:
                                        cargo_bidding_order_vehicle = {
                                            'bidding_order_id': bidding_order_id,
                                            'bidding_vehicle_id': bidding_vehicle_id,
                                            'cargo_id': cargo_id,
                                            'status': '1'
                                        }
                                        result = self.env[
                                            Constants.SHAREVAN_CARGO_BIDDING_ORDER_VEHICLE].sudo().create(
                                            cargo_bidding_order_vehicle)
                                else:
                                    raise ValidationError(
                                        'Cargo with id ' + cargo_id + 'does not existed in Bidding Order!')
                            if list_cargo_invalid:
                                val = {
                                    'list_cargo_invalid': list_cargo_invalid
                                }
                                records = {
                                    'records': [val]
                                }
                                simplejson.dumps(records, indent=4, sort_keys=True, default=str)
                                return records

                            self.check_quantity_cargo_confirmed(bidding_order_id, bidding_package_id,
                                                                list_cargo_in_package,
                                                                bidding_order.bidded_user_id.id, res_user_id)

                            query_bidding_order_receive = """ 
                                SELECT json_agg(t) FROM (
                                    SELECT id, bidding_order_id, TO_CHAR(from_expected_time,'YYYY-MM-DD HH24:MI:SS') from_expected_time, 
                                        TO_CHAR(to_expected_time,'YYYY-MM-DD HH24:MI:SS') to_expected_time, depot_id, 
                                        TO_CHAR(actual_time,'YYYY-MM-DD HH24:MI:SS') actual_time, stock_man_id, status, 
                                        description, TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS') create_date, 
                                        bidding_order_vehicle_id, bidding_vehicle_id
                                    FROM public.sharevan_bidding_order_receive s 
                                        where s.bidding_order_id = %s and s.bidding_vehicle_id = %s) t """

                            self.env.cr.execute(query_bidding_order_receive,
                                                (bidding_order_id, bidding_vehicle_id,))
                            record_bidding_order_receive = self._cr.fetchall()

                            if record_bidding_order_receive[0][0]:
                                for rec in record_bidding_order_receive[0][0]:
                                    receive = http.request.env['sharevan.bidding.order.receive']. \
                                        browse(rec['id']).write(
                                        {'actual_time': confirm_time,
                                         'status': CargoBiddingOrderVehicleStatus.running.value})
                                    order_received_array.append(receive)
                        val = {
                            'list_cargo_invalid': list_cargo_invalid
                        }
                        records = {
                            'records': [val]
                        }

                        check_status_array = self.env['sharevan.bidding.order.receive'].search(
                            [('bidding_order_id', '=', int(bidding_order_id))])
                        check_all = len(check_status_array)
                        check_one = 0
                        for status in check_status_array:
                            if status['status'] == '1':
                                check_one += 1
                        if check_one == check_all:
                            bidding_order.write({'status': '1'})
                            # update capacity depot
                            routing_query = """
                                select routing.from_routing_plan_day_id id,routing.id now_id,
                                    routing.depot_id,routing.total_volume
                                    from sharevan_bidding_order bidding_order
                                join sharevan_bidding_package package on package.id= bidding_order.bidding_package_id
                                join sharevan_bidding_package_sharevan_cargo_rel rel 
                                    on rel.sharevan_bidding_package_id = package.id
                                join sharevan_cargo cargo on cargo.id = rel.sharevan_cargo_id
                                join sharevan_cargo_sharevan_routing_plan_day_rel cargo_routing 
                                    on cargo_routing.sharevan_cargo_id = cargo.id
                                join sharevan_routing_plan_day routing 
                                    on routing.id = cargo_routing.sharevan_routing_plan_day_id
                                where bidding_order.id = %s
                            """
                            self.env.cr.execute(routing_query,
                                                (bidding_order_id,))
                            routing_result = self._cr.dictfetchall()
                            if routing_result:
                                for rec in routing_result:
                                    depot_vals = {
                                        "routing_plan_day_id": rec['id'],
                                        "depot_id": rec['depot_id'],
                                        "total_volume": rec['total_volume'],
                                        "type": 1,
                                        "force_save": False
                                    }
                                    http.request.env[DepotGoods._name].export_goods(depot_vals)
                                    routingAccept = http.request.env[RoutingPlanDay._name].search(
                                        [('id', '=', rec['now_id'])])
                                    if routingAccept:
                                        routingAccept.write({'status': '2'})
                                    else:
                                        logger.warn(
                                            "Can not update status because routing not found!",
                                            'sharevan.routing.plan.day', bidding_order_id,
                                            exc_info=True)
                            else:
                                logger.warn(
                                    "Can not update depot capacity because routing not found!",
                                    'sharevan.routing.plan.day', bidding_order_id,
                                    exc_info=True)
                        return records
                    else:
                        raise ValidationError('cargo_ids can not null!!')

                else:
                    raise ValidationError('Bidding order does not existed!')

            else:
                raise ValidationError('bidding_order_id can not null!')
        else:
            return False

    def check_quantity_cargo_confirmed(self, bidding_order_id, bidding_package_id, list_cargo_in_package,
                                       bidded_user_id, res_user_id):
        confirm_count = 0
        # Check số lượng cargo đã xác nhận có đủ với số lượng cargo của bidding_order không.
        query_count_bidding_vehicle = """ SELECT json_agg(t) FROM (SELECT count (*)
                                                                          FROM public.sharevan_bidding_order_sharevan_bidding_vehicle_rel rel where rel.sharevan_bidding_order_id = %s) t """
        self.env.cr.execute(query_count_bidding_vehicle, (bidding_order_id,))
        result_count_bidding_vehicle = self._cr.fetchall()
        if result_count_bidding_vehicle[0][0]:
            for rec in result_count_bidding_vehicle[0][0]:
                total_bidding_vehicle = rec['count']
                if confirm_count < total_bidding_vehicle - 1:
                    confirm_count += 1
                    http.request.env[Constants.SHAREVAN_BIDDING_ORDER]. \
                        browse(int(bidding_order_id)).write(
                        {'confirm_count': confirm_count, 'mobile': True})
                elif confirm_count == total_bidding_vehicle - 1:
                    query_count_cargo_order = """ SELECT json_agg(t) FROM (  SELECT count(*) FROM public.sharevan_bidding_package_sharevan_cargo_rel s where s.sharevan_bidding_package_id = %s) t """
                    self.env.cr.execute(query_count_cargo_order, (bidding_package_id,))
                    result_count_cargo_order = self._cr.fetchall()
                    total_cargo_of_bidding = 0
                    if result_count_cargo_order[0][0]:
                        for rec in result_count_cargo_order[0][0]:
                            print(int(rec['count']))
                            total_cargo_of_bidding = int(rec['count'])

                    query_count_cargo_confirmed_by_driver = """ SELECT json_agg(t) FROM (  SELECT count(*) FROM sharevan_cargo_bidding_order_vehicle order_vehicle  where order_vehicle.bidding_order_id = %s and order_vehicle.status = '1') t """
                    self.env.cr.execute(query_count_cargo_confirmed_by_driver,
                                        (bidding_order_id,))
                    result_count_cargo_confirmed_by_driver = self._cr.fetchall()
                    total_cargo_of_bidding_confirmed = 0
                    if result_count_cargo_confirmed_by_driver[0][0]:
                        for rec in result_count_cargo_confirmed_by_driver[0][0]:
                            print(rec['count'])
                            total_cargo_of_bidding_confirmed = int(rec['count'])
                    if total_cargo_of_bidding_confirmed != total_cargo_of_bidding:
                        query_cargo_confirmed_by_driver = """ SELECT json_agg(t) FROM (  SELECT cargo_id FROM sharevan_cargo_bidding_order_vehicle order_vehicle  where order_vehicle.bidding_order_id = %s and order_vehicle.status = '1') t """
                        self.env.cr.execute(query_cargo_confirmed_by_driver,
                                            (bidding_order_id,))
                        result_cargo_confirmed_by_driver = self._cr.fetchall()

                        # Kiểm tra trường hợp các tài xế đều xác nhận số cargo mình chở thành công nhưng vẫn còn sót cargo của đơn chưa được xác nhận
                        # Kiểm tra và lấy ra số lượng các cargo của đơn hàng chưa được tài xế cuối cùng xác nhận và gửi thông báo cho đơn vị bit để xử lý
                        list_cargo_id_confirmed = []
                        list_cargo_id_not_confirm = []

                        for rec in result_cargo_confirmed_by_driver[0][0]:
                            list_cargo_id_confirmed.append(rec['cargo_id'])
                        for re in list_cargo_in_package:
                            check_cargo_confirmed = False
                            for conf in list_cargo_id_confirmed:
                                if re == conf:
                                    check_cargo_confirmed = True
                            if check_cargo_confirmed == False:
                                list_cargo_id_not_confirm.append(re)
                        print(list_cargo_id_not_confirm)
                        if list_cargo_id_not_confirm:
                            bidding_company_user = self.env['res.users'].search(
                                [('partner_id', '=', bidded_user_id)])
                            val_send_to_company = {
                                'user_id': [bidding_company_user.id],
                                'title': 'Systems notification',
                                'content': 'List cargo do not confirm',
                                'click_action': ClickActionType.bidding_company.value,
                                'message_type': MessageType.warning.value,
                                'type': NotificationType.BiddingOrder.value,
                                'object_status': BiddingStatus.NotConfirm.value,
                                'item_id': bidding_order_id,
                            }
                            self.send_notification_confirm_cargos(val_send_to_company)
                            val_send_to_driver = {
                                'user_id': [res_user_id],
                                'title': 'Systems notification',
                                'content': 'List cargo do not confirm',
                                'click_action': ClickActionType.driver_vehicle.value,
                                'message_type': MessageType.warning.value,
                                'type': NotificationType.BiddingOrder.value,
                                'object_status': BiddingStatus.NotConfirm.value,
                                'item_id': bidding_order_id,
                            }
                            self.send_notification_confirm_cargos(val_send_to_driver)

    def send_notification_confirm_cargos(self, val):
        try:
            http.request.env['sharevan.notification.user.rel'].create(val)
        except:
            logger.warn(
                "Something wrong when send message to user!",
                'sharevan.notification.user.rel', self.id,
                exc_info=True)

    def get_bidding_order_detail_by_id(self, bidding_order_id):

        bidding_order_arr = []

        if bidding_order_id:
            query_get_bidding_vehicle_information = """  
                SELECT json_agg(t) FROM (  
                    select bidding_vehicle.id,bidding_vehicle.lisence_plate,
                        bidding_vehicle.driver_phone_number from sharevan_bidding_vehicle bidding_vehicle
                   where bidding_vehicle.res_user_id = %s ) t """
            res_user_id = http.request.env.uid
            self.env.cr.execute(query_get_bidding_vehicle_information,
                                (res_user_id,))
            get_bidding_vehicle_information = self._cr.fetchall()
            if get_bidding_vehicle_information[0][0]:
                bidding_vehicle_id = get_bidding_vehicle_information[0][0][0]['id']
                params = []
                currency_name = ''
                query_get_currency_by_company = """ SELECT json_agg(t)
                                        FROM (  select cur.name from res_company c join res_currency cur  on cur.id = c.currency_id where c.id = %s ) t """
                # params_currency.append()
                self.env.cr.execute(query_get_currency_by_company,
                                    (http.request.env.company.id,))
                result_get_currency_by_company = self._cr.fetchall()
                if result_get_currency_by_company[0][0]:
                    currency_name = result_get_currency_by_company[0][0][0]['name']
                query_get_bidding_order_json = """ 
                    SELECT json_agg(t) FROM ( 
                         SELECT  distinct bidding_order.id,
                             bidding_order.company_id,
                             bidding_order.bidding_order_number,
                             bidding_order.from_depot_id,
                             bidding_order.to_depot_id,
                             bidding_order.total_weight,
                             bidding_order.total_cargo,
                             bidding_order.price,
                             bidding_order.distance,
                             bidding_order.type,
                             bidding_order.status,
                             bidding_order.note,
                             bidding_order.bidding_order_receive_id,
                             bidding_order.bidding_order_return_id,
                             TO_CHAR(bidding_order.create_date,'YYYY-MM-DD HH24:MI:SS') create_date,
                             TO_CHAR(bidding_order.write_date,'YYYY-MM-DD HH24:MI:SS') write_date,
                             bidding_order.bidding_package_id,
                             TO_CHAR(bidding_order.from_receive_time,'YYYY-MM-DD HH24:MI:SS') from_receive_time,
                             TO_CHAR(bidding_order.to_receive_time,'YYYY-MM-DD HH24:MI:SS') to_receive_time,
                             TO_CHAR(bidding_order.from_return_time,'YYYY-MM-DD HH24:MI:SS') from_return_time,
                             TO_CHAR(bidding_order.to_return_time,'YYYY-MM-DD HH24:MI:SS')  to_return_time,
                             TO_CHAR(bidding_order.max_confirm_time,'YYYY-MM-DD HH24:MI:SS') max_confirm_time
                         FROM public.sharevan_bidding_order bidding_order 
                            where  bidding_order.id = %s ) t"""

                params.append(bidding_order_id)

                self.env.cr.execute(query_get_bidding_order_json,
                                    (params))
                result_get_bidding_order = self._cr.fetchall()

                if result_get_bidding_order[0][0]:
                    for bidding_order in result_get_bidding_order[0][0]:
                        # if bidding_order[type] != BiddingStatus.Received.value:
                        #     raise ValidationError(_('Admin has not approved the bidding order!'))
                        # Lấy tất cả các cargo của đơn
                        query_get_cargo_info = """ 
                        
                            SELECT sharevan_cargo.id, sharevan_cargo.cargo_number, sharevan_cargo.from_depot_id, 
                                sharevan_cargo.to_depot_id, sharevan_cargo.distance, sharevan_cargo.size_id, 
                                sharevan_cargo.weight, sharevan_cargo.description, sharevan_cargo.price, 
                                sharevan_cargo.from_latitude, sharevan_cargo.to_latitude, sharevan_cargo.bidding_package_id, 
                                sharevan_cargo.from_longitude, sharevan_cargo.to_longitude,size_standard,
                                size_standard.length, size_standard.width, size_standard.height, 
                                size_standard.type, size_standard.from_weight, size_standard.to_weight, 
                                size_standard.price_id, size_standard.price,
                                size_standard.size_standard_seq, size_standard.long_unit, size_standard.weight_unit
                            FROM public.sharevan_cargo 
                                join sharevan_size_standard  size_standard on size_standard.id = sharevan_cargo.size_id
                            join sharevan_bidding_package_sharevan_cargo_rel rel 
                                    on rel.sharevan_cargo_id=sharevan_cargo.id
                                where rel.sharevan_bidding_package_id = %s  """
                        self.env.cr.execute(query_get_cargo_info, (bidding_order['bidding_package_id'],))
                        result_query_get_cargo_info = self._cr.dictfetchall()

                        # cargo_ids danh sách cargo_id thuộc 1 bidding order
                        cargo_ids = result_query_get_cargo_info

                        query_get_size_standard = """ 
                        SELECT json_agg(t) FROM (  
                            select distinct  id, length, width, height,  type,
                                from_weight, to_weight, price_id, price, size_standard_seq, cargo_price_ids, long_unit, weight_unit 
                            from sharevan_size_standard size_stand
                                where size_stand.id in (select cargo.size_id from sharevan_cargo cargo where cargo.id  ::integer in ( """

                        if cargo_ids:
                            for cargo_id in cargo_ids:
                                query_get_size_standard += str(cargo_id['id']) + ","
                            query_get_size_standard = query_get_size_standard[:-1]
                            query_get_size_standard += "))) t"

                        self.env.cr.execute(query_get_size_standard, (cargo_ids))
                        result_get_size_standard = self._cr.fetchall()
                        size_standard_arr_order = []
                        if result_get_size_standard[0][0]:
                            for rec in result_get_size_standard[0][0]:
                                cargo_info_dtl = []
                                # Lấy cargo theo từng size
                                query_get_cargo_info_new = """ 
                                    SELECT json_agg(t) FROM ( 
                                        SELECT sharevan_cargo.id, sharevan_cargo.cargo_number, sharevan_cargo.from_depot_id, sharevan_cargo.to_depot_id, 
                                            sharevan_cargo.distance, sharevan_cargo.size_id, sharevan_cargo.weight, sharevan_cargo.description, 
                                            sharevan_cargo.price, sharevan_cargo.from_latitude, sharevan_cargo.to_latitude,
                                            sharevan_cargo.bidding_package_id,  sharevan_cargo.from_longitude, sharevan_cargo.to_longitude,
                                            size_standard,sharevan_cargo.code,size_standard.length, size_standard.width, 
                                            size_standard.height, size_standard.type, size_standard.from_weight, size_standard.to_weight,
                                            size_standard.price_id, size_standard.price, size_standard.size_standard_seq, size_standard.long_unit, 
                                            size_standard.weight_unit
                                        FROM public.sharevan_cargo 
                                            join sharevan_size_standard  size_standard on size_standard.id = sharevan_cargo.size_id
                                        where sharevan_cargo.bidding_package_id = %s and sharevan_cargo.size_id = %s ) t """
                                self.env.cr.execute(query_get_cargo_info_new,
                                                    (bidding_order['bidding_package_id'], rec['id'],))
                                result_query_get_cargo_info_new = self._cr.fetchall()
                                # danh sách cargo_id thuộc 1 size_standard
                                cargo_id_arr = []
                                if result_query_get_cargo_info_new[0][0]:
                                    for cargo in result_query_get_cargo_info_new[0][0]:
                                        cargo_id_arr.append(cargo['id'])
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
                                            'size_standard': "",
                                            'qr_code': cargo['cargo_number']

                                        }
                                        cargo_info_dtl.append(data)
                                query_count_cargo_map_with_size_standard = """ SELECT json_agg(t) FROM ( select count(*) from sharevan_cargo cargo where cargo.id  ::integer in ( """
                                for cargo_id in cargo_id_arr:
                                    query_count_cargo_map_with_size_standard += str(cargo_id) + ","
                                query_count_cargo_map_with_size_standard = query_count_cargo_map_with_size_standard[
                                                                           :-1]
                                query_count_cargo_map_with_size_standard += """ ) and cargo.size_id = %s  """
                                query_count_cargo_map_with_size_standard += " ) t"
                                self.env.cr.execute(query_count_cargo_map_with_size_standard, (rec['id'],))
                                result_count_cargo_map_with_size_standard = self._cr.fetchall()

                                query_caculate_cargo_total_weight = """ SELECT json_agg(t) FROM ( select sum(weight) from sharevan_cargo cargo where cargo.id  ::integer in ( """
                                for cargo_id in cargo_id_arr:
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
                                        'cargo_quantity': result_count_cargo_map_with_size_standard[0][0][0][
                                            'count'],
                                        'total_weight': result_query_caculate_cargo_total_weight[0][0][0]['sum'],
                                        'cargos': cargo_info_dtl

                                    }
                                    size_standard_arr_order.append(size_standard_data)
                        bidding_vehicle_arr = []
                        bidding_order_receive = {}
                        bidding_order_return = {}

                        query_get_bidding_vehicle = """ SELECT json_agg(t) FROM (SELECT id, code, lisence_plate, driver_phone_number, driver_name,
                                                      TO_CHAR(expiry_time,'YYYY-MM-DD HH24:MI:SS') expiry_time, company_id, status, description,
                                                     id_card, res_partner_id, tonnage, vehicle_type, weight_unit, bidding_vehicle_seq
                                                     FROM public.sharevan_bidding_vehicle  bidding_vehicle where bidding_vehicle.id = %s ) t """
                        self.env.cr.execute(query_get_bidding_vehicle, (bidding_vehicle_id,))
                        result_get_bidding_vehicle = self._cr.fetchall()
                        params = []
                        for rec in result_get_bidding_vehicle[0][0]:
                            query_get_bidding_order_receive = """ SELECT json_agg(t) FROM ( SELECT id, bidding_order_id,  TO_CHAR(from_expected_time,'YYYY-MM-DD HH24:MI:SS') from_expected_time, TO_CHAR(to_expected_time,'YYYY-MM-DD HH24:MI:SS') to_expected_time, depot_id, TO_CHAR(actual_time,'YYYY-MM-DD HH24:MI:SS') actual_time, stock_man_id, status, description, TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS') create_date, bidding_order_vehicle_id
                                                                                                                                  FROM public.sharevan_bidding_order_receive bidding_order_receive where bidding_order_receive.bidding_order_id = %s   and bidding_order_receive.bidding_vehicle_id = %s  ) t """
                            params.append(bidding_order['id'])
                            params.append(rec['id'])
                            self.env.cr.execute(query_get_bidding_order_receive, (params))
                            result_get_bidding_order_receive = self._cr.fetchall()
                            if result_get_bidding_order_receive[0][0]:
                                bidding_order_receive = result_get_bidding_order_receive[0][0][0]

                            query_get_bidding_order_return = """ SELECT json_agg(t) FROM ( SELECT id, bidding_order_id, TO_CHAR(from_expected_time,'YYYY-MM-DD HH24:MI:SS') from_expected_time,  TO_CHAR(to_expected_time,'YYYY-MM-DD HH24:MI:SS') to_expected_time,TO_CHAR(actual_time,'YYYY-MM-DD HH24:MI:SS') actual_time, depot_id,TO_CHAR(actual_time,'YYYY-MM-DD HH24:MI:SS')  , stock_man_id, status, description,TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS')   create_date, bidding_order_vehicle_id

                                                                                                                            FROM public.sharevan_bidding_order_return  bidding_order_return where bidding_order_return.bidding_order_id = %s  and bidding_order_return.bidding_vehicle_id = %s )  t """
                            self.env.cr.execute(query_get_bidding_order_return, (params))
                            result_get_bidding_order_return = self._cr.fetchall()
                            if result_get_bidding_order_return[0][0]:
                                bidding_order_return = result_get_bidding_order_return[0][0][0]

                        bidding_vehicle_param = []
                        query_get_cargo_bidding_order_vehicle = """ SELECT distinct cargo_id FROM public.sharevan_cargo_bidding_order_vehicle s 
                                                                   where s.status = '1' and s.bidding_order_id = """
                        query_get_cargo_bidding_order_vehicle += str(bidding_order['id'])
                        query_get_cargo_bidding_order_vehicle += """ and s.bidding_vehicle_id = """
                        query_get_cargo_bidding_order_vehicle += str(bidding_vehicle_id)
                        self.env.cr.execute(query_get_cargo_bidding_order_vehicle, ())
                        result_get_cargo_bidding_order_vehicle = self._cr.dictfetchall()
                        list_cargo_id = []
                        list_qr_code = []
                        size_standard_arr = []
                        if result_get_cargo_bidding_order_vehicle:
                            for id in result_get_cargo_bidding_order_vehicle:
                                cargo = self.env[Constants.SHAREVAN_CARGO].search([('id', '=', id['cargo_id'])])
                                list_qr_code.append(cargo.cargo_number)
                                list_cargo_id.append(id['cargo_id'])
                            query_get_size_standard = """ 
                                SELECT json_agg(t) FROM (  
                                    select distinct  id, length, width, height, type,from_weight, to_weight, 
                                        price_id, price, size_standard_seq, cargo_price_ids, long_unit, weight_unit 
                                    from sharevan_size_standard size_stand
                                        where size_stand.id in (select cargo.size_id from sharevan_cargo cargo where cargo.id  ::integer in ( """

                            if list_cargo_id:
                                for cargo_id in list_cargo_id:
                                    query_get_size_standard += str(cargo_id) + ","
                                query_get_size_standard = query_get_size_standard[:-1]
                                query_get_size_standard += "))) t"

                            self.env.cr.execute(query_get_size_standard, (list_cargo_id))
                            result_get_size_standard = self._cr.fetchall()
                            if result_get_size_standard[0][0]:
                                for rec in result_get_size_standard[0][0]:
                                    query_count_cargo_map_with_size_standard = """ SELECT json_agg(t) FROM ( select count(*) from sharevan_cargo cargo where cargo.id  ::integer in ( """
                                    for cargo_id in list_cargo_id:
                                        query_count_cargo_map_with_size_standard += str(
                                            cargo_id) + ","
                                    query_count_cargo_map_with_size_standard = query_count_cargo_map_with_size_standard[
                                                                               :-1]
                                    query_count_cargo_map_with_size_standard += """ ) and cargo.size_id = %s  """
                                    query_count_cargo_map_with_size_standard += " ) t"
                                    self.env.cr.execute(query_count_cargo_map_with_size_standard,
                                                        (rec['id'],))
                                    result_count_cargo_map_with_size_standard = self._cr.fetchall()

                                    query_caculate_cargo_total_weight = """ SELECT json_agg(t) FROM ( select sum(weight) from sharevan_cargo cargo where cargo.id  ::integer in ( """
                                    for cargo_id in list_cargo_id:
                                        query_caculate_cargo_total_weight += str(cargo_id) + ","
                                    query_caculate_cargo_total_weight = query_caculate_cargo_total_weight[
                                                                        :-1]
                                    query_caculate_cargo_total_weight += """ ) and cargo.size_id = %s  """
                                    query_caculate_cargo_total_weight += " ) t"
                                    self.env.cr.execute(query_caculate_cargo_total_weight,
                                                        (rec['id'],))
                                    result_query_caculate_cargo_total_weight = self._cr.fetchall()

                                    cargo_vehicle = []
                                    car_vehicle_id = []

                                    query_get_cargo_vehicle_infor = """ 
                                        SELECT json_agg(t) FROM ( 
                                            SELECT sharevan_cargo.id, sharevan_cargo.cargo_number, sharevan_cargo.from_depot_id, sharevan_cargo.to_depot_id, 
                                                sharevan_cargo.distance, sharevan_cargo.size_id, sharevan_cargo.weight, sharevan_cargo.description, 
                                                sharevan_cargo.price, sharevan_cargo.from_latitude, sharevan_cargo.to_latitude, sharevan_cargo.bidding_package_id, 
                                                sharevan_cargo.from_longitude, sharevan_cargo.to_longitude,size_standard,sharevan_cargo.code,
                                                size_standard.length, size_standard.width, size_standard.height
                                                ,size_standard.type, size_standard.from_weight, size_standard.to_weight, size_standard.price_id, size_standard.price,
                                                size_standard.size_standard_seq, size_standard.long_unit, size_standard.weight_unit
                                            FROM public.sharevan_cargo 
                                                join sharevan_size_standard  size_standard on size_standard.id = sharevan_cargo.size_id
                                            where sharevan_cargo.id ::integer in ( """
                                    for cargo_id in list_cargo_id:
                                        query_get_cargo_vehicle_infor += str(cargo_id) + ","
                                    query_get_cargo_vehicle_infor = query_get_cargo_vehicle_infor[
                                                                    :-1]
                                    query_get_cargo_vehicle_infor += """ ) and sharevan_cargo.size_id = %s  """
                                    query_get_cargo_vehicle_infor += " ) t"
                                    self.env.cr.execute(query_get_cargo_vehicle_infor,
                                                        (rec['id'],))
                                    result_query_get_cargo_vehicle_infor = self._cr.fetchall()

                                    if result_query_get_cargo_vehicle_infor[0][0]:
                                        for cargo in result_query_get_cargo_vehicle_infor[0][0]:
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
                                                'size_standard': "",
                                                'qr_code': cargo['cargo_number']

                                            }
                                            cargo_vehicle.append(data)

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
                                            'cargos': cargo_vehicle,
                                            'cargo_quantity':
                                                result_count_cargo_map_with_size_standard[0][0][0][
                                                    'count'],
                                            'total_weight':
                                                result_query_caculate_cargo_total_weight[0][0][0]['sum']

                                        }
                                        size_standard_arr.append(size_standard_data)

                        bidding_vehicle_json = {
                            'id': result_get_bidding_vehicle[0][0][0]['id'],
                            'code': result_get_bidding_vehicle[0][0][0]['code'],
                            'lisence_plate': result_get_bidding_vehicle[0][0][0]['lisence_plate'],
                            'driver_phone_number': result_get_bidding_vehicle[0][0][0][
                                'driver_phone_number'],
                            'driver_name': result_get_bidding_vehicle[0][0][0]['driver_name'],
                            'expiry_time': result_get_bidding_vehicle[0][0][0]['expiry_time'],
                            'company_id': result_get_bidding_vehicle[0][0][0]['company_id'],
                            'status': result_get_bidding_vehicle[0][0][0]['status'],
                            'description': result_get_bidding_vehicle[0][0][0]['description'],
                            'vehicle_type': result_get_bidding_vehicle[0][0][0]['vehicle_type'],
                            'weight_unit': result_get_bidding_vehicle[0][0][0]['weight_unit'],
                            'cargo_types': size_standard_arr,
                            'bidding_order_receive': bidding_order_receive,
                            'bidding_order_return': bidding_order_return
                        }

                        bidding_vehicle_arr.append(bidding_vehicle_json)

                        query_get_from_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.latitude,depot.longitude,depot.phone,depot.depot_code,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                                                                                               where depot.id =  %s ) t"""
                        self.env.cr.execute(query_get_from_depot, (bidding_order['from_depot_id'],))
                        result_get_from_depot = self._cr.fetchall()

                        array_length = len(result_get_from_depot)
                        if array_length > 0:
                            if result_get_from_depot[0][0]:
                                get_from_depot = result_get_from_depot[0][0][0]

                        query_get_to_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.phone,depot.latitude,depot.longitude,depot.depot_code,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                                                                                                                 where     depot.id = %s ) t"""
                        self.env.cr.execute(query_get_to_depot, (bidding_order['to_depot_id'],))
                        result_get_to_depot = self._cr.fetchall()
                        get_to_depot = []
                        array_length = len(result_get_to_depot)
                        if array_length > 0:
                            if result_get_to_depot[0][0]:
                                get_to_depot = result_get_to_depot[0][0][0]

                        data = {
                            'id': bidding_order['id'],
                            'company_id': bidding_order['company_id'],
                            'bidding_order_number': bidding_order['bidding_order_number'],
                            'from_depot': get_from_depot,
                            'to_depot': get_to_depot,
                            'total_weight': bidding_order['total_weight'],
                            'total_cargo': bidding_order['total_cargo'],
                            'price': bidding_order['price'],
                            'currency_name': currency_name,
                            'distance': bidding_order['distance'],
                            'type': bidding_order['type'],
                            'status': bidding_order['status'],
                            'note': bidding_order['note'],
                            'create_date': bidding_order['create_date'],
                            'write_date': bidding_order['write_date'],
                            'bidding_package_id': bidding_order['bidding_package_id'],
                            'from_receive_time': bidding_order['from_receive_time'],
                            'to_receive_time': bidding_order['to_receive_time'],
                            'from_return_time': bidding_order['from_return_time'],
                            'to_return_time': bidding_order['to_return_time'],
                            'max_confirm_time': bidding_order['max_confirm_time'],
                            'bidding_vehicles': bidding_vehicle_json,
                            'cargo_type': size_standard_arr_order
                        }

                        bidding_order_arr.append(data)
                else:
                    return {
                        'records': []
                    }
                records = {
                    'length': len(result_get_bidding_order[0][0]),
                    'records': bidding_order_arr
                }
                simplejson.dumps(records, indent=4, sort_keys=True, default=str)
                return records
            else:
                raise ValidationError(_('Bidding vehicle does not existed!'))
        else:
            raise ValidationError(_('bidding_order_id can not null'))

    def get_company_review(self):
        user = self.env['res.users'].search([('id', '=', self.env.uid)])
        if user:

            query_get_company_review = """ SELECT json_agg(t) FROM ( SELECT id, name, partner_id, currency_id, sequence, create_date, parent_id, report_header, report_footer, logo_web,
                                            account_no, street, street2, zip, city, state_id, country_id, email, phone, website, vat, company_registry,
                                            paperformat_id, external_report_layout_id, base_onboarding_company_state, font, primary_color, secondary_color,
                                             city_name, district, ward, latitude, longitude, status, company_type, point, award_company_id, code
                                                FROM public.res_company  res  where 1=1 and res.id = %s ) t """

            if user.company_id:
                company_id = user.company_id.id
                self.env.cr.execute(query_get_company_review, (company_id,))
                result_get_company_review = self._cr.fetchall()
                if result_get_company_review[0][0]:
                    records = {
                        'length': len(result_get_company_review[0][0]),
                        'records': result_get_company_review[0][0]
                    }
                    simplejson.dumps(records, indent=4, sort_keys=True, default=str)
                    return records
                return {
                    'records': []
                }
            else:
                raise ValidationError(_('Company does not existed!'))

        else:
            raise ValidationError(_('User does not existed!'))

    def get_all_bidding_order_rating(self, limit, offset):
        user = self.env['res.users'].search([('id', '=', self.env.uid)])
        params = []
        jsonRe = []
        order_rate_avg = 0.0
        rating_count = 0
        limit = 10
        params = []
        total = 0
        if user:
            company_id = user.company_id.id
            query_get_bidding_order_json = """ SELECT json_agg(t) FROM (  """
            query_get_bidding_order_nomal = """ SELECT  distinct bidding_order.id, bidding_order.company_id, bidding_order.bidding_order_number, bidding_order.from_depot_id, bidding_order.to_depot_id, bidding_order.total_weight,
                                             bidding_order.total_cargo, bidding_order.price, bidding_order.distance,   bidding_order.type,   bidding_order.status,  bidding_order.note,  bidding_order.bidding_order_receive_id,   bidding_order.bidding_order_return_id,
                                             TO_CHAR(bidding_order.create_date,'YYYY-MM-DD HH24:MI:SS') create_date, TO_CHAR(bidding_order.write_date,'YYYY-MM-DD HH24:MI:SS') write_date, bidding_order.bidding_package_id,  TO_CHAR(bidding_order.from_receive_time,'YYYY-MM-DD HH24:MI:SS') from_receive_time,
                                             TO_CHAR(bidding_order.to_receive_time,'YYYY-MM-DD HH24:MI:SS') to_receive_time,   TO_CHAR(bidding_order.from_return_time,'YYYY-MM-DD HH24:MI:SS') from_return_time,  TO_CHAR(bidding_order.to_return_time,'YYYY-MM-DD HH24:MI:SS')  to_return_time, TO_CHAR(bidding_order.max_confirm_time,'YYYY-MM-DD HH24:MI:SS') max_confirm_time
                                             FROM public.sharevan_bidding_order bidding_order
                                             LEFT JOIN sharevan_bidding_order_sharevan_bidding_vehicle_rel rel on bidding_order.id = rel.sharevan_bidding_order_id
                                             LEFT JOIN sharevan_bidding_vehicle bidding_vehicle on bidding_vehicle.id = rel.sharevan_bidding_vehicle_id
                                             where  bidding_order.company_id = %s and bidding_order.status = '2' """
            query_get_bidding_order_json += query_get_bidding_order_nomal

            query_count_bidding_order_info = """SELECT count(*) from ( """
            query_count_bidding_order_info += query_get_bidding_order_nomal
            query_count_bidding_order_info += """ ) bidding_order """
            self.env.cr.execute(query_count_bidding_order_info, (company_id,))
            result_count_cargo_info = self._cr.fetchall()
            if result_count_cargo_info[0][0]:
                total = result_count_cargo_info[0][0]
            if offset:
                offset = offset * 10
                query_get_bidding_order_json += """ offset %s  and limit = 10 """ % (offset)
                query_get_bidding_order_json += """ ) t """

            else:
                query_get_bidding_order_json += """ offset 0  limit  10 """
                query_get_bidding_order_json += """ ) t """

            self.env.cr.execute(query_get_bidding_order_json, (str(company_id),))
            result_get_bidding_order = self._cr.fetchall()

            if result_get_bidding_order[0][0]:
                for bidding_ord in result_get_bidding_order[0][0]:
                    rating_badges = []
                    query_get_bidding_package_infor = """ SELECT id, bidding_order_id, bidding_package_number, status, TO_CHAR(confirm_time,'YYYY-MM-DD HH24:MI:SS') confirm_time , TO_CHAR(release_time,'YYYY-MM-DD HH24:MI:SS') release_time, TO_CHAR(bidding_time,'YYYY-MM-DD HH24:MI:SS') bidding_time, max_count,
                                                       from_depot_id, to_depot_id, total_weight,
                                                       distance, from_latitude, from_longitude, to_latitude, to_longitude, TO_CHAR(from_receive_time,'YYYY-MM-DD HH24:MI:SS') from_receive_time, TO_CHAR(to_receive_time,'YYYY-MM-DD HH24:MI:SS') to_receive_time,
                                                       TO_CHAR(from_return_time,'YYYY-MM-DD HH24:MI:SS') from_return_time,  TO_CHAR(to_return_time,'YYYY-MM-DD HH24:MI:SS') to_return_time, price_origin, price,  TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS') create_date,
                                                       countdown_time,  price_time_change, price_level_change
                                                       FROM public.sharevan_bidding_package bidding_package where 1=1 
                                                       and bidding_package.id = %s """
                    print(result_get_bidding_order[0][0][0]['bidding_package_id'])
                    self.env.cr.execute(query_get_bidding_package_infor,
                                        (bidding_ord['bidding_package_id'],))

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

                            query_get_cargo_info = """ 
                            SELECT json_agg(t) FROM ( 
                                SELECT sharevan_cargo.id, sharevan_cargo.cargo_number, sharevan_cargo.from_depot_id, sharevan_cargo.to_depot_id, 
                                    sharevan_cargo.distance, sharevan_cargo.size_id,sharevan_cargo.weight, sharevan_cargo.description, 
                                    sharevan_cargo.price, sharevan_cargo.from_latitude, sharevan_cargo.to_latitude, sharevan_cargo.bidding_package_id, 
                                    sharevan_cargo.from_longitude, sharevan_cargo.to_longitude,size_standard,
                                    size_standard.length, size_standard.width, size_standard.height, size_standard.type, size_standard.from_weight, 
                                    size_standard.to_weight, size_standard.price_id, size_standard.price,
                                    size_standard.size_standard_seq, size_standard.long_unit, size_standard.weight_unit
                                FROM public.sharevan_cargo 
                                    join sharevan_size_standard  size_standard on size_standard.id = sharevan_cargo.size_id
                                where sharevan_cargo.bidding_package_id = %s ) t """
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
                                    select distinct  id, length, width, height, type, from_weight, to_weight, price_id, price,
                                        size_standard_seq, cargo_price_ids, long_unit, weight_unit 
                                    from sharevan_size_standard size_stand
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
                                    query_count_cargo_map_with_size_standard = query_count_cargo_map_with_size_standard[
                                                                               :-1]
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
                                            'cargo_quantity': result_count_cargo_map_with_size_standard[0][0][0][
                                                'count'],
                                            'total_weight': result_query_caculate_cargo_total_weight[0][0][0]['sum']

                                        }
                                        size_standard_arr.append(size_standard_data)
                    if bidding_ord:
                        bidding_order = bidding_ord
                        bidding_package_id = bidding_order['bidding_package_id']
                        bidding_order_json = {}

                        if bidding_order:
                            bidding_vehicle_arr = []
                            query_get_bidding_vehicle_order_rel = """ SELECT json_agg(t) FROM ( SELECT sharevan_bidding_order_id, sharevan_bidding_vehicle_id
                                                                     FROM public.sharevan_bidding_order_sharevan_bidding_vehicle_rel rel 
                                                                     where rel.sharevan_bidding_order_id = %s ) t """
                            self.env.cr.execute(query_get_bidding_vehicle_order_rel, (bidding_order['id'],))
                            result_get_bidding_vehicle_order_rel = self._cr.fetchall()

                            query_get_from_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.latitude,depot.longitude,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                                                                                           where depot.id =  %s ) t"""
                            self.env.cr.execute(query_get_from_depot, (bidding_order['from_depot_id'],))
                            result_get_from_depot = self._cr.fetchall()

                            array_length = len(result_get_from_depot)
                            if array_length > 0:
                                if result_get_from_depot[0][0]:
                                    get_from_depot = result_get_from_depot[0][0][0]

                            query_get_to_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                                                                                                             where     depot.id = %s ) t"""
                            self.env.cr.execute(query_get_to_depot, (bidding_order['to_depot_id'],))
                            result_get_to_depot = self._cr.fetchall()
                            get_to_depot = []
                            array_length = len(result_get_to_depot)
                            if array_length > 0:
                                if result_get_to_depot[0][0]:
                                    get_to_depot = result_get_to_depot[0][0][0]
                            if result_get_bidding_vehicle_order_rel[0][0]:
                                for rec in result_get_bidding_vehicle_order_rel[0][0]:
                                    query_get_bidding_vehicle = """ SELECT json_agg(t) FROM (SELECT bidding_vehicle.id, bidding_vehicle.code, bidding_vehicle.lisence_plate, bidding_vehicle.driver_phone_number, bidding_vehicle.driver_name,
                                                                    TO_CHAR(bidding_vehicle.expiry_time,'YYYY-MM-DD HH24:MI:SS') expiry_time, bidding_vehicle.company_id, bidding_vehicle.status, bidding_vehicle.description,
                                                                   bidding_vehicle.id_card, bidding_vehicle.res_partner_id, bidding_vehicle.tonnage, bidding_vehicle.vehicle_type, bidding_vehicle.weight_unit, bidding_vehicle.bidding_vehicle_seq, ia.store_fname
                                                                   FROM public.sharevan_bidding_vehicle  bidding_vehicle
                                                                   left join public.ir_attachment ia on bidding_vehicle.id = ia.res_id and ia.res_model = 'sharevan.bidding.vehicle'   and ia.res_field = 'image_128' and ia.status = 'running'
                                                                   where bidding_vehicle.id = %s ) t """
                                    bidding_vehicle_id = rec['sharevan_bidding_vehicle_id']
                                    self.env.cr.execute(query_get_bidding_vehicle, (bidding_vehicle_id,))
                                    result_get_bidding_vehicle = self._cr.fetchall()

                                    bidding_vehicle_param = []
                                    query_get_cargo_bidding_order_vehicle = """ SELECT distinct cargo_id FROM public.sharevan_cargo_bidding_order_vehicle s 
                                                                                 where s.bidding_order_id = """
                                    query_get_cargo_bidding_order_vehicle += str(bidding_order['id'])
                                    query_get_cargo_bidding_order_vehicle += """ and s.bidding_vehicle_id = """
                                    query_get_cargo_bidding_order_vehicle += str(bidding_vehicle_id)
                                    query_get_cargo_bidding_order_vehicle += """ and s.status = '1' """
                                    # query_get_cargo_bidding_order_vehicle += CargoBiddingOrderVehicleStatus.running.value
                                    self.env.cr.execute(query_get_cargo_bidding_order_vehicle, ())
                                    result_get_cargo_bidding_order_vehicle = self._cr.fetchall()
                                    list_cargo_id = []
                                    size_standard_arr = []
                                    if result_get_cargo_bidding_order_vehicle:
                                        for id in result_get_cargo_bidding_order_vehicle:
                                            list_cargo_id.append(id[0])
                                        query_get_size_standard = """ 
                                        SELECT json_agg(t) FROM (  
                                            select distinct  id, length, width, height, type,
                                                from_weight, to_weight, price_id, price, size_standard_seq, cargo_price_ids, long_unit, weight_unit 
                                            from sharevan_size_standard size_stand
                                                where size_stand.id in (select cargo.size_id from sharevan_cargo cargo where cargo.id  ::integer in ( """

                                        if list_cargo_id:
                                            for cargo_id in list_cargo_id:
                                                query_get_size_standard += str(cargo_id) + ","
                                            query_get_size_standard = query_get_size_standard[:-1]
                                            query_get_size_standard += "))) t"

                                        self.env.cr.execute(query_get_size_standard, (list_cargo_id))
                                        result_get_size_standard = self._cr.fetchall()
                                        if result_get_size_standard[0][0]:
                                            for rec in result_get_size_standard[0][0]:
                                                query_count_cargo_map_with_size_standard = """ SELECT json_agg(t) FROM ( select count(*) from sharevan_cargo cargo where cargo.id  ::integer in ( """
                                                for cargo_id in list_cargo_id:
                                                    query_count_cargo_map_with_size_standard += str(cargo_id) + ","
                                                query_count_cargo_map_with_size_standard = query_count_cargo_map_with_size_standard[
                                                                                           :-1]
                                                query_count_cargo_map_with_size_standard += """ ) and cargo.size_id = %s  """
                                                query_count_cargo_map_with_size_standard += " ) t"
                                                self.env.cr.execute(query_count_cargo_map_with_size_standard,
                                                                    (rec['id'],))
                                                result_count_cargo_map_with_size_standard = self._cr.fetchall()

                                                query_caculate_cargo_total_weight = """ SELECT json_agg(t) FROM ( select sum(weight) from sharevan_cargo cargo where cargo.id  ::integer in ( """
                                                for cargo_id in list_cargo_id:
                                                    query_caculate_cargo_total_weight += str(cargo_id) + ","
                                                query_caculate_cargo_total_weight = query_caculate_cargo_total_weight[
                                                                                    :-1]
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
                                                        'cargo_quantity':
                                                            result_count_cargo_map_with_size_standard[0][0][0][
                                                                'count'],
                                                        'total_weight':
                                                            result_query_caculate_cargo_total_weight[0][0][0][
                                                                'sum']

                                                    }
                                                    size_standard_arr.append(size_standard_data)

                                    query_get_rating = """ SELECT json_agg(t) FROM (SELECT id, driver_id, num_rating, employee_id, note,  TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS') create_date , bidding_vehicle_id, bidding_order_id
	                                                        FROM public.sharevan_rating rating where rating.bidding_vehicle_id = %s and rating.bidding_order_id = %s  ) t """
                                    bidding_vehicle_id = result_get_bidding_vehicle[0][0][0]['id']
                                    self.env.cr.execute(query_get_rating, (bidding_vehicle_id, bidding_order['id'],))
                                    result_get_rating = self._cr.fetchall()
                                    rating = {}

                                    if result_get_rating[0][0]:
                                        rating_count += 1
                                        rating = result_get_rating[0][0][0]
                                        order_rate_avg += rating['num_rating']
                                        query_get_rating_badges_driver = """ SELECT json_agg(t) FROM (SELECT id, sharevan_bidding_order_id, sharevan_bidding_vehicle_id, share_van_driver_id, share_van_rating_badges_id,   TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS') create_date  
	                                                                   FROM public.sharevan_bidding_vehicle_rating_badges  badges where badges.sharevan_bidding_vehicle_id = %s and  badges.sharevan_bidding_order_id = %s  ) t """
                                        bidding_vehicle_id = result_get_bidding_vehicle[0][0][0]['id']
                                        self.env.cr.execute(query_get_rating_badges_driver,
                                                            (bidding_vehicle_id, bidding_order['id'],))
                                        result_get_rating_badges_driver = self._cr.fetchall()
                                        if result_get_rating_badges_driver[0][0]:
                                            for rec in result_get_rating_badges_driver[0][0]:

                                                query_get_rating_badges = """ SELECT json_agg(t) FROM (SELECT id, name, code_seq, code, description, status, TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS') create_date
                                                                                      FROM public.sharevan_rating_badges r where r.id = %s ) t """
                                                self.env.cr.execute(query_get_rating_badges,
                                                                    (int(rec['share_van_rating_badges_id']),))
                                                result_get_rating_badges = self._cr.fetchall()
                                                if result_get_rating_badges[0][0]:
                                                    rating_badges.append(result_get_rating_badges[0][0][0])

                                    query_get_image = """ SELECT json_agg(t) FROM (SELECT id, uri_path FROM public.ir_attachment where id in (5971,5972,5973,5977,4970,411) ) t """
                                    self.env.cr.execute(query_get_image, ())
                                    images = []
                                    result_get_image = self._cr.fetchall()
                                    if result_get_image[0][0]:
                                        for image in result_get_image[0][0]:
                                            images.append(image['uri_path'])

                                    rating_data = {
                                        'id': result_get_rating[0][0][0]['id'],
                                        'driver_id': result_get_rating[0][0][0]['driver_id'],
                                        'num_rating': result_get_rating[0][0][0]['num_rating'],
                                        'employee_id': result_get_rating[0][0][0]['employee_id'],
                                        'note': result_get_rating[0][0][0]['note'],
                                        'create_date': result_get_rating[0][0][0]['create_date'],
                                        'bidding_vehicle_id': result_get_rating[0][0][0]['bidding_vehicle_id'],
                                        'bidding_order_id': result_get_rating[0][0][0]['bidding_order_id'],
                                        'rating_badges': rating_badges,
                                        'images': images
                                    }
                                    bidding_vehicle_json = {
                                        'id': result_get_bidding_vehicle[0][0][0]['id'],
                                        'code': result_get_bidding_vehicle[0][0][0]['code'],
                                        'lisence_plate': result_get_bidding_vehicle[0][0][0]['lisence_plate'],
                                        'driver_phone_number': result_get_bidding_vehicle[0][0][0][
                                            'driver_phone_number'],
                                        'driver_name': result_get_bidding_vehicle[0][0][0]['driver_name'],
                                        'expiry_time': result_get_bidding_vehicle[0][0][0]['expiry_time'],
                                        'company_id': result_get_bidding_vehicle[0][0][0]['company_id'],
                                        'status': result_get_bidding_vehicle[0][0][0]['status'],
                                        'description': result_get_bidding_vehicle[0][0][0]['description'],
                                        'vehicle_type': result_get_bidding_vehicle[0][0][0]['vehicle_type'],
                                        'weight_unit': result_get_bidding_vehicle[0][0][0]['weight_unit'],
                                        'store_fname': result_get_bidding_vehicle[0][0][0]['store_fname'],
                                        'cargo_types': size_standard_arr,
                                        'rating': rating_data
                                    }

                                    bidding_vehicle_arr.append(bidding_vehicle_json)

                                order_rate_avg = order_rate_avg / float(rating_count)
                                query_get_from_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                           join sharevan_bidding_package bidding_package on depot.id = %s ) t"""
                                self.env.cr.execute(query_get_from_depot, (re[8],))
                                result_get_from_depot = self._cr.fetchall()

                                array_length = len(result_get_from_depot)
                                if array_length > 0:
                                    if result_get_from_depot[0][0]:
                                        get_from_depot = result_get_from_depot[0][0][0]

                                query_get_to_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                         join sharevan_bidding_package bidding_package on depot.id = %s ) t"""
                                self.env.cr.execute(query_get_to_depot, (re[9],))
                                result_get_to_depot = self._cr.fetchall()
                                get_to_depot = []
                                array_length = len(result_get_to_depot)
                                if array_length > 0:
                                    if result_get_to_depot[0][0]:
                                        get_to_depot = result_get_to_depot[0][0][0]

                                bidding_order_json = {
                                    'id': bidding_order['id'],
                                    'company_id': bidding_order['company_id'],
                                    'bidding_order_number': bidding_order['bidding_order_number'],
                                    'from_depot': get_from_depot,
                                    'to_depot': get_to_depot,
                                    'total_weight': bidding_order['total_weight'],
                                    'total_cargo': bidding_order['total_cargo'],
                                    'price': bidding_order['price'],
                                    'distance': bidding_order['distance'],
                                    'type': bidding_order['type'],
                                    'status': bidding_order['status'],
                                    'note': bidding_order['note'],
                                    'bidding_order_receive_id': bidding_order['bidding_order_receive_id'],
                                    'bidding_order_return_id': bidding_order['bidding_order_return_id'],
                                    'create_date': bidding_order['create_date'],
                                    'write_date': bidding_order['write_date'],
                                    'bidding_package_id': bidding_order['bidding_package_id'],
                                    'from_receive_time': bidding_order['from_receive_time'],
                                    'to_receive_time': bidding_order['to_receive_time'],
                                    'from_return_time': bidding_order['from_return_time'],
                                    'to_return_time': bidding_order['to_return_time'],
                                    'max_confirm_time': bidding_order['max_confirm_time'],
                                    'bidding_vehicles': bidding_vehicle_arr,
                                    'total_cargo': total_cargos['count'],
                                    'order_rate_avg': order_rate_avg

                                }

                                content = {
                                    'id': re[0],
                                    'bidding_package_number': re[2],
                                    'status': re[3],
                                    'confirm_bidding_order_success': re[4],
                                    'release_time': re[5],
                                    'bidding_time': re[6],
                                    'max_count': re[7],
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
                                    'write_date': re[23],
                                    'countdown_time': re[24],

                                    'bidding_order': bidding_order_json
                                }
                                jsonRe.append(content)

        records = {
            'length': len(result_get_bidding_order[0][0]),
            'total': total,
            'records': jsonRe
        }
        simplejson.dumps(records, indent=4, sort_keys=True, default=str)
        return records

    def get_all_bidding_order_rating_v2(self, limit, offset):
        user = self.env['res.users'].search([('id', '=', self.env.uid)])
        params = []
        jsonRe = []

        order_rate_avg = 0.0
        rating_count = 0
        limit = 10
        params = []
        total = 0
        if user:
            company_id = user.company_id.id
            query_get_bidding_order_json = """ SELECT json_agg(t) FROM (  """
            query_get_bidding_order_nomal = """ SELECT  distinct bidding_order.id, bidding_order.company_id, bidding_order.bidding_order_number, bidding_order.from_depot_id, bidding_order.to_depot_id, bidding_order.total_weight,
                                                 bidding_order.total_cargo, bidding_order.price, bidding_order.distance,   bidding_order.type,   bidding_order.status,  bidding_order.note,  bidding_order.bidding_order_receive_id,   bidding_order.bidding_order_return_id,
                                                 TO_CHAR(bidding_order.create_date,'YYYY-MM-DD HH24:MI:SS') create_date, TO_CHAR(bidding_order.write_date,'YYYY-MM-DD HH24:MI:SS') write_date, bidding_order.bidding_package_id,  TO_CHAR(bidding_order.from_receive_time,'YYYY-MM-DD HH24:MI:SS') from_receive_time,
                                                 TO_CHAR(bidding_order.to_receive_time,'YYYY-MM-DD HH24:MI:SS') to_receive_time,   TO_CHAR(bidding_order.from_return_time,'YYYY-MM-DD HH24:MI:SS') from_return_time,  TO_CHAR(bidding_order.to_return_time,'YYYY-MM-DD HH24:MI:SS')  to_return_time, TO_CHAR(bidding_order.max_confirm_time,'YYYY-MM-DD HH24:MI:SS') max_confirm_time
                                                 FROM public.sharevan_bidding_order bidding_order
                                                 LEFT JOIN sharevan_bidding_order_sharevan_bidding_vehicle_rel rel on bidding_order.id = rel.sharevan_bidding_order_id
                                                 LEFT JOIN sharevan_bidding_vehicle bidding_vehicle on bidding_vehicle.id = rel.sharevan_bidding_vehicle_id
                                                 where  bidding_order.company_id = %s and bidding_order.status = '2' """
            query_get_bidding_order_json += query_get_bidding_order_nomal

            query_count_bidding_order_info = """SELECT count(*) from ( """
            query_count_bidding_order_info += query_get_bidding_order_nomal
            query_count_bidding_order_info += """ ) bidding_order """
            self.env.cr.execute(query_count_bidding_order_info, (company_id,))
            result_count_cargo_info = self._cr.fetchall()
            if result_count_cargo_info[0][0]:
                total = result_count_cargo_info[0][0]
            if offset:
                offset = offset * 10
                query_get_bidding_order_json += """ offset %s  and limit = 10 """ % (offset)
                query_get_bidding_order_json += """ ) t """

            else:
                query_get_bidding_order_json += """ offset 0  limit  10 """
                query_get_bidding_order_json += """ ) t """

            self.env.cr.execute(query_get_bidding_order_json, (str(company_id),))
            result_get_bidding_order = self._cr.fetchall()

            if result_get_bidding_order[0][0]:
                for bidding_ord in result_get_bidding_order[0][0]:
                    rating_badges = []
                    query_get_bidding_package_infor = """ SELECT id, bidding_order_id, bidding_package_number, status, TO_CHAR(confirm_time,'YYYY-MM-DD HH24:MI:SS') confirm_time , TO_CHAR(release_time,'YYYY-MM-DD HH24:MI:SS') release_time, TO_CHAR(bidding_time,'YYYY-MM-DD HH24:MI:SS') bidding_time, max_count,
                                                           from_depot_id, to_depot_id, total_weight,
                                                           distance, from_latitude, from_longitude, to_latitude, to_longitude, TO_CHAR(from_receive_time,'YYYY-MM-DD HH24:MI:SS') from_receive_time, TO_CHAR(to_receive_time,'YYYY-MM-DD HH24:MI:SS') to_receive_time,
                                                           TO_CHAR(from_return_time,'YYYY-MM-DD HH24:MI:SS') from_return_time,  TO_CHAR(to_return_time,'YYYY-MM-DD HH24:MI:SS') to_return_time, price_origin, price,  TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS') create_date,
                                                           countdown_time,  price_time_change, price_level_change
                                                           FROM public.sharevan_bidding_package bidding_package where 1=1 
                                                           and bidding_package.id = %s """
                    print(result_get_bidding_order[0][0][0]['bidding_package_id'])
                    self.env.cr.execute(query_get_bidding_package_infor,
                                        (bidding_ord['bidding_package_id'],))

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

                            query_get_cargo_info = """ 
                            SELECT json_agg(t) FROM ( 
                                SELECT sharevan_cargo.id, sharevan_cargo.cargo_number, sharevan_cargo.from_depot_id, sharevan_cargo.to_depot_id, 
                                    sharevan_cargo.distance, sharevan_cargo.size_id,  sharevan_cargo.weight, sharevan_cargo.description, 
                                    sharevan_cargo.price, sharevan_cargo.from_latitude, sharevan_cargo.to_latitude, sharevan_cargo.bidding_package_id, 
                                    sharevan_cargo.from_longitude, sharevan_cargo.to_longitude,size_standard,
                                    size_standard.length, size_standard.width, size_standard.height, 
                                    size_standard.type, size_standard.from_weight, size_standard.to_weight, size_standard.price_id, size_standard.price,
                                    size_standard.size_standard_seq, size_standard.long_unit, size_standard.weight_unit
                                FROM public.sharevan_cargo 
                                    join sharevan_size_standard  size_standard on size_standard.id = sharevan_cargo.size_id
                                where sharevan_cargo.bidding_package_id = %s ) t """
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
                                    select distinct  id, length, width, height, type,from_weight, to_weight, price_id,
                                        price, size_standard_seq, cargo_price_ids, long_unit, weight_unit 
                                    from sharevan_size_standard size_stand
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
                                    query_count_cargo_map_with_size_standard = query_count_cargo_map_with_size_standard[
                                                                               :-1]
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
                                            'cargo_quantity': result_count_cargo_map_with_size_standard[0][0][0][
                                                'count'],
                                            'total_weight': result_query_caculate_cargo_total_weight[0][0][0]['sum']

                                        }
                                        size_standard_arr.append(size_standard_data)
                    if bidding_ord:
                        bidding_order = bidding_ord
                        bidding_package_id = bidding_order['bidding_package_id']
                        bidding_order_json = {}

                        if bidding_order:
                            bidding_vehicle_arr = []
                            query_get_bidding_vehicle_order_rel = """ SELECT json_agg(t) FROM ( SELECT sharevan_bidding_order_id, sharevan_bidding_vehicle_id
                                                                         FROM public.sharevan_bidding_order_sharevan_bidding_vehicle_rel rel 
                                                                         where rel.sharevan_bidding_order_id = %s ) t """
                            self.env.cr.execute(query_get_bidding_vehicle_order_rel, (bidding_order['id'],))
                            result_get_bidding_vehicle_order_rel = self._cr.fetchall()

                            query_get_from_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.latitude,depot.longitude,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                                                                                               where depot.id =  %s ) t"""
                            self.env.cr.execute(query_get_from_depot, (bidding_order['from_depot_id'],))
                            result_get_from_depot = self._cr.fetchall()

                            array_length = len(result_get_from_depot)
                            if array_length > 0:
                                if result_get_from_depot[0][0]:
                                    get_from_depot = result_get_from_depot[0][0][0]

                            query_get_to_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                                                                                                                 where     depot.id = %s ) t"""
                            self.env.cr.execute(query_get_to_depot, (bidding_order['to_depot_id'],))
                            result_get_to_depot = self._cr.fetchall()
                            get_to_depot = []
                            array_length = len(result_get_to_depot)
                            if array_length > 0:
                                if result_get_to_depot[0][0]:
                                    get_to_depot = result_get_to_depot[0][0][0]
                            if result_get_bidding_vehicle_order_rel[0][0]:
                                for rec in result_get_bidding_vehicle_order_rel[0][0]:
                                    query_get_bidding_vehicle = """ SELECT json_agg(t) FROM (SELECT bidding_vehicle.id, bidding_vehicle.code, bidding_vehicle.lisence_plate, bidding_vehicle.driver_phone_number, bidding_vehicle.driver_name,
                                                                        TO_CHAR(bidding_vehicle.expiry_time,'YYYY-MM-DD HH24:MI:SS') expiry_time, bidding_vehicle.company_id, bidding_vehicle.status, bidding_vehicle.description,
                                                                       bidding_vehicle.id_card, bidding_vehicle.res_partner_id, bidding_vehicle.tonnage, bidding_vehicle.vehicle_type, bidding_vehicle.weight_unit, bidding_vehicle.bidding_vehicle_seq, ia.store_fname
                                                                       FROM public.sharevan_bidding_vehicle  bidding_vehicle
                                                                       left join public.ir_attachment ia on bidding_vehicle.id = ia.res_id and ia.res_model = 'sharevan.bidding.vehicle'   and ia.res_field = 'image_128' and ia.status = 'running'
                                                                       where bidding_vehicle.id = %s ) t """
                                    bidding_vehicle_id = rec['sharevan_bidding_vehicle_id']
                                    self.env.cr.execute(query_get_bidding_vehicle, (bidding_vehicle_id,))
                                    result_get_bidding_vehicle = self._cr.fetchall()

                                    bidding_vehicle_param = []
                                    query_get_cargo_bidding_order_vehicle = """ SELECT distinct cargo_id FROM public.sharevan_cargo_bidding_order_vehicle s 
                                                                                     where s.bidding_order_id = """
                                    query_get_cargo_bidding_order_vehicle += str(bidding_order['id'])
                                    query_get_cargo_bidding_order_vehicle += """ and s.bidding_vehicle_id = """
                                    query_get_cargo_bidding_order_vehicle += str(bidding_vehicle_id)
                                    query_get_cargo_bidding_order_vehicle += """ and s.status = '1' """
                                    # query_get_cargo_bidding_order_vehicle += CargoBiddingOrderVehicleStatus.running.value
                                    self.env.cr.execute(query_get_cargo_bidding_order_vehicle, ())
                                    result_get_cargo_bidding_order_vehicle = self._cr.fetchall()
                                    list_cargo_id = []
                                    size_standard_arr = []
                                    if result_get_cargo_bidding_order_vehicle:
                                        for id in result_get_cargo_bidding_order_vehicle:
                                            list_cargo_id.append(id[0])
                                        query_get_size_standard = """ 
                                        SELECT json_agg(t) FROM (  
                                            select distinct  id, length, width, height, type,
                                                from_weight, to_weight, price_id, price, size_standard_seq, cargo_price_ids, long_unit, weight_unit 
                                            from sharevan_size_standard size_stand
                                                where size_stand.id in (select cargo.size_id from sharevan_cargo cargo where cargo.id  ::integer in ( """

                                        if list_cargo_id:
                                            for cargo_id in list_cargo_id:
                                                query_get_size_standard += str(cargo_id) + ","
                                            query_get_size_standard = query_get_size_standard[:-1]
                                            query_get_size_standard += "))) t"

                                        self.env.cr.execute(query_get_size_standard, (list_cargo_id))
                                        result_get_size_standard = self._cr.fetchall()
                                        if result_get_size_standard[0][0]:
                                            for rec in result_get_size_standard[0][0]:
                                                query_count_cargo_map_with_size_standard = """ SELECT json_agg(t) FROM ( select count(*) from sharevan_cargo cargo where cargo.id  ::integer in ( """
                                                for cargo_id in list_cargo_id:
                                                    query_count_cargo_map_with_size_standard += str(cargo_id) + ","
                                                query_count_cargo_map_with_size_standard = query_count_cargo_map_with_size_standard[
                                                                                           :-1]
                                                query_count_cargo_map_with_size_standard += """ ) and cargo.size_id = %s  """
                                                query_count_cargo_map_with_size_standard += " ) t"
                                                self.env.cr.execute(query_count_cargo_map_with_size_standard,
                                                                    (rec['id'],))
                                                result_count_cargo_map_with_size_standard = self._cr.fetchall()

                                                query_caculate_cargo_total_weight = """ SELECT json_agg(t) FROM ( select sum(weight) from sharevan_cargo cargo where cargo.id  ::integer in ( """
                                                for cargo_id in list_cargo_id:
                                                    query_caculate_cargo_total_weight += str(cargo_id) + ","
                                                query_caculate_cargo_total_weight = query_caculate_cargo_total_weight[
                                                                                    :-1]
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
                                                        'cargo_quantity':
                                                            result_count_cargo_map_with_size_standard[0][0][0][
                                                                'count'],
                                                        'total_weight':
                                                            result_query_caculate_cargo_total_weight[0][0][0][
                                                                'sum']

                                                    }
                                                    size_standard_arr.append(size_standard_data)

                                    query_get_rating = """ SELECT json_agg(t) FROM (SELECT id, driver_id, num_rating, employee_id, note,  TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS') create_date , bidding_vehicle_id, bidding_order_id
    	                                                        FROM public.sharevan_rating rating where rating.bidding_vehicle_id = %s and rating.bidding_order_id = %s  ) t """
                                    bidding_vehicle_id = result_get_bidding_vehicle[0][0][0]['id']
                                    self.env.cr.execute(query_get_rating, (bidding_vehicle_id, bidding_order['id'],))
                                    result_get_rating = self._cr.fetchall()
                                    rating = {}

                                    if result_get_rating[0][0]:
                                        rating_count += 1
                                        rating = result_get_rating[0][0][0]
                                        order_rate_avg += rating['num_rating']
                                        query_get_rating_badges_driver = """ SELECT json_agg(t) FROM (SELECT id, sharevan_bidding_order_id, sharevan_bidding_vehicle_id, share_van_driver_id, share_van_rating_badges_id,   TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS') create_date  
    	                                                                   FROM public.sharevan_bidding_vehicle_rating_badges  badges where badges.sharevan_bidding_vehicle_id = %s and  badges.sharevan_bidding_order_id = %s  ) t """
                                        bidding_vehicle_id = result_get_bidding_vehicle[0][0][0]['id']
                                        self.env.cr.execute(query_get_rating_badges_driver,
                                                            (bidding_vehicle_id, bidding_order['id'],))
                                        result_get_rating_badges_driver = self._cr.fetchall()
                                        if result_get_rating_badges_driver[0][0]:
                                            for rec in result_get_rating_badges_driver[0][0]:

                                                query_get_rating_badges = """ SELECT json_agg(t) FROM (SELECT id, name, code_seq, code, description, status, TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS') create_date
                                                                                          FROM public.sharevan_rating_badges r where r.id = %s ) t """
                                                self.env.cr.execute(query_get_rating_badges,
                                                                    (int(rec['share_van_rating_badges_id']),))
                                                result_get_rating_badges = self._cr.fetchall()
                                                if result_get_rating_badges[0][0]:
                                                    rating_badges.append(result_get_rating_badges[0][0][0])

                                    query_get_image = """ SELECT json_agg(t) FROM (SELECT id, uri_path FROM public.ir_attachment where id in (5971,5972,5973,5977,4970,411) ) t """
                                    self.env.cr.execute(query_get_image, (int(rec['id']),))
                                    images = []
                                    result_get_image = self._cr.fetchall()
                                    if result_get_image[0][0]:
                                        for image in result_get_image[0][0]:
                                            images.append(image['uri_path'])

                                    rating_data = {
                                        'id': result_get_rating[0][0][0]['id'],
                                        'driver_id': result_get_rating[0][0][0]['driver_id'],
                                        'num_rating': result_get_rating[0][0][0]['num_rating'],
                                        'employee_id': result_get_rating[0][0][0]['employee_id'],
                                        'note': result_get_rating[0][0][0]['note'],
                                        'create_date': result_get_rating[0][0][0]['create_date'],
                                        'bidding_vehicle_id': result_get_rating[0][0][0]['bidding_vehicle_id'],
                                        'bidding_order_id': result_get_rating[0][0][0]['bidding_order_id'],
                                        'rating_badges': rating_badges,
                                        'images': images
                                    }
                                    bidding_vehicle_json = {
                                        'id': result_get_bidding_vehicle[0][0][0]['id'],
                                        'code': result_get_bidding_vehicle[0][0][0]['code'],
                                        'lisence_plate': result_get_bidding_vehicle[0][0][0]['lisence_plate'],
                                        'driver_phone_number': result_get_bidding_vehicle[0][0][0][
                                            'driver_phone_number'],
                                        'driver_name': result_get_bidding_vehicle[0][0][0]['driver_name'],
                                        'expiry_time': result_get_bidding_vehicle[0][0][0]['expiry_time'],
                                        'company_id': result_get_bidding_vehicle[0][0][0]['company_id'],
                                        'status': result_get_bidding_vehicle[0][0][0]['status'],
                                        'description': result_get_bidding_vehicle[0][0][0]['description'],
                                        'vehicle_type': result_get_bidding_vehicle[0][0][0]['vehicle_type'],
                                        'weight_unit': result_get_bidding_vehicle[0][0][0]['weight_unit'],
                                        'store_fname': result_get_bidding_vehicle[0][0][0]['store_fname'],
                                        'cargo_types': size_standard_arr,
                                        'rating': rating_data
                                    }

                                    bidding_vehicle_arr.append(bidding_vehicle_json)

                                order_rate_avg = order_rate_avg / float(rating_count)
                                query_get_from_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                               join sharevan_bidding_package bidding_package on depot.id = %s ) t"""
                                self.env.cr.execute(query_get_from_depot, (re[8],))
                                result_get_from_depot = self._cr.fetchall()

                                array_length = len(result_get_from_depot)
                                if array_length > 0:
                                    if result_get_from_depot[0][0]:
                                        get_from_depot = result_get_from_depot[0][0][0]

                                query_get_to_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                             join sharevan_bidding_package bidding_package on depot.id = %s ) t"""
                                self.env.cr.execute(query_get_to_depot, (re[9],))
                                result_get_to_depot = self._cr.fetchall()
                                get_to_depot = []
                                array_length = len(result_get_to_depot)
                                if array_length > 0:
                                    if result_get_to_depot[0][0]:
                                        get_to_depot = result_get_to_depot[0][0][0]

                                bidding_order_json = {
                                    'id': bidding_order['id'],
                                    'company_id': bidding_order['company_id'],
                                    'bidding_order_number': bidding_order['bidding_order_number'],
                                    'from_depot': get_from_depot,
                                    'to_depot': get_to_depot,
                                    'total_weight': bidding_order['total_weight'],
                                    'total_cargo': bidding_order['total_cargo'],
                                    'price': bidding_order['price'],
                                    'distance': bidding_order['distance'],
                                    'type': bidding_order['type'],
                                    'status': bidding_order['status'],
                                    'note': bidding_order['note'],
                                    'bidding_order_receive_id': bidding_order['bidding_order_receive_id'],
                                    'bidding_order_return_id': bidding_order['bidding_order_return_id'],
                                    'create_date': bidding_order['create_date'],
                                    'write_date': bidding_order['write_date'],
                                    'bidding_package_id': bidding_order['bidding_package_id'],
                                    'from_receive_time': bidding_order['from_receive_time'],
                                    'to_receive_time': bidding_order['to_receive_time'],
                                    'from_return_time': bidding_order['from_return_time'],
                                    'to_return_time': bidding_order['to_return_time'],
                                    'max_confirm_time': bidding_order['max_confirm_time'],
                                    'bidding_vehicles': bidding_vehicle_arr,
                                    'total_cargo': total_cargos['count'],
                                    'order_rate_avg': order_rate_avg

                                }

                                content = {
                                    'id': re[0],
                                    'bidding_package_number': re[2],
                                    'status': re[3],
                                    'confirm_time': re[4],
                                    'release_time': re[5],
                                    'bidding_time': re[6],
                                    'max_count': re[7],
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
                                    'write_date': re[23],
                                    'countdown_time': re[24],

                                    'bidding_order': bidding_order_json
                                }
                                jsonRe.append(content)

        records = {
            'length': len(result_get_bidding_order[0][0]),
            'total': total,
            'records': jsonRe
        }
        simplejson.dumps(records, indent=4, sort_keys=True, default=str)
        return records

    def list_to_string(self, list):
        string = ''
        count = 0
        lenght = len(list)
        for i in list:
            count = count + 1
            if count == lenght:
                string += str(i)
            else:
                string += str(i)
                string += ','
        return string

    def get_fleet_vehicle(self,**kwargs):
        user = self.env.user
        offset = '0'
        limit = '10'
        approved_check = kwargs.get('approved_check')
        offset = kwargs.get('offset')
        limit = kwargs.get('limit')
        text_search = kwargs.get('text_search')
        page = ' offset ' + str(offset)
        page += ' limit ' + str(limit)
        type = kwargs.get('type')
        # get list simple
        if type =='0':
            company_id = user['company_id']['id']
            if company_id is None:
                raise ValidationError(_('Company does not exist!'))
            if user:
                query_get_fleet_vehicle = """ 
                    SELECT json_agg(t) FROM ( 
                        SELECT fv.id, fv.name, license_plate, vin_sn, model_id, brand_id, location_log, acquisition_date,
                            color, latitude, longitude, vehicle_inspection, inspection_due_date, available_capacity, vehicle_registration,
                            capacity, body_length, body_width, height, vehicle_type,stv.name tonnage_name,fv.approved_check
                        FROM public.fleet_vehicle fv 
                            join sharevan_tonnage_vehicle stv on fv.tonnage_id = stv.id 
                            join fleet_vehicle_state state on state.id = fv.state_id
                        where fv.company_id = %s and state.name!= %s and fv.approved_check = %s and fv.active_type = %s  """
                query_get_fleet_vehicle+=  """ )t"""
                self.env.cr.execute(query_get_fleet_vehicle, (
                            company_id, VehicleStateStatus.DOWNGRADED.value, VehicleConfirmStatus.Accepted.value,
                            FleetSystemType.CODE_SHARE.value,))
                result_get_fleet_vehicle = self._cr.fetchall()
                if result_get_fleet_vehicle[0][0]:
                    records = {
                        'length': len(result_get_fleet_vehicle[0][0]),
                        'records': result_get_fleet_vehicle[0][0]
                    }
                    simplejson.dumps(records, indent=4, sort_keys=True, default=str)
                    return records
                records = {
                    'records': []
                }
                return records
            else:
                raise ValidationError(_('User does not exist!'))
        else:
            company_id = user['company_id']['id']
            if company_id is None:
                raise ValidationError(_('Company does not exist!'))
            if user:
                count_query="""
                    SELECT count(fv.id)
                    FROM public.fleet_vehicle fv 
                        join sharevan_tonnage_vehicle stv on fv.tonnage_id = stv.id 
                        join fleet_vehicle_state state on state.id = fv.state_id
                    where fv.company_id = 
                """
                query_get_fleet_vehicle = """ 
                    SELECT fv.id, fv.name, license_plate, vin_sn, model_id, brand_id, location_log, acquisition_date,
                        color, latitude, longitude, vehicle_inspection, inspection_due_date, available_capacity, vehicle_registration,
                        capacity, body_length, body_width, height, vehicle_type,stv.name tonnage_name,fv.approved_check
                    FROM public.fleet_vehicle fv 
                        join sharevan_tonnage_vehicle stv on fv.tonnage_id = stv.id 
                        join fleet_vehicle_state state on state.id = fv.state_id
                    where fv.company_id = """
                query_get_fleet_vehicle+= str(company_id)+""" and state.name != 'Downgraded' and fv.active_type = 'code_share' """
                count_query+= str(company_id)+""" and state.name != 'Downgraded' and fv.active_type = 'code_share' """

                if approved_check:
                    query_get_fleet_vehicle += """ and  LOWER(fv.approved_check) = LOWER('%s') """ % (str(approved_check),)
                    count_query += """ and  LOWER(fv.approved_check) = LOWER('%s') """ % (str(approved_check),)
                if text_search:
                    query_get_fleet_vehicle += """ and ( LOWER(fv.name)  like LOWER('%%%s%%') """ % (text_search,)
                    count_query += """ and ( LOWER(fv.name) like LOWER('%%%s%%') """ % (text_search,)
                query_get_fleet_vehicle += page
                self.env.cr.execute(query_get_fleet_vehicle, ())
                result_get_fleet_vehicle = self._cr.dictfetchall()
                self.env.cr.execute(count_query, ())
                count_result = self._cr.dictfetchall()
                if result_get_fleet_vehicle:
                    jsonArr=[]
                    for record in result_get_fleet_vehicle:
                        order_bidding_query="""
                            select bidding_order.id,bidding_order.bidding_order_number as name 
                                from sharevan_bidding_vehicle bi_vh
                            join sharevan_bidding_order_return bidding_return 
                                on bi_vh.id =  bidding_return.bidding_vehicle_id
                            join sharevan_bidding_order bidding_order on bidding_order.id = bidding_return.bidding_order_id
                                where bidding_order.type = '1' and bidding_order.status != '-1' and bidding_return.status = '0' 
                                and bi_vh.vehicle_id = %s
                        """
                        self.env.cr.execute(order_bidding_query, (record['id'],))
                        order_records = self._cr.dictfetchall()
                        if order_records:
                            record['bidding_orders'] = order_records
                        else:
                            record['bidding_orders'] = []
                    records = {
                        'length': len(result_get_fleet_vehicle),
                        'records': result_get_fleet_vehicle,
                        'total_record':count_result[0]['count']
                    }
                    simplejson.dumps(records, indent=4, sort_keys=True, default=str)
                    return records
                records = {
                    'length':0,
                    'records': [],
                    'total_record': 0
                }
                return records
            else:
                raise ValidationError(_('User does not exist!'))

    def get_vehicle_type(self):
        query_get_fleet_driver = """ 
            select id,name,code from fleet_vehicle_type where status = 'running'
                    """
        self.env.cr.execute(query_get_fleet_driver, ())
        result_vehicle_type = self._cr.dictfetchall()
        if result_vehicle_type:
            records = {
                'length': len(result_vehicle_type),
                'records': result_vehicle_type
            }
            simplejson.dumps(records, indent=4, sort_keys=True, default=str)
            return records
        else:
            records = {
                'length': 0,
                'records': []
            }
            return records

    def get_fleet_driver(self,**kwargs):
        offset = '0'
        limit = '10'
        approved_check = kwargs.get('approved_check')
        offset = kwargs.get('offset')
        limit = kwargs.get('limit')
        text_search = kwargs.get('text_search')
        page = ' offset ' + str(offset)
        page += ' limit ' + str(limit)

        user = http.request.env['res.users'].search([('id', '=', self.env.uid)])
        company_id = user['company_id']['id']
        count_query="""
            SELECT count(fd.id)
            FROM public.fleet_driver fd
                left JOIN ir_attachment ir on ir.res_id = fd.id and res_model ='fleet.driver'
                    and ir.name='image_1920'
                join sharevan_driver_license license on license.id = fd.class_driver
                where  fd.employee_type = 'driver'  and  fd.company_id =
        """
        query_get_fleet_driver = """ 
            SELECT fd.id, fd.name, fd.display_name, fd.date, fd.active, fd.employee, fd.function, 
                fd.street, fd.street2, fd.zip, fd.city_name,
                fd.state_id, fd.country_id, fd.partner_latitude,fd.partner_longitude, fd.email, fd.name_seq, fd.phone, 
                fd.mobile,    fd.ssn, 
                TO_CHAR(fd.birth_date, 'YYYY-MM-DD HH24:MI:SS') birth_date , fd.full_name,
                TO_CHAR(fd.expires_date, 'YYYY-MM-DD HH24:MI:SS') expires_date, fd.address, no,
                TO_CHAR(fd.driver_license_date, 'YYYY-MM-DD HH24:MI:SS')  driver_license_date,
                fd.class_driver, fd.driver_type,fd.approved_check,
                ir.uri_path image_1920,license.name as class_name,license.max_tonnage
            FROM public.fleet_driver fd
                left JOIN ir_attachment ir on ir.res_id = fd.id and res_model ='fleet.driver'
                    and ir.name='image_1920'
                join sharevan_driver_license license on license.id = fd.class_driver
                where  fd.employee_type = 'driver'  and  fd.company_id =  """
        query_get_fleet_driver+= str(company_id) +""" and fd.status = 'running'  and fd.driver_type = 'code_share'  """
        count_query+= str(company_id) +""" and fd.status = 'running'  and fd.driver_type = 'code_share'  """
        if approved_check:
            query_get_fleet_driver += """ and LOWER(fd.approved_check) = LOWER('%s') """% (approved_check,)
            count_query += """ and LOWER(fd.approved_check) = LOWER('%s') """% (approved_check,)
        if text_search:
            query_get_fleet_driver += """ and ( LOWER(fd.name)  like LOWER('%%%s%%') """ % (text_search,)
            count_query += """ and ( LOWER(fd.name)  like LOWER('%%%s%%') """ % (text_search,)
            query_get_fleet_driver += """ or  LOWER(fd.phone)  like LOWER('%%%s%%') """ % (text_search,)
            count_query += """ or  LOWER(fd.phone)  like LOWER('%%%s%%') """ % (text_search,)
            query_get_fleet_driver += """ ) """
            count_query += """ ) """
        query_get_fleet_driver +=  page
        self.env.cr.execute(query_get_fleet_driver, ())
        result_query_get_fleet_driver = self._cr.dictfetchall()
        self.env.cr.execute(count_query, ())
        count_result = self._cr.dictfetchall()
        if result_query_get_fleet_driver:
            records = {
                'length': len(result_query_get_fleet_driver),
                'records': result_query_get_fleet_driver,
                'total_record':count_result[0]['count']
            }
            simplejson.dumps(records, indent=4, sort_keys=True, default=str)
            return records
        records = {
            'records': [],
            'total_record': 0
        }
        return records

    def confirm_bidding_order_success(self, bidding_order_id, bidding_vehicle_id):
        if bidding_order_id is None:
            raise ValidationError(_('Bidding order id can not null!'))
        record_bidding_order = http.request.env[BiddingOrder._name].search_read([['id', '=', bidding_order_id]])
        if record_bidding_order:
            if record_bidding_order[0]['status'] == BiddingStatus.Cancel.value:
                raise ValidationError(_('Bidding order has been cancelled!'))
            elif record_bidding_order[0]['type'] != BiddingStatusType.Approved.value:
                raise ValidationError(_('Bidding order does not approved!'))
            elif record_bidding_order[0]['status'] == BiddingStatus.Returned.value:
                raise ValidationError(_('Bidding order has been returned!'))
            else:
                check_count_query = """
                    SELECT  return_order.id return_order_id, rel.id, rel.sharevan_bidding_order_id, 
                        rel.sharevan_bidding_vehicle_id,return_order.status
	                FROM public.sharevan_bidding_order_sharevan_bidding_vehicle_rel rel
                        JOIN sharevan_bidding_order bidding_order 
	                        on rel.sharevan_bidding_order_id = bidding_order.id
                        JOIN sharevan_bidding_order_return return_order 
                            on return_order.bidding_order_id = bidding_order.id
                    WHERE rel.sharevan_bidding_order_id = %s;
                """
                self.env.cr.execute(check_count_query, (bidding_order_id,))
                bidding_order_records = self._cr.dictfetchall()
                if bidding_order_records:
                    check_all = False
                    for vehicle_check_return in bidding_order_records:
                        if vehicle_check_return['status'] == BiddingStatus.NotConfirm.value:
                            if vehicle_check_return['sharevan_bidding_vehicle_id'] == bidding_vehicle_id:
                                time_now = datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")
                                http.request.env[Constants.SHAREVAN_BIDDING_ORDER_RETURN]. \
                                    browse(int(vehicle_check_return['return_order_id'])).write(
                                    {'status': BiddingStatus.Returned.value, 'actual_time': time_now})
                                check_all = True
                            else:
                                check_all = False
                        else:
                            check_all = True
                    if check_all == True:
                        bidding_order = http.request.env[BiddingOrder._name]. \
                            browse(bidding_order_id).write(
                            {'status': BiddingStatus.Returned.value,
                             'mobile': True})
                        # update capacity depot va routing plan day status
                        routing_query = """
                            select routing_assign.id now_id,routing_arrived.id old_id,routing_assign.total_volume,
                                    routing_assign.depot_id,routing_export.id export_id,routing.id
                                from sharevan_bidding_order bidding_order
                            join sharevan_bidding_package package on package.id= bidding_order.bidding_package_id
                            join sharevan_bidding_package_sharevan_cargo_rel rel 
                                on rel.sharevan_bidding_package_id = package.id
                            join sharevan_cargo cargo on cargo.id = rel.sharevan_cargo_id
                            join sharevan_cargo_sharevan_routing_plan_day_rel cargo_routing 
                                    on cargo_routing.sharevan_cargo_id = cargo.id
                            join sharevan_routing_plan_day routing 
                                    on routing.id = cargo_routing.sharevan_routing_plan_day_id
                            join sharevan_routing_plan_day routing_arrived 
                                on routing_arrived.from_routing_plan_day_id = routing.id
                            join sharevan_routing_plan_day routing_assign 
                                on routing_assign.from_routing_plan_day_id = routing_arrived.id
                            join sharevan_routing_plan_day routing_export 
                                on routing_export.from_routing_plan_day_id = routing_assign.id
                            where bidding_order.id =  %s
                        """
                        self.env.cr.execute(routing_query,
                                            (bidding_order_id,))
                        routing_result = self._cr.dictfetchall()
                        if routing_result:
                            for rec in routing_result:
                                depot_vals = {
                                    "routing_plan_day_id": rec['export_id'],
                                    "depot_id": rec['depot_id'],
                                    "total_volume": rec['total_volume'],
                                    "type": 0,
                                    "force_save": False
                                }
                                http.request.env[DepotGoods._name].import_goods(depot_vals)
                                routingWaitingDepot = http.request.env[RoutingPlanDay._name].search(
                                    [('id', '=', rec['export_id'])])
                                if routingWaitingDepot:
                                    routingWaitingDepot.write({'status': '0'})
                                routingAccept = http.request.env[RoutingPlanDay._name].search(
                                    [('id', '=', rec['now_id'])])
                                if routingAccept:
                                    routingAccept.write({'status': '2'})
                                else:
                                    logger.warn(
                                        "Can not update status because routing not found!",
                                        'sharevan.routing.plan.day', bidding_order_id,
                                        exc_info=True)
                        check_driver_market_query = """
                            select driver_id,driver.award_id, driver.user_id,award.percent_commission_value from sharevan_bidding_vehicle vehicle
                                join sharevan_bidding_order_sharevan_bidding_vehicle_rel rel 
                                    on rel.sharevan_bidding_vehicle_id = vehicle.id
                                join fleet_driver driver on driver.id = vehicle.driver_id
                                left join sharevan_title_award award on award.id = driver.award_id
                            where rel.sharevan_bidding_order_id = %s and driver_type ='market_place';
                        """
                        self.env.cr.execute(check_driver_market_query, (bidding_order_id,))
                        driver_info = self._cr.dictfetchall()
                        if driver_info:
                            driverInfo = driver_info[0]
                            amount = record_bidding_order[0]['price']
                            driver_level_id = driverInfo['award_id']
                            driver_id = driverInfo['driver_id']
                            user_id = driverInfo['user_id']
                            if not driverInfo['percent_commission_value']:
                                get_lower_reward = """
                                    select id, percent_commission_value 
                                        from sharevan_title_award award
                                    where award.title_award_type = 'driver' and status ='running'
                                    order by from_point asc LIMIT 1;
                                """
                                self.env.cr.execute(get_lower_reward, ())
                                rewardInfo = self._cr.dictfetchall()
                                if not rewardInfo:
                                    raise ValidationError('No driver title award found!')
                                http.request.env['fleet.driver']. \
                                    browse(driverInfo['driver_id']).write(
                                    {'award_id': rewardInfo[0]['id']})
                                commission = record_bidding_order[0]['price'] * rewardInfo[0][
                                    'percent_commission_value']
                                total_amount = int(record_bidding_order[0]['price']) - commission
                                vals = {
                                    'user_id': user_id,
                                    'amount': amount,
                                    'driver_level_id': rewardInfo[0]['id'],
                                    'total_amount': total_amount,
                                    'percent_commission': rewardInfo[0]['percent_commission_value'],
                                    'commission': commission,
                                    'order_id': bidding_order_id,
                                    'order_type': '2',
                                    'name': record_bidding_order[0]['bidding_order_number']
                                }
                                http.request.env['sharevan.driver.received'].create(vals)
                            else:
                                commission = record_bidding_order[0]['price'] * driverInfo['percent_commission_value']
                                total_amount = int(record_bidding_order[0]['price']) - commission
                                vals = {
                                    'user_id': user_id,
                                    'amount': amount,
                                    'driver_level_id': driver_level_id,
                                    'total_amount': total_amount,
                                    'percent_commission': driverInfo['percent_commission_value'],
                                    'commission': commission,
                                    'order_id': bidding_order_id,
                                    'order_type': '2',
                                    'name': record_bidding_order[0]['bidding_order_number']
                                }
                                http.request.env['sharevan.driver.received'].create(vals)
                            return True
                        return True
                else:
                    raise ValidationError(_('Bidding order id does not exist!'))
        else:
            raise ValidationError(_('Bidding order id does not exist!'))

    def driver_market_place_confirm_order(self, bidding_package_id, type):
        bidding_package = self.env['sharevan.bidding.package'].search([('id', '=', bidding_package_id)])
        if bidding_package:
            # cai gi day???
            # u_id = uid = http.request.session['uid']
            if type == True:
                u_id = self.env.uid
                company_id = http.request.env.company.id
                query_driver_vehicle = """ 
                    select driver.phone,driver.name,driver.ssn,driver.id as driver_id,use.partner_id,
                                vehicle.id as vehicle_id,vehicle.license_plate,vehicle.tonnage_id,vehicle.vehicle_type
                            from res_users use
                            join fleet_driver driver on use.id = driver.user_id
                            join fleet_vehicle vehicle 
                                on vehicle.id = driver.vehicle_id 
                        where use.id = %s """
                self.env.cr.execute(query_driver_vehicle, (u_id,))
                result_driver_vehicle = self._cr.dictfetchall()
                if not result_driver_vehicle:
                    raise ValidationError('Driver have no car')
                total_driver_vehicle = result_driver_vehicle[0]

                query_count_cargo = """ 
                    SELECT json_agg(t) FROM ( 
                        select count(cargo.id) from sharevan_cargo cargo
                            join sharevan_bidding_package bidding_package 
                                on bidding_package.id = cargo.bidding_package_id 
                        where bidding_package.id = %s ) t """
                self.env.cr.execute(query_count_cargo, (bidding_package_id,))
                result_count_cargo = self._cr.fetchall()
                total_cargos = result_count_cargo[0][0][0]['count']
                val_bidding_order = {
                    'company_id': company_id,
                    'bidding_package_id': bidding_package_id,
                    'from_depot_id': bidding_package['from_depot_id']['id'],
                    'to_depot_id': bidding_package['to_depot_id']['id'],
                    'total_weight': bidding_package['total_weight'],
                    'total_cargo': total_cargos,
                    'price': bidding_package['price'],
                    'type': '1',
                    'distance': bidding_package['distance'],
                    'from_receive_time': bidding_package['from_receive_time'],
                    'to_receive_time': bidding_package['to_receive_time'],
                    'bidded_user_id': total_driver_vehicle['partner_id'],
                    'max_confirm_time': bidding_package['max_confirm_time']
                }
                bidding_order = self.env['sharevan.bidding.order'].sudo().create(val_bidding_order)
                val_bidding_vehicle = {
                    'lisence_plate': total_driver_vehicle['license_plate'],
                    'driver_phone_number': total_driver_vehicle['phone'],
                    'driver_name': total_driver_vehicle['name'],
                    'company_id': company_id,
                    'id_card': total_driver_vehicle['ssn'],
                    'tonnage': total_driver_vehicle['tonnage_id'],
                    'vehicle_id': total_driver_vehicle['vehicle_id'],
                    'driver_id': total_driver_vehicle['driver_id'],
                    'res_partner_id': total_driver_vehicle['partner_id'],
                    'res_user_id': u_id,
                }
                bidding_vehicle = http.request.env['sharevan.bidding.vehicle'].create(val_bidding_vehicle)
                val_bidding_order_bidding_vehicle = {
                    'sharevan_bidding_order_id': bidding_order['id'],
                    'sharevan_bidding_vehicle_id': bidding_vehicle['id'],
                    'status': '1'
                }
                result_bidding_order_receive = self.env[
                    'sharevan.bidding.order.sharevan.bidding.vehicle.rel'].sudo().create(
                    val_bidding_order_bidding_vehicle)

                val_bidding_order_recive = {
                    'bidding_order_id': bidding_order['id'],
                    'bidding_vehicle_id': bidding_vehicle['id'],
                }
                result_bidding_order_receive = self.env['sharevan.bidding.order.receive'].sudo().create(
                    val_bidding_order_recive)

                val_bidding_order_return = {
                    'bidding_order_id': bidding_order['id'],
                    'bidding_vehicle_id': bidding_vehicle['id'],
                }
                result_bidding_order_return = self.env['sharevan.bidding.order.return'].sudo().create(
                    val_bidding_order_return)
                bidding_package.write({
                    'status': '1'
                })
                return {
                    'status': 200,
                    'message': ' Accept package successful!',
                    'id': bidding_order['id']
                }
            else:
                logger.warn(
                    "Driver have reject package request!" + self.env.user.login,
                    'sharevan.bidding.package', bidding_package_id,
                    exc_info=True)
                return {
                    'status': 200,
                    'message': ' Reject package successful!'
                }
        else:
            raise ValidationError(_('Bidding package id does not exist!'))

    # def driver_reject_bidding_package(self,package):
    #

    def get_bidding_package_id(self, bidding_package_id):
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
                url = config['security_url'] + config['socket_link'] + "pushAll"
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
                    'total_cargos': total_cargos['count'],
                    'cargo_types': size_standard_arr
                }

                records = {
                    'records': [vals]
                }
                return records

    def get_rating_title_award(self):
        u_id = uid = http.request.session['uid']
        user_respartner = self.env['res.partner'].search([('user_id', '=', u_id)])
        # list_title_award = self.env['sharevan.title.award'].search([('status', '=', 'running'),('title_award_type', '=', 'customer')])
        query_list_title_award = """ 
            SELECT json_agg(t) FROM ( 
                select award.id,award.name,award.from_point,award.to_point,ir.uri_path from sharevan_title_award award
                join ir_attachment ir on ir.res_id = award.id
                where award.status = 'running' and title_award_type = 'customer'  and res_model = 'sharevan.title.award' 
                Order by  award.from_point ASC
                                         ) t """
        querry_award_level = """ SELECT json_agg(t) FROM (  select level.name ,ir.uri_path from sharevan_awards_level level
										join sharevan_title_award award on award.id = level.title_ward_id
                                        join ir_attachment ir on ir.res_id = level.id 
                                        where award.id = %s and res_model = 'sharevan.awards.level'
										) t"""
        querry_sum_point = """ select COALESCE(sum(point),0) from sharevan_reward_point_customer where user_id = %s   """ % (
            u_id)
        self.env.cr.execute(query_list_title_award)
        result_list_title_award = self._cr.fetchall()
        if result_list_title_award:
            list_title_award = result_list_title_award[0][0]
            l_title_award = []

            self.env.cr.execute(querry_sum_point)
            result_award_point_cus = self._cr.fetchall()
            point = result_award_point_cus[0][0]
            for title_award in list_title_award:
                self.env.cr.execute(querry_award_level, (title_award['id'],))
                result_list_awards_level = self._cr.fetchall()

                l_title_award.append({
                    'id': title_award['id'],
                    'name': title_award['name'],
                    'from_point': title_award['from_point'],
                    'to_point': title_award['to_point'],
                    'current_rank': '1' if point >= title_award['from_point'] and
                                           point <= title_award['to_point'] else '0',
                    'point_level_up': title_award['to_point'] - user_respartner['rating_point'],
                    'uri_path': title_award['uri_path'],
                    'list_awards_leve': result_list_awards_level[0][0]
                })

            result = {
                'point': user_respartner['rating_point'],
                'point_expiration_date': user_respartner['point_expiration_date'].strftime("%d/%m/%Y"),
                'total_point': point,
                'list_rank': l_title_award
            }
            return result
        return []

    def get_history_rating_point(self, type, page, limit):
        u_id = uid = http.request.session['uid']
        offset_check = 0
        if type == 0:
            querry_json_agg = """SELECT json_agg(t) FROM ( """
            querry_customer_rating = """ SELECT cus.id,re_point.name ,cus.point,
                                        TO_CHAR(cus.create_date,'HH24:MI DD/MM/YYYY')  create_date,ir.uri_path
                                        FROM public.sharevan_reward_point_customer cus
                                        join sharevan_reward_point re_point on re_point.id = cus.reward_point_id
                                        join ir_attachment ir on ir.res_id = re_point.id
                                        join res_users use on use.id = cus.user_id
                                        where use.id = %s and ir.res_model = 'sharevan.reward.point'
                                         """ % (u_id)
            querry_total = querry_customer_rating
            if page is not None and limit is not None:
                if page > 0:
                    offset_check = page * limit
                    querry_json_agg += querry_customer_rating
                    querry_json_agg += """ Order  by  cus.create_date DESC OFFSET %s LIMIT %s """ % (
                        offset_check, limit)
                    querry_json_agg += """ ) t """

                else:
                    querry_json_agg += querry_customer_rating
                    querry_json_agg += """ Order  by  cus.create_date DESC OFFSET %s LIMIT %s """ % (
                        offset_check, limit)
                    querry_json_agg += """ ) t """
            else:
                querry_json_agg += querry_customer_rating
                querry_json_agg += """ Order  by  cus.create_date DESC OFFSET 0 LIMIT 10 """
                querry_json_agg += """ ) t """

            total_records = """ select count(*) from (  """
            total_records += querry_customer_rating
            total_records += " )t"

            self.env.cr.execute(querry_json_agg)
            result = self._cr.fetchall()
            list_point = result[0][0]
            list_points = []
            for point in list_point:
                val = {
                    'id': point['id'],
                    'type': 0,
                    'name': point['name'],
                    'point': point['point'],
                    'create_date': point['create_date'],
                    'uri_path': point['uri_path']
                }
                list_points.append(val)

            self.env.cr.execute(total_records)
            result = self._cr.fetchall()
            total = result[0][0]
            records = {
                'length': len(list_point),
                'total_record': total,
                'records': list_points
            }
            return records
        else:
            return {
                'length': 0,
                'total_record': 0,
                'records': []
            }

    def check_product_type(self, currentProductType, newProductType):
        self.env.cr.execute(""" 
            SELECT * FROM public.sharevan_product_type_rel rel
				where ( rel.main_product_type = 
			    (select id from sharevan_product_type where name_seq = %s ) 
					and rel.same_product_type_ids =(select id from sharevan_product_type where name_seq = %s ) ) or
			    ( rel.main_product_type = (select id from sharevan_product_type where name_seq = %s ) 
				    and rel.same_product_type_ids =(select id from sharevan_product_type where name_seq = %s ) )""",
                            (currentProductType, newProductType,currentProductType,newProductType,))
        un_conflig = self._cr.fetchall()

        return True if un_conflig else False
