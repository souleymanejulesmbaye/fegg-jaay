"""
Moteur de traitement IA — Fëgg Jaay.

Responsabilités :
  1. Construire le system prompt avec catalogue + stock + infos client
  2. Récupérer l'historique des derniers messages du client
  3. Appeler Claude API (claude-haiku pour messages simples)
  4. Parser la réponse JSON structurée
  5. Exécuter l'action métier (créer commande, annuler, adresse livraison…)
  6. Retourner le texte de réponse à envoyer au client
"""

import json
import logging
import re
from typing import Optional

import anthropic
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from boutiques.models import Boutique, Client, Commande, LigneCommande, MessageLog, Produit

logger = logging.getLogger(__name__)

# Modèles Claude utilisés
MODEL_SIMPLE = "claude-haiku-4-5-20251001"   # messages catalogue, questions simples
MODEL_COMPLEXE = "claude-sonnet-4-6"          # analyse commandes complexes, erreurs


SYSTEM_PROMPT_TEMPLATE = """Tu es l'assistant WhatsApp de la boutique "{nom_boutique}" au Sénégal.
Tu es intelligent, naturel et tu réponds à TOUT ce que le client dit — pas seulement aux commandes.

RÈGLES ABSOLUES :
- Détecte la langue du client : français → réponds en français, wolof → réponds en wolof, mélange → français
- Les prix sont TOUJOURS en FCFA (ex: 12 500 FCFA)
- Sois chaleureux, concis, humain — comme un vendeur sénégalais bienveillant
- Ne propose que des produits disponibles en stock
- Si le client donne son prénom, utilise-le naturellement
- Tu peux répondre à des salutations, blagues, questions générales — reste toujours poli et professionnel
- Si le client pose une question hors catalogue (horaires, localisation, etc.), réponds intelligemment avec ce que tu sais ou dis que le commerçant va répondre

{client_info}
{catalogue}

{stock}

QUAND RÉPONDRE AVEC INTENT "commande" :
- Le client mentionne un produit du catalogue ET veut l'acheter

QUAND RÉPONDRE AVEC INTENT "catalogue" :
- Le client demande à voir les produits. Liste TOUS les produits disponibles avec prix.

QUAND RÉPONDRE AVEC INTENT "paiement" :
- Le client parle de Wave, Orange Money, d'un virement ou dit qu'il a payé

QUAND RÉPONDRE AVEC INTENT "livraison" :
- Le client demande où en est sa commande

QUAND RÉPONDRE AVEC INTENT "annulation" :
- Le client veut annuler une commande

QUAND RÉPONDRE AVEC INTENT "autre" :
- Salutations, remerciements, questions générales, bavardage — réponds naturellement et guide vers le catalogue si pertinent

INSTRUCTIONS DE RÉPONSE :
Tu dois TOUJOURS répondre avec un JSON valide (et uniquement du JSON) :
{{
  "intent": "catalogue|commande|paiement|livraison|annulation|autre",
  "produits": [{{"nom": "nom exact du produit", "quantite": 1}}],
  "langue": "fr|wo",
  "reponse": "message à envoyer au client"
}}

Note : "produits" est une liste vide [] si ce n'est pas une commande.
"""


def traiter_message(
    boutique: Boutique,
    client: Client,
    message: str,
    type_message: str = "texte",
) -> str:
    """
    Point d'entrée principal du moteur IA.

    Retourne le texte de la réponse à envoyer au client via WhatsApp.
    En cas d'erreur, retourne un message d'excuse générique.
    """
    try:
        # Vérifier si on attend une référence de paiement
        commande_paiement = _est_en_attente_reference_paiement(boutique, client)
        if commande_paiement:
            return _sauver_reference_paiement(commande_paiement, message, client)

        # Vérifier si on attend une adresse de livraison
        commande_adresse = _est_en_attente_adresse(boutique, client)
        if commande_adresse:
            return _sauver_adresse_livraison(commande_adresse, message, client)

        # 1. Construire le prompt (avec infos client)
        system_prompt = _construire_system_prompt(boutique, client)
        historique = _get_historique(boutique, client.telephone)

        # 2. Appel Claude
        reponse_claude = _appeler_claude(system_prompt, historique, message)

        # 3. Parser la réponse
        parsed = _parser_reponse(reponse_claude)

        # 4. Exécuter l'action métier si nécessaire
        texte_reponse = _executer_action(boutique, client, parsed, message)

        return texte_reponse

    except anthropic.APIError as exc:
        logger.error("Erreur API Claude : %s", exc)
        return _message_erreur(client.langue_preferee)
    except Exception as exc:
        logger.exception("Erreur inattendue dans le moteur IA : %s", exc)
        return _message_erreur(client.langue_preferee)


# ─── Construction du prompt ────────────────────────────────────────────────────

def _construire_system_prompt(boutique: Boutique, client: Client = None) -> str:
    client_info = ""
    if client and client.prenom:
        client_info = (
            f"CLIENT CONNU : Le client s'appelle {client.prenom}. "
            f"Utilise son prénom dans tes réponses pour personnaliser l'expérience.\n"
        )
    return SYSTEM_PROMPT_TEMPLATE.format(
        nom_boutique=boutique.nom,
        catalogue=boutique.get_catalogue_text(),
        stock=boutique.get_stock_text(),
        client_info=client_info,
    )


def _get_historique(boutique: Boutique, telephone: str, nb_messages: int = 10) -> list[dict]:
    """
    Récupère les N derniers messages du client pour construire le contexte.
    Retourne une liste au format messages Anthropic [{"role": ..., "content": ...}].
    """
    logs = (
        MessageLog.objects.filter(boutique=boutique, telephone_client=telephone)
        .order_by("-created_at")[:nb_messages]
    )
    messages = []
    for log in reversed(logs):  # ordre chronologique
        role = "user" if log.direction == "entrant" else "assistant"
        messages.append({"role": role, "content": log.contenu})
    return messages


# ─── Appel Claude API ─────────────────────────────────────────────────────────

def _appeler_claude(
    system_prompt: str,
    historique: list[dict],
    message_actuel: str,
    modele: str = MODEL_SIMPLE,
) -> str:
    """Appelle Claude et retourne le texte brut de la réponse."""

    # MODE SIMULATION — à retirer quand les crédits Anthropic seront disponibles
    if not settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_API_KEY == "sk-ant-VOTRE_CLE_ICI":
        return _simuler_reponse(message_actuel, system_prompt)

    try:
        client_anthropic = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        messages = historique + [{"role": "user", "content": message_actuel}]
        response = client_anthropic.messages.create(
            model=modele,
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        )
        return response.content[0].text
    except anthropic.APIError:
        logger.warning("Crédits insuffisants — bascule en mode simulation.")
        return _simuler_reponse(message_actuel, system_prompt)


def _simuler_reponse(message: str, system_prompt: str) -> str:
    """
    Simulation locale du bot sans appel API.
    Détecte l'intention, la langue (fr/wo), supporte plusieurs produits.
    """
    msg = message.lower().strip()

    # ── Détection langue ──────────────────────────────────────────────────
    wolof_markers = ["jënd", "jërejëf", "mangi", "naka", "bañ", "yëgël",
                     "waaw", "xam", "dëkk", "dafa", "nanu", "bi dafa"]
    langue = "wo" if any(w in msg for w in wolof_markers) else "fr"

    # ── Nom du client dans le system_prompt ───────────────────────────────
    prenom_client = ""
    m_prenom = re.search(r"CLIENT CONNU : Le client s'appelle (\w+)", system_prompt)
    if m_prenom:
        prenom_client = m_prenom.group(1)

    # ── Extraction des produits depuis le catalogue ───────────────────────
    produits_catalogue = []
    produits_avec_prix = []
    noms_vus = set()
    in_catalogue = False
    for ligne in system_prompt.split("\n"):
        if "=== CATALOGUE ===" in ligne:
            in_catalogue = True
            continue
        if "===" in ligne and "CATALOGUE" not in ligne:
            in_catalogue = False
        if in_catalogue and ligne.strip().startswith("- ") and "FCFA" in ligne:
            parties = ligne.strip()[2:].split(":")
            nom = parties[0].strip()
            prix_match = re.search(r"([\d,]+)\s*FCFA", ligne)
            prix = prix_match.group(0) if prix_match else ""
            if nom and nom not in noms_vus:
                noms_vus.add(nom)
                produits_catalogue.append(nom)
                produits_avec_prix.append(f"• {nom} : {prix}")

    # Cherche TOUS les produits mentionnés avec leur quantité
    produits_trouves = _extraire_multi_produits(msg, produits_catalogue)

    # ── Annulation ────────────────────────────────────────────────────────
    annul_fr = ["annuler", "cancel", "annulation", "je veux annuler", "supprimer ma commande"]
    annul_wo = ["bañ commande", "bañal commande", "man bëgguma"]
    if any(m in msg for m in annul_fr + annul_wo):
        texte = ("Commande bi dina bañ. Yéndul…" if langue == "wo"
                 else "D'accord, je vais annuler votre commande en cours.")
        return json.dumps({"intent": "annulation", "produits": [], "langue": langue, "reponse": texte})

    # ── Catalogue ─────────────────────────────────────────────────────────
    cat_fr = ["catalogue", "vend", "avez", "liste", "produit", "disponible", "qu'est-ce que", "quoi"]
    cat_wo = ["li am", "yëgël", "jënd lool", "catalogue"]
    if any(m in msg for m in cat_fr + cat_wo):
        intro = f"Bonjour {prenom_client} ! " if prenom_client else ""
        liste = "\n".join(produits_avec_prix) if produits_avec_prix else "Aucun produit disponible."
        texte = (f"{intro}Yëgël yi am :\n{liste}\n\nBind nom bi ci yëgël yi ngir commande."
                 if langue == "wo"
                 else f"{intro}Voici nos produits :\n{liste}\n\nTapez le nom du produit pour commander.")
        return json.dumps({"intent": "catalogue", "produits": [], "langue": langue, "reponse": texte})

    # ── Commande / Achat ──────────────────────────────────────────────────
    achat_fr = ["acheter", "veux", "prendre", "commander", "je voudrais",
                "donne", "commande", "want", "je prends", "je veux"]
    achat_wo = ["jënd", "buy", "naan", "lekk", "bëgg", "man bëgg"]
    if produits_trouves or any(m in msg for m in achat_fr + achat_wo):
        if produits_trouves:
            nb = len(produits_trouves)
            if nb == 1:
                p = produits_trouves[0]
                texte = (f"Commande {p['quantite']}x {p['nom']} bi dafay def !"
                         if langue == "wo"
                         else f"Commande de {p['quantite']}x {p['nom']} enregistrée !")
            else:
                noms = ", ".join(f"{p['quantite']}x {p['nom']}" for p in produits_trouves)
                texte = (f"Commande bi dafay def ! {noms}"
                         if langue == "wo"
                         else f"Commande enregistrée ! {noms}")
            return json.dumps({"intent": "commande", "produits": produits_trouves,
                               "langue": langue, "reponse": texte})
        texte = ("Lan la bëgg jënd ? Bind nom bi ci yëgël bi."
                 if langue == "wo"
                 else "Quel produit souhaitez-vous commander ?")
        return json.dumps({"intent": "commande", "produits": [], "langue": langue, "reponse": texte})

    # ── Paiement ──────────────────────────────────────────────────────────
    pay_fr = ["pay", "wave", "orange", "envoy", "j'ai payé", "paiement", "virement"]
    pay_wo = ["jox", "xaalis", "defal", "wave"]
    if any(m in msg for m in pay_fr + pay_wo):
        texte = ("Jërejëf ! Commerçant bi dina xam-xam te dina la génne yoon bu ndaw."
                 if langue == "wo"
                 else "Merci ! Votre preuve de paiement a bien été reçue. Le commerçant va vérifier.")
        return json.dumps({"intent": "paiement", "produits": [], "langue": langue, "reponse": texte})

    # ── Livraison ─────────────────────────────────────────────────────────
    if any(m in msg for m in ["livraison", "où en est", "commande prête", "quand", "délai"]):
        texte = ("Commande bi dafay yëgëloon. Dina la xibaar."
                 if langue == "wo"
                 else "Votre commande est en cours de préparation. Nous vous tiendrons informé.")
        return json.dumps({"intent": "livraison", "produits": [], "langue": langue, "reponse": texte})

    # ── Salutations ───────────────────────────────────────────────────────
    salut_fr = ["bonjour", "bonsoir", "salut", "hello", "hi", "bjr", "bsr", "slt"]
    salut_wo = ["nanga def", "naka", "jamm", "asalaamaalekum", "salam"]
    if any(m in msg for m in salut_fr + salut_wo):
        nom = f" {prenom_client}" if prenom_client else ""
        liste = "\n".join(produits_avec_prix[:5]) if produits_avec_prix else ""
        texte_fr = (
            f"Bonjour{nom} ! 👋 Bienvenue chez *{_extraire_nom_boutique(system_prompt)}* !\n\n"
            f"Voici nos produits du moment :\n{liste}\n\n"
            f"Tapez *catalogue* pour tout voir ou dites-moi ce que vous cherchez 😊"
            if liste else
            f"Bonjour{nom} ! 👋 Bienvenue ! Comment puis-je vous aider ?"
        )
        texte_wo = (
            f"Nanga def{nom} ! 👋 Dalal ak Yëgël ci *{_extraire_nom_boutique(system_prompt)}* !\n\n"
            f"Yëgël yi am :\n{liste}\n\n"
            f"Bind *catalogue* ngir xam bees."
            if liste else
            f"Nanga def{nom} ! 👋 Lan la bëgg ?"
        )
        texte = texte_wo if langue == "wo" else texte_fr
        return json.dumps({"intent": "autre", "produits": [], "langue": langue, "reponse": texte})

    # ── Remerciements ─────────────────────────────────────────────────────
    merci_fr = ["merci", "thank", "super", "parfait", "excellent", "top", "ça marche", "ok merci", "d'accord"]
    merci_wo = ["jërejëf", "yow def na", "neex na"]
    if any(m in msg for m in merci_fr + merci_wo):
        texte = ("Jërejëf ! Am na lu bëgg ? 😊" if langue == "wo"
                 else "Avec plaisir ! 😊 Autre chose que je peux faire pour vous ?")
        return json.dumps({"intent": "autre", "produits": [], "langue": langue, "reponse": texte})

    # ── Défaut intelligent ────────────────────────────────────────────────
    nom_boutique = _extraire_nom_boutique(system_prompt)
    salut_prefix = f"Bonjour {prenom_client} ! " if prenom_client else ""
    liste = "\n".join(produits_avec_prix[:5]) if produits_avec_prix else ""
    texte_fr = (
        f"{salut_prefix}Je suis l'assistant de *{nom_boutique}* 🤖\n\n"
        f"Je peux vous aider à :\n"
        f"• Voir notre catalogue (tapez *catalogue*)\n"
        f"• Passer une commande\n"
        f"• Suivre une commande\n\n"
        f"Que puis-je faire pour vous ?"
    )
    texte_wo = (
        f"Man moy assistant bi ci *{nom_boutique}* 🤖\n\n"
        f"Bind *catalogue* ngir xam yëgël yi, walla yëgëlal lan la bëgg jënd."
    )
    texte = texte_wo if langue == "wo" else texte_fr
    return json.dumps({"intent": "autre", "produits": [], "langue": langue, "reponse": texte})


def _extraire_nom_boutique(system_prompt: str) -> str:
    m = re.search(r'boutique "([^"]+)"', system_prompt)
    return m.group(1) if m else "la boutique"


def _extraire_multi_produits(msg: str, produits_catalogue: list) -> list[dict]:
    """
    Extrait tous les produits mentionnés dans le message avec leur quantité.
    Retourne une liste de {"nom": str, "quantite": int}.
    """
    trouves = []
    for nom in produits_catalogue:
        nom_lower = nom.lower()
        # Cherche "[quantite] [x] [nom]" ou "[nom]" seul
        pattern = r"(\d+)\s*(?:x\s*)?" + re.escape(nom_lower)
        m = re.search(pattern, msg, re.IGNORECASE)
        if m:
            trouves.append({"nom": nom, "quantite": int(m.group(1))})
        elif nom_lower in msg:
            # Match exact sans quantité → 1
            trouves.append({"nom": nom, "quantite": 1})
        else:
            # Match sur le premier mot (≥ 3 caractères)
            premier_mot = nom_lower.split()[0]
            if len(premier_mot) >= 3:
                pattern2 = r"(\d+)\s*(?:x\s*)?" + re.escape(premier_mot)
                m2 = re.search(pattern2, msg, re.IGNORECASE)
                if m2:
                    trouves.append({"nom": nom, "quantite": int(m2.group(1))})
                elif premier_mot in msg and nom not in [t["nom"] for t in trouves]:
                    trouves.append({"nom": nom, "quantite": 1})
    return trouves


# ─── Parsing de la réponse JSON ───────────────────────────────────────────────

def _parser_reponse(texte: str) -> dict:
    """
    Parse la réponse JSON de Claude.
    Si le parsing échoue, retourne un intent "autre" avec le texte brut.
    """
    texte_nettoye = texte.strip()
    if texte_nettoye.startswith("```"):
        lignes = texte_nettoye.split("\n")
        texte_nettoye = "\n".join(lignes[1:-1])

    try:
        data = json.loads(texte_nettoye)
        data.setdefault("intent", "autre")
        data.setdefault("produits", [])
        data.setdefault("langue", "fr")
        data.setdefault("reponse", texte)

        # Compatibilité ancien format (produit/quantite → produits)
        if not data["produits"] and data.get("produit"):
            data["produits"] = [{"nom": data["produit"], "quantite": int(data.get("quantite", 1))}]

        return data
    except json.JSONDecodeError:
        logger.warning("Réponse Claude non-JSON : %s", texte[:200])
        return {"intent": "autre", "produits": [], "langue": "fr", "reponse": texte}


# ─── Actions métier ───────────────────────────────────────────────────────────

def _executer_action(
    boutique: Boutique,
    client: Client,
    parsed: dict,
    message_original: str,
) -> str:
    """
    Selon l'intent détecté, exécute l'action métier appropriée
    et retourne le texte de réponse final pour le client.
    """
    intent = parsed.get("intent", "autre")
    reponse_ia = parsed.get("reponse", "")
    langue = parsed.get("langue", "fr")

    # ── Détection et sauvegarde du prénom (tous intents) ─────────────────
    prenom = _detecter_prenom(message_original)
    if prenom and not client.prenom:
        Client.objects.filter(pk=client.pk).update(prenom=prenom)
        client.prenom = prenom
        logger.info("Prénom détecté : %s — client %s", prenom, client.telephone)

    if intent == "commande":
        return _traiter_commande(boutique, client, parsed, langue)

    if intent == "paiement":
        return _traiter_paiement(boutique, client, langue)

    if intent == "annulation":
        return _traiter_annulation(boutique, client, langue)

    # catalogue, livraison, autre → on retourne directement la réponse IA
    return reponse_ia


# ─── Traitement commande (multi-produits) ─────────────────────────────────────

def _traiter_commande(
    boutique: Boutique,
    client: Client,
    parsed: dict,
    langue: str,
) -> str:
    """
    Crée une commande avec plusieurs lignes (multi-produits).
    Gère le stock avec SELECT FOR UPDATE.
    """
    produits_list = parsed.get("produits", [])

    if not produits_list:
        return parsed.get("reponse", "")

    try:
        with transaction.atomic():
            commande = Commande.objects.create(
                boutique=boutique,
                client=client,
                statut="attente_paiement",
            )
            lignes_info = []
            erreurs = []

            for item in produits_list:
                nom_produit = item.get("nom", "")
                quantite = int(item.get("quantite", 1))

                try:
                    produit = (
                        Produit.objects.select_for_update()
                        .get(boutique=boutique, nom__iexact=nom_produit, actif=True)
                    )
                except Produit.DoesNotExist:
                    logger.warning("Produit introuvable : '%s'", nom_produit)
                    erreurs.append(nom_produit)
                    continue

                if produit.stock < quantite:
                    erreurs.append(f"{nom_produit} (stock insuffisant : {produit.stock})")
                    continue

                produit.stock -= quantite
                produit.save(update_fields=["stock"])

                LigneCommande.objects.create(
                    commande=commande,
                    produit=produit,
                    quantite=quantite,
                    prix_unitaire=produit.prix,
                )
                lignes_info.append({"produit": produit, "quantite": quantite})

            # Si aucune ligne valide, annuler la commande
            if not lignes_info:
                commande.delete()
                msg_erreur = ", ".join(erreurs)
                if langue == "wo":
                    return f"Baal ma, produits yi amul : {msg_erreur}. Bind *catalogue* ngir xam yi am."
                return f"Désolé, ces produits ne sont pas disponibles : {msg_erreur}. Tapez *catalogue* pour voir ce qui est disponible."

            commande.recalculer_total()

            # Mettre à jour le compteur client
            Client.objects.filter(pk=client.pk).update(
                total_commandes=client.total_commandes + 1
            )

            logger.info(
                "Commande %s créée — boutique=%s client=%s (%d ligne(s))",
                commande.numero_ref, boutique.nom, client.telephone, len(lignes_info),
            )

            # Notifier le commerçant
            try:
                from .sender import notifier_nouvelle_commande
                notifier_nouvelle_commande(boutique, commande)
            except Exception:
                logger.warning("Impossible de notifier le commerçant (commande %s).", commande.numero_ref)

            reponse = _message_confirmation_commande(commande, lignes_info, langue)

            # Avertir des articles non disponibles si partiels
            if erreurs:
                reponse += f"\n\n⚠️ Indisponibles : {', '.join(erreurs)}"

            return reponse

    except Exception as exc:
        logger.exception("Erreur dans _traiter_commande : %s", exc)
        return _message_erreur(langue)


def _traiter_paiement(boutique: Boutique, client: Client, langue: str) -> str:
    """
    Demande le numéro de transaction au client pour enregistrer le paiement.
    """
    if langue == "wo":
        return (
            "Jërejëf ! Bind numéro transaction Wave walla Orange Money bi :\n"
            "(ex: WV-12345678 walla OM-98765432)"
        )
    return (
        "Merci ! Quel est votre numéro de transaction Wave ou Orange Money ?\n"
        "(ex: WV-12345678 ou OM-98765432)"
    )


def _traiter_annulation(boutique: Boutique, client: Client, langue: str) -> str:
    """
    Annule la dernière commande en attente de paiement du client
    et remet les quantités en stock.
    """
    from django.db.models import F

    try:
        with transaction.atomic():
            commande = (
                Commande.objects
                .filter(boutique=boutique, client=client, statut="attente_paiement")
                .select_for_update()
                .order_by("-created_at")
                .first()
            )

            if not commande:
                if langue == "wo":
                    return "Amul commande bi tax-taxal pour annuler. Yëgël na ko."
                return "Vous n'avez aucune commande en attente à annuler."

            # Remettre le stock pour chaque ligne
            for ligne in commande.lignes.select_related("produit").all():
                Produit.objects.filter(pk=ligne.produit_id).update(
                    stock=F("stock") + ligne.quantite
                )

            commande.statut = "annulee"
            commande.save(update_fields=["statut", "updated_at"])

            logger.info(
                "Commande %s annulée par le client %s — stock remis.",
                commande.numero_ref, client.telephone,
            )

            if langue == "wo":
                return (
                    f"Commande *{commande.numero_ref}* bi dafa bañ ✅\n"
                    f"Stock bi daj nañ. Bëgg na ko ci kanam ?"
                )
            return (
                f"Votre commande *{commande.numero_ref}* a bien été annulée ✅\n"
                f"Le stock a été remis à jour. N'hésitez pas à recommander !"
            )

    except Exception as exc:
        logger.error("Erreur lors de l'annulation (client=%s) : %s", client.telephone, exc)
        if langue == "wo":
            return "Baal ma, am na jafe-jafe ci annulation bi. Jëël ci kanam ndaw si."
        return "Désolé, une erreur est survenue lors de l'annulation. Veuillez réessayer."


# ─── Mode livraison — collecte d'adresse ──────────────────────────────────────

def _est_en_attente_adresse(boutique: Boutique, client: Client) -> Optional[Commande]:
    """
    Retourne la commande récente sans adresse si le dernier message bot
    demandait une adresse de livraison.
    """
    from datetime import timedelta
    seuil = timezone.now() - timedelta(minutes=30)

    commande = (
        Commande.objects
        .filter(
            boutique=boutique,
            client=client,
            statut="attente_paiement",
            adresse_livraison="",
            created_at__gte=seuil,
        )
        .order_by("-created_at")
        .first()
    )
    if not commande:
        return None

    # Vérifier que le dernier message sortant demandait l'adresse
    dernier_bot = (
        MessageLog.objects
        .filter(boutique=boutique, telephone_client=client.telephone, direction="sortant")
        .order_by("-created_at")
        .first()
    )
    if dernier_bot and "adresse" in dernier_bot.contenu.lower():
        return commande
    return None


def _sauver_adresse_livraison(commande: Commande, adresse: str, client: Client) -> str:
    """Sauvegarde l'adresse de livraison et confirme au client."""
    commande.adresse_livraison = adresse.strip()
    commande.save(update_fields=["adresse_livraison", "updated_at"])
    logger.info("Adresse de livraison sauvegardée pour commande %s.", commande.numero_ref)

    langue = client.langue_preferee
    if langue == "wo":
        return (
            f"Jërejëf ! Adresse bi dafa def ✅\n"
            f"Commande *{commande.numero_ref}* — Jox ñu xaalis bi pour confirmer."
        )
    return (
        f"Adresse enregistrée ✅\n"
        f"Commande *{commande.numero_ref}* — Envoyez votre preuve de paiement pour confirmer."
    )


# ─── Paiement — collecte de la référence de transaction ──────────────────────

def _est_en_attente_reference_paiement(boutique: Boutique, client: Client) -> Optional[Commande]:
    """
    Retourne la commande récente sans référence de paiement si le dernier
    message bot demandait un numéro de transaction.
    """
    from datetime import timedelta
    seuil = timezone.now() - timedelta(minutes=30)

    commande = (
        Commande.objects
        .filter(
            boutique=boutique,
            client=client,
            statut="attente_paiement",
            reference_paiement="",
            created_at__gte=seuil,
        )
        .order_by("-created_at")
        .first()
    )
    if not commande:
        return None

    # Vérifier que le dernier message bot demandait la référence
    dernier_bot = (
        MessageLog.objects
        .filter(boutique=boutique, telephone_client=client.telephone, direction="sortant")
        .order_by("-created_at")
        .first()
    )
    if dernier_bot and "transaction" in dernier_bot.contenu.lower():
        return commande
    return None


def _sauver_reference_paiement(commande: Commande, reference: str, client: Client) -> str:
    """Sauvegarde la référence de transaction et notifie le commerçant."""
    ref = reference.strip()

    # Détecter le mode de paiement depuis la référence
    ref_lower = ref.lower()
    if "wave" in ref_lower or ref.upper().startswith("WV"):
        mode = "wave"
    elif "orange" in ref_lower or ref.upper().startswith("OM"):
        mode = "orange_money"
    elif "free" in ref_lower or ref.upper().startswith("FM"):
        mode = "free_money"
    else:
        mode = "wave"  # défaut le plus courant au Sénégal

    commande.reference_paiement = ref
    commande.mode_paiement = mode
    commande.save(update_fields=["reference_paiement", "mode_paiement", "updated_at"])

    logger.info(
        "Référence paiement '%s' (%s) enregistrée pour commande %s.",
        ref, mode, commande.numero_ref,
    )

    # Notifier le commerçant
    try:
        from .sender import notifier_paiement_recu
        notifier_paiement_recu(commande.boutique, commande)
    except Exception:
        logger.warning("Impossible de notifier le commerçant (paiement %s).", commande.numero_ref)

    langue = client.langue_preferee
    if langue == "wo":
        return (
            f"Jërejëf ! Réf *{ref}* bi nanu ko def ✅\n"
            f"Commande *{commande.numero_ref}* — Propriétaire bi dina xam-xam te dina la génne yoon."
        )
    return (
        f"Merci ! Référence *{ref}* bien enregistrée ✅\n"
        f"Votre commande *{commande.numero_ref}* sera confirmée très bientôt."
    )


# ─── Détection du prénom ──────────────────────────────────────────────────────

def _detecter_prenom(message: str) -> Optional[str]:
    """
    Détecte si le client mentionne son prénom dans le message.
    Retourne le prénom capitalisé, ou None si non trouvé.
    """
    patterns = [
        r"je m['\s]appelle\s+([A-Za-zÀ-ÿ]{2,30})",
        r"mon (?:prénom|nom) est\s+([A-Za-zÀ-ÿ]{2,30})",
        r"c['\s]est\s+([A-Za-zÀ-ÿ]{2,30})\s+(?:ici|qui parle)",
        r"(?:^|\s)je suis\s+([A-Za-zÀ-ÿ]{2,30})(?:\s|$)",
        r"mangi tudd\s+([A-Za-zÀ-ÿ]{2,30})",
        r"man\s+([A-Za-zÀ-ÿ]{2,30})\s+la\s+tudd",
    ]
    mots_exclus = {"pas", "une", "mon", "bien", "sur", "tout", "ici", "suis"}
    for pattern in patterns:
        m = re.search(pattern, message, re.IGNORECASE)
        if m:
            prenom = m.group(1).strip().capitalize()
            if prenom.lower() not in mots_exclus:
                return prenom
    return None


# ─── Messages formatés ────────────────────────────────────────────────────────

def _message_confirmation_commande(
    commande: Commande,
    lignes_info: list[dict],
    langue: str,
) -> str:
    montant = commande.montant_formate
    ref = commande.numero_ref
    detail = "\n".join(
        f"  • {l['quantite']}x {l['produit'].nom} — {l['produit'].prix_formate}"
        for l in lignes_info
    )

    if langue == "wo":
        return (
            f"Commande *{ref}* bi dafa def ✅\n\n"
            f"{detail}\n\n"
            f"*Total : {montant}*\n\n"
            f"Jox ñu xaalis bi ci Wave walla Orange Money.\n"
            f"Lan moy adresse livraison bi ?"
        )
    return (
        f"Commande *{ref}* confirmée ✅\n\n"
        f"{detail}\n\n"
        f"*Total : {montant}*\n\n"
        f"Veuillez payer via Wave ou Orange Money et envoyer la capture d'écran.\n"
        f"Quelle est votre adresse de livraison ?"
    )


def _message_stock_insuffisant(produit: Produit, quantite: int, langue: str) -> str:
    if langue == "wo":
        return (
            f"Baal ma, *{produit.nom}* amul ci stock {quantite} woon. "
            f"Stock bi yëgëloon *{produit.stock}* rekk. "
            f"Xam na bañ yi am ?"
        )
    return (
        f"Désolé, nous n'avons que *{produit.stock}* unité(s) de *{produit.nom}* en stock. "
        f"Voulez-vous commander une quantité différente ?"
    )


def _message_erreur(langue: str) -> str:
    if langue == "wo":
        return "Baal ma, am na jafe-jafe tekki ci yoon. Jëël ci kanam ndaw si."
    return "Désolé, une erreur technique est survenue. Veuillez réessayer dans quelques instants."
