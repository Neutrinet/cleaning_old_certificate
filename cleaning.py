# /usr/bin/env python3
# -*- coding: utf-8 -*-
import configparser
import logging
from datetime import datetime

from tools.get_users_expire import GetUsersExpire
from tools.liberate_ip import LiberateIp
from tools.send_email import SendEmail

if __name__ == '__main__':
    current_dir = "/opt/cleaning_old_certificate"
    templates_dir = current_dir + "/templates/"

    logging.basicConfig(
        filename=current_dir + "/logs/clean-" + datetime.now().strftime('%Y-%m-%d') + ".log",
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logging.info("Load config")

    config_file = current_dir + '/conf/config.ini'

    config = configparser.ConfigParser()
    config.read(config_file)

    date = datetime.now().strftime("%Y-%m-%d")
    get_users = GetUsersExpire(config, date)

    users_ago_2_months = get_users.find_user_interval(interval="- '2 months'")
    users_today = get_users.find_user_interval(interval="+ '0 day'")
    users_in_2_months = get_users.find_user_interval(interval="+ '2 months'")

    for user_ago_2_months in users_ago_2_months:
        SendEmail(
            config=config["zammad"],
            templates_dir=templates_dir,
            template="expire-ago-2-months",
            infos_user=user_ago_2_months,
        )

    for user_today in users_today:
        SendEmail(
            config=config["zammad"],
            templates_dir=templates_dir,
            template="expire-today",
            infos_user=user_today,
        )

    for user_in_2_months in users_in_2_months:
        SendEmail(
            config=config["zammad"],
            templates_dir=templates_dir,
            template="expire-in-2-months",
            infos_user=user_in_2_months,
        )

    LiberateIp(config=config, date=date, from_interval='25 years', to_interval='3 months')
