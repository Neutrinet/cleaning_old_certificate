# /usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime

import os
import configparser
import logging
from pprint import pprint

from tools.get_users_expire import GetUsersExpire

if __name__ == '__main__':

    current_dir = os.getcwd()

    logging.basicConfig(
        # filename=current_dir + "/logs/clean-" + datetime.datetime.now().strftime('%Y-%m-%d') + ".log",
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logging.info("Load config")

    config_file = current_dir + '/conf/config.ini'

    config = configparser.ConfigParser()
    config.read(config_file)

    # date = datetime.now().strftime("%Y-%m-%d")
    # date = "2017-09-20"
    date = "2017-06-20"
    get_users = GetUsersExpire(config, date)
    data = get_users.find_user_ago_expire(from_interval='25 years', to_interval='1 years')

    pprint(data)

    # send email

    # remove old ip from 6 months


