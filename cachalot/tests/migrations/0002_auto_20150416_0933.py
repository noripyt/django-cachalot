# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cachalot', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestOne',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='TestThese',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=20)),
            ],
        ),
        migrations.AddField(
            model_name='testone',
            name='have_lots_of_these',
            field=models.ManyToManyField(to='cachalot.TestThese', null=True, blank=True),
        ),
    ]
