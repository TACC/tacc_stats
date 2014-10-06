# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Job.packetrate'
        db.add_column(u'stampede_job', 'packetrate',
                      self.gf('django.db.models.fields.FloatField')(null=True),
                      keep_default=False)

        # Adding field 'Job.packetsize'
        db.add_column(u'stampede_job', 'packetsize',
                      self.gf('django.db.models.fields.FloatField')(null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Job.packetrate'
        db.delete_column(u'stampede_job', 'packetrate')

        # Deleting field 'Job.packetsize'
        db.delete_column(u'stampede_job', 'packetsize')


    models = {
        u'stampede.job': {
            'Meta': {'object_name': 'Job'},
            'cat': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'cores': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'cpi': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'cwd': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {'null': 'True', 'db_index': 'True'}),
            'end_epoch': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'end_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'exe': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'}),
            'id': ('django.db.models.fields.BigIntegerField', [], {'primary_key': 'True'}),
            'idle': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'mbw': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'mem': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'}),
            'nodes': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'packetrate': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'packetsize': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
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
            'user': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'}),
            'wayness': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'})
        }
    }

    complete_apps = ['stampede']
