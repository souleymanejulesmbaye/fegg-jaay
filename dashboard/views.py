"""
Dashboard commerçant — Fëgg Jaay.

Interface web simple pour gérer produits, suivre les commandes
et consulter les stats du jour. Accès protégé par login Django.
"""

import csv
import logging
from datetime import timedelta

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

from boutiques.models import Boutique, Commande, LigneCommande, Produit, Client, MessageLog

logger = logging.getLogger(__name__)


# ─── Authentification ─────────────────────────────────────────────────────────

def inscription(request):
    """Inscription d'un nouveau commerçant — crée User + Boutique liés."""
    if request.user.is_authenticated:
        return redirect("dashboard:accueil")

    erreurs = {}

    if request.method == "POST":
        nom_boutique = request.POST.get("nom_boutique", "").strip()
        telephone = request.POST.get("telephone", "").strip().replace(" ", "").replace("-", "")
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

    return render(request, "dashboard/inscription.html", {"erreurs": erreurs, "post": request.POST})


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
    """Retourne la boutique associée à l'utilisateur connecté."""
    # 1. Liaison directe via FK proprietaire
    try:
        return request.user.boutique
    except Boutique.DoesNotExist:
        pass
    # 2. Fallback legacy : username = proprietaire_tel
    boutique = Boutique.objects.filter(
        proprietaire_tel=request.user.username, actif=True
    ).first()
    if boutique:
        return boutique
    # 3. Fallback admin : première boutique active
    if request.user.is_staff:
        return Boutique.objects.filter(actif=True).first()
    return None


# ─── Accueil / Stats du jour ──────────────────────────────────────────────────

@login_required
def accueil(request):
    boutique = _get_boutique(request)
    if not boutique:
        messages.warning(request, "Aucune boutique associée à votre compte.")
        return render(request, "dashboard/no_boutique.html")

    maintenant = timezone.now()
    debut_journee = maintenant.replace(hour=0, minute=0, second=0, microsecond=0)
    debut_semaine = maintenant - timedelta(days=7)

    commandes_jour = Commande.objects.filter(boutique=boutique, created_at__gte=debut_journee)
    commandes_semaine = Commande.objects.filter(boutique=boutique, created_at__gte=debut_semaine)

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

    # Ventes par jour sur 7 jours (pour le graphique)
    ventes_7j_qs = (
        Commande.objects.filter(boutique=boutique, created_at__gte=debut_semaine)
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(nb=Count("id"), ca=Sum("montant_total"))
        .order_by("date")
    )
    # Remplir les jours manquants avec 0
    from datetime import date, timedelta as td
    jours_labels, jours_nb, jours_ca = [], [], []
    for i in range(7):
        jour = (maintenant - td(days=6 - i)).date()
        jours_labels.append(jour.strftime("%d/%m"))
        entree = next((v for v in ventes_7j_qs if v["date"] == jour), None)
        jours_nb.append(entree["nb"] if entree else 0)
        jours_ca.append(entree["ca"] or 0 if entree else 0)

    # Top 5 produits les plus commandés
    top_produits = (
        LigneCommande.objects.filter(commande__boutique=boutique)
        .values("produit__nom")
        .annotate(total_vendu=Sum("quantite"))
        .order_by("-total_vendu")[:5]
    )

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
        "onboarding_steps": onboarding_steps,
        "show_onboarding": show_onboarding,
        "onboarding_done": onboarding_done,
        "onboarding_total": onboarding_total,
        "onboarding_pct": int(onboarding_done / onboarding_total * 100),
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

        produit = Produit.objects.create(
            boutique=boutique,
            nom=nom,
            prix=prix,
            stock=stock,
            stock_alerte=stock_alerte,
            description=description,
        )
        if "photo" in request.FILES:
            produit.photo = request.FILES["photo"]
            produit.save(update_fields=["photo"])

        messages.success(request, f"Produit *{nom}* créé avec succès.")
        return redirect("dashboard:liste_produits")

    return render(request, "dashboard/produits/form.html", {
        "boutique": boutique,
        "mode": "creation",
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

        produit.actif = "actif" in request.POST
        if "photo" in request.FILES:
            produit.photo = request.FILES["photo"]

        produit.save()
        messages.success(request, f"Produit *{produit.nom}* mis à jour.")
        return redirect("dashboard:liste_produits")

    return render(request, "dashboard/produits/form.html", {
        "boutique": boutique,
        "produit": produit,
        "mode": "modification",
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

    # Notifier le client si commande passée à "payée"
    if nouveau_statut == "payee" and ancien_statut == "attente_paiement":
        from whatsapp.sender import envoyer_message_texte
        langue = commande.client.langue_preferee
        if langue == "wo":
            msg = f"Commande *{commande.numero_ref}* bi dafa sett ✅ Jërejëf ci jaay !"
        else:
            msg = f"Votre commande *{commande.numero_ref}* a été confirmée ✅ Merci pour votre achat !"
        envoyer_message_texte(boutique, commande.client.telephone, msg)

    messages.success(request, f"Statut mis à jour : {commande.get_statut_display()}")
    return redirect("dashboard:detail_commande", commande_id=commande_id)


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
        boutique.message_bienvenue = request.POST.get("message_bienvenue", boutique.message_bienvenue).strip()

        # Mise à jour stock_alerte global sur tous les produits si fourni
        stock_alerte_global = request.POST.get("stock_alerte_global", "").strip()
        if stock_alerte_global.isdigit():
            boutique.produits.filter(actif=True).update(stock_alerte=int(stock_alerte_global))

        boutique.save(update_fields=["nom", "ville", "proprietaire_tel", "message_bienvenue", "updated_at"])
        messages.success(request, "Configuration mise à jour.")
        return redirect("dashboard:config_boutique")

    return render(request, "dashboard/config.html", {"boutique": boutique})


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
