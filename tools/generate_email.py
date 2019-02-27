# /usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
from jinja2 import Environment, FileSystemLoader


class GenerateEmail:
    env = ''

    def __init__(self, templates_dir):
        self.logger = logging.getLogger(__name__)

        file_loader = FileSystemLoader(templates_dir)
        self.env = Environment(loader=file_loader)

    def genereate_email(self, type, infos):
        template = self.env.get_template(type + ".jinja2")
        print(template.render(infos))
