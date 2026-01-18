# Generated migration for shared data contract
# DO NOT MODIFY - this is part of the symlinked contract

from django.db import migrations, models
import django.db.models.deletion
import uuid


def content_addressable_path(instance, filename):
    """Generate storage path for content-addressable file."""
    hash_value = instance.hash
    ext = filename.split('.')[-1] if '.' in filename else ''
    if ext:
        return f"cas/{hash_value[:2]}/{hash_value[2:4]}/{hash_value}.{ext}"
    return f"cas/{hash_value[:2]}/{hash_value[2:4]}/{hash_value}"


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='FileContent',
            fields=[
                ('hash', models.CharField(
                    help_text='SHA-256 hash of file content',
                    max_length=64,
                    primary_key=True,
                    serialize=False
                )),
                ('file', models.FileField(
                    help_text='Path to physical file in content-addressable storage',
                    upload_to=content_addressable_path
                )),
                ('size', models.BigIntegerField(
                    help_text='File size in bytes'
                )),
                ('reference_count', models.PositiveIntegerField(
                    default=1,
                    help_text='Number of File records referencing this content'
                )),
                ('created_at', models.DateTimeField(
                    auto_now_add=True,
                    help_text='When this content was first uploaded'
                )),
            ],
            options={
                'verbose_name': 'File Content',
                'verbose_name_plural': 'File Contents',
            },
        ),
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4,
                    editable=False,
                    primary_key=True,
                    serialize=False
                )),
                ('original_filename', models.CharField(
                    help_text='Original filename as uploaded by user',
                    max_length=255
                )),
                ('file_type', models.CharField(
                    help_text='MIME type of the file',
                    max_length=100
                )),
                ('uploaded_at', models.DateTimeField(
                    auto_now_add=True,
                    help_text='When this file was uploaded'
                )),
                ('content', models.ForeignKey(
                    help_text='Reference to the actual file content',
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='files',
                    to='contracts.filecontent'
                )),
            ],
            options={
                'verbose_name': 'File',
                'verbose_name_plural': 'Files',
                'ordering': ['-uploaded_at'],
            },
        ),
        migrations.AddIndex(
            model_name='filecontent',
            index=models.Index(fields=['size'], name='filecontent_size_idx'),
        ),
        migrations.AddIndex(
            model_name='file',
            index=models.Index(fields=['original_filename'], name='file_filename_idx'),
        ),
        migrations.AddIndex(
            model_name='file',
            index=models.Index(fields=['file_type'], name='file_type_idx'),
        ),
        migrations.AddIndex(
            model_name='file',
            index=models.Index(fields=['uploaded_at'], name='file_uploaded_idx'),
        ),
        migrations.AddIndex(
            model_name='file',
            index=models.Index(fields=['file_type', 'uploaded_at'], name='file_type_date_idx'),
        ),
    ]
