from odoo import models, fields, api, _, http


class BiddingDriver(models.Model):
    _name = 'sharevan.bidding.driver'
    _description = 'Sharevan Bidding Driver'


    name = fields.Char(index=True)
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city_name = fields.Char()
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict',
                               domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict', required=True)
    phone = fields.Char(String="Phone 1", required=True)
    mobile = fields.Char(String="Phone 2")
    company_name = fields.Char('Company Name')
    user_driver = fields.Char(string="User Driver")
    ssn = fields.Char(string="Card Id")
    birth_date = fields.Date(string="Birth Day", required=True)
    hire_date = fields.Date(string="Hire Date", required=True)
    leave_date = fields.Date(string="Leave Date")
    driver_code = fields.Char()

    full_name = fields.Char(String="Full name", required=True)
    class_driver = fields.Many2one('sharevan.driver.license', string='Driver License',
                                   domain=lambda self: "[('country_id', '=', country_id),('status','=','running')]",
                                   required=True)
    expries_date = fields.Date(string="Expries Day", required=True)
    address = fields.Char(String="Address", required=True)
    no = fields.Char(String="No", required=True)
    driver_license_date = fields.Date(string="Driver's liscense date", required=True)

    # image = fields.Many2many('ir.attachment', string="Image")
    attach_File = fields.Many2many('ir.attachment', string="Attach File")
    company_id = fields.Many2one('res_company', string = " Res company")
