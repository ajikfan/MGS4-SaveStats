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

## Statut

En cours de reverse engineering par corrélation : on compare des saves à
values connues (affichées en jeu à l'écran de briefing) pour localiser
l'offset et l'encodage de chaque compteur.
