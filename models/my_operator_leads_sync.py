from __future__ import print_function

import traceback
import json
from odoo import fields, models, api
import requests
from datetime import date
import logging
from urllib.request import urlopen
import time
import base64

_logger = logging.getLogger(__name__)


class MyOpLeadsSync(models.TransientModel):
    _name = 'cron.myop.lead.sync'

    def get_source_id_from_odoo(self, name):
        ids = self.env['utm.source'].search([('name', '=', name)], limit=1).id
        return ids


    def _get_audio_link(self, file, name, id):
        if not file:
            return
        contents = urlopen(file).read()
        x = str(date.today()) + '_' + name
        attachment_id = self.env['ir.attachment'].create({
            'name': x,
            'datas': base64.b64encode(contents),
            'mimetype': 'audio/mpeg',
            'type': 'binary',
            'display_name': name,
            'id': id,
            'res_model': 'crm_lead'
        })
        return attachment_id

    def record_test(self, File):
        if (len(File) == 0):
            return
        Token = self.env['ir.config_parameter'].sudo().get_param('my_operator.token')
        authorization = self.env['ir.config_parameter'].sudo().get_param('my_operator.authorization')
        url = "https://developers.myoperator.co/recordings/link?token=" + str(Token) + "&file=" + str(File)

        payload = {}
        files = {}
        headers = {
            'Authorization': authorization,
            'Cookie': 'PHPSESSID=gpjd0bokagfusgitdec0fbjvk0; ci_session=a%3A5%3A%7Bs%3A10%3A%22session_id%22%3Bs%3A32%3A%22b6a7139f618b67a7cb93fdcd0ab6b93a%22%3Bs%3A10%3A%22ip_address%22%3Bs%3A9%3A%2210.0.1.81%22%3Bs%3A10%3A%22user_agent%22%3Bs%3A21%3A%22PostmanRuntime%2F7.29.2%22%3Bs%3A13%3A%22last_activity%22%3Bi%3A1662110545%3Bs%3A9%3A%22user_data%22%3Bs%3A0%3A%22%22%3B%7Dbc69296ae438df19d4c8f09cc437d2b1'
        }

        response = requests.request("GET", url, headers=headers, data=payload, files=files)
        json_data = json.loads(response.text)
        return json_data['url']

    @api.model
    def my_operator_lead_sync(self):
        _logger.info("Starting My Operator Leads Sync")
        x = int(time.time()) - 43200
        url = self.env['ir.config_parameter'].sudo().get_param('my_operator.url')
        token = self.env['ir.config_parameter'].sudo().get_param('my_operator.token')
        authorization = self.env['ir.config_parameter'].sudo().get_param('my_operator.authorization')
        youngman_india_myoperator_departments = self.env['ir.config_parameter'].sudo().get_param('my_operator.youngman_india_myoperator_departments')

        departments = youngman_india_myoperator_departments.split(",") if youngman_india_myoperator_departments else []
        departments = [s.strip().lower() for s in departments]


        payload = {'token': token,'from': x}
        files = [

        ]
        headers = {
            'Authorization': authorization,
            'Cookie': 'PHPSESSID=203s9hkjqhdr9tubpf0gsr6c17; ci_session=a%3A5%3A%7Bs%3A10%3A%22session_id%22%3Bs%3A32%3A%2277732330871d49b41b58bfad7085a580%22%3Bs%3A10%3A%22ip_address%22%3Bs%3A9%3A%2210.0.0.34%22%3Bs%3A10%3A%22user_agent%22%3Bs%3A21%3A%22PostmanRuntime%2F7.29.2%22%3Bs%3A13%3A%22last_activity%22%3Bi%3A1662099047%3Bs%3A9%3A%22user_data%22%3Bs%3A0%3A%22%22%3B%7D0b844e084787e76686beb44352352805'
        }

        response = requests.request("POST", url, headers=headers, data=payload, files=files)

        json_data = json.loads(response.text)

        lead_data = json_data['data']['hits']

        _logger.info("Recieved Records Count from MyOperator: " + str(len(lead_data)))

        i = 0
        for lead in lead_data:
            i=i+1
            try:
                my_op_lead_id = lead['_source']['additional_parameters'][0]['vl']
                if lead['_source']['department_name'].strip().lower() in departments and lead['_source']['log_details']:
                    crm_lead = self.env["crm.lead"].search([('remote_identifier', '=', my_op_lead_id)])

                    if not crm_lead:
                        self.env["res.users"].search([('login', '=', lead['_source']['log_details'][0]['received_by'][0]['email'])]),
                        lq = self.env["res.users"].search([('login', '=', lead['_source']['log_details'][0]['received_by'][0]['email'])]),

                        lead_data = self._get_lead_data(lead, lead_data, lq, my_op_lead_id)

                        self.env['crm.lead'].create(lead_data)
                        _logger.info("Created lead "+ str(i) +":" +  str(lead_data))
                    else:
                        _logger.info("Lead skipped " + str(i) + ": "  + my_op_lead_id + " exists. Skipping")
                else:
                    _logger.info("Lead skipped " + str(i) + ": " + my_op_lead_id + "Recieved Manufacturing Lead" + str(lead))
            except:
                _logger.error("Lead Failed " + str(i) + ": " + str(lead))
                tb = traceback.format_exc()
                _logger.error(tb)
                pass

    def _get_lead_data(self, lead, lead_data, lq, my_op_lead_id):
        lead_data = {
            'active': True,
            'name': 'Inbound leads',
            'contact_name': lead['_source']['caller_number_raw'],
            'phone': lead['_source']['caller_number'],
            'remote_identifier': my_op_lead_id,
            'lead_qualifier': lq[0].id if lq else False,
            'lead_generator': "My Operator",
            'description': lead['_source']["comments"][0]["text"] if len(lead['_source']["comments"]) > 0 else False,
            'source_id': self.get_source_id_from_odoo('INBOUND'),
            'audio_link': self._get_audio_link(self.record_test(lead['_source']['filename']),
                                               lead['_source']['log_details'][0]['received_by'][0]['name'],
                                               lead['_source']['additional_parameters'][0]['vl'])
        }
        return lead_data