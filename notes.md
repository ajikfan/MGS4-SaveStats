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

Tous les champs de la zone 0x150-0x1c8 sont en réalité des **u16** (2 octets),
pas des u32 comme supposé au début — l'erreur venait de champs voisins à 0
qui masquaient la vraie largeur. Attention en lisant du code plus ancien.

| Offset | Taille | Stat | Confiance | Notes |
|--------|--------|------|-----------|-------|
| 0x16e  | u16 | Alertes | Haute | Transition exacte 1→4 unique dans tout le fichier, historique monotone cohérent sur 8 saves |
| 0x178  | u16 | Total Kill | Haute | Delta exact +6 (3→9) confirmé pendant que Headshot restait figé |
| 0x182  | u16 | Headshots | Haute | Resté à 3 alors que Total Kill montait à 9 → désambiguïsé de 0x178 |
| 0x186  | u16 | KO au couteau | Haute | Historique cohérent sur 3 sessions (0→1→3→3→3) |
| 0x188  | u16 | Roulades de côté | Haute | 0→7, confirmé par élimination face à 0x18a |
| 0x18a  | u16 | Roulades en avant | Haute | Deux deltas exacts indépendants (0→6 puis 6→13) |
| 0x19e  | u16 | Pages de magazine tournées | Haute | Transition exacte 0→8 unique, **stat non affichée dans le briefing en jeu** |
| 0x0ae0 | u16 | Objets de soin utilisés | Haute | Transition exacte 2→5 unique, historique cohérent |
| 0x1c0  | u32 | Drebin actuel | Haute | Correspondance unique dans tout le fichier |
| 0x1c4  | u32 | Drebin total (ventes) | Haute | Correspondance unique dans tout le fichier |
| 0x158  | u16 | Continue | Haute | Transition exacte 1→4 unique dans tout le fichier, historique cohérent (0 pendant 7 saves, puis 1, puis 4) |
| 0x180  | u16 | CQC | Haute | Delta exact +14 (1→15) confirmé pendant que Continue augmentait différemment (+3) — désambiguïsé |
| 0x198  | u16 | Objets donnés aux milices/mercenaires | Haute | Transition exacte 0→3 unique dans le cluster de stats, resté à 0 sur 9 sauvegardes avant |

### Toujours non identifié

- `0x192` : passé de 0 à 1 en même temps que Continue/CQC la première fois,
  puis n'a plus bougé alors que Continue et CQC continuaient d'augmenter.
  Ne correspond à aucune stat de la liste connue pour l'instant.
- **Armes/objets acquis** (`0x18e`) : **hypothèse infirmée**. Le décalage
  constant "+4" qui collait sur 2 petits deltas (rounds avec delta ≤4) ne
  tient plus sur un delta plus grand (delta brut 13 pour delta affiché 17).
  Le champ suit grossièrement la même tendance mais n'est probablement pas
  le bon, ou pas une simple relation linéaire. Retiré de `STATS`. À
  rechercher à nouveau par transition exacte (valeur affichée avant/après,
  sans offset supposé) sur le prochain changement.
- **Armes obtenues** (55 puis 57, delta+2) : introuvable comme entier brut
  sous aucun format (B/H/I, LE/BE) dans tout le fichier. Hypothèse : ce
  n'est pas un compteur stocké mais une valeur **calculée** — par exemple
  le nombre d'entrées valides dans la table d'objets/armes repérée vers
  0x0820-0x0880 (ou une autre table similaire), plutôt qu'un scalaire
  dédié. Nécessiterait de cartographier cette table plus précisément
  (structure des entrées, marqueur "vide" vs "occupé") pour la retrouver.

### Pistes non confirmées (faux départs à éviter)

- `0x1c2` : **faux positif**. C'est un octet interne du u32 de Drebin actuel
  (952201 = 0x000E86C9, l'octet du milieu vaut 0x0E = 14 par coïncidence).
  Ne pas chercher une valeur numérique connue sans vérifier qu'elle ne tombe
  pas dans l'intervalle d'un champ déjà identifié.
- "Armes obtenues" (55) : recherche par valeur peu fiable — il existe une
  zone vers 0x820-0x880 qui ressemble à une table d'IDs d'objets/armes
  (valeurs séquentielles 0x27, 0x28, 0x29...), qui génère de nombreux faux
  positifs pour des petites valeurs. Nécessite une approche différentielle
  (avant/après obtention d'une arme précise) plutôt qu'une recherche de
  valeur absolue. Vu que la valeur est restée à 55 sur 2 sauvegardes de
  suite malgré de nouvelles armes obtenues, ce n'est peut-être même pas un
  compteur qui bouge souvent (ex: "types d'armes distincts", pas "armes
  obtenues").
- Stats de temps (Wall Press, Crawling, Crouch Walking, Cardboard/Drum) :
  l'hypothèse "stockage en frames à 60 fps" (candidats 0x1a4, 0x1a8, 0x1ac,
  0x1b0, 0x1b4) est **infirmée** — sur un 2e round de données, le ratio
  delta-fichier/delta-affiché varie trop (60.1 puis 63.75 pour un même
  candidat) et un candidat (0x1b0) a changé alors que le temps contre le mur
  affiché, lui, n'avait pas bougé du tout. Ces offsets ne sont probablement
  pas les bons, ou ne sont pas de simples compteurs linéaires. À reprendre
  avec un protocole strict : une seule action de mouvement isolée par
  checkpoint, chronométrée précisément (pas une estimation "+/-").
- Combat High, Flashbacks : toujours pas localisés (valeurs inchangées
  entre les sessions testées jusqu'ici, donc rien à corréler).
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
