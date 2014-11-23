# coding: utf-8

from __future__ import unicode_literals, print_function
import os
from time import time

if __name__ == '__main__':
    from settings import configure
    configure()

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.core.cache import get_cache
from django.db import connections, connection
from django.test.utils import CaptureQueriesContext
import matplotlib.pyplot as plt
import pandas as pd

from cachalot.api import clear
from cachalot.settings import cachalot_settings
from cachalot.tests.models import Test


RESULTS_PATH = 'benchmark/'
CONTEXTS = ('reference', '1st query', '2nd query')


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
    def __init__(self, n=20):
        self.n = n
        self.data = []

    def bench_once(self, context, num_queries, invalidate_after=False):
        for _ in range(self.n):
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
            if invalidate_after:
                clear(db_alias=self.db_alias)

    def benchmark(self, query_str, to_list=True, num_queries=1):
        self.query_name = query_str
        query_str = 'Test.objects.using(using)' + query_str
        if to_list:
            query_str = 'list(%s)' % query_str
        self.query_function = eval('lambda using: ' + query_str)

        with cachalot_settings(CACHALOT_ENABLED=False):
            self.bench_once(CONTEXTS[0], num_queries)

        self.bench_once(CONTEXTS[1], num_queries, invalidate_after=True)

        self.query_function(self.db_alias)

        self.bench_once(CONTEXTS[2], 0)

    def execute_benchmark(self):
        self.benchmark('.count()', to_list=False)
        self.benchmark('.first()', to_list=False)
        self.benchmark('[:5]')
        self.benchmark(".filter(name__icontains='e')[:5]")
        self.benchmark(".order_by('owner')[:5]")
        self.benchmark(".select_related('owner')[:5]")
        self.benchmark(
            ".select_related('owner').prefetch_related('owner__groups')[:5]",
            num_queries=2)

    def run(self):
        for db_alias in settings.DATABASES:
            self.db_alias = db_alias
            self.db_vendor = connections[self.db_alias].vendor
            print('Benchmarking %s…' % self.db_vendor)
            for cache_alias in settings.CACHES:
                cache = get_cache(cache_alias)
                self.cache_name = cache.__class__.__name__[:-5].lower()
                with cachalot_settings(CACHALOT_CACHE=cache_alias):
                    self.execute_benchmark()

        self.df = pd.DataFrame.from_records(self.data)
        if not os.path.exists(RESULTS_PATH):
            os.mkdir(RESULTS_PATH)
        self.df.to_csv(os.path.join(RESULTS_PATH, 'data.csv'))

        gp = self.df.groupby(('context', 'query', 'db'))['time']
        self.means = gp.mean().unstack().unstack().reindex(CONTEXTS[::-1])
        self.stds = gp.std().unstack().unstack().reindex(CONTEXTS[::-1])

        self.get_perfs()
        self.plot()

    def get_perfs(self):
        for db in self.means.columns.levels[0]:
            g = self.means[db].mean(axis=1)
            print('%s is %.1f× slower then %.1f× faster'
                  % (db.ljust(11), g[CONTEXTS[1]] / g[CONTEXTS[0]],
                     g[CONTEXTS[0]] / g[CONTEXTS[2]]))

    def plot(self):
        xlim = (0, (self.means + self.stds).unstack().max() * 1.05)
        for db in self.means.columns.levels[0]:
            plt.figure()
            self.means[db].plot(
                kind='barh', xerr=self.stds[db], title=db, xlim=xlim,
                figsize=(15, 10), subplots=True, layout=(4, 2),
                sharey=True, legend=False)
            plt.savefig(os.path.join(RESULTS_PATH, '%s_detail.svg' % db))

            plt.figure()
            self.means[db].mean(axis=1).plot(
                kind='barh', xerr=self.stds[db], title=db, xlim=xlim)
            plt.savefig(os.path.join(RESULTS_PATH, '%s.svg' % db))


def create_data(using):
    User.objects.using(using).bulk_create(
        [User(username='user%d' % i) for i in range(50)])
    Group.objects.using(using).bulk_create(
        [Group(name='test%d' % i) for i in range(10)])
    for u in User.objects.using(using):
        u.groups.add(*list(Group.objects.using(using).order_by('?')[:2]))
    Test.objects.using(using).bulk_create(
        [Test(name='test%d' % i,
              owner=User.objects.using(using).order_by('?')[0])
         for i in range(10000)])


if __name__ == '__main__':
    old_db_names = {}
    for alias in connections:
        conn = connections[alias]
        old_db_names[alias] = conn.settings_dict['NAME']
        conn.creation.create_test_db(autoclobber=True)

        print("Populating database '%s'…" % alias)
        create_data(alias)

    Benchmark().run()

    for alias in connections:
        connections[alias].creation.destroy_test_db(old_db_names[alias])
