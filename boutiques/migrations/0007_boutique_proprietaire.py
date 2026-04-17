"""Migration : FK proprietaire sur Boutique + wa_phone_id/wa_token optionnels."""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("boutiques", "0006_otpcode"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Rendre wa_phone_id et wa_token optionnels
        migrations.AlterField(
            model_name="boutique",
            name="wa_phone_id",
            field=models.CharField(blank=True, max_length=100, verbose_name="WhatsApp Phone ID (360dialog)"),
        ),
        migrations.AlterField(
            model_name="boutique",
            name="wa_token",
            field=models.CharField(blank=True, max_length=500, verbose_name="Token API WhatsApp (360dialog)"),
        ),
        # Ajouter la FK proprietaire
        migrations.AddField(
            model_name="boutique",
            name="proprietaire",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="boutique",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Compte propriétaire",
            ),
        ),
    ]
