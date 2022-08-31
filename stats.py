# /usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime

import configparser
import psycopg2
import psycopg2.extras

from pprint import pprint

if __name__ == '__main__':

    current_dir = "/opt/cleaning_old_certificate"
    config_file = current_dir + '/conf/config.ini'

    config = configparser.ConfigParser()
    config.read(config_file)

    conn = psycopg2.connect("{dsn}".format(dsn=config['postgresql']['dsn']))
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute('select count(id) as "ip_left" from address_pool where "ipVersion" = 4 and client_id = -1;')

    print(cur.fetchone()[0])
