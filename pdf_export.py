from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from datetime import datetime


class PDFExporter:

    def __init__(
        self,
        filename,
        algorithm,
        algorithm_info,
        frames,
        reference_string,
        result,
    ):

        self.filename = filename
        self.algorithm = algorithm
        self.algorithm_info = algorithm_info
        self.frames = frames
        self.reference_string = reference_string
        self.result = result

        self.doc = SimpleDocTemplate(
            filename,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40,
        )

        self.styles = getSampleStyleSheet()

        self.title_style = self.styles["Heading1"]
        self.title_style.alignment = TA_CENTER

        self.heading_style = self.styles["Heading2"]

        self.normal = self.styles["BodyText"]

        self.small = self.styles["BodyText"]
        self.small.fontSize = 9

        self.story = []


    def add_title(self):

        self.story.append(
            Paragraph(
                "PAGE REPLACEMENT ALGORITHM REPORT",
                self.title_style,
            )
        )

        self.story.append(Spacer(1, 0.30 * inch))

        self.story.append(
            Paragraph(
                datetime.now().strftime(
                    "Generated on %d %B %Y   %H:%M:%S"
                ),
                self.normal,
            )
        )

        self.story.append(Spacer(1, 0.35 * inch))


    def add_simulation_information(self):

        self.story.append(
            Paragraph(
                "Simulation Information",
                self.heading_style,
            )
        )

        data = [

            ["Algorithm", self.algorithm_info["name"]],

            ["Frames", str(self.frames)],

            [
                "Reference String",
                " ".join(map(str, self.reference_string))
            ],

            [
                "Time Complexity",
                self.algorithm_info["time"]
            ],

            [
                "Space Complexity",
                self.algorithm_info["space"]
            ],

        ]

        table = Table(
            data,
            colWidths=[2.2 * inch, 4.3 * inch]
        )

        table.setStyle(
            TableStyle(

                [

                    ("GRID", (0, 0), (-1, -1), 1, colors.black),

                    (
                        "BACKGROUND",
                        (0, 0),
                        (0, -1),
                        HexColor("#D9EAD3"),
                    ),

                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),

                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, -1),
                        "Helvetica",
                    ),

                ]

            )
        )

        self.story.append(table)

        self.story.append(
            Spacer(
                1,
                0.30 * inch,
            )
        )


    def add_algorithm_description(self):

        self.story.append(
            Paragraph(
                "Algorithm Description",
                self.heading_style,
            )
        )

        for line in self.algorithm_info["desc"].split("\n"):

            self.story.append(
                Paragraph(
                    line,
                    self.normal,
                )
            )

        self.story.append(
            Spacer(
                1,
                0.30 * inch,
            )
        )
    def add_simulation_steps(self):

        self.story.append(
            Paragraph(
                "Step-by-Step Simulation",
                self.heading_style,
            )
        )

        headers = [
            "Step",
            "Page",
            "Frames",
            "Hit / Fault",
            "Victim",
            "Action",
        ]

        rows = [headers]

        for index, step in enumerate(self.result["steps"], start=1):

            frame_text = []

            for frame in step["frame_state"]:

                if frame is None:
                    frame_text.append("-")

                elif isinstance(frame, dict):

                    page = frame.get("page", "-")
                    ref_bit = frame.get("ref_bit")

        # Show ref bit only for CLOCK
                    if self.algorithm.lower() == "clock":
                        frame_text.append(f"{page} ({ref_bit})")
                    else:
                        frame_text.append(str(page))

                else:
                    frame_text.append(str(frame))

            frames = " | ".join(frame_text)

            status = "Hit" if step["hit"] else "Fault"

            victim = "-"

            if step.get("evicted_page") is not None:
                victim = str(step["evicted_page"])

            if step["hit"]:
                action = "Already in memory"

            elif step.get("evicted_page") is None:
                action = "Loaded into empty frame"

            else:
                action = (
                    f"Replaced page {step['evicted_page']}"
                )

            rows.append(
                [
                    str(index),
                    str(step["page"]),
                    frames,
                    status,
                    victim,
                    action,
                ]
            )

        table = Table(
            rows,
            repeatRows=1,
            colWidths=[
                0.6 * inch,
                0.7 * inch,
                2.2 * inch,
                0.8 * inch,
                0.7 * inch,
                2.0 * inch,
            ],
        )

        table.setStyle(

            TableStyle(

                [

                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),

                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        HexColor("#4472C4"),
                    ),

                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white,
                    ),

                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),

                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "CENTER",
                    ),

                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),

                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, 0),
                        8,
                    ),

                    (
                        "BACKGROUND",
                        (0, 1),
                        (-1, -1),
                        HexColor("#F8F9FA"),
                    ),

                ]

            )

        )

        self.story.append(table)

        self.story.append(
            Spacer(
                1,
                0.30 * inch,
            )
        )
    def add_statistics(self):

        self.story.append(
            Paragraph(
                "Simulation Statistics",
                self.heading_style,
            )
        )

        hits = self.result["hits"]
        faults = self.result["faults"]

        total = hits + faults

        hit_ratio = (hits / total * 100) if total else 0
        fault_ratio = (faults / total * 100) if total else 0

        replacements = self.result.get(
            "replacements",
            max(0, faults - self.frames)
        )

        data = [

            ["Total References", str(total)],

            ["Page Hits", str(hits)],

            ["Page Faults", str(faults)],

            ["Hit Ratio", f"{hit_ratio:.2f}%"],

            ["Fault Ratio", f"{fault_ratio:.2f}%"],

            ["Page Replacements", str(replacements)],

        ]

        table = Table(
            data,
            colWidths=[2.5 * inch, 3.0 * inch],
        )

        table.setStyle(

            TableStyle(

                [

                    ("GRID", (0, 0), (-1, -1), 1, colors.black),

                    (
                        "BACKGROUND",
                        (0, 0),
                        (0, -1),
                        HexColor("#FFF2CC"),
                    ),

                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),

                ]

            )

        )

        self.story.append(table)

        self.story.append(
            Spacer(1, 0.3 * inch)
        )


    def add_conclusion(self):

        hits = self.result["hits"]
        faults = self.result["faults"]

        text = f"""
        <b>Conclusion</b><br/><br/>

        The simulation was performed using the
        <b>{self.algorithm_info['name']}</b> page replacement algorithm.

        The reference string generated
        <b>{hits}</b> page hits and
        <b>{faults}</b> page faults.

        The detailed table above illustrates every page request,
        the memory frame contents after each request,
        whether the request resulted in a page hit or page fault,
        and any page replacement performed during execution.

        This report can be used to understand the behaviour
        and performance of the selected page replacement algorithm.
        """

        self.story.append(
            Paragraph(
                text,
                self.normal,
            )
        )


    def export(self):

        self.add_title()

        self.add_simulation_information()

        self.add_algorithm_description()

        self.add_simulation_steps()

        self.add_statistics()

        self.add_conclusion()

        self.doc.build(self.story)