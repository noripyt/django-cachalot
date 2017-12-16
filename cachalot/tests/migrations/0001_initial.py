# coding: utf-8

from __future__ import unicode_literals

from django import VERSION as django_version
from django.conf import settings
from django.contrib.postgres.fields import (
    ArrayField, HStoreField,
    IntegerRangeField, FloatRangeField, DateRangeField, DateTimeRangeField)
from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Test',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=20)),
                ('public', models.BooleanField(default=False)),
                ('date', models.DateField(null=True, blank=True)),
                ('datetime', models.DateTimeField(null=True, blank=True)),
                ('owner', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)),
                ('permission', models.ForeignKey(blank=True, to='auth.Permission', null=True, on_delete=models.CASCADE)),
                ('a_float', models.FloatField(null=True, blank=True)),
                ('a_decimal', models.DecimalField(null=True, blank=True, max_digits=5, decimal_places=2)),
                ('bin', models.BinaryField(null=True, blank=True)),
                ('ip', models.GenericIPAddressField(null=True, blank=True)),
                ('duration', models.DurationField(null=True, blank=True)),
                ('uuid', models.UUIDField(null=True, blank=True)),
            ],
            options={
                'ordering': ('name',),
            },
        ),
        migrations.CreateModel(
            name='TestParent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='TestChild',
            fields=[
                ('testparent_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='cachalot.TestParent', on_delete=models.CASCADE)),
                ('public', models.BooleanField(default=False)),
                ('permissions', models.ManyToManyField('auth.Permission', blank=True))
            ],
            bases=('cachalot.testparent',),
        ),
        migrations.RunSQL('CREATE EXTENSION hstore;',
                          hints={'extension': 'hstore'}),
        migrations.RunSQL('CREATE EXTENSION unaccent;',
                          hints={'extension': 'unaccent'}),
        migrations.CreateModel(
            name='PostgresModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False,
                                        auto_created=True, primary_key=True)),
                ('int_array', ArrayField(
                    models.IntegerField(null=True, blank=True), size=3,
                    null=True, blank=True)),
                ('hstore', HStoreField(null=True, blank=True)),
                ('int_range', IntegerRangeField(null=True, blank=True)),
                ('float_range', FloatRangeField(null=True, blank=True)),
                ('date_range', DateRangeField(null=True, blank=True)),
                ('datetime_range', DateTimeRangeField(null=True, blank=True)),
            ],
        ),
    ]


if django_version[:2] >= (1, 9):
    from django.contrib.postgres.fields import JSONField
    Migration.operations.append(
        migrations.AddField('PostgresModel', 'json',
                            JSONField(null=True, blank=True))
    )
