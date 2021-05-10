import json
import logging

from odoo import models

from odoo.http import Response

logger = logging.getLogger(__name__)


class ShareVanArea(models.Model):
    _description = "Area"
    _name = 'sharevan.area'
    _inherit = 'sharevan.area'
    _order = 'code'

    def getAllArea(self, country_id):
        query_area = """
                              Select id,concat(code,' - ',name) as displayValue,code,parent_id 
                              from sharevan_area
                                  where country_id = %s and status = 'running'
                                  order by id asc 
                                                 """
        self.env.cr.execute(query_area, (country_id,))
        result_area = self._cr.dictfetchall()
        links = []
        if result_area:
            for record in result_area:
                if record['parent_id'] is None:
                    area = (record['id'], '', record['code'], record['displayvalue'],)
                    links.append(area)
                else:
                    area = (record['parent_id'], record['id'], record['code'], record['displayvalue'])
                    links.append(area)
        name_to_node = {}
        root = {'code': country_id, 'value': country_id, 'displayValue': 'VN', 'children': []}
        for parent, child, code, value in links:
            parent_node = name_to_node.get(parent)
            if not parent_node:
                name_to_node[parent] = parent_node = {'code': code, 'value': parent, 'displayValue': value}
                root['children'].append(parent_node)
            name_to_node[child] = child_node = {'code': code, 'value': child, 'displayValue': value}
            if parent_node['code'] == child_node['code']:  # bỏ nút giống cha
                parent_node.setdefault('children', [])
            else:
                parent_node.setdefault('children', []).append(child_node)
        return json.dumps(root, ensure_ascii=False)
