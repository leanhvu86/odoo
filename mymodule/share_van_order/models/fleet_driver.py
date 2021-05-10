# -*- coding: utf-8 -*-
import base64
import logging
from datetime import datetime, timedelta

import pytz

from mymodule.enum.DriverType import DriverType
from mymodule.enum.StatusEnum import StatusEnum
from mymodule.enum.VehicleConfirmStatus import VehicleConfirmStatus
from odoo import models, http
import json

from odoo.addons.base.models.ir_attachment import IrAttachment
from odoo.http import Response

logger = logging.getLogger(__name__)


class Driver(models.Model):
    _name = 'fleet.driver'
    _inherit = 'fleet.driver'
    MODEL = 'fleet.driver'
    _description = 'Fleet driver'

    def create_driver_code_share(self, driver, files):
        driver_info = json.loads(driver)

        # Xoa may cai key client gui lên nhưng trong model fleet.driver không có đi , không thì không tạo được driver
        del driver_info['image_license_frontsite']
        del driver_info['image_license_backsite']
        del driver_info['image_1920']
        response_data = {}
        if len(files) < 3:
            logger.warn(
                "File not enough !", Driver._name,
                exc_info=True)
            response_data = {
                'message': 'file is not enough !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)

        if 'ssn' not in driver_info or driver_info['ssn'] == '':
            logger.warn(
                "SSN is not null !",
                exc_info=True)
            response_data = {
                'message': 'ssn is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'phone' not in driver_info or driver_info['phone'] == '':
            logger.warn(
                "phone is not null !",
                exc_info=True)
            response_data = {
                'message': 'phone is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'birth_date' not in driver_info or driver_info['birth_date'] == '':
            logger.warn(
                "birth_date is not null !",
                exc_info=True)
            response_data = {
                'message': 'birth of date is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'full_name' not in driver_info or driver_info['full_name'] == '':
            logger.warn(
                "full_name is not null !",
                exc_info=True)
            response_data = {
                'message': 'full name is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        else:
            driver_info['name'] = driver_info['full_name']
        if 'class_driver' not in driver_info or not driver_info['class_driver']:
            logger.warn(
                "class_driver is not null !",
                exc_info=True)
            response_data = {
                'message': 'class driver is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'address' not in driver_info or driver_info['address'] == '':
            logger.warn(
                "address is not null !",
                exc_info=True)
            response_data = {
                'message': 'address is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'no' not in driver_info or driver_info['no'] == '':
            logger.warn(
                "no is not null !",
                exc_info=True)
            response_data = {
                'message': 'no id is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'country_id' not in driver_info or not driver_info['country_id']:
            logger.warn(
                "country_id is not null !",
                exc_info=True)
            response_data = {
                'message': 'country_id is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'hire_date' not in driver_info or driver_info['hire_date'] == '':
            driver_info['hire_date'] = datetime.today()
        driver_info['email'] = 'example@gmail.com'
        # birth_date = datetime.fromtimestamp(driver_info['birth_date'] / 1000.0)
        # driver_info['birth_date'] = birth_date.strftime("%Y-%m-%d")
        driver_info['nationality'] = driver_info['country_id']
        driver_info['driver_type'] = DriverType.CODE_SHARE.value
        driver_info['card_type'] = 'card'
        driver_license_date =  datetime.now(pytz.timezone('GMT')).strftime("%Y-%m-%d")
        next_year =datetime.now() + timedelta(days=2000)
        expires_date = next_year.strftime("%Y-%m-%d")
        driver_info['driver_license_date'] = driver_license_date
        driver_info['expires_date'] = expires_date
        check_driver = """
            select driver.id,company.name from fleet_driver driver
                join res_company company on company.id = driver.company_id
                where (driver.phone = %s or driver.ssn = %s) and driver.status = 'running'
        """
        self._cr.execute(check_driver, (driver_info['phone'], driver_info['ssn'],))
        driver = self._cr.dictfetchall()
        if driver:
            logger.warn(
                "Driver is exist! Please finish contract with company: " + driver[0]['name'],
                exc_info=True)
            response_data = {
                'message': driver[0]['name'],
                'status': StatusEnum.driver_is_exist_with_code.value
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        driver_info['login'] = driver_info['phone']
        driver_info['employee_type']='driver'
        driver_info['driver_type']='code_share'
        record = super(Driver, self).create(driver_info)
        if record:
            file = files[0]
            val = {
                'res_model': 'fleet.driver',
                'mimetype': file.mimetype,
                'name': 'image_1920',
                'res_field': 'image_1920',
                'res_id': record['id'],
                'company_id': http.request.env.company.id,
                'type': 'binary',
                'datas': base64.b64encode(file.read())
            }
            rec = http.request.env[IrAttachment._name].create(val)
            file = files[1]
            val = {
                'res_model': 'fleet.driver',
                'mimetype': file.mimetype,
                'name': 'image_license_frontsite',
                'res_field': 'image_license_frontsite',
                'res_id': record['id'],
                'company_id': http.request.env.company.id,
                'type': 'binary',
                'datas': base64.b64encode(file.read())
            }
            rec = http.request.env[IrAttachment._name].create(val)
            file = files[2]
            val = {
                'res_model': 'fleet.driver',
                'mimetype': file.mimetype,
                'name': 'image_license_backsite',
                'res_field': 'image_license_backsite',
                'res_id': record['id'],
                'company_id': http.request.env.company.id,
                'type': 'binary',
                'datas': base64.b64encode(file.read())
            }
            rec = http.request.env[IrAttachment._name].create(val)
            response_data = {
                'message': 'Create driver successful !',
                'status': 200
            }
            return Response(json.dumps(response_data), content_type="application/json", status=200)
        else:
            logger.warn(
                "driver is exist!",
                exc_info=True)
            response_data['result'] = {
                'message': 'Create driver fail !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)

    def update_deactive_driver(self, driver,files):
        driver_info = json.loads(driver)
        if driver_info['status']=='deactivate':
            record = http.request.env['fleet.driver'].search([('id', '=', driver_info['id'])])
            if record:
                http.request.env['fleet.driver'].deactivate_driver(record)
                response_data = {
                    'message': 'Deactivate driver is successful !',
                    'status': 200
                }
                return Response(json.dumps(response_data), content_type="application/json", status=200)
            else:
                logger.warn(
                    "Driver is not exist !",
                    exc_info=True)
                response_data = {
                    'message': 'Driver is not exist !',
                    'status': 500
                }
                return Response(json.dumps(response_data), content_type="application/json", status=500)
        response_data = {}
        if 'ssn' not in driver_info or driver_info['ssn'] == '':
            logger.warn(
                "SSN is not null !",
                exc_info=True)
            response_data = {
                'message': 'ssn is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'phone' not in driver_info or driver_info['phone'] == '':
            logger.warn(
                "phone is not null !",
                exc_info=True)
            response_data = {
                'message': 'phone is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'birth_date' not in driver_info or driver_info['birth_date'] == '':
            logger.warn(
                "birth_date is not null !",
                exc_info=True)
            response_data = {
                'message': 'birth of date is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'full_name' not in driver_info or driver_info['full_name'] == '':
            logger.warn(
                "full_name is not null !",
                exc_info=True)
            response_data = {
                'message': 'full name is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        else:
            driver_info['name'] = driver_info['full_name']
        if 'class_driver' not in driver_info or not driver_info['class_driver']:
            logger.warn(
                "class_driver is not null !",
                exc_info=True)
            response_data = {
                'message': 'class driver is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'driver_license_date' not in driver_info or driver_info['driver_license_date'] == '':
            logger.warn(
                "driver_license_date is not null !",
                exc_info=True)
            response_data = {
                'message': 'driver license is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'expires_date' not in driver_info or driver_info['expires_date'] == '':
            logger.warn(
                "expires_date is not null !",
                exc_info=True)
            response_data = {
                'message': 'expires date is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'address' not in driver_info or driver_info['address'] == '':
            logger.warn(
                "address is not null !",
                exc_info=True)
            response_data = {
                'message': 'address is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'no' not in driver_info or driver_info['no'] == '':
            logger.warn(
                "driver no is not null !",
                exc_info=True)
            response_data = {
                'message': 'driver no id is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'country_id' not in driver_info or not driver_info['country_id']:
            logger.warn(
                "country_id is not null !",
                exc_info=True)
            response_data = {
                'message': 'country_id is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'hire_date' not in driver_info or driver_info['hire_date'] == '':
            driver_info['hire_date'] = datetime.today()
            driver_info['approved_check'] = VehicleConfirmStatus.Waiting.value

        record = http.request.env['fleet.driver'].search([('id', '=', driver_info['id'])])
        if record:
            record.write(driver_info)
            if len(files)>0:
                file = files[0]
                val = {
                    'res_model': 'fleet.driver',
                    'mimetype': file.mimetype,
                    'name': 'image_1920',
                    'res_field': 'image_1920',
                    'res_id': record['id'],
                    'company_id': http.request.env.company.id,
                    'type': 'binary',
                    'datas': base64.b64encode(file.read())
                }
                rec = http.request.env[IrAttachment._name].create(val)
            response_data = {
                'message': 'Update driver successful ! Please waiting for checking new information',
                'status': 200
            }
            return Response(json.dumps(response_data), content_type="application/json", status=200)
        else:
            logger.warn(
                "driver is exist!",
                exc_info=True)
            response_data['result'] = {
                'message': 'Create driver fail !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)

    def get_driver_license(self, country_id):
        query = """
            select id,name,max_tonnage from sharevan_driver_license where status = 'running'
                and country_id = %s
        """
        http.request.env.cr.execute(query, (country_id,))
        result = http.request._cr.dictfetchall()
        if result:
            return {
                'records': result
            }
        else:
            return {
                'records': []
            }
