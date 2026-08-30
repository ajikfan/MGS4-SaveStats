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

### Stats de temps continu (framerate variable, pas de seconde exacte)

En reprenant 5 relevés du briefing avec les temps exacts affichés (couché,
mur, accroupi, carton, temps de jeu) et en exigeant qu'un candidat reste
**exactement figé** aux intervalles où le vrai temps ne bougeait pas (pas
juste "proche"), 3 offsets ont été confirmés :

| Offset | Taille | Stat | Confiance | Notes |
|--------|--------|------|-----------|-------|
| 0x1ac  | u16 | Temps allongé | Haute | Ratio delta-fichier/delta-affiché entre 54 et 62 sur 4 intervalles — pas un ×60 fixe, cohérent avec un framerate qui varie légèrement (~55-62 fps) plutôt qu'un jeu verrouillé à 60 fps |
| 0x1b4  | u16 | Temps contre un mur | Haute | Même signature de ratio que ci-dessus |
| 0x1bc  | u16 | Temps dans un carton/baril | Haute | Confirmé par un test isolé (~90s chronométrées, session sans aucun autre événement) : delta exact de 5434 sur ce seul champ, ratio ≈60.4, aucune ambiguïté |

Ces champs sont donc en **frames**, pas en secondes ni centisecondes, et le
framerate n'étant pas fixe, il n'y a pas de formule de conversion exacte
vers des secondes (diviser par ~58-60 donne un ordre de grandeur correct,
pas une valeur exacte).

**Toujours introuvables** : temps de jeu total et temps accroupi. Recherche
exhaustive sur tout le fichier (u16 et u32, tolérance de ratio 30%) sans
succès. Hypothèses : ce sont des valeurs calculées autrement (pas un simple
compteur incrémental), ou pour l'accroupi spécifiquement, le stat affiché
en jeu regroupe peut-être plusieurs comportements (marche accroupie +
immobile accroupi) que le fichier ne compte pas de la même façon, cassant
toute relation linéaire simple.

Pour "temps de jeu total" : indice intéressant, sa valeur a **diminué** de
2 secondes après une sauvegarde manuelle sans changement de zone (observé
en jeu) — un vrai total ne devrait jamais diminuer. `METADATA.SAV` (129
octets) n'est **pas chiffré** (contrairement à `MGS4.SAV`) et contient une
série de timestamps/compteurs qui eux se mettent à jour à chaque
sauvegarde manuelle — le temps de jeu total vient probablement de là plutôt
que de `MGS4.SAV`. Pas encore corrélé (un seul échantillon capturé pour
l'instant, `samples/METADATA_*.sav`). Basse priorité, à reprendre si
besoin avec plusieurs échantillons de METADATA.SAV horodatés.

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
- 0x1a4, 0x1a8, 0x1b0 (candidats initiaux pour accroupi/mur) : **faux
  candidats**, écartés par le protocole strict (voir section stats de temps
  ci-dessus pour les bons offsets : 0x1ac, 0x1b4, 0x1bc).
- Combat High, Flashbacks : toujours pas localisés (valeurs inchangées
  entre les sessions testées jusqu'ici, donc rien à corréler).
- **Leçon apprise (affinée)** : les compteurs d'**événements** (kills,
  alertes, continue, CQC, roulades...) se flushent dans `MGS4.SAV` à
  **chaque sauvegarde manuelle**. Seuls les compteurs de **temps continu**
  (accroupi/couché/mur/carton) n'apparaissent qu'au moment d'un vrai
  changement de zone/checkpoint — probablement parce qu'ils sont accumulés
  en mémoire pendant la zone et seulement reversés au total permanent au
  déchargement de la zone. Pour isoler un stat de temps proprement : une
  seule action chronométrée, puis changement de zone immédiat sans rien
  faire d'autre entre les deux.

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
