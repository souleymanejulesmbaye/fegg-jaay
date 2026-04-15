"""Migration initiale — app boutiques."""

import uuid
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        # ── Boutique ──────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="Boutique",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("nom", models.CharField(max_length=200, verbose_name="Nom de la boutique")),
                ("telephone_wa", models.CharField(max_length=20, unique=True, verbose_name="Numéro WhatsApp (avec indicatif, ex: 221771234567)")),
                ("wa_phone_id", models.CharField(max_length=100, verbose_name="WhatsApp Phone ID (360dialog)")),
                ("wa_token", models.CharField(max_length=500, verbose_name="Token API WhatsApp (360dialog)")),
                ("proprietaire_tel", models.CharField(max_length=20, verbose_name="Téléphone du propriétaire")),
                ("ville", models.CharField(default="Dakar", max_length=100)),
                ("plan", models.CharField(choices=[("starter", "Starter"), ("business", "Business"), ("premium", "Premium")], default="starter", max_length=20)),
                ("actif", models.BooleanField(default=True)),
                ("abonnement_fin", models.DateField(blank=True, null=True)),
                ("message_bienvenue", models.TextField(default="Bonjour ! Bienvenue dans notre boutique. Tapez *catalogue* pour voir nos produits disponibles.")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Boutique", "verbose_name_plural": "Boutiques", "ordering": ["nom"]},
        ),
        # ── Produit ───────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="Produit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("boutique", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="produits", to="boutiques.boutique")),
                ("nom", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("prix", models.PositiveIntegerField(help_text="Prix en FCFA (entier, sans décimale)")),
                ("stock", models.PositiveIntegerField(default=0)),
                ("stock_alerte", models.PositiveIntegerField(default=5, help_text="Seuil en dessous duquel une alerte est envoyée au commerçant")),
                ("photo", models.ImageField(blank=True, help_text="Photo stockée sur Cloudinary", null=True, upload_to="produits/")),
                ("actif", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Produit", "verbose_name_plural": "Produits", "ordering": ["nom"]},
        ),
        migrations.AddConstraint(
            model_name="produit",
            constraint=models.UniqueConstraint(fields=["boutique", "nom"], name="unique_produit_par_boutique"),
        ),
        # ── Client ────────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="Client",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("boutique", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="clients", to="boutiques.boutique")),
                ("telephone", models.CharField(help_text="Numéro WhatsApp avec indicatif pays", max_length=20)),
                ("prenom", models.CharField(blank=True, max_length=100)),
                ("langue_preferee", models.CharField(choices=[("fr", "Français"), ("wo", "Wolof")], default="fr", max_length=2)),
                ("total_commandes", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Client", "verbose_name_plural": "Clients", "ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="client",
            constraint=models.UniqueConstraint(fields=["boutique", "telephone"], name="unique_client_par_boutique"),
        ),
        # ── Commande ──────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="Commande",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("boutique", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="commandes", to="boutiques.boutique")),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="commandes", to="boutiques.client")),
                ("numero_ref", models.CharField(editable=False, help_text="Référence auto-générée, ex: CMD-0042", max_length=20, unique=True)),
                ("statut", models.CharField(choices=[("attente_paiement", "En attente de paiement"), ("payee", "Payée"), ("en_preparation", "En préparation"), ("livree", "Livrée"), ("annulee", "Annulée")], default="attente_paiement", max_length=20)),
                ("montant_total", models.PositiveIntegerField(default=0, help_text="Montant total en FCFA")),
                ("mode_paiement", models.CharField(blank=True, choices=[("wave", "Wave"), ("orange_money", "Orange Money"), ("free_money", "Free Money"), ("especes", "Espèces")], max_length=20)),
                ("adresse_livraison", models.TextField(blank=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Commande", "verbose_name_plural": "Commandes", "ordering": ["-created_at"]},
        ),
        # ── LigneCommande ─────────────────────────────────────────────────────
        migrations.CreateModel(
            name="LigneCommande",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("commande", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lignes", to="boutiques.commande")),
                ("produit", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="lignes_commande", to="boutiques.produit")),
                ("quantite", models.PositiveIntegerField(default=1)),
                ("prix_unitaire", models.PositiveIntegerField(help_text="Prix figé au moment de la commande, en FCFA")),
            ],
            options={"verbose_name": "Ligne de commande", "verbose_name_plural": "Lignes de commande"},
        ),
        # ── MessageLog ────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="MessageLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("boutique", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="message_logs", to="boutiques.boutique")),
                ("telephone_client", models.CharField(max_length=20)),
                ("direction", models.CharField(choices=[("entrant", "Entrant (client → bot)"), ("sortant", "Sortant (bot → client)")], max_length=10)),
                ("contenu", models.TextField()),
                ("type_message", models.CharField(choices=[("texte", "Texte"), ("image", "Image"), ("audio", "Audio / Vocal"), ("document", "Document"), ("autre", "Autre")], default="texte", max_length=10)),
                ("wa_message_id", models.CharField(blank=True, help_text="ID message WhatsApp (pour éviter les doublons)", max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"verbose_name": "Message log", "verbose_name_plural": "Messages logs", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="messagelog",
            index=models.Index(fields=["boutique", "telephone_client", "-created_at"], name="boutiques_m_boutiqu_idx"),
        ),
    ]
