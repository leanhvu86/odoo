# -*- coding: utf-8 -*-

from datetime import datetime
from mymodule.share_van_order.controllers.api.base import BaseApi
from mymodule.share_van_order.controllers.api.bill_package import BillPackageApi
from odoo import http
from odoo.exceptions import ValidationError


class BillLadingDetailApi:
    MODEL = 'sharevan.bill.lading.detail'

    @staticmethod
    def create_bill_lading_details(details):
        sorted_details = dict()
        result_dt = []
        for detail in details:
            warehouse_detail = detail['warehouse']
            detail['latitude'] = warehouse_detail['latitude']
            detail['longitude'] = warehouse_detail['longitude']
            detail['zone_area_id'] = warehouse_detail['areaInfo']['zoneInfo']['id']
            detail['phone'] = warehouse_detail['phone']
            detail['warehouse_name'] = warehouse_detail['name']
            detail['hub_id'] = warehouse_detail['areaInfo']['hubInfo']['id']
            detail['depot_id'] = warehouse_detail['areaInfo']['zoneInfo']['depotInfo']['id']
            if 'id' in warehouse_detail:
                detail['warehouse_id'] = warehouse_detail['id']
            if 'warehouse_code' in sorted_details:
                tmp = sorted_details['warehouse_code']
            else:
                tmp = []
                sorted_details['warehouse_code'] = tmp

            if detail['warehouse_type'] == '0':  # pickup
                tmp.insert(0, detail)
            else:
                tmp.append(detail)
            # if 'expected_from_time' not in detail:
            #     raise ValidationError("Validation error expected from time")
            # if 'expected_to_time' not in detail:
            #     raise ValidationError("Validation error expected to time")
            # Vui long bo di vi con kho khong thuoc trong he thong nen warehouse_id null dươc
            # if 'warehouse_id' not in detail:
            #     raise ValidationError("Validation error warehouse")
            if 'expected_from_time' in detail and isinstance(detail['expected_from_time'], int):
                detail['expected_from_time'] = datetime.fromtimestamp(detail['expected_from_time'] / 1000.0)
            if 'expected_to_time' in detail and isinstance(detail['expected_to_time'], int):
                detail['expected_to_time'] = datetime.fromtimestamp(detail['expected_to_time'] / 1000.0)
            list_pk = []
            detail['status_order'] = 'running'
            list_product_id = []
            for pk in detail['billPackages']:
                if 'productType' in pk:
                    pk['product_type_id'] = pk['productType']['id']
                    list_product_id.append(pk['product_type_id'])
                    pk.pop('productType')
                list_pk.append([0, '', pk])
            set_product_id = set(list_product_id)
            search_product_type = http.request.env['sharevan.product.type'].search(args=[('id', 'in', list_product_id)])
            if len(search_product_type) != len(set_product_id):
                raise ValidationError("Some product type doesn't exist")
            detail['bill_package_line'] = list_pk
            list_service = []
            for service in detail['billService']:
                list_service.append([0, '', service])
            detail['service_id'] = list_service
            detail.pop('billPackages')
            # detail.pop('bill_packages')
            detail.pop('billService')
            detail.pop('warehouse')
            result_dt.append([0, '', detail])
        return result_dt

    @staticmethod
    def create_bill_packages(detailId, billPackages):
        for package in billPackages:
            package['bill_lading_detail_id'] = detailId
            product_type = 0
            for key in package.keys():
                if key == 'productType':
                    product_type = package[key]
            package['product_type_id'] = product_type['id']
            BillPackageApi.create_bill_package(package)

    @staticmethod
    def create_bill_service(detailId, billservices):
        for service in billservices:
            service['bill_lading_detail_id'] = detailId
            BillPackageApi.create_bill_package(service)
