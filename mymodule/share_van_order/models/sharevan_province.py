from odoo import models, _, http, fields


class ZoneProvince(models.Model):
    _description = "Zone province"
    _name = 'sharevan.zone.province'
    MODEL = 'sharevan.zone.province'

    # _order = 'zone_id'

    country_id = fields.Many2one('res.country', string='Country', index=True, required=True, ondelete='cascade')

    status = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted')], 'Status', default="running",
                              help=' 1:running , 2:deleted')

class AwardLevel(models.Model):
    _name = 'sharevan.awards.level'
    _inherit =  'sharevan.awards.level'
    _description = 'sharevan awards level'
    MODEL = 'sharevan.awards.level'


    amount = fields.Float('Amount')
    vendor_id = fields.Many2one('sharevan.vendor', string='Vendor')
