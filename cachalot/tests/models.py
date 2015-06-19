# coding: utf-8

from __future__ import unicode_literals

from django.conf import settings
from django.db.models import (
    Model, CharField, ForeignKey, BooleanField, DateField, DateTimeField,
    ManyToManyField, BinaryField)


class Test(Model):
    name = CharField(max_length=20)
    owner = ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True)
    public = BooleanField(default=False)
    date = DateField(null=True, blank=True)
    datetime = DateTimeField(null=True, blank=True)
    permission = ForeignKey('auth.Permission', null=True, blank=True)
    bin = BinaryField(null=True, blank=True)

    class Meta(object):
        app_label = 'cachalot'
        ordering = ('name',)


class TestParent(Model):
    name = CharField(max_length=20)

    class Meta(object):
        app_label = 'cachalot'


class TestChild(TestParent):
    public = BooleanField(default=False)
    permissions = ManyToManyField('auth.Permission', blank=True)

    class Meta(object):
        app_label = 'cachalot'
