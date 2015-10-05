# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('machine', '0003_job_metadatarate'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='InternodeIBAveBW',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='job',
            name='InternodeIBMaxBW',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='job',
            name='LnetAveBW',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='job',
            name='LnetMaxBW',
            field=models.FloatField(null=True),
        ),
    ]
