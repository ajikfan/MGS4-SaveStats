"""Interface graphique MGS4 Save Stats (PySide6).

Fenetre unique : liste des slots a gauche, stats du slot selectionne a
droite (mise a jour au clic, pas de navigation par page). Lecture seule :
aucune ecriture dans les fichiers de save.
"""

import ctypes
import datetime
import html
import os
import sys
from ctypes import wintypes

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QFrame,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QDialog,
    QCheckBox,
)

import mgs4save
import save_finder

# Pas de suivi de version formel avant ce jour (pas de depot git) - liste
# reconstituee a partir du journal de travail (notes.md) pour donner un
# repere approximatif, pas un historique de commits exact.
# Limite du jeu (nombre max de slots de sauvegarde de partie par profil).
MGS4_MAX_SAVE_SLOTS = 100

APP_VERSION = "V4.4"
APP_CHANGELOG = [
    ("V4.4", "8 septembre 2026", "Mode comparaison : le choix de la sauvegarde de référence se fait désormais directement via un bouton \"Comparer\" sur chaque ligne de la liste (vert, absent sur la sauvegarde actuellement affichée), qui remplace le bouton \"Comparer avec…\" et son sélecteur dédié — recliquer sur la sauvegarde de comparaison annule la comparaison. Les batteries de la Solid Eye sont maintenant comparées comme le reste des statistiques. Correction d'un faux positif rouge/vert sur les objets à quantité variable (ex. Ration) qui ne devrait dépendre que d'être possédé ou non, pas du nombre exact. Onglet Emblèmes déplacé en dernière position, coins arrondis sur la barre d'onglets."),
    ("V4.3", "7 septembre 2026", "Nouvelle fonctionnalité : comparer sa sauvegarde actuelle à n'importe quelle autre. Sur tous les onglets, rouge = possédé ici mais pas sur la sauvegarde de comparaison, vert = l'inverse. La sauvegarde de comparaison est mise en évidence dans la liste, et le sélecteur reprend le même format (vignette, difficulté, temps de jeu...) que la liste principale."),
    ("V4.2", "7 septembre 2026", "Correction de deux identifications inversées (Lunette de fusil / Sachet à gaz somnifère) suite à des tests isolés. Le Silencieux M4 n'affiche plus le point rouge \"verrouillé chez Drebin\" à tort (il reste parfois à l'état verrouillé en données tout en étant déjà utilisable en jeu)."),
    ("V4.1", "6 septembre 2026", "Correction d'un bug d'affichage : les fenêtres de détail (chansons, emblèmes, aide...) s'affichaient avec un fond blanc au lieu du thème sombre sur certaines configurations Windows (le fond n'était appliqué explicitement qu'à la fenêtre principale, pas aux fenêtres secondaires)."),
    ("V4.0", "6 septembre 2026", "Nouvelle fonctionnalité : import ponctuel d'une sauvegarde externe (clé USB, email...) en plus des siennes, sans la copier. Onglet Armes : point rouge sur les armes/accessoires acquis mais verrouillés chez Drebin, refonte complète des catégories (renommées et recomptées via un guide d'inventaire officiel). Compteurs canoniques corrigés sur les onglets Objets, OctoCamo (fusion de l'ancienne section \"Camouflages spéciaux\", désormais 21 motifs) et Gilets. Ajout des récompenses d'emblèmes dans leur popup de détail. Nouvelles conditions de déblocage pour plusieurs chansons, et divers ajustements de texte."),
    ("V3.2", "6 septembre 2026", "Onglet Emblèmes : distinction entre un emblème obtenu sur la partie en cours et un obtenu sur une partie précédente (nouvelle nuance de couleur), message dédié quand la partie est déjà terminée plutôt que le texte générique \"condition dépassée\", et accord au pluriel quand plusieurs conditions sont dépassées à la fois."),
    ("V3.1", "5 septembre 2026", "Dizaines de nouvelles identifications d'armes et d'objets via tests isolés sur une nouvelle partie, avec correction de plusieurs erreurs héritées d'anciennes déductions peu fiables. Renommage \"Camouflage furtif (Stealth Camo)\" en \"Camouflage optique\", noms de grenades mis au singulier. Onglet Armes : tuiles à largeur adaptative par groupe pour les noms très longs, regroupement des couleurs de grenade fumigène sur leur propre ligne."),
    ("V3.0", "5 septembre 2026", "Onglet Emblèmes : refonte complète des couleurs (doré+bordure = obtenu sur une partie précédente, gris+bordure = obtenable en terminant maintenant, gris = encore possible, noir = impossible), popup de condition affichant la valeur actuelle à côté du seuil (ex. \"Moins de 75 alertes (18/75)\", difficulté affichée par son nom plutôt que son score brut) et conditions déjà dépassées barrées. Correction d'un bug d'affichage majeur (un style sheet posé directement sur un QScrollArea bloquait l'héritage du style pour tout ce qu'il contenait, empêchant les couleurs de s'afficher) et suppression du fond d'écran personnalisé (non utilisé). Onglet Armes : couleurs \"obtenu/pas obtenu\" séparées de celles des Emblèmes, couteau reclassé dans \"Autres\" (fin de la catégorie \"Corps à corps\" à une seule entrée), tuiles à taille fixe et centrées par groupe au lieu de s'étirer sur toute la largeur, largeur adaptative par groupe pour ne plus couper les noms longs (ex. \"Grenade à particules métalliques\")."),
    ("V2.5", "5 septembre 2026", "Correction d'un plantage au clic sur une sauvegarde supprimée entre-temps (message propre + liste actualisée à la place). Onglets Objets/OctoCamo/Tenues/Statuettes/Chansons : suppression des gros espaces vides entre le titre de section et la liste, et correction du texte \"Doré = obtenu\" en \"Blanc = obtenu\" (couleur réellement affichée). Nouvelles identifications : Bandana, Camouflage furtif (Stealth Camo) et Prise Scanner (via le fichier Cheat Engine du jeu et des tests en partie fraîche)."),
    ("V2.4", "3 septembre 2026", "Onglet Armes : sections \"Armes\" et \"Accessoires\" séparées avec compteurs sur le total canonique du jeu (70/20). Liste des sauvegardes : ajout du lieu, de l'acte et de la date, notation \"★ X\" pour le New Game+. Suppression : possibilité de supprimer toutes les sauvegardes d'une même partie d'un coup (détection fiable via compte Steam + compteurs cumulés du jeu, jamais activée par défaut)."),
    ("V2.3", "3 septembre 2026", "Dizaines de nouvelles identifications d'armes et d'objets (AK-102, Masterkey, MP7, PSS, P90, Vz. 83, Chargeur, Baril, plusieurs FaceCamo...) suite à des tests en jeu, avec correction de plusieurs erreurs héritées d'anciennes déductions peu fiables."),
    ("V2.2", "2 septembre 2026", "Affichage des noms trop longs sur 2 lignes (armes, chansons...), réorganisation de l'onglet Armes (Accessoires en fin de liste), ajout de cette aide."),
    ("V2.1", "2 septembre 2026", "Nouvelles identifications après la fin du jeu (armes bonus, poupées, statuette Screaming Mantis, couleurs de Gilet) et corrections (Ration, Nouilles, Compresse, iPod)."),
    ("V2.0", "2 septembre 2026", "Fusion des Camouflages/Facecamos en un onglet \"OctoCamo\", renommage \"Objets spéciaux\" en \"Objets\", affichage des objets/armes même non identifiés."),
    ("V1.5", "1er septembre 2026", "Tri des sauvegardes par date, bouton Actualiser, suppression d'une sauvegarde (vers la Corbeille Windows) avec confirmation."),
    ("V1.4", "1er septembre 2026", "Corrections d'identification (facecamos, chansons, armes) et ajout de la carte \"Solid Eye\" (batteries)."),
    ("V1.3", "31 août 2026", "Nombreuses corrections d'identification (armes, objets de soin, gilets) suite à des tests en jeu."),
    ("V1.2", "31 août 2026", "Ajout des onglets Camouflages, Tenues, Statuettes et Chansons."),
    ("V1.1", "30 août 2026", "Ajout de l'onglet Armes (premières identifications)."),
    ("V1.0", "30 août 2026", "Première version : détection automatique des sauvegardes Steam, stats de base (progression, difficulté, temps de jeu, Drebin), émblèmes."),
]

APP_HELP_TEXT = (
    "MGS4 Save Stats lit tes sauvegardes de Metal Gear Solid 4 (version Steam) "
    "pour afficher ta progression : armes, objets, camouflages, tenues, "
    "statuettes et chansons débloquées.\n\n"
    "L'application est en LECTURE SEULE : elle ne modifie jamais tes fichiers "
    "de sauvegarde.\n\n"
    "Le dossier de sauvegardes est détecté automatiquement via Steam, ou tu "
    "peux le choisir manuellement (\"Changer de dossier…\"). Sélectionne une "
    "sauvegarde dans la liste à gauche pour voir son détail dans les onglets "
    "à droite.\n\n"
    "Quelques armes ne sont pas encore identifiées avec certitude (affichées "
    "\"Arme #NN\") : c'est un travail en cours, basé sur des tests en jeu.\n\n"
    "Dans certains onglets (Objets, OctoCamo, Statuettes, Chansons), certaines "
    "entrées sont cliquables et affichent plus de détails (condition "
    "d'obtention, effet en jeu...)."
)

def _bundled_path(*parts):
    """Fichier embarque dans l'exe (PyInstaller --add-data), ou a cote du
    script en mode developpement."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def _external_path(*parts):
    """Fichier a cote de l'exe distribue (pas embarque) : permet a
    l'utilisateur de le remplacer sans reconstruire l'exe."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *parts)


class _SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", ctypes.c_uint16),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", ctypes.c_void_p),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]


_FO_DELETE = 3
_FOF_ALLOWUNDO = 0x40
_FOF_NOCONFIRMATION = 0x10


def send_folder_to_recycle_bin(path: str) -> bool:
    """Envoie un dossier a la Corbeille Windows (recuperable), via l'API
    Shell native - pas de suppression definitive, pas de dependance
    externe. Retourne True si l'operation a reussi."""
    op = _SHFILEOPSTRUCTW()
    op.hwnd = None
    op.wFunc = _FO_DELETE
    op.pFrom = os.path.abspath(path) + "\0"
    op.pTo = None
    op.fFlags = _FOF_ALLOWUNDO | _FOF_NOCONFIRMATION
    result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    return result == 0 and not op.fAnyOperationsAborted


APP_ICON = _bundled_path("assets", "app_icon.ico")

STAT_GROUPS = [
    (
        "Combat",
        [
            ("kills_total", "Kills"),
            ("headshots", "Headshots"),
            ("ko_couteau", "Kill/KO au couteau"),
            ("cqc", "CQC"),
            ("alertes", "Alertes"),
            ("continues", "Continues"),
            ("combat_high", "Poussées d'adrénaline"),
        ],
    ),
    (
        "Mouvement",
        [
            ("roulades_avant", "Roulades en avant"),
            ("roulades_cote", "Roulades de côté"),
        ],
    ),
    (
        "Divers",
        [
            ("soins_utilises", "Objets de soin utilisés"),
            ("objets_donnes_milices", "Objets donnés aux milices"),
            ("pages_magazine_tournees", "Pages de magazine tournées"),
            ("objets_speciaux_bitmask", "Objets spéciaux utilisé"),
            ("flashbacks_vues", "Flashbacks vus"),
            ("posters_vus", "Posters vus"),
            ("seringue_scanning_plug", "Seringue / Scanning Plug"),
            ("holdups", "Hold-ups"),
            ("body_searches", "Fouilles corporelles"),
            ("praises", "Compliments reçus"),
        ],
    ),
    (
        "Économie",
        [
            ("drebin_actuel", "Drebin Points (actuel)"),
            ("drebin_total_ventes", "Drebin Points (total ventes)"),
        ],
    ),
]

# Carte "Temps" a part : melange une valeur de METADATA.SAV (playtime) et
# des valeurs de MGS4.SAV (frames), assemblee separement dans show_slot().
TIME_FIELDS = [
    ("temps_accroupi_frames", "Temps accroupi"),
    ("temps_allonge_frames", "Temps allongé"),
    ("temps_mur_frames", "Temps contre un mur"),
    ("temps_carton_frames", "Temps carton/baril"),
]

FRAME_FIELDS = {
    "temps_accroupi_frames",
    "temps_allonge_frames",
    "temps_mur_frames",
    "temps_carton_frames",
}

# Ratio frames/seconde observe (framerate variable, voir notes.md) : ~60 pour
# accroupi, 55-62 pour les autres. 60 est une bonne approximation partout.
FRAMES_PER_SECOND = 60


def seconds_to_hms(seconds) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def format_partie_suffix(numero_partie) -> str:
    """Partie 0 = premiere partie, jamais de New Game+ : rien a afficher.
    Partie N>0 = Nieme New Game+, affiche comme le fait le jeu lui-meme
    (etoile + chiffre) plutot que "Partie n°N"."""
    return f"  —  ★ {numero_partie}" if numero_partie else ""


def format_lieu_acte(lieu: str, acte: str) -> str:
    """Certains lieux (ex. "Épilogue : cimetière") reprennent deja le nom de
    l'acte - evite d'afficher deux fois le meme mot (ex. "... — Épilogue")."""
    return lieu if acte.lower() in lieu.lower() else f"{lieu} — {acte}"


def frames_to_hms_approx(frames) -> str:
    # Pas de symbole "environ" affiche a la demande de l'utilisateur, mais la
    # valeur reste approximative (framerate variable, voir notes.md).
    return seconds_to_hms(frames / FRAMES_PER_SECOND)


DREBIN_FIELDS = {"drebin_actuel", "drebin_total_ventes"}


def format_stat_value(key: str, value) -> str:
    if key in FRAME_FIELDS:
        return frames_to_hms_approx(value)
    if key == "objets_speciaux_bitmask":
        return "Oui" if value else "Non"
    if key in DREBIN_FIELDS:
        return f"{value:,}".replace(",", " ")
    return str(value)


DARK_QSS = """
QMainWindow, QWidget#root, QDialog { background-color: #0b0b0c; }
QLabel { color: #d8d8d8; }
QLabel#title { color: #f0f0f0; font-size: 20px; font-weight: 600; letter-spacing: 1px; }
QLabel#subtitle { color: #c9a24b; font-size: 15px; font-weight: 600; }
QLabel#groupTitle { color: #c9a24b; font-size: 13px; font-weight: 700; letter-spacing: 2px; }
QLabel#statLabel { color: #9a9a9a; font-size: 12px; }
QLabel#statValue { color: #f0f0f0; font-size: 14px; font-weight: 600; }
QPushButton#statValueLink { background: transparent; color: #d8c39a; font-size: 14px; font-weight: 600; border: none; padding: 0px; }
QPushButton#statValueLink:hover { color: #c9a24b; text-decoration: underline; }
QLabel#placeholder { color: #6a6a6a; font-size: 14px; }
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QListWidget { background: transparent; border: none; }
QListWidget::item { background: rgba(20,20,22,190); border: 1px solid rgba(255,255,255,30); margin: 4px 8px; padding: 0px; }
QListWidget::item:selected { border: 1px solid #c9a24b; background: rgba(40,35,20,200); }
QWidget#slotRow { background: transparent; }
QWidget#slotRowCompareTarget { background: rgba(90,180,110,30); border: 2px solid #6fcf87; border-radius: 4px; }
QPushButton#deleteSlotLink { background: rgba(10,10,10,235); color: #d08080; border: 1px solid rgba(255,255,255,25); border-radius: 3px; font-size: 11px; padding: 3px 8px; }
QPushButton#deleteSlotLink:hover { color: #ff6b6b; background: rgba(30,10,10,235); }
QPushButton#compareSlotLink { background: rgba(10,10,10,235); color: #7fd99a; border: 1px solid rgba(255,255,255,25); border-radius: 3px; font-size: 11px; padding: 3px 8px; }
QPushButton#compareSlotLink:hover { color: #6fcf87; background: rgba(10,30,15,235); }
QPushButton#dangerButton { background: rgba(140,30,30,180); color: #ffffff; border: 1px solid #c94b4b; font-weight: 700; padding: 6px 16px; }
QPushButton#dangerButton:hover { background: rgba(180,40,40,220); }
QPushButton { background: rgba(255,255,255,20); color: #e8e8e8; border: 1px solid rgba(255,255,255,60); border-radius: 6px; padding: 6px 14px; }
QPushButton:hover { background: rgba(255,255,255,40); }
QFrame#card { background: rgba(15,15,17,170); border: 1px solid rgba(255,255,255,25); }
QSplitter::handle { background: rgba(255,255,255,20); }
QTabWidget::pane { border: 1px solid rgba(255,255,255,25); background: transparent; }
QTabBar::tab { background: rgba(255,255,255,15); color: #b0b0b0; padding: 8px 18px; border: 1px solid rgba(255,255,255,25); border-top-left-radius: 6px; border-top-right-radius: 6px; }
QTabBar::tab:selected { background: rgba(201,162,75,40); color: #f0f0f0; border-color: #c9a24b; }
QPushButton#collectionOwned { background: rgba(255,255,255,25); color: #ffffff; border: 1px solid rgba(255,255,255,60); font-weight: 700; }
QPushButton#collectionOwned:hover { background: rgba(255,255,255,40); }
QPushButton#collectionLocked { background: rgba(255,255,255,10); color: #808080; border: 1px solid rgba(255,255,255,30); font-weight: 500; }
QPushButton#collectionLocked:hover { background: rgba(255,255,255,20); }
QPushButton#collectionOnlyCompare { background: rgba(90,180,110,80); color: #ffffff; border: 2px solid #6fcf87; font-weight: 700; }
QPushButton#collectionOnlyCompare:hover { background: rgba(90,180,110,110); }
QPushButton#collectionOnlyHere { background: rgba(200,80,80,80); color: #ffffff; border: 2px solid #e08080; font-weight: 700; }
QPushButton#collectionOnlyHere:hover { background: rgba(200,80,80,110); }
QPushButton#emblemUnlocked { background: rgba(201,162,75,150); color: #ffffff; border: 2px solid #f0cd7a; font-weight: 700; }
QPushButton#emblemUnlocked:hover { background: rgba(201,162,75,180); }
QPushButton#emblemUnlockedPrevious { background: rgba(201,162,75,150); color: #ffffff; border: 2px solid transparent; font-weight: 700; }
QPushButton#emblemUnlockedPrevious:hover { background: rgba(201,162,75,180); }
QPushButton#emblemProjected { background: rgba(255,255,255,45); color: #f0f0f0; border: 2px solid #d8d8d8; font-weight: 600; }
QPushButton#emblemProjected:hover { background: rgba(255,255,255,65); }
QPushButton#emblemLocked { background: rgba(255,255,255,20); color: #b0b0b0; border: 2px solid transparent; font-weight: 600; }
QPushButton#emblemLocked:hover { background: rgba(255,255,255,35); }
QPushButton#emblemImpossible { background: rgba(0,0,0,90); color: #4a4a4a; border: 2px solid transparent; font-weight: 500; font-style: italic; }
QPushButton#emblemImpossible:hover { background: rgba(0,0,0,110); }
"""


class SlotRowWidget(QWidget):
    """Ligne d'une sauvegarde dans la liste : icone (taille d'origine) +
    texte. Le lien "Supprimer" flotte en superposition (pas dans la mise en
    page) au-dessus du coin bas-droit, pour ne jamais decaler le contenu
    quand il apparait/disparait au survol."""

    def __init__(self, slot, label_text, on_delete=None, is_compare_target=False, on_compare=None, is_current=False):
        super().__init__()
        self.label_text = label_text
        self.setObjectName("slotRowCompareTarget" if is_compare_target else "slotRow")
        # Necessaire pour qu'un QWidget "nu" (pas de peinture personnalisee)
        # respecte les regles QSS background/border - sans ça, la bordure
        # verte de "slotRowCompareTarget" est definie mais jamais dessinee.
        self.setAttribute(Qt.WA_StyledBackground, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(10)

        if os.path.isfile(slot.icon_png):
            icon_label = QLabel()
            pixmap = QPixmap(slot.icon_png).scaled(
                140, 79, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            icon_label.setPixmap(pixmap)
            layout.addWidget(icon_label)

        text_label = QLabel(label_text)
        text_label.setObjectName("statLabel")
        text_label.setWordWrap(True)
        # Hauteur minimale forcee (6 lignes) : le sizeHint() automatique
        # d'un QLabel avec word-wrap est peu fiable tant que le widget n'a
        # pas encore de largeur finale assignee par le layout parent (au
        # moment ou QListWidgetItem.setSizeHint() est appele, juste apres
        # la construction) - ça sous-estimait la hauteur et coupait la
        # derniere ligne (la date). 6 lignes couvre le pire cas (le nom du
        # lieu peut parfois passer sur 2 lignes).
        line_height = text_label.fontMetrics().lineSpacing()
        text_label.setMinimumHeight(6 * line_height)
        layout.addWidget(text_label, 1)

        # Parent = self mais PAS ajoutes au layout : flottent en
        # superposition, positionnes a la main (voir _position_overlay_btns),
        # sans reserver d'espace ni decaler le reste quand ils apparaissent/
        # disparaissent. on_delete/on_compare=None (ex. dans le picker du
        # mode comparaison) : pas de bouton correspondant, juste l'icone +
        # le texte.
        self.delete_btn = None
        if on_delete is not None:
            self.delete_btn = QPushButton("Supprimer", self)
            self.delete_btn.setObjectName("deleteSlotLink")
            self.delete_btn.setFlat(True)
            self.delete_btn.setCursor(Qt.PointingHandCursor)
            self.delete_btn.setToolTip("Envoyer cette sauvegarde à la Corbeille")
            self.delete_btn.setVisible(False)
            self.delete_btn.adjustSize()
            self.delete_btn.clicked.connect(lambda: on_delete(slot))

        # Pas de bouton Comparer sur la ligne actuellement affichee (is_current) :
        # se comparer a soi-meme n'a pas de sens.
        self.compare_btn = None
        if on_compare is not None and not is_current:
            self.compare_btn = QPushButton(
                "Quitter la comparaison" if is_compare_target else "Comparer", self
            )
            self.compare_btn.setObjectName("compareSlotLink")
            self.compare_btn.setFlat(True)
            self.compare_btn.setCursor(Qt.PointingHandCursor)
            self.compare_btn.setToolTip(
                "Arrêter de comparer avec cette sauvegarde" if is_compare_target
                else "Comparer la sauvegarde sélectionnée à celle-ci directement"
            )
            self.compare_btn.setVisible(False)
            self.compare_btn.adjustSize()
            self.compare_btn.clicked.connect(lambda: on_compare(slot))

    def _position_overlay_btns(self):
        margin = 6
        x = self.width() - margin
        y = self.height() - margin
        if self.delete_btn is not None:
            self.delete_btn.move(x - self.delete_btn.width(), y - self.delete_btn.height())
            self.delete_btn.raise_()
            x -= self.delete_btn.width() + margin
        if self.compare_btn is not None:
            self.compare_btn.move(x - self.compare_btn.width(), y - self.compare_btn.height())
            self.compare_btn.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_overlay_btns()

    def enterEvent(self, event):
        self._position_overlay_btns()
        if self.delete_btn is not None:
            self.delete_btn.setVisible(True)
        if self.compare_btn is not None:
            self.compare_btn.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.delete_btn is not None:
            self.delete_btn.setVisible(False)
        if self.compare_btn is not None:
            self.compare_btn.setVisible(False)
        super().leaveEvent(event)


class SlotListPanel(QWidget):
    def __init__(self, on_selection_changed, on_change_folder, on_refresh, on_delete_slot, on_import_folder, on_compare_row):
        super().__init__()
        self._on_delete_slot = on_delete_slot
        self._on_compare_row = on_compare_row
        self._compare_target_path = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 10, 20)

        header_row = QHBoxLayout()
        title = QLabel("SAUVEGARDES")
        title.setObjectName("title")
        header_row.addWidget(title)
        self.count_label = QLabel("")
        self.count_label.setObjectName("placeholder")
        header_row.addWidget(self.count_label)
        header_row.addStretch()
        help_btn = QPushButton("❓ Aide")
        help_btn.clicked.connect(self._show_help)
        header_row.addWidget(help_btn)
        refresh_btn = QPushButton("⟳ Actualiser")
        refresh_btn.clicked.connect(on_refresh)
        header_row.addWidget(refresh_btn)
        layout.addLayout(header_row)

        self.list_widget = QListWidget()
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.currentItemChanged.connect(self._on_current_item_changed)
        self._on_selection_changed = on_selection_changed
        self._selected_path = None
        layout.addWidget(self.list_widget)

        change_btn = QPushButton("Changer de dossier…")
        change_btn.clicked.connect(on_change_folder)
        layout.addWidget(change_btn)

        import_btn = QPushButton("Importer une sauvegarde…")
        import_btn.setToolTip(
            "Charger ponctuellement une sauvegarde reçue d'un tiers (clé USB, "
            "email...) en plus des tiennes, sans la copier dans ton dossier Steam."
        )
        import_btn.clicked.connect(on_import_folder)
        layout.addWidget(import_btn)

    def _on_current_item_changed(self, current, _prev):
        if not current:
            return
        slot = current.data(Qt.UserRole)
        self._selected_path = slot.path
        self._restyle_rows()  # bouton Comparer absent/present a mettre a jour sur l'ancienne/nouvelle ligne selectionnee
        self._on_selection_changed(slot)

    def set_compare_active(self, active, compare_label="", compare_path=None):
        self._compare_target_path = compare_path if active else None
        self._restyle_rows()

    def _restyle_rows(self):
        """Reconstruit juste le style des lignes deja affichees (contour vert
        sur la cible de comparaison), sans redemander les slots ni toucher a
        la selection courante - contrairement a set_slots()."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            slot = item.data(Qt.UserRole)
            old_row = self.list_widget.itemWidget(item)
            if old_row is None:
                continue
            new_row = SlotRowWidget(
                slot, old_row.label_text, self._on_delete_slot,
                is_compare_target=(slot.path == self._compare_target_path),
                on_compare=self._on_compare_row,
                is_current=(slot.path == self._selected_path),
            )
            self.list_widget.setItemWidget(item, new_row)

    def _show_help(self):
        HelpDialog(self).exec()

    def set_slots(self, slots_with_summary):
        """slots_with_summary : trie par l'appelant (plus recent en premier).
        Conserve la selection courante si le meme slot est toujours present
        (ex. apres bascule du mode comparaison), sinon retombe sur la
        premiere ligne (ex. veritable rafraichissement/nouvelle sauvegarde)."""
        count = len(slots_with_summary)
        self.count_label.setText(
            f"({count}/{MGS4_MAX_SAVE_SLOTS} sauvegarde{'s' if count != 1 else ''})"
        )
        self.list_widget.clear()
        restore_row = None
        for i, (slot, summary) in enumerate(slots_with_summary):
            if slot.path == self._selected_path:
                restore_row = i
            imported_tag = "📁 IMPORTÉE\n" if slot.imported else ""
            label = (
                f"{imported_tag}"
                f"{summary['difficulte_nom']}{format_partie_suffix(summary['numero_partie'])}\n"
                f"{format_lieu_acte(summary['lieu'], summary['acte'])}\n"
                f"Temps de jeu : {seconds_to_hms(summary['playtime_secondes'])}    "
                f"Drebin : {format_stat_value('drebin_actuel', summary['drebin_actuel'])}\n"
                f"{summary['date_modif'].strftime('%d/%m/%Y %H:%M')}"
            )
            item = QListWidgetItem()
            item.setData(Qt.UserRole, slot)
            row = SlotRowWidget(
                slot, label, self._on_delete_slot,
                is_compare_target=(slot.path == self._compare_target_path),
                on_compare=self._on_compare_row,
                is_current=(slot.path == self._selected_path),
            )
            item.setSizeHint(row.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, row)
        if self.list_widget.count():
            self.list_widget.setCurrentRow(restore_row if restore_row is not None else 0)


class StatsPanel(QWidget):
    def __init__(self):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 20, 20, 20)

        self.title = QLabel("")
        self.title.setObjectName("subtitle")
        outer.addWidget(self.title)

        self.compare_hint = QLabel(
            "Valeur de la sauvegarde actuelle à gauche, de la sauvegarde comparée à droite."
        )
        self.compare_hint.setObjectName("placeholder")
        self.compare_hint.setWordWrap(True)
        self.compare_hint.hide()
        outer.addWidget(self.compare_hint)

        self.placeholder = QLabel("Sélectionne une sauvegarde dans la liste à gauche.")
        self.placeholder.setObjectName("placeholder")
        outer.addWidget(self.placeholder)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.grid = QGridLayout(content)
        self.grid.setSpacing(16)
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def show_slot(self, slot, compare_slot=None):
        self.placeholder.hide()
        self.compare_hint.setVisible(compare_slot is not None)
        while self.grid.count():
            child = self.grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        stats = mgs4save.read_stats(slot.mgs4_sav)
        meta = mgs4save.read_metadata_summary(slot.metadata_sav)
        progress = mgs4save.read_progress_info(slot.mgs4_sav)
        title_text = (
            f"{meta['difficulte_nom']}{format_partie_suffix(meta['numero_partie'])}\n"
            f"{format_lieu_acte(progress['lieu'], progress['acte'])}"
        )

        stats_before = meta_before = None
        if compare_slot is not None:
            stats_before = mgs4save.read_stats(compare_slot.mgs4_sav)
            meta_before = mgs4save.read_metadata_summary(compare_slot.metadata_sav)
            title_text += "\nComparée à : " + format_lieu_acte(
                mgs4save.read_progress_info(compare_slot.mgs4_sav)["lieu"],
                mgs4save.read_progress_info(compare_slot.mgs4_sav)["acte"],
            )
        self.title.setText(title_text)

        def row_values(key, value):
            if stats_before is None:
                return (format_stat_value(key, value),)
            return (format_stat_value(key, value), format_stat_value(key, stats_before.get(key, 0)))

        compare_labels = ("Actuelle", "Comparée") if compare_slot is not None else None

        cards = [
            self._build_card(group_name, [
                (label, *row_values(key, stats.get(key, 0))) for key, label in fields
            ], compare_labels)
            for group_name, fields in STAT_GROUPS
        ]

        if meta_before is None:
            time_playtime = (seconds_to_hms(meta["playtime_secondes"]),)
        else:
            time_playtime = (seconds_to_hms(meta["playtime_secondes"]), seconds_to_hms(meta_before["playtime_secondes"]))
        time_rows = [("Temps de jeu total", *time_playtime)]
        time_rows += [(label, *row_values(key, stats.get(key, 0))) for key, label in TIME_FIELDS]
        cards.append(self._build_card("Temps", time_rows, compare_labels))

        battery_count = mgs4save.read_battery_count(slot.mgs4_sav)
        battery_before = mgs4save.read_battery_count(compare_slot.mgs4_sav) if compare_slot is not None else None
        cards.append(self._build_battery_card(battery_count, battery_before, compare_labels))

        columns = 2
        for i, card in enumerate(cards):
            self.grid.addWidget(card, i // columns, i % columns)

    @staticmethod
    def _build_card(title, rows, compare_labels=None):
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        group_title = QLabel(title.upper())
        group_title.setObjectName("groupTitle")
        card_layout.addWidget(group_title)
        if compare_labels:
            header = QHBoxLayout()
            header.addStretch()
            for col_label in compare_labels:
                col = QLabel(col_label)
                col.setObjectName("statLabel")
                col.setMinimumWidth(80)
                col.setAlignment(Qt.AlignRight)
                header.addWidget(col)
            card_layout.addLayout(header)
        for label, *values in rows:
            row = QHBoxLayout()
            name_label = QLabel(label)
            name_label.setObjectName("statLabel")
            row.addWidget(name_label)
            row.addStretch()
            for value in values:
                value_label = QLabel(str(value))
                value_label.setObjectName("statValue")
                value_label.setMinimumWidth(80)
                value_label.setAlignment(Qt.AlignRight)
                row.addWidget(value_label)
            card_layout.addLayout(row)
        # Sans ceci, une carte plus courte que sa voisine de la meme ligne
        # de grille est etiree pour remplir la hauteur de ligne, ce qui
        # espace ses lignes de stats au lieu de les garder compactes en
        # haut (meme cause que le fix CollectionPanel/AlignTop).
        card_layout.addStretch()
        return card

    def _build_battery_card(self, battery_count, battery_before=None, compare_labels=None):
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        group_title = QLabel("SOLID EYE")
        group_title.setObjectName("groupTitle")
        card_layout.addWidget(group_title)

        if compare_labels:
            header = QHBoxLayout()
            header.addStretch()
            for col_label in compare_labels:
                col = QLabel(col_label)
                col.setObjectName("statLabel")
                col.setMinimumWidth(80)
                col.setAlignment(Qt.AlignRight)
                header.addWidget(col)
            card_layout.addLayout(header)

        row = QHBoxLayout()
        name_label = QLabel("Batteries")
        name_label.setObjectName("statLabel")
        row.addWidget(name_label)
        row.addStretch()
        value_btn = self._battery_button(battery_count)
        row.addWidget(value_btn)
        if battery_before is not None:
            row.addWidget(self._battery_button(battery_before))
        card_layout.addLayout(row)
        card_layout.addStretch()
        return card

    def _battery_button(self, battery_count):
        value_btn = QPushButton(f"{battery_count} / {mgs4save.BATTERY_MAX}")
        value_btn.setObjectName("statValueLink")
        value_btn.setFlat(True)
        value_btn.setCursor(Qt.PointingHandCursor)
        value_btn.setMinimumWidth(80)
        value_btn.clicked.connect(lambda: self._show_battery_dialog(battery_count))
        return value_btn

    def _show_battery_dialog(self, battery_count):
        InfoDialog(
            "Solid Eye — Batteries",
            f"{battery_count} / {mgs4save.BATTERY_MAX}",
            mgs4save.BATTERY_CONDITION,
            self,
        ).exec()


class ConfirmDeleteDialog(QDialog):
    """Confirmation de suppression, dans le theme de l'appli (au lieu d'une
    QMessageBox generique avec des boutons anglais). Si d'autres slots
    partagent exactement la meme (difficulte, numero de partie) - identite
    fiable fournie par le jeu lui-meme, pas une heuristique - propose une
    case a cocher pour tout supprimer d'un coup."""

    def __init__(self, slot, summary, sibling_count=0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Supprimer cette sauvegarde ?")
        layout = QVBoxLayout(self)

        intro = QLabel("Vous êtes sur le point de supprimer cette sauvegarde :")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        detail = QLabel(
            f"{summary['difficulte_nom']}{format_partie_suffix(summary['numero_partie'])}\n"
            f"Temps de jeu : {seconds_to_hms(summary['playtime_secondes'])}\n"
            f"Drebin : {format_stat_value('drebin_actuel', summary['drebin_actuel'])}"
        )
        detail.setObjectName("statValue")
        detail.setWordWrap(True)
        card_layout.addWidget(detail)
        path_label = QLabel(slot.path)
        path_label.setObjectName("statLabel")
        path_label.setWordWrap(True)
        card_layout.addWidget(path_label)
        layout.addWidget(card)

        confirm = QLabel("Êtes-vous sûr ?")
        confirm.setObjectName("subtitle")
        layout.addWidget(confirm)

        note = QLabel("Vous pourrez la récupérer depuis la Corbeille Windows en cas d'erreur.")
        note.setObjectName("placeholder")
        note.setWordWrap(True)
        layout.addWidget(note)

        self.group_checkbox = None
        if sibling_count > 0:
            total = sibling_count + 1
            self.group_checkbox = QCheckBox(
                f"Supprimer aussi les {sibling_count} autres sauvegardes de cette même "
                f"partie ({total} au total, même difficulté et numéro de partie)"
            )
            layout.addWidget(self.group_checkbox)

        buttons = QHBoxLayout()
        buttons.addStretch()
        no_btn = QPushButton("Non")
        no_btn.clicked.connect(self.reject)
        buttons.addWidget(no_btn)
        yes_btn = QPushButton("Oui")
        yes_btn.setObjectName("dangerButton")
        yes_btn.clicked.connect(self.accept)
        buttons.addWidget(yes_btn)
        layout.addLayout(buttons)

        self.setMinimumWidth(420)

    def delete_group(self):
        return self.group_checkbox is not None and self.group_checkbox.isChecked()


class EmblemDialog(QDialog):
    def __init__(self, emblem, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Emblème {emblem['id']} — {emblem['name']}")
        layout = QVBoxLayout(self)

        if emblem.get("obtained_previous_run"):
            status_text = "Obtenu sur une précédente partie"
        elif emblem.get("obtained"):
            status_text = "Obtenu sur cette partie"
        elif emblem.get("projected"):
            status_text = "Pas encore obtenu — serait débloqué en terminant cette partie maintenant"
        elif emblem.get("impossible"):
            if emblem.get("completed"):
                status_text = "Impossible pour cette partie — partie déjà terminée"
            else:
                exceeded_count = sum(1 for line in emblem["requirement"] if line["exceeded"])
                if exceeded_count > 1:
                    status_text = f"Impossible pour cette partie — {exceeded_count} conditions ont déjà été dépassées"
                else:
                    status_text = "Impossible pour cette partie — une condition a déjà été dépassée"
        else:
            status_text = "Pas encore obtenu — encore possible avec plus de progression"
        status = QLabel(status_text)
        status.setObjectName("subtitle" if emblem.get("obtained") or emblem.get("projected") else "placeholder")
        status.setWordWrap(True)
        layout.addWidget(status)

        req_title = QLabel("CONDITION")
        req_title.setObjectName("groupTitle")
        layout.addWidget(req_title)

        req_lines = []
        for line in emblem["requirement"]:
            text = html.escape(line["text"])
            if line["exceeded"]:
                text = f'<span style="color:#6a6a6a; text-decoration: line-through;">{text}</span>'
            req_lines.append(f"• {text}")
        req = QLabel("<br>".join(req_lines))
        req.setWordWrap(True)
        req.setTextFormat(Qt.RichText)
        layout.addWidget(req)

        if emblem.get("reward"):
            reward_title = QLabel("RÉCOMPENSE")
            reward_title.setObjectName("groupTitle")
            layout.addWidget(reward_title)
            reward = QLabel(emblem["reward"])
            reward.setWordWrap(True)
            layout.addWidget(reward)

        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setMinimumWidth(360)


class EmblemsPanel(QWidget):
    COLUMNS = 6

    def __init__(self):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)

        self.header = QLabel("EMBLÈMES")
        self.header.setObjectName("title")
        outer.addWidget(self.header)

        self._base_subtitle = (
            "Doré + bordure = obtenu sur cette partie. Doré sans bordure = obtenu sur une partie précédente.\n"
            "Gris + bordure = serait obtenu en terminant maintenant. Gris sans bordure = encore possible. "
            "Noir sans bordure = impossible pour cette partie. Clique pour la condition et la récompense.\n"
            "Obtenir les 40 emblèmes débloque en plus la chanson iPod \"Snake Eater\"."
        )
        self.subtitle = QLabel(self._base_subtitle)
        self.subtitle.setWordWrap(True)
        self.subtitle.setObjectName("placeholder")
        outer.addWidget(self.subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.grid = QGridLayout(content)
        self.grid.setSpacing(6)
        scroll.setWidget(content)
        outer.addWidget(scroll)

        self.placeholder = QLabel("Sélectionne une sauvegarde dans la liste à gauche.")
        self.placeholder.setObjectName("placeholder")
        outer.addWidget(self.placeholder)

    def show_slot(self, slot, compare_slot=None):
        self.placeholder.hide()
        while self.grid.count():
            child = self.grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        obtained_ids = mgs4save.read_obtained_emblems(slot.mgs4_sav)
        emblems = mgs4save.compute_emblems(slot.mgs4_sav, slot.metadata_sav)
        obtained_ids_compare = mgs4save.read_obtained_emblems(compare_slot.mgs4_sav) if compare_slot is not None else None
        header_text = f"EMBLÈMES ({len(obtained_ids)} / {len(emblems)})"
        if obtained_ids_compare is not None:
            only_here = len(obtained_ids - obtained_ids_compare)
            only_compare = len(obtained_ids_compare - obtained_ids)
            header_text += f" — {only_here} en rouge, {only_compare} en vert"
        self.header.setText(header_text)
        self.subtitle.setText(
            f"{self._base_subtitle}\n{COMPARE_MODE_HINT}" if obtained_ids_compare is not None else self._base_subtitle
        )
        for i, emblem in enumerate(emblems):
            emblem = dict(emblem)
            emblem["obtained"] = emblem["id"] in obtained_ids
            # Obtenu + conditions actuelles remplies = obtenu sur CETTE
            # partie, mais seulement si au moins une condition est de type
            # MIN (ces stats repartent a zero a chaque partie, donc vraies
            # maintenant = forcement grace a celle-ci). Si l'embleme n'a que
            # des conditions MAX ("moins de X", "0 X"), elles sont souvent
            # trivialement vraies des le debut de N'IMPORTE quelle partie
            # (ex. RAVEN, "moins de 5h de jeu") - leur verite actuelle ne
            # prouve rien sur QUAND l'embleme a ete obtenu, donc on retombe
            # sur "partie precedente" par prudence dans ce cas.
            emblem["obtained_previous_run"] = emblem["obtained"] and not (
                emblem["unlocked"] and emblem["has_reliable_min_condition"]
            )
            emblem["projected"] = emblem["unlocked"] and not emblem["obtained"]
            emblem["only_here"] = obtained_ids_compare is not None and emblem["obtained"] and emblem["id"] not in obtained_ids_compare
            emblem["only_compare"] = obtained_ids_compare is not None and not emblem["obtained"] and emblem["id"] in obtained_ids_compare
            btn = QPushButton(f"{emblem['id']:02d}\n{emblem['name']}")
            if emblem["only_here"]:
                btn.setObjectName("collectionOnlyHere")
            elif emblem["only_compare"]:
                btn.setObjectName("collectionOnlyCompare")
            elif emblem["obtained_previous_run"]:
                btn.setObjectName("emblemUnlockedPrevious")
            elif emblem["obtained"]:
                btn.setObjectName("emblemUnlocked")
            elif emblem["projected"]:
                btn.setObjectName("emblemProjected")
            elif emblem["impossible"]:
                btn.setObjectName("emblemImpossible")
            else:
                btn.setObjectName("emblemLocked")
            btn.setMinimumSize(130, 64)
            btn.clicked.connect(lambda _checked=False, e=emblem: self._show_dialog(e))
            self.grid.addWidget(btn, i // self.COLUMNS, i % self.COLUMNS)

    def _show_dialog(self, emblem):
        EmblemDialog(emblem, self).exec()


class HelpDialog(QDialog):
    """Popup d'aide : explication rapide, version, et changelog condense."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Aide")
        self.setMinimumSize(480, 520)
        layout = QVBoxLayout(self)

        version = QLabel(f"MGS4 Save Stats — {APP_VERSION}")
        version.setObjectName("title")
        layout.addWidget(version)

        help_title = QLabel("COMMENT ÇA MARCHE")
        help_title.setObjectName("groupTitle")
        layout.addWidget(help_title)

        help_text = QLabel(APP_HELP_TEXT)
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        changelog_title = QLabel("CHANGELOG")
        changelog_title.setObjectName("groupTitle")
        layout.addWidget(changelog_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(10)
        for version_label, date, description in APP_CHANGELOG:
            entry = QFrame()
            entry.setObjectName("card")
            entry_layout = QVBoxLayout(entry)
            header = QLabel(f"{version_label} — {date}")
            header.setObjectName("statLabel")
            entry_layout.addWidget(header)
            desc = QLabel(description)
            desc.setWordWrap(True)
            entry_layout.addWidget(desc)
            content_layout.addWidget(entry)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class InfoDialog(QDialog):
    """Popup generique titre + valeur + texte d'explication, pour les
    stats numeriques cliquables (ex: batteries du Solid Eye)."""

    def __init__(self, title, value_text, condition_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)

        value = QLabel(value_text)
        value.setObjectName("subtitle")
        layout.addWidget(value)

        cond_title = QLabel("COMMENT L'OBTENIR")
        cond_title.setObjectName("groupTitle")
        layout.addWidget(cond_title)

        cond = QLabel(condition_text)
        cond.setWordWrap(True)
        layout.addWidget(cond)

        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setMinimumWidth(360)


class CollectionDetailDialog(QDialog):
    """Popup generique nom + statut + condition d'obtention, pour les
    collections qui ont une condition a expliquer (ex: Statuettes) -
    equivalent simplifie de EmblemDialog (pas de logique obtenu/pas encore/
    impossible, juste obtenu ou non)."""

    def __init__(self, entry, parent=None):
        super().__init__(parent)
        self.setWindowTitle(entry["name"])
        layout = QVBoxLayout(self)

        status = QLabel("Obtenue" if entry["owned"] else "Pas encore obtenue")
        status.setObjectName("subtitle" if entry["owned"] else "placeholder")
        layout.addWidget(status)

        if "condition" in entry:
            cond_title = QLabel("CONDITION D'OBTENTION")
            cond_title.setObjectName("groupTitle")
            layout.addWidget(cond_title)

            cond = QLabel(entry["condition"] or "Pas encore documentée (identification incertaine ou pas encore vérifiée).")
            cond.setWordWrap(True)
            layout.addWidget(cond)

        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setMinimumWidth(360)


class CollectionPanel(QWidget):
    """Panneau generique pour une collection d'objets a 2 etats (obtenu /
    verrouille) : reutilise pour Camouflages, Statuettes et Chansons. Les
    badges ne sont cliquables (popup de detail) que si show_detail=True et
    qu'une entree a une cle "condition" non vide."""

    COLUMNS = 4
    BUTTON_SIZE = (150, 50)

    def __init__(self, title, subtitle, reader, columns=None, footer=None, ratio_fn=None, group_totals=None, button_size=None, show_detail=False):
        super().__init__()
        self._title = title
        self._base_subtitle = subtitle
        self._reader = reader
        self._footer_fn = footer
        self._ratio_fn = ratio_fn or (lambda entries: (sum(e["owned"] for e in entries), len(entries)))
        # Total "canonique" a afficher par groupe (ex. 14 FaceCamo dans le
        # jeu bien qu'on n'en ait identifie que 13) - par defaut, le nombre
        # d'entrees effectivement suivies dans ce groupe.
        self._group_totals = group_totals or {}
        self._show_detail = show_detail
        if columns:
            self.COLUMNS = columns
        if button_size:
            self.BUTTON_SIZE = button_size
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)

        self.header = QLabel(title)
        self.header.setObjectName("title")
        outer.addWidget(self.header)

        self.subtitle = QLabel(subtitle)
        self.subtitle.setObjectName("placeholder")
        self.subtitle.setWordWrap(True)
        outer.addWidget(self.subtitle)

        self.footer = QLabel("")
        self.footer.setObjectName("subtitle")
        outer.addWidget(self.footer)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.sections = QVBoxLayout(content)
        self.sections.setSpacing(14)
        # Sans ceci, les QLabel/QWidget de sections (politique de taille
        # "Preferred", donc extensible) se partagent tout l'espace vertical
        # laisse libre par le QScrollArea, ce qui cree de gros vides entre
        # chaque section au lieu de les garder compactes en haut.
        self.sections.setAlignment(Qt.AlignTop)
        scroll.setWidget(content)
        outer.addWidget(scroll)

        self.placeholder = QLabel("Sélectionne une sauvegarde dans la liste à gauche.")
        self.placeholder.setObjectName("placeholder")
        outer.addWidget(self.placeholder)

    def show_slot(self, slot, compare_slot=None):
        self.placeholder.hide()
        while self.sections.count():
            child = self.sections.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        entries = self._reader(slot.mgs4_sav)
        if compare_slot is not None:
            entries = _mark_diff(entries, self._reader(compare_slot.mgs4_sav))
        owned, total = self._ratio_fn(entries)
        header_text = f"{self._title} ({owned} / {total})"
        if compare_slot is not None:
            only_here = sum(e.get("only_here", False) for e in entries)
            only_compare = sum(e.get("only_compare", False) for e in entries)
            header_text += f" — {only_here} en rouge, {only_compare} en vert"
        self.header.setText(header_text)
        self.subtitle.setText(
            f"{self._base_subtitle} {COMPARE_MODE_HINT}" if compare_slot is not None else self._base_subtitle
        )

        # Regroupe par cle "group" si presente (ordre d'apparition
        # preserve), sinon un seul groupe implicite sans en-tete.
        groups: dict[str | None, list[dict]] = {}
        for entry in entries:
            groups.setdefault(entry.get("group"), []).append(entry)

        for group_name, group_entries in groups.items():
            if group_name:
                group_owned = sum(e["owned"] for e in group_entries)
                group_total = self._group_totals.get(group_name, len(group_entries))
                label = QLabel(f"{group_name.upper()} ({group_owned} / {group_total})")
                label.setObjectName("groupTitle")
                self.sections.addWidget(label)

            grid_widget = QWidget()
            grid = QGridLayout(grid_widget)
            grid.setSpacing(6)
            for col in range(self.COLUMNS):
                grid.setColumnStretch(col, 0)

            # Meme technique que WeaponsPanel._add_group : mesure avec la
            # police reelle (post-polish) pour trouver la largeur commune
            # necessaire au groupe, puis reapplique le decoupage a cette
            # largeur finale (voir gui_app.py, WeaponsPanel._add_group pour
            # le detail de pourquoi ces 2 passes sont necessaires).
            buttons = []
            tile_width = self.BUTTON_SIZE[0]
            for entry in group_entries:
                btn = QPushButton()
                if entry.get("only_here"):
                    btn.setObjectName("collectionOnlyHere")
                elif entry.get("only_compare"):
                    btn.setObjectName("collectionOnlyCompare")
                else:
                    btn.setObjectName("collectionOwned" if entry["owned"] else "collectionLocked")
                btn.ensurePolished()
                fm = btn.fontMetrics()
                worst_case = _wrap_button_text(fm, entry["name"], 0)
                needed = max(fm.horizontalAdvance(line) for line in worst_case.split("\n")) * TILE_TEXT_SAFETY_FACTOR + 20
                tile_width = max(tile_width, needed)
                if self._show_detail and "condition" in entry:
                    btn.clicked.connect(lambda _checked=False, e=entry: self._show_dialog(e))
                buttons.append((btn, entry["name"], fm))

            for i, (btn, name, fm) in enumerate(buttons):
                btn.setFixedSize(int(tile_width), self.BUTTON_SIZE[1])
                btn.setText(_wrap_button_text(fm, name, (tile_width - 20) / TILE_TEXT_SAFETY_FACTOR))
                grid.addWidget(btn, i // self.COLUMNS, i % self.COLUMNS)

            row_wrap = QWidget()
            row_layout = QHBoxLayout(row_wrap)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addStretch()
            row_layout.addWidget(grid_widget)
            row_layout.addStretch()
            self.sections.addWidget(row_wrap)

        if self._footer_fn:
            self.footer.setText(self._footer_fn(entries))

    def _show_dialog(self, entry):
        CollectionDetailDialog(entry, self).exec()


# Marge de securite proportionnelle appliquee aux mesures de texte des
# tuiles (armes/objets). La police reellement utilisee a l'execution
# (Segoe UI sous Windows) n'est pas forcement celle disponible pendant le
# developpement/les tests - un simple pixel fixe ne suffit pas a absorber
# l'ecart, d'ou un facteur proportionnel a la longueur du texte.
TILE_TEXT_SAFETY_FACTOR = 1.3


def _wrap_button_text(fm, text, max_width):
    """Coupe un nom trop long sur 2 lignes (au niveau d'un espace) plutot
    que de le tronquer avec des points de suspension."""
    if fm.horizontalAdvance(text) <= max_width:
        return text
    words = text.split(" ")
    if len(words) == 1:
        return text
    best = None
    for i in range(1, len(words)):
        line1 = " ".join(words[:i])
        line2 = " ".join(words[i:])
        score = max(fm.horizontalAdvance(line1), fm.horizontalAdvance(line2))
        if best is None or score < best[0]:
            best = (score, line1, line2)
    return f"{best[1]}\n{best[2]}"


COMPARE_MODE_HINT = "Rouge = absent sur la sauvegarde comparée. Vert = l'inverse."


def _mark_diff(entries_here, entries_compare):
    """Mode comparaison bidirectionnel : pour chaque entree de
    `entries_here` (la save affichee - la 1ere selectionnee), ajoute :
    - "only_here" (rouge) : possedee ici, absente de la save de comparaison.
    - "only_compare" (vert) : absente ici, possedee sur la save de
      comparaison.
    Ni l'un ni l'autre = meme etat sur les deux (l'etat 1 vs 2 n'est pas
    pris en compte, "owned" les regroupe deja tous les deux). Appariement
    par "id" seul quand il existe (stable, independant de la quantite -
    le "name" peut varier d'une save a l'autre pour les objets a quantite,
    ex. "Ration (14)" vs "Ration (26)", donc ne JAMAIS l'inclure dans la
    cle tant qu'un id existe), ou par "name" seul quand "id" est None
    (tuiles indicatives comme les FaceCamo Dore, qui n'ont pas d'id)."""
    def _key(e):
        return e.get("id") if e.get("id") is not None else e.get("name")

    owned_compare = {_key(e) for e in entries_compare if e["owned"]}
    result = []
    for e in entries_here:
        e = dict(e)
        key = _key(e)
        e["only_here"] = e["owned"] and key not in owned_compare
        e["only_compare"] = (not e["owned"]) and key in owned_compare
        result.append(e)
    return result


def _camo_ratio(entries):
    # Compte tout (FaceCamo + Gilet + Octocamo, y compris les tuiles
    # indicatives id=None) pour que le total corresponde a la somme des
    # sous-totaux de groupe (16 + 11 + 21 = 48), au lieu d'ignorer
    # silencieusement des groupes entiers comme avant.
    return sum(e["owned"] for e in entries), len(entries)


TARGET_OBJECTS = 18  # Total canonique (13 equipements + 5 consommables), recompte via le guide d'inventaire du jeu - voir notes.md


def _objects_ratio(entries):
    return sum(e["owned"] for e in entries), TARGET_OBJECTS


class WeaponsPanel(CollectionPanel):
    """Cas particulier des armes : sections Armes et Accessoires rendues
    separement (pas juste un regroupement visuel), chacune avec son propre
    compteur cible sur le total canonique du jeu (70 armes / 18
    accessoires, recompte via le guide d'inventaire du jeu - voir notes.md)
    plutot que sur le nombre d'entrees deja identifiees dans notre tableau
    (qui grandit au fil des trouvailles). Les accessoires ont des noms plus
    longs en moyenne, donc une grille moins dense (colonnes plus larges)
    pour eviter le texte tronque."""

    TARGET_WEAPONS = 70
    TARGET_ACCESSORIES = 18
    WEAPON_COLUMNS = 8
    WEAPON_BUTTON_SIZE = (105, 50)
    ACCESSORY_COLUMNS = 5
    ACCESSORY_BUTTON_SIZE = (170, 50)

    def __init__(self):
        super().__init__(
            "ARMES",
            "Blanc = arme acquise. Gris = non acquise. Point rouge = acquise mais "
            "verrouillée chez Drebin. Quelques armes n'ont pas encore de nom "
            "identifié (affichées \"Arme #NN\") — travail en cours, voir notes.md. "
            "Les compteurs \"X / 70\" et \"X / 18\" visent le total canonique du "
            "jeu, pas le nombre d'entrées déjà identifiées.",
            mgs4save.read_weapons,
        )

    def show_slot(self, slot, compare_slot=None):
        self.placeholder.hide()
        while self.sections.count():
            child = self.sections.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        entries = self._reader(slot.mgs4_sav)
        if compare_slot is not None:
            entries = _mark_diff(entries, self._reader(compare_slot.mgs4_sav))
        groups: dict[str, list[dict]] = {}
        for entry in entries:
            groups.setdefault(entry["group"], []).append(entry)

        owned_weapons = sum(
            1 for g, es in groups.items() if g not in ("Accessoire", "Non identifiée")
            for e in es if e["owned"]
        )
        owned_accessories = sum(1 for e in groups.get("Accessoire", []) if e["owned"])

        header_text = f"ARMES ({owned_weapons} / {self.TARGET_WEAPONS})"
        if compare_slot is not None:
            only_here = sum(e.get("only_here", False) for e in entries)
            only_compare = sum(e.get("only_compare", False) for e in entries)
            header_text += f" — {only_here} en rouge, {only_compare} en vert"
        self.header.setText(header_text)
        self.subtitle.setText(
            f"{self._base_subtitle} {COMPARE_MODE_HINT}" if compare_slot is not None else self._base_subtitle
        )
        for group_name, group_entries in groups.items():
            if group_name in ("Accessoire", "Non identifiée"):
                continue
            self._add_group(group_name, group_entries, self.WEAPON_COLUMNS, self.WEAPON_BUTTON_SIZE)

        self._add_section_title(f"ACCESSOIRES ({owned_accessories} / {self.TARGET_ACCESSORIES})")
        self._add_group("Accessoire", groups.get("Accessoire", []), self.ACCESSORY_COLUMNS, self.ACCESSORY_BUTTON_SIZE, show_header=False)

        if groups.get("Non identifiée"):
            self._add_group("Non identifiée", groups["Non identifiée"], self.WEAPON_COLUMNS, self.WEAPON_BUTTON_SIZE)

    def _add_section_title(self, text):
        title = QLabel(text)
        title.setObjectName("title")
        self.sections.addWidget(title)

    def _add_group(self, group_name, group_entries, columns, button_size, show_header=True):
        if show_header:
            label = QLabel(group_name.upper())
            label.setObjectName("groupTitle")
            self.sections.addWidget(label)

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(6)
        for col in range(columns):
            grid.setColumnStretch(col, 0)

        # Premiere passe : cree les boutons et mesure, avec leur police
        # reelle (gras inclus pour les items obtenus), la largeur qu'il leur
        # faudrait au mieux (meilleur decoupage 2 lignes, sans plafond) pour
        # ne rien couper. La largeur commune du groupe est le max de tous -
        # les noms courts (Pistolets, Fusils...) restent compacts, seul un
        # groupe contenant un nom exceptionnellement long (ex. "Grenade a
        # particules metalliques") s'elargit, et seulement ce groupe-la.
        buttons = []
        tile_width = button_size[0]
        for entry in group_entries:
            btn = QPushButton()
            if entry.get("only_here"):
                btn.setObjectName("collectionOnlyHere")
            elif entry.get("only_compare"):
                btn.setObjectName("collectionOnlyCompare")
            else:
                btn.setObjectName("collectionOwned" if entry["owned"] else "collectionLocked")
            btn.ensurePolished()
            fm = btn.fontMetrics()
            # Decoupage force (max_width=0) juste pour mesurer le pire cas -
            # le texte reellement affiche est recalcule plus bas contre la
            # largeur finale du groupe, pour ne pas forcer un retour a la
            # ligne inutile sur un nom qui tiendrait sur une seule ligne.
            worst_case = _wrap_button_text(fm, entry["name"], 0)
            needed = max(fm.horizontalAdvance(line) for line in worst_case.split("\n")) * TILE_TEXT_SAFETY_FACTOR + 20
            tile_width = max(tile_width, needed)
            buttons.append((entry["id"], btn, entry["name"], fm, entry.get("drebin_locked", False)))

        # Les entrees listees dans WEAPON_ROW_BREAK_IDS (ex. couleurs de
        # grenade fumigene) sautent a une nouvelle ligne des la premiere
        # rencontree, pour rester groupees visuellement sur leur propre
        # ligne plutot que de se retrouver coupees en fin de ligne
        # precedente. Les autres entrees de WEAPON_SORT_OVERRIDE (ex.
        # Mk.2/Operator) se reordonnent seulement, sans sauter de ligne.
        row, col = 0, 0
        started_override_row = False
        for weapon_id, btn, name, fm, drebin_locked in buttons:
            if weapon_id in mgs4save.WEAPON_ROW_BREAK_IDS and not started_override_row:
                started_override_row = True
                if col != 0:
                    row += 1
                    col = 0
            btn.setFixedSize(int(tile_width), button_size[1])
            btn.setText(_wrap_button_text(fm, name, (tile_width - 20) / TILE_TEXT_SAFETY_FACTOR))
            grid.addWidget(btn, row, col)
            if drebin_locked:
                dot = QWidget(btn)
                dot.setFixedSize(9, 9)
                dot.setStyleSheet("background-color: #c0392b; border-radius: 4px; border: 1px solid #1a1a1a;")
                dot.move(int(tile_width) - 15, 4)
                dot.setAttribute(Qt.WA_TransparentForMouseEvents, True)
                dot.setToolTip("Acquise mais verrouillée chez Drebin")
                dot.show()
            col += 1
            if col >= columns:
                col = 0
                row += 1

        # Colonnes non etirees (ci-dessus) => grid_widget ne prend que la
        # largeur necessaire a son contenu ; les stretch de part et d'autre
        # centrent ce bloc compact dans le panneau, au lieu de l'etaler ou
        # de le coller a gauche quand le groupe a moins d'entrees que
        # `columns`.
        row_wrap = QWidget()
        row_layout = QHBoxLayout(row_wrap)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addStretch()
        row_layout.addWidget(grid_widget)
        row_layout.addStretch()
        self.sections.addWidget(row_wrap)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MGS4 Save Stats")
        self.resize(1500, 800)

        self.background = QWidget()
        self.background.setObjectName("root")
        self.setCentralWidget(self.background)
        bg_layout = QVBoxLayout(self.background)
        bg_layout.setContentsMargins(0, 0, 0, 0)

        self._current_folder = None  # None = detection automatique, sinon dossier choisi manuellement
        self._imported_slots = []  # saves importees ponctuellement (cle USB, email...), non persistees
        self._current_slot = None
        self._compare_slot = None  # mode comparaison actif si non None

        splitter = QSplitter()
        self.list_panel = SlotListPanel(
            self.show_stats, self.change_folder, self.refresh_current, self.delete_slot,
            self.import_save_folder, self.compare_with_slot,
        )
        self.stats_panel = StatsPanel()
        self.emblems_panel = EmblemsPanel()
        self.special_items_panel = CollectionPanel(
            "OBJETS",
            "Blanc = obtenu. Gris = pas encore obtenu.",
            mgs4save.read_objects,
            columns=4,
            ratio_fn=_objects_ratio,
            show_detail=True,
        )
        self.camo_panel = CollectionPanel(
            "OCTOCAMO",
            "Blanc = obtenu. Gris = pas encore obtenu. Clique sur un camouflage facial "
            "ou un motif Octocamo pour voir sa condition d'obtention. La section "
            "\"Octocamo\" n'est pas reliée à ta sauvegarde (IDs pas encore trouvés) — "
            "affichée à titre indicatif seulement.",
            mgs4save.read_camo,
            columns=4,
            ratio_fn=_camo_ratio,
            group_totals={"FaceCamo": 16, "Gilet": 11, "Octocamo": 21},
            show_detail=True,
        )
        self.outfits_panel = CollectionPanel(
            "TENUES",
            "Blanc = obtenue. Gris = pas encore obtenue. Clique sur une tenue "
            "pour voir sa condition d'obtention.",
            mgs4save.read_outfits,
            columns=3,
            show_detail=True,
        )
        self.figurines_panel = CollectionPanel(
            "STATUETTES",
            "Blanc = obtenue. Gris = pas encore obtenue. Clique sur une statuette "
            "pour voir sa condition d'obtention. La collection complète débloque "
            "le Pistolet solaire.",
            mgs4save.read_figurines,
            columns=5,
            show_detail=True,
        )
        self.songs_panel = CollectionPanel(
            "CHANSONS (iPod)",
            "Blanc = débloquée. Gris = pas encore débloquée.",
            mgs4save.read_songs,
            columns=4,
            show_detail=True,
        )
        self.weapons_panel = WeaponsPanel()
        tabs = QTabWidget()
        tabs.addTab(self.stats_panel, "Stats")
        tabs.addTab(self.weapons_panel, "Armes")
        tabs.addTab(self.special_items_panel, "Objets")
        tabs.addTab(self.camo_panel, "OctoCamo")
        tabs.addTab(self.outfits_panel, "Tenues")
        tabs.addTab(self.figurines_panel, "Statuettes")
        tabs.addTab(self.songs_panel, "Chansons")
        tabs.addTab(self.emblems_panel, "Emblèmes")
        splitter.addWidget(self.list_panel)
        splitter.addWidget(tabs)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([420, 1080])
        bg_layout.addWidget(splitter)

        self.refresh_slots()

    def refresh_slots(self):
        slots = save_finder.find_all_slots()
        if not slots:
            self.change_folder(auto_failed=True)
            return
        self._current_folder = None
        self._apply_slots(slots + self._imported_slots)

    def refresh_current(self):
        """Re-scanne le dossier actuellement utilise (auto-detecte ou choisi
        manuellement) sans redemander de dossier - pour le bouton Actualiser."""
        if self._current_folder is None:
            slots = save_finder.find_all_slots()
        else:
            slots = save_finder.list_save_slots(self._current_folder)
        self._apply_slots(slots + self._imported_slots)

    def change_folder(self, auto_failed=False):
        if auto_failed:
            QMessageBox.information(
                self,
                "Détection automatique impossible",
                "Le dossier de sauvegarde MGS4 n'a pas été trouvé automatiquement.\n"
                "Sélectionne le dossier 'mgs4_savedata_win' manuellement.",
            )
        folder = QFileDialog.getExistingDirectory(self, "Choisir le dossier mgs4_savedata_win")
        if not folder:
            return
        slots = save_finder.list_save_slots(folder)
        if not slots:
            QMessageBox.warning(self, "Aucun slot trouvé", "Aucune sauvegarde MGS4 dans ce dossier.")
            return
        self._current_folder = folder
        self._apply_slots(slots + self._imported_slots)

    def import_save_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choisir un dossier de sauvegarde à importer")
        if not folder:
            return
        found = save_finder.find_slots_in_any_folder(folder)
        if not found:
            QMessageBox.warning(
                self, "Aucun slot trouvé",
                "Aucun fichier MGS4.SAV / METADATA.SAV trouvé dans ce dossier (ni ses sous-dossiers).",
            )
            return
        existing_paths = {s.path for s in self._imported_slots}
        self._imported_slots.extend(s for s in found if s.path not in existing_paths)
        self.refresh_current()

    def delete_slot(self, slot):
        summary = mgs4save.read_metadata_summary(slot.metadata_sav)
        siblings = self._find_same_playthrough_siblings(slot, summary)
        dialog = ConfirmDeleteDialog(slot, summary, sibling_count=len(siblings), parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        targets = [slot] + siblings if dialog.delete_group() else [slot]
        failed = [s for s in targets if not send_folder_to_recycle_bin(s.path)]
        self.refresh_current()
        if failed:
            QMessageBox.warning(
                self, "Échec",
                f"{len(failed)} sauvegarde(s) n'ont pas pu être supprimées "
                "(peut-être utilisées par le jeu)."
            )

    # Compteurs cumules du jeu (MGS4.SAV) qui ne peuvent que monter au sein
    # d'une meme partie, et repartent forcement a 0 sur une toute nouvelle
    # partie - bien plus fiable qu'un delai arbitraire, vu que MGS4 n'a pas
    # de sauvegarde automatique (l'utilisateur peut tres bien laisser
    # passer plusieurs heures, voire plus, entre deux saves manuelles de la
    # meme partie).
    MONOTONIC_STAT_FIELDS = (
        "drebin_total_ventes", "weapon_pickups", "item_pickups", "holdups",
        "body_searches", "praises", "syringe_uses", "scanning_plug_uses",
        "playboy_pages", "emotion_magazine_pages", "cqc", "headshots",
        "knife_kills", "knife_knockouts", "soins_utilises", "flashbacks_vues",
    )

    def _find_same_playthrough_siblings(self, slot, summary):
        """Sauvegardes de la meme partie que `slot` : meme difficulte et
        meme numero de partie (identifiant fiable fourni par le jeu), ET
        temps de jeu + tous les compteurs cumules de MONOTONIC_STAT_FIELDS
        qui n'ont jamais redescendu entre elles (par date). Une vraie
        nouvelle partie (meme si elle partage par coincidence la meme
        difficulte et le meme numero 0) remet TOUS ces compteurs a 0 - il
        suffit qu'un seul redescende pour couper le groupe en segments.
        Ne renvoie que le segment contenant `slot`."""
        # ID Steam (dossier grand-parent du slot) : identifiant de compte
        # garanti par la structure de dossiers du jeu, pas une deduction -
        # deux comptes differents sur le meme PC ne seront jamais melanges.
        steamid = os.path.basename(os.path.dirname(os.path.dirname(slot.path)))
        key = (steamid, summary["difficulte_nom"], summary["numero_partie"])
        candidates = [
            (s, sm) for s, sm in getattr(self, "_current_slots_with_summary", [])
            if (os.path.basename(os.path.dirname(os.path.dirname(s.path))), sm["difficulte_nom"], sm["numero_partie"]) == key
        ]
        candidates.sort(key=lambda item: item[1]["date_modif"])

        segment: list = []
        prev_values = None
        for s, sm in candidates:
            stats = mgs4save.read_stats(s.mgs4_sav)
            values = tuple(stats[f] for f in self.MONOTONIC_STAT_FIELDS) + (sm["playtime_secondes"],)
            if prev_values is not None and any(v < pv for v, pv in zip(values, prev_values)):
                if any(s2.path == slot.path for s2 in segment):
                    return [s2 for s2 in segment if s2.path != slot.path]
                segment = []
            segment.append(s)
            prev_values = values
        return [s2 for s2 in segment if s2.path != slot.path]

    def _apply_slots(self, slots):
        # Plus recente en premier (par date de derniere modification de MGS4.SAV).
        slots = sorted(
            slots,
            key=lambda s: os.path.getmtime(s.mgs4_sav) if os.path.isfile(s.mgs4_sav) else 0,
            reverse=True,
        )
        slots_with_summary = []
        for slot in slots:
            try:
                slots_with_summary.append((
                    slot,
                    {
                        **mgs4save.read_metadata_summary(slot.metadata_sav),
                        **mgs4save.read_progress_info(slot.mgs4_sav),
                        "date_modif": datetime.datetime.fromtimestamp(os.path.getmtime(slot.mgs4_sav)),
                    },
                ))
            except OSError:
                # Save supprimee/en cours d'ecriture entre le listage du
                # dossier et la lecture - on l'ignore plutot que de planter
                # toute la liste.
                continue
        self._current_slots_with_summary = slots_with_summary
        self.list_panel.set_slots(slots_with_summary)

    def show_stats(self, slot):
        self._current_slot = slot
        cmp = self._compare_slot
        try:
            self.stats_panel.show_slot(slot, cmp)
            self.emblems_panel.show_slot(slot, cmp)
            self.weapons_panel.show_slot(slot, cmp)
            self.special_items_panel.show_slot(slot, cmp)
            self.camo_panel.show_slot(slot, cmp)
            self.outfits_panel.show_slot(slot, cmp)
            self.figurines_panel.show_slot(slot, cmp)
            self.songs_panel.show_slot(slot, cmp)
        except OSError:
            QMessageBox.warning(
                self,
                "Sauvegarde introuvable",
                "Cette sauvegarde a disparu ou est illisible (supprimée ou en cours d'écriture par le jeu). Actualisation de la liste.",
            )
            self.refresh_slots()

    def compare_with_slot(self, slot):
        """Bouton "Comparer"/"Quitter la comparaison" directement sur une
        ligne de la liste : clique sur la cible active pour arreter, sur une
        autre ligne pour comparer avec elle."""
        if self._compare_slot is not None and slot.path == self._compare_slot.path:
            self._compare_slot = None
            self.list_panel.set_compare_active(False)
            if self._current_slot is not None:
                self.show_stats(self._current_slot)
            return
        if slot.path == self._current_slot.path:
            return  # bouton absent sur la ligne selectionnee, garde-fou par securite
        self._activate_compare(slot)

    def _activate_compare(self, chosen):
        self._compare_slot = chosen
        summary = mgs4save.read_metadata_summary(chosen.metadata_sav)
        progress = mgs4save.read_progress_info(chosen.mgs4_sav)
        label = f"{summary['difficulte_nom']}, {format_lieu_acte(progress['lieu'], progress['acte'])}"
        self.list_panel.set_compare_active(True, label, compare_path=chosen.path)
        self.show_stats(self._current_slot)


def main():
    app = QApplication(sys.argv)
    # Le style natif Windows (windowsvista/windows11) peint lui-meme le fond
    # et la bordure des QPushButton via le theme systeme, en ignorant ces
    # proprietes du style sheet (seule la couleur du texte passe) - Fusion
    # est peint entierement par Qt et respecte tout le QSS ci-dessous.
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_QSS)
    if os.path.isfile(APP_ICON):
        app.setWindowIcon(QIcon(APP_ICON))
    window = MainWindow()
    if os.path.isfile(APP_ICON):
        window.setWindowIcon(QIcon(APP_ICON))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
