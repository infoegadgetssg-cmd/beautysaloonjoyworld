from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0004_stylistavailability'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='refund_status',
            field=models.CharField(
                choices=[('NOT_REQUIRED', 'Not Required'), ('PENDING', 'Pending'), ('REFUNDED', 'Refunded')],
                default='NOT_REQUIRED',
                max_length=20,
            ),
        ),
    ]

