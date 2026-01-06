"""
DSO Time-State Breakdown Component

Displays time-state decomposition for DSO diagnostic analysis.
"""

import streamlit as st
from typing import Dict, List, Optional
from utils.dso_analysis import format_currency, get_priority_emoji


def render_time_state_breakdown(
    time_state_summary: List[Dict],
    on_drill_down_callback=None
) -> None:
    """
    Render DSO time-state breakdown section.

    Args:
        time_state_summary: List of time state dictionaries with:
            - state_key: 'fulfilled_not_invoiced', 'credit_hold', etc.
            - name: Display name
            - priority: 'CRITICAL', 'MEDIUM', 'LOW'
            - color: 'red', 'amber', 'green'
            - total_amount: Total dollars in this state
            - count: Number of transactions
            - avg_days: Average days outstanding
            - fix_action: What to do
            - timeline: How long it takes
        on_drill_down_callback: Callback when user clicks drill down (receives state_key)
    """

    # CSS styling for time-state cards
    st.markdown("""
        <style>
        .time-state-section {
            margin: 2rem 0;
        }
        .time-state-header {
            font-size: 1.8rem;
            font-weight: bold;
            margin-bottom: 1.5rem;
            color: #1f2937;
        }
        .priority-header {
            font-size: 1.3rem;
            font-weight: bold;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }
        .time-state-card {
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            border: 2px solid;
            background-color: white;
        }
        .time-state-card-red {
            border-color: #dc2626;
            background-color: #fee;
        }
        .time-state-card-amber {
            border-color: #f59e0b;
            background-color: #fffbeb;
        }
        .time-state-card-green {
            border-color: #16a34a;
            background-color: #f0fdf4;
        }
        .time-state-name {
            font-size: 1.2rem;
            font-weight: bold;
            margin-bottom: 0.8rem;
            color: #1f2937;
        }
        .time-state-metric {
            font-size: 1rem;
            margin: 0.3rem 0;
            color: #374151;
        }
        .time-state-metric strong {
            color: #1f2937;
        }
        .time-state-action {
            margin-top: 0.8rem;
            padding-top: 0.8rem;
            border-top: 1px solid #d1d5db;
            font-size: 0.95rem;
            color: #4b5563;
        }
        .total-excess-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1.5rem;
            border-radius: 8px;
            color: white;
            margin: 2rem 0;
            text-align: center;
        }
        .total-excess-amount {
            font-size: 2rem;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown('<div class="time-state-section">', unsafe_allow_html=True)
    st.markdown('<div class="time-state-header">DSO TIME-STATE ANALYSIS</div>', unsafe_allow_html=True)

    # Group by priority
    critical_states = [s for s in time_state_summary if s['priority'] == 'CRITICAL']
    medium_states = [s for s in time_state_summary if s['priority'] == 'MEDIUM']
    low_states = [s for s in time_state_summary if s['priority'] == 'LOW']

    # Calculate totals
    total_amount = sum(s['total_amount'] for s in time_state_summary)
    total_count = sum(s['count'] for s in time_state_summary)

    # Render CRITICAL section
    if critical_states:
        st.markdown('### 🔴 CRITICAL (System/Process Fixes - No Customer Action Needed)', unsafe_allow_html=True)
        for state in critical_states:
            render_time_state_card(state, on_drill_down_callback)

    # Render MEDIUM section
    if medium_states:
        st.markdown('### 🟡 MEDIUM (Process/Policy Fixes - Some Coordination Required)', unsafe_allow_html=True)
        for state in medium_states:
            render_time_state_card(state, on_drill_down_callback)

    # Render LOW section
    if low_states:
        st.markdown('### 🟢 LOW PRIORITY (Behavioral - Requires Customer Action)', unsafe_allow_html=True)
        for state in low_states:
            render_time_state_card(state, on_drill_down_callback)

    # Total excess summary
    st.markdown(f"""
        <div class="total-excess-box">
            <div class="total-excess-amount">{format_currency(total_amount)}</div>
            <div>TOTAL EXCESS across {total_count} transactions</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def render_time_state_card(state: Dict, callback=None) -> None:
    """
    Render a single time-state card.

    Args:
        state: State dictionary with metrics
        callback: Callback when drill down is clicked
    """

    # Determine card styling based on color
    color_class_map = {
        'red': 'time-state-card-red',
        'amber': 'time-state-card-amber',
        'green': 'time-state-card-green'
    }
    card_class = color_class_map.get(state['color'], '')

    emoji = get_priority_emoji(state['priority'])

    # Create columns for card content and button
    col1, col2 = st.columns([5, 1])

    with col1:
        st.markdown(f"""
            <div class="time-state-card {card_class}">
                <div class="time-state-name">{state['name']}</div>
                <div class="time-state-metric">
                    <strong>Amount:</strong> {format_currency(state['total_amount'])} |
                    <strong>Count:</strong> {state['count']} |
                    <strong>Avg:</strong> {state['avg_days']:.1f} days
                </div>
                <div class="time-state-action">
                    <strong>Fix:</strong> {state['fix_action']} |
                    <strong>Timeline:</strong> {state['timeline']}
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        button_key = f"drill_{state['state_key']}"
        if st.button("Drill Down", key=button_key, use_container_width=True):
            if callback:
                callback(state['state_key'])


def render_time_state_drill_down(
    state_key: str,
    state_name: str,
    transactions_df,
    on_back_callback=None
) -> None:
    """
    Render drill-down view for a specific time state.

    Args:
        state_key: Time state key (e.g., 'fulfilled_not_invoiced')
        state_name: Display name of the time state
        transactions_df: DataFrame of transactions in this time state
        on_back_callback: Callback to return to time-state overview
    """

    st.subheader(f"Time State: {state_name}")

    # Back button
    if on_back_callback:
        if st.button("⬅️ Back to Time-State Overview"):
            on_back_callback()
            st.rerun()

    # Summary metrics
    total_trans = len(transactions_df)
    total_amount = transactions_df['outstanding_amount'].sum()
    avg_days = transactions_df['days_outstanding'].mean()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Transactions", f"{total_trans}")
    with col2:
        st.metric("Total Amount", f"${total_amount:,.2f}")
    with col3:
        st.metric("Avg Days Outstanding", f"{avg_days:.1f} days")

    st.divider()

    # Sort by amount (descending) to show biggest first
    transactions_df = transactions_df.sort_values('outstanding_amount', ascending=False)

    # Display transactions table
    st.subheader("Transactions")

    for idx, row in transactions_df.iterrows():
        # Create color coding based on status
        status_color = {
            'CREDIT_HOLD': '🔴',
            'PENDING': '🟡',
            'APPROVED': '🟢',
            'PAID': '🔵',
            'OVERDUE': '🔴',
            'DISPUTED': '🔴',
            'CREATED': '🟡',
            'PENDING_SEND': '🟡',
            'SENT': '⚪',
            'CLEARED': '🔵'
        }.get(row['status'], '⚪')

        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 2, 2])

            with col1:
                st.markdown(f"**{row['transaction_number']}**")
                st.caption(f"Date: {row['transaction_date']}")

            with col2:
                st.markdown(f"**{row['customer_vendor']}**")
                st.caption("Customer/Vendor")

            with col3:
                st.metric("Amount", f"${row['outstanding_amount']:,.2f}", label_visibility="collapsed")
                st.caption("Amount")

            with col4:
                st.markdown(f"{status_color} **{row['status']}**")
                st.caption(f"{row['days_outstanding']} days old")

            st.divider()
