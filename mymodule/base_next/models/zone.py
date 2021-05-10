import json
from datetime import datetime
from datetime import timedelta

from mymodule.base_next.controllers.api.base_method import BaseMethod
from mymodule.enum.MessageType import NotificationSocketType
from odoo.tools import float_compare

from odoo import api, models, fields, http, _
from odoo.exceptions import ValidationError


class ShareVanChat(models.Model):
    _description = "Chat"
    _name = 'sharevan.temp'

    name = fields.Char(string='Zone Name')


class ShareVanZone(models.Model):
    _description = "Zone"
    _name = 'sharevan.zone'
    MODEL = 'sharevan.zone'
    _order = 'code'

    name = fields.Char(string='Zone Name', required=True,
                       help='Administrative divisions of a country. E.g. Fed. Zone, Department, Canton')
    code = fields.Char(string='Zone Code', help='The Zone code.', required=True)
    country_id = fields.Many2one('res.country', string='Country')
    status = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted')], 'Status', default="running",
                              help=' 1:running , 2:deleted')
    area_line = fields.Many2many('sharevan.area', help='area in zone', string='Area',
                                 domain=lambda self: "[('status','=','running'),('zone_area_id','=',False),"
                                                     "('country_id', '=', country_id)]")
    depot_id = fields.Many2one('sharevan.depot', string='Depot',
                               domain=[('status', '=', 'running')])
    name_seq = fields.Char(string='Zone Reference', required=True, copy=False, readonly=True,
                           index=True,
                           default=lambda self: _('New'))

    depotInfo = fields.Char(string='depotInfo', store=False)

    @api.onchange('country_id')
    def onchangeDomain(self):
        return {'domain': {
            'area_line': [('country_id', '=', int(self.country_id)), ('zone_area_id', '=', False)]}}

    def unlink(self):
        for id in self.ids:
            self.env.cr.execute(""" 
                            UPDATE sharevan_zone
                            SET status= 'deleted' 
                            WHERE id = %s;  
                                            """, (id,))

        deletedZone = self.env['sharevan.area'].search([('zone_area_id', '=', self.id)])
        for zone in deletedZone:
            record = self.env['sharevan.area'].search([('id', '=', zone.id)])

            record.write({
                'zone_area_id': False
            })

    _sql_constraints = [
        ('name_code_uniq', 'unique(country_id, code)', 'The code of the zone must be unique by country !')
    ]

    @api.model
    def create(self, vals):
        if vals.get('name_seq', 'New') == 'New':
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('self.sharevan.zone') or 'New'
            if vals['code']:
                records = self.env['sharevan.zone'].search([('code', '=', vals['code'])])
                if len(records.ids) > 0:
                    raise ValidationError(
                        _('Zone code existed!'
                          ))
            result = super(ShareVanZone, self).create(vals)
            area_line_ids = vals['area_line'][0][2];
            if area_line_ids:
                for rec in area_line_ids:
                    if rec:
                        self.env['sharevan.area']. \
                            browse(rec).write({'zone_area_id': result['id']})
            if vals['depot_id']:
                self.env['sharevan.depot'].search([('id', '=', vals['depot_id'])]).write({
                    'main_type': True
                })
            return result

    def write(self, vals):
        if 'area_line' in vals:
            area_arr = vals['area_line'][0][2]
            area_arr_del = []
            for area in area_arr:
                area_arr_del.append(area)
            arr_area_id_db = []
            zone_id = self['id']
            # sharevan_zone_area = self.env['sharevan.area.sharevan.zone.rel'].search([('sharevan_zone_id', '=', zone_id)]).id
            self.env.cr.execute("""SELECT  sharevan_area_id
                                FROM public.sharevan_area_sharevan_zone_rel where sharevan_zone_id = %s;   """,
                                (zone_id,))
            # self.env.cr.execute(sql_driver)
            ardata = self.env.cr.fetchall()
            for arr in ardata:
                arr_area_id_db.append(int(arr[0]))
            if len(arr_area_id_db) > len(area_arr):
                arr_del_re = []
                for area_id_db in arr_area_id_db:
                    for area in area_arr:
                        if area_id_db == area:
                            arr_del_re.append(area_id_db)
                for arr_del in arr_del_re:
                    for area_db in arr_area_id_db:
                        if arr_del == area_db:
                            arr_area_id_db.remove(arr_del)

                for area_id in arr_area_id_db:
                    area_obj = self.env['sharevan.area'].search([('id', '=', area_id)])
                    area_obj.write({
                        'zone_area_id': False
                    })
            else:
                arr_del_re = []
                for area in area_arr:
                    for area_id_db in arr_area_id_db:
                        if area_id_db == area:
                            arr_del_re.append(area_id_db)
                for arr_del in arr_del_re:
                    for area_db in area_arr:
                        if arr_del == area_db:
                            area_arr_del.remove(arr_del)

                for area_id in area_arr:
                    area_obj = self.env['sharevan.area'].search([('id', '=', area_id)])
                    area_obj.write({
                        'zone_area_id': zone_id
                    })
        if 'depot_id' in vals and vals['depot_id']:
            self.env['sharevan.depot'].search([('id', '=', vals['depot_id'])]).write({
                'main_type': True
            })
            if self.depot_id:
                self.env['sharevan.depot'].search([('id', '=', self.depot_id.id)]).write({
                    'main_type': False
                })
        if vals['depot_id'] == False:
            if self.depot_id:
                self.env['sharevan.depot'].search([('id', '=', self.depot_id)]).write({
                    'main_type': False
                })
        super(ShareVanZone, self).write(vals)


class ShareVanArea(models.Model):
    _description = "Area"

    _name = 'sharevan.area'
    MODEL = 'sharevan.area'

    _order = 'code'

    country_id = fields.Many2one('res.country', string='Country', required=True)
    name = fields.Char(string='Name', required=True)
    province_name = fields.Char(string='Province name')
    code = fields.Char(string='Code')
    zone_area_id = fields.Many2one('sharevan.zone', string='Zone',
                                   domain=lambda self: "[('country_id', '=', country_id),('status','=','running')]")

    name_seq = fields.Char(string='Area Reference', required=True, copy=False, readonly=True,
                           index=True,
                           default=lambda self: _('New'))

    zoneInfo = fields.Char(string='zoneInfo', store=False)

    location_type = fields.Selection(
        [('province', 'PROVINCE'),
         ('district', 'DISTRICT'),
         ('township', 'TOWNSHIP'),
         ],
        string='Location type',

        help=' 1: tỉnh,thành phố,khu vực ; 2:quận huyện , 3:xã phường thị trấn', required=True
    )
    parent_id = fields.Many2one('sharevan.area', string='parent_id', domain=[('status', '=', 'running')])
    district_name = fields.Char(string='district_name')
    google_name = fields.Char(string='google_name')  # cac ten tren google_map
    # fields.Many2one('share.van.area', string='district name')

    status = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted')], 'Status', default="running",
                              help=' 1:running , 2:deleted')
    hub_id = fields.Many2one('sharevan.hub', string='hub', domain=[('status', '=', 'running')])
    hubInfo = fields.Char(string='hubInfo', store=False)

    @api.onchange('location_type')
    def onchangeDomain(self):
        if self.location_type == 'province':
            self.province_name = self.name
            return {'domain': {'parent_id': [('country_id', '=', int(self.country_id)), ('location_type', '=', '')]}}
        elif self.location_type == 'district':
            return {'domain': {
                'parent_id': [('country_id', '=', int(self.country_id)), ('location_type', '=', 'province')]}}
        elif self.location_type == 'township':
            return {'domain': {
                'parent_id': [('country_id', '=', int(self.country_id)), ('location_type', '=', 'district')]}}

    @api.onchange('parent_id')
    def onchangeDomainParentId(self):
        if self.parent_id.id == False:
            self.province_name = ''
        elif self.location_type == 'township':
            self.district_name = self.parent_id.name
            id = self.parent_id.id
            record = self.env['sharevan.area'].search([('id', '=', id)])
            self.province_name = record.province_name
        else:
            id = self.parent_id.id
            record = self.env['sharevan.area'].search([('id', '=', id)])
            self.province_name = record.province_name

    @api.onchange('country_id')
    def onchangeDomainCountry(self):
        return {'domain': {
            'zone_area_id': [('country_id', '=', int(self.country_id)), ('status', '=', 'running')]}}

    @api.model
    def create(self, vals):
        location_type = vals['location_type']
        parent_id = vals['parent_id']
        province_name = vals['province_name']
        # print(location_type)
        # print(parent_id)
        if location_type == 'district' and parent_id == False or location_type == 'township' and parent_id == False:
            raise ValidationError(_('Please enter the Parent area !'))

        if (province_name == False):
            raise ValidationError(_('Please enter the Pronvince name !'))
        seq = BaseMethod.get_new_sequence('sharevan.area', 'SA', 6, 'name_seq')
        vals['name_seq'] = seq
        res = super(ShareVanArea, self).create(vals)
        if self['zone_area_id']:
            INSERT_QUERY = """INSERT INTO sharevan_area_sharevan_zone_rel
                           VALUES ( %s , %s ) """
            http.request.cr.execute(INSERT_QUERY, (vals['zone_area_id'], res['id'],))
        return res

    def unlink(self):
        for id in self.ids:
            record = self.env['sharevan.area'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })
        return self

    def getZoneByProvince(self, province, district, wards):
        zoneId = 0
        query = """ 
            select zone_area_id 
                from sharevan_area as a
            where (google_name ilike '%' || %s ||'%')
                    """
        if wards:
            google_name = wards + ', ' + district + ', ' + province
        else:
            google_name = district + ', ' + province
        # area = self.search_read(domain=[('google_name', 'ilike', google_name)])
        print(google_name)
        query = """
                SELECT json_agg(t) from (select area.id, area.name,area.name_seq,area.code , 
                    zone.id zone_id ,zone.name zone_name, zone.name_seq zone_seq,zone.code zone_code,
                    hub.id hub_id,hub.name hub_name, hub.name_seq hub_seq,
                    hub.latitude hub_latitude,hub.longitude hub_longitude, hub.address hub_address,
                    depot.id depot_id,depot.name depot_name,depot.name_seq depot_seq,
                    depot.latitude depot_latitude,depot.longitude depot_longitude, depot.address depot_address
                from sharevan_area as area
                    left join sharevan_zone zone on area.zone_area_id = zone.id
                    left join sharevan_hub hub on hub.id= area.hub_id
                    left join sharevan_depot depot on depot.id = zone.depot_id
                where area.google_name ilike %s)t;
                    """
        self._cr.execute(query, (google_name,))
        records = self._cr.fetchall()
        if records[0]:
            if records[0][0]:
                record = records[0][0][0]
                area = {
                    'id': record['id'],
                    'name': record['name'],
                    'name_seq': record['name_seq'],
                    'code': record['code'],
                    'zoneInfo': {
                        'id': record['zone_id'],
                        'name': record['zone_name'],
                        'name_seq': record['zone_seq'],
                        'code': record['zone_code'],
                        'depotInfo': {
                            'id': record['depot_id'],
                            'name': record['depot_name'],
                            'name_seq': record['depot_seq'],
                            'address': record['depot_address'],
                            'latitude': record['depot_latitude'],
                            'longitude': record['depot_longitude']
                        }
                    },
                    'hubInfo': {
                        'id': record['hub_id'],
                        'name': record['hub_name'],
                        'name_seq': record['hub_seq'],
                        'address': record['hub_address'],
                        'latitude': record['hub_latitude'],
                        'longitude': record['hub_longitude']
                    }
                }
                return [area]
            else:
                return []


class ZonePrice(models.Model):
    _name = 'sharevan.zone.price'
    _description = 'zone price'
    MODEL = _name
    weight_unit = fields.Many2one('weight.unit', string='Weight Unit', required=True)
    distance_unit = fields.Many2one('distance.unit', string='Distance Unit', required=True)
    price_normal_min = fields.Float('Price normal min', required=True)
    price_normal_max = fields.Float('Price normal max', required=True)
    price_express_min = fields.Float('Price express min', required=True)
    price_express_max = fields.Float('Price express max', required=True)
    from_date = fields.Date('From Date', required=True)
    to_date = fields.Date('To Date')
    zone_id = fields.Many2one('sharevan.zone', string='Zone', domain=[('status', '=', 'running')])
    # _sql_constraints = [('zone_id_uniq', 'unique(zone_id)', 'chi co 1 ban ghi duy nhat')]

    status = fields.Selection([('running', 'Running'), ('deleted', 'Deleted'), ('draft', 'Draft')], string='Status',
                              default='running', required=True)

    @api.model
    def create(self, vals):
        checkZonePrice = self.env['sharevan.zone.price'].search(
            [('status', '=', 'running'), ('zone_id', '=', vals.get('zone_id'))])
        result = super(ZonePrice, self).create(vals)
        if vals:
            fromDate = datetime.strptime(vals.get('from_date'), "%Y-%m-%d")
            toDate = datetime.strptime(vals.get('to_date'), "%Y-%m-%d")
            priceNorMin = float(vals.get('price_normal_min'))
            priceNorMax = float(vals.get('price_normal_max'))
            priceExpMin = float(vals.get('price_express_min'))
            priceExpMax = float(vals.get('price_express_max'))

            if datetime.now() - timedelta(days=1) > fromDate:
                raise ValidationError(_('Sorry, From Date Must be greater Than Today...'))

            if datetime.now() - timedelta(days=1) > toDate:
                raise ValidationError(_('Sorry, To Date Must be greater Than Today...'))

            if fromDate > toDate:
                raise ValidationError("To date must be greater than From date")

            if float_compare(priceNorMax, priceNorMin, precision_digits=3) == -1:
                print(float_compare(priceNorMax, priceNorMin, precision_digits=3))
                raise ValidationError(_('Sorry, Price Normal Max Must be greater Price Normal Min...'))

            if float_compare(priceExpMax, priceExpMin, precision_digits=3) == -1:
                print(float_compare(priceNorMax, priceNorMin, precision_digits=3))
                raise ValidationError(_('Sorry, Price Express Max Must be greater Price Express Min...'))

            for record in checkZonePrice:
                start_rec = record.from_date
                end_rec = record.to_date
                if (vals.get('status') == 'running') and (
                        (fromDate.date() > start_rec and fromDate.date() <= end_rec) or
                        (fromDate.date() >= start_rec and fromDate.date() <= end_rec) or
                        (toDate.date() >= start_rec and toDate.date() < end_rec) or
                        (toDate.date() <= start_rec and toDate.date() >= end_rec)):
                    raise ValidationError(_('Date range cannot be intersected. Please check again'))

        return result

    def write(self, vals):
        checkZonePrice = self.env['sharevan.zone.price'].search(
            [('status', '=', 'running'), ('zone_id', '=', self.zone_id.id)])
        write_zone_price = super(ZonePrice, self).write(vals)
        if vals:
            fromDate = self.from_date
            toDate = self.to_date
            priceNorMin = self.price_normal_min
            priceNorMax = self.price_normal_max
            priceExpMin = self.price_express_min
            priceExpMax = self.price_express_max

            if datetime.now().date() - timedelta(days=1) > fromDate:
                raise ValidationError(_('Sorry, From Date Must be greater Than Today...'))

            if datetime.now().date() - timedelta(days=1) > toDate:
                raise ValidationError(_('Sorry, To Date Must be greater Than Today...'))

            if fromDate > toDate:
                raise ValidationError("To date must be greater than From date")

            if float_compare(priceNorMax, priceNorMin, precision_digits=3) == -1:
                print(float_compare(priceNorMax, priceNorMin, precision_digits=3))
                raise ValidationError(_('Sorry, Price Normal Max Must be greater Price Normal Min...'))

            if float_compare(priceExpMax, priceExpMin, precision_digits=3) == -1:
                print(float_compare(priceNorMax, priceNorMin, precision_digits=3))
                raise ValidationError(_('Sorry, Price Express Max Must be greater Price Express Min...'))

            print(vals.get('status'))
            for record in checkZonePrice:
                start_rec = record.from_date
                end_rec = record.to_date
                if (vals.get('status') == 'running') and (
                        (start_rec < fromDate <= end_rec) or
                        (start_rec <= fromDate <= end_rec) or
                        (start_rec <= toDate < end_rec) or
                        (start_rec >= toDate >= end_rec)):
                    raise ValidationError(_('Date range cannot be intersected. Please check again'))

        return write_zone_price

    def unlink(self):
        for selfId in self.ids:
            record_ids = self.env['sharevan.zone.price'].search([('id', '=', selfId)])
            record_ids.write({
                'status': 'deleted'
            })
        return self

    @api.constrains('price_normal_min', 'price_normal_max', 'price_express_min', 'price_express_max')
    def check_price(self):
        for record in self:
            message = ""
            if record.price_express_min < 0:
                notice = "Price express min cannot be less than 0"
                message += notice + "\n"
            if record.price_express_max < 0:
                notice = "Price express max cannot be less than 0"
                message += notice + "\n"
            if record.price_normal_min < 0:
                notice = "Price normal min cannot be less than 0"
                message += notice + "\n"
            if record.price_normal_max < 0:
                notice = "Price normal max cannot be less than 0"
                message += notice + "\n"
            message = message.strip()
            if message:
                raise ValidationError(message)


class DistanceUnit(models.Model):
    _name = "distance.unit"
    MODEL = "distance.unit"
    _description = 'Unit measuring distance'
    _order = 'code'

    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
    status = fields.Selection([('running', 'Running'), ('deleted', 'Deleted')], string='Status',
                              default='running')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Distance Unit Code must be unique!')
    ]


class WeightUnit(models.Model):
    _name = "weight.unit"
    _inherit = "weight.unit"
    MODEL = "weight.unit"
    _description = 'Unit measuring weight'
    _order = 'code'

    @api.model
    def create(self, vals):
        seq = BaseMethod.get_new_sequence('weight.unit', 'WUN', 6, 'code')
        vals['code'] = seq
        result = super(WeightUnit, self).create(vals)
        return result

    def unlink(self):
        for id in self.ids:
            record = self.env['weight.unit'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })
        return self

    def js_python_method(self, model_name, active_id):
        return self


class VolumeUnit(models.Model):
    _name = "volume.unit"
    MODEL = "volume.unit"
    _inherit = "volume.unit"

    @api.model
    def create(self, vals):
        seq = BaseMethod.get_new_sequence('volume.unit', 'VOV', 6, 'volume_code')
        vals['volume_code'] = seq
        result = super(VolumeUnit, self).create(vals)
        return result

    def unlink(self):
        for id in self.ids:
            record = self.env['volume.unit'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })
        return self


class ParcelUnit(models.Model):
    _name = "parcel.unit"
    MODEL = "parcel.unit"

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
    status = fields.Selection([('running', 'Running'), ('deleted', 'deleted')], string='Status',
                              default='running')

    @api.model
    def create(self, vals):
        seq = BaseMethod.get_new_sequence('parcel.unit', 'PU', 6, 'code')
        vals['code'] = seq
        result = super(ParcelUnit, self).create(vals)
        return result

    def unlink(self):
        for id in self.ids:
            record = self.env['parcel.unit'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })
        return self


class ShareVanWarningType(models.Model):
    _description = "Warning type"
    _name = 'sharevan.warning.type'

    name = fields.Char(string='Type Name', required=True)
    code = fields.Char(string='Code', required=True, copy=False, readonly=True,
                       index=True,
                       default=lambda self: _('New'))

    status = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted')], 'Status', default="running",
                              help=' 1:running , 2:deleted')
    description = fields.Text(string='Description')

    @api.model
    def create(self, vals):
        if vals.get('code', 'New') == 'New':
            vals['code'] = self.env['ir.sequence'].next_by_code(
                'self.warning.type.code') or 'New'
        result = super(ShareVanWarningType, self).create(vals)
        return result

    def unlink(self):
        for id in self.ids:
            record = self.env['sharevan.warning.type'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })
        return self
