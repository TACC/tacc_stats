# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('stampede', '0007_auto_20150316_1604'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='Load_All',
            field=models.BigIntegerField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='job',
            name='cpu_usage',
            field=models.FloatField(null=True),
            preserve_default=True,
        ),
    ]
