"""Detection automatique des saves MGS4 (portage PC Steam).

Cherche l'installation Steam via le registre Windows, lit ses bibliotheques,
localise le jeu et retourne la liste des slots de sauvegarde disponibles.
Lecture seule.
"""

import os
import re
import struct
import winreg
from dataclasses import dataclass

APP_NAME = "METAL GEAR SOLID 4"
SAVE_SUBPATH = os.path.join(APP_NAME, "mgs4_savedata_win")


@dataclass
class SaveSlot:
    slot_id: str
    path: str
    imported: bool = False  # save chargee ponctuellement depuis un dossier externe (pas Steam)

    @property
    def mgs4_sav(self):
        return os.path.join(self.path, "MGS4.SAV")

    @property
    def metadata_sav(self):
        return os.path.join(self.path, "METADATA.SAV")

    @property
    def icon_png(self):
        return os.path.join(self.path, "ICON0.PNG")


def _steam_install_path():
    for hive, subkey in (
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam"),
    ):
        try:
            with winreg.OpenKey(hive, subkey) as key:
                value, _ = winreg.QueryValueEx(key, "SteamPath" if hive == winreg.HKEY_CURRENT_USER else "InstallPath")
                return value.replace("/", os.sep)
        except FileNotFoundError:
            continue
    return None


def _library_folders(steam_path):
    libraries = [steam_path]
    vdf_path = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
    try:
        with open(vdf_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return libraries
    for match in re.finditer(r'"path"\s+"([^"]+)"', content):
        path = match.group(1).replace("\\\\", "\\")
        if path not in libraries:
            libraries.append(path)
    return libraries


def find_game_install_dir():
    """Cherche le dossier d'installation du jeu dans toutes les bibliotheques Steam."""
    steam_path = _steam_install_path()
    if not steam_path:
        return None
    for library in _library_folders(steam_path):
        candidate = os.path.join(library, "steamapps", "common", APP_NAME)
        if os.path.isdir(candidate):
            return candidate
    return None


def find_savedata_root(game_install_dir=None):
    """Retourne le dossier <install>/mgs4_savedata_win, ou None si introuvable."""
    game_install_dir = game_install_dir or find_game_install_dir()
    if not game_install_dir:
        return None
    candidate = os.path.join(game_install_dir, "mgs4_savedata_win")
    return candidate if os.path.isdir(candidate) else None


def list_save_slots(savedata_root):
    """Liste les slots de sauvegarde de partie (exclut le dossier systeme 'S')."""
    slots = []
    for steamid_dir in os.listdir(savedata_root):
        mgs4_dir = os.path.join(savedata_root, steamid_dir, "mgs4")
        if not os.path.isdir(mgs4_dir):
            continue
        for slot_id in os.listdir(mgs4_dir):
            slot_path = os.path.join(mgs4_dir, slot_id)
            if slot_id.endswith("S"):
                continue  # dossier systeme (MGS4SYS.SAV), pas un slot de partie
            if os.path.isfile(os.path.join(slot_path, "MGS4.SAV")):
                slots.append(SaveSlot(slot_id=slot_id, path=slot_path))
    return slots


def find_all_slots():
    """Point d'entree principal : detection automatique complete."""
    root = find_savedata_root()
    if not root:
        return []
    return list_save_slots(root)


def find_slots_in_any_folder(folder):
    """Cherche des slots de sauvegarde n'importe ou sous `folder`, sans
    supposer la structure exacte Steam (steamid/mgs4/slot_id/). Pour
    importer ponctuellement une save recue par un tiers (cle USB, email...)
    qui peut avoir ete recompressee/reorganisee. Un dossier est un slot des
    qu'il contient a la fois MGS4.SAV et METADATA.SAV (recherche
    insensible a la casse - Windows resout les noms de fichiers reels sans
    egard a la casse de toute facon). L'ID du slot est le nom du dossier
    qui les contient."""
    slots = []
    for dirpath, _dirnames, filenames in os.walk(folder):
        names_lower = {f.lower() for f in filenames}
        if "mgs4.sav" in names_lower and "metadata.sav" in names_lower:
            slots.append(SaveSlot(slot_id=os.path.basename(dirpath), path=dirpath, imported=True))
    return slots
