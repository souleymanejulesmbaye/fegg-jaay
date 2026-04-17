"""
Traductions FR / Wolof pour la vitrine publique Fëgg Jaay.

Usage dans les vues :
    from vitrine.translations import get_translations, get_lang
    lang = get_lang(request)
    t    = get_translations(lang)
    # Passer t et lang au contexte du template.
"""

# ─── Dictionnaire ─────────────────────────────────────────────────────────────

TRANSLATIONS: dict[str, dict[str, str]] = {
    "fr": {
        "lang_toggle": "Wolof",
        "lang_toggle_code": "wo",
        # --- Boutique ---
        "search_placeholder": "Rechercher un produit…",
        "nos_produits": "Nos produits",
        "votre_commande": "Votre commande",
        "panier_recap": "🛒 Récapitulatif",
        "label_prenom": "Votre prénom",
        "placeholder_prenom": "Ex: Moussa",
        "label_telephone": "Votre numéro WhatsApp",
        "placeholder_telephone": "Ex: +221771234567",
        "label_adresse": "Adresse de livraison",
        "placeholder_adresse": "Ex: Rue 10, Médina, Dakar",
        "label_zone": "Zone de livraison",
        "zone_placeholder": "— Choisir une zone —",
        "wa_info": (
            "📱 Après votre commande, envoyez votre référence de paiement "
            "Wave / Orange Money au commerçant via WhatsApp pour confirmer."
        ),
        "btn_commander": "Commander",
        "aucun_produit": "Aucun produit disponible pour le moment.",
        "aucun_resultat_prefix": "Aucun produit trouvé pour",
        "voir_tous": "Voir tous les produits →",
        "en_stock": "en stock",
        # --- Confirmation ---
        "cmd_enregistree": "Commande enregistrée !",
        "merci_commande": "Merci pour votre commande.",
        "livraison_label": "Livraison :",
        "total_label": "Total :",
        "paiement_soumis": "✅ Paiement soumis — en attente de confirmation",
        "reference_label": "Référence :",
        "mode_label": "Mode :",
        "comment_payer": "💰 Comment payer ?",
        "payer_instr_prefix": "Envoyez",
        "payer_instr_suffix": (
            "via Wave ou Orange Money au numéro du commerçant, "
            "puis entrez votre référence de transaction ci-dessous."
        ),
        "label_mode_paiement": "Mode de paiement",
        "label_reference": "Référence de transaction *",
        "placeholder_reference": "Ex : WV-1234567890",
        "btn_confirmer_paiement": "✅ Confirmer mon paiement",
        "btn_retour_boutique": "Retour à la boutique",
        "btn_payer_whatsapp": "💬 Payer via WhatsApp",
        # --- Connexion ---
        "connexion_titre": "Connexion",
        "connexion_sub": (
            "💬 Entrez votre numéro WhatsApp. "
            "Vous recevrez un code de confirmation."
        ),
        "label_telephone_connexion": "Numéro WhatsApp",
        "btn_recevoir_code": "Recevoir mon code",
        "pas_encore_client": "Pas encore client ?",
        "voir_catalogue": "Voir le catalogue",
        # --- OTP ---
        "otp_titre": "Code de vérification",
        "otp_sub": "Un code a été envoyé par WhatsApp à :",
        "otp_expire": "Ce code expire dans 10 minutes.",
        "btn_valider": "Valider",
        "changer_numero": "Changer de numéro",
        # --- Erreurs OTP ---
        "err_otp_expire": "Ce code a expiré. Recommencez.",
        "err_otp_incorrect": "Code incorrect. Vérifiez votre WhatsApp.",
        "err_numero_inconnu": "Numéro introuvable.",
        "err_telephone_vide": "Veuillez entrer votre numéro WhatsApp.",
        # --- Compte client ---
        "bonjour": "Bonjour",
        "mes_commandes": "Mes commandes",
        "btn_commander_lien": "Commander",
        "btn_deconnexion": "Déconnexion",
        "attente_paiement_info": (
            "En attente de paiement — payez via Wave ou Orange Money "
            "et envoyez la référence de transaction."
        ),
        "aucune_commande": "Vous n'avez pas encore de commande.",
        "voir_catalogue_btn": "Voir le catalogue",
        # --- Nav ---
        "mon_compte": "Mon compte",
        # --- Statuts commande ---
        "statut_attente_paiement": "En attente de paiement",
        "statut_payee": "Payée",
        "statut_en_preparation": "En préparation",
        "statut_livree": "Livrée",
        "statut_annulee": "Annulée",
    },

    "wo": {
        "lang_toggle": "Français",
        "lang_toggle_code": "fr",
        # --- Boutique ---
        "search_placeholder": "Seet ay xët yi…",
        "nos_produits": "Ay xët yiy jaay",
        "votre_commande": "Sa commande",
        "panier_recap": "🛒 Li ngay jënd",
        "label_prenom": "Sa tur",
        "placeholder_prenom": "Misaal: Moussa",
        "label_telephone": "Sa numéro WhatsApp",
        "placeholder_telephone": "Misaal: +221771234567",
        "label_adresse": "Fan nga dëkk",
        "placeholder_adresse": "Misaal: Rue 10, Médina, Dakar",
        "label_zone": "Périmètre bi",
        "zone_placeholder": "— Tann sa périmètre —",
        "wa_info": (
            "📱 Qëllaatal commande bi, yónneel sa référence Wave / Orange Money "
            "ci commerçant bi ci WhatsApp ngir sàmm."
        ),
        "btn_commander": "Jënd",
        "aucun_produit": "Amul xët yu ànd ci kanam.",
        "aucun_resultat_prefix": "Amul xët bu xam",
        "voir_tous": "Xool xët yépp →",
        "en_stock": "ci biir",
        # --- Confirmation ---
        "cmd_enregistree": "Commande bi dëgël na !",
        "merci_commande": "Jërejëf ci sa commande.",
        "livraison_label": "Yóbbali :",
        "total_label": "Jëmël :",
        "paiement_soumis": "✅ Fay bi yóoni — nëkk ci attente",
        "reference_label": "Référence :",
        "mode_label": "Wàll :",
        "comment_payer": "💰 Naka ngay fay ?",
        "payer_instr_prefix": "Yónneel",
        "payer_instr_suffix": (
            "ci Wave walla Orange Money ci commerçant bi, "
            "gannaaw bi bind sa référence ci yànqu."
        ),
        "label_mode_paiement": "Wàll bu fay",
        "label_reference": "Référence yu transaction *",
        "placeholder_reference": "Misaal : WV-1234567890",
        "btn_confirmer_paiement": "✅ Sàmm sa fay",
        "btn_retour_boutique": "Dellu ci boutique bi",
        "btn_payer_whatsapp": "💬 Fay ci WhatsApp",
        # --- Connexion ---
        "connexion_titre": "Dugg",
        "connexion_sub": "💬 Bind sa numéro WhatsApp. Dinaa la yónni code bi.",
        "label_telephone_connexion": "Numéro WhatsApp",
        "btn_recevoir_code": "Jënd sa code",
        "pas_encore_client": "Binduma ci kanam ?",
        "voir_catalogue": "Xool ay xët yi",
        # --- OTP ---
        "otp_titre": "Code bi",
        "otp_sub": "Dangaa jënd code ci WhatsApp :",
        "otp_expire": "Code bi dafa tàkk ci 10 minutes.",
        "btn_valider": "Sàmm",
        "changer_numero": "Soppal sa numéro",
        # --- Erreurs OTP ---
        "err_otp_expire": "Code bi dafa tàkk. Dëggël.",
        "err_otp_incorrect": "Code bi dof na. Xool sa WhatsApp.",
        "err_numero_inconnu": "Numéro bi amul.",
        "err_telephone_vide": "Bind sa numéro WhatsApp.",
        # --- Compte client ---
        "bonjour": "Asalaamalekum",
        "mes_commandes": "Sa ay commandes",
        "btn_commander_lien": "Jënd",
        "btn_deconnexion": "Dem",
        "attente_paiement_info": (
            "Nëkk ci attente bu fay — fay ci Wave walla Orange Money, "
            "gannaaw bi yónneel sa référence."
        ),
        "aucune_commande": "Dëggaluma commande.",
        "voir_catalogue_btn": "Xool ay xët yi",
        # --- Nav ---
        "mon_compte": "Sa kàddug",
        # --- Statuts commande ---
        "statut_attente_paiement": "Nëkk ci attente",
        "statut_payee": "Fayee na",
        "statut_en_preparation": "Ci kanam",
        "statut_livree": "Yóbbali na",
        "statut_annulee": "Wàcc na",
    },
}

_VALID_LANGS = frozenset(TRANSLATIONS.keys())
_LANG_SESSION_KEY = "vitrine_lang"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_lang(request) -> str:
    """
    Détecte la langue active pour la vitrine.

    Priorité :
      1. Paramètre GET ``?lang=wo`` (change + sauvegarde en session)
      2. Valeur en session
      3. Défaut : « fr »
    """
    lang_param = request.GET.get("lang", "").strip().lower()
    if lang_param in _VALID_LANGS:
        request.session[_LANG_SESSION_KEY] = lang_param
        return lang_param
    return request.session.get(_LANG_SESSION_KEY, "fr")


def get_translations(lang: str) -> dict:
    """Retourne le dictionnaire de traductions pour la langue donnée."""
    return TRANSLATIONS.get(lang, TRANSLATIONS["fr"])


def statut_traduit(lang: str, statut: str) -> str:
    """Retourne le libellé traduit d'un statut de commande."""
    t = get_translations(lang)
    return t.get(f"statut_{statut}", statut)
