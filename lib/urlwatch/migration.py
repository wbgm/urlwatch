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


import logging
import os.path
import sqlite3

from .util import atomic_rename
from .storage import UrlsYaml, UrlsTxt, CacheDirStorage, CacheMiniDBStorage, CacheMiniDBStorage2

logger = logging.getLogger(__name__)


def migrate_urls(urlwatch_config):
    # Migrate urlwatch 1.x URLs to urlwatch 2.x

    pkgname = urlwatch_config.pkgname
    urls = urlwatch_config.urls
    urls_txt = os.path.join(urlwatch_config.urlwatch_dir, 'urls.txt')

    if os.path.isfile(urls_txt) and not os.path.isfile(urls):
        print("""
    Migrating URLs: {urls_txt} -> {urls_yaml}
    Use "{pkgname} --edit" to customize it.
    """.format(urls_txt=urls_txt, urls_yaml=urls, pkgname=pkgname))
        UrlsYaml(urls).save(UrlsTxt(urls_txt).load_secure())
        atomic_rename(urls_txt, urls_txt + '.migrated')


def migrate_cache(urlwatch_config):
    cache = urlwatch_config.cache

    # Migrate urlwatch 2.0 - 2.17 cache DB to new design (Issue #347)
    if os.path.isfile(cache):
        db = sqlite3.connect(cache)
        tables = [row[1] for row in db.execute('SELECT * FROM sqlite_master WHERE type="table"')]
        db.close()
        if 'CacheEntry' in tables:
            print("""
    Migrating cache database to new format
    """)
            root, ext = os.path.splitext(cache)
            old_cache = root + '-old' + ext
            migrated_cache = root + '-migrated' + ext

            atomic_rename(cache, old_cache)
            old_cache_storage = CacheMiniDBStorage(old_cache)
            new_cache_storage = CacheMiniDBStorage2(cache)
            new_cache_storage.restore(old_cache_storage.backup())
            old_cache_storage.close()
            new_cache_storage.close()
            atomic_rename(old_cache, migrated_cache)

    # Migrate urlwatch 1.x cache to urlwatch 2.x
    cache_dir = os.path.join(urlwatch_config.urlwatch_dir, 'cache')

    # On Windows and macOS with case-insensitive filesystems, we have to check if
    # "cache.db" exists in the folder, and in this case, avoid migration (Issue #223)
    if os.path.isdir(cache_dir) and not os.path.isfile(os.path.join(cache_dir, 'cache.db')):
        print("""
    Migrating cache: {cache_dir} -> {cache_db}
    """.format(cache_dir=cache_dir, cache_db=cache))
        old_cache_storage = CacheDirStorage(cache_dir)
        new_cache_storage = CacheMiniDBStorage2(cache)
        new_cache_storage.restore(old_cache_storage.backup())
        new_cache_storage.close()
        atomic_rename(cache_dir, cache_dir + '.migrated')
