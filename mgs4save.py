"""Lecture (seule) des saves Metal Gear Solid 4 (portage PC Steam).

Statut : reverse engineering en cours. Voir notes.md pour la méthode et les
offsets déjà identifiés. Aucune fonction d'écriture volontairement : cet
outil ne doit jamais modifier un fichier de save.
"""

import argparse
import struct

XOR_KEY = bytes.fromhex(
    "6b6a6479654169776f47736b6c636d667539336c7773454e6637383435676877"
    "353233696630756c37506b6a30686e39656a776b73535645387477663033746536"
    "323344413834327263346f69514c"
)

# Offsets confirmés (par corrélation, puis recoupés et complétés avec la
# documentation externe zexk/bbtracker citée dans notes.md - meme cle XOR,
# donc meme build). name -> (offset, struct_format)
STATS = {
    "continues": (0x158, "<H"),
    "alertes": (0x16e, "<H"),
    "kills_total": (0x178, "<H"),
    "objets_speciaux_bitmask": (0x17a, "<H"),  # zero/non-zero uniquement, bits individuels non identifies
    "cqc": (0x180, "<H"),
    "headshots": (0x182, "<H"),
    "knife_kills": (0x184, "<H"),
    "knife_knockouts": (0x186, "<H"),
    "roulades_cote": (0x188, "<H"),
    "roulades_avant": (0x18a, "<H"),
    "combat_high": (0x18c, "<H"),
    "weapon_pickups": (0x18e, "<H"),
    "item_pickups": (0x190, "<H"),
    "holdups": (0x192, "<H"),
    "body_searches": (0x194, "<H"),
    "praises": (0x196, "<H"),
    "objets_donnes_milices": (0x198, "<H"),
    "syringe_uses": (0x19a, "<H"),
    "scanning_plug_uses": (0x19c, "<H"),
    "playboy_pages": (0x19e, "<H"),
    "emotion_magazine_pages": (0x1a0, "<H"),
    "drebin_actuel": (0x1c0, "<I"),
    "drebin_total_ventes": (0x1c4, "<I"),
    "flashbacks_vues": (0x5a34, "<H"),
    "soins_utilises": (0x0ae0, "<H"),
    # Stats de temps continu, en "frames" a framerate variable (~55-62 fps
    # observe). Ne se flushent qu'au changement de zone/checkpoint, jamais
    # sur une simple sauvegarde manuelle. Pas de conversion exacte en
    # secondes possible (framerate non fixe), voir notes.md.
    "temps_accroupi_frames": (0x1a8, "<H"),
    "temps_allonge_frames": (0x1ac, "<H"),
    "temps_mur_frames": (0x1b4, "<H"),
    "temps_boite_carton_frames": (0x1b8, "<I"),
    "temps_baril_frames": (0x1bc, "<I"),
    "temps_jeu_frames": (0x168, "<I"),  # alternative a read_playtime_seconds(), moins precis (framerate variable)
}

# Stats affichees en jeu comme une seule valeur mais stockees comme la somme
# de deux champs distincts (confirme via zexk/bbtracker, voir notes.md).
# name -> (champ1, champ2)
DERIVED_STATS = {
    "ko_couteau": ("knife_kills", "knife_knockouts"),
    "armes_objets_acquis": ("weapon_pickups", "item_pickups"),
    "seringue_scanning_plug": ("syringe_uses", "scanning_plug_uses"),
    "pages_magazine_tournees": ("playboy_pages", "emotion_magazine_pages"),
    "temps_carton_frames": ("temps_boite_carton_frames", "temps_baril_frames"),
}


def decrypt(data: bytes) -> bytes:
    return bytes(b ^ XOR_KEY[i % len(XOR_KEY)] for i, b in enumerate(data))


def read_playtime_seconds(metadata_path: str) -> int:
    """Lit le temps de jeu total depuis METADATA.SAV (non chiffre, contrairement
    a MGS4.SAV). Precision approximative : +/- 30s par rapport a l'affichage
    en jeu (le compteur en jeu continue de tourner un peu apres l'ecriture du
    fichier), voir notes.md."""
    with open(metadata_path, "rb") as f:
        data = f.read()
    return struct.unpack_from("<I", data, 0x34)[0]


def read_playthrough_number(metadata_path: str) -> int:
    """Numero de partie affiche par l'etoile dans le menu de chargement du jeu
    (1 = premiere completion, etc). Depuis METADATA.SAV, non chiffre."""
    with open(metadata_path, "rb") as f:
        data = f.read()
    return struct.unpack_from("<I", data, 0x38)[0]


# Score de difficulte -> nom affiche en jeu. Seuls 3 points connus pour
# l'instant (voir notes.md) ; les difficultes plus dures ne sont pas mappees.
DIFFICULTY_NAMES = {
    20: "LIQUID FACILE",
    30: "NAKED NORMAL",
    35: "SOLID NORMAL",
    40: "BIG BOSS DIFFICILE",
    50: "THE BOSS EXTREME",
}


def read_difficulty_score(metadata_path: str) -> int:
    """Score de difficulte brut depuis METADATA.SAV. Utiliser DIFFICULTY_NAMES
    pour le nom affiche en jeu (mapping incomplet, voir notes.md)."""
    with open(metadata_path, "rb") as f:
        data = f.read()
    return struct.unpack_from("<I", data, 0x30)[0]


# Code de stage interne -> lieu affiche en jeu (source zexk/bbtracker,
# extrait de common/stage/select/scenerio.gcx). Un nom combine signifie
# qu'un seul code de stage couvre plusieurs lieux visibles en jeu.
STAGE_NAMES = {
    "s00a00l": "Prologue : cimetière", "s00a10l": "Épilogue : cimetière",
    "s01a00l": "Infiltration Moyen-Orient", "s01a05l": "Infiltration Moyen-Orient",
    "s01a10l": "Zone rouge", "s01a20l": "Planque de la milice",
    "s01a30l": "Ruines urbaines", "s01a40l": "Palais de l'Avent",
    "s01a50l": "Crescent Meridian", "s01a55l": "Crescent Meridian",
    "s01a57l": "Millennium Park", "s01a60l": "Campement de Liquid",
    "s02a10l": "Village de Cove Valley", "s02a20l": "Centrale électrique",
    "s02a25l": "Centrale électrique", "s02a30l": "Centre de détention",
    "s02a40l": "Manoir Vista", "s02a50l": "Laboratoire de recherche",
    "s02a60l": "Sentier de montagne / Rivière", "s02a70l": "Embuscade de Vamp",
    "s02a73l": "Fuite de Stryker", "s02a75l": "Fuite de Stryker", "s02a78l": "Fuite de Stryker",
    "s02a80l": "Route des hauts bois", "s02a85l": "Entrée du marché",
    "s02a90l": "Marché", "s02a95l": "Place du marché",
    "s03a00l": "Gare d'Europe de l'Est", "s03a10l": "Centre-ville : la traque",
    "s03a15l": "Centre-ville : la traque", "s03a16l": "Centre-ville : les canaux",
    "s03a20l": "Centre-ville : la place", "s03a25l": "Centre-ville : secteur nord",
    "s03a30l": "Cour de l'église", "s03a35l": "Poursuite à moto",
    "s03a40l": "Poursuite à moto", "s03a60l": "Poursuite à moto",
    "s03a50l": "Embuscade de Raging Raven", "s03a65l": "Balise d'Echo", "s03a70l": "Balise d'Echo",
    "s03a90l": "Rivière Volta", "s04a05l": "Flashback Metal Gear Solid",
    "s04a10l": "Champ de neige / Héliport / Hangar", "s04a20l": "Stockage d'ogives nucléaires",
    "s04a30l": "Champ de neige / Tour de communication", "s04a40l": "Haut-fourneau / Fonderie",
    "s04a50l": "Base souterraine", "s04a60l": "Tunnel de ravitaillement souterrain",
    "s04a65l": "Fuite de REX", "s04a68l": "Zone portuaire",
    "s04a70l": "Zone portuaire : REX vs RAY", "s04a75l": "Arrivée à Outer Haven",
    "s05a10l": "Proue du navire", "s05a20l": "Centre de commandement / Hangar à missiles",
    "s05a30l": "Couloir micro-ondes", "s05a40l": "GW",
    "s05a45l": "Liquid Ocelot : prélude", "s05a50l": "Liquid Ocelot",
    "s05a55l": "Liquid Ocelot : aftermath",
    "s10a10l": "Briefing (Nomad)", "s10a20l": "Briefing Amérique du Sud",
    "s10a30l": "Briefing Europe de l'Est", "s10a40l": "Briefing Shadow Moses",
    "s20a00l": "USS Missouri", "s20a10l": "USS Missouri vs Outer Haven",
    "s20a20l": "Salle de Campbell", "s30a00l": "Mariage", "s30a10l": "Hôpital",
}

# progress (0x0054, u32) -> Acte (source zexk/bbtracker)
ACT_RANGES = [
    (0, 50, "Acte 1"), (51, 100, "Acte 2"), (101, 162, "Acte 3"),
    (163, 222, "Acte 4"), (223, 261, "Acte 5"), (262, 291, "Épilogue"),
]


def act_from_progress(progress: int) -> str:
    for lo, hi, name in ACT_RANGES:
        if lo <= progress <= hi:
            return name
    return f"inconnu ({progress})"


def read_progress_info(path: str) -> dict:
    """Lieu et acte actuels, depuis MGS4.SAV (source zexk/bbtracker)."""
    with open(path, "rb") as f:
        data = decrypt(f.read())
    stage_code = data[0x34:0x3b].decode("ascii", errors="replace")
    progress = struct.unpack_from("<I", data, 0x54)[0]
    return {
        "stage_code": stage_code,
        "lieu": STAGE_NAMES.get(stage_code, f"inconnu ({stage_code})"),
        "acte": act_from_progress(progress),
    }


def read_metadata_summary(metadata_path: str) -> dict:
    """Resume rapide d'un slot depuis METADATA.SAV seul (pas de dechiffrement
    necessaire) : suffisant pour un ecran de liste sans ouvrir MGS4.SAV."""
    with open(metadata_path, "rb") as f:
        data = f.read()
    difficulty_score = struct.unpack_from("<I", data, 0x30)[0]
    return {
        "playtime_secondes": struct.unpack_from("<I", data, 0x34)[0],
        "numero_partie": struct.unpack_from("<I", data, 0x38)[0],
        "difficulte_score": difficulty_score,
        "difficulte_nom": DIFFICULTY_NAMES.get(difficulty_score, f"inconnu ({difficulty_score})"),
        "drebin_actuel": struct.unpack_from("<I", data, 0x3c)[0],
        "objets_donnes_milices": struct.unpack_from("<I", data, 0x40)[0],
    }


def read_stats(path: str) -> dict:
    with open(path, "rb") as f:
        data = decrypt(f.read())
    values = {
        name: struct.unpack_from(fmt, data, offset)[0]
        for name, (offset, fmt) in STATS.items()
    }
    for name, (field_a, field_b) in DERIVED_STATS.items():
        values[name] = values[field_a] + values[field_b]
    return values


def find_value(data: bytes, value: int, region: tuple[int, int] | None = None):
    """Cherche `value` encodé en u8/u16/u32/i32 (LE et BE) dans `data`.

    Utilisé pour la corrélation manuelle : on connaît une valeur affichée en
    jeu, on cherche à quel(s) offset(s) elle apparaît dans le fichier
    déchiffré.
    """
    lo, hi = region or (0, len(data))
    hits = []
    for fmt in ("B", "<H", ">H", "<I", ">I", "<i", ">i"):
        size = struct.calcsize(fmt)
        for offset in range(lo, hi - size + 1):
            if struct.unpack_from(fmt, data, offset)[0] == value:
                hits.append((offset, fmt))
    return hits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_dump = sub.add_parser("dump", help="Déchiffre et affiche en hexa")
    p_dump.add_argument("save_path")
    p_dump.add_argument("--start", type=lambda x: int(x, 0), default=0)
    p_dump.add_argument("--length", type=lambda x: int(x, 0), default=0x100)

    p_find = sub.add_parser("find", help="Cherche une valeur connue (corrélation)")
    p_find.add_argument("save_path")
    p_find.add_argument("value", type=int)
    p_find.add_argument("--start", type=lambda x: int(x, 0), default=0)
    p_find.add_argument("--end", type=lambda x: int(x, 0), default=None)

    p_stats = sub.add_parser("stats", help="Affiche les stats déjà identifiées")
    p_stats.add_argument("save_path")
    p_stats.add_argument(
        "--metadata", help="Chemin vers METADATA.SAV (pour le temps de jeu total)"
    )

    args = parser.parse_args()

    if args.command == "dump":
        with open(args.save_path, "rb") as f:
            data = decrypt(f.read())
        chunk = data[args.start : args.start + args.length]
        for i in range(0, len(chunk), 16):
            row = chunk[i : i + 16]
            hexpart = " ".join(f"{b:02x}" for b in row)
            asciipart = "".join(chr(b) if 0x20 <= b < 0x7f else "." for b in row)
            print(f"{args.start + i:06x}  {hexpart:<47}  {asciipart}")

    elif args.command == "find":
        with open(args.save_path, "rb") as f:
            data = decrypt(f.read())
        end = args.end if args.end is not None else len(data)
        hits = find_value(data, args.value, (args.start, end))
        if not hits:
            print("Aucune correspondance.")
        for offset, fmt in hits:
            print(f"offset=0x{offset:04x} ({offset})  format={fmt}")

    elif args.command == "stats":
        if not STATS:
            print("Aucun offset confirmé pour l'instant (voir notes.md).")
            return
        for name, value in read_stats(args.save_path).items():
            print(f"{name}: {value}")
        if args.metadata:
            seconds = read_playtime_seconds(args.metadata)
            print(f"playtime_secondes (approx +/-30s): {seconds}")
            print(f"numero_partie: {read_playthrough_number(args.metadata)}")
            diff_score = read_difficulty_score(args.metadata)
            diff_name = DIFFICULTY_NAMES.get(diff_score, f"inconnu (score {diff_score})")
            print(f"difficulte: {diff_name}")


if __name__ == "__main__":
    main()
