"""
Disk Scheduling + Virtual File System Simulator — PyQt6 Edition
==================================================================
Tab 1 "Disk Scheduler": simulates and visualizes six classical disk
scheduling algorithms (FCFS, SSTF, SCAN, C-SCAN, LOOK, C-LOOK).

Tab 2 "Virtual File System": a mock VFS driven by a small command-line
interface (mkdir, touch, ls, cd, rm, write, cat, tree, diskmap, format).
Every file is allocated a set of simulated disk blocks (cylinders) on
creation/growth. Running `cat <file>` treats that file's block list as
a disk-scheduler request queue, switches to the Disk Scheduler tab, and
plots the resulting head-movement trace — closing the loop between the
file system and the disk scheduler, end to end.

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
    QGroupBox, QMessageBox, QHeaderView, QRadioButton, QButtonGroup, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QTextEdit
)


# --------------------------------------------------------------------------
# Disk scheduling algorithm implementations
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
# Shared plot helper: cylinder on the x-axis, service order on the y-axis
# (0 at top, increasing downward), line + markers + value labels.
# --------------------------------------------------------------------------

def draw_zigzag_trace(ax, name, head, order, disk_size, total=None, color="#2F5597"):
    positions = [head] + order
    steps = list(range(len(positions)))

    ax.plot(positions, steps, marker="o", color=color, linewidth=2)
    for i, pos in enumerate(positions):
        ax.annotate(str(pos), (pos, steps[i]), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=8)

    ax.invert_yaxis()
    ax.set_xlim(-disk_size * 0.03, disk_size * 1.03)

    title = f"Head Movement Trace — {name}"
    if total is not None:
        title += f"  (Total: {total})"
    ax.set_title(title, fontsize=10, pad=8)
    ax.set_xlabel("Cylinder")
    ax.set_ylabel("Service Order")
    ax.grid(True, linestyle="--", alpha=0.5)


# --------------------------------------------------------------------------
# Virtual File System
# --------------------------------------------------------------------------

UNIT_CHARS_PER_BLOCK = 8  # simulated: every 8 characters of content consumes one disk block

HELP_TEXT = """Available commands:
  pwd                        show current directory
  ls                         list contents of current directory
  mkdir <name>                create a subdirectory
  cd <name|..|/>              change directory
  touch <name> [blocks]       create an empty file (default 1 block)
  write <name> <text...>      write text to a file (grows allocation as needed)
  cat <name> [--all]          "read" a file — services its blocks with the disk
                               scheduler (current algorithm, or --all to compare all)
  rm <name>                   delete an empty directory or a file
  tree                        print the whole directory tree
  diskmap                     show the free/used block bitmap
  format [size]                erase everything and reformat the disk
  clear                        clear the console
  help                          show this message"""


class VFSError(Exception):
    pass


class VFSNode:
    def __init__(self, name, is_dir=True, parent=None):
        self.name = name
        self.is_dir = is_dir
        self.parent = parent
        self.children = {} if is_dir else None
        self.blocks = [] if not is_dir else None
        self.content = "" if not is_dir else None


class VirtualFileSystem:
    def __init__(self, disk_size=200):
        self.disk_size = disk_size
        self.free_bitmap = [True] * disk_size
        self.root = VFSNode("/", is_dir=True)
        self.cwd = self.root

    # ---- block allocation -----------------------------------------------

    def _find_free_blocks(self, count):
        n = self.disk_size
        free = self.free_bitmap
        run_start, run_len = None, 0
        for i in range(n):
            if free[i]:
                if run_start is None:
                    run_start = i
                run_len += 1
                if run_len == count:
                    return list(range(run_start, run_start + count))
            else:
                run_start, run_len = None, 0
        scattered = [i for i in range(n) if free[i]]
        if len(scattered) >= count:
            return scattered[:count]
        return None

    # ---- navigation -------------------------------------------------------

    def path_string(self):
        parts = []
        node = self.cwd
        while node.parent is not None:
            parts.append(node.name)
            node = node.parent
        return "/" + "/".join(reversed(parts))

    def cd(self, name):
        if name == "..":
            if self.cwd.parent is not None:
                self.cwd = self.cwd.parent
            return
        if name in ("/", ""):
            self.cwd = self.root
            return
        target = self.cwd.children.get(name)
        if target is None or not target.is_dir:
            raise VFSError(f"No such directory: {name}")
        self.cwd = target

    # ---- file / directory operations --------------------------------------

    def mkdir(self, name):
        if name in self.cwd.children:
            raise VFSError(f"'{name}' already exists")
        self.cwd.children[name] = VFSNode(name, is_dir=True, parent=self.cwd)

    def touch(self, name, size=1):
        if name in self.cwd.children:
            raise VFSError(f"'{name}' already exists")
        blocks = self._find_free_blocks(size)
        if blocks is None:
            raise VFSError("Not enough free disk space")
        for b in blocks:
            self.free_bitmap[b] = False
        node = VFSNode(name, is_dir=False, parent=self.cwd)
        node.blocks = blocks
        node.content = ""
        self.cwd.children[name] = node
        return node

    def rm(self, name):
        node = self.cwd.children.get(name)
        if node is None:
            raise VFSError(f"No such file or directory: {name}")
        if node.is_dir and node.children:
            raise VFSError(f"Directory '{name}' is not empty")
        if not node.is_dir:
            for b in node.blocks:
                self.free_bitmap[b] = True
        del self.cwd.children[name]

    def write(self, name, text):
        node = self.cwd.children.get(name)
        if node is None or node.is_dir:
            raise VFSError(f"No such file: {name}")
        needed = max(1, (len(text) // UNIT_CHARS_PER_BLOCK) + 1)
        if needed > len(node.blocks):
            extra = needed - len(node.blocks)
            new_blocks = self._find_free_blocks(extra)
            if new_blocks is None:
                raise VFSError("Not enough free disk space to grow file")
            for b in new_blocks:
                self.free_bitmap[b] = False
            node.blocks.extend(new_blocks)
        node.content = text
        return node

    def read(self, name):
        node = self.cwd.children.get(name)
        if node is None or node.is_dir:
            raise VFSError(f"No such file: {name}")
        return node

    def ls(self):
        return sorted(self.cwd.children.items())

    def tree_string(self):
        lines = ["/"]

        def walk(node, prefix):
            items = sorted(node.children.items())
            for i, (name, child) in enumerate(items):
                connector = "└── " if i == len(items) - 1 else "├── "
                if child.is_dir:
                    lines.append(f"{prefix}{connector}{name}/")
                    extension = "    " if i == len(items) - 1 else "│   "
                    walk(child, prefix + extension)
                else:
                    lines.append(f"{prefix}{connector}{name}  (blocks: {child.blocks})")

        walk(self.root, "")
        return "\n".join(lines)

    def diskmap_string(self):
        return "".join("░" if f else "█" for f in self.free_bitmap)

    def format(self, size):
        self.disk_size = size
        self.free_bitmap = [True] * size
        self.root = VFSNode("/", is_dir=True)
        self.cwd = self.root


# --------------------------------------------------------------------------
# Main window
# --------------------------------------------------------------------------

class DiskSchedulerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Disk Scheduling + Virtual File System Simulator — PyQt6")
        self.resize(1250, 750)
        self.vfs = VirtualFileSystem(disk_size=200)
        self._build_ui()

    # ---- top-level UI ------------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_scheduler_tab(), "Disk Scheduler")
        self.tabs.addTab(self._build_vfs_tab(), "Virtual File System")
        layout.addWidget(self.tabs)

    # ---- Tab 1: Disk Scheduler ----------------------------------------------

    def _build_scheduler_tab(self):
        tab = QWidget()
        root = QHBoxLayout(tab)

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

        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.figure = Figure(figsize=(6, 5))
        self.canvas = FigureCanvas(self.figure)
        right_layout.addWidget(self.canvas)
        root.addWidget(right)

        return tab

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

    # ---- Tab 2: Virtual File System -------------------------------------

    def _build_vfs_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Directory Structure"))
        self.vfs_tree = QTreeWidget()
        self.vfs_tree.setHeaderHidden(True)
        left_layout.addWidget(self.vfs_tree)
        left.setMaximumWidth(320)
        layout.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet(
            "background-color:#1e1e1e; color:#d4d4d4; font-family: Consolas, monospace; font-size: 11pt;"
        )
        right_layout.addWidget(self.console)

        input_row = QHBoxLayout()
        self.vfs_prompt_label = QLabel("/>")
        self.vfs_input = QLineEdit()
        self.vfs_input.returnPressed.connect(self._vfs_submit)
        input_row.addWidget(self.vfs_prompt_label)
        input_row.addWidget(self.vfs_input)
        right_layout.addLayout(input_row)
        layout.addWidget(right)

        self._refresh_vfs_tree()
        self._vfs_print(
            "Virtual File System ready. Type 'help' for a list of commands.\n" + HELP_TEXT
        )
        return tab

    def _refresh_vfs_tree(self):
        self.vfs_tree.clear()
        root_item = QTreeWidgetItem(["/"])
        self.vfs_tree.addTopLevelItem(root_item)
        self._populate_tree_item(root_item, self.vfs.root)
        root_item.setExpanded(True)

    def _populate_tree_item(self, item, node):
        for name, child in sorted(node.children.items()):
            if child.is_dir:
                child_item = QTreeWidgetItem([f"\U0001F4C1 {name}"])
                item.addChild(child_item)
                self._populate_tree_item(child_item, child)
                child_item.setExpanded(True)
            else:
                child_item = QTreeWidgetItem([f"\U0001F4C4 {name}  (blocks: {child.blocks})"])
                item.addChild(child_item)

    def _vfs_print(self, text):
        if text is not None and text != "":
            self.console.append(text)

    def _vfs_submit(self):
        cmd_text = self.vfs_input.text()
        if cmd_text.strip() == "":
            return
        self.console.append(f"{self.vfs.path_string()} $ {cmd_text}")
        output = self._vfs_execute(cmd_text)
        self._vfs_print(output)
        self.vfs_prompt_label.setText(f"{self.vfs.path_string()}>")
        self.vfs_input.clear()

    def _vfs_execute(self, raw):
        parts = raw.strip().split()
        if not parts:
            return ""
        cmd, args = parts[0].lower(), parts[1:]
        try:
            if cmd == "help":
                return HELP_TEXT
            if cmd == "pwd":
                return self.vfs.path_string()
            if cmd == "ls":
                entries = self.vfs.ls()
                if not entries:
                    return "(empty directory)"
                lines = []
                for name, node in entries:
                    if node.is_dir:
                        lines.append(f"[DIR]  {name}")
                    else:
                        lines.append(f"[FILE] {name}  blocks={node.blocks}")
                return "\n".join(lines)
            if cmd == "mkdir":
                if not args:
                    return "Usage: mkdir <name>"
                self.vfs.mkdir(args[0])
                self._refresh_vfs_tree()
                return f"Directory '{args[0]}' created."
            if cmd == "cd":
                if not args:
                    return "Usage: cd <name|..|/>"
                self.vfs.cd(args[0])
                return f"Now in {self.vfs.path_string()}"
            if cmd == "touch":
                if not args:
                    return "Usage: touch <name> [blocks]"
                size = int(args[1]) if len(args) > 1 else 1
                node = self.vfs.touch(args[0], size)
                self._refresh_vfs_tree()
                return f"File '{args[0]}' created — allocated blocks {node.blocks}."
            if cmd == "rm":
                if not args:
                    return "Usage: rm <name>"
                self.vfs.rm(args[0])
                self._refresh_vfs_tree()
                return f"'{args[0]}' removed."
            if cmd == "write":
                if len(args) < 2:
                    return "Usage: write <file> <text...>"
                name, text = args[0], " ".join(args[1:])
                node = self.vfs.write(name, text)
                self._refresh_vfs_tree()
                return f"Wrote {len(text)} chars to '{name}'. Blocks now: {node.blocks}"
            if cmd in ("cat", "read"):
                if not args:
                    return "Usage: cat <file> [--all]"
                name = args[0]
                node = self.vfs.read(name)
                return self._simulate_file_access(name, node, all_algos="--all" in args)
            if cmd == "tree":
                return self.vfs.tree_string()
            if cmd == "diskmap":
                return (
                    f"Disk map ({self.vfs.disk_size} blocks, \u2588=used \u2591=free):\n"
                    f"{self.vfs.diskmap_string()}"
                )
            if cmd == "format":
                size = int(args[0]) if args else self.vfs.disk_size
                self.vfs.format(size)
                self.disk_size_edit.setText(str(size))
                self._refresh_vfs_tree()
                return f"Disk reformatted with {size} cylinders. All files erased."
            if cmd == "clear":
                self.console.clear()
                return ""
            return f"Unknown command: '{cmd}'. Type 'help' for a list of commands."
        except VFSError as e:
            return f"Error: {e}"
        except ValueError:
            return "Error: expected a number where a number was required."

    def _simulate_file_access(self, name, node, all_algos):
        if not node.blocks:
            return f"'{name}' has no allocated blocks."
        try:
            int(self.head_edit.text())
            int(self.disk_size_edit.text())
        except ValueError:
            return "The Disk Scheduler tab has an invalid head position / disk size."

        self.requests_edit.setText(", ".join(str(b) for b in node.blocks))
        self.tabs.setCurrentIndex(0)
        if all_algos:
            self.compare_all()
            return (
                f"Reading '{name}' triggered disk access to blocks {node.blocks}.\n"
                f"Compared all six algorithms — see the Disk Scheduler tab."
            )
        self.run_selected()
        algo = self.algo_combo.currentText()
        return (
            f"Reading '{name}' triggered disk access to blocks {node.blocks}.\n"
            f"Serviced using {algo} — see the Disk Scheduler tab for the trace."
        )


def main():
    app = QApplication(sys.argv)
    window = DiskSchedulerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()