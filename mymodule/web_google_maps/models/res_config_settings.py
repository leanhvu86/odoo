# -*- coding: utf-8 -*-
# License AGPL-3
from mymodule.constants import Constants
from odoo import api, fields, models

GMAPS_LANG_LOCALIZATION = [
    ('af', 'Afrikaans'),
    ('ja', 'Japanese'),
    ('sq', 'Albanian'),
    ('kn', 'Kannada'),
    ('am', 'Amharic'),
    ('kk', 'Kazakh'),
    ('ar', 'Arabic'),
    ('km', 'Khmer'),
    ('ar', 'Armenian'),
    ('ko', 'Korean'),
    ('az', 'Azerbaijani'),
    ('ky', 'Kyrgyz'),
    ('eu', 'Basque'),
    ('lo', 'Lao'),
    ('be', 'Belarusian'),
    ('lv', 'Latvian'),
    ('bn', 'Bengali'),
    ('lt', 'Lithuanian'),
    ('bs', 'Bosnian'),
    ('mk', 'Macedonian'),
    ('bg', 'Bulgarian'),
    ('ms', 'Malay'),
    ('my', 'Burmese'),
    ('ml', 'Malayalam'),
    ('ca', 'Catalan'),
    ('mr', 'Marathi'),
    ('zh', 'Chinese'),
    ('mn', 'Mongolian'),
    ('zh-CN', 'Chinese (Simplified)'),
    ('ne', 'Nepali'),
    ('zh-HK', 'Chinese (Hong Kong)'),
    ('no', 'Norwegian'),
    ('zh-TW', 'Chinese (Traditional)'),
    ('pl', 'Polish'),
    ('hr', 'Croatian'),
    ('pt', 'Portuguese'),
    ('cs', 'Czech'),
    ('pt-BR', 'Portuguese (Brazil)'),
    ('da', 'Danish'),
    ('pt-PT', 'Portuguese (Portugal)'),
    ('nl', 'Dutch'),
    ('pa', 'Punjabi'),
    ('en', 'English'),
    ('ro', 'Romanian'),
    ('en-AU', 'English (Australian)'),
    ('ru', 'Russian'),
    ('en-GB', 'English (Great Britain)'),
    ('sr', 'Serbian'),
    ('et', 'Estonian'),
    ('si', 'Sinhalese'),
    ('fa', 'Farsi'),
    ('sk', 'Slovak'),
    ('fi', 'Finnish'),
    ('sl', 'Slovenian'),
    ('fil', 'Filipino'),
    ('es', 'Spanish'),
    ('fr', 'French'),
    ('es-419', 'Spanish (Latin America)'),
    ('fr-CA', 'French (Canada)'),
    ('sw', 'Swahili'),
    ('gl', 'Galician'),
    ('sv', 'Swedish'),
    ('ka', 'Georgian'),
    ('ta', 'Tamil'),
    ('de', 'German'),
    ('te', 'Telugu'),
    ('el', 'Greek'),
    ('th', 'Thai'),
    ('gu', 'Gujarati'),
    ('tr', 'Turkish'),
    ('iw', 'Hebrew'),
    ('uk', 'Ukrainian'),
    ('hi', 'Hindi'),
    ('ur', 'Urdu'),
    ('hu', 'Hungarian'),
    ('uz', 'Uzbek'),
    ('is', 'Icelandic'),
    ('vi', 'Vietnamese'),
    ('id', 'Indonesian'),
    ('zu', 'Zulu'),
    ('it', 'Italian'),
]


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def get_region_selection(self):
        country_ids = self.env['res.country'].search([])
        values = [(country.code, country.name) for country in country_ids]
        return values

    firebase_message_api_key = fields.Char(
        string='Firebase Message Api Key',
        config_parameter='firebase.api_key')
    driver_request_time_limit = fields.Char(
        string='Driver request time limit',
        config_parameter='driver.request.time.limit')
    weight_constant_order = fields.Char(
        string='Weight constant order',
        config_parameter='weight.constant.order')
    return_amount_percent = fields.Char(
        string='Return amount percent',
        config_parameter='return.amount.percent',default= '1')
    rating_customer_duration_key = fields.Char(
        string='Rating customer duration Key',
        config_parameter='rating.customer.duration.key')
    driver_check_point_duration_key = fields.Char(
        string='Driver check point duration Key',
        config_parameter='driver.check.point.duration.key')
    customer_check_point_duration_key = fields.Char(
        string='Customer check point duration Key',
        config_parameter='customer.check.point.duration.key')
    accept_time_package = fields.Char(
        string='Accept time package',
        config_parameter='accept.time.package')
    duration_server_request_mobile_key = fields.Integer(
        string='Duration mobile request Key', help='second unit',
        config_parameter='duration.request.mobile.key',default=60)
    mobile_save_log_duration_key = fields.Integer(
        string='Duration mobile save log Key', help='second unit',
        config_parameter='mobile.save.log.duration.key', default=60)
    distance_mobile_check_point_key = fields.Integer(
        string='Distance Mobile Check Point Key',help='meter unit',
        config_parameter='distance.mobile.check.point.key',default=200)
    distance_mobile_notification_key = fields.Integer(
        string='Distance Mobile Notification Key',help='meter unit',
        config_parameter='distance.mobile.notification.key',default=2000)
    time_mobile_notification_key = fields.Integer(
        string='Time Mobile Notification Key', help='meter unit',
        config_parameter='time.mobile.notification.key', default=30)
    fee_00 = fields.Integer(
        string='Fee 0', help='fee config',
        config_parameter='fee.zero.key', default=30)
    fee_01 = fields.Integer(
        string='Fee 1', help='fee config',
        config_parameter='fee.one.key', default=30)
    fee_02 = fields.Integer(
        string='Fee 2', help='fee config',
        config_parameter='fee.two.key', default=30)
    fee_03 = fields.Integer(
        string='Fee 3', help='fee config',
        config_parameter='fee.three.key', default=30)
    bidding_time_confirm = fields.Char(
        string='Bidding time confirm',
        config_parameter=Constants.BIDDING_TIME)
    max_distance_routing_key = fields.Integer(
        string='Max Distance Routing Key',
        help='meter unit',
        config_parameter='max.distance.routing.key', default=100000
    )
    sharevan_sos = fields.Char(string='Sharevan Number',
                               config_parameter='sharevan.sos')
    announce_time_before = fields.Integer(string='Announce Time Before',
                                          config_parameter=Constants.ANNOUNCE_TIME_BEFORE)
    google_maps_view_api_key = fields.Char(
        string='Google Maps View Api Key',
        config_parameter='google.api_key_geocode')
    mx_home_server_key = fields.Char(
        string='Chat homeserver Key',
        config_parameter='chat.homeserver.key',default='https://chat.aggregatoricapaci.com:8089')
    google_maps_lang_localization = fields.Selection(
        selection=GMAPS_LANG_LOCALIZATION,
        string='Google Maps Language Localization',
        config_parameter='web_google_maps.localization_lang')
    google_maps_region_localization = fields.Selection(
        selection=get_region_selection,
        string='Google Maps Region Localization',
        config_parameter='web_google_maps.localization_region')
    google_maps_theme = fields.Selection(
        selection=[('default', 'Default'),
                   ('aubergine', 'Aubergine'),
                   ('night', 'Night'),
                   ('dark', 'Dark'),
                   ('retro', 'Retro'),
                   ('silver', 'Silver')],
        string='Map theme',
        config_parameter='web_google_maps.map_theme')
    google_autocomplete_lang_restrict = fields.Boolean(
        string='Google Autocomplete Language Restriction',
        config_parameter='web_google_maps.autocomplete_lang_restrict')
    google_maps_lib_places = fields.Boolean(string='Places', default=True)
    google_maps_lib_geometry = fields.Boolean(string='Geometry', default=True)
    google_maps_lib_drawing = fields.Boolean(string='Drawing')
    google_maps_lib_visualization = fields.Boolean(string='Visualization')



    @api.onchange('google_maps_lang_localization')
    def onchange_lang_localization(self):
        if not self.google_maps_lang_localization:
            self.google_maps_region_localization = ''
            self.google_autocomplete_lang_restrict = False

    
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()

        lib_places = self._set_google_maps_places()
        lib_geometry = self._set_google_maps_geometry()
        lib_drawing = self._set_google_maps_drawing()
        lib_visualize = self._set_google_maps_visualization()

        active_libraries = ','.join(
            filter(None, [lib_places, lib_geometry, lib_drawing, lib_visualize]))

        ICPSudo.set_param('web_google_maps.maps_libraries', active_libraries)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()

        lib_places = self._get_google_maps_places()
        lib_geometry = self._get_google_maps_geometry()
        lib_drawing = self._get_google_maps_drawing()
        lib_visualize = self._get_google_maps_visualization()

        res.update({
            'google_maps_lib_places': lib_places,
            'google_maps_lib_geometry': lib_geometry,
            'google_maps_lib_drawing': lib_drawing,
            'google_maps_lib_visualization': lib_visualize
        })
        return res

    @api.model
    def _get_google_maps_geometry(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        google_maps_libraries = ICPSudo.get_param(
            'web_google_maps.maps_libraries', default='')
        libraries = google_maps_libraries.split(',')
        return 'geometry' in libraries

    
    def _set_google_maps_geometry(self):
        return 'geometry' if self.google_maps_lib_geometry else False

    @api.model
    def _get_google_maps_places(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        google_maps_libraries = ICPSudo.get_param(
            'web_google_maps.maps_libraries', default='')
        libraries = google_maps_libraries.split(',')
        return 'places' in libraries

    
    def _set_google_maps_places(self):
        return 'places' if self.google_maps_lib_places else False

    @api.model
    def _get_google_maps_drawing(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        google_maps_libraries = ICPSudo.get_param(
            'web_google_maps.maps_libraries', default='')
        libraries = google_maps_libraries.split(',')
        return 'drawing' in libraries

    
    def _set_google_maps_drawing(self):
        return 'drawing' if self.google_maps_lib_drawing else False

    @api.model
    def _get_google_maps_visualization(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        google_maps_libraries = ICPSudo.get_param(
            'web_google_maps.maps_libraries', default='')
        libraries = google_maps_libraries.split(',')
        return 'visualization' in libraries

    
    def _set_google_maps_visualization(self):
        return 'visualization' if self.google_maps_lib_visualization else False
