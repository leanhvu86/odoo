from mymodule.constants import Constants
from odoo import http


class WebsiteLongHaulController(http.Controller):

    # @http.route('/bidding_order', type='http', auth="user", website=True)
    # def get_list_bidding_order(self):
    #
    #     # domain = []
    #     # for arg in kwargs:
    #     #     if arg == 'keyword' and kwargs.get(arg) is not None:
    #     #         # domain.append(["price", '>=', kwargs.get(arg)])
    #     #         continue
    #     #     if arg == 'import-date' and kwargs.get(arg) is not None:
    #     #         # domain.append([""])
    #     #         continue
    #     #     if arg == 'from_price' and kwargs.get(arg) is not None:
    #     #         domain.append(["price", '>=', kwargs.get(arg)])
    #     #         continue
    #     #     if arg == 'to_price' and kwargs.get(arg) is not None:
    #     #         domain.append(["price", '<=', kwargs.get(arg)])
    #     #         continue
    #     #     if arg == 'from_weight' and kwargs.get(arg) is not None:
    #     #         domain.append(["total_weight", '>=', kwargs.get(arg)])
    #     #         continue
    #     #     if arg == 'to_weight' and kwargs.get(arg) is not None:
    #     #         domain.append(["total_weight", '<=', kwargs.get(arg)])
    #     #         continue
    #     #     if arg == 'location' and kwargs.get(arg) is not None:
    #     #         # domain.append(["location", 'like', kwargs.get(arg)])
    #     #         continue
    #
    #     offset = 0
    #     limit = 10
    #     params = []
    #     bidding_pack_detail = []
    #     type = '3'
    #
    #     bidding_time_arr = http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].get_bidding_package_time()
    #
    #     # bidding_order_arr = http.request.env[Constants.SHAREVAN_BIDDING_ORDER].get_bidding_order_bidded(type, offset,
    #     #                                                                                                 limit)
    #     bidding_order_arr =   http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].get_bidding_package_information("2020-09-16 04:00:00",
    #                                                                                                 10, offset,
    #                                                                                                 limit)
    #     # for bidding in bidding_order_arr.get('records') :
    #     #     if bidding['id'] != 299  :
    #     #         bidding1 = http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].get_bidding_package_detail(bidding['id']).get('records')
    #     #         bidding.update({'cargo_types': bidding1[0]['cargo_types']
    #     #     })
    #
    #         # bidding_package =  http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].get_bidding_package_detail(bidding['id'])
    #         # bidding_package_detail = bidding_package.get('records')
    #         # bidding_pack_detail.append(bidding['id'])
    #
    #     # bidding_package = http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].get_bidding_package_detail(285)
    #     # bidding_package_detail = bidding_package.get('records')
    #     # print(bidding_package_detail)
    #     return http.request.render('theme_long_haul.list_bidding_order', {
    #         'list_bidding_order': bidding_order_arr.get('records'),
    #         'bidding_time' :bidding_time_arr.get('records'),
    #     })


    # @http.route('/bidding_order', type='http', auth='public', website=True)
    # def get_list_bidding_order(self, **kwargs):
    #
    #     lst_bidding_order = http.request.env[Constants.SHAREVAN_BIDDING_ORDER].\
    #         search(args=domain, offset=0, limit=1, order='id desc')
    #     return http.request.render('theme_long_haul.list_bidding_order', {
    #         'list_bidding_order': lst_bidding_order,
    #     })

    @http.route('/call/api', type='json', auth="user")
    def call(self, data, token):
        print(data)

    @http.route('/register_vehicle', auth="user", website=True)
    def register_bidding_vehicle(self, **kwargs):
        res = http.request.env[Constants.SHAREVAN_BIDDING_VEHICLE].list_bidding_vehicle()
        print('xxxxx')
        # url = 'localhost:8070/bidding/get_vehicle_tonnage'
        # response = requests.get(url)
        # movies = response.json()
        return http.request.render('theme_long_haul.vehicle_register')

    @http.route('/register_bidding_vehicle_form', csrf=False, auth="public", methods=['POST'], website=True)
    def register_bidding_vehicle_form(self, **kwargs):
        a = 1
        print("print")
        return 'abc'

    @http.route('/test_data', type='json', csrf=False, auth='public', website=True)
    def test(self):
        return '123'

    @http.route('/bidding_package', csrf=False, type='http', auth='public', website=True)
    def get_bidding_package(self, **kwargs):
        bidding_package_arr = http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].get_bidding_package_time();
        return http.request.render('theme_long_haul.long_haul_bidding_package', {
            'bidding_times': bidding_package_arr,
        })

    @http.route('/get_list_bidding_vehicles', website=True)
    def get_list_bidding_vehicles(self, **kwargs):
        result = http.request.env[Constants.SHAREVAN_BIDDING_VEHICLE].list_manager_bidding_vehicle(**kwargs)
        return http.request.render('theme_long_haul.list_bidding_vehicle', {
            'list_vehicle': result['records'],
        })

    @http.route('/list_bidded', website=True)
    def get_list_bided_order(self):
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
        type = '0'

        # bidding_time_arr = http.request.env[Constants.SHAREVAN_BIDDING_PACKAGE].get_bidding_package_time()
        # bidding_order_arr = http.request.env[Constants.SHAREVAN_BIDDING_ORDER].get_bidding_order_bidded(type, offset,limit)

        bidding_order_arr = http.request.env[Constants.SHAREVAN_BIDDING_ORDER].get_bidding_order_bidded(type, offset,
                                                                                                        limit)
        return http.request.render('theme_long_haul.list_bided_order', {
            'list_bidding_order': bidding_order_arr.get('records'),
        })
