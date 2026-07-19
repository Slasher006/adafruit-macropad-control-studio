#!/usr/bin/env python3
"""Generate the exhaustive Adafruit MacroPad Configurator tutorial PDF."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    LongTable,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "adafruit-macropad-configurator-tutorial.pdf"

INK = colors.HexColor("#17212B")
MUTED = colors.HexColor("#52606D")
CYAN = colors.HexColor("#00A7C4")
CYAN_DARK = colors.HexColor("#087B90")
CYAN_PALE = colors.HexColor("#E9F8FB")
NAVY = colors.HexColor("#102A43")
SLATE = colors.HexColor("#D9E2EC")
PALE = colors.HexColor("#F5F7FA")
GREEN = colors.HexColor("#00A86B")
YELLOW = colors.HexColor("#F6C945")
ORANGE = colors.HexColor("#E67E22")
RED = colors.HexColor("#C0392B")
WHITE = colors.white


def register_fonts() -> tuple[str, str, str]:
    candidates = [
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
        ),
        (
            Path("/usr/share/fonts/TTF/DejaVuSans.ttf"),
            Path("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"),
            Path("/usr/share/fonts/TTF/DejaVuSansMono.ttf"),
        ),
    ]
    for regular, bold, mono in candidates:
        if regular.exists() and bold.exists() and mono.exists():
            pdfmetrics.registerFont(TTFont("TutorialSans", regular))
            pdfmetrics.registerFont(TTFont("TutorialSans-Bold", bold))
            pdfmetrics.registerFont(TTFont("TutorialMono", mono))
            return "TutorialSans", "TutorialSans-Bold", "TutorialMono"
    return "Helvetica", "Helvetica-Bold", "Courier"


FONT, FONT_BOLD, FONT_MONO = register_fonts()


def make_styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=sample["Title"],
            fontName=FONT_BOLD,
            fontSize=30,
            leading=34,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=9 * mm,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle",
            parent=sample["Normal"],
            fontName=FONT,
            fontSize=14,
            leading=20,
            textColor=CYAN_DARK,
            spaceAfter=8 * mm,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=sample["Heading1"],
            fontName=FONT_BOLD,
            fontSize=19,
            leading=23,
            textColor=NAVY,
            spaceBefore=7 * mm,
            spaceAfter=3.5 * mm,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=sample["Heading2"],
            fontName=FONT_BOLD,
            fontSize=13.5,
            leading=17,
            textColor=CYAN_DARK,
            spaceBefore=4.5 * mm,
            spaceAfter=2 * mm,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "H3",
            parent=sample["Heading3"],
            fontName=FONT_BOLD,
            fontSize=10.5,
            leading=14,
            textColor=INK,
            spaceBefore=3.5 * mm,
            spaceAfter=1.5 * mm,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=sample["BodyText"],
            fontName=FONT,
            fontSize=9.3,
            leading=13.2,
            textColor=INK,
            spaceAfter=2.2 * mm,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=sample["BodyText"],
            fontName=FONT,
            fontSize=7.8,
            leading=10.2,
            textColor=INK,
        ),
        "table": ParagraphStyle(
            "TableText",
            parent=sample["BodyText"],
            fontName=FONT,
            fontSize=7.4,
            leading=9.5,
            textColor=INK,
        ),
        "table_head": ParagraphStyle(
            "TableHead",
            parent=sample["BodyText"],
            fontName=FONT_BOLD,
            fontSize=7.6,
            leading=9.6,
            textColor=WHITE,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=sample["BodyText"],
            fontName=FONT,
            fontSize=9.2,
            leading=12.8,
            leftIndent=5 * mm,
            firstLineIndent=-3.2 * mm,
            bulletIndent=0,
            textColor=INK,
            spaceAfter=1.4 * mm,
        ),
        "number": ParagraphStyle(
            "Number",
            parent=sample["BodyText"],
            fontName=FONT,
            fontSize=9.2,
            leading=12.8,
            leftIndent=7 * mm,
            firstLineIndent=-5 * mm,
            textColor=INK,
            spaceAfter=1.7 * mm,
        ),
        "callout": ParagraphStyle(
            "Callout",
            parent=sample["BodyText"],
            fontName=FONT,
            fontSize=9,
            leading=12.6,
            textColor=INK,
            leftIndent=3 * mm,
            rightIndent=3 * mm,
            spaceBefore=1.5 * mm,
            spaceAfter=1.5 * mm,
        ),
        "code": ParagraphStyle(
            "Code",
            parent=sample["Code"],
            fontName=FONT_MONO,
            fontSize=7.5,
            leading=10.2,
            textColor=colors.HexColor("#E6EDF3"),
            leftIndent=3 * mm,
            rightIndent=3 * mm,
            spaceBefore=1.5 * mm,
            spaceAfter=1.5 * mm,
        ),
        "caption": ParagraphStyle(
            "Caption",
            parent=sample["BodyText"],
            fontName=FONT,
            fontSize=7.5,
            leading=10,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=3 * mm,
        ),
    }


STYLES = make_styles()
HEADING_SEQUENCE = 0


class TutorialDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str) -> None:
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=17 * mm,
            title="Adafruit MacroPad Configurator - Exhaustive Tutorial",
            author="Adafruit MacroPad Configurator project",
            subject="Complete configurator tutorial, examples, and reference",
        )
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="content",
        )
        self.addPageTemplates(PageTemplate(id="tutorial", frames=[frame], onPage=draw_page))

    def afterFlowable(self, flowable: Flowable) -> None:
        if not isinstance(flowable, Paragraph):
            return
        level = getattr(flowable, "_toc_level", None)
        if level is None:
            return
        key = flowable._bookmark_name
        self.canv.bookmarkPage(key)
        text = flowable.getPlainText()
        self.canv.addOutlineEntry(text, key, level=level, closed=False)
        self.notify("TOCEntry", (level, text, self.page, key))


def draw_page(canvas, doc) -> None:
    canvas.saveState()
    width, height = A4
    if doc.page > 1:
        canvas.setStrokeColor(SLATE)
        canvas.setLineWidth(0.5)
        canvas.line(18 * mm, height - 13 * mm, width - 18 * mm, height - 13 * mm)
        canvas.setFont(FONT, 7.4)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, height - 10 * mm, "Adafruit MacroPad Configurator - Tutorial")
    canvas.setFont(FONT, 7.4)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 9 * mm, "Version 1.1 workflow reference")
    canvas.drawRightString(width - 18 * mm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


def p(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, STYLES[style])


def heading(text: str, level: int = 1) -> Paragraph:
    global HEADING_SEQUENCE
    HEADING_SEQUENCE += 1
    item = Paragraph(text, STYLES[f"h{level}"])
    item._toc_level = level - 1
    item._bookmark_name = f"heading-{HEADING_SEQUENCE}"
    return item


def bullet(text: str) -> Paragraph:
    return Paragraph(f"- {text}", STYLES["bullet"])


def numbered(number: int, text: str) -> Paragraph:
    return Paragraph(f"{number}. {text}", STYLES["number"])


def callout(title: str, text: str, color=CYAN_PALE) -> Table:
    content = Paragraph(f"<b>{escape(title)}</b><br/>{text}", STYLES["callout"])
    box = Table([[content]], colWidths=[168 * mm])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), color),
                ("BOX", (0, 0), (-1, -1), 0.8, CYAN_DARK),
                ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ]
        )
    )
    return box


def code_block(text: str) -> Table:
    safe = escape(text).replace("\n", "<br/>").replace(" ", "&nbsp;")
    box = Table([[Paragraph(safe, STYLES["code"])]], colWidths=[168 * mm])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#334E68")),
                ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ]
        )
    )
    return box


def data_table(headers: list[str], rows: list[list[str]], widths: list[float]) -> LongTable:
    data = [[Paragraph(escape(value), STYLES["table_head"]) for value in headers]]
    for row in rows:
        data.append([Paragraph(value, STYLES["table"]) for value in row])
    table = LongTable(data, colWidths=[value * mm for value in widths], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE]),
                ("GRID", (0, 0), (-1, -1), 0.35, SLATE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 1.6 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6 * mm),
            ]
        )
    )
    return table


def workflow_table(labels: list[str]) -> Table:
    cells: list[Paragraph] = []
    widths: list[float] = []
    for index, label in enumerate(labels):
        cells.append(Paragraph(f"<b>{escape(label)}</b>", STYLES["small"]))
        widths.append(29 * mm)
        if index < len(labels) - 1:
            cells.append(Paragraph("-&gt;", STYLES["small"]))
            widths.append(5 * mm)
    table = Table([cells], colWidths=widths, hAlign="CENTER")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CYAN_PALE),
                ("BOX", (0, 0), (-1, -1), 0.7, CYAN_DARK),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
            ]
        )
    )
    return table


def pad_diagram() -> Table:
    rows = []
    for start in (1, 4, 7, 10):
        rows.append(
            [
                Paragraph(f"<b>Key {number}</b><br/>row {(number - 1) // 3 + 1}", STYLES["small"])
                for number in range(start, start + 3)
            ]
        )
    rows.append([Paragraph("<b>Encoder press</b> - below the 12 keys", STYLES["small"]), "", ""])
    table = Table(rows, colWidths=[52 * mm] * 3)
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, 3), 1, CYAN_DARK),
                ("BACKGROUND", (0, 0), (-1, 3), CYAN_PALE),
                ("SPAN", (0, 4), (2, 4)),
                ("BOX", (0, 4), (2, 4), 1, NAVY),
                ("BACKGROUND", (0, 4), (2, 4), SLATE),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
            ]
        )
    )
    return table


def add_cover(story: list[Flowable]) -> None:
    story.extend(
        [
            Spacer(1, 25 * mm),
            p("ADAFRUIT MACROPAD RP2040", "small"),
            p("Configurator Tutorial", "cover_title"),
            p(
                "A complete, example-driven guide to profiles, subprofiles, OLED labels, RGB, "
                "macro steps, device synchronization, backups, multiple decks, and repair.",
                "cover_subtitle",
            ),
            Spacer(1, 8 * mm),
            workflow_table(["Import", "Edit", "Compare", "Preview", "Sync"]),
            Spacer(1, 15 * mm),
            callout(
                "The one rule to remember",
                "<b>Import Device</b> copies from the MacroPad into the editor. "
                "<b>Sync Device</b> copies from the editor to the MacroPad. "
                "Use Compare before Sync when the device contains anything important.",
            ),
            Spacer(1, 22 * mm),
            p(
                "Applies to configurator version 1.1 and the matching CircuitPython firmware. "
                "Generated from the project tutorial source.",
                "small",
            ),
            PageBreak(),
        ]
    )


def add_toc(story: list[Flowable]) -> None:
    story.append(heading("Contents"))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(
            "TOC1",
            fontName=FONT_BOLD,
            fontSize=8.8,
            leading=10.5,
            leftIndent=0,
            firstLineIndent=0,
            textColor=NAVY,
            spaceBefore=1 * mm,
        ),
        ParagraphStyle(
            "TOC2",
            fontName=FONT,
            fontSize=7.4,
            leading=8.6,
            leftIndent=7 * mm,
            firstLineIndent=0,
            textColor=CYAN_DARK,
        ),
    ]
    story.extend([toc, PageBreak()])


def add_foundations(story: list[Flowable]) -> None:
    story.extend(
        [
            heading("1. Start here: the configurator mental model"),
            p(
                "The desktop configurator is an editor and deployment tool. The MacroPad does not "
                "need the desktop application after synchronization. The CircuitPython firmware on "
                "the device executes keyboard shortcuts, typed text, media controls, mouse actions, "
                "delays, OLED labels, and RGB behavior on its own."
            ),
            heading("The three copies you may encounter", 2),
            data_table(
                ["Copy", "Where it lives", "What it means"],
                [
                    ["Local editor library", "Qt application-data folder on the computer", "The working copy displayed and autosaved by the GUI."],
                    ["Device library", "The selected MacroPad CIRCUITPY drive", "The profiles currently used by that device."],
                    ["Export or backup", "A file chosen by you or the per-device backup folder", "A portable library archive, one-profile JSON, or historical snapshot."],
                ],
                [35, 52, 81],
            ),
            Spacer(1, 3 * mm),
            callout(
                "Direction matters",
                "<b>Import Device: device -&gt; local editor.</b><br/>"
                "<b>Sync Device: local editor -&gt; device.</b><br/>"
                "Export and backups do not change the connected device until you later choose Sync Device.",
                colors.HexColor("#FFF7E6"),
            ),
            heading("Status badge meanings", 2),
            data_table(
                ["Status", "Meaning", "Next action"],
                [
                    ["Autosaving...", "An edit is waiting for the 750 ms local autosave timer.", "Wait briefly or choose Save Local."],
                    ["Local saved - device differs", "The working copy is safe on the computer but not deployed.", "Compare, preview if useful, then Sync Device."],
                    ["Synced/local saved", "The selected device and local normalized libraries match.", "No action is required."],
                ],
                [42, 78, 48],
            ),
            heading("Tooltips are built into the application", 2),
            p(
                "Hover over any menu action, toolbar command, profile button, key tile, input, "
                "palette control, or macro-step field. Every tooltip contains a short purpose and "
                "a concrete Example line. Tooltips are the fastest in-context reminder; this PDF "
                "provides the complete workflow and the reasons behind each command."
            ),
        ]
    )


def add_installation(story: list[Flowable]) -> None:
    story.extend(
        [
            heading("2. Installation and launch"),
            heading("Requirements", 2),
            bullet("Linux desktop with Python 3.10 or newer."),
            bullet("PySide6 and pyserial, installed through the project package."),
            bullet("A normal USB data cable. Charge-only cables cannot mount CIRCUITPY or expose serial."),
            bullet("For firmware repair, circup must be installed in the same application environment."),
            heading("Create the environment once", 2),
            code_block(
                "python3 -m venv --system-site-packages .venv\n"
                ".venv/bin/pip install -e '.[test]'"
            ),
            heading("Launch options", 2),
            data_table(
                ["Method", "Command or action", "Use when"],
                [
                    ["Project launcher", "<font name='TutorialMono'>./run_gui.sh</font>", "Running from a terminal in the repository."],
                    ["File-manager launcher", "Double-click <font name='TutorialMono'>Start-MacroPad-Configurator.sh</font>", "Starting without an open terminal."],
                    ["Installed command", "<font name='TutorialMono'>macropad-configurator</font>", "The package is installed into the active environment."],
                    ["Exit", "File -&gt; Exit or Ctrl+Q", "Closing through save and preview-cleanup checks."],
                ],
                [38, 70, 60],
            ),
            heading("Connect the MacroPad", 2),
            p(
                "Connect a MacroPad running CircuitPython normally. Its drive should mount as "
                "CIRCUITPY and contain boot_out.txt with the Adafruit MacroPad RP2040 board ID. "
                "A board in UF2 bootloader mode appears as RPI-RP2 and is not treated as a "
                "configurable MacroPad."
            ),
            numbered(1, "Wait until the CIRCUITPY drive is mounted."),
            numbered(2, "Launch the configurator."),
            numbered(3, "Choose Refresh if the device was connected after launch."),
            numbered(4, "Select the correct device by friendly name, UID, and mount path."),
        ]
    )


def add_interface(story: list[Flowable]) -> None:
    story.extend(
        [
            heading("3. Complete interface tour"),
            p(
                "The window is organized as a top device toolbar, a second editing toolbar, and "
                "three working columns. The left column manages parent profiles. The center column "
                "manages layout screens and the 12-key pad. The right column edits the selected "
                "control's label, RGB, and action sequence."
            ),
            data_table(
                ["Region", "Primary job", "Typical example"],
                [
                    ["Device toolbar", "Select a device; refresh, import, preview, sync, save, and choose keyboard layout.", "Select Left App Deck, then Preview RGB."],
                    ["Editing toolbar and menus", "Undo, copy/paste, swap, compare, backups, import/export, health, repair, naming, and exit.", "Compare the local library before syncing."],
                    ["Left: Profile screens", "Create, select, delete, import, export, template, and reorder parent profiles.", "Move Firefox next to VS Code in encoder-turn order."],
                    ["Center: Active profile", "Name and reorder subprofiles, set icon and brightness, preview OLED, and select keys.", "Create Browse, Tabs, Tools, and In App layouts."],
                    ["Right: Control editor", "Name a key, set its six-character OLED label, configure RGB, and build macro steps.", "Create a green Copy key with CONTROL+C."],
                ],
                [41, 74, 53],
            ),
            heading("Physical key numbering", 2),
            pad_diagram(),
            p(
                "Keys are numbered left-to-right and top-to-bottom. The first row is Keys 1-3, "
                "the second is 4-6, the third is 7-9, and the fourth is 10-12. This matters when "
                "you choose Current row in the palette scope or read profile documentation.",
                "caption",
            ),
            heading("Parent profiles versus layout screens", 2),
            p(
                "A parent profile is selected by turning the encoder. A layout screen, also called "
                "a subprofile, is selected by pressing the encoder while that parent is active. "
                "Each layout has its own 12 keys, icon, brightness, colors, labels, and steps."
            ),
            workflow_table(["Turn encoder", "Choose parent", "Press encoder", "Choose layout", "Press key"]),
            Spacer(1, 2 * mm),
            callout(
                "Encoder assignment rule",
                "A parent with only one layout may use a custom encoder-press macro. As soon as "
                "additional layouts exist, encoder press is reserved for cycling layouts and its "
                "action editor is disabled.",
            ),
        ]
    )


def add_first_workflow(story: list[Flowable]) -> None:
    story.extend(
        [
            heading("4. First-device workflow: preserve, edit, verify, deploy"),
            p(
                "Use this workflow when the MacroPad already contains anything worth keeping. It "
                "makes direction explicit and gives you two review points before a write."
            ),
            workflow_table(["Import Device", "Edit", "Compare", "Preview RGB", "Sync Device"]),
            heading("Step 1 - Import Device", 2),
            numbered(1, "Select the intended MacroPad in the Device list."),
            numbered(2, "Choose Import Device."),
            numbered(3, "If prompted about local edits, stop unless you intend to replace them."),
            numbered(4, "Confirm the profiles visible in the left panel match the device."),
            p(
                "Import replaces the local working library. It does not change the MacroPad. If the "
                "local library also matters, export it before importing."
            ),
            heading("Step 2 - Make a small, identifiable edit", 2),
            p(
                "For a first test, choose a harmless key. Rename it, set a short OLED label, and "
                "change its idle color. A visible but safe change is easier to verify than a complex "
                "launcher or shutdown macro."
            ),
            heading("Step 3 - Compare", 2),
            p(
                "Compare reports keyboard-layout changes, profile membership or order, names and "
                "icons, brightness, changed controls, and subprofile changes. Read the summary. "
                "Unexpected removals usually mean you imported or selected the wrong library."
            ),
            heading("Step 4 - Preview RGB", 2),
            p(
                "Preview RGB sends temporary colors for the selected layout. It does not deploy "
                "profiles. Choose Clear Preview when finished, or let normal cleanup restore the "
                "device while closing."
            ),
            heading("Step 5 - Sync Device", 2),
            p(
                "Sync validates and saves the local library, reads the device, shows a change "
                "summary, asks for confirmation, creates a per-device backup, writes revisioned "
                "profile files, commits the index last, and asks the firmware to reload."
            ),
            callout(
                "Do not unplug during a write",
                "Wait for drive activity to stop. The revisioned write design reduces partial-update "
                "risk, but disconnecting USB during filesystem changes is still unsafe.",
                colors.HexColor("#FFF0ED"),
            ),
        ]
    )


def add_profiles(story: list[Flowable]) -> None:
    story.extend(
        [
            heading("5. Parent profiles and encoder-turn order"),
            heading("Creating profiles", 2),
            data_table(
                ["Command", "Result", "Worked example"],
                [
                    ["Add", "Creates a blank parent named New Profile.", "Add one, rename it OBS Studio, then build keys."],
                    ["Duplicate", "Copies every layout, key, label, color, and step.", "Duplicate Firefox before creating a testing variant."],
                    ["Template...", "Creates Editing, Media, or Blank from a maintained template.", "Choose Media for volume and transport controls."],
                    ["Import...", "Adds one profile from JSON without replacing the library.", "Import obs-studio.json from another computer."],
                ],
                [34, 66, 68],
            ),
            heading("Ordering profiles", 2),
            p(
                "The left list is the exact encoder-turn sequence. Drag a profile to a new position "
                "or use Up and Down. Put profiles used together next to each other. For example, a "
                "development cluster might be VS Code, Terminal, Firefox, and ComfyUI."
            ),
            heading("Clearing, resetting, and deleting", 2),
            bullet("<b>Clear profile</b> removes assignments but keeps identity and brightness. It asks for confirmation."),
            bullet("<b>Reset lights</b> enables every key light, restores default idle and pressed colors, and returns brightness to 5 percent."),
            bullet("<b>Delete</b> removes the selected parent after confirmation. At least one profile must remain."),
            heading("Profile identity limits", 2),
            p(
                "The library supports up to 32 parent profiles. Names are limited to 24 characters. "
                "Internal IDs are normalized slugs and remain unique. Use the visible name for human "
                "meaning; avoid renaming a parent merely to change a layout screen."
            ),
        ]
    )


def add_subprofiles(story: list[Flowable]) -> None:
    story.extend(
        [
            heading("6. Layout screens and encoder-press order"),
            p(
                "The Screens list in the center shows the primary layout plus up to eight additional "
                "layouts. The visible sequence is the order used when pressing the encoder."
            ),
            data_table(
                ["Control", "Purpose", "Example"],
                [
                    ["+", "Add a blank additional layout.", "Add In App as the fourth Firefox layout."],
                    ["Duplicate", "Copy the selected layout and insert the copy after it.", "Duplicate Browse, rename the copy Tabs, then adapt keys."],
                    ["Up / Down", "Move the selected layout earlier or later.", "Keep In App last for predictable automatic selection."],
                    ["Drag", "Reorder directly in the Screens list.", "Drag Tools before Tabs."],
                    ["-", "Delete an additional layout.", "Remove an abandoned Experiment layout. The primary cannot be deleted."],
                ],
                [30, 68, 70],
            ),
            heading("Naming and preview", 2),
            bullet("<b>Profile name</b> labels the parent chosen by turning the encoder."),
            bullet("<b>Layout name</b> labels the selected screen shown on the OLED."),
            bullet("<b>OLED icon</b> adds an optional two-character prefix."),
            bullet("<b>Light intensity</b> is stored per layout from 0 to 100 percent."),
            p(
                "Example: parent Firefox can contain Browse, Tabs, Tools, and In App. The parent name "
                "stays Firefox; Layout name changes as you select each screen. Use FF as the icon and "
                "5 percent brightness for each screen unless one needs a deliberate visual warning."
            ),
            heading("Remembered selection behavior", 2),
            p(
                "The device remembers the manually selected layout for each parent profile and "
                "restores it after restart. Turning away from Firefox and back does not force Browse "
                "again. Automatic In App selection is contextual and does not overwrite the manual "
                "selection used by a Manual or Profile deck."
            ),
        ]
    )


def add_labels_rgb(story: list[Flowable]) -> None:
    story.extend(
        [
            heading("7. Key selection, labels, OLED, and RGB"),
            heading("Selecting and moving keys", 2),
            bullet("Click a key tile to edit that key."),
            bullet("Ctrl-click multiple key tiles to apply lighting and palette changes together."),
            bullet("Drag a key to a new position to move it; intervening keys shift to close and open positions."),
            bullet("Use Swap... to exchange exactly two complete assignments without shifting anything between them."),
            bullet("Copy control and Paste control duplicate an assignment. Undo and Redo cover editor changes."),
            heading("Name versus OLED label", 2),
            data_table(
                ["Field", "Limit and purpose", "Example"],
                [
                    ["Name", "Up to 24 characters; descriptive text on the GUI tile.", "Command palette"],
                    ["OLED label", "Up to 6 characters; compact text on the physical display.", "CMDPAL"],
                    ["Unset key", "Resets name to Unassigned and clears OLED label and steps.", "Clear an unused corner key."],
                ],
                [32, 75, 61],
            ),
            heading("Lighting controls", 2),
            p(
                "Illuminate this key can disable a key light without losing its saved colors. Idle "
                "color is the resting color. Pressed color is short feedback while the key is active. "
                "The encoder has no RGB controls."
            ),
            heading("Recommended color language", 2),
            data_table(
                ["Color", "Hex", "Meaning", "Examples"],
                [
                    ["Green", "#00FF66", "Safe, start, create, confirm, increase", "Play, Save, Volume up"],
                    ["Lime", "#B8FF00", "Navigation and movement", "Next tab, Focus right"],
                    ["Yellow", "#FFD000", "Neutral toggle or reversible edit", "Undo, selection"],
                    ["Orange", "#FF7A00", "Caution or system-changing action", "Cut, Volume down"],
                    ["Red", "#FF2020", "Stop, close, remove, mute, destructive", "Interrupt, Close, Shutdown"],
                    ["White", "#FFFFFF", "Standard pressed feedback", "All pressed colors"],
                ],
                [25, 27, 65, 51],
            ),
            heading("Palette workflow", 2),
            numbered(1, "Select a key whose idle color you want to reuse and choose Save current."),
            numbered(2, "Select one or more target keys."),
            numbered(3, "Choose the saved hex value in Palette."),
            numbered(4, "Choose Selected keys, Current row, or All keys in Apply to."),
            numbered(5, "Choose Idle or Pressed."),
            p(
                "Example: select Key 4, choose Current row, select #FF2020, and choose Idle. Keys "
                "4-6 receive the red idle color. Use Preview RGB before Sync if brightness or risk "
                "semantics matter."
            ),
        ]
    )


def add_actions(story: list[Flowable]) -> None:
    story.extend(
        [
            heading("8. Build action sequences"),
            p(
                "A control may contain up to 16 steps. Steps run top-to-bottom. Add, edit, remove, "
                "drag, or use Move up and Move down. Double-clicking a step opens the editor. "
                "Safe preview summarizes without sending input; Run on device executes only after "
                "confirmation."
            ),
            heading("The five step types", 2),
            data_table(
                ["Type", "Fields", "Use", "Example"],
                [
                    ["hotkey", "Up to 6 HID key names", "Press keys together.", "CONTROL, SHIFT, P"],
                    ["text", "Up to 512 characters", "Type literal text into the focused application.", "pamac checkupdates"],
                    ["consumer", "Supported media code", "Send an OS media-control event.", "VOLUME_INCREMENT"],
                    ["mouse click", "LEFT, MIDDLE, or RIGHT button", "Click a mouse button.", "RIGHT_BUTTON"],
                    ["mouse move", "X, Y, wheel from -127 to 127", "Move pointer or wheel.", "wheel = -1"],
                    ["delay", "0 to 10000 ms", "Wait between steps.", "800 ms after opening a terminal"],
                ],
                [24, 48, 54, 42],
            ),
            heading("Hotkeys", 2),
            p(
                "Use CircuitPython HID names separated by commas. The searchable key picker appends "
                "valid names. CONTROL, C means press both together. If keys must happen sequentially, "
                "use separate hotkey steps. Common names include CONTROL, SHIFT, ALT, GUI, ENTER, "
                "ESCAPE, TAB, arrows, letters, digits, and F1-F12."
            ),
            callout(
                "German and US layouts",
                "Hotkey names remain HID names, but typed text and punctuation depend on the Layout "
                "selector. Match the configurator to the host desktop layout before synchronization.",
            ),
            heading("Text", 2),
            p(
                "Text steps type exactly what is stored. They do not press Enter unless a later "
                "hotkey step does so. This distinction is useful for terminal templates: open a "
                "terminal, wait, type a command, and stop so the user can review it."
            ),
            heading("Consumer media actions", 2),
            p(
                "Supported codes are MUTE, VOLUME_DECREMENT, VOLUME_INCREMENT, PLAY_PAUSE, "
                "SCAN_PREVIOUS_TRACK, SCAN_NEXT_TRACK, STOP, RECORD, and EJECT."
            ),
            heading("Mouse", 2),
            p(
                "Click sends a selected button. Move uses signed X, Y, and wheel values. Small values "
                "are easier to control. Test pointer movement in a harmless context because the active "
                "application receives it immediately."
            ),
            heading("Delay", 2),
            p(
                "Delays are essential when an earlier step opens or focuses a new window. Start with "
                "800 ms for a terminal or launcher on a typical desktop, then reduce only after repeatable "
                "testing. A delay of zero is valid but usually unnecessary."
            ),
            heading("Presets", 2),
            p(
                "The Preset list can fill common actions such as Copy, Paste, Cut, Undo, Redo, Save, "
                "Select all, Close tab, Play/Pause, Mute, volume, and mouse clicks. Select Custom action "
                "when building a step manually."
            ),
        ]
    )


def add_examples(story: list[Flowable]) -> None:
    story.extend(
        [
            heading("9. Worked macro examples"),
            heading("Example A - Copy", 2),
            data_table(
                ["Key field", "Value"],
                [
                    ["Name", "Copy"],
                    ["OLED label", "COPY"],
                    ["Idle / pressed", "#00FF66 / #FFFFFF"],
                    ["Step 1", "hotkey: CONTROL, C"],
                ],
                [46, 122],
            ),
            p("Use Safe preview. It should report one shortcut. Focus a harmless text editor, then Run on device."),
            heading("Example B - Application launcher", 2),
            data_table(
                ["Order", "Type", "Value", "Why"],
                [
                    ["1", "hotkey", "GUI, D", "Open the desktop launcher."],
                    ["2", "delay", "300 ms", "Allow the launcher to receive focus."],
                    ["3", "text", "firefox", "Type the application command."],
                    ["4", "hotkey", "ENTER", "Launch it."],
                ],
                [17, 28, 48, 75],
            ),
            p(
                "If characters are missing, increase the delay. If the launcher differs on your desktop, "
                "replace GUI+D with the configured shortcut."
            ),
            heading("Example C - Reviewable terminal command", 2),
            data_table(
                ["Order", "Type", "Value"],
                [
                    ["1", "hotkey", "GUI, ENTER"],
                    ["2", "delay", "800 ms"],
                    ["3", "text", "pamac checkupdates"],
                ],
                [20, 35, 113],
            ),
            callout(
                "Deliberately no Enter",
                "The MacroPad opens a terminal and types the command but does not execute it. Review, "
                "edit, or complete the command manually. Pamac performs its own privilege escalation; "
                "do not prefix pamac itself with sudo.",
                colors.HexColor("#FFF7E6"),
            ),
            heading("Example D - Volume up", 2),
            data_table(
                ["Key field", "Value"],
                [
                    ["Name / OLED", "Volume up / VOL+"],
                    ["Idle / pressed", "#00FF66 / #FFFFFF"],
                    ["Step 1", "consumer: VOLUME_INCREMENT"],
                ],
                [46, 122],
            ),
            heading("Example E - Right click", 2),
            data_table(
                ["Key field", "Value"],
                [
                    ["Name / OLED", "Context menu / RIGHT"],
                    ["Step 1", "mouse click: RIGHT_BUTTON"],
                ],
                [46, 122],
            ),
            heading("Example F - Safe delayed shutdown template", 2),
            data_table(
                ["Order", "Type", "Value"],
                [
                    ["1", "hotkey", "GUI, ENTER"],
                    ["2", "delay", "800 ms"],
                    ["3", "text", "shutdown +60"],
                ],
                [20, 35, 113],
            ),
            p(
                "Keep Enter out while testing. Once deliberately enabled, add ENTER as Step 4. Use a "
                "red idle color and a clear name such as Shutdown 60m. Add a separate green Cancel key "
                "that types shutdown -c and only add Enter after reviewing the complete sequence."
            ),
            heading("Example G - Multi-step Save As", 2),
            data_table(
                ["Order", "Type", "Value"],
                [
                    ["1", "hotkey", "CONTROL, SHIFT, S"],
                    ["2", "delay", "400 ms"],
                    ["3", "text", "project-copy"],
                ],
                [20, 35, 113],
            ),
            p(
                "Do not add Enter until the target application's dialog behavior is confirmed. Some "
                "applications preselect a filename extension or place focus in a different field."
            ),
        ]
    )


def add_library_device(story: list[Flowable]) -> None:
    story.extend(
        [
            heading("10. Local saving, imports, exports, and backups"),
            heading("Autosave and Save Local", 2),
            p(
                "Most edits mark the library dirty and schedule a local save after 750 ms. Save Local "
                "writes immediately. Closing with pending local changes asks whether to save, discard, "
                "or cancel closing."
            ),
            heading("One-profile JSON", 2),
            bullet("Export... writes only the selected parent profile as JSON."),
            bullet("Import... adds one normalized profile and creates a unique ID if needed."),
            bullet("Use this format when sharing one profile without palette or unrelated profiles."),
            heading("Complete library archive", 2),
            bullet("Export Library writes every profile plus the saved color palette to a .macropad.zip archive."),
            bullet("Import Library loads the archive into the local editor; review before syncing."),
            bullet("Use this format for migration, disaster recovery, or sharing a complete setup."),
            heading("Per-device backups", 2),
            p(
                "A changed Sync Device operation creates a backup identified by device UID and timestamp "
                "before writing. Backups loads a selected snapshot into the local editor. It does not "
                "write the device immediately. Compare the loaded snapshot, then Sync only if restoration "
                "is intended."
            ),
            data_table(
                ["Goal", "Best command", "Device changes immediately?"],
                [
                    ["Share one parent profile", "Export... / Import...", "No"],
                    ["Move the complete setup", "Export Library / Import Library", "No"],
                    ["Return one device to a prior state", "Backups, review, then Sync Device", "Only at Sync"],
                    ["Capture current device as working copy", "Import Device", "No"],
                ],
                [58, 68, 42],
            ),
        ]
    )


def add_sync_safety(story: list[Flowable]) -> None:
    story.extend(
        [
            heading("11. Preview, compare, synchronize, and recover"),
            heading("Preview RGB", 2),
            p(
                "Preview RGB is temporary and affects only lighting for the selected layout. It is "
                "ideal for checking brightness, row grouping, warning colors, and disabled keys. Clear "
                "Preview restores normal lighting."
            ),
            heading("Compare", 2),
            p(
                "Compare reads the selected device and reports normalized differences. If comparison "
                "fails, verify the device is still mounted, the correct unit is selected, and profile "
                "JSON is readable."
            ),
            heading("What Sync Device does internally", 2),
            numbered(1, "Validate and normalize the local project."),
            numbered(2, "Save the local library."),
            numbered(3, "Read the selected device and compute changes."),
            numbered(4, "Stop if there are no changes."),
            numbered(5, "Show a change summary and request confirmation."),
            numbered(6, "Create a per-device backup."),
            numbered(7, "Write revisioned profile files and device_config.json."),
            numbered(8, "Commit profiles/index.json and profiles/revision.txt last."),
            numbered(9, "Flush filesystem changes and ask firmware to reload."),
            heading("Interrupted sync recovery", 2),
            numbered(1, "Do not repeatedly unplug and reconnect while the drive is active."),
            numbered(2, "After the drive settles, reconnect if needed and choose Refresh."),
            numbered(3, "Run Device Health."),
            numbered(4, "Import Device only if you want the device's surviving state to replace local edits."),
            numbered(5, "Otherwise Compare the saved local library and Sync again."),
            numbered(6, "If required files are missing, use Repair Firmware after confirming the device."),
        ]
    )


def add_multiple_devices(story: list[Flowable]) -> None:
    story.extend(
        [
            heading("12. Multiple MacroPads, friendly names, and deck roles"),
            p(
                "Every connected MacroPad is identified by mount path and UID. Name Device stores a "
                "local friendly alias, such as Left Manual Deck or Right App Deck. Import, preview, "
                "compare, health, backup, repair, and sync always target the selected device."
            ),
            heading("Synchronize the same library to two devices", 2),
            numbered(1, "Finish and save the local library."),
            numbered(2, "Select the first device, Compare, then Sync Device."),
            numbered(3, "Select the second device, Compare, then Sync Device."),
            numbered(4, "Run Device Health for each if firmware versions might differ."),
            heading("Manual, Profile, and App deck roles", 2),
            data_table(
                ["Role", "Behavior", "Example"],
                [
                    ["Manual deck", "Stays on the parent and layout selected with its encoder; ignores focused-app commands.", "A fixed general-purpose deck for media and system tools."],
                    ["Profile deck", "Follows the focused program's parent but restores its remembered normal layout.", "Firefox opens on the last manually selected Firefox key screen."],
                    ["App deck", "Follows the focused desktop application and selects its In App layout.", "Firefox controls appear when Firefox gains focus."],
                ],
                [31, 82, 55],
            ),
            p(
                "On the device, turn to Options or hold the encoder for about one second. Key 1 selects "
                "Manual, Key 2 selects Profile, Key 3 selects App, and encoder press cycles all three. "
                "The role is stored independently on each device and survives restart."
            ),
            heading("Automatic profile switching", 2),
            p(
                "The included user service observes focused i3 or Sway windows and selects matching "
                "parents on Profile and App decks. Profile mode keeps remembered normal keys; App mode "
                "selects In App keys. Firefox, VS Code, VLC, Discord, LM Studio, ComfyUI, Caja, Krita, "
                "LibreOffice, Blender, and other included profiles have matching support."
            ),
            p(
                "On all three deck roles, the same service keeps encoder scrolling short by exposing only "
                "profiles for open applications plus the pinned i3wm, quicklaunch, and options profiles. "
                "This is a temporary filter: every profile remains stored, and a restart without the "
                "service restores the full library. Firefox website matching sees the selected tab title "
                "in each browser window, not every inactive tab."
            ),
            code_block(
                ".venv/bin/python tools/install_profile_switcher.py\n"
                "systemctl --user status macropad-profile-switcher.service\n"
                "journalctl --user -u macropad-profile-switcher.service -n 50"
            ),
            p(
                "Rules live in ~/.config/macropad-profile-switcher.json. Restart the user service after "
                "editing them. Set filter_open_apps to false for the complete encoder list, or edit "
                "pinned_profiles to choose the utilities that always remain visible. Automatic In App "
                "selection does not overwrite the remembered normal layout."
            ),
        ]
    )


def add_health_layouts(story: list[Flowable]) -> None:
    story.extend(
        [
            heading("13. Device health, firmware repair, and keyboard layouts"),
            heading("Device Health", 2),
            p(
                "Device Health reports configurator version, firmware version, configuration revision, "
                "active profile, deck role, keyboard layout, required files, and serial status. Use it "
                "before repair because a mounted drive can still have a busy or unavailable serial port."
            ),
            heading("Repair Firmware", 2),
            p(
                "Repair Firmware asks for confirmation, attempts a backup, uses circup to install "
                "adafruit_macropad and keyboard-layout dependencies, copies code.py and macropad_core.py, "
                "preserves an existing device_config.json and profile library when possible, and reloads "
                "the device."
            ),
            callout(
                "Repair is a device write",
                "Verify the selected friendly name, UID, and mount path. Repair is appropriate for "
                "missing required files or a version mismatch, not for a simple key-layout edit.",
                colors.HexColor("#FFF0ED"),
            ),
            heading("Keyboard layout", 2),
            p(
                "Choose US or German to match the host desktop. The setting affects typed text and "
                "characters whose physical HID positions differ. Standard modifier shortcuts are usually "
                "familiar, but punctuation and Y/Z behavior can differ. Synchronize after changing layout."
            ),
            data_table(
                ["Symptom", "Likely cause", "Correction"],
                [
                    ["Y and Z are exchanged", "Host and configurator layouts differ.", "Select the host layout and sync."],
                    ["Punctuation is wrong", "Typed text is mapped through the wrong layout.", "Match both configurator and desktop layout."],
                    ["Ctrl+C works but typed command is wrong", "Modifiers are stable while text mapping differs.", "Correct Layout, then sync and retest."],
                ],
                [46, 70, 52],
            ),
        ]
    )


def add_limits(story: list[Flowable]) -> None:
    story.extend(
        [
            heading("14. Limits and validation reference"),
            data_table(
                ["Item", "Limit", "Behavior"],
                [
                    ["Parent profiles", "32", "Additional creation is blocked."],
                    ["Additional layouts per parent", "8, plus the primary", "Up to 9 encoder-press screens total."],
                    ["Profile or layout name", "24 characters", "Longer input is truncated."],
                    ["OLED icon", "2 characters", "Optional prefix."],
                    ["OLED key label", "6 characters", "Designed for the physical display grid."],
                    ["Action steps per control", "16", "Only the supported maximum is retained and validated."],
                    ["Hotkey names per step", "6", "Names are normalized to uppercase HID form."],
                    ["Text step", "512 characters", "Longer text is truncated."],
                    ["Delay", "0-10000 ms", "Values are clamped."],
                    ["Mouse X, Y, wheel", "-127 to 127", "Values are clamped."],
                    ["Brightness", "0-100 percent", "Default is 5 percent."],
                    ["Saved palette", "24 colors", "Recent unique colors are kept."],
                    ["Undo history", "100 states", "Newest editor states are retained."],
                ],
                [55, 38, 75],
            ),
            p(
                "Validation rejects unnamed profiles, unsupported consumer codes, unsupported click "
                "buttons, and invalid normalized projects before synchronization. Invalid colors fall "
                "back to defaults. Project and profile imports are normalized before use."
            ),
        ]
    )


def add_control_reference(story: list[Flowable]) -> None:
    story.extend(
        [
            heading("15. Complete control reference"),
            heading("Device toolbar", 2),
            data_table(
                ["Control", "Description", "Example"],
                [
                    ["Device", "Select the connected unit targeted by device commands.", "Choose Left App Deck before Sync."],
                    ["Refresh", "Scan mounted drives again.", "Connect a pad, then Refresh."],
                    ["Import Device", "Replace local editor data with the selected device library.", "Capture an existing device before editing."],
                    ["Preview RGB", "Temporarily show selected-layout colors.", "Inspect red warning keys."],
                    ["Clear Preview", "Restore normal device lighting.", "End a color check without syncing."],
                    ["Sync Device", "Back up and write the complete local library.", "Deploy the finished Firefox profile."],
                    ["Save Local", "Save immediately.", "Save before closing after many edits."],
                    ["Layout", "Choose host keyboard mapping.", "German for a de-DE desktop."],
                    ["Status", "Show autosave and sync state.", "Device differs means deployment is pending."],
                ],
                [35, 76, 57],
            ),
            heading("Editing, Library, Device, and File commands", 2),
            data_table(
                ["Command", "Description", "Example"],
                [
                    ["Undo / Redo", "Reverse or reapply editor changes.", "Undo an accidental drag."],
                    ["Copy / Paste control", "Duplicate a selected assignment.", "Copy Ctrl+C into another layout."],
                    ["Swap...", "Exchange exactly two controls.", "Swap Key 1 and Key 12."],
                    ["Compare", "List local-to-device differences.", "Review before Sync."],
                    ["Backups", "Load a historical device snapshot locally.", "Restore yesterday's library after review."],
                    ["Export / Import Library", "Move every profile and palette as an archive.", "Migrate to another computer."],
                    ["Device Health", "Inspect versions, required files, and serial.", "Diagnose a mounted but unresponsive pad."],
                    ["Repair Firmware", "Reinstall firmware dependencies while preserving profiles when possible.", "Restore a missing macropad_core.py."],
                    ["Name Device", "Assign a local alias to a UID.", "Left Manual Deck."],
                    ["Exit", "Close with save and preview cleanup.", "Ctrl+Q."],
                ],
                [40, 81, 47],
            ),
            heading("Profile and layout controls", 2),
            data_table(
                ["Control", "Description", "Example"],
                [
                    ["Add / Duplicate / Delete", "Create, copy, or remove a parent profile.", "Duplicate Editing for an alternate map."],
                    ["Up / Down / drag", "Change encoder-turn order.", "Put Firefox next to VS Code."],
                    ["Import... / Export...", "Move one profile as JSON.", "Share firefox.json."],
                    ["Template...", "Start from Editing, Media, or Blank.", "Use Media for transport keys."],
                    ["Clear profile", "Remove assignments but retain identity.", "Prepare a duplicate for redesign."],
                    ["Reset lights", "Restore default lighting and 5 percent brightness.", "Undo an overbright experiment."],
                    ["Screens list", "Select and order encoder-press layouts.", "Browse, Tabs, Tools, In App."],
                    ["+ / Duplicate / Up / Down / -", "Manage additional layout screens.", "Duplicate Browse into Tabs."],
                    ["Profile name / Layout name", "Name the parent and selected screen.", "Firefox / Tabs."],
                    ["OLED icon / intensity", "Set two-character prefix and per-layout brightness.", "FF at 5 percent."],
                ],
                [48, 77, 43],
            ),
            heading("Control editor and macro-step fields", 2),
            data_table(
                ["Control", "Description", "Example"],
                [
                    ["Name / OLED label", "Set GUI description and six-character device label.", "Command palette / CMDPAL."],
                    ["Unset key", "Clear labels and action steps.", "Leave Key 12 unassigned."],
                    ["Illuminate / Idle / Pressed", "Enable light and choose resting and feedback colors.", "Green idle, white pressed."],
                    ["Palette / Apply to / Idle / Pressed", "Reuse colors across selected keys, a row, or all keys.", "Red idle for a Stop row."],
                    ["Save current", "Store the selected key's idle color.", "Save a custom purple."],
                    ["Step list", "Review, select, double-click, and drag execution steps.", "Delay before text."],
                    ["Add / Edit / Remove / Move", "Manage the action sequence.", "Move terminal delay before text."],
                    ["Safe preview", "Summarize without sending input.", "Review shutdown steps."],
                    ["Run on device", "Confirm and execute through the selected pad.", "Test Volume Up."],
                    ["Preset / Type", "Choose a common action and its step type.", "Copy preset creates CONTROL+C."],
                    ["Hotkey fields", "Enter or search HID names.", "CONTROL, SHIFT, S."],
                    ["Text", "Type literal content.", "pamac checkupdates."],
                    ["Consumer", "Choose a media code.", "PLAY_PAUSE."],
                    ["Mouse fields", "Choose click or signed movement.", "RIGHT_BUTTON or wheel -1."],
                    ["Delay", "Pause in milliseconds.", "800 ms after opening a terminal."],
                    ["OK / Cancel", "Save or discard the edited step.", "Cancel keeps the original delay."],
                ],
                [43, 80, 45],
            ),
        ]
    )


def add_troubleshooting(story: list[Flowable]) -> None:
    story.extend(
        [
            heading("16. Troubleshooting"),
            data_table(
                ["Problem", "Checks", "Resolution"],
                [
                    ["No device is listed", "CIRCUITPY mounted? Data cable? Correct board ID? Not RPI-RP2?", "Reconnect, wait for mount, then Refresh."],
                    ["Preview or Run fails", "Selected device correct? Serial port busy?", "Close serial monitors, reconnect, run Device Health."],
                    ["Import fails", "device_config.json and profiles/index.json readable?", "Repair malformed files from a known export or use Repair Firmware when required files are missing."],
                    ["Wrong symbols are typed", "Layout selector matches host?", "Select US or German correctly, sync, and retest."],
                    ["Macro types too early", "Does a window need focus time?", "Insert or increase a delay, often 800 ms."],
                    ["Macro executes too much", "Is ENTER a separate final step?", "Remove ENTER and use Safe preview."],
                    ["New color not on device", "Local saved - device differs?", "Preview RGB, then Sync Device."],
                    ["Encoder press editor disabled", "Does the parent have multiple layouts?", "This is expected; encoder press cycles layouts."],
                    ["Profile order wrong on device", "Was drag order synced?", "Compare and Sync Device."],
                    ["Device stale after sync", "Drive activity complete? Firmware reload received?", "Wait, reconnect, Refresh, Device Health, Compare."],
                    ["Firmware files missing", "Device Health missing list?", "Confirm the selected device, then Repair Firmware."],
                    ["Profile or App deck does not follow focus", "Service active? Matching rule? Automatic role selected?", "Inspect systemctl and journalctl output, then restart the service."],
                    ["Profile deck shows In App keys", "Role really set to Profile rather than App?", "Open Options and press Key 2."],
                    ["Manual choice is overwritten", "Device accidentally set to App role?", "Open Options and choose Manual deck."],
                ],
                [46, 68, 54],
            ),
            heading("When to use each recovery source", 2),
            bullet("Use the local library when your latest edits are correct and only the device is stale."),
            bullet("Use Import Device when the device is authoritative and should replace local edits."),
            bullet("Use Backups when a previous device snapshot is authoritative."),
            bullet("Use an exported library archive when migrating or recovering the complete setup."),
            bullet("Use Repair Firmware for missing runtime files or dependencies, not ordinary profile differences."),
        ]
    )


def add_checklists_glossary(story: list[Flowable]) -> None:
    story.extend(
        [
            heading("17. Operational checklists"),
            heading("Before running a new macro", 2),
            bullet("Read the step list from top to bottom."),
            bullet("Use Safe preview."),
            bullet("Remove ENTER from terminal, shutdown, delete, or reboot templates during initial testing."),
            bullet("Focus a harmless application or document."),
            bullet("Confirm the selected device."),
            bullet("Run on device only after the confirmation text matches your intent."),
            heading("Before synchronization", 2),
            bullet("Save Local and confirm the intended parent and layout are selected."),
            bullet("Select the correct MacroPad by friendly name, UID, and mount path."),
            bullet("Compare and investigate unexpected removals or large changes."),
            bullet("Preview RGB when brightness or risk colors changed."),
            bullet("Keep the USB connection stable until drive activity stops."),
            heading("Before firmware repair", 2),
            bullet("Run Device Health first."),
            bullet("Confirm circup is available in the application environment."),
            bullet("Confirm the selected device and preserve a complete export when practical."),
            bullet("Use Repair Firmware only for firmware/dependency problems."),
            heading("Glossary", 2),
            data_table(
                ["Term", "Meaning"],
                [
                    ["Parent profile", "A top-level profile selected by turning the encoder."],
                    ["Layout / subprofile", "One 12-key screen within a parent, selected by encoder press."],
                    ["Local library", "The GUI working copy stored in the computer's application-data folder."],
                    ["Device library", "The profile set currently stored on the selected CIRCUITPY drive."],
                    ["Control", "One of 12 keys or the single-layout encoder-press assignment."],
                    ["Step", "One hotkey, text, consumer, mouse, or delay operation in a control sequence."],
                    ["HID name", "CircuitPython key identifier such as CONTROL, ENTER, or PAGE_DOWN."],
                    ["Consumer code", "Operating-system media command such as MUTE or PLAY_PAUSE."],
                    ["Preview RGB", "Temporary lighting display that does not deploy profile data."],
                    ["Sync", "Validated, backed-up write of the local library to the selected device."],
                    ["Manual deck", "Device role that stays on encoder-selected profiles."],
                    ["Profile deck", "Device role that follows the focused parent and keeps remembered normal keys."],
                    ["App deck", "Device role that follows focused-application rules."],
                    ["In App", "Contextual layout selected in App mode without replacing normal-layout memory."],
                ],
                [43, 125],
            ),
            KeepTogether(
                [
                    heading("18. Final quick-start recipe"),
                    numbered(1, "Connect the MacroPad and choose Refresh."),
                    numbered(2, "Select the correct device."),
                    numbered(3, "Import Device if it contains profiles to preserve."),
                    numbered(4, "Create or select a parent profile and layout."),
                    numbered(5, "Select a key; set Name, OLED label, idle color, and pressed color."),
                    numbered(6, "Add macro steps and use Safe preview."),
                    numbered(7, "Save Local."),
                    numbered(8, "Compare with the device."),
                    numbered(9, "Preview RGB if lighting changed."),
                    numbered(10, "Sync Device and wait for drive activity to finish."),
                    numbered(11, "Test the physical key in a harmless context."),
                    Spacer(1, 6 * mm),
                    callout(
                        "You now have a recoverable workflow",
                        "Local autosave protects editor work, Compare exposes differences, Preview RGB checks "
                        "lighting without deployment, Sync creates a per-device backup, and complete Library "
                        "Export provides a portable recovery point.",
                    ),
                ]
            ),
        ]
    )


def build_story() -> list[Flowable]:
    story: list[Flowable] = []
    add_cover(story)
    add_toc(story)
    add_foundations(story)
    add_installation(story)
    add_interface(story)
    add_first_workflow(story)
    add_profiles(story)
    add_subprofiles(story)
    add_labels_rgb(story)
    add_actions(story)
    add_examples(story)
    add_library_device(story)
    add_sync_safety(story)
    add_multiple_devices(story)
    add_health_layouts(story)
    add_limits(story)
    add_control_reference(story)
    add_troubleshooting(story)
    add_checklists_glossary(story)
    return story


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = TutorialDocTemplate(str(OUTPUT))
    doc.multiBuild(build_story())
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
