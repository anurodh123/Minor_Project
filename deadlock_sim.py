import sys
import time
import random
import math
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, 
                             QPushButton, QComboBox, QSpinBox, QTextEdit, QMessageBox, 
                             QGroupBox, QListWidget, QListWidgetItem, QGridLayout, QGraphicsView, QGraphicsScene)
from PyQt6.QtCore import Qt, QPointF, QCoreApplication
from PyQt6.QtGui import QColor, QPen, QBrush, QPainter, QFont, QPolygonF

# =====================================================================
# BACKEND CORE LOGIC
# =====================================================================
class BankersAlgorithm:
    def __init__(self, num_processes, num_resources, available, max_matrix, allocation):
        self.num_processes = num_processes
        self.num_resources = num_resources
        self.available = list(available)
        self.max_matrix = [list(row) for row in max_matrix]
        self.allocation = [list(row) for row in allocation]
        self.calculate_need_matrix()

    def calculate_need_matrix(self):
        self.need = []
        for i in range(self.num_processes):
            row = []
            for j in range(self.num_resources):
                row.append(self.max_matrix[i][j] - self.allocation[i][j])
            self.need.append(row)

    def add_resource_type(self):
        self.num_resources += 1
        self.available.append(random.randint(2, 5))
        for i in range(self.num_processes):
            self.max_matrix[i].append(random.randint(2, 6))
            self.allocation[i].append(random.randint(0, 1))
        self.calculate_need_matrix()

    def remove_resource_type(self, res_idx):
        if self.num_resources > 1 and 0 <= res_idx < self.num_resources:
            self.available.pop(res_idx)
            for i in range(self.num_processes):
                self.max_matrix[i].pop(res_idx)
                self.allocation[i].pop(res_idx)
            self.num_resources -= 1
            self.calculate_need_matrix()
            return True
        return False

    def add_process(self):
        new_max = [random.randint(3, 7) for _ in range(self.num_resources)]
        new_alloc = [random.randint(0, 1) for _ in range(self.num_resources)]
        self.max_matrix.append(new_max)
        self.allocation.append(new_alloc)
        self.num_processes += 1
        self.calculate_need_matrix()

    def remove_targeted_process(self, proc_id):
        if self.num_processes > 1 and 0 <= proc_id < self.num_processes:
            target_alloc = self.allocation[proc_id]
            for j in range(self.num_resources):
                self.available[j] += target_alloc[j]
            self.max_matrix.pop(proc_id)
            self.allocation.pop(proc_id)
            self.num_processes -= 1
            self.calculate_need_matrix()
            return True
        return False

    def get_ready_candidates(self, work, finish):
        """Returns the indices of all not-yet-finished processes whose need
        can be satisfied by the given `work` vector right now. When this
        list has more than one entry, the safety check has hit a genuine
        tie -- more than one process could legally go next, and the caller
        (interactive UI or auto tie-break rule) decides which one runs."""
        candidates = []
        for i in range(self.num_processes):
            if not finish[i]:
                if all(self.need[i][j] <= work[j] for j in range(self.num_resources)):
                    candidates.append(i)
        return candidates

    def check_safety_state(self, scan_reverse=False):
        """
        Runs the Banker's Algorithm safety check.

        scan_reverse=False -> at each round, processes are considered in
            ascending order (P0, P1, ..., Pn-1). Ties (multiple processes
            executable in the same round) resolve in favor of the LOWER
            index, so sequences tend to start from P0's side.
        scan_reverse=True -> processes are considered in descending order
            (Pn-1, ..., P1, P0). Ties resolve in favor of the HIGHER
            index, so sequences tend to start from P4's side.

        Both directions are mathematically valid; the Banker's Algorithm
        only guarantees *a* safe sequence exists, not a unique one. This
        option just lets you reproduce whichever tie-breaking convention
        a particular textbook example used.
        """
        work = list(self.available)
        finish = [False] * self.num_processes
        safe_sequence = []

        scan_range = range(self.num_processes - 1, -1, -1) if scan_reverse else range(self.num_processes)

        while len(safe_sequence) < self.num_processes:
            found_executable_process = False
            for i in scan_range:
                if not finish[i]:
                    can_execute = True
                    for j in range(self.num_resources):
                        if self.need[i][j] > work[j]:
                            can_execute = False
                            break
                    
                    if can_execute:
                        for j in range(self.num_resources):
                            work[j] += self.allocation[i][j]
                        finish[i] = True
                        safe_sequence.append(i)
                        found_executable_process = True
                        break
            
            if not found_executable_process:
                return False, []
        return True, safe_sequence


class OSKernel:
    def __init__(self, bankers_engine, log_widget):
        self.kernel_space_engine = bankers_engine
        self.log_widget = log_widget
        self.log_kernel_event("BOOT", "Kernel subsystem initialized successfully.")

    def log_kernel_event(self, level, message):
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.log_widget.append(log_entry)


# =====================================================================
# FRONTEND DESKTOP INTERFACE
# =====================================================================
class DeadlockSimWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advanced Concurrency & Deadlock Engine")
        self.setGeometry(50, 50, 1450, 850)

        init_avail = [3, 3, 2]
        max_demand = [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]]
        current_alloc = [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]]
        self.engine = BankersAlgorithm(5, 3, init_avail, max_demand, current_alloc)
        self.dynamic_spinboxes = [] 
        self.history_snapshots = []  # Stores full-state snapshots, index-aligned with history_list_widget rows

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)

        self.init_ui()
        self.kernel = OSKernel(self.engine, self.log_area)
        
        self.sync_combobox_items()
        self.rebuild_dynamic_spinboxes()
        self.update_gui_tables()
        self.load_current_matrix_values_to_spinboxes()
        self.save_history_entry("Initial baseline state")

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        outer_layout = QHBoxLayout(main_widget)

        left_dashboard = QVBoxLayout()
        outer_layout.addLayout(left_dashboard, stretch=4)

        matrix_layout = QHBoxLayout()
        
        avail_group = QGroupBox("Available Resources")
        avail_vbox = QVBoxLayout(avail_group)
        self.avail_table = QTableWidget(1, 3)
        self.avail_table.cellChanged.connect(self.handle_cell_edit)
        avail_vbox.addWidget(self.avail_table)
        matrix_layout.addWidget(avail_group)

        alloc_group = QGroupBox("Allocation Matrix")
        alloc_vbox = QVBoxLayout(alloc_group)
        self.alloc_table = QTableWidget(5, 3)
        self.alloc_table.cellChanged.connect(self.handle_cell_edit)
        alloc_vbox.addWidget(self.alloc_table)
        matrix_layout.addWidget(alloc_group)

        max_group = QGroupBox("Max Demand Matrix")
        max_vbox = QVBoxLayout(max_group)
        self.max_table = QTableWidget(5, 3)
        self.max_table.cellChanged.connect(self.handle_cell_edit)
        max_vbox.addWidget(self.max_table)
        matrix_layout.addWidget(max_group)

        need_group = QGroupBox("Calculated Need Matrix")
        need_vbox = QVBoxLayout(need_group)
        self.need_table = QTableWidget(5, 3)
        need_vbox.addWidget(self.need_table)
        matrix_layout.addWidget(need_group)

        left_dashboard.addLayout(matrix_layout)

        # Lifecycle Controls Panel
        scaling_group = QGroupBox("Process & Resource Lifecycle Management")
        scaling_hbox = QHBoxLayout(scaling_group)
        
        self.btn_add_proc = QPushButton("Add New Process")
        self.btn_add_proc.clicked.connect(self.handle_add_process)
        scaling_hbox.addWidget(self.btn_add_proc)

        self.btn_add_resource = QPushButton("Add Resource Column")
        self.btn_add_resource.clicked.connect(self.handle_add_resource)
        scaling_hbox.addWidget(self.btn_add_resource)

        scaling_hbox.addSpacing(15)
        scaling_hbox.addWidget(QLabel("Column:"))
        self.combo_drop_resource = QComboBox()
        scaling_hbox.addWidget(self.combo_drop_resource)
        
        self.btn_rem_resource = QPushButton("Delete Column")
        self.btn_rem_resource.clicked.connect(self.handle_remove_resource)
        scaling_hbox.addWidget(self.btn_rem_resource)

        scaling_hbox.addSpacing(25)
        scaling_hbox.addWidget(QLabel("Process:"))
        self.combo_kill_target = QComboBox()
        scaling_hbox.addWidget(self.combo_kill_target)
        
        self.btn_rem_proc = QPushButton("Delete Process")
        self.btn_rem_proc.clicked.connect(self.handle_remove_process)
        scaling_hbox.addWidget(self.btn_rem_proc)
        left_dashboard.addWidget(scaling_group)

        bottom_layout = QHBoxLayout()

        # CONFIGURATION EDITOR & MASTER SEQUENCE SIMULATOR
        ctrl_group = QGroupBox("Matrix Value & Control Center")
        ctrl_vbox = QVBoxLayout(ctrl_group)
        ctrl_vbox.setSpacing(10)

        ctrl_vbox.addWidget(QLabel("Select Target Component to Configure:"))
        
        mat_hbox = QHBoxLayout()
        mat_hbox.addWidget(QLabel("Matrix:"))
        self.combo_matrix_target = QComboBox()
        self.combo_matrix_target.addItems(["Available Resources", "Allocation Matrix", "Max Demand Matrix"])
        self.combo_matrix_target.currentIndexChanged.connect(self.handle_matrix_selection_change)
        mat_hbox.addWidget(self.combo_matrix_target)
        ctrl_vbox.addLayout(mat_hbox)

        self.proc_select_row_widget = QWidget()
        proc_hbox = QHBoxLayout(self.proc_select_row_widget)
        proc_hbox.setContentsMargins(0, 0, 0, 0)
        proc_hbox.addWidget(QLabel("Process:"))
        self.combo_proc_target = QComboBox()
        self.combo_proc_target.currentIndexChanged.connect(self.load_current_matrix_values_to_spinboxes)
        proc_hbox.addWidget(self.combo_proc_target)
        ctrl_vbox.addWidget(self.proc_select_row_widget)

        self.spinbox_container_widget = QWidget()
        self.spinbox_container_layout = QGridLayout(self.spinbox_container_widget)
        self.spinbox_container_layout.setContentsMargins(0, 5, 0, 5)
        ctrl_vbox.addWidget(self.spinbox_container_widget)

        self.btn_apply_values = QPushButton("Apply Matrix Values")
        self.btn_apply_values.clicked.connect(self.handle_apply_matrix_values)
        ctrl_vbox.addWidget(self.btn_apply_values)

        ctrl_vbox.addSpacing(15)

        scan_dir_hbox = QHBoxLayout()
        scan_dir_hbox.addWidget(QLabel("When Multiple Processes Are Ready:"))
        self.combo_scan_direction = QComboBox()
        self.combo_scan_direction.addItems([
            "Ask me which one to run",
            "Auto: Ascending (P0 -> Pn first)",
            "Auto: Descending (Pn -> P0 first)"
        ])
        self.combo_scan_direction.setToolTip(
            "The Banker's Algorithm often has more than one process that\n"
            "could legally run next in a given round. \"Ask me\" pauses the\n"
            "simulation and lets you pick (e.g. P0 vs P4), just like working\n"
            "it out by hand. The Auto options pick automatically by index\n"
            "order instead, without prompting."
        )
        scan_dir_hbox.addWidget(self.combo_scan_direction)
        ctrl_vbox.addLayout(scan_dir_hbox)

        # ... (find this part in your init_ui method)
        self.btn_safety = QPushButton("Execute Simulation")
        self.btn_safety.setStyleSheet("font-weight: bold; height: 32px;")
        self.btn_safety.clicked.connect(self.handle_safety_check)
        ctrl_vbox.addWidget(self.btn_safety) # <--- YOU HAVE THIS ALREADY

        # --- PASTE THE NEW CODE HERE ---
        self.outcome_group = QGroupBox("Simulation Outcome & Sequence")
        outcome_layout = QVBoxLayout(self.outcome_group)
        
        self.lbl_outcome_status = QLabel("Status: Waiting...")
        self.lbl_outcome_status.setStyleSheet("font-weight: bold; color: #bdc3c7;")
        self.lbl_sequence = QLabel("Sequence: -")
        self.lbl_sequence.setWordWrap(True)
        
        outcome_layout.addWidget(self.lbl_outcome_status)
        outcome_layout.addWidget(self.lbl_sequence)
        
        ctrl_vbox.addWidget(self.outcome_group) # Add it to your control panel layout
        # -------------------------------

        ctrl_vbox.addStretch(1)
        bottom_layout.addWidget(ctrl_group, stretch=1)

        # DYNAMIC RAG GRAPHICSVIEW PORT
        rag_group = QGroupBox("Resource Allocation Graph (RAG)")
        rag_vbox = QVBoxLayout(rag_group)
        self.rag_view = QGraphicsView()
        self.rag_scene = QGraphicsScene()
        self.rag_view.setScene(self.rag_scene)
        self.rag_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        self.rag_view.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        rag_vbox.addWidget(self.rag_view)
        bottom_layout.addWidget(rag_group, stretch=2)

        left_dashboard.addLayout(bottom_layout)

        # Right Sidebar Layout
        right_sidebar_layout = QVBoxLayout()
        outer_layout.addLayout(right_sidebar_layout, stretch=1)

        history_group = QGroupBox("Action History (click an entry to restore it)")
        history_vbox = QVBoxLayout(history_group)
        self.history_list_widget = QListWidget()
        self.history_list_widget.itemClicked.connect(self.handle_history_item_clicked)
        history_vbox.addWidget(self.history_list_widget)

        history_btn_row = QHBoxLayout()
        self.btn_clear_history = QPushButton("Clear History")
        self.btn_clear_history.clicked.connect(self.handle_clear_history)
        history_btn_row.addWidget(self.btn_clear_history)
        history_vbox.addLayout(history_btn_row)

        right_sidebar_layout.addWidget(history_group, stretch=1)

        log_group = QGroupBox("Real-time Kernel Space Console Logs")
        log_vbox = QVBoxLayout(log_group)
        log_vbox.addWidget(self.log_area)
        right_sidebar_layout.addWidget(log_group, stretch=1)

    # =====================================================================
    # RAG RENDERING ENGINE
    # =====================================================================
    def update_rag_visualization(self):
        self.rag_scene.clear()
        
        num_p = self.engine.num_processes
        num_r = self.engine.num_resources
        
        if num_p == 0 or num_r == 0:
            return

        self.rag_scene.setSceneRect(0, 0, 720, 320)
        center_x, center_y = 510, 160
        
        radius_p = 125  
        radius_r = 55   

        proc_positions = []
        res_positions = []

        # GRAPH LEGEND BOX (Unaltered, Top Left Locked)
        self.rag_scene.addRect(15, 15, 210, 105, 
                               QPen(QColor("#7f8c8d"), 1), QBrush(QColor("#2c3e50")))
        
        lbl_title = self.rag_scene.addText("GRAPH LEGEND")
        lbl_title.setDefaultTextColor(QColor("#bdc3c7"))
        lbl_title.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        lbl_title.setPos(20, 17)

        self.rag_scene.addEllipse(25, 40, 12, 12, QPen(QColor("#2980b9")), QBrush(QColor("#3498db")))
        lbl_p = self.rag_scene.addText("Process Node")
        lbl_p.setDefaultTextColor(QColor("white"))
        lbl_p.setFont(QFont("Arial", 8))
        lbl_p.setPos(43, 36)

        self.rag_scene.addRect(25, 58, 12, 12, QPen(QColor("#27ae60")), QBrush(QColor("#2ecc71")))
        lbl_r = self.rag_scene.addText("Resource Node")
        lbl_r.setDefaultTextColor(QColor("white"))
        lbl_r.setFont(QFont("Arial", 8))
        lbl_r.setPos(43, 54)

        self.rag_scene.addLine(25, 82, 37, 82, QPen(QColor("#f1c40f"), 2))
        lbl_a = self.rag_scene.addText("Allocated Edge (Res → Proc)")
        lbl_a.setDefaultTextColor(QColor("white"))
        lbl_a.setFont(QFont("Arial", 8))
        lbl_a.setPos(43, 73)

        self.rag_scene.addLine(25, 100, 37, 100, QPen(QColor("#e74c3c"), 2))
        lbl_req = self.rag_scene.addText("Request Edge (Proc → Res)")
        lbl_req.setDefaultTextColor(QColor("white"))
        lbl_req.setFont(QFont("Arial", 8))
        lbl_req.setPos(43, 91)

        # 1. Render Outer Circle Nodes (Processes)
        for i in range(num_p):
            angle = (2 * math.pi * i) / num_p - (math.pi / 2)
            x = center_x + radius_p * math.cos(angle)
            y = center_y + radius_p * math.sin(angle)
            proc_positions.append(QPointF(x, y))

            self.rag_scene.addEllipse(x - 18, y - 18, 36, 36, 
                                      QPen(QColor("#2980b9"), 2), QBrush(QColor("#3498db")))
            txt = self.rag_scene.addText(f"P{i}")
            txt.setDefaultTextColor(QColor("white"))
            txt.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            txt.setPos(x - 12, y - 11)

        # 2. Render Inner Circle Nodes (Resources)
        for j in range(num_r):
            angle = (2 * math.pi * j) / num_r - (math.pi / 2) + (math.pi / (num_r * 2))
            x = center_x + radius_r * math.cos(angle)
            y = center_y + radius_r * math.sin(angle)
            res_positions.append(QPointF(x, y))

            self.rag_scene.addRect(x - 20, y - 20, 40, 40, 
                                   QPen(QColor("#27ae60"), 2), QBrush(QColor("#2ecc71")))
            char_res = chr(65 + j)
            txt = self.rag_scene.addText(f"{char_res}\n({self.engine.available[j]})")
            txt.setDefaultTextColor(QColor("white"))
            txt.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            txt.setPos(x - 16, y - 16)

        # 3. Vector Routing Engine
        pen_alloc = QPen(QColor("#f1c40f"), 1.5)  # Gold
        pen_need = QPen(QColor("#e74c3c"), 1.5)   # Red

        for i in range(num_p):
            for j in range(num_r):
                if j < len(self.engine.allocation[i]) and self.engine.allocation[i][j] > 0:
                    self.draw_directed_arrow(res_positions[j], proc_positions[i], pen_alloc)
                if j < len(self.engine.need[i]) and self.engine.need[i][j] > 0:
                    self.draw_directed_arrow(proc_positions[i], res_positions[j], pen_need)

    def draw_directed_arrow(self, start, end, pen):
        dx, dy = end.x() - start.x(), end.y() - start.y()
        length = math.hypot(dx, dy)
        if length == 0:
            return

        ux, uy = dx / length, dy / length
        p1 = QPointF(start.x() + ux * 20, start.y() + uy * 20)
        p2 = QPointF(end.x() - ux * 20, end.y() - uy * 20)
        
        self.rag_scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), pen)

        arrow_size = 6
        angle = math.atan2(-dy, dx)
        
        arrow_p1 = p2 + QPointF(math.sin(angle - math.pi / 3) * arrow_size,
                                 math.cos(angle - math.pi / 3) * arrow_size)
        arrow_p2 = p2 + QPointF(math.sin(angle - math.pi + math.pi / 3) * arrow_size,
                                 math.cos(angle - math.pi + math.pi / 3) * arrow_size)

        polygon = QPolygonF([p2, arrow_p1, arrow_p2])
        self.rag_scene.addPolygon(polygon, QPen(pen.color()), QBrush(pen.color()))

    # =====================================================================
    # INTERFACE HANDLERS & REALTIME SIMULATOR
    # =====================================================================
    def prompt_user_for_next_process(self, candidates, work):
        """Pops a dialog listing every process that is currently eligible
        to run (need <= work) and blocks until the user picks one. This is
        exactly the "should I go to P0 or P4?" fork -- both are valid,
        Banker's Algorithm doesn't say which comes first, so the person
        running the simulation decides."""
        msg = QMessageBox(self)
        msg.setWindowTitle("Multiple Processes Ready")
        msg.setIcon(QMessageBox.Icon.Question)
        cand_str = ", ".join(f"P{c}" for c in candidates)
        msg.setText(
            f"Available = {work}\n\n"
            f"More than one process can safely execute right now: {cand_str}.\n"
            f"Which one should run next?"
        )
        choice_buttons = {}
        for idx in candidates:
            btn = msg.addButton(f"Run P{idx}", QMessageBox.ButtonRole.ActionRole)
            choice_buttons[btn] = idx
        msg.exec()
        clicked = msg.clickedButton()
        return choice_buttons.get(clicked, candidates[0])

    def compute_sequence_interactively(self):
        """Steps through the safety algorithm one round at a time. Whenever
        exactly one process is ready, it's picked automatically (no real
        choice to make). Whenever several are ready, behavior depends on
        the 'When Multiple Processes Are Ready' mode: prompt the user,
        or auto-pick by ascending/descending index."""
        mode = self.combo_scan_direction.currentIndex()  # 0=ask, 1=ascending, 2=descending

        work = list(self.engine.available)
        finish = [False] * self.engine.num_processes
        sequence = []

        while len(sequence) < self.engine.num_processes:
            candidates = self.engine.get_ready_candidates(work, finish)
            if not candidates:
                return False, sequence

            if len(candidates) == 1:
                chosen = candidates[0]
            elif mode == 0:
                chosen = self.prompt_user_for_next_process(candidates, work)
            elif mode == 2:
                chosen = max(candidates)
            else:
                chosen = min(candidates)

            finish[chosen] = True
            sequence.append(chosen)
            for j in range(self.engine.num_resources):
                work[j] += self.engine.allocation[chosen][j]

        return True, sequence

    def handle_safety_check(self):
        # 1. DETERMINE THE SEQUENCE (prompting for ties if that mode is selected)
        work = list(self.engine.available)
        is_safe, sequence = self.compute_sequence_interactively()
        
        self.btn_safety.setEnabled(False)
        self.btn_apply_values.setEnabled(False)
        
        # 2. EXPAND TABLE FOR VISUAL TRACE
        self.avail_table.blockSignals(True)
        # +2 for "Final Target" (Row 0) and "Initial Start" (Row 1)
        self.avail_table.setRowCount(len(sequence) + 2)
        v_headers = ["Final Target", "Initial Start"] + [f"After P{p}" for p in sequence]
        self.avail_table.setVerticalHeaderLabels(v_headers)
        
        for j in range(self.engine.num_resources):
            self.avail_table.setItem(0, j, QTableWidgetItem(str(self.engine.available[j])))
            self.avail_table.setItem(1, j, QTableWidgetItem(str(self.engine.available[j])))
        self.avail_table.blockSignals(False)

        # 3. EXECUTION LOOP
        if is_safe:
            self.lbl_outcome_status.setText("Status: SYSTEM SAFE")
            self.lbl_outcome_status.setStyleSheet("color: #2ecc71; font-weight: bold;")

            for step_idx, proc_idx in enumerate(sequence):
                self.kernel.log_kernel_event("SIM_EXEC", f"Running Process P{proc_idx}...")

                QCoreApplication.processEvents()
                time.sleep(1.0) 

                for j in range(self.engine.num_resources):
                    work[j] += self.engine.allocation[proc_idx][j]

                self.avail_table.blockSignals(True)
                for j in range(self.engine.num_resources):
                    item = QTableWidgetItem(str(work[j]))
                    item.setForeground(QBrush(QColor("#2ecc71")))
                    self.avail_table.setItem(step_idx + 2, j, item)
                self.avail_table.blockSignals(False)
                QCoreApplication.processEvents()
            
            str_seq = " -> ".join([f"P{p}" for p in sequence])
            self.lbl_sequence.setText(f"Sequence: {str_seq}")
        else:
            self.lbl_outcome_status.setText("Status: DEADLOCK DETECTED")
            self.lbl_outcome_status.setStyleSheet("color: #e74c3c; font-weight: bold;")
            self.lbl_sequence.setText("Sequence: None")
        
        # Re-enable inputs
        self.btn_safety.setEnabled(True)
        self.btn_apply_values.setEnabled(True)

        # 4. SAVE ONE HISTORY ENTRY CAPTURING THE FINAL OUTCOME OF THIS RUN
        outcome_label = "SAFE" if is_safe else "DEADLOCK"
        self.save_history_entry(f"Executed Simulation -> {outcome_label}")

    def handle_cell_edit(self, row, column):
        sender = self.sender()
        if not sender:
            return
        try:
            item = sender.item(row, column)
            if not item:
                return
            val = int(item.text())
            
            sender.blockSignals(True)
            if sender == self.avail_table:
                # If editing a history log, ignore
                if row != 0:
                    sender.blockSignals(False)
                    return
                self.engine.available[column] = val
                
                # If editing while expanded, collapse to hide outdated simulation logs
                if self.avail_table.rowCount() > 1:
                    self.avail_table.setRowCount(1)
                    self.avail_table.setVerticalHeaderLabels(["Current Pool"])
            elif sender == self.alloc_table:
                self.engine.allocation[row][column] = val
            elif sender == self.max_table:
                self.engine.max_matrix[row][column] = val
            sender.blockSignals(False)
            
            self.engine.calculate_need_matrix()
            self.update_need_table_display()
            self.load_current_matrix_values_to_spinboxes()
            self.update_rag_visualization()

            if sender == self.avail_table:
                cell_desc = f"Available[{chr(65+column)}]"
            elif sender == self.alloc_table:
                cell_desc = f"Allocation[P{row}][{chr(65+column)}]"
            else:
                cell_desc = f"Max Demand[P{row}][{chr(65+column)}]"
            self.save_history_entry(f"Edited {cell_desc} -> {val}")

        except ValueError:
            pass 

    def update_gui_tables(self, reset_avail=True):
        self.alloc_table.blockSignals(True)
        self.max_table.blockSignals(True)
        self.need_table.blockSignals(True)

        if reset_avail:
            self.avail_table.blockSignals(True)
            self.avail_table.setRowCount(1)
            self.avail_table.setVerticalHeaderLabels(["Current Pool"])
            self.avail_table.setColumnCount(self.engine.num_resources)

        for table in [self.alloc_table, self.max_table, self.need_table]:
            table.setRowCount(self.engine.num_processes)
            table.setColumnCount(self.engine.num_resources)

        headers = [chr(65 + j) for j in range(self.engine.num_resources)]
        for table in [self.avail_table, self.alloc_table, self.max_table, self.need_table]:
            table.setHorizontalHeaderLabels(headers)

        proc_headers = [f"P{i}" for i in range(self.engine.num_processes)]
        self.alloc_table.setVerticalHeaderLabels(proc_headers)
        self.max_table.setVerticalHeaderLabels(proc_headers)
        self.need_table.setVerticalHeaderLabels(proc_headers)

        if reset_avail:
            for j in range(self.engine.num_resources):
                self.avail_table.setItem(0, j, QTableWidgetItem(str(self.engine.available[j])))
            self.avail_table.blockSignals(False)
        
        for i in range(self.engine.num_processes):
            for j in range(self.engine.num_resources):
                self.alloc_table.setItem(i, j, QTableWidgetItem(str(self.engine.allocation[i][j])))
                self.max_table.setItem(i, j, QTableWidgetItem(str(self.engine.max_matrix[i][j])))
                self.need_table.setItem(i, j, QTableWidgetItem(str(self.engine.need[i][j])))

        self.alloc_table.blockSignals(False)
        self.max_table.blockSignals(False)
        self.need_table.blockSignals(False)
        self.update_rag_visualization()

    # The rest remain structurally identical
    def rebuild_dynamic_spinboxes(self):
        while self.spinbox_container_layout.count():
            item = self.spinbox_container_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        
        self.dynamic_spinboxes.clear()
        
        for j in range(self.engine.num_resources):
            char_header = chr(65 + j)
            label = QLabel(char_header)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            spin = QSpinBox()
            spin.setRange(0, 50)
            
            self.spinbox_container_layout.addWidget(label, 0, j)
            self.spinbox_container_layout.addWidget(spin, 1, j)
            self.dynamic_spinboxes.append(spin)

    def handle_matrix_selection_change(self):
        if self.combo_matrix_target.currentIndex() == 0:
            self.proc_select_row_widget.setVisible(False)
        else:
            self.proc_select_row_widget.setVisible(True)
        self.load_current_matrix_values_to_spinboxes()

    def load_current_matrix_values_to_spinboxes(self):
        matrix_type = self.combo_matrix_target.currentIndex()
        proc_id = self.combo_proc_target.currentIndex()

        if proc_id < 0 or proc_id >= self.engine.num_processes:
            proc_id = 0

        for spin in self.dynamic_spinboxes:
            spin.blockSignals(True)

        for j in range(self.engine.num_resources):
            if j >= len(self.dynamic_spinboxes):
                break
            
            if matrix_type == 0: 
                val = self.engine.available[j]
            elif matrix_type == 1: 
                val = self.engine.allocation[proc_id][j]
            else: 
                val = self.engine.max_matrix[proc_id][j]
                
            self.dynamic_spinboxes[j].setValue(val)

        for spin in self.dynamic_spinboxes:
            spin.blockSignals(False)

    def handle_apply_matrix_values(self):
        matrix_type = self.combo_matrix_target.currentIndex()
        proc_id = self.combo_proc_target.currentIndex()
        
        new_values = [spin.value() for spin in self.dynamic_spinboxes]
        matrix_name = self.combo_matrix_target.currentText()

        if matrix_type == 0:
            self.engine.available = list(new_values)
            self.kernel.log_kernel_event("OS_CONFIG", f"Updated system Available pool to: {new_values}")
        elif matrix_type == 1:
            self.engine.allocation[proc_id] = list(new_values)
            self.kernel.log_kernel_event("OS_CONFIG", f"Updated P{proc_id} Allocation to: {new_values}")
        else:
            self.engine.max_matrix[proc_id] = list(new_values)
            self.kernel.log_kernel_event("OS_CONFIG", f"Updated P{proc_id} Max Demand to: {new_values}")

        self.engine.calculate_need_matrix()
        self.update_gui_tables()
        self.update_rag_visualization()
        
        target_info = f"P{proc_id}" if matrix_type != 0 else "System"
        self.save_history_entry(f"Configured {matrix_name} ({target_info}) -> {new_values}")

    def update_need_table_display(self):
        self.need_table.blockSignals(True)
        for i in range(self.engine.num_processes):
            for j in range(self.engine.num_resources):
                self.need_table.setItem(i, j, QTableWidgetItem(str(self.engine.need[i][j])))
        self.need_table.blockSignals(False)

    def sync_combobox_items(self):
        proc_headers = [f"P{i}" for i in range(self.engine.num_processes)]
        res_headers = [chr(65 + j) for j in range(self.engine.num_resources)]

        for combo in [self.combo_kill_target, self.combo_proc_target]:
            old_idx = combo.currentIndex()
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(proc_headers)
            combo.setCurrentIndex(old_idx if 0 <= old_idx < len(proc_headers) else 0)
            combo.blockSignals(False)

        old_res_idx = self.combo_drop_resource.currentIndex()
        self.combo_drop_resource.blockSignals(True)
        self.combo_drop_resource.clear()
        self.combo_drop_resource.addItems(res_headers)
        self.combo_drop_resource.setCurrentIndex(old_res_idx if 0 <= old_res_idx < len(res_headers) else 0)
        self.combo_drop_resource.blockSignals(False)

    def handle_add_resource(self):
        self.engine.add_resource_type()
        new_res_name = chr(64 + self.engine.num_resources)
        self.kernel.log_kernel_event("OS_CONFIG", f"Registered new Resource Column: {new_res_name}")
        
        self.sync_combobox_items()
        self.rebuild_dynamic_spinboxes()
        self.update_gui_tables()
        self.load_current_matrix_values_to_spinboxes()
        self.save_history_entry(f"Added Resource Column: {new_res_name}")

    def handle_remove_resource(self):
        target_res_idx = self.combo_drop_resource.currentIndex()
        if target_res_idx >= 0:
            res_label = chr(65 + target_res_idx)
            if self.engine.remove_resource_type(target_res_idx):
                self.kernel.log_kernel_event("OS_CONFIG", f"Removed Resource Column: {res_label}")
                self.sync_combobox_items()
                self.rebuild_dynamic_spinboxes()
                self.update_gui_tables()
                self.load_current_matrix_values_to_spinboxes()
                self.save_history_entry(f"Deleted Resource Column: {res_label}")
            else:
                QMessageBox.warning(self, "Action Denied", "System must maintain at least 1 resource column.")

    def handle_add_process(self):
        self.engine.add_process()
        new_proc_label = f"P{self.engine.num_processes-1}"
        self.kernel.log_kernel_event("OS_SPAWN", f"Spawned custom Process {new_proc_label}")
        self.sync_combobox_items()
        self.update_gui_tables()
        self.save_history_entry(f"Added Process: {new_proc_label}")

    def handle_remove_process(self):
        target_id = self.combo_kill_target.currentIndex()
        if target_id >= 0:
            if self.engine.remove_targeted_process(target_id):
                self.kernel.log_kernel_event("OS_KILL", f"Process P{target_id} deleted. Memory freed.")
                self.sync_combobox_items()
                self.update_gui_tables()
                self.load_current_matrix_values_to_spinboxes()
                self.save_history_entry(f"Deleted Process: P{target_id}")
            else:
                QMessageBox.warning(self, "Action Denied", "Cannot clear baseline core system process.")

    # =====================================================================
    # HISTORY TAB: FULL-STATE SNAPSHOT + RESTORE (like a browser history)
    # =====================================================================
    def capture_snapshot(self):
        """Grabs a full, independent copy of everything needed to reproduce
        the current screen exactly: matrix sizes/values plus the last
        simulation outcome shown in the outcome panel."""
        return {
            "num_processes": self.engine.num_processes,
            "num_resources": self.engine.num_resources,
            "available": list(self.engine.available),
            "max_matrix": [list(row) for row in self.engine.max_matrix],
            "allocation": [list(row) for row in self.engine.allocation],
            "matrix_target_idx": self.combo_matrix_target.currentIndex(),
            "proc_target_idx": self.combo_proc_target.currentIndex(),
            "scan_direction_idx": self.combo_scan_direction.currentIndex(),
            "outcome_status_text": self.lbl_outcome_status.text(),
            "outcome_status_style": self.lbl_outcome_status.styleSheet(),
            "sequence_text": self.lbl_sequence.text(),
        }

    def save_history_entry(self, description):
        """Call this after ANY state-changing action. Stores a snapshot and
        adds a clickable row to the history list; clicking that row later
        reloads this exact state, no need to re-enter values."""
        timestamp = time.strftime("%H:%M:%S")
        self.history_snapshots.append(self.capture_snapshot())

        item = QListWidgetItem(f"[{timestamp}] {description}")
        self.history_list_widget.addItem(item)
        self.history_list_widget.scrollToBottom()
        self.history_list_widget.setCurrentItem(item)

    def handle_history_item_clicked(self, item):
        row = self.history_list_widget.row(item)
        if row < 0 or row >= len(self.history_snapshots):
            return
        self.restore_snapshot(self.history_snapshots[row])

    def restore_snapshot(self, snapshot):
        """Rebuilds the engine and every widget on screen from a stored
        snapshot: matrices, process/resource counts, dropdown selections,
        the outcome banner, and the RAG diagram."""
        self.engine.num_processes = snapshot["num_processes"]
        self.engine.num_resources = snapshot["num_resources"]
        self.engine.available = list(snapshot["available"])
        self.engine.max_matrix = [list(row) for row in snapshot["max_matrix"]]
        self.engine.allocation = [list(row) for row in snapshot["allocation"]]
        self.engine.calculate_need_matrix()

        self.sync_combobox_items()
        self.rebuild_dynamic_spinboxes()
        self.update_gui_tables()  # also redraws the RAG

        self.combo_matrix_target.blockSignals(True)
        self.combo_matrix_target.setCurrentIndex(snapshot["matrix_target_idx"])
        self.combo_matrix_target.blockSignals(False)
        self.proc_select_row_widget.setVisible(snapshot["matrix_target_idx"] != 0)

        self.combo_proc_target.blockSignals(True)
        if 0 <= snapshot["proc_target_idx"] < self.combo_proc_target.count():
            self.combo_proc_target.setCurrentIndex(snapshot["proc_target_idx"])
        self.combo_proc_target.blockSignals(False)

        self.load_current_matrix_values_to_spinboxes()

        self.combo_scan_direction.blockSignals(True)
        self.combo_scan_direction.setCurrentIndex(snapshot.get("scan_direction_idx", 0))
        self.combo_scan_direction.blockSignals(False)

        self.lbl_outcome_status.setText(snapshot["outcome_status_text"])
        self.lbl_outcome_status.setStyleSheet(snapshot["outcome_status_style"])
        self.lbl_sequence.setText(snapshot["sequence_text"])

        self.kernel.log_kernel_event("HISTORY", "Restored full state from a saved history entry.")

    def handle_clear_history(self):
        confirm = QMessageBox.question(
            self, "Clear History", "Delete all saved history entries? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.history_list_widget.clear()
            self.history_snapshots.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DeadlockSimWindow()
    window.show()
    sys.exit(app.exec())