from odoo import http
class Test(http.Controller):
    @http.route('/academy/academy/', auth='public')
    def index(self, **kw):
        return http.request.render('website.index', {
            'teachers': ["Diana Padilla", "Jody Caroll", "Lester Vaughn"],
        })