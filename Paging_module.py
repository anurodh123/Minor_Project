import time
from io import BytesIO

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from Page_backend import (
    ALGO_ORDER,
    ALGORITHMS,
    ValidationError,
    compare_all,
    parse_ref_string,
    random_refs,
    simulate,
    validate_frames,
)


def frame_text(frame, algorithm):
    if frame is None:
        return "-"

    if algorithm == "clock":
        return f"{frame['page']} ({frame.get('ref_bit', '-')})"

    return str(frame["page"])


def step_dataframe(result, algorithm):
    rows = []

    for index, step in enumerate(result["steps"], start=1):
        frames = [
            frame_text(frame, algorithm)
            for frame in step["frame_state"]
        ]

        if step["hit"]:
            action = "Already in memory"
            status = "Hit"
        elif step["evicted_page"] is None:
            action = "Loaded into empty frame"
            status = "Fault"
        else:
            action = (
                f"Replaced page {step['evicted_page']}"
            )
            status = "Fault"

        rows.append(
            {
                "Step": index,
                "Page": step["page"],
                "Frames": " | ".join(frames),
                "Status": status,
                "Victim": (
                    "-"
                    if step["evicted_page"] is None
                    else str(step["evicted_page"])
                ),
                "Action": action,
            }
        )

    return pd.DataFrame(rows)


def render_frame_visualization(result, algorithm, frame_count):
    steps = result["steps"]

    if not steps:
        st.info("Start the simulation to view the frames.")
        return

    cursor = st.session_state.get(
        "paging_cursor",
        len(steps) - 1
    )

    cursor = max(
        0,
        min(cursor, len(steps) - 1)
    )

    step = steps[cursor]

    st.markdown(
        f"""
        <div style="
            background:#20242f;
            border:1px solid #2c3140;
            border-radius:10px;
            padding:18px;
            margin:10px 0;
        ">
            <h4 style="color:#E8A33D;">
                Reference {cursor + 1} of {len(steps)}
            </h4>
            <p style="color:#EDE8DE;">
                Requested page:
                <strong>{step["page"]}</strong>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    columns = st.columns(frame_count)

    for index, frame in enumerate(step["frame_state"]):
        with columns[index]:
            if frame is None:
                value = "·"
                color = "#262b38"
                border = "#2c3140"
            else:
                value = frame_text(frame, algorithm)
                color = (
                    "#1e3a37"
                    if step["hit"]
                    else "#4a2620"
                )
                border = (
                    "#5FB8B0"
                    if step["hit"]
                    else "#D95F4B"
                )

            st.markdown(
                f"""
                <div style="
                    text-align:center;
                    background:{color};
                    border:2px solid {border};
                    border-radius:8px;
                    padding:22px 4px;
                    color:#EDE8DE;
                    font-size:24px;
                    font-weight:bold;
                ">
                    {value}
                </div>
                <p style="
                    text-align:center;
                    color:#9098AC;
                ">
                    Frame F{index}
                </p>
                """,
                unsafe_allow_html=True
            )

    if step["hit"]:
        st.success(
            f"Page {step['page']} was already in memory."
        )
    elif step["evicted_page"] is None:
        st.error(
            f"Page fault: page {step['page']} was loaded "
            "into an empty frame."
        )
    else:
        st.error(
            f"Page fault: page {step['page']} replaced "
            f"page {step['evicted_page']}."
        )


def create_pdf_report(
    algorithm_key,
    frames,
    references,
    result
):
    from datetime import datetime

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    story = []

    story.append(
        Paragraph(
            "PAGE REPLACEMENT ALGORITHM REPORT",
            styles["Title"]
        )
    )

    story.append(
        Paragraph(
            datetime.now().strftime(
                "Generated on %d %B %Y %H:%M:%S"
            ),
            styles["BodyText"]
        )
    )

    story.append(Spacer(1, 18))

    info = ALGORITHMS[algorithm_key]

    information = [
        ["Algorithm", info["name"]],
        ["Frames", str(frames)],
        [
            "Reference String",
            " ".join(str(x) for x in references)
        ],
        ["Time Complexity", info["time"]],
        ["Space Complexity", info["space"]],
    ]

    info_table = Table(
        information,
        colWidths=[2.2 * inch, 4.3 * inch]
    )

    info_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor("#D9EAD3")
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    8
                ),
            ]
        )
    )

    story.append(
        Paragraph(
            "Simulation Information",
            styles["Heading2"]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 18))

    story.append(
        Paragraph(
            "Step-by-Step Simulation",
            styles["Heading2"]
        )
    )

    rows = [
        [
            "Step",
            "Page",
            "Frames",
            "Status",
            "Victim",
            "Action",
        ]
    ]

    for _, row in step_dataframe(
        result,
        algorithm_key
    ).iterrows():
        rows.append(
            [
                str(row["Step"]),
                str(row["Page"]),
                str(row["Frames"]),
                str(row["Status"]),
                str(row["Victim"]),
                str(row["Action"]),
            ]
        )

    steps_table = Table(
        rows,
        repeatRows=1,
        colWidths=[
            0.5 * inch,
            0.5 * inch,
            1.8 * inch,
            0.7 * inch,
            0.6 * inch,
            2.0 * inch,
        ],
    )

    steps_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#4472C4")
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER"
                ),
                (
                    "BACKGROUND",
                    (0, 1),
                    (-1, -1),
                    colors.HexColor("#F8F9FA")
                ),
            ]
        )
    )

    story.append(steps_table)
    story.append(Spacer(1, 18))

    hits = result["hits"]
    faults = result["faults"]
    total = hits + faults

    statistics = [
        ["Total References", str(total)],
        ["Page Hits", str(hits)],
        ["Page Faults", str(faults)],
        [
            "Hit Ratio",
            f"{hits / total * 100:.2f}%"
            if total else "0.00%"
        ],
        [
            "Fault Ratio",
            f"{faults / total * 100:.2f}%"
            if total else "0.00%"
        ],
        ["Page Replacements", str(result["replacements"])],
    ]

    story.append(
        Paragraph(
            "Simulation Statistics",
            styles["Heading2"]
        )
    )

    stats_table = Table(
        statistics,
        colWidths=[2.5 * inch, 3.0 * inch]
    )

    stats_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor("#FFF2CC")
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    8
                ),
            ]
        )
    )

    story.append(stats_table)
    document.build(story)

    return buffer.getvalue()


def render_simulation_tab():
    st.subheader("Simulation")

    default_refs = "7,0,1,2,0,3,0,4,2,3,0,3,2"

    if "paging_refs" not in st.session_state:
        st.session_state.paging_refs = default_refs

    if "paging_reference_input" not in st.session_state:
        st.session_state.paging_reference_input = default_refs

    if "paging_frames" not in st.session_state:
        st.session_state.paging_frames = 3

    if "paging_algorithm" not in st.session_state:
        st.session_state.paging_algorithm = "fifo"

    if "paging_result" not in st.session_state:
        st.session_state.paging_result = None

    if "paging_cursor" not in st.session_state:
        st.session_state.paging_cursor = -1

    if "paging_playing" not in st.session_state:
        st.session_state.paging_playing = False

    if "paging_speed_label" not in st.session_state:
        st.session_state.paging_speed_label = "Normal"

    # A widget's session_state key cannot be written to after that widget
    # has already been instantiated in the same script run. To let the
    # "Generate Random References" button push a new value into the
    # reference-string box, it stores the new text in a "pending" slot and
    # reruns; this block applies that pending value *before* the text_input
    # below is created, which is what actually makes the button work.
    if "paging_pending_refs" in st.session_state:
        st.session_state.paging_refs = st.session_state.pop("paging_pending_refs")
        st.session_state.paging_reference_input = st.session_state.paging_refs

    left, middle, right = st.columns([2, 1, 2])

    with left:
        reference_text = st.text_input(
            "Reference string",
            key="paging_reference_input"
        )

    with middle:
        frame_count = st.number_input(
            "Memory frames",
            min_value=1,
            max_value=10,
            value=st.session_state.paging_frames,
            step=1,
            key="paging_frame_input"
        )

    with right:
        algorithm_key = st.selectbox(
            "Algorithm",
            ALGO_ORDER,
            format_func=lambda key: (
                f"{ALGORITHMS[key]['label']} — "
                f"{ALGORITHMS[key]['name']}"
            ),
            key="paging_algorithm_input"
        )

    generate_left, generate_middle, generate_right = (
        st.columns([1, 1, 2])
    )

    with generate_left:
        random_length = st.number_input(
            "Random length",
            min_value=1,
            max_value=500,
            value=16,
            key="paging_random_length"
        )

    with generate_middle:
        random_max = st.number_input(
            "Maximum page",
            min_value=0,
            max_value=999,
            value=6,
            key="paging_random_max"
        )

    with generate_right:
        st.write("")
        if st.button(
            "Generate Random References",
            use_container_width=True,
            key="paging_generate"
        ):
            try:
                generated = random_refs(
                    int(random_length),
                    int(random_max)
                )

                new_refs = ",".join(str(x) for x in generated)

                # Don't touch paging_refs / paging_reference_input directly
                # here — the reference_text widget above has already been
                # instantiated this run. Stash the value and rerun; the
                # pending-refs block at the top of this function applies it
                # on the next run, before the widget is recreated.
                st.session_state.paging_pending_refs = new_refs
                st.session_state.paging_playing = False
                st.rerun()

            except ValidationError as error:
                st.error(str(error))

    run_clicked = st.button(
        "Run Simulation",
        type="primary",
        use_container_width=True,
        key="paging_run"
    )

    if run_clicked:
        try:
            references = parse_ref_string(
                reference_text
            )

            result = simulate(
                algorithm_key,
                references,
                int(frame_count)
            )

            st.session_state.paging_refs = reference_text
            st.session_state.paging_frames = int(frame_count)
            st.session_state.paging_algorithm = algorithm_key
            st.session_state.paging_result = result
            st.session_state.paging_cursor = 0
            st.session_state.paging_playing = False

        except ValidationError as error:
            st.error(str(error))

    result = st.session_state.paging_result

    if result is None:
        st.info(
            "Configure the simulation and click "
            "Run Simulation."
        )
        return

    if st.session_state.paging_cursor < 0:
        st.session_state.paging_cursor = 0

    total_steps = len(result["steps"])
    at_last_step = st.session_state.paging_cursor >= total_steps - 1

    if at_last_step:
        st.session_state.paging_playing = False

    st.markdown("##### Playback controls")

    restart_col, prev_col, play_col, next_col, speed_col = st.columns(
        [1, 1, 1.2, 1, 1.6]
    )

    with restart_col:
        if st.button(
            "⟲ Restart",
            use_container_width=True,
            key="paging_restart"
        ):
            st.session_state.paging_cursor = 0
            st.session_state.paging_playing = False
            st.rerun()

    with prev_col:
        if st.button(
            "◀ Previous",
            use_container_width=True,
            key="paging_prev",
            disabled=st.session_state.paging_cursor <= 0
        ):
            st.session_state.paging_playing = False
            st.session_state.paging_cursor = max(
                st.session_state.paging_cursor - 1, 0
            )
            st.rerun()

    with play_col:
        is_playing = st.session_state.paging_playing
        play_label = "⏸ Pause" if is_playing else "▶ Play"

        if st.button(
            play_label,
            use_container_width=True,
            type="primary",
            key="paging_play_pause",
            disabled=at_last_step and not is_playing
        ):
            st.session_state.paging_playing = not is_playing
            st.rerun()

    with next_col:
        if st.button(
            "Next ▶",
            use_container_width=True,
            key="paging_next",
            disabled=at_last_step
        ):
            st.session_state.paging_playing = False
            st.session_state.paging_cursor = min(
                st.session_state.paging_cursor + 1,
                total_steps - 1
            )
            st.rerun()

    with speed_col:
        speed_label = st.select_slider(
            "Playback speed",
            options=["Slow", "Normal", "Fast", "Very fast"],
            value=st.session_state.paging_speed_label,
            key="paging_speed_label"
        )

    speed_seconds = {
        "Slow": 1.4,
        "Normal": 0.9,
        "Fast": 0.5,
        "Very fast": 0.25,
    }[speed_label]

    st.progress(
        (st.session_state.paging_cursor + 1) / total_steps,
        text=(
            f"Reference {st.session_state.paging_cursor + 1} "
            f"of {total_steps}"
        )
    )

    render_frame_visualization(
        result,
        algorithm_key,
        int(frame_count)
    )

    stats_left, stats_middle, stats_right = st.columns(3)

    with stats_left:
        st.metric("Hits", result["hits"])

    with stats_middle:
        st.metric("Faults", result["faults"])

    with stats_right:
        st.metric(
            "Hit Ratio",
            f"{result['hit_ratio'] * 100:.2f}%"
        )

    if st.session_state.paging_playing:
        st.caption(
            "▶ Playing — pause to view the full step table "
            "and download the PDF report."
        )
    else:
        st.subheader("Step-by-Step Simulation")

        st.dataframe(
            step_dataframe(
                result,
                algorithm_key
            ),
            use_container_width=True,
            hide_index=True
        )

        pdf_bytes = create_pdf_report(
            algorithm_key,
            int(frame_count),
            parse_ref_string(reference_text),
            result
        )

        st.download_button(
            "Download PDF Report",
            data=pdf_bytes,
            file_name="page_replacement_report.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="paging_pdf_download"
        )

    # Autoplay driver: advance one step, pause briefly so the frame is
    # visible, then rerun. Stops automatically at the last reference.
    if st.session_state.paging_playing and not at_last_step:
        time.sleep(speed_seconds)
        st.session_state.paging_cursor = min(
            st.session_state.paging_cursor + 1,
            total_steps - 1
        )
        st.rerun()

def render_compare_tab():
    st.subheader("Algorithm Comparison")

    st.caption(
        "Run every algorithm on the same reference string and frame "
        "count, side by side, to see which one causes the fewest page "
        "faults."
    )

    references_text = st.text_input(
        "Reference string for comparison",
        value=st.session_state.get(
            "paging_refs",
            "7,0,1,2,0,3,0,4,2,3,0,3,2"
        ),
        key="comparison_reference_input"
    )

    frame_count = st.number_input(
        "Frames for comparison",
        min_value=1,
        max_value=10,
        value=st.session_state.get(
            "paging_frames",
            3
        ),
        key="comparison_frames"
    )

    if st.button(
        "Compare All Algorithms",
        type="primary",
        key="compare_paging"
    ):
        try:
            references = parse_ref_string(
                references_text
            )

            results, best = compare_all(
                references,
                int(frame_count)
            )

            st.session_state.paging_comparison = (
                results,
                best
            )

        except ValidationError as error:
            st.error(str(error))

    comparison = st.session_state.get(
        "paging_comparison"
    )

    if comparison is None:
        st.info(
            "Run a comparison to view the results."
        )
        return

    results, best = comparison

    rows = []
    for key in ALGO_ORDER:
        result = results[key]

        rows.append(
            {
                "Algorithm": ALGORITHMS[key]["label"],
                "Full Name": ALGORITHMS[key]["name"],
                "Hits": result["hits"],
                "Faults": result["faults"],
                "Replacements": result["replacements"],
                "Hit Ratio %": round(result["hit_ratio"] * 100, 2),
                "Fault Ratio %": round(result["fault_ratio"] * 100, 2),
            }
        )

    df = pd.DataFrame(rows).sort_values(
        "Faults", kind="stable"
    ).reset_index(drop=True)

    df.insert(0, "Rank", range(1, len(df) + 1))

    best_label = ALGORITHMS[best]["label"]
    best_faults = int(df["Faults"].min())
    worst_faults = int(df["Faults"].max())
    faults_saved = worst_faults - best_faults

    st.markdown(
        f"""
        <div style="
            background:linear-gradient(90deg,#1e3a37,#20242f);
            border:1px solid #5FB8B0;
            border-radius:10px;
            padding:16px 20px;
            margin:12px 0;
        ">
            <span style="color:#5FB8B0; font-size:22px;">🏆</span>
            <span style="color:#EDE8DE; font-size:18px; font-weight:bold;">
                Best for this input: {best_label} — {ALGORITHMS[best]['name']}
            </span>
            <br>
            <span style="color:#9098AC; font-size:14px;">
                {best_faults} page faults, the fewest of all six algorithms
                tested on this reference string.
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    metric_left, metric_middle, metric_right = st.columns(3)

    with metric_left:
        st.metric("Best algorithm", best_label)

    with metric_middle:
        st.metric("Fewest faults", best_faults)

    with metric_right:
        st.metric(
            "Faults saved vs. worst",
            faults_saved,
            help=(
                "Difference between the best and worst performing "
                "algorithm on this reference string."
            )
        )

    display_df = df[
        [
            "Rank", "Algorithm", "Full Name", "Hits", "Faults",
            "Replacements", "Hit Ratio %", "Fault Ratio %",
        ]
    ].copy()

    def highlight_best_row(row):
        is_best = row["Algorithm"] == best_label
        style = (
            "background-color:#1e3a37; color:#EDE8DE; font-weight:bold;"
            if is_best else ""
        )
        return [style] * len(row)

    styled = display_df.style.apply(
        highlight_best_row, axis=1
    ).format(
        {"Hit Ratio %": "{:.2f}%", "Fault Ratio %": "{:.2f}%"}
    ).hide(axis="index")

    st.dataframe(styled, use_container_width=True)

    st.markdown("###### Faults vs. Hits by algorithm")

    max_val = int(max(df["Hits"].max(), df["Faults"].max()))
    y_ceiling = max_val + max(2, round(max_val * 0.25))

    fault_hit_fig = go.Figure()
    fault_hit_fig.add_bar(
        name="Hits",
        x=df["Algorithm"],
        y=df["Hits"],
        marker_color="#5FB8B0",
        text=df["Hits"],
        textposition="outside",
        hovertemplate="%{x}<br>Hits: %{y}<extra></extra>",
    )
    fault_hit_fig.add_bar(
        name="Faults",
        x=df["Algorithm"],
        y=df["Faults"],
        marker_color="#E8A33D",
        text=df["Faults"],
        textposition="outside",
        hovertemplate="%{x}<br>Faults: %{y}<extra></extra>",
    )
    fault_hit_fig.update_layout(
        barmode="group",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#EDE8DE"),
        yaxis=dict(
            range=[0, y_ceiling],
            fixedrange=True,
            title="Count",
            gridcolor="rgba(255,255,255,0.08)",
        ),
        xaxis=dict(fixedrange=True, title=None),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1,
        ),
        margin=dict(l=10, r=10, t=30, b=10),
        height=360,
        bargap=0.3,
        bargroupgap=0.1,
    )

    st.plotly_chart(
        fault_hit_fig,
        use_container_width=True,
        config={"displayModeBar": False, "scrollZoom": False},
    )

    st.markdown("###### Hit ratio by algorithm")

    ratio_fig = go.Figure()
    ratio_fig.add_bar(
        x=df["Algorithm"],
        y=df["Hit Ratio %"],
        marker_color="#5FB8B0",
        text=[f"{v:.1f}%" for v in df["Hit Ratio %"]],
        textposition="outside",
        hovertemplate="%{x}<br>Hit ratio: %{y:.2f}%<extra></extra>",
    )
    ratio_fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#EDE8DE"),
        yaxis=dict(
            range=[0, 110],
            fixedrange=True,
            title="Hit ratio (%)",
            gridcolor="rgba(255,255,255,0.08)",
        ),
        xaxis=dict(fixedrange=True, title=None),
        showlegend=False,
        margin=dict(l=10, r=10, t=20, b=10),
        height=320,
        bargap=0.4,
    )

    st.plotly_chart(
        ratio_fig,
        use_container_width=True,
        config={"displayModeBar": False, "scrollZoom": False},
    )

    st.caption(
        "Lower Faults and higher Hit Ratio are better for a given "
        "reference string and frame count. The highlighted row and the "
        "banner above always show the strongest performer for this "
        "specific input — results can change with a different reference "
        "string or number of frames, which is worth trying."
    )

def render_learn_tab():
    st.subheader("Learn About Page Replacement")

    st.markdown(
        "New to paging? Start with **Core Concepts** to understand the "
        "vocabulary, then open **Algorithm Reference** to see how each "
        "strategy in the Simulate tab actually decides which page to "
        "evict."
    )

    st.markdown("#### How this simulator works")
    st.write(
        "Every entry in the reference string represents one memory "
        "access request from a running process, in the order it "
        "happens. On each request:"
    )
    st.markdown(
        "1. **Check memory** — if the page is already sitting in one of "
        "the frames, that's a **Hit**, and nothing changes.\n"
        "2. **Empty frame available** — if the page is missing but a "
        "frame is still empty, the page is loaded straight in — a "
        "**Fault**, but no eviction needed.\n"
        "3. **Memory full** — if the page is missing and every frame is "
        "occupied, the selected algorithm picks a **victim** page to "
        "evict, and the new page takes its place — a Fault **with** a "
        "replacement."
    )
    st.write(
        "The chosen algorithm only changes step 3 — how the victim is "
        "picked. Everything else about the simulation stays identical, "
        "which is exactly why the Compare tab can run the same "
        "reference string through all six algorithms and judge them "
        "fairly against each other."
    )

    st.markdown("#### Core Concepts")

    topics = {
        "Virtual Memory": (
            "Virtual memory lets a process behave as if it has access to "
            "more memory than physically exists, by keeping only the "
            "actively-used parts of the process in RAM and the rest on "
            "disk. Paging is the mechanism that makes this possible."
        ),
        "Page": (
            "A page is a fixed-size block of a process's virtual "
            "memory (its address space). Processes are split into "
            "equal-sized pages so they can be loaded into physical "
            "memory piece by piece instead of all at once."
        ),
        "Frame": (
            "A frame is a fixed-size block of physical memory (RAM) "
            "that stores exactly one page. Pages and frames are always "
            "the same size, so any page can go into any frame."
        ),
        "Page Table": (
            "The page table is the per-process data structure the "
            "operating system uses to map each virtual page number to "
            "the physical frame currently holding it. The CPU consults "
            "it on every memory access to translate a virtual address "
            "into a physical one."
        ),
        "Page Fault": (
            "A page fault occurs when a requested page is not "
            "currently loaded in physical memory. The OS must pause the "
            "process, find or make room in a frame, load the page from "
            "disk, update the page table, and then resume execution."
        ),
        "Page Replacement Algorithm": (
            "When a page fault happens and memory is already full, a "
            "page replacement algorithm decides which currently-loaded "
            "page (the 'victim') gets evicted to make room for the new "
            "one. FIFO, LRU, OPT, Clock, LFU, and MFU (all available in "
            "the Simulate tab) are different strategies for making that "
            "choice."
        ),
        "Demand Paging": (
            "A design where pages are only loaded into memory when they "
            "are actually referenced for the first time, rather than "
            "loading a whole process upfront. This is why the very "
            "first reference to any page is always a fault."
        ),
        "Locality of Reference": (
            "Programs tend to reuse recently accessed pages and pages "
            "near them (temporal and spatial locality). Most page "
            "replacement algorithms — especially LRU — are effective "
            "specifically because real programs exhibit this pattern."
        ),
        "Reference Bit": (
            "A single bit the hardware sets to 1 whenever a page is "
            "accessed. The Clock algorithm uses this bit to approximate "
            "LRU cheaply: a page gets a 'second chance' if its bit is "
            "still 1 when the replacement hand reaches it."
        ),
        "Belady's Anomaly": (
            "A counterintuitive result where FIFO can produce *more* "
            "page faults when given *more* frames for the same "
            "reference string — the opposite of what you'd expect. LRU "
            "and OPT never exhibit this because they belong to a class "
            "called stack algorithms; FIFO does not."
        ),
        "Stack Property": (
            "An algorithm has the stack property if the set of pages it "
            "keeps in memory with n frames is always a subset of what "
            "it would keep with n+1 frames. Stack algorithms (like LRU "
            "and OPT) are immune to Belady's Anomaly; FIFO is not a "
            "stack algorithm."
        ),
        "Thrashing": (
            "Thrashing occurs when the operating system spends most of "
            "its time swapping pages in and out instead of executing "
            "processes, usually because too many processes are "
            "competing for too little physical memory. Overall system "
            "throughput can collapse even though the CPU looks 'busy'."
        ),
        "Working Set": (
            "The working set is the group of pages a process is "
            "actively using during a period of execution. Giving a "
            "process at least enough frames to hold its working set is "
            "a common strategy for avoiding thrashing."
        ),
        "Hit Ratio / Fault Ratio": (
            "Hit Ratio = Hits ÷ Total References, and Fault Ratio = "
            "Faults ÷ Total References (the two always add up to 100%). "
            "A higher hit ratio means the algorithm and the available "
            "frames are handling this workload well."
        ),
        "Effective Access Time (EAT)": (
            "A formula used to measure how much page faults slow down "
            "memory access on average: "
            "EAT = (1 − fault rate) × memory access time + "
            "fault rate × page fault service time. Because servicing a "
            "fault (often a disk read) is thousands of times slower "
            "than a memory access, even a small fault rate has a large "
            "impact on EAT."
        ),
        "Dirty (Modified) Bit": (
            "A bit that marks whether a page was written to after being "
            "loaded. On eviction, a 'clean' page can simply be dropped "
            "(a copy already exists on disk), while a 'dirty' page must "
            "be written back to disk first — this simulator focuses on "
            "fault counts, but the dirty bit is why real systems care "
            "about *which* page is evicted, not just faults."
        ),
    }

    topic_items = list(topics.items())

    for i in range(0, len(topic_items), 2):
        left_col, right_col = st.columns(2)
        pair = topic_items[i:i + 2]

        for col, (title, explanation) in zip((left_col, right_col), pair):
            with col:
                with st.container(border=True):
                    st.markdown(
                        f"<span style='color:#5FB8B0; font-weight:700; "
                        f"font-size:15px;'>{title}</span>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<span style='color:#C7CBD9; font-size:14px;'>"
                        f"{explanation}</span>",
                        unsafe_allow_html=True,
                    )

    st.markdown("#### Algorithm Reference")

    for key in ALGO_ORDER:
        info = ALGORITHMS[key]

        with st.expander(
            f"{info['label']} — {info['name']}"
        ):
            st.write(info["desc"])
            st.caption(
                f"Time: {info['time']} | "
                f"Space: {info['space']}"
            )

    st.markdown("#### When to Use Each Algorithm")

    st.write(
        "Same six strategies, framed around a practical question: given "
        "a real workload, which one should you reach for?"
    )

    use_cases = {
        "FIFO": (
            "Pick this only when simplicity matters more than "
            "performance — e.g. constrained embedded systems where a "
            "plain queue is all the hardware can afford. Avoid it "
            "whenever page-access patterns actually matter, since it "
            "ignores usage entirely and can even get *worse* with more "
            "frames (Belady's Anomaly)."
        ),
        "LRU": (
            "The default choice for most real workloads. It tracks "
            "recency and rides locality of reference, landing close to "
            "optimal in practice. The trade-off is bookkeeping cost — "
            "timestamps or a linked list updated on every access."
        ),
        "OPT": (
            "Use this only as a theoretical benchmark to grade the "
            "other algorithms against, never in a live system — it "
            "requires knowing every future reference in advance, which "
            "no real OS can do."
        ),
        "CLOCK": (
            "The practical stand-in for LRU that real operating systems "
            "actually ship, because it gets LRU-like quality with far "
            "less overhead. Reach for this when you want LRU behavior "
            "without LRU's bookkeeping cost."
        ),
        "LFU": (
            "Effective when a workload has clear 'hot' pages that get "
            "reused constantly throughout the run. Weak spot: a page "
            "that was hot early can stay artificially protected long "
            "after it stops being used."
        ),
        "MFU": (
            "Mainly useful as a teaching contrast — it inverts the "
            "usual assumption and evicts frequently-used pages instead "
            "of protecting them. Rarely the right choice for a real "
            "workload."
        ),
    }

    for name, guidance in use_cases.items():
        st.markdown(f"**{name}** — {guidance}")


def aseem():
    """
    Public entry point used by hub.py.
    """

    st.markdown(
        """
        <style>
        .paging-title {
            color: #E8A33D;
            font-size: 30px;
            font-weight: bold;
        }

        .paging-subtitle {
            color: #9098AC;
            font-size: 14px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="paging-title">'
        'PAGEFRAME — Page Replacement Simulator'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="paging-subtitle">'
        'Explore page replacement algorithms, frame states, '
        'faults, hits, and performance comparisons.'
        '</div>',
        unsafe_allow_html=True
    )

    simulate_tab, compare_tab, learn_tab = st.tabs(
        [
            "Simulate",
            "Compare",
            "Learn"
        ]
    )

    with simulate_tab:
        render_simulation_tab()

    with compare_tab:
        render_compare_tab()

    with learn_tab:
        render_learn_tab()