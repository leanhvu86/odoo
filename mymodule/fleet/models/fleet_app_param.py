from odoo import api, fields, models
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class ParamGroup(models.Model):
    _name = 'fleet.param.group'
    _description = 'Param Group'
    _order = 'name asc,ord asc'
    name = fields.Char(string='name')
    description = fields.Char("Description")
    ord = fields.Integer('Order')
    group_code = fields.Char("Group Code")
    name = fields.Char("Group Name")


class AppParam(models.Model):
    _name = 'fleet.app.param'
    _description = 'App Param'
    _order = 'name desc,ord asc'
    name = fields.Char(string='name')
    group_id = fields.Many2one('fleet.param.group', 'ParamGroup',
                               default=lambda self: self.env['fleet.param.group'].search([], limit=1))
    ord = fields.Integer('Order')
    name = fields.Char("Param Name")
    param_code = fields.Char("Param Code")
    description = fields.Char("Description")


class AppParamValue(models.Model):
    _name = 'fleet.app.param.value'
    _description = 'App Param Value'
    _order = 'param_id asc,param_code asc,ord asc'
    _rec_name = 'param_value'

    param_value = fields.Char(string='param_value')
    param_id = fields.Many2one('fleet.app.param', 'App Param', required=True)
    ord = fields.Integer('Order')
    param_code = fields.Char("Param Code")
    param_value = fields.Char("Value")
    description = fields.Char("Description")
    status = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted')], 'Status', default="running")


    def unlink(self):
        """ unlink()

        Deletes the records of the current set

        update res_partner active = False
        """
        if not self:
            return True

        self.check_access_rights('unlink')
        self._check_concurrency()

        # mark fields that depend on 'self' to recompute them after 'self' has
        # been deleted (like updating a sum of lines after deleting one line)
        self.flush()
        self.modified(self._fields)

        with self.env.norecompute():
            self.check_access_rule('unlink')

            cr = self._cr
            data = self.env['ir.model.data'].sudo().with_context({})
            attachment = self.env['ir.attachment'].sudo()
            ir_model_data_unlink = data
            ir_attachment_unlink = attachment

            # TOFIX: this avoids an infinite loop when trying to recompute a
            # field, which triggers the recomputation of another field using the
            # same compute function, which then triggers again the computation
            # of those two fields
            for field in self._fields.values():
                self.env.remove_to_compute(field, self)

            for sub_ids in cr.split_for_in_conditions(self.ids):
                query = "UPDATE %s SET status = 'deleted' WHERE id IN %%s" % self._table
                cr.execute(query, (sub_ids,))
            # invalidate the *whole* cache, since the orm does not handle all
            # changes made in the database, like cascading delete!
            self.invalidate_cache()
            if ir_model_data_unlink:
                ir_model_data_unlink.unlink()
            if ir_attachment_unlink:
                ir_attachment_unlink.unlink()
            # DLE P93: flush after the unlink, for recompute fields depending on
            # the modified of the unlink
            self.flush()

        # auditing: deletions are infrequent and leave no trace in the database

        return True
