# Generated by Django 2.0.6 on 2018-06-15 02:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('explorer', '0002_auto_20180615_0247'),
    ]

    operations = [
        migrations.AlterField(
            model_name='taxonomy',
            name='subclass',
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name='taxonomy',
            name='taxclass',
            field=models.CharField(db_column='class', max_length=50, verbose_name='class'),
        ),
    ]
