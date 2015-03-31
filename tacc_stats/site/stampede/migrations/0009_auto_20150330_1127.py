# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('stampede', '0008_auto_20150330_1107'),
    ]

    operations = [
        migrations.RenameField(
            model_name='job',
            old_name='cpu_usage',
            new_name='CPU_Usage',
        ),
    ]
