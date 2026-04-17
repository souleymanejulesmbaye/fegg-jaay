"""Migration : ajout du modèle OTPCode pour l'authentification client web."""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("boutiques", "0005_boutique_slug"),
    ]

    operations = [
        migrations.CreateModel(
            name="OTPCode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=6)),
                ("expires_at", models.DateTimeField()),
                ("utilise", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "client",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="otps",
                        to="boutiques.client",
                    ),
                ),
            ],
            options={
                "verbose_name": "Code OTP",
                "verbose_name_plural": "Codes OTP",
                "ordering": ["-created_at"],
            },
        ),
    ]
