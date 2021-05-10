import json
import logging

from addons.web.controllers.auth import AuthSsoApi
from mymodule.base_next.controllers.api.base_method import BaseMethod
from mymodule.enum.ClickActionType import ClickActionType
from mymodule.enum.MessageType import MessageType, NotificationSocketType
from mymodule.enum.NotificationType import NotificationType
from mymodule.enum.RoutingDetailStatus import RoutingDetailStatus
from mymodule.enum.StaffType import StaffType
from mymodule.share_van_order.controllers.api.warehouse import WarehouseApi
from mymodule.share_van_order.models.sharevan_notification import Notification
from odoo import models, fields, http, api
from odoo.addons.base.models.ir_attachment import IrAttachment
from odoo.exceptions import ValidationError
from odoo.http import Response, request
from odoo.tools import config, base64

logger = logging.getLogger(__name__)

INSERT_QUERY = """INSERT INTO res_company_sharevan_career_rel
                           VALUES ( %s , %s ) """


class User(models.Model):
    _name = "res.users"
    _inherit = "res.users"

    fcm_token = fields.Char('Firebase token')
    accept_firebase_notification = fields.Boolean(defaule=True)
    online = fields.Boolean(defaule=True)
    image_256 = fields.Image("Image", related='partner_id.image_256', max_width=128, max_height=128)

    @api.onchange('channel_id')
    def check_channel_id(self):
        for record in self:
            if record['channel_id']:
                me = AuthSsoApi.find_user_by_username(self, request.session.access_token, record['login'])
                roles = AuthSsoApi.find_role(self, request.session.access_token)
                bytesThing = str(me, 'utf-8')
                list_user = json.loads(bytesThing)['content']
                user = AuthSsoApi.update_user_role(self,  request.session.access_token,list_user[0],
                                                   record['channel_id']['channel_code'])
                bytesThing = str(user, 'utf-8')
                data_json = json.dumps(bytesThing)
                if 'error' in data_json:
                    test_msg = {"message": "You have assign channel for user fail", "title": "Change channel fail", "sticky": True}
                    self.env.user.notify_danger(**test_msg)
                else:
                    test_msg = {"message": "You have assign channel for user successfully",
                                "title": "Change channel successfully", "sticky": True}
                    self.env.user.notify_warning(**test_msg)

    def create_individual_customer(self, customer, files):
        vals = json.loads(customer)
        response_data = {}
        if len(files) < 3:
            logger.warn(
                "3 image are required !",
                exc_info=True)
            error = '3 image are required'
            response_data = {
                'message': error,
                'status': 600
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'phone' not in vals:
            logger.warn(
                "Phone number is required !",
                exc_info=True)
            error = 'Phone number is required'
            response_data = {
                'message': error,
                'status': 601
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        uid = request.session.post_sso_authenticate(config['database'], str(config['account_admin']))
        request.env['ir.http'].session_info()['uid'] = uid
        request.env['ir.http'].session_info()['login_success'] = True
        request.env['ir.http'].session_info()
        record = self.env['res.users'].search([('login', '=', vals['phone'])])
        if 'name' not in vals or vals['name'] == None:
            logger.warn(
                "Name number is required !",
                exc_info=True)
            error = 'Name is required'
            response_data = {
                'message': error,
                'status': 602
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'birthday' not in vals or vals['birthday'] == None:
            logger.warn(
                "Birthday number is required !",
                exc_info=True)
            error = 'Birthday is required'
            response_data = {
                'message': error,
                'status': 603
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'gender' not in vals or vals['gender'] == None:
            logger.warn(
                "Gender number is required !",
                exc_info=True)
            error = 'Gender is required'
            response_data = {
                'message': error,
                'status': 604
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'address' not in vals or vals['address'] == '':
            logger.warn(
                "Address number is required !",
                exc_info=True)
            error = 'Address is required'
            response_data = {
                'message': error,
                'status': 605
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'province_id' not in vals or vals['province_id'] == '':
            logger.warn(
                "Province number is required !",
                exc_info=True)
            error = 'Province is required'
            response_data = {
                'message': error,
                'status': 606
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'district_id' not in vals or vals['district_id'] == '':
            logger.warn(
                "District number is required !",
                exc_info=True)
            error = 'District is required'
            response_data = {
                'message': error,
                'status': 607
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if record:
            logger.warn(
                "Account is exist !",
                exc_info=True)
            error = 'Account already exists'
            response_data = {
                'message': error,
                'status': 608
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        currency_query = """
                select currency_id,country_id from res_company where company_type ='2'
            """
        self.env.cr.execute(currency_query,
                            ())
        currency_result = self._cr.dictfetchall()
        city = http.request.env['sharevan.area'].search([('id', '=', vals['province_id'])])
        company = {
            'name': vals['name'] + '_' + vals['phone'],
            'phone': vals['phone'],
            'company_type': '1',
            'customer_type': '2',
            'province': vals['province_id'],
            'currency_id': currency_result[0]['currency_id'],
            'city': city['name'],
            'street': vals['address']
        }
        record = http.request.env['res.company'].create(company)
        print(customer)
        if record:
            http.request.cr.execute(INSERT_QUERY, (record['id'], vals['career_id'],))
            partner_record = http.request.env['res.partner'].search([('company_id', '=', record['id'])])
            staff_record_query = """
                            select id from res_staff_type where code = %s
                        """
            self.env.cr.execute(staff_record_query,
                                (StaffType.CUSTOMER_MANAGER.value,))
            staff_record = self._cr.dictfetchall()
            if record:
                avatar_file = files[0]
                val = {
                    'res_model': 'res.partner',
                    'mimetype': avatar_file.mimetype,
                    'name': 'image_256',
                    'res_field': 'image_256',
                    'res_id': partner_record['id'],
                    'company_id': record['id'],
                    'type': 'binary',
                    'datas': base64.b64encode(avatar_file.read())
                }
                rec = http.request.env[IrAttachment._name].create(val)
                front_file = files[1]
                val = {
                    'res_model': 'res.partner',
                    'mimetype': front_file.mimetype,
                    'name': 'image_identify_frontsite',
                    'res_id': partner_record['id'],
                    'res_field': 'image_identify_frontsite',
                    'company_id': record['id'],
                    'type': 'binary',
                    'datas': base64.b64encode(front_file.read())
                }
                rec = http.request.env[IrAttachment._name].create(val)
                back_image_file = files[2]
                val = {
                    'res_model': 'res.partner',
                    'mimetype': back_image_file.mimetype,
                    'name': 'image_identify_backsite',
                    'res_field': 'image_identify_backsite',
                    'res_id': partner_record['id'],
                    'company_id': record['id'],
                    'type': 'binary',
                    'datas': base64.b64encode(back_image_file.read())
                }
                rec = http.request.env[IrAttachment._name].create(val)

                partner_record.write({'birthday': vals['birthday'], 'gender': vals['gender'], 'name': vals['name'],
                                      'country_id': currency_result[0]['country_id'],
                                      'city': city['name'],'email':vals['email'],
                                      'staff_type': staff_record[0]['id']
                                         , 'street': vals['address']})
                request.session.logout(keep_db=True)
                return Response(response=str('Create company successful'), status=200)
            else:
                request.session.logout(keep_db=True)
                response_data = {
                    'message': 'Staff type are not found!',
                    'status': 609
                }
                return Response(json.dumps(response_data), content_type="application/json", status=500)
        else:
            request.session.logout(keep_db=True)
            response_data = {
                'message': 'Create company fail!',
                'status': 610
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)

    def update_avatar(self, files):
        response_data = {}
        if len(files) == 0:
            logger.warn(
                "3 image are required !",
                exc_info=True)
            response_data['result'] = 'image are required'
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        partner_record = http.request.env['res.partner'].search([('user_id', '=', http.request.env.uid)])
        if partner_record:
            query = """
                    select id from ir_attachment where res_model  = 'res.partner' and res_id = 
                """
            query += str(partner_record['id'])
            query += """ and name like 'image_256%' """
            self._cr.execute(query, ())
            result = self._cr.dictfetchall()
            if result:
                delete_query = """
                        DELETE FROM public.ir_attachment
    	                    WHERE id ::integer in(
                    """
                for id in result:
                    delete_query += str(id['id']) + ","
                delete_query = delete_query[:-1]
                delete_query += ")"
                self._cr.execute(delete_query, ())
            avatar_file = files[0]
            val = {
                'res_model': 'res.partner',
                'mimetype': avatar_file.mimetype,
                'name': 'image_256',
                'res_field': 'image_256',
                'res_id': partner_record['id'],
                # 'company_id': partner_record['company_id'],
                'type': 'binary',
                'datas': base64.b64encode(avatar_file.read())
            }
            rec = http.request.env[IrAttachment._name].create(val)
            logger.warn(
                "update avatar successful !",
                exc_info=True)
            return Response(response=str('update avatar successful'), status=200)
        else:
            logger.warn(
                "user not found !",
                exc_info=True)
            return Response(response=str('user not found'), status=200)

    def create_update_warehouse(self, warehouse_info):
        warehouse = json.loads(warehouse_info)
        response_data = {}
        session, data_json = BaseMethod.check_authorized()
        uid = http.request.env.uid
        if not session and not uid:
            return Response(json.dumps('UN_AUTHORIZED'), content_type="application/json", status=403)
        if not uid:
            warehouse['company_id'] =session['company_id']
        else:
            warehouse['company_id'] = http.request.env.company.id
        if 'status' in warehouse and warehouse['status'] == 'deleted':
            pass
        else:
            if 'name' not in warehouse:
                error = "Name is not null!"
                response_data = {
                    'message': error,
                    'status': 406
                }
                return Response(json.dumps(response_data), content_type="application/json", status=500)
            if 'address' not in warehouse:
                error = "address is not null!"
                response_data = {
                    'message': error,
                    'status': 406
                }
                return Response(json.dumps(response_data), content_type="application/json", status=500)
            if 'phone' not in warehouse:
                error = "phone is not null!"
                response_data = {
                    'message': error,
                    'status': 406
                }
                return Response(json.dumps(response_data), content_type="application/json", status=500)
            # warehouse trong 1 cty khong được trùng phone , address ,name
            check_warehouse_querry = """
                select id,name,address,phone from sharevan_warehouse
                    where (name ilike '%s' or address ilike '%s' or phone ilike '%s') and company_id = %s""" % (
                warehouse['name'], warehouse['address'], warehouse['phone'], warehouse['company_id'])
            http.request.env[WarehouseApi.MODEL]._cr.execute(check_warehouse_querry)
            check_record_check = http.request.env[WarehouseApi.MODEL]._cr.dictfetchall()
            if check_record_check:
                for rec in check_record_check:
                    if 'id' in warehouse and warehouse['id'] and rec['id'] != warehouse['id']:
                        if rec['name'] == warehouse['name']:
                            error = "Name:  %s  already exists !" % (warehouse['name'])
                            response_data = {
                                'message': error,
                                'status': 406
                            }
                            return Response(json.dumps(response_data), content_type="application/json", status=500)
                        if rec['phone'] == warehouse['phone']:
                            error = "Phone:  %s  already exists !" % (warehouse['phone'])
                            response_data = {
                                'message': error,
                                'status': 407
                            }
                            return Response(json.dumps(response_data), content_type="application/json", status=500)
                        if rec['address'] == warehouse['address']:
                            error = "Address:  %s  already exists !" % (warehouse['address'])
                            response_data = {
                                'message': error,
                                'status': 408
                            }
                            return Response(json.dumps(response_data), content_type="application/json", status=500)
                    elif 'id' not in warehouse:
                        if rec['name'] == warehouse['name']:
                            error = "Name:  %s  already exists !" % (warehouse['name'])
                            response_data = {
                                'message': error,
                                'status': 406
                            }
                            return Response(json.dumps(response_data), content_type="application/json", status=500)
                        if rec['phone'] == warehouse['phone']:
                            error = "Phone:  %s  already exists !" % (warehouse['phone'])
                            response_data = {
                                'message': error,
                                'status': 407
                            }
                            return Response(json.dumps(response_data), content_type="application/json", status=500)
                        if rec['address'] == warehouse['address']:
                            error = "Address:  %s  already exists !" % (warehouse['address'])
                            response_data = {
                                'message': error,
                                'status': 408
                            }
                            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'id' in warehouse and warehouse['id']:
            BaseMethod.check_role_access(http.request.env.user, 'sharevan.warehouse', warehouse['id'])
            record = http.request.env['sharevan.warehouse'].search([('id', '=', warehouse['id'])])
            check_query = """
                    select bill.* from sharevan_bill_lading bill
                        join sharevan_bill_lading_detail detail on detail.bill_lading_id = bill.id
                    where bill.status = 'running' and end_date >= CURRENT_DATE 
                        and bill.company_id = %s and detail.warehouse_id =%s
                                """
            http.request.env[WarehouseApi.MODEL]._cr.execute(check_query, (http.request.env.company.id, record['id'],))
            check_record = http.request.env[WarehouseApi.MODEL]._cr.dictfetchall()
            if record and 'status' in warehouse and warehouse['status'] == 'deleted':
                # TO DO - check còn đơn với kho hiện tại không
                if check_record:
                    bill_code = ''
                    for rec in check_record:
                        bill_code += rec['name'] + ', '
                    response_data = {
                        'message': 'You have to stop ordered bill before deleting warehouse: ' + bill_code,
                        'status': 403
                    }
                    return Response(json.dumps(response_data), content_type="application/json", status=500)
                result = record.write({'status': 'deleted'})
                if result:
                    response_data = []
                    logger.warn(
                        "Delete success !",
                        exc_info=True)
                    return Response(json.dumps(response_data), content_type="application/json", status=200)
                else:
                    response_data = {
                        'message': 'Deactivate fail! ',
                        'status': 500
                    }
                    return Response(json.dumps(response_data), content_type="application/json", status=500)
            else:
                # TO DO - kho đã chạy rồi thì ko update địa chỉ. chỉ update tên kho và phone
                vals = {
                    "name": warehouse['name'],
                    "phone": warehouse['phone']
                }
                record.write(vals)
        else:
            if warehouse['ward']:
                warehouse['area_id'] = warehouse['ward']
            else:
                warehouse['area_id'] = warehouse['district']
            if http.request.env.user.channel_id.name != 'customer':
                response_data = {
                    'message': 'You are not allow to create warehouse',
                    'status': 401
                }
                return Response(json.dumps(response_data), content_type="application/json", status=500)

            record = http.request.env['sharevan.warehouse'].create(warehouse)
        if record:
            query = """
                    SELECT area.id, area.name,area.name_seq,area.code , 
                        zone.id zone_id ,zone.name zone_name, zone.name_seq zone_seq,zone.code zone_code,
                        hub.id hub_id,hub.name hub_name, hub.name_seq hub_seq,
                        hub.latitude hub_latitude,hub.longitude hub_longitude, hub.address hub_address,
                        depot.id depot_id,depot.name depot_name,depot.name_seq depot_seq,
                        depot.latitude depot_latitude,depot.longitude depot_longitude, depot.address depot_address
                    from sharevan_area  area 
                        left join sharevan_zone zone on area.zone_area_id = zone.id
                        left join sharevan_hub hub on hub.id= area.hub_id
                        left join sharevan_depot depot on depot.id = zone.depot_id
                    where  area.id = %s and area.status = 'running'
                                        """
            http.request.env[WarehouseApi.MODEL]._cr.execute(query, (warehouse['area_id'],))
            records = http.request.env[WarehouseApi.MODEL]._cr.dictfetchall()
            if records:
                warehouse_info = []
                ware = {
                    'id': record['id'],
                    'warehouse_code': record['warehouse_code'],
                    'name': record['name'],
                    'address': record['address'],
                    'latitude': record['latitude'],
                    'longitude': record['longitude'],
                    'phone': record['phone'],
                    'areaInfo': {
                        'id': records[0]['id'],
                        'name': records[0]['name'],
                        'name_seq': records[0]['name_seq'],
                        'code': records[0]['code'],
                        'zoneInfo': {
                            'id': records[0]['zone_id'],
                            'name': records[0]['zone_name'],
                            'name_seq': records[0]['zone_seq'],
                            'code': records[0]['zone_code'],
                            'depotInfo': {
                                'id': records[0]['depot_id'],
                                'name': records[0]['depot_name'],
                                'name_seq': records[0]['depot_seq'],
                                'address': records[0]['depot_address'],
                                'latitude': records[0]['depot_latitude'],
                                'longitude': records[0]['depot_longitude']
                            }
                        },
                        'hubInfo': {
                            'id': records[0]['hub_id'],
                            'name': records[0]['hub_name'],
                            'name_seq': records[0]['hub_seq'],
                            'address': records[0]['hub_address'],
                            'latitude': records[0]['hub_latitude'],
                            'longitude': records[0]['hub_longitude']
                        }
                    }
                }
                warehouse_info.append(ware)
                response_data = warehouse_info
                return Response(json.dumps(response_data), content_type="application/json", status=200)
            else:
                error = 'Address not support'
                response_data['result'] = error
                return Response(json.dumps(response_data), content_type="application/json", status=500)
        else:
            error = 'Create warehouse fail!'
            response_data['result'] = error
            return Response(json.dumps(response_data), content_type="application/json", status=500)

    def get_allow_area(self, parent_id):
        query_area = """  
                Select id , name, code,parent_id ,country_id
                from sharevan_area
                    where  status = 'running'
                                   """
        param = []
        if parent_id and parent_id > 0:
            query_area += """ and parent_id = %s """
            param.append(parent_id)
        else:
            query_area += """ and location_type = 'province' 
                    and id in (Select parent_id 
    		                        from sharevan_area 
                    where  status = 'running' and location_type = 'district' and hub_id is not null)
    				"""
        self.env.cr.execute(query_area, (param))
        result_area = self._cr.dictfetchall()
        return {
            'records': result_area
        }

    def send_dlp_message(self, message):
        dlp_ids = BaseMethod.get_dlp_employee()
        if len(dlp_ids) > 0:
            try:
                val = {
                    'user_id': dlp_ids,
                    'title': message['title'],
                    'content': message['body'],
                    'res_id': message['res_id'],
                    'res_model': message['res_model'],
                    'click_action': ClickActionType.bill_routing_detail.value,
                    'message_type': MessageType.danger.value,
                    'type': NotificationType.RoutingMessage.value,
                    'object_status': RoutingDetailStatus.Done.value,
                    'item_id': message['res_id'],
                }
                http.request.env[Notification._name].create(val)
                notice = message['body']
                for user in dlp_ids:
                    users = self.env['res.users'].search(
                        [('id', '=', user)])
                    users.notify_info(message=notice, title=NotificationSocketType.NOTIFICATION.value)
            except:
                logger.warn(
                    "Account dlp employee found! But can not send message",
                    Notification._name, message['res_id'],
                    exc_info=True)
        else:
            logger.warn(
                "Account dlp employee not found !",
                exc_info=True)
        return Response(response=str('Send message successful'), status=200)
