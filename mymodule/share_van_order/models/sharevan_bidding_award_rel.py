import calendar
from datetime import datetime, timedelta

import simplejson

from odoo import fields, models
from ...constants import Constants


class CompanyAwardRel(models.Model):
    _name = 'sharevan.bidding.award.rel'
    _description = 'Show all awards of company'

    company_id = fields.Many2one(Constants.RES_COMPANY, string="Company")
    company_award_id = fields.Many2one('company_award', string='Company award')


class ShareVanDriverRecieved(models.Model):
    _name = 'sharevan.driver.received'
    _inherit = 'sharevan.driver.received'
    _description = 'ShareVan driver received'

    pay_check = fields.Boolean(string='Pay check', default=True)
    discount_amount = fields.Float(string='Discount amount', default=True)
    status = fields.Selection([('running', 'Running'), ('deleted', 'Deleted')], string='Status',
                              default='running')
    receive_type = fields.Selection([('0', 'Received'), ('1', 'Withdrawal')], string='Receive Type',
                                    default='0')
    driver_id = fields.Many2one('fleet.driver', string='Driver', required=True)

    def get_driver_wallet(self, **kwargs):
        print(kwargs)
        offset = False
        limit = False
        param = []
        page = None
        month = None
        year = None
        receive_type = None
        for arg in kwargs:
            if arg == 'receive_type':
                receive_type = kwargs.get(arg)
            if arg == 'month':
                month = kwargs.get(arg)
            if arg == 'year':
                year = kwargs.get(arg)
            if arg == 'offset':
                offset = kwargs.get(arg)
                page = ' offset ' + str(offset)
            if arg == 'limit':
                limit = kwargs.get(arg)
                if page:
                    page += ' limit ' + str(limit)
        query = """
            SELECT received.id, received.code, received.driver_level_id, received.percent_commission, received.coupon_id, 
                received.amount, received.total_amount, received.create_uid, 
                received.create_date, received.write_uid, received.write_date, received.pay_check, received.discount_amount, received.status, 
                received.driver_id, received.order_id, received.order_type, received.name, received.commission, received.receive_type
	        FROM public.sharevan_driver_received received
	            join fleet_driver driver on driver.user_id =  received.user_id
            where 1 =1    and received.status = 'running' and driver.user_id =%s
        """
        query_count = """
            SELECT count(received.id) count
	        FROM public.sharevan_driver_received received
	            join fleet_driver driver on driver.user_id =  received.user_id
            where 1 =1    and received.status = 'running' and driver.user_id = %s 
        """
        param.append(self.env.uid)
        if month and year:
            cal = calendar.monthrange(year, month)
            first_date = str(year) + '-' + str(month) + '-' + str(cal[0])
            last_date = str(year) + '-' + str(month) + '-' + str(cal[1])
            query += """ and received.create_date >= %s  
                         and received.create_date <= %s  
                          """
            query_count += """ and received.create_date >= %s  
                         and received.create_date <= %s  
                          """
            param.append(str(first_date))
            param.append(str(last_date))
        if receive_type == '0':
            query += """ and receive_type = %s """
            query_count += """ and receive_type = %s """
            param.append(receive_type)
        elif receive_type == '1':
            query += """ and receive_type = %s """
            query_count += """ and receive_type = %s """
            param.append(receive_type)
        else:
            query += """ and ( receive_type = '0' or receive_type = '1' )"""
            query_count += """ and ( receive_type = '0' or receive_type = '1' )"""

        if page:
            query += page

        self.env.cr.execute(query_count, (param))
        result_get_total_records = self._cr.dictfetchall()

        self.env.cr.execute(query, (param))
        result = self._cr.dictfetchall()
        total = 0
        if result_get_total_records:
            total = result_get_total_records[0]['count']
        if result:
            return {
                'records': result,
                'total_record': total
            }
        else:
            return {
                'records': [],
                'total_record': total
            }

    def get_driver_compute(self):
        today = datetime.today()
        print(today)
        last_day = today.day
        last_month = (today.month - 6) % 12
        last_year = today.year + ((today.month - 6) // 12)
        start_date = str(last_year) + "-" + str(last_month) + "-" + str(1)
        query = """
            SELECT
                DATE_TRUNC('month',received.create_date)
                    AS  month_amount,
                sum(total_amount) AS total_amount, receive_type
            FROM sharevan_driver_received received
                join fleet_driver driver on driver.user_id =  received.user_id
            where 1 =1   and received.status = 'running' and driver.user_id =%s
                and received.create_date >= %s
                GROUP BY DATE_TRUNC('month',received.create_date),receive_type
            order by DATE_TRUNC('month',received.create_date),receive_type asc"""
        self.env.cr.execute(query, (self.env.uid,start_date,))
        result = self._cr.dictfetchall()
        if result:
            val = {
                'month': '',
                'total_save': 0,
                'total_pay': 0,
                'total_amount': 0,
                'type': ''
            }
            jRe = []
            for rec in result:
                if rec['receive_type'] == '0':
                    val['month'] = rec['month_amount']
                    val['total_save'] = rec['total_amount']
                    val['type'] = rec['receive_type']
                else:
                    val['month'] = rec['month_amount']
                    val['total_save'] = rec['total_amount']
                    val['type'] = rec['receive_type']
                check_pay = False
                for rec in result:
                    if rec['receive_type'] != val['type'] and rec['month_amount'] == val['month']:
                        if rec['total_amount']:
                            val['total_pay'] = rec['total_amount']
                            val['total_amount'] = val['total_save'] - val['total_pay']
                            check_pay = True
                if check_pay == False:
                    val['total_amount'] = val['total_save']
                check_exist = False
                for check in jRe:
                    if check['month'] == val['month']:
                        check_exist = True
                if check_exist == False:
                    jRe.append(val)
                    val = {
                        'month': '',
                        'total_save': 0,
                        'total_pay': 0,
                        'total_amount': 0,
                        'type': ''
                    }
            records = {
                'records': jRe,
            }
            simplejson.dumps(records, indent=4, sort_keys=True, default=str)
            return records
        else:
            return {
                'records': []
            }

    def get_driver_last_money(self):
        query = """
             SELECT   COALESCE(sum(total_amount),0) get_amount,( SELECT   COALESCE(sum(total_amount),0) get_amount
                FROM public.sharevan_driver_received received
                            join fleet_driver driver on driver.user_id =  received.user_id
                where 1 =1    and received.status = 'running' and driver.user_id = %s
                            and received.receive_type ='1') pay_amount
                FROM public.sharevan_driver_received received
                            join fleet_driver driver on driver.id =  received.driver_id
                where 1 =1    and received.status = 'running' and driver.user_id = %s
                            and received.receive_type ='0'
        """
        self.env.cr.execute(query, (self.env.uid,self.env.uid,))
        result = self._cr.dictfetchall()
        if result:
            now_amount = int(result[0]['get_amount']) - int(result[0]['pay_amount'])
            return now_amount
        else:
            return 0
