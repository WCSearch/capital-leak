"""
Trapped Cash Indicator Component

Displays priority targets for surgical working capital analysis.
"""

import streamlit as st
from typing import Dict, List, Optional
from utils.trapped_cash import format_currency, format_percentage


def render_trapped_cash_indicator(
    total_trapped: float,
    targets: List[Dict],
    on_begin_analysis_callback=None
) -> None:
    """
    Render the trapped cash indicator with priority targets.

    Args:
        total_trapped: Total trapped cash amount
        targets: List of target dictionaries with priority info
        on_begin_analysis_callback: Callback function when "Begin Analysis" is clicked
    """

    # Main container with custom styling
    st.markdown("""
        <style>
        .trapped-cash-container {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            border-radius: 10px;
            color: white;
            margin-bottom: 2rem;
        }
        .trapped-cash-title {
            font-size: 1.5rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }
        .trapped-cash-amount {
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 1.5rem;
        }
        .priority-section-title {
            font-size: 1.2rem;
            font-weight: bold;
            margin-top: 1.5rem;
            margin-bottom: 1rem;
        }
        .priority-card {
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            border: 2px solid;
        }
        .priority-high {
            background-color: #fee;
            border-color: #dc2626;
            color: #1f2937;
        }
        .priority-medium {
            background-color: #fffbeb;
            border-color: #f59e0b;
            color: #1f2937;
        }
        .priority-low {
            background-color: #f0fdf4;
            border-color: #16a34a;
            color: #1f2937;
        }
        .priority-label {
            font-weight: bold;
            font-size: 1rem;
            margin-bottom: 0.5rem;
        }
        .priority-component {
            font-size: 1.3rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }
        .priority-detail {
            margin: 0.3rem 0;
            font-size: 0.95rem;
        }
        </style>
    """, unsafe_allow_html=True)

    # Header section
    st.markdown(f"""
        <div class="trapped-cash-container">
            <div class="trapped-cash-title">💰 ESTIMATED TRAPPED CASH</div>
            <div class="trapped-cash-amount">{format_currency(total_trapped)}</div>
            <div class="priority-section-title">🎯 PRIORITY TARGETS</div>
        </div>
    """, unsafe_allow_html=True)

    # Render each priority target
    for target in targets:
        render_priority_card(target, on_begin_analysis_callback)


def render_priority_card(target: Dict, callback=None) -> None:
    """
    Render a single priority card for a component.

    Args:
        target: Target dictionary with component details
        callback: Callback function for the button
    """

    priority = target['priority']
    component = target['component']
    trapped = target['trapped']
    excess_days = target['excess_days']
    recovery_rate = target['recovery_rate']
    expected_recovery = target['expected_recovery']

    # Determine priority styling
    if priority == 'HIGH':
        emoji = '🔴'
        css_class = 'priority-high'
        label = 'HIGH PRIORITY'
    elif priority == 'MEDIUM':
        emoji = '🟡'
        css_class = 'priority-medium'
        label = 'MEDIUM PRIORITY'
    else:
        emoji = '🟢'
        css_class = 'priority-low'
        label = 'LOW PRIORITY'

    # Create columns for card and button
    col1, col2 = st.columns([4, 1])

    with col1:
        # Render card HTML
        st.markdown(f"""
            <div class="priority-card {css_class}">
                <div class="priority-label">{emoji} {label}</div>
                <div class="priority-component">{component}</div>
                <div class="priority-detail">{format_currency(trapped)} potential</div>
                <div class="priority-detail">{excess_days:.1f} excess days above benchmark</div>
                <div class="priority-detail">Expected recovery: {format_percentage(recovery_rate)} ({format_currency(expected_recovery)})</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        # Add button with styling
        st.markdown("<br>" * 2, unsafe_allow_html=True)  # Align button vertically
        button_key = f"begin_{component}_analysis"
        if st.button(f"Begin {component} Analysis", key=button_key, use_container_width=True):
            if callback:
                callback(component)


def render_surgical_target(
    component_type: str,
    initial_estimate: float,
    surgical_target: Optional[Dict]
) -> None:
    """
    Render surgical target information on component drill-down page.

    Args:
        component_type: 'DSO', 'DIO', or 'DPO'
        initial_estimate: Initial trapped cash estimate
        surgical_target: Dictionary with surgical target details
    """

    st.markdown("""
        <style>
        .surgical-target-box {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            padding: 1.5rem;
            border-radius: 8px;
            border: 3px solid #dc2626;
            margin: 1.5rem 0;
            color: white;
        }
        .surgical-target-title {
            font-size: 1.5rem;
            font-weight: bold;
            margin-bottom: 1rem;
        }
        .surgical-target-detail {
            font-size: 1.1rem;
            margin: 0.5rem 0;
        }
        </style>
    """, unsafe_allow_html=True)

    # Show initial estimate
    st.markdown(f"""
        <div style="background-color: #f3f4f6; padding: 1rem; border-radius: 8px; margin: 1rem 0;">
            <h3>{component_type} ANALYSIS</h3>
            <p><strong>Initial Estimate:</strong> {format_currency(initial_estimate)}</p>
        </div>
    """, unsafe_allow_html=True)

    # Show surgical target if available
    if surgical_target:
        st.markdown(f"""
            <div class="surgical-target-box">
                <div class="surgical-target-title">🎯 SURGICAL TARGET</div>
                <div class="surgical-target-detail">
                    <strong>{surgical_target['functional_area']}</strong> (GL {surgical_target['gl_account']})
                </div>
                <div class="surgical-target-detail">
                    💰 {format_currency(surgical_target['amount'])}
                </div>
                <div class="surgical-target-detail">
                    📊 {surgical_target['transaction_count']} transactions |
                    Avg {surgical_target['avg_days_outstanding']:.0f} days outstanding
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.info(f"No transaction data available for {component_type} analysis yet.")
