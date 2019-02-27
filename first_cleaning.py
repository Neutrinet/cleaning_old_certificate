# /usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime

import os
import configparser
import logging
from pprint import pprint

from tools.generate_email import GenerateEmail
from tools.get_users_expire import GetUsersExpire

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
    # date = "2017-06-20"
    get_users = GetUsersExpire(config, date)
    datas = get_users.find_user_ago_expire(from_interval='2 years', to_interval='1 years')

    gen_email = GenerateEmail(templates_dir=templates_dir)

    for data in datas:
        gen_email.genereate_email(type='2-years', infos=data)

    # send email

    # remove old ip from 6 months


