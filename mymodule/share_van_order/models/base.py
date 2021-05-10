# -*- coding: utf-8 -*-

from odoo import models


class Base:
    isObject = False

    def _uniquify_list(self, seq):
        seen = set()
        return [x for x in seq if x not in seen and not seen.add(x)]
    # def toDict(self, isObject=False):
    #     if not isObject:
    #         return self.id, self.display_name
    #
    #     model_fields = self.fields_get()
    #     a = {}
    #     for name, field in model_fields.items():
    #         if not self[name]:
    #             continue
    #         if field['type'] in ('many2one'):
    #             if not self[name].id:
    #                 continue
    #             method = getattr(self[name], "toDict", None)
    #             if callable(method):
    #                 a[name] = self[name].toDict()
    #             else:
    #                 a[name] = self[name]
    #         elif field['type'] == 'one2many':
    #             # l = list()
    #             # for e in self[name].ids:
    #             #     method = getattr(e, "toDict", None)
    #             #     if callable(method):
    #             #         l.append(e.toDict())
    #             #     else:
    #             #         l.append(e[name])
    #             if self[name].ids:
    #                 a[name] = self[name]
    #         else:
    #             a[name] = self[name]
    #     return a
