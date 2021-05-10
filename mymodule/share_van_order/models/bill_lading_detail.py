import json as simplejson

import simplejson

from mymodule.base_next.models.bidding import BiddingOrder
# from mymodule.biding_order.models.base import Base
from mymodule.constants import Constants
from mymodule.share_van_order.models.cargo import Cargo
from odoo import http, fields
from odoo import models, _
from odoo.exceptions import ValidationError


class BillLading(models.Model):
    _name = Constants.SHAREVAN_BILL_LADING
    _description = 'Sharevan Bill of Lading'
    _inherit = Constants.SHAREVAN_BILL_LADING

    company_type = fields.Selection([
        ('1', 'Business'),
        ('2', 'Individual'),
        ('3', 'Logistics')
    ], 'Customer type', related='company_id.customer_type', help='Customer Type', store=False)

class BillLadingDetail(models.Model):
    _name = Constants.SHAREVAN_BILL_LADING_DETAIL
    _description = 'Sharevan Bill of Lading detail'
    _inherit = Constants.SHAREVAN_BILL_LADING_DETAIL

    def get_bill_lading_detail_by_cargo_id(self, cargo_id):
        list_bill_lading_detail_id = []
        list_bill_lading_detail_json  = []
        if cargo_id:
            query_get_cargo_rel = """ SELECT json_agg(t)
                                                             FROM (   SELECT sharevan_cargo_id, sharevan_bill_lading_detail_id
	                                  FROM public.sharevan_bill_lading_detail_sharevan_cargo_rel sbl where sbl.sharevan_cargo_id = %s ) t """

            self.env.cr.execute(query_get_cargo_rel, (cargo_id,))
            result_get_cargo_rel = self._cr.fetchall()
            cargo_result = result_get_cargo_rel[0][0]
            if cargo_result is None:
                raise ValidationError(_("Some thing wrong when create cargo!"))
            for rec in cargo_result:
                list_bill_lading_detail_id.append(rec['sharevan_bill_lading_detail_id'])
            if list_bill_lading_detail_id:
                for re in list_bill_lading_detail_id:
                    bill_lading_detail_id = re
                    query_get_bill_lading_detail = """SELECT json_agg(t)
                                                                                FROM (  SELECT id, name_seq, bill_lading_id, total_weight, warehouse_id, warehouse_type, from_bill_lading_detail_id,
                                                                   TO_CHAR(expected_from_time, 'YYYY-MM-DD HH24:MI:SS') expected_from_time,  TO_CHAR(expected_to_time, 'YYYY-MM-DD HH24:MI:SS') expected_to_time, name, status, approved_type, from_warehouse_id, latitude, 
                                                                   longitude, area_id, zone_area_id, address, status_order, warehouse_name, distance, description, 
                                                                  from_seq, max_price, min_price, to_seq, type, price, trans_id, depot_id, order_type, phone, hub_id
                                                                  FROM public.sharevan_bill_lading_detail bill_lading_detail WHERE  1=1 and bill_lading_detail.id = %s ) t """

                    self.env.cr.execute(query_get_bill_lading_detail, (bill_lading_detail_id,))
                    result_get_bill_lading_detail = self._cr.fetchall()
                    bill_lading_detail = result_get_bill_lading_detail[0][0][0]
                    if bill_lading_detail:
                        query_get_bill_package = """ SELECT json_agg(t)
                        FROM (  
                        SELECT id, item_name, bill_lading_detail_id, net_weight, quantity_package, length, width, height, capacity, description, 
                            product_type_id, status, name, from_bill_package_id
                        FROM public.sharevan_bill_package sharevan_bill_package 
                            where 1=1 and sharevan_bill_package.bill_lading_detail_id = %s ) t """

                        self.env.cr.execute(query_get_bill_package, (bill_lading_detail['id'],))
                        result_query_get_bill_package = self._cr.fetchall()
                        bill_package = result_query_get_bill_package[0][0][0]
                        if bill_package:
                            query_package_routing_plan = """ 
                                SELECT json_agg(t) FROM ( 
                                    SELECT id, quantity, length, width, height, total_weight, capacity,
                                        product_package_type_id, bill_package_id, bill_lading_detail_id, note, item_name,
                                        insurance_name, service_name, from_warehouse_id, to_warehouse_id, 
                                        qr_char, product_type_id, routing_plan_day_id, status, name
                                    FROM public.sharevan_bill_package_routing_plan sbpl where 1=1 and sbpl.bill_package_id = %s )t  """

                            self.env.cr.execute(query_package_routing_plan, (bill_package['id'],))
                            result_package_routing_plan = self._cr.fetchall()
                            bill_package_routing_plan = result_package_routing_plan[0][0][0]

                            query_get_bill_package_import = """
                                SELECT json_agg(t) FROM (  
                                    SELECT id, quantity_import, length, width, height, total_weight, capacity, product_package_type_id, 
                                        bill_package_id, bill_lading_detail_id, note, item_name,  insurance_name, service_name, 
                                        from_warehouse_id, to_warehouse_id,  routing_plan_code, qr_char, product_type_id, 
                                        routing_package_plan, routing_plan_day_id, status, name
                                    FROM public.sharevan_bill_package_routing_import sbpri where 1=1 and sbpri.routing_package_plan = %s ) t """

                            self.env.cr.execute(query_get_bill_package_import, (bill_package_routing_plan['id'],))
                            result_get_bill_package_import = self._cr.fetchall()
                            if result_get_bill_package_import[0][0]:
                                get_bill_package_import = result_get_bill_package_import[0][0][0]
                            else:
                                get_bill_package_import = ''

                            query_get_bill_package_export = """ 
                                SELECT json_agg(t) FROM (  
                                    SELECT id, quantity_export, length, width, height, total_weight, capacity, product_package_type_id, bill_package_id,product_type_id,
                                        bill_lading_detail_id, note, item_name, insurance_name, service_name, from_warehouse_id, to_warehouse_id, qr_char, 
                                        routing_package_plan, routing_plan_day_id, status
                                    FROM public.sharevan_bill_package_routing_export sbpre where 1=1 and sbpre.routing_package_plan = %s )  t"""

                            self.env.cr.execute(query_get_bill_package_export, (bill_package_routing_plan['id'],))
                            result_query_get_bill_package_export = self._cr.fetchall()
                            if result_query_get_bill_package_export[0][0]:
                                get_bill_package_export = result_query_get_bill_package_export[0][0][0]
                            else:
                                get_bill_package_export = ''

                            bill_package_json = {
                                'id': bill_package['id'],
                                'item_name': bill_package['item_name'],
                                'bill_lading_detail_id': bill_package['bill_lading_detail_id'],
                                'net_weight': bill_package['net_weight'],
                                'quantity_package': bill_package['quantity_package'],
                                'length': bill_package['length'],
                                'width': bill_package['width'],
                                'height': bill_package['height'],
                                'capacity': bill_package['capacity'],
                                'description': bill_package['description'],
                                'product_type_id': bill_package['product_type_id'],
                                'status': bill_package['status'],
                                'from_bill_package_id': bill_package['from_bill_package_id'],
                                # 'bill_package_import': get_bill_package_import,
                                # 'bill_package_export': get_bill_package_export,
                                'bill_package_routing_plan': bill_package_routing_plan
                            }

                            bill_lading_detail_json = {
                                'id': bill_lading_detail['id'],
                                'name_seq': bill_lading_detail['name_seq'],
                                'bill_lading_id': bill_lading_detail['bill_lading_id'],
                                'total_weight': bill_lading_detail['total_weight'],
                                'warehouse_id': bill_lading_detail['warehouse_id'],
                                'warehouse_type': bill_lading_detail['warehouse_type'],
                                'from_bill_lading_detail_id': bill_lading_detail['from_bill_lading_detail_id'],
                                'description': bill_lading_detail['description'],
                                'expected_from_time': bill_lading_detail['expected_from_time'],
                                'expected_to_time': bill_lading_detail['expected_to_time'],
                                'name': bill_lading_detail['name'],
                                'status': bill_lading_detail['status'],
                                'approved_type': bill_lading_detail['approved_type'],
                                'from_warehouse_id': bill_lading_detail['from_warehouse_id'],
                                'latitude': bill_lading_detail['latitude'],
                                'longitude': bill_lading_detail['longitude'],
                                'area_id': bill_lading_detail['area_id'],
                                'zone_area_id': bill_lading_detail['zone_area_id'],
                                'status_order': bill_lading_detail['status_order'],
                                'address': bill_lading_detail['address'],
                                'warehouse_name': bill_lading_detail['warehouse_name'],
                                'distance': bill_lading_detail['distance'],
                                'from_seq': bill_lading_detail['from_seq'],
                                'max_price': bill_lading_detail['max_price'],
                                'min_price': bill_lading_detail['min_price'],
                                'to_seq': bill_lading_detail['to_seq'],
                                'type': bill_lading_detail['type'],
                                'price': bill_lading_detail['price'],
                                'trans_id': bill_lading_detail['trans_id'],
                                'depot_id': bill_lading_detail['depot_id'],
                                'order_type': bill_lading_detail['order_type'],
                                'phone': bill_lading_detail['phone'],
                                'hub_id': bill_lading_detail['hub_id'],
                                'list_bill_package': [bill_package_json]
                            }

                            list_bill_lading_detail_json.append(bill_lading_detail_json)





                        else:
                            raise ValidationError(_('Bill package does not exist!'))
                    else:
                        raise ValidationError(_('Bill of lading detail does not exist!'))


            else:
                raise ValidationError(_('Cargo can not null!'))

            records = {
                'length': len(list_bill_lading_detail_json),
                'records': list_bill_lading_detail_json
            }
            simplejson.dumps(records, indent=4, sort_keys=True, default=str)
            return records

    def confirm_quantity_package_bill_package(self,cargo_id, list_bill_package_id_confirm):
        if cargo_id is None:
            raise ValidationError(_('Cargo id is null!'))
        if len(list_bill_package_id_confirm) <= 0:
            raise ValidationError(_('List bill package id null'))

        record_cargo = http.request.env[Cargo._name]. \
            web_search_read([['id', '=', cargo_id]], fields=None,
                            offset=0, limit=10, order='')
        if record_cargo['records']:
            query_get_bill_lading_detail_cargo_rel = """ SELECT json_agg(t)
                                                                                FROM (  SELECT sharevan_cargo_id, sharevan_bill_lading_detail_id
	                                                      FROM public.sharevan_bill_lading_detail_sharevan_cargo_rel rel where rel.sharevan_cargo_id = %s ) t """
            self.env.cr.execute(query_get_bill_lading_detail_cargo_rel, (cargo_id,))
            result_get_bill_lading_detail_cargo_rel = self._cr.fetchall()
            list_bill_lading_detail_id = []
            list_bill_package_id = []
            if result_get_bill_lading_detail_cargo_rel[0][0]:
                for rec in result_get_bill_lading_detail_cargo_rel[0][0]:
                    list_bill_lading_detail_id.append(rec['sharevan_bill_lading_detail_id'])
                for re in list_bill_lading_detail_id:
                    query_get_bill_lading_package = """ SELECT json_agg(t)
                                                                            FROM ( select sbp.id from  sharevan_bill_package sbp where sbp.bill_lading_detail_id = %s ) t """
                    self.env.cr.execute(query_get_bill_lading_package, (re,))
                    result_get_bill_lading_package = self._cr.fetchall()
                    if result_get_bill_lading_package[0][0]:
                        list_bill_package_id.append(result_get_bill_lading_package[0][0][0]['id'])
                a_set = set(list_bill_package_id)
                b_set = set(list_bill_package_id_confirm)
                if (a_set & b_set):
                    http.request.env[Cargo._name]. \
                        browse(cargo_id).write(
                        {'status': '1'})
                    return True
                else:
                    return False








        else:
            raise ValidationError(_('Cargo does not exist!'))
        # if record_bidding_vehicle['records']:
        #     if record_bidding_order['records'][0]:
        #         http.request.env[BiddingOrder._name]. \
        #             browse(record_bidding_order['records'][0]['id']).write(
        #             {'bidding_vehicle_id': bidding_vehicle_id})






