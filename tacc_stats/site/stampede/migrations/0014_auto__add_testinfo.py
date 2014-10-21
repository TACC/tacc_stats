# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'TestInfo'
        db.create_table(u'stampede_testinfo', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('test_name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('field_name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('threshold', self.gf('django.db.models.fields.FloatField')(null=True)),
            ('comparator', self.gf('django.db.models.fields.CharField')(max_length=2)),
        ))
        db.send_create_signal(u'stampede', ['TestInfo'])


    def backwards(self, orm):
        # Deleting model 'TestInfo'
        db.delete_table(u'stampede_testinfo')


    models = {
        u'stampede.host': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Host'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jobs': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['stampede.Job']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'stampede.job': {
            'GigEBW': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'Meta': {'object_name': 'Job'},
            'VecPercent': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'cat': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'cores': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'cpi': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'cwd': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {'null': 'True', 'db_index': 'True'}),
            'end_epoch': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'end_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'exe': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'}),
            'flops': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
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
        },
        u'stampede.testinfo': {
            'Meta': {'object_name': 'TestInfo'},
            'comparator': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'field_name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'test_name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'threshold': ('django.db.models.fields.FloatField', [], {'null': 'True'})
        }
    }

    complete_apps = ['stampede']