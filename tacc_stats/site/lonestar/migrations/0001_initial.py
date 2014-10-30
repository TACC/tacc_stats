# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='LS4Job',
            fields=[
                ('id', models.BigIntegerField(serialize=False, primary_key=True)),
                ('project', models.CharField(max_length=128)),
                ('start_time', models.DateTimeField(null=True)),
                ('end_time', models.DateTimeField(null=True)),
                ('start_epoch', models.PositiveIntegerField(null=True)),
                ('end_epoch', models.PositiveIntegerField(null=True)),
                ('run_time', models.PositiveIntegerField(null=True)),
                ('queue', models.CharField(max_length=16, null=True)),
                ('name', models.CharField(max_length=128, null=True)),
                ('status', models.CharField(max_length=16, null=True)),
                ('nodes', models.PositiveIntegerField(null=True)),
                ('cores', models.PositiveIntegerField(null=True)),
                ('path', models.FilePathField(max_length=128, null=True)),
                ('date', models.DateField(null=True, db_index=True)),
                ('user', models.CharField(max_length=128, null=True)),
                ('exe', models.CharField(max_length=128, null=True)),
                ('cwd', models.CharField(max_length=128, null=True)),
                ('threads', models.BigIntegerField(null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
