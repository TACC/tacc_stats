# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('stampede', '0006_auto_20150217_1528'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='requested_time',
            field=models.PositiveIntegerField(null=True),
            preserve_default=True,
        ),
    ]
