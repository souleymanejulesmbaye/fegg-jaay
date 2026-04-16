"""Migration : ajout du champ slug sur Boutique."""

from django.db import migrations, models
import django.utils.text


def generer_slugs(apps, schema_editor):
    Boutique = apps.get_model("boutiques", "Boutique")
    for boutique in Boutique.objects.all():
        if not boutique.slug:
            boutique.slug = django.utils.text.slugify(boutique.nom)
            boutique.save(update_fields=["slug"])


class Migration(migrations.Migration):

    dependencies = [
        ("boutiques", "0004_commande_reference_paiement"),
    ]

    operations = [
        migrations.AddField(
            model_name="boutique",
            name="slug",
            field=models.SlugField(
                blank=True,
                default="",
                unique=False,
                help_text="Identifiant URL de la boutique (ex: teranga-shop)",
                max_length=100,
            ),
            preserve_default=False,
        ),
        migrations.RunPython(generer_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="boutique",
            name="slug",
            field=models.SlugField(
                blank=True,
                unique=True,
                help_text="Identifiant URL de la boutique (ex: teranga-shop)",
                max_length=100,
            ),
        ),
    ]
