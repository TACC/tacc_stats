# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('machine', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='MIC_Usage',
            field=models.FloatField(null=True),
            preserve_default=True,
        ),
    ]
