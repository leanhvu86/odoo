# -*- coding: utf-8 -*-
import json

import requests

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request, Response
from odoo.tools import logging, config, base64

_logger = logging.getLogger(__name__)

class BaseMethod:
    @staticmethod
    def generate_code_by_range(prefix, range, count, model, field):
        code = ''
        check = 0
        while True:
            if check < range - len(str(count)):
                code += '0'
            if check == range - len(str(count)):
                code += str(count + 1)
                record = http.request.env[model].search([(field, '=', prefix + code)])
                if record:
                    BaseMethod.generate_code_by_range(prefix, range, count, model, field)
                else:
                    return prefix + code
            check += 1

    @staticmethod
    def get_new_sequence(model, prefix, range, field):
        model_array = model.split('.')
        s = "_"
        s = s.join(model_array)
        query = """ select COALESCE(max(id),0) count from """
        query += s
        http.request.env[model]._cr.execute(query, ())
        count_record = http.request.env[model]._cr.dictfetchall()
        if count_record:
            count = int(count_record[0]['count'])
            return BaseMethod.generate_code_by_range(prefix, range, count, model, field)
        else:
            raise ValidationError('Please check parameter')

    @staticmethod
    def get_dlp_employee():
        ids = []
        # employee share van
        query = """
            select us.id from res_users us
                join res_company company on us.company_id = company.id
            where company.company_type = '2' and us.active = true  """
        http.request.cr.execute(query, ())
        record = http.request._cr.dictfetchall()
        if record:
            for re in record:
                ids.append(re['id'])
            return ids
        else:
            return ids

    @staticmethod
    def get_customer_employee(company_id, type):
        ids = []
        query = """ 
            select us.id from res_users us
                join sharevan_channel channel on channel.id = us.channel_id 
            where us.company_id = %s and us.active = true
                and channel.name = 'customer'  """
        if type == 'manager':
            query += """and channel_type = 'manager' """
        if type == 'employee':
            query += """and channel_type = 'employee' """
        if type == 'all':
            query += """and channel_type in ('manager','employee') """
        http.request.cr.execute(query, (company_id,))
        record = http.request._cr.dictfetchall()
        if record:
            for re in record:
                ids.append(re['id'])
            return ids
        else:
            return ids

    @staticmethod
    def get_fleet_manager(driver_id):
        driver = http.request.env['fleet.management.driver.temp'].search([('id', '=', driver_id)])
        manager_ids = []
        if driver:
            query_find_fleet_management = """    
                select fleet_driver_id,fleet_management_id ,max(from_date) max_date 
                from fleet_management_driver_temp f 
                where f.fleet_driver_id = %s and f.status = 'active' 
                group by fleet_driver_id,fleet_management_id 
                order by max_date DESC LIMIT 1 
            """
            http.request.cr.execute(query_find_fleet_management, (driver_id,))
            result_find_fleet_management = http.request._cr.dictfetchall()
            if result_find_fleet_management:
                query_get_list_id_manager = """   
                    select user_info.user_id from fleet_management_driver_temp f
                        join fleet_driver user_info on user_info.id = f.fleet_driver_id
                        where 1=1 and f.status = 'active' and lower(f.type) = 'manager' and f.fleet_management_id = %s 
                                                 """

                http.request.cr.execute(query_get_list_id_manager,
                                        (result_find_fleet_management[0]['fleet_management_id'],))
                result_get_list_id_manager = http.request._cr.dictfetchall()

                if result_get_list_id_manager:
                    if result_get_list_id_manager[0]:
                        manager_ids.append(result_get_list_id_manager[0]['user_id'])
        return manager_ids

    @staticmethod
    def rating_point_company(self, type=None, point=None, code=None, company_id=None, rating_place_id=None,
                             driver_id=None, note=None):
        # 2 tham số đầu vào :
        #     - type = 'Rating',point,company_id,driver_id,rating_place_id,note : Đánh giá khi bằng rating
        #     - type = 'AwardPoint', code, company_id,note: Cộng điểm khi đặt đơn hay gì đó
        rating_badges = http.request.env['sharevan.title.award'].search([('title_award_type', '=', 'customer')])
        company = http.request.env['res.company'].search([('id', '=', company_id)])
        if type is 'Rating':
            plus_point = company['point'] + point
            from_point_rank_current = company['award_company_id']['from_point']
            to_point_rank_current = company['award_company_id']['to_point']
            if plus_point > to_point_rank_current:
                for badges in rating_badges:
                    if badges['from_point'] < plus_point and plus_point < badges['to_point']:
                        self.env.cr.execute(""" 
                                                UPDATE public.res_company
                                                SET point= %s, award_company_id = %s 
                                                WHERE id = %s;  
                                                                                """,
                                            (plus_point, badges['id'], company['id']))
                        break
            else:
                self.env.cr.execute(""" 
                                        UPDATE public.res_company
                                        SET point= %s
                                        WHERE id = %s;  
                                                                                                """,
                                    (plus_point, company['id']))
            http.request.env['sharevan.rating.company'].create({
                'rating_place_id': rating_place_id,
                'company_id': company_id,
                'num_rating': plus_point,
                'driver_id': driver_id,
                'note': note,
            })
        if type is 'AwardPoint':
            reward_point = http.request.env['sharevan.reward.point'].search(
                [('code', '=', code), ('type_reward_point', '=', 'customer')])
            plus_point = company['point'] + reward_point['point']
            from_point_rank_current = company['award_company_id']['from_point']
            to_point_rank_current = company['award_company_id']['to_point']
            if plus_point > to_point_rank_current:
                for badges in rating_badges:
                    if badges['from_point'] < plus_point and plus_point > badges['to_point']:
                        self.env.cr.execute(""" 
                                               UPDATE public.res_company
                                               SET point= %s, award_company_id = %s 
                                               WHERE id = %s;  
                                               """,
                                            (plus_point, badges['id'], company['id']))
                        break
            else:
                self.env.cr.execute(""" 
                         UPDATE public.res_company
                         SET point= %s
                          WHERE id = %s;  
                           """,
                                    (plus_point, company['id']))

            http.request.env['sharevan.rating.company'].create({
                'company_id': company_id,
                'reward_point_id': reward_point['id'],
                'note': note,
            })

    @staticmethod
    def send_notification_driver(user, model, model_id, click_action, message_type, title, body, type, item_id,
                                 object_status):
        try:
            content = {
                'title': title,
                'content': body,
                'type': type,
                'res_id': model_id,
                'res_model': model,
                'click_action': click_action,
                'message_type': message_type,
                'user_id': user,
                'item_id': item_id,
                'object_status': object_status
            }
            http.request.env['sharevan.notification'].sudo().create(content)
        except:
            _logger.warn(
                "Send message fail!",
                'sharevan.notification', id,
                exc_info=True)

    @staticmethod
    def check_role_access(user, model, model_id):
        # driver
        # DLP employee
        # customer
        if user.channel_id.name == 'fleet' and user.channel_id.channel_type == 'employee':
            query = """   
                select * from fleet_driver where user_id = %s and employee_type = 'driver' """

            http.request.cr.execute(query,
                                    (user.id,))
            result = http.request._cr.dictfetchall()

            if result:
                check_allow = http.request.env[model].search(
                    [('driver_id', '=', result[0]['id']), ('id', '=', model_id)])
                if check_allow:
                    return True
                else:
                    raise ValidationError('You are not allow to view record')
            else:
                raise ValidationError('You are not allow to view record')
        elif user.channel_id.name == 'dlp':
            # nhân viên DLP cho phép  xử lý toàn bộ bên đơn hàng và routing
            return True
        else:
            check_allow = http.request.env[model].search(
                [('company_id', '=', user.company_id.id), ('id', '=', model_id)])
            if check_allow:
                return True
            else:
                raise ValidationError('You are not allow to view record')

    @staticmethod
    def reject_dlp_employee_on_data(user):
        if user.channel_id.name == 'dlp':
            # nhân viên DLP không được phép sửa data bên module khác
            return False
        else:
            return True

    @staticmethod
    def filter_by_team(list_model, join_model):
        list_result = []
        filter_querry = """
            select fleet_team.*,(select coalesce( us.id, 0) count from res_users us
            where us.is_admin = true and us.id = %s) from (WITH RECURSIVE c AS (
                SELECT (select fleet_management_id from fleet_driver
            where employee_type ='manager' and user_id = %s) AS id
                UNION ALL
                    SELECT sa.id
                FROM fleet_management AS sa
                    JOIN c ON c.id = sa.parent_id
                )
            SELECT id FROM c ) fleet_team
        """

        http.request.env.cr.execute(filter_querry,
                                    (http.request.env.uid, http.request.env.uid,))
        result = http.request._cr.dictfetchall()
        if result:
            if result[0]['count']:
                return list_model
            else:
                if join_model == False:
                    for rec in result:
                        for check_record in list_model:
                            if rec['id'] == check_record['fleet_management_id'].id:
                                list_result.append(check_record)
                    return list_result
                else:
                    for rec in result:
                        for check_record in list_model:
                            if check_record['driver_id']:
                                if rec['id'] == check_record['driver_id']['fleet_management_id'].id:
                                    list_result.append(check_record)
                            elif check_record['vehicle_id']:
                                if rec['id'] == check_record['vehicle_id']['fleet_management_id'].id:
                                    list_result.append(check_record)
                    return list_result
        else:
            return list_result

    @staticmethod
    def create_warehouse_log(depot_type, depot, warehouse_check):
        if depot_type and depot:
            # log tất cả các depot
            query_get_all_depot = """
                select * from sharevan_depot where id != %s and main_type = true and status =  'running'
            """
            http.request.env.cr.execute(query_get_all_depot,
                                        (depot.id,))
            result_get_all_depot = http.request._cr.dictfetchall()
            for record in result_get_all_depot:
                # check chính xác bản ghi from - to
                query_log = """
                    select * from sharevan_warehouse_log where from_name = %s and to_name =%s
                """
                http.request.env.cr.execute(query_log,
                                            (depot.depot_code, record['depot_code'],))
                log_record = http.request._cr.dictfetchall()
                if log_record:
                    pass
                else:
                    vals = {
                        'from_name': depot.depot_code,
                        'to_name': record['depot_code'],
                        'from_latitude': depot.latitude,
                        'from_longitude': depot.longitude,
                        'to_latitude': record['latitude'],
                        'to_longitude': record['longitude'],
                        'scan_check': False,
                    }
                    http.request.env['sharevan.warehouse.log'].sudo().create(vals)
                query_log = """
                    select * from sharevan_warehouse_log where from_name = %s and to_name =%s
                """
                http.request.env.cr.execute(query_log,
                                            (record['depot_code'], depot.depot_code,))
                log_record = http.request._cr.dictfetchall()
                if log_record:
                    pass
                else:
                    vals = {
                        'from_name': record['depot_code'],
                        'to_name': depot.depot_code,
                        'from_latitude': record['latitude'],
                        'from_longitude': record['longitude'],
                        'to_latitude': depot.latitude,
                        'to_longitude': depot.longitude,
                        'scan_check': False,
                    }
                    http.request.env['sharevan.warehouse.log'].sudo().create(vals)
            # log tất cả các hub trong hệ thống của zone đó
            query_get_all_hub = """
                select * from sharevan_depot 
                    where zone_id = %s and main_type = false and status = 'running'
            """
            http.request.env.cr.execute(query_get_all_hub,
                                        (depot.zone_id.id,))
            result_get_all_hub = http.request._cr.dictfetchall()
            for hub in result_get_all_hub:
                # check chính xác bản ghi from - to
                query_log = """
                    select * from sharevan_warehouse_log where from_name = %s and to_name =%s
                """
                http.request.env.cr.execute(query_log,
                                            (depot.depot_code, hub['depot_code'],))
                log_record = http.request._cr.dictfetchall()
                if log_record:
                    pass
                else:
                    vals = {
                        'from_name': depot.depot_code,
                        'to_name': hub['depot_code'],
                        'from_latitude': depot.latitude,
                        'from_longitude': depot.longitude,
                        'to_latitude': hub['latitude'],
                        'to_longitude': hub['longitude'],
                        'scan_check': False,
                    }
                    http.request.env['sharevan.warehouse.log'].sudo().create(vals)
                query_log = """
                    select * from sharevan_warehouse_log where from_name = %s and to_name =%s
                """
                http.request.env.cr.execute(query_log,
                                            (hub['depot_code'], depot.depot_code,))
                log_record = http.request._cr.dictfetchall()
                if log_record:
                    pass
                else:
                    vals = {
                        'from_name': hub['depot_code'],
                        'to_name': depot.depot_code,
                        'from_latitude': hub['latitude'],
                        'from_longitude': hub['longitude'],
                        'to_latitude': depot.latitude,
                        'to_longitude': depot.longitude,
                        'scan_check': False,
                    }
                    http.request.env['sharevan.warehouse.log'].sudo().create(vals)
            # log tất cả các kho trong hệ thống của zone đó
            query_get_all_warehouse = """
                select * from sharevan_warehouse warehouse
                    join sharevan_area area on warehouse.area_id = area.id
                where area.zone_area_id =  %s
            """
            http.request.env.cr.execute(query_get_all_warehouse,
                                        (depot.zone_id.id,))
            result_get_all_warehouse = http.request._cr.dictfetchall()
            for warehouse in result_get_all_warehouse:
                # check chính xác bản ghi from - to
                query_log = """
                    select * from sharevan_warehouse_log where from_name = %s and to_name =%s
                """
                http.request.env.cr.execute(query_log,
                                            (depot.depot_code, warehouse['warehouse_code'],))
                log_record = http.request._cr.dictfetchall()
                if log_record:
                    pass
                else:
                    vals = {
                        'from_name': depot.depot_code,
                        'to_name': warehouse['warehouse_code'],
                        'from_latitude': depot.latitude,
                        'from_longitude': depot.longitude,
                        'to_latitude': warehouse['latitude'],
                        'to_longitude': warehouse['longitude'],
                        'scan_check': False,
                    }
                    http.request.env['sharevan.warehouse.log'].sudo().create(vals)
                query_log = """
                    select * from sharevan_warehouse_log where from_name = %s and to_name =%s
                """
                http.request.env.cr.execute(query_log,
                                            (warehouse['warehouse_code'], depot.depot_code,))
                log_record = http.request._cr.dictfetchall()
                if log_record:
                    pass
                else:
                    vals = {
                        'from_name': warehouse['warehouse_code'],
                        'to_name': depot.depot_code,
                        'from_latitude': warehouse['latitude'],
                        'from_longitude': warehouse['longitude'],
                        'to_latitude': depot.latitude,
                        'to_longitude': depot.longitude,
                        'scan_check': False,
                    }
                    http.request.env['sharevan.warehouse.log'].sudo().create(vals)
        elif depot:
            # log tất cả các depot và hub trong hệ thống của zone đó
            query_get_all_hub = """
                select * from sharevan_depot where zone_id = %s and status = 'running'
                        """
            http.request.env.cr.execute(query_get_all_hub,
                                        (depot.zone_id.id,))
            result_get_all_hub = http.request._cr.dictfetchall()
            for hub in result_get_all_hub:
                # check chính xác bản ghi from - to
                query_log = """
                    select * from sharevan_warehouse_log where from_name = %s and to_name =%s
                            """
                http.request.env.cr.execute(query_log,
                                            (depot.depot_code, hub['depot_code'],))
                log_record = http.request._cr.dictfetchall()
                if log_record:
                    pass
                else:
                    vals = {
                        'from_name': depot.depot_code,
                        'to_name': hub['depot_code'],
                        'from_latitude': depot.latitude,
                        'from_longitude': depot.longitude,
                        'to_latitude': hub['latitude'],
                        'to_longitude': hub['longitude'],
                        'scan_check': False,
                    }
                    http.request.env['sharevan.warehouse.log'].sudo().create(vals)
                query_log = """
                    select * from sharevan_warehouse_log where from_name = %s and to_name =%s
                            """
                http.request.env.cr.execute(query_log,
                                            (hub['depot_code'], depot.depot_code,))
                log_record = http.request._cr.dictfetchall()
                if log_record:
                    pass
                else:
                    vals = {
                        'from_name': hub['depot_code'],
                        'to_name': depot.depot_code,
                        'from_latitude': hub['latitude'],
                        'from_longitude': hub['longitude'],
                        'to_latitude': depot.latitude,
                        'to_longitude': depot.longitude,
                        'scan_check': False,
                    }
                    http.request.env['sharevan.warehouse.log'].sudo().create(vals)
            # log tất cả các kho trong area đó
            query_get_all_warehouse = """
                select * from sharevan_warehouse warehouse
                    join sharevan_area area on warehouse.area_id = area.id
                where area.id = %s
            """
            http.request.env.cr.execute(query_get_all_warehouse,
                                        (depot.group_area_id.id,))
            result_get_all_warehouse = http.request._cr.dictfetchall()
            for warehouse in result_get_all_warehouse:
                # check chính xác bản ghi from - to
                query_log = """
                    select * from sharevan_warehouse_log where from_name = %s and to_name =%s
                """
                http.request.env.cr.execute(query_log,
                                            (depot.depot_code, warehouse['warehouse_code'],))
                log_record = http.request._cr.dictfetchall()
                if log_record:
                    pass
                else:
                    vals = {
                        'from_name': depot.depot_code,
                        'to_name': warehouse['warehouse_code'],
                        'from_latitude': depot.latitude,
                        'from_longitude': depot.longitude,
                        'to_latitude': warehouse['latitude'],
                        'to_longitude': warehouse['longitude'],
                        'scan_check': False,
                    }
                    http.request.env['sharevan.warehouse.log'].sudo().create(vals)
                query_log = """
                    select * from sharevan_warehouse_log where from_name = %s and to_name =%s
                """
                http.request.env.cr.execute(query_log,
                                            (warehouse.warehouse_code, depot.depot_code,))
                log_record = http.request._cr.dictfetchall()
                if log_record:
                    pass
                else:
                    vals = {
                        'from_name': warehouse['warehouse_code'],
                        'to_name': depot.depot_code,
                        'from_latitude': warehouse['latitude'],
                        'from_longitude': warehouse['longitude'],
                        'to_latitude': depot.latitude,
                        'to_longitude': depot.longitude,
                        'scan_check': False,
                    }
                    http.request.env['sharevan.warehouse.log'].sudo().create(vals)
        elif warehouse_check:
            # log tất cả các depot và hub trong hệ thống của zone đó
            query_get_all_hub = """
                select * from sharevan_depot depot
                    join sharevan_area area on area.zone_area_id = depot.zone_id 
                where area_id = %s and depot.status = 'running'
                                    """
            http.request.env.cr.execute(query_get_all_hub,
                                        (warehouse_check.area_id.id,))
            result_get_all_hub = http.request._cr.dictfetchall()
            for hub in result_get_all_hub:
                # check chính xác bản ghi from - to
                query_log = """
                    select * from sharevan_warehouse_log where from_name = %s and to_name =%s
                                        """
                http.request.env.cr.execute(query_log,
                                            (warehouse_check.warehouse_code, hub.depot_code,))
                log_record = http.request._cr.dictfetchall()
                if log_record:
                    pass
                else:
                    vals = {
                        'from_name': warehouse_check.depot_code,
                        'to_name': hub.depot_code,
                        'from_latitude': warehouse_check.latitude,
                        'from_longitude': warehouse_check.longitude,
                        'to_latitude': hub.latitude,
                        'to_longitude': hub.longitude,
                        'scan_check': False,
                    }
                    http.request.env['sharevan.warehouse.log'].sudo().create(vals)
                query_log = """
                                select * from sharevan_warehouse_log where from_name = %s and to_name =%s
                                        """
                http.request.env.cr.execute(query_log,
                                            (hub.depot_code, depot.depot_code,))
                log_record = http.request._cr.dictfetchall()
                if log_record:
                    pass
                else:
                    vals = {
                        'from_name': hub.depot_code,
                        'to_name': warehouse_check.warehouse_code,
                        'from_latitude': hub.latitude,
                        'from_longitude': hub.longitude,
                        'to_latitude': warehouse_check.latitude,
                        'to_longitude': warehouse_check.longitude,
                        'scan_check': False,
                    }
                    http.request.env['sharevan.warehouse.log'].sudo().create(vals)
            # log tất cả các kho trong area đó
            query_get_all_warehouse = """
                select * from sharevan_warehouse warehouse
                    join sharevan_area area_zone on warehouse.area_id = area_zone.id
                    join sharevan_area area_old on area_old.zone_area_id = area_zone.zone_area_id
                where area_old.id = %s and warehouse.id != %s
            """
            http.request.env.cr.execute(query_get_all_warehouse,
                                        (warehouse_check.area_id.id,warehouse_check.id,))
            result_get_all_warehouse = http.request._cr.dictfetchall()
            matrix_count= 0
            exist_count= 0
            print(len(result_get_all_warehouse))
            for warehouse in result_get_all_warehouse:
                # check chính xác bản ghi from - to
                query_log = """
                    select * from sharevan_warehouse_log where from_name = %s and to_name =%s
                            """
                http.request.env.cr.execute(query_log,
                                            (warehouse_check.warehouse_code, warehouse['warehouse_code'],))
                log_record = http.request._cr.dictfetchall()
                if log_record:
                    pass
                    exist_count+=1
                else:
                    matrix_count += 1
                    vals = {
                        'from_name': warehouse_check.warehouse_code,
                        'to_name': warehouse['warehouse_code'],
                        'from_latitude': warehouse_check.latitude,
                        'from_longitude': warehouse_check.longitude,
                        'to_latitude': warehouse['latitude'],
                        'to_longitude': warehouse['longitude'],
                        'scan_check': False,
                    }
                    http.request.env['sharevan.warehouse.log'].sudo().create(vals)
                query_log = """
                    select * from sharevan_warehouse_log where from_name = %s and to_name =%s
                            """
                http.request.env.cr.execute(query_log,
                                            (warehouse['warehouse_code'], warehouse_check.warehouse_code,))
                log_record = http.request._cr.dictfetchall()
                if log_record:
                    exist_count += 1
                else:
                    matrix_count += 1
                    vals = {
                        'from_name': warehouse['warehouse_code'],
                        'to_name': warehouse_check.warehouse_code,
                        'from_latitude': warehouse['latitude'],
                        'from_longitude': warehouse['longitude'],
                        'to_latitude': warehouse_check.latitude,
                        'to_longitude': warehouse_check.longitude,
                        'scan_check': False,
                    }
                    http.request.env['sharevan.warehouse.log'].sudo().create(vals)
            warehouse_record = http.request.env['sharevan.warehouse'].search([('id', '=', warehouse_check['id'])])
            warehouse_record.write({'scan_check':True})
            _logger.info(
                "Run schedule for distance success!" + warehouse_check.warehouse_code+ 'existed'+ str(exist_count) + 'new '+str(matrix_count))

    @staticmethod
    def check_authorized():
        if request.httprequest.headers.get('X-Openerp-Session-Id'):
            session = http.root.session_store.get(request.httprequest.headers.get('X-Openerp-Session-Id'))
            if not session['db']:
                return None,None
            headers = {
                'Authorization':request.httprequest.headers.get('AUTHORIZATION'),
                'Accept-Language': 'en'
            }
            me = requests.get(config['sso_port'] + "/user/me", headers=headers).content
            bytesThing = str(me, 'utf-8')
            data_json = json.dumps(bytesThing)
            if 'error' in data_json:
                request.session.logout()
            authorities = json.loads(bytesThing)['authorities']
            check = False
            for auth in authorities:
                if auth['authority'] == request.httprequest.path:
                    check = True
                    break
            if check == False:
                _logger.debug(
                    json.loads(bytesThing)['name'] + " is not authorized this principal: " + request.httprequest.path,
                    'routing filter', '',
                    exc_info=True)
                return None,None
            data_json={}
            if request.httprequest.data and request.httprequest.data!= b'':
                search_object = request.httprequest.data
                bytesThing = str(search_object, 'utf-8')
                data_json = json.loads(bytesThing)['params']
            return session,data_json
        else:
            return None,None

    @staticmethod
    def get_excel_reponse(out_file, out_name,template):
        if not template:
            return Response('Templete not found', content_type="application/json", status=500)
        else:
            vals = {
                "state": "get",
                "data": out_file,
                "name": out_name,
                'template_id': template['id'],
            }
            record = http.request.env['report.res.users'].sudo().create(vals)
            status, headers, content = request.env['ir.http'].binary_content(
                xmlid=None, model='report.res.users', id=record['id'], field='data', unique=None, filename=out_name,
                filename_field='name', download=True, mimetype=None, access_token=None)
            content_base64 = base64.b64decode(content)
            headers.append(('Content-Length', len(content_base64)))
            response = request.make_response(content_base64, headers)
            response.set_cookie('fileToken', 'token')
            return response