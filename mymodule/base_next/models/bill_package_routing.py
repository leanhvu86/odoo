from odoo import models, api, fields, _


class BillPackageRoutingPlan(models.Model):
    _name = 'sharevan.bill.package.routing.plan'
    _description = 'bill package routing by plan '

    quantity = fields.Integer('Quantity by plan')
    length = fields.Float('Length of plan parcel')
    width = fields.Float('Width of plan parcel')
    height = fields.Float('Height of plan parcel')
    total_weight = fields.Float('Total weight of plan parcel')
    capacity = fields.Float('Capacity of plan parcel')
    product_type_id= fields.Many2one('sharevan.product.type', string='Product Type')
    product_package_type_id = fields.Integer(' Product package type')
    bill_package_id = fields.Many2one('sharevan.bill.package', string='Bill package')
    bill_lading_detail_id = fields.Integer('Bill of lading detail')
    note = fields.Char('Note')
    item_name = fields.Char('Item name')
    gen_qr_check = fields.Boolean('Gen qr code')
    insurance_name = fields.Char('Insurance name')
    service_name = fields.Char('Service name')
    key_map = fields.Char("Key Map")
    from_warehouse_id = fields.Many2one('sharevan.warehouse', 'From warehouse')
    to_warehouse_id = fields.Many2one('sharevan.warehouse', 'To warehouse')
    QRchar = fields.Char('QR char')
    qr_char = fields.Char('QR code')
    routing_plan_day_id = fields.Many2one('sharevan.routing.plan.day', 'Routing plan day'
                                                 ,index=True)
    status = fields.Selection(
        [('running', 'Running'),
         ('deleted', 'Deleted') ,
         ('draft', 'Draft')],
        string='Status', context={'status': 'running'}, default='running', required=True)
    # bill_package_routing_import_id = fields.One2many('sharevan.bill.package.routing.import', 'id')


class BillPackageRoutingImport(models.Model):
    _name = 'sharevan.bill.package.routing.import'
    _description = 'bill package routing when import'

    quantity_import = fields.Integer('Import quantity')
    length = fields.Float('Length of plan parcel')
    width = fields.Float('Width of plan parcel')
    height = fields.Float('Height of plan parcel')
    total_weight = fields.Float('Total weight of plan parcel')
    capacity = fields.Float('Capacity of plan parcel')
    product_type_id= fields.Many2one('sharevan.product.type', string='Product Type')
    product_package_type_id = fields.Integer(' Product package type')
    bill_package_id = fields.Many2one('sharevan.bill.package', string='Bill package')
    bill_lading_detail_id = fields.Integer('Bill of lading detail')
    note = fields.Char('Note')
    item_name = fields.Char('Item name')
    insurance_name = fields.Char('Insurance name')
    service_name = fields.Char('Service name')
    key_map = fields.Char("Key Map")
    from_warehouse_id = fields.Many2one('sharevan.warehouse', 'From warehouse')
    to_warehouse_id = fields.Many2one('sharevan.warehouse', 'To warehouse')

    QRchar = fields.Char('QR code')
    qr_char = fields.Char('QR code')
    routing_plan_day_id = fields.Many2one('sharevan.routing.plan.day', 'Routing plan day',
                                                 index=True)
    status = fields.Selection(
        [('running', 'Running'),
         ('deleted', 'Deleted'),
         ('draft', 'Draft')],
        string='Status', context={'status': 'running'}, default='running', required=True)
    # bill_package_routing_plan_id = fields.Many2one('sharevan.bill.package.routing.plan', 'Bill package routing plan')


class BillPackageRoutingExport(models.Model):
    _name = 'sharevan.bill.package.routing.export'
    _description = 'bill package routing when export'
    
    quantity_export = fields.Integer('Quantity')
    length = fields.Float('Length of package')
    width = fields.Float('Width')
    height = fields.Float('Height')
    total_weight = fields.Float('Total weight')
    capacity = fields.Float('Capacity')
    product_type_id= fields.Many2one('sharevan.product.type', string='Product Type')
    product_package_type_id = fields.Integer(' Product package type')
    bill_package_id = fields.Many2one('sharevan.bill.package', string='Bill package')
    bill_lading_detail_id = fields.Integer('Bill of lading detail')
    note = fields.Char('Note')
    item_name = fields.Char('Item name')
    insurance_name = fields.Char('Insurance name')
    service_name = fields.Char('Service name')
    key_map = fields.Char("Key Map")
    from_warehouse_id = fields.Many2one('sharevan.warehouse', 'From warehouse')
    to_warehouse_id = fields.Many2one('sharevan.warehouse', 'To warehouse')

    QRchar = fields.Char('QR code')
    qr_char = fields.Char('QR code')
    routing_plan_day_id = fields.Many2one('sharevan.routing.plan.day', 'Routing plan day',
                                                 index=True)
    status = fields.Selection(
        [('running', 'Running'),
         ('deleted', 'Deleted'),
         ('draft', 'Draft')],
        string='Status', context={'status': 'running'}, default='running', required=True)
    # bill_package_routing_plan_id = fields.Many2one('sharevan.bill.package.routing.plan', 'Bill package routing plan')
