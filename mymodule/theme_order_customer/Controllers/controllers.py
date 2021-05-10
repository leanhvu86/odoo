import odoo
from mymodule.constants import Constants
from odoo import http


class WebsiteController(http.Controller):
    news_object = None

    # @http.route('/', type='http', csrf=False, auth='public', website=True)
    # def home_page(self, **kwargs):
    #     image_host = odoo.tools.config['dbfilter']
    #     # banner_paths = attachment._full_path
    #     news = [{
    #         'id': 1,
    #         'article': '/dummy-link1',
    #         'url': '/theme_order_customer/static/src/img/chi-phi-dich-vu-cong-khai.jpg',
    #         'title': 'title 1',
    #         'content': "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum"
    #     },
    #         {
    #             'id': 2,
    #             'article': '/dummy-link2',
    #             'url': '/theme_order_customer/static/src/img/banner-geo-1.jpg',
    #             'title': 'title 2',
    #             'content': "Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo. Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt. Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet, consectetur, adipisci velit, sed quia non numquam eius modi tempora incidunt ut labore et dolore magnam aliquam quaerat voluptatem. Ut enim ad minima veniam, quis nostrum exercitationem ullam corporis suscipit laboriosam, nisi ut aliquid ex ea commodi consequatur? Quis autem vel eum iure reprehenderit qui in ea voluptate velit esse quam nihil molestiae consequatur, vel illum qui dolorem eum fugiat quo voluptas nulla pariatur?"
    #         },
    #         {
    #             'id': 3,
    #             'article': '/dummy-link3',
    #             'url': '/theme_order_customer/static/src/img/banner-geo-2.jpg',
    #             'title': 'title 3',
    #             'content': "At vero eos et accusamus et iusto odio dignissimos ducimus qui blanditiis praesentium voluptatum deleniti atque corrupti quos dolores et quas molestias excepturi sint occaecati cupiditate non provident, similique sunt in culpa qui officia deserunt mollitia animi, id est laborum et dolorum fuga. Et harum quidem rerum facilis est et expedita distinctio. Nam libero tempore, cum soluta nobis est eligendi optio cumque nihil impedit quo minus id quod maxime placeat facere possimus, omnis voluptas assumenda est, omnis dolor repellendus"
    #         }]
    #     for new in news:
    #         if len(new['content']) > 250:
    #             new['content'] = new['content'][0: 250] + "..."
    #     return http.request.render('theme_order_customer.homePage', {
    #         'news': news
    #     })
    #
    # @http.route('/test', type='http', csrf=False, auth='public', website=True)
    # def home_page(self, **kwargs):
    #     headers = ['Mã đơn hàng', 'Trạng thái', 'Điểm bốc', 'Điểm dỡ', 'Xử lý']
    #     return http.request.render('theme_order_customer.test_page_template', {
    #         'list_variable': [1, 2],
    #         'headers': headers
    #     })

    # @http.route('/order_customer', type='http', auth="user", website=True)
    # def get_order(self):
    #     return http.request.render('theme_order_customer.ordercustomer')
