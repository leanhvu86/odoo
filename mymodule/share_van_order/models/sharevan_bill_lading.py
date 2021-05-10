import json as simplejson
from datetime import datetime, timedelta
import googlemaps
import json
from addons.web.controllers.auth import AuthSsoApi
from mymodule.base_next.controllers.api.base_method import BaseMethod
from mymodule.base_next.models.notification import NotificationUser
from mymodule.enum.BiddingPackageStatus import OrderPackage
from mymodule.enum.BillRoutingStatus import BillRoutingStatus
from mymodule.enum.ClickActionType import ClickActionType
from mymodule.enum.MessageType import MessageType, NotificationSocketType
from mymodule.enum.NotificationType import NotificationType
from mymodule.enum.ObjectStatus import ObjectStatus
from mymodule.enum.VehicleStateStatus import CompanyName, VehicleStateStatus
from mymodule.enum.VehicleStatusAvailable import RoutingPlanDay
from mymodule.share_van_order.controllers.api.warehouse import WarehouseApi
from mymodule.share_van_order.models.base import Base
from mymodule.share_van_order.models.bill_package_routing import BillRouting
from odoo import models, api, http, fields
from odoo.exceptions import ValidationError
from odoo.tools import config
from odoo.http import Response, request


class BillLading(models.Model, Base):
    _name = 'sharevan.bill.lading'
    _description = 'bill of lading'
    _inherit = 'sharevan.bill.lading'

    order_package_id = fields.Many2one('sharevan.bill.order.package', string='Order package',
                                       domain=[('status', '=', 'running')],
                                       required=True)

    def get_bill_lading_history(self, **kwargs):
        domain = []
        param = []
        offset = 0
        limit = 10
        where_sql = """ where 1 = 1 """
        for arg in kwargs:
            if arg == 'start_date' and kwargs.get(arg) is not None:
                domain.append(['start_date', '>=', kwargs.get(arg)])
                where_sql += """ and start_date >= %s """
                param.append(kwargs.get(arg))
                continue
            if arg == 'offset':
                offset = kwargs.get(arg)
            if arg == 'limit':
                limit = kwargs.get(arg)
            if arg == 'end_date' and kwargs.get(arg) is not None:
                domain.append(['end_date', '<=', kwargs.get(arg)])
                where_sql += """ and end_date <= %s """
                param.append(kwargs.get(arg))
                continue
            if arg != 'start_date' and arg != 'end_date' and kwargs.get(arg) is not None:
                domain.append([arg, '=', kwargs.get(arg)])
                where_sql += """ and """ + arg + """ = %s """
                param.append(kwargs.get(arg))
                continue
        records = http.request.env['sharevan.bill.lading']. \
            web_search_read(domain, fields=None,
                            offset=offset, limit=limit, order='')
        for record in records['records']:
            detail = http.request.env['sharevan.bill.lading.detail']. \
                web_search_read([['bill_lading_id', '=', record['id']]], fields=None,
                                offset=0, limit=80, order='')
            details = detail['records']
            for bill_detail in details:
                billService = http.request.env['sharevan.service.type']. \
                    web_search_read([['id', 'in', bill_detail['service_id']]], fields=None,
                                    offset=0, limit=80, order='')
                bill_detail['billService'] = billService['records']
                bill_packages = http.request.env['sharevan.bill.package']. \
                    web_search_read([['bill_lading_detail_id', '=', bill_detail['id']]], fields=None,
                                    offset=0, limit=80, order='')
                bill_detail['bill_packages'] = bill_packages['records']
            record['arrBillLadingDetail'] = details
        query = """select count(id) from sharevan_bill_lading """
        query += where_sql
        http.request.env.cr.execute(query, param)
        count = http.request._cr.fetchall()
        records['total_record'] = count[0][0]
        return records

    def get_bill_lading_history_ad(self, **kwargs):
        param = []
        offset = 0
        limit = 10
        page =''
        where_sql = """ where 1 = 1 """
        text_search = kwargs.get('text_search')
        bill_state = kwargs.get('bill_state')
        if text_search:
            where_sql += """ and  LOWER(bill_lading.name)  like LOWER('%%%s%%') """ % (text_search,)
        for arg in kwargs:
            if arg == 'start_date' and kwargs.get(arg) is not None:
                start_date = kwargs.get(arg)
                start_date += " 00:00:00 "
                # to_date += " 23:59:59 "
                where_sql += """ and bill_lading.create_date >= '%s' """ % (start_date,)
                # param.append(kwargs.get(arg))
                continue
            elif arg == 'offset':
                offset = kwargs.get(arg)
            elif arg == 'limit':
                limit = kwargs.get(arg)
            elif arg == 'end_date' and kwargs.get(arg) is not None:
                end_date = kwargs.get(arg)
                end_date += " 00:00:00 "
                where_sql += """ and bill_lading.create_date <= '%s' """ % (end_date,)
                # param.append(kwargs.get(arg))
                continue
            elif arg == 'day_of_week' and kwargs.get(arg) is not None:
                where_sql += """ and extract(isodow from bill_lading.create_date) = '%s' """ % (kwargs.get(arg),)
                # param.append(kwargs.get(arg))
            elif arg == 'day_of_month' and kwargs.get(arg) is not None:
                where_sql += """ and extract(day from bill_lading.create_date) = '%s' """ % (kwargs.get(arg),)
                # param.append(kwargs.get(arg))
            elif arg != 'text_search' and arg != 'bill_state' and kwargs.get(arg) is not None:
                where_sql += """ and bill_lading.""" + arg + """ = '%s' """ % (kwargs.get(arg),)
                # param.append(kwargs.get(arg))
                continue
        if bill_state:
            if bill_state=='running':
                where_sql += """ and bill_lading.end_date > CURRENT_DATE """
            else:
                where_sql += """ and bill_lading.end_date < CURRENT_DATE """
        page = ' offset ' + str(offset) + ' limit ' + str(limit) + ' )t'
        query = """
            SELECT json_agg(t)
            FROM ( SELECT 
                bill_lading.id, bill_lading.name_seq, insurance.name insurance_name,
                bill_lading.total_weight, bill_lading.total_amount, 
                bill_lading.tolls,  bill_lading.surcharge, bill_lading.total_volume,
                bill_lading.vat, bill_lading.promotion_code, bill_lading.release_type,
                bill_lading.total_parcel, bill_lading.company_id, bill_lading.order_package_id,pack.name order_package_name,
                TO_CHAR(bill_lading.start_date, 'YYYY-MM-DD HH24:MI:SS')  start_date, 
                TO_CHAR(bill_lading.end_date, 'YYYY-MM-DD HH24:MI:SS') end_date, bill_lading.status, 
                bill_lading.description,bill_lading.name,
                bill_lading.create_uid,
                TO_CHAR( bill_lading.create_date, 'YYYY-MM-DD HH24:MI:SS') create_date, bill_lading.write_uid,
                TO_CHAR( bill_lading.write_date, 'YYYY-MM-DD HH24:MI:SS') write_date,subscribe.name subscribe_name, frequency, "day_of_week", "day_of_month"
            FROM public.sharevan_bill_lading bill_lading
                left join sharevan_bill_order_package pack on pack.id = bill_lading.order_package_id
                left join public.sharevan_subscribe subscribe on subscribe.id = bill_lading.subscribe_id
                left join public.sharevan_insurance insurance on insurance.id = bill_lading.insurance_id
        """
        query += where_sql
        query += ' order by create_date desc '
        query += page
        http.request.env.cr.execute(query,())
        result = http.request._cr.fetchall()
        length = len(result)
        jsonRe = []
        if length > 0:
            if result[0][0]:
                length = len(result[0][0])
                for rec in result[0][0]:
                    bill_state_record='running'
                    if datetime.strptime(rec['end_date'], "%Y-%m-%d %H:%M:%S").date()  < datetime.today().date():
                        bill_state_record = 'finished'
                    vals = {
                        "id": rec['id'],
                        "name_seq": rec['name_seq'],
                        "insurance_name": rec['insurance_name'],
                        "total_weight": rec['total_weight'],
                        "total_amount": rec['total_amount'],
                        "tolls": rec['tolls'],
                        "surcharge": rec['surcharge'],
                        "total_volume": rec['total_volume'],
                        "vat": rec['vat'],
                        "promotion_code": rec['promotion_code'],
                        "release_type": rec['release_type'],
                        "total_parcel": rec['total_parcel'],
                        "company_id": rec['company_id'],
                        "start_date": rec['start_date'],
                        "end_date": rec['end_date'],
                        "status": rec['status'],
                        "description": rec['description'],
                        "name": rec['name'],
                        "create_uid": rec['create_uid'],
                        "create_date": rec['create_date'],
                        "bill_state": bill_state_record,
                        "write_uid": rec['write_uid'],
                        "write_date": rec['write_date'],
                        "subscribe_name": rec['subscribe_name'],
                        "frequency": rec['frequency'],
                        "day_of_week": rec['day_of_week'],
                        "day_of_month": rec['day_of_month'],
                        "order_package": {
                            'id': rec['order_package_id'],
                            'name': rec['order_package_name'],
                        },
                    }
                    jsonRe.append(vals)
            else:
                length=0
        else:
            length=0
        simplejson.dumps(jsonRe, indent=4, sort_keys=True, default=str)
        count_query = """select count(id) from sharevan_bill_lading bill_lading """
        count_query += where_sql
        http.request.env.cr.execute(count_query, param)
        count = http.request._cr.fetchall()
        return {
            'total_record': count[0][0],
            'length': length,
            'records': jsonRe
        }

    def bill_lading_history_web(self ,pageNumber,pageSize):
        bill_state = None
        session,data_json = BaseMethod.check_authorized()
        if not session:
            return Response(json.dumps('UN_AUTHORIZED'), content_type="application/json", status=403)
        param = []
        offset = 0
        limit = 10
        page =''
        where_sql = """ where 1 = 1 """
        if 'bill_state' in data_json and data_json['bill_state']:
            bill_state = data_json['bill_state']

        if 'status' in data_json and data_json['status']!='' and data_json['status'] !='all':
            where_sql += """ and  bill_lading.status = '%s' """ % (data_json['status'],)
        # if 'company_id' in data_json and  data_json['company_id']:

        where_sql += """ and  bill_lading.company_id  = %s """ % (str(session['company_id']),)
        if 'text_search' in data_json and  data_json['text_search']:
            where_sql += """ and  LOWER(bill_lading.name)  like LOWER('%%%s%%') """ % (data_json['text_search'],)
        if  'start_date' in data_json and data_json['start_date'] is not None:
            start_date = data_json['start_date']
            start_date += " 00:00:00 "
            # to_date += " 23:59:59 "
            where_sql += """ and bill_lading.create_date >= '%s' """ % (start_date,)
            # param.append(kwargs.get(arg))
        offset = str((int(pageNumber)-1) * int(pageSize))
        limit = pageSize
        if 'end_date' in data_json and data_json['end_date'] is not None:
            end_date = data_json['end_date']
            end_date += " 00:00:00 "
            where_sql += """ and bill_lading.create_date <= '%s' """ % (end_date,)
        if 'day_of_week' in data_json and data_json['day_of_week'] is not None and data_json['day_of_week']!='':
            day_of_week = data_json['day_of_week'].split(',')
            if len(day_of_week)>0:
                where_sql += """ and bill_lading.day_of_week in  ("""
                for day in day_of_week:
                    where_sql += day+','
                where_sql = where_sql[:-1]
                where_sql += ')'
            # param.append(kwargs.get(arg))
        if 'day_of_month' in data_json and data_json['day_of_month'] is not None and data_json['day_of_month']!= '':
            where_sql += """ and  bill_lading.day_of_month = '%s'::int8 """ % (data_json['day_of_month'],)
        if 'order_package_id' in data_json and data_json['order_package_id'] is not None and data_json['order_package_id']!='_':
            where_sql += """ and  pack.type = '%s' """ % (data_json['order_package_id'],)
            # param.append(kwargs.get(arg))
        if bill_state:
            if bill_state=='running':
                where_sql += """ and bill_lading.end_date > CURRENT_DATE """
            else:
                where_sql += """ and bill_lading.end_date < CURRENT_DATE """
        page = ' offset ' + str(offset) + ' limit ' + str(limit) + ' )t'
        query = """
            SELECT json_agg(t)
            FROM ( SELECT 
                bill_lading.id, bill_lading.name_seq, insurance.name insurance_name,
                bill_lading.total_weight, bill_lading.total_amount, 
                bill_lading.tolls,  bill_lading.surcharge, bill_lading.total_volume,
                bill_lading.vat, bill_lading.promotion_code, bill_lading.release_type,
                bill_lading.total_parcel, bill_lading.company_id, bill_lading.order_package_id,pack.name order_package_name,
                TO_CHAR(bill_lading.start_date, 'YYYY-MM-DD HH24:MI:SS')  start_date, 
                TO_CHAR(bill_lading.end_date, 'YYYY-MM-DD HH24:MI:SS') end_date, bill_lading.status, 
                bill_lading.description,bill_lading.name,
                bill_lading.create_uid, award.name title_award_name,partner.name user_book_name,
                TO_CHAR( bill_lading.create_date, 'YYYY-MM-DD HH24:MI:SS') create_date, bill_lading.write_uid,
                TO_CHAR( bill_lading.write_date, 'YYYY-MM-DD HH24:MI:SS') write_date,subscribe.name subscribe_name, frequency, "day_of_week", "day_of_month"
            FROM public.sharevan_bill_lading bill_lading
                left join sharevan_bill_order_package pack on pack.id = bill_lading.order_package_id
                left join public.sharevan_subscribe subscribe on subscribe.id = bill_lading.subscribe_id
                left join public.sharevan_insurance insurance on insurance.id = bill_lading.insurance_id
                left join sharevan_title_award award on award.id = bill_lading.award_company_id
                join res_users us on us.id = bill_lading.create_uid
                join res_partner partner on partner.id = us.partner_id
        """
        query += where_sql
        query += ' order by create_date desc '
        query += page
        http.request.env.cr.execute(query,())
        result = http.request._cr.fetchall()
        length = len(result)
        jsonRe = []
        if length > 0:
            if result[0][0]:
                length = len(result[0][0])
                for rec in result[0][0]:
                    bill_state_record='running'
                    if datetime.strptime(rec['end_date'], "%Y-%m-%d %H:%M:%S").date()  < datetime.today().date():
                        bill_state_record = 'finished'
                    vals = {
                        "id": rec['id'],
                        "name_seq": rec['name_seq'],
                        "insurance_name": rec['insurance_name'],
                        "total_weight": rec['total_weight'],
                        "total_amount": rec['total_amount'],
                        "tolls": rec['tolls'],
                        "surcharge": rec['surcharge'],
                        "total_volume": rec['total_volume'],
                        "vat": rec['vat'],
                        "promotion_code": rec['promotion_code'],
                        "release_type": rec['release_type'],
                        "total_parcel": rec['total_parcel'],
                        "company_id": rec['company_id'],
                        "start_date": rec['start_date'],
                        "end_date": rec['end_date'],
                        "status": rec['status'],
                        "description": rec['description'],
                        "name": rec['name'],
                        "create_uid": rec['create_uid'],
                        "title_award_name": rec['title_award_name'],
                        "create_date": rec['create_date'],
                        "bill_state": bill_state_record,
                        "write_uid": rec['write_uid'],
                        "write_date": rec['write_date'],
                        "subscribe_name": rec['subscribe_name'],
                        "frequency": rec['frequency'],
                        "user_book_name": rec['user_book_name'],
                        "day_of_week": rec['day_of_week'],
                        "day_of_month": rec['day_of_month'],
                        "order_package": {
                            'id': rec['order_package_id'],
                            'name': rec['order_package_name'],
                        },
                    }
                    jsonRe.append(vals)
            else:
                length=0
        else:
            length=0
        count_query = """
            select count(bill_lading.id) from sharevan_bill_lading bill_lading
                left join sharevan_bill_order_package pack on pack.id = bill_lading.order_package_id
                left join public.sharevan_subscribe subscribe on subscribe.id = bill_lading.subscribe_id
                left join public.sharevan_insurance insurance on insurance.id = bill_lading.insurance_id
                left join sharevan_title_award award on award.id = bill_lading.award_company_id           
            """
        count_query += where_sql
        http.request.env.cr.execute(count_query, param)
        count = http.request._cr.fetchall()
        result= {
            'totalElements': count[0][0],
            'size': int(pageSize),
            'number': int(pageNumber)-1,
            'content': jsonRe
        }
        return  Response(json.dumps(result), content_type="application/json", status=200)

    def create_dlp_from_so(self, soInfor, company_name, access_token):
        access_token = 'Bearer ' + access_token
        me = AuthSsoApi.get(self, access_token, 'en', "/user/me",None)
        response_data = {}
        bytesThing = str(me, 'utf-8')
        data_json = json.dumps(bytesThing)

        if 'authorities' in bytesThing:
            list_so = []
            uid = request.session.post_sso_authenticate(config['database'], config['account_mfunction'])
            request.env['ir.http'].session_info()['uid'] = uid
            request.env['ir.http'].session_info()['login_success'] = True
            request.env['ir.http'].session_info()


            order_package = http.request.env['sharevan.bill.order.package'].search(
                [('type', '=', OrderPackage.Economy.value)]).id


            if soInfor:
                for so in soInfor:
                    sql_area_zone_hub_depot_id = """SELECT json_agg(t)
                                                FROM ( Select sa.id as area_id , sa.zone_area_id,sa.hub_id,depot.id as depot_id
                                                    From public.sharevan_warehouse sw
                                                    left join public.sharevan_area sa on sw.area_id = sa.id
                                                    left join public.sharevan_depot depot on depot.zone_id = sa.zone_area_id
                                                    where sw.id = %s )t"""
                    arr_address = []
                    sql_area_zone_hub_depot_id_dc = {}
                    sql_area_zone_hub_depot_id_l1 = {}
                    adrress_dc = http.request.env['sharevan.warehouse'].search([('address', '=', so['dc_info']['address'].strip()),('name', '=', so['dc_info']['name'].strip()),('phone', '=', so['dc_info']['phone'].strip()),('company_id', '=', http.request.env.company.id)])
                    adrress_l1 = http.request.env['sharevan.warehouse'].search([('address', '=', so['l1_info']['address'].strip()),('name', '=', so['l1_info']['name'].strip()),('phone', '=', so['l1_info']['phone'].strip()),('company_id', '=', http.request.env.company.id)])

                    #Kiểm tra qr code đã tồn tại hay chưa
                    sharevan_bill_lading = http.request.env['sharevan.bill.lading'].search(
                        [('qr_code', '=', so['qr_code'])])
                    if sharevan_bill_lading :
                        return {
                            'status': 204,
                            'message': 'QR code already %s exists  !' % (
                            so['qr_code'])
                        }

                    # check insurance
                    if so['insurance']:
                        insurance_id = http.request.env['sharevan.insurance'].search(
                            [('id', '=', so['insurance']),('status', '=', 'running')]).id
                        if insurance_id == False:
                            return {
                                'status': 204,
                                'message': 'Insurance does not exist for bill of lading orders with QR code %s !' % (so['qr_code'])
                            }

                    if adrress_dc['address'] == False:
                        arr_address.append('dc')
                        # Check phone , name, address khi tạo warehouse dc
                        check_warehouse_querry = """select name,address,phone from sharevan_warehouse
                                                                            where (name ilike '%s' or address ilike '%s' or phone ilike '%s') and status = 'running' and company_id = %s""" % (
                            so['dc_info']['name'], so['dc_info']['address'],so['dc_info']['phone'],http.request.env.company.id)
                        http.request.env[WarehouseApi.MODEL]._cr.execute(check_warehouse_querry)
                        check_record_check = http.request.env[WarehouseApi.MODEL]._cr.dictfetchall()
                        if check_record_check:
                            for rec in check_record_check:
                                if rec['name'] == so['dc_info']['name']:
                                    error = "Name:  %s  already exists !" % (so['dc_info']['name'])
                                    return {
                                        'status': 204,
                                        'message': error
                                    }
                                if rec['phone'] == so['dc_info']['phone']:
                                    error = "Phone:  %s  already exists !" % (so['dc_info']['phone'])
                                    return {
                                        'status': 204,
                                        'message': error
                                    }
                                if rec['address'] == so['dc_info']['address']:
                                    error = "Address:  %s  already exists !" % (so['dc_info']['address'])
                                    return {
                                        'status': 204,
                                        'message': error
                                    }

                    else:
                        self.env.cr.execute(sql_area_zone_hub_depot_id, (adrress_dc['id'],))
                        result = self._cr.fetchall()
                        sql_area_zone_hub_depot_id_dc = result[0][0][0]
                    if adrress_l1['address'] == False:
                        arr_address.append('l1')
                        # Check phone , name, address khi tạo warehouse l1
                        check_warehouse_querry = """select name,address,phone from sharevan_warehouse
                                                                                                    where (name ilike '%s' or address ilike '%s' or phone ilike '%s') and company_id = %s""" % (
                            so['l1_info']['name'], so['l1_info']['address'], so['l1_info']['phone'],
                            http.request.env.company.id)
                        http.request.env[WarehouseApi.MODEL]._cr.execute(check_warehouse_querry)
                        check_record_check = http.request.env[WarehouseApi.MODEL]._cr.dictfetchall()
                        if check_record_check:
                            for rec in check_record_check:
                                if rec['name'] == so['l1_info']['name']:
                                    error = "Name:  %s  already exists !" % (so['l1_info']['name'])
                                    return {
                                        'status': 204,
                                        'message': error
                                    }
                                if rec['phone'] == so['l1_info']['phone']:
                                    error = "Phone:  %s  already exists !" % (so['l1_info']['phone'])
                                    return {
                                        'status': 204,
                                        'message': error
                                    }
                                if rec['address'] == so['l1_info']['address']:
                                    error = "Address:  %s  already exists !" % (so['l1_info']['address'])
                                    return {
                                        'status': 204,
                                        'message': error
                                    }
                    else:
                        self.env.cr.execute(sql_area_zone_hub_depot_id, (adrress_l1['id'],))
                        result = self._cr.fetchall()
                        sql_area_zone_hub_depot_id_l1 = result[0][0][0]

                    if len(arr_address) > 0:
                        list_address = []
                        arr_area = []
                        for add in arr_address:
                            # api_key = http.request.env['ir.config_parameter'].sudo().get_param('google.api_key_geocode')
                            gmaps = googlemaps.Client(key='AIzaSyDbIf1-IDfQ0DGaOvAfu5lNZ0bZm0VaisM')

                            address_warehouse = so['dc_info']['address'] if add == 'dc' else so['l1_info']['address']

                            place = gmaps.find_place(input=address_warehouse, input_type="textquery",
                                                     fields=['geometry', 'place_id'])

                            lat = round(place['candidates'][0]['geometry']['location']['lat'], 5)
                            long = round(place['candidates'][0]['geometry']['location']['lng'], 5)

                            name = so['dc_info']['name'] if add == 'dc' else so['l1_info']['name']
                            wards = so['dc_info']['wards'] if add == 'dc' else so['l1_info']['wards']
                            list_address.append(wards)

                            district = so['dc_info']['district'] if add == 'dc' else so['l1_info']['district']
                            list_address.append(district)

                            province = so['dc_info']['province'] if add == 'dc' else so['l1_info']['province']
                            list_address.append(province)

                            country = so['dc_info']['country'] if add == 'dc' else so['l1_info']['country']
                            country_id = self.env['res.country'].search([('name', '=', country)]).id

                            phone = so['dc_info']['phone'] if add == 'dc' else so['l1_info']['phone']
                            area_id = None
                            sql_routing_plan_day_pendding = """SELECT * FROM public.sharevan_area
                                                        where name iLIKE '%%%s'  and  district_name iLIKE  '%%%s' and province_name  iLIKE '%%%s'  and status = 'running'
                                                                          """ % (wards, district, province)
                            self.env.cr.execute(sql_routing_plan_day_pendding, ())
                            result = self._cr.fetchall()
                            if len(result) > 0:
                                area_id = result[0][0]
                            else:
                                return 'Your %s address is not in the area !' % (address_warehouse)
                            value = {}
                            if area_id:
                                self.env.cr.execute("""SELECT json_agg(t)
                                                FROM (Select sa.id as area_id , sa.zone_area_id,sa.hub_id,depot.id as depot_id
                                                    from public.sharevan_area sa
                                                    left join public.sharevan_depot depot on depot.zone_id = sa.zone_area_id
                                                    where sa.id = %s ) t""", (area_id,))
                                result = self._cr.fetchall()
                                query_province_district_township = """ SELECT id, location_type FROM public.sharevan_area
                                                        where (name iLIKE  ('%%%s') and location_type = 'province'  and status = 'running') 
														or (name iLIKE  ('%%%s') and province_name iLIKE  ('%%%s') and location_type = 'district'  and status = 'running')
														or (name iLIKE  ('%%%s') and province_name iLIKE  ('%%%s') and district_name iLIKE  ('%%%s')  
														and location_type = 'township'  and status = 'running') """ % (
                                    province, district, province, wards, province, district)
                                self.env.cr.execute(query_province_district_township, ())
                                result_province_district_township = self._cr.fetchall()
                                value = {
                                    'name': name,
                                    'phone': phone,
                                    # 'district':district,
                                    # 'customer_id': '',
                                    'country_id': country_id,
                                    'address': address_warehouse,
                                    'area_id': area_id,
                                    'latitude': lat,
                                    'longitude': long,
                                    'company_id' : http.request.env.company.id
                                }
                                for res in result_province_district_township:
                                    if res[1] == 'district':
                                        value['district'] = res[0]
                                    elif res[1] == 'province':
                                        value['state_id'] = res[0]
                                    elif res[1] == 'township':
                                        value['ward'] = res[0]
                            warehouse = http.request.env['sharevan.warehouse'].sudo().create(value)
                            arr_area.append({
                                'warehouse_type': add,
                                'warehouse': warehouse if area_id else None,
                                'zone_area_hub-depot_id': result[0][0][0] if area_id else {
                                    'area_id': None,
                                    'zone_area_id': None,
                                    'hub_id': None,
                                    'depot_id': None,
                                }
                            })

                    vals = {}
                    total_weight = 0
                    date_start = datetime.strptime(so['start_time'], '%Y-%m-%d').date()
                    date_start_d = date_start + timedelta(hours=24)
                    expected_from_time = datetime.strptime(str(date_start_d), '%Y-%m-%d') + timedelta(hours=1)
                    expected_to_time = datetime.strptime(str(date_start_d), '%Y-%m-%d') + timedelta(hours=13)
                    bill_lading_detail = []
                    vals['cycle_type'] = '5'
                    vals['start_date'] = str(date_start_d)
                    vals['frequency'] = 5
                    vals['chooseDay'] = str(date_start_d)
                    vals['subscribe_id'] = False
                    vals['release_type'] = 0
                    vals['promotion_code'] = 0
                    vals['tolls'] = 0
                    vals['surcharge'] = 0
                    vals['vat'] = 0
                    vals['qr_code'] = so['qr_code']
                    vals['sbl_type'] = 'SO'
                    vals['company_id'] = http.request.env.company.id
                    vals['insurance_id'] = so['insurance']
                    vals['order_package_id'] = order_package
                    for warehouse_type in ['0', '1']:
                        if warehouse_type is '0':
                            dc = ''
                            index_dc = 0
                            count_dc = 0
                            for type_warahouse in arr_address:
                                index_dc += 1
                                if type_warahouse == 'dc':
                                    dc = type_warahouse
                                    index_dc = index_dc
                                    break
                            warehouse_type = warehouse_type
                            warehouse_name = so['dc_info']['name'] if dc == 'dc' else adrress_dc['name']

                            # Check dịch vụ ở kho
                            service_id = []
                            if so['dc_info']['service_type']:
                                for service in so['dc_info']['service_type']:
                                    service_type_id = http.request.env['sharevan.service.type'].search(
                                        [('id', '=', service), ('status', '=', 'running')]).id
                                    if service_type_id == False:
                                        return {
                                            'status': 204,
                                            'message': 'The service at the warehouse does not exist in the order with code qr %s !' % (
                                            so['qr_code'])
                                        }
                                service_id = so['l1_info']['service_type']
                            warehouse_id = arr_area[index_dc - 1]['warehouse']['id'] if dc == 'dc' else adrress_dc['id']
                            address = arr_area[index_dc - 1]['warehouse']['address'] if dc == 'dc' else adrress_dc[
                                'address']
                            latitude = arr_area[index_dc - 1]['warehouse']['latitude'] if dc == 'dc' else adrress_dc[
                                'latitude']
                            longitude = arr_area[index_dc - 1]['warehouse']['longitude'] if dc == 'dc' else adrress_dc[
                                'longitude']
                            phone = arr_area[index_dc - 1]['warehouse']['phone'] if dc == 'dc' else adrress_dc['phone']
                            area_id = arr_area[index_dc - 1]['zone_area_hub-depot_id']['area_id'] if dc == 'dc' else \
                                sql_area_zone_hub_depot_id_dc['area_id']
                            zone_area_id = arr_area[index_dc - 1]['zone_area_hub-depot_id'][
                                'zone_area_id'] if dc == 'dc' else sql_area_zone_hub_depot_id_dc['zone_area_id']
                            hub_id = arr_area[index_dc - 1]['zone_area_hub-depot_id']['hub_id'] if dc == 'dc' else \
                                sql_area_zone_hub_depot_id_dc['hub_id']
                            depot_id = arr_area[index_dc - 1]['zone_area_hub-depot_id']['depot_id'] if dc == 'dc' else \
                                sql_area_zone_hub_depot_id_dc['depot_id']
                            user_id = False
                        else:
                            l1 = ''
                            index_l1 = 0
                            count_l1 = 0
                            for type_warahouse in arr_address:
                                count_l1 += 1
                                if type_warahouse == 'l1':
                                    l1 = type_warahouse
                                    index_l1 = count_l1
                                    break
                            warehouse_type = warehouse_type
                            warehouse_name = so['dc_info']['name'] if l1 == 'l1' else adrress_l1['name']

                            # Check dịch vụ ở kho
                            service_id = []
                            if so['l1_info']['service_type'] :
                                for service in so['l1_info']['service_type'] :
                                    service_type_id = http.request.env['sharevan.service.type'].search(
                                        [('id', '=', service),('status', '=', 'running')]).id
                                    if service_type_id == False:
                                        return {
                                            'status': 204,
                                            'message': 'The service does not exist in the order with code qr %s!' % (so['qr_code'])
                                        }
                                service_id = so['l1_info']['service_type']

                            warehouse_id = arr_area[index_l1 - 1]['warehouse']['id'] if l1 == 'l1' else adrress_l1['id']
                            address = arr_area[index_l1 - 1]['warehouse']['address'] if l1 == 'l1' else adrress_l1[
                                'address']
                            latitude = arr_area[index_l1 - 1]['warehouse']['latitude'] if l1 == 'l1' else adrress_l1[
                                'latitude']
                            longitude = arr_area[index_l1 - 1]['warehouse']['longitude'] if l1 == 'l1' else adrress_l1[
                                'longitude']
                            phone = arr_area[index_l1 - 1]['warehouse']['phone'] if l1 == 'l1' else adrress_l1['phone']
                            area_id = arr_area[index_l1 - 1]['zone_area_hub-depot_id']['area_id'] if l1 == 'l1' else \
                                sql_area_zone_hub_depot_id_l1['area_id']
                            zone_area_id = arr_area[index_l1 - 1]['zone_area_hub-depot_id'][
                                'zone_area_id'] if l1 == 'l1' else sql_area_zone_hub_depot_id_l1['zone_area_id']
                            hub_id = arr_area[index_l1 - 1]['zone_area_hub-depot_id']['hub_id'] if l1 == 'l1' else \
                                sql_area_zone_hub_depot_id_l1['hub_id']
                            depot_id = arr_area[index_l1 - 1]['zone_area_hub-depot_id']['depot_id'] if l1 == 'l1' else \
                                sql_area_zone_hub_depot_id_l1['depot_id']
                            user_id = so['l1_info']['user_id']
                        bill_lading_detail.append(
                            [0, 'virtual_73',
                             {
                                 'warehouse_type': warehouse_type,
                                 'order_type': '0',
                                 'service_id': [[6, False, service_id]],
                                 'expected_from_time': str(expected_from_time),
                                 'expected_to_time': str(expected_to_time),
                                 '__last_update': False,
                                 'warehouse_id': warehouse_id,
                                 'warehouse_name': warehouse_name,
                                 'from_warehouse_id': False,
                                 'street': False, 'zip': False,
                                 'city_name': False,
                                 'country_id': False,
                                 'state_id': False,
                                 'district': False,
                                 'ward': False,
                                 'address': address,
                                 'street2': False,
                                 'latitude': latitude,
                                 'longitude': longitude,
                                 'phone': phone,
                                 'zone_area_id': zone_area_id,
                                 'area_id': area_id,
                                 'hub_id': hub_id,
                                 'depot_id': depot_id,
                                 'price': False,
                                 'user_id': user_id
                             }]

                        )
                    bill_package_line = []
                    key_map = 0
                    for index in [0, 1]:
                        for package in so['product_info']:
                            key_map +=1
                            if index is 0:
                                total_weight += package['net_weight']

                            sql_product_type = """SELECT json_agg(t)
                                                    FROM ( select DISTINCT parent.id from sharevan_product_type parent
                                                            join sharevan_product_type sub on sub.parent_id = parent.id
                                                            join sharevan_product product on product.product_type_id = sub.id
                                                            where product.name ilike '%%%s'  and parent.status = 'running' )t""" %(package['commodities_type'])
                            self.env.cr.execute(sql_product_type)
                            result_product_type = self._cr.fetchall()

                            if result_product_type[0][0] == None:
                                return  {
                                    'status': 204,
                                    'message': 'Commodities %s does not exist !' % (package['commodities_type'])
                                }


                            bill_package_line.append([0, 'virtual_73',
                                                      {'name': 'New', 'qr_code': False, '__last_update': False,
                                                       'product_type_id': result_product_type[0][0][0]['id'],
                                                       'net_weight': package['net_weight'],
                                                       'quantity_package': package['quantity'], 'item_name': False,
                                                       'length': package['leng'],
                                                       'item_name': package['item_name'],
                                                       'commodities_type': package['commodities_type'] ,
                                                       'width': package['width'], 'height': package['height'],
                                                       'key_map':key_map,
                                                       'capacity': False, 'description': False}])
                        key_map = 0
                        bill_lading_detail[index][2]['bill_package_line'] = bill_package_line
                        bill_package_line = []
                    vals['bill_lading_detail_ids'] = bill_lading_detail
                    vals['total_weight'] = total_weight
                    list_so.append(vals)
                    # http.request.env['sharevan.bill.lading'].sudo().create(vals)
                for so in list_so :
                    http.request.env['sharevan.bill.lading'].sudo().create(so)
                return 'Create Dlp from So success !'
            else:
                raise ValidationError("Dlp creation failed")
        else:
            error = "Error : Invalid token %s " % (access_token,)
            raise ValidationError(error)

    def list_routing_plan_day_pending(self, datePlan, access_token):
        status_draft = RoutingPlanDay.Draft.value
        so_type = RoutingPlanDay.SoType.value
        access_token = 'Bearer ' + access_token
        me = AuthSsoApi.get(self, access_token, 'en', "/user/me",None)
        response_data = {}
        bytesThing = str(me, 'utf-8')
        data_json = json.dumps(bytesThing)
        if 'authorities' in bytesThing:
            uid = request.session.post_sso_authenticate(config['database'], config['account_mfunction'])
            request.env['ir.http'].session_info()['uid'] = uid
            request.env['ir.http'].session_info()['login_success'] = True
            request.env['ir.http'].session_info()
            sql_routing_plan_day_pendding = """
                                                SELECT json_agg(t)
                                                    FROM ( SELECT rou_plan_day.id,
                                                                  rou_plan_day.qr_so,
                                                                  rou_plan_day.date_plan,
                                                                  driver.id as driver_id,
                                                                  driver.name as driver_name ,
                                                                  driver.phone as driver_phone,
                                                                  driver.email,
                                                                  driver.address,
                                                                  vehicle.id as vehicle_id,
                                                                  vehicle.name as vehicle_name ,
                                                                  vehicle.capacity,
                                                                  vehicle.license_plate,
                                                                  vehicle.model_year,
                                                                  TO_CHAR(rou_plan_day.expected_from_time, 'DD-MM-YYYY HH24:MI:SS') expected_from_time,
                                                                  TO_CHAR(rou_plan_day.expected_to_time, 'DD-MM-YYYY HH24:MI:SS') expected_to_time,
                                                                  warehouse_from.name as from_warehouse_name,
                                                                  warehouse_from.address as from_warehouse_address,
                                                                  warehouse_from.phone as from_warehouse_phone,
                                                                  warehouse_to.name as to_warehouse_name,
                                                                  warehouse_to.address as to_warehouse_address,
                                                                  warehouse_to.phone as to_warehouse_phone,
																  lading_detail.id as iddd
                                                    FROM public.sharevan_routing_plan_day rou_plan_day
                                                        left join public.fleet_vehicle vehicle on vehicle.id = rou_plan_day.vehicle_id
                                                        left join public.fleet_driver driver on driver.id = rou_plan_day.driver_id
                                                        left join sharevan_bill_lading_detail lading_detail on lading_detail.id = rou_plan_day.bill_lading_detail_id 
                                                        left join sharevan_bill_lading bill_lading on bill_lading.id = lading_detail.bill_lading_id 
														left join sharevan_bill_lading_detail lading_detail_from on lading_detail_from.bill_lading_id = bill_lading.id and lading_detail_from.warehouse_type = '0'
                                                        left join sharevan_bill_lading_detail lading_detail_to on lading_detail_to.bill_lading_id = bill_lading.id  and lading_detail_to.warehouse_type = '1'
														left join public.sharevan_warehouse warehouse_from on warehouse_from.id = lading_detail_from.warehouse_id
                                                        left join public.sharevan_warehouse warehouse_to on warehouse_to.id = lading_detail_to.warehouse_id
                                                    WHERE rou_plan_day.status = %s and rou_plan_day.date_plan = %s and rou_plan_day.so_type = %s
                                                    Order by expected_from_time ASC
                                                ) t"""
            self.env.cr.execute(sql_routing_plan_day_pendding, (status_draft, datePlan, so_type))
            result = self._cr.fetchall()
            list_so_pendding = []
            if result[0][0] != None:
                list_routing = []
                list_routing_driver_vehicle = []
                list_routing_no_driver_vehicle = []
                res = result[0][0]
                arr_check = []
                count = 0
                for re in res:
                    if count not in arr_check:
                        count += 1
                        driver_vehicle = {
                            'driver': {
                                'id': re['driver_id'],
                                'name': re['driver_name'],
                                'phone': re['driver_phone'],
                                'email': re['email'],
                                'address': re['address'],
                            },
                            'vehicle': {
                                'id': re['vehicle_id'],
                                'name': re['vehicle_name'],
                                'license_plate': re['license_plate'],
                                'model_year': re['model_year'],
                                'capacity': re['capacity'],
                            },
                            'list_so': [{
                                'routing_id': re['id'],
                                'qr_code': re['qr_so'],
                                'from_warehouse': {
                                    'name': re['from_warehouse_name'],
                                    'phone': re['from_warehouse_phone'],
                                    'address': re['from_warehouse_address'],
                                    'expected_from_time': re['expected_from_time'],
                                },
                                'to_warehouse': {
                                    'name': re['to_warehouse_name'],
                                    'phone': re['to_warehouse_phone'],
                                    'address': re['to_warehouse_address'],
                                    'expected_to_time': re['expected_to_time'],
                                }
                            }],
                        }
                        for x in range(count, len(res)):
                            if re['driver_id'] == result[0][0][x]['driver_id'] and re['vehicle_id'] == result[0][0][x][
                                'vehicle_id']:
                                driver_vehicle['list_so'].append({
                                    'routing_id': result[0][0][x]['id'],
                                    'qr_code': result[0][0][x]['qr_so'],
                                    'from_warehouse': {
                                        'name': result[0][0][x]['from_warehouse_name'],
                                        'phone': result[0][0][x]['from_warehouse_phone'],
                                        'address': result[0][0][x]['from_warehouse_address'],
                                        'expected_from_time': result[0][0][x]['expected_from_time'],
                                    },
                                    'to_warehouse': {
                                        'name': result[0][0][x]['to_warehouse_name'],
                                        'phone': result[0][0][x]['to_warehouse_phone'],
                                        'address': result[0][0][x]['to_warehouse_address'],
                                        'expected_to_time': result[0][0][x]['expected_to_time'],
                                    }
                                })
                                arr_check.append(x)
                        list_routing.append(driver_vehicle)
                    else:
                        count += 1
                    # list_so_pendding.append(content)
                for routing in list_routing:
                    if routing['driver']['id'] is None and routing['vehicle']['id'] is None:
                        list_routing_driver_vehicle.append(routing['list_so'])
                    else:
                        list_routing_no_driver_vehicle.append(routing)
                records = {
                    'total': len(list_routing),
                    'records':
                        {
                            'list_so_not_enough': list_routing_driver_vehicle,
                            'list_so_confirm': list_routing_no_driver_vehicle
                        }
                }
                simplejson.dumps(records, indent=4, sort_keys=True, default=str)
                return records

            return {
                'records': []
            }
        else:
            error = "Error : Invalid token %s " % (access_token,)
            raise ValidationError(error)

    def routing_plan_day_confirm_or_cancel_from_so(self, **kwargs):

        access_token = None
        listRoutingConfirm = None
        listRoutingCancel = None
        listRoutingCancelDriver = None
        date_plan = None

        list_routing_id_confirm = []
        list_routing_id_cancel = []
        list_driver_confirm = []

        for arg in kwargs:
            if arg == 'access_token':
                access_token = kwargs.get(arg)
            elif arg == 'list_routing_confirm':
                listRoutingConfirm = kwargs.get(arg)
            elif arg == 'list_routing_cancel':
                listRoutingCancel = kwargs.get(arg)
            elif arg == 'list_routing_cancel_driver':
                listRoutingCancelDriver = kwargs.get(arg)
            elif arg == 'date_plan':
                date_plan = kwargs.get(arg)

        if date_plan == None:
            return {
                'status': 204,
                'message': 'You must enter the date plan !'
            }
        if access_token :
            access_token = 'Bearer ' + access_token
            me = AuthSsoApi.get(self, access_token, 'en', "/user/me",None)
            response_data = {}
            bytesThing = str(me, 'utf-8')
            data_json = json.dumps(bytesThing)
        else:
            return {
                'status': 204,
                'message': 'You must enter the access token !'
            }
        if 'authorities' in bytesThing:

            uid = request.session.post_sso_authenticate(config['database'], config['account_mfunction'])
            request.env['ir.http'].session_info()['uid'] = uid
            request.env['ir.http'].session_info()['login_success'] = True
            request.env['ir.http'].session_info()


            if listRoutingConfirm :
                if len(listRoutingConfirm) > 0:
                    for routing in listRoutingConfirm :
                        if routing['driver_id'] is None or routing['vehicle_id'] is None or routing['list_routing_id'] is None or len(routing['list_routing_id']) == 0 :
                            return {
                                'status': 204,
                                'message': 'Driver_id and vehicle_id and list_routing_id cannot be empty !'
                            }
                        if isinstance(routing['driver_id'], str) or isinstance(routing['vehicle_id'], str) :
                            return {
                                'status': 204,
                                'message': 'Driver_id and vehicle_id and list_routing_id data type Interger !'
                            }
                        for id in routing['list_routing_id'] :
                            if isinstance(id, str) :
                                return {
                                    'status': 204,
                                    'message': 'Driver_id and vehicle_id and list_routing_id data type Interger !'
                                }

                        sql_routing_plan_confirm = """SELECT json_agg(t)
                                                        FROM (
                                                                select id from sharevan_routing_plan_day
                                                                where date_plan = %s and driver_id  = %s  and
                                                                      vehicle_id = %s and status = %s
                                                                        ) t"""
                        self.env.cr.execute(sql_routing_plan_confirm, (date_plan, routing['driver_id'], routing['vehicle_id'],RoutingPlanDay.Draft.value))
                        result = self._cr.fetchall()
                        if result[0][0] :
                            if len(result[0][0]) > len(routing['list_routing_id']):
                                return {
                                    'status': 204,
                                    'message': 'The list of routing ids you entered is missing , Driver id =  %s !' % (routing['driver_id'])
                                }
                            if len(result[0][0]) < len(routing['list_routing_id']):
                                return {
                                    'status': 204,
                                    'message': 'List of driver routing ids that have entered redundant ids , Driver id =  %s !' % (routing['driver_id'])
                                }
                            for routing_id in routing['list_routing_id']  :
                                check = 0
                                for re in result[0][0] :
                                    if re['id'] == routing_id :
                                        check = 1
                                        result[0][0].remove(re)
                                if check == 0:
                                    return {
                                        'status': 204,
                                        'message': 'Your Incorrect routing id = %s , Driver id =  %s !' % (routing_id,routing['driver_id'])
                                    }


                            for id in routing['list_routing_id']:
                                    list_routing_id_confirm.append(id)

                            list_driver_confirm.append(routing['driver_id'])
                        else :
                            return {
                                'status': 204,
                                'message': 'On %s driver id %s and vehicle id %s was approved !' % (date_plan, routing['driver_id'],routing['vehicle_id'])
                            }
            if listRoutingCancelDriver :
                if len(listRoutingCancelDriver) > 0:
                    for routing in listRoutingCancelDriver :
                        if routing['driver_id'] is None or routing['vehicle_id'] is None or routing[
                            'list_routing_id'] is None or len(routing['list_routing_id']) == 0:
                            return {
                                'status': 204,
                                'message': 'Driver_id and vehicle_id and list_routing_id cannot be empty !'
                            }
                        if isinstance(routing['driver_id'], str) or isinstance(routing['vehicle_id'], str) :
                            return {
                                'status': 204,
                                'message': 'Driver_id and vehicle_id and list_routing_id data type Interger !'
                            }

                        for id in routing['list_routing_id'] :
                            if isinstance(id, str) :
                                return {
                                    'status': 204,
                                    'message': 'Driver_id and vehicle_id and list_routing_id data type Interger !'
                                }
                        sql_routing_plan_confirm = """SELECT json_agg(t)
                                                        FROM (
                                                                select id from sharevan_routing_plan_day
                                                                where date_plan = %s and driver_id  = %s  and
                                                                      vehicle_id = %s and status = %s
                                                                        ) t"""
                        self.env.cr.execute(sql_routing_plan_confirm, (date_plan, routing['driver_id'], routing['vehicle_id'],RoutingPlanDay.Draft.value))
                        result = self._cr.fetchall()
                        if result[0][0] :
                            if len(result[0][0]) > len(routing['list_routing_id']):
                                return {
                                    'status': 204,
                                    'message': 'The list of routing ids cancel you entered is missing , Driver id =  %s !' % (routing['driver_id'])
                                }
                            if len(result[0][0]) < len(routing['list_routing_id']):
                                return {
                                    'status': 204,
                                    'message': 'List of driver routing ids cancel that have entered redundant ids , Driver id =  %s !' % (routing['driver_id'])
                                }
                            for routing_id in routing['list_routing_id']  :
                                check = 0
                                for re in result[0][0] :
                                    if re['id'] == routing_id :
                                        check = 1
                                        result[0][0].remove(re)
                                if check == 0:
                                    return {
                                        'status': 204,
                                        'message': 'Your Incorrect cancel routing id = %s , Driver id =  %s !' % (routing_id,routing['driver_id'])
                                    }


                            for id in routing['list_routing_id']:
                                    list_routing_id_cancel.append(id)
                        else :
                            return {
                                'status': 204,
                                'message': 'On %s driver id %s and vehicle id %s been canceled !' % (date_plan, routing['driver_id'],routing['vehicle_id'])
                            }
            if listRoutingCancel :
                if len(listRoutingCancel) > 0:
                    for id in listRoutingCancel :
                        sql_routing_plan_confirm = """SELECT json_agg(t)
                                                        FROM (
                                                                select id from sharevan_routing_plan_day
                                                                where date_plan = %s  and status = %s and id = %s and vehicle_id IS NULL and driver_id IS NULL
                                                                        ) t"""
                        self.env.cr.execute(sql_routing_plan_confirm, (date_plan,RoutingPlanDay.Draft.value,id))
                        result = self._cr.fetchall()
                        if result[0][0] :
                            list_routing_id_cancel.append(id)
                        else :
                                return {
                                    'status': 204,
                                    'message': 'The routing id %s is not in the correct state !' % (id)
                                }

            if len(list_routing_id_confirm) > 0 :
                query_update_list_routing_plan_day = "UPDATE public.sharevan_routing_plan_day  SET status = %s WHERE id IN ( "
                for id in list_routing_id_confirm:
                        query_update_list_routing_plan_day += str(id) + ","
                query_update_list_routing_plan_day_rs = query_update_list_routing_plan_day.rstrip(',')
                query_update_list_routing_plan_day_rs += " )"
                self.env.cr.execute(query_update_list_routing_plan_day_rs, (RoutingPlanDay.Unconfimred.value,))

            if len(list_routing_id_cancel) > 0:
                query_update_list_routing_plan_day = "UPDATE public.sharevan_routing_plan_day  SET status = %s WHERE id IN ( "
                for id in list_routing_id_cancel:
                    query_update_list_routing_plan_day += str(id) + ","
                    # update bill routing
                    sql_update_bill_routing = """Update sharevan_bill_routing
                                                 set status_routing = %s
                                                 where id  in (select bill_routing_id from sharevan_routing_plan_day
			                                                   where id = %s )""" % (BillRoutingStatus.Cancel.value,id)
                    self.env.cr.execute(sql_update_bill_routing)

                query_update_list_routing_plan_day_rs = query_update_list_routing_plan_day.rstrip(',')
                query_update_list_routing_plan_day_rs += " )"
                self.env.cr.execute(query_update_list_routing_plan_day_rs, (RoutingPlanDay.CancelSo.value,))
            if len(list_driver_confirm) > 0 :
                secret_key = config['client_secret']
                http.request.env[NotificationUser._name].notification_routing(list_driver_confirm, secret_key)

            # Thông báo DLP
            list_manager = BaseMethod.get_dlp_employee()
            if len(list_manager) >0:
                notice = ' We have confirmed or canceled the route !'
                content = {
                    'title': 'List of SO side applications have been confirmed. please check again !',
                    'content': notice,
                    'click_action': ClickActionType.driver_main_activity.value,
                    'message_type': MessageType.danger.value,
                    'type': NotificationType.RoutingMessage.value,
                    'object_status': ObjectStatus.ReloadRouting.value,
                    'item_id': 2
                }
                self.env['sharevan.notification'].sudo().create(content)
                for emp in list_manager:
                    user = self.env['res.users'].search([('id', '=', emp)])
                    user.notify_info(message=notice, title=NotificationSocketType.NOTIFICATION.value)
            return {
                'status': 200,
                'message': 'Successful confirmation !'
            }
        else:
            error = "Error : Invalid token %s " % (access_token,)
            return {
                'status': 204,
                'message': error
            }

    def cancel_routing_plan_day(self, idRoutingPlanDay):
        arr_cancel = []
        arr_cancel.append(idRoutingPlanDay)
        query_cancel_routing = """ SELECT json_agg(t) FROM ( select id from sharevan_routing_plan_day where from_routing_plan_day_id = %s)t """
        query_update_list_routing_plan_day = "UPDATE public.sharevan_routing_plan_day  SET status = %s WHERE id IN ( "

        self.env.cr.execute(query_cancel_routing, (idRoutingPlanDay,))
        result = self._cr.fetchall()
        re_arr = result[0][0]
        for re in re_arr:
            arr_cancel.append(re['id'])
        for arr in arr_cancel:
            query_update_list_routing_plan_day += str(arr) + ","
        query_update_list_routing_plan_day_rs = query_update_list_routing_plan_day.rstrip(',')
        query_update_list_routing_plan_day_rs += " )"
        self.env.cr.execute(query_update_list_routing_plan_day_rs, (RoutingPlanDay.Cancelled.value,))

        return "Canceled successfully !"


class BillPackage(models.Model, Base):
    _name = 'sharevan.bill.package'
    _description = 'bill package'
    _inherit = 'sharevan.bill.package'


class BillPackageType(models.Model, Base):
    _name = 'sharevan.product.package.type'
    _description = 'product package type'
    _inherit = 'sharevan.product.package.type'


class ProductType(models.Model, Base):
    _name = 'sharevan.product.type'
    _description = 'product type'
    _inherit = 'sharevan.product.type'

    extra_price = fields.Float('Extra price per distance unit', required=True)
    extra_percent = fields.Float('Extra per distance unit')
    active_shipping = fields.Boolean('Active shipping',default=True)

    @api.model
    def create(self, vals):
        vals['name_seq'] = BaseMethod.get_new_sequence('sharevan.product.type', 'PT', 6, 'name_seq')
        vals['status'] = 'running'
        result = super(ProductType, self).create(vals)
        if result.type == "0" and not result.parent_id:
            result.write({'parent_id': result.id})
        return result

    def write(self, vals):
        if 'type' in vals and vals['type'] == "0":
            vals['parent_id'] = self.id
        res = super(ProductType, self).write(vals)
        return res

    def unlink(self):
        for id in self.ids:
            record = self.env['sharevan.product.type'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })
            if record.type == '1':
                products = self.env['sharevan.product'].search([('product_type_id', '=', record.id)])
                for product in products:
                    pdt = self.env['sharevan.product'].search([('id', '=', product.id)])
                    pdt.write({
                        'product_type_id': False,
                        'product_type_parent_id': False
                    })
            else:
                sub_product_type = self.env['sharevan.product.type'].search([('parent_id', '=', record.id)])
                for spt in sub_product_type:
                    sptr = self.env['sharevan.product.type'].search([('id', '=', spt.id)])
                    sptr.write({
                        'parent_id': False,
                        'status': 'deleted'
                    })
                    products = self.env['sharevan.product'].search([('product_type_id', '=', sptr.id)])
                    for product in products:
                        pdt = self.env['sharevan.product'].search([('id', '=', product.id)])
                        pdt.write({
                            'product_type_id': False,
                            'product_type_parent_id': False
                        })
        return self

    @api.onchange("type")
    def _onchange_type(self):
        for record in self:
            record.parent_id = None

    @api.constrains("net_weight")
    def _check_something(self):
        for record in self:
            if record.net_weight < 0:
                raise ValidationError("Net weight must be a positive value: %s" % record.net_weight)

    @api.constrains('extra_price')
    def onchange_extra_price(self):
        for rec in self:
            if rec['extra_price'] <= 0:
                raise ValidationError('Extra price is bigger than zero')


class BillService(models.Model, Base):
    _name = 'sharevan.bill.service'
    _description = 'bill service'
    _rec_name = 'service_name'
    _inherit = 'sharevan.bill.service'
