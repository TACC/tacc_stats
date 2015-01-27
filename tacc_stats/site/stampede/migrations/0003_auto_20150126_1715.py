# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('stampede', '0002_auto_20150126_1700'),
    ]

    operations = [
        migrations.AlterField(
            model_name='job',
            name='exe_list',
            field=models.CharField(max_length=16384, null=True),
            preserve_default=True,
        ),
    ]
