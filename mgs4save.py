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

# Offsets confirmés par corrélation (voir notes.md).
# name -> (offset, struct_format)
STATS = {
    "continues": (0x158, "<H"),
    "alertes": (0x16e, "<H"),
    "kills_total": (0x178, "<H"),
    "cqc": (0x180, "<H"),
    "headshots": (0x182, "<H"),
    "ko_couteau": (0x186, "<H"),
    "roulades_cote": (0x188, "<H"),
    "roulades_avant": (0x18a, "<H"),
    "pages_magazine_tournees": (0x19e, "<H"),
    "objets_donnes_milices": (0x198, "<H"),
    "combat_high": (0x18c, "<H"),
    "objets_speciaux_bitmask": (0x17a, "<H"),  # bit1=camo optique (valeur 2), bit0=bandana (hypothese non confirmee)
    "soins_utilises": (0x0ae0, "<H"),
    "drebin_actuel": (0x1c0, "<I"),
    "drebin_total_ventes": (0x1c4, "<I"),
    # Stats de temps continu, en "frames" a framerate variable (~55-62 fps
    # observe). Ne se flushent qu'au changement de zone/checkpoint, jamais
    # sur une simple sauvegarde manuelle. Pas de conversion exacte en
    # secondes possible (framerate non fixe), voir notes.md.
    "temps_accroupi_frames": (0x1a8, "<H"),
    "temps_allonge_frames": (0x1ac, "<H"),
    "temps_mur_frames": (0x1b4, "<H"),
    "temps_carton_frames": (0x1bc, "<H"),
    # 0x192 : reste non identifie (passe de 0 a 1 en meme temps que Continue/CQC
    # la premiere fois, puis n'a plus bouge alors que Continue et CQC continuaient
    # d'augmenter). Pas dans la liste de stats connue, cause inconnue.
}

# Decalages constants entre la valeur brute du fichier et celle affichee en
# jeu, quand ils existent (voir notes.md pour l'hypothese).
DISPLAY_OFFSET = {}


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
    return {
        name: struct.unpack_from(fmt, data, offset)[0] + DISPLAY_OFFSET.get(name, 0)
        for name, (offset, fmt) in STATS.items()
    }


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
