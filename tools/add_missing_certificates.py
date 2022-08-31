# /usr/bin/env python3
# -*- coding: utf-8 -*-
import datetime
import glob

import ldap
import logging
import psycopg2
import psycopg2.extras
from pprint import pprint

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.x509 import NameOID


class AddMissingCertificates:
    logger = ''

    config = ''
    directory = ''
    cur = ''
    conn = ''

    all_files = []
    all_serial = []
    all_certificates = []

    def __init__(self, config, directory):
        self.logger = logging.getLogger(__name__)

        self.logger.info('Initialise')
        self.config = config
        self.directory = directory

        self._init_postgresql()

        self._get_all_serial()
        self._find_missing_serial()

    def __delete__(self):
        self.logger.debug('destroy AddMissingCertificates')

        self.cur.close()
        self.conn.close()

    def _get_all_serial(self):
        self.cur.execute('select serial from certificates where serial IS NOT NULL')
        for serial in self.cur.fetchall():
            self.all_serial.append(str(serial['serial']))

    def _find_missing_serial(self):
        self.logger.debug('Find all crt in {directory}'.format(directory=self.directory))
        for file in glob.glob('/home/fred/Dev/neutrinet/cleaning_old_certificate/store/*.crt'):

            cert = x509.load_pem_x509_certificate(open(file, "rb").read(), default_backend())
            self.cur.execute('select * from certificates where serial=\'{serial}\''.format(serial=cert.serial_number))
            data = self.cur.fetchone()
            print(cert.serial_number)

            if data:
                if (data['signedDate'] - cert.not_valid_before) > datetime.timedelta(days=1):
                    print('start date {database} - {files}'.format(database=data['signedDate'], files=cert.not_valid_before))

                if (cert.not_valid_after - data['revocationDate']) > datetime.timedelta(days=1):
                    print('end date {database} - {files}'.format(database=data['revocationDate'], files=cert.not_valid_after))
            if not data:
                print('oups je ne suis pas la')
            print('')


            # print(str(cert.serial_number))
            # if str(cert.serial_number) not in self.all_serial:
            #     cert_cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
            #     print('missing {serial} from cn : {cn}'.format(serial=cert.serial_number, cn=cert_cn))

    def _find_client_id(self):
        pass

    def _init_postgresql(self):
        self.logger.debug('Initialise postgresql connexion')

        self.conn = psycopg2.connect("{dsn}".format(dsn=self.config['dsn']))
        self.cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
