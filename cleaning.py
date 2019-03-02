# /usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime

import os
import configparser
import logging
from pprint import pprint

from tools.get_users_expire import GetUsersExpire
from tools.liberate_ip import LiberateIp
from tools.send_email import SendEmail

if __name__ == '__main__':

    current_dir = os.getcwd()
    templates_dir = current_dir + "/templates/"

    logging.basicConfig(
        # filename=current_dir + "/logs/clean-" + datetime.datetime.now().strftime('%Y-%m-%d') + ".log",
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logging.info("Load config")

    config_file = current_dir + '/conf/config.ini'

    config = configparser.ConfigParser()
    config.read(config_file)

    date = datetime.now().strftime("%Y-%m-%d")
    # date = "2017-09-20"
    get_users = GetUsersExpire(config, date)

    users_ago_3_months = get_users.find_user_ago_expire(from_interval='3 months 1 day', to_interval='3 months')
    users_today = get_users.find_user_ago_expire(from_interval='1 day', to_interval='0 day')
    users_in_3_months = get_users.find_user_in_expire(from_interval='3 months 1 day', to_interval='3 months')

    for user_ago_3_months in users_ago_3_months:
        SendEmail(
            config=config['zammad'],
            templates_dir=templates_dir,
            template='expire-ago-2-years',
            infos_user=user_ago_3_months
        )

    LiberateIp(config=config, date=date, from_interval='25 years', to_interval='6 months')
