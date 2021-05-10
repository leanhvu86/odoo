from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.exceptions import AccessError, ValidationError
from .utils import validate_utils as validate


class ParkingPoint(models.Model):
    _name = "parking.point"
    _description = "The packing point's vehicle"
    _order = "create_date desc, update_date desc"

    # @api.constrains('day_due_time', 'day_ready_time')
    def check_open_time_close_time(self):
        for rec in self:
            if rec.day_due_time:
                check_day_due_time = self.check_time(rec.day_due_time, 'day_due_time')
                if not check_day_due_time:
                    rec.update({'day_due_time': False})
                    raise ValidationError(
                        _('Hour must smaller than 23 and minute must smaller than 60, you must select Close (Hours)!'))

            if rec.day_ready_time:
                check_day_ready_time = self.check_time(rec.day_ready_time, 'day_ready_time')
                if check_day_ready_time == False:
                    rec.update({'day_ready_time': False})
                    raise ValidationError(_(
                        'Hour must smaller than 23 and minute must smaller than 60!,you must select Open time (Hours)'))

            if rec.day_due_time > rec.day_ready_time:
                raise ValidationError(_('The Open time must be less than Close time'))
            return True

    def check_time(self, time, field_name):
        arr_hour_minute = str(round(time, 2)).split(".")
        hour = arr_hour_minute[0]
        minute = arr_hour_minute[1]
        if int(hour) > 23 or int(minute) > 100:
            return False
        if int(hour) < 0 or int(minute) < 0:
            raise ValidationError(_('Time can not smaller than 0! '))
        return True

    # @api.constrains('phone')
    # def check_phone_number(self):
    #     return validate.validate_phone_number(self)
    #     return True

    @api.constrains('mail')
    def check_mail(self):
        print("Validate email")
        return validate.validate_mail(self)

    @api.constrains('zip')
    def check_zip_code(self):
        if self:
            for rec in self:
                if rec.zip:
                    validate.validate_zip_code(rec.zip)
            return True

    # @api.constrains('phone_number')
    # def check_phone_number(self):
    #     return validate.validate_phone_number(self)
    #     return True

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
    def validate_city_name(self):
        for rec in self:
            if rec.city_name != False:
                return validate.check_string_contain_special_character(rec.city_name, 'City')

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)

    address = fields.Char('Address')
    street = fields.Char('Street', required=True)
    street2 = fields.Char('Street2')
    city_name = fields.Char('City', required=True)
    district = fields.Many2one('sharevan.area', 'District', required=True,
                               domain=lambda
                                   self: "[('country_id', '=', country_id),('location_type','=','district'),('parent_id', '=', state_id),('status', '=','running')]")
    ward = fields.Many2one('sharevan.area', 'Ward', required=True,
                           domain=lambda
                               self: "[('country_id', '=', country_id),('location_type','=','township'),('parent_id', '=', district),('status', '=','running')]")

    zip = fields.Char('Zip')
    state_id = fields.Many2one('sharevan.area', 'Province', required=True,
                        domain=lambda self: "[('country_id', '=', country_id),('location_type','=','province')]")
    country_id = fields.Many2one('res.country', 'Country')
    day_due_time = fields.Float(string='Open time', digits=(2, 2))
    day_ready_time = fields.Float(string='Close time', digits=(2, 2))
    fleet_id = fields.Integer()
    latitude = fields.Float(string='Latitude', digits=(16, 5))
    longitude = fields.Float(string='Longitude', digits=(16, 5))
    name = fields.Char(required=True)
    phone_number = fields.Char(required=True)
    attach_File = fields.Many2many('ir.attachment', string="Attach File")
    status = fields.Selection(
        [('running', 'Running'),
         ('deleted', 'Deleted')
         ],
        string='Status', context={'status': 'running'}, default='running', required=True)
    create_user = fields.Char()
    update_date = fields.Date()
    update_user = fields.Char()
    image_128 = fields.Image("Image", max_width=128, max_height=128)
    vendor_id = fields.Many2one('res.partner', 'Vendor')
    name_seq_parking_point = fields.Char(string='Parking Point Reference', required=True, copy=False, readonly=True,
                                         index=True,
                                         default=lambda self: _('New'))

    _sql_constraints = [
        ('phone_unique', 'unique (phone_number)', 'Phone number must be unique!'),
    ]

    @api.onchange('country_id')
    def onchange_country(self):
        for record in self:
            street = record.street
            district = record.district
            city_name = record.city_name
            state = record.state_id
            country = record.country_id
            ward = record.ward
            record.update({'district': False})
            record.update({'state_id': False})
            record.update({'address': ''})

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

    def unlink(self):

        for selfId in self.ids:
            record_ids = self.env['parking.point'].search([('id', '=', selfId)])
            fleet_managements = self.env['fleet.management'].search([('parking_point_id', '=', selfId)], limit=1)
            if fleet_managements:
                raise ValidationError('You have to register new parking point for team: ' + fleet_managements[
                    'name'] + ', before deactivate parking point!')
            record_ids.write({
                'status': 'deleted'
            })

        return self

    @api.model
    def create(self, vals):
        if vals.get('name_seq_parking_point', 'New') == 'New':
            vals['name_seq_parking_point'] = self.env['ir.sequence'].next_by_code(
                'self.parking.point') or 'New'
        result = super(ParkingPoint, self).create(vals)
        return result

    # @api.onchange('day_due_time')
    # def _onchange_day_due_time(self):

    @api.onchange('street')
    def _onchange_street(self):
        for record in self:
            street = record.street
            district = record.district.name
            city_name = record.city_name
            state = record.state_id.name
            country = record.country_id
            ward = record.ward.name
            if ward is False:
                address = street
            else:
                address = street + ' - ' + ward
            if district is not False:
                address = address + ' - ' + district
            if city_name is not False:
                if city_name != '':
                    address = address + ' - ' + city_name
            if state:
                if city_name is False:
                    address = address + ' - ' + state.name
            if country:
                address = address + ' - ' + country.name
            record.update({'address': address})

    @api.onchange('ward')
    def _onchange_ward(self):
        for record in self:
            street = record.street
            if street:
                district = record.district
                city_name = record.city_name
                state = record.state_id
                country = record.country_id
                ward = record.ward.name
                if ward is False:
                    address = street
                else:
                    address = street + ' - ' + ward
                if district:
                    if district.name:
                        address = address + ' - ' + district.name
                if city_name is not False:
                    if city_name != '':
                        address = address + ' - ' + city_name
                if state:
                    if state.name is not False:
                        if state.name != city_name:
                            address = address + ' - ' + state.name
                if country:
                    address = address + ' - ' + country.name
                record.update({'address': address})
