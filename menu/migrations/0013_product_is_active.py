from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("menu", "0012_order_payment_method_order_status_updated_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
    ]
