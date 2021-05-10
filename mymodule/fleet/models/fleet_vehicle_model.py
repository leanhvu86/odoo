# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from mymodule.enum.MessageType import NotificationSocketType
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FleetVehicleModel(models.Model):
    _name = 'fleet.vehicle.model'
    _description = 'Model of a vehicle'
    _order = 'name asc'

    name = fields.Char('Model name', required=True)
    engine_name = fields.Char(String='Engine name')
    brand_id = fields.Many2one('fleet.vehicle.model.brand', 'Manufacturer', required=True,
                               help='Manufacturer of the vehicle')
    vendors = fields.Many2many('sharevan.vendor', 'fleet_vehicle_model_vendors', 'model_id', 'partner_id',
                               string='Vendors',
                               domain=[('type', '=', 'vendor_equipment'), ('status', '=', 'running')])
    manager_id = fields.Many2one('res.users', 'Fleet Manager', default=lambda self: self.env.uid,
                                 domain=lambda self: [
                                     ('groups_id', 'in', self.env.ref('fleet.fleet_group_manager').id)])
    image_128 = fields.Image(related='brand_id.image_128', readonly=False)
    capacity = fields.Float("Maximum capacity", default=0.0)
    engine_size = fields.Float("Engine size", default=0.0)
    seats = fields.Integer("Seats", default=0)
    horsepower = fields.Integer("Horsepower", default=0)
    tonnage_id = fields.Many2one('sharevan.tonnage.vehicle', 'Vehicle tonnage', help='Tonnage of the vehicle',
                                 domain=[('status', '=', 'running')])
    status = fields.Selection(
        [('running', 'Running'),
         ('deleted', 'Deleted')
         ],
        string='Status', default='running', required=True)

    overall_dimensions = fields.Char(String='Overall dimensions')
    dimensions_inside_box = fields.Char(String='Dimensions inside the box')
    standard_long = fields.Integer(String='The standard long')
    number_cylinders = fields.Integer(String='Number cylinders')
    fuel_type = fields.Selection([
        ('gasoline', 'Gasoline'),
        ('diesel', 'Diesel'),
        ('lpg', 'LPG'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid')
    ], 'Fuel Type', help='Fuel Used by the vehicle')

    color = fields.Many2one('fleet.color', string='Color', store=True)
    model_year = fields.Integer('Model Year', help='Year of the model')
    vehicle_type = fields.Many2one('fleet.vehicle.type', string='Vehicle type',
                                   domain=lambda self: "[('status','=','running')]")

    @api.depends('name', 'brand_id')
    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.brand_id.name:
                name = record.brand_id.name + '/' + name
            res.append((record.id, name))
        return res

    @api.depends('capacity', 'engine_size', 'seats', 'horsepower')
    def compute_infomation(self):
        for record in self:
            if record.capacity < 0:
                raise ValidationError('Capacity is not smaller than 0')
            if record.engine_size < 0:
                raise ValidationError('Capacity is not smaller than 0')
            if record.seats < 0:
                raise ValidationError('Capacity is not smaller than 0')
            if record.horsepower < 0:
                raise ValidationError('Capacity is not smaller than 0')

    @api.onchange('tonnage_id')
    def onchange_max_tonnage(self):
        for record in self:
            if record.tonnage_id:
                record.capacity = record.tonnage_id.max_tonnage

    @api.onchange('seats', 'capacity', 'number_cylinders', 'model_year', 'horsepower', 'engine_size', 'standard_long')
    def onchange_validator(self):
        for record in self:
            if record['seats'] < 0:
                record.update({'seats': 0})
                notice = "Seats is not small than 0 !"
                self.env.user.notify_danger(message=notice)
            if record['capacity'] < 0:
                record.update({'capacity': 0})
                notice = "Capacity is not small than 0 !"
                self.env.user.notify_danger(message=notice)
            if record['model_year'] < 0:
                record.update({'model_year': 0})
                notice = "Model year is not small than 0 !"
                self.env.user.notify_danger(message=notice)
            if record['number_cylinders'] < 0:
                record.update({'number_cylinders': 0})
                notice = "Number cylinders is not small than 0 !"
                self.env.user.notify_danger(message=notice)
            if record['horsepower'] < 0:
                record.update({'horsepower': 0})
                notice = "Horsepower is not small than 0 !"
                self.env.user.notify_danger(message=notice)
            if record['engine_size'] < 0:
                record.update({'engine_size': 0})
                notice = "Engine size is not small than 0 !"
                self.env.user.notify_danger(message=notice)
            if record['standard_long'] < 0:
                record.update({'standard_long': 0})
                notice = "Standard long is not small than 0 !"
                self.env.user.notify_danger(message=notice)

    _sql_constraints = [
        ('name', 'unique (name)', 'Model name must be unique!')
    ]

    def unlink(self):
        for id in self.ids:
            record = self.env['fleet.vehicle.model'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })
        return self


class FleetVehicleModelBrand(models.Model):
    _name = 'fleet.vehicle.model.brand'
    _description = 'Brand of the vehicle'
    _order = 'name asc'
    type = fields.Selection([('1', 'Hãng xe'), ('2', 'Bảo hiểm')], 'Vendor', default='1', required=True)
    # status = fields.Selection([('0','Chưa xác nhận'),
    #                           ('1','Lái xe xác nhận'),
    #                           ('2','Đã xác nhận')],'Status',default='0',help='status bill of lading', required=True)
    name = fields.Char('Make', required=True)
    address = fields.Char('Address')
    email = fields.Char('Email')
    phone = fields.Char('Phone')
    image_128 = fields.Image("Logo", max_width=128, max_height=128)
