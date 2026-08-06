import copy
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# Banker's Algorithm backend
# ============================================================

class BankersAlgorithm:
    def __init__(
        self,
        num_processes,
        num_resources,
        available,
        max_matrix,
        allocation
    ):
        self.num_processes = num_processes
        self.num_resources = num_resources
        self.available = list(available)
        self.max_matrix = [
            list(row)
            for row in max_matrix
        ]
        self.allocation = [
            list(row)
            for row in allocation
        ]
        self.calculate_need_matrix()

    def calculate_need_matrix(self):
        self.need = []

        for process_index in range(self.num_processes):
            row = []

            for resource_index in range(self.num_resources):
                value = (
                    self.max_matrix[process_index][resource_index]
                    - self.allocation[process_index][resource_index]
                )

                row.append(max(0, value))

            self.need.append(row)

    def add_resource_type(self):
        import random

        self.num_resources += 1
        self.available.append(random.randint(2, 5))

        for process_index in range(self.num_processes):
            self.max_matrix[process_index].append(
                random.randint(2, 6)
            )
            self.allocation[process_index].append(
                random.randint(0, 1)
            )

        self.calculate_need_matrix()

    def remove_resource_type(self, resource_index):
        if self.num_resources <= 1:
            return False

        if not 0 <= resource_index < self.num_resources:
            return False

        self.available.pop(resource_index)

        for process_index in range(self.num_processes):
            self.max_matrix[process_index].pop(resource_index)
            self.allocation[process_index].pop(resource_index)

        self.num_resources -= 1
        self.calculate_need_matrix()

        return True

    def add_process(self):
        import random

        new_maximum = [
            random.randint(3, 7)
            for _ in range(self.num_resources)
        ]

        new_allocation = [
            random.randint(0, 1)
            for _ in range(self.num_resources)
        ]

        self.max_matrix.append(new_maximum)
        self.allocation.append(new_allocation)
        self.num_processes += 1

        self.calculate_need_matrix()

    def remove_process(self, process_index):
        if self.num_processes <= 1:
            return False

        if not 0 <= process_index < self.num_processes:
            return False

        for resource_index in range(self.num_resources):
            self.available[resource_index] += (
                self.allocation[process_index][resource_index]
            )

        self.max_matrix.pop(process_index)
        self.allocation.pop(process_index)
        self.num_processes -= 1

        self.calculate_need_matrix()

        return True

    def ready_candidates(self, work, finished):
        candidates = []

        for process_index in range(self.num_processes):
            if finished[process_index]:
                continue

            can_run = all(
                self.need[process_index][resource_index]
                <= work[resource_index]
                for resource_index in range(self.num_resources)
            )

            if can_run:
                candidates.append(process_index)

        return candidates

    def calculate_safe_sequence(
        self,
        tie_breaking="Ask me"
    ):
        work = list(self.available)
        finished = [False] * self.num_processes
        sequence = []
        trace = []

        while len(sequence) < self.num_processes:
            candidates = self.ready_candidates(
                work,
                finished
            )

            if not candidates:
                return False, sequence, trace, []

            if len(candidates) == 1:
                selected = candidates[0]

            elif tie_breaking == "Ascending":
                selected = min(candidates)

            elif tie_breaking == "Descending":
                selected = max(candidates)

            else:
                return (
                    None,
                    sequence,
                    trace,
                    candidates
                )

            before = list(work)

            for resource_index in range(self.num_resources):
                work[resource_index] += (
                    self.allocation[selected][resource_index]
                )

            finished[selected] = True
            sequence.append(selected)

            trace.append(
                {
                    "Process": f"P{selected}",
                    "Work Before": before,
                    "Allocation Returned": list(
                        self.allocation[selected]
                    ),
                    "Work After": list(work)
                }
            )

        return True, sequence, trace, []


# ============================================================
# Session state
# ============================================================

def default_engine():
    return BankersAlgorithm(
        num_processes=5,
        num_resources=3,
        available=[3, 3, 2],
        max_matrix=[
            [7, 5, 3],
            [3, 2, 2],
            [9, 0, 2],
            [2, 2, 2],
            [4, 3, 3]
        ],
        allocation=[
            [0, 1, 0],
            [2, 0, 0],
            [3, 0, 2],
            [2, 1, 1],
            [0, 0, 2]
        ]
    )


def initialize_deadlock_state():
    if "deadlock_engine" not in st.session_state:
        st.session_state.deadlock_engine = default_engine()

    if "deadlock_logs" not in st.session_state:
        st.session_state.deadlock_logs = [
            "[BOOT] Kernel subsystem initialized successfully."
        ]

    if "deadlock_history" not in st.session_state:
        st.session_state.deadlock_history = []

    if "deadlock_result" not in st.session_state:
        st.session_state.deadlock_result = None


def get_engine():
    return st.session_state.deadlock_engine


def add_log(level, message):
    timestamp = datetime.now().strftime("%H:%M:%S")

    st.session_state.deadlock_logs.append(
        f"[{timestamp}] [{level}] {message}"
    )


def create_snapshot(description):
    engine = get_engine()

    return {
        "description": description,
        "available": copy.deepcopy(engine.available),
        "max_matrix": copy.deepcopy(engine.max_matrix),
        "allocation": copy.deepcopy(engine.allocation),
        "result": copy.deepcopy(
            st.session_state.deadlock_result
        ),
        "logs": copy.deepcopy(
            st.session_state.deadlock_logs
        )
    }


def save_history(description):
    st.session_state.deadlock_history.append(
        create_snapshot(description)
    )


def restore_snapshot(snapshot):
    engine = get_engine()

    engine.available = copy.deepcopy(
        snapshot["available"]
    )

    engine.max_matrix = copy.deepcopy(
        snapshot["max_matrix"]
    )

    engine.allocation = copy.deepcopy(
        snapshot["allocation"]
    )

    engine.num_processes = len(engine.max_matrix)

    engine.num_resources = len(engine.available)

    engine.calculate_need_matrix()

    st.session_state.deadlock_result = copy.deepcopy(
        snapshot["result"]
    )

    st.session_state.deadlock_logs = copy.deepcopy(
        snapshot["logs"]
    )


# ============================================================
# Matrix helpers
# ============================================================

def resource_names(count):
    return [
        chr(65 + index)
        for index in range(count)
    ]


def matrix_dataframe(matrix, process_count, resource_count):
    columns = resource_names(resource_count)

    frame = pd.DataFrame(
        matrix,
        columns=columns
    )

    frame.index = [
        f"P{index}"
        for index in range(process_count)
    ]

    return frame


def available_dataframe(values):
    return pd.DataFrame(
        [values],
        columns=resource_names(len(values)),
        index=["Available"]
    )


def dataframe_to_matrix(frame):
    cleaned = frame.fillna(0)

    return [
        [
            max(0, int(value))
            for value in row
        ]
        for row in cleaned.values.tolist()
    ]


def dataframe_to_vector(frame):
    cleaned = frame.fillna(0)

    return [
        max(0, int(value))
        for value in cleaned.iloc[0].tolist()
    ]


# ============================================================
# Resource Allocation Graph
# ============================================================

def render_resource_allocation_graph(engine):
    figure = go.Figure()

    process_count = engine.num_processes
    resource_count = engine.num_resources

    process_x = []
    process_y = []

    resource_x = []
    resource_y = []

    center_x = 0
    center_y = 0
    process_radius = 4
    resource_radius = 1.8

    for index in range(process_count):
        angle = (
            (2 * 3.14159 * index) / process_count
            - 3.14159 / 2
        )

        process_x.append(
            center_x + process_radius * __import__("math").cos(angle)
        )

        process_y.append(
            center_y + process_radius * __import__("math").sin(angle)
        )

    for index in range(resource_count):
        angle = (
            (2 * 3.14159 * index) / resource_count
            - 3.14159 / 2
            + 3.14159 / (resource_count * 2)
        )

        resource_x.append(
            center_x + resource_radius * __import__("math").cos(angle)
        )

        resource_y.append(
            center_y + resource_radius * __import__("math").sin(angle)
        )

    edge_x = []
    edge_y = []

    for process_index in range(process_count):
        for resource_index in range(resource_count):
            px = process_x[process_index]
            py = process_y[process_index]
            rx = resource_x[resource_index]
            ry = resource_y[resource_index]

            if engine.allocation[process_index][resource_index] > 0:
                edge_x.extend([rx, px, None])
                edge_y.extend([ry, py, None])

            if engine.need[process_index][resource_index] > 0:
                edge_x.extend([px, rx, None])
                edge_y.extend([py, ry, None])

    figure.add_trace(
        go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line=dict(
                color="#f1c40f",
                width=1.5
            ),
            hoverinfo="none",
            name="Edges"
        )
    )

    figure.add_trace(
        go.Scatter(
            x=process_x,
            y=process_y,
            mode="markers+text",
            text=[
                f"P{index}"
                for index in range(process_count)
            ],
            textposition="middle center",
            marker=dict(
                size=38,
                color="#3498db",
                line=dict(
                    color="#2980b9",
                    width=2
                )
            ),
            name="Processes"
        )
    )

    resource_labels = [
        f"{chr(65 + index)}"
        f"<br>({engine.available[index]})"
        for index in range(resource_count)
    ]

    figure.add_trace(
        go.Scatter(
            x=resource_x,
            y=resource_y,
            mode="markers+text",
            text=resource_labels,
            textposition="middle center",
            marker=dict(
                symbol="square",
                size=42,
                color="#2ecc71",
                line=dict(
                    color="#27ae60",
                    width=2
                )
            ),
            name="Resources"
        )
    )

    figure.update_layout(
        height=430,
        paper_bgcolor="#1e272e",
        plot_bgcolor="#1e272e",
        font=dict(color="white"),
        xaxis=dict(
            visible=False,
            range=[-6, 6]
        ),
        yaxis=dict(
            visible=False,
            range=[-6, 6]
        ),
        margin=dict(
            l=10,
            r=10,
            t=25,
            b=10
        ),
        legend=dict(
            orientation="h",
            y=-0.05
        )
    )

    st.plotly_chart(
        figure,
        use_container_width=True,
        config={
            "displayModeBar": False
        }
    )


# ============================================================
# Main Streamlit module
# ============================================================

def avash():
    initialize_deadlock_state()

    engine = get_engine()

    st.markdown(
        """
        <style>
        .deadlock-title {
            color: #3498db;
            font-size: 30px;
            font-weight: bold;
        }

        .safe-box {
            background-color: #1e8449;
            color: white;
            padding: 14px;
            border-radius: 8px;
            font-weight: bold;
        }

        .unsafe-box {
            background-color: #922b21;
            color: white;
            padding: 14px;
            border-radius: 8px;
            font-weight: bold;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="deadlock-title">'
        'Concurrency & Deadlock Avoidance Engine'
        '</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "Configure the system matrices and execute "
        "Banker's Algorithm safety analysis."
    )

    control_left, control_middle, control_right = (
        st.columns(3)
    )

    with control_left:
        if st.button(
            "Add Process",
            use_container_width=True,
            key="deadlock_add_process"
        ):
            engine.add_process()
            add_log(
                "OS_SPAWN",
                f"Spawned Process P{engine.num_processes - 1}."
            )
            save_history("Added process")
            st.rerun()

    with control_middle:
        if st.button(
            "Add Resource",
            use_container_width=True,
            key="deadlock_add_resource"
        ):
            engine.add_resource_type()
            add_log(
                "OS_CONFIG",
                "Added a resource column."
            )
            save_history("Added resource")
            st.rerun()

    with control_right:
        if st.button(
            "Reset Simulation",
            use_container_width=True,
            key="deadlock_reset"
        ):
            st.session_state.deadlock_engine = (
                default_engine()
            )
            st.session_state.deadlock_result = None
            st.session_state.deadlock_logs = [
                "[BOOT] Kernel subsystem initialized successfully."
            ]
            add_log(
                "SYSTEM",
                "Simulation reset to the baseline state."
            )
            st.rerun()

    st.divider()

    available_column, allocation_column = st.columns(2)

    with available_column:
        st.subheader("Available Resources")

        available_frame = st.data_editor(
            available_dataframe(
                engine.available
            ),
            hide_index=True,
            use_container_width=True,
            key="deadlock_available_editor"
        )

    with allocation_column:
        st.subheader("Allocation Matrix")

        allocation_frame = st.data_editor(
            matrix_dataframe(
                engine.allocation,
                engine.num_processes,
                engine.num_resources
            ),
            use_container_width=True,
            key="deadlock_allocation_editor"
        )

    max_column, need_column = st.columns(2)

    with max_column:
        st.subheader("Maximum Demand Matrix")

        maximum_frame = st.data_editor(
            matrix_dataframe(
                engine.max_matrix,
                engine.num_processes,
                engine.num_resources
            ),
            use_container_width=True,
            key="deadlock_maximum_editor"
        )

    engine.available = dataframe_to_vector(
        available_frame
    )

    engine.allocation = dataframe_to_matrix(
        allocation_frame
    )

    engine.max_matrix = dataframe_to_matrix(
        maximum_frame
    )

    engine.calculate_need_matrix()

    with need_column:
        st.subheader("Calculated Need Matrix")

        st.dataframe(
            matrix_dataframe(
                engine.need,
                engine.num_processes,
                engine.num_resources
            ),
            use_container_width=True
        )

    st.divider()

    left_controls, right_graph = st.columns(
        [1, 2]
    )

    with left_controls:
        st.subheader("Safety Check")

        tie_breaking = st.selectbox(
            "When multiple processes are ready",
            [
                "Ask me",
                "Ascending",
                "Descending"
            ],
            key="deadlock_tie_breaking"
        )

        if st.button(
            "Execute Simulation",
            type="primary",
            use_container_width=True,
            key="deadlock_execute"
        ):
            safe, sequence, trace, candidates = (
                engine.calculate_safe_sequence(
                    tie_breaking
                )
            )

            if safe is None:
                st.session_state.deadlock_pending = {
                    "sequence": sequence,
                    "trace": trace,
                    "candidates": candidates
                }

                add_log(
                    "SIM_WAIT",
                    "Multiple valid processes are ready."
                )

            else:
                st.session_state.deadlock_result = {
                    "safe": safe,
                    "sequence": sequence,
                    "trace": trace
                }

                if safe:
                    add_log(
                        "SIM_EXEC",
                        "System is safe. Safe sequence: "
                        + " -> ".join(
                            f"P{index}"
                            for index in sequence
                        )
                    )
                else:
                    add_log(
                        "SIM_EXEC",
                        "Deadlock detected. No safe sequence exists."
                    )

                save_history(
                    "Executed safety simulation"
                )

        pending = st.session_state.get(
            "deadlock_pending"
        )

        if pending:
            st.warning(
                "Multiple processes can execute next. "
                "Choose one."
            )

            selected_process = st.selectbox(
                "Select the next process",
                pending["candidates"],
                format_func=lambda index: f"P{index}",
                key="deadlock_pending_choice"
            )

            if st.button(
                "Continue With Selected Process",
                key="deadlock_continue"
            ):
                selected_sequence = (
                    pending["sequence"]
                    + [selected_process]
                )

                remaining_work = list(engine.available)

                for process_index in selected_sequence:
                    for resource_index in range(
                        engine.num_resources
                    ):
                        remaining_work[resource_index] += (
                            engine.allocation[
                                process_index
                            ][resource_index]
                        )

                finished = [
                    False
                    for _ in range(engine.num_processes)
                ]

                for process_index in selected_sequence:
                    finished[process_index] = True

                candidates = engine.ready_candidates(
                    remaining_work,
                    finished
                )

                st.session_state.deadlock_pending = None

                if not candidates:
                    safe = all(finished)

                    st.session_state.deadlock_result = {
                        "safe": safe,
                        "sequence": selected_sequence,
                        "trace": []
                    }

                st.rerun()

        result = st.session_state.get(
            "deadlock_result"
        )

        if result:
            if result["safe"]:
                st.markdown(
                    '<div class="safe-box">'
                    'STATUS: SYSTEM SAFE'
                    '</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<div class="unsafe-box">'
                    'STATUS: DEADLOCK DETECTED'
                    '</div>',
                    unsafe_allow_html=True
                )

            if result["sequence"]:
                st.write(
                    "**Safe sequence:** "
                    + " → ".join(
                        f"P{index}"
                        for index in result["sequence"]
                    )
                )
            else:
                st.write(
                    "**Safe sequence:** None"
                )

    with right_graph:
        st.subheader("Resource Allocation Graph")
        render_resource_allocation_graph(engine)

    st.divider()

    log_column, history_column = st.columns(2)

    with log_column:
        st.subheader("Kernel Space Console Logs")

        st.code(
            "\n".join(
                st.session_state.deadlock_logs
            ),
            language="text"
        )

    with history_column:
        st.subheader("Action History")

        history = st.session_state.deadlock_history

        if history:
            history_labels = [
                item["description"]
                for item in history
            ]

            selected_history = st.selectbox(
                "Select saved state",
                range(len(history_labels)),
                format_func=lambda index: (
                    history_labels[index]
                ),
                key="deadlock_history_selector"
            )

            if st.button(
                "Restore Selected State",
                key="deadlock_restore"
            ):
                restore_snapshot(
                    history[selected_history]
                )
                st.rerun()

            if st.button(
                "Clear History",
                key="deadlock_clear_history"
            ):
                st.session_state.deadlock_history = []
                st.rerun()
        else:
            st.info("No saved history entries yet.")