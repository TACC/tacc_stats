# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('stampede', '0003_auto_20150126_1715'),
    ]

    operations = [
        migrations.AlterField(
            model_name='job',
            name='exe_list',
            field=models.TextField(null=True),
            preserve_default=True,
        ),
    ]
