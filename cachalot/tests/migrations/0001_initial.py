# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


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
                ('owner', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('permission', models.ForeignKey(blank=True, to='auth.Permission', null=True)),
                ('bin', models.BinaryField(null=True, blank=True)),
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
                ('testparent_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='cachalot.TestParent')),
                ('public', models.BooleanField(default=False)),
                ('permissions', models.ManyToManyField('auth.Permission', blank=True))
            ],
            bases=('cachalot.testparent',),
        ),
    ]
