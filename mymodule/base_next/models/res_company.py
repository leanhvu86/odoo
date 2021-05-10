import logging
from datetime import datetime

from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'
    weight_unit_id = fields.Many2one('weight.unit', string='Weight Unit', required=True,
                                     default=lambda self: self._get_weight_unit())
    volume_unit_id = fields.Many2one('volume.unit', string='Volume Unit', required=True,
                                     default=lambda self: self._get_volume_unit())
    parcel_unit_id = fields.Many2one('parcel.unit', string='Parcel Unit', required=True,
                                     default=lambda self: self._get_parcel_unit())
    award_company_id = fields.Many2one('sharevan.title.award', string="Award customer",
                                       domain=[('status', '=', 'running'), ('title_award_type', '=', 'customer')], store=True)

    @api.model
    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        list_unfinished_bld = self.env['sharevan.bill.lading'].search(
            args=[('company_id', '=', self.id), ('end_date', '>', datetime.today())])
        for bld in list_unfinished_bld:
            bld.total_amount_actual = bld.price_not_discount * self.award_company_id.percent_commission_value \
                                      + bld.insurance_price + bld.service_price
        return res

    @api.model
    def _get_weight_unit(self):
        weight_unit_id = self.env['res.users'].browse(self._uid).company_id.weight_unit_id
        return weight_unit_id or self._get_none_weight_unit()

    @api.model
    def _get_none_weight_unit(self):
        return self.env['weight.unit'].search([('id', '=', 1)], limit=1).id

    @api.onchange('logo')
    def _onchange_image_128(self):
        for record in self:
            print(record)

    @api.model
    def _get_volume_unit(self):
        volume_unit_id = self.env['res.users'].browse(self._uid).company_id.volume_unit_id
        return volume_unit_id or self._get_none_volume_unit()

    @api.model
    def _get_none_volume_unit(self):
        return self.env['volume.unit'].search([('id', '=', 1)], limit=1).id

    @api.model
    def _get_parcel_unit(self):
        parcel_unit_id = self.env['res.users'].browse(self._uid).company_id.parcel_unit_id
        return parcel_unit_id or self._get_none_parcel_unit()

    @api.model
    def _get_none_parcel_unit(self):
        return self.env['parcel.unit'].search([('id', '=', 1)], limit=1).id



class CompanyLog(models.Model):
    _name = "res.company.log"
    _description = 'Companies'
    _order = 'sequence, name'

    point = fields.Float()
    province_id = fields.Many2one('sharevan.area', string="Province", domain=lambda
        self: "[('country_id', '=', country_id),('location_type','=','province'),('status','=','running')]")
    city_name = fields.Char('City name')
    district = fields.Char('District')
    ward = fields.Char('Ward')
    latitude = fields.Float(string='Geo Latitude', digits=(16, 5))
    longitude = fields.Float(string='Geo Longitude', digits=(16, 5))
    company_type = fields.Selection([
        ('0', 'Fleet'),
        ('1', 'Customer'),
        ('2', 'DLP')
    ], 'Company type', default='0', help='Company Type', required=True)
    customer_type = fields.Selection([
        ('1', 'Business'),
        ('2', 'Individual'),
        ('3', 'Logistics'),
        ('4', 'Transportation company'),
        ('5', 'Truck Group'),
        ('6', 'Individual fleet')
    ], 'Customer type', default='1', help='Customer Type', required=True)
    code = fields.Char(default='/', readonly=True)
    name = fields.Char(string='Company Name', required=True, store=True, readonly=False)
    sequence = fields.Integer(help='Used to order Companies in the company switcher', default=10)
    company_id = fields.Many2one('res.company', string='Parent Company', index=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    report_header = fields.Text(string='Company Tagline',
                                help="Appears by default on the top right corner of your printed documents (report header).")
    report_footer = fields.Text(string='Report Footer', translate=True,
                                help="Footer text displayed at the bottom of all reports.")
    # logo_web: do not store in attachments, since the image is retrieved in SQL for
    # performance reasons (see addons/web/controllers/main.py, Binary.company_logo)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self._get_user_currency())
    account_no = fields.Char(string='Account No.')
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street2')
    zip = fields.Char(string='Zip')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string="Fed. State")
    country_id = fields.Many2one('res.country', string="Country")
    email = fields.Char(store=True, readonly=False)
    phone = fields.Char(store=True, readonly=False)
    website = fields.Char(readonly=False)
    vat = fields.Char(string="Tax ID", readonly=False)
    company_registry = fields.Char()
    font = fields.Selection(
        [("Lato", "Lato"), ("Roboto", "Roboto"), ("Open_Sans", "Open Sans"), ("Montserrat", "Montserrat"),
         ("Oswald", "Oswald"), ("Raleway", "Raleway")], default="Lato")
    primary_color = fields.Char()
    secondary_color = fields.Char()
    sale = fields.Float('Sale')
    status = fields.Selection([('running', 'Active'),
                               ('deleted', 'Deactivate')], 'Status', help='Status', default="running")
    priority = fields.Selection([
        ('1', 'Bad'),
        ('2', 'Low'),
        ('3', 'Normal'),
        ('4', 'Good'),
        ('5', 'Perfect')
    ], 'Priority', default='3', help='Priority', required=True)
    weight_unit_id = fields.Many2one('weight.unit', string='Weight Unit', required=True,
                                     default=lambda self: self._get_weight_unit())
    volume_unit_id = fields.Many2one('volume.unit', string='Volume Unit', required=True,
                                     default=lambda self: self._get_volume_unit())
    parcel_unit_id = fields.Many2one('parcel.unit', string='Parcel Unit', required=True,
                                     default=lambda self: self._get_parcel_unit())
    award_company_id = fields.Many2one('sharevan.title.award', string="Award customer",
                                       domain=[('status', '=', 'running'), ('title_award_type', '=', 'customer')],
                                       store=True)
    from_date = fields.Datetime('from date', index=True)
    to_date = fields.Datetime('to date', index=True)