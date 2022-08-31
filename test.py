# /usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime

import os
import configparser
import logging
from pprint import pprint

from tools.add_missing_certificates import AddMissingCertificates
from tools.get_users_expire import GetUsersExpire
from tools.liberate_ip import LiberateIp
from tools.send_email import SendEmail

if __name__ == '__main__':

    current_dir = os.getcwd()
    templates_dir = current_dir + "/templates/"

    logging.basicConfig(
        #filename=current_dir + "/logs/clean-" + datetime.now().strftime('%Y-%m-%d') + ".log",
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logging.info("Load config")

    config_file = current_dir + '/conf/config.ini'

    config = configparser.ConfigParser()
    config.read(config_file)

    date = datetime.now().strftime("%Y-%m-%d")

    AddMissingCertificates(config=config['postgresql'], directory=config['certificates']['dir'])