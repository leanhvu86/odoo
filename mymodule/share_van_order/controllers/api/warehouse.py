# -*- coding: utf-8 -*-
import base64

from mymodule.base_next.controllers.api.base_method import BaseMethod
from mymodule.base_next.controllers.api.file_controller import FileApi
from odoo import http, fields
from odoo.exceptions import ValidationError
import json

from odoo.http import Response, request, content_disposition


class WarehouseApi:
    MODEL = 'sharevan.warehouse'
    AREA_MODEL = 'sharevan.area'
    ZONE_MODEL = 'sharevan.zone'
    DEPOT_MODEL = 'sharevan.depot'
    HUB_MODEL = 'sharevan.hub'

    @staticmethod
    def getZoneFromAddress(warehouse):
        province = ''
        district = ''
        wards = ''
        warehouse_json = json.loads(warehouse)
        address_components = warehouse_json['address_components']
        for element in address_components:
            types = element['types']
            if 'administrative_area_level_1' in types:
                province = element['long_name']
            elif 'administrative_area_level_2' in types:
                district = element['long_name']
            elif 'sublocality_level_1' in types or 'neighborhood' in types:
                wards = element['long_name']

        return province, district, wards
        # for level in address_components:
        #     print(level)

    @staticmethod
    def check_warehouse_area(warehouse):
        warehouse_json = json.loads(warehouse)
        address_components = warehouse_json['address_components']
        province = ''
        district = ''
        ward = ''
        zone = False
        for level in address_components:
            types = level['types']
            for type in types:
                if type == 'administrative_area_level_1':
                    province = level['long_name']
                if type == 'administrative_area_level_2':
                    district = level['long_name']
                if type == 'locality':
                    ward = level['long_name']
        record = http.request.env[WarehouseApi.AREA_MODEL] \
            .web_search_read([['name', '=', ward]], fields=None, offset=0, limit=80, order='')
        if record['length'] > 0:
            area = record['records']
            for ward_area in area:
                if ward_area['province_name'] == province:
                    zone_record = http.request.env[WarehouseApi.ZONE_MODEL] \
                        .web_search_read([['id', '=', ward_area['zone_area_id']]], fields=None, offset=0, limit=80,
                                         order='')
                    if zone_record['length'] > 0:
                        zone = zone_record['records'][0]
            if zone is False:
                record = http.request.env[WarehouseApi.AREA_MODEL] \
                    .web_search_read([['name', '=', district]], fields=None, offset=0, limit=80, order='')
                if record['length'] > 0:
                    area = record['records']
                    for district_area in area:
                        if district_area['province_name'] == province:
                            zone_record = http.request.env[WarehouseApi.ZONE_MODEL] \
                                .web_search_read([['id', '=', district_area['zone_area_id']]], fields=None, offset=0,
                                                 limit=80,
                                                 order='')
                            if zone_record['length'] > 0:
                                zone = zone_record['records'][0]
            if zone is False:
                record = http.request.env[WarehouseApi.AREA_MODEL] \
                    .web_search_read([['name', '=', district]], fields=None, offset=0, limit=80, order='')
                if record['length'] > 0:
                    area = record['records']
                    for province_area in area:
                        if province_area['province_name'] == province:
                            zone_record = http.request.env[WarehouseApi.ZONE_MODEL] \
                                .web_search_read([['id', '=', province_area['zone_area_id']]], fields=None, offset=0,
                                                 limit=80,
                                                 order='')
                            if zone_record['length'] > 0:
                                zone = zone_record['records'][0]
            if zone:
                return zone
            else:
                raise ValidationError('Zone id not found')
        else:
            record = http.request.env[WarehouseApi.AREA_MODEL] \
                .web_search_read([['name', '=', district]], fields=None, offset=0, limit=80, order='')
            if record['length'] > 0:
                if record['length'] > 0:
                    area = record['records']
                    for district_area in area:
                        if district_area['province_name'] == province:
                            zone_record = http.request.env[WarehouseApi.ZONE_MODEL] \
                                .web_search_read([['id', '=', district_area['zone_area_id']]], fields=None, offset=0,
                                                 limit=80,
                                                 order='')
                            if zone_record['length'] > 0:
                                zone = zone_record['records'][0]
                if zone is False:
                    record = http.request.env[WarehouseApi.AREA_MODEL] \
                        .web_search_read([['name', '=', district]], fields=None, offset=0, limit=80, order='')
                    if record['length'] > 0:
                        area = record['records']
                        for province_area in area:
                            if province_area['province_name'] == province:
                                zone_record = http.request.env[WarehouseApi.ZONE_MODEL] \
                                    .web_search_read([['id', '=', province_area['zone_area_id']]], fields=None,
                                                     offset=0,
                                                     limit=80,
                                                     order='')
                                if zone_record['length'] > 0:
                                    zone = zone_record['records'][0]
                if zone:
                    return zone
                else:
                    raise ValidationError('Zone id not found')
            else:
                record = http.request.env[WarehouseApi.AREA_MODEL] \
                    .web_search_read([['name', '=', province]], fields=None, offset=0, limit=80, order='')
                if record['length'] > 0:
                    area = record['records']
                    for province_area in area:
                        if province_area['province_name'] == province:
                            zone_record = http.request.env[WarehouseApi.ZONE_MODEL] \
                                .web_search_read([['id', '=', province_area['zone_area_id']]], fields=None, offset=0,
                                                 limit=80,
                                                 order='')
                            if zone_record['length'] > 0:
                                zone = zone_record['records'][0]
                    if zone:
                        return zone
                    else:
                        raise ValidationError('Area id not found')
                else:
                    raise ValidationError('Area id not found')

    @staticmethod
    def getWarehouseList(companyId):
        session, data_json = BaseMethod.check_authorized()
        companyId = http.request.env.company.id
        if not session and not companyId:
            return Response(json.dumps('UN_AUTHORIZED'), content_type="application/json", status=403)
        if not companyId:
            companyId = session['company_id']
        query = """
            SELECT json_agg(t) from ( select ware.id ware_id, ware.name_seq ware_code, ware.name ware_name ,
                ware.address ware_address, ware.latitude ware_latitude,ware.longitude ware_longitude,ware.country_id,
				ware.phone ware_phone, ware.area_id, area.id, area.name,area.name_seq,area.code , 
                zone.id zone_id ,zone.name zone_name, zone.name_seq zone_seq,zone.code zone_code,
                hub.id hub_id,hub.name hub_name, hub.name_seq hub_seq,
                hub.latitude hub_latitude,hub.longitude hub_longitude, hub.address hub_address,
                depot.id depot_id,depot.name depot_name,depot.name_seq depot_seq,
                depot.latitude depot_latitude,depot.longitude depot_longitude, depot.address depot_address,
                province.name province, province.id state_id, district.name district_name,district.id district,
                ward.id ward,ward.name ward_name
            from sharevan_warehouse ware
				join sharevan_area  area on ware.area_id = area.id
				left join sharevan_area  province on ware.state_id = province.id
				left join sharevan_area  district on ware.district = district.id
				left join sharevan_area  ward on ware.ward = ward.id
                left join sharevan_zone zone on area.zone_area_id = zone.id
                left join sharevan_hub hub on hub.id= area.hub_id
                left join sharevan_depot depot on depot.id = zone.depot_id
            where  ware.company_id = %s and ware.status = 'running' )t
                        """
        http.request.env[WarehouseApi.MODEL]._cr.execute(query, (companyId,))
        records = http.request.env[WarehouseApi.MODEL]._cr.fetchall()
        if records[0]:
            if records[0][0]:
                warehouse = []
                for record in records[0][0]:
                    ware = {
                        'id': record['ware_id'],
                        'warehouse_code': record['ware_code'],
                        'name_seq': record['ware_code'],
                        'name': record['ware_name'],
                        'address': record['ware_address'],
                        'latitude': record['ware_latitude'],
                        'longitude': record['ware_longitude'],
                        'phone': record['ware_phone'],
                        'state_id': record['state_id'],
                        'country_id': record['country_id'],
                        'province_name': record['province'],
                        'district_name': record['district_name'],
                        'district': record['district'],
                        'ward_name': record['ward_name'],
                        'ward': record['ward'],
                        'area_id': record['area_id'],
                        'areaInfo': {
                            'id': record['id'],
                            'name': record['name'],
                            'name_seq': record['name_seq'],
                            'code': record['code'],
                            'zoneInfo': {
                                'id': record['zone_id'],
                                'name': record['zone_name'],
                                'name_seq': record['zone_seq'],
                                'code': record['zone_code'],
                                'depotInfo': {
                                    'id': record['depot_id'],
                                    'name': record['depot_name'],
                                    'name_seq': record['depot_seq'],
                                    'address': record['depot_address'],
                                    'latitude': record['depot_latitude'],
                                    'longitude': record['depot_longitude']
                                }
                            },
                            'hubInfo': {
                                'id': record['hub_id'],
                                'name': record['hub_name'],
                                'name_seq': record['hub_seq'],
                                'address': record['hub_address'],
                                'latitude': record['hub_latitude'],
                                'longitude': record['hub_longitude']
                            }
                        }
                    }

                    warehouse.append(ware)
                return {
                    'records': warehouse
                }
            else:
                return {
                    'records': []
                }

    @staticmethod
    def bill_list_date(self, from_date, to_date):
        session, data_json = BaseMethod.check_authorized()
        if not session:
            return Response(json.dumps('UN_AUTHORIZED'), content_type="application/json", status=403)
        uId = session['uid']
        query = """
            SELECT  distinct(TO_CHAR(t.start_date, 'YYYY-MM-DD')) start_date,
            string_agg(t.code, ',') AS code,string_agg(cast(t.id as text), ',') AS description
        FROM sharevan_bill_routing as t
            join res_users ru on ru.company_id=  t.company_id
        WHERE t.start_date >= %s and t.start_date <=  %s
            and ru.id = %s group by t.start_date;
        """
        http.request.env[WarehouseApi.MODEL]._cr.execute(query, (from_date, to_date, uId,))
        result = http.request.env[WarehouseApi.MODEL]._cr.dictfetchall()
        json_data = {
            'records': result
        }
        return Response(json.dumps(json_data), content_type="application/json", status=200)

    @staticmethod
    def get_warehouse_list_web(self, pageNumber, pageSize):
        offset = 0
        limit = 10
        page = ''
        session, data_json = BaseMethod.check_authorized()
        if not session:
            return Response(json.dumps('UN_AUTHORIZED'), content_type="application/json", status=403)
        companyId = session['company_id']
        select = """
                 select ware.id ware_id, ware.name_seq ware_code, ware.name ware_name ,
                ware.address ware_address, ware.latitude ware_latitude,ware.longitude ware_longitude,ware.country_id,
				ware.phone ware_phone, ware.area_id, area.id, area.name,area.name_seq,area.code , 
                zone.id zone_id ,zone.name zone_name, zone.name_seq zone_seq,zone.code zone_code,
                hub.id hub_id,hub.name hub_name, hub.name_seq hub_seq,
                hub.latitude hub_latitude,hub.longitude hub_longitude, hub.address hub_address,
                depot.id depot_id,depot.name depot_name,depot.name_seq depot_seq,
                depot.latitude depot_latitude,depot.longitude depot_longitude, depot.address depot_address,
                province.name province, province.id state_id, district.name district_name,district.id district,
                ward.id ward,ward.name ward_name
            from sharevan_warehouse ware
				join sharevan_area  area on ware.area_id = area.id
				left join sharevan_area  province on ware.state_id = province.id
				left join sharevan_area  district on ware.district = district.id
				left join sharevan_area  ward on ware.ward = ward.id
                left join sharevan_zone zone on area.zone_area_id = zone.id
                left join sharevan_hub hub on hub.id= area.hub_id
                left join sharevan_depot depot on depot.id = zone.depot_id
            where ware.company_id = %s and ware.status = 'running' 
                        """ % (companyId)
        for arg in data_json:
            if arg == 'warehouse_code_search' and data_json.get(arg) is not '':
                select += " and ware.warehouse_code like '%%%s%%'" % data_json.get(arg)
            if arg == 'warehouse_name_search' and data_json.get(arg) is not '':
                select += " and ware.name like '%%%s%%' " % data_json.get(arg)
            if arg == 'address_search' and data_json.get(arg) is not '':
                select += " and ware.address like '%%%s%%' " % data_json.get(arg)
        count_query = """select count(id) from (%s) t """ % select
        http.request.env.cr.execute(count_query, ())
        count = http.request._cr.fetchall()

        offset = str((int(pageNumber) - 1) * int(pageSize))
        limit = pageSize
        page = ' offset ' + str(offset) + ' limit ' + str(limit)
        select += page
        http.request.env[WarehouseApi.MODEL]._cr.execute(select, ())
        records = http.request.env[WarehouseApi.MODEL]._cr.dictfetchall()
        warehouse = []
        if records:
            for record in records:
                ware = {
                    'id': record['ware_id'],
                    'warehouse_code': record['ware_code'],
                    'name_seq': record['ware_code'],
                    'name': record['ware_name'],
                    'address': record['ware_address'],
                    'latitude': record['ware_latitude'],
                    'longitude': record['ware_longitude'],
                    'phone': record['ware_phone'],
                    'state_id': record['state_id'],
                    'country_id': record['country_id'],
                    'province_name': record['province'],
                    'district_name': record['district_name'],
                    'district': record['district'],
                    'ward_name': record['ward_name'],
                    'ward': record['ward'],
                    'area_id': record['area_id'],
                    'areaInfo': {
                        'id': record['id'],
                        'name': record['name'],
                        'name_seq': record['name_seq'],
                        'code': record['code'],
                        'zoneInfo': {
                            'id': record['zone_id'],
                            'name': record['zone_name'],
                            'name_seq': record['zone_seq'],
                            'code': record['zone_code'],
                            'depotInfo': {
                                'id': record['depot_id'],
                                'name': record['depot_name'],
                                'name_seq': record['depot_seq'],
                                'address': record['depot_address'],
                                'latitude': record['depot_latitude'],
                                'longitude': record['depot_longitude']
                            }
                        },
                        'hubInfo': {
                            'id': record['hub_id'],
                            'name': record['hub_name'],
                            'name_seq': record['hub_seq'],
                            'address': record['hub_address'],
                            'latitude': record['hub_latitude'],
                            'longitude': record['hub_longitude']
                        }
                    }
                }
                warehouse.append(ware)
        result = {
            'totalElements': count,
            'size': int(pageSize),
            'number': int(pageNumber) - 1,
            'content': warehouse
        }
        return Response(json.dumps(result), content_type="application/json", status=200)

    @staticmethod
    def getWarehouseById(warehouseId):
        query = """
                SELECT json_agg(t) from ( select ware.id ware_id, ware.name_seq ware_code, ware.name ware_name ,
                    ware.address ware_address, ware.latitude ware_latitude,ware.longitude ware_longitude,ware.country_id,
    				ware.phone ware_phone, ware.area_id, area.id, area.name,area.name_seq,area.code , 
                    zone.id zone_id ,zone.name zone_name, zone.name_seq zone_seq,zone.code zone_code,
                    hub.id hub_id,hub.name hub_name, hub.name_seq hub_seq,
                    hub.latitude hub_latitude,hub.longitude hub_longitude, hub.address hub_address,
                    depot.id depot_id,depot.name depot_name,depot.name_seq depot_seq,
                    depot.latitude depot_latitude,depot.longitude depot_longitude, depot.address depot_address,
                    province.name province, province.id state_id, district.name district_name,district.id district,
                    ward.id ward,ward.name ward_name
                from sharevan_warehouse ware
    				join sharevan_area  area on ware.area_id = area.id
    				left join sharevan_area  province on ware.state_id = province.id
    				left join sharevan_area  district on ware.district = district.id
    				left join sharevan_area  ward on ware.ward = ward.id
                    left join sharevan_zone zone on area.zone_area_id = zone.id
                    left join sharevan_hub hub on hub.id= area.hub_id
                    left join sharevan_depot depot on depot.id = zone.depot_id
                where  ware.id = %s and ware.status = 'running' )t
                            """
        http.request.env[WarehouseApi.MODEL]._cr.execute(query, (warehouseId,))
        records = http.request.env[WarehouseApi.MODEL]._cr.fetchall()
        if records[0]:
            if records[0][0]:
                for record in records[0][0]:
                    ware = {
                        'id': record['ware_id'],
                        'warehouse_code': record['ware_code'],
                        'name': record['ware_name'],
                        'address': record['ware_address'],
                        'latitude': record['ware_latitude'],
                        'longitude': record['ware_longitude'],
                        'phone': record['ware_phone'],
                        'state_id': record['state_id'],
                        'country_id': record['country_id'],
                        'province_name': record['province'],
                        'district_name': record['district_name'],
                        'district': record['district'],
                        'ward_name': record['ward_name'],
                        'ward': record['ward'],
                        'area_id': record['area_id'],
                        'areaInfo': {
                            'id': record['id'],
                            'name': record['name'],
                            'name_seq': record['name_seq'],
                            'code': record['code'],
                            'zoneInfo': {
                                'id': record['zone_id'],
                                'name': record['zone_name'],
                                'name_seq': record['zone_seq'],
                                'code': record['zone_code'],
                                'depotInfo': {
                                    'id': record['depot_id'],
                                    'name': record['depot_name'],
                                    'name_seq': record['depot_seq'],
                                    'address': record['depot_address'],
                                    'latitude': record['depot_latitude'],
                                    'longitude': record['depot_longitude']
                                }
                            },
                            'hubInfo': {
                                'id': record['hub_id'],
                                'name': record['hub_name'],
                                'name_seq': record['hub_seq'],
                                'address': record['hub_address'],
                                'latitude': record['hub_latitude'],
                                'longitude': record['hub_longitude']
                            }
                        }
                    }
                return {
                    'records': ware
                }
            else:
                return {
                    'records': None
                }

    @staticmethod
    def get_warehouse_table(name_search, code_search, address_search):
        template = http.request.env['xlsx.template'].search([('id', '=', 2)])
        session, data_json = BaseMethod.check_authorized()
        if not session:
            return Response(json.dumps('UN_AUTHORIZED'), content_type="application/json", status=403)
        companyId = session['company_id']
        select = """
            select row_number() OVER () as id, ware.name_seq code, ware.name , ware.phone phone,
                ware.address address
            from sharevan_warehouse ware
            where ware.company_id = %s and ware.status = 'running' 
                                """ % (companyId)
        if name_search and name_search != '':
            select += " and ware.name like '%%%s%%'" % name_search
        if code_search and code_search != '':
            select += " and ware.warehouse_code like '%%%s%%' " % code_search
        if address_search and address_search != '':
            select += " and ware.address like '%%%s%%' " % address_search
        http.request.env[WarehouseApi.MODEL]._cr.execute(select, ())
        records = http.request.env[WarehouseApi.MODEL]._cr.dictfetchall()
        if records:
            data = str(records)
        else:
            data = """"""
        out_file, out_name = http.request.env["xlsx.export"].export_xlsx_by_template_and_data(template, data)
        return BaseMethod.get_excel_reponse(out_file, out_name, template)

    @staticmethod
    def get_area_distance(from_warehouse, to_warehouse):
        if to_warehouse and to_warehouse != '':
            if from_warehouse:
                list_area_distance = []
                if from_warehouse['areaInfo']['zoneInfo']['code'] != to_warehouse['areaInfo']['zoneInfo']['code']:
                    query = """
                        select * from sharevan_distance_compute where 
                        from_seq =%s and to_seq = %s
                                            """
                    http.request.env[WarehouseApi.MODEL]._cr.execute(query, (
                        from_warehouse['areaInfo']['hubInfo']['name_seq'],
                        from_warehouse['areaInfo']['zoneInfo']['depotInfo']['name_seq'],))
                    hub_depot_compute = http.request.env[WarehouseApi.MODEL]._cr.dictfetchall()
                    hub_to_depot = {
                        "distance": hub_depot_compute[0]['distance'],
                        "duration": hub_depot_compute[0]['time'],
                        "fromLocation": {
                            "latitude": from_warehouse['areaInfo']['hubInfo']['latitude'],
                            "longitude": from_warehouse['areaInfo']['hubInfo']['longitude']
                        },
                        "from_name_seq": from_warehouse['areaInfo']['hubInfo']['name_seq'],
                        "from_warehouse_name": from_warehouse['areaInfo']['hubInfo']['name'],
                        "toLocation": {
                            "latitude": from_warehouse['areaInfo']['zoneInfo']['depotInfo']['latitude'],
                            "longitude": from_warehouse['areaInfo']['zoneInfo']['depotInfo']['longitude']
                        },
                        "to_name_seq": from_warehouse['areaInfo']['zoneInfo']['depotInfo']['name_seq'],
                        "to_warehouse_name": from_warehouse['areaInfo']['zoneInfo']['depotInfo']['name'],
                        "type": 3
                    }
                    list_area_distance.append(hub_to_depot)

                    http.request.env[WarehouseApi.MODEL]._cr.execute(query, (
                        from_warehouse['areaInfo']['zoneInfo']['depotInfo']['name_seq'],
                        to_warehouse['areaInfo']['zoneInfo']['depotInfo']['name_seq'],))
                    depot_depot_compute = http.request.env[WarehouseApi.MODEL]._cr.dictfetchall()
                    depot_to_depot = {
                        "distance": depot_depot_compute[0]['distance'],
                        "duration": depot_depot_compute[0]['time'],
                        "fromLocation": {
                            "latitude": from_warehouse['areaInfo']['zoneInfo']['depotInfo']['latitude'],
                            "longitude": from_warehouse['areaInfo']['zoneInfo']['depotInfo']['longitude']
                        },
                        "from_name_seq": from_warehouse['areaInfo']['zoneInfo']['depotInfo']['name_seq'],
                        "from_warehouse_name": from_warehouse['areaInfo']['zoneInfo']['depotInfo']['name'],
                        "toLocation": {
                            "latitude": to_warehouse['areaInfo']['zoneInfo']['depotInfo']['latitude'],
                            "longitude": to_warehouse['areaInfo']['zoneInfo']['depotInfo']['longitude']
                        },
                        "to_name_seq": to_warehouse['areaInfo']['zoneInfo']['depotInfo']['name_seq'],
                        "to_warehouse_name": to_warehouse['areaInfo']['zoneInfo']['depotInfo']['name'],
                        "type": 4
                    }
                    list_area_distance.append(depot_to_depot)

                    http.request.env[WarehouseApi.MODEL]._cr.execute(query, (
                        to_warehouse['areaInfo']['zoneInfo']['depotInfo']['name_seq'],
                        to_warehouse['areaInfo']['hubInfo']['name_seq'],
                    ))
                    depot_hub_compute = http.request.env[WarehouseApi.MODEL]._cr.dictfetchall()
                    depot_to_hub = {
                        "distance": depot_hub_compute[0]['distance'],
                        "duration": depot_hub_compute[0]['time'],
                        "fromLocation": {
                            "latitude": to_warehouse['areaInfo']['zoneInfo']['depotInfo']['latitude'],
                            "longitude": to_warehouse['areaInfo']['zoneInfo']['depotInfo']['longitude']
                        },
                        "from_name_seq": to_warehouse['areaInfo']['zoneInfo']['depotInfo']['name_seq'],
                        "from_warehouse_name": to_warehouse['areaInfo']['zoneInfo']['depotInfo']['name'],
                        "toLocation": {
                            "latitude": to_warehouse['areaInfo']['hubInfo']['latitude'],
                            "longitude": to_warehouse['areaInfo']['hubInfo']['longitude']
                        },
                        "to_name_seq": to_warehouse['areaInfo']['hubInfo']['name_seq'],
                        "to_warehouse_name": to_warehouse['areaInfo']['hubInfo']['name'],
                        "type": 5
                    }
                    list_area_distance.append(depot_to_hub)
                    json_result = FileApi.check_driver_waiting_time(to_warehouse['areaInfo']['hubInfo']['latitude'],
                                                                    to_warehouse['areaInfo']['hubInfo'][
                                                                        'longitude'], to_warehouse['latitude'],
                                                                    to_warehouse['longitude'])
                    hub_to_warehouse = {}
                    if json_result:
                        hub_to_warehouse = {
                            "distance": json_result['cost'],
                            "duration": json_result['minutes'],
                            "fromLocation": {
                                "latitude": to_warehouse['areaInfo']['hubInfo']['latitude'],
                                "longitude": to_warehouse['areaInfo']['hubInfo']['longitude']
                            },
                            "from_name_seq": to_warehouse['areaInfo']['hubInfo']['name_seq'],
                            "from_warehouse_name": to_warehouse['areaInfo']['hubInfo']['name'],
                            "toLocation": {
                                "latitude": to_warehouse['latitude'],
                                "longitude": to_warehouse['longitude']
                            },
                            "to_name_seq": to_warehouse['name_seq'],
                            "to_warehouse_name": to_warehouse['name'],
                            "type": 6
                        }
                    list_area_distance.append(hub_to_warehouse)
                else:
                    if from_warehouse['areaInfo']['hubInfo']['name_seq'] == to_warehouse['areaInfo']['hubInfo'][
                        'name_seq']:
                        json_result = FileApi.check_driver_waiting_time(from_warehouse['latitude'],
                                                                        from_warehouse['longitude'],
                                                                        from_warehouse['areaInfo']['hubInfo'][
                                                                            'latitude'],
                                                                        from_warehouse['areaInfo']['hubInfo'][
                                                                            'longitude'])
                        hub_to_warehouse = {
                            "distance": json_result['cost'],
                            "duration": json_result['minutes'],
                            "fromLocation": {
                                "latitude": to_warehouse['areaInfo']['hubInfo']['latitude'],
                                "longitude": to_warehouse['areaInfo']['hubInfo']['longitude']
                            },
                            "from_name_seq": to_warehouse['areaInfo']['hubInfo']['name_seq'],
                            "from_warehouse_name": to_warehouse['areaInfo']['hubInfo']['name'],
                            "toLocation": {
                                "latitude": to_warehouse['latitude'],
                                "longitude": to_warehouse['longitude']
                            },
                            "to_name_seq": to_warehouse['name_seq'],
                            "to_warehouse_name": to_warehouse['name'],
                            "type": 6
                        }
                        list_area_distance.append(hub_to_warehouse)
                    else:
                        query = """
                            select * from sharevan_distance_compute where 
                            from_seq =%s and to_seq = %s
                        """
                        http.request.env[WarehouseApi.MODEL]._cr.execute(query, (
                            from_warehouse['areaInfo']['hubInfo']['name_seq'],
                            to_warehouse['areaInfo']['hubInfo']['name_seq'],))
                        hub_compute = http.request.env[WarehouseApi.MODEL]._cr.dictfetchall()
                        hub_to_hub = {
                            "distance": hub_compute[0]['distance'],
                            "duration": hub_compute[0]['time'],
                            "fromLocation": {
                                "latitude": from_warehouse['areaInfo']['hubInfo']['latitude'],
                                "longitude": from_warehouse['areaInfo']['hubInfo']['longitude']
                            },
                            "from_name_seq": from_warehouse['areaInfo']['hubInfo']['name_seq'],
                            "from_warehouse_name": from_warehouse['areaInfo']['hubInfo']['name'],
                            "toLocation": {
                                "latitude": to_warehouse['areaInfo']['hubInfo']['latitude'],
                                "longitude": to_warehouse['areaInfo']['hubInfo']['longitude']
                            },
                            "to_name_seq": to_warehouse['areaInfo']['hubInfo']['name_seq'],
                            "to_warehouse_name": to_warehouse['areaInfo']['hubInfo']['name'],
                            "type": 2
                        }
                        list_area_distance.append(hub_to_hub)
                        json_result = FileApi.check_driver_waiting_time(to_warehouse['areaInfo']['hubInfo']['latitude'],
                                                                        to_warehouse['areaInfo']['hubInfo'][
                                                                            'longitude'], to_warehouse['latitude'],
                                                                        to_warehouse['longitude'])
                        hub_to_warehouse = {}
                        if json_result:
                            hub_to_warehouse = {
                                "distance": json_result['cost'],
                                "duration": json_result['minutes'],
                                "fromLocation": {
                                    "latitude": to_warehouse['areaInfo']['hubInfo']['latitude'],
                                    "longitude": to_warehouse['areaInfo']['hubInfo']['longitude']
                                },
                                "from_name_seq": to_warehouse['areaInfo']['hubInfo']['name_seq'],
                                "from_warehouse_name": to_warehouse['areaInfo']['hubInfo']['name'],
                                "toLocation": {
                                    "latitude": to_warehouse['latitude'],
                                    "longitude": to_warehouse['longitude']
                                },
                                "to_name_seq": to_warehouse['name_seq'],
                                "to_warehouse_name": to_warehouse['name'],
                                "type": 1
                            }
                        list_area_distance.append(hub_to_warehouse)
                response_data = {
                    'records': list_area_distance,
                }
                return response_data
            else:
                return Response(json.dumps('From warehouse not found'), content_type="application/json", status=500)
        else:
            if from_warehouse and from_warehouse != '':
                json_result = FileApi.check_driver_waiting_time(from_warehouse['latitude'], from_warehouse['longitude'],
                                                                from_warehouse['areaInfo']['hubInfo']['latitude'],
                                                                from_warehouse['areaInfo']['hubInfo']['longitude'])
                result = {}
                if json_result:
                    result = {
                        "distance": json_result['cost'],
                        "duration": json_result['minutes'],
                        "fromLocation": {
                            "latitude": from_warehouse['latitude'],
                            "longitude": from_warehouse['longitude']
                        },
                        "from_name_seq": from_warehouse['name_seq'],
                        "from_warehouse_name": from_warehouse['name'],
                        "toLocation": {
                            "latitude": from_warehouse['areaInfo']['hubInfo']['latitude'],
                            "longitude": from_warehouse['areaInfo']['hubInfo']['longitude']
                        },
                        "to_name_seq": from_warehouse['areaInfo']['hubInfo']['name_seq'],
                        "to_warehouse_name": from_warehouse['areaInfo']['hubInfo']['name'],
                        "type": 1
                    }
                response_data = {
                    'records': [result],
                    'status': 200
                }
                return response_data
            else:
                return Response(json.dumps('From warehouse not found'), content_type="application/json", status=500)

    @staticmethod
    def getDepotList():
        companyId = http.request.env.user.company_id.id
        query = """
            SELECT json_agg(t) from ( select 
                depot.id depot_id,depot.name depot_name,depot.name_seq depot_seq,
                depot.latitude depot_latitude,depot.longitude depot_longitude, depot.address depot_address
            from sharevan_depot depot
            where  depot.company_id = %s and depot.status = 'running' )t
                                """
        http.request.env.cr.execute(query, (companyId,))
        records = http.request.env.cr.fetchall()
        return {
            'records': records[0][0]
        }
