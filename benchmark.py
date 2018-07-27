#!/usr/bin/env python
# coding: utf-8

from __future__ import unicode_literals, print_function
from collections import OrderedDict
import io
import os
import platform
from random import choice
import re
import sqlite3
from subprocess import check_output
from time import time


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

import django
django.setup()

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.core.cache import caches
from django.db import connections, connection
from django.test.utils import CaptureQueriesContext, override_settings
from django.utils.encoding import force_text
import matplotlib.pyplot as plt
import _mysql
import pandas as pd
import psycopg2

import cachalot
from cachalot.api import invalidate
from cachalot.tests.models import Test


RESULTS_PATH = 'benchmark/'
DATA_PATH = '/var/lib/'
CONTEXTS = ('Control', 'Cold cache', 'Hot cache')
DIVIDER = 'divider'
DISK_DATA_RE = re.compile(r'^MODEL="(.*)" MOUNTPOINT="(.*)"$')


def get_disk_model_for_path(path):
    out = force_text(check_output(['lsblk', '-Po', 'MODEL,MOUNTPOINT']))
    mount_points = []
    previous_model = None
    for model, mount_point in [DISK_DATA_RE.match(line).groups()
                               for line in out.split('\n') if line]:
        if model:
            previous_model = model.strip()
        if mount_point:
            mount_points.append((previous_model, mount_point))
    mount_points = sorted(mount_points, key=lambda t: -len(t[1]))
    for model, mount_point in mount_points:
        if path.startswith(mount_point):
            return model


def write_conditions():
    versions = OrderedDict()

    # CPU
    with open('/proc/cpuinfo') as f:
        versions['CPU'] = re.search(r'^model name\s+: (.+)$', f.read(),
                                    flags=re.MULTILINE).group(1)
    # RAM
    with open('/proc/meminfo') as f:
        versions['RAM'] = re.search(r'^MemTotal:\s+(.+)$', f.read(),
                                    flags=re.MULTILINE).group(1)
    versions.update((
        ('Disk', get_disk_model_for_path(DATA_PATH)),
    ))
    # OS
    linux_dist = ' '.join(platform.linux_distribution()).strip()
    if linux_dist:
        versions['Linux distribution'] = linux_dist
    else:
        versions['OS'] = platform.system() + ' ' + platform.release()

    versions.update((
        ('Python', platform.python_version()),
        ('Django', django.__version__),
        ('cachalot', cachalot.__version__),
        ('sqlite', sqlite3.sqlite_version),
    ))
    # PostgreSQL
    with connections['postgresql'].cursor() as cursor:
        cursor.execute('SELECT version();')
        versions['PostgreSQL'] = re.match(r'^PostgreSQL\s+(\S+)\s',
                                          cursor.fetchone()[0]).group(1)
    # MySQL
    with connections['mysql'].cursor() as cursor:
        cursor.execute('SELECT version();')
        versions['MySQL'] = cursor.fetchone()[0].split('-')[0]
    # Redis
    out = force_text(
        check_output(['redis-cli', 'INFO', 'server'])).replace('\r', '')
    versions['Redis'] = re.search(r'^redis_version:([\d\.]+)$', out,
                                  flags=re.MULTILINE).group(1)
    # memcached
    out = force_text(check_output(['memcached', '-h']))
    versions['memcached'] = re.match(r'^memcached ([\d\.]+)$', out,
                                     flags=re.MULTILINE).group(1)

    versions.update((
        ('psycopg2', psycopg2.__version__.split()[0]),
        ('mysqlclient', _mysql.__version__),
    ))

    with io.open(os.path.join('benchmark', 'conditions.rst'), 'w') as f:
        f.write('In this benchmark, a small database is generated, '
                'and each test is executed %s times '
                'under the following conditions:\n\n' % Benchmark.n)

        def write_table_sep(char='='):
            f.write((char * 20) + ' ' + (char * 50) + '\n')
        write_table_sep()
        for k, v in versions.items():
            f.write(k.ljust(20) + ' ' + v + '\n')
        write_table_sep()


class AssertNumQueries(CaptureQueriesContext):
    def __init__(self, n, using=None):
        self.n = n
        self.using = using
        super(AssertNumQueries, self).__init__(self.get_connection())

    def get_connection(self):
        if self.using is None:
            return connection
        return connections[self.using]

    def __exit__(self, exc_type, exc_val, exc_tb):
        super(AssertNumQueries, self).__exit__(exc_type, exc_val, exc_tb)
        if len(self) != self.n:
            print('The amount of queries should be %s, but %s were captured.'
                  % (self.n, len(self)))


class Benchmark(object):
    n = 20

    def __init__(self):
        self.data = []

    def bench_once(self, context, num_queries, invalidate_before=False):
        for _ in range(self.n):
            if invalidate_before:
                invalidate(db_alias=self.db_alias)
            with AssertNumQueries(num_queries, using=self.db_alias):
                start = time()
                self.query_function(self.db_alias)
                end = time()
            self.data.append(
                {'query': self.query_name,
                 'time': end - start,
                 'context': context,
                 'db': self.db_vendor,
                 'cache': self.cache_name})

    def benchmark(self, query_str, to_list=True, num_queries=1):
        # Clears the cache before a single benchmark to ensure the same
        # conditions across single benchmarks.
        caches[settings.CACHALOT_CACHE].clear()

        self.query_name = query_str
        query_str = 'Test.objects.using(using)' + query_str
        if to_list:
            query_str = 'list(%s)' % query_str
        self.query_function = eval('lambda using: ' + query_str)

        with override_settings(CACHALOT_ENABLED=False):
            self.bench_once(CONTEXTS[0], num_queries)

        self.bench_once(CONTEXTS[1], num_queries, invalidate_before=True)

        self.bench_once(CONTEXTS[2], 0)

    def execute_benchmark(self):
        self.benchmark('.count()', to_list=False)
        self.benchmark('.first()', to_list=False)
        self.benchmark('[:10]')
        self.benchmark('[5000:5010]')
        self.benchmark(".filter(name__icontains='e')[0:10]")
        self.benchmark(".filter(name__icontains='e')[5000:5010]")
        self.benchmark(".order_by('owner')[0:10]")
        self.benchmark(".order_by('owner')[5000:5010]")
        self.benchmark(".select_related('owner')[0:10]")
        self.benchmark(".select_related('owner')[5000:5010]")
        self.benchmark(".prefetch_related('owner__groups')[0:10]",
                       num_queries=3)
        self.benchmark(".prefetch_related('owner__groups')[5000:5010]",
                       num_queries=3)

    def run(self):
        for db_alias in settings.DATABASES:
            self.db_alias = db_alias
            self.db_vendor = connections[self.db_alias].vendor
            print('Benchmarking %s…' % self.db_vendor)
            for cache_alias in settings.CACHES:
                cache = caches[cache_alias]
                self.cache_name = cache.__class__.__name__[:-5].lower()
                with override_settings(CACHALOT_CACHE=cache_alias):
                    self.execute_benchmark()

        self.df = pd.DataFrame.from_records(self.data)
        if not os.path.exists(RESULTS_PATH):
            os.mkdir(RESULTS_PATH)
        self.df.to_csv(os.path.join(RESULTS_PATH, 'data.csv'))

        self.xlim = (0, self.df['time'].max() * 1.01)
        self.output('db')
        self.output('cache')

    def output(self, param):
        gp = self.df.groupby(['context', 'query', param])['time']
        self.means = gp.mean().unstack().unstack().reindex(CONTEXTS)
        los = self.means - gp.min().unstack().unstack().reindex(CONTEXTS)
        ups = gp.max().unstack().unstack().reindex(CONTEXTS) - self.means
        self.errors = dict(
            (key, dict(
                (subkey,
                 [[los[key][subkey][context] for context in self.means.index],
                  [ups[key][subkey][context] for context in self.means.index]])
                for subkey in self.means.columns.levels[1]))
            for key in self.means.columns.levels[0])
        self.get_perfs(param)
        self.plot_detail(param)

        gp = self.df.groupby(['context', param])['time']
        self.means = gp.mean().unstack().reindex(CONTEXTS)
        los = self.means - gp.min().unstack().reindex(CONTEXTS)
        ups = gp.max().unstack().reindex(CONTEXTS) - self.means
        self.errors = [
            [[los[key][context] for context in self.means.index],
             [ups[key][context] for context in self.means.index]]
            for key in self.means]
        self.plot_general(param)

    def get_perfs(self, param):
        with io.open(os.path.join(RESULTS_PATH, param + '_results.rst'),
                     'w') as f:
            for v in self.means.columns.levels[0]:
                g = self.means[v].mean(axis=1)
                perf = ('%s is %.1f× slower then %.1f× faster'
                        % (v.ljust(10), g[CONTEXTS[1]] / g[CONTEXTS[0]],
                           g[CONTEXTS[0]] / g[CONTEXTS[2]]))
                print(perf)
                f.write('- %s\n' % perf)

    def plot_detail(self, param):
        for v in self.means.columns.levels[0]:
            plt.figure()
            axes = self.means[v].plot(
                kind='barh', xerr=self.errors[v],
                xlim=self.xlim, figsize=(15, 15), subplots=True, layout=(6, 2),
                sharey=True, legend=False)
            plt.gca().invert_yaxis()
            for row in axes:
                for ax in row:
                    ax.xaxis.grid(True)
                    ax.set_ylabel('')
                    ax.set_xlabel('Time (s)')
            plt.savefig(os.path.join(RESULTS_PATH, '%s_%s.svg' % (param, v)))

    def plot_general(self, param):
        plt.figure()
        ax = self.means.plot(kind='barh', xerr=self.errors, xlim=self.xlim)
        ax.invert_yaxis()
        ax.xaxis.grid(True)
        ax.set_ylabel('')
        ax.set_xlabel('Time (s)')
        plt.savefig(os.path.join(RESULTS_PATH, '%s.svg' % param))


def create_data(using):
    User.objects.using(using).bulk_create(
        [User(username='user%d' % i) for i in range(50)])
    Group.objects.using(using).bulk_create(
        [Group(name='test%d' % i) for i in range(10)])
    groups = list(Group.objects.using(using))
    for u in User.objects.using(using):
        u.groups.add(choice(groups), choice(groups))
    users = list(User.objects.using(using))
    Test.objects.using(using).bulk_create(
        [Test(name='test%d' % i, owner=choice(users)) for i in range(10000)])


if __name__ == '__main__':
    if not os.path.exists(RESULTS_PATH):
        os.mkdir(RESULTS_PATH)

    write_conditions()

    old_db_names = {}
    for alias in connections:
        conn = connections[alias]
        old_db_names[alias] = conn.settings_dict['NAME']
        conn.creation.create_test_db(autoclobber=True)

        print("Populating %s…" % connections[alias].vendor)
        create_data(alias)

    Benchmark().run()

    for alias in connections:
        connections[alias].creation.destroy_test_db(old_db_names[alias])
