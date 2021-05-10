from odoo import models, api, fields, _
class BillCycle (models.Model):
    _name = 'sharevan.bill.cycle'
    _description = 'bill cycle'
    cycle_type = fields.Selection([('1','Chu kì tháng'),('2','Chu kì tuần'),('3','Đơn kế hoạch'),('4','Đơn phát sinh')],'Cycle type', default = '1')
    start_date = fields.Date('start date')
    end_date = fields.Date('end date')
    monday = fields.Boolean('monday', default = False)
    tuesday = fields.Boolean('tuesday', default = False)
    wednesday = fields.Boolean('wednesday', default = False)
    thursday = fields.Boolean('thursday', default = False)
    friday = fields.Boolean('friday', default = False)
    saturday = fields.Boolean('saturday', default = False)
    sunday = fields.Boolean('sunday', default = False)
    week1 = fields.Boolean('week1', default = False)
    week2 = fields.Boolean('week2', default = False)
    week3 = fields.Boolean('week3', default = False)
    week4 = fields.Boolean('week4', default = False)
    DELIVERY_DATE = fields.Char('DELIVERY date, separate by "," with cycle_type = 3 ')
    sequence = fields.Integer('sequence')