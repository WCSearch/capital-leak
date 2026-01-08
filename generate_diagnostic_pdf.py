#!/usr/bin/env python3
"""
WCSearch Working Capital Diagnostic PDF Generator
Generates a professional 1-page diagnostic report from ERP event log analysis
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.platypus.flowables import Flowable
from reportlab.pdfgen import canvas
from datetime import datetime
import os


class ColoredBox(Flowable):
    """A colored box for the executive summary"""
    def __init__(self, width, height, color):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.color = color

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.rect(0, 0, self.width, self.height, fill=1, stroke=0)


def format_currency_millions(amount):
    """Format currency in millions (e.g., $156.7M)"""
    if amount == 0:
        return "$0"
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    elif amount >= 1_000:
        return f"${amount / 1_000:.0f}K"
    else:
        return f"${amount:,.0f}"


def format_currency_thousands(amount):
    """Format currency with thousands separator (e.g., $127,450)"""
    return f"${amount:,.2f}"


def get_priority_color(priority):
    """Return color for priority badge"""
    if priority == 'HIGH':
        return colors.HexColor('#DC3545')  # Red
    elif priority == 'MEDIUM':
        return colors.HexColor('#FD7E14')  # Orange
    else:
        return colors.HexColor('#6C757D')  # Gray


def create_diagnostic_pdf(diagnostic_data, output_path='/mnt/user-data/outputs/diagnostic_report.pdf'):
    """
    Generate a professional 1-page diagnostic PDF

    Args:
        diagnostic_data: Dictionary containing company info, metrics, and findings
        output_path: Path where PDF should be saved
    """

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Create PDF with margins
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )

    # Container for PDF elements
    elements = []

    # Define styles
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    company_name_style = ParagraphStyle(
        'CompanyName',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#0066CC'),
        spaceAfter=4,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#666666'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )

    tagline_style = ParagraphStyle(
        'Tagline',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#888888'),
        spaceAfter=16,
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique'
    )

    finding_title_style = ParagraphStyle(
        'FindingTitle',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=4,
        fontName='Helvetica-Bold'
    )

    finding_detail_style = ParagraphStyle(
        'FindingDetail',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#333333'),
        spaceAfter=2,
        fontName='Helvetica',
        leading=10
    )

    finding_emphasis_style = ParagraphStyle(
        'FindingEmphasis',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#333333'),
        spaceAfter=2,
        fontName='Helvetica-Bold',
        leading=10
    )

    # --- HEADER SECTION ---
    elements.append(Paragraph("WCSearch", title_style))
    elements.append(Paragraph("Working Capital Diagnostic Report", title_style))
    elements.append(Spacer(1, 0.1*inch))

    elements.append(Paragraph(diagnostic_data['company_name'], company_name_style))
    elements.append(Paragraph(f"Analysis Date: {diagnostic_data['analysis_date']}", subtitle_style))
    elements.append(Paragraph("Surgical Analysis of ERP Event Logs", tagline_style))

    # --- EXECUTIVE SUMMARY BOX ---
    ccc = diagnostic_data['ccc_metrics']
    recovery = diagnostic_data['total_recovery_potential']
    num_findings = len(diagnostic_data['findings'])

    summary_data = [
        ['Cash Conversion Cycle', f"{ccc['ccc']:.1f} days"],
        ['Total Recovery Potential', format_currency_millions(recovery)],
        ['Issues Identified', str(num_findings)],
        ['Confidence Level', 'High (ERP Event Log Analysis)']
    ]

    summary_table = Table(summary_data, colWidths=[3*inch, 2.5*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E8F4F8')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1a1a1a')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#0066CC')),
    ]))

    elements.append(summary_table)
    elements.append(Spacer(1, 0.15*inch))

    # --- FINDINGS SECTION ---
    # Sort findings by amount_at_risk and take top 4
    sorted_findings = sorted(
        diagnostic_data['findings'],
        key=lambda x: x['amount_at_risk'],
        reverse=True
    )[:4]

    elements.append(Paragraph("<b>Key Findings</b>",
                             ParagraphStyle('SectionHeader', parent=styles['Heading2'],
                                          fontSize=12, textColor=colors.HexColor('#0066CC'),
                                          spaceAfter=8, fontName='Helvetica-Bold')))

    for idx, finding in enumerate(sorted_findings):
        # Finding header with badges
        priority_color = get_priority_color(finding['priority'])

        header_data = [[
            Paragraph(f"<b>{finding['component']}</b>",
                     ParagraphStyle('Badge', fontSize=8, textColor=colors.white, alignment=TA_CENTER)),
            Paragraph(f"<b>{finding['priority']}</b>",
                     ParagraphStyle('Badge', fontSize=8, textColor=colors.white, alignment=TA_CENTER)),
            Paragraph(f"<b>{finding['issue_title']}</b>", finding_title_style)
        ]]

        header_table = Table(header_data, colWidths=[0.6*inch, 0.7*inch, 5.2*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#0066CC')),
            ('BACKGROUND', (1, 0), (1, 0), priority_color),
            ('ALIGN', (0, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (1, 0), 3),
            ('PADDING', (2, 0), (2, 0), 0),
        ]))

        elements.append(header_table)
        elements.append(Spacer(1, 0.05*inch))

        # Finding metrics
        metrics_data = [[
            f"Amount at Risk: {format_currency_millions(finding['amount_at_risk'])}",
            f"Transactions: {finding['transaction_count']}",
            f"Days Impact: {finding['days_impact']}"
        ]]

        metrics_table = Table(metrics_data, colWidths=[2.2*inch, 2.2*inch, 2.1*inch])
        metrics_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#DC3545')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ]))

        elements.append(metrics_table)
        elements.append(Spacer(1, 0.04*inch))

        # Root cause
        elements.append(Paragraph(f"<b>Root Cause:</b> {finding['root_cause']}", finding_detail_style))
        elements.append(Spacer(1, 0.04*inch))

        # Example transaction
        ex = finding['example_transaction']

        # Transaction header
        tx_header = f"<b>Example Transaction:</b> {ex['transaction_number']} | Amount: {format_currency_thousands(ex['amount'])} | Status: {ex['status']}"
        elements.append(Paragraph(tx_header, finding_detail_style))

        # Key events (limit to 4, highlight MISSING)
        events_text = "<b>Key Events:</b> "
        for event_idx, event in enumerate(ex['key_events'][:4]):
            if 'MISSING' in event:
                events_text += f'<font color="#DC3545"><b>{event}</b></font>'
            else:
                events_text += event
            if event_idx < len(ex['key_events'][:4]) - 1:
                events_text += " • "

        elements.append(Paragraph(events_text, finding_detail_style))

        # Add spacing between findings (less for last one)
        if idx < len(sorted_findings) - 1:
            elements.append(Spacer(1, 0.1*inch))

    # --- FOOTER ---
    elements.append(Spacer(1, 0.15*inch))

    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.HexColor('#666666'),
        alignment=TA_CENTER,
        fontName='Helvetica'
    )

    elements.append(Paragraph(
        f"Confidential - Prepared for {diagnostic_data['company_name']} | "
        f"Page 1 of 1 | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
        f"For questions: linda@wcsearch.com",
        footer_style
    ))

    # Build PDF
    doc.build(elements)

    print(f"✓ PDF generated successfully: {output_path}")
    return output_path


if __name__ == "__main__":
    # Sample data for testing
    diagnostic_data = {
        'company_name': 'TechMfg Industries',
        'analysis_date': '2025-01-07',
        'ccc_metrics': {
            'dso': 85.2,
            'dio': 588.9,
            'dpo': 45.3,
            'ccc': 628.8
        },
        'total_recovery_potential': 156700000,  # $156.7M
        'findings': [
            {
                'component': 'DSO',
                'priority': 'HIGH',
                'issue_title': 'Billing Trigger Disabled',
                'amount_at_risk': 18500000,
                'days_impact': 143,
                'transaction_count': 143,
                'root_cause': 'SD module billing trigger disabled on 2024-03-17, preventing automated invoice generation for fulfilled orders',
                'example_transaction': {
                    'transaction_number': 'INV-2024-000543',
                    'amount': 127450.00,
                    'days_outstanding': 287,
                    'status': 'FULFILLED_NOT_BILLED',
                    'key_events': [
                        '2024-03-19: Order created',
                        '2024-03-20: Goods shipped',
                        'MISSING: Invoice generation event'
                    ]
                }
            },
            {
                'component': 'DSO',
                'priority': 'MEDIUM',
                'issue_title': 'Approval Workflow Bottleneck',
                'amount_at_risk': 4200000,
                'days_impact': 31,
                'transaction_count': 31,
                'root_cause': 'Approver BWILSON left company on 2024-06-15, leaving 31 invoices stuck in approval queue',
                'example_transaction': {
                    'transaction_number': 'INV-2024-001247',
                    'amount': 143200.00,
                    'days_outstanding': 198,
                    'status': 'PENDING_APPROVAL',
                    'key_events': [
                        '2024-06-10: Order created',
                        '2024-06-13: Goods shipped',
                        '2024-06-14: Invoice generated',
                        '2024-06-14: Approval assigned to BWILSON',
                        'MISSING: Approval event (BWILSON departed 2024-06-15)'
                    ]
                }
            },
            {
                'component': 'DIO',
                'priority': 'HIGH',
                'issue_title': 'Goods Receipt Without Valuation',
                'amount_at_risk': 0,  # No value because valuation never posted
                'days_impact': 87,
                'transaction_count': 87,
                'root_cause': 'MM module failed to post valuations for goods receipts starting 2024-05-12, creating invisible inventory',
                'example_transaction': {
                    'transaction_number': 'MAT-487392',
                    'amount': 0.00,
                    'days_outstanding': 240,
                    'status': 'RECEIVED_NOT_VALUED',
                    'key_events': [
                        '2024-05-14: Goods receipt posted (qty: 450)',
                        'MISSING: Valuation posted event'
                    ]
                }
            },
            {
                'component': 'DPO',
                'priority': 'MEDIUM',
                'issue_title': 'Approval Workflow Bottleneck',
                'amount_at_risk': 7800000,
                'days_impact': 56,
                'transaction_count': 56,
                'root_cause': 'Approver JSMITH left company on 2024-07-22, leaving 56 invoices stuck in approval queue',
                'example_transaction': {
                    'transaction_number': 'APINV-2024-001156',
                    'amount': 156700.00,
                    'days_outstanding': 169,
                    'status': 'PENDING_APPROVAL',
                    'key_events': [
                        '2024-07-23: Invoice received from vendor',
                        '2024-07-23: Approval assigned to JSMITH',
                        'MISSING: Approval event (JSMITH departed 2024-07-22)'
                    ]
                }
            }
        ]
    }

    # Generate PDF
    create_diagnostic_pdf(diagnostic_data, '/mnt/user-data/outputs/diagnostic_report.pdf')
