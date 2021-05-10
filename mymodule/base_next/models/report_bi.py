import requests

from odoo import models, fields


class ShareVanReport(models.Model):
    _description = "DLP Report"
    _name = 'sharevan.report'

    name = fields.Char(string='Report')

    def get_access_token(self, application_id, application_secret, user_id, user_password):
        data = {
            'grant_type': 'password',
            'scope': 'openid',
            'resource': "https://analysis.windows.net/powerbi/api",
            'client_id': application_id,
            'client_secret': application_secret,
            'username': user_id,
            'password': user_password
        }
        token = requests.post("https://login.microsoftonline.com/common/oauth2/token", data=data)
        assert token.status_code == 200, "Fail to retrieve token: {}".format(token.text)
        print("Got access token: ")
        print(token.json())
        return token.json()['access_token']

    def make_headers(self, application_id, application_secret, user_id, user_password):
        return {
            'Content-Type': 'application/json; charset=utf-8',
            'Authorization': "Bearer {}".format(
                self.get_access_token(application_id, application_secret, user_id, user_password))
        }

    # def get_embed_token_report(application_id, application_secret, user_id, user_password, group_id, report_id):
    #     endpoint = "https://api.powerbi.com/v1.0/myorg/groups/{}/reports/{}/GenerateToken".format(group_id, report_id)
    #     headers = make_headers(application_id, application_secret, user_id, user_password)
    #     res = requests.post(endpoint, headers=headers, json={"accessLevel": "View"})
    #     return res.json()['token']

    def get_groups(self, application_id, application_secret, user_id, user_password):
        endpoint = "https://api.powerbi.com/v1.0/myorg/groups"
        headers = self.make_headers(self, application_id, application_secret, user_id, user_password)
        return requests.get(endpoint, headers=headers).json()

    def get_dashboards(self, application_id, application_secret, user_id, user_password, group_id):
        endpoint = "https://api.powerbi.com/v1.0/myorg/groups/{}/dashboards".format(group_id)
        headers = self.make_headers(application_id, application_secret, user_id, user_password)
        return requests.get(endpoint, headers=headers).json()

    def get_reports(self, application_id, application_secret, user_id, user_password, group_id):
        endpoint = "https://api.powerbi.com/v1.0/myorg/groups/{}/reports".format(group_id)
        headers = self.make_headers(application_id, application_secret, user_id, user_password)
        return requests.get(endpoint, headers=headers).json()

    def get_report(self, group_id, report_id, access_token):
        endpoint = "https://api.powerbi.com/v1.0/myorg/groups/{}/reports/{}".format(group_id, report_id)
        headers = {'Content-Type': 'application/json; charset=utf-8',
                   'Authorization': "Bearer {}".format(access_token)}
        return requests.get(endpoint, headers=headers).json()

    def get_embed_token_report(self, group_id, report_id, datasets, access_token):
        print(self)
        company_id = self.env.company.id
        endpoint = "https://api.powerbi.com/v1.0/myorg/groups/{}/reports/{}/GenerateToken".format(group_id, report_id)
        headers = {'Content-Type': 'application/json; charset=utf-8',
                   'Authorization': "Bearer {}".format(access_token)}
        res = requests.post(endpoint, headers=headers, json={'accessLevel': "View", 'allowSaveAs': "false",
                                                             'identities': [{
                                                                 "username": "{}".format(company_id),
                                                                 "roles": ["Company"],
                                                                 'datasets': ["{}".format(datasets)]
                                                             }]
                                                             })
        return res.json()['token']

    # ex:
    # get_embed_token_report(APPLICATION_ID, APPLICATION_SECRET, USER_ID, USER_PASSWORD, GROUP_ID, REPORT_ID)
