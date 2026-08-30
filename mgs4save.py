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

# Offsets confirmés par corrélation (voir notes.md). Offsets dans le fichier
# déchiffré, valeurs u32 little-endian sauf indication contraire.
# name -> (offset, struct_format)
STATS = {
    "drebin_actuel": (0x1c0, "<I"),
    "drebin_total_ventes": (0x1c4, "<I"),
    "ko_couteau": (0x186, "<I"),
    "roulades_avant": (0x18a, "<I"),
}


def decrypt(data: bytes) -> bytes:
    return bytes(b ^ XOR_KEY[i % len(XOR_KEY)] for i, b in enumerate(data))


def read_stats(path: str) -> dict:
    with open(path, "rb") as f:
        data = decrypt(f.read())
    return {
        name: struct.unpack_from(fmt, data, offset)[0]
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


if __name__ == "__main__":
    main()
