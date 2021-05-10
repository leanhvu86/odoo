import base64
import json
import json as simplejson
import logging
import re as reg

from werkzeug import Response

from mymodule.base_next.models.bidding import BiddingOrder
from odoo import models, http, fields, _
from odoo.addons.base.models.ir_attachment import IrAttachment
from odoo.addons.base.models.res_users import Users
from odoo.exceptions import ValidationError
from mymodule.constants import Constants
from mymodule.enum.BiddingStatus import BiddingStatus
from mymodule.enum.BiddingStatusType import BiddingStatusType

logger = logging.getLogger(__name__)


class BiddingVehicle(models.Model):
    _name = 'sharevan.bidding.vehicle'
    _description = 'Bidding vehicle'
    _inherit = 'sharevan.bidding.vehicle'

    def confirm_bidding_vehicle(self, bidding_order_id, bidding_vehicle_id):
        if bidding_order_id:
            if bidding_vehicle_id:
                record_bidding_order = http.request.env[BiddingOrder._name]. \
                    web_search_read([['id', '=', bidding_order_id]], fields=None,
                                    offset=0, limit=10, order='')
                if record_bidding_order['records']:
                    if record_bidding_order['records'][0]:
                        record_bidding_vehicle = http.request.env[BiddingVehicle._name]. \
                            web_search_read([['id', '=', bidding_vehicle_id]], fields=None,
                                            offset=0, limit=10, order='')
                        if record_bidding_vehicle['records']:
                            if record_bidding_vehicle['records'][0]:
                                http.request.env[BiddingOrder._name]. \
                                    browse(record_bidding_order['records'][0]['id']).write(
                                    {'type': '2', 'driver_name': record_bidding_vehicle['records'][0]['driver_name'],
                                     'phone': record_bidding_vehicle['records'][0]['driver_phone_number']})
                                return True
                        else:
                            raise ValidationError(_('Bidding vehicle not existed!'))

                else:
                    raise ValidationError(_('Bidding order not existed!'))

            else:
                raise ValidationError(_('Bidding vehicle id can not null!'))

        else:
            raise ValidationError(_('Bidding order id can not null!'))
        return False

    def get_list_bidding_vehicle(self, uID):
        user = self.env['res.users'].search([('id', '=', self.env.uid)])
        if user:
            str = """ SELECT json_agg(t)
                                         FROM (
                                    SELECT sbv.id, sbv.code, sbv.res_user_id, sbv.lisence_plate, sbv.driver_phone_number,
                                         sbv.driver_name, TO_CHAR(sbv.expiry_time, 'YYYY-MM-DD HH24:MI:SS'),
                                          sbv.company_id, sbv.status, sbv.description, 
                                          ia.store_fname,sbv.create_uid, TO_CHAR(sbv.create_date, 'YYYY-MM-DD HH24:MI:SS') ,
                                          sbv.write_uid,TO_CHAR(sbv.write_date, 'YYYY-MM-DD HH24:MI:SS'),
                                           sbv.id_card, sbv.name_seq_self_sharevan_bidding_vehicle, 
                                           sbv.res_partner_id, sbv.tonnage, sbv.vehicle_type
	                                    FROM public.sharevan_bidding_vehicle sbv 
	                                    join public.ir_attachment ia on sbv.id = ia.res_id and ia.res_model = 'sharevan.bidding.vehicle' 
	                                     where sbv.company_id = %s and ia.res_field = 'image_128'
                                        ) t  """
            self.env.cr.execute(str,
                                (user.company_id.id,))

            jsonRe = []
            result = self._cr.fetchall()
            if result[0]:
                if result[0][0]:
                    re = result[0][0]
                    records = {
                        'length': len(re),
                        'records': re
                    }
                    simplejson.dumps(records, indent=4, sort_keys=True, default=str)
                    return records
        else:
            raise ValidationError("user not exitsed")
        return {
            'records': []
        }

    def get_lst_vehicle(self, text_search, status, offset, limit):
        User = self.env['res.users'].search([('id', '=', self.env.uid)])
        offset_check = 0
        limit_check = 10
        params = []
        if User:
            query = """
                  SELECT json_agg(t) FROM (
                   select sbv.id as id ,sbv.lisence_plate as lisencePlate, sbv.driver_name as driverName, 
                    sbv.driver_phone_number as driverPhone,sbv.id_card as idCard,
                    ia.store_fname as image,sbv.tonnage as tonnage,
                    al.latitude as latitude, al.longitude as longitude,
                    STRING_AGG(sbo.bidding_order_number, ',' ORDER BY sbo.bidding_order_number) AS bidding,
                    case when (select count(sbo.id) from public.sharevan_bidding_order sbo
                    where sbo.bidding_vehicle_id = sbv.id and sbo.type IN ('1','2')
                    and sbo.status IN ('0','1')) = 0 then 0 else 1 end as is_bidding
                    from public.sharevan_bidding_vehicle sbv join public.res_users ru on sbv.res_user_id = ru.id
                    left join public.ir_attachment ia on sbv.id = ia.res_id and ia.res_model = 'sharevan.bidding.vehicle'
                    left join (select * from public.sharevan_bidding_order sb where sb.type in ('1','2')
                    and sb.status IN ('0','1')) sbo on sbv.id = sbo.bidding_vehicle_id
                    left join (select max(id) as id,van_id, latitude as latitude,longitude as longitude from public.action_log 
		                group by van_id,latitude,longitude limit 1) al on sbv.id = al.id 
                     where ru.company_id = %s and (sbv.lisence_plate like '%%%s%%' or sbv.driver_name like '%%%s%%'
                           or sbv.driver_phone_number like '%%%s%%' or sbv.id_card like '%%%s%%') """ % (
                User.company_id.id, text_search, text_search, text_search, text_search)
            if status == 1:
                query += """ and sbo.status IN ('0','1') """
            elif status == 2:
                query += """ and sbo.status NOT IN ('0','1') or sbo.status isNull """
            query += """group by lisencePlate,driverName,driverPhone,idCard,is_bidding,image,tonnage,sbv.id,latitude,
            longitude """
            query1 = query
            query1 += """ ) t"""
            print(query1)
            self._cr.execute(query1, ())
            result1 = self._cr.fetchall()
            if offset is not None and limit is not None:
                if offset > 0:
                    offset_check = offset * limit
                    query += """  OFFSET %s LIMIT %s ) t""" % (offset_check, limit)
                    query_has_offset_limit = query
                else:
                    query += """  OFFSET %s LIMIT %s ) t""" % (offset, limit)
                    query_has_offset_limit = query
            else:
                query += """  OFFSET 0 LIMIT 10 ) t"""
                query_has_offset_limit = query

            self._cr.execute(query, ())
            result = self._cr.fetchall()
            jsonRe = []
            total = 0
            lenght = 0
            if result[0][0]:
                total = len(result1[0][0])
                lenght = len(result[0][0])
                for record in result[0][0]:
                    lstBidding = []
                    contentMain = {
                        'id': record['id'],
                        'lisence_plate': record['lisenceplate'],
                        'driver_name': record['drivername'],
                        'driver_phone': record['driverphone'],
                        'tonnage': record['tonnage'],
                        'image': record['image'],
                        'latitude': record['latitude'],
                        'longitude': record['longitude'],
                        'id_card': record['idcard'],
                        'is_bidding': record['is_bidding'],
                        'bidding': lstBidding
                    }
                    if record['bidding'] != None:
                        lstOrderBidding = record['bidding'].split(",")
                        print(lstOrderBidding)
                        for id in lstOrderBidding:
                            self.env.cr.execute("""
                                                    SELECT json_agg(t) FROM (
                                                        SELECT sbo.id, sbo.company_id, sbo.bidding_order_number, sbo.driver_name, sbo.phone,
                                                         sbo.van_id, sbo.from_depot_id, sbo.to_depot_id, sbo.total_weight,
                                                         sbo.total_cargo,sbo.price, sbo.distance, sbo.type, sbo.status, create_uid, 
                                                        TO_CHAR(sbo.create_date,'YYYY-MM-DD HH24:MI:SS') as create_date,
                                                        sbo.write_uid, TO_CHAR(sbo.write_date,'YYYY-MM-DD HH24:MI:SS') as write_date, sbo.driver_id, sbo.note, sbo.cargo_id,
                                                        sbo.bidding_order_receive_id, sbo.bidding_order_return_id, sbo.product_type_id, sbo.bidding_vehicle_id
                                                         FROM public.sharevan_bidding_order sbo
                                                                where sbo.bidding_order_number  = %s )t
                                                        """, (id,))
                            re = self._cr.fetchall()
                            print(re[0][0][0])
                            content = {
                                'id': re[0][0][0]['id'],
                                'company_id': re[0][0][0]['company_id'],
                                'bidding_order_number': re[0][0][0]['bidding_order_number'],
                                'driver_name': re[0][0][0]['driver_name'],
                                'phone': re[0][0][0]['phone'],
                                'van_id': re[0][0][0]['van_id'],
                                'from_depot_id': re[0][0][0]['from_depot_id'],
                                'to_depot_id': re[0][0][0]['to_depot_id'],
                                'total_weight': re[0][0][0]['total_weight'],
                                'total_cargo': re[0][0][0]['total_cargo'],
                                'price_bidding_order': re[0][0][0]['price'],
                                'distance': re[0][0][0]['distance'],
                                'type': re[0][0][0]['type'],
                                'status': re[0][0][0]['status'],
                                'create_uid': re[0][0][0]['create_uid'],
                                'create_date': re[0][0][0]['create_date'],
                                'driver_id': re[0][0][0]['driver_id'],
                                'cargo_id': re[0][0][0]['cargo_id'],
                                'note': re[0][0][0]['note'],
                                'bidding_order_receive_id': re[0][0][0]['bidding_order_receive_id'],
                                'bidding_order_return_id': re[0][0][0]['bidding_order_return_id'],
                                'product_type_id': re[0][0][0]['product_type_id'],
                                'bidding_vehicle_id': re[0][0][0]['bidding_vehicle_id']
                            }
                            lstBidding.append(content)
                    jsonRe.append(contentMain)
            return {
                'length': lenght,
                'total': total,
                'records': jsonRe
            }
        else:
            raise ValidationError('User id not found!')

    def creat_account_driver(self, driverInfo, files):
        driverInfoJson = json.loads(driverInfo)

        driver_phone_number = driverInfoJson['driver_phone_number']
        lisence_plate = driverInfoJson['lisence_plate']
        driver_name = driverInfoJson['driver_name']
        id_card = driverInfoJson['id_card']
        id_tonnage = driverInfoJson['id_tonnage']
        v = {
            'phone': driver_phone_number
        }
        # validate.validate_phone_number_v3(v)

        check_lisence_plate = self.env['res.users'].search([('login', '=', lisence_plate)])
        if len(check_lisence_plate) > 0:
            logger.warn(
                "Account already exists !",
                BiddingVehicle._name, lisence_plate,
                exc_info=True)
            response_data = {}
            response_data['result'] = 'error_lisence_plate'
            return Response(json.dumps(response_data), content_type="application/json", status=200)

        if isinstance(driver_phone_number, int) or isinstance(lisence_plate, int) or isinstance(driver_name,
                                                                                                int) or isinstance(
            id_card, int):
            logger.warn(
                "Phone , license_plate,name is of type string",
                BiddingVehicle._name,
                exc_info=True)
            response_data = {}
            response_data['result'] = 'error : Phone,license_plate,name,id_card is of type string'
            return Response(json.dumps(response_data), content_type="application/json", status=200)

        if isinstance(id_tonnage, str):
            logger.warn(
                "Id_tonnage is of type int  !",
                BiddingVehicle._name,
                exc_info=True)
            response_data = {}
            response_data['result'] = 'error : Id_tonnage is of type int'
            return Response(json.dumps(response_data), content_type="application/json", status=200)

        check_tonnage = self.env['sharevan.tonnage.vehicle'].search(
            [('id', '=', id_tonnage)])
        if len(check_tonnage) is 0:
            logger.warn(
                "Tonnage id does not exists  !",
                BiddingVehicle._name,
                exc_info=True)
            response_data = {}
            response_data['result'] = 'error_id_tonnage'
            return Response(json.dumps(response_data), content_type="application/json", status=200)

        check_phone_number = self.env['sharevan.bidding.vehicle'].search(
            [('driver_phone_number', '=', driver_phone_number)])
        if len(check_phone_number) > 0:
            logger.warn(
                "Phone number already exists !",
                BiddingVehicle._name, driverInfoJson['id_card'],
                exc_info=True)
            response_data = {}
            response_data['result'] = 'error_driver_phone_number'
            return Response(json.dumps(response_data), content_type="application/json", status=200)

        check_id_card = self.env['sharevan.bidding.vehicle'].search([('id_card', '=', id_card)])
        if len(check_id_card) > 0:
            logger.warn(
                "Id card already exists  !",
                BiddingVehicle._name,
                exc_info=True)
            response_data = {}
            response_data['result'] = 'error_id_card'
            return Response(json.dumps(response_data), content_type="application/json", status=200)

        context = self._context
        current_uid = context.get('uid')
        search_company_id = self.env['res.users'].search([('id', '=', current_uid)]).company_id

        check_res_partner = self.env['res.partner'].search([('user_id', '=', current_uid)])
        if len(check_res_partner) == 0:
            logger.warn(
                "You do not have permission to create !",
                BiddingVehicle._name, driverInfoJson['id_card'],
                exc_info=True)
            response_data = {}
            response_data['result'] = 'error : You do not have permission to create'
            return Response(json.dumps(response_data), content_type="application/json", status=200)

        v = {
            'lisence_plate': lisence_plate,
            'driver_phone_number': driver_phone_number,
            'driver_name': driver_name,
            'res_partner_id': check_res_partner['id'],
            'company_id': int(search_company_id),
            'id_card': id_card,
            'tonnage': id_tonnage

        }
        bidding_vehicle = self.env[BiddingVehicle._name].sudo().create(v)

        for file in files:
            if file.filename:
                val = {
                    'res_model': 'sharevan.bidding.vehicle',
                    'mimetype': file.mimetype,
                    'name': file.filename,
                    'res_id': bidding_vehicle['id'],
                    'status': 'running',
                    'type': 'binary',
                    'datas': base64.b64encode(file.read())
                }
                rec = http.request.env[IrAttachment._name].create(val)
                rec.write({'uri_path': rec['store_fname'], 'res_field': 'image_128'})
            break

        response_data = {}
        response_data['result'] = 'Create success'
        return Response(json.dumps(response_data), content_type="application/json", status=200)

    def update_account_driver(self, driverInfo, files):
        driverInfoJson = json.loads(driverInfo)

        driver_phone_number = driverInfoJson['driver_phone_number']
        driver_name = driverInfoJson['driver_name']
        id_vehicle = driverInfoJson['id_vehicle']
        id_card = driverInfoJson['id_card']
        id_tonnage = driverInfoJson['id_tonnage']

        if isinstance(driver_phone_number, int) or isinstance(driver_name, int) or isinstance(id_card, int):
            logger.warn(
                "Phone,name,id_card is of type string",
                BiddingVehicle._name,
                exc_info=True)
            response_data = {}
            response_data['result'] = 'error: Phone,name,id_card is of type string'
            return Response(json.dumps(response_data), content_type="application/json", status=200)
        if isinstance(id_vehicle, str) or isinstance(id_tonnage, str):
            logger.warn(
                "Id_vehicle is of type int  !",
                BiddingVehicle._name,
                exc_info=True)
            response_data = {}
            response_data['result'] = 'error : Id_vehicle is of type int'
            return Response(json.dumps(response_data), content_type="application/json", status=200)
        check_tonnage = self.env['sharevan.tonnage.vehicle'].search(
            [('id', '=', id_tonnage)])
        if len(check_tonnage) is 0:
            logger.warn(
                "Tonnage id does not exists  !",
                BiddingVehicle._name,
                exc_info=True)
            response_data = {}
            response_data['result'] = 'error_id_tonnage'
            return Response(json.dumps(response_data), content_type="application/json", status=200)

        check_phone_number = self.env['sharevan.bidding.vehicle'].search(
            [('driver_phone_number', '=', driver_phone_number), ('id', '!=', id_vehicle)])
        v = {
            'phone': driver_phone_number
        }
        # validate.validate_phone_number_v3(v)
        if len(check_phone_number) > 0:
            logger.warn(
                "Phone number already exists  !",
                BiddingVehicle._name,
                exc_info=True)
            response_data = {}
            response_data['result'] = 'error_driver_phone_number'
            return Response(json.dumps(response_data), content_type="application/json", status=200)

        check_id_card = self.env['sharevan.bidding.vehicle'].search(
            [('id_card', '=', id_card), ('id', '!=', id_vehicle)])
        if len(check_id_card) > 0:
            logger.warn(
                "Id card already exists  !",
                BiddingVehicle._name,
                exc_info=True)
            response_data = {}
            response_data['result'] = 'error_id_card'
            return Response(json.dumps(response_data), content_type="application/json", status=200)

        context = self._context
        current_uid = context.get('uid')

        check_vehicle = self.env['sharevan.bidding.vehicle'].search([('id', '=', id_vehicle)])
        if len(check_vehicle) == 0:
            if len(check_phone_number) > 0:
                logger.warn(
                    "Account does not exist !",
                    BiddingVehicle._name,
                    exc_info=True)
                response_data = {}
                response_data['result'] = 'error: Account already exists'
                return Response(json.dumps(response_data), content_type="application/json", status=200)
        if current_uid != int(check_vehicle['create_uid']):
            logger.warn(
                "You do not have permission to update   !",
                BiddingVehicle._name,
                exc_info=True)
            response_data = {}
            response_data['result'] = 'error : You do not have permission to update'
            return Response(json.dumps(response_data), content_type="application/json", status=200)
        check_vehicle.write({
            'driver_name': driver_name,
            'driver_phone_number': driver_phone_number,
            'id_card': id_card,
            'tonnage': id_tonnage
        })

        for file in files:
            if file.filename:
                image_querry = """ 
                                                            SELECT ir.id
                                                            FROM ir_attachment ir
                                                            where res_model = 'sharevan.bidding.vehicle' and  res_id = %s and status = 'running'
                                                         """
                self.env.cr.execute(image_querry, (id_vehicle,))
                result = self._cr.fetchall()
                if len(result) > 0:

                    id_image = result[0]
                    len(id_image)
                    if len(id_image):
                        update_status = """ Update ir_attachment
                                                                    Set status = 'deleted'  
                                                                    where id = %s
                                                                        """
                        self.env.cr.execute(update_status, (id_image,))
                # val = {
                #     'res_model': 'sharevan.bidding.vehicle',
                #     'mimetype': file.mimetype,
                #     'name': 'image_128',
                #     'res_field': 'image_128',
                #     'res_id': check_vehicle['id'],
                #     'type': 'binary',
                #     'datas': base64.b64encode(file.read())
                # }
                # rec = http.request.env[IrAttachment._name].create(val)

                val = {
                    'res_model': 'sharevan.bidding.vehicle',
                    'mimetype': file.mimetype,
                    'name': file.filename,
                    'res_id': check_vehicle['id'],
                    'type': 'binary',
                    'datas': base64.b64encode(file.read())
                }
                rec = http.request.env[IrAttachment._name].create(val)

                rec.write({'uri_path': rec['store_fname'], 'res_field': 'image_128'})
                break

        response_data = {}
        response_data['result'] = 'Update success'
        return Response(json.dumps(response_data), content_type="application/json", status=200)

    def delete_account_driver(self, vehicle_id):
        if isinstance(vehicle_id, str):
            raise ValidationError(_('user_id is of type int !'))

        check_user_vehicle = self.env['sharevan.bidding.vehicle'].search([('id', '=', vehicle_id)])
        if len(check_user_vehicle) == 0:
            raise ValidationError(_('User does not exist !'))

        check_user = self.env[Users._name].search([('id', '=', check_user_vehicle['res_user_id'].id)])
        if len(check_user) == 0:
            raise ValidationError(_('User does not exist !'))
        else:
            update_status = """ Update res_users
                                                   Set active = False  
                                                   where id = %s
                                                       """
            self.env.cr.execute(update_status, (check_user['id'],))

            update = """ Update sharevan_bidding_vehicle
                               Set active_deactive = 'deleted'  
                               where id = %s
                                                      """
            self.env.cr.execute(update, (check_user_vehicle['id'],))
            return True

    def get_support_phone_number(self):
        # sharevan_sos là key của bản ghi trong bảng ir_config_key , bản ghi này lưu số điện thoại hỗ trợ của trung tâm share_van
        sharevan_sos = "sharevan_sos"
        str = """ SELECT json_agg(t)
                                        FROM (
                                            SELECT * FROM ir_config_parameter ir_config where ir_config.key = %s ) t  """
        self.env.cr.execute(str, (sharevan_sos,))
        jsonRe = []
        result = self._cr.fetchall()
        if result[0]:
            if result[0][0]:
                re = result[0][0]
                records = {
                    'length': len(re),
                    'records': re
                }
                simplejson.dumps(records, indent=4, sort_keys=True, default=str)
                return records

        return {
            'records': []
        }

    def get_company_information(self):
        user = self.env['res.users'].search([('id', '=', self.env.uid)])
        if user:
            str = """ SELECT json_agg(t)
                                               FROM (
                                              select * from res_company s where s.id = %s ) t  """
            self.env.cr.execute(str,
                                (user.company_id.id,))

            jsonRe = []
            result = self._cr.fetchall()
            if result[0]:
                if result[0][0]:
                    re = result[0][0]
                    records = {
                        'length': len(re),
                        'records': re
                    }
                    simplejson.dumps(records, indent=4, sort_keys=True, default=str)
                    return records
        else:
            raise ValidationError("User does not existed")
        return {
            'records': []
        }

    def get_list_bidding_vehicle_for_company(self, text_search, status, offset, limit):
        user = self.env['res.users'].search([('id', '=', self.env.uid)])
        offset_check = 0
        limit_check = 10
        params = []
        json_return = []
        if user:
            query_get_bidding_vehicle = """ SELECT json_agg(t)
                                                         FROM (
                                                       SELECT sbv.id, sbv.code, sbv.res_user_id, sbv.lisence_plate, sbv.driver_phone_number,
                                                         sbv.driver_name, TO_CHAR(sbv.expiry_time, 'YYYY-MM-DD HH24:MI:SS'),
                                                          sbv.company_id, sbv.status, sbv.description, 
                                                          ia.store_fname,sbv.create_uid, TO_CHAR(sbv.create_date, 'YYYY-MM-DD HH24:MI:SS') ,
                                                          sbv.write_uid,TO_CHAR(sbv.write_date, 'YYYY-MM-DD HH24:MI:SS'),
                                                           sbv.id_card, sbv.name_seq_self_sharevan_bidding_vehicle, 
                                                           sbv.res_partner_id, sbv.tonnage, sbv.vehicle_type
                	                                    FROM public.sharevan_bidding_vehicle sbv 
                	                                    left join public.ir_attachment ia on sbv.id = ia.res_id and ia.res_model = 'sharevan.bidding.vehicle'   and ia.res_field = 'image_128' 
                	                                     where sbv.company_id = %s and sbv.status = 'running' 
                                                        ) t  """
            self.env.cr.execute(query_get_bidding_vehicle,
                                (user.company_id.id,))

            result_get_bidding_vehicle = self._cr.fetchall()

            if result_get_bidding_vehicle[0][0]:
                bidding_order_arr = []
            for bidding_vehicle in result_get_bidding_vehicle[0][0]:
                query_get_action_log = """ SELECT json_agg(t)
                                                         FROM ( SELECT id, van_id, latitude, longitude, create_uid, TO_CHAR(create_date, 'YYYY-MM-DD HH24:MI:SS') create_date, write_uid,TO_CHAR(write_date, 'YYYY-MM-DD HH24:MI:SS') write_date
                                                                  FROM public.action_log ac where ac.van_id = %s
                                                                  order by id DESC
                                                                  limit 1) t
                                                              """
                self.env.cr.execute(query_get_action_log,
                                    (bidding_vehicle['id'],))
                result_get_action_log = self._cr.fetchall()

                query_get_bidding_order = """ SELECT json_agg(t)
                                                         FROM (  SELECT bidding_order.id id, bidding_order.company_id company_id, bidding_order.bidding_order_number bidding_order_number, bidding_order.driver_id driver_id, bidding_order.driver_name driver_name,
                                                          bidding_order.phone phone, bidding_order.van_id van_id,
                                                    bidding_order.from_depot_id from_depot_id, bidding_order.to_depot_id to_depot_id, bidding_order.product_type_id product_type_id, bidding_order.total_weight total_weight, bidding_order.total_cargo total_cargo,
                                                   bidding_order.price price, bidding_order.distance distance, bidding_order.type type, bidding_order.status status, bidding_order.cargo_id cargo_id, 
                                                   bidding_order.note note, bidding_order.bidding_order_receive_id bidding_order_receive_id,
                                                    bidding_order.bidding_order_return_id bidding_order_return_id, bidding_order.bidding_vehicle_id bidding_vehicle_id, bidding_vehicle_id.create_uid create_uid, 
                                                    TO_CHAR(bidding_order.create_date, 'YYYY-MM-DD HH24:MI:SS'), bidding_order.write_uid write_uid, TO_CHAR(bidding_order.write_date, 'YYYY-MM-DD HH24:MI:SS') write_date, bidding_order.name_seq_self_sharevan_bidding name_seq_self_sharevan_bidding
    	                                            FROM public.sharevan_bidding_order bidding_order 
    	                                            join public.sharevan_bidding_vehicle bidding_vehicle on bidding_order.bidding_vehicle_id = bidding_vehicle.id
    	                                            where bidding_vehicle.status = 'running' and bidding_vehicle.id = %s ) t  """

                self.env.cr.execute(query_get_bidding_order,
                                    (bidding_vehicle['id'],))
                result_get_bidding_order = self._cr.fetchall()

                if result_get_bidding_order[0][0]:
                    for bidding_order in result_get_bidding_order[0][0]:
                        query_get_from_depot = """ SELECT depot.id id, depot.name name, depot.depot_code depot_code, depot.address address, depot.street street, depot.street2 street2, depot.city_name city_name, depot.district district, depot.ward ward,
                                                          depot.zip zip, depot.state_id state_id, depot.country_id country_id, depot.latitude latitude, depot.longitude longitude, depot.phone phone, depot.zone_id zone_id, depot.area_id area_id, depot.company_id company_id, 
                                                           depot.customer_id customer_id, depot.status status, depot.name_seq name_seq, depot.create_uid create_uid, TO_CHAR(depot.create_date, 'YYYY-MM-DD HH24:MI:SS') create_date,
                                                             TO_CHAR(depot.write_date, 'YYYY-MM-DD HH24:MI:SS') write_date, depot.open_time open_time, depot.closing_time closing_time
    	                                                  FROM public.sharevan_depot depot 
    	                                                  join public.sharevan_bidding_order bidding_order on bidding_order.from_depot_id = depot.id 
    	                                                  where 1=1  and depot.status = 'running' and depot.id = %s """
                        self.env.cr.execute(query_get_from_depot,
                                            (bidding_order['from_depot_id'],))
                        result_get_from_depot = self._cr.fetchall()

                        query_get_to_depot = """ SELECT depot.id id, depot.name name, depot.depot_code depot_code, depot.address address, depot.street street, depot.street2 street2, depot.city_name city_name, depot.district district, depot.ward ward,
                                                          depot.zip zip, depot.state_id state_id, depot.country_id country_id, depot.latitude latitude, depot.longitude longitude, depot.phone phone, depot.zone_id zone_id, depot.area_id area_id, depot.company_id company_id, 
                                                           depot.customer_id customer_id, depot.status status, depot.name_seq name_seq, depot.create_uid create_uid, TO_CHAR(depot.create_date, 'YYYY-MM-DD HH24:MI:SS') create_date,
                                                             TO_CHAR(depot.write_date, 'YYYY-MM-DD HH24:MI:SS') write_date, depot.open_time open_time, depot.closing_time closing_time
    	                                                  FROM public.sharevan_depot depot 
    	                                                  join public.sharevan_bidding_order bidding_order on bidding_order.from_depot_id = depot.id 
    	                                                  where 1=1  and depot.status = 'running' and depot.id = %s  """
                        self.env.cr.execute(query_get_to_depot,
                                            (bidding_order['to_depot_id'],))
                        result_get_to_depot = self._cr.fetchall()

                        query_get_product_type = """ SELECT product_type.id id, product_type.name_seq name_seq, product_type.net_weight net_weight, product_type.name name, product_type.description description, product_type.status status, product_type.create_date create_date
    	                                                FROM public.sharevan_product_type product_type 
    	                                                join public.sharevan_bidding_order bidding_order on bidding_order.product_type_id = product_type.id 
    	                                                where 1=1 and product_type.status = 'running' and product_type.id = %s """
                        self.env.cr.execute(query_get_product_type,
                                            (bidding_order['product_type_id'],))
                        result_get_product_type = self._cr.fetchall()

                        bidding_order_data = {
                            'id': bidding_order['id'],
                            'company_id': bidding_order['company_id'],
                            'bidding_order_number': bidding_order['bidding_order_number'],
                            'driver_id': bidding_order['driver_id'],
                            'driver_name': bidding_order['driver_name'],
                            'phone': bidding_order['phone'],
                            'van_id': bidding_order['van_id'],
                            'from_depot': result_get_from_depot,
                            'to_depot': result_get_to_depot,
                            'product_type': query_get_product_type,
                            'total_weight': bidding_order['total_weight'],
                            'total_cargo': bidding_order['total_cargo'],
                            'price': bidding_order['price'],
                            'distance': bidding_order['distance'],
                            'type': bidding_order['type'],
                            'status': bidding_order['status'],
                            'cargo_id': bidding_order['cargo_id'],
                            'note': bidding_order['note'],
                            'bidding_order_receive_id': bidding_order['bidding_order_receive_id'],
                            'bidding_order_return_id': bidding_order['bidding_order_return_id'],
                            'bidding_vehicle_id': bidding_order['bidding_vehicle_id'],
                            'create_date': bidding_order['create_date'],
                            'name_seq_self_sharevan_bidding': bidding_order['name_seq_self_sharevan_bidding']
                        }
                        bidding_order_arr.append(bidding_order_data)

                bidding_vehicle_data = {
                    'id': bidding_vehicle['id'],
                    'code': bidding_vehicle['code'],
                    'res_user_id': bidding_vehicle['res_user_id'],
                    'lisence_plate': bidding_vehicle['lisence_plate'],
                    'driver_phone_number': bidding_vehicle['driver_phone_number'],
                    'driver_name': bidding_vehicle['driver_name'],
                    'expiry_time': bidding_vehicle['expiry_time'],
                    'company_id': bidding_vehicle['company_id'],
                    'status': bidding_vehicle['status'],
                    'description': bidding_vehicle['description'],
                    'create_date': bidding_vehicle['create_date'],
                    'id_card': bidding_vehicle['id_card'],
                    'name_seq_self_sharevan_bidding_vehicle': bidding_vehicle['name_seq_self_sharevan_bidding_vehicle'],
                    'res_partner_id': bidding_vehicle['res_partner_id'],
                    'tonnage': bidding_vehicle['tonnage'],
                    'vehicle_type': bidding_vehicle['vehicle_type'],
                    'weight_unit': bidding_vehicle['weight_unit'],
                    'bidding_orders': bidding_order_arr
                }

                json_return.append(bidding_vehicle_data)

            records = {
                'length': len(result_get_bidding_vehicle),
                'records': json_return
            }
            simplejson.dumps(records, indent=4, sort_keys=True, default=str)
            return records
        else:
            raise ValidationError(_('User id not found!'))

        return {
            'records': []
        }

    def get_bidding_vehicle_information_for_login(self, license_plate):
        if license_plate:
            query_get_bidding_vehicle_information = """  SELECT json_agg(t)
                                                         FROM (  select bidding_vehicle.lisence_plate,bidding_vehicle.driver_phone_number from sharevan_bidding_vehicle bidding_vehicle
                                                        where bidding_vehicle.lisence_plate = %s ) t """
            self.env.cr.execute(query_get_bidding_vehicle_information,
                                (license_plate,))

            get_bidding_vehicle_information = self._cr.fetchall()
            if get_bidding_vehicle_information[0][0]:
                records = {
                    'length': len(get_bidding_vehicle_information),
                    'records': get_bidding_vehicle_information[0][0],
                }
                simplejson.dumps(records, indent=4, sort_keys=True, default=str)
                return records

            else:
                return {
                    'records': []
                }

        else:
            raise ValidationError(_('license_plate does not existed!'))

    def list_bidding_vehicle(self):
        uid = http.request.env.uid
        company_id = self.env['res.users'].search([('id', '=', uid)]).company_id

        # query_list_bidding_vehicle = """ SELECT json_agg(t)
        #                                                  FROM (
        #                                                SELECT sbv.id, sbv.code, sbv.res_user_id, sbv.lisence_plate, sbv.driver_phone_number,
        #
        #         	                                    FROM sharevan_bidding_vehicle sbv
        #         	                                    left join public.ir_attachment ia on sbv.id = ia.res_id and ia.res_model = 'sharevan.bidding.vehicle'   and ia.res_field = 'image_128'
        #         	                                     where sbv.company_id = %s and sbv.status = 'running'
        #                                                 ) t  """
        # self.env.cr.execute(query_get_bidding_vehicle,
        #                         (user.company_id.id,))
        #
        #     result_get_bidding_vehicle = self._cr.fetchall()
        query_list_bidding_vehicle = """ SELECT json_agg(t)
                                                 FROM (
                                                 SELECT sbv.id, sbv.driver_name, sbv.code, sbv.lisence_plate,sbv.id_card, sbv.driver_phone_number,
                                                        stv.name
                                                 FROM sharevan_bidding_vehicle sbv 
                                                 LEFT JOIN sharevan_tonnage_vehicle stv on stv.id = sbv.tonnage
                                                 WHERE sbv.company_id = %s   and active_deactive = 'running'
                                                ) t  """
        self.env.cr.execute(query_list_bidding_vehicle,
                            (company_id['id'],))

        result = self._cr.fetchall()
        list_vehicle = []
        if result:
            for re in result[0][0]:
                vehicle = {
                    'id': re['id'],
                    'code': re['code'],
                    'driver_name': re['driver_name'],
                    'id_card': re['id_card'],
                    'lisence_plate': re['lisence_plate'],
                    'driver_phone_number': re['driver_phone_number'],
                    'tonnage': re['name']
                }

                query = """ SELECT json_agg(t)
                                                                 FROM (
                                                                 SELECT uri_path as images_128
    
                                                                 FROM ir_attachment 
                                                                 WHERE status = 'running' and res_model = 'sharevan.bidding.vehicle' and res_id = %s
                                                                ) t  """
                self.env.cr.execute(query, (re['id'],))
                result_1 = self._cr.fetchall()
                res = result_1[0][0]

                if res:
                    for re in res:
                        vehicle.update({'image_128': re['images_128']})
                else:
                    vehicle.update({'image_128': None})
                list_vehicle.append(vehicle)

            content = list_vehicle
            records = {
                'length': len(result[0][0]),
                'records': content
            }
            simplejson.dumps(records, indent=4, sort_keys=True, default=str)
            return records

        return True

    def check_driver_phone_number(self, driver_phone_number):
        check_phone_number = self.env[Constants.SHAREVAN_BIDDING_VEHICLE].search(
            [('driver_phone_number', '=', driver_phone_number)])
        if len(check_phone_number) > 0:
            return True
        return False

    def check_lisence_plate(self, lisence_plate):
        check_lisence_plate = self.env[Constants.SHAREVAN_BIDDING_VEHICLE].search(
            [('lisence_plate', '=', lisence_plate)])
        if len(check_lisence_plate) > 0:
            return True
        return False

    def check_driver_id_card(self, id_card):
        check_id_card = self.env[Constants.SHAREVAN_BIDDING_VEHICLE].search([('id_card', '=', id_card)])
        if len(check_id_card) > 0:
            return True
        return False

    def list_manager_bidding_vehicle(self, **kwargs):
        uid = http.request.env.uid
        company_id = self.env['res.users'].search([('id', '=', uid)]).company_id
        check = 0
        query_list_bidding_vehicle = """ SELECT json_agg(t)
                                                         FROM (
                                                         SELECT sbv.id, sbv.driver_name, sbv.code, sbv.id_card, sbv.lisence_plate, sbv.driver_phone_number,sbv.status,
                                                                stv.max_tonnage
                                	                     FROM sharevan_bidding_vehicle sbv 
                                	                     LEFT JOIN sharevan_tonnage_vehicle stv on stv.id = sbv.tonnage
                                	                     WHERE sbv.company_id = %s and active_deactive = 'running'

                                	                     """ % (company_id['id'])
        query_list_bidding_vehicle_total = """ 
                                                                 SELECT sbv.id, sbv.driver_name, sbv.code, sbv.id_card, sbv.lisence_plate, sbv.driver_phone_number,sbv.status,
                                                                        stv.max_tonnage
                                        	                     FROM sharevan_bidding_vehicle sbv 
                                        	                     LEFT JOIN sharevan_tonnage_vehicle stv on stv.id = sbv.tonnage
                                        	                     WHERE sbv.company_id = %s and active_deactive = 'running'

                                        	                     """ % (company_id['id'])
        query_rel_bidding_order_vehicle = """SELECT sbor.sharevan_bidding_order_id, sbor.sharevan_bidding_vehicle_id,sbo.bidding_order_number
                                    	                     FROM sharevan_bidding_order_sharevan_bidding_vehicle_rel sbor
                                    	                     LEFT JOIN sharevan_bidding_order sbo on sbo.id = sbor.sharevan_bidding_order_id
                                    	                     where sbor.sharevan_bidding_vehicle_id = %s  and ((sbo.type = '1' and sbo.status !='2') or (sbo.type = '2' and sbo.status !='2'))
                                    	                     """
        querry_action_log = """ SELECT json_agg(t)
                                                         FROM (
                                                                 SELECT al.latitude , al.longitude
                                        	                     FROM action_log al
                                        	                     WHERE al.van_id = %s
                                        	                     ORDER BY al.id DESC LIMIT 1 ) t
                            """

        querry_search = """  ( LOWER(lisence_plate) like LOWER('%s%%') or  LOWER(driver_phone_number) like LOWER('%s%%')
                            or LOWER(driver_name) like LOWER('%s%%') or LOWER(id_card) like LOWER('%s%%')) 
                            ORDER BY sbv.id ASC LIMIT %s OFFSET %s ) t
                        """
        querry_search_count = """  ( LOWER(lisence_plate) like LOWER('%s%%') or  LOWER(driver_phone_number) like LOWER('%s%%')
                            or LOWER(driver_name) like LOWER('%s%%') or LOWER(id_card) like LOWER('%s%%')) """
        querry_count = """ select count(*) from (  """
        querry_count += query_list_bidding_vehicle_total
        offset = 0
        status = 0
        txt_search = ''
        limit = 10
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
                txt_search = kwargs.get(arg)
                txt_search = reg.sub('[^A-Za-z0-9]+', '', txt_search.lower())
                check = 1
                continue
        if offset > 0:
            offset = offset * offset

        if status == 0:
            if check == 1:
                query_list_bidding_vehicle += """ and sbv.status = '0'  and """
                query_list_bidding_vehicle += querry_search % (
                    txt_search, txt_search, txt_search, txt_search, limit, offset)
                querry_count += """ and  sbv.status = '0' and """
                querry_count += querry_search_count % (txt_search, txt_search, txt_search, txt_search)
            else:
                query_list_bidding_vehicle += """  and sbv.status = '0'   ORDER BY sbv.id ASC LIMIT %s OFFSET %s  ) t  """ % (
                    limit, offset)
                querry_count += """ and sbv.status = '0' """

        if status == 1:
            if check == 1:
                query_list_bidding_vehicle += """ and sbv.status = '1' and """
                query_list_bidding_vehicle += querry_search % (
                    txt_search, txt_search, txt_search, txt_search, limit, offset)
                querry_count += """ and sbv.status = '1' and """
                querry_count += querry_search_count % (txt_search, txt_search, txt_search, txt_search)
            else:
                query_list_bidding_vehicle += """ and sbv.status = '1'   ORDER BY sbv.id ASC LIMIT %s OFFSET %s) t   """ % (
                    limit, offset)
                querry_count += """ and sbv.status = '1' """

        if status == 2:
            if check == 1:
                query_list_bidding_vehicle += """ and """
                query_list_bidding_vehicle += querry_search % (
                    txt_search, txt_search, txt_search, txt_search, limit, offset)
                querry_count += """ and """
                querry_count += querry_search_count % (txt_search, txt_search, txt_search, txt_search)
            else:
                query_list_bidding_vehicle += """   ORDER BY sbv.id ASC LIMIT %s OFFSET %s) t """ % (limit, offset)

        self.env.cr.execute(query_list_bidding_vehicle)

        result = self._cr.fetchall()

        querry_count += """ ) t """
        self.env.cr.execute(querry_count)

        result_total = self._cr.fetchall()

        list_vehicle = []
        records = {}
        lat = 0
        long = 0
        if result[0][0]:
            count = len(result[0][0])
            result_count = result_total[0][0]
            for re in result[0][0]:

                vehicle = {
                    'id': re['id'],
                    'code': re['code'],
                    'driver_name': re['driver_name'],
                    'driver_phone_number': re['driver_phone_number'],
                    'id_card': re['id_card'],
                    'lisence_plate': re['lisence_plate'],
                    'tonnage': re['max_tonnage'],
                    'status': re['status']
                }
                self.env.cr.execute(querry_action_log, (re['id'],))
                result_action_log = self._cr.fetchall()
                latlong = result_action_log[0][0]
                if latlong:
                    for r in latlong:
                        vehicle.update({'latitude': r['latitude'],
                                        'longitude': r['longitude']
                                        })

                query = """ SELECT json_agg(t)
                                                                 FROM (
                                                                 SELECT uri_path as images_128

                                        	                     FROM ir_attachment 
                                        	                     WHERE status = 'running' and res_model = 'sharevan.bidding.vehicle' and res_id = %s
                                                                ) t  """
                vehicle_id = re['id']
                status_id = re['status']
                self.env.cr.execute(query, (re['id'],))
                result_1 = self._cr.fetchall()
                res = result_1[0][0]

                if res:
                    for re in res:
                        vehicle.update({'image_128': re['images_128']})
                else:
                    vehicle.update({'image_128': None})
                if status == 1:

                    self.env.cr.execute(query_rel_bidding_order_vehicle, (vehicle_id,))
                    result_rel = self._cr.fetchall()
                    bidding_order = []
                    for re in result_rel:
                        bidding_order.append(
                            {
                                'id': re[0],
                                'bidding_order_number': re[2]
                            }
                        )
                    vehicle.update({'list_bidding_order': bidding_order})

                elif status == 2:
                    if status_id == '1':
                        self.env.cr.execute(query_rel_bidding_order_vehicle, (vehicle_id,))
                        result_rel = self._cr.fetchall()
                        bidding_order = []
                        for re in result_rel:
                            bidding_order.append(
                                {
                                    'id': re[0],
                                    'bidding_order_number': re[2]
                                }
                            )
                        vehicle.update({'list_bidding_order': bidding_order})

                list_vehicle.append(vehicle)

            content = list_vehicle
            records = {
                'length': count,
                'total': result_count,
                'records': content
            }
            simplejson.dumps(records, indent=4, sort_keys=True, default=str)

        else:
            records = {
                'length': 0,
                'records': []

            }
        return records

    def get_list_bidding_order_by_bidding_vehicle_id(self, bidding_vehicle_id, offset, limit):
        params = []
        params_for_count = []
        bidding_order_arr = []
        offset_check = 0
        limit_check = 10
        user = self.env['res.users'].search([('id', '=', self.env.uid)])
        if user:
            if bidding_vehicle_id:
                query_get_bidding_vehicle_information = """ 
                    SELECT json_agg(t) FROM (  
                        select bidding_vehicle.lisence_plate,bidding_vehicle.driver_phone_number 
                            from sharevan_bidding_vehicle bidding_vehicle
                        where bidding_vehicle.id = %s ) t """
                self.env.cr.execute(query_get_bidding_vehicle_information,
                                    (bidding_vehicle_id,))
                get_bidding_vehicle_information = self._cr.fetchall()
                if get_bidding_vehicle_information[0][0]:
                    query_bidding_vehicle_rel = """ 
                        SELECT sharevan_bidding_order_id, sharevan_bidding_vehicle_id
                            FROM public.sharevan_bidding_order_sharevan_bidding_vehicle_rel rel 
                        where rel.sharevan_bidding_vehicle_id = %s """
                    self.env.cr.execute(query_bidding_vehicle_rel,
                                        (bidding_vehicle_id,))
                    get_bidding_vehicle_rel = self._cr.fetchall()
                    if get_bidding_vehicle_rel[0][0]:
                        for re in get_bidding_vehicle_rel:
                            params = []
                            query_get_bidding_order_json = """ SELECT json_agg(t)
                                                                        FROM ( """
                            query_get_bidding_order = """ 
                                SELECT  distinct bidding_order.id,
                                    bidding_order.company_id,
                                    bidding_order.bidding_order_number,
                                    bidding_order.from_depot_id,
                                    bidding_order.to_depot_id,
                                    bidding_order.total_weight,
                                    bidding_order.total_cargo,
                                    bidding_order.price,
                                    bidding_order.distance,
                                    bidding_order.type,
                                    bidding_order.status,
                                    bidding_order.note,
                                    bidding_order.bidding_order_receive_id,
                                    bidding_order.bidding_order_return_id,
                                    TO_CHAR(bidding_order.create_date,'YYYY-MM-DD HH24:MI:SS') create_date,
                                    TO_CHAR(bidding_order.write_date,'YYYY-MM-DD HH24:MI:SS') write_date,
                                    bidding_order.bidding_package_id,
                                    TO_CHAR(bidding_order.from_receive_time,'YYYY-MM-DD HH24:MI:SS') from_receive_time,
                                    TO_CHAR(bidding_order.to_receive_time,'YYYY-MM-DD HH24:MI:SS') to_receive_time,
                                    TO_CHAR(bidding_order.from_return_time,'YYYY-MM-DD HH24:MI:SS') from_return_time,
                                    TO_CHAR(bidding_order.to_return_time,'YYYY-MM-DD HH24:MI:SS')  to_return_time,
                                    TO_CHAR(bidding_order.max_confirm_time,'YYYY-MM-DD HH24:MI:SS') max_confirm_time
                                FROM public.sharevan_bidding_order bidding_order
                                    LEFT JOIN sharevan_bidding_order_sharevan_bidding_vehicle_rel rel 
                                        on bidding_order.id = rel.sharevan_bidding_order_id
                                    LEFT JOIN sharevan_bidding_vehicle bidding_vehicle 
                                        on bidding_vehicle.id = rel.sharevan_bidding_vehicle_id
                                where bidding_order.company_id = %s and rel.sharevan_bidding_vehicle_id = %s """

                            query_get_bidding_order += """ and ( bidding_order.type = %s or   bidding_order.type = %s ) and (bidding_order.status != %s ) """

                            params.append(user.company_id.id)
                            params.append(re[1])
                            params.append(BiddingStatusType.Approved.value)
                            params.append(BiddingStatusType.Waiting.value)
                            params.append(BiddingStatus.Returned.value)

                            params_for_count.append(user.company_id.id)
                            params_for_count.append(re[1])
                            params_for_count.append(BiddingStatusType.Approved.value)
                            params_for_count.append(BiddingStatusType.Waiting.value)
                            params_for_count.append(BiddingStatus.Returned.value)
                            query_get_bidding_order_json += query_get_bidding_order

                            if offset is not None and limit is not None:
                                if offset > 0:
                                    offset_check = offset * limit
                                    query_get_bidding_order_json += """  OFFSET %s LIMIT %s """
                                    query_has_offset_limit = query_get_bidding_order_json
                                    query_has_offset_limit += """ ) t """

                                    params.append(offset_check)
                                    params.append(limit)
                                else:
                                    query_get_bidding_order_json += """  OFFSET %s LIMIT %s """
                                    query_has_offset_limit = query_get_bidding_order_json
                                    query_get_bidding_order_json += """ ) t """
                                    query_has_offset_limit += """ ) t """
                                    params.append(offset)
                                    params.append(limit)
                            else:
                                query_get_bidding_order_json += """  OFFSET 0 LIMIT 10 """
                                query_has_offset_limit = query_get_bidding_order_json
                                query_get_bidding_order_json += """ ) t """

                            total_records = """ select count(*) from (  """

                            total_records += query_get_bidding_order
                            total_records += """ ) t """

                            self.env.cr.execute(total_records, (params_for_count))
                            result_get_total_records = self._cr.fetchall()
                            if result_get_total_records[0]:
                                if result_get_total_records[0][0]:
                                    total = result_get_total_records[0][0]
                                else:
                                    total = 0

                            self.env.cr.execute(query_has_offset_limit, (params))
                            result_get_bidding_order = self._cr.fetchall()

                            if result_get_bidding_order[0][0]:
                                for bidding_order in result_get_bidding_order[0][0]:
                                    bidding_vehicle_arr = []
                                    bidding_order_receive = {}
                                    bidding_order_return = {}

                                    query_get_bidding_vehicle = """ SELECT json_agg(t) FROM (SELECT id, code, lisence_plate, driver_phone_number, driver_name,
                                                                                                                                      TO_CHAR(expiry_time,'YYYY-MM-DD HH24:MI:SS') expiry_time, company_id, status, description,
                                                                                                                                     id_card, res_partner_id, tonnage, vehicle_type, weight_unit, bidding_vehicle_seq
                                                                                                                                     FROM public.sharevan_bidding_vehicle  bidding_vehicle where bidding_vehicle.id = %s ) t """
                                    self.env.cr.execute(query_get_bidding_vehicle, (bidding_vehicle_id,))
                                    result_get_bidding_vehicle = self._cr.fetchall()

                                    bidding_vehicle_arr = []
                                    bidding_order_receive = {}
                                    bidding_order_return = {}

                                    query_get_bidding_vehicle = """ SELECT json_agg(t) FROM (SELECT id, code, lisence_plate, driver_phone_number, driver_name,
                                                                                                                                                                                                     TO_CHAR(expiry_time,'YYYY-MM-DD HH24:MI:SS') expiry_time, company_id, status, description,
                                                                                                                                                                                                    id_card, res_partner_id, tonnage, vehicle_type, weight_unit, bidding_vehicle_seq
                                                                                                                                                                                                    FROM public.sharevan_bidding_vehicle  bidding_vehicle where bidding_vehicle.id = %s ) t """
                                    self.env.cr.execute(query_get_bidding_vehicle, (bidding_vehicle_id,))
                                    result_get_bidding_vehicle = self._cr.fetchall()
                                    params = []
                                    for rec in result_get_bidding_vehicle[0][0]:
                                        query_get_bidding_order_receive = """ SELECT json_agg(t) FROM ( SELECT id, bidding_order_id, from_expected_time, to_expected_time, depot_id, actual_time, stock_man_id, status, description, create_date, write_date, bidding_order_vehicle_id
                                                                                              	                                                                          FROM public.sharevan_bidding_order_receive bidding_order_receive where bidding_order_receive.bidding_order_id = %s   and bidding_order_receive.bidding_vehicle_id = %s  ) t """
                                        params.append(bidding_order['id'])
                                        params.append(rec['id'])
                                        self.env.cr.execute(query_get_bidding_order_receive, (params))
                                        result_get_bidding_order_receive = self._cr.fetchall()
                                        if result_get_bidding_order_receive[0][0]:
                                            bidding_order_receive = result_get_bidding_order_receive[0][0][0]

                                        query_get_bidding_order_return = """ SELECT json_agg(t) FROM ( SELECT id, bidding_order_id, from_expected_time, to_expected_time, depot_id, actual_time, stock_man_id, status, description,  create_date, write_date, bidding_order_vehicle_id

                                                                                         	                                                                        FROM public.sharevan_bidding_order_return  bidding_order_return where bidding_order_return.bidding_order_id = %s  and bidding_order_return.bidding_vehicle_id = %s )  t """
                                        self.env.cr.execute(query_get_bidding_order_return, (params))
                                        result_get_bidding_order_return = self._cr.fetchall()
                                        if result_get_bidding_order_return[0][0]:
                                            bidding_order_return = result_get_bidding_order_return[0][0][0]

                                    bidding_vehicle_param = []
                                    query_get_cargo_bidding_order_vehicle = """ SELECT distinct cargo_id FROM public.sharevan_cargo_bidding_order_vehicle s 
                                                                                                                                                 where s.bidding_order_id = """
                                    query_get_cargo_bidding_order_vehicle += str(bidding_order['id'])
                                    query_get_cargo_bidding_order_vehicle += """ and s.bidding_vehicle_id = """
                                    query_get_cargo_bidding_order_vehicle += str(bidding_vehicle_id)
                                    query_get_cargo_bidding_order_vehicle += """ and s.status = '1' """
                                    # query_get_cargo_bidding_order_vehicle += CargoBiddingOrderVehicleStatus.running.value
                                    self.env.cr.execute(query_get_cargo_bidding_order_vehicle, ())
                                    result_get_cargo_bidding_order_vehicle = self._cr.fetchall()
                                    list_cargo_id = []
                                    size_standard_arr = []
                                    if result_get_cargo_bidding_order_vehicle:
                                        for id in result_get_cargo_bidding_order_vehicle:
                                            list_cargo_id.append(id[0])
                                        query_get_size_standard = """ 
                                        SELECT json_agg(t) FROM (  
                                            select distinct  id, length, width, height, type,from_weight, to_weight, 
                                                price_id, price, size_standard_seq, cargo_price_ids, long_unit, weight_unit 
                                            from sharevan_size_standard size_stand
                                                where size_stand.id in (select cargo.size_id from sharevan_cargo cargo where cargo.id  ::integer in ( """

                                        if list_cargo_id:
                                            for cargo_id in list_cargo_id:
                                                query_get_size_standard += str(cargo_id) + ","
                                            query_get_size_standard = query_get_size_standard[:-1]
                                            query_get_size_standard += "))) t"

                                        self.env.cr.execute(query_get_size_standard, (list_cargo_id))
                                        result_get_size_standard = self._cr.fetchall()
                                        if result_get_size_standard[0][0]:
                                            for rec in result_get_size_standard[0][0]:
                                                query_count_cargo_map_with_size_standard = """ SELECT json_agg(t) FROM ( select count(*) from sharevan_cargo cargo where cargo.id  ::integer in ( """
                                                for cargo_id in list_cargo_id:
                                                    query_count_cargo_map_with_size_standard += str(
                                                        cargo_id) + ","
                                                query_count_cargo_map_with_size_standard = query_count_cargo_map_with_size_standard[
                                                                                           :-1]
                                                query_count_cargo_map_with_size_standard += """ ) and cargo.size_id = %s  """
                                                query_count_cargo_map_with_size_standard += " ) t"
                                                self.env.cr.execute(query_count_cargo_map_with_size_standard,
                                                                    (rec['id'],))
                                                result_count_cargo_map_with_size_standard = self._cr.fetchall()

                                                query_caculate_cargo_total_weight = """ SELECT json_agg(t) FROM ( select sum(weight) from sharevan_cargo cargo where cargo.id  ::integer in ( """
                                                for cargo_id in list_cargo_id:
                                                    query_caculate_cargo_total_weight += str(cargo_id) + ","
                                                query_caculate_cargo_total_weight = query_caculate_cargo_total_weight[
                                                                                    :-1]
                                                query_caculate_cargo_total_weight += """ ) and cargo.size_id = %s  """
                                                query_caculate_cargo_total_weight += " ) t"
                                                self.env.cr.execute(query_caculate_cargo_total_weight,
                                                                    (rec['id'],))
                                                result_query_caculate_cargo_total_weight = self._cr.fetchall()

                                                if result_count_cargo_map_with_size_standard[0][0]:
                                                    size_standard_data = {
                                                        'id': rec['id'],
                                                        'length': rec['length'],
                                                        'width': rec['width'],
                                                        'height': rec['height'],
                                                        'type': rec['type'],
                                                        'from_weight': rec['from_weight'],
                                                        'to_weight': rec['to_weight'],
                                                        'price_id': rec['price_id'],
                                                        'price': rec['price'],
                                                        'size_standard_seq': rec['size_standard_seq'],
                                                        'long_unit': rec['long_unit'],
                                                        'weight_unit': rec['weight_unit'],
                                                        'cargo_quantity':
                                                            result_count_cargo_map_with_size_standard[0][0][0][
                                                                'count'],
                                                        'total_weight':
                                                            result_query_caculate_cargo_total_weight[0][0][0][
                                                                'sum']

                                                    }
                                                    size_standard_arr.append(size_standard_data)

                                    bidding_vehicle_json = {
                                        'id': result_get_bidding_vehicle[0][0][0]['id'],
                                        'code': result_get_bidding_vehicle[0][0][0]['code'],
                                        'lisence_plate': result_get_bidding_vehicle[0][0][0]['lisence_plate'],
                                        'driver_phone_number': result_get_bidding_vehicle[0][0][0][
                                            'driver_phone_number'],
                                        'driver_name': result_get_bidding_vehicle[0][0][0]['driver_name'],
                                        'expiry_time': result_get_bidding_vehicle[0][0][0]['expiry_time'],
                                        'company_id': result_get_bidding_vehicle[0][0][0]['company_id'],
                                        'status': result_get_bidding_vehicle[0][0][0]['status'],
                                        'description': result_get_bidding_vehicle[0][0][0]['description'],
                                        'vehicle_type': result_get_bidding_vehicle[0][0][0]['vehicle_type'],
                                        'weight_unit': result_get_bidding_vehicle[0][0][0]['weight_unit'],
                                        'cargo_types': size_standard_arr,
                                        'bidding_order_receive': bidding_order_receive,
                                        'bidding_order_return': bidding_order_return
                                    }

                                    bidding_vehicle_arr.append(bidding_vehicle_json)

                                    query_get_from_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.latitude,depot.longitude,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                                                                       where depot.id =  %s ) t"""
                                    self.env.cr.execute(query_get_from_depot, (bidding_order['from_depot_id'],))
                                    result_get_from_depot = self._cr.fetchall()

                                    array_length = len(result_get_from_depot)
                                    if array_length > 0:
                                        if result_get_from_depot[0][0]:
                                            get_from_depot = result_get_from_depot[0][0][0]

                                    query_get_to_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.latitude,depot.longitude,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                                                                                         where     depot.id = %s ) t"""
                                    self.env.cr.execute(query_get_to_depot, (bidding_order['to_depot_id'],))
                                    result_get_to_depot = self._cr.fetchall()
                                    get_to_depot = []
                                    array_length = len(result_get_to_depot)
                                    if array_length > 0:
                                        if result_get_to_depot[0][0]:
                                            get_to_depot = result_get_to_depot[0][0][0]

                                    data = {
                                        'id': bidding_order['id'],
                                        'company_id': bidding_order['company_id'],
                                        'bidding_order_number': bidding_order['bidding_order_number'],
                                        'from_depot': get_from_depot,
                                        'to_depot': get_to_depot,
                                        'total_weight': bidding_order['total_weight'],
                                        'total_cargo': bidding_order['total_cargo'],
                                        'price': bidding_order['price'],
                                        'distance': bidding_order['distance'],
                                        'type': bidding_order['type'],
                                        'status': bidding_order['status'],
                                        'note': bidding_order['note'],
                                        'create_date': bidding_order['create_date'],
                                        'write_date': bidding_order['write_date'],
                                        'bidding_package_id': bidding_order['bidding_package_id'],
                                        'from_receive_time': bidding_order['from_receive_time'],
                                        'to_receive_time': bidding_order['to_receive_time'],
                                        'from_return_time': bidding_order['from_return_time'],
                                        'to_return_time': bidding_order['to_return_time'],
                                        'max_confirm_time': bidding_order['max_confirm_time'],
                                        'bidding_vehicles': bidding_vehicle_arr
                                    }

                                    bidding_order_arr.append(data)
                            else:
                                return {
                                    'records': []
                                }
                            records = {
                                'length': len(result_get_bidding_order[0][0]),
                                'total': total,
                                'records': bidding_order_arr
                            }
                            simplejson.dumps(records, indent=4, sort_keys=True, default=str)
                            return records


                else:
                    raise ValidationError(_('Bidding vehicle does not existed!'))

            else:
                raise ValidationError(_('bidding_vehicle_id can not null'))

    def get_list_bidding_order_shipping(self, offset, limit, txt_search, status):
        uid = http.request.session['uid']
        params = []
        params_for_count = []
        bidding_order_arr = []
        bidding_vehicle_arr = []
        depot_arr = []
        depot_coincident_arr = []
        offset_check = 0
        limit_check = 10
        length = 0
        txt_search = txt_search.lower()
        user = self.env['res.users'].search([('id', '=', uid)])
        bidding_vehicle_id = self.env['sharevan.bidding.vehicle'].search([('res_user_id', '=', uid)]).id

        if user:

            if bidding_vehicle_id:
                query_get_bidding_vehicle_information = """  SELECT json_agg(t)
                                                                        FROM (  select bidding_vehicle.lisence_plate,bidding_vehicle.driver_phone_number from sharevan_bidding_vehicle bidding_vehicle
                                                                       where bidding_vehicle.id = %s ) t """
                self.env.cr.execute(query_get_bidding_vehicle_information,
                                    (bidding_vehicle_id,))
                get_bidding_vehicle_information = self._cr.fetchall()
                if get_bidding_vehicle_information[0][0]:
                    query_bidding_vehicle_rel = """ SELECT sharevan_bidding_order_id, sharevan_bidding_vehicle_id
                                FROM public.sharevan_bidding_order_sharevan_bidding_vehicle_rel rel where rel.sharevan_bidding_vehicle_id = %s """
                    self.env.cr.execute(query_bidding_vehicle_rel,
                                        (bidding_vehicle_id,))
                    get_bidding_vehicle_rel = self._cr.fetchall()
                    if get_bidding_vehicle_rel:
                        for re in get_bidding_vehicle_rel:
                            params = []
                            currency_name = ''
                            query_get_currency_by_company = """ SELECT json_agg(t)
                                                                        FROM (  select cur.name from res_company c join res_currency cur  on cur.id = c.currency_id where c.id = %s ) t """
                            # params_currency.append()
                            self.env.cr.execute(query_get_currency_by_company,
                                                (user.company_id.id,))
                            result_get_currency_by_company = self._cr.fetchall()
                            if result_get_currency_by_company[0][0]:
                                currency_name = result_get_currency_by_company[0][0][0]['name']
                            query_get_bidding_order_json = """ SELECT json_agg(t)
                                                                        FROM ( """
                            query_get_bidding_order = """ SELECT  distinct bidding_order.id,
                                                                         bidding_order.company_id,
                                                                         bidding_order.bidding_order_number,
                                                                         bidding_order.from_depot_id,
                                                                         bidding_order.to_depot_id,
                                                                         bidding_order.total_weight,
                                                                         bidding_order.total_cargo,
                                                                         bidding_order.price,
                                                                         bidding_order.distance,
                                                                         bidding_order.type,
                                                                         bidding_order.status,
                                                                         bidding_order.note,
                                                                         bidding_order.bidding_order_receive_id,
                                                                         bidding_order.bidding_order_return_id,
                                                                         TO_CHAR(bidding_order.create_date,'YYYY-MM-DD HH24:MI:SS') create_date,
                                                                         TO_CHAR(bidding_order.write_date,'YYYY-MM-DD HH24:MI:SS') write_date,
                                                                         bidding_order.bidding_package_id,
                                                                         TO_CHAR(bidding_order.from_receive_time,'YYYY-MM-DD HH24:MI:SS') from_receive_time,
                                                                         TO_CHAR(bidding_order.to_receive_time,'YYYY-MM-DD HH24:MI:SS') to_receive_time,
                                                                         TO_CHAR(bidding_order.from_return_time,'YYYY-MM-DD HH24:MI:SS') from_return_time,
                                                                         TO_CHAR(bidding_order.to_return_time,'YYYY-MM-DD HH24:MI:SS')  to_return_time,
                                                                         TO_CHAR(bidding_order.max_confirm_time,'YYYY-MM-DD HH24:MI:SS') max_confirm_time
                                                                          FROM public.sharevan_bidding_order bidding_order
                                                                          LEFT JOIN sharevan_depot from_depot on from_depot.id = bidding_order.from_depot_id
                                                                          LEFT JOIN sharevan_depot to_depot on to_depot.id = bidding_order.to_depot_id
                                                                          LEFT JOIN sharevan_bidding_order_receive bidding_order_receive on bidding_order.id = bidding_order_receive.bidding_order_id
																		  LEFT JOIN sharevan_bidding_order_return bidding_order_return on bidding_order.id = bidding_order_return.bidding_order_id
                                                                          LEFT JOIN sharevan_bidding_order_sharevan_bidding_vehicle_rel rel on bidding_order.id = rel.sharevan_bidding_order_id
                                                                          LEFT JOIN sharevan_bidding_vehicle bidding_vehicle on bidding_vehicle.id = rel.sharevan_bidding_vehicle_id
                                                                          where bidding_order.company_id = %s and rel.sharevan_bidding_vehicle_id = %s  and
                                                                          (bidding_order_receive.bidding_vehicle_id = %s and bidding_order_return.bidding_vehicle_id =  %s) and
                                                                          (LOWER(from_depot.depot_code)like LOWER('%s%%') or LOWER(from_depot.address)like LOWER('%s%%') or  LOWER(from_depot.street2)like LOWER('%s%%') or LOWER(from_depot.city_name)like LOWER('%s%%')
																		  or LOWER(to_depot.depot_code)like LOWER('%s%%') or LOWER(to_depot.address)like LOWER('%s%%') or  LOWER(to_depot.street2)like LOWER('%s%%') or LOWER(to_depot.city_name)like LOWER('%s%%'))
                                                                          
                                                                          """ % (
                                user.company_id.id, re[1], bidding_vehicle_id, bidding_vehicle_id, txt_search,
                                txt_search,
                                txt_search, txt_search, txt_search, txt_search, txt_search, txt_search)

                            query_get_bidding_order += """  and   (bidding_order.status = '0'  and  bidding_order.type = '1')  """

                            if status == 0:
                                query_get_bidding_order += """ and bidding_order_receive.status = '0' and bidding_order_return.status = '0' """
                            elif status == 1:
                                query_get_bidding_order += """ and bidding_order_receive.status = '1' and bidding_order_return.status = '0' """
                            elif status == 2:
                                query_get_bidding_order += """ and (( bidding_order_receive.status = '1' and bidding_order_return.status = '2' )  
                                                               or ( bidding_order_receive.status = '-1' and bidding_order_return.status = '-1' )) 
                                                                """

                            query_get_bidding_order_json += query_get_bidding_order

                            if offset is not None and limit is not None:
                                if offset > 0:
                                    offset_check = offset * limit
                                    query_get_bidding_order_json += """ Order  by  bidding_order.id DESC OFFSET %s LIMIT %s """ % (
                                        offset_check, limit)
                                    query_has_offset_limit = query_get_bidding_order_json
                                    query_has_offset_limit += """ ) t """

                                else:
                                    query_get_bidding_order_json += """ Order  by  bidding_order.id DESC OFFSET %s LIMIT %s """ % (
                                        offset_check, limit)
                                    query_has_offset_limit = query_get_bidding_order_json
                                    query_get_bidding_order_json += """ ) t """
                                    query_has_offset_limit += """ ) t """
                            else:
                                query_get_bidding_order_json += """ Order  by  bidding_order.id DESC OFFSET 0 LIMIT 10 """
                                query_has_offset_limit = query_get_bidding_order_json
                                query_get_bidding_order_json += """ ) t """

                            total_records = """ select count(*) from (  """

                            total_records += query_get_bidding_order
                            total_records += """ ) t """ % ()

                            self.env.cr.execute(total_records)
                            result_get_total_records = self._cr.fetchall()
                            if result_get_total_records[0]:
                                if result_get_total_records[0][0]:
                                    total = result_get_total_records[0][0]
                                else:
                                    total = 0

                            self.env.cr.execute(query_has_offset_limit)
                            result_get_bidding_order = self._cr.fetchall()
                            if result_get_bidding_order[0][0]:
                                length = len(result_get_bidding_order[0][0])
                                for bidding_order in result_get_bidding_order[0][0]:
                                    obj_arr = []
                                    bidding_order_receive = {}
                                    bidding_order_return = {}

                                    query_get_bidding_vehicle = """ SELECT json_agg(t) FROM (SELECT id, code, lisence_plate, driver_phone_number, driver_name,
                                                                                                                                                                              TO_CHAR(expiry_time,'YYYY-MM-DD HH24:MI:SS') expiry_time, company_id, status, description,
                                                                                                                                                                             id_card, res_partner_id, tonnage, vehicle_type, weight_unit, bidding_vehicle_seq
                                                                                                                                                                             FROM public.sharevan_bidding_vehicle  bidding_vehicle where bidding_vehicle.id = %s ) t """
                                    self.env.cr.execute(query_get_bidding_vehicle, (bidding_vehicle_id,))
                                    result_get_bidding_vehicle = self._cr.fetchall()

                                    bidding_vehicle_arr = []
                                    bidding_order_receive = {}
                                    bidding_order_return = {}

                                    query_get_bidding_vehicle = """ SELECT json_agg(t) FROM (SELECT id, code, lisence_plate, driver_phone_number, driver_name,
                                                                                                                                  TO_CHAR(expiry_time,'YYYY-MM-DD HH24:MI:SS') expiry_time, company_id, status, description,
                                                                                                                                 id_card, res_partner_id, tonnage, vehicle_type, weight_unit, bidding_vehicle_seq
                                                                                                                                 FROM public.sharevan_bidding_vehicle  bidding_vehicle where bidding_vehicle.id = %s ) t """
                                    self.env.cr.execute(query_get_bidding_vehicle, (bidding_vehicle_id,))
                                    result_get_bidding_vehicle = self._cr.fetchall()
                                    params = []
                                    for rec in result_get_bidding_vehicle[0][0]:
                                        query_get_bidding_order_receive = """ SELECT json_agg(t) FROM ( SELECT id, bidding_order_id,  TO_CHAR(from_expected_time,'YYYY-MM-DD HH24:MI:SS') from_expected_time, TO_CHAR(to_expected_time,'YYYY-MM-DD HH24:MI:SS') to_expected_time, depot_id, TO_CHAR(actual_time,'YYYY-MM-DD HH24:MI:SS') actual_time, stock_man_id, status, description, TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS') create_date, bidding_order_vehicle_id
                                                                                                                                   	                                                                          FROM public.sharevan_bidding_order_receive bidding_order_receive where bidding_order_receive.bidding_order_id = %s   and bidding_order_receive.bidding_vehicle_id = %s  ) t """
                                        params.append(bidding_order['id'])
                                        params.append(rec['id'])
                                        self.env.cr.execute(query_get_bidding_order_receive, (params))
                                        result_get_bidding_order_receive = self._cr.fetchall()
                                        if result_get_bidding_order_receive[0][0]:
                                            bidding_order_receive = result_get_bidding_order_receive[0][0][0]

                                        query_get_bidding_order_return = """ SELECT json_agg(t) FROM ( SELECT id, bidding_order_id, TO_CHAR(from_expected_time,'YYYY-MM-DD HH24:MI:SS') from_expected_time,  TO_CHAR(to_expected_time,'YYYY-MM-DD HH24:MI:SS') to_expected_time,TO_CHAR(actual_time,'YYYY-MM-DD HH24:MI:SS') actual_time, depot_id,TO_CHAR(actual_time,'YYYY-MM-DD HH24:MI:SS')  , stock_man_id, status, description,TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS')   create_date, bidding_order_vehicle_id

                                                                                                                              	                                                                        FROM public.sharevan_bidding_order_return  bidding_order_return where bidding_order_return.bidding_order_id = %s  and bidding_order_return.bidding_vehicle_id = %s )  t """
                                        self.env.cr.execute(query_get_bidding_order_return, (params))
                                        result_get_bidding_order_return = self._cr.fetchall()
                                        if result_get_bidding_order_return[0][0]:
                                            bidding_order_return = result_get_bidding_order_return[0][0][0]

                                    bidding_vehicle_param = []
                                    query_get_cargo_bidding_order_vehicle = """ SELECT distinct cargo_id FROM public.sharevan_cargo_bidding_order_vehicle s 
                                                                                                                                               where s.status = '1' and s.bidding_order_id = """
                                    query_get_cargo_bidding_order_vehicle += str(bidding_order['id'])
                                    query_get_cargo_bidding_order_vehicle += """ and s.bidding_vehicle_id = """
                                    query_get_cargo_bidding_order_vehicle += str(bidding_vehicle_id)
                                    self.env.cr.execute(query_get_cargo_bidding_order_vehicle, ())
                                    result_get_cargo_bidding_order_vehicle = self._cr.fetchall()
                                    list_cargo_id = []
                                    list_qr_code = []
                                    size_standard_arr = []
                                    if result_get_cargo_bidding_order_vehicle:
                                        for id in result_get_cargo_bidding_order_vehicle:
                                            cargo = self.env[Constants.SHAREVAN_CARGO].search([('id', '=', id)])
                                            list_qr_code.append(cargo.cargo_number)
                                            list_cargo_id.append(id[0])
                                        query_get_size_standard = """ 
                                        SELECT json_agg(t) FROM (  
                                            select distinct  id, length, width, height,type,from_weight, to_weight, price_id, price, 
                                                size_standard_seq, cargo_price_ids, long_unit, weight_unit 
                                            from sharevan_size_standard size_stand
                                                where size_stand.id in (select cargo.size_id from sharevan_cargo cargo where cargo.id  ::integer in ( """

                                        if list_cargo_id:
                                            for cargo_id in list_cargo_id:
                                                query_get_size_standard += str(cargo_id) + ","
                                            query_get_size_standard = query_get_size_standard[:-1]
                                            query_get_size_standard += "))) t"

                                        self.env.cr.execute(query_get_size_standard, (list_cargo_id))
                                        result_get_size_standard = self._cr.fetchall()
                                        if result_get_size_standard[0][0]:
                                            for rec in result_get_size_standard[0][0]:
                                                query_count_cargo_map_with_size_standard = """ SELECT json_agg(t) FROM ( select count(*) from sharevan_cargo cargo where cargo.id  ::integer in ( """
                                                for cargo_id in list_cargo_id:
                                                    query_count_cargo_map_with_size_standard += str(
                                                        cargo_id) + ","
                                                query_count_cargo_map_with_size_standard = query_count_cargo_map_with_size_standard[
                                                                                           :-1]
                                                query_count_cargo_map_with_size_standard += """ ) and cargo.size_id = %s  """
                                                query_count_cargo_map_with_size_standard += " ) t"
                                                self.env.cr.execute(query_count_cargo_map_with_size_standard,
                                                                    (rec['id'],))
                                                result_count_cargo_map_with_size_standard = self._cr.fetchall()

                                                query_caculate_cargo_total_weight = """ SELECT json_agg(t) FROM ( select sum(weight) from sharevan_cargo cargo where cargo.id  ::integer in ( """
                                                for cargo_id in list_cargo_id:
                                                    query_caculate_cargo_total_weight += str(cargo_id) + ","
                                                query_caculate_cargo_total_weight = query_caculate_cargo_total_weight[
                                                                                    :-1]
                                                query_caculate_cargo_total_weight += """ ) and cargo.size_id = %s  """
                                                query_caculate_cargo_total_weight += " ) t"
                                                self.env.cr.execute(query_caculate_cargo_total_weight,
                                                                    (rec['id'],))
                                                result_query_caculate_cargo_total_weight = self._cr.fetchall()

                                                cargo_vehicle = []
                                                car_vehicle_id = []

                                                query_get_cargo_vehicle_infor = """ 
                                                SELECT json_agg(t) FROM ( 
                                                    SELECT sharevan_cargo.id, sharevan_cargo.cargo_number, sharevan_cargo.from_depot_id, 
                                                        sharevan_cargo.to_depot_id, sharevan_cargo.distance, sharevan_cargo.size_id, 
                                                        sharevan_cargo.weight, sharevan_cargo.description, sharevan_cargo.price, 
                                                        sharevan_cargo.from_latitude, sharevan_cargo.to_latitude, sharevan_cargo.bidding_package_id, 
                                                        sharevan_cargo.from_longitude, sharevan_cargo.to_longitude,size_standard,sharevan_cargo.code,
                                                        size_standard.length, size_standard.width, size_standard.height, 
                                                        size_standard.type, size_standard.from_weight, size_standard.to_weight, 
                                                        size_standard.price_id, size_standard.price,
                                                        size_standard.size_standard_seq, size_standard.long_unit, size_standard.weight_unit
                                                        FROM public.sharevan_cargo 
                                                        join sharevan_size_standard  size_standard on size_standard.id = sharevan_cargo.size_id
                                                        where sharevan_cargo.id ::integer in ( """
                                                for cargo_id in list_cargo_id:
                                                    query_get_cargo_vehicle_infor += str(cargo_id) + ","
                                                query_get_cargo_vehicle_infor = query_get_cargo_vehicle_infor[
                                                                                :-1]
                                                query_get_cargo_vehicle_infor += """ ) and sharevan_cargo.size_id = %s  """
                                                query_get_cargo_vehicle_infor += " ) t"
                                                self.env.cr.execute(query_get_cargo_vehicle_infor,
                                                                    (rec['id'],))
                                                result_query_get_cargo_vehicle_infor = self._cr.fetchall()

                                                if result_query_get_cargo_vehicle_infor[0][0]:
                                                    for cargo in result_query_get_cargo_vehicle_infor[0][0]:
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
                                                            'size_standard': "",
                                                            'qr_code': cargo['cargo_number']

                                                        }
                                                        cargo_vehicle.append(data)

                                                if result_count_cargo_map_with_size_standard[0][0]:
                                                    size_standard_data = {
                                                        'id': rec['id'],
                                                        'length': rec['length'],
                                                        'width': rec['width'],
                                                        'height': rec['height'],
                                                        'type': rec['type'],
                                                        'from_weight': rec['from_weight'],
                                                        'to_weight': rec['to_weight'],
                                                        'price_id': rec['price_id'],
                                                        'price': rec['price'],
                                                        'size_standard_seq': rec['size_standard_seq'],
                                                        'long_unit': rec['long_unit'],
                                                        'weight_unit': rec['weight_unit'],
                                                        'cargos': cargo_vehicle,
                                                        'cargo_quantity':
                                                            result_count_cargo_map_with_size_standard[0][0][0][
                                                                'count'],
                                                        'total_weight':
                                                            result_query_caculate_cargo_total_weight[0][0][0]['sum']

                                                    }
                                                    size_standard_arr.append(size_standard_data)

                                    bidding_vehicle_json = {
                                        'id': result_get_bidding_vehicle[0][0][0]['id'],
                                        'code': result_get_bidding_vehicle[0][0][0]['code'],
                                        'lisence_plate': result_get_bidding_vehicle[0][0][0]['lisence_plate'],
                                        'driver_phone_number': result_get_bidding_vehicle[0][0][0][
                                            'driver_phone_number'],
                                        'driver_name': result_get_bidding_vehicle[0][0][0]['driver_name'],
                                        'expiry_time': result_get_bidding_vehicle[0][0][0]['expiry_time'],
                                        'company_id': result_get_bidding_vehicle[0][0][0]['company_id'],
                                        'status': result_get_bidding_vehicle[0][0][0]['status'],
                                        'description': result_get_bidding_vehicle[0][0][0]['description'],
                                        'vehicle_type': result_get_bidding_vehicle[0][0][0]['vehicle_type'],
                                        'weight_unit': result_get_bidding_vehicle[0][0][0]['weight_unit'],
                                        'cargo_types': size_standard_arr,
                                        'bidding_order_receive': bidding_order_receive,
                                        'bidding_order_return': bidding_order_return
                                    }

                                    bidding_vehicle_arr.append(bidding_vehicle_json)

                                    query_get_from_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.latitude,depot.longitude,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                                                                                                                                              where depot.id =  %s ) t"""
                                    self.env.cr.execute(query_get_from_depot, (bidding_order['from_depot_id'],))
                                    result_get_from_depot = self._cr.fetchall()
                                    depot_from_to = {}
                                    get_from_depot = []
                                    depot_from_id = 0
                                    depot_to_id = 0
                                    index_arr = 0
                                    check = 0

                                    array_length = len(result_get_from_depot)
                                    if array_length > 0:
                                        if result_get_from_depot[0][0]:
                                            get_from_depot = result_get_from_depot[0][0][0]
                                            depot_from_id = get_from_depot['id']

                                    query_get_to_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.latitude,depot.longitude,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                                                                                                                                                                 where     depot.id = %s ) t"""

                                    self.env.cr.execute(query_get_to_depot, (bidding_order['to_depot_id'],))
                                    result_get_to_depot = self._cr.fetchall()
                                    get_to_depot = []
                                    array_length = len(result_get_to_depot)
                                    if array_length > 0:
                                        if result_get_to_depot[0][0]:
                                            get_to_depot = result_get_to_depot[0][0][0]
                                            depot_to_id = get_to_depot['id']
                                    if depot_arr:
                                        for depot in depot_arr:
                                            if depot['depot_from_id'] == depot_from_id and depot[
                                                'depot_to_id'] == depot_to_id:
                                                check = 1
                                                break
                                            else:
                                                index_arr += 1

                                    data = {
                                        'id': bidding_order['id'],
                                        'company_id': bidding_order['company_id'],
                                        'bidding_order_number': bidding_order['bidding_order_number'],
                                        'from_depot': get_from_depot,
                                        'to_depot': get_to_depot,
                                        'total_weight': bidding_order['total_weight'],
                                        'total_cargo': bidding_order['total_cargo'],
                                        'price': bidding_order['price'],
                                        'currency_name': currency_name,
                                        'distance': bidding_order['distance'],
                                        'type': bidding_order['type'],
                                        'status': bidding_order['status'],
                                        'note': bidding_order['note'],
                                        'create_date': bidding_order['create_date'],
                                        'write_date': bidding_order['write_date'],
                                        'bidding_package_id': bidding_order['bidding_package_id'],
                                        'from_receive_time': bidding_order['from_receive_time'],
                                        'to_receive_time': bidding_order['to_receive_time'],
                                        'from_return_time': bidding_order['from_return_time'],
                                        'to_return_time': bidding_order['to_return_time'],
                                        'max_confirm_time': bidding_order['max_confirm_time'],
                                        'bidding_vehicles': bidding_vehicle_json
                                    }

                                    if check > 0:
                                        bidding_order_arr[index_arr].append(data)
                                    else:
                                        obj_arr.append(data)
                                        depot_from_to.update({
                                            'depot_from_id': depot_from_id,
                                            'depot_to_id': depot_to_id
                                        })
                                        depot_arr.append(depot_from_to)
                                        bidding_order_arr.append(obj_arr)
                            else:
                                records = {
                                    'length': length,
                                    'total': total,
                                    'records': []
                                }
                            records = {
                                'length': length,
                                'total': total,
                                'records': bidding_order_arr
                            }
                            simplejson.dumps(records, indent=4, sort_keys=True, default=str)
                            return records
                    else:
                        return {
                            'length': 0,
                            'total': 0,
                            'records': bidding_order_arr
                        }

                else:
                    raise ValidationError(_('Bidding vehicle does not existed!'))

            else:
                raise ValidationError(_('bidding_vehicle_id can not null'))

    def get_list_bidding_order_history(self, from_date, to_date, txt_search, offset, limit):
        uid = http.request.session['uid']
        params = []
        params_for_count = []
        bidding_order_arr = []
        bidding_vehicle_arr = []
        depot_arr = []
        depot_coincident_arr = []
        offset_check = 0
        limit_check = 10
        length = 0
        txt_search = txt_search.lower()
        user = self.env['res.users'].search([('id', '=', uid)])
        bidding_vehicle_id = self.env['sharevan.bidding.vehicle'].search([('res_user_id', '=', uid)]).id

        if user:

            if bidding_vehicle_id:
                query_get_bidding_vehicle_information = """  SELECT json_agg(t)
                                                                                FROM (  select bidding_vehicle.lisence_plate,bidding_vehicle.driver_phone_number from sharevan_bidding_vehicle bidding_vehicle
                                                                               where bidding_vehicle.id = %s ) t """
                self.env.cr.execute(query_get_bidding_vehicle_information,
                                    (bidding_vehicle_id,))
                get_bidding_vehicle_information = self._cr.fetchall()
                if get_bidding_vehicle_information[0][0]:
                    query_bidding_vehicle_rel = """ SELECT sharevan_bidding_order_id, sharevan_bidding_vehicle_id
                                        FROM public.sharevan_bidding_order_sharevan_bidding_vehicle_rel rel where rel.sharevan_bidding_vehicle_id = %s """
                    self.env.cr.execute(query_bidding_vehicle_rel,
                                        (bidding_vehicle_id,))
                    get_bidding_vehicle_rel = self._cr.fetchall()
                    if get_bidding_vehicle_rel:
                        for re in get_bidding_vehicle_rel:
                            params = []
                            currency_name = ''
                            query_get_currency_by_company = """ SELECT json_agg(t)
                                                                                FROM (  select cur.name from res_company c join res_currency cur  on cur.id = c.currency_id where c.id = %s ) t """
                            # params_currency.append()
                            self.env.cr.execute(query_get_currency_by_company,
                                                (user.company_id.id,))
                            result_get_currency_by_company = self._cr.fetchall()
                            if result_get_currency_by_company[0][0]:
                                currency_name = result_get_currency_by_company[0][0][0]['name']
                            query_get_bidding_order_json = """ SELECT json_agg(t)
                                                                                FROM ( """
                            query_get_bidding_order = """ SELECT  distinct bidding_order.id,
                                                                                                     bidding_order.company_id,
                                                                                                     bidding_order.bidding_order_number,
                                                                                                     bidding_order.from_depot_id,
                                                                                                     bidding_order.to_depot_id,
                                                                                                     bidding_order.total_weight,
                                                                                                     bidding_order.total_cargo,
                                                                                                     bidding_order.price,
                                                                                                     bidding_order.distance,
                                                                                                     bidding_order.type,
                                                                                                     bidding_order.status,
                                                                                                     bidding_order.note,
                                                                                                     bidding_order.bidding_order_receive_id,
                                                                                                     bidding_order.bidding_order_return_id,
                                                                                                     TO_CHAR(bidding_order.create_date,'YYYY-MM-DD HH24:MI:SS') create_date,
                                                                                                     TO_CHAR(bidding_order.write_date,'YYYY-MM-DD HH24:MI:SS') write_date,
                                                                                                     bidding_order.bidding_package_id,
                                                                                                     TO_CHAR(bidding_order.from_receive_time,'YYYY-MM-DD HH24:MI:SS') from_receive_time,
                                                                                                     TO_CHAR(bidding_order.to_receive_time,'YYYY-MM-DD HH24:MI:SS') to_receive_time,
                                                                                                     TO_CHAR(bidding_order.from_return_time,'YYYY-MM-DD HH24:MI:SS') from_return_time,
                                                                                                     TO_CHAR(bidding_order.to_return_time,'YYYY-MM-DD HH24:MI:SS')  to_return_time,
                                                                                                     TO_CHAR(bidding_order.max_confirm_time,'YYYY-MM-DD HH24:MI:SS') max_confirm_time
                                                                                                      FROM public.sharevan_bidding_order bidding_order
                                                                                                      LEFT JOIN sharevan_depot from_depot on from_depot.id = bidding_order.from_depot_id
                                                                                                      LEFT JOIN sharevan_depot to_depot on to_depot.id = bidding_order.to_depot_id
                                                                                                      LEFT JOIN sharevan_bidding_order_receive bidding_order_receive on bidding_order.id = bidding_order_receive.bidding_order_id
                            																		  LEFT JOIN sharevan_bidding_order_return bidding_order_return on bidding_order.id = bidding_order_return.bidding_order_id
                                                                                                      LEFT JOIN sharevan_bidding_order_sharevan_bidding_vehicle_rel rel on bidding_order.id = rel.sharevan_bidding_order_id
                                                                                                      LEFT JOIN sharevan_bidding_vehicle bidding_vehicle on bidding_vehicle.id = rel.sharevan_bidding_vehicle_id
                                                                                                      where bidding_order.company_id = %s and rel.sharevan_bidding_vehicle_id = %s  and
                                                                                                      (LOWER(from_depot.depot_code)like LOWER('%s%%') or LOWER(from_depot.address)like LOWER('%s%%') or  LOWER(from_depot.street2)like LOWER('%s%%') or LOWER(from_depot.city_name)like LOWER('%s%%')
                            																		  or LOWER(to_depot.depot_code)like LOWER('%s%%') or LOWER(to_depot.address)like LOWER('%s%%') or  LOWER(to_depot.street2)like LOWER('%s%%') or LOWER(to_depot.city_name)like LOWER('%s%%'))

                                                                                                      """ % (
                                user.company_id.id, re[1], txt_search, txt_search, txt_search, txt_search, txt_search,
                                txt_search, txt_search, txt_search)

                            query_get_bidding_order += """  and   (( bidding_order.status = '2'  and  bidding_order.type = '1' ) or bidding_order.type = '-1')  """
                            if len(from_date) > 0 and len(to_date) > 0:
                                from_date += " 00:00:00 "
                                to_date += " 23:59:59 "
                                query_get_bidding_order += """ and (bidding_order.create_date >= '%s' AND bidding_order.create_date <= '%s') """ % (
                                    from_date, to_date)

                            query_get_bidding_order_json += query_get_bidding_order

                            if offset is not None and limit is not None:
                                if offset > 0:
                                    offset_check = offset * limit
                                    query_get_bidding_order_json += """ Order  by  bidding_order.id DESC  OFFSET %s LIMIT %s """ % (
                                        offset_check, limit)
                                    query_has_offset_limit = query_get_bidding_order_json
                                    query_has_offset_limit += """ ) t """

                                else:
                                    query_get_bidding_order_json += """ Order  by  bidding_order.id DESC OFFSET %s LIMIT %s """ % (
                                        offset_check, limit)
                                    query_has_offset_limit = query_get_bidding_order_json
                                    query_get_bidding_order_json += """ ) t """
                                    query_has_offset_limit += """ ) t """
                            else:
                                query_get_bidding_order_json += """ Order  by  bidding_order.id DESC OFFSET 0 LIMIT 10 """
                                query_has_offset_limit = query_get_bidding_order_json
                                query_get_bidding_order_json += """ ) t """

                            total_records = """ select count(*) from (  """

                            total_records += query_get_bidding_order
                            total_records += """ ) t """ % ()

                            self.env.cr.execute(total_records)
                            result_get_total_records = self._cr.fetchall()
                            if result_get_total_records[0]:
                                if result_get_total_records[0][0]:
                                    total = result_get_total_records[0][0]
                                else:
                                    total = 0

                            self.env.cr.execute(query_has_offset_limit)
                            result_get_bidding_order = self._cr.fetchall()

                            if result_get_bidding_order[0][0]:
                                length = len(result_get_bidding_order[0][0])
                                for bidding_order in result_get_bidding_order[0][0]:

                                    obj_arr = []
                                    bidding_order_receive = {}
                                    bidding_order_return = {}

                                    query_get_bidding_vehicle = """ SELECT json_agg(t) FROM (SELECT id, code, lisence_plate, driver_phone_number, driver_name,
                                                                                                                                              TO_CHAR(expiry_time,'YYYY-MM-DD HH24:MI:SS') expiry_time, company_id, status, description,
                                                                                                                                             id_card, res_partner_id, tonnage, vehicle_type, weight_unit, bidding_vehicle_seq
                                                                                                                                             FROM public.sharevan_bidding_vehicle  bidding_vehicle where bidding_vehicle.id = %s ) t """
                                    self.env.cr.execute(query_get_bidding_vehicle, (bidding_vehicle_id,))
                                    result_get_bidding_vehicle = self._cr.fetchall()

                                    bidding_vehicle_arr = []
                                    bidding_order_receive = {}
                                    bidding_order_return = {}

                                    query_get_bidding_vehicle = """ SELECT json_agg(t) FROM (SELECT id, code, lisence_plate, driver_phone_number, driver_name,
                                                                                                                                                                              TO_CHAR(expiry_time,'YYYY-MM-DD HH24:MI:SS') expiry_time, company_id, status, description,
                                                                                                                                                                             id_card, res_partner_id, tonnage, vehicle_type, weight_unit, bidding_vehicle_seq
                                                                                                                                                                             FROM public.sharevan_bidding_vehicle  bidding_vehicle where bidding_vehicle.id = %s ) t """
                                    self.env.cr.execute(query_get_bidding_vehicle, (bidding_vehicle_id,))
                                    result_get_bidding_vehicle = self._cr.fetchall()

                                    bidding_vehicle_arr = []
                                    bidding_order_receive = {}
                                    bidding_order_return = {}

                                    query_get_bidding_vehicle = """ SELECT json_agg(t) FROM (SELECT id, code, lisence_plate, driver_phone_number, driver_name,
                                                                                                                                  TO_CHAR(expiry_time,'YYYY-MM-DD HH24:MI:SS') expiry_time, company_id, status, description,
                                                                                                                                 id_card, res_partner_id, tonnage, vehicle_type, weight_unit, bidding_vehicle_seq
                                                                                                                                 FROM public.sharevan_bidding_vehicle  bidding_vehicle where bidding_vehicle.id = %s ) t """
                                    self.env.cr.execute(query_get_bidding_vehicle, (bidding_vehicle_id,))
                                    result_get_bidding_vehicle = self._cr.fetchall()
                                    params = []
                                    for rec in result_get_bidding_vehicle[0][0]:
                                        query_get_bidding_order_receive = """ SELECT json_agg(t) FROM ( SELECT id, bidding_order_id,  TO_CHAR(from_expected_time,'YYYY-MM-DD HH24:MI:SS') from_expected_time, TO_CHAR(to_expected_time,'YYYY-MM-DD HH24:MI:SS') to_expected_time, depot_id, TO_CHAR(actual_time,'YYYY-MM-DD HH24:MI:SS') actual_time, stock_man_id, status, description, TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS') create_date, bidding_order_vehicle_id
                                                                                                                                   	                                                                          FROM public.sharevan_bidding_order_receive bidding_order_receive where bidding_order_receive.bidding_order_id = %s   and bidding_order_receive.bidding_vehicle_id = %s  ) t """
                                        params.append(bidding_order['id'])
                                        params.append(rec['id'])
                                        self.env.cr.execute(query_get_bidding_order_receive, (params))
                                        result_get_bidding_order_receive = self._cr.fetchall()
                                        if result_get_bidding_order_receive[0][0]:
                                            bidding_order_receive = result_get_bidding_order_receive[0][0][0]

                                        query_get_bidding_order_return = """ SELECT json_agg(t) FROM ( SELECT id, bidding_order_id, TO_CHAR(from_expected_time,'YYYY-MM-DD HH24:MI:SS') from_expected_time,  TO_CHAR(to_expected_time,'YYYY-MM-DD HH24:MI:SS') to_expected_time,TO_CHAR(actual_time,'YYYY-MM-DD HH24:MI:SS') actual_time, depot_id,TO_CHAR(actual_time,'YYYY-MM-DD HH24:MI:SS')  , stock_man_id, status, description,TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS')   create_date, bidding_order_vehicle_id

                                                                                                                              	                                                                        FROM public.sharevan_bidding_order_return  bidding_order_return where bidding_order_return.bidding_order_id = %s  and bidding_order_return.bidding_vehicle_id = %s )  t """
                                        self.env.cr.execute(query_get_bidding_order_return, (params))
                                        result_get_bidding_order_return = self._cr.fetchall()
                                        if result_get_bidding_order_return[0][0]:
                                            bidding_order_return = result_get_bidding_order_return[0][0][0]

                                    bidding_vehicle_param = []
                                    query_get_cargo_bidding_order_vehicle = """ SELECT distinct cargo_id FROM public.sharevan_cargo_bidding_order_vehicle s 
                                                                                                                                               where s.status = '1' and s.bidding_order_id = """
                                    query_get_cargo_bidding_order_vehicle += str(bidding_order['id'])
                                    query_get_cargo_bidding_order_vehicle += """ and s.bidding_vehicle_id = """
                                    query_get_cargo_bidding_order_vehicle += str(bidding_vehicle_id)
                                    self.env.cr.execute(query_get_cargo_bidding_order_vehicle, ())
                                    result_get_cargo_bidding_order_vehicle = self._cr.fetchall()
                                    list_cargo_id = []
                                    list_qr_code = []
                                    size_standard_arr = []
                                    if result_get_cargo_bidding_order_vehicle:
                                        for id in result_get_cargo_bidding_order_vehicle:
                                            cargo = self.env[Constants.SHAREVAN_CARGO].search([('id', '=', id)])
                                            list_qr_code.append(cargo.cargo_number)
                                            list_cargo_id.append(id[0])
                                        query_get_size_standard = """ 
                                            SELECT json_agg(t) FROM (  
                                                select distinct  id, length, width, height, type, from_weight, to_weight, price_id,
                                                    price, size_standard_seq, cargo_price_ids, long_unit, weight_unit 
                                                from sharevan_size_standard size_stand
                                                    where size_stand.id in (select cargo.size_id from sharevan_cargo cargo where cargo.id  ::integer in ( """

                                        if list_cargo_id:
                                            for cargo_id in list_cargo_id:
                                                query_get_size_standard += str(cargo_id) + ","
                                            query_get_size_standard = query_get_size_standard[:-1]
                                            query_get_size_standard += "))) t"

                                        self.env.cr.execute(query_get_size_standard, (list_cargo_id))
                                        result_get_size_standard = self._cr.fetchall()
                                        if result_get_size_standard[0][0]:
                                            for rec in result_get_size_standard[0][0]:
                                                query_count_cargo_map_with_size_standard = """ SELECT json_agg(t) FROM ( select count(*) from sharevan_cargo cargo where cargo.id  ::integer in ( """
                                                for cargo_id in list_cargo_id:
                                                    query_count_cargo_map_with_size_standard += str(
                                                        cargo_id) + ","
                                                query_count_cargo_map_with_size_standard = query_count_cargo_map_with_size_standard[
                                                                                           :-1]
                                                query_count_cargo_map_with_size_standard += """ ) and cargo.size_id = %s  """
                                                query_count_cargo_map_with_size_standard += " ) t"
                                                self.env.cr.execute(query_count_cargo_map_with_size_standard,
                                                                    (rec['id'],))
                                                result_count_cargo_map_with_size_standard = self._cr.fetchall()

                                                query_caculate_cargo_total_weight = """ SELECT json_agg(t) FROM ( select sum(weight) from sharevan_cargo cargo where cargo.id  ::integer in ( """
                                                for cargo_id in list_cargo_id:
                                                    query_caculate_cargo_total_weight += str(cargo_id) + ","
                                                query_caculate_cargo_total_weight = query_caculate_cargo_total_weight[
                                                                                    :-1]
                                                query_caculate_cargo_total_weight += """ ) and cargo.size_id = %s  """
                                                query_caculate_cargo_total_weight += " ) t"
                                                self.env.cr.execute(query_caculate_cargo_total_weight,
                                                                    (rec['id'],))
                                                result_query_caculate_cargo_total_weight = self._cr.fetchall()

                                                cargo_vehicle = []
                                                car_vehicle_id = []

                                                query_get_cargo_vehicle_infor = """ 
                                                    SELECT json_agg(t) FROM ( 
                                                        SELECT sharevan_cargo.id, sharevan_cargo.cargo_number, sharevan_cargo.from_depot_id, 
                                                            sharevan_cargo.to_depot_id, sharevan_cargo.distance, sharevan_cargo.size_id, 
                                                            sharevan_cargo.weight, sharevan_cargo.description, sharevan_cargo.price, 
                                                            sharevan_cargo.from_latitude, sharevan_cargo.to_latitude, sharevan_cargo.bidding_package_id, 
                                                            sharevan_cargo.from_longitude, sharevan_cargo.to_longitude,size_standard,sharevan_cargo.code,
                                                            size_standard.length, size_standard.width, size_standard.height, 
                                                            size_standard.type, size_standard.from_weight, size_standard.to_weight, size_standard.price_id, size_standard.price,
                                                            size_standard.size_standard_seq, size_standard.long_unit, size_standard.weight_unit
                                                        FROM public.sharevan_cargo 
                                                            join sharevan_size_standard  size_standard on size_standard.id = sharevan_cargo.size_id
                                                        where sharevan_cargo.id ::integer in ( """
                                                for cargo_id in list_cargo_id:
                                                    query_get_cargo_vehicle_infor += str(cargo_id) + ","
                                                query_get_cargo_vehicle_infor = query_get_cargo_vehicle_infor[
                                                                                :-1]
                                                query_get_cargo_vehicle_infor += """ ) and sharevan_cargo.size_id = %s  """
                                                query_get_cargo_vehicle_infor += " ) t"
                                                self.env.cr.execute(query_get_cargo_vehicle_infor,
                                                                    (rec['id'],))
                                                result_query_get_cargo_vehicle_infor = self._cr.fetchall()

                                                if result_query_get_cargo_vehicle_infor[0][0]:
                                                    for cargo in result_query_get_cargo_vehicle_infor[0][0]:
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
                                                            'size_standard': "",
                                                            'qr_code': cargo['cargo_number']

                                                        }
                                                        cargo_vehicle.append(data)

                                                if result_count_cargo_map_with_size_standard[0][0]:
                                                    size_standard_data = {
                                                        'id': rec['id'],
                                                        'length': rec['length'],
                                                        'width': rec['width'],
                                                        'height': rec['height'],
                                                        'type': rec['type'],
                                                        'from_weight': rec['from_weight'],
                                                        'to_weight': rec['to_weight'],
                                                        'price_id': rec['price_id'],
                                                        'price': rec['price'],
                                                        'size_standard_seq': rec['size_standard_seq'],
                                                        'long_unit': rec['long_unit'],
                                                        'weight_unit': rec['weight_unit'],
                                                        'cargos': cargo_vehicle,
                                                        'cargo_quantity':
                                                            result_count_cargo_map_with_size_standard[0][0][0][
                                                                'count'],
                                                        'total_weight':
                                                            result_query_caculate_cargo_total_weight[0][0][0]['sum']

                                                    }
                                                    size_standard_arr.append(size_standard_data)

                                    bidding_vehicle_json = {
                                        'id': result_get_bidding_vehicle[0][0][0]['id'],
                                        'code': result_get_bidding_vehicle[0][0][0]['code'],
                                        'lisence_plate': result_get_bidding_vehicle[0][0][0]['lisence_plate'],
                                        'driver_phone_number': result_get_bidding_vehicle[0][0][0][
                                            'driver_phone_number'],
                                        'driver_name': result_get_bidding_vehicle[0][0][0]['driver_name'],
                                        'expiry_time': result_get_bidding_vehicle[0][0][0]['expiry_time'],
                                        'company_id': result_get_bidding_vehicle[0][0][0]['company_id'],
                                        'status': result_get_bidding_vehicle[0][0][0]['status'],
                                        'description': result_get_bidding_vehicle[0][0][0]['description'],
                                        'vehicle_type': result_get_bidding_vehicle[0][0][0]['vehicle_type'],
                                        'weight_unit': result_get_bidding_vehicle[0][0][0]['weight_unit'],
                                        'cargo_types': size_standard_arr,
                                        'bidding_order_receive': bidding_order_receive,
                                        'bidding_order_return': bidding_order_return
                                    }

                                    bidding_vehicle_arr.append(bidding_vehicle_json)

                                    query_get_from_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.latitude,depot.longitude,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                                                                                                                                                      where depot.id =  %s ) t"""
                                    self.env.cr.execute(query_get_from_depot, (bidding_order['from_depot_id'],))
                                    result_get_from_depot = self._cr.fetchall()
                                    depot_from_to = {}
                                    get_from_depot = []
                                    depot_from_id = 0
                                    depot_to_id = 0
                                    index_arr = 0
                                    check = 0

                                    array_length = len(result_get_from_depot)
                                    if array_length > 0:
                                        if result_get_from_depot[0][0]:
                                            get_from_depot = result_get_from_depot[0][0][0]
                                            depot_from_id = get_from_depot['id']

                                    query_get_to_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.latitude,depot.longitude,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                                                                                                                                                                         where     depot.id = %s ) t"""

                                    self.env.cr.execute(query_get_to_depot, (bidding_order['to_depot_id'],))
                                    result_get_to_depot = self._cr.fetchall()
                                    get_to_depot = []
                                    array_length = len(result_get_to_depot)
                                    if array_length > 0:
                                        if result_get_to_depot[0][0]:
                                            get_to_depot = result_get_to_depot[0][0][0]
                                            depot_to_id = get_to_depot['id']
                                    if depot_arr:
                                        for depot in depot_arr:
                                            if depot['depot_from_id'] == depot_from_id and depot[
                                                'depot_to_id'] == depot_to_id:
                                                check = 1
                                                break
                                            else:
                                                index_arr += 1

                                    data = {
                                        'id': bidding_order['id'],
                                        'company_id': bidding_order['company_id'],
                                        'bidding_order_number': bidding_order['bidding_order_number'],
                                        'from_depot': get_from_depot,
                                        'to_depot': get_to_depot,
                                        'total_weight': bidding_order['total_weight'],
                                        'total_cargo': bidding_order['total_cargo'],
                                        'price': bidding_order['price'],
                                        'currency_name': currency_name,
                                        'distance': bidding_order['distance'],
                                        'type': bidding_order['type'],
                                        'status': bidding_order['status'],
                                        'note': bidding_order['note'],
                                        'create_date': bidding_order['create_date'],
                                        'write_date': bidding_order['write_date'],
                                        'bidding_package_id': bidding_order['bidding_package_id'],
                                        'from_receive_time': bidding_order['from_receive_time'],
                                        'to_receive_time': bidding_order['to_receive_time'],
                                        'from_return_time': bidding_order['from_return_time'],
                                        'to_return_time': bidding_order['to_return_time'],
                                        'max_confirm_time': bidding_order['max_confirm_time'],
                                        'bidding_vehicles': bidding_vehicle_json
                                    }

                                    if check > 0:
                                        bidding_order_arr[index_arr].append(data)
                                    else:
                                        obj_arr.append(data)
                                        depot_from_to.update({
                                            'depot_from_id': depot_from_id,
                                            'depot_to_id': depot_to_id
                                        })
                                        depot_arr.append(depot_from_to)
                                        bidding_order_arr.append(obj_arr)

                            else:
                                records = {
                                    'length': length,
                                    'total': total,
                                    'records': []
                                }
                            records = {
                                'length': length,
                                'total': total,
                                'records': bidding_order_arr
                            }
                            simplejson.dumps(records, indent=4, sort_keys=True, default=str)
                            return records
                    else:
                        return {
                            'length': 0,
                            'total': 0,
                            'records': bidding_order_arr
                        }

                else:
                    raise ValidationError(_('Bidding vehicle does not existed!'))

            else:
                raise ValidationError(_('bidding_vehicle_id can not null'))

    def get_list_bidding_order_history_enterprise(self, from_date, to_date, txt_search, order_by, offset, limit):
        uid = http.request.session['uid']
        params = []
        params_for_count = []
        bidding_order_arr = []
        bidding_vehicle_arr = []
        depot_coincident_arr = []
        offset_check = 0
        limit_check = 10
        length = 0
        txt_search = txt_search.lower()
        user = self.env['res.users'].search([('id', '=', uid)])
        # bidding_vehicle_id = self.env['sharevan.bidding.vehicle'].search([('res_user_id', '=', uid)]).id

        if user:

            params = []
            currency_name = ''
            query_get_currency_by_company = """ SELECT json_agg(t)
                                                                                        FROM (  select cur.name from res_company c join res_currency cur  on cur.id = c.currency_id where c.id = %s ) t """
            # params_currency.append()
            self.env.cr.execute(query_get_currency_by_company,
                                (user.company_id.id,))
            result_get_currency_by_company = self._cr.fetchall()
            if result_get_currency_by_company[0][0]:
                currency_name = result_get_currency_by_company[0][0][0]['name']
            query_get_bidding_order_json = """ SELECT json_agg(t)
                                                                                        FROM ( """
            query_get_bidding_order = """ SELECT  distinct bidding_order.id,
                                                                                                                 bidding_order.company_id,
                                                                                                                 bidding_order.bidding_order_number,
                                                                                                                 bidding_order.from_depot_id,
                                                                                                                 bidding_order.to_depot_id,
                                                                                                                 bidding_order.total_weight,
                                                                                                                 bidding_order.total_cargo,
                                                                                                                 bidding_order.price,
                                                                                                                 bidding_order.distance,
                                                                                                                 bidding_order.type,
                                                                                                                 bidding_order.status,
                                                                                                                 bidding_order.note,
                                                                                                                 bidding_order.bidding_order_receive_id,
                                                                                                                 bidding_order.bidding_order_return_id,
                                                                                                                 TO_CHAR(bidding_order.create_date,'YYYY-MM-DD HH24:MI:SS') create_date,
                                                                                                                 TO_CHAR(bidding_order.write_date,'YYYY-MM-DD HH24:MI:SS') write_date,
                                                                                                                 bidding_order.bidding_package_id,
                                                                                                                 TO_CHAR(bidding_order.from_receive_time,'YYYY-MM-DD HH24:MI:SS') from_receive_time,
                                                                                                                 TO_CHAR(bidding_order.to_receive_time,'YYYY-MM-DD HH24:MI:SS') to_receive_time,
                                                                                                                 TO_CHAR(bidding_order.from_return_time,'YYYY-MM-DD HH24:MI:SS') from_return_time,
                                                                                                                 TO_CHAR(bidding_order.to_return_time,'YYYY-MM-DD HH24:MI:SS')  to_return_time,
                                                                                                                 TO_CHAR(bidding_order.max_confirm_time,'YYYY-MM-DD HH24:MI:SS') max_confirm_time
                                                                                                                  FROM public.sharevan_bidding_order bidding_order
                                                                                                                  LEFT JOIN sharevan_depot from_depot on from_depot.id = bidding_order.from_depot_id
                                                                                                                  LEFT JOIN sharevan_depot to_depot on to_depot.id = bidding_order.to_depot_id
                                                                                                                  LEFT JOIN sharevan_bidding_order_receive bidding_order_receive on bidding_order.id = bidding_order_receive.bidding_order_id
                                        																		  LEFT JOIN sharevan_bidding_order_return bidding_order_return on bidding_order.id = bidding_order_return.bidding_order_id
                                                                                                                  where bidding_order.company_id = %s  and
                                                                                                                  (LOWER(from_depot.depot_code)like LOWER('%s%%') or LOWER(from_depot.address)like LOWER('%s%%') or  LOWER(from_depot.street2)like LOWER('%s%%') or LOWER(from_depot.city_name)like LOWER('%s%%')
                                        																		  or LOWER(to_depot.depot_code)like LOWER('%s%%') or LOWER(to_depot.address)like LOWER('%s%%') or  LOWER(to_depot.street2)like LOWER('%s%%') or LOWER(to_depot.city_name)like LOWER('%s%%'))

                                                                                                                  """ % (
                user.company_id.id, txt_search, txt_search, txt_search, txt_search, txt_search, txt_search,
                txt_search, txt_search)
            query_get_bidding_order += """  and   (( bidding_order.status = '2'  and  bidding_order.type = '1' ) or bidding_order.type = '-1') """
            if len(from_date) > 0 and len(to_date) > 0:
                from_date += " 00:00:00 "
                to_date += " 23:59:59 "
                query_get_bidding_order += """ and (bidding_order.create_date >= '%s' AND bidding_order.create_date <= '%s') """ % (
                    from_date, to_date)

            query_get_bidding_order_json += query_get_bidding_order

            # order by = 1 : Sắp xếp theo giá tăng giần
            # order by = 2 : Sắp xếp theo giá giảm giần
            # order by = 3 : Sắp xếp theo quãng đường tăng dần
            # order by = 4 : Sắp xếp theo  quãng đường giảm dần
            # order by = 5 : Sắp xếp đơn mới nhất
            # order by = 6 : Sắp xếp đơn cũ nhất
            query = """ """
            if order_by:
                if order_by == '1':
                    query = """ order by bidding_order.price ASC """

                if order_by == '2':
                    query = """ order by bidding_order.price DESC """

                if order_by == '3':
                    query = """ order by bidding_order.distance ASC """

                if order_by == '4':
                    query = """ order by bidding_order.distance DESC """

                if order_by == '5':
                    query = """ order by TO_CHAR(bidding_order.create_date, 'YYYY-MM-DD HH24:MI:SS') ASC """

                if order_by == '6':
                    query = """ order by TO_CHAR(bidding_order.create_date, 'YYYY-MM-DD HH24:MI:SS') DESC """
                if order_by == '0':
                    query = """ order by TO_CHAR(bidding_order.create_date, 'YYYY-MM-DD HH24:MI:SS') DESC """

            if offset is not None and limit is not None:
                if offset > 0:
                    offset_check = offset * limit
                    query_get_bidding_order_json += query
                    query_get_bidding_order_json += """  OFFSET %s LIMIT %s   """ % (offset_check, limit)
                    query_has_offset_limit = query_get_bidding_order_json
                    query_has_offset_limit += """ ) t """

                else:
                    query_get_bidding_order_json += query
                    query_get_bidding_order_json += """  OFFSET %s LIMIT %s """ % (offset_check, limit)
                    query_has_offset_limit = query_get_bidding_order_json
                    query_get_bidding_order_json += """ ) t """
                    query_has_offset_limit += """ ) t """
            else:
                query_get_bidding_order_json += query
                query_get_bidding_order_json += """  OFFSET 0 LIMIT 10 """
                query_has_offset_limit = query_get_bidding_order_json
                query_get_bidding_order_json += """ ) t """

            total_records = """ select count(*) from (  """

            total_records += query_get_bidding_order
            total_records += """ ) t """ % ()

            self.env.cr.execute(total_records)
            result_get_total_records = self._cr.fetchall()
            if result_get_total_records[0]:
                if result_get_total_records[0][0]:
                    total = result_get_total_records[0][0]
                else:
                    total = 0

            self.env.cr.execute(query_has_offset_limit)
            result_get_bidding_order = self._cr.fetchall()
            if result_get_bidding_order[0][0]:
                length = len(result_get_bidding_order[0][0])
                for bidding_order in result_get_bidding_order[0][0]:

                    obj_arr = []
                    bidding_order_receive = {}
                    bidding_order_return = {}

                    query_get_bidding_vehicle = """ SELECT json_agg(t) FROM (SELECT bidding_vehicle.id, bidding_vehicle.code, bidding_vehicle.lisence_plate, bidding_vehicle.driver_phone_number, bidding_vehicle.driver_name,
                                                     TO_CHAR(bidding_vehicle.expiry_time,'YYYY-MM-DD HH24:MI:SS') expiry_time, bidding_vehicle.company_id, bidding_vehicle.status, bidding_vehicle.description,
                                                      bidding_vehicle.id_card, bidding_vehicle.res_partner_id, bidding_vehicle.tonnage, bidding_vehicle.vehicle_type, bidding_vehicle.weight_unit, bidding_vehicle.bidding_vehicle_seq
                                                      FROM sharevan_bidding_order_sharevan_bidding_vehicle_rel rel 
                                                      left join sharevan_bidding_vehicle  bidding_vehicle on bidding_vehicle.id =  rel.sharevan_bidding_vehicle_id
                                                      where rel.sharevan_bidding_order_id = %s
                                                      ) t """ % (bidding_order['id'])
                    self.env.cr.execute(query_get_bidding_vehicle)
                    result_get_bidding_vehicle = self._cr.fetchall()

                    bidding_vehicle_arr = []
                    bidding_order_receive = {}
                    bidding_order_return = {}

                    query_get_bidding_order_receive = """ SELECT json_agg(t) FROM ( SELECT id, bidding_order_id, from_expected_time, to_expected_time, depot_id, 
                                                                                                                TO_CHAR(actual_time,'YYYY-MM-DD HH24:MI:SS') actual_time, 
                                                                                                                stock_man_id, status, description, 
                                                                                                                TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS') create_date, 
                                                                                                                TO_CHAR(write_date,'YYYY-MM-DD HH24:MI:SS') write_date, 
                                                                                                                bidding_order_vehicle_id
                                                                                                              	FROM public.sharevan_bidding_order_receive bidding_order_receive 
                                                                                                              	where bidding_order_receive.bidding_order_id = %s  ) t
                                                                                                              	""" % (
                        bidding_order['id'])
                    self.env.cr.execute(query_get_bidding_order_receive)
                    result_get_bidding_order_receive = self._cr.fetchall()
                    if result_get_bidding_order_receive[0][0]:
                        bidding_order_receive = result_get_bidding_order_receive[0][0][0]

                    query_get_bidding_order_return = """ SELECT json_agg(t) FROM ( SELECT id, bidding_order_id, from_expected_time, to_expected_time, depot_id, 
                                                                                                              TO_CHAR(actual_time,'YYYY-MM-DD HH24:MI:SS') actual_time, 
                                                                                                              stock_man_id, status, description,  
                                                                                                              TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS') create_date, 
                                                                                                              TO_CHAR(write_date,'YYYY-MM-DD HH24:MI:SS') write_date, 
                                                                                                              bidding_order_vehicle_id

                                                                                                         	  FROM public.sharevan_bidding_order_return  bidding_order_return 
                                                                                                         	  where bidding_order_return.bidding_order_id = %s  ) t
                                                                                                         	  """ % (
                        bidding_order['id'])

                    self.env.cr.execute(query_get_bidding_order_return)
                    result_get_bidding_order_return = self._cr.fetchall()
                    if result_get_bidding_order_return[0][0]:
                        bidding_order_return = result_get_bidding_order_return[0][0][0]

                    bidding_vehicle_param = []

                    if result_get_bidding_vehicle[0][0]:
                        bidding_vehicle_json = {
                            'id': result_get_bidding_vehicle[0][0][0]['id'],
                            'code': result_get_bidding_vehicle[0][0][0]['code'],
                            'lisence_plate': result_get_bidding_vehicle[0][0][0]['lisence_plate'],
                            'driver_phone_number': result_get_bidding_vehicle[0][0][0][
                                'driver_phone_number'],
                            'driver_name': result_get_bidding_vehicle[0][0][0]['driver_name'],
                            'expiry_time': result_get_bidding_vehicle[0][0][0]['expiry_time'],
                            'company_id': result_get_bidding_vehicle[0][0][0]['company_id'],
                            'status': result_get_bidding_vehicle[0][0][0]['status'],
                            'description': result_get_bidding_vehicle[0][0][0]['description'],
                            'vehicle_type': result_get_bidding_vehicle[0][0][0]['vehicle_type'],
                            'weight_unit': result_get_bidding_vehicle[0][0][0]['weight_unit'],
                            'bidding_order_receive': bidding_order_receive,
                            'bidding_order_return': bidding_order_return
                        }

                    bidding_vehicle_arr.append(bidding_vehicle_json)

                    query_get_from_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.latitude,depot.longitude,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                                                                                                                                                                  where depot.id =  %s ) t"""
                    self.env.cr.execute(query_get_from_depot, (bidding_order['from_depot_id'],))
                    result_get_from_depot = self._cr.fetchall()
                    depot_from_to = {}
                    get_from_depot = []
                    depot_from_id = 0
                    depot_to_id = 0

                    array_length = len(result_get_from_depot)
                    if array_length > 0:
                        if result_get_from_depot[0][0]:
                            get_from_depot = result_get_from_depot[0][0][0]
                            depot_from_id = get_from_depot['id']

                    query_get_to_depot = """ SELECT json_agg(t) FROM (  select distinct  depot.id, depot.name,depot.depot_code,depot.latitude,depot.longitude,depot.address,depot.street,depot.street2,depot.city_name from sharevan_depot depot
                                                                                                                                                                                                                                     where     depot.id = %s ) t"""

                    self.env.cr.execute(query_get_to_depot, (bidding_order['to_depot_id'],))
                    result_get_to_depot = self._cr.fetchall()
                    get_to_depot = []
                    array_length = len(result_get_to_depot)
                    if array_length > 0:
                        if result_get_to_depot[0][0]:
                            get_to_depot = result_get_to_depot[0][0][0]
                            depot_to_id = get_to_depot['id']

                    data = {
                        'id': bidding_order['id'],
                        'company_id': bidding_order['company_id'],
                        'bidding_order_number': bidding_order['bidding_order_number'],
                        'from_depot': get_from_depot,
                        'to_depot': get_to_depot,
                        'total_weight': bidding_order['total_weight'],
                        'total_cargo': bidding_order['total_cargo'],
                        'price': bidding_order['price'],
                        'currency_name': currency_name,
                        'distance': bidding_order['distance'],
                        'type': bidding_order['type'],
                        'status': bidding_order['status'],
                        'note': bidding_order['note'],
                        'create_date': bidding_order['create_date'],
                        'write_date': bidding_order['write_date'],
                        'bidding_package_id': bidding_order['bidding_package_id'],
                        'from_receive_time': bidding_order['from_receive_time'],
                        'to_receive_time': bidding_order['to_receive_time'],
                        'from_return_time': bidding_order['from_return_time'],
                        'to_return_time': bidding_order['to_return_time'],
                        'max_confirm_time': bidding_order['max_confirm_time'],
                        'bidding_vehicles': result_get_bidding_vehicle[0][0]
                    }

                    bidding_order_arr.append(data)

        else:
            return {
                'records': []
            }
        records = {
            'length': length,
            'total': total,
            'records': bidding_order_arr
        }
        simplejson.dumps(records, indent=4, sort_keys=True, default=str)
        return records

    def get_list_bidding_order_shipping_v2(self, offset, limit, txt_search, order_by, status):
        uid = http.request.session['uid']
        params = []
        params_for_count = []
        bidding_order_arr = []
        bidding_vehicle_arr = []
        depot_arr = []
        depot_coincident_arr = []
        offset_check = 0
        limit_check = 10
        length = 0
        txt_search = txt_search.lower()
        params = []
        currency_name = ''
        query_get_currency_by_company = """ 
            SELECT json_agg(t) FROM (  
                select cur.name from res_company c 
                    join res_currency cur  on cur.id = c.currency_id where c.id = %s ) t """
        # params_currency.append()
        self.env.cr.execute(query_get_currency_by_company,
                            (http.request.env.company.id,))
        result_get_currency_by_company = self._cr.fetchall()
        if result_get_currency_by_company[0][0]:
            currency_name = result_get_currency_by_company[0][0][0]['name']
        query_get_bidding_order_json = """ SELECT json_agg(t)
                                                                                        FROM ( """
        query_get_bidding_order = """ 
            SELECT  distinct bidding_order.id,bidding_order.company_id, bidding_order.bidding_order_number,
                bidding_order.from_depot_id,bidding_order.to_depot_id,bidding_order.total_weight,
                bidding_order.total_cargo, bidding_order.price,bidding_order.distance,
                bidding_order.type, bidding_order.status,
                bidding_order.note,
                bidding_order.bidding_order_receive_id,
                bidding_order.bidding_order_return_id,
                TO_CHAR(bidding_order.create_date,'YYYY-MM-DD HH24:MI:SS') create_date,
                TO_CHAR(bidding_order.write_date,'YYYY-MM-DD HH24:MI:SS') write_date,
                bidding_order.bidding_package_id,
                TO_CHAR(bidding_order.from_receive_time,'YYYY-MM-DD HH24:MI:SS') from_receive_time,
                TO_CHAR(bidding_order.to_receive_time,'YYYY-MM-DD HH24:MI:SS') to_receive_time,
                TO_CHAR(bidding_order.from_return_time,'YYYY-MM-DD HH24:MI:SS') from_return_time,
                TO_CHAR(bidding_order.to_return_time,'YYYY-MM-DD HH24:MI:SS')  to_return_time,
                TO_CHAR(bidding_order.max_confirm_time,'YYYY-MM-DD HH24:MI:SS') max_confirm_time,
                bidding_vehicle.id bidding_vehicle_id
            FROM public.sharevan_bidding_order bidding_order
                LEFT JOIN sharevan_depot from_depot on from_depot.id = bidding_order.from_depot_id
                LEFT JOIN sharevan_depot to_depot on to_depot.id = bidding_order.to_depot_id
                LEFT JOIN sharevan_bidding_order_receive bidding_order_receive on bidding_order.id = bidding_order_receive.bidding_order_id
                LEFT JOIN sharevan_bidding_order_return bidding_order_return on bidding_order.id = bidding_order_return.bidding_order_id
                LEFT JOIN sharevan_bidding_order_sharevan_bidding_vehicle_rel rel on bidding_order.id = rel.sharevan_bidding_order_id
                LEFT JOIN sharevan_bidding_vehicle bidding_vehicle on bidding_vehicle.id = rel.sharevan_bidding_vehicle_id
            where bidding_order.company_id = %s and bidding_vehicle.res_user_id = %s   and
                (LOWER(from_depot.depot_code)like LOWER('%s%%') or 
                    LOWER(from_depot.address)like LOWER('%s%%') or  
                    LOWER(from_depot.street2)like LOWER('%s%%') or 
                    LOWER(from_depot.city_name)like LOWER('%s%%') or 
                    LOWER(to_depot.depot_code)like LOWER('%s%%') or 
                    LOWER(to_depot.address)like LOWER('%s%%') or  
                    LOWER(to_depot.street2)like LOWER('%s%%') or 
                    LOWER(to_depot.city_name)like LOWER('%s%%'))
                                                                                          """ % (
            http.request.env.company.id, uid, txt_search,
            txt_search, txt_search, txt_search, txt_search, txt_search, txt_search, txt_search)

        if status == 0:
            query_get_bidding_order += """ and bidding_order_receive.status = '0' and bidding_order_return.status = '0' """
        elif status == 1:
            query_get_bidding_order += """ and bidding_order_receive.status = '1' and bidding_order_return.status = '0' """
        elif status == 2:
            query_get_bidding_order += """ and (( bidding_order_receive.status = '1' and bidding_order_return.status = '2' )  
                                                                               or ( bidding_order_receive.status = '-1' and bidding_order_return.status = '-1' )) 
                                                                                """

        query_get_bidding_order += """ and bidding_order.type = '1' """

        query_get_bidding_order_json += query_get_bidding_order

        if offset is not None and limit is not None:
            if offset > 0:
                offset_check = offset * limit
                if order_by == 0:
                    query_get_bidding_order_json += """ Order  by  TO_CHAR(bidding_order.create_date,'YYYY-MM-DD HH24:MI:SS') DESC OFFSET %s LIMIT %s """ % (
                        offset_check, limit)
                else:
                    query_get_bidding_order_json += """ Order  by  TO_CHAR(bidding_order.create_date,'YYYY-MM-DD HH24:MI:SS') ASC OFFSET %s LIMIT %s """ % (
                        offset_check, limit)
                query_has_offset_limit = query_get_bidding_order_json
                query_has_offset_limit += """ ) t """

            else:
                if order_by == 0:
                    query_get_bidding_order_json += """ Order  by  TO_CHAR(bidding_order.create_date,'YYYY-MM-DD HH24:MI:SS') DESC OFFSET %s LIMIT %s """ % (
                        offset_check, limit)
                else:
                    query_get_bidding_order_json += """ Order  by  TO_CHAR(bidding_order.create_date,'YYYY-MM-DD HH24:MI:SS') ASC OFFSET %s LIMIT %s """ % (
                        offset_check, limit)
                query_has_offset_limit = query_get_bidding_order_json
                query_get_bidding_order_json += """ ) t """
                query_has_offset_limit += """ ) t """
        else:
            if order_by == 0:
                query_get_bidding_order_json += """ Order  by  TO_CHAR(bidding_order.create_date,'YYYY-MM-DD HH24:MI:SS') DESC OFFSET %s LIMIT %s """ % (
                    offset_check, limit)
            else:
                query_get_bidding_order_json += """ Order  by  TO_CHAR(bidding_order.create_date,'YYYY-MM-DD HH24:MI:SS') ASC OFFSET %s LIMIT %s """ % (
                    offset_check, limit)
            query_has_offset_limit = query_get_bidding_order_json
            query_get_bidding_order_json += """ ) t """

        total_records = """ select count(*) from (  """

        total_records += query_get_bidding_order
        total_records += """ ) t """ % ()

        self.env.cr.execute(total_records)
        result_get_total_records = self._cr.fetchall()
        if result_get_total_records[0]:
            if result_get_total_records[0][0]:
                total = result_get_total_records[0][0]
            else:
                total = 0

        self.env.cr.execute(query_has_offset_limit)
        result_get_bidding_order = self._cr.fetchall()
        if result_get_bidding_order[0][0]:
            length = len(result_get_bidding_order[0][0])
            for bidding_order in result_get_bidding_order[0][0]:
                obj_arr = []
                bidding_vehicle_arr = []
                bidding_order_receive = None
                bidding_order_return = None

                query_get_bidding_vehicle = """ 
                SELECT json_agg(t) FROM (SELECT id, code, lisence_plate, driver_phone_number, driver_name,
                      TO_CHAR(expiry_time,'YYYY-MM-DD HH24:MI:SS') expiry_time, company_id, status, description,
                     id_card, res_partner_id, tonnage, vehicle_type, weight_unit, bidding_vehicle_seq
                     FROM public.sharevan_bidding_vehicle  bidding_vehicle where bidding_vehicle.id = %s ) t """
                self.env.cr.execute(query_get_bidding_vehicle, (bidding_order['bidding_vehicle_id'],))
                result_get_bidding_vehicle = self._cr.fetchall()
                params = []
                for rec in result_get_bidding_vehicle[0][0]:
                    query_get_bidding_order_receive = """ 
                        SELECT json_agg(t) FROM ( 
                            SELECT id, bidding_order_id,  
                                TO_CHAR(from_expected_time,'YYYY-MM-DD HH24:MI:SS') from_expected_time, 
                                TO_CHAR(to_expected_time,'YYYY-MM-DD HH24:MI:SS') to_expected_time, depot_id, 
                                TO_CHAR(actual_time,'YYYY-MM-DD HH24:MI:SS') actual_time, stock_man_id, status, 
                                description, TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS') create_date, 
                                bidding_order_vehicle_id
                            FROM public.sharevan_bidding_order_receive bidding_order_receive 
                                where bidding_order_receive.bidding_order_id = %s   
                                and bidding_order_receive.bidding_vehicle_id = %s  ) t """
                    params.append(bidding_order['id'])
                    params.append(rec['id'])
                    self.env.cr.execute(query_get_bidding_order_receive, (params))
                    result_get_bidding_order_receive = self._cr.fetchall()
                    if result_get_bidding_order_receive[0][0]:
                        bidding_order_receive = result_get_bidding_order_receive[0][0][0]

                    query_get_bidding_order_return = """ SELECT json_agg(t) FROM ( SELECT id, bidding_order_id, TO_CHAR(from_expected_time,'YYYY-MM-DD HH24:MI:SS') from_expected_time,  TO_CHAR(to_expected_time,'YYYY-MM-DD HH24:MI:SS') to_expected_time,TO_CHAR(actual_time,'YYYY-MM-DD HH24:MI:SS') actual_time, depot_id,TO_CHAR(actual_time,'YYYY-MM-DD HH24:MI:SS')  , stock_man_id, status, description,TO_CHAR(create_date,'YYYY-MM-DD HH24:MI:SS')   create_date, bidding_order_vehicle_id

                                                                                                                                                                                FROM public.sharevan_bidding_order_return  bidding_order_return where bidding_order_return.bidding_order_id = %s  and bidding_order_return.bidding_vehicle_id = %s )  t """
                    self.env.cr.execute(query_get_bidding_order_return, (params))
                    result_get_bidding_order_return = self._cr.fetchall()
                    if result_get_bidding_order_return[0][0]:
                        bidding_order_return = result_get_bidding_order_return[0][0][0]

                bidding_vehicle_param = []
                query_get_cargo_bidding_order_vehicle = """ SELECT distinct cargo_id FROM public.sharevan_cargo_bidding_order_vehicle s 
                                                                                                                       where s.status = '1' and s.bidding_order_id = """
                query_get_cargo_bidding_order_vehicle += str(bidding_order['id'])
                query_get_cargo_bidding_order_vehicle += """ and s.bidding_vehicle_id = """
                query_get_cargo_bidding_order_vehicle += str(bidding_order['bidding_vehicle_id'])
                self.env.cr.execute(query_get_cargo_bidding_order_vehicle, ())
                result_get_cargo_bidding_order_vehicle = self._cr.fetchall()
                list_cargo_id = []
                list_qr_code = []
                size_standard_arr = []
                if result_get_cargo_bidding_order_vehicle:
                    for id in result_get_cargo_bidding_order_vehicle:
                        cargo = self.env[Constants.SHAREVAN_CARGO].search([('id', '=', id)])
                        list_qr_code.append(cargo.cargo_number)
                        list_cargo_id.append(id[0])
                    query_get_size_standard = """ 
                        SELECT json_agg(t) FROM (  
                            select distinct  id, length, width, height, type,from_weight,
                                to_weight, price_id, price, size_standard_seq, cargo_price_ids, long_unit, weight_unit 
                            from sharevan_size_standard size_stand
                                where size_stand.id in (select cargo.size_id 
                                    from sharevan_cargo cargo where cargo.id  ::integer in ( """
                    if list_cargo_id:
                        for cargo_id in list_cargo_id:
                            query_get_size_standard += str(cargo_id) + ","
                        query_get_size_standard = query_get_size_standard[:-1]
                        query_get_size_standard += "))) t"

                    self.env.cr.execute(query_get_size_standard, (list_cargo_id))
                    result_get_size_standard = self._cr.fetchall()
                    if result_get_size_standard[0][0]:
                        for rec in result_get_size_standard[0][0]:
                            query_count_cargo_map_with_size_standard = """ 
                            SELECT json_agg(t) FROM ( select count(*) 
                                from sharevan_cargo cargo where cargo.id  ::integer in ( """
                            for cargo_id in list_cargo_id:
                                query_count_cargo_map_with_size_standard += str(
                                    cargo_id) + ","
                            query_count_cargo_map_with_size_standard = query_count_cargo_map_with_size_standard[
                                                                       :-1]
                            query_count_cargo_map_with_size_standard += """ ) and cargo.size_id = %s  """
                            query_count_cargo_map_with_size_standard += " ) t"
                            self.env.cr.execute(query_count_cargo_map_with_size_standard,
                                                (rec['id'],))
                            result_count_cargo_map_with_size_standard = self._cr.fetchall()

                            query_caculate_cargo_total_weight = """ 
                                SELECT json_agg(t) FROM ( select sum(weight) 
                                    from sharevan_cargo cargo where cargo.id  ::integer in ( """
                            for cargo_id in list_cargo_id:
                                query_caculate_cargo_total_weight += str(cargo_id) + ","
                            query_caculate_cargo_total_weight = query_caculate_cargo_total_weight[
                                                                :-1]
                            query_caculate_cargo_total_weight += """ ) and cargo.size_id = %s  """
                            query_caculate_cargo_total_weight += " ) t"
                            self.env.cr.execute(query_caculate_cargo_total_weight,
                                                (rec['id'],))
                            result_query_caculate_cargo_total_weight = self._cr.fetchall()

                            cargo_vehicle = []
                            car_vehicle_id = []

                            query_get_cargo_vehicle_infor = """ 
                                SELECT json_agg(t) FROM ( 
                                    SELECT sharevan_cargo.id, sharevan_cargo.cargo_number, sharevan_cargo.from_depot_id, 
                                        sharevan_cargo.to_depot_id, sharevan_cargo.distance, sharevan_cargo.size_id, 
                                        sharevan_cargo.weight, sharevan_cargo.description, sharevan_cargo.price, sharevan_cargo.from_latitude, sharevan_cargo.to_latitude, sharevan_cargo.bidding_package_id, 
                                        sharevan_cargo.from_longitude, sharevan_cargo.to_longitude,size_standard,sharevan_cargo.code,
                                        size_standard.length, size_standard.width, size_standard.height,
                                        size_standard.type, size_standard.from_weight, size_standard.to_weight, size_standard.price_id, size_standard.price,
                                        size_standard.size_standard_seq, size_standard.long_unit, size_standard.weight_unit
                                    FROM public.sharevan_cargo 
                                        join sharevan_size_standard  size_standard on size_standard.id = sharevan_cargo.size_id
                                    where sharevan_cargo.id ::integer in ( """
                            for cargo_id in list_cargo_id:
                                query_get_cargo_vehicle_infor += str(cargo_id) + ","
                            query_get_cargo_vehicle_infor = query_get_cargo_vehicle_infor[
                                                            :-1]
                            query_get_cargo_vehicle_infor += """ ) and sharevan_cargo.size_id = %s  """
                            query_get_cargo_vehicle_infor += " ) t"
                            self.env.cr.execute(query_get_cargo_vehicle_infor,
                                                (rec['id'],))
                            result_query_get_cargo_vehicle_infor = self._cr.fetchall()

                            if result_query_get_cargo_vehicle_infor[0][0]:
                                for cargo in result_query_get_cargo_vehicle_infor[0][0]:
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
                                        'size_standard': "",
                                        'qr_code': cargo['cargo_number']

                                    }
                                    cargo_vehicle.append(data)

                            if result_count_cargo_map_with_size_standard[0][0]:
                                size_standard_data = {
                                    'id': rec['id'],
                                    'length': rec['length'],
                                    'width': rec['width'],
                                    'height': rec['height'],
                                    'type': rec['type'],
                                    'from_weight': rec['from_weight'],
                                    'to_weight': rec['to_weight'],
                                    'price_id': rec['price_id'],
                                    'price': rec['price'],
                                    'size_standard_seq': rec['size_standard_seq'],
                                    'long_unit': rec['long_unit'],
                                    'weight_unit': rec['weight_unit'],
                                    'cargos': cargo_vehicle,
                                    'cargo_quantity':
                                        result_count_cargo_map_with_size_standard[0][0][0][
                                            'count'],
                                    'total_weight':
                                        result_query_caculate_cargo_total_weight[0][0][0]['sum']

                                }
                                size_standard_arr.append(size_standard_data)

                bidding_vehicle_json = {
                    'id': result_get_bidding_vehicle[0][0][0]['id'],
                    'code': result_get_bidding_vehicle[0][0][0]['code'],
                    'lisence_plate': result_get_bidding_vehicle[0][0][0]['lisence_plate'],
                    'driver_phone_number': result_get_bidding_vehicle[0][0][0][
                        'driver_phone_number'],
                    'driver_name': result_get_bidding_vehicle[0][0][0]['driver_name'],
                    'expiry_time': result_get_bidding_vehicle[0][0][0]['expiry_time'],
                    'company_id': result_get_bidding_vehicle[0][0][0]['company_id'],
                    'status': result_get_bidding_vehicle[0][0][0]['status'],
                    'description': result_get_bidding_vehicle[0][0][0]['description'],
                    'vehicle_type': result_get_bidding_vehicle[0][0][0]['vehicle_type'],
                    'weight_unit': result_get_bidding_vehicle[0][0][0]['weight_unit'],
                    'cargo_types': size_standard_arr,
                    'bidding_order_receive': bidding_order_receive,
                    'bidding_order_return': bidding_order_return
                }

                bidding_vehicle_arr.append(bidding_vehicle_json)

                query_get_from_depot = """ 
                    SELECT json_agg(t) FROM (  
                        select distinct  depot.id, depot.name,depot.depot_code,depot.latitude,
                        depot.longitude,depot.address,depot.street,depot.street2,depot.city_name 
                    from sharevan_depot depot 
                        where depot.id =  %s ) t"""
                self.env.cr.execute(query_get_from_depot, (bidding_order['from_depot_id'],))
                result_get_from_depot = self._cr.fetchall()
                depot_from_to = {}
                get_from_depot = []
                depot_from_id = 0
                depot_to_id = 0
                index_arr = 0
                check = 0

                array_length = len(result_get_from_depot)
                if array_length > 0:
                    if result_get_from_depot[0][0]:
                        get_from_depot = result_get_from_depot[0][0][0]
                        depot_from_id = get_from_depot['id']

                query_get_to_depot = """ 
                    SELECT json_agg(t) FROM (  
                        select distinct  depot.id, depot.name,depot.depot_code,depot.latitude,
                            depot.longitude,depot.address,depot.street,depot.street2,depot.city_name 
                        from sharevan_depot depot
                            where     depot.id = %s ) t"""

                self.env.cr.execute(query_get_to_depot, (bidding_order['to_depot_id'],))
                result_get_to_depot = self._cr.fetchall()
                array_length = len(result_get_to_depot)
                if array_length > 0:
                    if result_get_to_depot[0][0]:
                        get_to_depot = result_get_to_depot[0][0][0]
                        depot_to_id = get_to_depot['id']

                data = {
                    'id': bidding_order['id'],
                    'company_id': bidding_order['company_id'],
                    'bidding_order_number': bidding_order['bidding_order_number'],
                    'from_depot': get_from_depot,
                    'to_depot': get_to_depot,
                    'total_weight': bidding_order['total_weight'],
                    'total_cargo': bidding_order['total_cargo'],
                    'price': bidding_order['price'],
                    'currency_name': currency_name,
                    'distance': bidding_order['distance'],
                    'type': bidding_order['type'],
                    'status': bidding_order['status'],
                    'note': bidding_order['note'],
                    'create_date': bidding_order['create_date'],
                    'write_date': bidding_order['write_date'],
                    'bidding_package_id': bidding_order['bidding_package_id'],
                    'from_receive_time': bidding_order['from_receive_time'],
                    'to_receive_time': bidding_order['to_receive_time'],
                    'from_return_time': bidding_order['from_return_time'],
                    'to_return_time': bidding_order['to_return_time'],
                    'max_confirm_time': bidding_order['max_confirm_time'],
                    'bidding_vehicles': bidding_vehicle_json
                }

                bidding_order_arr.append(data)
        else:
            records = {
                'length': length,
                'total': total,
                'records': []
            }
        records = {
            'length': length,
            'total': total,
            'records': bidding_order_arr
        }
        simplejson.dumps(records, indent=4, sort_keys=True, default=str)
        return records



class DepotGoods(models.Model):
    _name = 'sharevan.depot.goods'
    _inherit = 'sharevan.depot.goods'
    _description = 'Sharevan depot goods'
    type = fields.Selection([('0', 'Import'),
                             ('1', 'Export')], required=True)
