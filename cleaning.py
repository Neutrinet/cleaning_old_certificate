# /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import configparser
import logging

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

    get_users = GetUsersExpire(config)
    get_users.users_expire_bigger_3_months()



