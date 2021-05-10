from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools import float_round

MODULE_UNINSTALL_FLAG = '_force_unlink'
class IrModelFields(models.Model):
    _name = 'ir.model.fields'
    _inherit = ['ir.model.fields']
    _description = 'IrModelFields'

    # @api.model
    # def unlink(self):
    #     ur_ui_new_dynamic_field = "employee.dynamic.fields." + self.name
    #     print("Field deletedxxxxxxxxxxxxxxxxxx:" + ur_ui_new_dynamic_field)
    #     if not self:
    #         return True
    #
    #     # Prevent manual deletion of module columns
    #     if not self._context.get(MODULE_UNINSTALL_FLAG) and \
    #             any(field.state != 'manual' for field in self):
    #         raise UserError(_("This column contains module data and cannot be removed!"))
    #
    #     # prevent screwing up fields that depend on these fields
    #     print("Xoa dynamic field", self.name)
    #     result = self.name.startswith('x_')
    #     if self.name.startswith('x_'):
    #         pass
    #     else:
    #         self._prepare_update()
    #     self.env["ir.ui.view"].search(
    #         [('model', '=', 'fleet.vehicle'), ('name', '=', ur_ui_new_dynamic_field)]).unlink()
    #     fields = []
    #     for record in self:
    #         try:
    #             fields.append(self.pool[record.model]._fields[record.name])
    #         except KeyError:
    #             pass
    #
    #     model_names = self.mapped('model')
    #     self._drop_column()
    #     res = super(IrModelFields, self).unlink()
    #
    #     # discard the removed fields from field triggers
    #     def discard_fields(tree):
    #         # discard fields from the tree's root node
    #         tree.get(None, set()).difference_update(fields)
    #         # discard subtrees labelled with any of the fields
    #         for field in fields:
    #             tree.pop(field, None)
    #         # discard fields from remaining subtrees
    #         for field, subtree in tree.items():
    #             if field is not None:
    #                 discard_fields(subtree)
    #
    #     discard_fields(self.pool.field_triggers)
    #     self.pool.registry_invalidated = True
    #
    #     # The field we just deleted might be inherited, and the registry is
    #     # inconsistent in this case; therefore we reload the registry.
    #     if not self._context.get(MODULE_UNINSTALL_FLAG):
    #         # setup models; this re-initializes models in registry
    #         self.flush()
    #         self.pool.setup_models(self._cr)
    #         # update database schema of model and its descendant models
    #         models = self.pool.descendants(model_names, '_inherits')
    #         self.pool.init_models(self._cr, models, dict(self._context, update_custom_fields=True))
    #
    #     return self