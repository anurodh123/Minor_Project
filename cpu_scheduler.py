import copy
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st

def din():

    st.markdown("## CPU Scheduling Simulation")


    def default_process_table():
        return pd.DataFrame(
            [
                {
                    "Process ID": "P1",
                    "Arrival Time": 0,
                    "Burst Time": 3,
                    "Priority": 1
                },
                {
                    "Process ID": "P2",
                    "Arrival Time": 2,
                    "Burst Time": 6,
                    "Priority": 3
                },
                {
                    "Process ID": "P3",
                    "Arrival Time": 4,
                    "Burst Time": 4,
                    "Priority": 2
                },
                {
                    "Process ID": "P4",
                    "Arrival Time": 6,
                    "Burst Time": 5,
                    "Priority": 5
                },
                {
                    "Process ID": "P5",
                    "Arrival Time": 8,
                    "Burst Time": 2,
                    "Priority": 4
                }
            ]
        )

    if "cpu_process_table" not in st.session_state:
        st.session_state.cpu_process_table = (
            default_process_table()
        )

    @dataclass
    class Process:
        pid: str
        arrival_time: int
        burst_time: int
        priority: int = 0
        completion_time: int = 0
        turnaround_time: int = 0
        waiting_time: int = 0
        remaining_time: int = 0

        def __post_init__(self):
            self.remaining_time = self.burst_time


    def finish_process(process, current_time):
        process.completion_time = current_time
        process.turnaround_time = (
            process.completion_time - process.arrival_time
        )
        process.waiting_time = (
            process.turnaround_time - process.burst_time
        )


    class CPUSchedulerEngine:

        @staticmethod
        def run_fcfs(processes):
            procs = sorted(
                copy.deepcopy(processes),
                key=lambda process: process.arrival_time
            )

            gantt = []
            logs = []
            current_time = 0

            logs.append(
                f"[Time 0]: FCFS Engine initialized "
                f"with {len(procs)} processes."
            )

            for process in procs:
                if current_time < process.arrival_time:
                    logs.append(
                        f"[Time {current_time}]: CPU is IDLE. "
                        "Waiting for next arrival."
                    )

                    gantt.append(
                        ("IDLE", current_time, process.arrival_time)
                    )

                    current_time = process.arrival_time

                start_time = current_time

                logs.append(
                    f"[Time {start_time}]: Context Switch -> "
                    f"dispatching Process {process.pid}."
                )

                current_time += process.burst_time

                finish_process(process, current_time)

                gantt.append(
                    (process.pid, start_time, current_time)
                )

                logs.append(
                    f"[Time {current_time}]: "
                    f"Process {process.pid} terminated."
                )

            return procs, gantt, logs

        @staticmethod
        def run_sjf_non_preemptive(processes):
            procs = copy.deepcopy(processes)
            gantt = []
            logs = []
            current_time = 0
            completed = []

            logs.append(
                "[Time 0]: SJF (Non-Preemptive) Engine initialized."
            )

            while len(completed) < len(procs):
                available = [
                    process
                    for process in procs
                    if (
                        process.arrival_time <= current_time
                        and process not in completed
                    )
                ]

                if not available:
                    remaining = [
                        process
                        for process in procs
                        if process not in completed
                    ]

                    next_process = min(
                        remaining,
                        key=lambda process: process.arrival_time
                    )

                    gantt.append(
                        (
                            "IDLE",
                            current_time,
                            next_process.arrival_time
                        )
                    )

                    current_time = next_process.arrival_time
                    continue

                chosen = min(
                    available,
                    key=lambda process: (
                        process.burst_time,
                        process.arrival_time
                    )
                )

                start_time = current_time

                logs.append(
                    f"[Time {start_time}]: Selecting Process "
                    f"{chosen.pid} "
                    f"(Burst={chosen.burst_time})."
                )

                current_time += chosen.burst_time

                finish_process(chosen, current_time)

                gantt.append(
                    (chosen.pid, start_time, current_time)
                )

                completed.append(chosen)

                logs.append(
                    f"[Time {current_time}]: Process "
                    f"{chosen.pid} completed execution."
                )

            return procs, gantt, logs

        @staticmethod
        def run_sjf_preemptive(processes):
            procs = copy.deepcopy(processes)
            gantt = []
            logs = []

            current_time = 0
            completed_count = 0
            last_pid = None
            block_start = 0

            logs.append(
                "[Time 0]: SRTF/SJF "
                "(Preemptive) Engine active."
            )

            while completed_count < len(procs):
                available = [
                    process
                    for process in procs
                    if (
                        process.arrival_time <= current_time
                        and process.remaining_time > 0
                    )
                ]

                if not available:
                    if last_pid is not None:
                        gantt.append(
                            (last_pid, block_start, current_time)
                        )
                        last_pid = None

                    next_arrival = min(
                        process.arrival_time
                        for process in procs
                        if process.remaining_time > 0
                    )

                    gantt.append(
                        ("IDLE", current_time, next_arrival)
                    )

                    current_time = next_arrival
                    continue

                chosen = min(
                    available,
                    key=lambda process: (
                        process.remaining_time,
                        process.arrival_time
                    )
                )

                if chosen.pid != last_pid:
                    if last_pid is not None:
                        gantt.append(
                            (last_pid, block_start, current_time)
                        )

                        logs.append(
                            f"[Time {current_time}]: Preemption! "
                            f"Context switch from {last_pid} "
                            f"to {chosen.pid}."
                        )

                    last_pid = chosen.pid
                    block_start = current_time

                chosen.remaining_time -= 1
                current_time += 1

                if chosen.remaining_time == 0:
                    gantt.append(
                        (chosen.pid, block_start, current_time)
                    )

                    last_pid = None

                    finish_process(chosen, current_time)

                    completed_count += 1

                    logs.append(
                        f"[Time {current_time}]: Process "
                        f"{chosen.pid} fully closed out."
                    )

                    block_start = current_time

            return procs, gantt, logs

        @staticmethod
        def run_round_robin(processes, time_quantum):
            procs = copy.deepcopy(processes)
            gantt = []
            logs = []

            current_time = 0
            ready_queue = []
            visited = [False] * len(procs)
            completed_count = 0

            logs.append(
                f"[Time 0]: Round Robin active "
                f"with Quantum={time_quantum}."
            )

            def check_new_arrivals():
                for index, process in enumerate(procs):
                    if (
                        process.arrival_time <= current_time
                        and not visited[index]
                        and process.remaining_time > 0
                    ):
                        ready_queue.append(process)
                        visited[index] = True

                        logs.append(
                            f"[Time {current_time}]: Process "
                            f"{process.pid} added to ready queue."
                        )

            check_new_arrivals()

            while completed_count < len(procs):
                if not ready_queue:
                    unfinished = [
                        process
                        for process in procs
                        if process.remaining_time > 0
                    ]

                    if unfinished:
                        next_arrival = min(
                            process.arrival_time
                            for process in unfinished
                        )

                        gantt.append(
                            (
                                "IDLE",
                                current_time,
                                next_arrival
                            )
                        )

                        current_time = next_arrival
                        check_new_arrivals()

                    continue

                current_process = ready_queue.pop(0)
                start_time = current_time

                execution_time = min(
                    time_quantum,
                    current_process.remaining_time
                )

                current_process.remaining_time -= execution_time
                current_time += execution_time

                gantt.append(
                    (
                        current_process.pid,
                        start_time,
                        current_time
                    )
                )

                check_new_arrivals()

                if current_process.remaining_time > 0:
                    ready_queue.append(current_process)
                else:
                    finish_process(
                        current_process,
                        current_time
                    )

                    completed_count += 1

            return procs, gantt, logs

        @staticmethod
        def run_priority_non_preemptive(
            processes,
            reverse_priority=False
        ):
            procs = copy.deepcopy(processes)
            gantt = []
            logs = []

            current_time = 0
            completed = []

            if reverse_priority:
                mode = "Higher value = Higher priority"
            else:
                mode = "Lower value = Higher priority"

            logs.append(
                "[Time 0]: Priority "
                f"(Non-Preemptive) Engine initialized. Mode: {mode}."
            )

            while len(completed) < len(procs):
                available = [
                    process
                    for process in procs
                    if (
                        process.arrival_time <= current_time
                        and process not in completed
                    )
                ]

                if not available:
                    remaining = [
                        process
                        for process in procs
                        if process not in completed
                    ]

                    next_process = min(
                        remaining,
                        key=lambda process: process.arrival_time
                    )

                    gantt.append(
                        (
                            "IDLE",
                            current_time,
                            next_process.arrival_time
                        )
                    )

                    current_time = next_process.arrival_time
                    continue

                if reverse_priority:
                    chosen = max(
                        available,
                        key=lambda process: (
                            process.priority,
                            -process.arrival_time
                        )
                    )
                else:
                    chosen = min(
                        available,
                        key=lambda process: (
                            process.priority,
                            process.arrival_time
                        )
                    )

                start_time = current_time
                current_time += chosen.burst_time

                finish_process(chosen, current_time)

                gantt.append(
                    (chosen.pid, start_time, current_time)
                )

                completed.append(chosen)

                logs.append(
                    f"[Time {current_time}]: Process "
                    f"{chosen.pid} completed execution."
                )

            return procs, gantt, logs

        @staticmethod
        def run_priority_preemptive(
            processes,
            reverse_priority=False
        ):
            procs = copy.deepcopy(processes)
            gantt = []
            logs = []

            current_time = 0
            completed_count = 0
            last_pid = None
            block_start = 0

            if reverse_priority:
                mode = "Higher value = Higher priority"
            else:
                mode = "Lower value = Higher priority"

            logs.append(
                "[Time 0]: Priority "
                f"(Preemptive) Engine initialized. Mode: {mode}."
            )

            while completed_count < len(procs):
                available = [
                    process
                    for process in procs
                    if (
                        process.arrival_time <= current_time
                        and process.remaining_time > 0
                    )
                ]

                if not available:
                    if last_pid is not None:
                        gantt.append(
                            (last_pid, block_start, current_time)
                        )
                        last_pid = None

                    next_arrival = min(
                        process.arrival_time
                        for process in procs
                        if process.remaining_time > 0
                    )

                    gantt.append(
                        (
                            "IDLE",
                            current_time,
                            next_arrival
                        )
                    )

                    current_time = next_arrival
                    continue

                if reverse_priority:
                    chosen = max(
                        available,
                        key=lambda process: (
                            process.priority,
                            -process.arrival_time
                        )
                    )
                else:
                    chosen = min(
                        available,
                        key=lambda process: (
                            process.priority,
                            process.arrival_time
                        )
                    )

                if chosen.pid != last_pid:
                    if last_pid is not None:
                        gantt.append(
                            (last_pid, block_start, current_time)
                        )

                        logs.append(
                            f"[Time {current_time}]: Preemption! "
                            f"Context switch to {chosen.pid}."
                        )

                    else:
                        logs.append(
                            f"[Time {current_time}]: "
                            f"Dispatching Process {chosen.pid}."
                        )

                    last_pid = chosen.pid
                    block_start = current_time

                chosen.remaining_time -= 1
                current_time += 1

                if chosen.remaining_time == 0:
                    gantt.append(
                        (chosen.pid, block_start, current_time)
                    )

                    last_pid = None

                    finish_process(chosen, current_time)

                    completed_count += 1
                    block_start = current_time

                    logs.append(
                        f"[Time {current_time}]: Process "
                        f"{chosen.pid} completed execution."
                    )

            return procs, gantt, logs

        @staticmethod
        def run_hrrn(processes):
            procs = copy.deepcopy(processes)
            gantt = []
            logs = []

            current_time = 0
            completed = []

            logs.append(
                "[Time 0]: HRRN Engine initialized."
            )

            while len(completed) < len(procs):
                available = [
                    process
                    for process in procs
                    if (
                        process.arrival_time <= current_time
                        and process not in completed
                    )
                ]

                if not available:
                    remaining = [
                        process
                        for process in procs
                        if process not in completed
                    ]

                    next_process = min(
                        remaining,
                        key=lambda process: process.arrival_time
                    )

                    gantt.append(
                        (
                            "IDLE",
                            current_time,
                            next_process.arrival_time
                        )
                    )

                    current_time = next_process.arrival_time
                    continue

                def response_ratio(process):
                    waiting_time = (
                        current_time - process.arrival_time
                    )

                    return (
                        waiting_time + process.burst_time
                    ) / process.burst_time

                chosen = max(
                    available,
                    key=lambda process: (
                        response_ratio(process),
                        -process.arrival_time
                    )
                )

                ratio = response_ratio(chosen)

                logs.append(
                    f"[Time {current_time}]: Selecting Process "
                    f"{chosen.pid} with response ratio {ratio:.2f}."
                )

                start_time = current_time
                current_time += chosen.burst_time

                finish_process(chosen, current_time)

                gantt.append(
                    (chosen.pid, start_time, current_time)
                )

                completed.append(chosen)

                logs.append(
                    f"[Time {current_time}]: Process "
                    f"{chosen.pid} completed execution."
                )

            return procs, gantt, logs


    def run_selected_algorithm(
        processes,
        algorithm,
        quantum,
        reverse_priority
    ):
        if algorithm == "FCFS":
            return CPUSchedulerEngine.run_fcfs(processes)

        if algorithm == "SJF (Non-Preemptive)":
            return CPUSchedulerEngine.run_sjf_non_preemptive(processes)

        if algorithm == "SJF (Preemptive)":
            return CPUSchedulerEngine.run_sjf_preemptive(processes)

        if algorithm == "Round Robin":
            return CPUSchedulerEngine.run_round_robin(
                processes,
                quantum
            )

        if algorithm == "Priority (Non-Preemptive)":
            return CPUSchedulerEngine.run_priority_non_preemptive(
                processes,
                reverse_priority
            )

        if algorithm == "Priority (Preemptive)":
            return CPUSchedulerEngine.run_priority_preemptive(
                processes,
                reverse_priority
            )

        if algorithm == "Highest Response Ratio Next (HRRN)":
            return CPUSchedulerEngine.run_hrrn(processes)

        raise ValueError(f"Unsupported algorithm: {algorithm}")
    def render_gantt_chart(gantt_data):
        import plotly.graph_objects as go

        if not gantt_data:
            st.info("No Gantt timeline is available yet.")
            return

        figure = go.Figure()

        for pid, start_time, end_time in gantt_data:
            if pid == "IDLE":
                background_color = "#d2d7d9"
                text_color = "#7f8c8d"
            else:
                background_color = "#3498db"
                text_color = "#ffffff"

            figure.add_shape(
                type="rect",
                x0=start_time,
                x1=end_time,
                y0=0,
                y1=1,
                fillcolor=background_color,
                line=dict(
                    color="#1e272e",
                    width=2
                )
            )

            figure.add_annotation(
                x=(start_time + end_time) / 2,
                y=0.5,
                text=str(pid),
                showarrow=False,
                font=dict(
                    color=text_color,
                    size=14
                )
            )

        timeline_end = gantt_data[-1][2]

        figure.update_layout(
            height=155,
            paper_bgcolor="#1e272e",
            plot_bgcolor="#1e272e",
            font=dict(color="white"),
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=45
            ),
            xaxis=dict(
                title="Time",
                range=[0, max(timeline_end, 1)],
                dtick=1,
                gridcolor="#485460",
                zeroline=False
            ),
            yaxis=dict(
                visible=False,
                range=[0, 1]
            ),
            showlegend=False
        )

        st.plotly_chart(
            figure,
            use_container_width=True,
            config={
                "displayModeBar": False
            }
        )


    def results_to_dataframe(results):
        rows = []

        for process in results:
            rows.append(
                {
                    "Process ID": process.pid,
                    "Arrival Time": process.arrival_time,
                    "Burst Time": process.burst_time,
                    "Priority": process.priority,
                    "Completion Time": process.completion_time,
                    "Turnaround Time": process.turnaround_time,
                    "Waiting Time": process.waiting_time
                }
            )

        return pd.DataFrame(rows)


    def create_pdf_report(results, algorithm, average_waiting, average_turnaround):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle
        )

        buffer = BytesIO()

        document = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        story = []

        title = Paragraph(
            "COSMOS COLLEGE - CPU SCHEDULING REPORT",
            styles["Title"]
        )

        algorithm_text = Paragraph(
            f"<b>Algorithm Evaluated:</b> {algorithm}",
            styles["Normal"]
        )

        story.append(title)
        story.append(Spacer(1, 12))
        story.append(algorithm_text)
        story.append(Spacer(1, 16))

        table_data = [
            [
                "PID",
                "Arrival",
                "Burst",
                "Priority",
                "Completion",
                "TAT",
                "WT"
            ]
        ]

        for process in results:
            table_data.append(
                [
                    process.pid,
                    process.arrival_time,
                    process.burst_time,
                    process.priority,
                    process.completion_time,
                    process.turnaround_time,
                    process.waiting_time
                ]
            )

        results_table = Table(table_data)

        results_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#dfe6e9")
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.black
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.grey
                    ),
                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "CENTER"
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold"
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, 0),
                        8
                    )
                ]
            )
        )

        story.append(results_table)
        story.append(Spacer(1, 18))

        story.append(
            Paragraph(
                f"<b>Average Waiting Time:</b> "
                f"{average_waiting:.2f} ms",
                styles["Normal"]
            )
        )

        story.append(
            Paragraph(
                f"<b>Average Turnaround Time:</b> "
                f"{average_turnaround:.2f} ms",
                styles["Normal"]
            )
        )

        document.build(story)

        return buffer.getvalue()
    
    def read_processes_from_table(table):
        processes = []

        for _, row in table.iterrows():
            process_id = str(row.get("Process ID", "")).strip()

            if not process_id:
                continue

            if pd.isna(row.get("Arrival Time")):
                continue

            if pd.isna(row.get("Burst Time")):
                continue

            arrival_time = int(row["Arrival Time"])
            burst_time = int(row["Burst Time"])

            if pd.isna(row.get("Priority")):
                priority = 0
            else:
                priority = int(row["Priority"])

            if arrival_time < 0:
                raise ValueError(
                    f"{process_id}: arrival time cannot be negative."
                )

            if burst_time <= 0:
                raise ValueError(
                    f"{process_id}: burst time must be greater than zero."
                )

            processes.append(
                Process(
                    pid=process_id,
                    arrival_time=arrival_time,
                    burst_time=burst_time,
                    priority=priority
                )
            )

        if not processes:
            raise ValueError(
                "Enter at least one complete process row."
            )

        process_ids = [process.pid for process in processes]

        if len(process_ids) != len(set(process_ids)):
            raise ValueError(
                "Process IDs must be unique."
            )

        return processes


    def show_history():
        history = st.session_state.get(
            "cpu_history",
            []
        )

        if not history:
            return

        st.subheader("Simulation Run History Archive")

        history_titles = [
            record["title"]
            for record in history
        ]

        selected_index = st.selectbox(
            "Select a previous simulation",
            options=range(len(history_titles)),
            format_func=lambda index: history_titles[index],
            key="cpu_history_selector"
        )

        left_column, right_column = st.columns(2)

        with left_column:
            if st.button(
                "Load Selected Run",
                use_container_width=True,
                key="load_cpu_history"
            ):
                st.session_state.cpu_current = (
                    history[selected_index]
                )
                st.rerun()

        with right_column:
            if st.button(
                "Clear History",
                use_container_width=True,
                key="clear_cpu_history"
            ):
                st.session_state.cpu_history = []
                st.session_state.pop("cpu_current", None)
                st.rerun()


    def loader():
        """
        Streamlit entry point used by hub.py.

        The hub imports this function using:

            from cpu_scheduler import din

        and displays it using:

            din()
        """

        st.markdown(
            """
            <style>
            .cpu-title {
                color: #3498db;
                font-size: 30px;
                font-weight: bold;
            }

            .section-box {
                background-color: #1e272e;
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 15px;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="cpu-title">'
            'CPU Scheduling Simulation'
            '</div>',
            unsafe_allow_html=True
        )

        st.caption(
            "Configure processes, execute a scheduling algorithm, "
            "and inspect its timeline and performance metrics."
        )

        if "cpu_process_table" not in st.session_state:
            st.cpu_process_table = default_process_table()

        if "cpu_process_table" not in st.session_state:
            st.session_state.cpu_process_table = (
                default_process_table()
            )

        algorithm_options = [
            "FCFS",
            "SJF (Non-Preemptive)",
            "SJF (Preemptive)",
            "Round Robin",
            "Priority (Non-Preemptive)",
            "Priority (Preemptive)",
            "Highest Response Ratio Next (HRRN)"
        ]

        configuration_left, configuration_middle, configuration_right = (
            st.columns([2, 1, 3])
        )

        with configuration_left:
            algorithm = st.selectbox(
                "Algorithm",
                algorithm_options,
                key="cpu_algorithm"
            )

        with configuration_middle:
            quantum = st.number_input(
                "Time Quantum",
                min_value=1,
                max_value=20,
                value=2,
                step=1,
                disabled=algorithm != "Round Robin",
                key="cpu_quantum"
            )

        with configuration_right:
            priority_is_enabled = "Priority" in algorithm

            reverse_priority = st.radio(
                "Priority Order",
                options=[False, True],
                format_func=lambda value: (
                    "Higher number = higher priority"
                    if value
                    else "Lower number = higher priority"
                ),
                horizontal=True,
                disabled=not priority_is_enabled,
                key="cpu_priority_order"
            )

        st.subheader("Process Management Table")
        visible_input_columns = [
            "Process ID",
            "Arrival Time",
            "Burst Time"
        ]

        if "Priority" in algorithm:
            visible_input_columns.append("Priority")

        edited_table = st.data_editor(
            st.session_state.cpu_process_table,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_order= visible_input_columns,
            key="cpu_process_editor",
            column_config={
                "Process ID": st.column_config.TextColumn(
                    "Process ID",
                    required=True
                ),
                "Arrival Time": st.column_config.NumberColumn(
                    "Arrival Time",
                    min_value=0,
                    step=1
                ),
                "Burst Time": st.column_config.NumberColumn(
                    "Burst Time",
                    min_value=1,
                    step=1
                ),
                "Priority": st.column_config.NumberColumn(
                    "Priority",
                    step=1
                )
                }
            )

        st.session_state.cpu_process_table = edited_table

        execute_column, reset_column = st.columns(2)

        with execute_column:
            execute_clicked = st.button(
                "Execute Simulation",
                type="primary",
                use_container_width=True,
                key="execute_cpu_simulation"
            )

        with reset_column:
            reset_clicked = st.button(
                "Reset Process Table",
                use_container_width=True,
                key="reset_cpu_table"
            )

        if reset_clicked:
            st.session_state.cpu_process_table = (
                default_process_table()
            )
            st.session_state.pop("cpu_current", None)
            st.rerun()

        if execute_clicked:
            try:
                processes = read_processes_from_table(
                    edited_table
                )

                results, gantt, logs = run_selected_algorithm(
                    processes=processes,
                    algorithm=algorithm,
                    quantum=int(quantum),
                    reverse_priority=reverse_priority
                )

                timestamp = datetime.now().strftime(
                    "%H:%M:%S"
                )

                title = (
                    f"[{timestamp}] "
                    f"{algorithm} "
                    f"({len(results)} Procs)"
                )

                current_record = {
                    "title": title,
                    "algorithm": algorithm,
                    "results": results,
                    "gantt": gantt,
                    "logs": logs,
                    "quantum": int(quantum),
                    "reverse_priority": reverse_priority
                }

                st.session_state.cpu_current = current_record

                if "cpu_history" not in st.session_state:
                    st.session_state.cpu_history = []

                st.session_state.cpu_history.append(
                    current_record
                )

            except Exception as error:
                st.error(str(error))

        current_record = st.session_state.get(
            "cpu_current"
        )

        if current_record is not None:
            results = current_record["results"]
            gantt = current_record["gantt"]
            logs = current_record["logs"]
            current_algorithm = current_record["algorithm"]

            average_waiting = sum(
                process.waiting_time
                for process in results
            ) / len(results)

            average_turnaround = sum(
                process.turnaround_time
                for process in results
            ) / len(results)

            st.divider()

            st.subheader("Visual Gantt Timeline")
            render_gantt_chart(gantt)

            st.subheader("Analytics & Performance Metrics")

            result_table = results_to_dataframe(
                results
            )

            is_priority_algorithm = (
                "Priority" in current_algorithm
            )

            if not is_priority_algorithm:
                result_table = result_table.drop(
                    columns=["Priority"]
                )

            st.dataframe(
                result_table,
                use_container_width=True,
                hide_index=True
            )

            average_column_1, average_column_2 = st.columns(2)

            with average_column_1:
                st.metric(
                    "Average Waiting Time",
                    f"{average_waiting:.2f} ms"
                )

            with average_column_2:
                st.metric(
                    "Average Turnaround Time",
                    f"{average_turnaround:.2f} ms"
                )

            st.subheader("State Transition Verification Log")

            st.code(
                "\n".join(logs),
                language="text"
            )

            pdf_data = create_pdf_report(
                results=results,
                algorithm=current_algorithm,
                average_waiting=average_waiting,
                average_turnaround=average_turnaround
            )

            st.download_button(
                label="Export Analytical Report",
                data=pdf_data,
                file_name="cpu_scheduling_report.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="download_cpu_report"
            )

        show_history()
    loader()