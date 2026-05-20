from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0002_initial'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='userprofile',
            name='user_profil_supabas_02edd6_idx',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='supabase_uid',
        ),
        migrations.AddField(
            model_name='userprofile',
            name='password',
            field=models.CharField(default='!', max_length=128),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='userprofile',
            name='email_verification_token',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='email_verification_token_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='password_reset_token',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='password_reset_token_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
