# -*- coding: utf-8 -*-
import json as simplejson
from odoo import http


class FleetDriverApi:
    MODEL = 'fleet.driver'

    @staticmethod
    def getDriverLocation(routing_plan_day_id):
        query = """
            SELECT json_agg(t)
                FROM ( 
                SELECT  driver.id, driver.name,
                    driver.phone, driver.mobile,
                    driver.driver_code, driver.full_name, veh.id vehicle_id,
                    veh.latitude,veh.longitude,veh.license_plate,veh.name vehicle_name
                FROM 	sharevan_routing_plan_day plan 
                    join  public.fleet_driver driver on plan.driver_id = driver.id
                    join fleet_vehicle veh on veh.id = plan.vehicle_id
                where plan.id = %s )t; 
        """
        http.request.env[FleetDriverApi.MODEL]._cr.execute(query, (routing_plan_day_id,))
        records = http.request.env[FleetDriverApi.MODEL]._cr.fetchall()
        jsonRe = []
        if records[0]:
            if records[0][0]:
                content = {
                    'id': records[0][0][0]['vehicle_id'],
                    'latitude': records[0][0][0]['latitude'],
                    'longitude': records[0][0][0]['longitude'],
                    'license_plate': records[0][0][0]['license_plate'],
                    'name': records[0][0][0]['vehicle_name'],
                    'driver': {
                        'id': records[0][0][0]['id'],
                        'driver_code': records[0][0][0]['driver_code'],
                        'name': records[0][0][0]['name'],
                        'full_name': records[0][0][0]['full_name'],
                        'phone': records[0][0][0]['phone'],
                    }
                }
                jsonRe.append(content)
                result = {
                    'length': 1,
                    'records': jsonRe
                }
                simplejson.dumps(result, indent=4, sort_keys=True, default=str)
                return result
        return {
            'length': 0,
            'records': jsonRe
        }

    @staticmethod
    def bidding_location_vehicle(bidding_vehicle_ids):
        query = """
            SELECT   veh.id vehicle_id,
                veh.latitude,veh.longitude,veh.license_plate,veh.name vehicle_name,
                driver.name, driver.phone
            FROM sharevan_bidding_vehicle bidding_veh
                JOIN fleet_vehicle veh on veh.id = bidding_veh.vehicle_id
                JOIN fleet_driver driver on driver.id = bidding_veh.driver_id
                    where bidding_veh.id ::Integer in ( 
            """
        if bidding_vehicle_ids:
            for vehicle in bidding_vehicle_ids:
                query += str(vehicle) + ","
            query = query[:-1]
            query += ")"
        http.request.env[FleetDriverApi.MODEL]._cr.execute(query, ())
        records = http.request.env[FleetDriverApi.MODEL]._cr.dictfetchall()
        jsonRe = []
        if records:
            for record in records:
                content = {
                    'id': record['vehicle_id'],
                    'latitude': record['latitude'],
                    'longitude': record['longitude'],
                    'license_plate': record['license_plate'],
                    'name': record['vehicle_name'],
                    'driver': {
                        'name': record['name'],
                        'phone': record['phone']
                    }
                }
                jsonRe.append(content)
            result = {
                'length': len(jsonRe),
                'records': jsonRe
            }
            simplejson.dumps(result, indent=4, sort_keys=True, default=str)
            return result
        return {
            'length': 0,
            'records': jsonRe
        }
