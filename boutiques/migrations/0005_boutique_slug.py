"""Migration : ajout du champ slug sur Boutique."""

from django.db import migrations, models


def generer_slugs(apps, schema_editor):
    from django.utils.text import slugify
    Boutique = apps.get_model("boutiques", "Boutique")
    for boutique in Boutique.objects.all():
        slug = slugify(boutique.nom)
        if not slug:
            slug = str(boutique.pk)[:8]
        # S'assurer que le slug est unique
        base = slug
        compteur = 1
        while Boutique.objects.filter(slug=slug).exclude(pk=boutique.pk).exists():
            slug = f"{base}-{compteur}"
            compteur += 1
        Boutique.objects.filter(pk=boutique.pk).update(slug=slug)


class Migration(migrations.Migration):

    dependencies = [
        ("boutiques", "0004_commande_reference_paiement"),
    ]

    operations = [
        # Étape 1 : ajouter la colonne sans contrainte unique
        migrations.AddField(
            model_name="boutique",
            name="slug",
            field=models.SlugField(
                blank=True,
                default="",
                max_length=100,
            ),
        ),
        # Étape 2 : remplir les slugs depuis le nom
        migrations.RunPython(generer_slugs, migrations.RunPython.noop),
        # Étape 3 : ajouter la contrainte unique maintenant que tout est rempli
        migrations.AlterField(
            model_name="boutique",
            name="slug",
            field=models.SlugField(
                blank=True,
                max_length=100,
                unique=True,
            ),
        ),
    ]
