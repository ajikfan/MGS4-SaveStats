"""Interface graphique MGS4 Save Stats (PySide6).

Detection automatique des saves, liste des slots, detail des stats par
slot. Lecture seule : aucune ecriture dans les fichiers de save.
"""

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont, QIcon
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
    QStackedWidget,
    QFileDialog,
    QMessageBox,
    QFrame,
    QScrollArea,
)

import mgs4save
import save_finder

THEME_BACKGROUND = os.path.join(os.path.dirname(__file__), "themes", "background.jpg")

STAT_GROUPS = [
    (
        "Combat",
        [
            ("kills_total", "Kills"),
            ("headshots", "Headshots"),
            ("ko_couteau", "KO au couteau"),
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
            ("temps_accroupi_frames", "Temps accroupi"),
            ("temps_allonge_frames", "Temps allongé"),
            ("temps_mur_frames", "Temps contre un mur"),
            ("temps_carton_frames", "Temps carton/baril"),
        ],
    ),
    (
        "Divers",
        [
            ("soins_utilises", "Objets de soin utilisés"),
            ("objets_donnes_milices", "Objets donnés aux milices"),
            ("pages_magazine_tournees", "Pages de magazine tournées"),
            ("objets_speciaux_bitmask", "Objets spéciaux (bitmask)"),
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


FRAME_FIELDS = {
    "temps_accroupi_frames",
    "temps_allonge_frames",
    "temps_mur_frames",
    "temps_carton_frames",
}

# Ratio frames/seconde observe (framerate variable, voir notes.md) : ~60 pour
# accroupi, 55-62 pour les autres. 60 est une bonne approximation partout.
FRAMES_PER_SECOND = 60


def seconds_to_hms(seconds: int) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def frames_to_hms_approx(frames: int) -> str:
    return "≈ " + seconds_to_hms(frames / FRAMES_PER_SECOND)


DARK_QSS = """
QMainWindow, QWidget#root { background-color: #0b0b0c; }
QLabel { color: #d8d8d8; }
QLabel#title { color: #f0f0f0; font-size: 20px; font-weight: 600; letter-spacing: 1px; }
QLabel#groupTitle { color: #c9a24b; font-size: 13px; font-weight: 700; letter-spacing: 2px; }
QLabel#statLabel { color: #9a9a9a; font-size: 12px; }
QLabel#statValue { color: #f0f0f0; font-size: 14px; font-weight: 600; }
QListWidget { background: transparent; border: none; }
QListWidget::item { background: rgba(20,20,22,190); border: 1px solid rgba(255,255,255,30); margin: 4px 8px; padding: 6px; }
QListWidget::item:selected { border: 1px solid #c9a24b; background: rgba(40,35,20,200); }
QPushButton { background: rgba(255,255,255,20); color: #e8e8e8; border: 1px solid rgba(255,255,255,60); padding: 6px 14px; }
QPushButton:hover { background: rgba(255,255,255,40); }
QFrame#card { background: rgba(15,15,17,170); border: 1px solid rgba(255,255,255,25); }
"""


class BackgroundWidget(QWidget):
    """Widget racine qui dessine une image de fond si disponible, sinon un
    simple aplat sombre. L'image n'est jamais fournie avec le projet (voir
    themes/README.md) : chacun met la sienne."""

    def __init__(self):
        super().__init__()
        self._pixmap = QPixmap(THEME_BACKGROUND) if os.path.isfile(THEME_BACKGROUND) else None

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor

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


class SlotListPage(QWidget):
    def __init__(self, on_select, on_change_folder):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)

        title = QLabel("METAL GEAR SOLID 4 — STATS DE SAUVEGARDE")
        title.setObjectName("title")
        layout.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.setIconSize(self.list_widget.iconSize() * 3)
        self.list_widget.itemActivated.connect(lambda item: on_select(item.data(Qt.UserRole)))
        layout.addWidget(self.list_widget)

        bottom = QHBoxLayout()
        change_btn = QPushButton("Changer de dossier de sauvegarde…")
        change_btn.clicked.connect(on_change_folder)
        bottom.addWidget(change_btn)
        bottom.addStretch()
        layout.addLayout(bottom)

    def set_slots(self, slots_with_summary):
        self.list_widget.clear()
        for slot, summary in slots_with_summary:
            label = (
                f"{summary['difficulte_nom']}  —  Partie n°{summary['numero_partie']}\n"
                f"Temps de jeu : {seconds_to_hms(summary['playtime_secondes'])}    "
                f"Drebin : {summary['drebin_actuel']}"
            )
            item = QListWidgetItem(label)
            if os.path.isfile(slot.icon_png):
                item.setIcon(QIcon(slot.icon_png))
            item.setData(Qt.UserRole, slot)
            self.list_widget.addItem(item)


class DetailPage(QWidget):
    def __init__(self, on_back):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(30, 24, 30, 24)

        header = QHBoxLayout()
        back_btn = QPushButton("← Retour")
        back_btn.clicked.connect(on_back)
        header.addWidget(back_btn)
        self.title = QLabel("")
        self.title.setObjectName("title")
        header.addWidget(self.title)
        header.addStretch()
        outer.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        content = QWidget()
        self.grid = QGridLayout(content)
        self.grid.setSpacing(16)
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def show_slot(self, slot):
        while self.grid.count():
            child = self.grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        stats = mgs4save.read_stats(slot.mgs4_sav)
        meta = mgs4save.read_metadata_summary(slot.metadata_sav)
        self.title.setText(f"{meta['difficulte_nom']} — Partie n°{meta['numero_partie']}")

        col = 0
        for group_name, fields in STAT_GROUPS:
            card = QFrame()
            card.setObjectName("card")
            card_layout = QVBoxLayout(card)
            group_title = QLabel(group_name.upper())
            group_title.setObjectName("groupTitle")
            card_layout.addWidget(group_title)
            for key, label in fields:
                value = stats.get(key, "—")
                if key in FRAME_FIELDS:
                    value = frames_to_hms_approx(value)
                row = QHBoxLayout()
                name_label = QLabel(label)
                name_label.setObjectName("statLabel")
                value_label = QLabel(str(value))
                value_label.setObjectName("statValue")
                row.addWidget(name_label)
                row.addStretch()
                row.addWidget(value_label)
                card_layout.addLayout(row)
            self.grid.addWidget(card, 0, col)
            col += 1

        # temps de jeu total, a part car il vient de METADATA.SAV, pas MGS4.SAV
        playtime_card = QFrame()
        playtime_card.setObjectName("card")
        pc_layout = QVBoxLayout(playtime_card)
        pc_title = QLabel("TEMPS DE JEU")
        pc_title.setObjectName("groupTitle")
        pc_layout.addWidget(pc_title)
        pt_row = QHBoxLayout()
        pt_row.addWidget(self._label("Temps de jeu total (± 30s)", "statLabel"))
        pt_row.addStretch()
        pt_row.addWidget(self._label(seconds_to_hms(meta["playtime_secondes"]), "statValue"))
        pc_layout.addLayout(pt_row)
        self.grid.addWidget(playtime_card, 1, 0)

    @staticmethod
    def _label(text, object_name):
        label = QLabel(text)
        label.setObjectName(object_name)
        return label


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MGS4 Save Stats")
        self.resize(1000, 700)

        self.background = BackgroundWidget()
        self.background.setObjectName("root")
        self.setCentralWidget(self.background)
        bg_layout = QVBoxLayout(self.background)
        bg_layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        bg_layout.addWidget(self.stack)

        self.list_page = SlotListPage(self.show_detail, self.change_folder)
        self.detail_page = DetailPage(self.show_list)
        self.stack.addWidget(self.list_page)
        self.stack.addWidget(self.detail_page)

        self.refresh_slots()

    def refresh_slots(self):
        slots = save_finder.find_all_slots()
        if not slots:
            self.change_folder(auto_failed=True)
            return
        slots_with_summary = [
            (slot, mgs4save.read_metadata_summary(slot.metadata_sav)) for slot in slots
        ]
        self.list_page.set_slots(slots_with_summary)

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
        slots_with_summary = [
            (slot, mgs4save.read_metadata_summary(slot.metadata_sav)) for slot in slots
        ]
        self.list_page.set_slots(slots_with_summary)
        self.stack.setCurrentWidget(self.list_page)

    def show_detail(self, slot):
        self.detail_page.show_slot(slot)
        self.stack.setCurrentWidget(self.detail_page)

    def show_list(self):
        self.stack.setCurrentWidget(self.list_page)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_QSS)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
