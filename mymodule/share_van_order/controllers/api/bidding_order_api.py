# -*- coding: utf-8 -*-
import json as simplejson
import werkzeug

from mymodule.share_van_order.controllers.api.base import BaseApi
from odoo import http
from datetime import datetime


class BiddingOrderApi:
    MODEL = 'sharevan.bidding.order'

    @staticmethod
    def get_history_bidding(**kwargs):
        print(kwargs)
        order_by = None
        offset = 0
        limit = 10
        fromDate = None
        toDate = None
        fromActualTime = None
        toActualTime = None
        status='1'
        for arg in kwargs:
            if arg == 'fromDate':
                fromDate = kwargs.get(arg)
            if arg == 'toDate':
                toDate = kwargs.get(arg)
            if arg == 'order_by':
                order_by = kwargs.get(arg)
            if arg == 'offset':
                offset = kwargs.get(arg)
            if arg == 'limit':
                limit = kwargs.get(arg)
            if arg == 'status':
                status = kwargs.get(arg)
            if arg == 'fromActualTime':
                fromActualTime = kwargs.get(arg)
            if arg == 'toActualTime':
                toActualTime = kwargs.get(arg)
        paging = ' offset ' + str(offset) + ' limit ' + str(limit)
        query = """
        SELECT json_agg(t)
            FROM (
              select distinct cargo.id cargo_id,
                      cargo.cargo_number,
                      cargo.status,
                      TO_CHAR(cargo.confirm_time, 'YYYY-MM-DD HH24:MI:SS') confirm_time,
                      cargo.from_depot_id,
                      cargo.to_depot_id,
                      cargo.distance,
                      cargo.size_id,
                      cargo.quantity,
                      TO_CHAR(cargo.from_receive_time, 'YYYY-MM-DD HH24:MI:SS') from_receive_time,
                      TO_CHAR(cargo.to_receive_time, 'YYYY-MM-DD HH24:MI:SS') to_receive_time ,
                      TO_CHAR(cargo.from_return_time, 'YYYY-MM-DD HH24:MI:SS')  from_return_time,
                      TO_CHAR(cargo.to_return_time, 'YYYY-MM-DD HH24:MI:SS')  to_return_time,
                      cargo.bidding_order_id,
                      TO_CHAR(bidding.create_date, 'YYYY-MM-DD HH24:MI:SS') create_date,
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
                      bidding.distance,
                      bidding.status,
                      bidding.type,
                      price.price,
                      product_type.name,
					  depot.name from_depot_name,
					  depot.address from_depot_address,
					  to_depot.name to_depot_name,
					  to_depot.address to_depot_address
            from sharevan_bidding_order bidding
               left join sharevan_cargo cargo on bidding.id = cargo.bidding_order_id
               left join sharevan_cargo_price price on price.cargo_id = cargo.id
			   left join sharevan_depot depot on depot.id = cargo.from_depot_id
			   left join sharevan_depot to_depot on to_depot.id = cargo.to_depot_id
               left join sharevan_product_type product_type on product_type.id = cargo.product_type_id
               join res_users us on us.company_id = bidding.company_id
            where 1=1 and price.status = 'running' 
			    and bidding.type = '1' and bidding.status = %s
			    and us.id =  %s 
			    """

        query_total = """          
                    select 
                        count(bidding.id)
                    from sharevan_bidding_order bidding
                        left join sharevan_cargo cargo on bidding.id = cargo.bidding_order_id
                        left join sharevan_cargo_price price on price.cargo_id = cargo.id
                        join res_users us on us.company_id = bidding.company_id
                    where 1=1 and price.status = 'running'
                        and bidding.type = '1' and bidding.status = %s 
        			    and us.id = %s
        			"""
        params = []
        params.append(status)
        params.append(http.request.env.uid)
        if fromDate:
            query += """ and  cargo.from_receive_time >= %s """
            query_total += """ and  cargo.from_receive_time >= %s """
            params.append(fromDate)
        if toDate:
            query += """ and  cargo.to_return_time <= %s """
            query_total += """ and  cargo.to_return_time <= %s """
            params.append(toDate)
        if fromActualTime:
            query += """ and  bidding.actual_time >= %s """
            query_total += """ and  bidding.actual_time >= %s """
            params.append(fromActualTime)
        if toActualTime:
            query += """ and  bidding.to_actual_time <= %s """
            query_total += """ and  bidding.to_actual_time <= %s """
            params.append(toActualTime)
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
                query += """ order by TO_CHAR(bidding.create_date, 'YYYY-MM-DD HH24:MI:SS') ASC """

            if order_by == '6':
                query += """ order by TO_CHAR(bidding.create_date, 'YYYY-MM-DD HH24:MI:SS') DESC """
        else:
            query += """ order by TO_CHAR(bidding.create_date, 'YYYY-MM-DD HH24:MI:SS') ASC """
        query += ' ' + paging + ' )t'
        http.request.env.cr.execute(query, params)
        result = http.request._cr.fetchall()
        jsonRe = []
        length_count = 0
        if len(result) > 0:
            if result[0][0]:
                length_count = len(result[0][0])
                for rec in result[0][0]:
                    content = {
                        'id': rec['id'],
                        'company_id': rec['company_id'],
                        'driver_name': rec['driver_name'],
                        'phone': rec['phone'],
                        'van_id': rec['van_id'],
                        'total_weight': rec['total_weight'],
                        'total_cargo': rec['total_cargo'],
                        'from_latitude': rec['from_latitude'],
                        'to_latitude': rec['to_latitude'],
                        'from_receive_time': rec['from_receive_time'],
                        'to_receive_time': rec['to_receive_time'],
                        'from_return_time': rec['from_return_time'],
                        'to_return_time': rec['to_return_time'],
                        'from_longitude': rec['from_longitude'],
                        'to_longitude': rec['to_longitude'],
                        'distance': rec['distance'],
                        'cargo_number': rec['cargo_number'],
                        'type': rec['type'],
                        'status': rec['status'],
                        'quantity': rec['quantity'],
                        'confirm_time': rec['confirm_time'],
                        'create_date': rec['create_date'],
                        'from_depot': {
                            'name': rec['from_depot_name'],
                            'address': rec['from_depot_address']
                        },
                        'to_depot': {
                            'to_depot_name': rec['to_depot_name'],
                            'address': rec['to_depot_address']
                        },
                        'product_type': {
                            'name': rec['name']
                        },
                        'price': {
                            'price': rec['price']
                        }
                    }
                    jsonRe.append(content)

        http.request.env.cr.execute(query_total, params)
        result = http.request._cr.fetchall()
        total_record = 0
        if result[0]:
            total_record = result[0][0]
        records = {
            'length': length_count,
            'total_record': total_record,
            'records': jsonRe
        }
        simplejson.dumps(records, indent=4, sort_keys=True, default=str)
        return records

    @staticmethod
    def get_history_bidding_price(**kwargs):
        fromDate = None
        toDate = None
        fromActualTime = None
        toActualTime = None

        for arg in kwargs:
            if arg == 'fromDate':
                fromDate = kwargs.get(arg)
            if arg == 'toDate':
                toDate = kwargs.get(arg)
            if arg == 'fromActualTime':
                fromActualTime = kwargs.get(arg)
            if arg == 'toActualTime':
                toActualTime = kwargs.get(arg)

        query_total = """          
                        select 
                            sum(bidding.price) price,
                            count(bidding.id)
                        from sharevan_bidding_order bidding
                            left join sharevan_cargo cargo on bidding.id = cargo.bidding_order_id
                           join res_users us on us.company_id = bidding.company_id
                        where 1=1

            			    and us.id = %s
            			"""

        params = []
        params.append(http.request.env.uid)
        if fromDate:
            query_total += """ and  cargo.from_receive_time >= %s """
            params.append(fromDate)
        if toDate:
            query_total += """ and  cargo.to_return_time <= %s """
            params.append(toDate)
        if fromActualTime:
            query_total += """ and  bidding.actual_time >= %s """
            params.append(fromActualTime)
        if toActualTime:
            query_total += """ and  bidding.to_actual_time <= %s """
            params.append(toActualTime)
        jsonRe = []
        http.request.env.cr.execute(query_total, params)
        result = http.request._cr.fetchall()
        total_record = 0
        total_price = 0
        if result[0]:
            total_price = result[0][0]
            total_record = result[0][1]
        content = {
            'price': total_price
        }
        jsonRe.append(content)
        records = {
            'length': 1,
            'total_record': total_record,
            'records': jsonRe
        }
        simplejson.dumps(records, indent=4, sort_keys=True, default=str)
        return records
