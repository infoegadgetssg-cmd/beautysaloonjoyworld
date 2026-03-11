from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0003_stylist_shift_end_stylist_shift_start_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='service_color',
            field=models.CharField(choices=[('#3b82f6', 'Blue'), ('#9333ea', 'Purple'), ('#10b981', 'Green'), ('#f59e0b', 'Orange'), ('#ef4444', 'Red'), ('#06b6d4', 'Cyan'), ('#ec4899', 'Pink'), ('#84cc16', 'Lime'), ('#6366f1', 'Indigo'), ('#64748b', 'Gray')], default='#3b82f6', max_length=7),
        ),
    ]
