# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('stampede', '0005_auto_20150217_0933'),
        ]
    operations = [
        migrations.AddField(
            model_name='job',
            name='exec_path',
            field=models.CharField(max_length=1024, null=True),
            preserve_default=True,
            ),
        ]
