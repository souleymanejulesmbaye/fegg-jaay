"""
Modèles de données pour Fëgg Jaay.

Multi-tenant : chaque Boutique est un tenant isolé avec ses propres
clés WhatsApp API, produits, clients et commandes.
"""

import uuid
from django.db import models
from django.utils import timezone


# ─── Boutique (tenant principal) ─────────────────────────────────────────────

class Boutique(models.Model):
    """Représente un commerçant sénégalais et sa boutique WhatsApp."""

    PLAN_CHOICES = [
        ("starter", "Starter"),
        ("business", "Business"),
        ("premium", "Premium"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=200, verbose_name="Nom de la boutique")

    # WhatsApp Business API (360dialog) — propre à chaque boutique
    telephone_wa = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Numéro WhatsApp (avec indicatif, ex: 221771234567)",
    )
    wa_phone_id = models.CharField(
        max_length=100,
        verbose_name="WhatsApp Phone ID (360dialog)",
    )
    wa_token = models.CharField(
        max_length=500,
        verbose_name="Token API WhatsApp (360dialog)",
    )

    # URL publique
    slug = models.SlugField(
        max_length=100,
        unique=True,
        blank=True,
        help_text="Identifiant URL de la boutique (ex: teranga-shop)",
    )

    # Contact commerçant
    proprietaire_tel = models.CharField(
        max_length=20,
        verbose_name="Téléphone du propriétaire",
    )
    ville = models.CharField(max_length=100, default="Dakar")

    # Abonnement
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default="starter")
    actif = models.BooleanField(default=True)
    abonnement_fin = models.DateField(null=True, blank=True)

    # Message d'accueil affiché au premier contact
    message_bienvenue = models.TextField(
        default=(
            "Bonjour ! Bienvenue dans notre boutique. "
            "Tapez *catalogue* pour voir nos produits disponibles."
        )
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Boutique"
        verbose_name_plural = "Boutiques"
        ordering = ["nom"]

    def __str__(self):
        return f"{self.nom} ({self.telephone_wa})"

    def get_catalogue_text(self) -> str:
        """
        Retourne le catalogue formaté pour l'injection dans le system prompt Claude.
        Seuls les produits actifs avec stock > 0 sont listés.
        """
        produits = self.produits.filter(actif=True, stock__gt=0).order_by("nom")
        if not produits.exists():
            return "Aucun produit disponible en ce moment."

        lignes = ["=== CATALOGUE ==="]
        for p in produits:
            ligne = f"- {p.nom} : {p.prix:,} FCFA (stock: {p.stock})"
            if p.description:
                ligne += f"\n  {p.description}"
            lignes.append(ligne)
        return "\n".join(lignes)

    def get_stock_text(self) -> str:
        """Résumé stock pour le prompt Claude — alerte sur les niveaux bas."""
        produits = self.produits.filter(actif=True).order_by("nom")
        if not produits.exists():
            return "Aucun produit configuré."

        lignes = ["=== STOCK ==="]
        for p in produits:
            statut = "✓" if p.stock > p.stock_alerte else "⚠ BAS"
            lignes.append(f"- {p.nom}: {p.stock} unités [{statut}]")
        return "\n".join(lignes)


# ─── Produit ──────────────────────────────────────────────────────────────────

class Produit(models.Model):
    """Produit vendu par une boutique."""

    boutique = models.ForeignKey(
        Boutique, on_delete=models.CASCADE, related_name="produits"
    )
    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    prix = models.PositiveIntegerField(help_text="Prix en FCFA (entier, sans décimale)")
    stock = models.PositiveIntegerField(default=0)
    stock_alerte = models.PositiveIntegerField(
        default=5,
        help_text="Seuil en dessous duquel une alerte est envoyée au commerçant",
    )
    photo = models.ImageField(
        upload_to="produits/",
        blank=True,
        null=True,
        help_text="Photo stockée sur Cloudinary",
    )
    actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Produit"
        verbose_name_plural = "Produits"
        ordering = ["nom"]
        unique_together = [("boutique", "nom")]

    def __str__(self):
        return f"{self.nom} — {self.prix:,} FCFA (boutique: {self.boutique.nom})"

    @property
    def prix_formate(self) -> str:
        """Prix formaté avec séparateur espace : ex. 12 500 FCFA"""
        return f"{self.prix:,} FCFA".replace(",", " ")


# ─── Client ───────────────────────────────────────────────────────────────────

class Client(models.Model):
    """Client d'une boutique identifié par son numéro WhatsApp."""

    LANGUE_CHOICES = [
        ("fr", "Français"),
        ("wo", "Wolof"),
    ]

    boutique = models.ForeignKey(
        Boutique, on_delete=models.CASCADE, related_name="clients"
    )
    telephone = models.CharField(
        max_length=20,
        help_text="Numéro WhatsApp avec indicatif pays",
    )
    prenom = models.CharField(max_length=100, blank=True)
    langue_preferee = models.CharField(
        max_length=2, choices=LANGUE_CHOICES, default="fr"
    )
    total_commandes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"
        unique_together = [("boutique", "telephone")]
        ordering = ["-created_at"]

    def __str__(self):
        nom = self.prenom or "Inconnu"
        return f"{nom} ({self.telephone}) — {self.boutique.nom}"


# ─── Commande ─────────────────────────────────────────────────────────────────

class Commande(models.Model):
    """Commande passée par un client via WhatsApp."""

    STATUT_CHOICES = [
        ("attente_paiement", "En attente de paiement"),
        ("payee", "Payée"),
        ("en_preparation", "En préparation"),
        ("livree", "Livrée"),
        ("annulee", "Annulée"),
    ]

    MODE_PAIEMENT_CHOICES = [
        ("wave", "Wave"),
        ("orange_money", "Orange Money"),
        ("free_money", "Free Money"),
        ("especes", "Espèces"),
    ]

    boutique = models.ForeignKey(
        Boutique, on_delete=models.CASCADE, related_name="commandes"
    )
    client = models.ForeignKey(
        Client, on_delete=models.PROTECT, related_name="commandes"
    )
    numero_ref = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Référence auto-générée, ex: CMD-0042",
    )
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default="attente_paiement"
    )
    montant_total = models.PositiveIntegerField(
        default=0, help_text="Montant total en FCFA"
    )
    mode_paiement = models.CharField(
        max_length=20,
        choices=MODE_PAIEMENT_CHOICES,
        blank=True,
    )
    reference_paiement = models.CharField(
        max_length=100,
        blank=True,
        help_text="Numéro de transaction Wave/Orange Money fourni par le client",
    )
    adresse_livraison = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Commande"
        verbose_name_plural = "Commandes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.numero_ref} — {self.client} — {self.get_statut_display()}"

    def save(self, *args, **kwargs):
        # Génère le numéro de référence à la première sauvegarde
        if not self.numero_ref:
            super().save(*args, **kwargs)  # sauvegarde pour obtenir le pk
            self.numero_ref = f"CMD-{self.pk:04d}"
            Commande.objects.filter(pk=self.pk).update(numero_ref=self.numero_ref)
        else:
            super().save(*args, **kwargs)

    def recalculer_total(self):
        """Recalcule et sauvegarde le montant total depuis les lignes."""
        total = sum(
            l.quantite * l.prix_unitaire for l in self.lignes.all()
        )
        self.montant_total = total
        self.save(update_fields=["montant_total"])

    @property
    def montant_formate(self) -> str:
        return f"{self.montant_total:,} FCFA".replace(",", " ")


# ─── LigneCommande ────────────────────────────────────────────────────────────

class LigneCommande(models.Model):
    """Ligne d'une commande : un produit + quantité + prix figé au moment de l'achat."""

    commande = models.ForeignKey(
        Commande, on_delete=models.CASCADE, related_name="lignes"
    )
    produit = models.ForeignKey(
        Produit, on_delete=models.PROTECT, related_name="lignes_commande"
    )
    quantite = models.PositiveIntegerField(default=1)
    prix_unitaire = models.PositiveIntegerField(
        help_text="Prix figé au moment de la commande, en FCFA"
    )

    class Meta:
        verbose_name = "Ligne de commande"
        verbose_name_plural = "Lignes de commande"

    def __str__(self):
        return f"{self.commande.numero_ref} — {self.produit.nom} x{self.quantite}"

    @property
    def sous_total(self) -> int:
        return self.quantite * self.prix_unitaire

    @property
    def sous_total_formate(self) -> str:
        return f"{self.sous_total:,} FCFA".replace(",", " ")


# ─── MessageLog ───────────────────────────────────────────────────────────────

class MessageLog(models.Model):
    """Journal de tous les messages WhatsApp entrants et sortants."""

    DIRECTION_CHOICES = [
        ("entrant", "Entrant (client → bot)"),
        ("sortant", "Sortant (bot → client)"),
    ]

    TYPE_CHOICES = [
        ("texte", "Texte"),
        ("image", "Image"),
        ("audio", "Audio / Vocal"),
        ("document", "Document"),
        ("autre", "Autre"),
    ]

    boutique = models.ForeignKey(
        Boutique, on_delete=models.CASCADE, related_name="message_logs"
    )
    telephone_client = models.CharField(max_length=20)
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    contenu = models.TextField()
    type_message = models.CharField(max_length=10, choices=TYPE_CHOICES, default="texte")
    wa_message_id = models.CharField(
        max_length=200,
        blank=True,
        help_text="ID message WhatsApp (pour éviter les doublons)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Message log"
        verbose_name_plural = "Messages logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["boutique", "telephone_client", "-created_at"]),
        ]

    def __str__(self):
        return (
            f"[{self.get_direction_display()}] "
            f"{self.telephone_client} → {self.boutique.nom} "
            f"({self.created_at:%d/%m/%Y %H:%M})"
        )
