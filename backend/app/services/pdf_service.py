import io
from datetime import datetime, timezone
from typing import Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable
)
from app.models.issue import Issue


def generate_issue_work_order_pdf(issue: Issue) -> bytes:
    """
    Generates a professional, print-ready municipal work order PDF
    for field maintenance crews and infrastructure inspectors.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f172a'),
        alignment=0
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#2563eb')
    )
    meta_label_style = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#475569')
    )
    meta_val_style = ParagraphStyle(
        'MetaVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0f172a')
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=8,
        spaceAfter=4
    )
    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#334155')
    )
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#0f172a')
    )

    story = []

    # 1. Header with Municipal Badge
    header_data = [
        [
            Paragraph("<b>MUNICIPAL INFRASTRUCTURE COMMISSION</b><br/><font size=8 color='#64748b'>PUBLIC WORKS & ROAD SAFETY OPERATIONS</font>", subtitle_style),
            Paragraph(f"<b>WORK ORDER:</b> #{str(issue.id)[:8].upper()}<br/><font size=8 color='#64748b'>DATE: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</font>", ParagraphStyle('RightMeta', parent=meta_label_style, alignment=2))
        ]
    ]
    header_table = Table(header_data, colWidths=[340, 200])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#2563eb'), spaceBefore=2, spaceAfter=10))

    # 2. Main Title Banner
    story.append(Paragraph(f"WORK ORDER: {issue.title}", title_style))
    story.append(Spacer(1, 10))

    # 3. Key Parameters Grid (Category, Severity, Priority, Status)
    sev_color = "#ef4444" if issue.severity.value == "CRITICAL" else ("#f59e0b" if issue.severity.value == "HIGH" else "#3b82f6")
    param_data = [
        [
            Paragraph("CATEGORY", meta_label_style),
            Paragraph("SEVERITY", meta_label_style),
            Paragraph("PRIORITY SCORE", meta_label_style),
            Paragraph("CURRENT STATUS", meta_label_style)
        ],
        [
            Paragraph(f"<b>{issue.category.value}</b>", meta_val_style),
            Paragraph(f"<b><font color='{sev_color}'>{issue.severity.value}</font></b>", meta_val_style),
            Paragraph(f"<b>{issue.priority_score:.1f}/100 ({issue.priority_level.value})</b>", meta_val_style),
            Paragraph(f"<b>{issue.status.value}</b>", meta_val_style)
        ]
    ]
    param_table = Table(param_data, colWidths=[135, 135, 135, 135])
    param_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(param_table)
    story.append(Spacer(1, 12))

    # 4. Location & Geospatial Context
    story.append(Paragraph("1. Location & Environmental Context", section_heading))
    loc_data = [
        [
            Paragraph("STREET ADDRESS:", meta_label_style),
            Paragraph(issue.address or "Indiranagar, 100ft Road, Bangalore", meta_val_style),
            Paragraph("GPS COORDINATES:", meta_label_style),
            Paragraph(f"{issue.latitude:.6f}, {issue.longitude:.6f}", meta_val_style),
        ],
        [
            Paragraph("LOCATION ZONE:", meta_label_style),
            Paragraph(issue.location_zone.value if issue.location_zone else "MAIN_ROAD", meta_val_style),
            Paragraph("TRAFFIC DENSITY:", meta_label_style),
            Paragraph(issue.traffic_density.value if issue.traffic_density else "MEDIUM", meta_val_style),
        ]
    ]
    loc_table = Table(loc_data, colWidths=[110, 160, 110, 160])
    loc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ffffff')),
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#f1f5f9')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(loc_table)
    story.append(Spacer(1, 12))

    # 5. Dispatch & Department Assignment
    story.append(Paragraph("2. Dispatch & Municipal Crew Assignment", section_heading))
    dept_name = issue.assigned_department.value if issue.assigned_department else "Pending Assignment"
    disp_data = [
        [
            Paragraph("ASSIGNED DEPT:", meta_label_style),
            Paragraph(f"<b>{dept_name}</b>", meta_val_style),
            Paragraph("REPORT COUNT:", meta_label_style),
            Paragraph(f"{issue.report_count} Citizen Submissions", meta_val_style),
        ],
        [
            Paragraph("FIRST REPORTED:", meta_label_style),
            Paragraph(issue.created_at.strftime('%Y-%m-%d %H:%M UTC') if issue.created_at else "N/A", meta_val_style),
            Paragraph("LAST UPDATED:", meta_label_style),
            Paragraph(issue.updated_at.strftime('%Y-%m-%d %H:%M UTC') if issue.updated_at else "N/A", meta_val_style),
        ]
    ]
    disp_table = Table(disp_data, colWidths=[110, 160, 110, 160])
    disp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ffffff')),
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#f1f5f9')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(disp_table)
    story.append(Spacer(1, 12))

    # 6. Contributing Citizen Reports Summary Table
    story.append(Paragraph("3. Supporting Citizen Reports & Field Descriptions", section_heading))
    reports_data = [
        [
            Paragraph("REPORT ID", table_cell_bold),
            Paragraph("TIMESTAMP", table_cell_bold),
            Paragraph("DESCRIPTION", table_cell_bold)
        ]
    ]
    if hasattr(issue, 'reports') and issue.reports:
        for r in issue.reports[:4]:
            reports_data.append([
                Paragraph(str(r.id)[:8], table_cell),
                Paragraph(r.created_at.strftime('%m/%d %H:%M') if r.created_at else "N/A", table_cell),
                Paragraph(r.description[:80] + ("..." if len(r.description) > 80 else ""), table_cell)
            ])
    else:
        reports_data.append([
            Paragraph("REP-INIT", table_cell),
            Paragraph(datetime.now(timezone.utc).strftime('%m/%d %H:%M'), table_cell),
            Paragraph(issue.description or "Hazard identified and registered.", table_cell)
        ])

    rep_table = Table(reports_data, colWidths=[80, 90, 370])
    rep_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(rep_table)
    story.append(Spacer(1, 14))

    # 7. Field Inspector & Repair Crew Sign-Off Block
    story.append(Paragraph("4. Field Crew Sign-Off & Verification Certificate", section_heading))
    sign_data = [
        [
            Paragraph("<b>FIELD CREW LEAD:</b>", meta_label_style),
            Paragraph("____________________________", meta_val_style),
            Paragraph("<b>DATE STARTED:</b>", meta_label_style),
            Paragraph("____ / ____ / 20___", meta_val_style)
        ],
        [
            Paragraph("<b>SUPERVISING INSPECTOR:</b>", meta_label_style),
            Paragraph("____________________________", meta_val_style),
            Paragraph("<b>DATE COMPLETED:</b>", meta_label_style),
            Paragraph("____ / ____ / 20___", meta_val_style)
        ],
        [
            Paragraph("<b>MATERIALS USED:</b>", meta_label_style),
            Paragraph("[  ] Asphalt Cold Patch &nbsp;&nbsp; [  ] Concrete &nbsp;&nbsp; [  ] Luminaire Fixture &nbsp;&nbsp; [  ] Sign Post", table_cell),
            Paragraph("<b>QUALITY AUDIT:</b>", meta_label_style),
            Paragraph("[  ] PASSED &nbsp;&nbsp; [  ] RE-INSPECT", table_cell)
        ]
    ]
    sign_table = Table(sign_data, colWidths=[130, 170, 110, 130])
    sign_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fafafa')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#94a3b8')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(sign_table)

    # Build PDF document
    doc.build(story)
    return buffer.getvalue()
