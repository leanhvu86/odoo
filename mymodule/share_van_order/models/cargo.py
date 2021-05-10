import json as simplejson
import logging
from datetime import datetime
from json import JSONEncoder

from mymodule.base_next.controllers.api.base_method import BaseMethod
from mymodule.base_next.models.bidding import BiddingOrder
from mymodule.base_next.models.bidding_vehicle import BiddingVehicle
from mymodule.base_next.models.routing_plan_day import RoutingPlanDay
from mymodule.constants import Constants
from mymodule.enum.BiddingStatus import BiddingStatus
from mymodule.enum.BiddingStatusType import BiddingStatusType
from mymodule.enum.CargoStatus import CargoStatus
from mymodule.enum.StatusType import StatusType
from mymodule.enum.PackageCargoStatus import PackageCargoStatus
from mymodule.enum.RoutingDetailStatus import RoutingDetailStatus
from odoo import api, models, _
from odoo import http
from odoo.exceptions import ValidationError

logger = logging.getLogger(__name__)


class Cargo(models.Model):
    _name = 'sharevan.cargo'
    _description = 'cargo'
    _inherit = 'sharevan.cargo'

    @api.model
    def create(self, vals):

        cargo_price = vals.get('size_id')
        if vals.get('cargo_number', 'New') == 'New':
            vals['cargo_number'] = BaseMethod.get_new_sequence('sharevan.cargo', 'CAR', 12, 'cargo_number')
        if vals.get('size_id'):
            cargo_price = self.env[Constants.SHAREVAN_CARGO_PRICE].search([('id', '=', vals.get('size_id'))])
            vals['price'] = cargo_price.price
            # check total weight
            cargo_size = self.env[Constants.SHAREVAN_SIZE_STANDARD].search([('id', '=', vals.get('size_id'))])
            if vals.get('weight') not in range(int(cargo_size.from_weight), int(cargo_size.to_weight)):
                raise ValidationError(
                    'Total weight is out of range cargo!!!! min size = %s and max size = %s' % (cargo_size.from_weight,
                                                                                                cargo_size.to_weight))
        # if vals.get('bill_lading_detail_ids')[0][2]:
        #     dem = 0
        #     from_depot = None
        #     to_depot = None
        #     for id in vals.get('bill_lading_detail_ids')[0][2]:
        #         bill_lading_detail = self.env[Constants.SHAREVAN_BILL_LADING_DETAIL].search([('id','=',id)],limit=1)
        #         if dem == 0:
        #             from_depot = bill_lading_detail.from_depot_id.id
        #             to_depot = bill_lading_detail.depot_id.id
        #             if vals.get('from_depot_id') and vals.get('from_depot_id') != from_depot:
        #                 raise ValidationError('Not same from depot')
        #             if vals.get('to_depot_id') and vals.get('to_depot_id') != to_depot:
        #                 raise ValidationError('Not same to depot')
        #         else:
        #             if from_depot != bill_lading_detail.from_depot_id.id or to_depot != bill_lading_detail.depot_id.id:
        #                 raise ValidationError('Note same depot')
        res = super(Cargo, self).create(vals)

        list_routing_plan_day_ids = vals['routing_plan_day_id'][0][2]
        for rec in list_routing_plan_day_ids:
            http.request.env[Constants.SHAREVAN_ROUTING_PLAN_DAY]. \
                browse(rec).write(
                {'packaged_cargo': '2'})
            from_record = self.env[Constants.SHAREVAN_ROUTING_PLAN_DAY].search(
                [('from_routing_plan_day_id', '=', rec)])
            if from_record:
                from_record.write(
                    {'packaged_cargo': '2', 'status': '0'})
            else:
                logger.warn(
                    "Next record of routing plan day type = '0' not found!",
                    RoutingPlanDay._name, rec,
                    exc_info=True)

        return res

    def write(self, vals):
        if 'weight' in vals:
            if vals.get('weight') not in range(int(self.size_id.from_weight), int(self.size_id.to_weight)):
                raise ValidationError(
                    'Total weight is out of range cargo!!!! min size = %s and max size = %s' % (self.size_id.from_weight,
                                                                                                self.size_id.to_weight))
        res = super(Cargo, self).write(vals)

    def get_bidding_information(self, uID, status_cargo, type, order_by, offset, limit):
        params = []
        offset_check = 0
        limit_check = 10
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
        if status_cargo:
            query += """ and  cargo.status = %s """
            params.append(status_cargo)
        # if status_bidding:
        #     query += """ and  bidding.status = %s """
        #     params.append(status_bidding)
        if type:
            query += """ and bidding.type = %s """
            params.append(type)
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
                        'bidding_type': re[29]

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

    def edit_bidding_information(self, bidding_vehicle_id, bidding_id):
        if bidding_id:
            if bidding_vehicle_id:
                record_bidding_order = http.request.env[BiddingOrder._name]. \
                    web_search_read([['id', '=', bidding_id]], fields=None,
                                    offset=0, limit=10, order='')
                if record_bidding_order['records']:
                    record_bidding_vehicle = http.request.env[BiddingVehicle._name]. \
                        web_search_read([['id', '=', bidding_vehicle_id]], fields=None,
                                        offset=0, limit=10, order='')
                    if record_bidding_vehicle['records']:
                        if record_bidding_order['records'][0]:
                            http.request.env[BiddingOrder._name]. \
                                browse(record_bidding_order['records'][0]['id']).write(
                                {'bidding_vehicle_id': bidding_vehicle_id})

                            return True;
                    else:
                        raise ValidationError(_('Bidding vehicle not existed!'))
                else:
                    raise ValidationError(_('Bidding order not existed!'))
            else:
                raise ValidationError(_('Bidding vehicle id can not can not null!'))
        else:
            raise ValidationError(_('Bidding order id can not null!'))
        return False

    def bidding_cargo(self, cargo_id, user_id):
        if cargo_id == False:
            raise ValidationError("Not info id cargo")
        cargo = self.env[Cargo._name].search([('id', '=', cargo_id)], limit=1)
        if cargo:

            if cargo.status != CargoStatus.NotBidding.value:
                raise ValidationError("Cargo not bidding!")
            if cargo.bidding_order_id:
                raise ValidationError("Cargo had info bidding")
            cargo_price = self.env['sharevan.cargo.price'].search(
                [('cargo_id', '=', cargo_id), ('status', '=', StatusType.Running.value)])

            ####################################################
            if user_id == False:
                raise ValidationError("Not info user_id")
            user = self.env['res.users'].search([('id', '=', user_id)], limit=1)

            if user:
                bidding_time = http.request.env[Constants.IR_CONFIG_PARAMETER].sudo().get_param(Constants.BIDDING_TIME)
                # bidding_time = self.env[Constants.IR_CONFIG_PARAMETER].search([('key', '=', Constants.BIDDING_TIME)], limit=1)
                if user.company_id == False:
                    raise ValidationError("user have not info company!")
                bidding_order = self.env[Constants.SHAREVAN_BIDDING_ORDER].create({
                    'company_id': user.company_id.id,
                    'cargo_id': cargo_id,
                    'type': BiddingStatusType.NotApprove.value,
                    'status': BiddingStatus.NotConfirm.value,
                    'create_uid': user_id,
                    'distance': cargo.distance,
                    'from_depot_id': cargo.from_depot_id.id,
                    'to_depot_id': cargo.to_depot_id.id,
                    'total_weight': cargo.weight,
                    'total_cargo': cargo.quantity,
                    'price': cargo_price.price,
                    'product_type_id': cargo.product_type_id.id,
                    'from_latitude': cargo.from_latitude,
                    'from_longitude': cargo.from_longitude,
                    'to_latitude': cargo.to_latitude,
                    'to_longitude': cargo.to_longitude
                })
                bidding_order_number = 'BO' + str(bidding_order.id)
                bidding_order.write({
                    'bidding_order_number': bidding_order_number
                })
                cargo.write({
                    'status': CargoStatus.Waiting.value,
                    'confirm_time': datetime.now(),
                    'bidding_order_id': bidding_order.id
                })
                if cargo and bidding_order:
                    bidding = {
                        'id': cargo.id,
                        'cargo_number': cargo.cargo_number,
                        'status': cargo.status,
                        'bidding_order_id': cargo.bidding_order_id.id,
                        'confirm_time': cargo.confirm_time,
                        'time_countdown': bidding_time
                    }

                    return {
                        'records': [bidding]}
                else:
                    raise ValidationError("Error")
        else:
            raise ValidationError("Id is invalid!")

    def get_all_cargo_size_standard(self):
        query_get_size_standard_infor = """ SELECT json_agg(t) FROM ( SELECT id, length, width, height,
                    type, from_weight, to_weight, price_id, price, size_standard_seq, cargo_price_ids, long_unit, weight_unit
	                                          FROM public.sharevan_size_standard order by id ASC) t """
        self.env.cr.execute(query_get_size_standard_infor, ())
        result_get_size_standard_infor = self._cr.fetchall()
        if result_get_size_standard_infor[0][0]:
            records = {
                'length': len(result_get_size_standard_infor[0][0]),
                'records': result_get_size_standard_infor[0][0]
            }
            simplejson.dumps(records, indent=4, sort_keys=True, default=str)
            return records

        return {
            'records': []
        }

    def get_all_cargo_by_depot_id(self, **kwargs):
        limit = 10

        jsonRe = []
        total_cargos = []
        cargo_info_dtl = []
        total = 0
        params = []
        depot_id = 0
        code = ''
        size_id = ''
        status = None
        offset = 0
        for arg in kwargs:
            if arg == 'depot_id':
                depot_id = kwargs.get(arg)
            if arg == 'code':
                code = kwargs.get(arg)
            if arg == 'size_id':
                size_id = int(kwargs.get(arg))
            if arg == 'status':
                status = int(kwargs.get(arg))
            if arg == 'offset':
                offset = kwargs.get(arg)
        search_code = code.lower()
        query_get_cargo_info_json = """ SELECT json_agg(t) FROM (  """
        query_get_cargo_info_nomal = """ 
            SELECT sharevan_cargo.id, sharevan_cargo.cargo_number, sharevan_cargo.from_depot_id, 
                sharevan_cargo.to_depot_id, sharevan_cargo.distance, sharevan_cargo.size_id, 
                sharevan_cargo.weight, sharevan_cargo.description, sharevan_cargo.price, sharevan_cargo.from_latitude,
                sharevan_cargo.to_latitude, sharevan_cargo.bidding_package_id,  sharevan_cargo.from_longitude, 
                sharevan_cargo.to_longitude,size_standard,
                TO_CHAR(sharevan_cargo.pack_plant_day,'YYYY-MM-DD HH24:MI:SS')  pack_plant_day,
                size_standard.length, size_standard.width, size_standard.height,
                size_standard.type, size_standard.from_weight, 
                size_standard.to_weight, size_standard.price_id, size_standard.price,size_standard.size_standard_seq, 
                size_standard.long_unit, size_standard.weight_unit, sharevan_cargo.status
            FROM public.sharevan_cargo 
                join sharevan_size_standard  size_standard on size_standard.id = sharevan_cargo.size_id
            where 1=1  """
        print(query_get_cargo_info_json)
        if code:
            query_get_cargo_info_nomal += """ and  (LOWER('sharevan_cargo.cargo_number')like LOWER('%%%s%%') or LOWER('sharevan_cargo.weight')like LOWER('%%%s%%'))""" % (
                code, code)
        if size_id and size_id != '0':
            query_get_cargo_info_nomal += """ and sharevan_cargo.size_id = %s  """ % (size_id)
        if status:
            query_get_cargo_info_nomal += """ and sharevan_cargo.status ::Integer = %s  """ % (status)

        query_get_cargo_info_nomal += """ and sharevan_cargo.from_depot_id = %s  """ % (depot_id)
        query_get_cargo_info_nomal += """   order by pack_plant_day ASC """
        query_get_cargo_info_json += query_get_cargo_info_nomal
        query_count_cargo_info = """SELECT count(*) from ( """
        query_count_cargo_info += query_get_cargo_info_nomal
        query_count_cargo_info += """ ) cargo """
        self.env.cr.execute(query_count_cargo_info, ())
        result_count_cargo_info = self._cr.fetchall()
        if result_count_cargo_info[0][0]:
            total = result_count_cargo_info[0][0]

        if offset:
            query_get_cargo_info_json += """ offset %s  limit  %s """ % (offset, limit)
            query_get_cargo_info_json += """ ) t """
            print(query_get_cargo_info_json)
        else:
            query_get_cargo_info_json += """ offset 0   limit  %s """ % (limit)
            query_get_cargo_info_json += """ ) t """

        self.env.cr.execute(query_get_cargo_info_json, ())

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
                    'pack_plant_day': cargo['pack_plant_day'],
                    'status': cargo['status'],
                    'size_standard': {
                        'length': cargo['length'],
                        'width': cargo['width'],
                        'height': cargo['height'],
                        'type': cargo['type'],
                        'from_weight': cargo['from_weight'],
                        'to_weight': cargo['to_weight'],
                        'price_id': cargo['price_id'],
                        'price': cargo['price'],
                        'long_unit': cargo['long_unit'],
                        'weight_unit': cargo['weight_unit']
                    }

                }
                cargo_info_dtl.append(data)
            if len(cargo_info_dtl) > 0:
                records = {
                    'length': len(cargo_info_dtl),
                    'total_record': total,
                    'records': cargo_info_dtl
                }
                simplejson.dumps(records, indent=4, sort_keys=True, default=str)
                return records

        return {
            'records': []
        }


class CargoDetail(models.Model):
    _name = 'sharevan.cargo.detail'
    _description = 'Cargo detail'
    _inherit = 'sharevan.cargo.detail'


class ObjectEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__
