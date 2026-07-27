# TODO LIST TARTINE

## 🟢 Quick wins (à faire en premier)

### Épicerie de la semaine
- Ex: "Maxi! Le plus gros nombre de rabais et la plus grosse somme cette semaine"
- Historique des meilleures épiceries (par montant total en rabais)
- Calculable directement avec les données déjà en DB (discount + stores)

### Notifications sur favoris
- Notification spéciale quand un item favori se retrouve en rabais
- Réutilise : système de notifications existant + job de téléchargement des circulaires + matching catalogue/rabais
- Ajouter table `favorites (idClient, idCatalog)`
- Hook dans `triggerDownloadFlyers()` pour checker les favoris après chaque nouveau téléchargement

---

## 🟡 Coeur du produit (priorité après les quick wins)

### Système de liste d'épicerie
- Pouvoir rentrer toute sa liste d'épicerie
- Bouton "J'ai utilisé cette liste" → ajoute à une page d'historique des listes utilisées
- Page qui montre combien économisé au total avec toutes ses listes
- Pouvoir ajouter des plats/recettes à sa liste (auto-ajoute les ingrédients)
  - Attention: dédupliquer/additionner les quantités si 2 recettes utilisent le même ingrédient
- **À clarifier avant de coder**: comment on définit "économisé"? (différence juste sur items en rabais, ou vs prix normal général?)

---

## 🟠 Prometteur mais plus complexe

### Marque des produits
- Ajouter la marque quand on match les rabais (préciser marque spécifique ou "n'importe laquelle")
- Va falloir un matching de marque en plus du matching de produit
- **Risque**: extraction fiable de la marque depuis le texte scrapé (données pas toujours propres)
- Suggestion: commencer par une colonne `brand` nullable dans `catalog`, remplir manuellement pour les produits populaires avant d'automatiser

---

## 🔴 Gros morceau (à découper, garder pour la fin)

### Système d'amis et profil public
- Publier/partager des recettes
- Publier/partager des listes d'épicerie (avec épiceries fréquentées)
- Recettes publiques recommandées, possibilité de les ajouter à sa propre liste
- **Ça inclut en fait 3 projets séparés**: graphe social (amis/follow), visibilité publique + feed de découverte, partage de listes
- Penser à la modération dès le départ (flag "reported" sur recettes publiques)
- **MVP suggéré**: commencer par juste "partager une recette via un lien" (`/recipes/shared/<uuid>`) sans système d'amis complet, valider l'intérêt avant d'investir dans le graphe social

---

## 💰 Monétisation — donner un incitatif clair à passer Premium

Principe: toujours montrer un **chiffre en dollars réel et vérifiable**, jamais juste une liste de features. Les gens réagissent à "t'as perdu X$" bien plus qu'à "débloquez plus de features".

### Compteur d'économies manquées
- User gratuit = alertes en digest hebdomadaire (jeudi)
- User premium = alerte immédiate quand un favori tombe en rabais
- Afficher: "Tu as manqué X$ cette semaine parce que t'as pas été alerté à temps"

### Preview partiel + flou sur les recommandations
- Dashboard recettes en rabais: montrer les 3 meilleures gratuitement
- "+ 12 autres recettes en rabais cette semaine → Passer Premium pour voir"
- Le nombre doit être réel, calculé sur toutes les recettes de l'utilisateur (pas juste les 6 premières)

### Optimisation multi-épiceries (feature premium)
- Calculer l'itinéraire optimal entre plusieurs épiceries pour maximiser les économies sur une liste
- Ex: "Itinéraire optimal = 34$ d'économies vs 21$ en restant juste à une épicerie"

### Résumé mensuel avec comparaison sociale
- Email/notif fin de mois: "T'as économisé 47$ ce mois-ci. Les users Premium ont économisé en moyenne 71$."
- Nécessite le système de liste d'épicerie (voir plus haut) pour calculer les vraies économies
- Important: la moyenne affichée doit être réelle, pas inventée

### Reformuler le message de limite de recettes
- Actuel: "Limite atteinte, pendant le développement on limite le nombre de recettes" (sonne technique/temporaire)
- Mieux: cadrer autour de la valeur perdue, ex. "X de tes recettes auraient pu économiser plus avec le matching prioritaire Premium"

### ⚠️ Règle d'or
Tous les chiffres affichés (économies, moyennes, comparaisons) doivent être réels et calculables à partir des vraies données — jamais inventés ou gonflés. Perdre la confiance des utilisateurs sur ces chiffres tue la crédibilité du produit.

---

## Ordre de priorité suggéré
1. Épicerie de la semaine (quick win)
2. Notifications favoris (quick win, réutilise l'existant)
3. Liste d'épicerie + tracking d'économies (coeur du produit)
4. Compteur d'économies manquées (monétisation, branché sur #2)
5. Marque des produits (commencer manuel)
6. Social/amis (commencer par MVP de partage par lien)