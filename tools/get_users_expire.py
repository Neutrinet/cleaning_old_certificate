# /usr/bin/env python3
# -*- coding: utf-8 -*-
import psycopg2
from pprint import pprint


class GetUsersExpire:
    config = ''
    cur = ''
    conn = ''

    def __init__(self, config):
        self.config = config

        self._init_postgresql()

    def __delete__(self):
        self.cur.close()
        self.conn.close()

    def users_expire_bigger_3_months(self):
        self.cur.execute('select distinct T1.client_id, '
                         'T3."userId", '
                         'T2.revoc, '
                         'T4.address as address4, '
                         'T5.address as address6 '
                         'from certificates as T1 '
                         'join ( '
                         'select client_id, max("revocationDate"'
                         ') as revoc from certificates group by client_id) as T2 '
                         'on (T1.client_id = T2.client_id) '
                         'join ovpn_clients as T3 '
                         'on (T1.client_id = T3.id) '
                         'join (select distinct client_id, address from address_pool where "ipVersion"=4) as T4 '
                         'on (T1.client_id=T4.client_id) '
                         'RIGHT join ('
                         'select distinct client_id, address from address_pool where "ipVersion"=6 and not client_id=-1'
                         ') as T5 '
                         'on (T1.client_id=T5.client_id) '
                         'where T2.revoc < (now() - INTERVAL \'24 months\');'
                         )
        results = self.cur.fetchall()
        for result in results:
            pprint(result)

        return []

    def users_expire_smaller_3_months(self):
        return []

    def users_not_expire_smaller_3_months(self):
        return []

    def _init_postgresql(self):
        self.conn = psycopg2.connect("dbname={database}".format(database=self.config['postgresql']['database']))
        self.cur = self.conn.cursor()
