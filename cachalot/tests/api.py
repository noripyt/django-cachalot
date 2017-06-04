# coding: utf-8

from __future__ import unicode_literals
from time import time, sleep
from unittest import skipIf

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import DEFAULT_CACHE_ALIAS, caches
from django.core.management import call_command
from django.db import connection, transaction, DEFAULT_DB_ALIAS
from django.template import engines
from django.test import TransactionTestCase
from jinja2.exceptions import TemplateSyntaxError

from ..api import *
from .models import Test
from .test_utils import TestUtilsMixin


class APITestCase(TestUtilsMixin, TransactionTestCase):
    def setUp(self):
        super(APITestCase, self).setUp()
        self.t1 = Test.objects.create(name='test1')
        self.cache_alias2 = next(alias for alias in settings.CACHES
                                 if alias != DEFAULT_CACHE_ALIAS)

    def test_invalidate_tables(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.values_list('name', flat=True))
            self.assertListEqual(data1, ['test1'])

        with self.settings(CACHALOT_INVALIDATE_RAW=False):
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO cachalot_test (name, public) "
                    "VALUES ('test2', %s);", [1 if self.is_sqlite else True])

        with self.assertNumQueries(0):
            data2 = list(Test.objects.values_list('name', flat=True))
            self.assertListEqual(data2, ['test1'])

        invalidate('cachalot_test')

        with self.assertNumQueries(1):
            data3 = list(Test.objects.values_list('name', flat=True))
            self.assertListEqual(data3, ['test1', 'test2'])

    def test_invalidate_models_lookups(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.values_list('name', flat=True))
            self.assertListEqual(data1, ['test1'])

        with self.settings(CACHALOT_INVALIDATE_RAW=False):
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO cachalot_test (name, public) "
                    "VALUES ('test2', %s);", [1 if self.is_sqlite else True])

        with self.assertNumQueries(0):
            data2 = list(Test.objects.values_list('name', flat=True))
            self.assertListEqual(data2, ['test1'])

        invalidate('cachalot.Test')

        with self.assertNumQueries(1):
            data3 = list(Test.objects.values_list('name', flat=True))
            self.assertListEqual(data3, ['test1', 'test2'])

    def test_invalidate_models(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.values_list('name', flat=True))
            self.assertListEqual(data1, ['test1'])

        with self.settings(CACHALOT_INVALIDATE_RAW=False):
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO cachalot_test (name, public) "
                    "VALUES ('test2', %s);", [1 if self.is_sqlite else True])

        with self.assertNumQueries(0):
            data2 = list(Test.objects.values_list('name', flat=True))
            self.assertListEqual(data2, ['test1'])

        invalidate(Test)

        with self.assertNumQueries(1):
            data3 = list(Test.objects.values_list('name', flat=True))
            self.assertListEqual(data3, ['test1', 'test2'])

    def test_invalidate_all(self):
        with self.assertNumQueries(1):
            Test.objects.get()

        with self.assertNumQueries(0):
            Test.objects.get()

        invalidate()

        with self.assertNumQueries(1):
            Test.objects.get()

    def test_invalidate_all_in_atomic(self):
        with transaction.atomic():
            with self.assertNumQueries(1):
                Test.objects.get()

            with self.assertNumQueries(0):
                Test.objects.get()

            invalidate()

            with self.assertNumQueries(1):
                Test.objects.get()

        with self.assertNumQueries(1):
            Test.objects.get()

    def test_get_last_invalidation(self):
        invalidate()
        timestamp = get_last_invalidation()
        self.assertAlmostEqual(timestamp, time(), delta=0.1)

        sleep(0.1)

        invalidate('cachalot_test')
        timestamp = get_last_invalidation('cachalot_test')
        self.assertAlmostEqual(timestamp, time(), delta=0.1)
        same_timestamp = get_last_invalidation('cachalot.Test')
        self.assertEqual(same_timestamp, timestamp)
        same_timestamp = get_last_invalidation(Test)
        self.assertEqual(same_timestamp, timestamp)

        timestamp = get_last_invalidation('cachalot_testparent')
        self.assertNotAlmostEqual(timestamp, time(), delta=0.1)
        timestamp = get_last_invalidation('cachalot_testparent',
                                          'cachalot_test')
        self.assertAlmostEqual(timestamp, time(), delta=0.1)

    def test_get_last_invalidation_template_tag(self):
        # Without arguments
        original_timestamp = engines['django'].from_string(
            "{{ timestamp }}"
        ).render({
            'timestamp': get_last_invalidation(),
        })

        template = engines['django'].from_string("""
        {% load cachalot %}
        {% get_last_invalidation as timestamp %}
        {{ timestamp }}
        """)
        timestamp = template.render().strip()

        self.assertNotEqual(timestamp, '')
        self.assertNotEqual(timestamp, '0.0')
        self.assertAlmostEqual(float(timestamp), float(original_timestamp),
                               delta=0.1)

        # With arguments
        original_timestamp = engines['django'].from_string(
            "{{ timestamp }}"
        ).render({
            'timestamp': get_last_invalidation('auth.Group', 'cachalot_test'),
        })

        template = engines['django'].from_string("""
        {% load cachalot %}
        {% get_last_invalidation 'auth.Group' 'cachalot_test' as timestamp %}
        {{ timestamp }}
        """)
        timestamp = template.render().strip()

        self.assertNotEqual(timestamp, '')
        self.assertNotEqual(timestamp, '0.0')
        self.assertAlmostEqual(float(timestamp), float(original_timestamp),
                               delta=0.1)

        # While using the `cache` template tag, with invalidation
        template = engines['django'].from_string("""
        {% load cachalot cache %}
        {% get_last_invalidation 'auth.Group' 'cachalot_test' as timestamp %}
        {% cache 10 cache_key_name timestamp %}
            {{ content }}
        {% endcache %}
        """)
        content = template.render({'content': 'something'}).strip()
        self.assertEqual(content, 'something')
        content = template.render({'content': 'anything'}).strip()
        self.assertEqual(content, 'something')
        invalidate('cachalot_test')
        content = template.render({'content': 'yet another'}).strip()
        self.assertEqual(content, 'yet another')

    def test_get_last_invalidation_jinja2(self):
        original_timestamp = engines['jinja2'].from_string(
            "{{ timestamp }}"
        ).render({
            'timestamp': get_last_invalidation('auth.Group', 'cachalot_test'),
        })
        template = engines['jinja2'].from_string(
            "{{ get_last_invalidation('auth.Group', 'cachalot_test') }}")
        timestamp = template.render({})

        self.assertNotEqual(timestamp, '')
        self.assertNotEqual(timestamp, '0.0')
        self.assertAlmostEqual(float(timestamp), float(original_timestamp),
                               delta=0.1)

    def test_cache_jinja2(self):
        # Invalid arguments
        with self.assertRaises(TemplateSyntaxError,
                               msg="'invalid' is not a valid keyword argument "
                                   "for {% cache %}"):
            engines['jinja2'].from_string("""
            {% cache cache_key='anything', invalid='what?' %}{% endcache %}
            """)
        with self.assertRaises(ValueError, msg='You must set `cache_key` when '
                                               'the template is not a file.'):
            engines['jinja2'].from_string(
                '{% cache %} broken {% endcache %}').render()

        # With the minimum number of arguments
        template = engines['jinja2'].from_string("""
        {%- cache cache_key='first' -%}
            {{ content1 }}
        {%- endcache -%}
        {%- cache cache_key='second' -%}
            {{ content2 }}
        {%- endcache -%}
        """)
        content = template.render({'content1': 'abc', 'content2': 'def'})
        self.assertEqual(content, 'abcdef')
        invalidate()
        content = template.render({'content1': 'ghi', 'content2': 'jkl'})
        self.assertEqual(content, 'abcdef')

        # With the maximum number of arguments
        template = engines['jinja2'].from_string("""
        {%- cache get_last_invalidation('auth.Group', 'cachalot_test',
                                        cache_alias=cache),
                 timeout=10, cache_key='cache_key_name', cache_alias=cache -%}
            {{ content }}
        {%- endcache -%}
        """)
        content = template.render({'content': 'something',
                                   'cache': self.cache_alias2})
        self.assertEqual(content, 'something')
        content = template.render({'content': 'anything',
                                   'cache': self.cache_alias2})
        self.assertEqual(content, 'something')
        invalidate('cachalot_test', cache_alias=DEFAULT_CACHE_ALIAS)
        content = template.render({'content': 'yet another',
                                   'cache': self.cache_alias2})
        self.assertEqual(content, 'something')
        invalidate('cachalot_test')
        content = template.render({'content': 'will you change?',
                                   'cache': self.cache_alias2})
        self.assertEqual(content, 'will you change?')
        caches[self.cache_alias2].clear()
        content = template.render({'content': 'better!',
                                   'cache': self.cache_alias2})
        self.assertEqual(content, 'better!')


class CommandTestCase(TransactionTestCase):
    multi_db = True

    def setUp(self):
        self.db_alias2 = next(alias for alias in settings.DATABASES
                              if alias != DEFAULT_DB_ALIAS)

        self.cache_alias2 = next(alias for alias in settings.CACHES
                                 if alias != DEFAULT_CACHE_ALIAS)

        self.t1 = Test.objects.create(name='test1')
        self.t2 = Test.objects.using(self.db_alias2).create(name='test2')
        self.u = User.objects.create_user('test')

    def test_invalidate_cachalot(self):
        with self.assertNumQueries(1):
            self.assertListEqual(list(Test.objects.all()), [self.t1])
        call_command('invalidate_cachalot', verbosity=0)
        with self.assertNumQueries(1):
            self.assertListEqual(list(Test.objects.all()), [self.t1])

        call_command('invalidate_cachalot', 'auth', verbosity=0)
        with self.assertNumQueries(0):
            self.assertListEqual(list(Test.objects.all()), [self.t1])

        call_command('invalidate_cachalot', 'cachalot', verbosity=0)
        with self.assertNumQueries(1):
            self.assertListEqual(list(Test.objects.all()), [self.t1])

        call_command('invalidate_cachalot', 'cachalot.testchild', verbosity=0)
        with self.assertNumQueries(0):
            self.assertListEqual(list(Test.objects.all()), [self.t1])

        call_command('invalidate_cachalot', 'cachalot.test', verbosity=0)
        with self.assertNumQueries(1):
            self.assertListEqual(list(Test.objects.all()), [self.t1])

        with self.assertNumQueries(1):
            self.assertListEqual(list(User.objects.all()), [self.u])
        call_command('invalidate_cachalot', 'cachalot.test', 'auth.user',
                     verbosity=0)
        with self.assertNumQueries(1):
            self.assertListEqual(list(Test.objects.all()), [self.t1])
        with self.assertNumQueries(1):
            self.assertListEqual(list(User.objects.all()), [self.u])

    @skipIf(len(settings.DATABASES) == 1,
            'We can’t change the DB used since there’s only one configured')
    def test_invalidate_cachalot_multi_db(self):
        with self.assertNumQueries(1):
            self.assertListEqual(list(Test.objects.all()), [self.t1])
        call_command('invalidate_cachalot', verbosity=0,
                     db_alias=self.db_alias2)
        with self.assertNumQueries(0):
            self.assertListEqual(list(Test.objects.all()), [self.t1])

        with self.assertNumQueries(1, using=self.db_alias2):
            self.assertListEqual(list(Test.objects.using(self.db_alias2)),
                                 [self.t2])
        call_command('invalidate_cachalot', verbosity=0,
                     db_alias=self.db_alias2)
        with self.assertNumQueries(1, using=self.db_alias2):
            self.assertListEqual(list(Test.objects.using(self.db_alias2)),
                                 [self.t2])

    @skipIf(len(settings.CACHES) == 1,
            'We can’t change the cache used since there’s only one configured')
    def test_invalidate_cachalot_multi_cache(self):
        with self.assertNumQueries(1):
            self.assertListEqual(list(Test.objects.all()), [self.t1])
        call_command('invalidate_cachalot', verbosity=0,
                     cache_alias=self.cache_alias2)
        with self.assertNumQueries(0):
            self.assertListEqual(list(Test.objects.all()), [self.t1])

        with self.assertNumQueries(1):
            with self.settings(CACHALOT_CACHE=self.cache_alias2):
                self.assertListEqual(list(Test.objects.all()), [self.t1])
        call_command('invalidate_cachalot', verbosity=0,
                     cache_alias=self.cache_alias2)
        with self.assertNumQueries(1):
            with self.settings(CACHALOT_CACHE=self.cache_alias2):
                self.assertListEqual(list(Test.objects.all()), [self.t1])
