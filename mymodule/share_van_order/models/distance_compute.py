import geopy

from mymodule.base_next.controllers.api.file_controller import FileApi
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class DistanceCompute(models.Model):
    _name = 'sharevan.distance.compute'
    _description = 'distance compute'
    _inherit = 'sharevan.distance.compute'

    @api.model
    def create(self, vals):
        if vals.get('name_seq', 'New') == 'New':
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('self.sharevan.distance.compute') or 'New'
        if vals['from_seq'] == vals['to_seq']:
            raise ValidationError('Please check place chosen!')
        result = super(DistanceCompute, self).create(vals)
        return result

    @api.onchange('from_depot_id')
    def onchange_from_depot_id(self):
        for record in self:
            if record['from_depot_id']:
                name_seq = record['from_depot_id']['name_seq']
                if record['type'] == '0' and record['to_depot_id']:
                    name = record['from_depot_id']['name_seq'] + '-' + record['to_depot_id']['name_seq']
                    distance = FileApi.get_distance(record['from_depot_id'].latitude,
                                                    record['from_depot_id'].longitude, record['to_depot_id'].latitude,
                                                    record['to_depot_id'].longitude, False)
                    record.update({'from_seq': name_seq, 'name': name, 'distance': distance})
                else:
                    record.update({'from_seq': name_seq})

    @api.onchange('from_hub_id')
    def onchange_from_hub_id(self):
        for record in self:
            if record['from_hub_id']:
                name_seq = record['from_hub_id']['name_seq']
                if record['type'] == '2' and record['to_hub_id']:
                    name = record['from_hub_id']['name_seq'] + '-' + record['to_hub_id']['name_seq']
                    distance = FileApi.get_distance(record['from_hub_id'].latitude,
                                                    record['from_hub_id'].longitude, record['to_hub_id'].latitude,
                                                    record['to_hub_id'].longitude, False)
                    record.update({'from_seq': name_seq, 'name': name, 'distance': distance})
                elif record['type'] == '3' and record['to_depot_id']:
                    name = record['from_hub_id']['name_seq'] + '-' + record['to_depot_id']['name_seq']
                    distance = FileApi.get_distance(record['from_hub_id'].latitude,
                                                    record['from_hub_id'].longitude, record['to_depot_id'].latitude,
                                                    record['to_depot_id'].longitude, False)
                    record.update({'from_seq': name_seq, 'name': name, 'distance': distance})
                else:
                    record.update({'from_seq': name_seq})

    @api.onchange('to_hub_id')
    def onchange_to_hub_id(self):
        for record in self:
            if record['to_hub_id']:
                name_seq = record['to_hub_id']['name_seq']
                if record['type'] == '2' and record['from_hub_id']:
                    name = record['from_hub_id']['name_seq'] + '-' + record['to_hub_id']['name_seq']
                    distance = FileApi.get_distance(record['from_hub_id'].latitude,
                                                    record['from_hub_id'].longitude, record['to_hub_id'].latitude,
                                                    record['to_hub_id'].longitude, False)
                    record.update({'to_seq': name_seq, 'name': name, 'distance': distance})
                if record['type'] == '1' and record['from_depot_id']:
                    name = record['from_depot_id']['name_seq'] + '-' + record['to_hub_id']['name_seq']
                    distance = FileApi.get_distance(record['from_depot_id'].latitude,
                                                    record['from_depot_id'].longitude, record['to_hub_id'].latitude,
                                                    record['to_hub_id'].longitude, False)
                    record.update({'to_seq': name_seq, 'name': name, 'distance': distance})
                else:
                    record.update({'to_seq': name_seq})

    @api.onchange('min_price','max_price')
    def onchange_price(self):
        for record in self:
            if record['min_price'] < 0:
                raise ValidationError('Min price is bigger than 0')
            if record['max_price'] <0:
                raise ValidationError('Max price is bigger than 0')
            if record['max_price'] and record['min_price'] > record['max_price']:
                raise ValidationError('Min price is smaller than max price')


    @api.onchange('to_depot_id')
    def onchange_to_depot_id(self):
        for record in self:
            if record['to_depot_id']:
                name_seq = record['to_depot_id']['name_seq']
                if record['type'] == '0' and record['from_depot_id']:
                    name = record['from_depot_id']['name_seq'] + '-' + record['to_depot_id']['name_seq']
                    distance = FileApi.get_distance(record['from_depot_id'].latitude,
                                                    record['from_depot_id'].longitude, record['to_depot_id'].latitude,
                                                    record['to_depot_id'].longitude, False)
                    record.update({'to_seq': name_seq, 'name': name, 'distance': distance})
                elif record['type'] == '3' and record['from_hub_id']:
                    name = record['from_hub_id']['name_seq'] + '-' + record['to_depot_id']['name_seq']
                    distance = FileApi.get_distance(record['from_hub_id'].latitude,
                                                    record['from_hub_id'].longitude, record['to_depot_id'].latitude,
                                                    record['to_depot_id'].longitude, False)
                    record.update({'to_seq': name_seq, 'name': name, 'distance': distance})
                else:
                    record.update({'to_seq': name_seq})

    @api.onchange('type')
    def onchange_type(self):
        for record in self:
            record['from_depot_id'] = None
            record['to_depot_id'] = None
            record['from_hub_id'] = None
            record['to_hub_id'] = None
            if record['type'] == '0':
                name = ''
                from_seq = ''
                to_seq = ''
                distance = 0
                if record['from_depot_id']:
                    name = record['from_depot_id']['name_seq']
                    from_seq = name
                    if record['to_depot_id']:
                        name = name + '-' + record['to_depot_id']['name_seq']
                        to_seq = record['to_depot_id']['name_seq']
                        distance = FileApi.get_distance(record['from_depot_id'].latitude,
                                                        record['from_depot_id'].longitude,
                                                        record['to_depot_id'].latitude,
                                                        record['to_depot_id'].longitude, False)
                record.update({'name': name, 'from_seq': from_seq, 'to_seq': to_seq, 'distance': distance})
            if record['type'] == '1':
                name = ''
                from_seq = ''
                to_seq = ''
                distance = 0
                if record['from_depot_id']:
                    name = record['from_depot_id']['name_seq']
                    from_seq = name
                    if record['to_hub_id']:
                        name = name + '-' + record['to_hub_id']['name_seq']
                        to_seq = record['to_hub_id']['name_seq']
                        distance = FileApi.get_distance(record['from_depot_id'].latitude,
                                                        record['from_depot_id'].longitude,
                                                        record['to_hub_id'].latitude,
                                                        record['to_hub_id'].longitude, False)
                record.update({'name': name, 'from_seq': from_seq, 'to_seq': to_seq, 'distance': distance})
            if record['type'] == '2':
                name = ''
                from_seq = ''
                to_seq = ''
                distance = 0
                if record['from_hub_id']:
                    name = record['from_hub_id']['name_seq']
                    from_seq = name
                    if record['to_hub_id']:
                        name = name + '-' + record['to_hub_id']['name_seq']
                        to_seq = record['to_hub_id']['name_seq']
                        distance = FileApi.get_distance(record['from_hub_id'].latitude,
                                                        record['from_hub_id'].longitude,
                                                        record['to_hub_id'].latitude,
                                                        record['to_hub_id'].longitude, False)
                record.update({'name': name, 'from_seq': from_seq, 'to_seq': to_seq, 'distance': distance})
            if record['type'] == '3':
                name = ''
                from_seq = ''
                to_seq = ''
                distance = 0
                if record['from_hub_id']:
                    name = record['from_hub_id']['name_seq']
                    from_seq = name
                    if record['to_depot_id']:
                        name = name + '-' + record['to_depot_id']['name_seq']
                        to_seq = record['to_depot_id']['name_seq']
                        distance = FileApi.get_distance(record['from_hub_id'].latitude,
                                                        record['from_hub_id'].longitude,
                                                        record['to_depot_id'].latitude,
                                                        record['to_depot_id'].longitude, False)
                record.update({'name': name, 'from_seq': from_seq, 'to_seq': to_seq, 'distance': distance})

    def scanning_distance_compute(self, type, zone_id):
        print(type, zone_id)
        # type = '0' quét nội zone hub- hub
        # type = '1' quét nội zone hub- depot
        if type == '0':
            query = """
                select price_normal_min,price_normal_max from sharevan_zone_price 
                    where from_date <= CURRENT_DATE  and (to_date is null or to_date > CURRENT_DATE)
                        and zone_id = %s LIMIT 1
            """
            self._cr.execute(query, (zone_id,))
            price = self._cr.dictfetchall()
            if price:
                hub_query = """
                    select distinct hub.id, hub.name_seq, hub.latitude, hub.longitude from sharevan_area area
                        join sharevan_hub hub on area.hub_id = hub.id 
                    where area.zone_area_id = %s and hub.status = 'running' 
                """
                self._cr.execute(hub_query, (zone_id,))
                hub_record = self._cr.dictfetchall()
                for hub1 in hub_record:
                    for hub2 in hub_record:
                        if hub1['name_seq'] != hub2['name_seq']:
                            # distance = FileApi.get_distance_time(hub1['latitude'],
                            #                                      hub1['longitude'],
                            #                                      hub2['latitude'],
                            #                                      hub2['longitude'], False)
                            coords_1 = (hub1['latitude'], hub1['longitude'])
                            coords_2 = (hub2['latitude'], hub2['longitude'])

                            distance = geopy.distance.distance(coords_1, coords_2).m / 1000
                            min_price = float(price[0]['price_normal_min']) * float(distance),
                            max_price = float(price[0]['price_normal_max']) * float(distance),
                            time = float(distance) / 35 * 60
                            # min_price=float(price[0]['price_normal_min']) * float(distance['distance']),
                            # max_price= float(price[0]['price_normal_max']) * float(distance['distance']),
                            vals = {
                                'name': hub1['name_seq'] + '-' + hub2['name_seq'],
                                'distance': distance,
                                'min_price': min_price[0],
                                'max_price': max_price[0],
                                'from_hub_id': hub1['id'],
                                'to_hub_id':hub2['id'],
                                'from_seq': hub1['name_seq'],
                                'to_seq': hub2['name_seq'],
                                'status': 'running',
                                'type': '2',
                                'name_seq': 'New',
                                # 'time': distance['duration']
                                'time': time
                            }
                            record = super(DistanceCompute, self).create(vals)
                            print(record['id'], record['name'])
                return 'Successful'
            else:
                raise ValidationError('Price not found!')
        elif type == '1':
            query = """
                select price_normal_min,price_normal_max from sharevan_zone_price 
                    where from_date <= CURRENT_DATE  and (to_date is null or to_date > CURRENT_DATE)
                        and zone_id = %s LIMIT 1
                        """
            self._cr.execute(query, (zone_id,))
            price = self._cr.dictfetchall()
            if price:
                hub_query = """
                    select distinct hub.id,hub.name_seq,hub.name, hub.latitude, hub.longitude,
			            depot.name_seq depot_code ,depot.latitude depot_lat,depot.longitude depot_lng,depot.id depot_id
				    from sharevan_area area
                        join sharevan_hub hub on area.hub_id = hub.id 
                        join sharevan_zone zone on zone.id = area.zone_area_id
                        join sharevan_depot depot on depot.id = zone.depot_id
                    where area.zone_area_id = %s and hub.status = 'running'
                            """
                self._cr.execute(hub_query, (zone_id,))
                hub_record = self._cr.dictfetchall()
                depot = {}
                count = 0
                for hub1 in hub_record:
                    if count == 0:
                        depot['latitude'] = hub1['depot_lat']
                        depot['longitude'] = hub1['depot_lng']
                        depot['name_seq'] = hub1['depot_code']
                        depot['id'] = hub1['depot_id']
                        count += 1
                    # distance = FileApi.get_distance_time(hub1['latitude'],
                    #                                      hub1['longitude'],
                    #                                      hub2['latitude'],
                    #                                      hub2['longitude'], False)
                    coords_1 = (hub1['latitude'], hub1['longitude'])
                    coords_2 = (depot['latitude'], depot['longitude'])

                    distance = geopy.distance.distance(coords_1, coords_2).m / 1000
                    min_price = float(price[0]['price_normal_min']) * float(distance),
                    max_price = float(price[0]['price_normal_max']) * float(distance),
                    time = float(distance) / 35 * 60
                    # min_price=float(price[0]['price_normal_min']) * float(distance['distance']),
                    # max_price= float(price[0]['price_normal_max']) * float(distance['distance']),
                    vals = {
                        'name': hub1['name_seq'] + '-' + depot['name_seq'],
                        'distance': distance,
                        'min_price': min_price[0],
                        'max_price': max_price[0],
                        'from_seq': hub1['name_seq'],
                        'to_seq': depot['name_seq'],
                        'from_hub_id': hub1['id'],
                        'to_depot_id': depot['id'],
                        'status': 'running',
                        'type': '3',
                        'name_seq': 'New',
                        # 'time': distance['duration']
                        'time': time
                    }
                    record = super(DistanceCompute, self).create(vals)
                    vals = {
                        'name': depot['name_seq'] + '-' + hub1['name_seq'],
                        'distance': distance,
                        'min_price': min_price[0],
                        'max_price': max_price[0],
                        'from_seq': depot['name_seq'],
                        'to_seq': hub1['name_seq'],
                        'from_depot_id': depot['id'],
                        'to_hub_id': hub1['id'],
                        'status': 'running',
                        'type': '1',
                        'name_seq': 'New',
                        # 'time': distance['duration']
                        'time': time
                    }
                    record = super(DistanceCompute, self).create(vals)
                    print(record['id'], record['name'])
                return 'Successful'
