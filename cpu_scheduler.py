import sys
import os
import copy
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTableWidget, QTableWidgetItem, QPushButton, QComboBox, 
    QLabel, QSpinBox, QHeaderView, QGroupBox, QTextEdit, QFileDialog,
    QRadioButton, QButtonGroup, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QRect, QMarginsF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QIcon, QTextDocument, QPageLayout
from PyQt6.QtPrintSupport import QPrinter

# ==============================================================================
# 1. CORE OBJECT MODELS AND DATA CONTRACTS
# ==============================================================================
class Process:
    def __init__(self, pid, arrival_time, burst_time, priority=0):
        self.pid = pid                      
        self.arrival_time = arrival_time    
        self.burst_time = burst_time        
        self.priority = priority            
        
        # Computed Output Metrics
        self.completion_time = 0
        self.turnaround_time = 0            
        self.waiting_time = 0               
        
        # Temporary tracking fields for preemptive algorithms
        self.remaining_time = burst_time

# ==============================================================================
# 2. SCHEDULER ENGINE WITH LOG LOGIC LOOPS
# ==============================================================================
class CPUSchedulerEngine:
    @staticmethod
    def run_fcfs(processes):
        procs = sorted([copy.deepcopy(p) for p in processes], key=lambda x: x.arrival_time)
        gantt = []
        logs = []
        current_time = 0
        
        logs.append(f"[Time 0]: FCFS Engine initialized with {len(procs)} processes.")
        for p in procs:
            if current_time < p.arrival_time:
                logs.append(f"[Time {current_time}]: CPU is IDLE. Waiting for next arrival.")
                gantt.append(("IDLE", current_time, p.arrival_time))
                current_time = p.arrival_time
            
            start = current_time
            logs.append(f"[Time {start}]: Context Switch -> dispatching Process {p.pid}.")
            current_time += p.burst_time
            p.completion_time = current_time
            p.turnaround_time = p.completion_time - p.arrival_time
            p.waiting_time = p.turnaround_time - p.burst_time
            gantt.append((p.pid, start, current_time))
            logs.append(f"[Time {current_time}]: Process {p.pid} terminated.")
            
        return procs, gantt, logs

    @staticmethod
    def run_sjf_non_preemptive(processes):
        procs = [copy.deepcopy(p) for p in processes]
        gantt = []
        logs = []
        current_time = 0
        completed = []
        
        logs.append(f"[Time 0]: SJF (Non-Preemptive) Engine initialized.")
        while len(completed) < len(processes):
            available = [p for p in procs if p.arrival_time <= current_time and p not in completed]
            
            if not available:
                next_proc = min([p for p in procs if p not in completed], key=lambda x: x.arrival_time)
                gantt.append(("IDLE", current_time, next_proc.arrival_time))
                current_time = next_proc.arrival_time
                continue
                
            chosen = min(available, key=lambda x: x.burst_time)
            start = current_time
            logs.append(f"[Time {start}]: Selecting Process {chosen.pid} (Burst={chosen.burst_time}).")
            current_time += chosen.burst_time
            
            chosen.completion_time = current_time
            chosen.turnaround_time = chosen.completion_time - chosen.arrival_time
            chosen.waiting_time = chosen.turnaround_time - chosen.burst_time
            
            gantt.append((chosen.pid, start, current_time))
            completed.append(chosen)
            logs.append(f"[Time {current_time}]: Process {chosen.pid} completed execution.")
            
        return procs, gantt, logs

    @staticmethod
    def run_sjf_preemptive(processes):
        procs = [copy.deepcopy(p) for p in processes]
        gantt = []
        logs = []
        current_time = 0
        completed_count = 0
        n = len(procs)
        last_pid = None
        block_start = 0
        
        logs.append(f"[Time 0]: SRTF/SJF (Preemptive) Engine active.")
        while completed_count < n:
            available = [p for p in procs if p.arrival_time <= current_time and p.remaining_time > 0]
            
            if not available:
                if last_pid is not None:
                    gantt.append((last_pid, block_start, current_time))
                    last_pid = None
                next_arrival = min([p.arrival_time for p in procs if p.remaining_time > 0])
                gantt.append(("IDLE", current_time, next_arrival))
                current_time = next_arrival
                continue
                
            chosen = min(available, key=lambda x: x.remaining_time)
            
            if chosen.pid != last_pid:
                if last_pid is not None:
                    gantt.append((last_pid, block_start, current_time))
                    logs.append(f"[Time {current_time}]: Preemption! Context switch from {last_pid} to {chosen.pid}.")
                last_pid = chosen.pid
                block_start = current_time
                
            chosen.remaining_time -= 1
            current_time += 1
            
            if chosen.remaining_time == 0:
                gantt.append((chosen.pid, block_start, current_time))
                last_pid = None
                chosen.completion_time = current_time
                chosen.turnaround_time = chosen.completion_time - chosen.arrival_time
                chosen.waiting_time = chosen.turnaround_time - chosen.burst_time
                completed_count += 1
                logs.append(f"[Time {current_time}]: Process {chosen.pid} fully closed out.")
                block_start = current_time
                
        return procs, gantt, logs

    @staticmethod
    def run_round_robin(processes, time_quantum):
        procs = [copy.deepcopy(p) for p in processes]
        gantt = []
        logs = []
        current_time = 0
        ready_queue = []
        visited = [False] * len(procs)
        completed_count = 0
        n = len(procs)
        
        logs.append(f"[Time 0]: Round Robin active with Quantum={time_quantum}.")
        def check_new_arrivals():
            for i, p in enumerate(procs):
                if p.arrival_time <= current_time and not visited[i] and p.remaining_time > 0:
                    ready_queue.append(procs[i])
                    visited[i] = True
                    logs.append(f"[Time {current_time}]: Process {p.pid} added to ready queue.")

        check_new_arrivals()
        
        while completed_count < n:
            if not ready_queue:
                uncompleted = [p for p in procs if p.remaining_time > 0]
                if uncompleted:
                    next_arrival = min(uncompleted, key=lambda x: x.arrival_time).arrival_time
                    gantt.append(("IDLE", current_time, next_arrival))
                    current_time = next_arrival
                    check_new_arrivals()
                continue
                
            curr_p = ready_queue.pop(0)
            start = current_time
            
            if curr_p.remaining_time > time_quantum:
                curr_p.remaining_time -= time_quantum
                current_time += time_quantum
                check_new_arrivals()
                ready_queue.append(curr_p)
                gantt.append((curr_p.pid, start, current_time))
            else:
                current_time += curr_p.remaining_time
                curr_p.remaining_time = 0
                curr_p.completion_time = current_time
                curr_p.turnaround_time = curr_p.completion_time - curr_p.arrival_time
                curr_p.waiting_time = curr_p.turnaround_time - curr_p.burst_time
                completed_count += 1
                gantt.append((curr_p.pid, start, current_time))
                check_new_arrivals()
                
        return procs, gantt, logs

    @staticmethod
    def run_priority_non_preemptive(processes, reverse_priority=False):
        procs = [copy.deepcopy(p) for p in processes]
        gantt = []
        logs = []
        current_time = 0
        completed = []
        
        logs.append(f"[Time 0]: Priority (Non-Preemptive) Engine initialized. Mode: {'Higher value = Higher priority' if reverse_priority else 'Lower value = Higher priority'}.")
        while len(completed) < len(processes):
            available = [p for p in procs if p.arrival_time <= current_time and p not in completed]
            
            if not available:
                next_proc = min([p for p in procs if p not in completed], key=lambda x: x.arrival_time)
                logs.append(f"[Time {current_time}]: CPU is IDLE. Waiting for arrival of Process {next_proc.pid}.")
                gantt.append(("IDLE", current_time, next_proc.arrival_time))
                current_time = next_proc.arrival_time
                continue
            
            if reverse_priority:
                chosen = max(available, key=lambda x: (x.priority, -x.arrival_time))
            else:
                chosen = min(available, key=lambda x: (x.priority, x.arrival_time))
                
            start = current_time
            logs.append(f"[Time {start}]: Selecting Process {chosen.pid} (Priority={chosen.priority}, Burst={chosen.burst_time}).")
            current_time += chosen.burst_time
            
            chosen.completion_time = current_time
            chosen.turnaround_time = chosen.completion_time - chosen.arrival_time
            chosen.waiting_time = chosen.turnaround_time - chosen.burst_time
            
            gantt.append((chosen.pid, start, current_time))
            completed.append(chosen)
            logs.append(f"[Time {current_time}]: Process {chosen.pid} completed execution.")
            
        return procs, gantt, logs

    @staticmethod
    def run_priority_preemptive(processes, reverse_priority=False):
        procs = [copy.deepcopy(p) for p in processes]
        gantt = []
        logs = []
        current_time = 0
        completed_count = 0
        n = len(procs)
        last_pid = None
        block_start = 0
        
        logs.append(f"[Time 0]: Priority (Preemptive) Engine initialized. Mode: {'Higher value = Higher priority' if reverse_priority else 'Lower value = Higher priority'}.")
        while completed_count < n:
            available = [p for p in procs if p.arrival_time <= current_time and p.remaining_time > 0]
            
            if not available:
                if last_pid is not None:
                    gantt.append((last_pid, block_start, current_time))
                    last_pid = None
                next_arrival = min([p.arrival_time for p in procs if p.remaining_time > 0])
                logs.append(f"[Time {current_time}]: CPU is IDLE. Fast-forwarding to next arrival at Time {next_arrival}.")
                gantt.append(("IDLE", current_time, next_arrival))
                current_time = next_arrival
                continue
            
            if reverse_priority:
                chosen = max(available, key=lambda x: (x.priority, -x.arrival_time))
            else:
                chosen = min(available, key=lambda x: (x.priority, x.arrival_time))
            
            if chosen.pid != last_pid:
                if last_pid is not None:
                    gantt.append((last_pid, block_start, current_time))
                    logs.append(f"[Time {current_time}]: Preemption! Context switch from {last_pid} to higher priority Process {chosen.pid}.")
                else:
                    logs.append(f"[Time {current_time}]: Context Switch -> dispatching Process {chosen.pid}.")
                last_pid = chosen.pid
                block_start = current_time
                
            chosen.remaining_time -= 1
            current_time += 1
            
            if chosen.remaining_time == 0:
                gantt.append((chosen.pid, block_start, current_time))
                last_pid = None
                chosen.completion_time = current_time
                chosen.turnaround_time = chosen.completion_time - chosen.arrival_time
                chosen.waiting_time = chosen.turnaround_time - chosen.burst_time
                completed_count += 1
                logs.append(f"[Time {current_time}]: Process {chosen.pid} completed execution.")
                block_start = current_time
                
        return procs, gantt, logs

    @staticmethod
    def run_hrrn(processes):
        procs = [copy.deepcopy(p) for p in processes]
        gantt = []
        logs = []
        current_time = 0
        completed = []
        
        logs.append(f"[Time 0]: HRRN Engine initialized.")
        while len(completed) < len(processes):
            available = [p for p in procs if p.arrival_time <= current_time and p not in completed]
            
            if not available:
                next_proc = min([p for p in procs if p not in completed], key=lambda x: x.arrival_time)
                logs.append(f"[Time {current_time}]: CPU is IDLE. Waiting for arrival of Process {next_proc.pid}.")
                gantt.append(("IDLE", current_time, next_proc.arrival_time))
                current_time = next_proc.arrival_time
                continue
                
            highest_ratio = -1
            chosen = None
            logs.append(f"[Time {current_time}]: Calculating Response Ratios for available processes:")
            for p in available:
                wait_time = current_time - p.arrival_time
                ratio = (wait_time + p.burst_time) / p.burst_time
                logs.append(f" -> Process {p.pid}: (Wait {wait_time} + Burst {p.burst_time}) / {p.burst_time} = Ratio {ratio:.2f}")
                if ratio > highest_ratio:
                    highest_ratio = ratio
                    chosen = p
            
            start = current_time
            logs.append(f"[Time {start}]: Selecting Process {chosen.pid} with the highest Response Ratio ({highest_ratio:.2f}).")
            current_time += chosen.burst_time
            chosen.completion_time = current_time
            chosen.turnaround_time = chosen.completion_time - chosen.arrival_time
            chosen.waiting_time = chosen.turnaround_time - chosen.burst_time
            
            gantt.append((chosen.pid, start, current_time))
            completed.append(chosen)
            logs.append(f"[Time {current_time}]: Process {chosen.pid} completed execution.")
            
        return procs, gantt, logs

# ==============================================================================
# 3. GANTT CHART TIMELINE RENDERING ENGINE
# ==============================================================================
class GanttTimelineWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.gantt_data = []
        self.setMinimumHeight(80)  
        
    def update_data(self, gantt_data):
        self.gantt_data = gantt_data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QColor("#1e272e"))

        if not self.gantt_data:
            return

        margin_x = 40
        top_y = 15
        box_height = 32  
        axis_y = top_y + box_height
        block_gap = 4  
        
        total_duration = self.gantt_data[-1][2] if self.gantt_data else 1
        if total_duration == 0:
            total_duration = 1
            
        render_width = self.width() - (2 * margin_x)
        scale_factor = render_width / total_duration

        for block in self.gantt_data:
            pid, start, end = block
            
            x_start = margin_x + int(start * scale_factor)
            x_end = margin_x + int(end * scale_factor)
            w = x_end - x_start
            
            if w > block_gap:
                w -= block_gap

            rect = QRect(x_start, top_y, w, box_height)
            
            if pid == "IDLE":
                bg_color = QColor("#d2d7d9")
                fg_color = QColor("#7f8c8d")
            else:
                bg_color = QColor("#3498db")  
                fg_color = QColor("#ffffff")

            painter.setBrush(bg_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 4, 4)

            painter.setPen(fg_color)
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(pid))

        painter.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        
        timestamps = []
        timestamps.append((self.gantt_data[0][1], margin_x))
        
        for i in range(len(self.gantt_data) - 1):
            curr_end_val = self.gantt_data[i][2]
            x_end_theoretical = margin_x + int(curr_end_val * scale_factor)
            x_left_aligned = x_end_theoretical - block_gap
            timestamps.append((curr_end_val, int(x_left_aligned)))
            
        final_t = self.gantt_data[-1][2]
        final_x = margin_x + int(final_t * scale_factor) - block_gap
        timestamps.append((final_t, final_x))

        for time_val, x_pos in timestamps:
            text_str = str(time_val)
            text_width = painter.fontMetrics().horizontalAdvance(text_str)
            text_rect = QRect(int(x_pos - (text_width / 2.0)), axis_y + 4, text_width + 10, 15)
            
            painter.setPen(QColor("#ffffff"))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignHCenter, text_str)

# ==============================================================================
# 4. INTERACTIVE DASHBOARD UI SYSTEM (WITH COMPREHENSIVE HISTORY STATE)
# ==============================================================================
class SimulationDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cosmos College - Interactive CPU Scheduler Dashboard")
        self.resize(1300, 860)
        
        # Look for the custom logo
        icon_filename = "image_1b910a.jpg"
        if os.path.exists(icon_filename):
            self.setWindowIcon(QIcon(icon_filename))
        
        self.last_sim_results = None
        self.last_algo_used = ""
        
        # Structured Runtime History Archive
        self.history_records = []
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # --- Top Configurations Area ---
        config_box = QGroupBox("Configuration Panel")
        config_layout = QHBoxLayout()
        
        config_layout.addWidget(QLabel("Algorithm:"))
        self.algo_combo = QComboBox()
        self.algo_combo.addItems([
            "FCFS", "SJF (Non-Preemptive)", "SJF (Preemptive)", 
            "Round Robin", "Priority (Non-Preemptive)", "Priority (Preemptive)",
            "Highest Response Ratio Next (HRRN)"
        ])
        self.algo_combo.currentTextChanged.connect(self.toggle_inputs)
        config_layout.addWidget(self.algo_combo)
        
        self.lbl_quantum = QLabel("Time Quantum:")
        config_layout.addWidget(self.lbl_quantum)
        self.quantum_spin = QSpinBox()
        self.quantum_spin.setRange(1, 20)
        self.quantum_spin.setValue(2)
        config_layout.addWidget(self.quantum_spin)
        
        self.lbl_priority_rule = QLabel("Priority Order:")
        self.radio_low_high = QRadioButton("Lower # = Higher Priority")
        self.radio_high_low = QRadioButton("Higher # = Higher Priority")
        self.radio_low_high.setChecked(True)
        
        self.priority_group = QButtonGroup(self)
        self.priority_group.addButton(self.radio_low_high)
        self.priority_group.addButton(self.radio_high_low)
        
        config_layout.addWidget(self.lbl_priority_rule)
        config_layout.addWidget(self.radio_low_high)
        config_layout.addWidget(self.radio_high_low)
        
        self.btn_run = QPushButton("Execute Simulation")
        self.btn_run.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold; padding: 6px;")
        self.btn_run.clicked.connect(self.run_simulation)
        config_layout.addWidget(self.btn_run)
        
        self.btn_report = QPushButton("Export Analytical Report")
        self.btn_report.setStyleSheet("background-color: #e67e22; color: white; font-weight: bold; padding: 6px;")
        self.btn_report.clicked.connect(self.export_report)
        config_layout.addWidget(self.btn_report)
        
        config_box.setLayout(config_layout)
        main_layout.addWidget(config_box)
        
        # --- Middle Process Setup Matrix ---
        proc_box = QGroupBox("Process Management Table")
        proc_layout = QVBoxLayout()
        
        table_ctrl_layout = QHBoxLayout()
        self.btn_add_row = QPushButton("+ Add Process")
        self.btn_add_row.clicked.connect(self.add_process_row)
        self.btn_remove_row = QPushButton("- Remove Selected Process")
        self.btn_remove_row.clicked.connect(self.remove_process_row)
        table_ctrl_layout.addWidget(self.btn_add_row)
        table_ctrl_layout.addWidget(self.btn_remove_row)
        table_ctrl_layout.addStretch()
        proc_layout.addLayout(table_ctrl_layout)
        
        self.input_table = QTableWidget(5, 4)
        self.input_table.setHorizontalHeaderLabels(["Process ID", "Arrival Time", "Burst Time", "Priority"])
        self.input_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        default_data = [
            ("P1", "0", "3", "1"),
            ("P2", "2", "6", "3"),
            ("P3", "4", "4", "2"),
            ("P4", "6", "5", "5"),
            ("P5", "8", "2", "4")
        ]
        for row, data in enumerate(default_data):
            for col, val in enumerate(data):
                self.input_table.setItem(row, col, QTableWidgetItem(val))
                
        proc_layout.addWidget(self.input_table)
        proc_box.setLayout(proc_layout)
        main_layout.addWidget(proc_box)
        
        # --- Visual Vector-Based Gantt Timeline Panel ---
        self.gantt_box = QGroupBox("Visual Gantt Timeline Stream")
        gantt_container_layout = QVBoxLayout(self.gantt_box)
        
        self.gantt_view = GanttTimelineWidget()
        gantt_container_layout.addWidget(self.gantt_view)
        main_layout.addWidget(self.gantt_box)
        
        self.gantt_box.setVisible(False)
        
        # --- Middle Bottom Split Layout ---
        bottom_split = QHBoxLayout()
        
        output_box = QGroupBox("Analytics & Performance Metrics")
        output_layout = QVBoxLayout()
        
        self.output_table = QTableWidget(0, 7)
        self.output_table.setHorizontalHeaderLabels([
            "Process ID", "Arrival Time", "Burst Time", "Priority", "Completion Time", "Turnaround Time", "Waiting Time"
        ])
        self.output_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        output_layout.addWidget(self.output_table)
        
        self.lbl_averages = QLabel("Average Waiting Time: -- | Average Turnaround Time: --")
        self.lbl_averages.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff;")
        output_layout.addWidget(self.lbl_averages)
        output_box.setLayout(output_layout)
        bottom_split.addWidget(output_box, stretch=4)
        
        log_box = QGroupBox("State Transition Verification Log")
        log_layout = QVBoxLayout()
        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setStyleSheet("background-color: #2c3e50; color: #1abc9c; font-family: Consolas; font-size: 11px;")
        log_layout.addWidget(self.txt_logs)
        log_box.setLayout(log_layout)
        bottom_split.addWidget(log_box, stretch=3)

        # --- Simulation Run History Archive Panel ---
        history_box = QGroupBox("Simulation Run History Archive")
        history_layout = QVBoxLayout()
        self.history_list_widget = QListWidget()
        self.history_list_widget.setStyleSheet("background-color: #1e272e; color: #f5f6fa; font-family: Segoe UI; font-size: 11px;")
        self.history_list_widget.itemClicked.connect(self.load_historical_record)
        history_layout.addWidget(self.history_list_widget)
        
        self.btn_clear_history = QPushButton("Clear History")
        self.btn_clear_history.setStyleSheet("background-color: #c0392b; color: white; font-size: 11px; padding: 3px;")
        self.btn_clear_history.clicked.connect(self.clear_history_log)
        history_layout.addWidget(self.btn_clear_history)
        
        history_box.setLayout(history_layout)
        bottom_split.addWidget(history_box, stretch=2)
        
        main_layout.addLayout(bottom_split)
        self.toggle_inputs()
        
    def toggle_inputs(self):
        algo = self.algo_combo.currentText()
        is_rr = (algo == "Round Robin")
        is_priority_algo = "Priority" in algo
        
        self.lbl_quantum.setVisible(is_rr)
        self.quantum_spin.setVisible(is_rr)
        self.lbl_priority_rule.setVisible(is_priority_algo)
        self.radio_low_high.setVisible(is_priority_algo)
        self.radio_high_low.setVisible(is_priority_algo)
        
        self.input_table.setColumnHidden(3, not is_priority_algo)
        self.output_table.setColumnHidden(3, not is_priority_algo)

    def add_process_row(self):
        row_idx = self.input_table.rowCount()
        self.input_table.insertRow(row_idx)
        self.input_table.setItem(row_idx, 0, QTableWidgetItem(f"P{row_idx+1}"))
        self.input_table.setItem(row_idx, 1, QTableWidgetItem("0"))
        self.input_table.setItem(row_idx, 2, QTableWidgetItem("5"))
        self.input_table.setItem(row_idx, 3, QTableWidgetItem("1"))

    def remove_process_row(self):
        curr_row = self.input_table.currentRow()
        if curr_row >= 0:
            self.input_table.removeRow(curr_row)
        elif self.input_table.rowCount() > 0:
            self.input_table.removeRow(self.input_table.rowCount() - 1)

    def run_simulation(self):
        processes = []
        for row in range(self.input_table.rowCount()):
            try:
                pid = self.input_table.item(row, 0).text()
                arr = int(self.input_table.item(row, 1).text())
                burst = int(self.input_table.item(row, 2).text())
                priority_item = self.input_table.item(row, 3)
                priority = int(priority_item.text() if (priority_item and priority_item.text()) else 0)
                
                processes.append(Process(pid, arr, burst, priority))
            except (ValueError, AttributeError):
                continue
                
        if not processes:
            return

        algo = self.algo_combo.currentText()
        self.last_algo_used = algo
        reverse_priority = self.radio_high_low.isChecked()
        
        if algo == "FCFS":
            results, gantt, logs = CPUSchedulerEngine.run_fcfs(processes)
        elif algo == "SJF (Non-Preemptive)":
            results, gantt, logs = CPUSchedulerEngine.run_sjf_non_preemptive(processes)
        elif algo == "SJF (Preemptive)":
            results, gantt, logs = CPUSchedulerEngine.run_sjf_preemptive(processes)
        elif algo == "Round Robin":
            results, gantt, logs = CPUSchedulerEngine.run_round_robin(processes, self.quantum_spin.value())
            self.last_algo_used += f" (Quantum={self.quantum_spin.value()})"
        elif algo == "Priority (Non-Preemptive)":
            results, gantt, logs = CPUSchedulerEngine.run_priority_non_preemptive(processes, reverse_priority)
            mode_desc = "Higher Value Wins" if reverse_priority else "Lower Value Wins"
            self.last_algo_used += f" ({mode_desc})"
        elif algo == "Priority (Preemptive)":
            results, gantt, logs = CPUSchedulerEngine.run_priority_preemptive(processes, reverse_priority)
            mode_desc = "Higher Value Wins" if reverse_priority else "Lower Value Wins"
            self.last_algo_used += f" ({mode_desc})"
        elif algo == "Highest Response Ratio Next (HRRN)":
            results, gantt, logs = CPUSchedulerEngine.run_hrrn(processes)

        self.last_sim_results = results
        
        # Calculate metric averages
        tot_wt, tot_tat = 0, 0
        for p in results:
            tot_wt += p.waiting_time
            tot_tat += p.turnaround_time
        avg_wt = tot_wt / len(results) if results else 0
        avg_tat = tot_tat / len(results) if results else 0
        
        # Render the current layout outputs
        self.display_metrics_and_gantt(results, gantt, "\n".join(logs), avg_wt, avg_tat)

        # Archive metrics data structural matrix into simulation runtime history array
        timestamp_str = datetime.now().strftime("%H:%M:%S")
        record_title = f"[{timestamp_str}] {algo} ({len(results)} Procs)"
        
        snapshot = {
            "title": record_title,
            "algo_used": self.last_algo_used,
            "results": results,
            "gantt": gantt,
            "logs_text": "\n".join(logs),
            "avg_wt": avg_wt,
            "avg_tat": avg_tat,
            "hide_priority": "Priority" not in algo
        }
        
        self.history_records.append(snapshot)
        
        # Insert item into history view tracking list widget
        list_item = QListWidgetItem(record_title)
        self.history_list_widget.addItem(list_item)
        self.history_list_widget.scrollToItem(list_item)

    def display_metrics_and_gantt(self, results, gantt, logs_text, avg_wt, avg_tat, hide_priority_override=None):
        """Helper to draw and update metrics panel fields dynamically."""
        self.txt_logs.setText(logs_text)
        self.output_table.setRowCount(len(results))
        
        for row, p in enumerate(results):
            self.output_table.setItem(row, 0, QTableWidgetItem(str(p.pid)))
            self.output_table.setItem(row, 1, QTableWidgetItem(str(p.arrival_time)))
            self.output_table.setItem(row, 2, QTableWidgetItem(str(p.burst_time)))
            self.output_table.setItem(row, 3, QTableWidgetItem(str(p.priority)))
            self.output_table.setItem(row, 4, QTableWidgetItem(str(p.completion_time)))
            self.output_table.setItem(row, 5, QTableWidgetItem(str(p.turnaround_time)))
            self.output_table.setItem(row, 6, QTableWidgetItem(str(p.waiting_time)))
            
        self.lbl_averages.setText(f"Average Waiting Time: {avg_wt:.2f} ms | Average Turnaround Time: {avg_tat:.2f} ms")
        
        # Apply correct visibility configuration constraints
        hide_p = "Priority" not in self.algo_combo.currentText() if hide_priority_override is None else hide_priority_override
        self.output_table.setColumnHidden(3, hide_p)

        self.gantt_box.setVisible(True)
        self.gantt_view.update_data(gantt)

    def load_historical_record(self, item):
        """Loads and switches dashboard focus view to an archived past simulation run execution state context."""
        clicked_idx = self.history_list_widget.row(item)
        if 0 <= clicked_idx < len(self.history_records):
            snapshot = self.history_records[clicked_idx]
            
            # Temporarily restore engine global parameter values for report tracking metrics matching
            self.last_sim_results = snapshot["results"]
            self.last_algo_used = snapshot["algo_used"]
            
            # Repopulate user workspace display widgets seamlessly
            self.display_metrics_and_gantt(
                snapshot["results"], 
                snapshot["gantt"], 
                snapshot["logs_text"] + "\n\n*** [HISTORY SNAPSHOT VIEW ACTIVE] ***", 
                snapshot["avg_wt"], 
                snapshot["avg_tat"],
                hide_priority_override=snapshot["hide_priority"]
            )

    def clear_history_log(self):
        """Purges history records backend state maps and clears list layout components widget interface elements."""
        self.history_records.clear()
        self.history_list_widget.clear()
        self.txt_logs.append("\n[SYSTEM]: Local runtime execution history archive has been wiped.")

    def export_report(self):
        if not self.last_sim_results:
            self.txt_logs.append("\n[ERROR]: No active simulation results to export. Run a simulation first.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Simulation Report", "", "PDF Files (*.pdf);;All Files (*)")
        if not file_path:
            return
            
        # Ensure file extension is explicitly .pdf
        if not file_path.lower().endswith('.pdf'):
            file_path += '.pdf'
            
        try:
            # Build HTML content for structural PDF formatting with explicit legible styling [cite: 26, 27]
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 30px; color: #2c3e50; }}
                    h2 {{ text-align: center; color: #2c3e50; border-bottom: 2px solid #34495e; padding-bottom: 12px; font-size: 20px; }}
                    p {{ font-size: 14px; margin-bottom: 8px; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                    th, td {{ border: 1px solid #bdc3c7; padding: 10px; text-align: center; font-size: 13px; }}
                    th {{ background-color: #f8f9fa; font-weight: bold; color: #2c3e50; }}
                    .summary {{ margin-top: 25px; padding: 15px; background-color: #f1f2f6; border-radius: 6px; border-left: 5px solid #2ecc71; }}
                    .summary p {{ font-weight: bold; font-size: 14px; color: #2c3e50; margin: 5px 0; }}
                </style>
            </head>
            <body>
                <h2>COSMOS COLLEGE - CPU SCHEDULING SIMULATION REPORT</h2>
                <p><strong>Algorithm Evaluated:</strong> {self.last_algo_used}</p>
                
                <table>
                    <tr>
                        <th>PID</th>
                        <th>Arrival Time</th>
                        <th>Burst Time</th>
                        <th>Completion Time</th>
                        <th>Turnaround (TAT)</th>
                        <th>Waiting (WT)</th>
                    </tr>
            """
            
            tot_wt, tot_tat = 0, 0
            for p in self.last_sim_results:
                html_content += f"""
                    <tr>
                        <td><strong>{p.pid}</strong></td>
                        <td>{p.arrival_time} ms</td>
                        <td>{p.burst_time} ms</td>
                        <td>{p.completion_time} ms</td>
                        <td>{p.turnaround_time} ms</td>
                        <td>{p.waiting_time} ms</td>
                    </tr>
                """
                tot_wt += p.waiting_time
                tot_tat += p.turnaround_time
                
            avg_wt = tot_wt / len(self.last_sim_results)
            avg_tat = tot_tat / len(self.last_sim_results)
            
            html_content += f"""
                </table>
                <div class="summary">
                    <p>AVERAGE WAITING TIME (AWT): &nbsp;&nbsp;&nbsp;&nbsp;{avg_wt:.2f} ms</p>
                    <p>AVERAGE TURNAROUND TIME (ATAT): {avg_tat:.2f} ms</p>
                </div>
            </body>
            </html>
            """
            
            # Setup Printer and Document components [cite: 23, 28]
            document = QTextDocument()
            document.setHtml(html_content)
            
            # Using ScreenResolution so font sizes match expected visual output [cite: 39, 41]
            printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(file_path)
            printer.setPageMargins(QMarginsF(15, 15, 15, 15), QPageLayout.Unit.Millimeter)
            
            # Print document map to storage [cite: 23, 28]
            document.print(printer)
            self.txt_logs.append(f"\n[SYSTEM]: PDF Report successfully saved to: {file_path}")
            
        except Exception as e:
            self.txt_logs.append(f"\n[SYSTEM ERROR]: Could not render PDF document. {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SimulationDashboard()
    window.show()
    sys.exit(app.exec())