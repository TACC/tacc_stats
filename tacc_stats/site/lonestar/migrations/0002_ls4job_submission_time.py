# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('lonestar', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ls4job',
            name='submission_time',
            field=models.PositiveIntegerField(null=True),
            preserve_default=True,
        ),
    ]
