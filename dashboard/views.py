"""
Dashboard commerçant — Fëgg Jaay.

Interface web simple pour gérer produits, suivre les commandes
et consulter les stats du jour. Accès protégé par login Django.
"""

import csv
import logging
from datetime import timedelta

VILLES_SENEGAL = [
    "Dakar", "Pikine", "Guédiawaye", "Rufisque", "Thiès", "Mbour", "Tivaouane",
    "Diourbel", "Touba", "Mbacké", "Kaolack", "Nioro du Rip", "Gossas",
    "Fatick", "Foundiougne", "Ziguinchor", "Bignona", "Oussouye",
    "Saint-Louis", "Dagana", "Podor", "Richard-Toll",
    "Louga", "Linguère", "Kébémer",
    "Tambacounda", "Bakel", "Goudiry",
    "Kolda", "Vélingara", "Médina Yoro Foulah",
    "Sédhiou", "Bounkiling", "Goudomp",
    "Kaffrine", "Birkelane", "Koungheul", "Malem Hodar",
    "Matam", "Kanel", "Ranérou",
    "Kédougou", "Saraya", "Salemata",
    "Autre",
]

from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from django.db.models.functions import TruncDate

from django.contrib.auth.models import User
from django.utils.text import slugify

from boutiques.models import Boutique, Categorie, Commande, LigneCommande, Produit, Client, MessageLog, ZoneLivraison, PushSubscription

logger = logging.getLogger(__name__)


# ─── Authentification ─────────────────────────────────────────────────────────

def inscription(request):
    """Inscription d'un nouveau commerçant — crée User + Boutique liés."""
    if request.user.is_authenticated:
        return redirect("dashboard:accueil")

    erreurs = {}

    if request.method == "POST":
        nom_boutique = request.POST.get("nom_boutique", "").strip()
        _tel_raw = request.POST.get("telephone", "").strip().replace(" ", "").replace("-", "").replace(".", "").lstrip("+")
        telephone = ("221" + _tel_raw) if (len(_tel_raw) == 9 and _tel_raw.isdigit()) else _tel_raw
        ville = request.POST.get("ville", "Dakar").strip()
        username = request.POST.get("username", "").strip()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        # Validations
        if not nom_boutique:
            erreurs["nom_boutique"] = "Nom de boutique requis."
        if not telephone:
            erreurs["telephone"] = "Numéro WhatsApp requis."
        elif Boutique.objects.filter(telephone_wa=telephone.lstrip("+")).exists():
            erreurs["telephone"] = "Ce numéro est déjà utilisé."
        if not username:
            erreurs["username"] = "Nom d'utilisateur requis."
        elif User.objects.filter(username=username).exists():
            erreurs["username"] = "Ce nom d'utilisateur est déjà pris."
        if len(password1) < 6:
            erreurs["password1"] = "Le mot de passe doit faire au moins 6 caractères."
        elif password1 != password2:
            erreurs["password2"] = "Les mots de passe ne correspondent pas."

        if not erreurs:
            # Générer un slug unique
            slug_base = slugify(nom_boutique) or username
            slug = slug_base
            compteur = 1
            while Boutique.objects.filter(slug=slug).exists():
                slug = f"{slug_base}-{compteur}"
                compteur += 1

            tel_normalise = telephone.lstrip("+")

            from django.db import transaction as db_transaction
            with db_transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    password=password1,
                    is_staff=True,
                )
                Boutique.objects.create(
                    proprietaire=user,
                    nom=nom_boutique,
                    telephone_wa=tel_normalise,
                    proprietaire_tel=tel_normalise,
                    ville=ville,
                    slug=slug,
                    wa_phone_id="",
                    wa_token="",
                )

            login(request, user)
            messages.success(request, f"Bienvenue ! Votre boutique *{nom_boutique}* est créée.")
            return redirect("dashboard:accueil")

    return render(request, "dashboard/inscription.html", {"erreurs": erreurs, "post": request.POST, "villes_senegal": VILLES_SENEGAL})


def vue_login(request):
    if request.user.is_authenticated:
        return redirect("dashboard:accueil")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect(request.GET.get("next", "dashboard:accueil"))
        messages.error(request, "Identifiants incorrects.")

    return render(request, "dashboard/login.html")


@login_required
def vue_logout(request):
    logout(request)
    return redirect("dashboard:login")


# ─── Helper : récupérer la boutique de l'utilisateur connecté ─────────────────

def _get_boutique(request):
    """Retourne la boutique active pour l'utilisateur connecté.

    Priorité :
      1. Boutique choisie via le sélecteur (stockée en session)
      2. Seule boutique du compte
      3. Fallback legacy (proprietaire_tel = username)
      4. Admin : première boutique active
    """
    user = request.user

    # Toutes les boutiques du compte
    qs = Boutique.objects.filter(proprietaire=user)
    if not qs.exists():
        # Fallback legacy
        boutique = Boutique.objects.filter(
            proprietaire_tel=user.username, actif=True
        ).first()
        if boutique:
            return boutique
        if user.is_staff:
            return Boutique.objects.filter(actif=True).first()
        return None

    # Session : boutique choisie
    boutique_id = request.session.get("boutique_active_id")
    if boutique_id:
        b = qs.filter(pk=boutique_id).first()
        if b:
            return b

    # Par défaut : première boutique
    b = qs.first()
    request.session["boutique_active_id"] = str(b.pk)
    return b


def _get_mes_boutiques(request):
    """Retourne toutes les boutiques de l'utilisateur connecté."""
    return Boutique.objects.filter(proprietaire=request.user).order_by("nom")


@login_required
@require_POST
def changer_boutique(request):
    """Sélectionne la boutique active (POST: boutique_id)."""
    boutique_id = request.POST.get("boutique_id", "").strip()
    if boutique_id and Boutique.objects.filter(pk=boutique_id, proprietaire=request.user).exists():
        request.session["boutique_active_id"] = boutique_id
    return redirect(request.POST.get("next", "dashboard:accueil"))


# ─── Accueil / Stats du jour ──────────────────────────────────────────────────

@login_required
def accueil(request):
    boutique = _get_boutique(request)
    if not boutique:
        messages.warning(request, "Aucune boutique associée à votre compte.")
        return render(request, "dashboard/no_boutique.html")

    maintenant = timezone.now()
    debut_journee = maintenant.replace(hour=0, minute=0, second=0, microsecond=0)

    # Période sélectionnée pour le graphique
    periode = request.GET.get("periode", "7")
    if periode not in ("7", "30", "90"):
        periode = "7"
    nb_jours = int(periode)
    debut_periode = maintenant - timedelta(days=nb_jours)

    commandes_jour = Commande.objects.filter(boutique=boutique, created_at__gte=debut_journee)
    commandes_semaine = Commande.objects.filter(boutique=boutique, created_at__gte=debut_periode)

    # Produits en stock bas (calculé en amont pour réutilisation dans stats)
    produits_bas = [
        p for p in Produit.objects.filter(boutique=boutique, actif=True)
        if p.stock <= p.stock_alerte
    ]

    stats = {
        "commandes_jour": commandes_jour.count(),
        "commandes_payees_jour": commandes_jour.filter(
            statut__in=["payee", "en_preparation", "livree"]
        ).count(),
        "ca_jour": commandes_jour.filter(
            statut__in=["payee", "en_preparation", "livree"]
        ).aggregate(total=Sum("montant_total"))["total"] or 0,
        "commandes_en_attente": Commande.objects.filter(
            boutique=boutique, statut="attente_paiement"
        ).count(),
        "clients_total": Client.objects.filter(boutique=boutique).count(),
        "produits_stock_bas": len(produits_bas),
    }

    # Dernières commandes
    dernieres_commandes = Commande.objects.filter(
        boutique=boutique
    ).select_related("client").order_by("-created_at")[:10]

    # Ventes par jour sur la période sélectionnée (pour le graphique)
    from datetime import timedelta as td
    ventes_qs = (
        Commande.objects.filter(boutique=boutique, created_at__gte=debut_periode)
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(nb=Count("id"), ca=Sum("montant_total"))
        .order_by("date")
    )
    # Remplir les jours manquants avec 0
    jours_labels, jours_nb, jours_ca = [], [], []
    for i in range(nb_jours):
        jour = (maintenant - td(days=nb_jours - 1 - i)).date()
        # Pour 30j/90j, afficher semaines ou mois
        if nb_jours <= 7:
            jours_labels.append(jour.strftime("%d/%m"))
        elif nb_jours <= 30:
            jours_labels.append(jour.strftime("%d/%m"))
        else:
            jours_labels.append(jour.strftime("%d/%m"))
        entree = next((v for v in ventes_qs if v["date"] == jour), None)
        jours_nb.append(entree["nb"] if entree else 0)
        jours_ca.append(entree["ca"] or 0 if entree else 0)

    # Top 5 produits les plus commandés
    top_produits = (
        LigneCommande.objects.filter(commande__boutique=boutique)
        .values("produit__nom")
        .annotate(total_vendu=Sum("quantite"))
        .order_by("-total_vendu")[:5]
    )

    # Top 5 clients par CA
    top_clients = (
        Commande.objects.filter(boutique=boutique, statut__in=["payee", "en_preparation", "livree"])
        .values("client__prenom", "client__telephone")
        .annotate(ca=Sum("montant_total"), nb=Count("id"))
        .order_by("-ca")[:5]
    )

    # Répartition commandes par statut (pour donut)
    statuts_data = (
        Commande.objects.filter(boutique=boutique)
        .values("statut")
        .annotate(nb=Count("id"))
    )
    statuts_labels = []
    statuts_nb = []
    statuts_colors = {
        "attente_paiement": "#ffc107",
        "payee": "#17a2b8",
        "en_preparation": "#6f42c1",
        "livree": "#28a745",
        "annulee": "#dc3545",
    }
    statuts_display = {
        "attente_paiement": "Attente paiement",
        "payee": "Payée",
        "en_preparation": "En préparation",
        "livree": "Livrée",
        "annulee": "Annulée",
    }
    donut_colors = []
    for s in statuts_data:
        statuts_labels.append(statuts_display.get(s["statut"], s["statut"]))
        statuts_nb.append(s["nb"])
        donut_colors.append(statuts_colors.get(s["statut"], "#aaa"))

    # Onboarding : calcul des étapes complètes
    has_products = Produit.objects.filter(boutique=boutique, actif=True).exists()
    has_wa_config = bool(boutique.wa_phone_id and boutique.wa_token)
    has_tested_bot = MessageLog.objects.filter(boutique=boutique).exists()
    onboarding_steps = [
        {"label": "Boutique créée", "done": True, "url": None},
        {"label": "Ajouter vos produits", "done": has_products, "url": "dashboard:creer_produit"},
        {"label": "Configurer WhatsApp API", "done": has_wa_config, "url": "dashboard:config_boutique"},
        {"label": "Tester votre bot", "done": has_tested_bot, "url": "dashboard:test_bot"},
    ]
    onboarding_done = sum(1 for s in onboarding_steps if s["done"])
    onboarding_total = len(onboarding_steps)
    show_onboarding = onboarding_done < onboarding_total

    # Stats globales période
    ca_periode = sum(jours_ca)
    nb_commandes_periode = sum(jours_nb)

    context = {
        "boutique": boutique,
        "stats": stats,
        "produits_bas": produits_bas,
        "dernieres_commandes": dernieres_commandes,
        "maintenant": maintenant,
        "jours_labels": jours_labels,
        "jours_nb": jours_nb,
        "jours_ca": jours_ca,
        "top_produits": top_produits,
        "top_clients": top_clients,
        "statuts_labels": statuts_labels,
        "statuts_nb": statuts_nb,
        "donut_colors": donut_colors,
        "onboarding_steps": onboarding_steps,
        "show_onboarding": show_onboarding,
        "onboarding_done": onboarding_done,
        "onboarding_total": onboarding_total,
        "onboarding_pct": int(onboarding_done / onboarding_total * 100),
        "periode": periode,
        "ca_periode": ca_periode,
        "nb_commandes_periode": nb_commandes_periode,
    }
    return render(request, "dashboard/accueil.html", context)


# ─── Gestion produits ─────────────────────────────────────────────────────────

@login_required
def liste_produits(request):
    boutique = _get_boutique(request)
    if not boutique:
        return redirect("dashboard:accueil")

    produits = Produit.objects.filter(boutique=boutique).order_by("nom")
    return render(request, "dashboard/produits/liste.html", {
        "boutique": boutique,
        "produits": produits,
    })


@login_required
def creer_produit(request):
    boutique = _get_boutique(request)
    if not boutique:
        return redirect("dashboard:accueil")

    if request.method == "POST":
        nom = request.POST.get("nom", "").strip()
        prix_str = request.POST.get("prix", "0").replace(" ", "").replace("FCFA", "")
        stock_str = request.POST.get("stock", "0")
        stock_alerte_str = request.POST.get("stock_alerte", "5")
        description = request.POST.get("description", "").strip()

        try:
            prix = int(prix_str)
            stock = int(stock_str)
            stock_alerte = int(stock_alerte_str)
        except ValueError:
            messages.error(request, "Prix et stock doivent être des nombres entiers.")
            return render(request, "dashboard/produits/form.html", {
                "boutique": boutique,
                "mode": "creation",
            })

        categorie_id = request.POST.get("categorie", "").strip()
        categorie = Categorie.objects.filter(pk=categorie_id, boutique=boutique).first() if categorie_id else None

        produit = Produit.objects.create(
            boutique=boutique,
            nom=nom,
            prix=prix,
            stock=stock,
            stock_alerte=stock_alerte,
            description=description,
            categorie=categorie,
        )
        if "photo" in request.FILES:
            produit.photo = request.FILES["photo"]
            produit.save(update_fields=["photo"])

        messages.success(request, f"Produit *{nom}* créé avec succès.")
        return redirect("dashboard:liste_produits")

    categories = Categorie.objects.filter(boutique=boutique)
    return render(request, "dashboard/produits/form.html", {
        "boutique": boutique,
        "mode": "creation",
        "categories": categories,
    })


@login_required
def modifier_produit(request, produit_id):
    boutique = _get_boutique(request)
    produit = get_object_or_404(Produit, pk=produit_id, boutique=boutique)

    if request.method == "POST":
        produit.nom = request.POST.get("nom", produit.nom).strip()
        produit.description = request.POST.get("description", produit.description).strip()
        try:
            produit.prix = int(
                request.POST.get("prix", produit.prix)
                .replace(" ", "").replace("FCFA", "")
            )
            produit.stock = int(request.POST.get("stock", produit.stock))
            produit.stock_alerte = int(request.POST.get("stock_alerte", produit.stock_alerte))
        except (ValueError, AttributeError):
            messages.error(request, "Données invalides.")
            return render(request, "dashboard/produits/form.html", {
                "boutique": boutique,
                "produit": produit,
                "mode": "modification",
            })

        categorie_id = request.POST.get("categorie", "").strip()
        produit.categorie = Categorie.objects.filter(pk=categorie_id, boutique=boutique).first() if categorie_id else None
        produit.actif = "actif" in request.POST
        if "photo" in request.FILES:
            produit.photo = request.FILES["photo"]

        produit.save()
        messages.success(request, f"Produit *{produit.nom}* mis à jour.")
        return redirect("dashboard:liste_produits")

    categories = Categorie.objects.filter(boutique=boutique)
    return render(request, "dashboard/produits/form.html", {
        "boutique": boutique,
        "produit": produit,
        "mode": "modification",
        "categories": categories,
    })


@login_required
@require_POST
def supprimer_produit(request, produit_id):
    boutique = _get_boutique(request)
    produit = get_object_or_404(Produit, pk=produit_id, boutique=boutique)
    nom = produit.nom
    produit.actif = False
    produit.save(update_fields=["actif"])
    messages.success(request, f"Produit *{nom}* désactivé.")
    return redirect("dashboard:liste_produits")


# ─── Gestion commandes ────────────────────────────────────────────────────────

@login_required
def liste_commandes(request):
    boutique = _get_boutique(request)
    if not boutique:
        return redirect("dashboard:accueil")

    statut_filtre = request.GET.get("statut", "")
    recherche = request.GET.get("q", "").strip()
    commandes = Commande.objects.filter(boutique=boutique).select_related("client")

    if statut_filtre:
        commandes = commandes.filter(statut=statut_filtre)

    if recherche:
        commandes = commandes.filter(
            Q(numero_ref__icontains=recherche) |
            Q(client__telephone__icontains=recherche) |
            Q(client__prenom__icontains=recherche)
        )

    commandes = commandes.order_by("-created_at")
    paginator = Paginator(commandes, 25)
    page = paginator.get_page(request.GET.get("page", 1))

    return render(request, "dashboard/commandes/liste.html", {
        "boutique": boutique,
        "commandes": page,
        "page_obj": page,
        "statut_filtre": statut_filtre,
        "recherche": recherche,
        "statuts": Commande.STATUT_CHOICES,
    })


@login_required
def detail_commande(request, commande_id):
    boutique = _get_boutique(request)
    commande = get_object_or_404(
        Commande.objects.select_related("client").prefetch_related("lignes__produit"),
        pk=commande_id,
        boutique=boutique,
    )
    return render(request, "dashboard/commandes/detail.html", {
        "boutique": boutique,
        "commande": commande,
    })


@login_required
@require_POST
def changer_statut_commande(request, commande_id):
    boutique = _get_boutique(request)
    commande = get_object_or_404(Commande, pk=commande_id, boutique=boutique)

    nouveau_statut = request.POST.get("statut", "")
    statuts_valides = [s[0] for s in Commande.STATUT_CHOICES]

    if nouveau_statut not in statuts_valides:
        messages.error(request, "Statut invalide.")
        return redirect("dashboard:detail_commande", commande_id=commande_id)

    ancien_statut = commande.statut
    commande.statut = nouveau_statut
    commande.save(update_fields=["statut", "updated_at"])

    # Notifier le client selon le nouveau statut
    _notifier_client_statut(boutique, commande, nouveau_statut, ancien_statut)

    messages.success(request, f"Statut mis à jour : {commande.get_statut_display()}")
    return redirect("dashboard:detail_commande", commande_id=commande_id)


def _notifier_client_statut(boutique, commande, nouveau_statut, ancien_statut):
    """Envoie une notification WhatsApp au client lors d'un changement de statut."""
    if nouveau_statut == ancien_statut:
        return

    ref = commande.numero_ref
    messages_fr = {
        "payee": f"✅ Votre commande *{ref}* a été confirmée. Nous préparons votre colis !",
        "en_preparation": f"📦 Votre commande *{ref}* est en cours de préparation.",
        "livree": f"🎉 Votre commande *{ref}* a été livrée. Merci pour votre achat !",
        "annulee": f"❌ Votre commande *{ref}* a été annulée. Contactez-nous pour plus d'infos.",
    }
    messages_wo = {
        "payee": f"✅ Commande *{ref}* bi dafa sett. Dañuy lëkk sa yëgël !",
        "en_preparation": f"📦 Commande *{ref}* bi dañuy am ci kanam.",
        "livree": f"🎉 Commande *{ref}* bi dafa àgg. Jërejëf ci jaay !",
        "annulee": f"❌ Commande *{ref}* bi dafa dëkk. Wax ak nun ngir xam dëggëru.",
    }

    langue = commande.client.langue_preferee
    msg_map = messages_wo if langue == "wo" else messages_fr
    msg = msg_map.get(nouveau_statut)

    if msg:
        try:
            from whatsapp.sender import envoyer_message_texte
            envoyer_message_texte(boutique, commande.client.telephone, msg)
        except Exception:
            logger.warning("Impossible de notifier client commande %s → %s", ref, nouveau_statut)


# ─── Clients ──────────────────────────────────────────────────────────────────

@login_required
def liste_clients(request):
    boutique = _get_boutique(request)
    if not boutique:
        return redirect("dashboard:accueil")

    recherche = request.GET.get("q", "").strip()
    clients = Client.objects.filter(boutique=boutique)

    if recherche:
        clients = clients.filter(
            Q(telephone__icontains=recherche) | Q(prenom__icontains=recherche)
        )

    clients = clients.order_by("-created_at")
    paginator = Paginator(clients, 25)
    page = paginator.get_page(request.GET.get("page", 1))

    return render(request, "dashboard/clients/liste.html", {
        "boutique": boutique,
        "clients": page,
        "page_obj": page,
        "recherche": recherche,
    })


@login_required
def conversation_client(request, client_id):
    boutique = _get_boutique(request)
    client = get_object_or_404(Client, pk=client_id, boutique=boutique)

    messages_log = (
        MessageLog.objects.filter(boutique=boutique, telephone_client=client.telephone)
        .order_by("created_at")
    )
    commandes = (
        Commande.objects.filter(boutique=boutique, client=client)
        .prefetch_related("lignes__produit")
        .order_by("-created_at")
    )

    return render(request, "dashboard/clients/conversation.html", {
        "boutique": boutique,
        "client": client,
        "messages_log": messages_log,
        "commandes": commandes,
    })


# ─── Export CSV commandes ─────────────────────────────────────────────────────

@login_required
def exporter_commandes_csv(request):
    boutique = _get_boutique(request)
    if not boutique:
        return redirect("dashboard:accueil")

    statut_filtre = request.GET.get("statut", "")
    commandes = Commande.objects.filter(boutique=boutique).select_related("client").prefetch_related("lignes__produit")
    if statut_filtre:
        commandes = commandes.filter(statut=statut_filtre)
    commandes = commandes.order_by("-created_at")

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="commandes.csv"'
    response.write("\ufeff")  # BOM pour Excel

    writer = csv.writer(response, delimiter=";")
    writer.writerow(["Référence", "Client", "Téléphone", "Produits", "Montant (FCFA)", "Statut", "Mode paiement", "Date"])

    for c in commandes:
        produits_str = " | ".join(
            f"{l.quantite}x {l.produit.nom}" for l in c.lignes.all()
        )
        writer.writerow([
            c.numero_ref,
            c.client.prenom or "",
            c.client.telephone,
            produits_str,
            c.montant_total,
            c.get_statut_display(),
            c.get_mode_paiement_display() if c.mode_paiement else "",
            c.created_at.strftime("%d/%m/%Y %H:%M"),
        ])

    return response


# ─── Configuration boutique ───────────────────────────────────────────────────

@login_required
def config_boutique(request):
    boutique = _get_boutique(request)
    if not boutique:
        return redirect("dashboard:accueil")

    if request.method == "POST":
        boutique.nom = request.POST.get("nom", boutique.nom).strip()
        boutique.ville = request.POST.get("ville", boutique.ville).strip()
        boutique.proprietaire_tel = request.POST.get("proprietaire_tel", boutique.proprietaire_tel).strip()
        boutique.description = request.POST.get("description", boutique.description).strip()
        boutique.message_bienvenue = request.POST.get("message_bienvenue", boutique.message_bienvenue).strip()
        boutique.wa_phone_id = request.POST.get("wa_phone_id", boutique.wa_phone_id).strip()
        boutique.wa_token = request.POST.get("wa_token", boutique.wa_token).strip()

        # Mise à jour stock_alerte global sur tous les produits si fourni
        stock_alerte_global = request.POST.get("stock_alerte_global", "").strip()
        if stock_alerte_global.isdigit():
            boutique.produits.filter(actif=True).update(stock_alerte=int(stock_alerte_global))

        # QR code Wave
        if "qr_code_wave" in request.FILES:
            boutique.qr_code_wave = request.FILES["qr_code_wave"]
        elif request.POST.get("supprimer_qr"):
            boutique.qr_code_wave = None

        boutique.save(update_fields=["nom", "ville", "proprietaire_tel", "description", "message_bienvenue", "qr_code_wave", "wa_phone_id", "wa_token", "updated_at"])
        messages.success(request, "Configuration mise à jour.")
        return redirect("dashboard:config_boutique")

    return render(request, "dashboard/config.html", {"boutique": boutique, "villes_senegal": VILLES_SENEGAL})


# ─── Catégories produits ──────────────────────────────────────────────────────

@login_required
def gestion_categories(request):
    """Gestion des catégories de produits."""
    boutique = _get_boutique(request)
    if not boutique:
        return redirect("dashboard:accueil")

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "ajouter":
            nom = request.POST.get("nom", "").strip()
            if nom:
                Categorie.objects.get_or_create(boutique=boutique, nom=nom)
                messages.success(request, f"Catégorie « {nom} » ajoutée.")

        elif action == "supprimer":
            cat_id = request.POST.get("cat_id")
            Categorie.objects.filter(pk=cat_id, boutique=boutique).delete()
            messages.success(request, "Catégorie supprimée.")

        return redirect("dashboard:gestion_categories")

    categories = Categorie.objects.filter(boutique=boutique).annotate(
        nb_produits=Count("produits")
    )
    return render(request, "dashboard/produits/categories.html", {
        "boutique": boutique,
        "categories": categories,
    })


# ─── Zones de livraison ───────────────────────────────────────────────────────

@login_required
def zones_livraison(request):
    """Gestion des zones de livraison de la boutique."""
    boutique = _get_boutique(request)
    if not boutique:
        return redirect("dashboard:accueil")

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "ajouter":
            nom = request.POST.get("nom", "").strip()
            frais_str = request.POST.get("frais", "0").strip()
            if nom:
                frais = int(frais_str) if frais_str.isdigit() else 0
                ZoneLivraison.objects.create(boutique=boutique, nom=nom, frais=frais)
                messages.success(request, f"Zone « {nom} » ajoutée.")

        elif action == "supprimer":
            zone_id = request.POST.get("zone_id")
            ZoneLivraison.objects.filter(pk=zone_id, boutique=boutique).delete()
            messages.success(request, "Zone supprimée.")

        elif action == "toggle":
            zone_id = request.POST.get("zone_id")
            zone = ZoneLivraison.objects.filter(pk=zone_id, boutique=boutique).first()
            if zone:
                zone.actif = not zone.actif
                zone.save(update_fields=["actif"])

        return redirect("dashboard:zones_livraison")

    zones = ZoneLivraison.objects.filter(boutique=boutique).order_by("frais", "nom")
    return render(request, "dashboard/livraisons/zones.html", {
        "boutique": boutique,
        "zones": zones,
    })


# ─── Page de test bot ────────────────────────────────────────────────────────

TEST_BOT_PHONE = "test_dashboard"


@login_required
def test_bot(request):
    """
    Interface de test du bot directement depuis le dashboard.
    Simule une conversation WhatsApp sans passer par le webhook ni Celery.
    """
    boutique = _get_boutique(request)
    if not boutique:
        return redirect("dashboard:accueil")

    if request.method == "POST":
        message = request.POST.get("message", "").strip()
        if not message:
            return JsonResponse({"error": "Message vide"}, status=400)

        from whatsapp.bot_engine import traiter_message

        # Récupérer ou créer le client test
        client, _ = Client.objects.get_or_create(
            boutique=boutique,
            telephone=TEST_BOT_PHONE,
            defaults={"prenom": "", "langue_preferee": "fr"},
        )

        # Logger le message entrant
        MessageLog.objects.create(
            boutique=boutique,
            telephone_client=TEST_BOT_PHONE,
            direction="entrant",
            contenu=message,
            type_message="texte",
        )

        # Appeler le bot directement (synchrone, pas de Celery)
        reponse = traiter_message(boutique=boutique, client=client, message=message)

        # Logger la réponse sortante
        MessageLog.objects.create(
            boutique=boutique,
            telephone_client=TEST_BOT_PHONE,
            direction="sortant",
            contenu=reponse,
            type_message="texte",
        )

        return JsonResponse({"reponse": reponse})

    # GET — charger la conversation de test
    messages_log = (
        MessageLog.objects.filter(boutique=boutique, telephone_client=TEST_BOT_PHONE)
        .order_by("created_at")
    )
    return render(request, "dashboard/test_bot.html", {
        "boutique": boutique,
        "messages_log": messages_log,
    })


@login_required
@require_POST
def reset_test_bot(request):
    """Efface la conversation de test et le client test."""
    boutique = _get_boutique(request)
    if boutique:
        # Supprimer commandes (et leurs lignes) liées au client test avant de supprimer le client (FK protégée)
        client_qs = Client.objects.filter(boutique=boutique, telephone=TEST_BOT_PHONE)
        commandes_qs = Commande.objects.filter(boutique=boutique, client__in=client_qs)
        LigneCommande.objects.filter(commande__in=commandes_qs).delete()
        commandes_qs.delete()
        MessageLog.objects.filter(boutique=boutique, telephone_client=TEST_BOT_PHONE).delete()
        client_qs.delete()
    return redirect("dashboard:test_bot")


# ─── Super-Admin ─────────────────────────────────────────────────────────────

def _superuser_required(view_fn):
    """Décorateur : réserve la vue aux superutilisateurs Django."""
    from functools import wraps
    @wraps(view_fn)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        return view_fn(request, *args, **kwargs)
    return wrapper


@_superuser_required
def superadmin_accueil(request):
    """Vue globale super-admin : stats plateforme + liste boutiques."""
    boutiques = (
        Boutique.objects.all()
        .annotate(
            nb_commandes=Count("commandes"),
            nb_clients=Count("clients"),
            ca_total=Sum("commandes__montant_total"),
        )
        .order_by("-created_at")
    )

    stats_globales = {
        "nb_boutiques": Boutique.objects.count(),
        "nb_boutiques_actives": Boutique.objects.filter(actif=True).count(),
        "nb_commandes": Commande.objects.count(),
        "nb_clients": Client.objects.count(),
        "ca_total": Commande.objects.filter(
            statut__in=["payee", "en_preparation", "livree"]
        ).aggregate(total=Sum("montant_total"))["total"] or 0,
    }

    recherche = request.GET.get("q", "").strip()
    if recherche:
        boutiques = boutiques.filter(
            Q(nom__icontains=recherche) | Q(ville__icontains=recherche)
        )

    return render(request, "dashboard/superadmin/accueil.html", {
        "boutiques": boutiques,
        "stats": stats_globales,
        "recherche": recherche,
    })


@_superuser_required
def superadmin_boutique(request, boutique_id):
    """Détail d'une boutique côté super-admin."""
    shop = get_object_or_404(Boutique, pk=boutique_id)

    stats = {
        "nb_commandes": Commande.objects.filter(boutique=shop).count(),
        "nb_clients": Client.objects.filter(boutique=shop).count(),
        "nb_produits": Produit.objects.filter(boutique=shop, actif=True).count(),
        "ca_total": Commande.objects.filter(
            boutique=shop, statut__in=["payee", "en_preparation", "livree"]
        ).aggregate(total=Sum("montant_total"))["total"] or 0,
        "commandes_attente": Commande.objects.filter(boutique=shop, statut="attente_paiement").count(),
    }

    dernieres_commandes = (
        Commande.objects.filter(boutique=shop)
        .select_related("client")
        .order_by("-created_at")[:10]
    )

    return render(request, "dashboard/superadmin/boutique.html", {
        "shop": shop,
        "stats": stats,
        "dernieres_commandes": dernieres_commandes,
        "plans": Boutique.PLAN_CHOICES,
    })


@_superuser_required
@require_POST
def superadmin_toggle_boutique(request, boutique_id):
    """Active ou désactive une boutique."""
    shop = get_object_or_404(Boutique, pk=boutique_id)
    shop.actif = not shop.actif
    shop.save(update_fields=["actif", "updated_at"])
    etat = "activée" if shop.actif else "désactivée"
    messages.success(request, f"Boutique « {shop.nom} » {etat}.")
    return redirect("dashboard:superadmin_boutique", boutique_id=boutique_id)


@_superuser_required
@require_POST
def superadmin_changer_plan(request, boutique_id):
    """Change le plan d'abonnement d'une boutique."""
    shop = get_object_or_404(Boutique, pk=boutique_id)
    nouveau_plan = request.POST.get("plan", "").strip()
    plans_valides = [p[0] for p in Boutique.PLAN_CHOICES]
    if nouveau_plan in plans_valides:
        shop.plan = nouveau_plan
        shop.save(update_fields=["plan", "updated_at"])
        messages.success(request, f"Plan mis à jour : {shop.get_plan_display()}.")
    else:
        messages.error(request, "Plan invalide.")
    return redirect("dashboard:superadmin_boutique", boutique_id=boutique_id)


# ─── Web Push ────────────────────────────────────────────────────────────────

@login_required
@require_POST
def push_subscribe(request):
    """Enregistre un abonnement push navigateur pour la boutique du commerçant."""
    boutique = _get_boutique(request)
    if not boutique:
        return JsonResponse({"error": "no boutique"}, status=400)

    import json as _json
    try:
        data = _json.loads(request.body)
        endpoint = data["endpoint"]
        keys = data["keys"]
        PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "boutique": boutique,
                "p256dh": keys["p256dh"],
                "auth": keys["auth"],
            },
        )
        return JsonResponse({"ok": True})
    except (KeyError, ValueError):
        return JsonResponse({"error": "invalid"}, status=400)


@login_required
@require_POST
def push_unsubscribe(request):
    """Supprime un abonnement push navigateur."""
    import json as _json
    try:
        data = _json.loads(request.body)
        PushSubscription.objects.filter(endpoint=data["endpoint"]).delete()
    except (KeyError, ValueError):
        pass
    return JsonResponse({"ok": True})


# ─── API JSON interne (pour les mises à jour AJAX) ───────────────────────────

@login_required
def api_stats(request):
    """Retourne les stats du jour en JSON pour les mises à jour dynamiques."""
    boutique = _get_boutique(request)
    if not boutique:
        return JsonResponse({"error": "No boutique"}, status=404)

    debut_journee = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    commandes_jour = Commande.objects.filter(boutique=boutique, created_at__gte=debut_journee)

    ca = commandes_jour.filter(
        statut__in=["payee", "en_preparation", "livree"]
    ).aggregate(total=Sum("montant_total"))["total"] or 0

    return JsonResponse({
        "commandes_jour": commandes_jour.count(),
        "ca_jour": ca,
        "ca_jour_formate": f"{ca:,} FCFA".replace(",", " "),
        "en_attente": Commande.objects.filter(
            boutique=boutique, statut="attente_paiement"
        ).count(),
    })


# ─── Créer une nouvelle boutique ──────────────────────────────────────────────

@login_required
def creer_boutique(request):
    """Crée une nouvelle boutique pour l'utilisateur connecté."""
    erreurs = {}

    if request.method == "POST":
        nom_boutique = request.POST.get("nom_boutique", "").strip()
        telephone = request.POST.get("telephone", "").strip().replace(" ", "").replace("-", "")
        ville = request.POST.get("ville", "Dakar").strip()

        if not nom_boutique:
            erreurs["nom_boutique"] = "Nom de boutique requis."
        if not telephone:
            erreurs["telephone"] = "Numéro WhatsApp requis."
        elif Boutique.objects.filter(telephone_wa=telephone.lstrip("+")).exists():
            erreurs["telephone"] = "Ce numéro est déjà utilisé."

        if not erreurs:
            from django.utils.text import slugify
            slug_base = slugify(nom_boutique) or request.user.username
            slug = slug_base
            compteur = 1
            while Boutique.objects.filter(slug=slug).exists():
                slug = f"{slug_base}-{compteur}"
                compteur += 1

            tel_normalise = telephone.lstrip("+")
            boutique = Boutique.objects.create(
                proprietaire=request.user,
                nom=nom_boutique,
                telephone_wa=tel_normalise,
                proprietaire_tel=tel_normalise,
                ville=ville,
                slug=slug,
                wa_phone_id="",
                wa_token="",
            )
            request.session["boutique_active_id"] = str(boutique.pk)
            messages.success(request, f"Boutique « {nom_boutique} » créée.")
            return redirect("dashboard:accueil")

    return render(request, "dashboard/creer_boutique.html", {"erreurs": erreurs, "post": request.POST, "villes_senegal": VILLES_SENEGAL})


# ─── Page statistiques avancées ───────────────────────────────────────────────

@login_required
def stats(request):
    """Page statistiques avancées : vue mensuelle, annuelle, comparaisons."""
    boutique = _get_boutique(request)
    if not boutique:
        return redirect("dashboard:accueil")

    from django.db.models.functions import TruncMonth, TruncYear
    from datetime import date

    annee = request.GET.get("annee", str(timezone.now().year))
    try:
        annee = int(annee)
    except ValueError:
        annee = timezone.now().year

    annees_dispo = (
        Commande.objects.filter(boutique=boutique)
        .dates("created_at", "year")
    )
    annees_list = [d.year for d in annees_dispo] or [timezone.now().year]

    # CA et nb commandes par mois pour l'année sélectionnée
    mois_qs = (
        Commande.objects.filter(boutique=boutique, created_at__year=annee)
        .annotate(mois=TruncMonth("created_at"))
        .values("mois")
        .annotate(nb=Count("id"), ca=Sum("montant_total"))
        .order_by("mois")
    )
    noms_mois = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun", "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]
    mois_labels = noms_mois[:]
    mois_nb = [0] * 12
    mois_ca = [0] * 12
    for row in mois_qs:
        idx = row["mois"].month - 1
        mois_nb[idx] = row["nb"]
        mois_ca[idx] = row["ca"] or 0

    # Totaux annuels
    total_annee_nb = sum(mois_nb)
    total_annee_ca = sum(mois_ca)

    # Comparaison avec l'année précédente
    annee_prec = annee - 1
    ca_prec = Commande.objects.filter(
        boutique=boutique, created_at__year=annee_prec,
        statut__in=["payee", "en_preparation", "livree"]
    ).aggregate(total=Sum("montant_total"))["total"] or 0
    ca_actuel = Commande.objects.filter(
        boutique=boutique, created_at__year=annee,
        statut__in=["payee", "en_preparation", "livree"]
    ).aggregate(total=Sum("montant_total"))["total"] or 0
    evolution_ca = None
    if ca_prec:
        evolution_ca = round((ca_actuel - ca_prec) / ca_prec * 100, 1)

    # Top 10 produits de l'année
    top_produits_annee = (
        LigneCommande.objects.filter(commande__boutique=boutique, commande__created_at__year=annee)
        .values("produit__nom")
        .annotate(total_vendu=Sum("quantite"), ca=Sum("prix_unitaire"))
        .order_by("-total_vendu")[:10]
    )

    # Top 10 clients de l'année
    top_clients_annee = (
        Commande.objects.filter(
            boutique=boutique, created_at__year=annee,
            statut__in=["payee", "en_preparation", "livree"]
        )
        .values("client__prenom", "client__telephone")
        .annotate(ca=Sum("montant_total"), nb=Count("id"))
        .order_by("-ca")[:10]
    )

    # Taux de conversion (commandes payées / total)
    total_cmds = Commande.objects.filter(boutique=boutique, created_at__year=annee).count()
    payees_cmds = Commande.objects.filter(
        boutique=boutique, created_at__year=annee,
        statut__in=["payee", "en_preparation", "livree"]
    ).count()
    taux_conversion = round(payees_cmds / total_cmds * 100, 1) if total_cmds else 0

    # Panier moyen
    panier_moyen = round(ca_actuel / payees_cmds) if payees_cmds else 0

    return render(request, "dashboard/stats.html", {
        "boutique": boutique,
        "annee": annee,
        "annees_list": annees_list,
        "mois_labels": mois_labels,
        "mois_nb": mois_nb,
        "mois_ca": mois_ca,
        "total_annee_nb": total_annee_nb,
        "total_annee_ca": total_annee_ca,
        "ca_prec": ca_prec,
        "ca_actuel": ca_actuel,
        "evolution_ca": evolution_ca,
        "annee_prec": annee_prec,
        "top_produits_annee": top_produits_annee,
        "top_clients_annee": top_clients_annee,
        "taux_conversion": taux_conversion,
        "panier_moyen": panier_moyen,
        "total_cmds": total_cmds,
        "payees_cmds": payees_cmds,
    })
