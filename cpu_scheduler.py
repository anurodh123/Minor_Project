import sys
import copy
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTableWidget, QTableWidgetItem, QPushButton, QComboBox, 
    QLabel, QSpinBox, QHeaderView, QGroupBox, QTextEdit, QFileDialog,
    QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt

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
# 2. SCHEDULER ENGINE WITH LOG LOGIC LOOPS (INCLUDING HRRN)
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
            logs.append(f"[Time {current_time}]: Process {p.pid} terminated (Completion={p.completion_time}, WT={p.waiting_time}).")
            
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
                logs.append(f"[Time {current_time}]: CPU IDLE. Advancing time to next arrival at {next_proc.arrival_time}.")
                current_time = next_proc.arrival_time
                continue
                
            chosen = min(available, key=lambda x: x.burst_time)
            start = current_time
            logs.append(f"[Time {start}]: Selecting Process {chosen.pid} (Burst={chosen.burst_time}) out of {len(available)} ready jobs.")
            current_time += chosen.burst_time
            
            chosen.completion_time = current_time
            chosen.turnaround_time = chosen.completion_time - chosen.arrival_time
            chosen.waiting_time = chosen.turnaround_time - chosen.burst_time
            
            gantt.append((chosen.pid, start, current_time))
            completed.append(chosen)
            logs.append(f"[Time {current_time}]: Process {chosen.pid} completed execution loop.")
            
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
                logs.append(f"[Time {current_time}]: Ready queue empty. CPU idling.")
                current_time = next_arrival
                continue
                
            chosen = min(available, key=lambda x: x.remaining_time)
            
            if chosen.pid != last_pid:
                if last_pid is not None:
                    gantt.append((last_pid, block_start, current_time))
                    logs.append(f"[Time {current_time}]: Preemption event! Context switching from Process {last_pid} to Process {chosen.pid}.")
                else:
                    logs.append(f"[Time {current_time}]: Loading Process {chosen.pid} into active CPU core.")
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
                logs.append(f"[Time {current_time}]: Process {chosen.pid} fully calculated and closed out.")
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
                    logs.append(f"[Time {current_time}]: Process {p.pid} arrived and added to FIFO queue.")

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
            logs.append(f"[Time {start}]: Allocating CPU to Process {curr_p.pid} (Remaining={curr_p.remaining_time}).")
            
            if curr_p.remaining_time > time_quantum:
                curr_p.remaining_time -= time_quantum
                current_time += time_quantum
                check_new_arrivals()
                ready_queue.append(curr_p)
                gantt.append((curr_p.pid, start, current_time))
                logs.append(f"[Time {current_time}]: Quantum expired. Interrupted Process {curr_p.pid} moved to queue tail.")
            else:
                current_time += curr_p.remaining_time
                curr_p.remaining_time = 0
                curr_p.completion_time = current_time
                curr_p.turnaround_time = curr_p.completion_time - curr_p.arrival_time
                curr_p.waiting_time = curr_p.turnaround_time - curr_p.burst_time
                completed_count += 1
                gantt.append((curr_p.pid, start, current_time))
                logs.append(f"[Time {current_time}]: Process {curr_p.pid} finished completely.")
                check_new_arrivals()
                
        return procs, gantt, logs

    @staticmethod
    def run_priority_non_preemptive(processes, reverse_priority=False):
        procs = [copy.deepcopy(p) for p in processes]
        gantt = []
        logs = []
        current_time = 0
        completed = []
        
        mode_str = "Higher Value = Higher Priority" if reverse_priority else "Lower Value = Higher Priority"
        logs.append(f"[Time 0]: Non-Preemptive Priority scheduler initialized ({mode_str}).")
        
        while len(completed) < len(processes):
            available = [p for p in procs if p.arrival_time <= current_time and p not in completed]
            
            if not available:
                next_proc = min([p for p in procs if p not in completed], key=lambda x: x.arrival_time)
                gantt.append(("IDLE", current_time, next_proc.arrival_time))
                current_time = next_proc.arrival_time
                continue
            
            # Sort matching user priority configuration rule
            if reverse_priority:
                chosen = max(available, key=lambda x: (x.priority, -x.arrival_time))
            else:
                chosen = min(available, key=lambda x: (x.priority, x.arrival_time))
                
            start = current_time
            logs.append(f"[Time {start}]: Executing Process {chosen.pid} based on requested priority metric rules ({chosen.priority}).")
            current_time += chosen.burst_time
            
            chosen.completion_time = current_time
            chosen.turnaround_time = chosen.completion_time - chosen.arrival_time
            chosen.waiting_time = chosen.turnaround_time - chosen.burst_time
            
            gantt.append((chosen.pid, start, current_time))
            completed.append(chosen)
            logs.append(f"[Time {current_time}]: Finished Priority process {chosen.pid}.")
            
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
        
        mode_str = "Higher Value = Higher Priority" if reverse_priority else "Lower Value = Higher Priority"
        logs.append(f"[Time 0]: Preemptive Priority Scheduling core active ({mode_str}).")
        
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
            
            # Select matching rule matching user configuration settings
            if reverse_priority:
                chosen = max(available, key=lambda x: (x.priority, -x.arrival_time))
            else:
                chosen = min(available, key=lambda x: (x.priority, x.arrival_time))
            
            if chosen.pid != last_pid:
                if last_pid is not None:
                    gantt.append((last_pid, block_start, current_time))
                    logs.append(f"[Time {current_time}]: Preemption via priority shift! Process {chosen.pid} took core from {last_pid}.")
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
                logs.append(f"[Time {current_time}]: Finished priority task {chosen.pid}.")
                block_start = current_time
                
        return procs, gantt, logs

    @staticmethod
    def run_hrrn(processes):
        """Highest Response Ratio Next (HRRN) Scheduling Logic Loop"""
        procs = [copy.deepcopy(p) for p in processes]
        gantt = []
        logs = []
        current_time = 0
        completed = []
        
        logs.append(f"[Time 0]: Highest Response Ratio Next (HRRN) Engine online.")
        while len(completed) < len(processes):
            available = [p for p in procs if p.arrival_time <= current_time and p not in completed]
            
            if not available:
                next_proc = min([p for p in procs if p not in completed], key=lambda x: x.arrival_time)
                gantt.append(("IDLE", current_time, next_proc.arrival_time))
                logs.append(f"[Time {current_time}]: CPU IDLE. Advancing clock directly to next process arrival at {next_proc.arrival_time}.")
                current_time = next_proc.arrival_time
                continue
                
            logs.append(f"[Time {current_time}]: Evaluating Response Ratios for active jobs:")
            highest_ratio = -1
            chosen = None
            
            for p in available:
                wait_time = current_time - p.arrival_time
                ratio = (wait_time + p.burst_time) / p.burst_time
                logs.append(f" -> Process {p.pid}: Wait={wait_time}, Burst={p.burst_time} => Response Ratio = {ratio:.2f}")
                
                if ratio > highest_ratio:
                    highest_ratio = ratio
                    chosen = p
            
            start = current_time
            logs.append(f"[Time {start}]: Dispatched Process {chosen.pid} with the Highest Response Ratio ({highest_ratio:.2f}).")
            
            current_time += chosen.burst_time
            chosen.completion_time = current_time
            chosen.turnaround_time = chosen.completion_time - chosen.arrival_time
            chosen.waiting_time = chosen.turnaround_time - chosen.burst_time
            
            gantt.append((chosen.pid, start, current_time))
            completed.append(chosen)
            logs.append(f"[Time {current_time}]: Non-preemptive block finished for Process {chosen.pid}.")
            
        return procs, gantt, logs

# ==============================================================================
# 3. INTERACTIVE DASHBOARD SYSTEM
# ==============================================================================
class SimulationDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cosmos College - Interactive CPU Scheduler Dashboard")
        self.resize(1200, 800)
        
        self.last_sim_results = None
        self.last_algo_used = ""
        
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
        
        # Round Robin Inputs
        self.lbl_quantum = QLabel("Time Quantum:")
        config_layout.addWidget(self.lbl_quantum)
        self.quantum_spin = QSpinBox()
        self.quantum_spin.setRange(1, 20)
        self.quantum_spin.setValue(2)
        config_layout.addWidget(self.quantum_spin)
        
        # Priority Radio Selection Logic Setup (Ascending vs Descending Sort)
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
        
        # --- Middle Process Setup Matrix (Dynamic Rows) ---
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
        
        # --- Visual Gantt Sequence Generation Bar ---
        gantt_box = QGroupBox("Visual Gantt Timeline Stream")
        self.gantt_layout = QHBoxLayout()
        gantt_box.setLayout(self.gantt_layout)
        main_layout.addWidget(gantt_box)
        
        # --- Middle Bottom Split Layout (Analytics vs Logs) ---
        bottom_split = QHBoxLayout()
        
        output_box = QGroupBox("Analytics & Performance Metrics")
        output_layout = QVBoxLayout()
        
        # Updated output table to include Optional Priority column mapping (7 columns total)
        self.output_table = QTableWidget(0, 7)
        self.output_table.setHorizontalHeaderLabels([
            "Process ID", "Arrival Time", "Burst Time", "Priority", "Completion Time", "Turnaround Time", "Waiting Time"
        ])
        self.output_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        output_layout.addWidget(self.output_table)
        
        self.lbl_averages = QLabel("Average Waiting Time: -- | Average Turnaround Time: --")
        self.lbl_averages.setStyleSheet("font-size: 13px; font-weight: bold; color: #2c3e50;")
        output_layout.addWidget(self.lbl_averages)
        output_box.setLayout(output_layout)
        bottom_split.addWidget(output_box, stretch=3)
        
        # State Verification Simulation Log
        log_box = QGroupBox("Step-by-Step State Transition Verification Log")
        log_layout = QVBoxLayout()
        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setStyleSheet("background-color: #2c3e50; color: #1abc9c; font-family: Consolas; font-size: 11px;")
        log_layout.addWidget(self.txt_logs)
        log_box.setLayout(log_layout)
        bottom_split.addWidget(log_box, stretch=2)
        
        main_layout.addLayout(bottom_split)
        self.toggle_inputs()
        
    def toggle_inputs(self):
        algo = self.algo_combo.currentText()
        is_rr = (algo == "Round Robin")
        is_priority_algo = "Priority" in algo
        
        # Toggle Time Quantum Visibility
        self.lbl_quantum.setVisible(is_rr)
        self.quantum_spin.setVisible(is_rr)
        
        # Toggle Priority Sorting Order Radio Options Visibility
        self.lbl_priority_rule.setVisible(is_priority_algo)
        self.radio_low_high.setVisible(is_priority_algo)
        self.radio_high_low.setVisible(is_priority_algo)
        
        # Dynamic Column Filtering: Priority column is Index 3 on input_table and Index 3 on output_table
        if is_priority_algo:
            self.input_table.setColumnHidden(3, False)
            self.output_table.setColumnHidden(3, False)
        else:
            self.input_table.setColumnHidden(3, True)
            self.output_table.setColumnHidden(3, True)

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
                
                # Check priority item text safely, default to 0 if hidden/empty
                priority_item = self.input_table.item(row, 3)
                priority = int(priority_item.text() if (priority_item and priority_item.text()) else 0)
                
                processes.append(Process(pid, arr, burst, priority))
            except (ValueError, AttributeError):
                continue
                
        if not processes:
            return

        algo = self.algo_combo.currentText()
        self.last_algo_used = algo
        
        # Read user choice for radio priority order orientation
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

        # Update Logs display
        self.txt_logs.setText("\n".join(logs))

        # Render Output Table metrics
        self.output_table.setRowCount(len(results))
        tot_wt, tot_tat = 0, 0
        for row, p in enumerate(results):
            self.output_table.setItem(row, 0, QTableWidgetItem(str(p.pid)))
            self.output_table.setItem(row, 1, QTableWidgetItem(str(p.arrival_time)))
            self.output_table.setItem(row, 2, QTableWidgetItem(str(p.burst_time)))
            self.output_table.setItem(row, 3, QTableWidgetItem(str(p.priority)))
            self.output_table.setItem(row, 4, QTableWidgetItem(str(p.completion_time)))
            self.output_table.setItem(row, 5, QTableWidgetItem(str(p.turnaround_time)))
            self.output_table.setItem(row, 6, QTableWidgetItem(str(p.waiting_time)))
            tot_wt += p.waiting_time
            tot_tat += p.turnaround_time
            
        avg_wt = tot_wt / len(results)
        avg_tat = tot_tat / len(results)
        self.lbl_averages.setText(f"Average Waiting Time: {avg_wt:.2f} ms | Average Turnaround Time: {avg_tat:.2f} ms")

        # Generate Graphical Gantt blocks
        while self.gantt_layout.count():
            child = self.gantt_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        for block in gantt:
            pid, start, end = block
            duration = end - start
            lbl_block = QLabel(f"{pid}\n({start}-{end})")
            lbl_block.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_block.setMinimumHeight(50)
            
            if pid == "IDLE":
                lbl_block.setStyleSheet("background-color: #bdc3c7; color: #7f8c8d; border: 1px solid gray; border-radius: 4px;")
            else:
                lbl_block.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; border: 1px solid #2980b9; border-radius: 4px;")
                
            self.gantt_layout.addWidget(lbl_block, stretch=duration)

    def export_report(self):
        if not self.last_sim_results:
            self.txt_logs.append("\n[ERROR]: Run a simulation before exporting a report.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Simulation Report", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            with open(file_path, "w") as f:
                f.write("========================================================================\n")
                f.write("          COSMOS COLLEGE - CPU SCHEDULING SIMULATION REPORT            \n")
                f.write("========================================================================\n\n")
                f.write(f"Algorithm Evaluated: {self.last_algo_used}\n")
                f.write(f"Total Process Workload: {len(self.last_sim_results)} processes\n\n")
                f.write("------------------------------------------------------------------------\n")
                
                if "Priority" in self.last_algo_used:
                    f.write("PID\tArrival\tBurst\tPriority\tCompletion\tTurnaround (TAT)\tWaiting (WT)\n")
                else:
                    f.write("PID\tArrival\tBurst\tCompletion\tTurnaround (TAT)\tWaiting (WT)\n")
                    
                f.write("------------------------------------------------------------------------\n")
                
                tot_wt, tot_tat = 0, 0
                for p in self.last_sim_results:
                    if "Priority" in self.last_algo_used:
                        f.write(f"{p.pid}\t{p.arrival_time}\t{p.burst_time}\t{p.priority}\t\t{p.completion_time}\t\t{p.turnaround_time}\t\t\t{p.waiting_time}\n")
                    else:
                        f.write(f"{p.pid}\t{p.arrival_time}\t{p.burst_time}\t{p.completion_time}\t\t{p.turnaround_time}\t\t\t{p.waiting_time}\n")
                    tot_wt += p.waiting_time
                    tot_tat += p.turnaround_time
                    
                avg_wt = tot_wt / len(self.last_sim_results)
                avg_tat = tot_tat / len(self.last_sim_results)
                
                f.write("------------------------------------------------------------------------\n")
                f.write(f"AVERAGE WAITING TIME (AWT):     {avg_wt:.2f} ms\n")
                f.write(f"AVERAGE TURNAROUND TIME (ATAT): {avg_tat:.2f} ms\n")
                f.write("========================================================================\n")
                f.write("Report generated successfully via Interactive Simulation UI Framework.\n")
            
            self.txt_logs.append(f"\n[SYSTEM]: Analytical report written to: {file_path}")

# ==============================================================================
# 4. EXECUTION RUNTIME ENTRYPOINT
# ==============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SimulationDashboard()
    window.show()
    sys.exit(app.exec())