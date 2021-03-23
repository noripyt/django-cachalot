from django.conf import settings
from django.contrib.postgres.fields import (
    ArrayField, HStoreField, IntegerRangeField,
    DateRangeField, DateTimeRangeField)
from django.contrib.postgres.operations import (
    HStoreExtension, UnaccentExtension)
from django.db import models, migrations


def extra_regular_available_fields():
    fields = []
    try:
        # TODO Add to module import when Dj40 dropped
        from django import VERSION as DJANGO_VERSION
        from django.contrib.postgres.fields import JSONField
        if float(".".join(map(str, DJANGO_VERSION[:2]))) > 3.0:
            fields.append(('json', JSONField(null=True, blank=True)))
    except ImportError:
        pass

    return fields


def extra_postgres_available_fields():
    fields = []
    try:
        # TODO Remove when Dj31 support is dropped
        from django.contrib.postgres.fields import FloatRangeField
        fields.append(('float_range', FloatRangeField(null=True, blank=True)))
    except ImportError:
        pass

    try:
        # TODO Add to module import when Dj31 is dropped
        from django.contrib.postgres.fields import DecimalRangeField
        fields.append(('decimal_range', DecimalRangeField(null=True, blank=True)))
    except ImportError:
        pass

    # Future proofing with Django 40 deprecation
    try:
        # TODO Remove when Dj40 support is dropped
        from django.contrib.postgres.fields import JSONField
        fields.append(('json', JSONField(null=True, blank=True)))
    except ImportError:
        pass

    return fields


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
                ('owner', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)),
                ('permission', models.ForeignKey(blank=True, to='auth.Permission', null=True, on_delete=models.PROTECT)),
                ('a_float', models.FloatField(null=True, blank=True)),
                ('a_decimal', models.DecimalField(null=True, blank=True, max_digits=5, decimal_places=2)),
                ('bin', models.BinaryField(null=True, blank=True)),
                ('ip', models.GenericIPAddressField(null=True, blank=True)),
                ('duration', models.DurationField(null=True, blank=True)),
                ('uuid', models.UUIDField(null=True, blank=True)),
            ] + extra_regular_available_fields(),
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
        HStoreExtension(),
        UnaccentExtension(),
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
                ('date_range', DateRangeField(null=True, blank=True)),
                ('datetime_range', DateTimeRangeField(null=True, blank=True)),
            ] + extra_postgres_available_fields(),
        ),
        migrations.RunSQL('CREATE TABLE cachalot_unmanagedmodel '
                          '(id SERIAL PRIMARY KEY, name VARCHAR(50));'),
    ]
