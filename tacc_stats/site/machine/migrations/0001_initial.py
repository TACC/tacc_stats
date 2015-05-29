# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Host',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=128)),
            ],
            options={
                'ordering': ('name',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', models.BigIntegerField(serialize=False, primary_key=True)),
                ('uid', models.BigIntegerField(null=True)),
                ('project', models.CharField(max_length=128)),
                ('start_time', models.DateTimeField(null=True)),
                ('end_time', models.DateTimeField(null=True)),
                ('start_epoch', models.PositiveIntegerField(null=True)),
                ('end_epoch', models.PositiveIntegerField(null=True)),
                ('run_time', models.PositiveIntegerField(null=True)),
                ('requested_time', models.PositiveIntegerField(null=True)),
                ('queue_time', models.PositiveIntegerField(null=True)),
                ('queue', models.CharField(max_length=16, null=True)),
                ('name', models.CharField(max_length=128, null=True)),
                ('status', models.CharField(max_length=16, null=True)),
                ('nodes', models.PositiveIntegerField(null=True)),
                ('cores', models.PositiveIntegerField(null=True)),
                ('wayness', models.PositiveIntegerField(null=True)),
                ('path', models.FilePathField(max_length=128, null=True)),
                ('date', models.DateField(null=True, db_index=True)),
                ('user', models.CharField(max_length=128, null=True)),
                ('exe', models.CharField(max_length=128, null=True)),
                ('exec_path', models.CharField(max_length=1024, null=True)),
                ('exe_list', models.TextField(null=True)),
                ('cwd', models.CharField(max_length=128, null=True)),
                ('threads', models.BigIntegerField(null=True)),
                ('cpi', models.FloatField(null=True)),
                ('cpld', models.FloatField(null=True)),
                ('mbw', models.FloatField(null=True)),
                ('idle', models.FloatField(null=True)),
                ('cat', models.FloatField(null=True)),
                ('mem', models.FloatField(null=True)),
                ('packetrate', models.FloatField(null=True)),
                ('packetsize', models.FloatField(null=True)),
                ('GigEBW', models.FloatField(null=True)),
                ('flops', models.FloatField(null=True)),
                ('VecPercent', models.FloatField(null=True)),
                ('Load_All', models.BigIntegerField(null=True)),
                ('Load_L1Hits', models.BigIntegerField(null=True)),
                ('Load_L2Hits', models.BigIntegerField(null=True)),
                ('Load_LLCHits', models.BigIntegerField(null=True)),
                ('CPU_Usage', models.FloatField(null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Libraries',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_path', models.CharField(max_length=1024)),
                ('module_name', models.CharField(max_length=64)),
                ('jobs', models.ManyToManyField(to='machine.Job')),
            ],
            options={
                'ordering': ('object_path',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TestInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('test_name', models.CharField(max_length=128)),
                ('field_name', models.CharField(max_length=128)),
                ('threshold', models.FloatField(null=True)),
                ('comparator', models.CharField(max_length=2)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='host',
            name='jobs',
            field=models.ManyToManyField(to='machine.Job'),
            preserve_default=True,
        ),
    ]
