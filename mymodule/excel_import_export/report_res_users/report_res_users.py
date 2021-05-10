# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class ReportResUsers(models.TransientModel):
    _name = "report.res.users"
    _description = "Wizard for res_user"
    _inherit = "xlsx.report"

    # Search Criteria
    user_id = fields.Many2one("res.partner", string="Sales Team")
    # Report Result, crm.lead
    # results = fields.Many2many("res.partner", compute="_compute_results")
    results = fields.Text(compute="_compute_results")

    # revenue_by_country = fields.Many2many(
    #     "crm.lead", compute="_compute_revenue_by_country",
    # )
    # revenue_by_team = fields.Many2many(
    #     "crm.lead", compute="_compute_revenue_by_team",
    # )

    def _compute_results(self):
        self.ensure_one()
        domain = []
        cr = self._cr
        query = "SELECT json_agg(t) from (SELECT id,name,COALESCE(phone,'') phone,COALESCE(email,'') email ,COALESCE(gender,'') gender FROM res_partner rp where 1=1 "
        if self.user_id:
            query += "and rp.id = %s" % (self.user_id.id,)
        query += " )t"
        cr.execute(query, ())
        result = self._cr.fetchall()
        self.results = result[0][0]
        # if self.user_id:
        #     domain += [("id", "=", self.user_id.id)]
        # self.results = self.env["res.partner"].search(domain)

    # def _compute_revenue_by_country(self):
    #     self.ensure_one()
    #     domain = []
    #     if self.team_id:
    #         domain += [("team_id", "=", self.team_id.id)]
    #     results = self.env["crm.lead"].read_group(
    #         domain,
    #         ["country_id", "planned_revenue"],
    #         ["country_id"],
    #         orderby="country_id",
    #     )
    #     for row in results:
    #         self.revenue_by_country += self.env["crm.lead"].new(
    #             {
    #                 "country_id": row["country_id"],
    #                 "planned_revenue": row["planned_revenue"],
    #             }
    #         )
    #
    # def _compute_revenue_by_team(self):
    #     self.ensure_one()
    #     domain = []
    #     if self.team_id:
    #         domain += [("team_id", "=", self.team_id.id)]
    #     results = self.env["crm.lead"].read_group(
    #         domain, ["team_id", "planned_revenue"], ["team_id"], orderby="team_id"
    #     )
    #     for row in results:
    #         self.revenue_by_team += self.env["crm.lead"].new(
    #             {"team_id": row["team_id"], "planned_revenue": row["planned_revenue"]}
    #         )
