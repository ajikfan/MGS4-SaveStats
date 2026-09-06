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
chaque case n'est pas un simple booléen (0/1) mais peut valoir 0, 1 ou 2.

**Sens de 1 vs 2 CONFIRMÉ (2026-09-06)** : l'utilisateur précise que
certaines armes ramassées sur le terrain sont verrouillées (état 1) et
nécessitent un déverrouillage payant via Drebin avant de pouvoir être
utilisées ; une fois déverrouillées, elles passent à l'état 2. Ce n'est
donc pas "possédée" vs "équipée/personnalisée" comme supposé au départ.
L'appli traite actuellement les deux comme simplement "possédée"
(`owned=True`), sans distinguer verrouillée/déverrouillée dans
l'affichage - à revoir si un jour on veut refléter cette nuance. Table
ID→nom d'arme/objet toujours à construire par corrélation (débloquer une
arme connue, repérer quel index du tableau passe de 0 à 1/2).

### Emblèmes obtenus "à vie" — RÉSOLU : vrai bitmask trouvé à 0x18

L'utilisateur a fait remarquer à juste titre qu'une simple évaluation des
prédicats sur les stats de la partie **en cours** ne suffit pas : un
emblème obtenu lors d'une partie précédente doit continuer à s'afficher
comme obtenu même si la run actuelle ne le mériterait plus (ex: PIGEON,
0 kill, obtenu une fois puis on rejoue en tuant tout le monde).

Même la source externe (zexk/bbtracker) liste ça comme question ouverte
non résolue ("whether emblem predicates run only at results or maintain
cached state"). Premier essai (union des prédicats évalués sur les slots
**terminés** uniquement) donnait 8 emblèmes pour l'utilisateur, mais il a
vérifié en jeu qu'il en avait **22** — écart trop grand pour être expliqué
par de simples parties dont le fichier de save aurait été écrasé.

**Méthode gagnante** : l'utilisateur a donné la liste exacte de ses 22
emblèmes obtenus (par numéro). À partir de cette liste, calcul d'un
bitmask théorique de 5 octets (40 bits, bit0=embleme1, LSB en premier) et
recherche de cette séquence exacte d'octets dans le fichier déchiffré —
**trouvée du premier coup, correspondance parfaite, à l'offset `0x18` de
`MGS4.SAV`**. Confirmé sur les 5 slots disponibles, avec une progression
chronologique cohérente :

| Slot | Bitmask (hex) | Emblèmes |
|------|---------------|----------|
| `903CC9` (1ère partie terminée) | `0022008200` | {10,14,26,32} |
| `919CFF` (2e partie terminée) | `f022008200` | {5,6,7,8,10,14,26,32} |
| `944D92`/`944EE9` (saves de test créées après) | `f022008200` | identique à 919CFF — copié tel quel à la création du slot |
| `91DA17` (partie en cours, la plus avancée) | `f032f6fbc0` | les 22 emblèmes |

Le registre est bien **cumulatif** (chaque nouvelle partie ajoute des bits,
n'en retire jamais) et **copié dans chaque nouveau slot de sauvegarde** au
moment de sa création (les 2 slots de test ont hérité du bitmask de
919CFF telle quelle). Fait intéressant : `91DA17` a des emblèmes en plus
qui ne sont accordés ni par 903CC9 ni par 919CFF pris isolément ni par ses
propres stats en tant que partie non terminée — ça montre que le jeu
accorde bien des emblèmes **en cours de route** (probablement à chaque
écran de bilan d'Acte), pas seulement à l'écran de résultats final comme
supposé au départ.

Fonctions dans `mgs4save.py` : `read_obtained_emblems(mgs4_sav_path)`
(lit directement le bitmask, aucun calcul de prédicat nécessaire) et
`compute_lifetime_emblems(slot_paths)` (union sur tous les slots, par
sécurité). L'interface affiche 3 états par badge : obtenu à vie (doré
plein, lu depuis le bitmask), serait *en plus* obtenu en terminant la run
actuelle maintenant (contour doré, calculé via les prédicats sur les
stats live), verrouillé (gris).

Les fonctions `is_completed_playthrough()` / filtrage par `stage_code`
utilisées dans la version précédente ne sont plus nécessaires pour cette
partie-là (gardées dans `read_progress_info()` pour l'affichage
lieu/Acte, qui reste utile par ailleurs).

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
- `0x0350` (tableau de 68 × u16) : **rôle identifié (2026-08-31)**, voir
  section dédiée plus bas ("Tableau 0x352 : munitions par emplacement
  d'équipement").

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

## Objets de soin (recovery items), correction Pentazemine/Compress (2026-08-31)

Ces objets (0x00-0x04 du tableau `0x0526`) n'ont jamais été formalisés en
dict dans le code (pas de tab dédié), juste mentionnés informellement plus
tôt : `0x00`=Rations, `0x01`=Noodles, `0x02`=Regain 24G, `0x03`=Pentazemin,
`0x04`=Compress (ordre venant de la table Cheat Engine communautaire).

Test isolé sur la partie fraîche : l'utilisateur obtient de la Pentazémine,
et c'est `item[0x04]` qui passe de verrouillé à obtenu - pas `item[0x03]`.

**Mise à jour** : un 2e test isolé (Regain 24G obtenu seul) montre que
c'est `item[0x03]`, pas `item[0x02]`, qui passe de verrouillé à obtenu.
Donc ce n'est pas un simple échange 2-par-2 (Pentazemin/Compress) comme
supposé d'abord, mais un **décalage d'un cran** à partir de la position 2 :
`0x03`=Regain 24G (au lieu de `0x02`), `0x04`=Pentazemin (au lieu de
`0x03`). Ça décale aussi potentiellement `0x05`, jusque-là étiqueté
"Solid Eye" par la table d'origine mais dont les valeurs n'ont jamais
vraiment collé (ex: 15 observé sur une save, une valeur qui bouge aussi
lors d'événements sans rapport avec Solid Eye) - avec ce décalage, ce
serait plutôt **Compress** (objet de soin consommable, donc une quantité
qui varie, ce qui explique bien mieux ces valeurs que "Solid Eye" qui est
un équipement fixe sans raison de fluctuer). Emplacement réel de Solid
Eye (si tant est qu'il y en ait un - voir le précédent similaire
d'Octocamo/FaceCamo qui n'ont pas de flag du tout) encore à déterminer.
À corriger/creuser si/quand un tab "objets de soin" est construit.

## Liste officielle des 70 armes trouvée (2026-09-01)

L'utilisateur a pointé vers https://metalgear.fandom.com/wiki/Metal_Gear_Solid_4_weapons,
qui confirme texto **"There are a total of 70 weapons in the game"** - pas
95. Ça valide une intuition qu'on avait déjà : notre tableau `0x1d4` (95
cases) contient un mélange d'armes réelles ET d'autres choses (munitions/
pièces détachées comme les 3 sous-entrées du RPG-7, le Magazine Playboy
classé comme "arme"...) - cohérent avec ~70 vraies armes + ~25 entrées de
customisation/objets annexes.

Le fetch direct de cette page a échoué via l'outil WebFetch (402, comme
tous les Fandom), mais un `curl` direct (avec un faux user-agent
navigateur) a fonctionné - à retenter si WebFetch bloque à nouveau sur ce
domaine.

Noms d'armes officiels extraits de la page (liste brute des titres de
liens, pas encore triée par catégorie ni recoupée avec nos ID) : AK-102,
AN94, Claymore mine, DSR-1, Desert Eagle, FAL, FGM-148 Javelin,
Five-seveN, G3A3, GP30, GSR, Glock 18, Grenade, HK21E, M14 EBR, M1911A1,
M4 Custom, M60E4, M72A3, M82A2, M870, MAC-10, MGL-140, MP5SD2, MP7,
Makarov PMM, Mk.17, Mk.46 MOD1, Mosin-Nagant, **P90** (confirme donc bien
exister sous ce nom, toujours pas d'ID trouve - voir plus haut la piste
"chargeur vide" non tranchee), PK/PKM, PP-19 Bizon, PSS, Patriot (arme
bonus, emblème BIG BOSS), Petrol bomb (= notre "Cocktail Molotov"),
Plastic explosive (= notre "C4"), RPG-7, Rail gun, Ruger MK. 2 Pistol (=
notre "MK.2 Pistol"), SOCOM, SVD, Saiga-12, Sleep Gas Satchel (= notre
"Mine à gaz somnifère"), Smoke Grenade (= nos "Grenades fumigènes"),
Springfield Operator (= notre "Operator"), Stinger, Stun Grenade (= nos
"Grenades paralysantes"), Tanegashima, Thor .45-70 (déjà en confiance
basse, bundle Otacon), **Twin Barrel** (corrige : on avait "Double
Barrel", nom officiel confirmé par la page - corrigé dans le code), Type
17 Mauser, VSS, White phosphorus grenade (= nos "Grenades au phosphore
blanc"), XM25 CDTE, XM8.

Utile pour la suite : liste de référence à garder sous la main pour
reconnaître un nom d'arme donné par l'utilisateur et savoir s'il
correspond à une entrée déjà connue ou une toute nouvelle à chercher.

## Recherche noms d'armes / conditions de déblocage (2026-08-30)

Tentative rapide de trouver une table ID→nom d'arme complète prête à
l'emploi pour le tableau `0x1d4` (95 armes), suite à la demande de
l'utilisateur. Pistes explorées, toutes des impasses pour l'instant :

- Table Cheat Engine (`MGS4.CT`) : section armes explicitement marquée
  "WIP" par son auteur, seulement 5 noms sur 95 (déjà dans `WEAPON_NAMES`).
- Google Sheet "My Other Tables" citée dans le CT (auteur RMLSNK) : juste
  un suivi de statut de ses tables ("MGS4 : In progress"), aucune donnée
  d'armes.
- Dépôt `zexk/bbtracker` : documente explicitement qu'il **exclut**
  volontairement les tableaux armes/objets de son offset-list ("per-slot ID
  tables rather than simple scalar stats").
- Dépôt `InsaGram-it/mgs4-trainer` (C#) : même choix, `Constants.cs` ne
  contient aucune table d'armes/objets, seulement les stats scalaires.
- Wikis (Fandom Metal Gear Wiki, StrategyWiki, IMFDB, GameFAQs) : tous
  renvoient 402/403 au fetch direct (déjà documenté plus haut dans ce
  fichier). La recherche web (résumé IA, pas de fetch direct) donne des
  bribes utiles mais pas de liste exhaustive dans l'ordre d'un ID
  numérique - impossible d'en tirer une correspondance ID→nom fiable.

**Conclusion** : aucune ressource externe ne donne une table ID→nom
complète et alignée sur NOTRE tableau compact (0x1d4). Contrairement au
tableau d'objets (où la table CE s'est alignée par chance/conception avec
le tableau du fichier de save), rien d'équivalent n'existe pour les armes.
La seule voie fiable reste la corrélation manuelle utilisée pour toutes les
autres stats de ce projet : ramasser une arme précise et connue, comparer
le tableau `0x1d4` avant/après pour repérer quel index a changé. Travail
remis à plus tard par l'utilisateur.

### Conditions de déblocage trouvées (recherche web, à vérifier avant usage)

Utile pour plus tard, mais **non vérifié par nous** (résumé IA de
recherche web, sources secondaires) :

- **Solar Gun** : débloqué après avoir terminé une partie avec les 5
  statuettes Beauty and the Beast en inventaire (chaque statuette =
  vaincre l'unité correspondante en non-létal, viser la jauge de psychisme
  plutôt que la santé). Cohérent avec le commentaire de l'utilisateur.
- **Patriot** : débloqué via l'emblème BIG BOSS (ou un mot de passe de
  triche `pkhhnwhsjt`, hors-scope pour ce projet). Cohérent avec le
  commentaire de l'utilisateur.
- **Desert Eagle Long Barrel** : débloqué via l'emblème FOX.
- **Rail Gun (MK.3)** : obtenu automatiquement par progression d'histoire
  (Acte 4, après le combat contre Crying Wolf).
- **Tanegashima** : achetable chez Drebin (très cher, jusqu'à 1 000 000
  DP), pas un déblocage par emblème/collection.

Si on reprend ce chantier plus tard : commencer par ces armes à
condition "spéciale" (emblème/collection) plutôt que par les ~90 armes
"normales" trouvables en jeu, car ce sont probablement celles qui
intéressent le plus l'utilisateur et elles sont en nombre restreint donc
plus faciles à corréler une par une.

## Facecamos / Tenues séparés du tableau Camouflages (2026-08-31)

Suite à une demande de l'utilisateur, scission de `CAMO_NAMES` (qui
mélangeait à tort camouflages, camo facial de base et costumes) en trois
groupes distincts, avec des noms et un ordre confirmés par une source
externe indépendante : le site fan francophone **Metal Gear Generation**
(http://metalgeargeneration.free.fr/mgs4/camos.php, page dédiée aux
camouflages de MGS4). Cette page liste explicitement 3 catégories : Facecamos,
Tenues, Camouflages spéciaux — avec pour chaque item son nom exact et sa
condition de déblocage en jeu.

- `FACECAMO_NAMES` (14 entrées, ID 0x14-0x2b) : FaceCamo de base, Jeune
  Snake (+ variante bandana), Facecamo MGS1, Roy Campbell, Otacon,
  Raiden A/B, Drebin, les 4 Beauty (Laughing/Raging/Crying/Screaming),
  Big Boss.
- `OUTFIT_NAMES` (5 entrées, ID 0x19-0x1d) : déguisements Moyen-Orient/
  Amérique du Sud/Europe de l'Est, costume d'Altaïr, costume de Snake.

Vérification croisée réussie sur le slot 91DA17 (le plus avancé) : les 2
seules entrées encore verrouillées sont "Facecamo MGS1" (débloqué en
entrant dans l'Acte 4) et "Drebin" (débloqué à 60 armes) — et ce slot est
justement encore à l'Acte 1 avec seulement 56 armes (`count_acquired_weapons`)
au moment du sample testé. Résout au passage une fausse alerte : le
tableau `0x352` (slots armes) contenait 69 entrées non-nulles, mais c'est
bien le compte restreint à 73 (hors ID 11) de `count_acquired_weapons()`
qui correspond au seuil du jeu, pas un simple comptage brut du tableau.

Les 4 facecamos "Beauty" (labellisées S/L/R/C dans la table Cheat Engine
d'origine) sont supposées correspondre à Screaming/Laughing/Raging/Crying
par initiale — plausible mais pas vérifié par diff temporel (les 4 valent
déjà 1 sur tous nos slots disponibles, aucune transition observée).

La page source documente aussi une catégorie "Camouflages spéciaux" (Camo
Cadavre, Camo Digit R/B, Camo Rire, Camo Rage) débloqués par mécanismes
différents (mort ×41, DLC menu Extra) - non repris ici car pas encore
recoupés avec un ID de notre tableau, et le menu Extra/DLC pourrait ne
même pas exister sur le portage PC.

### Corrections après vérification directe par l'utilisateur

L'utilisateur a signalé en jeu : pas de costume d'Altaïr, mais bien le
costume de Snake, et bien le FaceCamo de base. Ça contredisait notre
mapping (0x1c/0x1d inversés, FaceCamo mal placé à 0x14) - corrigé :

- `0x1c` = Costume de Snake (pas Altaïr), `0x1d` = Costume d'Altaïr (pas
  Suit). La table Cheat Engine d'origine avait les deux inversés.
- FaceCamo de base : en réalité à `0x1e` (jusque-là étiqueté "Face Camo
  (dup?)" et jamais utilisé), pas `0x14`. `0x14` vaut 0 sur tous nos slots
  malgré le FaceCamo obtenu - son rôle réel reste inconnu.

Leçon : la table Cheat Engine communautaire est fiable pour la plupart des
IDs mais pas infaillible - une vérification directe par l'utilisateur
reste plus fiable que nos déductions par corrélation quand les deux se
contredisent.

### ENVG et Octocamo "de base" retirés (2026-08-31)

Deux nouveaux problèmes signalés par l'utilisateur :

- **ENVG** ne devrait pas être une entrée séparée : c'est une fonction
  intégrée au Solid Eye, pas un objet indépendant. Retiré de `CAMO_NAMES`.
- **Octocamo de base** (`0x18`) : l'utilisateur indique qu'il se débloque
  automatiquement assez tôt dans l'Acte 1 - donc devrait valoir 1 sur
  toute save ayant dépassé ce point, en particulier sur une partie
  **entièrement terminée**. Vérification : `0x18` vaut **0 sur tous nos
  slots sans exception**, y compris `903CC9` et `919CFF` qui sont des
  parties terminées. Preuve suffisante que cet ID est faux.
  - Fait notable : `0x14` à `0x18` valent TOUS 0 sur TOUS les échantillons
    disponibles (5 slots très différents, aucune variation nulle part) -
    à la différence des couleurs Octocamo (`0x2c`-`0x35`) qui, elles,
    varient bien selon les slots (vérifié : `944D92`/`944EE9` ont un
    mélange verrouillé/débloqué alors que les 3 vraies parties les ont
    toutes débloquées). Ça suggère que `0x14`-`0x18` est une zone
    simplement inutilisée par cette version du jeu (peut-être parce que
    l'Octocamo "de base" et le Face Camo "de base" sont dérivés de la
    progression de scénario à la volée plutôt que stockés comme un flag
    permanent), plutôt qu'un décalage d'ID isolé à corriger. Pas
    d'emplacement de remplacement trouvé pour l'instant - retiré de
    l'interface en attendant. Les 10 couleurs Octocamo restent affichées,
    elles sont fiables.

### Baril (Drum Can) : 0x02, pas 0x09 (2026-09-01)

Test isolé sur partie fraîche (Molotov + baril obtenus ensemble, seul
`item[0x02]` a flush - `item[0x09]`, notre ancien candidat informel pour
"Drum Can", n'a pas bougé). Comparaison sur plusieurs parties pour
trancher : `item[0x02]` varie naturellement (10, 14, 13 selon la partie -
cohérent avec une quantité de tonneaux utilisés/ramassés), alors que
`item[0x09]` vaut **exactement 25 sur les 3 parties avancées testées**
(903CC9, 919CFF, 91DA17) - beaucoup trop constant pour une vraie quantité
d'usage, donc probablement pas le bon candidat (rôle réel inconnu).
`0x02` = Baril (Drum Can). Ni l'un ni l'autre n'était formalisé dans le
code (pas de tab objets de soin/déguisements-terrain), juste des notes
informelles - rien à corriger dans l'app pour l'instant, gardé pour
référence future.

### Chansons décalées de +1 : correction du correctif précédent (2026-09-01)

Découverte majeure : le "correctif" précédent (échange de "Level 3
Warning"/"The Best Is Yet To Come" entre `0x58`/`0x59`) traitait le
symptôme, pas la cause. Nouveau test isolé : une **batterie** obtenue
(pas une chanson) fait passer `item[0x3c]` de verrouillé à obtenu - or
`0x3c` était censé être la première chanson ("Warhead Storage") dans notre
table d'origine.

En recoupant avec les 2 autres tests isolés déjà faits sur des chansons
nommées :
- "Theme of Tara" trouvé à `0x54` (ancienne table : `0x53`)
- "Level 3 Warning" trouvé à `0x59` (ancienne table : `0x58`)

Les deux écarts sont EXACTEMENT +1 par rapport à l'ancienne table - donc
ce n'est pas un échange isolé de 2 noms adjacents, mais un **décalage
uniforme de +1 sur toute la liste des 38 chansons**, à cause d'une case
"Batterie" intercalée à `0x3c` que la table Cheat Engine d'origine avait
oubliée entre les statuettes (`0x36`-`0x3a`) et les chansons.

Corrigé : toute la table `SONG_NAMES` recalée de +1 (`0x3d` à `0x62` au
lieu de `0x3c` à `0x61`). Revérifié sur la même save que "Theme of Tara"
et "Level 3 Warning" affichent maintenant tous les deux "obtenu" avec le
bon nom. Rôle de `0x3c` lui-même ("Batterie") pas formalisé dans le code
(pas de tab dédié aux objets divers) - noté ici pour référence.

Leçon (déjà notée mais visiblement pas assez suivie) : face à un écart
isolé, toujours se demander s'il s'agit d'un échange local ou d'un
décalage global avant de corriger - vérifier plusieurs points de la même
séquence plutôt qu'un seul suffit à trancher.

### Camouflage furtif/Bandana infirmés, Muna trouvé (2026-09-01)

Notre identification d'origine de `0x0e` = "Camouflage furtif" reposait
sur une preuve fragile ("déjà à 1 dès le début" sur nos 3 vraies parties)
qui ne prouvait en fait rien, puisqu'on n'avait jamais capturé ces parties
à leur tout début - on ne pouvait pas savoir si "1 dès le début" était
vrai ou juste "1 avant même notre premier échantillon".

Test isolé sur partie fraîche : `item[0x0e]` passe de verrouillé à obtenu
exactement au moment où l'utilisateur récupère la **Muna**, pas le
Camouflage furtif. Réattribué à Muna (`ITEM_NAMES_MISC`, pas de tab dédié
pour l'instant). **Onglet "Objets spéciaux" vidé** (Camouflage furtif et
Bandana retirés) en attendant de retrouver leurs vrais ID.

### Déguisement Amérique du Sud : 0x1b, pas 0x19 (2026-09-01)

Test isolé : `item[0x1b]` (pas `0x19`) se débloque exactement au moment où
l'histoire entre au "Village de Cove Valley" (tout début de l'Acte 2) -
correspond pile à la description du site source pour ce déguisement.
`0x19` était déjà obtenu bien avant, en pleine Acte 1, donc incompatible.
Corrigé : `OUTFIT_NAMES[0x1b]` = Amérique du Sud. "Europe de l'Est" (qui
occupait `0x1b` avant) et l'identité réelle de `0x19` retirés de la table
en attendant de les retrouver - mieux vaut ne rien afficher que du faux.

### Boîte en carton : 0x09, pas 0x08 (2026-09-01)

Nouveau test isolé (un seul changement malgré un gros saut de progression
Acte 1 → Acte 2) : `item[0x09]` passe de verrouillé à **25** en obtenant
la boîte en carton. Ça confirme aussi la piste ouverte plus haut : `0x09`
n'est PAS "Drum Can" (déjà réassigné à `0x02`), c'est la boîte en carton.
Le fait qu'il saute directement à 25 (pas 1) au lieu de croître
progressivement est cohérent avec ce qu'on avait observé (0x09 vaut
exactement 25 sur toutes les parties avancées) - probablement une
capacité/jauge fixe plutôt qu'un compteur d'usage. Rôle de `0x08`
(l'ancien candidat pour la boîte en carton) encore inconnu. Toujours rien
à corriger dans l'app (pas de tab dédié), juste pour référence future.

Retenir pour la suite : ne plus faire confiance aux ID de la zone
`0x14`-`0x1e` sans vérification croisée sur au moins une partie
**entièrement terminée** (le test le plus dur : tout ce qui se débloque
"automatiquement en avançant" doit absolument valoir 1 dessus).

### RPG-7 : les 3 sous-ID ne sont pas toujours liés (2026-08-31, session suivante)

L'utilisateur a remarqué dans l'interface qu'une seule des 3 entrées RPG-7
était marquée "obtenue" sur une de ses saves, alors qu'on pensait les 3
toujours liées (vu qu'elles bougeaient ensemble dans nos tests sur partie
fraîche). Vérification sur `903CC9`/`919CFF` (parties terminées) :
`0x32` vaut "obtenu" sur les deux, mais `0x0a` et `0x0b` restent à 0 -
seule la save la plus avancée (`91DA17`) a les 3.

Conclusion révisée : `0x32` = RPG-7 de base (toujours obtenu), `0x0a` et
`0x0b` = probablement 2 types de munitions/ogives séparés, obtenus plus
tard ou optionnellement - pas systématiquement liés au RPG-7 de base. Nos
tests précédents les avaient vus bouger ensemble par coïncidence de
timing (un seul et même événement de jeu les avait tous débloqués d'un
coup sur cette partie précise), pas parce qu'ils sont indissociables.
Renommés `0x0a`/`0x0b` en "RPG-7 (munition spéciale ?)" pour refléter
cette incertitude, `0x32` reste simplement "RPG-7".

### Gilet vs Octocamo, et Camo Cadavre retrouvé (2026-08-31)

Nouvelle correction de l'utilisateur : les 10 couleurs `0x2c`-`0x35` que
j'affichais comme "Octocamo - couleur" sont en réalité des couleurs de
**gilet**, pas de l'Octocamo. Renommées `CAMO_NAMES` en "Gilet - X".

Par ailleurs, l'utilisateur signale l'absence du **Camo Cadavre**, qui lui
est bien lié à l'Octocamo. Ça recoupe exactement la section "Camouflages
spéciaux" du site Metal Gear Generation (Camo Cadavre, Camo Digit R, Camo
Digit B, Camo Rire, Camo Rage - 5 entrées), et coïncide en nombre avec les
5 ID `0x14`-`0x18` qu'on avait déjà identifiés comme "toujours à 0 partout,
sur tous les échantillons" (précédemment attribués à tort à FaceCamo/ENVG/
Kerotan/Ga-Ko/Octocamo de base). Contrairement à ces derniers, les
camouflages spéciaux sont des déblocages rares/optionnels (ex: Camo
Cadavre demande 41+ morts en fin de partie) - rester à 0 sur tout notre
échantillon ne les contredit donc pas.

Ajoutés comme `SPECIAL_CAMO_NAMES` (repris dans `CAMO_NAMES`) :
`0x14`=Camo Cadavre, `0x15`=Camo Digit R, `0x16`=Camo Digit B,
`0x17`=Camo Rire, `0x18`=Camo Rage.

**Confiance modérée seulement** : la correspondance de compte (5 items
documentés = 5 ID toujours à 0) est un bon indice structurel, mais
**l'ordre exact à l'intérieur du bloc n'est pas vérifié** - aucun de nos
échantillons n'a jamais débloqué l'un de ces camouflages, donc aucune
transition 0→1 n'a pu être observée pour confirmer quel ID correspond à
quel nom précisément. À corriger si quelqu'un obtient un jour l'un de ces
camouflages et peut confirmer lequel s'allume.

### Camo Cadavre introuvable - hypothèse infirmée (2026-08-31)

L'utilisateur signale que le Camo Cadavre **est bien débloqué en jeu** sur
le slot `91DA17` (NAKED NORMAL), alors que l'appli l'affiche encore
verrouillé. Vérification :

- Le fichier live `MGS4.SAV` de ce slot est **strictement identique** (au
  bit près) à notre dernier échantillon horodaté du 30/08 - donc pas de
  nouvelle sauvegarde entre les deux, mais ça veut aussi dire qu'on ne
  peut pas corréler par diff temporel : le Camo Cadavre était déjà
  débloqué dès notre premier échantillon de ce slot.
- Scan intégral du tableau d'objets (les 99 entrées, `0x00` à `0x62`) sur
  ce fichier live : **aucun ID inexpliqué ne vaut 1**. Tous les ID déjà
  assignés à quelque chose (recovery items, camos faciaux, tenues, gilet,
  statuettes, chansons) ont des valeurs cohérentes avec ce qu'on a déjà
  vérifié ; `0x14`-`0x18` valent toujours 0.
- Conclusion : **`SPECIAL_CAMO_NAMES` (0x14-0x18) est une hypothèse
  fausse**, retirée de l'affichage (code gardé en commentaire dans
  `mgs4save.py` pour mémoire, mais plus utilisé). Le Camo Cadavre n'est
  simplement pas dans ce tableau `0x0526` du tout.
- Piste pour la suite : comme le déclencheur documenté est "41 morts **à
  la fin du jeu**", ça ressemble à un bonus global (compte de morts
  cumulé, tous slots confondus) plutôt qu'un flag par sauvegarde -
  probablement stocké dans `MGS4SYS.SAV` (fichier partagé entre tous les
  slots), dans une des zones encore non défrichées (`0x40-0xc7` ou
  `0xe0-0x158`, voir section MGS4SYS.SAV plus haut). Diff rapide
  old-vs-live de `MGS4SYS.SAV` : un seul octet change (`0x1fd`,
  `0x3d→0x39`), dans la zone footer/checksum documentée comme non-fiable
  (change à chaque écriture, sans rapport avec le contenu) - donc pas
  d'indice exploitable pour l'instant.
- Pour avancer : demander à l'utilisateur si le Camo Cadavre apparaît
  débloqué sur ses AUTRES slots aussi (903CC9, 919CFF...). Si oui, ça
  confirmerait l'hypothèse "bonus global dans MGS4SYS.SAV" et justifierait
  de creuser ce fichier plus sérieusement.

**Hypothèse INFIRMÉE (2026-09-06)** : l'utilisateur confirme directement
que ce n'est PAS un bonus global partagé - le Camo Cadavre se comporte
exactement comme les FaceCamo/autres camouflages : débloqué sur une
partie, il est hérité par les parties SUIVANTES (carry-over NG+), mais
PAS par les parties précédentes déjà existantes. C'est donc bien un flag
individuel dans `MGS4.SAV` de chaque slot (pas dans `MGS4SYS.SAV`),
simplement dans une zone du fichier qu'on n'a pas encore explorée - ni
le tableau d'armes (`0x1d4`) ni le tableau d'objets (`0x0526`) ne
contiennent de candidat (vérifié par diff entre une partie fraîche
`BLJM67001G6A9D936C` et la partie NG+4 `BLJM67001G6A95B67B` : aucun ID
non mappé ne diffère entre les deux, à part nos deux mystères déjà
connus `0x1d`/`0x4e`, sans rapport). Reste à chercher ailleurs dans le
fichier (zone stats, ou zone jamais scannée) - pas de piste concrète
pour l'instant.

### MK.2 Pistol : mauvais ID, corrigé (2026-08-31)

L'utilisateur a confirmé (et une recherche web l'a corroboré) que le
Mk.2 Pistol est le pistolet tranquillisant donné automatiquement dès le
début de l'Acte 1, avec l'Operator, via le robot Mk.II d'Otacon - donc
devrait valoir 1/2 dès la toute première sauvegarde de n'importe quelle
partie.

Vérification sur la série temporelle complète du slot `91DA17` (18
sauvegardes, du tout début jusqu'à plus tard dans l'Acte 1) :
- `0x00` (ID d'origine de la table Cheat Engine) : reste à **0 tout du
  long**, jamais 1 ni 2, y compris sur des parties entièrement terminées.
- `0x01` : vaut **2 dès le tout premier échantillon**, constant depuis -
  signature exacte d'une arme donnée dès le départ.

Correction : `WEAPON_NAMES[0x01] = "MK.2 Pistol"` (au lieu de `0x00`).
Vérifié que ce n'est **pas** un décalage global de toute la table : les 4
autres ID confirmés (Operator `0x0B`, AK102 `0x11`, MK.17 `0x14`, Stun
Grenades `0x2A`) transitionnent bien de 0 à une valeur non-nulle plus tard
dans cette même série - à leur position d'origine, pas à +1. Donc
uniquement `0x00` était faux, probablement une case morte/inutilisée
(même famille de problème que les ID `0x14`-`0x18` du tableau d'objets).

**Correction #2 (0x01 infirmé à son tour)** : l'utilisateur a 2 saves de
test (`944D92` Big Boss Difficile, `944EE9` The Boss Extreme) **prises
explicitement avant la cinématique de remise d'équipement** d'Otacon (donc
le Mk.2 Pistol n'y est pas encore disponible - confirmé par l'utilisateur).
Or `weapon[0x01]` y vaut déjà 2. Donc `0x01` est une valeur par
défaut/structurelle sans rapport avec une acquisition réelle - ni `0x00`
ni `0x01` ne conviennent.

Méthode corrigée (comparaison demandée explicitement par l'utilisateur pour
les prochaines requêtes) : diff complet du tableau d'armes entre `944D92`
(stage `s01a00l`, avant remise) et le premier échantillon du slot `91DA17`
où le stage a déjà avancé (`141536`, stage `s01a10l` "Zone rouge", donc
forcément après la remise). **Une seule différence sur les 95 entrées** :
`0x19` passe de 0 à 2. Revérifié sur toutes les saves disponibles : 0 sur
les 2 saves "avant remise", 2 partout ailleurs (`903CC9`, `919CFF`,
`91DA17` avancé) - signature nette, sans exception. Nouvelle valeur :
`WEAPON_NAMES[0x19] = "MK.2 Pistol"`.

Leçon retenue : pour les futures questions similaires, comparer
systématiquement avec les autres saves disponibles plutôt que de se fier à
une seule save qui "a l'air plausible" - une valeur constante sur UN SEUL
échantillon ne suffit pas à distinguer "donné dès le début" de "valeur par
défaut sans rapport avec le jeu".

### Campagne de tests sur partie fraîche (2026-08-31) - armes trouvées/corrigées

Suite du travail ci-dessus, en utilisant une partie toute neuve (LIQUID
FACILE, partie n°0) et des comparaisons avant/après isolées à chaque
nouvelle acquisition. Confirme la leçon ci-dessus : **2 des 3 ID d'armes
trouvés via l'ancienne méthode du "gros flush bruyant" étaient faux** :

| Arme | Ancien ID (faux) | Vrai ID | Méthode |
|------|-------------------|---------|---------|
| MK.17 | `0x14` | `0x1e` | Test isolé, save avant/après |
| Stun Grenades | `0x2A` | `0x36` | Test isolé, save avant/après |
| MK.2 Pistol | `0x00` puis `0x01` | `0x19` | Déjà corrigé précédemment |
| AK102 | `0x11` | *(toujours pas re-vérifié)* | En attente |

Nouvelles armes trouvées par test isolé (confiance haute) :
- `0x35` = White Phosphorus Grenades
- `0x45` = Magazine Playboy (fait notable : classée dans le tableau
  **armes**, pas objets - la frontière armes/objets du jeu ne correspond
  pas à l'intuition)

### Chansons : "regression" expliquée - retour volontaire à une save antérieure (2026-09-01)

Observé : "Bio Hazard" (`item[0x4b]`) était à 1 (obtenu) sur une save,
puis de retour à 65535 (verrouillé) sur la "suivante". Pas une mécanique
du jeu ni une anomalie : l'utilisateur était en fait reparti volontairement
sur une sauvegarde antérieure où il ne l'avait pas encore. Leçon : quand
un ID déjà confirmé semble "redescendre", demander si l'utilisateur a
rechargé une save plus ancienne avant de conclure quoi que ce soit sur la
fiabilité de l'ID - ça ne remet pas en cause l'identification en soi,
c'est juste un retour en arrière réel dans la progression.

### Chanson 0x41 : "Bon Dance", pas "'Yell' Dead Cell" (2026-09-01)

Test isolé : `item[0x41]` se débloque en obtenant la chanson "Bon Dance",
pas "'Yell' Dead Cell" comme dans notre liste (déjà décalée de +1 une
fois). Corrigé. Emplacement réel de "'Yell' Dead Cell" de nouveau
inconnu - retiré de la liste. Les chansons voisines confirmées restent
correctes (`0x42`=Sailor, déjà vérifié séparément).

### À reprendre : Baril/Boîte en carton ne sont pas des quantités (2026-09-01)

L'utilisateur précise : Baril et Boîte en carton sont comme l'iPod ou la
Seringue - soit on les a, soit pas, pas de "quantité en stock" à proprement
parler. Le nombre affiché (ex: Baril=12, Boîte en carton=25) est donc
probablement un **compteur d'usage** (nombre de fois utilisé/entré dedans),
pas un inventaire empilable comme Regain/Pentazémine/Rations/Nouilles qui
eux sont de vrais objets consommables en pile. À corriger : afficher ces
deux-là en obtenu/pas obtenu simple (comme iPod/Seringue/Muna), pas avec
le nombre entre parenthèses comme les vrais objets à quantité. Reporté à
la prochaine session.

### AK-102 (0x11) était en fait Masterkey (2026-09-01)

L'utilisateur signale que le jeu affiche une fenêtre de "nouvelle
acquisition" à chaque objet/arme/accessoire ramassé pour la première fois
- un signal fiable pour savoir si quelque chose est vraiment nouveau.
Masterkey a déclenché cette fenêtre, confirmant que c'était une vraie
première acquisition (pas déjà possédé).

Ça a permis de repérer une erreur : `0x11` avait été étiqueté "AK102"
après l'avoir vu flush dans le lot Masterkey/MP7/DSR-1, en supposant que
c'était enfin le flush retardé de l'AK-102 qu'on cherchait depuis
longtemps. Mais l'utilisateur précise que l'AK-102 est sa **toute
première arme du jeu**, obtenue avant même le don d'Otacon (Operator/1911/
Thor). Vérification sur toute la série temporelle de la partie fraîche :
`weapon[0x11]` reste à **0 même après** que `weapon[0x02]` (Operator, le
don d'Otacon) soit déjà flaggé - impossible si `0x11` était vraiment
l'AK-102, qui aurait dû flush bien avant. Donc `0x11` = **Masterkey**
(confirmé par la fenêtre de nouvelle acquisition), pas l'AK-102.

**L'AK-102 reste donc non identifié**, malgré toute la chasse précédente
sur ce nom. Piste pour la suite : chercher un ID qui flush très tôt dans
la partie fraîche (avant ou en même temps que le Mk.2 Pistol/Operator),
pas encore attribué à autre chose.

Leçon retenue : ne pas conclure qu'un flush retardé "confirme" une arme
activement recherchée juste parce qu'il arrive enfin - toujours vérifier
que la case reste bien à 0 à TOUS les points antérieurs où l'arme est
censée être déjà possédée, pas seulement au moment du flush lui-même.

### Mise à jour Operator/1911 Modifié/Thor .45-70 (2026-09-01, capture d'écran inventaire)

Une capture d'écran de l'inventaire en jeu a résolu une partie du mystère
du lot Otacon :
- "Mk.22" n'existe pas comme nom affiché en jeu - l'utilisateur désignait
  en fait **"1911 Modifié"** sous ce nom. Corrigé : `0x03` = "1911 Modifié"
  (au lieu de "MK.22").
- La capture confirme aussi les munitions exactes : Operator=54, 1911
  Modifié=54 (**même valeur** - pool `.45 ACP` partagé confirmé), Thor
  .45-70=10 (pool séparé), AK-102=112 (confirme `slot[0x11]` du tableau
  munitions, cohérent avec le partage AK-102/XM8 déjà établi).
- Ça confirme qu'il y avait bien exactement **3 armes** (pas 4) dans le
  don d'Otacon : Operator, 1911 Modifié, Thor .45-70. Le 3e ID mystère
  (`0x4d`), laissé de côté jusqu'ici, est donc réattribué à Thor .45-70
  par élimination - toujours confiance basse sur l'attribution 1-pour-1
  exacte entre les 3.
- Fait notable : comme Operator et 1911 Modifié partagent le même slot de
  munitions, la technique de corrélation par ordre d'apparition (qui avait
  marché pour XM8/Javelin) ne peut PAS s'appliquer ici - le partage de
  munitions fausse le comptage "nouvelles cases munitions = nouvelles
  armes" puisque 3 armes ne créent que 2 nouvelles cases de ce type (une
  partagée + une pour Thor). À garder en tête pour de futurs lots ambigus
  impliquant des armes de calibres identiques.

Operator + MK.22 (confiance BASSE) : donnés simultanément par Otacon dans
la même cinématique, confirmé par l'utilisateur comme **impossible à
séparer** en jeu. Diff avant/après : 3 cases changent (`0x02`, `0x03`,
`0x4d`), aucun moyen de savoir laquelle est laquelle. Attribution par
convention : `0x02`=Operator, `0x03`=MK.22, et `0x4d` volontairement
laissé sans nom (pourrait être une coïncidence de timing avec un autre
événement du même flush, comme Solid Eye/MG Mk2/Camera qui ont aussi
changé au même moment sans rapport avec Otacon).

### "Objets donnés aux milices" - confirmé faux (2026-08-31)

Champ `0x198` (MGS4.SAV) / `0x40` (METADATA.SAV), jusque-là affiché comme
"Objets donnés aux milices". L'utilisateur a remarqué que ce compteur
augmentait sans qu'il ait donné quoi que ce soit à un milicien. Vérifié sur
la partie fraîche : vaut déjà **1 à 156 secondes de jeu** (bien avant tout
contact possible avec des rebelles), puis progresse (1→2→5→6) sans lien
apparent avec des dons d'objets. **Confirmé faux.**

Renommé en `progression_menu_sauvegarde` partout dans le code (offset
inchangé), en reprenant le nom neutre de la source externe bbtracker
("save-menu progress resource index") qu'on avait ignoré à tort au profit
d'une supposition. Rôle réel toujours inconnu - piste possible : un
compteur de jalons de progression/cinématiques plutôt qu'un vrai objet
donné. L'emblème BLUE BIRD (seuil ≥50) garde le même seuil numérique mais
le libellé affiché signale maintenant l'incertitude.

**Fait notable découvert au passage** : la copie de ce champ dans
`MGS4.SAV` (`0x198`) et celle dans `METADATA.SAV` (`0x40`) peuvent
diverger fortement au même instant (vu 0 vs 6 sur le même slot).

### objets_donnes_milices, deuxième revirement (2026-08-31) - c'était correct au final

Nouveau test isolé : l'utilisateur a donné exactement 2 objets à des
miliciens sur la partie fraîche. Diff avant/après sur `MGS4.SAV` :
`0x198` passe de **0 à 2**, pile la bonne valeur. **Ce champ est donc bien
"objets donnés aux milices"**, confirmé par un test propre et précis -
renommage précédent annulé, remis à `objets_donnes_milices` partout
(`STATS`, libellé GUI, condition de l'emblème BLUE BIRD).

Explication de la confusion initiale : ce n'est PAS le même compteur que
`progression_menu_sauvegarde` de `read_metadata_summary()` (`METADATA.SAV`,
offset `0x40`) - malgré le nom identique dans le code d'origine, ce sont
deux compteurs **indépendants** dans deux fichiers différents. C'est celui
de `METADATA.SAV` qui se comporte bizarrement (déjà à 1 après 156 secondes
de jeu) et qui reste renommé/marqué incertain - celui de `MGS4.SAV`
(utilisé par `read_stats()`, affiché dans l'onglet Stats, et par l'emblème
BLUE BIRD) est fiable.

Leçon : avant de corriger un champ suite à un comportement suspect,
vérifier précisément QUEL fichier et QUEL offset est réellement utilisé
par le code affiché à l'utilisateur - ne pas supposer que deux champs au
nom similaire dans deux fichiers différents sont la même donnée sans le
vérifier explicitement.

### FaceCamo et Laughing Beauty : encore la même leçon (2026-09-01)

Test isolé sur partie fraîche : l'utilisateur obtient la Seringue, la
statuette Laughing Octopus, le FaceCamo de base et le FaceCamo "Laughing
Beast" (Laughing Beauty). Résultat :

- `item[0x1f]` se débloque - pas `0x1e` (notre ancienne identification du
  FaceCamo de base, "confirmée" uniquement par recoupement sur des
  parties déjà avancées - même défaut méthodologique que Camouflage
  furtif/Muna plus tôt). Corrigé : FaceCamo = `0x1f`.
- `item[0x22]` se débloque - pas `0x21` (notre ancienne "Laughing
  Beauty"). Corrigé : Laughing Beauty = `0x22`. Ça infirme du même coup
  l'hypothèse des initiales S/L/R/C de la table Cheat Engine d'origine
  pour les 4 Beauty - Crying/Screaming Beauty restent affichées mais avec
  une confiance revue à la baisse (pas encore d'évidence directe pour les
  corriger précisément).
- `item[0x11]` = **Seringue**, nouvel objet non formalisé dans le code
  (pas de tab dédié). Note : l'ancienne hypothèse informelle "0x10 =
  Syringe" (jamais utilisée dans le code) est donc aussi fausse.
- La statuette Laughing Octopus a aussi été confirmée cohérente avec
  notre table existante (`0x36`), rien à changer là.

Leçon répétée : ne plus jamais se fier à "déjà à 1 sur une save avancée"
comme preuve d'identification - toujours préférer un test isolé sur
partie fraîche quand c'est possible.

### Gilet Kaki/Vert inversés + variantes "Doré" manquantes (2026-09-01)

Capture d'écran du menu "Poitrine" en jeu : confirme l'inversion Kaki/Vert
(corrigé, voir `VEST_NAMES`). Révèle aussi une couleur qu'on n'a pas du
tout dans notre liste de 10 : **Doré**, un bonus de précommande (donc pas
débloqué chez tout le monde). À creuser un jour : soit c'est un 11e ID
qu'on n'a pas encore trouvé, soit une de nos 10 couleurs actuelles
(Bleu/Rouge/Orange/Tan, jamais vérifiées individuellement) n'existe pas
réellement et correspond en fait à Doré.

2e capture (menu "Camouflage - Visage") : confirme l'ordre Aucun/FaceCamo/
L.Beauty déjà établi, et montre 2 entrées "Doré" supplémentaires du même
genre : **Doré** et **Facecamo Doré**. L'utilisateur confirme : "tout ce
qui est doré est un cadeau pour la précommande" - donc probablement une
famille d'items bonus précommande répétée dans plusieurs catégories
(Gilet, FaceCamo, peut-être d'autres), pas un cas isolé. Aucun ID connu
pour l'instant pour ces variantes Doré - à chercher si l'occasion se
présente (l'utilisateur les ayant précommandé, il devrait pouvoir isoler
leur ID via le même genre de test qu'avant si besoin).

### Complément 0x352 : munitions partagées par calibre (2026-09-01)

L'utilisateur confirme en jeu (observation directe, pas encore revérifiée
par diff de fichier) que certaines armes de même calibre partagent le même
pool de munitions : Operator/GSR/1911 modifié (`.45 ACP`) d'un côté,
AK-102/M4 modifié/XM8 (`5.56mm` ou équivalent) de l'autre - tirer avec
l'une fait baisser le compteur affiché en jeu pour les autres aussi.

Donc le tableau `0x352` est probablement organisé par **type de
munition/calibre partagé**, pas par arme individuelle comme on le
supposait. À garder en tête pour toute future utilisation de ce tableau
pour départager des armes ambiguës par munitions : deux armes du même
calibre pointeront vers la MÊME case, pas des cases séparées - un lot
"plusieurs armes + une seule nouvelle case de munition" pourrait donc
signifier "plusieurs armes de même calibre" plutôt que "une arme trouvée
et une autre qui n'a pas d'ammo".

### Tableau 0x352 : munitions par emplacement d'équipement (2026-08-31)

Rôle de ce tableau (`u16[68]`, sentinelle `0xFFFF` = case vide, jamais
identifié même par la source externe bbtracker) enfin percé, grâce à un
test suggéré par l'utilisateur : tirer un nombre précis de munitions
connues avec une arme et observer le tableau avant/après.

Contexte : 2 armes (Thor .45-70, 1911 modifié) sont apparues "de nulle
part" (probablement données automatiquement par le scénario, impossible à
isoler par un test avant/après classique) en même temps qu'Operator et
MK.22. En creusant les changements de CE moment précis, 3 cases de ce
tableau sont passées de vide à une petite valeur numérique (41, 36, 30) -
qui ressemblaient à des comptes de munitions plutôt qu'à des ID.
L'utilisateur a fait le rapprochement : 41 correspond exactement aux
munitions de son Mk.2 Pistol. Test de confirmation : tirer 3 munitions
avec le Mk.2 Pistol puis sauvegarder → `slot[0x00]` passe de **41 à 38**,
soit exactement -3. **Confirmé : ce tableau contient les compte de
munitions actuelles, une entrée par arme équipée au moins une fois.**

Limite importante : ce tableau ne semble PAS indexé par un ID d'arme fixe
comme le tableau principal `0x1d4` (95 entrées, un ID stable par type
d'arme). Avec seulement 68 cases et une sentinelle "vide" en tête de
liste, il ressemble plutôt à un **historique d'équipement dans l'ordre
chronologique** : la première arme jamais équipée dans une partie prend le
slot 0, la deuxième le slot 1, etc. Chez l'utilisateur, le Mk.2 Pistol
(sa toute première arme) est au slot 0 - mais rien ne garantit que ce
soit le cas sur une autre partie où l'ordre d'équipement diffère. **Donc
ce tableau ne permet pas de construire une table ID→nom générale
réutilisable pour toutes les sauvegardes**, contrairement au tableau
`0x1d4`. Utile uniquement pour suivre les munitions au sein d'UNE partie
donnée (nécessiterait de d'abord établir la correspondance slot↔arme pour
CHAQUE partie individuellement, par exemple en repérant l'ordre
d'apparition des ID du tableau `0x1d4` et en le comparant à l'ordre de
remplissage de ce tableau `0x352`).

**Exemple de correspondance slot↔arme établie pour UNE partie précise**
(2026-09-05, partie neuve sans NG+, slot `BLJM67001G6A9C5C27` et
succession de saves associée) - confirmée par recoupement avec les
munitions affichées en jeu par l'utilisateur, à ne PAS réutiliser sur une
autre partie (voir limite ci-dessus) :

| Emplacement | Arme |
|---|---|
| 0 | Mk.2 Pistol |
| 11 | GSR (pool .45 ACP partagé) |
| 17 | AK-102 / M4 (pool 5.56mm partagé) |
| 20 | Mk.17 |

## Samples de saves conservés

Voir `samples/` (copies horodatées, non versionnées dans git — voir
`.gitignore`, ce sont des données de save personnelles).

## État en cours (2026-09-05, à reprendre en priorité)

- **Couleurs des emblèmes (onglet Emblèmes)** : l'utilisateur a signalé à
  deux reprises que les distinctions de couleur entre les 4 états
  (obtenu / serait obtenu en terminant maintenant / encore possible /
  impossible pour cette partie) n'étaient pas assez visibles ("il n'y a
  rien de doré"). Deux passes de retouche de `DARK_QSS` (gui_app.py,
  styles `#emblemUnlocked/#emblemProjected/#emblemLocked/#emblemImpossible`)
  ont été faites : bordure epaissie/eclaircie pour "obtenu", fond dore
  renforce de 12/255 a 55/255 pour "serait obtenu maintenant" (l'etat qui
  posait probleme - trop discret). **Pas encore confirme visuellement par
  l'utilisateur** (session bloquee par la limite d'images ci-dessous avant
  la verification finale). A verifier en priorite a la reprise : ouvrir
  l'appli, selectionner une save recente (ex. slot du 04/09 23h38,
  "Planque de la milice") qui a des emblemes "projetes" (calcule via
  `compute_emblems` + `read_obtained_emblems`, voir mgs4save.py) et
  confirmer que ces cases se voient bien comme dorees a l'oeil.
- **Limite technique rencontree** : a un moment de la session du
  2026-09-04/05, TOUTE image (mienne ou de l'utilisateur, y compris un
  test de 200x150px cree expres pour verifier) a commence a etre rejetee
  par l'API avec l'erreur "exceed max allowed size for many-image
  requests: 2000 pixels" - une limite cumulative liee au volume d'images
  deja echangees dans la conversation, pas a la taille du fichier
  individuel. Aucune parade trouvee (recadrage/compression inutiles). Se
  resout en ouvrant une nouvelle conversation (le compteur repart a
  zero) - c'est ce qui a motive cet ajout recapitulatif.
- Autres chantiers d'audit deja identifies mais pas encore traites :
  - `SPECIAL_CAMO_NAMES` (Camo Cadavre/Digit R/Digit B/Rire/Rage, IDs
    0x14-0x18) marque "code mort" - plus utilise nulle part (remplace par
    `SPECIAL_CAMO_INFO`, non relie a la save) mais jamais supprime du
    fichier.
  - **Hypothese "item[0x00] = deblocage OctoCamo" INFIRMEE (2026-09-05)** :
    test isole propre sur une partie neuve (backup juste avant/apres avoir
    debloque la fonction OctoCamo en jeu) - `item[0x00]` reste a 0, ne
    bouge pas du tout. Seul `item[0x0d]` a flush (65535->1) dans cette
    fenetre, mais c'est deja "Cigarettes" (confirme independamment le
    2026-09-02) - l'utilisateur confirme avoir aussi recupere des
    cigarettes exactement au meme moment (meme etape scenaristique que le
    deblocage OctoCamo), donc pas de contradiction, `0x0d` reste
    "Cigarettes". **Toujours aucun flag trouve pour le deblocage OctoCamo
    lui-meme** - reste coherent avec l'hypothese que l'Octocamo "de base"
    est derive de la progression de scenario a la volee plutot que stocke
    comme un flag permanent (voir plus haut, meme famille de probleme que
    FaceCamo "de base").
  - Mystere du trio d'armes 0x5c/0x5d/0x5e : comportement incoherent
    d'une partie a l'autre (voir plus haut/mgs4save.py), actuellement
    exclu de l'affichage via `STRUCTURAL_WEAPON_IDS`, identite reelle
    toujours inconnue. Reconfirme (2026-09-05) : deja a 2 sur une partie
    neuve (155s de jeu, encore Acte 1, seul le couteau possede cote armes
    identifiees) - coherent avec le cas "deja obtenu des le debut".
  - Onglet Tenues : seulement 4 tenues suivies (Milicien/Rebelle/
    Civil/Costume de Snake) - possible qu'il en manque d'autres non
    identifiees, jamais verifie par test en jeu.

## Connaissances générales MGS4 utiles au projet

Section de synthèse (2026-09-05) pour qu'une nouvelle conversation n'ait
pas besoin de tout redemander. Mélange de recherches web faites pendant
le projet et d'explications données directement par l'utilisateur (qui
connaît le jeu en détail) - la distinction est précisée quand elle
compte.

### Structure narrative : Prologue / Actes 1-5 / Épilogue

Le jeu a 2 systèmes de suivi de progression distincts dans la save, qui
ne bougent PAS forcément ensemble :
- `stage_code` (string à 0x34, ex. `s01a20l`) : le lieu précis actuel
  (voir `STAGE_NAMES`). Prefixe `s00` = scenes hors-Actes (Prologue au
  tout debut du jeu, Epilogue a la toute fin, toutes les deux au meme
  lieu "cimetiere" - la tombe de Big Boss, scene d'ouverture ET de
  fermeture du jeu). Prefixe `s01`-`s05` = Actes 1 a 5. Prefixes `s10`/
  `s20`/`s30` = briefings/cinematiques hors-mission (Nomad, USS
  Missouri, mariage/hopital de l'epilogue).
- `progress` (u32 à 0x54) : un compteur numérique séparé qui détermine
  l'"Acte" affiché (voir `ACT_RANGES`), indépendant du `stage_code`.

**Pourquoi on peut voir "Acte 1" puis "Prologue" puis revenir à "Acte
1"** (explique par l'utilisateur, question au depart deroutante) : en
plein milieu de l'Acte 1 (Moyen-Orient), il y a une cinematique de
flashback qui bascule brievement le `stage_code` vers `s00a00l`
("Prologue : cimetière" - jeune Snake/Naked Snake à l'enterrement de Big
Boss), MAIS le compteur `progress` ne change pas pendant ce flashback -
donc l'app peut afficher un lieu "Prologue : cimetière" tout en restant
en "Acte 1" cote compteur, avant que le `stage_code` ne revienne a un
code `s01a...` normal juste apres la cinematique. Ce n'est pas un bug de
lecture, c'est fidele a la structure reelle du jeu. Sequence concrete
donnee par l'utilisateur : arrivee Moyen-Orient -> avancee en jeu ->
cinematique flashback cimetiere (Prologue) -> retour Moyen-Orient (Acte
1) - c'est PENDANT cette sequence qu'on obtient l'AK-102 (voir plus haut
la correction historique 0x19).

### Systèmes de jeu (pour comprendre les onglets de l'appli)

- **OctoCamo** : camouflage corporel adaptatif, débloqué **tôt dans
  l'Acte 1** (pas après Laughing Octopus - c'est le FaceCamo qui se
  débloque après Laughing Octopus, Acte 2 - confusion qu'on a eu et que
  l'utilisateur a corrigée). Nécessite d'appuyer le corps contre une
  surface/texture pour s'y fondre.
- **FaceCamo** : calque visuel sur le visage (pas le corps), débloqué
  après avoir vaincu Laughing Octopus (Acte 2). Différents FaceCamo
  s'obtiennent ensuite via diverses conditions (voir `FACECAMO_CONDITIONS`
  dans mgs4save.py) : cogner des personnages avec le Mk.II pendant les
  briefings interactifs (Otacon, Campbell, Naomi->Raiden visière ouverte,
  Sunny->Raiden visière fermée par élimination), vaincre les Beauty and
  the Beast Unit sans les tuer (Laughing/Raging/Crying/Screaming Beauty),
  avoir le rang Big Boss, avoir 60+ armes (Drebin), etc.
- **Gilet (couleur de la tenue tactique)** : 10 couleurs. Les 5
  premières (Olive/Noir/Gris/Bleu marine/Kaki) sont **disponibles dès le
  début de la partie**. Les 5 suivantes (Vert/Bleu/Rouge/Orange/Brun) se
  débloquent **automatiquement en terminant le jeu une première fois**
  (confirmé par l'utilisateur 2026-09-05, cohérent avec le diff isolé
  documenté plus haut : ces 5 ID passent de verrou à possédé en un seul
  bloc, exactement au moment de l'épilogue).
- **Camouflages spéciaux** (Camo Cadavre/Digit R/Digit B/Rire/Rage) : PAS
  liés à l'OctoCamo standard. Camo Cadavre se débloque après 41+ morts
  cumulées à la fin du jeu (condition confirmée par l'utilisateur) - il
  est possédé dès ce moment mais n'apparaît/n'est sélectionnable dans le
  menu qu'une fois le Metal Gear Mk.II/Mk.III obtenu (nuance précisée par
  l'utilisateur, cause de confusion au départ). Les 3 autres (Digit R/B,
  Rire, Rage) sont des téléchargements du menu Extra, disponibilité sur
  le portage PC non confirmée. IDs de save réels jamais retrouvés pour
  aucun des 5 (voir `SPECIAL_CAMO_INFO`, affichage indicatif uniquement).
- **Tenues/déguisements** (pas l'OctoCamo, des vêtements complets) :
  Milicien du Moyen-Orient (Acte 1, casier du refuge de la milice, secteur
  nord-est), Rebelle d'Amérique du Sud (Acte 2, bâtiment fermé de Cove
  Valley, faire du bruit pour attirer le soldat), Civil d'Europe de l'Est
  (automatique au début de l'Acte 3), Costume de Snake (terminer le jeu
  une fois). Chaque déguisement n'est utilisable que dans son propre Acte.
- **Solid Eye / batteries** : le Solid Eye (vision nocturne/zoom, intégré
  dès le début) a jusqu'à 6 batteries au total (1 de base + 5
  récupérables, une par briefing de mission via le Mk.II/Mk.III dans le
  Nomad).
- **Metal Gear Mk.II / Mk.III** : robot compagnon controlable (camera,
  peut distraire/electrocuter les ennemis, transporte des objets). Permet
  aussi de "cogner" des personnages pendant les briefings interactifs
  pour débloquer certains FaceCamo (voir plus haut).
- **Drebin Points (DP)** : monnaie gagnée en vendant des armes/munitions
  trouvées à Drebin (le marchand d'armes), dépensée pour débloquer/acheter
  de l'équipement chez lui. Distinct des Points Drebin "total ventes"
  (cumul historique) vs "actuel" (solde disponible) suivis dans nos
  stats.
- **Munitions émotives (Emotive Ammo)** : certaines armes tirent des
  munitions à effet psychologique sur les soldats maîtrisés en CQC (rire,
  pleurs, peur, rage - voir les effets listés dans `SONG_CONDITIONS`,
  liés aux chansons iPod qui ont cet effet en combat rapproché). Lien
  partagé par l'utilisateur :
  https://metalgear.fandom.com/wiki/Emotive_Ammo (pas re-verifie
  directement, wiki externe).
- **iPod / chansons** : liste de 38 morceaux suivis dans la save (table
  `SONG_NAMES`). Il existe en plus un groupe de morceaux "de base"
  pré-chargés dès le début de la partie, totalement distinct des 38
  suivis, jamais stocké dans le bitmask de `MGS4.SAV` - **confirmé à 35
  morceaux** sur une partie neuve (2026-09-05, l'utilisateur a vérifié en
  jeu qu'aucun des 35 ne correspond à un nom de notre liste de 38), pas
  ~9 comme estimé au départ. L'affichage "0 chanson obtenue" sur une save
  fraîche est donc correct : les 38 suivies restent bien toutes à
  trouver, indépendamment de ces 35 déjà disponibles. Plusieurs
  chansons ont un effet en CQC (accélère la récupération de vie, calme
  les tremblements de main, augmente les dégâts d'endurance, ou
  provoquent une émotion chez le soldat maîtrisé). 5 titres
  (0x3f/0x5f-0x62 : Metal Gear Solid Main Theme, Gekko, Desperate Chase,
  Midnight Shadow, Mobs Alive) ont un nom incertain (absent de la source
  de référence metalgeargeneration.free.fr, probable héritage d'erreur de
  la table Cheat Engine d'origine) et aucune condition d'obtention
  trouvée - affiché avec un message "pas encore documenté" au clic
  plutôt que rien.
- **Statuettes (Beauty and the Beast Unit)** : 5 statuettes (Unité FROG,
  Laughing Octopus, Raging Raven, Crying Wolf, Screaming Mantis), une par
  boss vaincu avec des armes non létales (sauf Unité FROG, combat avant
  Laughing Octopus, statuette trouvée après coup). Obtenir les 5
  débloquerait potentiellement une arme bonus (info non vérifiée dans nos
  données).
- **Emblèmes** : 40 emblèmes (voir `EMBLEMS` dans mgs4save.py), calculés
  par un ensemble de conditions sur les stats cumulées de CHAQUE partie
  individuellement (le jeu ne les évalue réellement qu'à l'écran de
  résultats final). 4 états distingués dans l'appli : obtenu (déjà écrit
  dans le bitmask de la save, définitif), serait obtenu en terminant
  maintenant (toutes conditions déjà vraies mais partie pas terminée),
  encore possible (pas encore toutes vraies, mais rien n'empêche
  définitivement), impossible pour cette partie précise (soit une
  condition à seuil MAX déjà dépassée, soit la partie est déjà terminée
  donc plus aucune progression possible pour elle).
- **New Game+ (★ N)** : `numero_partie` dans METADATA.SAV. Conserve les
  armes/objets/camouflages/statuettes/emblèmes d'une partie à l'autre
  (cumulatif), mais les stats de session (alertes, etc.) et la
  progression de mission repartent à zéro pour la nouvelle partie -
  distinction importante utilisée pour la fonctionnalité de suppression
  de partie complète (regroupement par steamid + difficulté + numéro de
  partie + non-régression des compteurs cumulatifs, voir gui_app.py
  `_find_same_playthrough_siblings`).
- **Difficultés connues** (score brut -> nom, voir `DIFFICULTY_NAMES`) :
  20=LIQUID FACILE, 30=NAKED NORMAL, 35=SOLID NORMAL, 40=BIG BOSS
  DIFFICILE, 50=THE BOSS EXTREME. Mapping incomplet (d'autres scores
  possibles pas encore vus dans nos échantillons).

## Reprise de l'identification (2026-09-05, session suivante)

Nouvelle méthode adoptée pour la suite : un backup (`samples/backup_<slot>_<horodatage>/`)
est recréé après chaque identification confirmée, pour permettre un diff
propre au prochain "nouvelle arme/objet/chanson" sans que l'utilisateur
ait à s'en soucier. Voir aussi le tableau `weapon[0x352]` (munitions par
emplacement d'équipement) pour la piste ci-dessous.

Identifications confirmées par test isolé (diff avant/après, un seul ID
d'arme ou d'objet a bougé à chaque fois) : VSS (`weapon[0x27]`), PP-19
Bizon (`weapon[0x15]`), HK21E (`weapon[0x21]`), MP5SD2 (`weapon[0x12]`),
Saiga-12 (`weapon[0x26]`), M82A2 (`weapon[0x28]`). Confirmations de champs
déjà connus (correspondance exacte) : The Fury (`item[0x58]`), Sailor
(`item[0x42]`), Bio Hazard (`item[0x4b]`), Test Subjects Duality
(`item[0x53]`).

**Correction** : "Drebin" (FaceCamo) était à tort sur `item[0x28]` dans
`FACECAMO_NAMES` (jamais confirmé par test isolé, hérité tel quel de la
table Cheat Engine d'origine) - `item[0x28]` restait verrouillé même
après obtention en jeu du FaceCamo Drebin. Test isolé propre : c'est
`item[0x29]` qui passe de 65535 à 1. Corrigé, identité réelle de `0x28`
de nouveau inconnue.

**Nouveau stat trouvé** : `posters_vus` à l'offset `0x1aa` (u16) dans
`MGS4.SAV` - seule transition exacte 0->1 de toute la zone de stats lors
d'un test isolé, sur un offset jusque-là inutilisé (coincé entre
`temps_accroupi_frames` 0x1a8 et `temps_allonge_frames` 0x1ac). Ajouté à
`STATS` et affiché dans l'onglet Stats (groupe Divers).

**Grenades fumigènes par couleur, IDs distincts confirmés**. Chaque
couleur a son propre ID d'arme (l'entrée générique préexistante
`weapon[0x38] = "Grenades fumigènes"` ne précise toujours pas de couleur,
mais l'ID lui-même est maintenant confirmé solide - voir plus bas) :
- Bleue = `weapon[0x3c]` (test isolé 2026-09-05, 0->2)
- Verte = `weapon[0x3a]` (test isolé 2026-09-05, 0->2)
- Générique = `weapon[0x38]` (test isolé 2026-09-05 : séquence propre
  Phosphore blanc, puis +Paralysante, puis +cette entrée, un seul ID du
  groupe Grenades bougeait à chaque étape)

Confirmé par le tableau de munitions `weapon[0x352]`, qui suit bien Rouge
et Jaune séparément avec des comptes cohérents avec les valeurs données
par l'utilisateur à chaque étape :

| Étape | Rouge (`0x3ac`) | Jaune (`0x3b0`) | Nouvel emplacement |
|-------|------------------|------------------|---------------------|
| Avant Bleue | 5 | 5 | - |
| Test Bleue | 3 (verifie : "3 rouges") | 4 (verifie : "4 jaunes") | `0x394`=5 (compte initial Bleue) |
| Test Verte | 2 (verifie : "plus que 2") | 3 (verifie : "plus que 3") | `0x3ae`=5 (compte initial Verte) |

Reste à faire : un test isolé dédié pour Rouge et pour Jaune (les obtenir
sur une partie fraîche où elles ne sont pas encore possédées, comme pour
Bleue/Verte) pour trouver leurs vrais ID d'arme et éventuellement corriger
`0x38` si elle correspond à l'une d'entre elles - le tableau munitions
0x352 ne peut pas donner cette réponse (indexé par ordre chronologique
d'équipement, pas par ID fixe, voir section dédiée plus haut dans ce
fichier).

## Munitions émotives (Mk.2 Pistol) : pas de flag stable, juste le tableau munitions (2026-09-05)

Test isolé sur l'obtention d'une munition émotive "Rire" pour le Mk.2
Pistol : **aucun changement** dans le tableau d'armes (`0x1d4`) ni dans le
tableau d'objets (`0x0526`) - seul le tableau de munitions par emplacement
d'équipement (`0x352`) gagne un nouvel emplacement (`0x356`, 65535->20),
exactement le même signal que pour une nouvelle couleur de grenade
fumigène. Confirme que les munitions émotives ne sont pas un
objet/arme séparé avec un flag "obtenu" persistant - juste une réserve de
munitions de plus pour une arme déjà possédée. Comme ce tableau n'est pas
indexé par ID fixe (voir plus haut), il n'y a rien de stable à ajouter à
`WEAPON_NAMES`/`ITEM_NAMES` pour ce genre d'évènement.

Munition "Rage" testée juste après : même signature exacte, nouvel
emplacement `0x358` (65535->20), juste à côté de `0x356` (Rire). Les deux
occupent des emplacements consécutifs dans le tableau - ça pourrait
indiquer un sous-bloc dédié aux munitions émotives (rempli dans un ordre
propre à ces munitions, indépendant de l'ordre d'équipement général des
armes), mais rien ne le confirme encore avec un seul point de données par
munition.

**Décision (2026-09-05)** : l'utilisateur a proposé un onglet "Munitions"
dédié, mais a préféré attendre d'avoir plus de données avant de trancher
sur la fiabilité des offsets (0x356/0x358 pourraient tomber ailleurs sur
une autre partie où l'ordre d'équipement diffère - voir mise en garde
donnée avant cette décision). Piste pour la suite : tester Peur et Pleurs
(les 2 munitions émotives restantes du Mk.2) sur CETTE même partie pour
voir si elles continuent la séquence (0x35a, 0x35c ?) - si oui, ça
renforcerait l'hypothèse d'un sous-bloc dédié stable ; sinon, confirmer la
theorie plus prudente (offsets non reutilisables d'une partie a l'autre).

**Suite (2026-09-06, même partie NG+)** : Pleurs testé juste après Rage -
nouvel emplacement `0x35a` (65535->20), qui semblait continuer la
séquence +2 (`0x356` Rire, `0x358` Rage, `0x35a` Pleurs). Mais en
reconstituant l'historique complet des backups après coup, `0x354` a
*aussi* changé (65535->20) dans cette même fenêtre - manqué sur le
moment car le jeu a resauvegardé entre le diff et le backup suivant
(meme phenomene que la visee laser/grenade jaune, voir plus haut).
`0x354` ne peut pas être Pleurs (un seul objet obtenu ce tour-ci) - c'est
très probablement un tout autre événement (un deuxième équipement
d'arme) capturé par accident dans le même intervalle.

**Test Peur/Hurlement (2026-09-06, même partie)** : nom exact vu en jeu
par l'utilisateur = "Hurlement" (pas "Peur"). Résultat : **aucun
changement nulle part** dans le tableau de munitions (0x352-0x391) entre
avant et après. En reconstituant l'historique, le slot qui aurait
continué la séquence (`0x35c`, val=30) était déjà rempli dès le tout
premier backup de cette partie NG+ (avant même le test de Rire) - donc
hérité du carry-over de l'ancienne partie, pas un nouvel évènement
isolable ici.

**Conclusion** : la séquence +2 était une coïncidence d'ordre de test,
pas un sous-bloc dédié stable. Théorie prudente confirmée : ce tableau
reste un historique chronologique global de tous les équipements (armes
+ munitions spéciales confondues), pas un ID stable réutilisable pour
les munitions émotives. Rien à ajouter à `WEAPON_NAMES`/`ITEM_NAMES`
pour ce type d'évènement - sujet clos.

**Résolution du mystère `0x35c`** : le slot 5 (`0x35c`, valeur 30 depuis
le tout début de cette partie NG+, avant meme le test Hurlement/Peur)
n'a rien à voir avec les munitions émotives - test au tir confirmé
(2026-09-06) : équiper le Mosin-Nagant puis tirer une balle fait passer
`0x35c` de 30 à 29 (exactement -1). C'est le slot de munitions du
Mosin-Nagant, hérité du carry-over de l'ancienne partie. Confirme une
fois de plus que ce tableau est un historique chronologique global,
sans rapport avec le type d'arme ou de munition.

**Confirmation externe via le magasin Drebin (2026-09-06, save
`BLJM67001G6A99AEBD`, partie #3, Acte 2)** : capture d'écran du menu
d'achat de munitions pour le Mk.2 Pistol - "ANESTH" (munition
anesthésiante standard) affiche exactement **893**, qui correspond au
slot 0 (`0x352` = 893) lu dans le fichier de cette save. Rire/Rage/
Pleurs/Hurlement affichent tous 0 dans ce menu, cohérent avec les slots
2/3/4 vides (65535) trouvés dans le fichier. Confirme que le slot 0
correspond bien à la munition standard (pas une munition émotive) sur
cette save, et valide au passage la fiabilité de la lecture brute du
tableau `0x352` par recoupement avec l'interface en jeu.

### Découverte majeure : bloc fixe de 5 emplacements par arme, ordre interne stable (2026-09-06)

Test décisif sur une toute nouvelle save (`BLJM67001G6A9D5846`, créée
depuis `BLJM67001G6A99AEBD`) où le Mk.2 Pistol n'avait encore aucune
munition spéciale enregistrée :

1. Achat de **Rage** uniquement (confirmé par capture d'écran, menu
   Drebin) → **4 nouveaux slots apparaissent d'un coup** : `0x354`
   (slot 1) = 0, `0x356` (slot 2) = 0, `0x358` (slot 3) = **40**,
   `0x35a` (slot 4) = 0. Un seul achat, mais tout le bloc se remplit
   (avec des zéros pour les munitions non achetées) - pas juste le
   slot acheté.
2. Achat de **Rire** juste après → seul `0x356` (slot 2) change,
   0 -> 80. Aucun nouveau slot créé (le bloc était déjà réservé).

**Conclusion** : le jeu ne alloue pas un slot par munition achetée
individuellement - il réserve un **bloc contigu de 5 emplacements par
arme** (1 munition standard + 4 munitions émotives) dès la première
interaction avec le magasin Drebin pour cette arme, avec un **ordre
interne fixe** (probablement une énumération codée en dur côté jeu, pas
un ordre d'achat) :

| Offset relatif | Munition |
|---|---|
| +0 | Standard (Anesthésiante pour le Mk.2) |
| +1 | Hurlement (Peur) |
| +2 | Rire |
| +3 | Rage |
| +4 | Pleurs |

Cet ordre est **identique** sur les deux parties testées
indépendamment (`BLJM67001G6A9D45FF` : slot+2=Rire, slot+3=Rage,
slot+4=Pleurs confirmés par tests isolés successifs ; et cette nouvelle
save : mêmes positions relatives confirmées par achat + capture
d'écran). Ça règle la question ouverte plus haut ("coïncidence d'ordre
de test ou énumération fixe ?") en faveur de l'**énumération fixe** :
ce qui varie d'une partie à l'autre, c'est uniquement le **point de
départ du bloc** dans le tableau global de 68 emplacements (dépend de
quand l'arme a été touchée pour la première fois dans l'historique
global chronologique de la partie), pas l'ordre interne des 5
munitions à l'intérieur du bloc une fois celui-ci commencé.

**Relecture a posteriori (2026-09-06)** : avec le schéma bloc-de-5
maintenant confirmé, le slot 6 (`0x35e`) - vide/65535 au moment du test
- est en fait le Hurlement du Mosin-Nagant (slot+1 de son bloc), et
son Rire au slot 7 (`0x360`, slot+2) colle finalement bien avec le
même espacement que le Mk.2 (+0 standard, +1 Hurlement, +2 Rire, +3
Rage, +4 Pleurs). Le "décalage de +4 au lieu de +2" évoqué plus haut
était une erreur de lecture - le Mosin suit exactement le même schéma.
De même, le slot 1 (`0x354`) qui avait changé "mystérieusement" en même
temps que Pleurs (voir plus haut, "Pleurs testé juste après Rage") est
en réalité le **Hurlement du Mk.2 Pistol lui-même** (slot+1 de son
propre bloc), pas un évènement sans rapport comme supposé sur le
moment - il ne s'agissait donc pas d'un raté de capture, juste d'une
mauvaise interprétation avant la découverte du schéma en bloc.

**Piste "ordre par ID d'arme" INFIRMÉE (2026-09-06)** : hypothèse
initiale basée sur les deux blocs connus sur `BLJM67001G6A9D45FF` -
Mk.2 Pistol (ID arme `0x02`) → bloc aux slots 0-4 ; Mosin-Nagant (ID
`0x2b`, plus grand) → bloc aux slots 5-9, juste après. Semblait
suggérer un ordre croissant d'ID. **Contre-exemple trouvé** sur la save
`BLJM67001G6A99AEBD` (Acte 2, partie #3) : le Mosin-Nagant (ID plus
grand) y a déjà son bloc complet aux slots 5-9 (standard=893, puis des
0), alors que le Mk.2 Pistol (ID plus petit, `0x02`) n'a QUE son slot
standard (slot 0 = 893) - ses slots 1-4 sont encore vierges (`65535`,
jamais créés). Si l'allocation suivait l'ordre des ID, le bloc du Mk.2
aurait dû exister en premier. Ce n'est pas le cas : **l'ordre des ID
ne détermine donc pas la position d'un bloc**.

**Conclusion finale** : la position d'un bloc dépend réellement du
moment où le joueur ouvre le magasin Drebin pour l'arme concernée
(ordre chronologique réel de jeu, propre à chaque partie), pas d'une
règle statique déductible à l'avance à partir de l'ID d'arme ou de
toute autre donnée stable identifiée jusqu'ici. Retour à la conclusion
prudente d'origine : localiser un bloc nécessite un test manuel
(acheter/tirer + diff avant/après) sur la save concernée, pas de
raccourci générique possible pour l'instant.

**Généralisation à d'autres familles de munitions (2026-09-06, save
`BLJM67001G6A9D5846`)** : le mécanisme de bloc ne concerne pas que les
munitions émotives du Mk.2/Mosin - captures d'écran du magasin Drebin
montrant d'autres armes à munitions multiples :
- **Double Canon / M870 Modifié** (12 gauge) : 3 types - Chev. 00
  (chevrotine), Balle (slug), Ann. Vort. (anneau vortex). Les deux
  armes affichent EXACTEMENT les mêmes valeurs (893/40/260) - **pool
  partagé** entre les deux, comme le pool .45 ACP (GSR/Operator/1911)
  ou 5.56mm (AK-102/M4) déjà connus. Localisé dans le fichier : bloc
  de 3 aux slots 27-28-29 (`0x388`/`0x38a`/`0x38c`).
- **MGL-140** (lance-grenades) : 4 types - GRD (standard), G Pho
  (phosphore), G Para (paralysante), G Fumi (fumigène). Sur cette save,
  seul le slot standard existe (slot 31 = 82, "GRD") ; les 3 autres
  affichent "0" dans le menu Drebin mais n'ont **aucun slot créé** dans
  le fichier (pas de bloc réservé) - confirme que c'est l'**achat
  effectif d'au moins une munition alternative** qui crée tout le bloc
  d'un coup (comme observé pour Rage/Mk.2 plus haut), pas la simple
  consultation du menu.

Donc la taille du bloc "munitions spéciales" varie selon l'arme (5
pour Mk.2/Mosin avec standard+4 émotives, 3 pour les fusils à pompe,
vraisemblablement 4 pour le MGL-140 une fois testé) - pas une constante
universelle de 5. Rappel utilisateur : d'autres armes encore non
débloquées pourraient avoir le même genre de munitions multiples,
à identifier au fur et à mesure.

**Contre-exemple : la "famille créée d'un coup" n'est pas systématique
(2026-09-06, save `BLJM67001G6A99ACCA`, partie originale #0, Acte 2)** :
sur cette save, Double Canon possédé mais M870 Modifié pas encore.
Dans le pool 12GA partagé : slot 27 (Chev. 00) = 22 et slot 29
(Ann. Vort.) = 20 existent, mais **slot 28 (Balle) est totalement
absent** (`65535`, jamais créé). Si l'achat d'un type créait toute la
famille d'un coup (comme observé pour Rage/Mk.2), les 3 slots
devraient soit tous exister soit tous être vides - pas un mélange.
Hypothèse révisée : chaque type de munition serait en fait créé
**indépendamment**, dès sa toute première obtention (achat OU
ramassage sur le terrain) - le Chev. 00 vient probablement chargé par
défaut avec l'arme, l'Ann. Vort. aurait été ramassée en jeu, et aucune
Balle n'a encore été ni achetée ni trouvée sur cette save. Le cas
Rage/Mk.2 (où les 4 slots apparaissent ensemble pour un seul achat)
pourrait être un mécanisme spécifique à l'interface d'achat groupé du
Mk.2/Mosin, pas une règle générale à toutes les familles de munitions.
Conclusion : pas de règle fiable unique, chaque famille/arme doit être
vérifiée au cas par cas.

**Correction majeure : la position DANS le groupe est bien figée
(2026-09-06, meme save, nouvelle sauvegarde `BLJM67001G6A9D6100`)** :
test décisif - achat de "Balle" (12GA) sur la save où elle manquait
(slot 28 vide, Chev.00/Ann.Vort. déjà présents aux slots 27/29 depuis
longtemps, beaucoup d'autres choses changées entre-temps : Prise
Scanner récupérée, munitions d'autres armes consommées). Résultat :
`slot 28` passe de `65535` à `100` - **elle se place exactement à
l'emplacement prévu entre ses deux voisins**, pas à la fin du tableau
comme l'hypothèse "liste qui grandit simplement" le prédisait.

Ça infirme l'hypothèse juste au-dessus et confirme au contraire que la
position relative de chaque type de munition **au sein de son groupe**
est bien figée à l'avance (structure fixe par arme, cote code du jeu),
même si la valeur reste `65535` (pas `0`) tant que la munition n'a
jamais été obtenue. Le sentinel `65535` ne veut donc pas dire "pas
encore reservé" mais juste "jamais obtenu" - la place existe déjà
conceptuellement, elle attend simplement sa valeur.

**Donc, réponse à la question "les munitions spéciales sont-elles
fatalement juste après l'arme concernée ?" : oui**, une fois le groupe
de cette arme commencé (première munition de ce groupe obtenue), les
autres types du même groupe obtenus plus tard prennent leur place
prédéfinie dans ce même groupe contigu, peu importe le délai entre les
deux. Ce qui reste imprévisible, c'est uniquement **où le groupe
commence** dans le tableau de 68 emplacements (dépend de l'ordre
chronologique réel d'activation de cette arme sur cette partie
précise) - pas l'agencement interne une fois le groupe démarré.

## Correction des compteurs cibles (2026-09-06)

L'utilisateur a recroisé le total canonique du jeu avec un guide
d'inventaire externe et le comptage utilisé par le jeu lui-même :

- **70 armes** (déjà notre valeur, confirmé - inclut grenades, C4,
  Claymore, poupées Mantis/Sorrow, etc. comme "armes"). Le chiffre 69
  qu'on croise parfois vient de l'emblème Little Gray dans la version
  originale (avant l'ajout du 1911 Custom, cas particulier lié à un mot
  de passe).
- **18 accessoires** (Custom Parts), pas 20 comme on l'avait
  auparavant (source fandom wiki, imprécise sur ce total) : Masterkey,
  GP30, XM320, 6 silencieux (Operator/Mk.23/1911 Custom/P90/M10/M4/M14 -
  attention la liste utilisateur n'en compte que 6 alors qu'elle nomme
  7 armes, a verifier), Dot Sight, D.Sight (MP7), Scope, Laser Sight,
  F.Light (H.G.), F.Light (L.G.), Fore Grip A, Fore Grip B.
- **18 objets** (13 équipements + 5 consommables) : Solid Eye, Camera,
  Metal Gear Mk.II/III (compté comme UN SEUL objet - le Mk.III
  remplace le Mk.II en jeu, jamais les deux en meme temps, pas un
  deuxieme objet de collection independant), Cardboard Box, Drum Can,
  iPod, Signal Interceptor, Bandana, Stealth Camouflage, Cigarettes,
  Muña, Syringe, Scanning Plug, puis Ration/Noodles/Regain/
  Pentazemin/Compress.

Corrigé dans `gui_app.py` : `WeaponsPanel.TARGET_ACCESSORIES` passé de
20 à 18 ; nouveau `TARGET_OBJECTS = 18` avec un `ratio_fn` dédié
(`_objects_ratio`) qui exclut "Batterie (Solid Eye)" du compte (jauge
séparée, pas un objet canonique) - avant ce correctif, le panneau
Objets affichait un total dynamique de 20 (18 + Mk.II/Mk.III splittés
en 2 tuiles + Batterie en plus), incohérent avec le vrai total de 18.

Piste ouverte : la liste des 18 accessoires donnée par l'utilisateur
mentionne "SUP. (Mk.23)" comme accessoire distinct, mais on n'a
toujours pas trouvé son ID dans le fichier (voir plus haut, section
"munitions spéciales" - tests d'achat/usage n'ont montré aucun
changement détectable dans aucune table connue, ni pour un achat isolé
ni pour un aller-retour usage+rachat).

## TODO - liste pour la prochaine partie de test dédiée (2026-09-06)

À faire lors d'une prochaine partie fraîche dédiée aux tests, pour
maximiser les identifications et passer un max de choses en confiance
haute :

**Armes/objets jamais identifiés :**
- `0x1d` (arme #29) - bonus lié à la 2e fin de partie ou plus, identité
  toujours inconnue (pas Race Gun, contre-exemple trouvé).
- `0x4e` (arme #78) - bonus lié à la 1ère fin de partie, identité
  toujours inconnue (pas Race Gun non plus - c'est le 1911 Modifié/1911
  Custom).
- `0x5c`/`0x5d`/`0x5e` ("le trio") - se débloquent ensemble dès la 1ère
  fin de partie, toujours non identifiés.
- Race Gun, Type 17, D.E. Long Barrel, Patriot, Tanegashima - aucun ID
  trouvé pour l'instant parmi les armes de la liste utilisateur.
- `0x19` (objet) - déjà à 1 dès le tout début d'une partie fraîche
  (Acte 1), absent du sac à dos affiché en jeu - mystère total.
- Silencieux Mk.23 - achat/usage ne laisse aucune trace détectable
  nulle part, à retester avec plus de rigueur (capture DP avant/après
  pour confirmer que l'achat passe bien).
- Camo Cadavre (Octocamo) - pas dans le tableau d'armes ni objets, need
  un diff isolé avant/après avoir dépassé 41 morts sur UNE MÊME partie
  continue (mourir 41+ fois délibérément, sauvegarder juste avant et
  juste après le seuil).
- FaceCamo Doré, "Doré" (FaceCamo), Gilet Doré, Costume d'Altaïr - liés
  à la détection d'une sauvegarde Master Collection - test
  suppression/ajout de la save MC Vol.1 tenté mais pas concluant
  (le FaceCamo restait présent), à refaire plus rigoureusement avec un
  vrai diff avant/après.
- Les 21 motifs Octocamo - aucun ID de sauvegarde connu pour aucun des
  21 (gros chantier, voir section dédiée plus haut).

**Confiance basse à confirmer/corriger :**
- `0x08` (D.E.) et `0x29` (DSR-1) - obtenus ensemble, jamais isolés
  individuellement, attribution par convention.
- `0x02`/`0x03`/`0x0a`/`0x0b`/`0x4d` (Mk.2 Pistol/Operator/1911
  Modifié/Thor .45-70/Silencieux Operator) - lot Otacon complet,
  attribution par simple ordre d'ID croissant, aucune certitude réelle
  sur qui est qui au sein du lot.
- "Destiny's Call" (chanson, `0x5c` dans SONG_NAMES - attention,
  numérotation différente du "trio" d'armes) - titre exact incertain.

**Munitions spéciales (sujet secondaire, optionnel) :**
- Confirmer si le Mosin-Nagant a bien le même schéma de bloc que le
  Mk.2 (standard/Hurlement/Rire/Rage/Pleurs) en testant Rage/Peur/
  Pleurs pour le Mosin sur une partie où son bloc n'est pas encore créé.
