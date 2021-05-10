# -*- coding: utf-8 -*-
import base64
import imghdr
import os
import pytz
import json
from io import BytesIO

import googlemaps
import qrcode
import requests

from odoo import http
from odoo.addons.base.models.ir_attachment import IrAttachment
from odoo.tools import ImageProcess, datetime, date_utils, logging, config

_logger = logging.getLogger(__name__)


class FileApi:
    @staticmethod
    def upload_image_file(files, model):
        model = json.loads(model)
        list_ids = []
        for file in files:
            extension = imghdr.what(file)
            if extension not in ('png', 'jpg', 'jpeg'):
                return http.Response("Invalid file type")
            image_base64 = base64.b64encode(file.read())
            odoo_image = ImageProcess(image_base64)
            size = model['size'] or 256
            odoo_image.resize(size, size)
            val = {
                'res_model': model['res_model'],
                'mimetype': file.mimetype,
                'name': file.filename,
                'res_id': model['res_id'],
                'company_id': model['company_id'],
                'type': 'binary',
                'datas': odoo_image.image_base64(95, extension)
            }
            record = http.request.env[IrAttachment._name].create(val)
            list_ids.append(record.id)
        return {
            "records": list_ids
        }
        # try:
        #     extension = multipart.mimetype.split('/')[1]
        #     if extension not in ('png', 'jpg', 'jpeg'):
        #         return False
        #     minetype = multipart.mimetype
        #     file_name = multipart.filename
        #     index_content = multipart.mimetype.split('/')[0]
        #     image_base64 = base64.b64encode(multipart.read())
        # odoo_image = ImageProcess(image_base64)
        # odoo_image.resize(model['size'], model['size'])
        # converted_image = base64.b64decode(odoo_image.image_base64(95, extension))
        # checksum = hashlib.sha1(image_base64).hexdigest()
        # fname, full_path = http.request.env[IrAttachment.model]._get_path('', checksum)
        # file_size = len(converted_image)
        # with open(full_path, 'wb') as f:
        #     f.write(converted_image)

    @staticmethod
    def delete_attachment(fname):
        # without id in domain, search method add res_field = False
        domain = (('id', '<>', -1), ('store_fname', '=', fname))
        att = http.request.env[IrAttachment.model].search(args=domain, limit=1)
        file_path = http.request.env[IrAttachment.model]._full_path(fname)
        if att:
            att.unlink()
            os.remove(file_path)
            return http.Response("Deleted")
        return http.Response("Failed")

    @staticmethod
    def build_qr_code(qr_data):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image()
        temp = BytesIO()
        img.save(temp, format="PNG")
        qr_image = base64.b64encode(temp.getvalue())
        return qr_image

    # hạn chế gọi api nào. vì bây giờ đã sử dụng api của bên routing rồi
    @staticmethod
    def get_distance(from_latitude, from_longitude, to_latitude, to_longitude, way_point):
        try:
            url = config['security_url'] + config['routing_host'] + ':' + config['routing_port'] + '/location'
            payload = {
                'f_lat': from_latitude,
                'f_lon': from_longitude,
                't_lat': to_latitude,
                't_lon': to_longitude
            }
            resps = requests.get(url, params=payload, timeout=10).json()
            return resps
        except:
            _logger.error("There was problem requesting distance!")
            return None


    @staticmethod
    def get_distanceOld(from_latitude, from_longitude, to_latitude, to_longitude, way_point):
        api_key = http.request.env['ir.config_parameter'].sudo().get_param('google.api_key_geocode')
        gmaps = googlemaps.Client(key=api_key)
        now = datetime.now()
        from_co = str(from_latitude) + "," + str(from_longitude)
        to_co = str(to_latitude) + "," + str(to_longitude)
        direction_result = gmaps.directions(from_co, to_co, waypoints=way_point,
                                            mode='driving',
                                            avoid='ferries',
                                            departure_time=now)
        if direction_result:
            if direction_result[0]['legs'][0]:
                if 'distance' in direction_result[0]['legs'][0]:
                    distance = direction_result[0]['legs'][0]['distance']
                    if distance['value'] > 0:
                        return distance['value'] / 1000
                    else:
                        return 0
        else:
            return 0

    # hạn chế gọi api nào. vì bây giờ đã sử dụng api của bên routing rồi
    @staticmethod
    def get_distance_time(from_latitude, from_longitude, to_latitude, to_longitude, way_point):
        time_now = datetime.now(pytz.timezone('UTC')).strftime("%Y-%m-%d %H:%M:%S")
        api_key = http.request.env['ir.config_parameter'].sudo().get_param('google.api_key_geocode')
        gmaps = googlemaps.Client(key=api_key)
        now = datetime.now()
        from_co = str(from_latitude) + "," + str(from_longitude)
        to_co = str(to_latitude) + "," + str(to_longitude)
        direction_result = gmaps.directions(from_co, to_co, waypoints=way_point,
                                            mode='driving',
                                            avoid='ferries',
                                            departure_time=now)
        if direction_result:
            if direction_result[0]['legs'][0]:
                if 'distance' in direction_result[0]['legs'][0]:
                    distance = direction_result[0]['legs'][0]['distance']
                    location = None
                    f_lat = round(from_latitude,3)
                    f_lon = round(from_longitude,3)
                    t_lat = round(to_latitude,3)
                    t_lon = round(to_longitude,3)
                    code = 'FLAT' + str(f_lat) + '-FLON' + str(f_lon) + 'TLAT' + str(t_lat) + '-TLON' + str(t_lon)
                    distance1 = 0
                    duration1 = 0
                    if distance['value'] > 0:
                        distance1 =  distance['value']
                        duration1 = direction_result[0]['legs'][0]['duration']['value'] / 60
                    start_address = direction_result[0]['legs'][0]['start_address'],
                    end_address =  direction_result[0]['legs'][0]['end_address']
                    location = {
                        'from_latitude': f_lat,
                        'from_longtitude': f_lon,
                        'to_latitude': t_lat,
                        'to_longitude': t_lon,
                        'code': code,
                        'cost': distance1,
                        'minutes': duration1,
                        'start_address':  start_address,
                        'end_address': end_address,
                        'create_date': time_now
                    }
                    query = """insert into location_data(code,from_latitude,from_longtitude,to_latitude,to_longitude,cost,minutes,start_address,end_address,create_date) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) """
                    http.request.env['location.data']._cr.execute(query, (code,f_lat,f_lon,t_lat,t_lon,distance1,duration1,start_address, end_address,time_now,))

                    #location = http.request.env['location.data'].sudo().create(location)

                    print(location)
                    return location
        else:
            return None

    @staticmethod
    def convert_list_to_string(org_list, seperator=', '):
        """ Convert list to string, by joining all item in list with given separator.
            Returns the concatenated string """
        return seperator.join(org_list)

    @staticmethod
    def check_driver_waiting_time(from_latitude, from_longitude, to_latitude, to_longitude):
        try:
            url = config['security_url'] + config['routing_host'] + ':' + config['routing_port'] + '/location'
            payload = {
                'f_lat': from_latitude,
                'f_lon': from_longitude,
                't_lat': to_latitude,
                't_lon': to_longitude
            }
            headers = {
                'Authorization': 'Bearer ' + http.request.session.access_token,
                'Accept-Language': 'en',
                'Content-Type': 'application/json'
            }
            resps = requests.get(url, params=payload, timeout=10,headers=headers).json()
        except:
            _logger.error("There was problem requesting distance!")
            return None
        return resps
