"""Interface graphique MGS4 Save Stats (PySide6).

Fenetre unique : liste des slots a gauche, stats du slot selectionne a
droite (mise a jour au clic, pas de navigation par page). Lecture seule :
aucune ecriture dans les fichiers de save.
"""

import os
import sys

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QIcon, QPainter, QColor
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
)

import mgs4save
import save_finder

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


THEME_BACKGROUND = _external_path("themes", "background.jpg")
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
QMainWindow, QWidget#root { background-color: #0b0b0c; }
QLabel { color: #d8d8d8; }
QLabel#title { color: #f0f0f0; font-size: 20px; font-weight: 600; letter-spacing: 1px; }
QLabel#subtitle { color: #c9a24b; font-size: 15px; font-weight: 600; }
QLabel#groupTitle { color: #c9a24b; font-size: 13px; font-weight: 700; letter-spacing: 2px; }
QLabel#statLabel { color: #9a9a9a; font-size: 12px; }
QLabel#statValue { color: #f0f0f0; font-size: 14px; font-weight: 600; }
QLabel#placeholder { color: #6a6a6a; font-size: 14px; }
QListWidget { background: transparent; border: none; }
QListWidget::item { background: rgba(20,20,22,190); border: 1px solid rgba(255,255,255,30); margin: 4px 8px; padding: 6px; }
QListWidget::item:selected { border: 1px solid #c9a24b; background: rgba(40,35,20,200); }
QPushButton { background: rgba(255,255,255,20); color: #e8e8e8; border: 1px solid rgba(255,255,255,60); padding: 6px 14px; }
QPushButton:hover { background: rgba(255,255,255,40); }
QFrame#card { background: rgba(15,15,17,170); border: 1px solid rgba(255,255,255,25); }
QSplitter::handle { background: rgba(255,255,255,20); }
"""


class BackgroundWidget(QWidget):
    """Widget racine qui dessine une image de fond si disponible, sinon un
    simple aplat sombre. L'image n'est jamais fournie avec le projet (voir
    themes/README.md) : chacun met la sienne."""

    def __init__(self):
        super().__init__()
        self._pixmap = QPixmap(THEME_BACKGROUND) if os.path.isfile(THEME_BACKGROUND) else None

    def paintEvent(self, event):
        painter = QPainter(self)
        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            painter.fillRect(self.rect(), QColor(0, 0, 0, 140))
        else:
            painter.fillRect(self.rect(), QColor(12, 12, 14))
        painter.end()


class SlotListPanel(QWidget):
    def __init__(self, on_selection_changed, on_change_folder):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 10, 20)

        title = QLabel("SAUVEGARDES")
        title.setObjectName("title")
        layout.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(140, 79))  # ratio 16:9, taille ICON0.PNG du jeu
        self.list_widget.currentItemChanged.connect(
            lambda current, _prev: current and on_selection_changed(current.data(Qt.UserRole))
        )
        layout.addWidget(self.list_widget)

        change_btn = QPushButton("Changer de dossier…")
        change_btn.clicked.connect(on_change_folder)
        layout.addWidget(change_btn)

    def set_slots(self, slots_with_summary):
        self.list_widget.clear()
        for slot, summary in slots_with_summary:
            label = (
                f"{summary['difficulte_nom']}  —  Partie n°{summary['numero_partie']}\n"
                f"Temps de jeu : {seconds_to_hms(summary['playtime_secondes'])}    "
                f"Drebin : {format_stat_value('drebin_actuel', summary['drebin_actuel'])}"
            )
            item = QListWidgetItem(label)
            if os.path.isfile(slot.icon_png):
                item.setIcon(QIcon(slot.icon_png))
            item.setData(Qt.UserRole, slot)
            self.list_widget.addItem(item)
        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)


class StatsPanel(QWidget):
    def __init__(self):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 20, 20, 20)

        self.title = QLabel("")
        self.title.setObjectName("subtitle")
        outer.addWidget(self.title)

        self.placeholder = QLabel("Sélectionne une sauvegarde dans la liste à gauche.")
        self.placeholder.setObjectName("placeholder")
        outer.addWidget(self.placeholder)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        content = QWidget()
        self.grid = QGridLayout(content)
        self.grid.setSpacing(16)
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def show_slot(self, slot):
        self.placeholder.hide()
        while self.grid.count():
            child = self.grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        stats = mgs4save.read_stats(slot.mgs4_sav)
        meta = mgs4save.read_metadata_summary(slot.metadata_sav)
        self.title.setText(f"{meta['difficulte_nom']} — Partie n°{meta['numero_partie']}")

        cards = [
            self._build_card(group_name, [
                (label, format_stat_value(key, stats.get(key, 0))) for key, label in fields
            ])
            for group_name, fields in STAT_GROUPS
        ]

        time_rows = [("Temps de jeu total", seconds_to_hms(meta["playtime_secondes"]))]
        time_rows += [(label, format_stat_value(key, stats.get(key, 0))) for key, label in TIME_FIELDS]
        cards.append(self._build_card("Temps", time_rows))

        columns = 2
        for i, card in enumerate(cards):
            self.grid.addWidget(card, i // columns, i % columns)

    @staticmethod
    def _build_card(title, rows):
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        group_title = QLabel(title.upper())
        group_title.setObjectName("groupTitle")
        card_layout.addWidget(group_title)
        for label, value in rows:
            row = QHBoxLayout()
            name_label = QLabel(label)
            name_label.setObjectName("statLabel")
            value_label = QLabel(str(value))
            value_label.setObjectName("statValue")
            row.addWidget(name_label)
            row.addStretch()
            row.addWidget(value_label)
            card_layout.addLayout(row)
        return card


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MGS4 Save Stats")
        self.resize(1200, 750)

        self.background = BackgroundWidget()
        self.background.setObjectName("root")
        self.setCentralWidget(self.background)
        bg_layout = QVBoxLayout(self.background)
        bg_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter()
        self.list_panel = SlotListPanel(self.show_stats, self.change_folder)
        self.stats_panel = StatsPanel()
        splitter.addWidget(self.list_panel)
        splitter.addWidget(self.stats_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([480, 720])
        bg_layout.addWidget(splitter)

        self.refresh_slots()

    def refresh_slots(self):
        slots = save_finder.find_all_slots()
        if not slots:
            self.change_folder(auto_failed=True)
            return
        self._apply_slots(slots)

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
        self._apply_slots(slots)

    def _apply_slots(self, slots):
        slots_with_summary = [
            (slot, mgs4save.read_metadata_summary(slot.metadata_sav)) for slot in slots
        ]
        self.list_panel.set_slots(slots_with_summary)

    def show_stats(self, slot):
        self.stats_panel.show_slot(slot)


def main():
    app = QApplication(sys.argv)
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
