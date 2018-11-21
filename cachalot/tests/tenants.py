from unittest import mock

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import connection, connections
from django.test import SimpleTestCase, override_settings

from cachalot import utils
from cachalot.cache import make_key
from cachalot.tenants import tenant_handler
from cachalot.tests.models import PostgresModel, TestChild


class CacheTestCase(SimpleTestCase):
    def test_make_key_public(self):
        with mock.patch(
            'cachalot.tenants.TenantHandler.public_schema_name',
            new_callable=mock.PropertyMock,
        ) as mock_public:
            mock_public.return_value = 'public'
            prefix = 'prefix'
            key = 'test_key'
            tenant_handler.public_schema_keys.add(key)

            self.assertEqual(
                make_key(key, prefix, 1), 'public:{}:1:{}'.format(prefix, key)
            )

            tenant_handler.public_schema_keys.clear()

    def test_make_key_tenant(self):
        prefix = 'prefix'
        key = 'test_key'
        connection.schema_name = 'tenant_schema'
        self.assertEqual(
            make_key(key, 'prefix', 1),
            '{}:{}:1:{}'.format(connection.schema_name, prefix, key),
        )


@override_settings(
    CACHALOT_TABLE_KEYGEN='cachalot.utils.get_multi_tenant_table_cache_key'
)
class TenantHandlerTestCase(SimpleTestCase):
    def test_get_public_schema_name_not_configured_raises_exception(self):
        with self.assertRaises(ImproperlyConfigured):

            tenant_handler.public_schema_name

    def test_is_multi_tenant_database_false(self):
        for alias in connections:
            self.assertFalse(tenant_handler.is_multi_tenant_database(alias))

    def test_is_m2m_relation(self):
        model = TestChild()
        m2m_field_name = 'permissions'
        self.assertTrue(
            tenant_handler._is_m2m_relation(
                model, '{}_{}'.format(model._meta.db_table, m2m_field_name)
            )
        )

    def test_get_tenant_config_for_table_shared_app(self):
        with self.settings(SHARED_APPS=['cachalot'], TENANT_APPS=[]):
            with mock.patch(
                'cachalot.tenants.apps.get_models', return_value=[PostgresModel()]
            ):

                self.assertEqual(
                    (True, False),
                    tenant_handler.get_tenant_config_for_table(
                        '"public"."cachalot_postgresmodel"'
                    ),
                )
                tenant_handler._tenant_config = {}

    def test_get_tenant_config_for_table_tenant_app(self):

        with self.settings(SHARED_APPS=[], TENANT_APPS=['cachalot']):
            db_model = PostgresModel()
            with mock.patch('cachalot.tenants.apps.get_models', return_value=[db_model]):
                self.assertEqual(
                    (False, True),
                    tenant_handler.get_tenant_config_for_table(
                        '"public"."cachalot_postgresmodel"'  # Value of 'schema' not relevant for this test
                    ),
                )
                tenant_handler._tenant_config = {}

    def test_get_tenant_config_for_table_tenant_app_public_active(self):
        with self.settings(SHARED_APPS=[], TENANT_APPS=['cachalot']):

            db_model = PostgresModel()
            with mock.patch('cachalot.tenants.apps.get_models', return_value=[db_model]):
                self.assertEqual(
                    (False, True),
                    tenant_handler.get_tenant_config_for_table(
                        '"public"."cachalot_postgresmodel"'  # Value of 'schema' not relevant for this test
                    ),
                )
                tenant_handler._tenant_config = {}

    def test_get_active_schema_for_table_tenant_is_active(self):
        with mock.patch(
            'cachalot.tenants.TenantHandler.public_schema_name',
            new_callable=mock.PropertyMock,
        ) as mock_public:
            mock_public.return_value = 'public'
            with mock.patch(
                'cachalot.tenants.TenantHandler.get_tenant_config_for_table', return_value=(True, True)
            ):

                connection.schema_name = 'test_schema'
                self.assertEqual(
                    tenant_handler.get_active_schema_for_table('test_table'),
                    'test_schema',
                )

    def test_get_active_schema_for_table_falls_back_to_public(self):
        with mock.patch(
            'cachalot.tenants.TenantHandler.public_schema_name',
            new_callable=mock.PropertyMock,
        ) as mock_public:
            mock_public.return_value = 'public'
            with mock.patch(
                'cachalot.tenants.TenantHandler.get_tenant_config_for_table', return_value=(True, True)
            ):

                self.assertEqual(
                    tenant_handler.get_active_schema_for_table('test_table'), 'public'
                )

    def test_get_active_schema_for_table_error(self):
        with mock.patch(
            'cachalot.tenants.TenantHandler.public_schema_name',
            new_callable=mock.PropertyMock,
        ) as mock_public:
            mock_public.return_value = 'public'
            with mock.patch(
                'cachalot.tenants.TenantHandler.get_tenant_config_for_table', return_value=(False, True)
            ):
                with self.assertRaises(ValidationError):

                    connection.schema_name = 'public'
                    self.assertEqual(
                        tenant_handler.get_active_schema_for_table('test_table'),
                        'test_schema',
                    )

    def test_get_multi_tenant_table_cache_key_adds_public_keys(self):
        with mock.patch(
            'cachalot.tenants.TenantHandler.public_schema_name',
            new_callable=mock.PropertyMock,
        ) as mock_public:
            mock_public.return_value = 'public'
            with mock.patch(
                'cachalot.tenants.TenantHandler.get_active_schema_for_table', return_value='public'
            ):

                db_alias = 'default'
                table = 'test_table'
                connection.schema_name = 'test_schema'

                key = utils.get_multi_tenant_table_cache_key(db_alias, table)
                self.assertIn(key, tenant_handler.public_schema_keys)

    def test_get_multi_tenant_table_cache_key_is_idempotent(self):
        with mock.patch(
            'cachalot.tenants.TenantHandler.public_schema_name',
            new_callable=mock.PropertyMock,
        ) as mock_public:
            mock_public.return_value = 'public'
            with mock.patch(
                'cachalot.tenants.TenantHandler.get_active_schema_for_table', return_value='test_schema'
            ):

                db_alias = 'default'
                table = 'test_table'
                connection.schema_name = 'test_schema'

                key = utils.get_multi_tenant_table_cache_key(db_alias, table)
                self.assertEqual(
                    key, utils.get_table_cache_key(db_alias, table)
                )
