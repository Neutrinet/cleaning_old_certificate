# /usr/bin/env python3
# -*- coding: utf-8 -*-
import datetime
import ldap
import logging
import psycopg2
import psycopg2.extras
from pprint import pprint


class LiberateIp:
    logger = ''

    config = ''
    cur = ''
    conn = ''
    ldap = ''
    date = ''

    from_interval = ''
    to_interval = ''

    def __init__(self, config, date, from_interval, to_interval):
        self.logger = logging.getLogger(__name__)

        self.from_interval = from_interval
        self.to_interval = to_interval

        self.logger.info('Initialise')
        self.config = config
        self.date = date

        self._init_postgresql()
        self._find_ip_ago_expire()

    def __delete__(self):
        self.logger.debug('destroy GetUsersExpire')

        self.cur.close()
        self.conn.close()

    def _find_ip_ago_expire(self):
        self.logger.info(
            'liberate ip ago expire interval {from_interval} to {to_interval}'
            .format(from_interval=self.from_interval, to_interval=self.to_interval)
        )

        self.cur.execute('update address_pool '
                         'set client_id=-1, enabled=true '
                         'where id in ( '
                         'select address_pool.id '
                         'from address_pool '
                         'join '
                         '(select client_id, max("revocationDate") as revoc from certificates group by client_id) as T2 '
                         'on (address_pool.client_id = T2.client_id) '
                         'where T2.revoc >= (\'{date}\'::date - interval \'{from_interval}\') '
                         'and T2.revoc < (\'{date}\'::date -  interval \'{to_interval}\') '
                         ')'.format(date=self.date, from_interval=self.from_interval, to_interval=self.to_interval)
                         )

        self.conn.commit()

    def _init_postgresql(self):
        self.logger.debug('Initialise postgresql connexion')

        self.conn = psycopg2.connect("{dsn}".format(dsn=self.config['postgresql']['dsn']))
        self.cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
