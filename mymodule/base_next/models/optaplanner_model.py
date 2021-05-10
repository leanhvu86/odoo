from odoo import api, fields, models
class LocationData (models.Model):
    _name = 'location.data'
    _description = 'location data'
    code = fields.Char('code')
    from_latitude = fields.Float('from_latitude')
    from_longtitude = fields.Float('from_longtitude')
    to_latitude = fields.Float('to latitude')
    to_longitude = fields.Float('to_longitude')
    minutes = fields.Float('minutes')
    cost = fields.Float('cost')
    start_address = fields.Char('start address')
    end_address = fields.Char('end address')
    system_schedule=fields.Char(' System schedule')

    @api.model
    def create(self, vals):
        result = super(LocationData, self).create(vals)
        return result

    def get_lstLocation_by_lstlat_and_lstlng(self,latStr,lngStr):
        query = """ select * from location_data where from_latitude in (""" + latStr + ") and to_latitude in (" + latStr + ") and from_longtitude in (" + lngStr + ") and to_longitude in (" + lngStr + ")"
        self._cr.execute(query,)
        locationLst = self._cr.dictfetchall()
        return locationLst


class SolutionDay (models.Model):
    _name = 'solution.day'
    _description = 'solution day'
    name = fields.Char('Name')
    hard_score = fields.Integer('hard score')
    soft_score = fields.Integer('soft score')
    solve_time = fields.Datetime('solve time')
    date_plan = fields.Date('date plan')
    group_code = fields.Char('group code')
    status = fields.Selection([('-1','Cancel'),
                               ('0','New'),
                               ('1','Resolved'),('2','Processing')],'Status',default='0')
