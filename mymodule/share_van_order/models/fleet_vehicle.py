import base64
import json
import logging
from datetime import datetime

from mymodule.base_next.controllers.api.file_controller import FileApi
from mymodule.enum.VehicleStateStatus import VehicleStateStatus
from odoo import api, models, fields, _, http
from odoo.addons.base.models.ir_attachment import IrAttachment
from odoo.exceptions import ValidationError
from odoo.http import Response

logger = logging.getLogger(__name__)


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'
    _name = 'fleet.vehicle'
    _description = 'Vehicle'
    _order = 'license_plate asc, acquisition_date asc'

    def create_vehicle_code_share(self, vehicleInfo, files):
        vehicle_info = json.loads(vehicleInfo)
        if len(files)== 0:
            logger.warn(
                "File not enough !", FleetVehicle._name,
                exc_info=True)
            response_data = {
                'message': 'file is not enough !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        check_vehicle = """
            select veh.id from fleet_vehicle veh
                where (veh.license_plate = %s or veh.vin_sn = %s) and veh.company_id = %s
                """
        self._cr.execute(check_vehicle,
                         (vehicle_info['license_plate'], vehicle_info['vin_sn'], http.request.env.company.id,))
        vehicle = self._cr.dictfetchall()
        if vehicle:
            response_data={
                'status':500,
                'message':'Vehicle is exist already  with this license plate and vin sn!'
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'model_id' not in vehicle_info or vehicle_info['model_id'] == '':
            logger.warn(
                "model_id is not null !",
                exc_info=True)
            response_data = {
                'message': 'model id is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'license_plate' not in vehicle_info or vehicle_info['license_plate'] == '':
            logger.warn(
                "license_plate is not null !",
                exc_info=True)
            response_data = {
                'message': 'license plate is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'vin_sn' not in vehicle_info or vehicle_info['vin_sn'] == '':
            logger.warn(
                "vin_sn is not null !",
                exc_info=True)
            response_data = {
                'message': 'vin_sn is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'tonage_id' not in vehicle_info or vehicle_info['tonage_id'] == '':
            logger.warn(
                "tonage_id is not null !",
                exc_info=True)
            response_data = {
                'message': 'tonage id is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'vehicle_registration' not in vehicle_info or vehicle_info['vehicle_registration'] == '':
            logger.warn(
                "vehicle_registration is not null !",
                exc_info=True)
            response_data = {
                'message': 'vehicle_registration is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'vehicle_inspection' not in vehicle_info or vehicle_info['vehicle_inspection'] == '':
            logger.warn(
                "vehicle_inspection is not null !",
                exc_info=True)
            response_data = {
                'message': 'vehicle_inspection is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'vehicle_type' not in vehicle_info or vehicle_info['vehicle_type'] == '':
            logger.warn(
                "vehicle_type is not null !",
                exc_info=True)
            response_data = {
                'message': 'vehicle_type is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'registration_date' not in vehicle_info or vehicle_info['registration_date'] == '':
            logger.warn(
                "registration_date is not null !",
                exc_info=True)
            response_data = {
                'message': 'registration_date is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'inspection_date' not in vehicle_info or vehicle_info['inspection_date'] == '':
            logger.warn(
                "inspection_date is not null !",
                exc_info=True)
            response_data = {
                'message': 'inspection_date is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        if 'inspection_due_date' not in vehicle_info or vehicle_info['inspection_due_date'] == '':
            logger.warn(
                "inspection_due_date is not null !",
                exc_info=True)
            response_data = {
                'message': 'inspection_due_date is not null !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        from_date = datetime.strptime(str(vehicle_info['inspection_date']), '%Y-%m-%d')
        to_date = datetime.strptime(str(vehicle_info['inspection_due_date']), '%Y-%m-%d')
        if from_date<to_date:
            logger.warn(
                "inspection_due_date is bigger than inspection_date !",
                exc_info=True)
            response_data = {
                'message': 'inspection_due_date is bigger than inspection_date !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        availableState = self.env['fleet.vehicle.state'].search([('code', '=', VehicleStateStatus.Available.value)],
                                                                limit=1).id
        vehicle_info['state_id'] = availableState
        vehicle_info['active_type']='code_share'
        model_brand = http.request.env['fleet.vehicle.model'].search([('id', '=', vehicle_info['model_id'])])
        if not model_brand:
            logger.warn(
                "model_brand is not found !",
                exc_info=True)
            response_data = {
                'message': 'model_brand is not found !',
                'status': 500
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)
        else:
            vehicle_info['seats'] = model_brand['seats']
            vehicle_info['capacity'] = model_brand['capacity']
            vehicle_info['horsepower'] = model_brand['horsepower']
            vehicle_info['engine_size'] = model_brand['engine_size']
            vehicle_info['overall_dimensions'] = model_brand['overall_dimensions']
            vehicle_info['dimensions_inside_box'] = model_brand['dimensions_inside_box']
            vehicle_info['standard_long'] = model_brand['standard_long']
            vehicle_info['engine_name'] = model_brand['engine_name']
            vehicle_info['number_cylinders'] = model_brand['number_cylinders']
            vehicle_info['color'] = model_brand['color']
            vehicle_info['model_year'] = model_brand['model_year']
            vehicle_info['fuel_type'] = model_brand['fuel_type']
        record = super(FleetVehicle, self).create(vehicle_info)
        if record:
            file = files[0]
            val = {
                'res_model': 'fleet.vehicle',
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
                'status': 200,
                'message': 'Create vehicle successful!'
            }
            return Response(json.dumps(response_data), content_type="application/json", status=200)
        else:
            response_data = {
                'status': 500,
                'message': 'Create vehicle fail!'
            }
            return Response(json.dumps(response_data), content_type="application/json", status=500)

    def get_vehicle_model(self):
        query = """
            select model.id,model.name ,brand.name brand_name from fleet_vehicle_model model 
                join fleet_vehicle_model_brand brand on brand.id = model.brand_id
        """
        self._cr.execute(query, ())
        model = self._cr.dictfetchall()
        return {
            'records': model
        }
