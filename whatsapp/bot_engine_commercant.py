"""
Moteur de traitement des messages WhatsApp pour les commerçants Fëgg Jaay.

Permet aux commerçants de gérer leur boutique via WhatsApp :
- Ajouter/modifier/supprimer des produits
- Gérer le stock
- Confirmer/annuler des commandes
- Voir les statistiques
"""

import logging
import re
from typing import Optional, Tuple

from boutiques.models import Boutique, Produit, Commande, Client

logger = logging.getLogger(__name__)


# ─── État de conversation du commerçant ─────────────────────────────────────────

class EtatCommercant:
    """Gère l'état de conversation d'un commerçant."""

    ETATS = {
        "MENU": "menu",
        "AJOUTER_NOM": "ajouter_nom",
        "AJOUTER_PRIX": "ajouter_prix",
        "AJOUTER_STOCK": "ajouter_stock",
        "AJOUTER_PHOTO": "ajouter_photo",
        "AJOUTER_DESCRIPTION": "ajouter_description",
        "MODIFIER_PRODUIT": "modifier_produit",
        "MODIFIER_CHAMP": "modifier_champ",
        "SUPPRIMER_PRODUIT": "supprimer_produit",
        "CONFIRMER_COMMANDE": "confirmer_commande",
        "ANNULER_COMMANDE": "annuler_commande",
    }

    def __init__(self, boutique: Boutique):
        self.boutique = boutique
        self.etat = self.ETATS["MENU"]
        self.donnees_temp = {}

    def set_etat(self, etat: str, donnees: dict = None):
        """Change l'état de la conversation."""
        self.etat = etat
        if donnees:
            self.donnees_temp.update(donnees)

    def reset(self):
        """Réinitialise la conversation."""
        self.etat = self.ETATS["MENU"]
        self.donnees_temp = {}


# ─── Stockage des états (en production, utiliser Redis) ───────────────────────

_etats_conversations = {}


def get_etat(boutique: Boutique) -> EtatCommercant:
    """Récupère ou crée l'état de conversation d'une boutique."""
    # Priorité : variable globale (pour tests) → champ conversation_etat
    if boutique.pk in _etats_conversations:
        return _etats_conversations[boutique.pk]

    # Créer depuis le champ conversation_etat
    etat = EtatCommercant(boutique)
    if boutique.conversation_etat:
        etat.etat = boutique.conversation_etat.get("etat", EtatCommercant.ETATS["MENU"])
        etat.donnees_temp = boutique.conversation_etat.get("donnees_temp", {})

    _etats_conversations[boutique.pk] = etat
    return etat


def save_etat(boutique: Boutique):
    """Sauvegarde l'état de conversation dans la boutique."""
    if boutique.pk in _etats_conversations:
        etat = _etats_conversations[boutique.pk]
        boutique.conversation_etat = {
            "etat": etat.etat,
            "donnees_temp": etat.donnees_temp,
        }
        boutique.save(update_fields=["conversation_etat"])


def clear_etat(boutique: Boutique):
    """Efface l'état de conversation d'une boutique."""
    if boutique.pk in _etats_conversations:
        del _etats_conversations[boutique.pk]
    boutique.conversation_etat = {}
    boutique.save(update_fields=["conversation_etat"])


# ─── Commandes disponibles ─────────────────────────────────────────────────────

COMMANDES = {
    "/menu": "Menu principal",
    "/ajouter": "Ajouter un produit",
    "/modifier": "Modifier un produit",
    "/supprimer": "Supprimer un produit",
    "/stock": "Voir le stock",
    "/commandes": "Voir les commandes",
    "/confirmer": "Confirmer une commande",
    "/annuler": "Annuler une commande",
    "/stats": "Voir les statistiques",
    "/help": "Aide",
    "/cancel": "Annuler l'action en cours",
}


# ─── Fonctions de traitement ───────────────────────────────────────────────────

def traiter_message_commercant(
    boutique: Boutique,
    message: str,
    type_message: str = "texte",
    media_url: str = None,
) -> Tuple[str, bool]:
    """
    Traite un message d'un commerçant.

    Returns:
        (réponse, action_requise) où action_requise indique si une réponse est attendue
    """
    etat = get_etat(boutique)
    message = message.strip().lower()

    logger.info("Message commerçant %s: %s (état: %s)", boutique.nom, message, etat.etat)

    # Commandes globales (disponibles dans tous les états)
    if message == "/cancel":
        etat.reset()
        save_etat(boutique)
        return "❌ Action annulée. Retour au menu principal.\n\n" + get_menu_principal(), False

    if message == "/menu":
        etat.reset()
        save_etat(boutique)
        return get_menu_principal(), False

    if message == "/help":
        return get_aide(), False

    # Traitement selon l'état
    if etat.etat == EtatCommercant.ETATS["MENU"]:
        return traiter_menu(etat, message)

    elif etat.etat == EtatCommercant.ETATS["AJOUTER_NOM"]:
        return traiter_ajouter_nom(etat, message)

    elif etat.etat == EtatCommercant.ETATS["AJOUTER_PRIX"]:
        return traiter_ajouter_prix(etat, message)

    elif etat.etat == EtatCommercant.ETATS["AJOUTER_STOCK"]:
        return traiter_ajouter_stock(etat, message)

    elif etat.etat == EtatCommercant.ETATS["AJOUTER_PHOTO"]:
        return traiter_ajouter_photo(etat, type_message, media_url)

    elif etat.etat == EtatCommercant.ETATS["AJOUTER_DESCRIPTION"]:
        return traiter_ajouter_description(etat, message)

    elif etat.etat == EtatCommercant.ETATS["MODIFIER_PRODUIT"]:
        return traiter_modifier_produit(etat, message)

    elif etat.etat == EtatCommercant.ETATS["MODIFIER_CHAMP"]:
        return traiter_modifier_champ(etat, message)

    elif etat.etat == "modifier_prix":
        return traiter_modifier_prix(etat, message)

    elif etat.etat == "modifier_stock":
        return traiter_modifier_stock(etat, message)

    elif etat.etat == "modifier_description":
        return traiter_modifier_description(etat, message)

    elif etat.etat == EtatCommercant.ETATS["SUPPRIMER_PRODUIT"]:
        return traiter_supprimer_produit(etat, message)

    elif etat.etat == EtatCommercant.ETATS["CONFIRMER_COMMANDE"]:
        return traiter_confirmer_commande(etat, message)

    elif etat.etat == EtatCommercant.ETATS["ANNULER_COMMANDE"]:
        return traiter_annuler_commande(etat, message)

    else:
        etat.reset()
        return "❌ Je ne comprends pas. Tapez /menu pour voir les options.", False


# ─── Traitement du menu principal ───────────────────────────────────────────────

def traiter_menu(etat: EtatCommercant, message: str) -> Tuple[str, bool]:
    """Traite les commandes du menu principal."""
    if message == "/ajouter":
        etat.set_etat(EtatCommercant.ETATS["AJOUTER_NOM"])
        save_etat(etat.boutique)
        return (
            "📝 *Ajouter un produit*\n\n"
            "Quel est le nom du produit ?\n\n"
            "Exemple : T-shirt blanc"
        ), True

    elif message == "/modifier":
        produits = list(etat.boutique.produits.filter(actif=True).order_by("nom"))
        if not produits:
            return "❌ Aucun produit à modifier. Tapez /ajouter pour créer un produit.", False

        etat.set_etat(EtatCommercant.ETATS["MODIFIER_PRODUIT"])
        save_etat(etat.boutique)
        return (
            "📝 *Modifier un produit*\n\n"
            "Voici vos produits :\n\n" +
            "\n".join(f"{i+1}. {p.nom} ({p.prix:,} FCFA)" for i, p in enumerate(produits)) +
            "\n\nEntrez le numéro du produit à modifier ou tapez /cancel"
        ), True

    elif message == "/supprimer":
        produits = list(etat.boutique.produits.filter(actif=True).order_by("nom"))
        if not produits:
            return "❌ Aucun produit à supprimer.", False

        etat.set_etat(EtatCommercant.ETATS["SUPPRIMER_PRODUIT"])
        save_etat(etat.boutique)
        return (
            "🗑️ *Supprimer un produit*\n\n"
            "Voici vos produits :\n\n" +
            "\n".join(f"{i+1}. {p.nom}" for i, p in enumerate(produits)) +
            "\n\nEntrez le numéro du produit à supprimer ou tapez /cancel"
        ), True

    elif message == "/stock":
        return get_liste_stock(etat.boutique), False

    elif message == "/commandes":
        return get_liste_commandes(etat.boutique), False

    elif message == "/confirmer":
        commandes = list(etat.boutique.commandes.filter(statut="attente_paiement").order_by("-created_at"))
        if not commandes:
            return "✅ Aucune commande en attente de confirmation.", False

        etat.set_etat(EtatCommercant.ETATS["CONFIRMER_COMMANDE"])
        save_etat(etat.boutique)
        return (
            "✅ *Confirmer une commande*\n\n"
            "Commandes en attente :\n\n" +
            "\n".join(f"{i+1}. {c.numero_ref} - {c.client.prenom or c.client.telephone} ({c.montant_formate})" for i, c in enumerate(commandes)) +
            "\n\nEntrez le numéro de la commande à confirmer ou tapez /cancel"
        ), True

    elif message == "/annuler":
        commandes = list(etat.boutique.commandes.exclude(statut="annulee").exclude(statut="livree").order_by("-created_at"))
        if not commandes:
            return "❌ Aucune commande à annuler.", False

        etat.set_etat(EtatCommercant.ETATS["ANNULER_COMMANDE"])
        save_etat(etat.boutique)
        return (
            "❌ *Annuler une commande*\n\n"
            "Commandes en cours :\n\n" +
            "\n".join(f"{i+1}. {c.numero_ref} - {c.client.prenom or c.client.telephone} ({c.get_statut_display()})" for i, c in enumerate(commandes)) +
            "\n\nEntrez le numéro de la commande à annuler ou tapez /cancel"
        ), True

    elif message == "/stats":
        return get_statistiques(etat.boutique), False

    else:
        return (
            "❌ Commande inconnue.\n\n"
            "Tapez /menu pour voir les options disponibles."
        ), False


# ─── Ajout de produit ─────────────────────────────────────────────────────────

def traiter_ajouter_nom(etat: EtatCommercant, message: str) -> Tuple[str, bool]:
    """Traite l'entrée du nom du produit."""
    if not message or len(message) < 2:
        return "❌ Le nom doit avoir au moins 2 caractères. Réessayez :", True

    etat.set_etat(EtatCommercant.ETATS["AJOUTER_PRIX"], {"nom": message})
    save_etat(etat.boutique)
    return (
        f"✅ Nom : *{message}*\n\n"
        "Quel est le prix en FCFA ?\n\n"
        "Exemple : 5000"
    ), True


def traiter_ajouter_prix(etat: EtatCommercant, message: str) -> Tuple[str, bool]:
    """Traite l'entrée du prix du produit."""
    try:
        prix = int(message.replace(" ", "").replace("fcfa", "").replace("f", ""))
        if prix <= 0:
            return "❌ Le prix doit être positif. Réessayez :", True
    except ValueError:
        return "❌ Prix invalide. Entrez un nombre (ex: 5000) :", True

    etat.set_etat(EtatCommercant.ETATS["AJOUTER_STOCK"], {"prix": prix})
    save_etat(etat.boutique)
    return (
        f"✅ Prix : *{prix:,} FCFA*\n\n"
        "Quel est le stock initial ?\n\n"
        "Exemple : 10"
    ), True


def traiter_ajouter_stock(etat: EtatCommercant, message: str) -> Tuple[str, bool]:
    """Traite l'entrée du stock du produit."""
    try:
        stock = int(message.replace(" ", ""))
        if stock < 0:
            return "❌ Le stock ne peut pas être négatif. Réessayez :", True
    except ValueError:
        return "❌ Stock invalide. Entrez un nombre (ex: 10) :", True

    etat.set_etat(EtatCommercant.ETATS["AJOUTER_PHOTO"], {"stock": stock})
    save_etat(etat.boutique)
    return (
        f"✅ Stock : *{stock}*\n\n"
        "Envoyez une photo du produit (optionnel).\n\n"
        "Tapez /skip pour passer cette étape."
    ), True


def traiter_ajouter_photo(etat: EtatCommercant, type_message: str, media_url: str) -> Tuple[str, bool]:
    """Traite l'ajout de photo du produit."""
    if type_message == "image" and media_url:
        etat.set_etat(EtatCommercant.ETATS["AJOUTER_DESCRIPTION"], {"photo": media_url})
        save_etat(etat.boutique)
        return (
            "✅ Photo reçue !\n\n"
            "Ajoutez une description (optionnel).\n\n"
            "Tapez /skip pour passer cette étape."
        ), True
    elif type_message == "texte" and message == "/skip":
        etat.set_etat(EtatCommercant.ETATS["AJOUTER_DESCRIPTION"])
        save_etat(etat.boutique)
        return (
            "Photo ignorée.\n\n"
            "Ajoutez une description (optionnel).\n\n"
            "Tapez /skip pour passer cette étape."
        ), True
    else:
        return (
            "❌ Envoyez une photo ou tapez /skip pour continuer."
        ), True


def traiter_ajouter_description(etat: EtatCommercant, message: str) -> Tuple[str, bool]:
    """Traite l'ajout de description et crée le produit."""
    if message == "/skip":
        description = ""
    else:
        description = message

    # Créer le produit
    donnees = etat.donnees_temp
    produit = Produit.objects.create(
        boutique=etat.boutique,
        nom=donnees["nom"],
        prix=donnees["prix"],
        stock=donnees["stock"],
        description=description,
        photo=donnees.get("photo"),
        actif=True,
    )

    etat.reset()
    save_etat(etat.boutique)

    return (
        f"🎉 *Produit ajouté avec succès !*\n\n"
        f"📦 Nom : {produit.nom}\n"
        f"💰 Prix : {produit.prix_formate}\n"
        f"📊 Stock : {produit.stock}\n"
        f"📝 Description : {produit.description or 'Aucune'}\n\n"
        f"Tapez /menu pour continuer."
    ), False


# ─── Modification de produit ───────────────────────────────────────────────────

def traiter_modifier_produit(etat: EtatCommercant, message: str) -> Tuple[str, bool]:
    """Traite la sélection du produit à modifier."""
    try:
        index = int(message) - 1
        produits = list(etat.boutique.produits.filter(actif=True).order_by("nom"))
        if index < 0 or index >= len(produits):
            return "❌ Numéro invalide. Réessayez :", True

        produit = produits[index]
        etat.set_etat(EtatCommercant.ETATS["MODIFIER_CHAMP"], {"produit_id": produit.pk})
        save_etat(etat.boutique)

        return (
            f"📝 *Modifier : {produit.nom}*\n\n"
            f"Prix actuel : {produit.prix_formate}\n"
            f"Stock actuel : {produit.stock}\n"
            f"Description : {produit.description or 'Aucune'}\n\n"
            "Que voulez-vous modifier ?\n"
            "1. Prix\n"
            "2. Stock\n"
            "3. Description\n\n"
            "Entrez le numéro ou tapez /cancel"
        ), True
    except ValueError:
        return "❌ Entrez un numéro valide ou tapez /cancel :", True


def traiter_modifier_champ(etat: EtatCommercant, message: str) -> Tuple[str, bool]:
    """Traite la modification d'un champ du produit."""
    try:
        champ_index = int(message)
        if champ_index not in [1, 2, 3]:
            return "❌ Choix invalide. Entrez 1, 2 ou 3 :", True

        produit_id = etat.donnees_temp["produit_id"]
        produit = Produit.objects.get(pk=produit_id, boutique=etat.boutique)

        if champ_index == 1:  # Prix
            etat.set_etat("modifier_prix", {"produit_id": produit_id})
            save_etat(etat.boutique)
            return f"Prix actuel : {produit.prix_formate}\n\nEntrez le nouveau prix :", True

        elif champ_index == 2:  # Stock
            etat.set_etat("modifier_stock", {"produit_id": produit_id})
            save_etat(etat.boutique)
            return f"Stock actuel : {produit.stock}\n\nEntrez le nouveau stock :", True

        elif champ_index == 3:  # Description
            etat.set_etat("modifier_description", {"produit_id": produit_id})
            save_etat(etat.boutique)
            return f"Description actuelle : {produit.description or 'Aucune'}\n\nEntrez la nouvelle description :", True

    except ValueError:
        return "❌ Entrez un numéro valide :", True


def traiter_modifier_prix(etat: EtatCommercant, message: str) -> Tuple[str, bool]:
    """Traite la modification du prix d'un produit."""
    try:
        prix = int(message.replace(" ", "").replace("fcfa", "").replace("f", ""))
        if prix <= 0:
            return "❌ Le prix doit être positif. Réessayez :", True
    except ValueError:
        return "❌ Prix invalide. Entrez un nombre (ex: 5000) :", True

    produit_id = etat.donnees_temp["produit_id"]
    produit = Produit.objects.get(pk=produit_id, boutique=etat.boutique)
    produit.prix = prix
    produit.save(update_fields=["prix", "updated_at"])

    etat.reset()
    save_etat(etat.boutique)

    return (
        f"✅ *Prix mis à jour !*\n\n"
        f"Produit : {produit.nom}\n"
        f"Nouveau prix : {produit.prix_formate}\n\n"
        "Tapez /menu pour continuer."
    ), False


def traiter_modifier_stock(etat: EtatCommercant, message: str) -> Tuple[str, bool]:
    """Traite la modification du stock d'un produit."""
    try:
        stock = int(message.replace(" ", ""))
        if stock < 0:
            return "❌ Le stock ne peut pas être négatif. Réessayez :", True
    except ValueError:
        return "❌ Stock invalide. Entrez un nombre (ex: 10) :", True

    produit_id = etat.donnees_temp["produit_id"]
    produit = Produit.objects.get(pk=produit_id, boutique=etat.boutique)
    produit.stock = stock
    produit.save(update_fields=["stock", "updated_at"])

    etat.reset()
    save_etat(etat.boutique)

    return (
        f"✅ *Stock mis à jour !*\n\n"
        f"Produit : {produit.nom}\n"
        f"Nouveau stock : {produit.stock} unités\n\n"
        "Tapez /menu pour continuer."
    ), False


def traiter_modifier_description(etat: EtatCommercant, message: str) -> Tuple[str, bool]:
    """Traite la modification de la description d'un produit."""
    produit_id = etat.donnees_temp["produit_id"]
    produit = Produit.objects.get(pk=produit_id, boutique=etat.boutique)
    produit.description = message
    produit.save(update_fields=["description", "updated_at"])

    etat.reset()
    save_etat(etat.boutique)

    return (
        f"✅ *Description mise à jour !*\n\n"
        f"Produit : {produit.nom}\n"
        f"Nouvelle description : {produit.description or 'Aucune'}\n\n"
        "Tapez /menu pour continuer."
    ), False


# ─── Suppression de produit ─────────────────────────────────────────────────────

def traiter_supprimer_produit(etat: EtatCommercant, message: str) -> Tuple[str, bool]:
    """Traite la suppression d'un produit."""
    try:
        index = int(message) - 1
        produits = list(etat.boutique.produits.filter(actif=True).order_by("nom"))
        if index < 0 or index >= len(produits):
            return "❌ Numéro invalide. Réessayez :", True

        produit = produits[index]
        nom = produit.nom
        produit.actif = False
        produit.save(update_fields=["actif"])

        etat.reset()
        save_etat(etat.boutique)

        return (
            f"🗑️ *Produit supprimé : {nom}*\n\n"
            "Tapez /menu pour continuer."
        ), False
    except ValueError:
        return "❌ Entrez un numéro valide ou tapez /cancel :", True


# ─── Confirmation de commande ───────────────────────────────────────────────────

def traiter_confirmer_commande(etat: EtatCommercant, message: str) -> Tuple[str, bool]:
    """Traite la confirmation d'une commande."""
    try:
        index = int(message) - 1
        commandes = list(etat.boutique.commandes.filter(statut="attente_paiement").order_by("-created_at"))
        if index < 0 or index >= len(commandes):
            return "❌ Numéro invalide. Réessayez :", True

        commande = commandes[index]
        commande.statut = "payee"
        commande.save(update_fields=["statut", "updated_at"])

        etat.reset()
        save_etat(etat.boutique)

        return (
            f"✅ *Commande confirmée : {commande.numero_ref}*\n\n"
            f"Client : {commande.client.prenom or commande.client.telephone}\n"
            f"Montant : {commande.montant_formate}\n\n"
            "Tapez /menu pour continuer."
        ), False
    except ValueError:
        return "❌ Entrez un numéro valide ou tapez /cancel :", True


# ─── Annulation de commande ───────────────────────────────────────────────────

def traiter_annuler_commande(etat: EtatCommercant, message: str) -> Tuple[str, bool]:
    """Traite l'annulation d'une commande."""
    try:
        index = int(message) - 1
        commandes = list(etat.boutique.commandes.exclude(statut="annulee").exclude(statut="livree").order_by("-created_at"))
        if index < 0 or index >= len(commandes):
            return "❌ Numéro invalide. Réessayez :", True

        commande = commandes[index]
        commande.statut = "annulee"
        commande.save(update_fields=["statut", "updated_at"])

        etat.reset()
        save_etat(etat.boutique)

        return (
            f"❌ *Commande annulée : {commande.numero_ref}*\n\n"
            f"Client : {commande.client.prenom or commande.client.telephone}\n"
            f"Montant : {commande.montant_formate}\n\n"
            "Tapez /menu pour continuer."
        ), False
    except ValueError:
        return "❌ Entrez un numéro valide ou tapez /cancel :", True


# ─── Fonctions d'affichage ─────────────────────────────────────────────────────

def get_menu_principal() -> str:
    """Retourne le menu principal."""
    return (
        "📱 *MENU PRINCIPAL*\n\n"
        "📦 *Produits*\n"
        "  /ajouter - Ajouter un produit\n"
        "  /modifier - Modifier un produit\n"
        "  /supprimer - Supprimer un produit\n"
        "  /stock - Voir le stock\n\n"
        "🛒 *Commandes*\n"
        "  /commandes - Voir les commandes\n"
        "  /confirmer - Confirmer une commande\n"
        "  /annuler - Annuler une commande\n\n"
        "📊 *Autres*\n"
        "  /stats - Voir les statistiques\n"
        "  /help - Aide\n"
        "  /cancel - Annuler l'action en cours"
    )


def get_aide() -> str:
    """Retourne l'aide."""
    return (
        "❓ *AIDE*\n\n"
        "Pour gérer votre boutique via WhatsApp :\n\n"
        "1. Tapez /menu pour voir les options\n"
        "2. Suivez les instructions pour chaque action\n"
        "3. Tapez /cancel pour annuler une action en cours\n\n"
        "Exemples :\n"
        "- /ajouter → Créer un nouveau produit\n"
        "- /stock → Voir tout votre stock\n"
        "- /commandes → Voir les commandes en attente\n\n"
        "Besoin d'aide ? Contactez-nous au +221778953918"
    )


def get_liste_stock(boutique: Boutique) -> str:
    """Retourne la liste du stock."""
    produits = boutique.produits.filter(actif=True).order_by("nom")
    if not produits:
        return "❌ Aucun produit en stock."

    lignes = ["📦 *STOCK ACTUEL*\n"]
    for p in produits:
        statut = "✅" if p.stock > p.stock_alerte else "⚠️"
        lignes.append(f"{statut} {p.nom} : {p.stock} unités ({p.prix_formate})")

    lignes.append(f"\nTotal : {len(produits)} produits")
    lignes.append("\nTapez /menu pour continuer.")

    return "\n".join(lignes)


def get_liste_commandes(boutique: Boutique) -> str:
    """Retourne la liste des commandes."""
    commandes = boutique.commandes.order_by("-created_at")[:10]
    if not commandes:
        return "❌ Aucune commande."

    lignes = ["🛒 *COMMANDES RÉCENTES*\n"]
    for c in commandes:
        emoji = {
            "attente_paiement": "⏳",
            "payee": "✅",
            "en_preparation": "📦",
            "livree": "🎉",
            "annulee": "❌",
        }.get(c.statut, "📋")

        lignes.append(
            f"{emoji} {c.numero_ref} - {c.client.prenom or c.client.telephone}\n"
            f"   {c.montant_formate} - {c.get_statut_display()}"
        )

    lignes.append("\nTapez /menu pour continuer.")

    return "\n".join(lignes)


def get_statistiques(boutique: Boutique) -> str:
    """Retourne les statistiques de la boutique."""
    from django.db.models import Sum, Count, F
    from django.utils import timezone
    from datetime import timedelta

    aujourd_hui = timezone.now().date()
    debut_jour = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    commandes_jour = boutique.commandes.filter(created_at__gte=debut_jour)
    commandes_payees = commandes_jour.filter(statut__in=["payee", "en_preparation", "livree"])

    ca_jour = commandes_payees.aggregate(total=Sum("montant_total"))["total"] or 0
    nb_commandes_jour = commandes_jour.count()
    nb_clients = boutique.clients.count()
    nb_produits = boutique.produits.filter(actif=True).count()
    stock_bas = boutique.produits.filter(actif=True).filter(stock__lte=F("stock_alerte")).count()

    lignes = [
        "📊 *STATISTIQUES*\n\n",
        f"📅 *Aujourd'hui*\n",
        f"  Commandes : {nb_commandes_jour}",
        f"  CA : {ca_jour:,} FCFA".replace(",", " "),
        f"\n📦 *Produits*\n",
        f"  Total : {nb_produits}",
        f"  Stock bas : {stock_bas}",
        f"\n👥 *Clients*\n",
        f"  Total : {nb_clients}",
        f"\nTapez /menu pour continuer.",
    ]

    return "\n".join(lignes)
