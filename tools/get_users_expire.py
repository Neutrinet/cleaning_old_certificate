# /usr/bin/env python3
# -*- coding: utf-8 -*-
import datetime
from dateutil.relativedelta import relativedelta
import ldap
import logging
import psycopg2
import psycopg2.extras
from pprint import pprint


class GetUsersExpire:
    logger = ''

    config = ''
    cur = ''
    conn = ''
    ldap = ''
    date = ''

    def __init__(self, config, date):
        self.logger = logging.getLogger(__name__)

        self.logger.info('Initialise')
        self.config = config
        self.date = date

        self._init_postgresql()
        self._init_ldap()

    def __delete__(self):
        self.logger.debug('destroy GetUsersExpire')

        self.cur.close()
        self.conn.close()

    def find_user_interval(self, interval):
        self.logger.info(
            'find in expire interval {interval}'
            .format(interval=interval)
        )

        data = []
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
                         'LEFT join ('
                         'select distinct client_id, address from address_pool where "ipVersion"=6 and not client_id=-1'
                         ') as T5 '
                         'on (T1.client_id=T5.client_id) '
                         'where T2.revoc::date = (\'{date}\'::date {interval}::interval ) '
                         .format(date=self.date, interval=interval)
                         )
        results = self.cur.fetchall()
        for result in results:
            ldap_infos = self._more_info_by_uuid(result['userId'])
            if ldap_infos:
                delta_day = result['revoc'] - datetime.datetime.today()
                delta_remove_day = (result['revoc'] + relativedelta(months=+6)) - datetime.datetime.today()

                pgsq_infos = {
                    "ipv4": result['address4'],
                    "ipv6": result['address6'],
                    "expire_at": result['revoc'],
                    "delta_day": delta_day.days,
                    "delta_remove_day": delta_remove_day.days,
                    "uuid": result['userId'],
                }

                infos = pgsq_infos.copy()
                infos.update(ldap_infos)
                data.append(infos)
            else:
                self.logger.info('not ldap infos found from user_id = {uudi}'.format(uudi=result['userId']))

        return data

    def _more_info_by_uuid(self, uuid):
        self.logger.debug('find info in ldap from user {uuid}'.format(uuid=uuid))

        res = self.ldap.search_s(
            "ou=Users,dc=neutrinet,dc=be",
            ldap.SCOPE_SUBTREE,
            "(uid=" + str(uuid) + ")",
        )
        if res:
            return {
                "lastname": str(res[0][1]['sn'][0].decode("utf-8")),
                "firstname": str(res[0][1]['givenName'][0].decode("utf-8")),
                "email": str(res[0][1]['mail'][0].decode("utf-8"))
            }

    def _init_postgresql(self):
        self.logger.debug('Initialise postgresql connexion')

        self.conn = psycopg2.connect("{dsn}".format(dsn=self.config['postgresql']['dsn']))
        self.cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    def _init_ldap(self):
        self.logger.debug('Initialise ldap connexion')

        self.ldap = ldap.initialize("{dsn}".format(dsn=self.config['ldap']['dsn']))
        login_dn = self.config['ldap']['dn']
        login_pw = self.config['ldap']['password']
        self.ldap.simple_bind_s(login_dn, login_pw)


