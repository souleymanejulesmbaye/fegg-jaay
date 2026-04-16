"""Migration : ajout du champ reference_paiement sur Commande."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("boutiques", "0003_seed_teranga_shop"),
    ]

    operations = [
        migrations.AddField(
            model_name="commande",
            name="reference_paiement",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Numéro de transaction Wave/Orange Money fourni par le client",
                max_length=100,
            ),
            preserve_default=False,
        ),
    ]
