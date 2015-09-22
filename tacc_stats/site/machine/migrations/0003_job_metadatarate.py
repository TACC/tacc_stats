# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('machine', '0002_job_mic_usage'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='MetaDataRate',
            field=models.FloatField(null=True),
            preserve_default=True,
        ),
    ]
