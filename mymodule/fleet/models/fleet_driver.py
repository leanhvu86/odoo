# -*- coding: utf-8 -*-
import base64
import json
import json as simplejson
from datetime import datetime, timedelta, timezone
import re as re

import pytz

from addons.web.controllers.main import DataSet
from addons.website.controllers.main import logger
from mymodule.enum.VehicleStateStatus import VehicleStateStatus
from odoo import http
from odoo import models, _
from odoo.addons.base.models.ir_attachment import IrAttachment
from odoo.exceptions import ValidationError
from odoo.http import Response
from odoo.tools import config
from .fleet_vehicle_status import VehicleEquipmentDriver
from ...base_next.controllers.api.base_method import BaseMethod
from ...base_next.controllers.api.firebase_messaging import FirebaseMessagingAPI
from ...base_next.models.fleet_driver import MODEL_FLEET_VEHICLE_MODEL_BRAND, MODEL_FLEET_DRIVER
from ...base_next.models.notification import Notification
from ...constants import Constants
from ...enum.ClickActionType import ClickActionType
from ...enum.MessageType import MessageType, NotificationSocketType
from ...enum.NotificationType import NotificationType
from ...enum.RoutingDetailStatus import RoutingDetailStatus


class FleetDriver(models.Model):
    _name = 'fleet.driver'
    _inherit = 'fleet.driver'
    MODEL = 'fleet.driver'
    _description = 'Fleet driver'

    def get_fleet_driver(self, uid):
        driver_id = self.env['fleet.driver'].search([('user_id', '=', int(uid))]).id
        if driver_id == False:
            raise ValidationError(_('You are not authorized to enter the fleet !'))

        sql_list_image_vehicle = """
                                 SELECT ir.uri_path as image
                                 FROM fleet_vehicle fv
                                 LEFT JOIN ir_attachment ir on fv.id = ir.res_id 
								 and ir.res_model='fleet.vehicle'
                                 WHERE  fv.id = %s
              				      """

        self.env.cr.execute("""
            SELECT json_agg(t)
                FROM (SELECT
                vehlog.id as vehlog_id , vehlog.assignation_log_code ,TO_CHAR(vehlog.date_start,'YYYY-MM-DD HH24:MI:SS') date_start,
                TO_CHAR(vehlog.date_end,'YYYY-MM-DD HH24:MI:SS') date_end,
                pk.id as parking_point_id,pk.name as parking_point_name, pk.address as parking_point_address,pk.phone_number,pk.latitude,pk.longitude,
                pk.street,pk.city_name,
                veh.id as vehicle_id , veh.name as vehicle_name , veh.license_plate,veh.color,veh.model_year,veh.fuel_type,
                veh.body_length,veh.body_width,veh.height,veh.vehicle_type,veh.engine_size,fleet_type.name fleet_type_name,
                ir.uri_path image_logo,
                rc.name as country_name,veh.sos_status,
                vs.name as status ,vehlog.id assignation_id ,veh.uniqueid, COALESCE(veh.iot_type,false) iot_type
                FROM  fleet_vehicle veh
                    LEFT JOIN fleet_vehicle_assignation_log vehlog on vehlog.vehicle_id = veh.id
                    LEFT JOIN fleet_vehicle_state vs on veh.state_id = vs.id
                    LEFT JOIN parking_point pk on veh.parking_point_id = pk.id
                    LEFT JOIN res_country rc on pk.country_id = rc.id
                    LEFT JOIN fleet_vehicle_type fleet_type on veh.vehicle_type = fleet_type.id
                    LEFT JOIN fleet_vehicle_model fvm on fvm.id = veh.model_id
                    LEFT JOIN fleet_vehicle_model_brand fvmb on fvmb.id = fvm.brand_id
                    LEFT JOIN ir_attachment ir on fvmb.id = ir.res_id and ir.res_model = 'fleet.vehicle.model.brand' 
                WHERE  vehlog.driver_id = %s and vehlog.give_car_back IS NULL
                    and vehlog.driver_status = '1' 
                    ORDER BY vehlog.date_start ASC
                LIMIT 1
            		) t ;""", (driver_id,))

        result = self._cr.fetchall()
        parking_point = None
        assignation_log = None
        vehicle = None
        if result[0][0]:
            re = result[0][0][0]

            parking_point = {
                'id': re['parking_point_id'],
                'name': re['parking_point_name'],
                'address': re['parking_point_address'],
                'phone': re['phone_number'],
                'latitude': re['latitude'],
                'longitude': re['longitude']
            }
            assignation_log = {
                'id': re['assignation_id'],
                'assignation_log_code': re['assignation_log_code'],
                'date_start': re['date_start'],
                'date_end': re['date_end']

            }
            vehicle = {
                'id': re['vehicle_id'],
                'status': re['status'],
                'image_logo': re['image_logo'],
                'name': re['vehicle_name'],
                'sos_status': re['sos_status'],
                'license_plate': re['license_plate'],
                'color': re['color'],
                'model_year': re['model_year'],
                'fuel_type': re['fuel_type'],
                'body_length': re['body_length'],
                'body_width': re['body_width'],
                'fleet_type_name': re['fleet_type_name'],
                'height': re['height'],
                'vehicle_type': re['vehicle_type'],
                'engine_size': re['engine_size'],
                'uniqueid': re['uniqueid'],
                'iot_type': re['iot_type'],
                'parking_point': parking_point

            }
            self.env.cr.execute(sql_list_image_vehicle, (vehicle['id'],))
            result = self._cr.fetchall()
            list_imgae_vehicle = []
            for image in result:
                list_imgae_vehicle.append(image[0])
            vehicle.update({'list_image': list_imgae_vehicle})

        self.env.cr.execute("""
            SELECT json_agg(t)
                FROM (SELECT
                fd.id,fd.driver_code,fd.name,fd.display_name,fd.full_name,
                fd.address,fd.point,fd.trip_number,fd.gender,
                fd.phone,fd.tz,fd.lang,fd.nationality,
                fd.user_driver,fd.ssn, TO_CHAR(fd.birth_date,'YYYY-MM-DD HH24:MI:SS') birth_date,
                TO_CHAR(fd.hire_date,'YYYY-MM-DD HH24:MI:SS') hire_date, 
                TO_CHAR(fd.leave_date,'YYYY-MM-DD HH24:MI:SS') leave_date,
                cld.name class_driver, TO_CHAR(fd.expires_date,'YYYY-MM-DD HH24:MI:SS') expires_date,fd.no,
                TO_CHAR(fd.driver_license_date,'YYYY-MM-DD HH24:MI:SS') driver_license_date,
                rp.id as parent_id,rp.name as parent_name,
                rc.id as company_id , rc.name as company_name, rc.vat,rc.street,rc.phone as company_phone,
                sta.id as award_id , sta.name as award_name ,
                rcs.name as state_name,
                rco.name as country_name,management.name fleet_management_name,
                ir.uri_path
                   	FROM fleet_driver fd
                   	    LEFT JOIN partner_driver log_driver on fd.id = log_driver.driver_id
                   	    LEFT JOIN fleet_management management on fd.fleet_management_id = management.id
                        LEFT JOIN res_partner rp on log_driver.partner_id = rp.id and log_driver.to_date is null
                        LEFT JOIN res_company rc on fd.company_id = rc.id
                        LEFT JOIN ir_attachment ir on fd.id = ir.res_id
                        LEFT JOIN sharevan_title_award sta  on fd.award_id = sta.id
                        LEFT JOIN res_country_state rcs  on rcs.id = rc.state_id
                        LEFT JOIN res_country rco on   rc.country_id = rco.id
                        JOIN sharevan_driver_license cld on cld.id = fd.class_driver
                    WHERE  fd.id = %s and ir.res_model = %s and ir.res_field = 'image_1920'
    				LIMIT 1
    				) t ;""", (driver_id, MODEL_FLEET_DRIVER))
        result = self._cr.fetchall()

        if result[0][0]:
            re = result[0][0][0]
            average_rating = 0
            if re['point'] and re['trip_number']:
                average_rating = round(re['point'] / re['trip_number'], 2)
            content = {
                'id': re['id'],
                'driver_code': re['driver_code'],
                'name': re['name'],
                'image_1920': re['uri_path'],
                'display_name': re['display_name'],
                'full_name': re['full_name'],
                'address': re['address'],
                'phone': re['phone'],
                'gender': re['gender'],
                'average_rating': average_rating,
                'point': re['point'],
                'trip_number': re['trip_number'],
                'tz': re['tz'],
                'lang': re['lang'],
                'nationality': re['nationality'],
                'user_driver': re['user_driver'],
                'ssn': re['ssn'],
                'birth_date': re['birth_date'],
                'fleet_management_name': re['fleet_management_name'],
                'hire_date': re['hire_date'],
                'leave_date': re['leave_date'],
                'class_driver': re['class_driver'],
                'expires_date': re['expires_date'],
                'no': re['no'],
                'driver_license_date': re['driver_license_date'],
                'vehicle': vehicle,
                'assignation_log': assignation_log,
                'parent_id': re['parent_id'],
                'parent_name': re['parent_name'],
                'company': {
                    'id': re['company_id'],
                    'name': re['company_name'],
                    'tax_id': re['vat'],
                    'phone': re['company_phone'],
                    'address': re['street']
                },

            }
            records = {
                'records': [content, ]
            }
            simplejson.dumps(records, indent=4, sort_keys=True, default=str)
            return records
        return {
            'records': []
        }

    def check_driver_assign_log_confirm_receive_allow(self, assignation_log_id):
        self.env.cr.execute("""
            select log_all.assignation_log_code, log_all.date_start,log_all.date_end, driver.name from fleet_vehicle_assignation_log log_all
                join (select * from fleet_vehicle_assignation_log where id = %s) now_log
                    on now_log.vehicle_id = log_all.vehicle_id
                join fleet_driver driver on driver.id = log_all.driver_id 
            where log_all.driver_status ='1' and log_all.give_car_back is  null 
                and log_all.id != %s and log_all.date_start < CURRENT_DATE +1 
                """, (str(assignation_log_id),str(assignation_log_id),))
        result = self._cr.dictfetchall()
        if result:
            message = "Please finish driver calendar code: "
            for rec in result:
                message += rec['assignation_log_code'] + " ( Driver: " + \
                    rec['name'] + ", start date: " + str(rec['date_start']) + ", end date: " + str(rec['date_end'])+ ")"
            print(message)
            logger.warn(
                message,
                FleetDriver._name, assignation_log_id,
                exc_info=True)
            return {
                'status':1001,
                'message': message
            }
        else:
            return {
                'status': 200,
                'message': ''
            }


    def get_rating(self, user_id):
        self.env.cr.execute("""
                SELECT num_rating rating, count(*) count
                FROM sharevan_rating sr
                left join fleet_driver fd on sr.driver_id = fd.id
                WHERE fd.user_id = 2
                GROUP BY num_rating ORDER BY num_rating asc
        """, (user_id,))
        result = self._cr.fetchall()
        jsonRe = []
        for res in result:
            content = {
                "num_rating": res[0],
                "count": res[1]
            }
            jsonRe.append(content)
        records = {
            'length': len(result),
            'records': jsonRe
        }
        simplejson.dumps(records, indent=4, sort_keys=True, default=str)
        return records

    def get_profile(self, driver_id):
        uid = http.request.session['uid']
        driver = self.env['fleet.driver'].search([('user_id', '=', uid)])
        if driver.id == False:
            raise ValidationError(_('Driver not exits !'))
        self.env.cr.execute("""
                   SELECT json_agg(t)
                       FROM (SELECT sta.id,sta.name,sta.from_point,sta.to_point,ir.uri_path as icon
                             FROM sharevan_title_award sta
                             LEFT JOIN ir_attachment ir on sta.id = ir.res_id
                             WHERE sta.status = 'running' and ir.res_model = 'sharevan.title.award' and title_award_type = 'driver'
                             ORDER BY sta.from_point ASC
           				) t ;""")
        result_1 = self._cr.fetchall()
        title_award_name = None
        if result_1[0][0]:
            re = result_1[0][0]
            for rating in re:
                if driver['point'] >= rating['from_point'] and driver['point'] < rating['to_point'] :
                    title_award_name = rating['name']
        array = [5, 4, 3, 2, 1]
        list_start = []
        for start in array:
            start_1 = self.env['sharevan.rating'].search([('driver_id', '=', driver['id']), ('num_rating', '=', start)])
            list_start.append(len(start_1))

        self.env.cr.execute("""
            SELECT json_agg(t)
                FROM (SELECT stb.id,stb.name ,stb.description, ir.uri_path as icon
                    FROM sharevan_rating_badges stb
                    LEFT JOIN ir_attachment ir on stb.id = ir.res_id
                    Where stb.status = 'running' and ir.res_model = 'sharevan.rating.badges' and stb.type = 'DRIVER'
                  				) t ;""")
        result_2 = self._cr.fetchall()
        re1 = []

        self.env.cr.execute("""
                        SELECT rel.sharevan_rating_badges_id, COALESCE(count(id),0) FROM public.sharevan_rating_sharevan_rating_badges_rel rel
                        join sharevan_rating rating on rating.id = rel.sharevan_rating_id
                        where rating.driver_id = %s 
                        Group by rel.sharevan_rating_badges_id
                          				 ;""", (driver['id'],))
        result_count_rating_badges = self._cr.fetchall()

        if result_2[0][0] != None:
            re1 = result_2[0][0]
            start = 0
            for rea in re1:
                if len(result_count_rating_badges) > 0:
                    for x in range(start, len(result_count_rating_badges)):
                        if result_count_rating_badges[x][0] == rea['id']:
                            start += 1
                            rea.update({'len': result_count_rating_badges[x][1]})
                            break
                        else:
                            rea.update({'len': 0})
                else:
                    for rea in re1:
                        rea.update({'len': 0})
        content = {
            'current_award_name':title_award_name,
            'title_award': re,
            'num_rating': list_start,
            'badges': re1

        }

        records = {
            'records': [content, ]
        }
        simplejson.dumps(records, indent=4, sort_keys=True, default=str)
        return records

    def getInforVehicle(self, assignation_log_id):
        sql_list_image_vehicle = """
            SELECT ir.uri_path as image
                FROM fleet_vehicle fv
            LEFT JOIN ir_attachment ir on fv.id = ir.res_id 
                and ir.res_model='fleet.vehicle'
            WHERE  fv.id = %s
          """
        self.env.cr.execute("""
           SELECT json_agg(t)
               FROM (
                     SELECT vh.id ,vh.name , vh.license_plate ,vh.vin_sn ,vh.fuel_type , vh.color ,vh.model_year , vh.doors ,
                     vh.doors ,vh.transmission ,vh.fuel_type , vh.vehicle_inspection ,vh.sos_status,
                     TO_CHAR(vh.inspection_due_date,'YYYY-MM-DD HH24:MI:SS') inspection_due_date ,
                     TO_CHAR(vh.acquisition_date,'YYYY-MM-DD HH24:MI:SS') acquisition_date , vh.available_capacity,
                     vh.capacity,vh.axle,vh.body_length,vh.body_width,vh.height,
                     rc.name as company_name,
                     vhm.name as model_name , park.name parking_name , park.address parking_address, park.phone_number phone_number,
                     vhmb.name as brand_name, state.name status,park.latitude,park.longitude
                     FROM fleet_vehicle vh
                     join fleet_vehicle_assignation_log log on log.vehicle_id = vh.id
                     left join parking_point park on park.id = vh.parking_point_id
                     join fleet_vehicle_state state on vh.state_id = state.id
                     LEFT JOIN res_company rc on rc.id = vh.company_id
                     LEFT JOIN fleet_vehicle_model vhm on vh.model_id = vhm.id
                     LEFT JOIN fleet_vehicle_model_brand vhmb on vhm.brand_id = vhmb.id
                     WHERE log.id = %s and vh.active = True
             				) t ;""", (assignation_log_id,))
        result = self._cr.fetchall()
        if result[0][0]:
            re = result[0][0][0]
            self.env.cr.execute(sql_list_image_vehicle, (re['id'],))
            result = self._cr.fetchall()
            list_image_vehicle = []
            for image in result:
                list_image_vehicle.append(image[0])
            # list_image = sql_imgae[0]
            re.update({'list_image': list_image_vehicle})

            content = {
                "id": re['id'],
                "name": re['name'],
                "license_plate": re['license_plate'],
                "vin_sn": re['vin_sn'],
                "fuel_type": re['fuel_type'],
                "color": re['color'],
                "model_year": re['model_year'],
                "sos_status": re['sos_status'],
                "doors": re['doors'],
                "transmission": re['transmission'],
                "vehicle_inspection": re['vehicle_inspection'],
                "inspection_due_date": re['inspection_due_date'],
                "acquisition_date": re['acquisition_date'],
                "available_capacity": re['available_capacity'],
                "capacity": re['capacity'],
                "axle": re['axle'],
                "body_length": re['body_length'],
                "body_width": re['body_width'],
                "height": re['height'],
                "company_name": re['company_name'],
                "model_name": re['model_name'],
                "brand_name": re['brand_name'],
                "status": re['status'],
                "list_image": list_image_vehicle,
                "parking_point": {
                    "name": re['parking_name'],
                    "phone": re['phone_number'],
                    "address": re['parking_address'],
                    "latitude": re['latitude'],
                    "longitude": re['longitude']
                }
            }

        else:
            raise ValidationError(_('Vehicle not exits !'))
        equipments = []
        if content['status'] == VehicleStateStatus.SHIPPING.value:
            query = """
                SELECT json_agg(t)
                    from
                    (select log.id, part.name,part.equipment_part_code,unit_measure,
                        part.description, uri_path ,true as isSelect ,
                        log.quantity_take, log.quantity_return
                        from  fleet_driver_equipment_log log
                    left join fleet_driver_equipment_part part on part.id =log.equipment_id
                    left join ir_attachment ir on ir.res_id = part.id and ir.res_model = 'fleet.driver.equipment.part'
                        where part.status = 'running' and log.assignation_log_id =%s ) t
                        """
        elif content['status'] == VehicleStateStatus.CONFIRMTAKE.value or content[
            'status'] == VehicleStateStatus.CONFIRMRETURN.value:
            query = """
                SELECT json_agg(t)
                    from
                    (select log.id, part.name,part.equipment_part_code,unit_measure,
                        part.description, uri_path ,false as isSelect ,
                        log.quantity_take, log.quantity_return
                        from  fleet_driver_equipment_log log
                    left join fleet_driver_equipment_part part on part.id =log.equipment_id
                    left join ir_attachment ir on ir.res_id = part.id and ir.res_model = 'fleet.driver.equipment.part'
                        where part.status = 'running' and log.assignation_log_id =%s ) t
                        """
        else:
            query = """
                SELECT json_agg(t)
                    from
                    (select part.id, part.name,part.equipment_part_code,unit_measure,part.description,
                        uri_path ,false as isSelect
                        from  fleet_driver_equipment_part part
                    left join ir_attachment ir on ir.res_id = part.id and ir.res_model = 'fleet.driver.equipment.part'
                        where part.status = 'running') t
                                    """
        self.env.cr.execute(query, (assignation_log_id,))
        result = self._cr.fetchall()
        if result[0]:
            if result[0][0]:
                equipments = result[0][0]
        content['equipments'] = equipments
        records = {
            'records': [content, ]
        }
        simplejson.dumps(records, indent=4, sort_keys=True, default=str)
        return records

    def editInfoDriver(self, driverInfo):
        id = driverInfo['driver_id']
        checkString = isinstance(id, str)
        if checkString is True:
            raise ValidationError('Driver Id must Integer!')

        info_driver = self.env['fleet.driver'].search([('id', '=', id)])
        if info_driver:
            if info_driver['driver_type']=='fleet':
                info_driver.write({
                    'name': driverInfo['name'],
                    'address': driverInfo['address'],
                    'phone': driverInfo['phone']
                })
                return {
                    'id': info_driver.id
                }
            else:
                raise ValidationError('You not alow to update information')
        else:
            raise ValidationError('Error update!')

    def receive_return_vehicle(self, driverInfo, files):
        driverInforJson = json.loads(driverInfo)
        vehicle_id = driverInforJson['vehicle_id']
        driver_id = driverInforJson['driver_id']
        status = driverInforJson['status']
        assignation_log_id = driverInforJson['assignation_log_id']
        lat = driverInforJson['latitude']
        long = driverInforJson['longitude']
        description = driverInforJson['description']
        response_data = {}
        if isinstance(vehicle_id, str) or isinstance(driver_id, str) or isinstance(assignation_log_id, str):
            response_data = {
                'status': 204,
                'message': 'Vehicle_id and driver_id and assignation_log_id must Integer !'
            }
            return Response(json.dumps(response_data), content_type="application/json", status=200)
        if isinstance(status, int):
            response_data = {
                'status': 204,
                'message': 'Status must Str !'
            }
            return Response(json.dumps(response_data), content_type="application/json", status=200)
        query = """
            SELECT json_agg(t)
                from
                (SELECT veh_log.id,veh_log.vehicle_id, driver.user_id,driver.name as driver_name, veh_log.driver_id,
                        TO_CHAR(veh_log.date_start,'YYYY-MM-DD HH24:MI:SS') date_start,
                        TO_CHAR(veh_log.date_end,'YYYY-MM-DD HH24:MI:SS') date_end,
                        veh_log.receive_car, veh_log.give_car_back,log_status.id vehicle_status_id ,
                        park.latitude,park.longitude,stat.name state_name,
                        veh.name as vehicle_name
                FROM public.fleet_vehicle_assignation_log veh_log
                    join fleet_vehicle_status log_status  on veh_log.id = log_status.assignation_log_id
                    join fleet_vehicle veh on  veh_log.vehicle_id = veh.id
                    join fleet_driver driver on driver.id = veh_log.driver_id
                    left join parking_point park on park.id = veh.parking_point_id
                    join fleet_vehicle_state stat on stat.id = veh.state_id
                where veh_log.driver_id = %s and veh_log.vehicle_id = %s and veh_log.id = %s
                    and driver.user_id = %s)t ;
        """
        self.env.cr.execute(query, (driver_id, vehicle_id, assignation_log_id, http.request.env.uid,))
        records = self._cr.fetchall()
        record = False
        if records[0]:
            if records[0][0]:
                if records[0][0][0]:
                    record = records[0][0][0]
        if record == False:
            response_data = {
                'status': 204,
                'message': 'Driver not assign for vehicle today !'
            }
            return Response(json.dumps(response_data), content_type="application/json", status=200)
        vehicle_id = vehicle_id
        vehicle_name = record['vehicle_name']
        driver_name = record['driver_name']
        date_start = record['date_start']
        date_end = record['date_end']
        vehicle_status = record['vehicle_status_id']
        confirm_id = None
        distance_check = http.request.env['ir.config_parameter'].sudo().get_param('distance.mobile.check.point.key')
        check = 0
        notice = ""
        if distance_check:
            check = int(distance_check)
        else:
            check = 500
        if record['latitude'] and record['longitude']:
            distance = DataSet.get_distance(self, lat, long, record['latitude'], record['longitude'])
            if distance > check:
                response_data = {
                    'status': 204,
                    'message': 'Your distance is too far, from the parking spot !'
                }
                return Response(json.dumps(response_data), content_type="application/json", status=200)
        else:
            response_data = {
                'status': 204,
                'message': 'Vehicle have no parking point! Please call the admin for submit car !'
            }
            return Response(json.dumps(response_data), content_type="application/json", status=200)

        if status == 'ConfirmTake':
            check_result = self.check_driver_assign_log_confirm_receive_allow(assignation_log_id)
            if check_result['status'] != 200:
                response_data = check_result
                return Response(json.dumps(response_data), content_type="application/json", status=200)
            if record['receive_car']:
                response_data = {
                    'status': 204,
                    'message': 'Your got the car !'
                }
                return Response(json.dumps(response_data), content_type="application/json", status=200)
            if record['state_name'] != 'Ordered':
                response_data = {
                    'status': 204,
                    'message': 'Error receive the car !'
                }
                return Response(json.dumps(response_data), content_type="application/json", status=200)

            record_status = self.env['fleet.vehicle.status'].search([('assignation_log_id', '=', assignation_log_id)])
            confirm_id = record_status['id']
            time_now = datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")
            self.env.cr.execute(""" 
                UPDATE public.fleet_vehicle_status
                SET status= 'running', delivery_receipt_vehicles = 'Confirm vehicle handing', description= %s, date_driver_receives = %s 
                WHERE id = %s;  
                                """, (description, time_now, confirm_id,))
            state = self.env['fleet.vehicle.state'].search([('name', '=', VehicleStateStatus.CONFIRMTAKE.value)])
            vehicle = self.env['fleet.vehicle'].search([('id', '=', vehicle_id)])
            check = vehicle.write({
                'state_id': state['id']

            })

            if check:
                equipment_lst = driverInforJson['equipments']
                for equipment in equipment_lst:
                    val = {
                        'equipment_id': equipment['id'],
                        'assignation_log_id': equipment['assignation_log_id'],
                        'quantity_take': equipment['quantity_take']
                    }
                    rec = http.request.env[VehicleEquipmentDriver._name].create(val)

                list_manager = BaseMethod.get_fleet_manager(driver_id)

                http.request.env['sharevan.notification'].create({
                    'user_id':  list_manager,
                    'title': 'Nhận trả xe',
                    'content': 'Xác nhận lấy xe cho lái xe %s' % (vehicle_name),
                    'res_id': confirm_id,
                    'res_model': 'fleet.vehicle.status',
                    'click_action': ClickActionType.routing_plan_day_driver.value,
                    'message_type': MessageType.danger.value,
                    'type': NotificationType.RoutingMessage.value,
                    'object_status': RoutingDetailStatus.Unconfimred.value,
                    'item_id': '2'
                })
                for manager in list_manager:
                    # web notification
                    notice += "Request confirmation to pick up the car from " + driver_name + " driver"
                    users = http.request.env['res.users'].search(
                        [('id', '=', manager)])
                    if users:
                        users.notify_info(message=notice, title=NotificationSocketType.NOTIFICATION.value)
                response_data = {
                    'status': 200,
                    'message': 'Successful to receive a vehicle !'
                }
                return Response(json.dumps(response_data), content_type="application/json", status=200)
            else:
                response_data = {
                    'status': 204,
                    'message': 'can not update car state !'
                }
                return Response(json.dumps(response_data), content_type="application/json", status=200)

        if status == 'ConfirmReturn':
            query = """
                select * from sharevan_routing_plan_day
                    where status  not in ( '-1','2','3') and vehicle_id = %s and driver_id = %s
                        and ( date_plan = %s or date_plan < %s)
            """
            date_start = datetime.strptime(record['date_start'], "%Y-%m-%d %H:%M:%S").date()
            date_end = datetime.strptime(record['date_end'], "%Y-%m-%d %H:%M:%S").date()
            # date_start_str = date_start.strftime("%Y-%m-%d %H:%M:%S")

            self.env.cr.execute(query, (vehicle_id, driver_id, date_start, date_end,))

            check_routing_finish = self._cr.dictfetchall()
            if check_routing_finish:
                response_data = {
                    'status': 205,
                    'message': 'You have to finish routing to return car'
                }
                return Response(json.dumps(response_data), content_type="application/json", status=200)

            record_status = self.env['fleet.vehicle.status'].search([('assignation_log_id', '=', assignation_log_id)])

            if record['give_car_back']:
                response_data = {
                    'status': 204,
                    'message': 'You have returned the car !'
                }
                return Response(json.dumps(response_data), content_type="application/json", status=200)
            # status = self.env['fleet.vehicle'].search([('id', '=', record['state_id'])])
            if record['state_name'] != 'Shipping':
                response_data = {
                    'status': 204,
                    'message': 'Error receive the car !'
                }
                return Response(json.dumps(response_data), content_type="application/json", status=200)
            for file in files:
                if file.filename:
                    val = {
                        'res_model': 'fleet.vehicle.status',
                        'mimetype': file.mimetype,
                        'name': file.filename,
                        'type': 'binary',
                        'datas': base64.b64encode(file.read())
                    }
                    rec = http.request.env[IrAttachment._name].create(val)
                    rec.write({'uri_path': rec['store_fname']})
                    INSERT_QUERY = """INSERT INTO fleet_vehicle_status_ir_attachment_rel
                                           VALUES ( %s , %s ) """
                    http.request.cr.execute(INSERT_QUERY, (vehicle_status, rec['id'],))

            confirm_id = record_status['id']
            time_now = datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")
            self.env.cr.execute(""" 
                                    UPDATE public.fleet_vehicle_status
                                    SET status= 'running', delivery_receipt_vehicles = 'Confirm receive the car', description= %s, date_driver_returns = %s 
                                    WHERE id = %s;  
                                            """, (description, time_now, confirm_id,))
            state = self.env['fleet.vehicle.state'].search([('name', '=', VehicleStateStatus.CONFIRMRETURN.value)])
            check = http.request.env['fleet.vehicle']. \
                browse(vehicle_id).write({'state_id': state['id']})
            equipment_lst = driverInforJson['equipments']
            if check:
                for equipment in equipment_lst:
                    state = self.env[VehicleEquipmentDriver._name].search([('id', '=', equipment['id'])])
                    state.write({'quantity_return': equipment['quantity_return']})
                list_manager = BaseMethod.get_fleet_manager(driver_id)

                http.request.env['sharevan.notification'].create({
                    'user_id': list_manager,
                    'title': 'Nhận trả xe',
                    'content': 'Xác nhận trả xe cho xe %s' % (vehicle_name),
                    'res_id': confirm_id,
                    'res_model': 'fleet.vehicle.status',
                    'click_action': ClickActionType.routing_plan_day_driver.value,
                    'message_type': MessageType.danger.value,
                    'type': NotificationType.RoutingMessage.value,
                    'object_status': RoutingDetailStatus.Unconfimred.value,
                    'item_id': 2
                })
                for manager in list_manager:
                    notice += "Request confirmation of return car from " + driver_name + " driver"
                    users = http.request.env['res.users'].search(
                        [('id', '=', manager)])
                    if users:
                        users.notify_info(message=notice, title=NotificationSocketType.NOTIFICATION.value)
                response_data = {
                    'status': 200,
                    'message': 'Successful to return a vehicle !'
                }
                return Response(json.dumps(response_data), content_type="application/json", status=200)
            else:
                response_data = {
                    'status': 204,
                    'message': 'Can not update vehicle state !'
                }
                return Response(json.dumps(response_data), content_type="application/json", status=200)

    def history_vehicle(self, date):
        uid = http.request.env.uid
        driver = self.env['fleet.driver'].search([('user_id', '=', uid)])

        date += " 00:00:00"
        date_start = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        date_end = date_start + timedelta(hours=24)

        sql = """
            SELECT json_agg(t)
                FROM ( Select Distinct  vehlog.id as vehlog_id , vehlog.assignation_log_code ,
                        TO_CHAR(vehlog.date_start,'YYYY-MM-DD HH24:MI:SS') date_start,
                        TO_CHAR(vehlog.date_end,'YYYY-MM-DD HH24:MI:SS') date_end,
                        TO_CHAR(vehlog.receive_car,'YYYY-MM-DD HH24:MI:SS') receive_car,
                        TO_CHAR(vehlog.give_car_back,'YYYY-MM-DD HH24:MI:SS') give_car_back,
                        pk.id as parking_point_id,pk.name as parking_point_name, pk.address as parking_point_address,
                        pk.phone_number,pk.latitude,pk.longitude,
                        pk.street,pk.city_name,
                        veh.id as vehicle_id , veh.name as vehicle_name , veh.license_plate,veh.color,veh.model_year,veh.fuel_type,
                        veh.body_length,veh.body_width,veh.height,veh_type.name vehicle_type,veh.engine_size,
                        rc.name as country_name,
                        vs.name as status ,vehlog.id assignation_id
                    FROM fleet_vehicle_assignation_log vehlog
                    JOIN fleet_vehicle veh on vehlog.vehicle_id = veh.id
                    JOIN fleet_vehicle_state vs on veh.state_id = vs.id
                    JOIN parking_point pk on veh.parking_point_id = pk.id
                    JOIN res_country rc on pk.country_id = rc.id
                    JOIN fleet_vehicle_model fvm on fvm.id = veh.model_id
                    JOIN fleet_vehicle_model_brand fvmb on fvmb.id = fvm.brand_id
                    left JOIN fleet_vehicle_type veh_type on veh.vehicle_type = veh_type.id
                    Where vehlog.date_start::timestamp >= %s and date_start::timestamp < %s and vehlog.driver_id = %s
            ) t ;"""
        self.env.cr.execute(sql, (date_start, date_end, driver['id']))
        result = self._cr.fetchall()
        list_calandar = []

        if result[0][0]:
            for re in result[0][0]:
                calandar = {}
                sql_list_image_vehicle = """
                     SELECT ir.uri_path as image
                        FROM fleet_vehicle fv
                    LEFT JOIN ir_attachment ir on fv.id = ir.res_id 
                        and ir.res_model='fleet.vehicle'
                    WHERE  fv.id = %s
                """

                self.env.cr.execute(sql_list_image_vehicle, (re['vehicle_id'],))
                result = self._cr.fetchall()
                list_imgae_vehicle = []
                for image in result:
                    list_imgae_vehicle.append(image[0])
                assignation_log = {
                    'id': re['assignation_id'],
                    'assignation_log_code': re['assignation_log_code'],
                    'date_start': re['date_start'],
                    'date_end': re['date_end'],
                    'receive_car': re['receive_car'],
                    'give_car_back': re['give_car_back']
                }
                calandar.update({'assignation_log': assignation_log})
                parking_point = {
                    'id': re['parking_point_id'],
                    'name': re['parking_point_name'],
                    'address': re['parking_point_address'],
                    'phone': re['phone_number'],
                    'latitude': re['latitude'],
                    'longitude': re['longitude']
                }

                vehicle = {
                    'id': re['vehicle_id'],
                    'status': re['status'],
                    'name': re['vehicle_name'],
                    'license_plate': re['license_plate'],
                    'color': re['color'],
                    'model_year': re['model_year'],
                    'fuel_type': re['fuel_type'],
                    'body_length': re['body_length'],
                    'body_width': re['body_width'],
                    'height': re['height'],
                    'vehicle_type': re['vehicle_type'],
                    'engine_size': re['engine_size'],
                    'parking_point': parking_point,
                    'list_image': list_imgae_vehicle

                }
                calandar.update({'vehicle': vehicle})
                list_calandar.append(calandar)

        content = list_calandar

        records = {
            'records': content
        }
        simplejson.dumps(records, indent=4, sort_keys=True, default=str)
        return records

    def search_driver(self, **kwargs):
        company_id = http.request.env.companies.ids
        keyword = None
        status = 0
        offset = 0
        limit = 10
        exclude_ids = []
        for arg in kwargs:
            if arg == 'status':
                status = kwargs.get(arg)
                continue
            if arg == 'limit' and kwargs.get(arg) > 0:
                limit = kwargs.get(arg)
                continue
            if arg == 'offset':
                offset = kwargs.get(arg)
                continue
            if arg == 'txt_search':
                keyword = kwargs.get(arg)
                keyword = re.sub('[^A-Za-z0-9]+', '', keyword)
                continue
            if arg == 'exclude_ids':
                exclude_ids = kwargs.get(arg)
                continue

        condition = ""
        params = []
        params.extend(company_id)
        if keyword and len(keyword) > 0:
            params.append(keyword + '%')
            condition += " AND LOWER(fd.full_name) like LOWER(%s) "
        else:
            return []
        if len(exclude_ids) > 0:
            params.extend(exclude_ids)
            format_ids = ','.join(['%s'] * len(exclude_ids))
            condition += " AND fd.id not in (%s) " % format_ids

        format_strings = ','.join(['%s'] * len(company_id))
        query = """
            SELECT id, name, display_name, full_name, email, phone, status FROM fleet_driver fd
            WHERE fd.company_id in (%s)
        """ % format_strings
        query += condition
        self.env.cr.execute(query, tuple(params))
        result = self._cr.dictfetchall()
        return result

    # def send_notification_drivers(self, driver_ids, title, body):
    #     if not isinstance(driver_ids, list):
    #         raise ValidationError("Driver ids invalid")
    #     driver = self.search(args=[('id', 'in', driver_ids)])
    #     if not title or not body:
    #         raise ValidationError('Body and content invalid')
    #     list_ids = []
    #     for dv in driver:
    #         list_ids.append(dv.user_id.id)
    #     val = {
    #         'type': 'system',
    #         'user_id': [[6, False, list_ids]],
    #         'title': title,
    #         'content': body,
    #         'click_action': ClickActionType.share_van_inbox_driver.value,
    #         'click_action_type': ClickActionType.share_van_inbox_driver.value
    #     }
    #     noti = http.request.env['sharevan.notification'].create(val)
    #     if noti:
    #         return noti.copy_data()[0]

    def send_notification_drivers(self, driver_ids, title, body):
        query = """
                select user_id from fleet_driver driver
                    where driver.id ::integer in (
            """
        for driver in driver_ids:
            query += str(driver) + ","
        query = query[:-1]
        query += ")"
        self.env.cr.execute(query, ())
        list_user = self._cr.dictfetchall()
        ids = []
        for user in list_user:
            ids.append(user['user_id'])
        item_id = ''
        try:
            objct_val = {
                "title": title,
                "name": title,
                "content": body,
                "create_date": datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S"),
                "type": 'routing',
                "image_256": '',
                "object_status": RoutingDetailStatus.Unconfimred.value,
                "click_action": ClickActionType.driver_main_activity.value,
                "message_type": MessageType.success.value,
                "item_id": item_id,
                "is_read": False
            }
            objct_val = json.dumps(objct_val)
            click_action = ClickActionType.notification_driver.value
            message_type = MessageType.success.value
            item_id = ''
            INSERT_NOTIFICATION_QUERY = """INSERT INTO public.sharevan_notification( title, content, sent_date, type, 
                object_status, click_action, message_type, item_id, create_uid, create_date,status) VALUES ( 
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s) RETURNING id """
            sent_date = datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d %H:%M:%S")
            http.request.cr.execute(INSERT_NOTIFICATION_QUERY, (
                title, body, sent_date, 'routing', RoutingDetailStatus.Unconfimred.value,
                ClickActionType.driver_main_activity.value, MessageType.success.value, '', 1, sent_date, 'status',))
            result = http.request.env[Notification._name]._cr.dictfetchall()
            if result:
                for rec in ids:
                    INSERT_NOTIFICATION_REL_QUERY = """
                            INSERT INTO public.sharevan_notification_user_rel(
                                notification_id, user_id, is_read)
                                VALUES (%s, %s, %s) RETURNING id 
                        """
                    http.request.cr.execute(INSERT_NOTIFICATION_REL_QUERY, (result, rec, False,))
            FirebaseMessagingAPI. \
                send_message_for_all_normal(ids=ids, title=title, body=str(objct_val), short_body=body,
                                            item_id=item_id,
                                            click_action=click_action, message_type=message_type)
            return 200
        except:
            logger.warn(
                "Not send message",
                FleetDriver._name, item_id,
                exc_info=True)
            return 500


class FleetDriverResPartnerRel(models.Model):
    _name = Constants.PARTNER_DRIVER
    _inherit = Constants.PARTNER_DRIVER
    _description = 'res_partner fleet_driver'
