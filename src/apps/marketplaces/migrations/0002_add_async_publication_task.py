# Generated migration for AsyncPublicationTask model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('marketplaces', '0001_initial'),
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='marketplace',
            name='webhook_url',
            field=models.URLField(blank=True, help_text='Marketplace-specific webhook URL'),
        ),
        migrations.CreateModel(
            name='AsyncPublicationTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('task_id', models.CharField(max_length=255, unique=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('enhancing', 'Enhancing with AI'), ('enhanced', 'Enhanced'), ('publishing', 'Publishing to Marketplace'), ('published', 'Published'), ('webhook_sent', 'Webhook Sent'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('current_step', models.CharField(blank=True, max_length=100)),
                ('steps_completed', models.JSONField(default=list)),
                ('total_steps', models.IntegerField(default=4)),
                ('enhancement_retries', models.IntegerField(default=0)),
                ('publication_retries', models.IntegerField(default=0)),
                ('webhook_retries', models.IntegerField(default=0)),
                ('enhancement_result', models.JSONField(blank=True, default=dict)),
                ('publication_result', models.JSONField(blank=True, default=dict)),
                ('webhook_result', models.JSONField(blank=True, default=dict)),
                ('error_details', models.JSONField(blank=True, default=dict)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('marketplace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketplaces.marketplace')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='products.product')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]