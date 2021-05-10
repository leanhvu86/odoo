import logging

from mymodule.base_next.controllers.api.base_method import BaseMethod
from mymodule.constants import Constants
from mymodule.enum.MessageType import NotificationSocketType
from mymodule.share_van_order.controllers.api.warehouse import WarehouseApi
from odoo import api, models, fields, _, http
from odoo.exceptions import ValidationError
from odoo.addons.base.models.utils import validate_utils as validate

_logger = logging.getLogger(__name__)


class Depot(models.Model):
    _name = 'sharevan.depot'
    # _inherit = 'stock.warehouse'
    _description = 'depot'

    name = fields.Char('Depot Name', index=True, required=True)
    depot_code = fields.Char('Depot Code',required=True)
    address = fields.Char('Address')
    street = fields.Char('Street', required=True)
    street2 = fields.Char('Street2')
    city_name = fields.Char('City')
    district = fields.Many2one('sharevan.area', 'District', required=True,
                               domain=lambda
                                   self: "[('country_id', '=', country_id),('location_type','=','district'),('parent_id', '=', state_id),('status', '=','running')]")
    ward = fields.Many2one('sharevan.area', 'Ward', required=True,
                           domain=lambda
                               self: "[('country_id', '=', country_id),('location_type','=','township'),('parent_id', '=', district),('status', '=','running')]")
    zip = fields.Char('Zip')
    state_id = fields.Many2one('sharevan.area', 'Province', required=True,
                               domain=lambda
                                   self: "[('country_id', '=', country_id),('location_type','=','province'),('status', '=','running')]")
    country_id = fields.Many2one('res.country', 'Country', required=True)
    latitude = fields.Float(string='Geo Latitude', digits=(16, 5))
    longitude = fields.Float(string='Geo Longitude', digits=(16, 5))
    phone = fields.Char('Phone')
    zone_id = fields.Many2one('sharevan.zone', 'Zone',
                              domain=lambda
                                  self: "[('status', '=', 'running'),('country_id', '=', country_id)]")
    area_id = fields.Many2one('sharevan.area', 'Area')
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        help='The company is automatically set from your user preferences.',
        domain=lambda self: "[('status', '=','running')]")
    customer_id = fields.Many2one('res.partner', 'Customer')
    image_128 = fields.Image("Image", max_width=128, max_height=128)
    # status = fields.Selection([('0', 'NO-ACTIVE'), ('1', 'ACTIVE'), ('2', 'DRAFT')], 'Status', default='0',
    #                           help='status of warehouse', required=True)
    status = fields.Selection([('running', 'Open'),
                               ('deleted', 'Close')], 'Status', help='Status', default="running")
    capacity = fields.Float('Capacity', required=True)
    available_capacity = fields.Float('Available Capacity', required=True)
    attach_File = fields.Many2many('ir.attachment', string="Attach File")
    name_seq = fields.Char(string='Depot Reference', required=True, copy=False, readonly=True,
                           index=True,
                           default=lambda self: _('New'))

    open_time = fields.Float('Open time', digits=(16, 2), group_operator="avg")
    closing_time = fields.Float('Closing time', digits=(16, 2), group_operator="avg")
    product_id = fields.Many2many('sharevan.product.type', domain=[('status', '=', 'running')],
                                  string='Product Type Available')
    group_area_id = fields.Many2one('sharevan.hub', domain=[('status', '=', 'running')],
                                    string='Group area')
    warehouse_type = fields.Selection([("0", "Kho x")])
    main_type = fields.Boolean('Main type',
                               help='True : main depot for code share to export out zone , '
                                    'False = small warehouse support for transporting in zone ',
                               default=False)
    max_tonnage_shipping = fields.Float('Max tonnage shipping')
    array_capacity = fields.Char(compute="_compute_array_capacity", compute_sudo=True, store=False)

    def _compute_array_capacity(self):
        for record in self:
            capacity_current = record.capacity - record.available_capacity
            record.array_capacity = str(capacity_current) + ',' + str(record.available_capacity)

    @api.onchange('image_128')
    def _onchange_image_128(self):
        for record in self:
            print(record)

    @api.model
    def create(self, vals):
        seq = BaseMethod.get_new_sequence('sharevan.depot', 'DP', 6, 'depot_code')
        vals['name_seq'] = seq
        vals['depot_code'] = vals['name_seq']
        if 'capacity' in vals:
            vals.update({
                'available_capacity': vals['capacity']
            })
        if 'zone_area_id' not in vals:
            area_inside = self.env['sharevan.area'].search([('id', '=', vals['ward'])], limit=1)
            if area_inside:
                vals['zone_id'] = area_inside.zone_area_id.id
            else:
                notice = "Group area have no children! you have to set up children for group area" + area_inside['name']
                self.env.user.notify_danger(message=notice, title=NotificationSocketType.NOTIFICATION.value)
        result = super(Depot, self).create(vals)
        if result.main_type == False and result.group_area_id:
            group_area_info = self.env['sharevan.hub'].search([('id', '=', result.group_area_id.id)], limit=1)
            group_area_info.write({
                'street': result['street'],
                'address': result['address'],
                'state_id': result['state_id'].id,
                'district': result['district'].id,
                'ward': result['ward'].id,
                'latitude': result['latitude'],
                'longitude': result['longitude'],
                'city_name': result['city_name'],
                'hub_area_id': result['id']
            })
        return result

    def write(self, vals):
        if 'street' in vals:
            vals.update({
                'address': vals['street']
            })
        if 'capacity' in vals:
            vals['available_capacity'] = vals['capacity'] - self.capacity + self.available_capacity
            if vals['available_capacity'] < 0:
                test_msg = {"message": "Your depot is too lower storage ! "
                            }
                self.env.user.notify_warning(**test_msg)
        if 'available_capacity' in vals:
            create_vals = {
                'depot_id': self.id,
                'available_capacity': vals['available_capacity'],
                'used_capacity': self.capacity - vals['available_capacity']
            }
            res = self.env['sharevan.depot.log'].create(create_vals)
            if not res:
                raise ValidationError("Failed to log capacity change!")
        super(Depot, self).write(vals)
        result = self.env['sharevan.depot'].search([('id', '=', self.id)])
        if result.main_type == False and result.group_area_id:
            params = []
            params.append(result['street'])
            params.append(result['address'])
            params.append(result['state_id'].id)
            params.append(result['country_id'].id)
            params.append(result['district'].id)
            params.append(result['ward'].id)
            params.append(result['latitude'])
            params.append(result['longitude'])
            if result['city_name']:
                params.append(result['city_name'])
            else:
                params.append('')
            params.append(result['id'])
            params.append(result.group_area_id.id)
            http.request.env.cr.execute(
                'UPDATE sharevan_hub SET street = %s ,address=%s ,state_id=%s, country_id=%s,district=%s,ward=%s ,latitude=%s ,longitude=%s,city_name=%s,hub_area_id=%s  WHERE id = %s',
                (params))
            # group_area_info = self.env['sharevan.hub'].search([('id', '=', result.group_area_id.id)], limit=1)

        elif result.main_type == False and not result.group_area_id:
            group_area_info = self.env['sharevan.hub'].search([('hub_area_id', '=', result.id)])
            group_area_info.write({
                'street': False,
                'address': False,
                'state_id': False,
                'district': False,
                'ward': False,
                'latitude': result['latitude'],
                'longitude': result['longitude'],
                'city_name': False,
                'hub_area_id': False,
            })
        return result

    def run_depot_log(self):
        if self.main_type:
            _logger.info(
                "Start scan depot for distance!")
            BaseMethod.create_warehouse_log(True, self, False)
            query_get_all_warehouse = """
                select warehouse.id,warehouse.name from sharevan_warehouse warehouse
                    join sharevan_area area on warehouse.area_id = area.id
                where area.zone_area_id =  %s
            """
            http.request.env.cr.execute(query_get_all_warehouse,
                                        (self.zone_id.id,))
            result_get_all_warehouse = http.request._cr.dictfetchall()
            for warehouse in result_get_all_warehouse:
                warehouse_record = self.env['sharevan.warehouse'].search([('id', '=', warehouse['id'])])
                warehouse_record.write({'scan_check': False})
            self.env.user.notify_info('Scan distance for depot successful! Please scan warehouse 50 record 1 times!')
        else:
            _logger.info(
                "Start scan hub for distance!")
            BaseMethod.create_warehouse_log(False, self, False)
            query_get_all_warehouse = """
                select warehouse.id,warehouse.name from sharevan_warehouse warehouse
                    join sharevan_area area on warehouse.area_id = area.id
                where area.id = %s        
                        """
            http.request.env.cr.execute(query_get_all_warehouse,
                                        (self.group_area_id.id,))
            result_get_all_warehouse = http.request._cr.dictfetchall()
            for warehouse in result_get_all_warehouse:
                warehouse_record = self.env['sharevan.warehouse'].search([('id', '=', warehouse['id'])])
                warehouse_record.write({'scan_check': False})

            self.env.user.notify_info('Scan distance for hub successful! Please scan warehouse 50 record 1 times!')

    def run_warehouse_log(self):
        if self.main_type:
            _logger.info(
                "Start scan depot for distance!")
            query_get_all_warehouse = """
                select warehouse.id,warehouse.name from sharevan_warehouse warehouse
                    join sharevan_area area on warehouse.area_id = area.id
                where area.zone_area_id =  %s and scan_check = false order by RANDOM() LIMIT 50
            """
            http.request.env.cr.execute(query_get_all_warehouse,
                                        (self.zone_id.id,))
            result_get_all_warehouse = http.request._cr.dictfetchall()
            for warehouse in result_get_all_warehouse:
                warehouse_record = self.env['sharevan.warehouse'].search([('id', '=', warehouse['id'])])
                BaseMethod.create_warehouse_log(False, False, warehouse_record)

            self.env.user.notify_info('Scan distance for depot successful')
        else:
            _logger.info(
                "Start scan hub for distance!")
            BaseMethod.create_warehouse_log(False, self, False)
            query_get_all_warehouse = """
                select warehouse.id,warehouse.name from sharevan_warehouse warehouse
                    join sharevan_area area on warehouse.area_id = area.id
                where area.id = %s and scan_check = false order by RANDOM() LIMIT 50     
                        """
            http.request.env.cr.execute(query_get_all_warehouse,
                                        (self.group_area_id.id,))
            result_get_all_warehouse = http.request._cr.dictfetchall()
            for warehouse in result_get_all_warehouse:
                warehouse_record = self.env['sharevan.warehouse'].search([('id', '=', warehouse['id'])])
                BaseMethod.create_warehouse_log(False, False, warehouse_record)

            self.env.user.notify_info('Scan distance for hub successful')
    # Chuyen trang thai Depot sang No-Active
    def unlink(self):
        for id in self.ids:
            record = self.env['sharevan.depot'].search([('id', '=', id)])
            if record.status in ('running', 'draft'):
                raise ValidationError(
                    _('You cannot delete a depot which is not deleted . You should refund it instead.'
                      + record.name_seq))
            record.write({
                'status': 'deleted'
            })
        return self

    @api.onchange('capacity')
    def onchange_capacity(self):
        for record in self:
            if record.capacity < 0:
                record.update({
                    'capacity': False
                })
                test_msg = {"message": "You must enter a capacity greater than 0 ! "
                            }
                self.env.user.notify_danger(**test_msg)

    @api.onchange('street')
    def _onchange_street(self):
        for record in self:
            street = record.street
            district = record.district
            city_name = record.city_name
            state = record.state_id
            country = record.country_id
            ward = record.ward
            area_id = record.area_id
            if street == '':
                record.update({'district': False})
                record.update({'city_name': ''})
                record.update({'state_id': False})
                record.update({'ward': False})
                record.update({'country_id': False})
                record.update({'address': ''})
                record.update({'zone_id': False})
            else:
                if ward:
                    address = street + ' - ' + ward.name
                    if district:
                        address = address + ' - ' + district.name
                    if city_name:
                        if city_name != '':
                            address = address + ' - ' + city_name
                    if state:
                        if city_name is False:
                            address = address + ' - ' + state.name
                    if country:
                        address = address + ' - ' + country.name
                else:
                    address = street
                    if district:
                        address = address + ' - ' + district.name
                    if city_name:
                        if city_name != '':
                            address = address + ' - ' + city_name
                    if state:
                        if city_name is False:
                            address = address + ' - ' + state.name
                    if country:
                        address = address + ' - ' + country.name
                record.update({'district': False})
                record.update({'city_name': False})
                record.update({'state_id': False})
                record.update({'ward': False})
                record.update({'address': address})

    @api.onchange('country_id')
    def onchange_country_id(self):
        for rec in self:
            if rec:
                rec.update(
                    {
                        'state_id': False,
                        'district': False,
                        'ward': False,
                        'address': False,
                    }
                )
                return {'domain': {
                    'state_id': [('country_id', '=', rec['country_id']['id']), ('location_type', '=', 'province'),
                                 ('status', '=', 'running')]
                }}

    @api.onchange('state_id')
    def onchange_state_id(self):
        for rec in self:
            if rec:
                rec.update(
                    {
                        'district': False,
                        'ward': False,
                        'address': False,
                        'city_name': False,
                    }
                )
                return {'domain': {
                    'district': [('country_id', '=', rec['country_id']['id']), ('location_type', '=', 'district'),
                                 ('province_name', '=', rec['state_id']['name']), ('status', '=', 'running')]}}

    @api.onchange('ward')
    def onchange_ward(self):
        for rec in self:
            if rec:
                area_id = rec.ward
                rec.update({'area_id': area_id, 'address': False, })

    @api.onchange('district')
    def onchange_district(self):
        for rec in self:
            if rec:
                if rec.district:
                    area_id = rec.district
                    rec.update({'ward': False, 'address': False, })
                return {'domain': {
                    'ward': [('country_id', '=', rec['country_id']['id']), ('location_type', '=', 'township'),
                             ('district_name', '=', rec['district']['name']), ('status', '=', 'running')]}}


class DepotLog(models.Model):
    _name = 'sharevan.depot.log'

    depot_id = fields.Many2one('sharevan.depot')
    available_capacity = fields.Float('Available capacity')
    used_capacity = fields.Float('Used capacity')  # equal depot_id.capacity - depot_id.available_capacity


class Warehouse(models.Model):
    _name = 'sharevan.warehouse'
    # _inherit = 'stock.warehouse'
    _description = 'warehouse'

    name = fields.Char('Warehouse Name', index=True, required=True)
    warehouse_code = fields.Char('Warehouse Code',required=True)
    address = fields.Char('Address')
    street = fields.Char('Street', required=True)
    street2 = fields.Char('Street2')
    city_name = fields.Char('City')

    state_id = fields.Many2one('sharevan.area', 'Province', required=True,
                               domain=lambda
                                   self: "[('country_id', '=', country_id),('location_type','=','province'),('status', '=','running')]")
    district = fields.Many2one('sharevan.area', 'District', required=True,
                               domain=lambda
                                   self: "[('country_id', '=', country_id),('location_type','=','district'),('parent_id', '=', state_id),('status', '=','running')]")
    ward = fields.Many2one('sharevan.area', 'Ward', required=True,
                           domain=lambda
                               self: "[('country_id', '=', country_id),('location_type','=','township'),('parent_id', '=', district),('status', '=','running')]")
    zip = fields.Char('Zip')

    country_id = fields.Many2one('res.country', 'Country', required=True)
    latitude = fields.Float(string='Geo Latitude', digits=(16, 5),required=True)
    longitude = fields.Float(string='Geo Longitude', digits=(16, 5),required=True)
    max_tonnage_shipping = fields.Float(string='Max tonnage shipping')
    phone = fields.Char('Phone', required=True)

    zone_id = fields.Many2one('sharevan.zone', 'Zone', domain=[('status', '=', 'running')])
    area_id = fields.Many2one('sharevan.area', 'Area',
                              domain=lambda self: "[('country_id', '=', country_id),('status','=','running')]",
                              required=True)

    company_id = fields.Many2one(
        'res.company', 'Customer',
        help='The company is automatically set from your user preferences.',
        domain=[('status', '=', 'running'), ('company_type', '!=', '0')], required=True)
    open_time = fields.Float('Open time', digits=(16, 2), group_operator="avg")

    closing_time = fields.Float('Closing time', digits=(16, 2), group_operator="avg")
    capacity = fields.Integer('Capacity', required=True)
    scan_check = fields.Boolean('Scan', default=False)
    available_capacity = fields.Integer('Available Capacity')
    customer_id = fields.Many2one('res.partner', 'Employee')
    image_128 = fields.Image("Image", max_width=128, max_height=128)
    status = fields.Selection([('running', 'Active'),
                               ('deleted', 'Deactivate')], 'Status', help='Status', default="running")

    attach_File = fields.Many2many('ir.attachment', string="Attach File")
    name_seq = fields.Char(string='Warehouse Reference', required=True, copy=False, readonly=True,
                           index=True,
                           default=lambda self: _('New'))
    product_id = fields.Many2many('sharevan.product.type', domain=[('status', '=', 'running'), ('type', '=', '0')],
                                  string='Product Type Available')
    province_name = fields.Char('province name', store=False)
    district_name = fields.Char('district name', store=False)
    ward_name = fields.Char('ward name', store=False)

    @api.onchange('image_128')
    def _onchange_image_128(self):
        for record in self:
            print(record)

    @api.onchange('capacity')
    def onchange_capacity(self):
        for record in self:
            if record.capacity < 0:
                record.update({
                    'capacity': False,
                    'available_capacity': False
                })
                test_msg = {"message": "You must enter a capacity greater than 0! "
                            }
                self.env.user.notify_danger(**test_msg)
            else:
                record.update({
                    'available_capacity': record.capacity
                })

            if record.available_capacity:
                if record.available_capacity > record.capacity:
                    record.update({
                        'capacity': False,
                        'available_capacity': False
                    })
                    test_msg = {"message": "You must enter capacity greater than available_capacity ! "
                                }
                    self.env.user.notify_danger(**test_msg)

    def domain_all(self):
        for record in self:
            name = record['name']
            return {'domain': {
                'state_id': [('country_id', '=', 241), ('location_type', '=', 'province'),
                             ('status', '=', 'running')]
            }}

    @api.onchange('country_id')
    def onchange_country_id(self):
        for rec in self:
            if rec:
                rec.update(
                    {
                        'state_id': False,
                        'district': False,
                        'ward': False,
                        'area_id': False
                    }
                )
                return {'domain': {
                    'state_id': [('country_id', '=', rec['country_id']['id']), ('location_type', '=', 'province'),
                                 ('status', '=', 'running')]
                }}

    @api.onchange('state_id')
    def onchange_state_id(self):
        for rec in self:
            if rec:
                rec.update(
                    {
                        'district': False,
                        'ward': False,
                        'area_id': False,
                        'city_name': False
                    }
                )
                return {'domain': {
                    'district': [('country_id', '=', rec['country_id']['id']), ('location_type', '=', 'district'),
                                 ('province_name', '=', rec['state_id']['name']), ('status', '=', 'running')]}}

    @api.onchange('ward')
    def onchange_ward(self):
        for rec in self:
            if rec:
                area_id = rec.ward
                rec.update({'area_id': area_id})

    @api.onchange('district')
    def onchange_district(self):
        for rec in self:
            if rec:
                if rec.district:
                    area_id = rec.district
                    rec.update({'area_id': area_id, 'ward': False})
                return {'domain': {
                    'ward': [('country_id', '=', rec['country_id']['id']), ('location_type', '=', 'township'),
                             ('district_name', '=', rec['district']['name']), ('status', '=', 'running')]}}

    @api.constrains('zip')
    def check_zip_code(self):
        if self:
            if self.zip:
                return validate.validate_zip_code(self.zip)

    # @api.constrains('phone')
    # def validate_phone_field(self):
    #     for rec in self:
    #         if rec.phone != False:
    #             return validate.validate_phone_number_v2(rec.phone)

    @api.constrains('street')
    def validate_street_field(self):
        for rec in self:
            if rec.street != False:
                return validate.check_string_contain_special_character(rec.street, 'Street')

    @api.constrains('street2')
    def validate_street2_field(self):
        for rec in self:
            if rec.street2 != False:
                return validate.check_string_contain_special_character(rec.street2, 'Street2')

    @api.constrains('address')
    def validate_address_field(self):
        for rec in self:
            if rec.address != False:
                return validate.check_string_contain_special_character(rec.address, 'Address')

    @api.model
    def create(self, vals):

        seq = BaseMethod.get_new_sequence('sharevan.warehouse', 'WH', 12, 'warehouse_code')
        vals['warehouse_code'] = seq
        vals['name_seq'] = seq
        if 'address' in vals:
            vals['street'] = vals['address']
        else:
            vals['address'] = vals['street']

        if 'capacity' in vals:
            vals.update({
                'available_capacity': vals['capacity']
            })
        # check trùng tên , phone , company , địa chỉ thì update lại status là running
        check_warehouse_querry = """select id,status from sharevan_warehouse
                                    where name ilike '%s' and address ilike '%s' and phone ilike '%s' and company_id = %s""" % (
            vals['name'], vals['address'], vals['phone'], vals['company_id'])
        http.request.env[WarehouseApi.MODEL]._cr.execute(check_warehouse_querry)
        check_record = http.request.env[WarehouseApi.MODEL]._cr.dictfetchall()
        if check_record:
            for rec in check_record:
                if rec['status'] == 'running':
                    raise ValidationError('Warehouse already exists !')
                else:
                    record = self.env['sharevan.warehouse'].search([('id', '=', rec['id'])])
                    record.write({
                        'status': 'running'
                    })
                    return record
        else:
            # warehouse trong 1 cty khong được trùng phone , address ,name
            check_warehouse_querry = """select name,address,phone from sharevan_warehouse
                                                    where (name ilike '%s' or address ilike '%s' or phone ilike '%s') and company_id = %s""" % (
                vals['name'], vals['address'], vals['phone'], vals['company_id'])
            http.request.env[WarehouseApi.MODEL]._cr.execute(check_warehouse_querry)
            check_record_check = http.request.env[WarehouseApi.MODEL]._cr.dictfetchall()
            if check_record_check:
                for rec in check_record_check:
                    if rec['name'] == vals['name']:
                        error = "Name:  %s  already exists !" % (vals['name'])
                        raise ValidationError(error)
                    if rec['phone'] == vals['phone']:
                        error = "Phone:  %s  already exists !" % (vals['phone'])
                        raise ValidationError(error)
                    if rec['address'] == vals['address']:
                        error = "Address:  %s  already exists !" % (vals['address'])
                        raise ValidationError(error)

            result = super(Warehouse, self).create(vals)
            return result

    # Chuyen trang thai warehouse sang No-Active
    def unlink(self):
        for id in self.ids:
            record = self.env['sharevan.warehouse'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })
        return record

    def write(self, vals):
        if 'scan_check' in vals:
            return super(Warehouse, self).write(vals)
        else:
            if 'street' in vals:
                vals.update({
                    'address': vals['street']
                })
            # check nếu còn tuyến thì ko được update warehouse
            check_query = """
                            select bill.* from sharevan_bill_lading bill
                                join sharevan_bill_lading_detail detail on detail.bill_lading_id = bill.id
                            where bill.status = 'running' and end_date >= CURRENT_DATE 
                                and  detail.warehouse_id =%s
            """
            http.request.env[WarehouseApi.MODEL]._cr.execute(check_query, (self.id,))
            check_record = http.request.env[WarehouseApi.MODEL]._cr.dictfetchall()
            if check_record:
                bill_code = ''
                for rec in check_record:
                    bill_code += rec['name'] + ', '
                raise ValidationError('You have to stop ordered bill before update warehouse information: ' + bill_code)
            # check trùng tên , phone , company , địa chỉ thì update lại status là running
            if 'name' in vals or 'address' in vals or 'phone' in vals or 'company_id' in vals:
                name = vals['name'] if 'name' in vals else self.name
                address = vals['address'] if 'address' in vals else self.address
                phone = vals['phone'] if 'phone' in vals else self.phone
                company_id = vals['company_id'] if 'company_id' in vals else self.company_id.id

                check_warehouse_querry = """select id,status from sharevan_warehouse
                                                        where name ilike '%s' and address ilike '%s' and phone ilike '%s' and company_id = %s and id!= %s""" % (
                    name, address, phone, company_id, self.id)
                http.request.env[WarehouseApi.MODEL]._cr.execute(check_warehouse_querry)
                check_record_name_phone_company_address = http.request.env[WarehouseApi.MODEL]._cr.dictfetchall()
                if check_record_name_phone_company_address:
                    for rec in check_record_name_phone_company_address:
                        if rec['status'] == 'running':
                            raise ValidationError('Warehouse already exists !')
                # warehouse trong 1 cty khong được trùng phone , address ,name
                check_warehouse_querry = """select name,address,phone from sharevan_warehouse
                                            where (name ilike '%s' or address ilike '%s' or phone ilike '%s') and company_id = %s and id!= %s""" % (
                    name, address, phone, company_id, self.id)
                http.request.env[WarehouseApi.MODEL]._cr.execute(check_warehouse_querry)
                check_record_check = http.request.env[WarehouseApi.MODEL]._cr.dictfetchall()
                if check_record_check:
                    for rec in check_record_check:
                        if rec['name'] == name:
                            error = "Name:  %s  already exists !" % (name)
                            raise ValidationError(error)
                        if rec['phone'] == phone:
                            error = "Phone:  %s  already exists !" % (phone)
                            raise ValidationError(error)
                        if rec['address'] == address:
                            error = "Address:  %s  already exists !" % (address)
                            raise ValidationError(error)

            return super(Warehouse, self).write(vals)

    @api.onchange('street')
    def _onchange_street(self):
        for record in self:
            street = record.street
            district = record.district
            state = record.state_id
            country = record.country_id
            ward = record.ward
            area_id = record.area_id
            # city_name = record.city_name
            if street == '':
                record.update({'district': False})
                record.update({'city_name': ''})
                record.update({'state_id': False})
                record.update({'ward': False})
                record.update({'country_id': False})
                record.update({'address': ''})
                record.update({'area_id': False})
            else:
                if ward:
                    area_id = ward
                else:
                    if district:
                        area_id = district
                if area_id is False:
                    raise ValidationError('Area not found')
                record.update({'district': False})
                record.update({'city_name': False})
                record.update({'state_id': False})
                record.update({'ward': False})
                record.update({'area_id': False})
                record.update({'address': street})
        return {'domain': {
            'district': [('country_id', '=', country), ('location_type', '=', 'district'),
                         ('province_name', '=', state), ('status', '=', 'running')]}}


class Hub(models.Model):
    _name = 'sharevan.hub'
    # _inherit = 'stock.warehouse'
    _description = 'hub'

    @api.constrains('street')
    def validate_street_field(self):
        for rec in self:
            if rec.street != False:
                return validate.check_string_contain_special_character(rec.street, 'Street')

    @api.constrains('street2')
    def validate_street2_field(self):
        for rec in self:
            if rec.street2 != False:
                return validate.check_string_contain_special_character(rec.street2, 'Street2')

    @api.constrains('city_name')
    def validate_city(self):
        for rec in self:
            if rec.city_name != False:
                return validate.check_string_contain_special_character(rec.city_name, 'City')

    @api.constrains('address')
    def validate_address_field(self):
        for rec in self:
            if rec.address != False:
                return validate.check_string_contain_special_character(rec.address, 'Address')

    # @api.constrains('phone')
    # def validate_phone_field(self):
    #     for rec in self:
    #         if rec.phone != False:
    #             return validate.check_string_contain_special_character(rec.phone, 'Phone')
    #         pass
    #     return False

    name = fields.Char('Hub Name', index=True, required=True)
    hub_code = fields.Char('Hub Code',required=True)
    address = fields.Char('Address')
    street = fields.Char('Street')
    street2 = fields.Char('Street2')
    city_name = fields.Char('City')
    district = fields.Many2one('sharevan.area', 'District',
                               domain=lambda
                                   self: "[('country_id', '=', country_id),('location_type','=','district'),('status','=','running')]")
    ward = fields.Many2one('sharevan.area', 'Ward',
                           domain=lambda
                               self: "[('country_id', '=', country_id),('location_type','=','township'),('status','=','running')]")
    zip = fields.Char('Zip')
    state_id = fields.Many2one('sharevan.area', 'Province',
                               domain=lambda
                                   self: "[('country_id', '=', country_id),('location_type','=','province'),('status','=','running')]")
    country_id = fields.Many2one('res.country', 'Country')
    hub_area_id = fields.Many2one('sharevan.depot', 'Hub area')
    latitude = fields.Float(string='Geo Latitude', digits=(16, 5))
    longitude = fields.Float(string='Geo Longitude', digits=(16, 5))
    phone = fields.Char('Phone')
    # area_id = fields.Many2one('sharevan.area', 'Area', required=True,
    #                           domain=lambda self: "[('country_id', '=', country_id),('status','=','running')]")
    image_128 = fields.Image("Image", max_width=128, max_height=128)
    # status = fields.Selection([('0', 'NO-ACTIVE'), ('1', 'ACTIVE'), ('2', 'DRAFT')], 'Status', default='0',
    #                           help='status of warehouse', required=True)
    status = fields.Selection([('running', 'Open'),
                               ('deleted', 'Close')], 'Status', help='Status', default="running")

    attach_File = fields.Many2many('ir.attachment', string="Attach File")
    name_seq = fields.Char(string='Hub Reference', required=True, copy=False, readonly=True,
                           index=True,
                           default=lambda self: _('New'))
    open_time = fields.Float('Open time', digits=(16, 2), group_operator="avg")
    closing_time = fields.Float('Closing time', digits=(16, 2), group_operator="avg")

    @api.model
    def create(self, vals):
        seq = BaseMethod.get_new_sequence('sharevan.warehouse', 'HB', 6, 'hub_code')
        vals['hub_code'] = seq
        vals['name_seq'] = seq

        result = super(Hub, self).create(vals)
        result.write({
            'status': 'running'
        })
        return result

    # Chuyen trang thai Depot sang No-Active
    def unlink(self):
        for id in self.ids:
            record = self.env['sharevan.hub'].search([('id', '=', id)])
            if record.status in ('running', 'draft'):
                raise ValidationError(
                    _('You cannot delete a hub which is not deleted . You should refund it instead.'
                      + record.name_seq))
            record.write({
                'status': 'deleted'
            })
        return self

    def write(self, vals):
        if self['name_seq'] == 'New':
            vals['name_seq'] = self.env['ir.sequence'].next_by_code(
                'self.sharevan.hub') or 'New'
            vals['hub_code'] = vals['name_seq']
        if 'latitude' in vals:
            vals.pop('latitude')
        if 'longitude' in vals:
            vals.pop('longitude')
        res = super(Hub, self).write(vals)
        return res

    @api.onchange('street')
    def _onchange_street(self):
        for record in self:
            street = record.street
            district = record.district
            city_name = record.city_name
            state = record.state_id
            country = record.country_id
            ward = record.ward
            if street == '':
                record.update({'district': False})
                record.update({'city_name': ''})
                record.update({'state_id': False})
                record.update({'ward': False})
                record.update({'country_id': False})
                record.update({'address': ''})
                record.update({'zone_id': False})
            else:
                if ward:
                    address = street + ' - ' + ward.name
                    if district:
                        address = address + ' - ' + district.name
                    if city_name:
                        if city_name != '':
                            address = address + ' - ' + city_name
                    if state:
                        if city_name is False:
                            address = address + ' - ' + state.name
                    if country:
                        address = address + ' - ' + country.name
                else:
                    address = street
                    if district:
                        address = address + ' - ' + district.name
                    if city_name:
                        if city_name != '':
                            address = address + ' - ' + city_name
                    if state:
                        if city_name is False:
                            address = address + ' - ' + state.name
                    if country:
                        address = address + ' - ' + country.name
                record.update({'address': address})

    @api.onchange('state_id', 'district', 'ward')
    def _onchange_state_id(self):
        for record in self:
            street = record.street
            if street:
                district = record.district
                city_name = record.city_name
                state = record.state_id
                country = record.country_id
                ward = record.ward
                # area_id = record.area_id
                if ward:
                    address = street + ' - ' + ward.name
                    # area_id = ward
                    if district:
                        address = address + ' - ' + district.name
                    if city_name:
                        if city_name != '':
                            address = address + ' - ' + city_name
                    if state:
                        if city_name is False:
                            address = address + ' - ' + state.name
                    if country:
                        address = address + ' - ' + country.name
                else:
                    address = street
                    if district:
                        # area_id = district
                        address = address + ' - ' + district.name
                    if city_name:
                        if city_name != '':
                            address = address + ' - ' + city_name
                    if state:
                        if city_name is False:
                            address = address + ' - ' + state.name
                    if country:
                        address = address + ' - ' + country.name
                # if area_id is False:
                #     raise ValidationError('Area not found')
                # record.update({'area_id': area_id})
                record.update({'address': address})

    @api.onchange('country_id')
    def onchange_country(self):
        for record in self:
            record.update({'district': False})
            record.update({'state_id': False})
            record.update({'address': ''})
            # record.update({'area_id': False})
            record.update({'ward': False})
            record.update({'city_name': ''})


class ProductType(models.Model):
    _name = 'sharevan.product.type'
    MODEL = 'sharevan.product.type'
    _description = 'product type'

    name_seq = fields.Char(string='Product type Code', required=True, copy=False, readonly=True,
                           index=True,
                           default=lambda self: _('New'))
    # net_weight = fields.Float('Net weight')
    name = fields.Char('Product type', required=True)
    description = fields.Text('Description')
    status = fields.Selection(
        [('running', 'Running'),
         ('deleted', 'Deleted'),
         ('draft', 'Draft')
         ],
        string='Status', context={'status': 'running'}, readonly=True)
    type = fields.Selection([('0', 'Parent product'), ('1', 'Subproduct')], 'Type', default='0', required=True)

    parent_id = fields.Many2one('sharevan.product.type', 'Parent product type',
                                domain=[('status', '=', 'running'), ('type', '=', '0')], )
    subProductType = fields.One2many('sharevan.product.type', 'parent_id', string='Sub Product',
                                     domain=[('status', '=', 'running')], )

    product = fields.One2many('sharevan.product', 'product_type_id', 'Product',
                              domain=lambda self: "[('status','=','running'),('product_type_id','=',False)]")

    main_product_type = fields.Many2many(comodel_name="sharevan.product.type",
                                         relation="sharevan_product_type_rel", column1="main_product_type",
                                         column2="same_product_type_ids",
                                         domain="[('type','=','0'),('status','=','running')]")
    same_product_type_ids = fields.Many2many(comodel_name="sharevan.product.type",
                                             relation="sharevan_product_type_rel", column1="same_product_type_ids",
                                             column2="main_product_type",
                                             domain="[('type','=','0'),('status','=','running')]")


class Product(models.Model):
    _name = 'sharevan.product'
    MODEL = 'sharevan.product'
    _description = 'product'

    name_seq = fields.Char(string='Product Code', required=True, copy=False, readonly=True,
                           index=True,
                           default=lambda self: _('New'))
    name = fields.Char('Product')
    description = fields.Text('Description')
    status = fields.Selection(
        [('running', 'Running'),
         ('deleted', 'Deleted'),
         ('draft', 'Draft')
         ],
        string='Status', context={'status': 'running'}, readonly=True)

    product_type_id = fields.Many2one('sharevan.product.type', 'Product Type', domain="[('type','=','1')]",
                                      readonly=True)
    product_type_parent_id = fields.Many2one('sharevan.product.type', 'Parent Product Type',
                                             related='product_type_id.parent_id',
                                             store=True)

    @api.model
    def create(self, vals):
        vals['name_seq'] = BaseMethod.get_new_sequence('sharevan.product', 'P', 6, 'name_seq')
        vals['status'] = 'running'
        result = super(Product, self).create(vals)
        return result

    def unlink(self):
        for id in self.ids:
            record = self.env['sharevan.product'].search([('id', '=', id)])
            record.write({
                'status': 'deleted',
                'product_type_id': False,
                'product_type_parent_id': False
            })


class SheduleLogWarehouse(models.Model):
    _name = 'sharevan.warehouse.log'
    MODEL = 'sharevan.warehouse.log'
    _description = 'sharevan.warehouse.log'

    from_name = fields.Char('From name')
    to_name = fields.Char('To name')
    from_latitude = fields.Float('From latitude')
    from_longitude = fields.Float('To longitude')
    to_latitude = fields.Float('To latitude')
    to_longitude = fields.Float('To longitude')
    time = fields.Float('Time', help='Time between two point')
    distance = fields.Float('Distance', help='Distance between two point')
    scan_check = fields.Boolean('Scan check')
    description = fields.Text('Description')

    def run_warehoue_log_chedule(self):
        _logger.info(
            "Start Run schedule for distance!")
        warehouse = http.request.env['sharevan.warehouse'].search([('scan_check', '=', False)], limit=1)
        BaseMethod.create_warehouse_log(False, False, warehouse)
