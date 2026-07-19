import streamlit as st
import random
import time
def avash():
    # Set up page layout to occupy the full widescreen space
    st.set_page_config(
        page_title="Advanced Concurrency & Deadlock Engine", 
        layout="wide"
    )

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

        def check_safety_state(self):
            work = list(self.available)
            finish = [False] * self.num_processes
            safe_sequence = []

            while len(safe_sequence) < self.num_processes:
                found_executable_process = False
                for i in range(self.num_processes):
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

    # Initialize application persistent state tracking
    if "engine" not in st.session_state:
        init_avail = [3, 3, 2]
        max_demand = [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]]
        current_alloc = [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]]
        st.session_state.engine = BankersAlgorithm(5, 3, init_avail, max_demand, current_alloc)

    if "logs" not in st.session_state:
        st.session_state.logs = [f"[{time.strftime('%H:%M:%S')}] [BOOT] Kernel subsystem initialized successfully."]

    def log_event(level, message):
        st.session_state.logs.append(f"[{time.strftime('%H:%M:%S')}] [{level}] {message}")

    engine = st.session_state.engine

    # =====================================================================
    # FRONTEND WEB INTERFACE
    # =====================================================================
    st.title(" Advanced Concurrency & Deadlock Engine")

    # --- Lifecycle Controls Panel ---
    st.write("### Process & Resource Lifecycle Management")
    ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([1, 1, 1.5, 1.5])

    with ctrl_col1:
        if st.button(" Add New Process", use_container_width=True):
            engine.add_process()
            log_event("KERNEL", f"Added Process P{engine.num_processes - 1}")
            st.rerun()

    with ctrl_col2:
        if st.button(" Add Resource Column", use_container_width=True):
            engine.add_resource_type()
            log_event("KERNEL", f"Added Resource Type R{engine.num_resources - 1}")
            st.rerun()

    with ctrl_col3:
        drop_res_options = [f"R{i}" for i in range(engine.num_resources)]
        selected_res = st.selectbox("Select Column to Delete:", drop_res_options, index=0)
        if st.button(" Delete Column", use_container_width=True, disabled=engine.num_resources <= 1):
            res_idx = drop_res_options.index(selected_res)
            if engine.remove_resource_type(res_idx):
                log_event("KERNEL", f"Deleted Resource Type {selected_res}")
                st.rerun()

    with ctrl_col4:
        kill_proc_options = [f"P{i}" for i in range(engine.num_processes)]
        selected_proc = st.selectbox("Select Process to Delete:", kill_proc_options, index=0)
        if st.button(" Delete Process", use_container_width=True, disabled=engine.num_processes <= 1):
            proc_idx = kill_proc_options.index(selected_proc)
            if engine.remove_targeted_process(proc_idx):
                log_event("KERNEL", f"Terminated Process {selected_proc} & released resources")
                st.rerun()

    st.divider()

    # --- Editable Data Entry Section ---
    st.write("###  System Matrices (Editable)")
    st.caption("Change values inside the input cells below to update matrices in real-time.")

    # Available Vectors Input Row
    st.write("**Available Resources Vector**")
    avail_cols = st.columns(engine.num_resources)
    for j in range(engine.num_resources):
        with avail_cols[j]:
            val = st.number_input(f"R{j}", min_value=0, value=int(engine.available[j]), key=f"avail_{j}")
            if val != engine.available[j]:
                engine.available[j] = val
                log_event("USER", f"Updated Available R{j} to {val}")

    # Build structured columns for the side-by-side matrices
    matrix_col1, matrix_col2, matrix_col3 = st.columns(3)

    with matrix_col1:
        st.write("**Allocation Matrix**")
        for i in range(engine.num_processes):
            cols = st.columns(engine.num_resources)
            for j in range(engine.num_resources):
                with cols[j]:
                    val = st.number_input(f"P{i}, R{j}", min_value=0, value=int(engine.allocation[i][j]), key=f"alloc_{i}_{j}", label_visibility="collapsed")
                    if val != engine.allocation[i][j]:
                        engine.allocation[i][j] = val
                        engine.calculate_need_matrix()
                        log_event("USER", f"Updated Allocation P{i}[R{j}] to {val}")

    with matrix_col2:
        st.write("**Max Demand Matrix**")
        for i in range(engine.num_processes):
            cols = st.columns(engine.num_resources)
            for j in range(engine.num_resources):
                with cols[j]:
                    val = st.number_input(f"P{i}, R{j}", min_value=0, value=int(engine.max_matrix[i][j]), key=f"max_{i}_{j}", label_visibility="collapsed")
                    if val != engine.max_matrix[i][j]:
                        engine.max_matrix[i][j] = val
                        engine.calculate_need_matrix()
                        log_event("USER", f"Updated Max Demand P{i}[R{j}] to {val}")

    with matrix_col3:
        st.write("**Calculated Need Matrix**")
        # Displays the mathematical Need values dynamically calculated by the backend
        for i in range(engine.num_processes):
            cols = st.columns(engine.num_resources)
            for j in range(engine.num_resources):
                with cols[j]:
                    st.text_input(f"Need P{i}, R{j}", value=str(engine.need[i][j]), disabled=True, key=f"need_{i}_{j}", label_visibility="collapsed")

    st.divider()

    # --- Safety Evaluation Engine and Live Logger Panels ---
    side_col1, side_col2 = st.columns([1.5, 1])

    with side_col1:
        st.write("###  Safety Validation Target")
        if st.button(" Evaluate System Safety State", type="primary", use_container_width=True):
            is_safe, sequence = engine.check_safety_state()
            if is_safe:
                seq_str = " ➔ ".join([f"P{x}" for x in sequence])
                st.success(f"**System is SAFE!** Found an executable sequence: **{seq_str}**")
                log_event("SAFETY", f"Verification PASSED. Safe Sequence: {seq_str}")
            else:
                st.error(" **System is UNSAFE!** Deadlock condition or starvation detected.")
                log_event("SAFETY", "Verification FAILED. Deadlock scenario footprint identified.")

    with side_col2:
        st.write("###  System Activity Logs")
        # Text container to emulate the original QTextEdit read-only view
        log_text = "\n".join(st.session_state.logs[::-1])  # Show newest log on top
        st.text_area("Kernel Operations", value=log_text, height=180, disabled=True, label_visibility="collapsed")