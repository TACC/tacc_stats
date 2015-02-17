# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('stampede', '0004_auto_20150126_1719'),
    ]

    operations = [
        migrations.CreateModel(
            name='Libraries',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_path', models.CharField(max_length=1024)),
                ('module_name', models.CharField(max_length=64)),
                ('jobs', models.ManyToManyField(to='stampede.Job')),
            ],
            options={
                'ordering': ('object_path',),
            },
            bases=(models.Model,),
        ),
    ]
