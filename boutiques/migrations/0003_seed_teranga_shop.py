"""Migration de données : crée la boutique TERANGA SHOP et ses produits."""

from django.db import migrations


def seed_data(apps, schema_editor):
    Boutique = apps.get_model("boutiques", "Boutique")
    Produit = apps.get_model("boutiques", "Produit")

    boutique, _ = Boutique.objects.get_or_create(
        telephone_wa="+14155238886",
        defaults={
            "nom": "TERANGA SHOP",
            "twilio_account_sid": "AC9cb5d91b3f6af1b96c930a41244c7b1d",
            "twilio_auth_token": "79bb9b67ae564a03f651726f48a01abd",
            "actif": True,
        },
    )

    produits = [
        {"nom": "Boubou Grand Bazin", "prix": 25000, "stock": 10},
        {"nom": "Kaftan Brodé", "prix": 18000, "stock": 15},
        {"nom": "Chemise Wax Homme", "prix": 8500, "stock": 20},
        {"nom": "Pantalon Thiaw", "prix": 12000, "stock": 12},
        {"nom": "Ensemble 3 Pièces Cérémonie", "prix": 45000, "stock": 5},
    ]

    for p in produits:
        Produit.objects.get_or_create(
            boutique=boutique,
            nom=p["nom"],
            defaults={"prix": p["prix"], "stock": p["stock"], "actif": True},
        )


def unseed_data(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("boutiques", "0002_remove_client_unique_client_par_boutique_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_data, unseed_data),
    ]
