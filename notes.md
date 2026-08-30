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

## Source externe : zexk/bbtracker (2026-08-30)

Découverte tardive d'une documentation de rétro-ingénierie externe,
beaucoup plus poussée que notre travail manuel : dépôt GitHub
[zexk/bbtracker](https://github.com/zexk/bbtracker), fichier
`docs/mgs4_research.md`, et le projet qui le cite,
[InsaGram-it/mgs4-trainer](https://github.com/InsaGram-it/mgs4-trainer)
(trainer C# qui édite la mémoire du jeu en direct).

**Confirmation d'identité totale** : la clé XOR qu'ils documentent
(`kjdyeAiwoGsklcmfu93lwsENf7845ghw523if0ul7Pkj0hn9ejwksSVE8twf03te623DA842rc4oiQL`)
est exactement la nôtre (recouvrée indépendamment par vote majoritaire).
Même jeu, même build, même format de save. Leur méthode : lecture directe
de la mémoire du processus (`mgs4.exe`) pendant l'exécution, pas
uniquement du fichier de save — plus rapide et plus précis que notre
corrélation manuelle, mais la structure "run-stats" (`linkvarbuf`) qu'ils
documentent est **sérialisée telle quelle dans `MGS4.SAV`** aux mêmes
offsets, ce qui explique pourquoi presque tous nos offsets trouvés à la
main correspondent exactement aux leurs.

Cette source a permis de :
- confirmer quasiment tous nos offsets déjà trouvés, mot pour mot ;
- résoudre nos champs abandonnés ou mal compris (voir tableau ci-dessous
  et sections corrigées) ;
- donner l'offset direct de **Flashbacks vus** (`0x5a34`) sans avoir
  besoin de corrélation (le stat n'avait jamais bougé chez nous) ;
- révéler que plusieurs stats affichées comme une seule valeur en jeu sont
  en réalité la **somme de deux champs distincts** en mémoire ;
- documenter les tableaux d'armes/objets (`0x1d4` = 95 armes,
  `0x0526` = 99 objets, plus un tableau `0x0350` de 68 entrées non
  identifié), utiles pour un futur onglet armes/camo ;
- documenter les **40 formules d'emblèmes exactes** (seuils sur nos
  stats déjà connues) — un onglet Emblèmes est donc réalisable **sans
  aucune nouvelle donnée**, juste du calcul sur ce qu'on a déjà.

### Corrections apportées grâce à cette source

| Ancien | Nouveau | Explication |
|--------|---------|-------------|
| `ko_couteau` = `0x186` seul | `ko_couteau` = `0x184` (knife kills) + `0x186` (knife knockouts) | Le briefing affiche la somme des deux |
| `armes_objets_acquis` abandonné (hypothèse de décalage +4 infirmée) | `0x18e` (weapon pickups) + `0x190` (item pickups) | Confirmé exact : 118+18=136 correspond pile au dernier relevé connu |
| `temps_carton_frames` = `0x1bc` seul | `0x1b8` (boîte en carton) + `0x1bc` (baril) | Deux timers distincts sommés pour l'affichage "carton/baril" |
| `0x192` non identifié | **Hold-ups** | Nouvelle stat, jamais dans notre liste d'origine |
| Armes obtenues introuvable | Toujours pas résolu directement, mais probablement lié à `0x1d4`/tableau armes (à explorer) | Voir tableaux d'armes ci-dessous |
| — | `pages_magazine_tournees` = `0x19e` (Playboy) + `0x1a0` (magazine "Emotion") | Il existe deux magazines distincts, sommés pour l'affichage |
| — | `0x168` = temps de jeu total (u32, frames@60Hz) **dans MGS4.SAV lui-même** | On ne le savait que via METADATA.SAV avant ; gardé METADATA comme source d'affichage principale (plus stable, pas de variance de framerate) |
| — | `0x0034` = code de zone (7 caractères ASCII), `0x0054` = progression de scénario (→ Acte) | Permet d'afficher le lieu et l'Acte en cours, voir `STAGE_NAMES`/`act_from_progress()` |

### Tableaux d'armes/objets (pour un futur onglet armes/camo)

D'après cette source (mémoire du jeu, structure `linkvarbuf`, sérialisée
dans `MGS4.SAV`) :

| Offset | Contenu |
|--------|---------|
| `0x1d4` | `uint16[95]` — état de chaque arme, IDs 0 à 94 |
| `0x0350` | `uint16[68]` — tableau lié à l'inventaire, rôle non identifié par la source elle-même |
| `0x0526` | `uint16[99]` — état de chaque objet, IDs 0 à 98 |

"Weapon count scans IDs 1..73 and counts states 1 or 2" — la valeur de
chaque case n'est pas un simple booléen (0/1) mais peut valoir 0, 1 ou 2 ;
le sens exact de 1 vs 2 n'est pas documenté par la source (peut-être
"possédée" vs "équipée/personnalisée"). Il manque encore une table
ID→nom d'arme/objet — à construire par corrélation (débloquer une arme
connue, repérer quel index du tableau passe de 0 à 1/2) ou en cherchant
si la source ou une autre référence communautaire la publie.

### Emblèmes obtenus "à vie" (persistance retrouvée sans MGS4SYS.SAV)

L'utilisateur a fait remarquer à juste titre qu'une simple évaluation des
prédicats sur les stats de la partie **en cours** ne suffit pas : un
emblème obtenu lors d'une partie précédente doit continuer à s'afficher
comme obtenu même si la run actuelle ne le mériterait plus (ex: PIGEON,
0 kill, obtenu une fois puis on rejoue en tuant tout le monde).

Même la source externe (zexk/bbtracker) liste ça comme question ouverte
non résolue ("whether emblem predicates run only at results or maintain
cached state") — pas de réponse toute faite disponible.

**Solution trouvée sans avoir besoin de casser `MGS4SYS.SAV`** : chaque
slot de sauvegarde garde en mémoire les stats *au moment où cette partie a
été jouée*. Un slot qui a atteint la fin du jeu (`stage_code == "s00a10l"`,
"Épilogue : cimetière") a forcément déjà eu ses emblèmes évalués et
accordés avec exactement les stats qu'on peut lire dans son fichier. Il
suffit donc de :

1. Filtrer les slots réellement **terminés** (`is_completed_playthrough()`)
   — indispensable : un slot fraîchement commencé a des stats à 0 partout,
   ce qui le fait *qualifier à tort* pour plein d'emblèmes bas-seuil
   (BIG BOSS, PIGEON, SCORPION...) jamais réellement accordés puisque la
   partie n'a jamais été finie. Vérifié empiriquement : sans ce filtre,
   deux saves de test tout juste créées (Big Boss/Extreme) "débloquaient"
   à tort 8-10 emblèmes chacune.
2. Calculer les emblèmes éligibles sur *chacun* de ces slots terminés
   séparément, puis faire l'**union** de tous les IDs obtenus.

Validé sur les 2 vraies parties terminées de l'utilisateur : `903CC9`
(SOLID NORMAL) → {10,14,26,32} ; `919CFF` (LIQUID FACILE) → {5,6,7,8,14,32}.
Union = {5,6,7,8,10,14,26,32}, cohérent avec des runs propres et rapides
(peu d'alertes/continues, bon score CQC/headshots). Aucune fausse
qualification de save fraîche mélangée dedans.

Fonctions : `is_completed_playthrough(mgs4_sav_path)` et
`compute_lifetime_emblems(slot_paths)` dans `mgs4save.py`. L'interface
affiche 3 états par badge : obtenu à vie (doré plein), serait obtenu en
terminant la run actuelle maintenant mais pas encore obtenu ailleurs
(contour doré), verrouillé (gris).

**Limite connue** : si l'utilisateur a supprimé/écrasé une save qui avait
servi à obtenir un emblème (plus aucun slot disque ne prouve cette
completion), cet emblème disparaîtra de notre calcul même s'il est
toujours affiché comme obtenu par le jeu lui-même (qui a peut-être un
vrai registre persistant ailleurs, non retrouvé). Pas de solution pour
ce cas sans localiser le vrai stockage dans `MGS4SYS.SAV`.

### Petits compléments trouvés en creusant le dépôt bbtracker en detail

- Le dépôt contient aussi un script `scripts/inspect-mgs4-save.py` qui
  confirme `0x0000` comme contenant le numéro de partie (ils l'appellent
  "clear_count" en u32, mais en réalité c'est un u16 à `0x0000` — vérifié
  sur nos 3 slots réels : 903CC9→1, 919CFF→2, 91DA17→3, exactement comme
  `numero_partie` de METADATA.SAV. Le u16 juste après (`0x0002`) vaut
  toujours 1 chez nous, rôle inconnu).
- Le "footer" de 8 octets en fin de `MGS4.SAV`/`MGS4SYS.SAV` que la doc
  externe présente comme une chaîne fixe ("XPQT3Q5\0") est en fait une
  **donnée d'intégrité qui varie par fichier** (leur propre script plante
  sur nos saves avec "unsupported framing" à cause de ça) — cohérent avec
  ce qu'on avait nous-mêmes observé (zone qui change de façon chaotique
  dès qu'autre chose change dans le fichier). Ne pas copier leur script
  tel quel, notre `decrypt()` qui ignore le footer fonctionne mieux.
- Tableau `0x352` (u16[68], sentinelle `0xFFFF` = slot vide) : rôle encore
  incertain, semble être des slots d'équipement/loadout plutôt qu'un
  inventaire complet.

### Emblèmes (40, formules exactes disponibles)

Chaque emblème est un seuil sur des stats qu'on a déjà (alertes, kills,
continues, temps, CQC, headshots, etc.), évalué uniquement en fin de
partie par le jeu — mais rien n'empêche de calculer nous-mêmes
"qualifierait pour quel emblème avec l'état actuel" à tout moment, comme
le fait le trainer C# cité plus haut. Liste complète des 40 prédicats
disponible dans `docs/mgs4_research.md` du dépôt bbtracker (section
"Emblem predicates") — à recopier dans `mgs4save.py` le jour où l'onglet
Emblèmes est implémenté plutôt que dupliquée ici.

### METADATA.SAV, champs restants clarifiés

La source confirme aussi la structure de `METADATA.SAV` qu'on avait
déjà en grande partie déduite : `0x00` = 9× ID de ressource/stage hashés
(pas juste des timestamps comme on le supposait), `0x24` = version
(observée à 1), `0x28` = timestamp Unix de sauvegarde (confirme notre
hypothèse "horloge système"), `0x2c` = taille du corps de `MGS4.SAV`
(`0x8344`, cohérent avec ce qu'on a observé), `0x44` = copie de la
progression de scénario.

**Ambigu** : la source appelle `0x40` "save-menu progress resource index"
alors qu'on l'utilise comme "objets donnés aux milices" (`read_metadata_summary`).
Vérifié sur nos 3 échantillons de METADATA.SAV conservés : les trois valent 8,
mais les milices valaient déjà 8 sur toute cette période chez nous — donc ça
ne permet pas de trancher (coïncidence possible). Il faudrait un échantillon
de METADATA.SAV antérieur au moment où les milices sont passées de 3 à 8
pour vérifier si `0x40` suit ce changement ou reste sur une autre valeur.
À garder en tête : `objets_donnes_milices` dans `read_metadata_summary()`
pourrait être incorrect.

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
| 0x18c  | u16 | Poussées d'adrénaline (Combat High) | Haute | Transition exacte 0→2 unique dans le cluster de stats, resté à 0 sur 16 sauvegardes avant |
| 0x17a  | u16 | "Objets spéciaux : utilisé" (bitmask) | Haute | Affiché en jeu comme "utilisé" sans autre précision (pas de "oui/non" séparé par objet). Passé de 0 à **2** (pas 1) après usage de la Stealth Camo — confirme l'hypothèse de l'utilisateur : ce n'est pas un booléen mais un bitmask. Hypothèse : bit1 (valeur 2) = camo optique, bit0 (valeur 1) = bandana. Resté à 0 sur 17 sauvegardes avant. **Bandana non testé** (pas encore obtenu en jeu) — à confirmer : la valeur devrait passer à 3 si les deux objets sont utilisés. |

### Stats de temps continu (framerate variable, pas de seconde exacte)

En reprenant 5 relevés du briefing avec les temps exacts affichés (couché,
mur, accroupi, carton, temps de jeu) et en exigeant qu'un candidat reste
**exactement figé** aux intervalles où le vrai temps ne bougeait pas (pas
juste "proche"), 3 offsets ont été confirmés :

| Offset | Taille | Stat | Confiance | Notes |
|--------|--------|------|-----------|-------|
| 0x1a8  | u16 | Temps accroupi | Haute | Ratio ≈60.00 sur les 8 points de données disponibles (60.13, 60.13, 60.26, 60.03, 60.07, 60.07, 60.02, 60.01) — le plus précis de tous les stats de temps. Trouvé en réutilisant tout l'historique de la conversation (8 points/7 intervalles) plutôt que 2-5 points ; écarté à tort au tout début sur la base de 2 points seulement en le testant (à tort) pour "mur" |
| 0x1ac  | u16 | Temps allongé | Haute | Ratio delta-fichier/delta-affiché entre 54 et 62 sur 4 intervalles — pas un ×60 fixe, cohérent avec un framerate qui varie légèrement (~55-62 fps) plutôt qu'un jeu verrouillé à 60 fps |
| 0x1b4  | u16 | Temps contre un mur | Haute | Même signature de ratio que ci-dessus |
| 0x1bc  | u16 | Temps dans un carton/baril | Haute | Confirmé par un test isolé (~90s chronométrées, session sans aucun autre événement) : delta exact de 5434 sur ce seul champ, ratio ≈60.4, aucune ambiguïté |

Ces champs sont donc en **frames**, pas en secondes ni centisecondes, et le
framerate n'étant pas fixe, il n'y a pas de formule de conversion exacte
vers des secondes (diviser par ~58-60 donne un ordre de grandeur correct,
pas une valeur exacte).

**Résolu (avec réserve)** — "temps de jeu total" est dans `METADATA.SAV`
(129 octets, **non chiffré**, contrairement à `MGS4.SAV`), à l'offset
`0x34` (u32 LE), **en secondes directement** (pas en frames). Confirmé sur
2 points de données indépendants avec un écart constant de 24-28s par
rapport à la valeur affichée en jeu (3729 vs 3753s ; 5187 vs 5215s) — écart
probablement dû au fait que le compteur en jeu continue de tourner un peu
entre l'écriture du fichier et le moment où le joueur lit l'écran. Précision
donc approximative (+/-30s), mais l'ordre de grandeur et la tendance sont
fiables. `METADATA.SAV` contient aussi des copies non chiffrées d'autres
stats déjà connues (0x3c = Drebin actuel, 0x40 = objets donnés aux
milices), ce qui a aidé à confirmer que ce fichier reflète bien l'état du
jeu à la dernière sauvegarde. Son champ `0x28` est un timestamp système
(Unix, ~date réelle actuelle) qui avance au rythme du temps réel écoulé
entre sauvegardes, pas du gameplay — à ne pas confondre avec le playtime.

Fonction dédiée : `read_playtime_seconds(metadata_path)` dans
`mgs4save.py` (lecture directe, pas de déchiffrement XOR nécessaire).

### Difficulté et numéro de partie (METADATA.SAV, par slot)

Trouvés en comparant les 3 slots de sauvegarde réels, dont les valeurs sont
connues via le menu de chargement du jeu (capture d'écran de
l'utilisateur) :

| Slot | Difficulté affichée | Étoile (n° partie) |
|------|---------------------|---------------------|
| BLJM67001G6A903CC9 | SOLID NORMAL | ★01 |
| BLJM67001G6A919CFF | LIQUID FACILE | ★02 |
| BLJM67001G6A91DA17 | NAKED NORMAL | ★03 |

- `0x38` (u32) = **numéro de partie** (l'étoile). Correspondance exacte et
  sans ambiguïté sur les 3 slots (1, 2, 3). Confiance haute.
  Fonction : `read_playthrough_number(metadata_path)`.
- `0x30` (u32) = **score de difficulté interne**. Table complète, les 5
  niveaux officiels confirmés chacun sur un save dédié :

  | Score | Difficulté |
  |-------|------------|
  | 20 | LIQUID FACILE |
  | 30 | NAKED NORMAL |
  | 35 | SOLID NORMAL |
  | 40 | BIG BOSS DIFFICILE |
  | 50 | THE BOSS EXTRÊME |

  Pas un simple 0-4 mais pas non plus totalement arbitraire (pas +10, +5,
  +5, +10). Confiance haute, table complète dans `DIFFICULTY_NAMES`
  (`mgs4save.py`). Attention : un premier test avait mal étiqueté le save
  944D92 comme "BIG BOSS DIFFICILE" alors que c'était "THE BOSS EXTRÊME" —
  corrigé après vérification par l'utilisateur avec un save dédié
  (`BLJM67001G6A944EE9`) pour BIG BOSS DIFFICILE.

### MGS4SYS.SAV (fichier système, partagé entre tous les slots)

Chiffré avec la **même clé XOR** que `MGS4.SAV`. Contient une grande zone
(0x40-0xc7 environ) qui ressemble à une liste d'IDs d'entrées débloquées
dans la Database (valeurs `0x8000xxxx`), et une autre zone (0xe0-0x158)
qui ressemble à des bitmasks (puissances de 2) — probablement des
unlocks de contenu bonus. Pas creusé en détail, pas nécessaire pour les
stats de jeu visées par ce projet.

### Toujours non identifié

- **Armes obtenues** (le stat "55 puis 57" du briefing, distinct de
  `armes_objets_acquis`) : toujours pas résolu directement. Probablement
  lié au tableau d'armes `0x1d4` (voir section source externe ci-dessus) —
  la doc externe mentionne "count acquired weapon types" comme une
  fonction native séparée qui scanne le tableau plutôt qu'un scalaire
  stocké, cohérent avec notre observation qu'aucun entier brut ne
  correspondait. À reprendre en scannant `0x1d4` (95 × u16) et en comptant
  les entrées à l'état 1 ou 2 le jour où l'onglet armes est construit.
- `0x0350` (tableau de 68 × u16) : rôle non identifié, même par la source
  externe.

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
- 0x1a4, 0x1b0 (candidats initiaux écartés pour mur) : **faux candidats**,
  jamais résolus par notre propre corrélation. La source externe ne les
  documente pas non plus (pas dans la table `linkvarbuf`) — probablement
  des données de mission/checkpoint sans rapport avec les stats de Play
  Data.
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
