# MGS4 Save Stats

Petit utilitaire pour lire les statistiques de progression (kills, alertes,
temps passé à ramper/accroupi, Drebin points, etc.) depuis les fichiers de
sauvegarde de Metal Gear Solid 4 (portage PC Steam, sorti en 2026).

But : lecture seule. Ce n'est **pas** un éditeur de save.

## Emplacement des saves (Steam)

```
<SteamLibrary>\steamapps\common\METAL GEAR SOLID 4\mgs4_savedata_win\<SteamID64>\mgs4\<SLOT_ID>\MGS4.SAV
```

Chaque `<SLOT_ID>` (ex: `BLJM67001G6A91DA17`) contient :
- `MGS4.SAV` / `MGS4.bak` — le vrai save de partie (identiques, `.bak` est un
  simple miroir, pas un historique)
- `METADATA.SAV` / `METADATA.bak` — petit en-tête (129 octets, timestamps +
  quelques compteurs, pas encore analysé en détail)
- `ICON0.PNG` — capture d'écran du save

`BLJM67001S/MGS4SYS.SAV` = données système partagées entre slots (à explorer).

Le dossier `MGS4DB/` à côté du jeu est l'appli "MGS4 Database" (encyclopédie
bonus déjà présente sur PS3). Son save (`DBSaveSlot.sav`, format GVAS/Unreal)
ne contient que des réglages d'UI (langue, clavier, fiches lues) — pas les
stats de jeu. Lancé directement, l'exe se contente de relancer le jeu (attend
probablement d'être invoqué depuis un menu interne).

## Format du fichier MGS4.SAV

- Taille fixe : 33613 octets (au moins pour cette save, pas encore confirmé
  invariant à 100%).
- Obfusqué avec un XOR à clé répétitive d'environ 79 octets (pas un vrai
  chiffrement, pas de resigning nécessaire côté PC — voir `notes.md`).
- Zone de stats candidate : environ `0x000` à `0x460`, identifiée par diff
  entre plusieurs saves à des instants différents (beaucoup de petits
  compteurs qui bougent entre deux sessions de jeu, zone quasi entièrement à
  zéro sur une save fraîche de New Game+).

Voir [`notes.md`](notes.md) pour l'état détaillé de la rétro-ingénierie
(clé XOR recouvrée, offsets identifiés, hypothèses en cours).

## Stats visées (liste complète, à confirmer/localiser une par une)

Voir [`notes.md`](notes.md#stats-cibles).

## Interface graphique

`gui_app.py` (PySide6) : détection automatique du dossier de sauvegarde,
liste des slots à gauche (miniature, difficulté, temps de jeu, Drebin),
détail des stats à droite au clic. Bouton "Changer de dossier…" en secours
si la détection automatique échoue (bibliothèque Steam non standard, etc.),
bouton/raccourci **F5** pour actualiser la liste sans relancer l'appli.

Onglets de collection (Armes, Objets, OctoCamo, Tenues, Statuettes,
Chansons, Emblèmes) : identification individuelle de chaque entrée
(nom réel plutôt qu'un ID brut) via des tests isolés en jeu documentés au
cas par cas dans `notes.md` — armes/accessoires, FaceCamos, couleurs de
Gilet, motifs OctoCamo (hors "Camo Cadavre" et quelques motifs bonus,
jamais localisés malgré de nombreuses tentatives, voir `notes.md`). Les
armes jamais identifiées avec certitude ne sont pas affichées plutôt que
de montrer un ID brut.

```
python gui_app.py
```

Fond d'écran personnalisable : voir `themes/README.md`.

## Empaqueter en .exe autonome

```
python -m PyInstaller --noconfirm MGS4SaveStats.spec
```

Utiliser le fichier `.spec` fourni (pas une commande PyInstaller "à la main")
est important : il embarque l'icône de l'exe et le dossier `assets/`
(nécessaire à l'icône affichée dans la fenêtre au runtime).

Le résultat est dans `dist/MGS4SaveStats/` (dossier complet à copier, pas
juste l'exe — mode `--onedir` choisi plutôt que `--onefile` pour réduire
les faux positifs antivirus liés à l'auto-extraction en mémoire).

L'exe n'est pas signé (un certificat de signature valable coûte cher pour
un usage personnel) : Windows SmartScreen affichera un avertissement au
premier lancement ("Windows a protégé votre PC") — c'est normal pour un
outil indépendant non signé, il suffit de cliquer "Informations
complémentaires" → "Exécuter quand même".

## Trainer (recherche mémoire live) — V1.0

`live_trainer.py` (PySide6) : outil séparé de `gui_app.py`, pas embarqué
dans MGS4SaveStats et non lié à lui (`MGS4SaveStats.spec` ne l'embarque
pas, `gui_app.py` ne l'importe pas). Lit et **écrit** en direct la mémoire
du process `mgs4.exe` pendant une partie en cours : permet de forcer
n'importe quel champ déjà identifié (armes, objets, stats, vie/stamina/
stress/batterie Solid Eye...) sans passer par le fichier de sauvegarde, et
sert aussi d'outil de recherche pour identifier les ID encore inconnus.

Prérequis : Windows (accès mémoire process via l'API kernel32/psapi, pas
portable Linux/Mac), et MGS4 lancé avec une partie chargée — le trainer
se connecte au process en cours, inutile s'il n'est pas lancé.

```
python live_trainer.py
```

Bouton "Aide" dans l'appli pour un résumé rapide (version compatible,
avertissements, mode avancé) et le changelog détaillé.

### Fonctionnement

Utilise la chaîne de pointeurs documentée par le dépôt externe
[zexk/bbtracker](https://github.com/zexk/bbtracker) (licence MIT) pour
localiser la structure de jeu en cours (`varbuf`) directement en mémoire,
sans scan. Un contrôle de cohérence (`sanity_check`, basé sur deux champs
toujours à 0 sur toute sauvegarde connue) s'exécute avant d'autoriser la
moindre écriture — si le jeu ne répond pas comme attendu, le trainer
refuse d'écrire plutôt que de risquer de corrompre la mémoire du jeu.

### Compatibilité / mises à jour du jeu

**À ne pas confondre : deux numérotations indépendantes.** "V1.0" (titre
de cette section) est la version du trainer lui-même (voir le changelog
dans le bouton "Aide"). "1.4.1" ci-dessous est la version du jeu MGS4
avec laquelle il a été testé — rien à voir l'une avec l'autre, elles
évoluent séparément.

Les adresses mémoire utilisées dépendent de la version exacte de
`mgs4.exe` : une mise à jour Steam du jeu peut décaler toutes les
adresses. C'est déjà arrivé une fois (mise à jour du 24 septembre 2026) :
tout un bloc de données s'est décalé d'une quantité fixe, sans changer la
structure interne — corrigé via une seule constante (`MODULE_PATCH_SHIFT`
dans `live_trainer.py`, voir `notes.md` pour la méthode de diagnostic).

**Trainer calibré et testé sur la version Steam actuelle de MGS4 :
1.4.1.** Si une future mise à jour du jeu casse la détection (le trainer
reste bloqué sur "Non connecté", ou le contrôle de cohérence échoue en
boucle après reconnexion), c'est probablement la même cause : il faudra
recalibrer ce décalage.

### ⚠️ Avertissements

- **Usage solo uniquement, à tes risques.** Ce n'est pas un outil
  officiel : il lit/écrit dans la mémoire d'un autre processus, ce qu'un
  antivirus peut signaler à tort (comme pour l'exe de MGS4SaveStats,
  voir plus haut).
- Certains champs restent en confiance basse ou pas encore testés
  individuellement (documentés au cas par cas dans `notes.md`) : une
  valeur peut se comporter différemment de ce qui est indiqué.
- Le "Mode avancé" masque par défaut certains objets internes/de debug
  dont le comportement en jeu est incertain ou dangereux (ex. un objet
  dont l'équipement fait planter le jeu, confirmé à plusieurs reprises) —
  à n'activer qu'en connaissance de cause.

### Empaqueter en .exe autonome

```
python -m PyInstaller --noconfirm MGS4Trainer.spec
```

Même logique que MGS4SaveStats ci-dessus : utiliser le `.spec` fourni,
copier le dossier complet `dist/MGS4Trainer/`, exe non signé (avertissement
SmartScreen normal au premier lancement).

## Statut

Toutes les stats visées ont été localisées et vérifiées sur plusieurs
sauvegardes indépendantes (voir `notes.md` pour le détail complet des
offsets et de la méthode de corrélation).
