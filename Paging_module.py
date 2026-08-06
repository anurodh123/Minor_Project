from io import BytesIO

import pandas as pd
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
                    else step["evicted_page"]
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

    if "paging_frames" not in st.session_state:
        st.session_state.paging_frames = 3

    if "paging_algorithm" not in st.session_state:
        st.session_state.paging_algorithm = "fifo"

    if "paging_result" not in st.session_state:
        st.session_state.paging_result = None

    if "paging_cursor" not in st.session_state:
        st.session_state.paging_cursor = -1

    left, middle, right = st.columns([2, 1, 2])

    with left:
        reference_text = st.text_input(
            "Reference string",
            value=st.session_state.paging_refs,
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

                st.session_state.paging_refs = (
                    ",".join(str(x) for x in generated)
                )

                st.rerun()

            except ValidationError as error:
                st.error(str(error))

    run_left, run_middle, run_right = st.columns(3)

    with run_left:
        run_clicked = st.button(
            "Run Simulation",
            type="primary",
            use_container_width=True,
            key="paging_run"
        )

    with run_middle:
        if st.button(
            "Restart Steps",
            use_container_width=True,
            key="paging_restart"
        ):
            st.session_state.paging_cursor = -1
            st.rerun()

    with run_right:
        if st.button(
            "Next Step",
            use_container_width=True,
            key="paging_next"
        ):
            result = st.session_state.paging_result

            if result:
                st.session_state.paging_cursor = min(
                    st.session_state.paging_cursor + 1,
                    len(result["steps"]) - 1
                )

                st.rerun()

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
            st.session_state.paging_cursor = -1

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


def render_compare_tab():
    st.subheader("Algorithm Comparison")

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
                "Hits": result["hits"],
                "Faults": result["faults"],
                "Replacements": result["replacements"],
                "Hit Ratio": f"{result['hit_ratio'] * 100:.2f}%",
                "Fault Ratio": f"{result['fault_ratio'] * 100:.2f}%"
            }
        )

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True
    )

    st.success(
        f"Best result: "
        f"{ALGORITHMS[best]['label']} "
        f"with {results[best]['faults']} page faults."
    )


def render_learn_tab():
    st.subheader("Learn About Page Replacement")

    topics = {
        "Page Fault": (
            "A page fault occurs when a requested page is not "
            "currently loaded in physical memory."
        ),
        "Locality of Reference": (
            "Programs tend to reuse recently accessed pages "
            "and nearby pages."
        ),
        "Frame": (
            "A frame is a fixed-size block of physical memory "
            "that stores one page."
        ),
        "Belady's Anomaly": (
            "FIFO can sometimes produce more page faults when "
            "the number of frames is increased."
        ),
        "Thrashing": (
            "Thrashing occurs when the operating system spends "
            "most of its time swapping pages instead of executing."
        ),
        "Working Set": (
            "The working set is the group of pages a process is "
            "actively using during a period of execution."
        ),
    }

    for title, explanation in topics.items():
        with st.expander(title):
            st.write(explanation)

    st.subheader("Algorithm Reference")

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