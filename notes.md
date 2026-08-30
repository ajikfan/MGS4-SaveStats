# Notes de rétro-ingénierie

## Clé XOR recouvrée (par vote majoritaire sur octets nuls)

```
6b6a6479654169776f47736b6c636d667539336c7773454e6637383435676877353233696630756c37506b6a30686e39656a776b73535645387477663033746536323344413834327263346f69514c
```

Longueur : 79 octets. Recouvrée par vote majoritaire (le plaintext est
majoritairement nul sur les zones inutilisées du fichier). Confirmée sur
2 saves différentes (~71-82% de zéros après déchiffrement dans la zone
0x000-0x460). Probablement encore légèrement fausse sur quelques octets
(là où la majorité du plaintext n'est pas nulle) — à affiner au fur et à
mesure.

Pas de signature cryptographique façon PS3 (pas de clé console/PSN côté PC),
donc pas de "resigning" à prévoir. Un simple checksum anti-corruption est
possible mais pas encore localisé.

## Zone de stats candidate : 0x000 - 0x460

Identifiée par diff entre 3 saves prises à des instants différents (28/08
16h32, 28/08 20h50, 30/08 11h04) — nombreux petits runs de 1-10 octets qui
changent entre chaque save, concentrés dans cette zone. Sur une save fraîche
de New Game+, cette zone est ~71% de zéros après déchiffrement.

Le reste du fichier (0x460 à 33613) n'a pas encore été étudié en détail.

## Stats cibles

Liste fournie par l'utilisateur, à localiser une par une par corrélation
(valeur connue affichée en jeu → recherche de cet entier dans le fichier
déchiffré, en testant int8/16/32, little/big-endian).

Compteurs simples (probablement faciles à isoler en premier) :
- Total Play Time
- Continues
- Alert Phases
- Total Kills
- LIFE Recovery Items Used
- Weapon Types Acquired
- Flashbacks Viewed
- Special Items (utilisation)
- CQC Uses (holds/grabs, étranglements, hold-ups, fouilles)
- Headshots
- Knife Kills/Knockouts
- Combat Highs
- Weapons/Items Acquired (total)
- Total Drebin Points (gagnés via ventes)
- Current Drebin Points (solde actuel)
- Compliments/remerciements des miliciens
- Objets donnés aux miliciens
- Pages Playboy regardées
- Utilisation Stealth Camo / Bandana
- Utilisation seringue / Scanning Plug
- Armes abandonnées récupérées
- Difficulté de complétion

Compteurs de temps cumulé (probablement en secondes, plus dur à valider
précisément sans chrono) :
- Wall Press Time
- Crawling Time
- Crouch Walking Time
- Time in Cardboard Box/Drum

Compteurs d'actions physiques :
- Sideway Rolls
- Forward Rolls

## Offsets identifiés

| Offset | Taille | Encodage | Stat | Confiance | Notes |
|--------|--------|----------|------|-----------|-------|
| 0x1c0  | 4 octets | u32 LE | Drebin actuel | Haute | Correspondance unique dans tout le fichier (952201) |
| 0x1c4  | 4 octets | u32 LE | Drebin total (ventes) | Haute | Correspondance unique dans tout le fichier (769826) |
| 0x186  | 4 octets | u32 LE | KO au couteau | Haute | Confirmé sur 2 sessions cohérentes (1→3 puis inchangé sans nouveau KO) |
| 0x18a  | 4 octets | u32 LE | Roulades en avant | Haute | Correspondance unique (=6) |
| 0x178  | 4 octets | u32 LE | Kill **ou** Headshot | Moyenne | Passé de 0 à 3 en même temps que 0x182 ; les 2 stats valaient 3 simultanément (probablement tous les kills étaient des headshots). Ambigu, à trancher avec un kill sans headshot. |
| 0x182  | 4 octets | u32 LE | Kill **ou** Headshot | Moyenne | Voir ci-dessus |

### Pistes non confirmées (faux départs à éviter)

- `0x1c2` : **faux positif**. C'est un octet interne du u32 de Drebin actuel
  (952201 = 0x000E86C9, l'octet du milieu vaut 0x0E = 14 par coïncidence).
  Ne pas chercher une valeur numérique connue sans vérifier qu'elle ne tombe
  pas dans l'intervalle d'un champ déjà identifié.
- "Armes obtenues" (55) et "Armes/objets acquis" (14) : recherche par valeur
  peu fiable ici — il existe une zone vers 0x820-0x880 qui ressemble à une
  table d'IDs d'objets/armes (valeurs séquentielles 0x27, 0x28, 0x29...),
  qui génère de nombreux faux positifs pour des petites valeurs comme 14 ou
  55. Nécessite une approche différentielle (avant/après obtention d'une
  arme précise) plutôt qu'une recherche de valeur absolue.
- Stats de temps (Wall Press, Crawling, Crouch Walking, Cardboard/Drum),
  CQC, Continue, Alerte, Soins, Roulade latérale, Combat High, Flashbacks :
  pas encore localisés avec certitude — valeur 0 ou 1 trop fréquente dans le
  fichier pour une recherche fiable sans plusieurs points de données
  différentiels propres.
- **Leçon apprise** : ces compteurs ne se mettent à jour qu'au moment d'un
  vrai changement de zone/checkpoint (chargement), pas à chaque sauvegarde
  manuelle. Un test isolé (une seule action entre deux checkpoints) donne
  des résultats bien plus propres qu'un enchaînement de plusieurs actions.

## Méthode de corrélation

1. Le joueur sauvegarde à un point A, relève les valeurs affichées à l'écran
   de briefing (kills, alertes, continues, Drebin points, temps de jeu).
2. Copier `MGS4.SAV` vers `samples/` avec un nom horodaté (ne jamais
   travailler sur le fichier original du jeu).
3. Le joueur continue à jouer un peu, sauvegarde à un point B, relève à
   nouveau les valeurs.
4. Déchiffrer A et B avec la clé XOR, chercher les valeurs connues comme
   entiers à divers offsets, confirmer par la variation attendue entre A et B.

## Samples de saves conservés

Voir `samples/` (copies horodatées, non versionnées dans git — voir
`.gitignore`, ce sont des données de save personnelles).
