from odoo import models, api, fields, _

# chưa sư dung
class BillPackageRoutingPlan(models.Model):
    _name = 'sharevan.bill.package.routing.plan'
    _description = 'bill package routing by plan'
    quantity_import = fields.Integer('Quantity by plan')
    length = fields.Float('Length of plan parcel')
    width = fields.Float('Width of plan parcel')
    height = fields.Float('Height of plan parcel')
    total_weight = fields.Float('Total weight of plan parcel')
    capacity = fields.Float('Capacity of plan parcel')
    note = fields.Char('note')
    item_name = fields.Char('Item name')
    insurance_name = fields.Char('Insurance name')
    service_name = fields.Char('Service name')
    from_warehouse_id = fields.Many2one('sharevan.warehouse', 'From warehouse', required=True)
    to_warehouse_id = fields.Many2one('sharevan.warehouse', 'To warehouse', required=True)
    QRchar = fields.Char('QR code')
    routing_plan_day_id = fields.Many2one('sharevan.routing.plan.day', 'Routing plan day', required=True)
    bill_package_routing_import_id = fields.One2many('sharevan.bill.package.routing.import', 'id')

# chưa sư dung
class BillPackageRoutingImport(models.Model):
    _name = 'sharevan.bill.package.routing.import'
    _description = 'bill package routing when import'
    quantity_import = fields.Integer('Import quantity')
    length = fields.Float('Length of plan parcel')
    width = fields.Float('Width of plan parcel')
    height = fields.Float('Height of plan parcel')
    total_weight = fields.Float('Total weight of plan parcel')
    capacity = fields.Float('Capacity of plan parcel')
    note = fields.Char('note')
    item_name = fields.Char('Item name')
    insurance_name = fields.Char('Insurance name')
    service_name = fields.Char('Service name')
    from_warehouse_id = fields.Many2one('sharevan.warehouse', 'From warehouse', required=True)
    to_warehouse_id = fields.Many2one('sharevan.warehouse', 'To warehouse', required=True)
    QRchar = fields.Char('QR import')
    routing_plan_day_id = fields.Many2one('sharevan.routing.plan.day', 'Routing plan day', required=True)
    bill_package_routing_plan_id = fields.Many2one('sharevan.bill.package.routing.plan', 'Bill package routing plan')
    bill_package_routing_export_id = fields.One2many('sharevan.bill.package.routing.export', 'id')

# chưa sư dung
class BillPackageRoutingExport(models.Model):
    _name = 'sharevan.bill.package.routing.export'
    _description = 'bill package routing when export'
    quantity_export = fields.Integer('quantity by export')
    length = fields.Float('Length of plan parcel')
    width = fields.Float('Width of plan parcel')
    height = fields.Float('Height of plan parcel')
    total_weight = fields.Float('Total weight of plan parcel')
    capacity = fields.Float('Capacity of plan parcel')
    note = fields.Char('note')
    item_name = fields.Char('Item name')
    insurance_name = fields.Char('Insurance name')
    service_name = fields.Char('Service name')
    from_warehouse_id = fields.Many2one('sharevan.warehouse', 'From warehouse', required=True)
    to_warehouse_id = fields.Many2one('sharevan.warehouse', 'To warehouse', required=True)
    QRchar = fields.Char('QR code export')
    routing_plan_day_id = fields.Many2one('sharevan.routing.plan.day', 'Routing plan day', required=True)
    bill_package_routing_import_id = fields.Many2one('sharevan.bill.package.routing.import',
                                                     'Bill package routing import')
