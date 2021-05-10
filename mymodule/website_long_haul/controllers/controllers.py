# -*- coding: utf-8 -*-
from odoo import http
from mymodule.constants import Constants


class WebsiteOrderCustomer(http.Controller):

    @http.route('/bidding_order', type='http', auth="user", website=True)
    def get_list_bidding_order(self):
        # domain = []
        # for arg in kwargs:
        #     if arg == 'keyword' and kwargs.get(arg) is not None:
        #         # domain.append(["price", '>=', kwargs.get(arg)])
        #         continue
        #     if arg == 'import-date' and kwargs.get(arg) is not None:
        #         # domain.append([""])
        #         continue
        #     if arg == 'from_price' and kwargs.get(arg) is not None:
        #         domain.append(["price", '>=', kwargs.get(arg)])
        #         continue
        #     if arg == 'to_price' and kwargs.get(arg) is not None:
        #         domain.append(["price", '<=', kwargs.get(arg)])
        #         continue
        #     if arg == 'from_weight' and kwargs.get(arg) is not None:
        #         domain.append(["total_weight", '>=', kwargs.get(arg)])
        #         continue
        #     if arg == 'to_weight' and kwargs.get(arg) is not None:
        #         domain.append(["total_weight", '<=', kwargs.get(arg)])
        #         continue
        #     if arg == 'location' and kwargs.get(arg) is not None:
        #         # domain.append(["location", 'like', kwargs.get(arg)])
        #         continue

        offset = 0
        limit = 10
        params = []
        bidding_pack_detail = []
        type = '3'

        bidding_time_arr = http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].get_bidding_package_time()

        # bidding_order_arr = http.request.env[Constants.SHAREVAN_BIDDING_ORDER].get_bidding_order_bidded(type, offset,
        #                                                                                                 limit)
        bidding_order_arr = http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].get_bidding_package_information(
            "2020-09-16 04:00:00",
            10, offset,
            limit)
        # for bidding in bidding_order_arr.get('records') :
        #     if bidding['id'] != 299  :
        #         bidding1 = http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].get_bidding_package_detail(bidding['id']).get('records')
        #         bidding.update({'cargo_types': bidding1[0]['cargo_types']
        #     })

        # bidding_package =  http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].get_bidding_package_detail(bidding['id'])
        # bidding_package_detail = bidding_package.get('records')
        # bidding_pack_detail.append(bidding['id'])

        # bidding_package = http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].get_bidding_package_detail(285)
        # bidding_package_detail = bidding_package.get('records')
        # print(bidding_package_detail)
        return http.request.render('website_long_haul.list_bidding_order', {
            'list_bidding_order': bidding_order_arr.get('records'),
            'bidding_time': bidding_time_arr.get('records'),
        })

#     @http.route('/website_order_customer/website_order_customer/objects/<model("website_order_customer.website_order_customer"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('website_order_customer.object', {
#             'object': obj
#         })
