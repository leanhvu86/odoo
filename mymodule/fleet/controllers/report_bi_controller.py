"""
Simple example code to communicate with Power BI REST API. Hope it helps.
"""

from mymodule.base_next.models.report_bi import ShareVanReport
from odoo import http

# Configuration goes here:
RESOURCE = "https://analysis.windows.net/powerbi/api"  # Don't change that.
APPLICATION_ID = "19180a34-1eca-417f-a613-e99f62e59eba"  # The ID of the application in Active Directory
APPLICATION_SECRET = "y1a61DpebVxWXpBxujqCyICP5Xx8XZQegYfcxyg2sAc="  # A valid key for that application in Active Directory
USER_ID = "admin@mfunctions.onmicrosoft.com"  # A user that has access to PowerBI and the application
USER_PASSWORD = "Mfunction@2020"  # The password for that user
GROUP_ID = '827e1ff1-e81b-43a9-ad59-11df02df36f4'  # The id of the workspace containing the report you want to embed
REPORT_ID = 'ebff9572-cac0-42f3-897c-94c40a6f6a9f'  # The id of the report you want to embed


class ReportController(http.Controller):
    @http.route('/power-bi/embed', type='json', auth='user')
    def getembedinfo(self):
        token = http.request.env[ShareVanReport._name].get_access_token(APPLICATION_ID, APPLICATION_SECRET, USER_ID,
                                                                        USER_PASSWORD)
        report = http.request.env[ShareVanReport._name].get_report(GROUP_ID, REPORT_ID, token)
        embedUrl = report['embedUrl']
        dataSetId = report['datasetId']
        reportId = report['id']
        # reportId = REPORT_ID
        user_id = http.request.env.uid
        accessToken = http.request.env[ShareVanReport._name].get_embed_token_report(GROUP_ID, REPORT_ID,
                                                                                    dataSetId, token)
        return {
            'accessToken': accessToken,
            'embedUrl': embedUrl,
            'reportId': reportId,
        }
