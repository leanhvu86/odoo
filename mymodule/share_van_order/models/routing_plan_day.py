import base64

import geopy

from mymodule.base_next.controllers.api.base_method import BaseMethod
from mymodule.base_next.controllers.api.file_controller import FileApi
from mymodule.base_next.models.depot_goods import DepotGoods
from mymodule.base_next.models.fleet import FleetVehicle
from mymodule.base_next.models.notification import *
# from mymodule.base_next.models.warehouse import Depot
from mymodule.enum.BillRoutingStatus import BillRoutingStatus
from mymodule.enum.MessageType import NotificationSocketType
from mymodule.enum.NotificationType import NotificationType
from mymodule.enum.RoutingDetailStatus import RoutingDetailStatus
from mymodule.enum.StaffType import StaffType
from mymodule.enum.WarehouseType import WarehouseType
from mymodule.share_van_order.models.bill_lading_detail import BillLadingDetail
from mymodule.share_van_order.models.bill_package_routing import BillRouting
from odoo import _
from odoo.addons.base.models.ir_attachment import IrAttachment
from odoo.http import Response

INSERT_QUERY = "INSERT INTO ir_attachment_sharevan_routing_plan_day_rel " \
               " VALUES ( %s , %s ) "

logger = logging.getLogger(__name__)


class RoutingPlanDay(models.Model):
    _name = 'sharevan.routing.plan.day'
    MODEL = 'sharevan.routing.plan.day'
    _inherit = 'sharevan.routing.plan.day'
    _description = ' routing .plan. day'

    total_volume = fields.Float('Total volume')
    capacity_vehicle = fields.Float('Capacity vehicle')
    capacity_actual = fields.Float('Capacity actual')
    bill_routing_id = fields.Many2one('sharevan.bill.routing', 'Bill Routing')
    routing_vehicle_id = fields.Many2one('sharevan.routing.vehicle', 'Vehicle Routing')
    change_bill_lading_detail_id = fields.Many2one('sharevan.bill.lading.detail', 'Bill detail change')
    driver_arrived_time = fields.Date('Arrived time')
    claim_type = fields.Boolean('Claim type', default=False)
    redirect_routing = fields.Boolean('Redirect routing', default=False)

    def get_driver_routing_plan(self, **kwargs):
        driver_id = False
        date = False
        from_date = False
        to_date = False
        offset = False
        limit = False
        page = False
        total_record = 0
        status = []
        param = []
        routing_plan_code = False
        bill_routing_code = False
        for arg in kwargs:
            if arg == 'driver_id':
                driver_id = kwargs.get(arg)
            if arg == 'date':
                date = kwargs.get(arg)
            if arg == 'status':
                status = kwargs.get(arg)
            if arg == 'routing_plan_code':
                routing_plan_code = kwargs.get(arg)
            if arg == 'bill_routing_code':
                bill_routing_code = kwargs.get(arg)
            if arg == 'from_date':
                from_date = kwargs.get(arg)
            if arg == 'to_date':
                to_date = kwargs.get(arg)
            if arg == 'offset':
                offset = kwargs.get(arg)
                page = ' offset ' + str(offset)
            if arg == 'limit':
                limit = kwargs.get(arg)
                if page:
                    page += ' limit ' + str(limit)
        count_query = """
            SELECT count(plan.id)
                    FROM sharevan_routing_plan_day plan
                join sharevan_bill_routing bill_routing on bill_routing.id = plan.bill_routing_id
            WHERE plan.driver_id =
        """
        count_query += str(driver_id)
        count_query += """ and plan.status::integer in ( """
        if date:
            query = """
            SELECT json_agg(t)
                            FROM (
                SELECT plan.id, plan.routing_plan_day_code, plan.status, plan.type, plan.latitude, plan.longitude,
                        plan.address,TO_CHAR(plan.expected_from_time, 'YYYY-MM-DD HH24:MI:SS') expected_from_time,
                        TO_CHAR(plan.expected_to_time, 'YYYY-MM-DD HH24:MI:SS') expected_to_time,
                        plan.warehouse_name,plan.previous_id,plan.next_id,
                        plan.phone, plan.order_number, us.login ,plan.so_type, plan.warehouse_id,plan.company_id,
                        COALESCE(plan.check_point,false) check_point,COALESCE(plan.arrived_check,false) arrived_check,
                        plan.order_number,plan.capacity_expected,plan.rating_customer,
                        plan.company_id, ins.name insurance_id,ins.name insurance_name,
                        plan.description, plan.type, part.name,plan.ship_type,plan.qr_gen_check,
                        TO_CHAR(plan.due_time, 'YYYY-MM-DD HH24:MI:SS') due_time, 
                        TO_CHAR(plan.ready_time, 'YYYY-MM-DD HH24:MI:SS') ready_time, 
                        TO_CHAR(plan.write_date, 'YYYY-MM-DD HH24:MI:SS') write_date ,
                        TO_CHAR(plan.date_plan, 'YYYY-MM-DD HH24:MI:SS')  date_plan ,
                        TO_CHAR(plan.confirm_time, 'YYYY-MM-DD HH24:MI:SS')  confirm_time,
                        TO_CHAR(plan.accept_time, 'YYYY-MM-DD HH24:MI:SS')  accept_time,
                        bill_routing.name bill_routing_name, COALESCE(plan.trouble_type,'0') trouble_type
                    FROM sharevan_routing_plan_day plan
                        left join sharevan_insurance ins on ins.id= plan.insurance_id
                        left join res_users us on us.id = plan.write_uid
                        join fleet_vehicle veh on veh.id = plan.vehicle_id
                        join sharevan_bill_routing bill_routing on bill_routing.id = plan.bill_routing_id
                        left join res_partner part on part.id = plan.partner_id
                WHERE plan.driver_id = %s """ % (str(driver_id),)
            query += """ and plan.status::integer in ( """
            if status:
                for sta in status:
                    query += str(sta) + ","
                    count_query += str(sta) + ","
                query = query[:-1]
                count_query = count_query[:-1]
                query += ")"
                count_query += ")"
            query += """ and plan.date_plan = '""" + str(date) + """' """
            count_query += """ and plan.date_plan = '""" + str(date) + """' """
            if bill_routing_code:
                query += """ and ( LOWER(plan.routing_plan_day_code) like LOWER('%%%s%%')  """ % (bill_routing_code,)
                count_query += """ and ( LOWER(plan.routing_plan_day_code) like LOWER('%%%s%%')  """ % (
                    bill_routing_code,)
                query += """ or LOWER(bill_routing.name) like LOWER('%%%s%%')  """ % (bill_routing_code,)
                count_query += """ or LOWER(bill_routing.name) like LOWER('%%%s%%')  """ % (bill_routing_code,)
                query += """ )  """
                count_query += """ )  """
            query += """ order by plan.date_plan ASC ,plan.order_number )t """
            # if page:
            #     query += page
            self.env.cr.execute(query,
                                ())
        if from_date and to_date:
            query = """
            SELECT json_agg(t)
                            FROM (
                SELECT plan.id, plan.routing_plan_day_code, plan.status, plan.type, plan.latitude, plan.longitude,
                        plan.address,
                        TO_CHAR(plan.expected_from_time, 'YYYY-MM-DD HH24:MI:SS') expected_from_time,
                        TO_CHAR(plan.expected_to_time, 'YYYY-MM-DD HH24:MI:SS') expected_to_time,
                        plan.warehouse_name,plan.previous_id,plan.next_id,
                        plan.phone, plan.order_number, us.login ,plan.so_type,
                        COALESCE(plan.check_point,false) check_point, plan.warehouse_id,plan.company_id,
                        COALESCE(plan.arrived_check,false) arrived_check,plan.qr_gen_check,
                        plan.order_number,plan.capacity_expected,
                        plan.company_id,ins.name insurance_id,ins.name insurance_name,
                        plan.description, plan.type, part.name,plan.ship_type, plan.rating_customer,
                        TO_CHAR(plan.due_time, 'YYYY-MM-DD HH24:MI:SS') due_time, 
                        TO_CHAR(plan.ready_time, 'YYYY-MM-DD HH24:MI:SS') ready_time, 
                        TO_CHAR(plan.write_date, 'YYYY-MM-DD HH24:MI:SS') write_date ,
                        TO_CHAR(plan.date_plan, 'YYYY-MM-DD HH24:MI:SS')  date_plan ,
                        TO_CHAR(plan.confirm_time, 'YYYY-MM-DD HH24:MI:SS')  confirm_time,
                        COALESCE(plan.trouble_type,'0') trouble_type,
                        TO_CHAR(plan.accept_time, 'YYYY-MM-DD HH24:MI:SS')  accept_time,bill_routing.name bill_routing_name
                    FROM sharevan_routing_plan_day plan
                        left join sharevan_insurance ins on ins.id= plan.insurance_id
                        join sharevan_bill_routing bill_routing on bill_routing.id = plan.bill_routing_id
                        left join res_users us on us.id = plan.write_uid
                        join res_partner part on part.id = plan.partner_id
                WHERE plan.driver_id = %s """ % (str(driver_id),)
            query += """ and plan.status::integer in ("""
            if status:
                for sta in status:
                    query += str(sta) + ","
                    count_query += str(sta) + ","
                query = query[:-1]
                count_query = count_query[:-1]
                query += ")"
                count_query += ")"
            query += """ and plan.date_plan >= '""" + str(from_date) + """'  and plan.date_plan <=  '""" + str(
                to_date) + """' """
            count_query += """ and plan.date_plan >= '""" + str(from_date) + """' and plan.date_plan <=  '""" + str(
                to_date) + """' """
            if bill_routing_code:
                query += """ and ( LOWER(plan.routing_plan_day_code) like LOWER('%%%s%%')  """ % (bill_routing_code,)
                count_query += """ and ( LOWER(plan.routing_plan_day_code) like LOWER('%%%s%%')  """ % (
                    bill_routing_code,)
                query += """ or LOWER(bill_routing.name) like LOWER('%%%s%%')  """ % (bill_routing_code,)
                count_query += """ or LOWER(bill_routing.name) like LOWER('%%%s%%')  """ % (bill_routing_code,)
                query += """ )  """
                count_query += """ )  """
            query += """ order by plan.date_plan ASC , plan.order_number  """
            if page:
                query += page + " )t"
            self.env.cr.execute(query,
                                ())
        result = self._cr.fetchall()
        if date:
            self.env.cr.execute(count_query,
                                ())
        elif from_date and to_date:
            self.env.cr.execute(count_query,
                                ())
        count = self._cr.fetchall()
        total_record = count[0][0]
        jsonRe = {
            'length': 0,
            'total_record': 0,
            'records': []
        }
        records = []
        if result[0]:
            if result[0][0]:
                # YTI TODO: check lai giai phap luu service hoac luon luu vao bang, hoac join
                for rec in result[0][0]:
                    service_query = """ 
                        SELECT json_agg(t)
                                        FROM (
                               SELECT ser_ty.name, ser.type ,partner.name partner_name 
                                   FROM public.sharevan_routing_plan_day_service ser
                                       left join public.sharevan_service_type ser_ty on ser_ty.id = ser.service_id
                                       join public.res_partner partner on partner.id = assign_partner_id
                                       where routing_plan_day_id = %s )t
                    """
                    self.env.cr.execute(service_query,
                                        (rec['id'],))
                    service_result = self._cr.fetchall()
                    services = []
                    if service_result[0]:
                        if service_result[0][0]:
                            services = service_result[0][0]
                    rec['services'] = services
                    sos_query = """ 
                        SELECT json_agg(t)
                            FROM (
                    SELECT sos.id, sos.driver_id,
                        TO_CHAR(sos.create_date, 'YYYY-MM-DD HH24:MI:SS') create_date, sos.create_uid,
                        sos.vehicle_id,sos.routing_plan_day_id,sos.note,sos.latitude, sos.longitude,
                        warn_ty.name,warn_ty.code,
                        driver.name driver_name ,driver.phone, vehicle.name vehicle_name ,vehicle.license_plate
                    FROM public.sharevan_driver_sos sos
                        left join public.sharevan_warning_type warn_ty on warn_ty.id = sos.warning_type_id
                        left join fleet_driver driver on driver.id = sos.driver_id
                        left join fleet_vehicle vehicle on vehicle.id = sos.vehicle_id
                    where routing_plan_day_id = %s and warn_ty.status ='running')t
                    """
                    self.env.cr.execute(sos_query,
                                        (rec['id'],))
                    sos_result = self._cr.fetchall()
                    sos_ids = []
                    if sos_result[0]:
                        if sos_result[0][0]:
                            for sos in sos_result[0][0]:
                                warning_type = {
                                    'name': sos['name'],
                                    'code': sos['code'],
                                }
                                vehicle = {
                                    'name': sos['vehicle_name'],
                                    'license_plate': sos['license_plate'],
                                }
                                driver = {
                                    'name': sos['driver_name'],
                                    'phone': sos['phone'],
                                }
                                val = {
                                    'id': sos['id'],
                                    'driver_id': sos['driver_id'],
                                    'create_date': sos['create_date'],
                                    'create_uid': sos['create_uid'],
                                    'vehicle_id': sos['vehicle_id'],
                                    'routing_plan_day_id': sos['routing_plan_day_id'],
                                    'note': sos['note'],
                                    'latitude': sos['latitude'],
                                    'longitude': sos['longitude'],
                                    'warning_type': warning_type,
                                    'vehicle': vehicle,
                                    'driver': driver,
                                }
                                sos_ids.append(val)
                    rec['sos_ids'] = sos_ids
                    records.append(rec)
                jsonRe = {
                    'length': len(records),
                    'total_record': total_record,
                    'records': records
                }
        simplejson.dumps(jsonRe, indent=4, sort_keys=True, default=str)
        return jsonRe

    def get_driver_routing_plan_by_vehicle(self, vehicle_id, date_plan, type):
        records = []
        jsonRe = {
            'length': 0,
            'total_record': 0,
            'records': []
        }
        query = """
        SELECT json_agg(t)
                        FROM (
            SELECT plan.id,plan.partner_id,plan.vehicle_id,plan.driver_id, plan.routing_plan_day_code, plan.status, plan.type, plan.latitude, plan.longitude,
                    plan.address,TO_CHAR(plan.expected_from_time, 'YYYY-MM-DD HH24:MI:SS') expected_from_time,
                    TO_CHAR(plan.expected_to_time, 'YYYY-MM-DD HH24:MI:SS') expected_to_time,
                    plan.warehouse_name,plan.previous_id,plan.next_id,
                    plan.phone, COALESCE(plan.order_number,0) order_number,
                    STRING_AGG( COALESCE(plan.order_number,0)::text, ',') OVER(PARTITION BY plan.latitude, plan.longitude ) order_number_routing
                     ,us.login ,plan.so_type, 
                    COALESCE(plan.check_point,false) check_point,COALESCE(plan.arrived_check,false) arrived_check
                    ,plan.capacity_expected,plan.rating_customer,
                    plan.company_id, ins.name insurance_id,ins.name insurance_name,
                    plan.description, plan.type,plan.ship_type,plan.qr_gen_check,
                    TO_CHAR(plan.due_time, 'YYYY-MM-DD HH24:MI:SS') due_time, 
                    TO_CHAR(plan.ready_time, 'YYYY-MM-DD HH24:MI:SS') ready_time, 
                    TO_CHAR(plan.write_date, 'YYYY-MM-DD HH24:MI:SS') write_date ,
                    TO_CHAR(plan.date_plan, 'YYYY-MM-DD HH24:MI:SS')  date_plan ,
                    TO_CHAR(plan.confirm_time, 'YYYY-MM-DD HH24:MI:SS')  confirm_time,
                    TO_CHAR(plan.accept_time, 'YYYY-MM-DD HH24:MI:SS')  accept_time,
                    bill_routing.name bill_routing_name
                FROM sharevan_routing_plan_day plan
                    left join sharevan_insurance ins on ins.id= plan.insurance_id
                    left join res_users us on us.id = plan.write_uid
                    join sharevan_bill_routing bill_routing on bill_routing.id = plan.bill_routing_id
            WHERE plan.vehicle_id = %s and plan.date_plan = %s """
        if type == 1:
            query += """ and plan.status::integer in (0,1,2,3,4) """
        else:
            query += """ and plan.status::integer in (0,1,2) """

        query += """ order by plan.date_plan ASC , plan.order_number ASC )t
                            """
        self.env.cr.execute(query,
                            (vehicle_id, date_plan,))

        result = self._cr.fetchall()
        if result[0]:
            if result[0][0]:

                # YTI TODO: check lai giai phap luu service hoac luon luu vao bang, hoac join
                for rec in result[0][0]:
                    if http.request.env.user.channel_id.name != 'dlp':
                        rec['phone'] = ''
                    sos_query = """ 
                        SELECT json_agg(t)
                            FROM (
                    SELECT sos.id, sos.driver_id,
                        TO_CHAR(sos.create_date, 'YYYY-MM-DD HH24:MI:SS') create_date, sos.create_uid,
                        sos.vehicle_id,sos.routing_plan_day_id,sos.note,sos.latitude, sos.longitude,
                        warn_ty.name,warn_ty.code,
                        driver.name driver_name ,driver.phone, vehicle.name vehicle_name ,vehicle.license_plate
                    FROM public.sharevan_driver_sos sos
                        left join public.sharevan_warning_type warn_ty on warn_ty.id = sos.warning_type_id
                        left join fleet_driver driver on driver.id = sos.driver_id
                        left join fleet_vehicle vehicle on vehicle.id = sos.vehicle_id
                    where routing_plan_day_id = %s and warn_ty.status ='running')t
                    """
                    self.env.cr.execute(sos_query,
                                        (rec['id'],))
                    sos_result = self._cr.fetchall()
                    sos_ids = []
                    if sos_result[0]:
                        if sos_result[0][0]:
                            for sos in sos_result[0][0]:
                                warning_type = {
                                    'name': sos['name'],
                                    'code': sos['code'],
                                }
                                vehicle = {
                                    'name': sos['vehicle_name'],
                                    'license_plate': sos['license_plate'],
                                }
                                driver = {
                                    'name': sos['driver_name'],
                                    'phone': sos['phone'],
                                }
                                val = {
                                    'id': sos['id'],
                                    'driver_id': sos['driver_id'],
                                    'create_date': sos['create_date'],
                                    'create_uid': sos['create_uid'],
                                    'vehicle_id': sos['vehicle_id'],
                                    'routing_plan_day_id': sos['routing_plan_day_id'],
                                    'note': sos['note'],
                                    'latitude': sos['latitude'],
                                    'longitude': sos['longitude'],
                                    'warning_type': warning_type,
                                    'vehicle': vehicle,
                                    'driver': driver,
                                }
                                sos_ids.append(val)
                    rec['sos_ids'] = sos_ids
                    records.append(rec)
                jsonRe = {
                    'length': len(records),
                    'records': records
                }
        simplejson.dumps(jsonRe, indent=4, sort_keys=True, default=str)
        return jsonRe

    def get_vehicle_routing_distinct_vehicle(self, lst_vehicle_ids, date_plan):
        jsonRe = {
            'records': []
        }
        if len(lst_vehicle_ids) == 0:
            return jsonRe
        query = """
        SELECT json_agg(t)
                        FROM (
                        select distinct vehicle_id from sharevan_routing_plan_day plan where plan.status::integer in ( 0,1,2) and  vehicle_id in (%s) and date_plan = '%s' 
                         )t
                            """ % (','.join([str(elem) for elem in lst_vehicle_ids]), date_plan)
        self.env.cr.execute(query, ())
        result = self._cr.fetchall()
        jsonRe = {
            'records': result[0][0]
        }
        simplejson.dumps(jsonRe, indent=4, sort_keys=True, default=str)
        return jsonRe

    def get_routing_detail(self, routing_plan_day_code):
        if routing_plan_day_code is False or routing_plan_day_code == '':
            raise ValidationError('No input')
        query = """
            SELECT json_agg(t) FROM (
                select distinct  rpd.routing_plan_day_code code,
                    rpd.id,
                    rpd.status,
                    rpd.vehicle_id,
                    rpd.phone,
                    rpd.warehouse_name,
                    rpd.latitude,
                    rpd.longitude, rpd.toogle,
                     COALESCE(rpd.trouble_type,'0') trouble_type,
                    rpd.bill_lading_detail_code,
                    rpd.address,
                    COALESCE(rpd.qr_gen_check,false) qr_gen_check,
                    rpd.warehouse_id,
                    rpd.so_type,COALESCE(rpd.check_point,false) check_point,
                    COALESCE(rpd.arrived_check,false) arrived_check,
                    COALESCE(rpd.first_rating_customer,false) first_rating_customer,
                    rpd.bill_lading_detail_id,
                    TO_CHAR(rpd.expected_from_time, 'YYYY-MM-DD HH24:MI:SS')  expected_from_time,
                    TO_CHAR(rpd.expected_to_time, 'YYYY-MM-DD HH24:MI:SS') expected_to_time,
                    TO_CHAR(rpd.date_plan, 'YYYY-MM-DD HH24:MI:SS') date_plan,
                    ins.name insurance_name,
                    ins.id insurance_id,
                    rpd.ship_type,
                    v.id vehicle_id,
                    v.name vehicle_name,
                    v.license_plate,
                    rpd.routing_plan_day_code,
                    driver.id driver_id,
                    driver.name driver_name,
                    driver.driver_code,
                    driver.phone driver_phone,
                    ir.uri_path driver_image,
					rpd.warehouse_name,rpd.previous_id,rpd.next_id,
					rpd.phone, rpd.order_number,
					rpd.order_number,rpd.capacity_expected,
					rpd.company_id,rpd.bill_routing_id,
					company.name company_name,
					company.id company_id,
					part.name booked_employee,
					rpd.description, rpd.type,
                    TO_CHAR(rpd.confirm_time, 'YYYY-MM-DD HH24:MI:SS')  confirm_time,
                    TO_CHAR(rpd.accept_time, 'YYYY-MM-DD HH24:MI:SS')  accept_time,
                    TO_CHAR(rpd.write_date, 'YYYY-MM-DD HH24:MI:SS')  write_date,
                    rpd.bill_lading_detail_id,
                    COALESCE(rpd.rating_customer,false) rating_customer,rpd.from_routing_plan_day_id,
                    stock.name stock_man_name,rpd.qr_so  ,bill_routing.name bill_routing_name
                from sharevan_routing_plan_day rpd
                    join public.sharevan_bill_package_routing_plan plan 
                                    on plan.routing_plan_day_id = rpd.id
                    join sharevan_bill_routing bill_routing  on bill_routing.id = rpd.bill_routing_id
                    left join fleet_vehicle v on v.id = rpd.vehicle_id
                    left join fleet_driver driver on driver.id = rpd.driver_id
                    left join sharevan_insurance ins  on ins.id = rpd.insurance_id
                    left join ir_attachment ir on ir.res_id = driver.id and ir.res_model =  'fleet.driver' and ir.name='image_1920'
					left join res_partner part on part.id= rpd.partner_id
					left join res_partner stock on stock.id= rpd.stock_man_id
					left join res_company company on company.id = rpd.company_id
                where 1 = 1 and ( LOWER(rpd.routing_plan_day_code) 
        """
        query += """  like LOWER('%%%s%%')  """ % (routing_plan_day_code,)
        query += """ or LOWER(plan.qr_char) like LOWER('%%%s%%')  """ % (routing_plan_day_code,)
        query += """ or LOWER(rpd.qr_so) like LOWER('%%%s%%')  """ % (routing_plan_day_code,)
        query += """ ) )t """
        self.env.cr.execute(query, ())
        result = self._cr.fetchall()
        if result[0]:
            if result[0][0]:
                jsonRe = []
                jsonListUrl = []
                BaseMethod.check_role_access(http.request.env.user, 'sharevan.routing.plan.day', result[0][0][0]['id'])
                getUrl_query = """
                    SELECT json_agg(t) FROM (
                        select irc.uri_path from ir_attachment irc
                            join public.ir_attachment_sharevan_routing_plan_day_rel pi on pi.ir_attachment_id = irc.id
                            join sharevan_routing_plan_day srpd on pi.sharevan_routing_plan_day_id = srpd.id 
                                and srpd.routing_plan_day_code= %s ) t """
                self.env.cr.execute(getUrl_query, (routing_plan_day_code,))
                get_list_images_or_attachment_url = self._cr.fetchall()
                if get_list_images_or_attachment_url:
                    if get_list_images_or_attachment_url[0][0]:
                        for rec in get_list_images_or_attachment_url[0][0]:
                            jsonListUrl.append(rec['uri_path'])
                if result[0][0][0]['trouble_type'] == '3' and result[0][0][0]['toogle'] == True:
                    getUrl_query = """
                        select irc.uri_path from ir_attachment irc
                            join public.ir_attachment_sharevan_routing_plan_day_rel pi on pi.ir_attachment_id = irc.id
                            join sharevan_routing_plan_day srpd on pi.sharevan_routing_plan_day_id = srpd.id 
                                and srpd.id= %s  """
                    self.env.cr.execute(getUrl_query, (result[0][0][0]['from_routing_plan_day_id'],))
                    get_list_images_or_attachment_url = self._cr.dictfetchall()
                    if get_list_images_or_attachment_url:
                        for rec in get_list_images_or_attachment_url:
                            jsonListUrl.append(rec['uri_path'])
                if result[0][0][0]['status'] == '3':
                    url_bill_routing = """
                        select irc.uri_path from ir_attachment irc
                            join public.ir_attachment_sharevan_bill_routing_rel pi on pi.ir_attachment_id = irc.id
                            join sharevan_routing_plan_day srpd on pi.sharevan_bill_routing_id = srpd.bill_routing_id 
                                and srpd.routing_plan_day_code= %s
                    """
                    self.env.cr.execute(url_bill_routing, (routing_plan_day_code,))
                    get_list_images_of_routing = self._cr.dictfetchall()
                    if get_list_images_of_routing:
                        for rec in get_list_images_of_routing:
                            jsonListUrl.append(rec['uri_path'])
                # qr_code = ''
                # get_qr_query = """
                #     SELECT json_agg(t)
                #         FROM (SELECT uri_path
                #             FROM public.ir_attachment
                #     where res_id= %s and res_field ='qr_code' and res_model='sharevan.routing.plan.day' ) t """
                # self.env.cr.execute(get_qr_query, (result[0][0][0]['id'],))
                # result_qr = self._cr.fetchall()
                # if result_qr:
                #     if result_qr[0][0]:
                #         for rec in result_qr[0][0]:
                #             qr_code = rec['uri_path']
                service_query = """ 
                    SELECT json_agg(t)
                            FROM (
                    SELECT ser_ty.name, ser.type ,partner.name partner_name 
                       FROM public.sharevan_routing_plan_day_service ser
                           left join public.sharevan_service_type ser_ty on ser_ty.id = ser.service_id
                           join public.res_partner partner on partner.id = assign_partner_id
                           where routing_plan_day_id = %s )t
                                    """
                self.env.cr.execute(service_query,
                                    (result[0][0][0]['id'],))
                service_result = self._cr.fetchall()
                services = []
                if service_result[0]:
                    if service_result[0][0]:
                        services = service_result[0][0]

                sos_query = """ 
                    SELECT json_agg(t)
                        FROM (
                    SELECT sos.id
                    FROM public.sharevan_driver_sos sos
                        where routing_plan_day_id = %s and sos.status ='running')t
                                    """
                self.env.cr.execute(sos_query,
                                    (result[0][0][0]['id'],))
                sos_result = self._cr.fetchall()
                sos_ids = False
                if sos_result[0]:
                    if sos_result[0][0]:
                        sos_ids = True
                rating = {}
                rating_query = """ 
                   SELECT json_agg(t)
                        FROM ( SELECT num_rating ,note
	                FROM public.sharevan_rating where rating_place_id  = %s and type = 'ROUTING' )t
                                    """
                self.env.cr.execute(rating_query,
                                    (result[0][0][0]['id'],))
                rating_result = self._cr.fetchall()
                if rating_result[0]:
                    if rating_result[0][0]:
                        rating['num_rating'] = rating_result[0][0][0]['num_rating']
                        rating['note'] = rating_result[0][0][0]['note']
                        badge_query = """ 
                            SELECT json_agg(t)
                                FROM (
                           SELECT rating.id, rating.note, rating.create_uid,badges.name, irr.uri_path image,
                                 TO_CHAR(rating.create_date, 'YYYY-MM-DD HH24:MI:SS') create_date
                           FROM public.sharevan_rating  rating
								left join sharevan_rating_sharevan_rating_badges_rel rating_badges_rel on rating.id = rating_badges_rel.sharevan_rating_id
                                left join sharevan_rating_badges badges on badges.id = rating_badges_rel.sharevan_rating_badges_id
                                left join ir_attachment irr on irr.res_id = badges.id and res_model='sharevan.rating.badges'
                           Where rating.rating_place_id = %s )t
                                            """
                        self.env.cr.execute(badge_query,
                                            (result[0][0][0]['id'],))
                        badge_result = self._cr.fetchall()
                        rating_ids = []
                        if badge_result[0]:
                            if badge_result[0][0]:
                                rating_ids = badge_result[0][0]
                        rating['badges_routings'] = rating_ids
                customer_rating_query = """
                    select rating.id,rating.rating_place_id , rating.driver_id, rating.employee_id, 
                        rating.note,rating.rating, partner.name , partner.phone, ir.uri_path image
                    from sharevan_rating_customer rating
                        JOIN res_partner partner on partner.id = rating.employee_id
                        JOIN fleet_driver driver on driver.id = rating.driver_id
                        LEFT JOIN ir_attachment ir on ir.res_id = partner.id and ir.res_model ='res.partner' 
                            and ir.name='image_256'
                    where rating.rating_place_id = %s and rating.type ='ROUTING'
                            and driver.user_id = %s;
                """
                self.env.cr.execute(customer_rating_query, (result[0][0][0]['id'], http.request.env.uid,))
                customer_rating = self._cr.dictfetchall()
                rating_customer = {}
                if customer_rating:
                    rating_customer = customer_rating[0]
                    customer_badges = """
                        select badges.name 
                            from sharevan_rating_badges badges
                        join sharevan_rating_badges_sharevan_rating_customer_rel rel 
                            on rel.sharevan_rating_badges_id =badges.id
                        join sharevan_rating_customer rating_customer 
                            on rating_customer.id = rel.sharevan_rating_customer_id
                        where rating_customer.id =%s
                    """
                    self.env.cr.execute(customer_badges, (customer_rating[0]['id'],))
                    badges_customer = self._cr.dictfetchall()
                    if badges_customer:
                        lst_badge = []
                        for badge in badges_customer:
                            lst_badge.append(badge['name'])
                        rating_customer['list_badge_names'] = lst_badge
                # rec['services'] = services
                if result[0][0][0]['type'] == WarehouseType.Export.value:
                    self.env.cr.execute("""
                        SELECT json_agg(t)
                            FROM (SELECT 
                                export_plan.routing_plan_day_code,export_plan.warehouse_name,export_plan.address,export_plan.phone,export_plan.latitude,
                                export_plan.longitude, rb_export_now.id, rb_export_now.quantity_export,rb_export_now.length,
                                rb_export_now.width,  rb_export_now.height , rb_export_now.total_weight, rb_export_now.capacity,
                                pt.name product_type_name,pt.id product_type_id, rb_export_now.note, rb_export_now.item_name ,rb_export_now.key_map ,
                                plan.qr_char ,rb_export_now.bill_package_id
                            FROM  sharevan_routing_plan_day rpd_now
                                join public.sharevan_bill_package_routing_export rb_export_now 
                                    on rb_export_now.routing_plan_day_id = rpd_now.id
                                join sharevan_routing_plan_day export_plan 
									on export_plan.bill_routing_id = rpd_now.bill_routing_id 
									and export_plan.type ='0' 
                                join public.sharevan_bill_package_routing_plan plan 
                                    on plan.routing_plan_day_id = export_plan.id
									and plan.product_type_id = rb_export_now.product_type_id
									and plan.key_map = rb_export_now.key_map
                                left join public.sharevan_product_type pt on pt.id =  rb_export_now.product_type_id
                            where  rpd_now.routing_plan_day_code =  %s and export_plan.warehouse_id is not null ) t """
                                        , (routing_plan_day_code,))
                    result_export_warehouse_package = self._cr.fetchall()
                    list_export = []
                    result_length = len(result_export_warehouse_package)
                    if result_length > 0:
                        if result_export_warehouse_package[0][0]:
                            list_export = result_export_warehouse_package[0][0]
                    warehouse_return = {}
                    if result[0][0][0]['trouble_type'] == '3':
                        from_routing_plan_day_id = result[0][0][0]['from_routing_plan_day_id']
                        return_query = """
                        select 
                            rpd.routing_plan_day_code,
                            rpd.id,
                            rpd.status,
                            rpd.vehicle_id,
                            rpd.phone,
                            rpd.warehouse_name,
                            rpd.latitude,
                            rpd.longitude,
                             COALESCE(rpd.trouble_type,'0') trouble_type,
                            rpd.bill_lading_detail_code,
                            rpd.address,
                            COALESCE(rpd.qr_gen_check,false) qr_gen_check,
                            rpd.warehouse_id,
                            rpd.so_type,COALESCE(rpd.check_point,false) check_point,
                            COALESCE(rpd.arrived_check,false) arrived_check,
                            COALESCE(rpd.first_rating_customer,false) first_rating_customer,
                            rpd.bill_lading_detail_id,
                            TO_CHAR(rpd.expected_from_time, 'YYYY-MM-DD HH24:MI:SS')  expected_from_time,
                            TO_CHAR(rpd.expected_to_time, 'YYYY-MM-DD HH24:MI:SS') expected_to_time,
                            TO_CHAR(rpd.date_plan, 'YYYY-MM-DD HH24:MI:SS') date_plan
                             from sharevan_routing_plan_day rpd where rpd.id = %s 
                                """
                        self.env.cr.execute(return_query, (from_routing_plan_day_id,))
                        check = self._cr.dictfetchall()
                        if check:
                            warehouse_return = check[0]
                    vehicle = {
                        'id': result[0][0][0]['vehicle_id'],
                        'license_plate': result[0][0][0]['license_plate'],
                        'name': result[0][0][0]['vehicle_name']
                    }
                    driver = {
                        'id': result[0][0][0]['driver_id'],
                        'name': result[0][0][0]['driver_name'],
                        'driver_code': result[0][0][0]['driver_code'],
                        'phone': result[0][0][0]['driver_phone'],
                        'image_1920': result[0][0][0]['driver_image']
                    }
                    content = {
                        'id': result[0][0][0]['id'],
                        'date_plan': result[0][0][0]['date_plan'],
                        'bill_lading_detail_code': result[0][0][0]['bill_lading_detail_code'],
                        'expected_from_time': result[0][0][0]['expected_from_time'],
                        'expected_to_time': result[0][0][0]['expected_to_time'],
                        'confirm_time': result[0][0][0]['confirm_time'],
                        'bill_routing_name': result[0][0][0]['bill_routing_name'],
                        'accept_time': result[0][0][0]['accept_time'],
                        'status': result[0][0][0]['status'],
                        'toogle': result[0][0][0]['toogle'],
                        'warehouse_return': warehouse_return,
                        'vehicle': vehicle,
                        'driver': driver,
                        'order_number': result[0][0][0]['order_number'],
                        'bill_routing_id': result[0][0][0]['bill_routing_id'],
                        'latitude': result[0][0][0]['latitude'],
                        'longitude': result[0][0][0]['longitude'],
                        'address': result[0][0][0]['address'],
                        'trouble_type': result[0][0][0]['trouble_type'],
                        'type': result[0][0][0]['type'],
                        'bill_lading_detail_id': result[0][0][0]['bill_lading_detail_id'],
                        'routing_plan_day_code': result[0][0][0]['routing_plan_day_code'],
                        'phone': result[0][0][0]['phone'],
                        'warehouse_name': result[0][0][0]['warehouse_name'],
                        'company_name': result[0][0][0]['company_name'],
                        'booked_employee': result[0][0][0]['booked_employee'],
                        'stock_man_name': result[0][0][0]['stock_man_name'],
                        'description': result[0][0][0]['description'],
                        'insurance_name': result[0][0][0]['insurance_name'],
                        'insurance_id': result[0][0][0]['insurance_id'],
                        'company_id': result[0][0][0]['company_id'],
                        'rating_customer': result[0][0][0]['rating_customer'],
                        'rating_customer_id': rating_customer,
                        'qr_so': result[0][0][0]['qr_so'],
                        'qr_gen_check': result[0][0][0]['qr_gen_check'],
                        'image_urls': jsonListUrl,
                        'list_bill_package': list_export,
                        'services': services,
                        # 'qr_code': qr_code,
                        'sos_ids': sos_ids,
                        'so_type': result[0][0][0]['so_type'],
                        'check_point': result[0][0][0]['check_point'],
                        'arrived_check': result[0][0][0]['arrived_check'],
                        'write_date': result[0][0][0]['write_date'],
                        'first_rating_customer': result[0][0][0]['first_rating_customer'],
                        'rating_drivers': rating
                    }
                    jsonRe.append(content)
                else:
                    self.env.cr.execute("""
                        SELECT json_agg(t)
                            FROM (SELECT  rb_import_now.id, rb_import_now.quantity_import,rb_import_now.length,
                                rb_import_now.width,  rb_import_now.height , rb_import_now.total_weight,
                                rb_import_now.capacity,rb_import_now.key_map ,
                                pt.name product_type_name,pt.id product_type_id , rb_import_now.note, rb_import_now.item_name ,
                                rb_import_now.routing_plan_day_id ,plan.qr_char,rb_import_now.bill_package_id
                            FROM   public.sharevan_bill_package_routing_import rb_import_now
                                join public.sharevan_bill_package_routing_plan plan 
                                    on plan.id = rb_import_now.routing_package_plan
                                left join public.sharevan_product_type pt on pt.id =  rb_import_now.product_type_id
                            where  rb_import_now.routing_plan_day_id =  %s) t  """
                                        , (result[0][0][0]['id'],))
                    result_export_warehouse_package = self._cr.fetchall()
                    bill_package_import = []
                    result_length = len(result_export_warehouse_package)
                    if result_length > 0:
                        if result_export_warehouse_package[0][0]:
                            bill_package_import = result_export_warehouse_package[0][0]
                    vehicle = {
                        'id': result[0][0][0]['vehicle_id'],
                        'license_plate': result[0][0][0]['license_plate'],
                        'name': result[0][0][0]['vehicle_name']
                    }
                    driver = {
                        'id': result[0][0][0]['driver_id'],
                        'name': result[0][0][0]['driver_name'],
                        'driver_code': result[0][0][0]['driver_code'],
                        'phone': result[0][0][0]['driver_phone'],
                        'image_1920': result[0][0][0]['driver_image']
                    }
                    content = {
                        'id': result[0][0][0]['id'],
                        'date_plan': result[0][0][0]['date_plan'],
                        'bill_lading_detail_code': result[0][0][0]['bill_lading_detail_code'],
                        'expected_from_time': result[0][0][0]['expected_from_time'],
                        'expected_to_time': result[0][0][0]['expected_to_time'],
                        'confirm_time': result[0][0][0]['confirm_time'],
                        'accept_time': result[0][0][0]['accept_time'],
                        'status': result[0][0][0]['status'],
                        'toogle': result[0][0][0]['toogle'],
                        'vehicle': vehicle,
                        'driver': driver,
                        'order_number': result[0][0][0]['order_number'],
                        'trouble_type': result[0][0][0]['trouble_type'],
                        'bill_routing_name': result[0][0][0]['bill_routing_name'],
                        'latitude': result[0][0][0]['latitude'],
                        'longitude': result[0][0][0]['longitude'],
                        'bill_lading_detail_id': result[0][0][0]['bill_lading_detail_id'],
                        'address': result[0][0][0]['address'],
                        'routing_plan_day_code': result[0][0][0]['routing_plan_day_code'],
                        'phone': result[0][0][0]['phone'],
                        'type': result[0][0][0]['type'],
                        'rating_customer': result[0][0][0]['rating_customer'],
                        'warehouse_name': result[0][0][0]['warehouse_name'],
                        'company_name': result[0][0][0]['company_name'],
                        'company_id': result[0][0][0]['company_id'],
                        'bill_routing_id': result[0][0][0]['bill_routing_id'],
                        'qr_so': result[0][0][0]['qr_so'],
                        'qr_gen_check': result[0][0][0]['qr_gen_check'],
                        'rating_customer_id': rating_customer,
                        'booked_employee': result[0][0][0]['booked_employee'],
                        'stock_man_name': result[0][0][0]['stock_man_name'],
                        'description': result[0][0][0]['description'],
                        'image_urls': jsonListUrl,
                        'list_bill_package': bill_package_import,
                        'services': services,
                        # 'qr_code': qr_code,
                        'sos_ids': sos_ids,
                        'so_type': result[0][0][0]['so_type'],
                        'check_point': result[0][0][0]['check_point'],
                        'write_date': result[0][0][0]['write_date'],
                        'first_rating_customer': result[0][0][0]['first_rating_customer'],
                        'arrived_check': result[0][0][0]['arrived_check'],
                        'rating_drivers': rating
                    }
                    jsonRe.append(content)
                return {
                    'records': jsonRe
                }
            else:
                return {
                    'length': 0,
                    'total_record': 0,
                    'records': []
                }
        else:
            return {
                'length': 0,
                'total_record': 0,
                'records': []
            }

    def get_sos_lst(self, routing_plan_day_id):
        if routing_plan_day_id:
            sos_query = """ 
                SELECT json_agg(t)
                    FROM (
                SELECT sos.id, sos.driver_id,
                    TO_CHAR(sos.create_date, 'YYYY-MM-DD HH24:MI:SS') create_date, sos.create_uid,
                    sos.vehicle_id,sos.routing_plan_day_id,sos.note,sos.latitude, sos.longitude,
                    warn_ty.name,warn_ty.code,
                    driver.name driver_name ,driver.phone, vehicle.name vehicle_name ,vehicle.license_plate
                FROM public.sharevan_driver_sos sos
                    left join public.sharevan_warning_type warn_ty on warn_ty.id = sos.warning_type_id
                    left join fleet_driver driver on driver.id = sos.driver_id
                    left join fleet_vehicle vehicle on vehicle.id = sos.vehicle_id
                where routing_plan_day_id = %s and warn_ty.status ='running')t
                                                """
            self.env.cr.execute(sos_query,
                                (routing_plan_day_id,))
            sos_result = self._cr.fetchall()
            sos_ids = []
            if sos_result[0]:
                if sos_result[0][0]:
                    for sos in sos_result[0][0]:
                        warning_type = {
                            'name': sos['name'],
                            'code': sos['code'],
                        }
                        vehicle = {
                            'name': sos['vehicle_name'],
                            'license_plate': sos['license_plate'],
                        }
                        driver = {
                            'name': sos['driver_name'],
                            'phone': sos['phone'],
                        }
                        image_query = """
                        SELECT irr.uri_path FROM public.ir_attachment irr
                            join ir_attachment_sharevan_driver_sos_rel rel on irr.id= rel.ir_attachment_id
                            join sharevan_driver_sos sos on sos.id = rel.sharevan_driver_sos_id 
                        where sos.routing_plan_day_id = %s and sos.id = %s """
                        self.env.cr.execute(image_query,
                                            (routing_plan_day_id, sos['id'],))
                        image_result = self._cr.dictfetchall()
                        images = []
                        for image in image_result:
                            images.append(image['uri_path'])
                        val = {
                            'id': sos['id'],
                            'driver_id': sos['driver_id'],
                            'create_date': sos['create_date'],
                            'create_uid': sos['create_uid'],
                            'vehicle_id': sos['vehicle_id'],
                            'routing_plan_day_id': sos['routing_plan_day_id'],
                            'note': sos['note'],
                            'latitude': sos['latitude'],
                            'longitude': sos['longitude'],
                            'warning_type': warning_type,
                            'vehicle': vehicle,
                            'driver': driver,
                            'attach_image': images
                        }
                        sos_ids.append(val)
            return {
                'records': sos_ids
            }
        else:
            raise ValidationError('Routing plan day id not found')

    def accept_warehouse_place(self, routing_plan_day_id):
        if len(routing_plan_day_id) == 0:
            raise ValidationError('Routing plan day list is null')
        query = """
            SELECT rpd.id,rpd.type, rpd.warehouse_id, rpd.date_plan ,rpd.driver_id ,rpd.status ,rpd.company_id,
                rpd.latitude,rpd.longitude, rpd.routing_plan_day_code,rpd.arrived_check,
                veh.latitude vehicle_latitude,veh.longitude vehicle_longitude
                FROM public.sharevan_routing_plan_day rpd
            JOIN fleet_vehicle veh on veh.id = rpd.vehicle_id
            JOIN fleet_driver driver on driver.id = rpd.driver_id 
                WHERE driver.user_id =%s and rpd.id ::integer in (
            """
        for id in routing_plan_day_id:
            query += str(id) + ","
        query = query[:-1]
        query += ")"
        self._cr.execute(query, (http.request.env.uid,))
        record = self._cr.dictfetchall()
        if record and not record[0]['arrived_check']:
            check = False
            distance_allow = http.request.env['ir.config_parameter'].sudo().get_param(
                'distance.mobile.check.point.key')
            for rec in record:
                # distance =
                # FileApi.get_distance(record[0]['latitude'], record[0]['longitude'],
                #                             record[0]['vehicle_latitude'],
                #                             record[0]['vehicle_longitude'], False)
                coords_1 = (rec['latitude'], rec['longitude'])
                coords_2 = (rec['vehicle_latitude'], rec['vehicle_longitude'])
                distance = geopy.distance.distance(coords_1, coords_2).m
                if int(distance) > int(distance_allow):
                    return 500

                time_now = datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")
                check = http.request.env[RoutingPlanDay._name]. \
                    browse(rec['id']).write(
                    {'arrived_check': True, 'driver_arrived_time': time_now})
            if check:
                query = """
                    SELECT res.id  FROM public.res_users res where res.company_id = %s and active = true
                """
                http.request.env['res.users']._cr.execute(query, (record[0]['company_id'],))
                ids = http.request.env['res.users']._cr.dictfetchall()
                if ids:
                    list_id = []
                    for id in ids:
                        list_id.append(id['id'])
                    title = 'Driver has arrived warehouse already!'
                    body = 'Driver has arrived warehouse already! Please check order! ' \
                           + record[0]['routing_plan_day_code']
                    item_id = record[0]['routing_plan_day_code']

                    try:
                        val = {
                            'user_id': list_id,
                            'title': title,
                            'content': body,
                            'click_action': ClickActionType.routing_plan_day_customer.value,
                            'message_type': MessageType.success.value,
                            'type': NotificationType.RoutingMessage.value,
                            'object_status': RoutingDetailStatus.Driver_confirm.value,
                            'item_id': item_id,
                        }
                        http.request.env['sharevan.notification'].create(val)
                        return 200
                    except:
                        logger.warn(
                            "Accept arrived Successful! But can not send message",
                            RoutingPlanDay._name, item_id,
                            exc_info=True)
                        return 200
                else:
                    logger.warn(
                        "Employee fcm token not found!",
                        RoutingPlanDay._name, routing_plan_day_id,
                        exc_info=True)
                    return 500
            else:
                logger.warn(
                    "Update routing plan day fail.Notification employee fail!",
                    RoutingPlanDay._name, routing_plan_day_id,
                    exc_info=True)
                return 500
        else:
            logger.warn(
                "You have accepted at place already!",
                RoutingPlanDay._name, routing_plan_day_id,
                exc_info=True)
            return 500

    def update_rating_customer_check(self, routing_plan_day_id):
        query = """
            select driver.user_id 
                from sharevan_routing_plan_day plan 
            join fleet_driver driver on plan.driver_id = driver.id
                where driver.user_id = %s   and plan.id = %s
        """
        self._cr.execute(query, (http.request.env.uid, routing_plan_day_id,))
        record = self._cr.dictfetchall()
        if record:
            routing = self.env['sharevan.routing.plan.day'].search([('id', '=', routing_plan_day_id)])
            if routing:
                routing.write({'first_rating_customer': True})
                return routing['id']
            else:
                raise ValidationError('Routing plan day not found')
        else:
            raise ValidationError('You are not allowed on this routing plan day')

    def accept_package(self, routingPlan, files):
        print(routingPlan)
        routingPlan = json.loads(routingPlan)
        BaseMethod.check_role_access(http.request.env.user, 'sharevan.routing.plan.day', routingPlan['id'])
        lst_image = []
        check_query = """
            select export_routing.status,export_routing.id from sharevan_routing_plan_day routing
                left join sharevan_bill_lading_detail detail on detail.id = routing.bill_lading_detail_id
                left join sharevan_routing_plan_day export_routing 
                    on export_routing.bill_routing_id = routing.bill_routing_id
            where export_routing.type = '0' and export_routing.from_routing_plan_day_id is null
                and routing.id = %s;
        """
        self._cr.execute(check_query, (routingPlan['id'],))
        check_record = self._cr.dictfetchall()
        if not check_record or check_record[0]['status'] == '0' and check_record[0]['id'] != routingPlan['id']:
            raise ValidationError('Accept routing plan fail because you have not pick up package at export warehouse')
        query = """
            SELECT json_agg(t) FROM (
                SELECT rpd.id,rpd.type, rpd.warehouse_id, rpd.date_plan ,rpd.driver_id ,rpd.status ,rpd.company_id,
                    rpd.latitude,rpd.longitude,rpd.ship_type,rpd.depot_id,rpd.total_volume,rpd.type,rpd.bill_routing_id,
                    veh.latitude vehicle_latitude,veh.longitude vehicle_longitude,rpd.capacity_expected,rpd.vehicle_id
                FROM public.sharevan_routing_plan_day rpd
                    JOIN fleet_vehicle veh on veh.id = rpd.vehicle_id 
                WHERE rpd.id = %s)t
                        """
        self._cr.execute(query, (routingPlan['id'],))
        record = self._cr.fetchall()
        if record[0]:
            if record[0][0]:
                # check = BillRouting.check_routing_update(self, record[0][0]['driver_id'], record[0][0]['id'])
                # if check == False:
                #     raise ValidationError('You have not finish last routing! Please finish or cancel it!')
                if 3 > int(routingPlan['status']) > -1 \
                        and int(routingPlan['status']) - int(record[0][0][0]['status']) == 1:

                    # distance = FileApi.get_distance(record[0][0][0]['latitude'], record[0][0][0]['longitude'],
                    #                                 record[0][0][0]['vehicle_latitude'],
                    #                                 record[0][0][0]['vehicle_longitude'], False)
                    # distance_allow = http.request.env['ir.config_parameter'].sudo().get_param(
                    #     'distance.mobile.check.point.key')
                    coords_1 = (record[0][0][0]['latitude'], record[0][0][0]['longitude'])
                    coords_2 = (record[0][0][0]['vehicle_latitude'], record[0][0][0]['vehicle_longitude'])
                    distance = geopy.distance.distance(coords_1, coords_2).m
                    distance_allow = http.request.env['ir.config_parameter'].sudo().get_param(
                        'distance.mobile.check.point.key')
                    if int(distance) > int(distance_allow):
                        return http.Response('Employee too far from warehouse!')
                    for file in files:
                        if file.filename:
                            val = {
                                'res_model': 'sharevan.routing.plan.day',
                                'mimetype': file.mimetype,
                                'name': file.filename,
                                'res_id': routingPlan['id'],
                                # 'company_id': routingPlan['company_id'],
                                'type': 'binary',
                                'datas': base64.b64encode(file.read())
                            }
                            rec = http.request.env[IrAttachment._name].create(val)
                            image = {
                                'store_fname': rec['store_fname']
                            }
                            lst_image.append(image)
                            http.request.cr.execute(INSERT_QUERY, (routingPlan['id'], rec['id'],))

                    routing_plan_id = routingPlan['id']
                    routing_plan = None
                    if routingPlan['status'] == RoutingDetailStatus.Driver_confirm.value and routingPlan[
                        'so_type'] == False:
                        if record[0][0][0]['type'] == '0':
                            routing_plan = http.request.env[RoutingPlanDay._name]. \
                                browse(routing_plan_id).write(
                                {'status': RoutingDetailStatus.Done.value, 'description': routingPlan['description'],
                                 'confirm_time': datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S"),
                                 'accept_time': datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")})
                        else:
                            routing_plan = http.request.env[RoutingPlanDay._name]. \
                                browse(routing_plan_id).write(
                                {'status': RoutingDetailStatus.Driver_confirm.value,
                                 'description': routingPlan['description'],
                                 'confirm_time': datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")})
                    elif routingPlan['status'] == RoutingDetailStatus.Done.value and routingPlan['so_type'] == False:
                        query = """
                            SELECT partner.id
                                FROM public.res_partner partner
                            where user_id = %s
                        """
                        self._cr.execute(query, (http.request.env.uid,))
                        stockman = self._cr.dictfetchall()

                        # update routing plan with stock man id
                        routing_plan = http.request.env[RoutingPlanDay._name]. \
                            browse(routing_plan_id).write(
                            {'status': routingPlan['status'], 'description': routingPlan['description'],
                             'stock_man_id': stockman[0]['id'],
                             'accept_time': datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")})
                    BillRouting.check_routing_update(self, record[0][0][0]['bill_routing_id'])
                    # update depot capacity
                    if record[0][0][0]['ship_type'] == '0' and record[0][0][0]['type'] == '1' and routingPlan[
                        'status'] == '2':
                        next_routing_plan_day = http.request.env['sharevan.routing.plan.day'].search(
                            [('from_routing_plan_day_id', '=', routing_plan_id)])
                        if next_routing_plan_day:
                            next_routing_plan_day.write({'status': '0', 'packaged_cargo': '1'})
                            depot_vals = {
                                "routing_plan_day_id": routing_plan_id,
                                "depot_id": record[0][0][0]['depot_id'],
                                "total_volume": record[0][0][0]['total_volume'],
                                "type": 0,
                                "force_save": False
                            }
                            http.request.env[DepotGoods._name].import_goods(depot_vals)
                        else:
                            logger.debug(
                                "Next routing plan day for this routing not found! There is a trouble in create routing in depot in ship type: " +
                                record[0][0][0]['ship_type'],
                                RoutingPlanDay._name, routingPlan['routing_plan_day_code'],
                                exc_info=True)
                    else:
                        if not record[0][0][0]['warehouse_id'] and record[0][0][0]['type'] == '0':
                            depot_vals = {
                                "routing_plan_day_id": routing_plan_id,
                                "depot_id": record[0][0][0]['depot_id'],
                                "total_volume": record[0][0][0]['total_volume'],
                                "type": 1,
                                "force_save": False
                            }
                            http.request.env[DepotGoods._name].export_goods(depot_vals)
                    # đơn so Mstore
                    if routingPlan['status'] == RoutingDetailStatus.Driver_confirm.value and routingPlan['so_type'] and \
                            routingPlan['so_type'] == True:

                        # update nhận hàng luôn k cần khách hàng confirm
                        routing_plan = http.request.env['sharevan.routing.plan.day']. \
                            browse(routing_plan_id).write(
                            {'status': RoutingDetailStatus.Done.value, 'description': routingPlan['description'],
                             'accept_time': datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S"),
                             'confirm_time': datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")})
                        BillRouting.check_routing_update(self, record[0][0][0]['bill_routing_id'])
                        # update depot capacity nếu là đơn long haul
                        if record[0][0][0]['ship_type'] == '1' and record[0][0][0]['type'] == '1':
                            next_routing_plan_day = http.request.env['sharevan.routing.plan.day'].search(
                                [('from_routing_plan_id', '=', routing_plan_id)])
                            if next_routing_plan_day:
                                next_routing_plan_day.write({'status': '0', 'packaged_cargo': '1'})
                                depot_vals = {
                                    "routing_plan_day_id": routing_plan_id,
                                    "depot_id": record[0][0][0]['depot_id'],
                                    "total_volume": record[0][0][0]['total_volume'],
                                    "type": 0,
                                    "force_save": False
                                }
                                http.request.env[DepotGoods._name].import_goods(depot_vals)
                            else:
                                logger.warn(
                                    "Next routing plan day for this routing not found! There is a trouble in create routing in depot in ship type: " +
                                    record[0][0][0]['ship_type'],
                                    RoutingPlanDay._name, routingPlan['routing_plan_day_code'],
                                    exc_info=True)

                        else:
                            if not record[0][0][0]['warehouse_id'] and record[0][0][0]['type'] == '0':
                                depot_vals = {
                                    "routing_plan_day_id": routing_plan_id,
                                    "depot_id": record[0][0][0]['depot_id'],
                                    "total_volume": record[0][0][0]['total_volume'],
                                    "type": 1,
                                    "force_save": False
                                }
                                http.request.env[DepotGoods._name].export_goods(depot_vals)
                    vehicle = http.request.env[FleetVehicle._name].search(
                        [('id', '=', record[0][0][0]['vehicle_id'])])
                    if vehicle:
                        available_capacity = float(vehicle['available_capacity'])
                        available_capacity = available_capacity - float(record[0][0][0]['capacity_expected'])
                        vehicle.write({'available_capacity': available_capacity})
                    if routing_plan:
                        type = record[0][0][0]['type']
                        id = record[0][0][0]['warehouse_id']
                        date_plan = record[0][0][0]['date_plan']
                        ids = False
                        driver_id = record[0][0][0]['driver_id']
                        if routingPlan['status'] == '1':
                            if record[0][0][0]['warehouse_id']:
                                query = """
                                SELECT json_agg(t) from(
                                    SELECT res.id  FROM public.res_users res where res.company_id = %s)t
                                        """
                                http.request.env['res.users']._cr.execute(query, (record[0][0][0]['company_id'],))
                                ids = http.request.env['res.users']._cr.fetchall()
                                if ids[0]:
                                    list_id = []
                                    for id in ids[0][0]:
                                        list_id.append(id['id'])
                                    title = 'Waiting routing play driver accepted already!'
                                    body = 'Driver have accept routing plan day. Please check order! ' \
                                           + routingPlan['routing_plan_day_code']
                                    item_id = routingPlan['routing_plan_day_code']

                                    try:
                                        val = {
                                            'user_id': list_id,
                                            'title': title,
                                            'content': body,
                                            'click_action': ClickActionType.routing_plan_day_customer.value,
                                            'message_type': MessageType.success.value,
                                            'type': NotificationType.RoutingMessage.value,
                                            'object_status': RoutingDetailStatus.Driver_confirm.value,
                                            'item_id': item_id,
                                        }
                                        http.request.env['sharevan.notification'].create(val)
                                        return http.Response('Successful')
                                    except:
                                        logger.warn(
                                            "Accept Successful! But can not send message",
                                            RoutingPlanDay._name, item_id,
                                            exc_info=True)
                                        return http.Response('Successful')
                                else:
                                    logger.warn(
                                        "Employee fcm not found",
                                        RoutingPlanDay._name, 1,
                                        exc_info=True)
                                    return http.Response('Successful')
                            else:
                                dlp_employee_user = BaseMethod.get_dlp_employee()
                                if dlp_employee_user:
                                    title = 'Waiting routing play driver accepted already!'
                                    body = 'Driver have accept routing plan day. Please check order! ' \
                                           + routingPlan['routing_plan_day_code']
                                    item_id = routingPlan['routing_plan_day_code']

                                    try:
                                        val = {
                                            'user_id': dlp_employee_user,
                                            'title': title,
                                            'content': body,
                                            'click_action': ClickActionType.routing_plan_day_customer.value,
                                            'message_type': MessageType.success.value,
                                            'type': NotificationType.RoutingMessage.value,
                                            'object_status': RoutingDetailStatus.Driver_confirm.value,
                                            'item_id': item_id,
                                        }
                                        http.request.env['sharevan.notification'].create(val)
                                        return http.Response('Successful')
                                    except:
                                        logger.warn(
                                            "Accept Successful! But can not send message",
                                            RoutingPlanDay._name, item_id,
                                            exc_info=True)
                                        return http.Response('Successful')
                                else:
                                    logger.warn(
                                        "Employee fcm not found",
                                        RoutingPlanDay._name, 1,
                                        exc_info=True)
                                    return http.Response('Successful')
                        elif routingPlan['status'] == '2':
                            query = """
                                SELECT driver.user_id
                                FROM public.fleet_driver driver
                                where id = %s
                                    """
                            self._cr.execute(query, (driver_id,))
                            ids = self._cr.fetchall()
                            if len(ids) > 0:
                                title = 'Waiting routing play accepted already!'
                                body = 'Routing plan day have accept . Please check order! ' \
                                       + routingPlan['routing_plan_day_code']
                                item_id = routingPlan['routing_plan_day_code']

                                try:
                                    list_id = [ids[0][0], ]
                                    val = {
                                        'user_id': list_id,
                                        'title': title,
                                        'content': body,
                                        'click_action': ClickActionType.routing_plan_day_driver.value,
                                        'message_type': MessageType.success.value,
                                        'type': NotificationType.RoutingMessage.value,
                                        'object_status': RoutingDetailStatus.Done.value,
                                        'item_id': item_id,
                                    }
                                    http.request.env['sharevan.notification'].create(val)
                                    return http.Response('Successful')
                                except:
                                    logger.warn(
                                        "Accept Successful! But can not send message",
                                        RoutingPlanDay._name, item_id,
                                        exc_info=True)
                                    return http.Response('Successful')
                            else:
                                logger.warn(
                                    "Accept Successful! Driver fcm token not found!",
                                    RoutingPlanDay._name, '',
                                    exc_info=True)
                                return http.Response('Successful')
                    else:
                        raise ValidationError('Accept routing plan fail')
                else:
                    raise ValidationError('Routing plan have accepted already')
            else:
                raise ValidationError('Routing plan not found')

    #
    def get_routing_plan_day_by_employeeid(self, **kwargs):
        offset = 0
        limit = 10
        uID = http.request.env.uid
        param = []
        warehouse_code = None
        status = None
        for arg in kwargs:
            if arg == 'date':
                date = kwargs.get(arg)
                param.append(date)
            if arg == 'warehouse_code':
                warehouse_code = kwargs.get(arg)
            if arg == 'status':
                status = kwargs.get(arg)
            if arg == 'offset':
                offset = kwargs.get(arg)
            if arg == 'limit':
                limit = kwargs.get(arg)
        page = " offset " + str(offset) + " limit " + str(limit)
        user = http.request.env.uid
        user_record = http.request.env['res.users'].search([('id', '=', user)])
        # lấy tất cả các kho và depot của khách hàng có tuyến ngày chon
        query = """SELECT json_agg(t)
          FROM (
            select distinct(srpd.routing_plan_day_code),srpd.id,
                TO_CHAR(srpd.actual_time, 'YYYY-MM-DD HH24:MI:SS')        actual_time,
                TO_CHAR(srpd.expected_from_time, 'YYYY-MM-DD HH24:MI:SS') expected_from_time,
                TO_CHAR(srpd.expected_to_time, 'YYYY-MM-DD HH24:MI:SS')   expected_to_time,
                srpd.warehouse_name,
                srpd.status, srpd.so_type,
                CASE WHEN srpd.status = '4' THEN '-1'
                WHEN srpd.status = '1' THEN '0'
                WHEN srpd.status = '0' THEN '1'
                 ELSE srpd.status END
                 AS status_order,
                COALESCE(srpd.check_point,false) check_point,
                COALESCE(srpd.first_rating_customer,false) first_rating_customer,
                COALESCE(srpd.arrived_check,false) arrived_check,
                part.name booked_employee,
                TO_CHAR(srpd.date_plan, 'YYYY-MM-DD HH24:MI:SS')          date_plan,
                srpd.id routing_plan_day_id,
                srpd.type,srpd.order_number,
                srpd.vehicle_id,
                srpd.qr_gen_check,
                srpd.rating_customer,srpd.change_bill_lading_detail_id,
                veh.license_plate,
                driver.name driver_name,
                driver.phone driver_phone,COALESCE(srpd.trouble_type,'0') trouble_type,
                TO_CHAR(srpd.confirm_time, 'YYYY-MM-DD HH24:MI:SS')  confirm_time,
                TO_CHAR(srpd.accept_time, 'YYYY-MM-DD HH24:MI:SS')  accept_time
            from sharevan_routing_plan_day srpd
                join fleet_driver driver on driver.id = srpd.driver_id
                join fleet_vehicle veh on veh.id = srpd.vehicle_id
                join res_partner part on part.id = srpd.partner_id
            where 1 = 1
                and srpd.date_plan = %s
                 """
        count_query = """
                    select count(srpd.id)
                          from sharevan_routing_plan_day srpd
                          join fleet_driver driver on driver.id = srpd.driver_id
                        join fleet_vehicle veh on veh.id = srpd.vehicle_id
                          where 1 = 1
                          and srpd.date_plan = %s
                          
                """
        if status:
            query += " and srpd.status = %s  "
            count_query += " and srpd.status = %s "
            param.append(status)
        if user_record['channel_id'].name == 'customer':
            query += """ and ( srpd.warehouse_id in 
                     ( select distinct(sw.id) id
                        from sharevan_warehouse sw
                    join res_company rsc on rsc.id = sw.company_id
                    join res_users rus on rus.company_id = rsc.id and rus.id = %s 
                        where sw.status = 'running' and srpd.company_id = %s  
                        """
            count_query += """ and ( srpd.warehouse_id in 
                     ( select distinct(sw.id) id
                        from sharevan_warehouse sw
                    join res_company rsc on rsc.id = sw.company_id
                    join res_users rus on rus.company_id = rsc.id and rus.id = %s 
                        where sw.status = 'running' and srpd.company_id = %s """
            param.append(uID)
            param.append(user_record['company_id'].id)
            if warehouse_code:
                query += " and sw.warehouse_code = %s "
                count_query += " and sw.warehouse_code = %s "
                param.append(warehouse_code)
            query += """) or srpd.depot_id in 
                        (select distinct(sw.id) id
                            from sharevan_depot sw
                        join res_company rsc on rsc.id = sw.company_id
                        join res_users rus on rus.company_id = rsc.id and rus.id = %s 
                            where sw.status = 'running' """
            count_query += """) or srpd.depot_id in 
                        (select distinct(sw.id) id
                            from sharevan_depot sw
                        join res_company rsc on rsc.id = sw.company_id
                        join res_users rus on rus.company_id = rsc.id and rus.id = %s 
                            where sw.status = 'running' """
            param.append(uID)
            if warehouse_code:
                query += " and sw.depot_code = %s "
                count_query += " and sw.depot_code = %s "
                param.append(warehouse_code)
            query += """ )) """
            count_query += """ )) """
        elif user_record['channel_id'].name == 'dlp' and user_record['channel_id'].channel_type == 'manager':
            query += """ and ( srpd.warehouse_id in 
                                 ( select distinct(sw.id) id
                                    from sharevan_warehouse sw
                                    where sw.status = 'running' 
                                    """
            count_query += """ and ( srpd.warehouse_id in 
                                 ( select distinct(sw.id) id
                                    from sharevan_warehouse sw """
            if warehouse_code:
                query += " and sw.warehouse_code = %s "
                count_query += " and sw.warehouse_code = %s "
                param.append(warehouse_code)
            query += """) or srpd.depot_id in 
                                    (select distinct(sw.id) id
                                        from sharevan_depot sw
                                        where sw.status = 'running' """
            count_query += """) or srpd.depot_id in 
                                    (select distinct(sw.id) id
                                        from sharevan_depot sw
                                        where sw.status = 'running' """
            if warehouse_code:
                query += " and sw.depot_code = %s "
                count_query += " and sw.depot_code = %s "
                param.append(warehouse_code)
            query += """ )) """
            count_query += """ )) """
        elif user_record['channel_id'].name == 'dlp' and user_record['channel_id'].channel_type == 'employee':
            query += """
                 and srpd.depot_id in ( select place_id from sharevan_employee_warehouse ru
                       WHERE ru.user_id =%s and ru.date_assign = CURRENT_DATE  
            """
            count_query += """
                             and srpd.depot_id in ( select place_id from sharevan_employee_warehouse ru
                                   WHERE ru.user_id =%s and ru.date_assign = CURRENT_DATE  
                        """
            param.append(uID)
            if warehouse_code:
                query += " and sw.depot_code = %s "
                count_query += " and sw.depot_code = %s "
                param.append(warehouse_code)
            query += " ) and srpd.warehouse_id is null "
            count_query += " ) and srpd.warehouse_id is null "
        query += " order by status_order  " + page + " ) t"
        self.env.cr.execute(query,
                            (param))
        result = self._cr.fetchall()
        self.env.cr.execute(count_query,
                            (param))
        count = self._cr.fetchall()
        if result[0]:
            if result[0][0]:
                for re in result[0][0]:
                    service_query = """ 
                        SELECT json_agg(t)
                            FROM (
                        SELECT ser_ty.name, ser.type ,partner.name partner_name 
                           FROM public.sharevan_routing_plan_day_service ser
                               left join public.sharevan_service_type ser_ty on ser_ty.id = ser.service_id
                               join public.res_partner partner on partner.id = assign_partner_id
                               where routing_plan_day_id = %s )t
                    """
                    self.env.cr.execute(service_query,
                                        (re['id'],))
                    service_result = self._cr.fetchall()
                    services = []
                    if service_result[0]:
                        if service_result[0][0]:
                            services = service_result[0][0]
                    re['services'] = services
                records = {
                    'length': len(result[0][0]),
                    'records': result[0][0],
                    'total_record': count[0][0]
                }
                simplejson.dumps(records, indent=4, sort_keys=True, default=str)
                return records
        return {
            'records': []
        }

    def get_list_date_routing_plan(self, from_date, to_date, type):
        uID = http.request.env.uid
        query_check_role = """
            select partner.company_id ,st_type.code
                from res_partner partner 
            join res_staff_type st_type on st_type.id = partner.staff_type
                where partner.user_id = %s
            """
        self._cr.execute(query_check_role, (uID,))
        role_result = self._cr.dictfetchall()
        result = None
        if role_result:
            query = None
            if role_result[0]['code'] == StaffType.CUSTOMER_MANAGER.value or role_result[0][
                'code'] == StaffType.CUSTOMER_STOCKMAN.value:
                query = """
                    SELECT  distinct(TO_CHAR(t.date_plan, 'YYYY-MM-DD HH24:MI:SS')) date_plan
                        FROM sharevan_routing_plan_day as t
                            join res_users ru on ru.company_id=  t.company_id
                        WHERE t.date_plan >= %s and t.date_plan <=  %s 
                            and t.driver_id is not null and t.vehicle_id is not null
                            and ru.id = %s
                    """
                if type:
                    query = """
                        SELECT  distinct(TO_CHAR(t.date_plan, 'YYYY-MM-DD HH24:MI:SS')) date_plan
                            FROM sharevan_routing_plan_day as t
                                join res_users ru on ru.company_id=  t.company_id
                            WHERE t.date_plan >= %s and t.date_plan <=  %s 
                                and ru.id = %s
                                        """
                if from_date is None:
                    raise ValidationError("From date can not null")
                self._cr.execute(query, (from_date, to_date, uID,))
                result = self._cr.dictfetchall()
            elif role_result[0]['code'] == StaffType.SHAREVAN_MANAGER.value:
                query = """
                    SELECT  distinct(TO_CHAR(t.date_plan, 'YYYY-MM-DD HH24:MI:SS')) date_plan
                        FROM sharevan_routing_plan_day as t
                    WHERE t.date_plan >= %s and t.date_plan <=  %s   
                        and t.driver_id is not null and t.vehicle_id is not null
                """
                if type:
                    query = """
                        SELECT  distinct(TO_CHAR(t.date_plan, 'YYYY-MM-DD HH24:MI:SS')) date_plan
                            FROM sharevan_routing_plan_day as t
                        WHERE t.date_plan >= %s and t.date_plan <=  %s   
                                    """
                if from_date is None:
                    raise ValidationError("From date can not null")
                self._cr.execute(query, (from_date, to_date,))
                result = self._cr.dictfetchall()
            elif role_result[0]['code'] == StaffType.SHAREVAN_STOCKMAN.value:
                query = """
                    SELECT  distinct(TO_CHAR(t.date_plan, 'YYYY-MM-DD HH24:MI:SS')) date_plan
                       FROM sharevan_routing_plan_day as t
                           join sharevan_employee_warehouse ru on ru.place_id=  t.depot_id
                       WHERE ru.user_id =%s and ru.date_assign = CURRENT_DATE
                            and t.date_plan >= %s and t.date_plan <=  %s    
                        and t.driver_id is not null and t.vehicle_id is not null
                """
                if type:
                    query = """
                        SELECT  distinct(TO_CHAR(t.date_plan, 'YYYY-MM-DD HH24:MI:SS')) date_plan
                           FROM sharevan_routing_plan_day as t
                               join sharevan_employee_warehouse ru on ru.place_id=  t.depot_id
                           WHERE ru.user_id =%s and ru.date_assign = CURRENT_DATE
                                and t.date_plan >= %s and t.date_plan <=  %s    
                    """
                if from_date is None:
                    raise ValidationError("From date can not null")
                self._cr.execute(query, (uID, from_date, to_date,))
                result = self._cr.dictfetchall()
            if result and len(result) > 0:
                jreson = []
                for rec in result:
                    jreson.append(rec['date_plan'])
                records = {
                    'length': len(result),
                    'records': jreson
                }
            else:
                records = {
                    'length': 0,
                    'records': []
                }
            simplejson.dumps(records, indent=4, sort_keys=True, default=str)
            return records
        else:
            raise ValidationError('You are not allow to sign in app customer')

    def gen_qr_code(self, routing_plan_day_id):
        print(routing_plan_day_id)
        query = """
            select  distinct package.id, package.qr_char,package.quantity from sharevan_routing_plan_day plan
                join sharevan_bill_package_routing_plan package on package.routing_plan_day_id = plan.id
            where plan.id = %s and plan.type = '0'
        """
        self.env.cr.execute(query, (routing_plan_day_id,))
        get_qr_record = self._cr.dictfetchall()
        if get_qr_record:
            for record in get_qr_record:
                record = self.env['sharevan.bill.package.routing.plan'].search([('id', '=', record['id'])])
                if record:
                    if record['gen_qr_check'] == False and int(record['quantity']) < 500:
                        qr_code_new = ''
                        count = 1
                        while True:
                            if record['quantity'] > count or record['quantity'] == count:
                                qr_code_new += record['qr_char'] + '_' + str(count) + ','
                                count += 1
                            else:
                                qr_code_new = qr_code_new[:-1]
                                break
                        record.write({'qr_char': qr_code_new, 'gen_qr_check': True})
                else:
                    raise ValidationError('Routing package not found')
            routing = http.request.env['sharevan.routing.plan.day'].search([('id', '=', routing_plan_day_id)])
            vals = {'qr_gen_check': True}
            routing.write(vals)
            return {
                'status': 200,
                'message': 'Gen QR success'
            }
        else:
            raise ValidationError('Routing plan export not found')

    def get_bill_lading_details(self, bill_ladding_id):
        if bill_ladding_id:
            get_bill_lading = """
                SELECT json_agg(t)
                    from ( SELECT
                    bill_lading.id, bill_lading.name_seq, bill_lading.insurance_id, 
                    bill_lading.total_weight,
                    bill_lading.total_amount, bill_lading.tolls, bill_lading.surcharge, bill_lading.total_volume, bill_lading.vat, bill_lading.promotion_code,
                    bill_lading.release_type, bill_lading.total_parcel, bill_lading.company_id,
                    TO_CHAR(bill_lading.start_date, 'YYYY-MM-DD HH24:MI:SS') start_date,
                    TO_CHAR(bill_lading.end_date, 'YYYY-MM-DD HH24:MI:SS') end_date ,
                    bill_lading.status, bill_lading.description, bill_lading.name, bill_lading.create_uid,
                    TO_CHAR(bill_lading.create_date, 'YYYY-MM-DD HH24:MI:SS') create_date  ,
                    bill_lading.write_uid, bill_lading.create_uid,TO_CHAR(bill_lading.write_date, 'YYYY-MM-DD HH24:MI:SS') write_date ,
                    bill_lading.subscribe_id, bill_lading.frequency, bill_lading.day_of_week, bill_lading.day_of_month,
                    pack.name order_package_name,pack.id order_package_id,subscribe.name subscribe_name,
                    insurance.name insurance_name,insurance.amount insurance_amount,bill_lading.insurance_price,
                    bill_lading.service_price,bill_lading.price_not_discount,
                    bill_lading.cycle_type,bill_lading.award_company_id,award.name award_company_name
                FROM public.sharevan_bill_lading  bill_lading 
                    left join sharevan_bill_order_package pack on pack.id = bill_lading.order_package_id
                    left join sharevan_subscribe subscribe on subscribe.id = bill_lading.subscribe_id
                    left join sharevan_insurance insurance on insurance.id = bill_lading.insurance_id
                    left join sharevan_title_award award on award.id = bill_lading.award_company_id
                where bill_lading.id = %s ) t"""
            http.request.env['sharevan.bill.lading']._cr.execute(get_bill_lading, (bill_ladding_id,))
            result_get_bill_lading = http.request.env['sharevan.bill.lading']._cr.fetchall()
            if result_get_bill_lading[0]:
                if result_get_bill_lading[0][0]:
                    for recc in result_get_bill_lading[0][0]:
                        bill_lading_detail_arr = []
                        get_bill_lading_detail = """
                        SELECT json_agg(t)
                            from
                            ( SELECT id, name_seq, bill_lading_id, total_weight, warehouse_id, warehouse_type,
                                from_bill_lading_detail_id, description,
                                     TO_CHAR(expected_from_time, 'YYYY-MM-DD HH24:MI:SS') expected_from_time,
                                     TO_CHAR(expected_to_time, 'YYYY-MM-DD HH24:MI:SS')  expected_to_time,
                                     name, status, approved_type, from_warehouse_id, latitude, longitude,
                                      area_id, zone_area_id, address, status_order, create_uid,
                                      TO_CHAR(create_date, 'YYYY-MM-DD HH24:MI:SS') create_date, write_uid,
                                      TO_CHAR(write_date, 'YYYY-MM-DD HH24:MI:SS') write_date,
                                      warehouse_name, max_price, min_price,
                                      price, trans_id, depot_id, order_type
                            FROM public.sharevan_bill_lading_detail b where b.bill_lading_id = %s order by b.id) t """
                        http.request.env['sharevan.bill.lading.detail']._cr.execute(get_bill_lading_detail, (bill_ladding_id,))
                        result_get_bill_lading_detail = http.request.env['sharevan.bill.lading.detail']._cr.fetchall()

                        for bill_lading_detail in result_get_bill_lading_detail[0][0]:
                            bill_detail_json = {}
                            get_sharevan_bill_lading_detail_sharevan_service_type_rel = """  SELECT json_agg(t)
                                            from
                                            ( SELECT sharevan_bill_lading_detail_id, sharevan_service_type_id
                                            FROM public.sharevan_bill_lading_detail_sharevan_service_type_rel rel where rel.sharevan_bill_lading_detail_id = %s ) t  """
                            print(bill_lading_detail['id'])
                            http.request.env['sharevan.bill.lading.detail']._cr.execute(get_sharevan_bill_lading_detail_sharevan_service_type_rel,
                                                (bill_lading_detail['id'],))
                            result_service_rel = http.request.env['sharevan.bill.lading.detail']._cr.fetchall()

                            get_warehouse = """
                                SELECT json_agg(t)    from  (
                                    SELECT  id, name, warehouse_code, address, street, street2, city_name,
                                        district, ward, zip, state_id, country_id, latitude, longitude, phone,
                                        zone_id, area_id, company_id, customer_id, status, name_seq, create_uid,
                                        TO_CHAR(create_date, 'YYYY-MM-DD HH24:MI:SS') create_date, write_uid,
                                        TO_CHAR(write_date, 'YYYY-MM-DD HH24:MI:SS') write_date,
                                         open_time,closing_time
                                    from sharevan_warehouse  warehouse
                                        where warehouse.id = %s ) t  """
                            http.request.env['sharevan.warehouse']._cr.execute(get_warehouse,
                                                (bill_lading_detail['warehouse_id'],))
                            result_get_warehouse = http.request.env['sharevan.warehouse']._cr.fetchall()
                            if result_get_warehouse[0][0]:
                                warehouse_infor = result_get_warehouse[0][0][0]
                            else:
                                warehouse_infor = {}
                            result_service_rel_arr = []
                            if result_service_rel[0][0]:

                                for rec in result_service_rel[0][0]:
                                    get_sharevan_service_type = """ SELECT json_agg(t)
                                                from
                                                ( SELECT id, name, price, vendor_id, service_code, status, description, create_uid, TO_CHAR(create_date, 'YYYY-MM-DD HH24:MI:SS') create_date, write_uid,TO_CHAR(write_date, 'YYYY-MM-DD HH24:MI:SS') write_date
                                                                                   FROM public.sharevan_service_type service_type where service_type.id = %s ) t """
                                    print(rec['sharevan_service_type_id'])
                                    http.request.env['sharevan.service.type']._cr.execute(get_sharevan_service_type, (rec['sharevan_service_type_id'],))
                                    result_get_sharevan_service_type = http.request.env['sharevan.service.type']._cr.fetchall()
                                    result_service_rel_arr.append(result_get_sharevan_service_type[0][0][0])

                            get_bill_package = """ SELECT json_agg(t)
                                            from
                                            ( SELECT bill_package.id, bill_package.item_name, bill_package.bill_lading_detail_id, bill_package.net_weight, bill_package.quantity_package, bill_package.length, bill_package.width, bill_package.height, bill_package.capacity, bill_package.description, bill_package.product_type_id,p.name product_type_name,  bill_package.status, bill_package.create_uid, TO_CHAR(bill_package.create_date, 'YYYY-MM-DD HH24:MI:SS') create_date, bill_package.write_uid, TO_CHAR(bill_package.write_date, 'YYYY-MM-DD HH24:MI:SS') write_date
                                                       FROM public.sharevan_bill_package bill_package
                                                       join sharevan_product_type p on p.id = bill_package.product_type_id
                                                       where bill_package.bill_lading_detail_id = %s ) t """
                            http.request.env['sharevan.bill.package']._cr.execute(get_bill_package, (bill_lading_detail['id'],))
                            result_get_bill_package = http.request.env['sharevan.bill.package']._cr.fetchall()

                            bidding_detail_js = {
                                'id': bill_lading_detail['id'],
                                'name_seq': bill_lading_detail['name_seq'],
                                'bill_lading_id': bill_lading_detail['bill_lading_id'],
                                'total_weight': bill_lading_detail['total_weight'],
                                'warehouse': warehouse_infor,
                                'warehouse_type': bill_lading_detail['warehouse_type'],
                                'from_bill_lading_detail_id': bill_lading_detail['from_bill_lading_detail_id'],
                                'description': bill_lading_detail['description'],
                                'expected_from_time': bill_lading_detail['expected_from_time'],
                                'expected_to_time': bill_lading_detail['expected_to_time'],
                                'name': bill_lading_detail['name'],
                                'status': bill_lading_detail['status'],
                                'approved_type': bill_lading_detail['approved_type'],
                                'latitude': bill_lading_detail['latitude'],
                                'longitude': bill_lading_detail['longitude'],
                                'area_id': bill_lading_detail['area_id'],
                                'zone_area_id': bill_lading_detail['zone_area_id'],
                                'price': bill_lading_detail['price'],
                                'max_price': bill_lading_detail['max_price'],
                                'min_price': bill_lading_detail['min_price'],
                                'address': bill_lading_detail['address'],
                                'status_order': bill_lading_detail['status_order'],
                                'billPackages': result_get_bill_package[0][0],
                                'billService': result_service_rel_arr,
                            }

                            bill_lading_detail_arr.append(bidding_detail_js)
                        bill_state_record = 'running'
                        if datetime.strptime(recc['end_date'], "%Y-%m-%d %H:%M:%S").date()  < datetime.today().date():
                            bill_state_record = 'finished'
                        content = {
                            'id': recc['id'],
                            'name_seq': recc['name_seq'],
                            'insurance_id': recc['insurance_id'],
                            'insurance': {
                                'insurance_id': recc['insurance_id'],
                                'insurance_name': recc['insurance_name'],
                                'insurance_amount': recc['insurance_amount'],
                            },
                            'cycle_type': recc['cycle_type'],
                            'total_weight': recc['total_weight'],
                            'total_amount': recc['total_amount'],
                            'price_not_discount': recc['price_not_discount'],
                            'insurance_price': recc['insurance_price'],
                            'service_price': recc['service_price'],
                            'order_package': {
                                'id': recc['order_package_id'],
                                'name': recc['order_package_name'],
                            },
                            'tolls': recc['tolls'],
                            'surcharge': recc['surcharge'],
                            'total_volume': recc['total_volume'],
                            'bill_state': bill_state_record,
                            'vat': recc['vat'],
                            'promotion_code': recc['promotion_code'],
                            'release_type': recc['release_type'],
                            'total_parcel': recc['total_parcel'],
                            'company_id': recc['company_id'],
                            'day_of_week': recc['day_of_week'],
                            'award_company_id': recc['award_company_id'],
                            'award_company_name': recc['award_company_name'],
                            'day_of_month': recc['day_of_month'],
                            'start_date': recc['start_date'],
                            'end_date': recc['end_date'],
                            'status': recc['status'],
                            'name': recc['name'],
                            'subscribe': {
                                'subscribe_id': recc['subscribe_id'],
                                'name': recc['subscribe_name'],
                            },
                            'frequency': recc['frequency'],
                            'arrBillLadingDetail': bill_lading_detail_arr
                        }

                        re = content
                        records = {
                            'length': len(re),
                            'records': [re]
                        }
                        simplejson.dumps(records, indent=4, sort_keys=True, default=str)
                        return records
                else:
                    raise ValidationError(_('Bill of lading id does not exist'))
        else:
            raise ValidationError(_('Bill of lading id can not null !'))

    def update_routing_plan_day(self, routing_plan_day):
        driver = http.request.env['fleet.driver'].search \
            ([('id', '=', routing_plan_day['driver']['id']), ('user_id', '=', http.request.env.user.id),
              ('company_id', '=', http.request.env.company.id)])
        if driver is False:
            raise ValidationError('You are not allow to accept routing plan day of other company')

        bill_lading_detail = http.request.env['sharevan.bill.lading.detail'].search \
            ([('id', '=', routing_plan_day['bill_lading_detail_id'])])
        if bill_lading_detail is None:
            raise ValidationError('Bill of lading detail not found')
        vals = {
            'bill_lading_id': bill_lading_detail['bill_lading_id']['id'],
            'warehouse_id': bill_lading_detail['warehouse_id']['id'],
            'warehouse_type': bill_lading_detail['warehouse_type'],
            'expected_from_time': bill_lading_detail['expected_from_time'],
            'expected_to_time': bill_lading_detail['expected_to_time'],
            'longitude': bill_lading_detail['longitude'],
            'latitude': bill_lading_detail['latitude'],
            'area_id': bill_lading_detail['area_id']['id'],
            'zone_area_id': bill_lading_detail['zone_area_id']['id'],
            'warehouse_name': bill_lading_detail['warehouse_name'],
            'address': bill_lading_detail['address'],
            'depot_id': bill_lading_detail['depot_id']['id'],
            'hub_id': bill_lading_detail['hub_id']['id'],
            'phone': bill_lading_detail['phone'],
            'service_id': bill_lading_detail['service_id'],
            'status_order': 'draft'
        }
        bill_lading_id = bill_lading_detail['bill_lading_id']['id']

        record = http.request.env['sharevan.bill.lading.detail'].create(vals)
        bill_lading_detail_id = record['id']
        for bill_package in routing_plan_day['list_bill_package']:
            if 'item_name' in bill_package:
                item_name = bill_package['item_name']
            else:
                item_name = ''
            package = {
                'bill_lading_detail_id': record['id'],
                'net_weight': bill_package['total_weight'],
                'quantity_package': bill_package['quantity_import'],
                'length': bill_package['length'],
                'width': bill_package['width'],
                'height': bill_package['height'],
                'item_name': item_name,
                'product_type_id': bill_package['product_type_id'],
                'capacity': bill_package['capacity'],
                'status': 'draft',
                'from_bill_package_id': bill_package['bill_package_id']
            }
            http.request.env['sharevan.bill.package'].create(package)
        record_routing = http.request.env[RoutingPlanDay._name]. \
            browse(routing_plan_day['id']).write(
            {'status': RoutingDetailStatus.WaitingApprove.value, 'change_bill_lading_detail_id': bill_lading_detail_id})
        record_bill_routing = http.request.env[BillRouting._name]. \
            browse(routing_plan_day['bill_routing_id']).write(
            {'status_routing': BillRoutingStatus.InClaim.value,
             'change_bill_lading_detail_id': bill_lading_detail_id})
        ids = []
        # employee share van
        query = """ select us.id from res_users us
                        join res_company company on us.company_id = company.id
                     where company.company_type = '2' and us.active = true """
        self._cr.execute(query, ())
        record = self._cr.dictfetchall()
        for id in record:
            ids.append(id['id'])
        # gui den quan ly cua cong ty doi tac de duyet don
        query = """ 
            select us.id from res_users us
                join sharevan_channel channel on channel.id = us.channel_id 
            where us.company_id = %s and us.active = true
                and channel.name = 'customer' and channel_type = 'manager' """
        self._cr.execute(query, (routing_plan_day['company_id'],))
        record = self._cr.dictfetchall()
        if len(record) > 0:
            for id in record:
                ids.append(id['id'])
            title = 'Bill of lading change plan'
            body = 'Bill of lading change  in routing plan day! ' \
                   + 'Bill of lading id : ' + str(bill_lading_id)
            item_id = bill_lading_detail_id
            try:
                val = {
                    'user_id': ids,
                    'title': title,
                    'content': body,
                    'click_action': ClickActionType.bill_lading.value,
                    'message_type': MessageType.danger.value,
                    'type': NotificationType.RoutingMessage.value,
                    'object_status': RoutingDetailStatus.Unconfimred.value,
                    'item_id': item_id,
                }
                http.request.env['sharevan.notification'].create(val)
                return {
                    'length': 1,
                    'records': [{
                        'bill_lading_id': bill_lading_id,
                        'bill_lading_detail_id': bill_lading_detail_id,
                    }]
                }
            except:
                logger.warn(
                    "Save bill of lading change! But can not send message",
                    BillLadingDetail._name, item_id,
                    exc_info=True)
                return {
                    'length': 1,
                    'records': [{
                        'bill_lading_id': bill_lading_id,
                        'bill_lading_detail_id': bill_lading_detail_id,
                    }]
                }
        else:
            title = 'Bill of lading change plan'
            body = 'Bill of lading change  in routing plan day! ' \
                   + 'Bill of lading id : ' + str(bill_lading_id)
            item_id = bill_lading_detail_id
            try:
                val = {
                    'user_id': ids,
                    'title': title,
                    'content': body,
                    'click_action': ClickActionType.bill_lading.value,
                    'message_type': MessageType.danger.value,
                    'type': NotificationType.RoutingMessage.value,
                    'object_status': RoutingDetailStatus.Unconfimred.value,
                    'item_id': item_id,
                }
                http.request.env['sharevan.notification'].create(val)
                return {
                    'length': 1,
                    'records': [{
                        'bill_lading_id': bill_lading_id,
                        'bill_lading_detail_id': bill_lading_detail_id,
                    }]
                }
            except:
                logger.warn(
                    "Save bill of lading change! But can not send message",
                    BillLadingDetail._name, item_id,
                    exc_info=True)
                return {
                    'length': 1,
                    'records': [{
                        'bill_lading_id': bill_lading_id,
                        'bill_lading_detail_id': bill_lading_detail_id,
                    }]
                }

    def update_routing_plan_day_with_image(self, routingPlan, files):
        routing_plan_day = json.loads(routingPlan)
        lst_image = []
        driver = http.request.env['fleet.driver'].search \
            ([('id', '=', routing_plan_day['driver']['id']), ('user_id', '=', http.request.env.user.id),
              ('company_id', '=', http.request.env.company.id)])
        if driver is False:
            response_data = {
                'status': 500,
                'message': 'Driver is not allow this routing',
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)

        bill_lading_detail = http.request.env['sharevan.bill.lading.detail'].search \
            ([('id', '=', routing_plan_day['bill_lading_detail_id'])])
        if bill_lading_detail is None:
            response_data = {
                'status': 500,
                'message': 'Bill of lading not found',
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        vals = {
            'bill_lading_id': bill_lading_detail['bill_lading_id']['id'],
            'warehouse_id': bill_lading_detail['warehouse_id']['id'],
            'warehouse_type': bill_lading_detail['warehouse_type'],
            'expected_from_time': bill_lading_detail['expected_from_time'],
            'expected_to_time': bill_lading_detail['expected_to_time'],
            'longitude': bill_lading_detail['longitude'],
            'latitude': bill_lading_detail['latitude'],
            'area_id': bill_lading_detail['area_id']['id'],
            'zone_area_id': bill_lading_detail['zone_area_id']['id'],
            'warehouse_name': bill_lading_detail['warehouse_name'],
            'address': bill_lading_detail['address'],
            'depot_id': bill_lading_detail['depot_id']['id'],
            'hub_id': bill_lading_detail['hub_id']['id'],
            'phone': bill_lading_detail['phone'],
            'service_id': bill_lading_detail['service_id'],
            'status_order': 'draft'
        }
        bill_lading_id = bill_lading_detail['bill_lading_id']['id']

        record = http.request.env['sharevan.bill.lading.detail'].create(vals)
        bill_lading_detail_id = record['id']
        for bill_package in routing_plan_day['list_bill_package']:
            if 'item_name' in bill_package:
                item_name = bill_package['item_name']
            else:
                item_name = ''
            package = {
                'bill_lading_detail_id': record['id'],
                'net_weight': bill_package['total_weight'],
                'quantity_package': bill_package['quantity_import'],
                'length': bill_package['length'],
                'width': bill_package['width'],
                'height': bill_package['height'],
                'item_name': item_name,
                'product_type_id': bill_package['product_type_id'],
                'capacity': bill_package['capacity'],
                'status': 'draft',
                'from_bill_package_id': bill_package['bill_package_id']
            }
            http.request.env['sharevan.bill.package'].create(package)
        record_routing = http.request.env[RoutingPlanDay._name]. \
            browse(routing_plan_day['id']).write(
            {'status': RoutingDetailStatus.WaitingApprove.value, 'change_bill_lading_detail_id': bill_lading_detail_id})
        record_bill_routing = http.request.env[BillRouting._name]. \
            browse(routing_plan_day['bill_routing_id']).write(
            {'status_routing': BillRoutingStatus.InClaim.value,
             'change_bill_lading_detail_id': bill_lading_detail_id})
        for file in files:
            if file.filename:
                val = {
                    'res_model': 'sharevan.routing.plan.day',
                    'mimetype': file.mimetype,
                    'name': file.filename,
                    'res_id': routing_plan_day['id'],
                    'status': 'running',
                    'type': 'binary',
                    'datas': base64.b64encode(file.read())
                }
                rec = http.request.env[IrAttachment._name].create(val)
                http.request.cr.execute(INSERT_QUERY, (routing_plan_day['id'], rec['id'],))
        ids = []
        # employee share van
        query = """ select us.id from res_users us
                        join res_company company on us.company_id = company.id
                     where company.company_type = '2' and us.active = true """
        self._cr.execute(query, ())
        record = self._cr.dictfetchall()
        for id in record:
            ids.append(id['id'])
        # gui den quan ly cua cong ty doi tac de duyet don
        query = """ 
            select us.id from res_users us
                join sharevan_channel channel on channel.id = us.channel_id 
            where us.company_id = %s and us.active = true
                and channel.name = 'customer' and channel_type in( 'manager','employee') """
        self._cr.execute(query, (routing_plan_day['company_id'],))
        record = self._cr.dictfetchall()
        if len(record) > 0:
            for id in record:
                ids.append(id['id'])
            title = 'Bill of lading change plan'
            body = 'Bill of lading change  in routing plan day! ' \
                   + 'Bill of lading id : ' + str(bill_lading_id)
            item_id = bill_lading_detail_id
            try:
                val = {
                    'user_id': ids,
                    'title': title,
                    'content': body,
                    'click_action': ClickActionType.bill_lading.value,
                    'message_type': MessageType.danger.value,
                    'type': NotificationType.RoutingMessage.value,
                    'object_status': RoutingDetailStatus.Unconfimred.value,
                    'item_id': item_id,
                }
                http.request.env['sharevan.notification'].create(val)
                response_data = {
                    'status': 200,
                    'message': bill_lading_detail_id,
                }
                return Response(json.dumps(response_data), content_type="application/json", status=200)
            except:
                logger.warn(
                    "Save bill of lading change! But can not send message",
                    BillLadingDetail._name, item_id,
                    exc_info=True)
                response_data = {
                    'status': 200,
                    'message': bill_lading_detail_id,
                }
            return Response(json.dumps(response_data), content_type="application/json", status=200)
        else:
            title = 'Bill of lading change plan'
            body = 'Bill of lading change  in routing plan day! ' \
                   + 'Bill of lading id : ' + str(bill_lading_id)
            item_id = bill_lading_detail_id
            try:
                val = {
                    'user_id': ids,
                    'title': title,
                    'content': body,
                    'click_action': ClickActionType.bill_lading.value,
                    'message_type': MessageType.danger.value,
                    'type': NotificationType.RoutingMessage.value,
                    'object_status': RoutingDetailStatus.Unconfimred.value,
                    'item_id': item_id,
                }
                http.request.env['sharevan.notification'].create(val)
                response_data = {
                    'status': 200,
                    'message': bill_lading_detail_id,
                }
                return Response(json.dumps(response_data), content_type="application/json", status=200)
            except:
                logger.warn(
                    "Save bill of lading change! But can not send message",
                    BillLadingDetail._name, item_id,
                    exc_info=True)
                response_data = {
                    'status': 200,
                    'message': bill_lading_detail_id,
                }
                return Response(json.dumps(response_data), content_type="application/json", status=200)

    def cancel_update_rpd(self, bill_lading_detail_id):
        rpd = http.request.env[RoutingPlanDay._name].search(
            [('bill_lading_detail_id', '=', bill_lading_detail_id), ('date_plan', '=', datetime.today())])
        if rpd is None or len(rpd) == 0:
            raise ValidationError("Check your input and try again")
        update_res = rpd.write({'status': '0'})
        if not update_res:
            raise RuntimeError("Something went wrong, contact the admin to resolve the problem")
        # users = [rpd['driver_id']]
        users = []
        company_users = http.request.env['fleet.driver']. \
            search([('id', '=', rpd['driver_id'])])
        if company_users:
            for driver in company_users:
                users.append(driver['user_id'])
        content = {
            'title': 'Routing cancel for change. ' + rpd['routing_plan_day_code'],
            'content': 'Changing of routing is cancel. You should pick up right quantity or request to cancel the '
                       'routing',
            'sent_date': datetime.today(),
            'type': 'routing',
            'object_status': 'running',
            'click_action': ClickActionType.routing_plan_day_driver.value,
            'message_type': MessageType.warning.value,
            'user_id': users,
        }
        self.env['sharevan.notification'].sudo().create(content)
        return {
            'status': 200,
            'message': 'Cancel update bill successful!'
        }

    def cancel_routing_once_day(self, bill_lading_detail, description, files):
        routing_query = """
            select id , driver_id,routing_plan_day_code, status, type from sharevan_routing_plan_day 
                where id in (
            WITH RECURSIVE c AS (
                SELECT (select id from sharevan_routing_plan_day 
                    where bill_lading_detail_id = %s and date_plan = CURRENT_DATE
                       ) AS id
                UNION ALL
                SELECT sa.id
                FROM sharevan_routing_plan_day AS sa
                JOIN c ON c.id = sa.from_routing_plan_day_id
                )
            SELECT id FROM c ) order by type
        """
        self._cr.execute(routing_query, (bill_lading_detail,))
        rpd = self._cr.dictfetchall()
        if rpd is None or len(rpd) == 0:
            raise ValidationError("No routing found")
        driver_lst = []
        driver_id = None
        bill_routing_id = None
        routing_plan_day_id = None
        image_record_id = 0
        time_now = datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")
        BaseMethod.check_role_access(http.request.env.user, 'sharevan.routing.plan.day',
                                     rpd[0]['id'])
        for rec in rpd:
            if (rec['type'] == '0'):
                image_record_id = rec['id']
                if rec['status'] == RoutingDetailStatus.Done.value:
                    raise ValidationError('Driver have pick up date export warehouse bill not allow to cancel!')
            routing_plan_day_id = rec['id']
            record = http.request.env[RoutingPlanDay._name].search(
                [('id', '=', rec['id'])])
            driver_id = record['driver_id']['id']
            driver_lst.append(driver_id)
            if record:
                bill_routing_id = record['bill_routing_id']
                update_res = record.write(
                    {
                        'status': RoutingDetailStatus.Cancel.value,
                        'accept_time': time_now,
                        'description': description
                    }
                )
            else:
                raise ValidationError("No routing found")
        record_routing = http.request.env[BillRouting._name].search(
            [('id', '=', bill_routing_id.id)])
        if record_routing:
            record_routing.write(
                {
                    'status_routing': BillRoutingStatus.Cancel.value,
                    'description': description,
                    'cancel_check': False
                }
            )
        for file in files:
            if file.filename:
                val = {
                    'res_model': 'sharevan.routing.plan.day',
                    'mimetype': file.mimetype,
                    'name': file.filename,
                    'res_id': image_record_id,
                    'status': 'running',
                    'type': 'binary',
                    'datas': base64.b64encode(file.read())
                }
                rec = http.request.env[IrAttachment._name].create(val)
                rec.write({'uri_path': rec['store_fname'], 'res_field': 'image_128'})
                http.request.cr.execute(
                    INSERT_QUERY,
                    (image_record_id, rec['id'],))

        users = BaseMethod.get_fleet_manager(driver_id)
        employee_dlp = BaseMethod.get_dlp_employee()
        if len(employee_dlp) > 0:
            for employee in employee_dlp:
                users.append(employee)
        if len(users) > 0:
            content = {
                'title': 'Routing cancel for change. ' + record_routing['code'],
                'content': 'Changing of routing is cancel. Customer have cancel routing !',
                'type': 'routing',
                'res_id': routing_plan_day_id,
                'res_model': 'sharevan.routing.plan.day',
                'click_action': ClickActionType.routing_plan_day_driver.value,
                'message_type': MessageType.warning.value,
                'user_id': users,
            }
            self.env['sharevan.notification'].sudo().create(content)
            for manager in users:
                notice = "Changing of routing is cancel. Customer have cancel routing !"
                user = self.env['res.users'].search(
                    [('id', '=', manager)])
                user.notify_info(message=notice, title=NotificationSocketType.NOTIFICATION.value)
        driver_users = []
        for id in driver_lst:
            routing_query = """
                select user_id from fleet_driver where id =%s
                                            """
            self._cr.execute(routing_query, (id,))
            driver = self._cr.dictfetchall()
            if driver:
                if len(driver_users) > 0:
                    for d_id in driver_users:
                        if d_id != driver[0]['user_id']:
                            driver_users.append(d_id)
                else:
                    driver_users.append(driver[0]['user_id'])
        # send for driver
        if len(driver_users) > 0:
            try:
                content = {
                    'title': 'Routing cancel for change. ' + record_routing['code'],
                    'content': 'Changing of routing is cancel. Customer have cancel routing !',
                    'type': 'routing',
                    'res_id': routing_plan_day_id,
                    'res_model': 'sharevan.routing.plan.day',
                    'click_action': ClickActionType.driver_history_activity.value,
                    'message_type': MessageType.warning.value,
                    'user_id': driver_users,
                    'item_id': record_routing['code'],
                }
                http.request.env[Notification._name].create(content)
            except:
                logger.warn(
                    "Cancel Successful! But can not send message for driver",
                    BillRouting._name, routing_plan_day_id,
                    exc_info=True)
            response_data = {
                'status': 200,
                'message': 'Cancel routing request for today is successful!'
            }
            return Response(json.dumps(response_data), content_type="application/json", status=200)
        else:
            response_data = {
                'status': 204,
                'message': 'Cancel routing request for today is successful! But you have to call for sharevan employee'
            }
            return Response(json.dumps(response_data), content_type="application/json", status=200)

    def get_model_name(self, model):

        querry_model_name = """SELECT json_agg(t) from (
                                SELECT id, name From """
        querry_model_name += model
        querry_model_name += " Where status = 'running' ) t"

        self.env.cr.execute(querry_model_name, ())
        result_ = self._cr.fetchall()

        re = result_
        records = {
            'length': len(re),
            'records': [re]
        }
        simplejson.dumps(records, indent=4, sort_keys=True, default=str)
        return records

    def get_model_name_warehouse(self, model, id):
        querry_model_name = """SELECT json_agg(t) from (
                                            SELECT warehouse.name ,
                                                   state.name as state_name,
                                                   district.name as district_name,
                                                   ward.name as ward_name,
                                                   warehouse.phone,
                                                   employee.name as customer_name,
                                                   warehouse.address
                                            From sharevan_warehouse warehouse
                                            join sharevan_area state on warehouse.state_id = state.id
                                            join sharevan_area district on warehouse.district = district.id
                                            join sharevan_area ward on warehouse.ward = ward.id
                                            left join res_partner employee on warehouse.customer_id = employee.id
                                            where warehouse.id =%s ) t"""

        self.env.cr.execute(querry_model_name, (id,))
        result_ = self._cr.fetchall()

        re = result_
        records = {
            'length': len(re),
            'records': [re]
        }
        simplejson.dumps(records, indent=4, sort_keys=True, default=str)
        return records

    def get_service_type(self):
        querry_service_type = """SELECT json_agg(t) from (
                                            SELECT 
                                                    service.id,
                                                    service.name ,
                                                    service.price
                                            From sharevan_service_type service
                                            where status = 'running' ) t"""

        self.env.cr.execute(querry_service_type, (id,))
        result_ = self._cr.fetchall()

        re = result_
        result_list = []
        if re:
            for record in re[0][0]:
                result_list.append({
                    'id':record['id'],
                    'name': record['name'],
                    'price': '{:20,.2f}'.format(record['price']),
                })

        records = {
            'length': len(result_list),
            'records': [result_list]
        }
        simplejson.dumps(records, indent=4, sort_keys=True, default=str)
        return records

class Rating(models.Model):
    _name = 'sharevan.rating'
    _inherit = 'sharevan.rating'
    MODEL = _name

    _description = 'Rating'

    # @api.model
    # def create(self, vals):
    #     res = super(Rating, self).create(vals)
    #     bonus_point = vals.get('num_rating')
    #     if 'num_rating' in vals :
    #         driver = self.env['fleet.driver'].search([('id', '=', vals.get('driver_id'))])
    #         point = driver.point + bonus_point
    #         driver.write({'point': point})
    #     return res


class RatingBadges(models.Model):
    _name = 'sharevan.rating.badges'
    _inherit = 'sharevan.rating.badges'
    _description = ' rating badges'


class RatingBadgesDriver(models.Model):
    _name = 'sharevan.rating.driver.badges'
    _inherit = 'sharevan.rating.driver.badges'
    _description = 'Rating driver badges'
    MODEL = _name


class TitleAward(models.Model):
    _name = 'sharevan.title.award'
    _inherit = 'sharevan.title.award'
    _description = 'title award driver'
    MODEL = _name


