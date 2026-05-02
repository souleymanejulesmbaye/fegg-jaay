# 📱 Guide WhatsApp pour Commerçants - Fëgg Jaay

## 🎯 Vue d'ensemble

Ce guide explique comment gérer votre boutique Fëgg Jaay directement depuis WhatsApp, sans avoir besoin d'utiliser un ordinateur ou le dashboard web.

## 🚀 Commencer

### 1. Connectez-vous à votre bot

Envoyez un message à votre numéro WhatsApp de boutique :
- Exemple : 221767600283 (pour SALMON SHOP)

### 2. Tapez `/menu`

Vous verrez le menu principal avec toutes les options disponibles.

---

## 📦 Gérer les produits

### Ajouter un produit

```
1. Tapez /ajouter
2. Entrez le nom du produit
   Exemple : T-shirt blanc
3. Entrez le prix en FCFA
   Exemple : 5000
4. Entrez le stock initial
   Exemple : 10
5. Envoyez une photo (optionnel)
   Tapez /skip pour passer
6. Entrez une description (optionnel)
   Tapez /skip pour passer
```

**Exemple complet :**
```
Vous: /ajouter
Bot: Quel est le nom du produit ?
Vous: T-shirt blanc
Bot: Quel est le prix en FCFA ?
Vous: 5000
Bot: Quel est le stock initial ?
Vous: 10
Bot: Envoyez une photo du produit (optionnel).
Vous: [envoyez une photo]
Bot: Ajoutez une description (optionnel).
Vous: T-shirt en coton, disponible en plusieurs tailles
Bot: 🎉 Produit ajouté avec succès !
```

### Modifier un produit

```
1. Tapez /modifier
2. Sélectionnez le produit par son numéro
3. Choisissez ce que vous voulez modifier :
   1. Prix
   2. Stock
   3. Description
4. Entrez la nouvelle valeur
```

### Supprimer un produit

```
1. Tapez /supprimer
2. Sélectionnez le produit par son numéro
3. Confirmez la suppression
```

### Voir le stock

```
Tapez /stock
```

Vous verrez la liste de tous vos produits avec leur stock actuel.

---

## 🛒 Gérer les commandes

### Voir les commandes

```
Tapez /commandes
```

Vous verrez les 10 dernières commandes avec leur statut.

### Confirmer une commande

```
1. Tapez /confirmer
2. Sélectionnez la commande par son numéro
3. La commande passe en statut "Payée"
```

### Annuler une commande

```
1. Tapez /annuler
2. Sélectionnez la commande par son numéro
3. La commande passe en statut "Annulée"
```

---

## 📊 Voir les statistiques

```
Tapez /stats
```

Vous verrez :
- Commandes du jour
- Chiffre d'affaires du jour
- Nombre de produits
- Stock bas (alertes)
- Nombre de clients

---

## 🎯 Commandes disponibles

| Commande | Description |
|----------|-------------|
| `/menu` | Menu principal |
| `/ajouter` | Ajouter un produit |
| `/modifier` | Modifier un produit |
| `/supprimer` | Supprimer un produit |
| `/stock` | Voir le stock |
| `/commandes` | Voir les commandes |
| `/confirmer` | Confirmer une commande |
| `/annuler` | Annuler une commande |
| `/stats` | Voir les statistiques |
| `/help` | Aide |
| `/cancel` | Annuler l'action en cours |

---

## 💡 Astuces

### Annuler une action en cours

Si vous faites une erreur ou voulez arrêter une action :

```
Tapez /cancel
```

Cela vous ramène au menu principal.

### Passer une étape optionnelle

Pour les étapes optionnelles (photo, description) :

```
Tapez /skip
```

### Revenir au menu principal

```
Tapez /menu
```

---

## 📱 Exemples d'utilisation

### Scénario 1 : Ajouter un nouveau produit

```
Vous: /ajouter
Bot: Quel est le nom du produit ?
You: Chemise bleue
Bot: Quel est le prix en FCFA ?
You: 8000
Bot: Quel est le stock initial ?
You: 5
Bot: Envoyez une photo du produit (optionnel).
You: /skip
Bot: Ajoutez une description (optionnel).
You: Chemise en coton, taille M
Bot: 🎉 Produit ajouté avec succès !
```

### Scénario 2 : Mettre à jour le stock

```
Vous: /modifier
Bot: Voici vos produits :
1. T-shirt blanc (5 000 FCFA)
2. Chemise bleue (8 000 FCFA)
3. Pantalon noir (10 000 FCFA)
Entrez le numéro du produit à modifier :
You: 1
Bot: Que voulez-vous modifier ?
1. Prix
2. Stock
3. Description
Entrez le numéro :
You: 2
Bot: Stock actuel : 10
Entrez le nouveau stock :
You: 15
Bot: ✅ Stock mis à jour !
```

### Scénario 3 : Confirmer une commande

```
Vous: /commandes
Bot: 🛒 COMMANDES RÉCENTES
⏳ CMD-0001 - Amadou (15 000 FCFA)
   En attente de paiement
✅ CMD-0002 - Fatou (8 000 FCFA)
   Payée

Vous: /confirmer
Bot: Commandes en attente :
1. CMD-0001 - Amadou (15 000 FCFA)
Entrez le numéro de la commande à confirmer :
You: 1
Bot: ✅ Commande confirmée : CMD-0001
```

---

## 🆘 Dépannage

### Le bot ne répond pas

1. Vérifiez que vous envoyez le message au bon numéro
2. Vérifiez que votre numéro est configuré comme propriétaire
3. Contactez le support : +221778953918

### Commande non reconnue

1. Vérifiez que vous avez bien tapé `/` avant la commande
2. Vérifiez l'orthographe de la commande
3. Tapez `/help` pour voir la liste des commandes

### Erreur lors de l'ajout de produit

1. Vérifiez que le prix est un nombre valide
2. Vérifiez que le stock est un nombre positif
3. Tapez `/cancel` pour annuler et recommencer

---

## 📞 Support

- **WhatsApp** : +221778953918
- **Email** : support@feggjaay.shop
- **Horaires** : 24h/24, 7j/7

---

## 🎉 Avantages

Avec cette interface WhatsApp :

- ✅ **Pas besoin d'ordinateur** : Tout se fait sur votre téléphone
- ✅ **Simple et intuitif** : Pas besoin de connaissances techniques
- ✅ **Rapide** : Ajoutez un produit en moins de 2 minutes
- ✅ **Accessible partout** : Gérez votre boutique de n'importe où
- ✅ **24h/24** : Le bot est toujours disponible

---

## 📝 Résumé rapide

```
/ajouter    → Créer un produit
/modifier   → Modifier un produit
/supprimer  → Supprimer un produit
/stock      → Voir le stock
/commandes  → Voir les commandes
/confirmer  → Confirmer une commande
/annuler    → Annuler une commande
/stats      → Voir les statistiques
/menu       → Menu principal
/help       → Aide
/cancel     → Annuler l'action en cours
```

C'est tout ! Vous pouvez maintenant gérer votre boutique entièrement depuis WhatsApp. 🚀
