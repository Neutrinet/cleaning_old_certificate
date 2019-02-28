# /usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import logging
import requests
from jinja2 import Environment, FileSystemLoader
from pprint import pprint

class SendEmail:
    env = ''
    template = ''
    infos_user = ''
    zammad_url = ''
    zammad_token = ''

    ticket = ''

    def __init__(self, config, templates_dir, template, infos_user):
        self.logger = logging.getLogger(__name__)
        self.logger.info('Initialise')

        self.zammad_url = config['url']
        self.zammad_token = config['token']

        self.template = template
        self.infos_user = infos_user

        file_loader = FileSystemLoader(templates_dir)
        self.env = Environment(loader=file_loader)

        self.logger.info('create ticket for uuid' + self.infos_user['uuid'])

        self._send_email()
        self._add_tag()
        self._add_note()

    def _send_email(self):
        self.logger.debug('create ticket uuid : ' + self.infos_user['uuid'])
        data = {
            "title": "VPN certificate renewal",
            "group": "Hub Cube",
            "state_id": 4,
            "note": "UUID {uuid}".format(uuid=self.infos_user['uuid']),
            "customer_id": "guess:{email}".format(email="contact@tharyrok.eu"
                                                  # email=infos_user['email']
                                                  ),
            "article": {
                "subject": "[Neutrinet] Renouvellement de votre certificat de connexion au VPN - VPN certificate renewal",
                "to": "{firstname} {lastname} <{email}>".format(
                    firstname=self.infos_user['firstname'],
                    lastname=self.infos_user['lastname'],
                    email="contact@tharyrok.eu"
                    # email=infos_user['email']
                ),
                "body": self._generated_email(),
                "type": "email",
                "internal": False
            }
        }
        self.ticket = requests.post(
            self.zammad_url + '/api/v1/tickets',
            json=data,
            headers={'Authorization': 'Token token=' + self.zammad_token}
        )

    def _generated_email(self):
        self.logger.debug('Generate email for uuid : ' + self.infos_user['uuid'])

        result = self.env.get_template(self.template + ".jinja2")

        return result.render(self.infos_user)

    def _add_tag(self):
        self.logger.debug('add tag in ticket ' + str(self.ticket.json()['id']) + ' for uuid : ' + self.infos_user['uuid'])

        requests.get(
            self.zammad_url + '/api/v1/tags/add?object=Ticket&o_id=' + str(self.ticket.json()['id']) +'&item=certificate+renewal',
            headers={'Authorization': 'Token token=' + self.zammad_token}
        )

    def _add_note(self):
        self.logger.debug('add note in ticket '+ str(self.ticket.json()['id']) +' for uuid : ' + self.infos_user['uuid'])

        data = {
            "ticket_id": self.ticket.json()['id'],
            "title": "more info certificate and ip",
            "body": json.dumps(self.infos_user, sort_keys=True, default=str, indent=4, ensure_ascii=False),
            "type": "note",
            "internal": True
        }

        respond = requests.post(
            self.zammad_url + '/api/v1/ticket_articles',
            json=data,
            headers={'Authorization': 'Token token=' + self.zammad_token}
        )
