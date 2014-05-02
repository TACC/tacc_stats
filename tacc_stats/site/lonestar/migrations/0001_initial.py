# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'LS4Job'
        db.create_table(u'lonestar_ls4job', (
            ('id', self.gf('django.db.models.fields.BigIntegerField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('start_time', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('end_time', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('start_epoch', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
            ('end_epoch', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
            ('run_time', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
            ('queue', self.gf('django.db.models.fields.CharField')(max_length=16, null=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128, null=True)),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=16, null=True)),
            ('nodes', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
            ('cores', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
            ('path', self.gf('django.db.models.fields.FilePathField')(max_length=128, null=True)),
            ('date', self.gf('django.db.models.fields.DateField')(null=True)),
            ('user', self.gf('django.db.models.fields.CharField')(max_length=128, null=True)),
            ('exe', self.gf('django.db.models.fields.CharField')(max_length=128, null=True)),
            ('cwd', self.gf('django.db.models.fields.CharField')(max_length=128, null=True)),
            ('threads', self.gf('django.db.models.fields.BigIntegerField')(null=True)),
        ))
        db.send_create_signal(u'lonestar', ['LS4Job'])


    def backwards(self, orm):
        # Deleting model 'LS4Job'
        db.delete_table(u'lonestar_ls4job')


    models = {
        u'lonestar.ls4job': {
            'Meta': {'object_name': 'LS4Job'},
            'cores': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'cwd': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {'null': 'True'}),
            'end_epoch': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'end_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'exe': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'}),
            'id': ('django.db.models.fields.BigIntegerField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'}),
            'nodes': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'path': ('django.db.models.fields.FilePathField', [], {'max_length': '128', 'null': 'True'}),
            'project': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'queue': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True'}),
            'run_time': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'start_epoch': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True'}),
            'threads': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'})
        }
    }

    complete_apps = ['lonestar']