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
from pathlib import Path
import os
import sys
import argparse
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import recovery analysis
from utils.recovery_analysis import calculate_dio_recovery
from utils.dio_trapped_capital_unified import DIOTrappedCapitalCalculator
from utils.company_type_detector import detect_company_type


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

    # Add company type and methodology badge
    company_type = diagnostic_data.get('company_type', 'UNKNOWN')
    methodology = diagnostic_data.get('methodology', 'Standard Analysis')

    type_badge_style = ParagraphStyle(
        'TypeBadge',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#0066CC'),
        fontName='Helvetica-Bold',
        spaceAfter=2
    )

    methodology_style = ParagraphStyle(
        'Methodology',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#666666'),
        fontName='Helvetica-Oblique',
        spaceAfter=4
    )

    elements.append(Paragraph(f"Company Type: {company_type}", type_badge_style))
    elements.append(Paragraph(f"Methodology: {methodology}", methodology_style))
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

    # --- DIO RECOVERY ANALYSIS SECTION ---
    if diagnostic_data.get('dio_recovery_analysis'):
        elements.append(Spacer(1, 0.15*inch))

        recovery = diagnostic_data['dio_recovery_analysis']

        # Section header
        recovery_header_style = ParagraphStyle(
            'RecoveryHeader',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#0066CC'),
            spaceAfter=6,
            fontName='Helvetica-Bold'
        )
        elements.append(Paragraph("DIO NET RECOVERY ANALYSIS", recovery_header_style))

        # Recovery breakdown table
        recovery_data = [
            ['Category', 'Amount', 'Recoverable'],
            ['Trapped Capital (Fully Recoverable)', format_currency_millions(recovery['trapped_capital']), format_currency_millions(recovery['trapped_capital'])],
            ['Partial Recovery (Liquidation)', format_currency_millions(recovery['total_value'] - recovery['trapped_capital'] - recovery['recognized_losses']) if recovery['total_value'] > 0 else '$0.0M', format_currency_millions(recovery['partial_recovery'])],
            ['Recognized Losses (Write-offs)', format_currency_millions(recovery['recognized_losses']), '$0.0M'],
            ['TOTAL', format_currency_millions(recovery['total_value']), f"{format_currency_millions(recovery['net_recovery'])} ({recovery['recovery_rate']:.1f}%)']
        ]

        recovery_table = Table(recovery_data, colWidths=[2.8*inch, 1.6*inch, 1.6*inch])
        recovery_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066CC')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            # Data rows
            ('BACKGROUND', (0, 1), (-1, -2), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -2), colors.black),
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 8),
            # Total row
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E8F4F8')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#0066CC')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 9),
            # Borders
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#0066CC')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))

        elements.append(recovery_table)
        elements.append(Spacer(1, 0.08*inch))

        # Recovery note
        recovery_note_style = ParagraphStyle(
            'RecoveryNote',
            parent=styles['Normal'],
            fontSize=7,
            textColor=colors.HexColor('#666666'),
            fontName='Helvetica-Oblique'
        )
        elements.append(Paragraph(
            f"<b>Net Recovery:</b> ${recovery['net_recovery']:,.0f} represents actual cash that can be freed "
            f"({recovery['recovery_rate']:.1f}% of total DIO value). Excludes recognized losses requiring write-offs.",
            recovery_note_style
        ))

    # --- COMPONENT CASCADE (Manufacturing Only) ---
    if diagnostic_data.get('component_cascade') and len(diagnostic_data['component_cascade']) > 0:
        elements.append(Spacer(1, 0.12*inch))

        cascade_header_style = ParagraphStyle(
            'CascadeHeader',
            parent=styles['Heading2'],
            fontSize=10,
            textColor=colors.HexColor('#DC3545'),
            spaceAfter=6,
            fontName='Helvetica-Bold'
        )
        elements.append(Paragraph("COMPONENT SHORTAGE CASCADE ANALYSIS", cascade_header_style))

        cascade_note_style = ParagraphStyle(
            'CascadeNote',
            parent=styles['Normal'],
            fontSize=7,
            textColor=colors.HexColor('#666666'),
            fontName='Helvetica-Oblique',
            spaceAfter=4
        )
        elements.append(Paragraph(
            "Single component shortages impact multiple work orders. Root cause analysis shows:",
            cascade_note_style
        ))

        # Build cascade table with top 3 component shortages
        cascade_data = [['Component', 'Lead Time', 'WOs Affected', 'Total Trapped']]

        sorted_components = sorted(
            diagnostic_data['component_cascade'].items(),
            key=lambda x: x[1]['total_trapped'],
            reverse=True
        )[:3]  # Top 3

        for comp_name, comp_data in sorted_components:
            cascade_data.append([
                comp_name,
                f"{comp_data['lead_time']} days",
                str(len(comp_data['work_orders_affected'])),
                format_currency_millions(comp_data['total_trapped'])
            ])

        cascade_table = Table(cascade_data, colWidths=[2.0*inch, 1.3*inch, 1.3*inch, 1.4*inch])
        cascade_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#DC3545')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            # Data rows
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            # Borders
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#DC3545')),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))

        elements.append(cascade_table)
        elements.append(Spacer(1, 0.05*inch))

        elements.append(Paragraph(
            "<b>System Issue:</b> Work orders released without component availability checks. "
            "Recommend: Configure 'Check Material Availability = YES' before release.",
            recovery_note_style
        ))

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


def get_supabase_client() -> Client:
    """Initialize Supabase client"""
    try:
        # Try to get from .streamlit/secrets.toml first
        secrets_file = Path(".streamlit/secrets.toml")
        if secrets_file.exists():
            import toml
            secrets = toml.load(secrets_file)
            url = secrets.get('supabase', {}).get('url')
            key = secrets.get('supabase', {}).get('service_role_key') or secrets.get('supabase', {}).get('key')
        else:
            url = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "https://vlbvrhotrlipaoedudys.supabase.co")
            # Prefer service role key for reading data (bypasses RLS)
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY", "")

        # Extract API URL from PostgreSQL connection string if needed
        if url and url.startswith("postgresql://"):
            # Format: postgresql://postgres:password@db.PROJECT_REF.supabase.co:5432/postgres
            parts = url.split("@")
            if len(parts) > 1:
                host_part = parts[1].split(":")[0]  # db.PROJECT_REF.supabase.co
                project_ref = host_part.replace("db.", "").replace(".supabase.co", "")
                url = f"https://{project_ref}.supabase.co"

        if not key or key == "YOUR_SERVICE_ROLE_KEY_HERE":
            print("✗ Error: Supabase service role key not found")
            print("  Please set SUPABASE_SERVICE_ROLE_KEY in .env file")
            print("  Get it from: Supabase Dashboard → Settings → API → service_role key")
            sys.exit(1)

        client = create_client(url, key)
        return client
    except Exception as e:
        print(f"✗ Failed to connect to Supabase: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def fetch_company_data(client: Client, company_id: str):
    """Fetch company data from Supabase"""
    try:
        # Fetch company info
        company_response = client.table('companies').select('*').eq('company_id', company_id).execute()
        if not company_response.data:
            print(f"✗ Company not found: {company_id}")
            sys.exit(1)

        company = company_response.data[0]

        # Fetch CCC metrics
        metrics_response = client.table('ccc_metrics').select('*').eq('company_id', company_id).execute()
        metrics = metrics_response.data[0] if metrics_response.data else None

        # Fetch transactions to analyze
        transactions_response = client.table('transactions').select('*').eq('company_id', company_id).execute()
        transactions = transactions_response.data

        return {
            'company': company,
            'metrics': metrics,
            'transactions': transactions
        }
    except Exception as e:
        print(f"✗ Failed to fetch company data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def build_diagnostic_data(data):
    """Build diagnostic data structure from Supabase data"""
    company = data['company']
    metrics = data['metrics']
    transactions = data['transactions']

    # Analyze transactions to find issues
    findings = []
    dso_transactions = [t for t in transactions if t['component_type'] == 'DSO']
    dio_transactions = [t for t in transactions if t['component_type'] == 'DIO']
    dpo_transactions = [t for t in transactions if t['component_type'] == 'DPO']

    # Group by status to find issues
    status_groups = {}
    for trans in transactions:
        status = trans['status']
        if status not in status_groups:
            status_groups[status] = []
        status_groups[status].append(trans)

    # Build findings from problematic statuses
    problem_statuses = {
        'FULFILLED_NOT_BILLED': {'component': 'DSO', 'priority': 'HIGH', 'title': 'Billing Trigger Disabled'},
        'PENDING_APPROVAL': {'component': 'DSO', 'priority': 'MEDIUM', 'title': 'Approval Workflow Stuck'},
        'CREDIT_HOLD': {'component': 'DSO', 'priority': 'MEDIUM', 'title': 'Credit Holds'},
        'PAYMENT_RECEIVED_NOT_APPLIED': {'component': 'DSO', 'priority': 'HIGH', 'title': 'Payment Application Delays'},
        'UNAPPLIED_CASH': {'component': 'DSO', 'priority': 'MEDIUM', 'title': 'Unapplied Cash'},
        'MILESTONE_ACHIEVED_NOT_BILLED': {'component': 'DSO', 'priority': 'HIGH', 'title': 'Progress Billing Not Triggered'},
        'PENDING_CUSTOMER_ACCEPTANCE': {'component': 'DSO', 'priority': 'MEDIUM', 'title': 'Customer Acceptance Delays'},
        'RETAINAGE_ELIGIBLE_NOT_BILLED': {'component': 'DSO', 'priority': 'MEDIUM', 'title': 'Retainage Not Billed'},
        # DIO - Trapped Capital (Fully Recoverable)
        'RECEIVED_NOT_VALUED': {'component': 'DIO', 'priority': 'HIGH', 'title': 'Goods Receipt Without Valuation', 'recovery_type': 'TRAPPED_CAPITAL'},
        'COUNT_VARIANCE_POSITIVE': {'component': 'DIO', 'priority': 'MEDIUM', 'title': 'Cycle Count Positive Variances', 'recovery_type': 'TRAPPED_CAPITAL'},
        'QUALITY_HOLD_RELEASABLE': {'component': 'DIO', 'priority': 'MEDIUM', 'title': 'Quality Hold (Releasable)', 'recovery_type': 'TRAPPED_CAPITAL'},
        'QUALITY_HOLD': {'component': 'DIO', 'priority': 'MEDIUM', 'title': 'Quality Hold Stall', 'recovery_type': 'TRAPPED_CAPITAL'},
        'RESERVED_CANCELLED_ORDER': {'component': 'DIO', 'priority': 'MEDIUM', 'title': 'Ghost Allocations', 'recovery_type': 'TRAPPED_CAPITAL'},
        'STAGED_NOT_SHIPPED': {'component': 'DIO', 'priority': 'MEDIUM', 'title': 'Cross-Dock Staging Timeouts', 'recovery_type': 'TRAPPED_CAPITAL'},
        'RELEASED_NOT_STARTED': {'component': 'DIO', 'priority': 'HIGH', 'title': 'Work Order Release Delays', 'recovery_type': 'TRAPPED_CAPITAL'},
        'AT_SUBCONTRACTOR': {'component': 'DIO', 'priority': 'MEDIUM', 'title': 'Subcontract PO Delays', 'recovery_type': 'TRAPPED_CAPITAL'},
        # DIO - Partial Recovery (Liquidation)
        'OBSOLETE_LIQUIDATION': {'component': 'DIO', 'priority': 'MEDIUM', 'title': 'Obsolete Inventory (Liquidation)', 'recovery_type': 'PARTIAL_RECOVERY'},
        # DIO - Recognized Losses
        'COUNT_VARIANCE_NEGATIVE': {'component': 'DIO', 'priority': 'LOW', 'title': 'Cycle Count Negative Variances', 'recovery_type': 'RECOGNIZED_LOSS'},
        'QUALITY_HOLD_FAILED': {'component': 'DIO', 'priority': 'LOW', 'title': 'Quality Hold (Failed)', 'recovery_type': 'RECOGNIZED_LOSS'},
        'OBSOLETE_ZERO_VALUE': {'component': 'DIO', 'priority': 'LOW', 'title': 'Obsolete Inventory (Zero Value)', 'recovery_type': 'RECOGNIZED_LOSS'},
        'DAMAGED_RTV_PENDING': {'component': 'DIO', 'priority': 'LOW', 'title': 'RTV Authorization Delays', 'recovery_type': 'RECOGNIZED_LOSS'},
        # Legacy statuses
        'COUNT_VARIANCE_PENDING': {'component': 'DIO', 'priority': 'MEDIUM', 'title': 'Cycle Count Adjustments Pending', 'recovery_type': 'TRAPPED_CAPITAL'},
        'QUARANTINE_PENDING_MRB': {'component': 'DIO', 'priority': 'MEDIUM', 'title': 'Quarantine Pending MRB', 'recovery_type': 'TRAPPED_CAPITAL'},
        'MATCHING_EXCEPTION': {'component': 'DPO', 'priority': 'HIGH', 'title': 'PO Receipt Matching Failures'},
        'UNMATCHED_FREIGHT': {'component': 'DPO', 'priority': 'MEDIUM', 'title': 'Freight Invoice Backlog'},
        'PO_CHANGE_NOT_CLOSED': {'component': 'DPO', 'priority': 'HIGH', 'title': 'PO Change Order Not Closed'},
        'MILESTONE_NOT_CONFIRMED': {'component': 'DPO', 'priority': 'MEDIUM', 'title': 'Subcontractor Milestone Payments'},
        'TERMS_MISMATCH_HOLD': {'component': 'DPO', 'priority': 'LOW', 'title': 'Supplier Terms Mismatch'},
        'VARIANCE_HOLD': {'component': 'DPO', 'priority': 'MEDIUM', 'title': 'Variance Holds'},
        'GR_IR_MISMATCH': {'component': 'DPO', 'priority': 'MEDIUM', 'title': 'GR/IR Mismatches'}
    }

    total_recovery = 0
    for status, info in problem_statuses.items():
        if status in status_groups:
            trans_list = status_groups[status]
            amount_at_risk = sum(t.get('outstanding_amount', 0) or 0 for t in trans_list)

            if amount_at_risk > 0 or len(trans_list) > 0:
                # Get example transaction
                example = trans_list[0] if trans_list else None

                finding = {
                    'component': info['component'],
                    'priority': info['priority'],
                    'issue_title': info['title'],
                    'amount_at_risk': amount_at_risk,
                    'days_impact': len(trans_list),
                    'transaction_count': len(trans_list),
                    'root_cause': f"{len(trans_list)} transactions in {status} status with ${amount_at_risk:,.2f} at risk",
                    'example_transaction': {
                        'transaction_number': example.get('transaction_number', 'N/A') if example else 'N/A',
                        'amount': example.get('amount', 0) if example else 0,
                        'days_outstanding': example.get('days_outstanding', 0) if example else 0,
                        'status': status,
                        'key_events': ['See event logs for details']
                    } if example else None
                }

                findings.append(finding)
                total_recovery += amount_at_risk

    # Sort findings by amount at risk (descending)
    findings.sort(key=lambda x: x['amount_at_risk'], reverse=True)

    # Take top 5 findings
    findings = findings[:5]

    # Calculate DIO recovery analysis using unified calculator
    dio_recovery = None
    company_type = 'UNKNOWN'
    methodology = 'Standard Analysis'
    component_cascade = None

    if dio_transactions:
        try:
            # Use the unified DIO calculator
            from datetime import datetime
            analysis_date = datetime.fromisoformat(metrics['calculation_date'] if metrics else company['analysis_date'])

            calculator = DIOTrappedCapitalCalculator(company['company_id'], analysis_date)
            full_results = calculator.calculate_trapped_capital()

            # Extract summary for PDF
            dio_recovery = {
                'total_value': full_results.get('total_dio_value', 0),
                'trapped_capital': full_results.get('trapped_capital', 0),
                'partial_recovery': full_results.get('partial_recovery_amount', 0),
                'recognized_losses': full_results.get('recognized_losses', 0),
                'net_recovery': full_results.get('net_recovery', 0),
                'recovery_rate': full_results.get('recovery_rate', 0),
                'breakdown_by_status': {}  # Could add detailed breakdown if needed
            }

            # Get company type and methodology
            company_type = full_results.get('company_type', 'UNKNOWN')
            methodology = full_results.get('methodology', 'Standard Analysis')

            # Get component cascade for manufacturing
            if company_type == 'MANUFACTURING':
                component_cascade = full_results.get('component_cascade_analysis', {})

        except Exception as e:
            print(f"   ⚠ Warning: Could not use unified calculator: {e}")
            print(f"   → Falling back to legacy recovery analysis")
            # Fallback to legacy calculator
            transactions_df = pd.DataFrame(dio_transactions)
            dio_recovery = calculate_dio_recovery(transactions_df)

            # Try to detect company type from company data
            try:
                company_type = company.get('company_type', 'UNKNOWN')
                if company_type == 'DISTRIBUTION':
                    methodology = 'Velocity-based time benchmarks (hours/days)'
                elif company_type == 'MANUFACTURING':
                    methodology = 'BOM critical path analysis with component availability verification'
            except:
                pass

    return {
        'company_name': company['company_name'],
        'company_type': company_type,
        'methodology': methodology,
        'analysis_date': metrics['calculation_date'] if metrics else company['analysis_date'],
        'ccc_metrics': {
            'dso': metrics['dso_value'] if metrics else 0,
            'dio': metrics['dio_value'] if metrics else 0,
            'dpo': metrics['dpo_value'] if metrics else 0,
            'ccc': metrics['ccc_value'] if metrics else 0
        },
        'total_recovery_potential': total_recovery,
        'dio_recovery_analysis': dio_recovery,
        'component_cascade': component_cascade,
        'findings': findings
    }


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Generate WCSearch Working Capital Diagnostic PDF',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_diagnostic_pdf.py --company-id f2c4b1b6-aab7-4ace-a050-8b0ee159c591
  python generate_diagnostic_pdf.py --company-id 79d556f0-fb62-4988-95b0-43d490f39126 --output reports/infor_report.pdf
        """
    )

    parser.add_argument(
        '--company-id',
        type=str,
        required=True,
        help='Company ID from Supabase'
    )

    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output PDF path (default: /mnt/user-data/outputs/<company_name>_diagnostic.pdf)'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("WCSEARCH WORKING CAPITAL DIAGNOSTIC PDF GENERATOR")
    print("=" * 80)
    print(f"Company ID: {args.company_id}")
    print("=" * 80)

    # Connect to Supabase
    print("\n[1/4] Connecting to Supabase...")
    client = get_supabase_client()
    print("   ✓ Connected")

    # Fetch company data
    print("\n[2/4] Fetching company data...")
    data = fetch_company_data(client, args.company_id)
    print(f"   ✓ Fetched data for: {data['company']['company_name']}")
    print(f"   ✓ Transactions: {len(data['transactions'])}")

    # Build diagnostic data
    print("\n[3/4] Analyzing transactions...")
    diagnostic_data = build_diagnostic_data(data)
    print(f"   ✓ Found {len(diagnostic_data['findings'])} issues")
    print(f"   ✓ Total recovery potential: {format_currency_millions(diagnostic_data['total_recovery_potential'])}")

    # Generate PDF
    print("\n[4/4] Generating PDF...")

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        # Create company-specific filename
        company_name_slug = diagnostic_data['company_name'].lower().replace(' ', '_').replace('.', '')
        output_path = f"/mnt/user-data/outputs/{company_name_slug}_diagnostic.pdf"

    create_diagnostic_pdf(diagnostic_data, output_path)

    print("\n" + "=" * 80)
    print("✅ PDF GENERATION COMPLETE")
    print("=" * 80)
    print(f"\nCompany: {diagnostic_data['company_name']}")
    print(f"Output: {output_path}")
    print(f"Recovery Potential: {format_currency_millions(diagnostic_data['total_recovery_potential'])}")
    print(f"Issues Found: {len(diagnostic_data['findings'])}")
