"""
Disk Scheduling Simulator — PyQt6 Edition
==========================================
Simulates and visualizes six classical disk scheduling algorithms:
FCFS, SSTF, SCAN, C-SCAN, LOOK, and C-LOOK.

Requirements:
    pip install PyQt6 matplotlib

Run:
    python disk_scheduling_pyqt6.py
"""

import sys
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QComboBox, QTableWidget, QTableWidgetItem,
    QGroupBox, QMessageBox, QHeaderView, QRadioButton, QButtonGroup, QSplitter
)
from PyQt6.QtCore import Qt


# --------------------------------------------------------------------------
# Algorithm implementations
# --------------------------------------------------------------------------

def fcfs(requests, head, **kwargs):
    order = requests[:]
    seq = [head] + order
    total = sum(abs(seq[i + 1] - seq[i]) for i in range(len(seq) - 1))
    return order, total


def sstf(requests, head, **kwargs):
    pending = requests[:]
    order = []
    cur = head
    total = 0
    while pending:
        nearest = min(pending, key=lambda r: abs(r - cur))
        total += abs(nearest - cur)
        cur = nearest
        order.append(nearest)
        pending.remove(nearest)
    return order, total


def scan(requests, head, disk_size=200, direction="up", **kwargs):
    reqs = sorted(requests)
    upper = [r for r in reqs if r >= head]
    lower = [r for r in reqs if r < head]
    if direction == "up":
        path = upper + [disk_size - 1] + list(reversed(lower))
    else:
        path = list(reversed(lower)) + [0] + upper
    order, total, cur = [], 0, head
    for pos in path:
        total += abs(pos - cur)
        cur = pos
        if pos in requests:
            order.append(pos)
    return order, total


def c_scan(requests, head, disk_size=200, direction="up", **kwargs):
    reqs = sorted(requests)
    upper = [r for r in reqs if r >= head]
    lower = [r for r in reqs if r < head]
    if direction == "up":
        path = upper + [disk_size - 1, 0] + lower
    else:
        path = list(reversed(lower)) + [0, disk_size - 1] + list(reversed(upper))
    order, total, cur = [], 0, head
    for pos in path:
        total += abs(pos - cur)
        cur = pos
        if pos in requests:
            order.append(pos)
    return order, total


def look(requests, head, direction="up", **kwargs):
    reqs = sorted(requests)
    upper = [r for r in reqs if r >= head]
    lower = [r for r in reqs if r < head]
    path = upper + list(reversed(lower)) if direction == "up" else list(reversed(lower)) + upper
    order, total, cur = [], 0, head
    for pos in path:
        total += abs(pos - cur)
        cur = pos
        order.append(pos)
    return order, total


def c_look(requests, head, direction="up", **kwargs):
    reqs = sorted(requests)
    upper = [r for r in reqs if r >= head]
    lower = [r for r in reqs if r < head]
    path = upper + lower if direction == "up" else list(reversed(lower)) + list(reversed(upper))
    order, total, cur = [], 0, head
    for pos in path:
        total += abs(pos - cur)
        cur = pos
        order.append(pos)
    return order, total


ALGORITHMS = {
    "FCFS": fcfs,
    "SSTF": sstf,
    "SCAN": scan,
    "C-SCAN": c_scan,
    "LOOK": look,
    "C-LOOK": c_look,
}


# --------------------------------------------------------------------------
# Shared "textbook style" plot: a horizontal cylinder ruler at the top with
# a diagonal zig-zag trace descending as the head services each request,
# in the style of classic OS-textbook disk scheduling diagrams.
# --------------------------------------------------------------------------

def draw_zigzag_trace(ax, name, head, order, disk_size, total=None, color="#2F5597"):
    positions = [head] + order
    steps = list(range(len(positions)))

    ax.plot(positions, steps, marker="o", color=color, linewidth=2)
    for i, pos in enumerate(positions):
        ax.annotate(str(pos), (pos, steps[i]), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=8)

    ax.invert_yaxis()  # service order 0 at the top, increasing downward
    ax.set_xlim(-disk_size * 0.03, disk_size * 1.03)

    title = f"Head Movement Trace — {name}"
    if total is not None:
        title += f"  (Total: {total})"
    ax.set_title(title, fontsize=10, pad=8)
    ax.set_xlabel("Cylinder")
    ax.set_ylabel("Service Order")
    ax.grid(True, linestyle="--", alpha=0.5)


# --------------------------------------------------------------------------
# Main window
# --------------------------------------------------------------------------

class DiskSchedulerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Disk Scheduling Simulator — PyQt6")
        self.resize(1100, 700)
        self._build_ui()

    # ---- UI construction -------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        # ---- Left panel: inputs + results table ----
        left = QWidget()
        left_layout = QVBoxLayout(left)

        input_box = QGroupBox("Simulation Parameters")
        form = QFormLayout()
        self.disk_size_edit = QLineEdit("200")
        self.head_edit = QLineEdit("53")
        self.requests_edit = QLineEdit("98, 183, 37, 122, 14, 124, 65, 67")
        form.addRow("Disk size (cylinders):", self.disk_size_edit)
        form.addRow("Initial head position:", self.head_edit)
        form.addRow("Request queue (comma-separated):", self.requests_edit)

        dir_row = QHBoxLayout()
        self.dir_group = QButtonGroup(self)
        self.dir_up = QRadioButton("Up (toward higher cylinders)")
        self.dir_down = QRadioButton("Down (toward lower cylinders)")
        self.dir_up.setChecked(True)
        self.dir_group.addButton(self.dir_up)
        self.dir_group.addButton(self.dir_down)
        dir_row.addWidget(self.dir_up)
        dir_row.addWidget(self.dir_down)
        form.addRow("Direction (SCAN family):", dir_row)

        self.algo_combo = QComboBox()
        self.algo_combo.addItems(list(ALGORITHMS.keys()))
        form.addRow("Algorithm:", self.algo_combo)

        input_box.setLayout(form)
        left_layout.addWidget(input_box)

        btn_row = QHBoxLayout()
        self.run_btn = QPushButton("Run Selected Algorithm")
        self.run_btn.clicked.connect(self.run_selected)
        self.compare_btn = QPushButton("Compare All Algorithms")
        self.compare_btn.clicked.connect(self.compare_all)
        btn_row.addWidget(self.run_btn)
        btn_row.addWidget(self.compare_btn)
        left_layout.addLayout(btn_row)

        self.summary_label = QLabel("Run a simulation to see results.")
        self.summary_label.setWordWrap(True)
        left_layout.addWidget(self.summary_label)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Algorithm", "Total Head Movement"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        left_layout.addWidget(self.table)

        left.setMaximumWidth(430)
        root.addWidget(left)

        # ---- Right panel: matplotlib chart ----
        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.figure = Figure(figsize=(6, 5))
        self.canvas = FigureCanvas(self.figure)
        right_layout.addWidget(self.canvas)
        root.addWidget(right)

    # ---- Helpers -----------------------------------------------------

    def _parse_inputs(self):
        try:
            disk_size = int(self.disk_size_edit.text())
            head = int(self.head_edit.text())
            requests = [int(x.strip()) for x in self.requests_edit.text().split(",") if x.strip() != ""]
        except ValueError:
            raise ValueError("Disk size, head position, and requests must be integers.")
        if not requests:
            raise ValueError("Request queue cannot be empty.")
        if head < 0 or head >= disk_size:
            raise ValueError("Head position must lie within [0, disk_size - 1].")
        for r in requests:
            if r < 0 or r >= disk_size:
                raise ValueError(f"Request {r} lies outside the valid range [0, {disk_size - 1}].")
        direction = "up" if self.dir_up.isChecked() else "down"
        return disk_size, head, requests, direction

    def _plot_single(self, name, head, order, disk_size, total):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        draw_zigzag_trace(ax, name, head, order, disk_size, total=total)
        self.figure.tight_layout()
        self.canvas.draw()

    def _plot_comparison(self, results, head, disk_size):
        self.figure.clear()
        names = list(results.keys())
        for i, name in enumerate(names):
            order, total = results[name]
            ax = self.figure.add_subplot(2, 3, i + 1)
            draw_zigzag_trace(ax, name, head, order, disk_size, total=total)
        self.figure.suptitle("Head Movement Comparison — All Algorithms", fontsize=12)
        self.figure.tight_layout(rect=[0, 0, 1, 0.95])
        self.canvas.draw()

    # ---- Button actions -------------------------------------------------

    def run_selected(self):
        try:
            disk_size, head, requests, direction = self._parse_inputs()
        except ValueError as e:
            QMessageBox.warning(self, "Invalid input", str(e))
            return

        name = self.algo_combo.currentText()
        func = ALGORITHMS[name]
        order, total = func(requests, head, disk_size=disk_size, direction=direction)

        self.summary_label.setText(
            f"<b>{name}</b> — Service order: {order}<br>Total head movement: <b>{total}</b> cylinders"
        )
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem(name))
        self.table.setItem(0, 1, QTableWidgetItem(str(total)))
        self._plot_single(name, head, order, disk_size, total)

    def compare_all(self):
        try:
            disk_size, head, requests, direction = self._parse_inputs()
        except ValueError as e:
            QMessageBox.warning(self, "Invalid input", str(e))
            return

        results = {}
        for name, func in ALGORITHMS.items():
            order, total = func(requests, head, disk_size=disk_size, direction=direction)
            results[name] = (order, total)

        best = min(results, key=lambda n: results[n][1])
        self.summary_label.setText(
            f"Compared all 6 algorithms on queue {requests} from head {head}.<br>"
            f"Best (lowest total movement): <b>{best}</b> ({results[best][1]} cylinders)"
        )

        self.table.setRowCount(len(results))
        for row, (name, (order, total)) in enumerate(results.items()):
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(str(total)))

        self._plot_comparison(results, head, disk_size)


def main():
    app = QApplication(sys.argv)
    window = DiskSchedulerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()