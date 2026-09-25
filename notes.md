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

**Reconfirmation (2026-09-10)** : après une période où l'ID du Costume
d'Altaïr avait été retiré faute de certitude (tuile indicative
"toujours verrouillée" dans `read_outfits`), un test isolé propre
(seule case du tableau d'items à bouger entre deux saves comparées, 0x1d
`65535` -> `1`) confirme bien `0x1d` = Costume d'Altaïr, pile entre les 3
déguisements et le Costume de Snake (`0x1e`) - cohérent avec l'hypothèse
d'origine ci-dessus. Tuile indicative retirée de `read_outfits`, `0x1d`
ajouté à `OUTFIT_NAMES` en confiance haute.

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

## Session du 2026-09-09 : FIM-92A retrouvé, Metal Gear Solid Main Theme confirmé

**FIM-92A** (`0x30`) : l'utilisateur remarque que l'app affiche son
FIM-92A comme déjà utilisable (état 2) alors qu'il est encore verrouillé
en jeu (état 1) - l'ancien ID `0x43` (jamais confirmé individuellement,
hérité tel quel de la table Cheat Engine d'origine) était donc faux.
Il déverrouille volontairement le FIM-92A ; sur cette fenêtre, 3 armes
passent de 1 à 2 dans le fichier (`0x07` GSR, `0x0f` G18C, `0x30`), mais
GSR et G18C avaient déjà été déverrouillés et confirmés indépendamment
par l'utilisateur sur d'autres saves - seul `0x30` est une transition
nouvelle et inexpliquée sur cette save, coïncidant exactement avec le
déverrouillage du FIM-92A. Confiance haute. `0x30` était étiqueté
"Sachet à gaz somnifère" (confiance basse, attribution par
élimination/convention lors du swap avec la Lunette de fusil le
2026-09-07) - identité de nouveau inconnue. Ancien `0x43` retiré de
`WEAPON_NAMES`/`WEAPON_CATEGORIES`, redevient "Non identifiée".

**Metal Gear Solid Main Theme** (`0x3f`, chanson) : passée en confiance
haute - nom confirmé par popup en jeu au déblocage, à l'endroit attendu
(Acte 5, Outer Haven, sous la trappe). Absente de la source externe de
référence (metalgeargeneration.free.fr) mais confirmée directement.

**D.E.** (`0x08`) : passé en confiance haute - test isolé propre, seul
`0x08` bouge (`0x29`/DSR-1 reste inchangé) parmi les transitions non
déjà expliquées sur la fenêtre de test. DSR-1 (`0x29`) reste en
confiance basse, toujours pas isolé.

**M60E4** (`0x23`) : passé en confiance haute - jamais testé isolément
auparavant, seul cet ID bouge parmi les transitions non déjà expliquées
sur la fenêtre de test.

**MK.17, XM8, XM25, FGM-148 Javelin, Grenade au phosphore blanc** :
reconfirmés chacun par une transition isolée cohérente (déjà en
confiance haute depuis des tests antérieurs) - aucun changement de
statut, juste des confirmations supplémentaires.

**Sachet à gaz somnifère** (`0x43`) : CONFIANCE BASSE, attribution par
convention/déduction (PAS un test isolé) - `0x43` est immédiatement
adjacent au bloc continu d'explosifs/grenades/lance-roquettes `0x2e`-
`0x42` (Claymore, Mine à gaz somnifère, C4, puis ce slot juste après).
Identité plausible par position dans la table, mais non confirmée par
une transition observée. À retester isolément si l'occasion se
présente (obtenir/utiliser le Sachet sur une save où l'effet est
observable).

## TODO - liste pour la prochaine partie de test dédiée (2026-09-06)

À faire lors d'une prochaine partie fraîche dédiée aux tests, pour
maximiser les identifications et passer un max de choses en confiance
haute :

**Armes/objets jamais identifiés :**
- `0x1d` (arme #29) - bonus lié à la 2e fin de partie ou plus (pas Race
  Gun, contre-exemple trouvé). **CONFIANCE BASSE (2026-09-09) : pari de
  l'utilisateur pour "Tanegashima"**, PAS un test isolé - 0x1d est pile
  au milieu d'un bloc continu de fusils d'assaut (M4 0x18 à XM8 0x1f,
  sans autre trou), cohérent avec une arme bonus de complétion. À
  confirmer par un test isolé si l'occasion se présente.
- `0x4e` (arme #78) - bonus lié à la 1ère fin de partie (pas Race Gun,
  pas le 1911 Modifié). **CONFIANCE BASSE (2026-09-09) : pari de
  l'utilisateur pour "Silencieux Mk.23"**, PAS un test isolé - 0x4e est
  pile entre le Silencieux Operator (`0x4d`) et le Silencieux 1911
  (`0x4f`) dans le bloc continu d'accessoires `0x4a`-`0x5b`. Ajouté à
  `DREBIN_LOCK_EXCEPTIONS` par précaution/analogie avec le Silencieux M4
  (même situation potentielle, point rouge "verrouillé" retiré), mais
  pas confirmé par un test dédié pour cet ID précis. À confirmer par un
  test isolé si l'occasion se présente.
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
- FaceCamo Doré, "Doré" (FaceCamo), Gilet Doré - liés à la détection
  d'une sauvegarde Master Collection - test suppression/ajout de la
  save MC Vol.1 tenté mais pas concluant (le FaceCamo restait présent),
  à refaire plus rigoureusement avec un
  vrai diff avant/après.
- Les 21 motifs Octocamo - aucun ID de sauvegarde connu pour aucun des
  21 (gros chantier, voir section dédiée plus haut).

**Confiance basse à confirmer/corriger :**
- `posters_vus` (`0x1aa`, MGS4.SAV) - confirmé par un test isolé le
  2026-09-05 (transition 0->1), mais reste bloqué à 0 malgré un poster
  "Akina" regardé le 2026-09-09 (confirmé par l'utilisateur, avec succès
  Steam dédié à la clé pour "avoir regardé tous les posters" - donc un
  état persisté existe forcément quelque part). Le test du 2026-09-09
  n'était pas isolé (changement de zone entre les deux saves comparées),
  donc pas de nouvelle piste trouvée ailleurs non plus. Hypothèses : ce
  champ suit un autre type d'affiche (PMC ?) et pas les posters "Akina",
  ou le mécanisme réel est un bitmask par poster plutôt qu'un simple
  compteur cumulatif. À revalider avec un vrai test isolé (save juste
  avant/après un poster "Akina" précis, sans changer de zone entre les
  deux). Total confirmé par l'utilisateur : 4 posters "Akina" à trouver
  dans le jeu, donc si ce champ est le bon, l'affichage cible est "X/4".
  **Nouvelle piste (2026-09-10)** : `0x636c` passe de `00` à `02` sur un
  test où l'utilisateur passe de 0 à 2 posters vus d'un coup (en
  changeant de zone, seul moyen de forcer un flush) - correspondance
  exacte avec le delta observé, hors de toutes les zones de bruit connu
  liées au changement de zone (`0x0aa4`-`0x1b2b`, `0x8344` et voisins).
  `0x634c` passe aussi de `00` à `01` juste avant, peut-être un flag "au
  moins un poster vu" distinct du compteur.
  **PISTE INFIRMÉE (2026-09-10)** : l'utilisateur a ensuite vu les 4
  posters du jeu et obtenu le succès Steam correspondant, mais `0x636c`
  reste bloqué à `02` (et `0x634c` à `01`) malgré un nouveau changement
  de zone (donc un flush a bien eu lieu). Recherche élargie (tout octet
  passé de `0` à `4`, puis tout octet passé de `0` à `1` depuis le
  backup à 0 poster, hors zones de bruit connues) : aucun candidat
  clair ne ressort - soit un gros paquet d'une vingtaine d'octets à
  `0x51d8`-`0x51fe` (trop nombreux, probablement lié aux multiples
  checkpoints franchis entre-temps, pas aux posters), soit un groupe de
  7 (pas 4) autour de `0x6500`-`0x65f4`.
  **Nouvelle hypothèse à tester (proposée par l'utilisateur)** : plutôt
  qu'un compteur unique 0-4, le jeu pourrait stocker 4 flags séparés
  (un par poster, chacun 0->1 indépendamment), le succès se déclenchant
  quand les 4 valent 1. Pas testable avec les données actuelles (aucun
  backup de l'état intermédiaire à 2 posters, donc impossible de savoir
  quels flags progressent entre 0->2 puis 2->4). À reprendre sur une
  toute nouvelle partie, en sauvegardant (avec backup local à chaque
  fois) après CHAQUE poster individuellement pour isoler les flags un
  par un plutôt qu'en bloc.
  **Suite et 2e infirmation (2026-09-12/13, autre partie n°6)** : la
  méthode "un backup par poster" a bien été appliquée cette fois-ci
  (saves à 0, 2, 3 et 4 posters, toutes comparées deux à deux). Un
  cluster prometteur avait émergé entre les saves à 0 et 2 posters :
  `0x634c` et `0x6418` passant tous deux de `0` à `1`, seuls candidats
  après filtrage exhaustif du bruit de zone (plusieurs nouvelles zones
  de bruit générique découvertes au passage : `0x51ad`-`0x5216`,
  `0x6890`-`0x6a00` rempli de `162` répété en masse, `0x4ba4`/`0x4bb4`
  déjà vus bouger lors du test "copain avec les rebelles"). Mais :
  - Entre 2 et 3 posters (même nom de zone affiché, sous-zone
    différente, 657 octets de bruit générique mais un vrai flush a eu
    lieu) : AUCUN changement dans le cluster, et aucun autre candidat
    fiable trouvé après filtrage (un candidat isolé `0x3ab` s'est
    montré non-monotone donc écarté).
  - Sur une toute nouvelle save où l'utilisateur affirme avoir les 4
    posters, tant que le nom de zone affiché ne changeait pas, le
    cluster restait figé - cohérent avec "pas encore flush".
  - Mais après un vrai changement de zone nommée (confirmé), le
    cluster est resté figé à l'identique (`0x634c`=1, `0x6418`=1,
    `0x636c`=0, `0x6414`=0) malgré les 4 posters. Le flush a donc bien
    eu lieu (changement de zone réel), et RIEN n'a bougé.
  **Conclusion : piste du cluster `0x634c`/`0x636c`/`0x6414`/`0x6418`
  définitivement infirmée.** Le changement observé sur `2F98B` (session
  du 2026-09-10, `0x636c` 0->2 et `0x6414` 0->1 entre 2 et 4 posters)
  était très probablement une coïncidence liée à un autre événement de
  progression de cette partie-là, pas causé par les posters. Par
  extension, `0x634c`/`0x6418` (changés entre 0 et 2 posters sur la
  partie du 2026-09-10) sont eux aussi suspects de coïncidence, malgré
  leur stabilité apparente sur plusieurs saves. À ce stade, aucune
  piste fiable n'a été trouvée pour ce compteur - repartir de zéro si
  l'occasion se représente, idéalement avec un seul poster vu par test
  et le moins d'autres actions possible entre les saves comparées.
- **Flashbacks distincts vus (2026-09-13)** : `flashbacks_vues` (`0x5a34`)
  est un compteur d'OCCURRENCES total (peut revoir le même flashback
  plusieurs fois), pas le nombre de flashbacks distincts vus au moins
  une fois - les deux ne sont pas déductibles l'un de l'autre. Piste
  trouvée pour ce 2e nombre : zone `0x5a44`-`0x5a64` (au moins, à
  confirmer si elle va plus loin), entièrement à `0` sur une partie
  neuve, remplie de bits épars sur une partie avancée (191 bits actifs
  sur 264 disponibles pour une save de la partie n°6, playtime 16199s).
  Comportement cohérent avec un bitmask "flashback distinct vu" : reste
  PARFAITEMENT stable sur toute une partie (580FF à 64E18) pendant que
  `flashbacks_vues` grimpe de 235 à 255 occurrences - donc uniquement
  des revisionnages de flashbacks déjà vus sur cette période, aucun bit
  n'a dû changer, et aucun n'a changé. Pas encore de test isolé (un
  seul nouveau flashback entre deux saves) pour confirmer la
  granularité exacte bit-par-bit. Nombre total réel de flashbacks dans
  le jeu incertain - le "65" avancé initialement par l'utilisateur
  était une erreur ; un forum MGS non officiel mentionne plutôt ~245
  (chaque "flashback" au sens large contiendrait 6 à 8 images/moments
  qui compteraient chacun séparément), plus cohérent avec nos
  observations mais à confirmer. À reprendre sur une partie toute
  fraîche : comparer une save juste avant/après avoir vu UN SEUL
  flashback pour vérifier qu'exactement un bit change, et déterminer
  les vraies limites de la zone.
- `0x29` (DSR-1) - obtenus ensemble avec le D.E. à l'époque (0x08 et 0x29
  flushaient en même temps), attribution par convention, toujours pas
  isolé depuis. **D.E. (`0x08`) passé en confiance haute le 2026-09-09** :
  test isolé propre, seul 0x08 bouge (0x29 reste inchangé) parmi les
  transitions non déjà expliquées par ailleurs sur cette fenêtre.
- `0x02`/`0x03`/`0x0a`/`0x0b`/`0x4d` (Mk.2 Pistol/Operator/1911
  Modifié/Thor .45-70/Silencieux Operator) - lot Otacon complet,
  attribution par simple ordre d'ID croissant, aucune certitude réelle
  sur qui est qui au sein du lot.
- "Destiny's Call" (chanson, `0x5c` dans SONG_NAMES - attention,
  numérotation différente du "trio" d'armes) - titre exact incertain.
- `0x43` (Sachet à gaz somnifère) - attribution par convention/déduction
  (position dans la table, immédiatement adjacent au bloc continu
  d'explosifs/grenades/lance-roquettes `0x2e`-`0x42`), PAS un test isolé.
  À confirmer/infirmer avec un vrai test si l'occasion se présente.
- `0x1d` (Tanegashima) - pari de l'utilisateur, PAS un test isolé -
  position pile au milieu du bloc continu de fusils d'assaut `0x18`-
  `0x1f`, cohérent avec une arme bonus de complétion (2e fin de partie
  ou plus). À confirmer/infirmer avec un vrai test si l'occasion se
  présente.
- `0x4e` (Silencieux Mk.23) - pari de l'utilisateur, PAS un test isolé -
  position pile entre Silencieux Operator (`0x4d`) et Silencieux 1911
  (`0x4f`). Point rouge "verrouillé chez Drebin" retiré par précaution
  (voir `DREBIN_LOCK_EXCEPTIONS`), non confirmé par un test dédié. À
  confirmer/infirmer avec un vrai test si l'occasion se présente.

**Munitions spéciales (sujet secondaire, optionnel) :**
- Confirmer si le Mosin-Nagant a bien le même schéma de bloc que le
  Mk.2 (standard/Hurlement/Rire/Rage/Pleurs) en testant Rage/Peur/
  Pleurs pour le Mosin sur une partie où son bloc n'est pas encore créé.

## Chansons débloquées "à vie" au niveau du compte, pas par partie (2026-09-13)

Sur une toute nouvelle partie fraîche (partie n°0, Acte 1, 155s de jeu),
5 chansons apparaissent déjà "owned" dans le fichier : Subsistence
Action, Gekko, Desperate Chase, Midnight Shadow, Mobs Alive - toutes
déjà présentes dans l'iPod en jeu (confirmé par l'utilisateur pour
Desperate Chase). Ce sont exactement les chansons déjà notées
"suspectes" plus haut (absentes de la source de référence externe,
`0x5f`/`0x60`/`0x61`/`0x62` + `0x55` Subsistence Action) - PAS un bug
d'identification : ces chansons ont probablement été débloquées sur
une partie précédente de l'utilisateur et restent acquises à vie,
peu importe la partie en cours. Cohérent avec un mécanisme déjà
observé ailleurs (Costume d'Altaïr `0x1d` et l'arme bonus `0x4e`,
tous deux liés à une fin de partie complétée puis disponibles sur
les parties suivantes). Ne pas reconfondre ça avec un vrai souci
d'ID si ça ressort dans une future session - le comportement de
l'app est correct, c'est le jeu qui fonctionne ainsi.

## Bitmask des flashbacks confirmé bit-par-image (2026-09-13)

Suite de la piste ouverte plus haut ("Flashbacks distincts vus") : deux
tests isolés propres sur une partie neuve (partie n°0, saves à 0, puis 1,
puis 2 flashbacks vus par l'utilisateur, en évitant tout autre
changement significatif entre chaque save) confirment le mécanisme :

- 1er flashback vu : `flashbacks_vues` 0->3, et exactement 3 bits
  s'activent dans la zone `0x5a44`-`0x5a64` (tous les 3 dans le même
  octet `0x5a64`, bits 3/4/5).
- 2e flashback vu : `flashbacks_vues` 3->8 (+5), et exactement 5
  nouveaux bits s'activent (répartis sur 5 octets différents cette
  fois : `0x5a49`, `0x5a4a`, `0x5a4b`, `0x5a4d`, `0x5a4e`, un bit
  chacun).

Confirmation solide : `flashbacks_vues` compte les IMAGES individuelles
composant chaque flashback (pas les scènes au sens narratif - un
flashback = plusieurs images, ici 3 puis 5), et le bitmask suit
exactement la même granularité, un bit par image, réparti dans
l'ensemble de la zone sans ordre groupé apparent par flashback. Les
mêmes bits (`0x5a64` bits 3-4-5) ont aussi été vérifiés stables et
actifs sur plusieurs saves bien plus avancées (parties n°5/6/7, NG+
inclus) - cohérent, puisque ce premier flashback est vu tôt et
forcément déjà passé sur ces runs. Poursuivre les tests isolés au fil
de la partie pour cartographier davantage de bits individuels, et
déterminer la taille réelle totale de la zone (pas encore confirmée
au-delà de `0x5a64`).

### Total réel confirmé via le trophée "Flashback Mania" (2026-09-19)

L'utilisateur a obtenu le trophée "Flashback Mania" (tous les flashbacks
vus) sur sa save la plus avancée (`BLJM67001G6AAEA1C9`, `flashbacks_vues`
= 705 occurrences cumulées). Lecture de la zone `0x5a44`-`0x5a64` sur
cette save, plus une vérification large au-delà (jusqu'à `0x5ac0`) pour
confirmer la borne :

- Tout ce qui suit `0x5a64` est à `0` - la zone fait bien exactement
  **33 octets** (`0x5a44` à `0x5a64` inclus), soit **264 emplacements de
  bits**, borne désormais confirmée (plus seulement "au moins").
- **238 bits actifs sur 264**, et ce total ne peut plus augmenter (le
  trophée signifie que tous les flashbacks du jeu ont été vus au moins
  une fois). Les 26 bits jamais activés dessinent un motif net et stable :
  deux octets entièrement à zéro (`0x5a46`, `0x5a47`) et trois octets
  partiels (`0x5a45` = 4/8, `0x5a48` = 4/8, `0x5a64` = 6/8) - cohérent
  avec des emplacements de bits structurellement inutilisés (padding),
  pas des flashbacks restant à voir.

**Le nombre réel total d'images de flashback dans le jeu est donc 238**
(ni les ~245 avancés par un forum non officiel, ni les 65 de l'estimation
initiale de l'utilisateur). Reste non résolu : la cartographie bit ->
flashback narratif précis (quel bit appartient à quelle scène/quel Acte),
qui nécessiterait de reprendre les tests isolés flashback par flashback
sur une partie fraîche - gros chantier, à faire uniquement si l'occasion
se représente. Sans cette cartographie, on peut déjà afficher un compteur
global fiable "X / 238" mais pas encore un onglet Flashback détaillé par
Acte/scène.

## Trainer mémoire live : formule fixe du tableau objets retrouvée (2026-09-22/23)

Chantier parti du bug rapporté par l'utilisateur : "One Night in Neo Kobe
City" (`0x4c`) apparaît systématiquement verrouillée sur les 76 saves
locales détectées automatiquement (via `save_finder`), y compris la save
la plus avancée (trophée "Flashback Mania" obtenu) - alors que
l'utilisateur confirme la posséder en jeu. Hypothèse initiale : mapping
d'ID faux. Verdict final : **le mapping est correct**, voir plus bas.

### Chaîne de pointeurs zexk/bbtracker infirmée pour les compteurs d'objets

Le dépôt externe `zexk/bbtracker` (docs/mgs4_research.md, licence MIT,
déjà cité plus haut) documente une chaîne `module base + 0x1C28B28 ->
linkvarbuf` (et une variante `varbuf` à `linkvarbuf - 0x2800`, plus 2
"snapshots" à `+0x1C28B30`/`+0x1C28B40`), avec la même disposition interne
que `MGS4.SAV`. Testé en direct sur `live_trainer.py` (nouveau script,
voir son docstring) : **aucun des 4 buffers ne suit le stock de Ration en
temps réel** - tous restent figés pendant qu'un ramassage/consommation
change réellement le stock affiché en jeu. Probablement des buffers de
sérialisation (préparés pour la sauvegarde), pas l'état de jeu actif.
Cause du bug initial confondu avec un problème de mapping : on cherchait
au mauvais endroit en mémoire, pas une erreur d'ID.

### Scan mémoire "valeur exacte" (technique Cheat Engine)

Faute de mieux, scan direct de toute la mémoire accessible en écriture du
process `mgs4.exe`, affiné sur plusieurs changements réels du stock de
Ration en jeu (1->2->3->4->5->6, un changement à la fois, intersection des
candidats à chaque étape). Piège rencontré : le scan initial se limitait
aux régions `MEM_PRIVATE` (heap classique) et ne trouvait jamais la bonne
adresse (0 survivants après plusieurs affinages) - il manquait ~280 Mo de
mémoire `MEM_MAPPED`, cohérent avec de la RAM de console émulée (le jeu
tourne très probablement via un émulateur, cf. mention `WINEDLLOVERRIDES`
dans mgs4_research.md). Une fois cette zone incluse, convergence de
681 231 candidats à 4 en 4 affinages, puis 1 seul en confirmant un
changement supplémentaire : `module_base + 0x1D8436C`.

Détail important : cette adresse est dans une région `MEM_IMAGE` dont
`AllocationBase` correspond exactement à la base du module - donc une
variable globale statique du jeu (section .data/.bss), **stable d'un
lancement à l'autre** (contrairement à une adresse heap qui change à
chaque redémarrage à cause de l'ASLR).

### Formule générale retrouvée via le fichier MGS4.CT (Cheat Engine, fourni par l'utilisateur)

Le fichier `MGS4.CT` (racine du repo, non versionné) contient deux scripts
Auto Assembler ("Songs Backup"/`objSongs` et un 2e appelé `objItems`) qui
désassemblent une fonction de lookup générique du jeu (bound check
`cmp ecx,62` = `0x62`, exactement `ITEM_STATE_COUNT-1`). Les deux lisent
`[base_struct+0x14]` pour l'état d'un objet. Formule complète :

```
struct_base(id) = 0x1D84310 + id*0x48
etat(id)        = struct_base(id) + 0x14
```

Vérifiée par calcul exact : `struct_base(0x01) + 0x14 = 0x1D8436C`,
**identique** à l'adresse de Ration retrouvée indépendamment par scan.
Aucun décalage d'ID (contrairement à une autre section du même fichier
CT, "Items -- Unknown"/`+48*N`, qui semble utiliser une convention décalée
de -1 et s'est révélée non fiable/non vérifiée - à ignorer au profit de
cette formule-ci, dérivée du désassemblage réel du code du jeu).

Cette formule couvre les 99 entrées du tableau objets (objets généraux,
gilets, statuettes, chansons, tenues - tout ce que `mgs4save.py` lit via
`read_item_states`), adresse fixe, pas de pointeur à suivre. Intégrée
dans `live_trainer.py` (`item_state_rva()`). Le tableau armes (0x1d4 dans
le fichier de save, 95 entrées) n'a PAS d'équivalent retrouvé pour
l'instant - aucun script `objWeapon`-like trouvé dans le CT, toujours sur
l'ancien mécanisme (`varbuf`) non fiable pour ce tableau.

### "One Night in Neo Kobe City" : mapping confirmé, condition infirmée

Test décisif : `write_item(0x4c, 1)` en live sur une save fraîche ->
la chanson apparaît immédiatement dans l'iPod en jeu. **Le mapping `0x4c`
est donc correct**, confirmé en confiance haute. Séance de vérification
plus large le même jour : verrouillage manuel des 38 chansons, sauvegarde,
confirmation via `MGS4SaveStats` (lecture du fichier) que les 38
affichent bien 0 - donc l'écriture live se propage correctement au
fichier de save. L'utilisateur a ensuite légitimement débloqué 37/38
chansons en jouant (tout sauf Big Boss, volontairement laissé de côté
pour ne pas fausser le succès Steam associé), confirmées persistantes
dans le fichier de save.

Seule exception : "One Night in Neo Kobe City" reste non obtenue sur la
save avancée malgré plusieurs passages où l'utilisateur affirme avoir
fouillé un SMP après l'avoir braqué (l'action documentée dans
`SONG_CONDITIONS`). Condition marquée infirmée dans le code - source
externe (metalgeargeneration.free.fr) jamais vérifiée par un test isolé
de notre côté avant aujourd'hui. Vraie condition d'obtention encore
inconnue, à chercher en jouant (piste ouverte).

### Tableau armes : pas de formule générale, IDs confirmés un par un (2026-09-23)

Contrairement au tableau objets, aucune formule fixe trouvée pour les 95
armes. Le fichier `MGS4.CT` a une section "🧬Weapons" (foulée `0x18`,
Current à `+0`/Max à `+2`, comme espéré), mais indexée sur un pointeur
capturé dynamiquement (`pItems-2598`) et surtout sur une **numérotation
différente de la nôtre** : leur "AK102" à l'ID `0x11` est en fait notre
"Masterkey" (confirmé par test isolé il y a longtemps). Tentative de
formule "même ID que le fichier de save, foulée `0x18`" : validée par
construction pour MK.17 (puisque dérivée de son adresse), mais **infirmée
par un vrai test** - "Mine à gaz somnifère" (`0x41`) ramassée sur le
terrain (transition franche jamais-eue -> utilisable) sans que l'adresse
calculée par la formule ne bouge d'un octet. Donc pas de raccourci
général possible pour l'instant, à refaire par arme via scan mémoire.

**MK.17 (`0x1e`)** confirmé (RVA `0x1D82EEA`) : scan sur transition réelle
verrouillé(1)->utilisable(2) après déverrouillage chez Drebin, narrowing
2 894 191 -> 410 -> 1 seul candidat en filtrant sur la zone stable de
l'image du module (même critère que pour Ration : `AllocationBase` ==
base du module).

**Tentative sur la Mine à gaz somnifère (`0x41`), flag "possédée" non
trouvé** : ramassée sur le terrain, "poser puis reprendre" ne redonnant
aucune transition exploitable (le flag ne redescend pas quand le stock
tombe à 0 - cohérent avec "possession acquise une fois pour toutes").
51 candidats trouvés proches de la zone armes connue (valeur `2`, filtre
"zone stable + proche RVA MK.17") mais aucun n'a bougé après avoir posé
l'unique exemplaire - piste abandonnée pour cette session.

**Table MUNITIONS distincte trouvée en contournant le problème** :
achat de 36 mines puis pose de 2 (36->34), scan classique (pas de filtre
de proximité nécessaire cette fois) : 248 089 -> 3 candidats -> 1 seul
stable dans l'image du module. RVA confirmé : `0x1D82420`. Cohérent avec
le tableau `0x352` "munitions par emplacement d'équipement" déjà connu
côté fichier de save (tableau séparé du flag possession/état) - voir
`CONFIRMED_WEAPON_AMMO_RVAS` dans `live_trainer.py`. Le flag "possédée"
de cette arme reste non localisé.

**Correction (2026-09-23, même session)** : premier test jugé "écriture
sans effet" (forcer à 99 ne changeait rien à l'affichage), mais en fait
l'écriture est bonne - il manquait juste le bon déclencheur. Une fois
l'utilisateur ayant **équipé la mine**, l'affichage s'est mis à jour à
99. Le HUD/inventaire ne se resynchronise donc qu'à l'équipement de
l'arme concernée, pas en continu ni immédiatement après l'écriture -
même famille de comportement que les posters/Prise Scanner déjà
documentés plus haut (états qui ne "flushent" qu'à un déclencheur
précis, pas en temps réel). Adresse confirmée fiable en lecture ET
écriture au final. Leçon pour la suite : avant de conclure "l'écriture
ne marche pas" sur un champ, tester un déclencheur de rafraîchissement
plausible (équiper/déséquiper, ouvrir le menu concerné, changer de zone)
avant d'abandonner la piste.

Bilan méthode pour la suite : le scan "valeur exacte" + filtre "zone
stable de l'image du module" (`AllocationBase` == base du module) marche
très bien pour n'importe quel compteur qui varie (munitions, objets en
stock...), converge en general en 1-2 tours. Pour un simple flag
possession/verrou (0/1/2/65535) qui ne varie qu'une fois dans toute une
partie, c'est plus dur : il faut une vraie transition fraîche (arme
jamais eue -> juste obtenue, ou verrouillée -> débloquée chez Drebin),
pas de méthode de contournement trouvée si la transition a déjà eu lieu
avant le début de la session de recherche.

### Pool de munitions partagé confirmé en mémoire live (2026-09-23)

Le trainer a maintenant une colonne "Munitions" par ligne d'arme (en plus
de l'état/possession), alimentée par `CONFIRMED_WEAPON_AMMO_RVAS` -
grisée/désactivée pour les armes dont l'adresse n'est pas encore connue.

Test décisif suggéré par l'utilisateur : AK-102 (`0x19`) et M4 (`0x18`)
partagent le même pool de munitions en jeu (déjà noté il y a longtemps,
côté fichier de save uniquement - jamais vérifié côté mémoire live avant
aujourd'hui). Scan "valeur exacte" sur une vraie dépense de munitions
(278->270) : 11 014 -> 33 candidats stables dans l'image du module -> 1
seul après le changement réel. **RVA confirmé : `0x1D820C0`, identique
pour les deux armes** - confirme que le partage de munitions par calibre
existe aussi en mémoire live, pas seulement dans le fichier de save.

Suite de la même session : Magazine Playboy (`0x45`) ajoutée pareil (scan
2->11 sur un vrai changement de stock, 1 seul candidat stable après
intersection). RVA `0x1D82480`.

### Points Drebin confirmés via linkvarbuf (2026-09-23)

Contrairement aux quantités par objet/arme (qui vivent dans le tableau
"chaud" `0x1D84310+...`), les Points Drebin sont un champ de stats
globales - et là, `linkvarbuf` (le buffer qu'on avait pourtant écarté
pour Ration) s'avère fiable : lecture ET écriture confirmées par
l'utilisateur (`linkvarbuf+0x1c0`, même offset que `STATS["drebin_actuel"]`
dans le fichier de save). Cohérent avec la doc externe zexk/bbtracker qui
plaçait déjà ce champ à cet offset. Ajouté au trainer comme champ dédié
(pas une entrée de tableau) dans la barre du haut, `read_drebin_points`/
`write_drebin_points` dans `live_trainer.py`.

Point à retenir pour la suite : `linkvarbuf` n'est donc pas un buffer
"mort" partout - juste pour les tableaux objets/armes. Pour un futur champ
de type stats globales (kills, temps de jeu, etc. déjà lus depuis le
fichier de save via `STATS`/`DERIVED_STATS` dans mgs4save.py), vérifier
`linkvarbuf` en premier avant de repartir sur un scan complet - beaucoup
plus rapide si ça marche du premier coup comme ici.

## Session du 2026-09-23 (suite) : onglet Stats, Points Drebin corrélés, refonte UI, nouvelles armes

### Onglet Stats et conversion des compteurs "frames"

Ajout d'un onglet "Stats" au trainer (`StatsTab` dans `live_trainer.py`) :
un champ par entrée de `mgs4save.STATS` (kills, CQC, roulades, temps
divers...), lu/écrit via `linkvarbuf` (même offset que le fichier de
save). Fiabilité en écriture confirmée individuellement seulement pour
`drebin_actuel` - le reste est affiché avec un avertissement explicite
("à vérifier au cas par cas"), pas encore testé champ par champ.

Les champs `*_frames` (temps accroupi, allongé, contre un mur, carton,
baril, jeu) affichent maintenant en plus une conversion lisible
(`~HH:MM:SS`), avec le même taux `FRAMES_PER_SECOND = 60` déjà utilisé
dans `gui_app.py` (`frames_to_hms_approx`) - approximation assumée, pas
une conversion exacte (framerate réellement variable, voir plus haut).

### Points Drebin séparés en deux champs corrélés

Sur suggestion de l'utilisateur : remplacement du champ unique "Points
Drebin" par deux champs distincts et corrélés dans la barre du haut du
trainer - "Actuel" (`drebin_actuel`, solde dépensable) et "Ventes"
(`drebin_total_ventes`, cumul historique). Règles imposées par
l'utilisateur (garde-fou d'édition, pas forcément la logique exacte du
jeu) : `actuel >= ventes` toujours, aucun des deux négatif, et modifier
"Ventes" répercute automatiquement le même delta sur "Actuel" (gagner
plus de ventes historiques augmente d'autant le solde courant).
Implémenté via `write_drebin_actuel`/`write_drebin_total_ventes` dans
`MGS4Live` (retournent `False` sans rien écrire si la contrainte serait
violée). Ces deux champs ont été retirés de l'onglet Stats générique
pour ne garder qu'un seul chemin d'édition validé (les deux UI en
parallèle avaient permis de contourner la contrainte une fois par
erreur, d'où la correction).

### Refonte de l'interface du trainer (retours utilisateur successifs)

Plusieurs passes de nettoyage visuel sur `TableTab` :
- **Ordre des onglets aligné sur `gui_app.py`** : Stats, Armes, Objets,
  OctoCamo, Tenues, Statuettes, Chansons, puis "Non classés" en dernier
  (propre au trainer, n'existe pas dans l'appli principale).
- **Menu déroulant au lieu d'une rangée de boutons** pour l'état de
  chaque ligne - sélectionner une entrée écrit immédiatement (pas de
  bouton "OK" séparé). Réglait aussi les soucis récurrents de largeur de
  colonne qu'on avait eu (bouton row qui écrasait la colonne "Nom").
- **Mode avancé** (case à cocher en haut de la fenêtre) : masque par
  défaut la colonne "Valeur brute" et le contrôle "Définir (brut)"
  (édition d'une valeur arbitraire) - visibles seulement si coché.
  `TableTab.set_advanced()`/`StatsTab.set_advanced()` (no-op pour ce
  dernier, deja tout "brut").
- **Colonnes Quantité/Munitions fusionnées** : à l'origine il y avait une
  colonne d'affichage séparée ET une colonne "Définir quantité/munitions"
  - redondant, le spinbox affiche déjà la valeur courante. Une seule
  colonne "Quantité"/"Munitions" reste, toujours visible (pas réservée au
  mode avancé, contrairement à la valeur brute générique).
- **Suppression de l'entrée "Autre" grisée** dans les menus à choix
  multiples (armes : Non possédée/Verrouillée/Utilisable) - jamais
  sélectionnable, jugée inutile. Remplacée par un menu simplement vide
  (`setCurrentIndex(-1)`) quand la valeur ne correspond à aucun état
  connu ; la vraie valeur reste consultable via "Valeur brute".

### Logique Verrouillé/Déverrouillé généralisée (objets)

Pour tous les onglets objets (pas seulement les consommables), le menu
d'état est maintenant strictement binaire : "Verrouillé" (sentinelle
65535) / "Déverrouillé" (**n'importe quelle autre valeur**, pas une
correspondance exacte sur une valeur figée comme "1"). Contrôlé par le
nouveau paramètre `binary_lock_value` de `TableTab`. Corrige un bug réel
détecté par l'utilisateur : un stock de Ration à 15 ou 42 tombait à tort
dans "Autre" au lieu d'être reconnu comme "Déverrouillé", puisque
l'ancienne logique cherchait une correspondance exacte avec la valeur
fixe "Obtenu=1".

Pour les objets à quantité (`GENERAL_ITEM_QUANTITY_IDS` = Ration/
Nouilles/Régain/Pentazémine/Compresse Arsenal, IDs `0x01`-`0x05`), la
colonne "Quantité" dédiée n'est éditable que si l'état courant est
"Déverrouillé" (désactivée si verrouillé - pas de stock à ajuster tant
que ce n'est pas débloqué).

### Cas particulier : Batterie (Solid Eye)

Signalé par l'utilisateur : la Batterie (`0x3c`) n'a pas d'état
verrouillé/déverrouillé propre - elle suit celui du Solid Eye (`0x06`,
pas de Solid Eye = pas de batterie du tout, même "de base"). Et
contrairement aux autres quantités, l'affichage va de 1 à
`BATTERY_MAX` (6), jamais 0 (une batterie de base est toujours
installée), avec un décalage +1 affichage / -1 stockage par rapport à
la valeur brute (même convention que `read_battery_count()` dans
mgs4save.py). Implémenté comme cas spécial dans `TableTab` via le
paramètre `battery_link=(BATTERY_ITEM_ID, 0x06)` : menu d'état désactivé
(reflet en lecture seule de l'état de Solid Eye), molette Quantité
bornée 1-6, activée seulement si Solid Eye déverrouillé.

### Nouvelles armes confirmées (même méthode scan + filtre "zone stable")

- **Grenade paralysante (`0x36`)** : état RVA `0x1D8366A` (scan sur
  transition réelle verrouillée(1)->utilisable(2) après déverrouillage
  chez Drebin, 2 870 831 -> 512 -> 1 candidat stable). Munitions RVA
  `0x1D82318` (scan sur consommation réelle 5->4, 4 candidats -> 1).
  Écriture de l'état vérifiée par aller-retour mémoire (pas encore
  confirmée visuellement en jeu comme MK.17).
- **MK.17 munitions** : RVA `0x1D82108` (scan sur consommation réelle
  37->29, 2 candidats stables dans la zone connue -> 1 seul confirmé par
  le vrai changement, l'autre étant resté figé à 37 - faux positif
  éliminé).

Bilan actuel des armes couvertes en munitions dans le trainer : Mine à
gaz somnifère, M4/AK-102 (pool partagé), Magazine Playboy, Grenade
paralysante, MK.17, Thor .45-70 - voir `CONFIRMED_WEAPON_AMMO_RVAS` dans
`live_trainer.py`.

## Lot Otacon enfin résolu + chasse "isolation manuelle" sur 54 candidats (2026-09-23)

Technique nouvelle, suggérée par l'utilisateur, complémentaire au scan
"valeur exacte" classique : quand on a une **liste de candidats déjà
"utilisables" (état 2) sans transition disponible pour les départager**
(cas de Thor .45-70, déblocage lié au compte Steam donc plus moyen de
repartir de "jamais eue"), on peut forcer TOUS les candidats à verrouillé
(1) sauf un (ou un petit groupe) à la fois, et demander à l'utilisateur
quelle(s) arme(s) redevient/deviennent utilisable(s) en jeu. Beaucoup
plus rapide que d'attendre une vraie transition de gameplay, et permet
d'identifier plusieurs armes d'un coup si on procède par lots (5 par 5,
puis 1 par 1 seulement si le lot montre un changement - optimisation
proposée par l'utilisateur en cours de route pour ne pas perdre de temps
sur les lots qui ne contiennent que des inconnues).

Départ : scan "valeur exacte" sur `2` (déjà utilisable) filtré sur la
zone stable connue autour de `0x1D82420` → 54 candidats (dont 2 déjà
identifiés par ailleurs : `0x1D82EEA`=MK.17, `0x1D8366A`=Grenade
paralysante, retombés dans le filtre par coïncidence, exclus des tests).

**9 armes nouvellement identifiées** (ajoutées à `CONFIRMED_WEAPON_RVAS`
dans `live_trainer.py`), qui résolvent enfin l'ambiguïté historique du
"lot Otacon" (`0x02`/`0x03`/`0x0a`/`0x0b`/`0x4d` - "attribution par ordre
d'ID croissant, aucune certitude réelle", voir plus haut dans ce
fichier) :

| Arme | ID | RVA état |
|---|---|---|
| Couteau paralysant | `0x01` | `0x1D825DA` |
| Mk.2 Pistol | `0x02` | `0x1D8262A` |
| Operator | `0x03` | `0x1D8267A` |
| 1911 Modifié | `0x0a` | `0x1D828FA` |
| Thor .45-70 | `0x0b` | `0x1D828AA` |
| M4 | `0x18` | `0x1D82D0A` |
| AK-102 | `0x19` | `0x1D82D5A` |
| Mine à gaz somnifère | `0x41` | `0x1D839DA` |
| Magazine Playboy | `0x45` | `0x1D83B1A` |

Seul `0x4d` (Silencieux Operator) du lot Otacon reste non résolu -
absent des candidats testés (pas "déjà utilisable" au moment du scan,
probablement encore verrouillé chez Drebin ou pas encore obtenu).

**43 candidats restent non identifiés** - stables (zone image du module,
donc valables sans rescanner, contrairement à des adresses heap), mis de
côté à la demande de l'utilisateur pour un futur test sur sa save la
plus avancée (plus de chances d'avoir toutes les armes déjà en stock
pour les reconnaître d'un coup d'œil) :

```
0x1D82608  0x1D82658  0x1D826A8  0x1D826F8  0x1D82748  0x1D82798  0x1D827E8
0x1D82838  0x1D82888  0x1D828D8  0x1D82928  0x1D82978  0x1D829C8
0x1D82A18  0x1D82A68  0x1D82ABA  0x1D82B0A  0x1D82B5A
0x1D82BAA  0x1D82BFA  0x1D82C4A  0x1D82C9A  0x1D82CEA
0x1D82D3A  0x1D82D8A  0x1D82DDA
0x1D82E2A  0x1D82E7A  0x1D82ECA  0x1D82F1A  0x1D82F6A
0x1D82FBA  0x1D8300A  0x1D8305A  0x1D830D2  0x1D830FA
0x1D8314A  0x1D833CA  0x1D8341A  0x1D83602  0x1D83882
0x1D83D9A  0x1D8415A
```

Méthode pour les retester plus tard : même isolation manuelle (forcer un
sous-groupe à `2`/utilisable, le reste à `1`/verrouillé, demander à
l'utilisateur quelle arme apparaît) - pas besoin de refaire le scan
initial, ces adresses sont déjà connues et stables.

### Accessoires (silencieux, lumières...) : introuvables dans la zone armes connue, PLANTAGE sur recherche large (2026-09-23)

Tentative d'identifier Silencieux Operator (`0x4d`, dernier membre du lot
Otacon) et "Lumière pour pistolet" (`0x59`) avec la même méthode. Aucun
des deux n'est dans la zone déjà connue (`0x1D82420` ± `0x8000`, qui
contient toutes les armes principales trouvées jusqu'ici) - même un
cluster de 19 adresses à foulée régulière (`0x2C`) repéré dans une
fenêtre élargie ne les contient pas. Les accessoires semblent vivre dans
une zone mémoire séparée des armes principales, jamais localisée.

**Piège dangereux découvert** : scan complet de toute l'image du module
pour la valeur `2` → 9152 candidats. Tentative de dichotomie (couper en
deux, verrouiller une moitié, vérifier) sur ce volume-là : **le jeu a
freeze** en écrivant sur la moitié (~4576 adresses) d'un coup. Remettre
toutes les valeurs à l'identique n'a PAS suffi à débloquer le jeu -
redémarrage nécessaire. Contrairement aux recherches ciblées habituelles
(quelques dizaines à centaines de candidats dans une zone réduite déjà
connue, jamais de souci), écrire sur des milliers d'adresses réparties
dans toute l'image du module semble déstabiliser le jeu, probablement en
touchant des zones non liées aux armes/objets (autres systèmes du
moteur). **Ne plus jamais faire une dichotomie a cette echelle (milliers
de candidats sur toute l'image) - se limiter a des zones reduites deja
identifiees comme sures, quitte a multiplier les allers-retours.**

Résolution pour Silencieux Operator : piste abandonnée pour l'instant -
l'utilisateur note qu'il est peut-être donné automatiquement avec
l'Operator (pas de déblocage séparé possible), ce qui pourrait aussi
expliquer pourquoi aucune adresse dédiée n'a été trouvée. "Lumière pour
pistolet" reste également non localisée.

## Mise à jour du jeu (2026-09-24) : toutes les adresses décalées d'un bloc uniforme

Le jeu a reçu une mise à jour Steam entre les sessions du 23 et du 24. Au
redémarrage, toutes les adresses trouvées la veille (table objets,
armes/munitions) renvoyaient des valeurs fausses (`0` partout, états
"Verrouillée" généralisés) - la vérification `sanity_check` passait quand
même (`item[0x00]`/`item[0x13]` toujours à 0), ce qui a d'abord semé le
doute avant que l'utilisateur confirme en jeu que les valeurs affichées
ne correspondaient plus à rien de réel.

Plutôt que de tout rescanner depuis zéro, hypothèse testée sur suggestion
de l'utilisateur : **la mise à jour a peut-être juste décalé tout le
bloc de données d'une quantité fixe**, sans changer la structure interne
(stride, offsets relatifs) - un scénario courant quand le patch ajoute
un peu de code avant cette zone dans le binaire. Scan "valeur exacte" sur
la vraie valeur de Ration (15) restreint à une fenêtre autour de
l'ancienne adresse (`±0x20000`) plutôt qu'un scan complet : un candidat
net à exactement `+0x20` de l'ancienne adresse (les autres candidats
proches avaient des écarts erratiques, clairement du bruit).

**Hypothèse confirmée en un seul test** : appliquer `+0x20` à la formule
du tableau objets ET à toutes les adresses d'armes/munitions
individuellement confirmées la veille restaure tout instantanément,
y compris des valeurs de munitions bizarrement précises retombées pile
sur les mêmes nombres que la veille (Mk.2 Pistol = 95, Operator = 98).
Un seul décalage uniforme (`MODULE_PATCH_SHIFT = 0x20` dans
`live_trainer.py`, appliqué dans `item_state_rva()` et dans les 4
méthodes de lookup armes/munitions de `MGS4Live`) a suffi à tout
récupérer sans re-scanner une seule arme.

**Point important** : `LINKVARBUF_POINTER_RVA`/`VARBUF_POINTER_RVA` (la
chaîne de pointeurs documentée par zexk/bbtracker) n'ont PAS bougé - le
`sanity_check` passait déjà sans ce décalage avant qu'on le découvre,
preuve que ce n'est pas toute l'image du module qui s'est décalée
uniformément, juste la zone de données où vivent nos tables (probablement
liée à un ajout de taille fixe plus tôt dans le binaire).

**Méthode à retenir pour une future mise à jour** : avant de tout
rescanner, tester d'abord l'hypothèse d'un décalage uniforme - scanner
une seule valeur connue (ex. Ration) dans une fenêtre réduite autour de
l'ancienne adresse plutôt que toute la mémoire, calculer le delta du
candidat le plus "propre", puis vérifier que ce même delta appliqué aux
autres adresses connues (table objets + quelques armes) redonne des
résultats coherents. Beaucoup plus rapide qu'une redécouverte complète -
mais pas garanti a chaque fois (un patch pourrait tout réorganiser
différemment, auquel cas il faudra revenir à la méthode complète).

## Reprise sur la sauvegarde la plus avancée : chasse aux munitions (2026-09-24)

Après confirmation du décalage `+0x20`, reprise de la sauvegarde la plus
avancée de l'utilisateur pour continuer la couverture de
`CONFIRMED_WEAPON_AMMO_RVAS`. Constat de départ : **plus aucune arme
verrouillée disponible** sur cette sauvegarde, donc la découverte de
nouvelles adresses d'état (possession/lock) est bloquée pour de bon ici
(voir tentatives ci-dessous). Pivot assumé vers la découverte de
munitions uniquement, méthode qui reste pleinement productive (chaque
arme a une vraie consommation en jeu qui donne une transition de valeur
exploitable).

**Tentatives infructueuses de découverte d'état (documentées pour ne pas
retenter) :**
- Scan "valeur exacte" sur `2` (déjà utilisable) autour de la zone connue
  a redonné un gros lot de candidats "restants" (43 puis, le lendemain,
  78 nouveaux) jamais départagés : verrouiller/déverrouiller ces
  candidats en lot n'a produit AUCUN changement visible en jeu, alors que
  le mécanisme de base a été re-vérifié comme fonctionnel entre-temps (le
  Mk.2 Pistol, adresse déjà confirmée, bascule bien visiblement). Conclu
  que cette zone mémoire est saturée de données moteur non liées aux
  armes qui prennent coïncidemment de petites valeurs comme `2`.
- Idée testée (proposée par l'utilisateur) : chercher des candidats à `2`
  juste **avant** vs juste **après** chaque adresse de munitions déjà
  confirmée. Avant : liste courte et propre (3 candidats). Après :
  ~200 candidats, aussi bruités que le lot précédent. Même les 3
  candidats "avant" n'ont montré aucun effet visible une fois verrouillés.
- Conclusion actuelle : la découverte de nouveaux états d'armes nécessite
  une vraie transition de gameplay (arme encore verrouillée puis
  débloquée, ou nouvelle arme jamais obtenue) qui n'existe plus sur cette
  sauvegarde très avancée. À reprendre si l'utilisateur retrouve une
  telle situation (nouvelle partie, sauvegarde moins avancée, etc.).

**Nouvelles adresses de munitions confirmées** (méthode identique à
chaque fois : scan "valeur exacte" sur le compte annoncé par
l'utilisateur, filtré sur la zone stable connue autour de
`0x1D82420 + MODULE_PATCH_SHIFT`, confirmé soit directement par un seul
candidat restant, soit par une vraie consommation en jeu quand plusieurs
candidats survivaient) :

| Arme | ID | RVA munitions | Notes |
|---|---|---|---|
| PSS | `0x0e` | `0x1D820F0` | 3 candidats, confirmé par vraie conso (77→75) |
| G18C | `0x0f` | `0x1D82150` | 1 candidat direct (210) |
| Mk.23 | `0x04` | `0x1D82030` | Même pool .45 ACP que Operator/1911/M-10 (933, correspondance directe) |
| Arme de chasse | `0x0c` | `0x1D82018` | Confirmé par 4 conso réelles (18→15→14→7→37) ; un 2e candidat (`0x1D82950`) était resté synchronisé par coïncidence sur les 3 premiers tours puis a divergé au 4e - éliminé comme faux positif |
| D.E. / Desert Eagle | `0x08` | `0x1D82060` | 3 candidats, confirmé par vraie conso (11→8) |
| P90 | `0x14` | `0x1D820D8` | Même pool 5.7x28mm que Five-Seven, confirmé par conso simultanée (2058→2038) |
| M-10 | `0x13` | `0x1D82030` | Même pool .45 ACP (938, correspondance directe) |
| MP7 | `0x11` | `0x1D82090` | 1 candidat direct (953) |
| Vz. 83 | `0x17` | `0x1D82138` | Même pool 9x18mm Makarov que PMM - 1er scan (490) écarté par prudence car identique à la valeur PMM du moment (risque de coïncidence) ; confirmé par une vraie conso simultanée sur les deux armes (490→484) |
| PP-19 Bizon | `0x15` | `0x1D82138` | Même pool 9x18mm Makarov (PMM/Vz. 83/Bizon tous les trois) - confirmé par l'utilisateur (484 visible en même temps sur les trois), pas de scan séparé nécessaire |
| MP5SD2 | `0x12` | `0x1D82150` | Même pool 9x19mm Parabellum que G18C - 1er scan (210) écarté par prudence car identique à la valeur G18C du moment ; confirmé par une vraie conso simultanée sur les deux armes (210→188) |

### Capture d'écran boutique "Fusils" : 7 armes d'un coup (2026-09-24)

L'utilisateur a partagé une capture du menu boutique en jeu (onglet
"Fusils"), qui affiche pour chaque arme son calibre et son stock de
munitions actuel - exactement les mêmes valeurs que celles lues en
mémoire (vérifié : AK-102/M4 Modifié = 829, MK.17 = 2214, correspondance
exacte avec `read_weapon_ammo`). Ça confirme que ces chiffres de boutique
sont bien les vraies munitions live, pas des prix, et ça donne un moyen
très rapide de confirmer plusieurs armes par calibre partagé d'un seul
coup sans manipulation en jeu :

| Arme | ID | RVA munitions | Notes |
|---|---|---|---|
| XM8 | `0x1f` | `0x1D820C0` | Même pool 5,56x45mm que M4/AK-102 (829, correspondance directe via capture) |
| G3A3 | `0x1a` | `0x1D82108` | Même pool 7,62x51mm que MK.17 (2214, correspondance directe) |
| Carabine FAL | `0x1c` | `0x1D82108` | Même pool 7,62x51mm (2214, correspondance directe) |
| M14EBR | `0x2a` | `0x1D82108` | Même pool 7,62x51mm (2214, correspondance directe) |
| AN-94 | `0x1b` | `0x1D820A8` | Calibre propre (5,45x39mm, 180) - scan "valeur exacte", 1 seul candidat direct |
| Tanegashima | `0x1d` | `0x1D82198` | Calibre propre (balle plomb, 300) - scan "valeur exacte", 1 seul candidat direct ; identité de l'arme toujours confiance basse (voir `WEAPON_NAMES`) |
| DSR-1 | `0x29` | `0x1D82180` | Calibre propre (7,62x67mm, 365) - scan "valeur exacte", 1 seul candidat direct ; identité de l'arme toujours confiance basse, jamais confirmée individuellement (voir `WEAPON_NAMES`) |

Bilan à ce stade : **31 armes couvertes en munitions** dans
`CONFIRMED_WEAPON_AMMO_RVAS` (`live_trainer.py`), en comptant les pools
partagés (.45 ACP : Operator/1911 Modifié/Mk.23/M-10 ; 5.7x28mm :
Five-Seven/P90 ; 9x18mm Makarov : PMM/Vz. 83/PP-19 Bizon ; 9x19mm
Parabellum : G18C/MP5SD2 ; 5,56x45mm : M4/AK-102/XM8 ; 7,62x51mm :
MK.17/G3A3/FAL/M14EBR).

### Deuxième capture d'écran boutique "Fusils" : 5 armes de plus (2026-09-24)

Suite de la même méthode avec une 2e capture (bas de la liste fusils) :
SVD, VSS, Mosin-Nagant, M82A2, Rail Gun - tous sur des calibres propres
(pas de pool partagé avec une arme déjà connue).

| Arme | ID | RVA munitions | Notes |
|---|---|---|---|
| SVD | `0x2c` | `0x1D82120` | Calibre propre (7,62x54mm R, 936) - scan "valeur exacte", 1 seul candidat direct |
| Mosin-Nagant | `0x2b` | `0x1D81FA0` | Calibre propre (flèche anesthésiante 7,62mm, 320) - scan "valeur exacte", 1 seul candidat direct |
| VSS | `0x27` | `0x1D82168` | Calibre propre (9x39mm, 110) - 2 candidats stables, confirmé par une vraie conso (110→104, capture d'écran du HUD en jeu zoom x03), l'autre resté figé |
| M82A2 | `0x28` | `0x1D82078` | Calibre propre (.50 BMR, 80) - 3 candidats stables, confirmé par une vraie conso (80→70), les 2 autres restés figés |
| Rail Gun | `0x2d` | `0x1D824B0` | Munitions Rail Gun (100) - 8 candidats stables, confirmé par une vraie conso (100→98), les 7 autres restés figés |

Bilan à ce stade : **36 armes couvertes en munitions** dans
`CONFIRMED_WEAPON_AMMO_RVAS` (`live_trainer.py`).

### Troisième capture d'écran boutique "Fusils" : fin de liste (2026-09-24)

Suite avec la fin de la liste fusils : HK21E, M60E4, PKM, Mk.46 MOD1,
Double canon, M870 Modifié, Saiga-12, XM25, MGL-140, RPG-7. Plusieurs
tombent directement dans des pools déjà connus (confirmés sans scan par
correspondance exacte de valeur affichée) ; les 3 armes sur calibre/
munition propre (XM25, MGL-140, RPG-7) ont nécessité un scan classique,
avec pour XM25 une valeur de départ très basse (`2`) qui a produit 132
candidats - affinée en deux temps via deux captures HUD successives de
l'utilisateur (2→1 puis 1→51 après rechargement), chaque étape divisant
drastiquement les candidats jusqu'à un seul survivant.

| Arme | ID | RVA munitions | Notes |
|---|---|---|---|
| HK21E | `0x21` | `0x1D82108` | Même pool 7,62x51mm que MK.17 (2214, correspondance directe) |
| M60E4 | `0x23` | `0x1D82108` | Même pool 7,62x51mm (2214, correspondance directe) |
| PKM | `0x22` | `0x1D82120` | Même pool 7,62x54mm R que SVD (936, correspondance directe) |
| Mk.46 MOD1 | `0x20` | `0x1D820C0` | Même pool 5,56x45mm que M4/AK-102/XM8 (829, correspondance directe) |
| Double canon | `0x24` | `0x1D821B0` | Calibre propre (12GA chevrotine 00, 152) - scan "valeur exacte", 1 seul candidat direct |
| M870 Modifié | `0x25` | `0x1D821B0` | Même pool 12GA que Double canon (152, correspondance directe) |
| Saiga-12 | `0x26` | `0x1D821B0` | Même pool 12GA (152, correspondance directe) |
| MGL-140 | `0x2e` | `0x1D82210` | Calibre propre (40mm GRD, 63) - 2 candidats stables, confirmé par vraie conso (63→60), l'autre resté figé |
| RPG-7 | `0x32` | `0x1D822B8` | Munitions propres (64) - 12 candidats stables, confirmé par vraie conso (64→63), les 11 autres restés figés |
| XM25 | `0x2f` | `0x1D82270` | Munitions propres, valeur de départ très basse (2, 132 candidats) - affiné en 2 étapes (2→1 puis 1→51 après rechargement) jusqu'à 1 seul survivant |

Bilan à ce stade : **46 armes couvertes en munitions** dans
`CONFIRMED_WEAPON_AMMO_RVAS` (`live_trainer.py`).

### Lance-roquettes/missiles : M72A3, Javelin, FIM-92A (2026-09-24)

Capture d'écran boutique puis captures HUD en jeu pour départager (2
candidats stables pour chacune des 3 armes) :

| Arme | ID | RVA munitions | Notes |
|---|---|---|---|
| FIM-92A | `0x30` | `0x1D82288` | 2 candidats stables, confirmé par vraie conso (54→51), l'autre resté figé |
| FGM-148 Javelin | `0x31` | `0x1D822A0` | 2 candidats stables, confirmé par vraie conso (36→34), l'autre resté figé |
| M72A3 | `0x33` | `0x1D822D0` | 2 candidats stables, confirmé par vraie conso (35→34), l'autre resté figé |

Note : Javelin et M72A3 terminent par coïncidence sur la même valeur
finale (34), mais chacun suivi individuellement depuis une valeur de
départ différente (36 vs 35) sur une adresse distincte - confirmé que ce
n'est PAS un pool partagé, juste une coïncidence de timing.

Bilan à ce stade : **49 armes couvertes en munitions** dans
`CONFIRMED_WEAPON_AMMO_RVAS` (`live_trainer.py`).

### Onglet "Explosifs" (grenades) : 5 sur 9 départagées (2026-09-24)

Capture boutique de l'onglet "Explosifs" (Grenade, Cocktail Molotov,
Grenade Phosphore, Grenade Paralysante déjà connue - valeur 125 confirmée
à l'identique, validant l'ancre de zone -, Grenade Électro, Grenade
Fumigène générique, et les 4 fumigènes colorées J/R/B/V). Chaque valeur a
généré plusieurs candidats stables (2 à 9). Une 2e capture après usage en
jeu n'a fait bouger que 5 des 9 items - les 4 fumigènes colorées sont
restées identiques (28/7/35/70), donc toujours non départagées.

| Arme | ID | RVA munitions | Notes |
|---|---|---|---|
| Grenade | `0x34` | `0x1D822E8` | 2 candidats, confirmé par vraie conso (85→84), l'autre resté figé |
| Cocktail Molotov | `0x3d` | `0x1D823C0` | 8 candidats, confirmé par vraie conso (60→57), les 7 autres restés figés |
| Grenade au phosphore blanc | `0x35` | `0x1D82300` | 2 candidats, confirmé par vraie conso (75→70), l'autre resté figé |
| Grenade à particules métalliques ("Électro") | `0x37` | `0x1D82330` | 3 candidats, confirmé par vraie conso (22→18), les 2 autres restés figés |
| Grenade fumigène générique | `0x38` | `0x1D82348` | 2 candidats, confirmé par vraie conso (77→75), l'autre resté figé |

Reste à départager (candidats stables déjà en main, en attente d'une
vraie consommation de chaque couleur) : Fumigène Jaune (`0x3b`, valeur
28, 6 candidats), Fumigène Rouge (`0x39`, valeur 7, 9 candidats),
Fumigène Bleue (`0x3c`, valeur 35, 2 candidats), Fumigène Verte (`0x3a`,
valeur 70, 2 candidats - attention un des 2 candidats coïncide avec
l'adresse déjà confirmée du M82A2, faux positif probable).

Bilan à ce stade : **54 armes couvertes en munitions** dans
`CONFIRMED_WEAPON_AMMO_RVAS` (`live_trainer.py`).

### Fumigènes colorées + fin "Explosifs" : Claymore, C4, Sachet somnifère (2026-09-24)

Toutes les 4 fumigènes colorées départagées grâce à une vraie
consommation en jeu (capture avant/après) :

| Arme | ID | RVA munitions | Notes |
|---|---|---|---|
| Grenade fumigène (Jaune) | `0x3b` | `0x1D82390` | 6 candidats, confirmé par vraie conso (28→27) |
| Grenade fumigène (Rouge) | `0x39` | `0x1D82360` | 9 candidats, confirmé par vraie conso (7→5) |
| Grenade fumigène (Bleue) | `0x3c` | `0x1D823A8` | 2 candidats, confirmé par vraie conso (35→32) |
| Grenade fumigène (Verte) | `0x3a` | `0x1D82378` | 2 candidats, confirmé par vraie conso (70→66) - l'autre candidat était bien le faux positif M82A2 soupçonné, resté figé |

Puis fin de l'onglet "Explosifs" (Claymore, C4, Sachet à gaz
somnifère) départagés de la même façon (capture HUD CQC avant/après) :

| Arme | ID | RVA munitions | Notes |
|---|---|---|---|
| Claymore | `0x40` | `0x1D82408` | 2 candidats, confirmé par vraie conso (59→58) |
| C4 | `0x42` | `0x1D82438` | 7 candidats, confirmé par vraie conso (18→17) - un des faux positifs était `0x1D82330` (adresse déjà connue de la grenade Électro), coïncidence de valeur confirmée par élimination |
| Sachet à gaz somnifère | `0x43` | `0x1D82450` | 10 candidats, confirmé par vraie conso (12→11) |

Bilan à ce stade : **61 armes/objets de lancer couverts en munitions**
dans `CONFIRMED_WEAPON_AMMO_RVAS` (`live_trainer.py`). L'onglet
"Explosifs" du menu boutique est désormais entièrement couvert.

### Onglet "Etc." : Chargeur confirmé, Magazine Émotion en attente (2026-09-24)

Capture de l'onglet "Etc." (Couteau paralysant - déjà connu comme arme
sans munitions -, Chargeur, Playboy déjà connu - valeur 52 confirmée à
l'identique -, Mag Émo, figurines Mantis/Sorrow qui n'ont pas de compteur
de munitions affiché, juste possession).

- **Chargeur** (`0x3e`, objet de diversion à lancer, pas une arme) : RVA
  `0x1D823D8`, confirmé (2026-09-24) - scan "valeur exacte" sur 110,
  1 seul candidat direct.
- **Magazine Émotion** (`0x46`) : RVA `0x1D82498`, confirmé (2026-09-24) -
  5 candidats stables sur la valeur 19, 1 seul confirmé par une vraie
  consommation (19->18), les 4 autres restés figés. Testé le raccourci
  via le champ STATS `emotion_magazine_pages` (déjà suivi côté fichier de
  sauvegarde) mais sa valeur live actuelle (0) ne correspondait pas à
  19 - ce n'était donc PAS la même adresse mémoire, pas de raccourci
  possible, scan classique nécessaire.

Bilan à ce stade : **63 armes/objets couverts en munitions** dans
`CONFIRMED_WEAPON_AMMO_RVAS` (`live_trainer.py`). L'onglet "Etc." du
menu boutique (hors figurines/objets clés sans compteur) est désormais
entièrement couvert.

### GSR ajouté au pool .45 ACP (2026-09-24)

GSR (`0x07`, SIG Sauer GSR - pistolet .45 ACP malgré son nom, voir
commentaire dans `WEAPON_NAMES`) partage le MEME pool `.45 ACP` que
Operator/1911 Modifié/Mk.23/M-10 - confirmé par l'utilisateur (938,
correspondance directe avec la valeur déjà lue), pas de scan séparé
nécessaire.

Bilan à ce stade : **64 armes couvertes en munitions** dans
`CONFIRMED_WEAPON_AMMO_RVAS` (`live_trainer.py`).

## Formule linéaire du tableau d'état des armes + correction 1911/Thor .45-70 (2026-09-24)

Question de l'utilisateur : existe-t-il une logique/formule liant les
adresses mémoire live aux ID d'armes (comme pour la table objets), qui
pourrait aider à identifier des armes ? Vérification faite sur les 11
RVA d'état déjà confirmées individuellement (`CONFIRMED_WEAPON_RVAS`) :
**oui**, elles suivent toutes une formule linéaire stricte :

```
RVA_etat(id) = 0x1D8258A + id * 0x50   (avant MODULE_PATCH_SHIFT)
```

9 des 11 entrées collaient exactement. Les 2 seules exceptions -
`0x0a` (étiquetée "1911 Modifié") et `0x0b` (étiquetée "Thor .45-70") -
collaient parfaitement **si on les échangeait**, ce qui correspondait
justement à l'ambiguïté déjà documentée du "lot Otacon" (attribution par
convention, jamais isolée individuellement, confiance basse).

**Double confirmation en jeu par l'utilisateur** : désactiver l'adresse
prédite pour l'ID `0x0a` (`0x1D828AA`) verrouille bien le **Thor .45-70**
en jeu, et désactiver l'adresse prédite pour l'ID `0x0b` (`0x1D828FA`)
verrouille bien le **1911 Modifié**. Les adresses mémoire elles-mêmes
étaient donc déjà correctes (comportementalement validées depuis le
23/09) - c'est l'étiquette d'ID (0x0a vs 0x0b) qui était inversée depuis
l'attribution initiale par convention.

**Cohérence supplémentaire trouvée après coup** : sous les anciens ID,
"Thor .45-70" (0x0b) avait sa munition dans le pool .45 ACP partagé avec
Operator, ce qui n'avait pas de sens réel (le Thor .45-70 tire une
munition `.45-70 Government`, complètement différente du `.45 ACP`).
Après correction, c'est maintenant le vrai 1911 Modifié (`.45 ACP`,
0x0b) qui partage ce pool, et le Thor .45-70 (`0x0a`) qui a bien sa
munition séparée (`0x1D82048`) - cohérent avec les calibres réels.

**Corrections appliquées** dans `mgs4save.py` (`WEAPON_NAMES`,
`WEAPON_CATEGORIES`) et `live_trainer.py` (`CONFIRMED_WEAPON_RVAS`,
`CONFIRMED_WEAPON_AMMO_RVAS`) : `0x0a` = Thor .45-70, `0x0b` = 1911
Modifié (échange par rapport à l'ancienne convention). **Impact sur
l'application principale MGS4SaveStats** : les statistiques basées sur
le fichier de sauvegarde pour ces deux armes étaient donc affichées avec
les noms inversés jusqu'à cette correction.

**Anomalie interessante repérée** en testant la formule sur toute la
plage d'ID : `0x4e` (Silencieux Mk.23) lit **1** (verrouillée mais
connue) - première arme non totalement débloquée retrouvée depuis
longtemps sur cette sauvegarde très avancée.

### Formule intégrée comme méthode principale (2026-09-24)

Suite logique de la découverte ci-dessus : `weapon_state_rva(weapon_id)`
ajoutée dans `live_trainer.py` (même principe que `item_state_rva()`),
`MGS4Live.read_weapon`/`write_weapon` simplifiées pour l'utiliser
directement - **toutes** les armes (pas seulement les 11 scannées
individuellement) affichent maintenant leur véritable état dans le
trainer. Le mécanisme `confirmed_ids` de `TableTab`/`GroupedWeaponsTab`
(qui grisait le menu État pour les ID non confirmés, seul usage réel :
l'onglet Armes) n'est plus câblé - conservé générique dans `TableTab` au
cas où, mais `GroupedWeaponsTab` ne le prend plus en paramètre.
`_read_u16`/`_write_u16` (l'ancien fallback varbuf, plus jamais appelé)
supprimés. `CONFIRMED_WEAPON_RVAS` conservé tel quel, mais reclassé en
simple trace d'audit : la formule donne le RVA fiable pour n'importe
quel ID, ce dictionnaire documente seulement quels ID ont été
**comportementalement confirmés en jeu** (quelle arme reelle se cache
derrière le numéro) - une question indépendante et toujours ouverte pour
les ID "confiance basse" de `mgs4save.py.WEAPON_NAMES` (Mk.2 Pistol vs
Operator, Tanegashima, DSR-1, Sachet à gaz somnifère...).

Vérifié : `TrainerWindow` se construit sans erreur, lecture testée sur
un échantillon incluant `0x00` (0, cohérent), `0x4e` (1, Silencieux
Mk.23 toujours verrouillé) et plusieurs ID confirmés (tous à 2).

### Tanegashima (0x1d) confirmé grâce à la formule (2026-09-24)

Premier cas concret où la nouvelle liberté (état éditable pour toute
arme, plus seulement les 11 confirmées) sert à trancher une identité
"confiance basse" historique : bascule de l'état de `0x1d` via le
trainer, confirmé en jeu que c'est bien le **Tanegashima** qui se
verrouille/déverrouille. Résout l'incertitude documentée depuis le
2026-09-09 dans `mgs4save.py` (attribution par déduction contextuelle -
position dans le bloc de fusils d'assaut - jamais testée isolément).
Passé en confiance haute dans `WEAPON_NAMES`/`WEAPON_CATEGORIES`
(mgs4save.py) et ajouté à `CONFIRMED_WEAPON_RVAS` (live_trainer.py,
`0x1d: 0x1D82E9A`) comme trace d'audit comportemental.

### Mk.2 Pistol (0x02) confirmé de la même façon (2026-09-24)

Même méthode appliquée au reste du "lot Otacon" encore en confiance
basse : bascule de l'état de `0x02` via le trainer, confirmé en jeu que
c'est bien le **Mk.2 Pistol**. Passé en confiance haute dans
`WEAPON_NAMES` (mgs4save.py).

### Suite : Operator, DSR-1, Sachet à gaz somnifère confirmés (2026-09-24)

Même méthode (bascule d'état + vérification en jeu) appliquée par
l'utilisateur à trois autres identités "confiance basse" historiques,
toutes confirmées et passées en confiance haute dans `WEAPON_NAMES` :
**Operator** (`0x03`, dernier morceau du lot Otacon dont l'identité
restait à isoler), **DSR-1** (`0x29`, ambiguïté avec D.E. depuis
2026-09-06), **Sachet à gaz somnifère** (`0x43`, attribution par
déduction contextuelle depuis 2026-09-09, jamais testée isolément).

Reste en confiance basse dans le lot Otacon : **Silencieux Operator**
(`0x4d`, jamais testé) et **Silencieux Mk.23** (`0x4e`, actuellement
verrouillé sur la save de l'utilisateur - état lu via `weapon_state_rva`
= 1 - donc testable en le forçant à 2 et en observant si un silencieux
apparaît sur le Mk.23 en jeu).

### Silencieux Operator (0x4d) : piste "stock" abandonnée, faux verrouillé confirmé (2026-09-24)

Tentative de trouver l'adresse du **stock** de silencieux Operator
(affichage HUD en jeu "SIL 26"/"SIL 25" pendant le tir, décompté à
chaque bris) via la méthode scan+affinage habituelle. Échec répété (4
tentatives, 0 survivant à chaque nouvelle valeur) : la valeur ne vit pas
dans l'image statique du module (comme la table objets/armes) mais dans
une zone allouée dynamiquement (`Type=MEM_PRIVATE`), qui semble
réallouée en continu par le moteur - probablement un buffer d'affichage
HUD recomposé, pas un compteur persistant exploitable. **Abandonné** :
une adresse aussi instable ne serait de toute façon pas réutilisable
d'un lancement à l'autre.

Détour intéressant en cours de route : l'utilisateur a fait remarquer
qu'il possède et utilise activement des dizaines de silencieux Operator,
alors que `weapon_state_rva(0x4d)` lit **état=1** ("verrouillée") - une
contradiction apparente qui semblait indiquer un mauvais ID. Mais
recoupement avec `DREBIN_LOCK_EXCEPTIONS` (mgs4save.py) : ce même
phénomène était déjà documenté depuis le 2026-09-07 pour le
**Silencieux M4** (`0x52`, "reste bloqué à 1... déjà monté et
fonctionnel en jeu") et suspecté par analogie pour le Silencieux Mk.23
(`0x4e`). Le Silencieux Operator en est donc une **3e confirmation
directe** du même phénomène (accessoires à durabilité/stock consommable
dont l'état ne reflète pas fidèlement la possession réelle), pas une
preuve d'ID erroné. `0x4d` ajouté à `DREBIN_LOCK_EXCEPTIONS`. Impact
réel sur MGS4SaveStats : le silencieux Operator n'affichait plus
l'indicateur trompeur "verrouillé chez Drebin" pour les utilisateurs qui
le possèdent déjà.

### Masterkey (0x4a) ajouté au pool 12GA (2026-09-24)

Masterkey (fusil de brèche calibre 12) partage le MEME pool 12GA que
Double canon/M870 Modifié/Saiga-12 - confirmé par correspondance directe
(152) puis vraie consommation simultanée sur le pool (152→148). Cohérent
avec son usage réel (munitions de brèche calibre 12). **65 armes**
couvertes en munitions dans `CONFIRMED_WEAPON_AMMO_RVAS`.

**Comportement particulier découvert en testant son état** : forcer
l'état à `1` (Verrouillée) via le trainer n'a montré aucun effet visible
en jeu (le Masterkey restait utilisable) - premier essai qui a semblé
indiquer que l'écriture n'avait pas d'effet. Mais l'utilisateur a
poursuivi le test avec `0` (Non possédée) : le Masterkey devient alors
bien indisponible/impossible à équiper. Explication : contrairement aux
armes achetées (verrouillées chez Drebin puis débloquées, `1`→`2`), les
armes obtenues via déclencheur scénaristique unique comme le Masterkey
n'ont pas de palier intermédiaire - `1` et `2` se comportent tous les
deux comme "possédée", seul `0` fait vraiment la différence. Confirme
donc l'identité `0x4a` = Masterkey (déjà confiance haute depuis
2026-09-06) au lieu de l'infirmer. Ajouté à `CONFIRMED_WEAPON_RVAS`
(`live_trainer.py`, `0x4a: 0x1D83CAA` = `weapon_state_rva(0x4a)`). À
garder en tête pour la suite : sur les armes/accessoires à déclencheur
unique (Masterkey, XM320, GP-30...), tester `0` plutôt que `1` pour
observer un effet visible.

### Silencieux Operator (0x4d) confirmé, lot Otacon entièrement résolu (2026-09-24)

Même test appliqué au Silencieux Operator : forcer l'état à `0` (au lieu
de `1`, leçon tirée du Masterkey) - le silencieux devient bien
indisponible en jeu. **Dernier morceau du lot Otacon confirmé** (`0x02`
Mk.2 Pistol, `0x03` Operator, `0x0a` Thor .45-70, `0x0b` 1911 Modifié,
`0x4d` Silencieux Operator - les 5 ID qui flushaient ensemble à
l'obtention du don d'Otacon, jamais isolés individuellement avant cette
session). Passé en confiance haute dans `WEAPON_NAMES` (mgs4save.py).
Ajouté à `CONFIRMED_WEAPON_RVAS` (`live_trainer.py`, `0x4d: 0x1D83D9A`).
Restauré à l'état "Utilisable" après le test (l'utilisateur en possède
une vingtaine en jeu).

Reste en confiance basse hors lot Otacon : **Silencieux Mk.23** (`0x4e`)
- actuellement verrouillé (`état=1`) sur la save de l'utilisateur, donc
pas encore testable de la même façon (il faudrait d'abord le débloquer
réellement en jeu).

### Rachat des accessoires un par un pour confirmation (2026-09-24)

Méthode inspirée du test Masterkey/Silencieux Operator, étendue à toute
la catégorie Accessoire : les 18 ID (`0x4a`-`0x5b`) forcés à `0` d'un
coup (valeurs d'origine sauvegardées avant), puis l'utilisateur les
rachète un par un chez Drebin en jeu pour voir lequel repasse à `2` à
chaque achat - variante "isolation manuelle" sans avoir besoin de
verrouiller/déverrouiller par lots successifs comme la première fois
(2026-09-23), puisque tout part maintenant de zéro.

Premier rachat : **Lumière pour pistolet** (`0x59`) repassé à `2` -
reconfirme une identité déjà en confiance haute depuis un test isolé du
2026-09-05.

Rachats suivants : **Silencieux Operator** (`0x4d`) - reconfirme le lot
Otacon déjà résolu - puis **Silencieux Mk.23** (`0x4e`) repassé à `2`.
Cette dernière identité, en confiance basse depuis 2026-09-09 (pari de
l'utilisateur, "pile entre 0x4d et 0x4f", jamais isolée), passe enfin en
confiance haute - toute la plage d'accessoires connue jusqu'ici
(`0x4a`-`0x59`) est désormais confirmée individuellement. Mis à jour
dans `WEAPON_NAMES`, `CONFIRMED_WEAPON_RVAS` et le commentaire
`DREBIN_LOCK_EXCEPTIONS` (identité confirmée, mais le comportement "faux
verrouillé" spécifique reste non testé pour cet ID).

**Silencieux 1911** (`0x4f`) rachetée ensuite, repassée à `2` -
reconfirme une identité déjà en confiance haute (test isolé du
2026-09-05). Ajoutée à `CONFIRMED_WEAPON_RVAS`.

**Silencieux P90** (`0x51`) rachetée ensuite, repassée à `2` -
reconfirme une identité déjà en confiance haute (test isolé du
2026-09-05). Ajoutée à `CONFIRMED_WEAPON_RVAS`.

**Visée laser (M4)** (`0x58`) rachetée ensuite, repassée à `2` -
reconfirme une identité déjà en confiance haute (test isolé du
2026-09-06). Ajoutée à `CONFIRMED_WEAPON_RVAS`.

**Lumière Fusil (M4)** (`0x57`) rachetée ensuite, repassée à `2` -
reconfirme une identité déjà confirmée par capture d'écran
(2026-09-02). Ajoutée à `CONFIRMED_WEAPON_RVAS`.

**Silencieux M10** (`0x50`) rachetée ensuite, repassée à `2` -
reconfirme une identité déjà en confiance haute (test isolé du
2026-09-05). Ajoutée à `CONFIRMED_WEAPON_RVAS`.

**Visée point rouge (MP7)** (`0x56`) rachetée ensuite, repassée à `2` -
reconfirme une identité déjà confirmée (test isolé, partie fraîche).
Ajoutée à `CONFIRMED_WEAPON_RVAS`.

**Lunette de fusil** (`0x54`) rachetée ensuite, repassée à `2` -
reconfirme une identité déjà en confiance haute. Ajoutée à
`CONFIRMED_WEAPON_RVAS`.

**GP-30** (`0x4c`) racheté ensuite, repassé à `2` - reconfirme une
identité déjà en confiance haute. Ajouté à `CONFIRMED_WEAPON_RVAS`.
Munitions confirmées aussi : RVA `0x1D821F8`, vraie consommation
(65→63) - 66 armes/objets couverts en munitions.

**Visée point rouge (M4)** (`0x55`) rachetée ensuite, repassée à `2` -
reconfirme une identité déjà confirmée. Ajoutée à `CONFIRMED_WEAPON_RVAS`.

**Silencieux M4** (`0x52`) racheté ensuite, repassé à `2` - reconfirme
une identité déjà en confiance haute. Ajouté à `CONFIRMED_WEAPON_RVAS`.

**XM320** (`0x4b`) racheté ensuite, repassé à `2` - reconfirme une
identité déjà en confiance haute. Ajouté à `CONFIRMED_WEAPON_RVAS`.
Munitions confirmées aussi : partage en fait le MEME pool 40mm que le
MGL-140 (pas une coïncidence après tout) - vraie consommation
simultanée sur les deux (65→61). 67 armes/objets couverts en munitions.

**Poignée avant A.** (`0x5a`) rachetée ensuite, repassée à `2` -
reconfirme une identité déjà en confiance haute. Ajoutée à
`CONFIRMED_WEAPON_RVAS`.

**Poignée avant B.** (`0x5b`) rachetée ensuite, repassée à `2` -
reconfirme une identité déjà en confiance haute. Ajoutée à
`CONFIRMED_WEAPON_RVAS`.

**Silencieux M14EBR** (`0x53`) racheté en dernier, repassé à `2` -
reconfirme une identité déjà en confiance haute. Ajouté à
`CONFIRMED_WEAPON_RVAS`. **Les 18 accessoires (`0x4a`-`0x5b`) sont
désormais tous confirmés individuellement** - clôture cette campagne de
rachat un par un.

### Menu État simplifié pour la catégorie Accessoire (2026-09-24)

Suite logique du constat Masterkey/silencieux (`1` et `2` se comportent
pareil, seul `0` a un effet visible) : à la demande de l'utilisateur, le
menu État de la section Accessoire du trainer passe de 3 options
(Non poss./Verrouillée/Utilisable) à 2 (Non poss./Utilisable), sur le
même mécanisme binaire déjà utilisé pour les objets (`binary_lock_value`
- n'importe quelle valeur différente de 0 compte comme "Utilisable").
Nouveau `GroupedWeaponsTab.BINARY_CATEGORIES = {"Accessoire"}` dans
`live_trainer.py`. Au passage, correction d'un bug mineur préexistant :
le menu binaire ignorait les libellés de `quick_states` et affichait des
libellés français codés en dur ("Verrouillé"/"Déverrouillé") - utilise
désormais les vrais libellés/valeurs passés (impact cosmétique sur les
objets aussi : "Déverrouillé" devient "Obtenu", comme c'était censé être
depuis le départ).

### Desert Eagle (Canon Long) (0x09) découvert (2026-09-24)

Nouvel ID identifié directement par l'utilisateur via le trainer :
"Arme #09" est en fait le **Desert Eagle (Canon Long)** - variante
canon long du D.E. classique (`0x08`), partage le MEME pool de
munitions (même calibre, confirmé par correspondance directe : 8 à
l'instant de l'observation). Ajouté à `WEAPON_NAMES`/`WEAPON_CATEGORIES`
(mgs4save.py) et `CONFIRMED_WEAPON_RVAS`/`CONFIRMED_WEAPON_AMMO_RVAS`
(live_trainer.py). **68 armes/objets couverts en munitions.**

**Piège à noter** : le placeholder du trainer pour les armes sans nom
est `"Arme #{:02d}"` - format **décimal**, pas hexadécimal ! "Arme #16"
vu en jeu correspond donc à l'ID `0x10`, pas `0x16`. Source de confusion
potentielle à surveiller pour la suite des découvertes.

### Type 17 (0x10) découvert (2026-09-24)

Nouvel ID identifié par l'utilisateur via le trainer ("Arme #16" =
`0x10`, voir piège ci-dessus) : le **Type 17**, partage le pool .45 ACP
déjà connu (Operator/1911/Mk.23/M-10/GSR/D.E. Canon Long... non, D.E.
Canon Long est un pool distinct - le pool .45 ACP proprement dit),
confirmé par correspondance directe (878). Ajouté à
`WEAPON_NAMES`/`WEAPON_CATEGORIES` et
`CONFIRMED_WEAPON_RVAS`/`CONFIRMED_WEAPON_AMMO_RVAS`. Particularité
notée : état actuel = `1` malgré les 878 munitions en stock - pattern
qui rappelle le "faux verrouillé" des silencieux
(`DREBIN_LOCK_EXCEPTIONS`), pas encore confirmé par un test dédié
(bascule d'état + vérification en jeu). **69 armes/objets couverts en
munitions.**

### Patriot (0x16) découvert (2026-09-24)

Nouvel ID identifié par l'utilisateur via le trainer (cette fois avec
l'ID hexadécimal explicite, `0x16`) : le **Patriot** - arme bonus
emblématique de Big Boss, munitions illimitées (pas de pool à suivre
dans `CONFIRMED_WEAPON_AMMO_RVAS`), catégorie "Pistolet-mitrailleur".
Ajouté à `WEAPON_NAMES`/`WEAPON_CATEGORIES` et `CONFIRMED_WEAPON_RVAS`.
Même pattern que le Type 17 : état actuel = `1` malgré possession
confirmée.

### "Déstabil. SOP" (0x44) découvert - objet inédit (2026-09-24)

Trouvaille surprenante de l'utilisateur en explorant les ID sans nom
restants (`0x3f`, `0x44`) : `0x44` est un **objet totalement inédit**,
jamais documenté ailleurs à sa connaissance - un poster/objet à poser
("POSER" en jeu), poids 3.0kg, nom affiché tronqué à l'écran
("DÉSTABIL.SOP"). Ajouté à `WEAPON_NAMES` sous "Déstabil. SOP"
(confiance basse sur l'orthographe/nom exact complet, à confirmer),
catégorie "Autre" (comme Chargeur/Magazine Playboy - pas une arme).
Ajouté à `CONFIRMED_WEAPON_RVAS`. État=2 (possédé) au moment de la
découverte.

`0x3f` reste non identifié ("inconnu" selon l'utilisateur, état=`1` -
verrouillé/pas encore débloqué), à reprendre plus tard. `0x49` dans le
même état (inconnu, verrouillé).

**Munitions/stock du "Déstabil. SOP" trouvées sans scan** : `0x44` tombe
dans la plage déjà couverte par la formule linéaire du bloc explosifs/
etc (`0x1D81E08 + id*0x18`, validée le 2026-09-24 sur `0x34`-`0x46`) -
calcul direct plutôt que scan, confirmé en lisant 0 (l'utilisateur n'en
avait aucun exemplaire, l'empêchant de tester l'objet en jeu). Forcé à
10 pour débloquer le test. Ajouté à `CONFIRMED_WEAPON_AMMO_RVAS`
(`0x44: 0x1D82468`). Hypothèse de nom en cours de vérification par
l'utilisateur : "poster déstabilisant" à la Magazine Playboy (objet de
diversion). **70 armes/objets couverts en munitions.**

**⚠️ DANGEREUX - CRASH CONFIRMÉ (2026-09-24)** : tenter d'équiper/utiliser
le "Déstabil. SOP" (`0x44`) en jeu après lui avoir forcé un stock (10
puis 1, retesté) a fait **planter le jeu à chaque fois** (fatal error,
dump généré). Précision de l'utilisateur après un 2e essai : **le crash
se déclenche précisément au moment de l'équiper**, pas juste en le
possédant en inventaire - confirme l'hypothèse d'un objet interne/debug
(probablement lié à un système SOP en ligne absent du mode solo) dont le
jeu ne sait pas charger les assets d'équipement. Pas de dégât réel
constaté (partie non sauvegardée au moment du 1er crash, jeu redémarré
normalement les deux fois, aucune autre arme/fonctionnalité affectée).
**Règle à respecter** : ne plus jamais équiper cet objet en jeu, même
avec un stock forcé. Le lire/écrire en mémoire ou le laisser en
inventaire sans l'équiper reste sans danger.

### Nettoyage de la liste + verrou de sécurité (2026-09-24)

Deux demandes de l'utilisateur suite aux découvertes ci-dessus :

1. **Armes jamais identifiées retirées de la liste, partout** (trainer
   ET MGS4SaveStats, pas seulement en mode avancé) - filtre sur
   `weapon_id in mgs4save.WEAPON_NAMES` côté trainer
   (`TrainerWindow.__init__`) et sur `entry["identified"]` côté
   `WeaponsPanel.show_slot` (gui_app.py). Les lignes "Arme #NN" bruyantes
   ont disparu des deux applications. Textes d'aide mis à jour en
   conséquence.
2. **"Destabil.SOP" (0x44) verrouillé en mode simple** - nouveau
   mécanisme générique `advanced_only_ids` sur `TableTab` (masque
   certaines lignes tant que le mode avancé n'est pas actif, combiné
   avec le filtre texte existant) et `GroupedWeaponsTab.DANGEROUS_IDS =
   {0x44}` qui l'active pour toutes les sections. Visible uniquement en
   mode avancé désormais, pour éviter qu'un utilisateur non averti (ex.
   le frère de l'utilisateur, destinataire prévu d'un build partagé)
   tombe dessus et fasse planter son jeu. Testé : ligne cachée en mode
   simple, visible en mode avancé.

### Onglet "FaceCamo" ajouté au trainer (2026-09-25)

À la demande de l'utilisateur, pour reprendre la même méthode
"bascule + vérification en jeu" (déjà très productive sur les armes)
appliquée cette fois aux FaceCamo. Techniquement, `item_state_rva()`
couvrait déjà ces ID depuis le tout début du projet (contrairement aux
armes) - le seul manque était une UI dédiée pour les manipuler
confortablement, ils étaient auparavant fondus avec les Gilets dans un
même onglet "OctoCamo".

- Nouveau `_FACECAMO_NAMES_VISIBLE` (`live_trainer.py`) : copie de
  `mgs4save.FACECAMO_NAMES` (13 entrées confirmées) + `0x28` ajouté avec
  un nom générique "FaceCamo #28 (inconnu)" - ce slot est coincé entre
  Campbell (`0x27`) et Drebin (`0x29`), très probablement un FaceCamo
  lui aussi mais jamais isolé individuellement (voir historique dans
  `FACECAMO_NAMES`).
- `_OCTOCAMO_NAMES` réduit aux seuls Gilets (`VEST_NAMES`).
- Nouvel onglet "FaceCamo" dans `ITEM_CATEGORIES`, entre "Objets" et
  "OctoCamo".

Testé : le trainer se lance sans erreur, onglet "FaceCamo (14)" présent,
"OctoCamo" réduit à "OctoCamo (10)".

**Toujours inconnus après cet ajout** : FaceCamo "Big Boss" et FaceCamo
"Doré" - IDs potentiellement n'importe où dans l'espace non classé (pas
forcément dans ce bloc contigu), donc pas ajoutés ici ; à chercher via
l'onglet "Non classes" existant si l'occasion se présente.

### Impasse sur "Doré" / "FaceCamo Doré" (2026-09-25)

Capture d'écran du menu "Visage" de l'utilisateur confirmant l'existence
de **2 entrées distinctes** verrouillées : "Doré" et "FaceCamo Doré"
(en plus de "Aucun"/"FaceCamo" déjà connus). Tentative de les retrouver
en forçant à `1` (Obtenu) les **6 derniers ID non classés** du tableau
objets (`0x14`-`0x19`, "Non classes" dans le trainer) en un seul lot -
taille très raisonnable, rien à voir avec l'incident dangereux du
2026-09-23 (dichotomie sur 9152 candidats). **Aucun changement observé**
en jeu après le forçage - ni Doré ni FaceCamo Doré ne sont dans ce lot.
Restauré immédiatement aux valeurs d'origine (`0x14`-`0x18` = 0, `0x19` =
1, déjà obtenu avant le test).

**Conclusion importante** : ces 6 ID étaient le dernier espace libre du
tableau objets (99 entrées, `ITEM_STATE_COUNT`) - il est désormais
**entièrement classé** sans que Doré/FaceCamo Doré y figurent nulle
part. **Correction** (l'utilisateur a rappelé le contexte déjà établi le
2026-09-01, voir plus haut dans ce fichier "Gilet Kaki/Vert inversés +
variantes Doré manquantes") : Doré est un bonus de précommande/MGS2 lié
au compte Steam, mais reste bien un flag persisté dans le fichier de
sauvegarde (le menu affiche un point rouge "verrouillé", pas une
absence) - PAS un flag vérifié dynamiquement comme je l'avais
faussement conclu. Puisque le tableau est complet, l'hypothèse à
retenir est donc celle déjà posée le 2026-09-01 : Doré/FaceCamo Doré se
cachent probablement parmi des ID **déjà attribués à autre chose mais
jamais vérifiés individuellement** (ex. couleurs de Gilet Bleu/Rouge/
Orange/Tan) - un de nos noms actuels serait donc faux. Piste à reprendre
dans ce sens plutôt qu'en cherchant un ID libre.

### Big Boss (0x28) enfin identifié (2026-09-25)

Premier fruit du nouvel onglet "FaceCamo" : `0x28` forcé à `1` via le
trainer, confirmé en jeu par l'utilisateur - c'est bien le FaceCamo
**"Big Boss"**, dont le vrai ID était inconnu depuis le 2026-09-05 (voir
historique dans `FACECAMO_NAMES`, ancien `0x27` réassigné à Campbell
avant ça). Ajouté à `FACECAMO_NAMES` (mgs4save.py) ; le placeholder
`0x28` devenu inutile retiré de `live_trainer.py`. FaceCamo Doré et
Doré (Gilet) restent à chercher, probablement parmi les entrées
"jamais vérifiées individuellement" comme noté ci-dessus. `0x28` a
depuis été reverrouillé (65535) après le test - pas légitimement
obtenu par l'utilisateur.

### Déduction de l'utilisateur : FaceCamo Doré est dérivé, pas un ID séparé (2026-09-25)

Test malin de l'utilisateur : tous les FaceCamo verrouillés d'un coup →
seuls "Aucun" et "Doré" apparaissent dans le menu Visage. FaceCamo
(0x1f) débloqué → "FaceCamo Doré" apparaît aussi. Déduction : "FaceCamo
Doré" n'est probablement PAS un slot indépendant, mais une variante
affichée dynamiquement dès que FaceCamo (0x1f) ET le bonus de compte
"Doré" sont tous les deux vrais - donc pas besoin de chercher un ID
séparé pour "FaceCamo Doré" spécifiquement. Seul "Doré" (le flag de
base) reste à localiser.

Vérification par scan : 65535 scanné sur toute la mémoire (22 331 233
candidats bruts, bien trop pour être exploitable - 0xFFFF est un motif
extrêmement courant), puis restreint aux régions stables de l'image du
module (97 640 candidats). FaceCamo débloqué (0x1f → 1), puis
re-vérification des 97 640 candidats : seuls 6 ont changé, dont 5 dans
des zones sans rapport (bruit) et 1 qui est... `item_state_rva(0x1f)`
lui-même (notre propre écriture). **Rien de nouveau trouvé** - confirme
que rien n'est écrit nulle part quand "FaceCamo Doré" apparaît dans le
menu : c'est une pure vérification de lecture au moment de l'affichage,
pas un flag qui se met à jour en réaction à autre chose. Le flag "Doré"
lui-même ne bouge jamais en réponse à ce qu'on peut manipuler côté save
individuelle - donc impossible à isoler par la méthode "avant/après"
habituelle (aucun levier pour le faire changer depuis une save
individuelle).

### Piste MGS4SYS.SAV explorée et refermée (2026-09-25)

Suite à la suggestion de l'utilisateur (le bonus Doré est lié au compte
Steam/MGS2, donc peut-être dans le fichier système partagé plutôt que
par save) : localisation et déchiffrement de `MGS4SYS.SAV`
(`BLJM67001S/MGS4SYS.SAV`, même clé XOR que `MGS4.SAV`, 513 octets).
Confirme la structure déjà repérée à l'époque de la découverte de ce
fichier (voir section "MGS4SYS.SAV" plus haut) :
- Zone `0x40-0xc7` : liste de ~20 valeurs `0x0000xxxx` façon
  enregistrements Database/Intel (`0x801a`, `0x8016`, `0x2001`...), pas
  creusée davantage (structure différente, moins prometteuse pour un
  camouflage cosmétique).
- Zone `0xe0-0x158` : 30 valeurs u32, chacune une puissance de 2
  distincte (avec quelques doublons entre entrées) - ressemble à une
  table de constantes/masques plutôt qu'à des flags "obtenu" un par un.

**Localisée en mémoire live** : pattern de 40 octets de la zone
`0x40-0xc7` recherché sur toute la mémoire du process - 1 seul match,
à l'adresse RVA `0x1D77BF0` (zone stable de l'image du module, comme le
tableau objets/armes - pas un pointeur dynamique, vérifié par lecture
de la zone bitmask et comparaison octet à octet avec le fichier
déchiffré : identiques). Zone bitmask = `0x1D77CD0`-`0x1D77D44`
(30 × u32).

**Question de sécurité légitime de l'utilisateur** avant de toucher à
quoi que ce soit ici : le trainer écrit-il directement dans le fichier
et risque-t-il de corrompre toutes les saves ? Réponse : non, toutes
les écritures passent par `WriteProcessMemory` (RAM du process
uniquement, jamais le disque directement) - mais incertitude réelle sur
le moment où le jeu réécrit `MGS4SYS.SAV` sur disque (fichier partagé
par toutes les saves, contrairement aux tables par-slot déjà
manipulées). Par précaution, backup indépendant de `MGS4SYS.SAV` fait
dans `backups/` (ajouté au `.gitignore`) avant tout test dans cette
zone.

**Deux tests menés avec ce backup comme filet de sécurité** :
1. Diff complet des 513 octets de la structure live avant/après bascule
   de FaceCamo (0x1f) : **0 octet différent** - cette zone ne réagit à
   rien de ce qu'on peut manipuler côté save individuelle.
2. Les 30 valeurs de la zone bitmask forcées à `0` simultanément, puis
   restaurées immédiatement (vérifié octet par octet) : **aucun
   changement visible** dans les menus (Visage, Poitrine...) pendant le
   test.

**Conclusion** : cette zone ne semble pas être le siège de flags "Doré
débloqué" directement lisibles/modifiables de façon simple. Piste mise
de côté - exploration consciencieuse (tableau objets complet, scan
mémoire complet post-bascule FaceCamo, structure MGS4SYS.SAV) sans
trouver de levier exploitable pour l'instant. À reprendre seulement si
une nouvelle piste concrète se présente (ex. quelqu'un sans le bonus
précommande qui partage son `MGS4SYS.SAV` pour un diff direct).

### Confirmation définitive : Doré n'est pas dans le fichier de sauvegarde (2026-09-25)

Test décisif de l'utilisateur côté Gilet : les 10 `VEST_NAMES` connus
(`0x2d`-`0x36`) tous forcés à `65535` (verrouillé) via le trainer.
Résultat en jeu : seuls **Kaki** et **Doré** restent sélectionnables/
portables dans la liste, tout le reste a bien disparu. Deux
enseignements :

- **Kaki (`0x31`)** ignore son propre flag verrouillé (vérifié en
  mémoire : bien à `65535`, mais reste portable en jeu) - même
  phénomène que le Masterkey/certains silencieux (accessoire "de base"
  dont le jeu ne revérifie pas l'état). Probable couleur de départ,
  toujours disponible par design.
- **Doré** reste portable alors que **tout** le reste est verrouillé -
  la preuve la plus solide obtenue sur toute cette enquête. Confirme
  que le Gilet Doré (et très probablement FaceCamo Doré, même
  logique) n'est **pas géré par le fichier de sauvegarde du tout** :
  le jeu vérifie le droit Steam (précommande/MGS2) directement à
  l'exécution et l'accorde sans passer par aucun flag manipulable en
  mémoire ou sur disque - cohérent avec l'absence totale de résultat
  sur tous les tests précédents (scan tableau objets, diff mémoire
  complet, structure MGS4SYS.SAV).

**Conclusion finale** : Doré (Gilet et FaceCamo) est un cas d'entitlement
Steam vérifié dynamiquement, pas une donnée persistée - **aucun ID ne
sera jamais trouvé pour ces deux variantes**, ce n'est pas un manque de
recherche mais une impossibilité de fond. Sujet définitivement clos.

### Bonus inattendu : correction des Gilets Olive/Noir/Gris (2026-09-25)

Le test "verrouiller tous les gilets" pour traquer Doré a révélé au
passage une erreur préexistante : l'ancienne attribution
`0x2d`=Olive/`0x2e`=Noir/`0x2f`=Gris/`0x30`=Bleu marine n'avait jamais
été confirmée individuellement (juste déduite par ordre), et était
fausse. Test isolé propre (méthode cumulative suggérée par
l'utilisateur : tout verrouiller, puis débloquer un par un en gardant
les précédents actifs plutôt que de reverrouiller entre chaque test -
plus rapide et moins sujet aux erreurs d'observation) :

| ID | Couleur confirmée |
|---|---|
| `0x2e` | Olive |
| `0x2f` | Noir |
| `0x30` | Gris |
| `0x31` | Kaki (probable par position, mais non confirmable par ce test - voir ci-dessous) |
| `0x2d` | Aucune couleur n'apparaît (testé 2 fois) - rôle réel inconnu |

**Kaki (`0x31`) et Doré ignorent tous les deux leur flag verrouillé** -
Kaki reste portable même forcé à `65535` (vérifié en mémoire). Même
phénomène que le Masterkey/plusieurs silencieux : probablement une
couleur de départ que le jeu ne revalide jamais depuis cette case
mémoire. Contrairement à Doré, ce n'est PAS un entitlement Steam - juste
un flag ignoré comme dans les autres cas déjà documentés.

**"Bleu marine" n'a plus d'ID connu** - retiré de `VEST_NAMES`, `0x2d`
repasse dans l'onglet "Non classes" du trainer (`Objet #45`) en
attendant. Piste pour la suite : soit `0x2d` est bien Bleu marine mais
avec le même comportement "flag ignoré" que Kaki (pas encore testé sous
cet angle - il faudrait vérifier si Bleu marine est déjà portable même
verrouillé, comme Kaki), soit c'est un slot inutilisé et le vrai ID de
Bleu marine reste à chercher ailleurs.

Mis à jour dans `VEST_NAMES` (mgs4save.py) - propagé automatiquement à
`_OCTOCAMO_NAMES`/`_NON_CLASSES_NAMES` (live_trainer.py) et à
`CollectionPanel` (gui_app.py) puisque c'est le même dictionnaire
partagé.

**Vérification complémentaire** : même méthode cumulative appliquée aux
5 couleurs restantes (`0x32`-`0x36`, Vert/Bleu/Rouge/Orange/Brun,
initialement confirmées en 2026-09-02 par un lot de 5 débloquées
simultanément) pour s'assurer qu'elles n'avaient pas la même erreur -
**toutes reconfirmées correctes**, une par une, dans l'ordre déjà
documenté. L'erreur ne concernait donc bien que le groupe des 5
premières couleurs (les "déjà possédées dès le début", jamais testées
individuellement à l'origine).

**Correction finale** : l'utilisateur confirme directement que `0x31`
est en réalité **Bleu marine**, pas Kaki comme supposé. Comme Kaki,
Bleu marine reste portable même verrouillé (`65535`) - même phénomène
que le Masterkey/plusieurs silencieux. Puisque Bleu marine occupe déjà
`0x31`, et que `0x2d` (jamais concluant lors des tests) est le seul nom
du groupe encore sans ID, **Kaki est très probablement `0x2d`** - mais
ce résultat est fondamentalement indécidable par cette méthode : Kaki
étant déjà visible en permanence dès le départ, débloquer `0x2d` ne
peut de toute façon jamais rien changer de visible, qu'il soit le bon
ID ou non. `0x2d` = Kaki ajouté en **confiance basse** (candidat par
élimination, pas une confirmation directe).

Bilan final Gilets : `0x2d`=Kaki (confiance basse), `0x2e`=Olive,
`0x2f`=Noir, `0x30`=Gris, `0x31`=Bleu marine (ces 4 en confiance haute),
`0x32`-`0x36`=Vert/Bleu/Rouge/Orange/Brun (confiance haute, reconfirmées).
**10 gilets sur 11 identifiés** - il ne manque plus que "Gilet Doré",
qui restera à jamais introuvable (entitlement Steam, voir plus haut).

### Ordre d'affichage FaceCamo aligné sur le jeu (2026-09-25)

À la demande de l'utilisateur, deux captures d'écran successives du
menu "Visage" ont donné l'ordre réel des 14 FaceCamo (qui ne suit PAS
l'ordre croissant des ID) : FaceCamo, Jeune Snake, Jeune Snake avec
bandana, MGS1, L./R./C./S. Beauty, Campbell, Otacon, Raiden A/B, Drebin,
Big Boss. Nouveau `FACECAMO_SORT_ORDER` (mgs4save.py, même mécanisme que
`WEAPON_SORT_ORDER` déjà existant pour les armes) branché dans le
trainer (`TrainerWindow`, onglet FaceCamo trié par cet ordre plutôt que
par ID croissant). Vérifié : ordre final identique aux captures
d'écran, application testée sans erreur.

Au passage, la capture confirme qu'il y a bien **2 entrées Raiden
distinctes** ("Raiden A"/"Raiden B") dans le menu, contredisant une
ancienne note (2026-09-02) qui affirmait qu'il n'y en avait qu'une
seule - cette ancienne note était donc elle-même erronée. Nos deux ID
`0x2b`/`0x2c` ("Visière fermée"/"Visière ouverte") correspondent très
probablement à "Raiden A"/"Raiden B" dans cet ordre (déjà confirmés
individuellement par ailleurs), aucun changement nécessaire pour eux.

### Onglets FaceCamo/OctoCamo refusionnés (2026-09-25)

Retour en arrière partiel sur la séparation de la veille : l'utilisateur
préfère finalement la même logique que MGS4SaveStats (`CAMO_GROUPS`
dans gui_app.py) - un seul onglet "OctoCamo" avec des sous-sections
empilées ("FaceCamo", "Gilet", "Octocamo") plutôt que des onglets
séparés. Nouvelle classe `GroupedItemsTab` (`live_trainer.py`),
généralisation de `GroupedWeaponsTab` sans les mécanismes spécifiques
aux armes (pas de munitions, une seule convention verrouillé/obtenu
`binary_lock_value=65535` commune à toutes les sections). FaceCamo
garde son ordre d'affichage spécial (`FACECAMO_SORT_ORDER`) au sein de
sa sous-section. Troisième sous-section "Octocamo" (motifs de base)
incluse mais vide (`_OCTOCAMO_BASE_NAMES = {}`) - jamais d'ID trouvé
pour ces camouflages, même trou que `CAMO_GROUPS`/`group_totals` côté
appli principale ; se cache automatiquement tant qu'elle est vide (0
lignes).

Testé : onglet "OctoCamo (24)" avec sous-sections "FaceCamo (14)" et
"Gilet (10)" visibles, "Octocamo" correctement masquée.

### Tentative de localiser les 21 motifs Octocamo de base (2026-09-25)

L'utilisateur voulait appliquer la même méthode que pour les Gilets aux
21 motifs Octocamo (`OCTOCAMO_INFO` dans mgs4save.py, jamais reliés à
la vraie save - voir commentaire sur ce dict). Trois tentatives :

1. **ID au-delà du tableau objets** (`102`/`0x66`, repéré la veille
   pendant la chasse à Doré, seul à lire `1` dans la zone 99-104) forcé
   à `0` : aucun effet visible dans le menu Octocamo en jeu.
2. **Diff complet de deux saves** (`BLJM67001G6AB54D83` avec Camo
   Cadavre, `BLJM67001G6AB53FC9` sans) : **2648 octets différents**,
   toujours ~2340 après avoir exclu les zones déjà connues (tableau
   objets, tableau armes, table munitions `0x350`, champs STATS) - bien
   trop bruité pour isoler un seul flag, ces deux saves divergent sur
   bien plus que le Cadavre (zones de mission/checkpoint qui varient
   naturellement selon la progression). Cadavre ne peut pas être obtenu
   à la demande pour un test contrôlé avant/après (déblocage lié à la
   fin du jeu) - piste diff abandonnée faute de paire de saves assez
   proches.
3. **Struct complet de l'item en mémoire live** (72 octets, pas
   seulement le champ état à +0x14 utilisé jusqu'ici) : révèle un champ
   +0x08 qui ressemble à un tag de catégorie interne (FaceCamo `0x1f` =
   `0x200000`, Kaki `0x2d` ET Bleu marine `0x31` = `0x400000` tous les
   deux - probablement "ceci est un Gilet" -, Déstabil.SOP `0x44` = `0`)
   - intéressant pour la structure generale, mais ne ressemble pas à un
   flag "Octocamo obtenu" par motif individuel.

**Conclusion** : aucune des 3 approches n'a abouti. Combiné à l'ancien
scan complet du tableau objets (2026-09-06, avec Cadavre confirmé
débloqué sur cette save-là - aucun ID inexpliqué à 1) qui avait déjà
exclu ce tableau, on n'a plus de piste concrète à tester sans une paire
de saves "juste avant/après" un vrai déblocage. Mis de côté en attendant
une meilleure opportunité (ex. l'utilisateur termine le jeu et peut
sauvegarder juste avant/après le 41e death pour Cadavre).

### Piste "buffer de liste temporaire" pour FaceCamo/Gilet (2026-09-25)

Idée de l'utilisateur : plutôt que traquer un flag "obtenu", chercher où
vit l'**ID actuellement équipé**, en scannant pour la valeur exacte du
FaceCamo/Gilet porté puis en la recoupant après un changement (même
méthode que d'habitude, mais sur un concept différent).

- **FaceCamo équipé** : scan sur MGS1 (42) → Jeune Snake (32) → MGS1
  (42) confirmé sur une seule adresse (`0x2cd37856a40`, tas dynamique).
  Mais la vérification suivante (changement pour Vert, puis re-test) a
  échoué - l'adresse ne correspondait plus. Surveillance continue en
  arrière-plan (polling toutes les 0.15s sur une fenêtre de 128 octets
  autour de cette adresse) a révélé la cause : **ce n'est pas une case
  "équipé" stable, mais un buffer temporaire de liste que le jeu
  réécrit entièrement à chaque interaction avec un menu de
  sélection** (tout le bloc change d'un coup, avec une structure
  relative similaire mais une plage de valeurs différente selon le menu
  actif - ex. 31-55 pour FaceCamo/Gilet, plage différente 9-33 observée
  une fois lors d'un changement de FaceCamo vers "Otacon").
- **Tentative d'extension à Octocamo** : même zone surveillée en
  continu pendant que l'utilisateur naviguait dans le menu Octocamo
  (Forêt, Cadavre, Mouche testés) - **aucun changement détecté**, cette
  zone n'est donc pas utilisée par le menu Octocamo. Piste non
  transférable à cette catégorie, contrairement à l'espoir initial.

Conclusion : mécanisme intéressant compris (buffer de liste UI
transitoire, pas une case de donnée stable), mais qui n'aide pas à
localiser les ID Octocamo. Les pistes Octocamo restent toutes closes
pour l'instant (voir section précédente).

### Chasse au "code effet spécial" via Cheat Engine (2026-09-25)

Nouvelle piste de l'utilisateur, cette fois via Cheat Engine directement
(scan "Unknown initial value" → "Changed value" répété sur plusieurs
changements de motif, bien plus rapide que notre approche Python). Trois
adresses stables trouvées dans l'image du module :
`mgs4.exe+1DF5148`, `+1DF514A`, `+1DF514E`.

**`+1DF514E` converge exactement avec un candidat qu'on avait isolé de
notre côté** (diff complet Rire→Metal→Mouche, adresse
`0x7ff706bb514e` = même RVA) - double confirmation indépendante :
Rire=78, Metal=85, Mouche=84.

Tableau complet obtenu par l'utilisateur sur les 19 motifs testables
(hors Doré/Précommande) :

| Motif | `1DF514E` |
|---|---|
| Infiltration | 0 |
| Olive | 0 |
| Tigré | 0 |
| Forêt | 0 |
| 3 Couleurs Désert | 0 |
| Marpat | 0 |
| Cadavre | 0 |
| Digit. B | 0 |
| Digit. R | 0 |
| Pleurs | 80 |
| Mouche | 84 |
| Gear | 108 |
| Haven | 77 |
| Rire | 78 |
| Metal | 85 |
| Snake | 83 |
| Rage | 79 |
| Hurler | 81 |
| Beauté | 82 |

**Interprétation** : en recoupant avec `OCTOCAMO_INFO` (descriptions
déjà connues), le motif est clair - tous les motifs à `0` sont
exactement ceux décrits comme "sans effet spécial", et tous les motifs
à effet de gameplay documenté (Rire fait rire les ennemis, Metal réduit
les dégâts, Gear réduit la perte de Psyché...) ont un code non-nul
distinct. **Ce n'est donc pas un ID de motif, c'est le code de l'effet
spécial actif** - ça ne permet pas de distinguer les 9 motifs "sans
effet" entre eux (tous à 0), donc ne résout pas le besoin initial
(identifier tous les ID pour debloquer/verrouiller). Exceptions
notables : Cadavre et Digit. B ont un effet décrit mais restent à 0 -
probablement un système de detection IA distinct plutot qu'un bonus de
stats comme les autres.

### Piste MGS4.CT (fichier Cheat Engine communautaire) (2026-09-25)

Recherche dans `MGS4.CT` (fourni par l'utilisateur, licence perso) d'une
section documentant Face Camo/Octo Camo. Trouvé une section "Items --
Unknown" avec des entrées `pItems+48*14` ("Face Camo") et `pItems+48*18`
("Octo Camo"), utilisant le meme pointeur `pItems` que la fonction
`objItems`/`900AE6` deja utilisee pour deriver notre propre formule
`item_state_rva()`. Interpretation initiale (ID general 14/18 dans le
tableau objets, comme Solid Eye) **contredite** par nos propres donnees
deja confirmees par isolation : ID 14 = "Muna" et ID 18 = "Prise
Scanner" chez nous, pas "Face Camo"/"Octo Camo". Cette section du
fichier CE est d'ailleurs explicitement etiquetee "WIP || Graveyard"
(travail abandonne) par son propre auteur - meme categorie de piste
non fiable que le pointeur `varbuf` deja ecarte au debut du projet.
**Piste rejetee.**

### Vérification finale : structs complets FaceCamo/Gilet/Tenue (2026-09-25)

Dernier test suggéré par l'utilisateur : dump complet des 72 octets de
struct (pas seulement l'état à +0x14) pour les 28 ID connus de
FaceCamo/Gilet/Tenue, recherche de tout `1` inattendu ailleurs dans le
struct. **Résultat uniforme et négatif** : tous les items montrent
exactement les 2 mêmes offsets à `1` (`+0x14` état connu, `+0x16`
valeur constante identique partout, pas distinctive) - rien de caché
ni de particulier à un item plutôt qu'un autre.

### Tentative de téléportation narrative via édition de fichier (2026-09-25)

Idée de l'utilisateur pour obtenir une paire "avant/après" propre sur
Cadavre : créer une save fraîche, puis éditer directement le fichier
(`stage_code`/`progress` à 0x34-0x58) pour la faire pointer sur le même
point de l'histoire qu'une save avancée (`A17A36`, Acte 5 "Mariage",
progress=261), afin de pouvoir ensuite jouer jusqu'au vrai déclencheur
de fin avec `continues` forcé à 50 et observer ce qui change au
déblocage de Cadavre.

**Tentative 1 (mémoire live)** : recherche du pattern `stage_code`
("s01a00l" + contexte) en mémoire live - **introuvable**, ni dans
l'image du module ni dans le tas. Le jeu utilise probablement en
interne une representation numerique completement differente de la
chaine ASCII du fichier de save (qui ne serait qu'un format de
serialisation a l'ecriture) - pas de piste live exploitable ici.

**Tentative 2 (édition de fichier directe)** : backup du fichier fait
dans `backups/`, puis modification directe de `stage_code` (`s01a00l`
→ `s30a00l`) et `progress` (1 → 261) sur le fichier déchiffré,
réécriture avec la même fonction XOR (symétrique). Le fichier se
relit correctement avec `read_progress_info()` côté Python, mais **le
jeu refuse de charger la save** ("mauvaise signature" selon
l'utilisateur) - confirme l'existence d'un **checksum anti-corruption**
déjà suspecté depuis le tout début du projet ("Pas de signature
cryptographique façon PS3... un simple checksum anti-corruption est
possible mais pas encore localisé", voir tout début de ce fichier) mais
jamais localisé ni compris. Fichier restauré depuis le backup
immédiatement après - aucune perte, mais confirme que **l'édition
directe de fichier n'est pas exploitable** pour ce genre de
modification tant que ce checksum n'est pas percé (chantier séparé et
non entamé, potentiellement conséquent : algorithme et portée
inconnus).

## Nouvelles découvertes : état de jeu en direct (Vie/Endurance/Stress/Alerte) (2026-09-25)

Suite logique après la piste `pItems`/`pStatistics` explorée pendant la
chasse à Octocamo : le fichier `MGS4.CT` contient une section "aob
Statistics" **non marquée WIP/Graveyard** (donc a priori fiable,
utilisée pour de vraies triches "vie/endurance/batterie infinies") qui
confirme que **`pStatistics` = notre `linkvarbuf`** déjà utilisé (même
pointeur `mgs4.exe+1C28B28`). Recoupement supplémentaire : les offsets
`+0x34` (zone/stage) et `+0x54` (scène/progression) et `+0x1C0` (Drebin
actuel) documentés dans le CT correspondent EXACTEMENT aux offsets déjà
établis chez nous pour le fichier de save - preuve que `linkvarbuf`
mirrore le format du fichier avec les memes offsets pour cette region.

**Champs confirmés en jeu, testés avec de vraies transitions** (Vie et
Endurance touchées par de vrais dégâts/déplacements, Stress observé sur
plusieurs valeurs distinctes avec correspondance précise à l'affichage
HUD) :

| Champ | Offset (`linkvarbuf` +) | Taille | Formule |
|---|---|---|---|
| Vie actuelle | `0xB48` | u16 | valeur brute (2000 = 100%) |
| Vie max | `0xB4A` | u16 | |
| Endurance/Stamina actuelle | `0xB4C` | u16 | valeur brute (2000 = 100%) |
| Endurance/Stamina max | `0xB4E` | u16 | |
| Stress | `0xB50` | u16 | **÷10 = %** (confirmé pile : 3→0.3%, 60→6%, 125→12.5%) |
| Batterie Solid Eye actuelle | `0xB52` | u16 | (300 observé, jamais recoupé avec l'affichage) |
| Batterie Solid Eye max | `0xB54` | u16 | |
| Metal Gear REX vie | `0xB70` | u32 | (60000 observé sur save fraîche, jamais recoupé en combat) |
| Metal Gear REX vie max | `0xB74` | u32 | |
| Drebin Points | `0x1C0` | u32 | déjà connu/utilisé (`drebin_actuel`) |
| Drebin Points (ventes) | `0x1C4` | CT dit 2 octets, nous avons 4 (`drebin_total_ventes`) - écart mineur a noter |

**État d'alerte** : adresse **statique** (pas via `linkvarbuf`) trouvée
dans le même fichier CT, section "Alert -- Ignore" (elle-même WIP/
Graveyard, mais l'adresse capturée à l'injection s'est révélée fiable
malgré tout) : `mgs4.exe+1D77AB8` (u32, PAS de `MODULE_PATCH_SHIFT` à
appliquer - confirmé car appliquer le décalage donne une valeur
absurde). Très proche de la zone `MGS4SYS` trouvée plus tôt dans la
journée (`0x1D77BF0`), même région générale de "données système/jeu".
**3 états confirmés par tests réels successifs** : `0`=Normal/non
repéré, `1`=Alerte, `2`=Évasion.

**Piste non résolue** : la jauge de détection précise affichée en HUD
("ALERTE 99.99"/"49.66", 2 décimales) est une variable DIFFERENTE du
statut 0/1/2 - recherchée activement (scan entier + flottant) autour de
`linkvarbuf`, y compris avec le jeu **suspendu** (voir ci-dessous) pour
avoir une valeur figée fiable à chercher - **rien trouvé**. Probablement
recalculée à la volée par le code d'affichage HUD à partir de données
IA (distance/temps de détection des ennemis proches) plutôt que stockée
comme une variable simple. Mis de côté pour l'instant.

### Nouvel onglet "Etat de jeu" dans le trainer (2026-09-25)

Ajout de `VITALS`/`ALERT_STATE_RVA`/`ALERT_STATE_NAMES` et des methodes
`MGS4Live.read_vital`/`write_vital`/`read_alert_state`, plus une nouvelle
classe `VitalsTab` (nouvel onglet "Etat de jeu" dans le trainer, juste
apres "Stats") : Vie/Endurance/Stress/Batterie Solid Eye/Metal Gear REX
avec case **"Verrouiller"** par ligne (reecrit la valeur a chaque
rafraichissement - vie/endurance infinies etc.), plus l'etat d'alerte
affiche en lecture seule (l'ecriture ne tient pas, confirme par
l'utilisateur - forcer `1` ou `2` puis figer le jeu 2.5s plus tard n'a
donne aucun changement visible, le jeu la recalcule en continu depuis
l'etat reel de l'IA).

Testé fonctionnellement : lecture correcte de tous les champs, et le
verrou confirmé (vie forcée à 999 "de l'exterieur", `refresh()` l'a bien
remise à la valeur verrouillée 111 juste après).

**Batterie Solid Eye - max non correle au nombre de batteries** :
l'utilisateur a teste 1 vs 6 batteries possedees (`item[0x3c]`, voir
`BATTERY_MAX`/`read_battery_count` dans mgs4save.py) et un changement de
zone - aucun des deux ne fait bouger le max Solid Eye live (`linkvarbuf
+0xB54`, toujours 300). Le champ reste bien une **vraie valeur en
memoire** (pas une constante "en dur" dans le code, puisque justement
accessible via ce pointeur de donnees) mais son contenu semble ecrit une
fois pour toutes plutot que derive dynamiquement du nombre de batteries.
**Confirme fonctionnel et pas juste cosmetique** : force a `800`, le
jeu a bien recalcule la jauge en consequence (barre partiellement videe
relativement au nouveau plafond, puis recharge visible vers 800) -
prouve que ce champ est reellement utilise par la logique du jeu
(affichage ET recharge), pas un artefact inerte. Restaure a `300`
apres test.

**Piste ouverte (2026-09-25, non testee davantage)** : apres etre mort
en jeu, l'utilisateur a constate que le max Solid Eye etait repasse a
`800` alors qu'il ne possede qu'une seule batterie - alors que la
valeur avait ete explicitement remise a `300` cote process juste avant.
Hypothese la plus probable : le jeu conserve un instantane (checkpoint/
"continue") d'une partie du struct `linkvarbuf` pris a un moment ou
notre test avait deja pousse le champ a `800`, et la restaure telle
quelle au rechargement du dernier point de sauvegarde - plutot qu'un
recalcul depuis le nombre de batteries (deja exclu ci-dessus) ou une
"vraie" valeur deverrouillee par la mort. A verifier : remettre le
champ a `300`, mourir une fois SANS l'avoir modifie entretemps, et
voir si la valeur reste a `300` au respawn (confirmerait/infirmerait
l'hypothese du snapshot checkpoint).

**Etat d'alerte affiné a 3 valeurs confirmees par transitions reelles
successives** (pas les 2 initialement supposees - l'utilisateur a
precise qu'il manquait un etat, la vraie sequence MGS4 etant Normal ->
Alerte -> Evasion) : `0`=Normal/non repere, `1`=Alerte, `2`=Evasion.
Reste a distinguer si `1` correspond specifiquement a l'alerte "jaune"
(recherche, position inconnue des ennemis) ou s'il y a un 4e etat
distinct pour l'alerte "rouge" (position connue) - piste ouverte, pas
encore testee (tentative de forcer `1`/`2` par ecriture infructueuse
comme note ci-dessus, il faudra observer passivement une vraie
transition en jeu).

### Nouvelle capacité : suspendre/reprendre le process (2026-09-25)

Ajout d'une capacité générale utile pour figer le jeu pendant les tests
(lire des valeurs sans qu'elles changent en temps réel, contrairement à
la course contre la montre habituelle) : `NtSuspendProcess`/
`NtResumeProcess` (ntdll, via un handle `OpenProcess` avec le droit
`PROCESS_SUSPEND_RESUME = 0x0800`, non present dans les droits de
`ProcessHandle` par defaut - handle temporaire dedie a cet usage). Gel
complet du process (pas le menu pause du jeu, un vrai freeze systeme,
image/son fige) - testé et confirmé fonctionnel (capture d'écran de
l'utilisateur montrant le HUD figé), sans effet de bord observé au
resume. Utile pour figer un instant precis et scanner sereinement.

**Complément** : snapshot complet des 29 structs avant/après un
changement réel de motif (Snake) - **0 octet différent**, confirmation
définitive et propre qu'aucun de ces structs ne réagit à la sélection
Octocamo (pas seulement "pas de 1 inattendu à un instant donné", mais
"rien ne bouge du tout entre deux sélections différentes").

**Bilan de la journée sur Octocamo** : de très nombreuses pistes
explorées avec sérieux (tableau objets complet, diff de fichiers
save, struct mémoire, buffer UI transitoire, scan complet Python +
Cheat Engine, fichier CE communautaire, vérification structs
complémentaires) - aucune n'a permis de retrouver les 21 vrais ID de
motifs Octocamo. Seul résultat concret conservé : la table "code
effet spécial" à `1DF514E`, intéressante mais insuffisante pour
l'objectif initial (verrouiller/débloquer chaque motif). Chantier
refermé, à reprendre uniquement si une idée vraiment nouvelle émerge.

### Onglet Stats du trainer reorganise en cartes (2026-09-25)

L'onglet Stats (`live_trainer.py`, `StatsTab`) etait une simple table a
plat des 30 champs de `mgs4save.STATS` (moins drebin, deja gere
ailleurs), avec une colonne "Offset" hexadecimale peu utile a l'usage
courant et aucun regroupement - jugee peu lisible par l'utilisateur.
Remplacee par une grille de `QGroupBox` (meme esprit que les cartes de
`StatsPanel` dans gui_app.py) regroupant les champs par theme via le
nouveau `STATS_TRAINER_GROUPS` (Combat / Infiltration / Mouvement /
Objets / Flashbacks / Temps), offset+type deplaces en tooltip sur le
libelle plutot qu'en colonne. Le filtre texte cache maintenant les
lignes individuelles ET les cartes qui se retrouvent vides. Verifie
par script que `STATS_TRAINER_GROUPS` couvre exactement les 30 champs
attendus (aucun manquant, aucun en trop).

**Iteration suivante (meme jour)** : retour utilisateur sur un
screenshot - la carte `QGroupBox` affichait une valeur en gros/gras
juste a cote d'un spinbox qui montrait deja le meme nombre (doublon
illisible pour un neophyte), et le bouton "OK" etait questionne. Refait
en suivant la convention deja etablie ailleurs dans le trainer
(GroupedWeaponsTab/GroupedItemsTab) plutot qu'en copiant le style carte
de gui_app.py : une mini `QTableWidget` par section (colonnes "Champ"/
"Valeur", dimensionnee a son contenu comme `fit_height` dans TableTab)
au lieu du `QGroupBox`+lignes libres. Plus de valeur dupliquee : le
spinbox EST l'affichage (les champs `_frames` montrent l'equivalent
hh:mm:ss via `setSuffix()` plutot qu'un 2e label). Bouton "OK" retire -
`setKeyboardTracking(False)` + ecriture sur `valueChanged` : les
fleches/la molette ecrivent immediatement, la saisie clavier n'ecrit
qu'a la validation (Entree/perte de focus), evite les ecritures
intermediaires incompletes pendant la frappe.

**Iteration suivante (meme jour, screenshot)** : le suffixe "(~HH:MM:SS)"
ajoute au spinbox brut des champs `_frames` etait tronque (colonne
dimensionnee avant que le suffixe soit connu) et l'utilisateur voulait
un vrai format HH:MM:SS plutot qu'un nombre de frames avec une
approximation entre parentheses. Remplace par 3 spinbox H/M/S cote a
cote (`_build_time_widget`/`_write_time`, boutons +/- caches via
`NoButtons` - inutiles/encombrants a 3 sur la meme ligne, molette et
saisie clavier restent actives) plutot qu'un `QTimeEdit` : son plafond
Qt de 23:59:59 ne convient pas a `temps_jeu_frames`/`temps_boite_carton_
frames`/`temps_baril_frames` (u32, peuvent largement depasser 24h de
jeu cumule). Conversion H/M/S -> frames faite via `FRAMES_PER_SECOND`
(approximation deja assumee ailleurs, framerate reel variable) et
plafonnee a la taille reelle du champ (u16 ou u32) avant ecriture.
