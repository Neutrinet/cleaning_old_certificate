# /usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime

import os
import configparser
import logging
import ldap
from pprint import pprint

from tools.liberate_ip import LiberateIp
from tools.send_email import SendEmail
from tools.get_users_expire import GetUsersExpire

if __name__ == '__main__':

    current_dir = os.getcwd()
    templates_dir = current_dir + "/templates/"

    logging.basicConfig(
        # filename=current_dir + "/logs/clean-" + datetime.datetime.now().strftime('%Y-%m-%d') + ".log",
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logging.info("Load config")

    config_file = current_dir + '/conf/config.ini'

    config = configparser.ConfigParser()
    config.read(config_file)

    date = datetime.now().strftime("%Y-%m-%d")
    # date = "2017-09-20"
    # date = "2017-05-30"
    #get_users = GetUsersExpire(config, date)
    #users_ago_3_months = get_users.find_user_ago_expire(from_interval='25 years', to_interval='6 months')
    # users_ago_3_months = get_users.find_user_in_expire(from_interval='3 months 1 day', to_interval=' 25 years')

    #users = []

    #for user in users:
    #    SendEmail(
    #        config=config['zammad'],
    #        templates_dir=templates_dir,
    #        template='expire-ago-3-months',
    #        infos_user=user_ago_3_months
    #    )
    #    pprint(user)

    #LiberateIp(config=config, date=date, from_interval='25 years', to_interval='6 years')
    logging.debug('Initialise ldap connexion')

    ldap_neutrinet = ldap.initialize("{dsn}".format(dsn=config['ldap']['dsn']))
    login_dn = config['ldap']['dn']
    login_pw = config['ldap']['password']
    ldap_neutrinet.simple_bind_s(login_dn, login_pw)

    users = ldap_neutrinet.search_s("ou=Users,dc=neutrinet,dc=be", ldap.SCOPE_SUBTREE, "(mail=*)")

    for user in users:
        if user[1]['mail'][0]:
            user_info = {
                            "lastname": str(user[1]['sn'][0].decode("utf-8")),
                            "firstname": str(user[1]['givenName'][0].decode("utf-8")),
                            "email": str(user[1]['mail'][0].decode("utf-8"))
                        }    
            pprint(user_info)

            SendEmail(
                config=config['zammad'],
                templates_dir=templates_dir,
                template='comm_neutrinet',
                infos_user=user_info
            )

