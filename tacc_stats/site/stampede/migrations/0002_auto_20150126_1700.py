# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('stampede', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='exe_list',
            field=models.CharField(max_length=1024, null=True),
            preserve_default=True,
        ),
    ]
