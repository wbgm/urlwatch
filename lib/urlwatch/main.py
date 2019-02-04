# -*- coding: utf-8 -*-
#
# This file is part of urlwatch (https://thp.io/2008/urlwatch/).
# Copyright (c) 2008-2019 Thomas Perl <m@thp.io>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. The name of the author may not be used to endorse or promote products
#    derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


import imp
import logging
import os
import sys

from .storage import YamlConfigStorage, CacheMiniDBStorage2, UrlsYaml
from .handler import Report
from .worker import run_jobs

logger = logging.getLogger(__name__)


class Urlwatch(object):
    def __init__(self, urlwatch_config):

        self.urlwatch_config = urlwatch_config

        logger.info('Using %s as URLs file', self.urlwatch_config.urls)
        logger.info('Using %s for hooks', self.urlwatch_config.hooks)
        logger.info('Using %s as cache database', self.urlwatch_config.cache)

        self.check_url()

        self.config_storage = YamlConfigStorage(self.urlwatch_config.config)
        self.cache_storage = CacheMiniDBStorage2(self.urlwatch_config.cache)
        self.urls_storage = UrlsYaml(self.urlwatch_config.urls)

        self.report = Report(self)
        self.jobs = None

        self.check_directories()

        if not self.urlwatch_config.edit_hooks:
            self.load_hooks()

        if not self.urlwatch_config.edit:
            self.load_jobs()

    def check_directories(self):
        if not os.path.isdir(self.urlwatch_config.urlwatch_dir):
            os.makedirs(self.urlwatch_config.urlwatch_dir)
        if not os.path.exists(self.urlwatch_config.config):
            self.config_storage.write_default_config(self.urlwatch_config.config)
            print("""
    A default config has been written to {config_yaml}.
    Use "{pkgname} --edit-config" to customize it.
        """.format(config_yaml=self.urlwatch_config.config, pkgname=self.urlwatch_config.pkgname))

    def check_url(self):
        urls = self.urlwatch_config.urls
        pkgname = self.urlwatch_config.pkgname
        if not os.path.isfile(urls) and not any(getattr(self.urlwatch_config, flag) for flag in (
                'edit', 'add', 'features', 'edit_hooks', 'edit_config', 'gc_cache',
                'smtp_login', 'telegram_chats', 'test_slack')):
            print("""
    You need to create {urls_yaml} in order to use {pkgname}.
    Use "{pkgname} --edit" to open the file with your editor.
        """.format(urls_yaml=urls, pkgname=pkgname))
            sys.exit(1)

    def load_hooks(self):
        if os.path.exists(self.urlwatch_config.hooks):
            imp.load_source('hooks', self.urlwatch_config.hooks)

    def load_jobs(self):
        if os.path.isfile(self.urlwatch_config.urls):
            jobs = self.urls_storage.load_secure()
            logger.info('Found {0} jobs'.format(len(jobs)))
        else:
            logger.warn('No jobs file found')
            jobs = []

        self.jobs = jobs

    def run_jobs(self):
        run_jobs(self)

    def close(self):
        self.report.finish()
        self.cache_storage.close()
