# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Job.mbw'
        db.add_column(u'stampede_job', 'mbw',
                      self.gf('django.db.models.fields.FloatField')(null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Job.mbw'
        db.delete_column(u'stampede_job', 'mbw')


    models = {
        u'stampede.job': {
            'Meta': {'object_name': 'Job'},
            'cores': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'cpi': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'cwd': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {'null': 'True', 'db_index': 'True'}),
            'end_epoch': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'end_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'exe': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'}),
            'id': ('django.db.models.fields.BigIntegerField', [], {'primary_key': 'True'}),
            'mbw': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'}),
            'nodes': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'path': ('django.db.models.fields.FilePathField', [], {'max_length': '128', 'null': 'True'}),
            'project': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'queue': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True'}),
            'queue_time': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'run_time': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'start_epoch': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True'}),
            'threads': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'uid': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'})
        }
    }

    complete_apps = ['stampede']