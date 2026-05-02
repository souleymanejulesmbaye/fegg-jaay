from boutiques.models import Boutique

try:
    boutique = Boutique.objects.get(nom__icontains="salmon")
    print(f"Boutique trouvee : {boutique.nom}")
    print(f"Numero WhatsApp actuel : {boutique.telephone_wa}")
    print(f"Numero proprietaire actuel : {boutique.proprietaire_tel}")

    nouveau_proprietaire_tel = "221778953918"
    boutique.proprietaire_tel = nouveau_proprietaire_tel
    boutique.save(update_fields=["proprietaire_tel"])

    print(f"\nMise a jour effectuee !")
    print(f"Nouveau numero proprietaire : {boutique.proprietaire_tel}")
    print("\nVous pouvez maintenant envoyer des commandes de gestion au bot depuis ce numero.")

except Boutique.DoesNotExist:
    print("Boutique SALMON SHOP non trouvee.")
    print("Liste des boutiques disponibles :")
    for b in Boutique.objects.all():
        print(f"  - {b.nom} (ID: {b.id})")
