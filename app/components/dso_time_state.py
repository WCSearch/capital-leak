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


# ============================================================================
# RECOVERY CONFIDENCE COMPONENTS (PHASE 2)
# ============================================================================

def render_recovery_confidence(confidence_groups: Dict) -> None:
    """
    Render recovery confidence breakdown section.

    Args:
        confidence_groups: Output from analyze_recovery_confidence()
    """

    st.markdown("""
        <style>
        .confidence-section {
            margin: 2rem 0;
        }
        .confidence-header {
            font-size: 1.8rem;
            font-weight: bold;
            margin-bottom: 1.5rem;
            color: #1f2937;
        }
        .confidence-card {
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            border: 2px solid;
        }
        .confidence-card-certain {
            border-color: #16a34a;
            background-color: #f0fdf4;
        }
        .confidence-card-probable {
            border-color: #f59e0b;
            background-color: #fffbeb;
        }
        .confidence-card-contested {
            border-color: #dc2626;
            background-color: #fee;
        }
        .confidence-level {
            font-size: 1.3rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }
        .confidence-amount {
            font-size: 1.8rem;
            font-weight: bold;
            color: #1f2937;
        }
        .confidence-detail {
            font-size: 1rem;
            margin: 0.3rem 0;
            color: #374151;
        }
        .actionable-box {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            padding: 1.5rem;
            border-radius: 8px;
            color: white;
            margin: 2rem 0;
            text-align: center;
        }
        .actionable-amount {
            font-size: 2.5rem;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="confidence-section">', unsafe_allow_html=True)
    st.markdown('<div class="confidence-header">RECOVERY CONFIDENCE ANALYSIS</div>', unsafe_allow_html=True)

    # Calculate actionable recovery (Certain + Probable)
    certain_amount = confidence_groups['CERTAIN']['total_amount']
    probable_amount = confidence_groups['PROBABLE']['total_amount']
    contested_amount = confidence_groups['CONTESTED']['total_amount']
    total_amount = certain_amount + probable_amount + contested_amount
    actionable_amount = certain_amount + probable_amount
    actionable_pct = (actionable_amount / total_amount * 100) if total_amount > 0 else 0

    # Render each confidence level
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
            <div class="confidence-card confidence-card-certain">
                <div class="confidence-level">🟢 CERTAIN</div>
                <div class="confidence-amount">{format_currency(certain_amount)}</div>
                <div class="confidence-detail">{confidence_groups['CERTAIN']['percentage']:.0f}% of total</div>
                <div class="confidence-detail">Recoverable without customer involvement</div>
                <div class="confidence-detail" style="margin-top: 0.8rem; padding-top: 0.8rem; border-top: 1px solid #d1d5db;">
                    <strong>Timeline:</strong> {confidence_groups['CERTAIN']['expected_timeline']}
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Show states in this category
        if confidence_groups['CERTAIN']['states']:
            with st.expander("View breakdown"):
                for state in confidence_groups['CERTAIN']['states']:
                    st.markdown(f"**{state['state_name']}**: {format_currency(state['amount'])}")
                    st.caption(f"Fix: {state['fix_action']}")

    with col2:
        st.markdown(f"""
            <div class="confidence-card confidence-card-probable">
                <div class="confidence-level">🟡 PROBABLE</div>
                <div class="confidence-amount">{format_currency(probable_amount)}</div>
                <div class="confidence-detail">{confidence_groups['PROBABLE']['percentage']:.0f}% of total</div>
                <div class="confidence-detail">Clear fix path, requires coordination</div>
                <div class="confidence-detail" style="margin-top: 0.8rem; padding-top: 0.8rem; border-top: 1px solid #d1d5db;">
                    <strong>Timeline:</strong> {confidence_groups['PROBABLE']['expected_timeline']}
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Show states in this category
        if confidence_groups['PROBABLE']['states']:
            with st.expander("View breakdown"):
                for state in confidence_groups['PROBABLE']['states']:
                    st.markdown(f"**{state['state_name']}**: {format_currency(state['amount'])}")
                    st.caption(f"Fix: {state['fix_action']}")

    with col3:
        st.markdown(f"""
            <div class="confidence-card confidence-card-contested">
                <div class="confidence-level">🔴 CONTESTED</div>
                <div class="confidence-amount">{format_currency(contested_amount)}</div>
                <div class="confidence-detail">{confidence_groups['CONTESTED']['percentage']:.0f}% of total</div>
                <div class="confidence-detail">Requires customer action/negotiation</div>
                <div class="confidence-detail" style="margin-top: 0.8rem; padding-top: 0.8rem; border-top: 1px solid #d1d5db;">
                    <strong>Timeline:</strong> {confidence_groups['CONTESTED']['expected_timeline']}
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Show states in this category
        if confidence_groups['CONTESTED']['states']:
            with st.expander("View breakdown"):
                for state in confidence_groups['CONTESTED']['states']:
                    st.markdown(f"**{state['state_name']}**: {format_currency(state['amount'])}")
                    st.caption(f"Fix: {state['fix_action']}")

    # Actionable recovery summary
    st.markdown(f"""
        <div class="actionable-box">
            <div class="actionable-amount">{format_currency(actionable_amount)}</div>
            <div>ACTIONABLE RECOVERY (Certain + Probable = {actionable_pct:.0f}%)</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================================
# ROOT CAUSE HEATMAP COMPONENTS (PHASE 3)
# ============================================================================

def render_root_cause_heatmap(root_cause_list: List[Dict], on_drill_callback=None) -> None:
    """
    Render root cause heatmap section.

    Args:
        root_cause_list: List of root cause groups
        on_drill_callback: Callback when user clicks to view transactions
    """

    st.markdown("""
        <style>
        .heatmap-section {
            margin: 2rem 0;
        }
        .heatmap-header {
            font-size: 1.8rem;
            font-weight: bold;
            margin-bottom: 1.5rem;
            color: #1f2937;
        }
        .surgical-target-box {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            padding: 1.5rem;
            border-radius: 8px;
            border: 3px solid #dc2626;
            margin: 1rem 0 2rem 0;
            color: white;
        }
        .surgical-title {
            font-size: 1.5rem;
            font-weight: bold;
            margin-bottom: 1rem;
        }
        .surgical-detail {
            font-size: 1.1rem;
            margin: 0.3rem 0;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="heatmap-section">', unsafe_allow_html=True)
    st.markdown('<div class="heatmap-header">DSO ROOT CAUSE HEATMAP</div>', unsafe_allow_html=True)

    if not root_cause_list:
        st.warning("No root cause data available")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # Highlight surgical target (top root cause)
    surgical_target = root_cause_list[0]

    st.markdown(f"""
        <div class="surgical-target-box">
            <div class="surgical-title">🎯 SURGICAL TARGET</div>
            <div class="surgical-detail"><strong>{surgical_target['name']}</strong></div>
            <div class="surgical-detail">{surgical_target['count']} transactions | {format_currency(surgical_target['total_amount'])} impact | {surgical_target['fix_days']}-day fix</div>
            <div class="surgical-detail"><strong>ACTION:</strong> {surgical_target['action']}</div>
            <div class="surgical-detail"><strong>OWNER:</strong> {surgical_target['owner']}</div>
        </div>
    """, unsafe_allow_html=True)

    # Create DataFrame for table display
    table_data = []
    for rc in root_cause_list:
        table_data.append({
            'Root Cause': rc['name'],
            'Count': rc['count'],
            'Avg Days': f"{rc['avg_days']:.1f}",
            '$ Impact': format_currency(rc['total_amount']),
            'Fix Type': rc['fix_type'].replace('_', ' ').title(),
            'Owner': rc['owner'],
            'Timeline': f"{rc['fix_days']}d" if rc['fix_days'] else 'TBD'
        })

    df = pd.DataFrame(table_data)

    # Display table
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================================
# EXECUTION QUEUE COMPONENTS (PHASE 4)
# ============================================================================

def render_execution_queue(execution_queue: List[Dict]) -> None:
    """
    Render execution queue section with efficiency ranking.

    Args:
        execution_queue: List of execution items sorted by efficiency
    """

    st.markdown("""
        <style>
        .queue-section {
            margin: 2rem 0;
        }
        .queue-header {
            font-size: 1.8rem;
            font-weight: bold;
            margin-bottom: 1.5rem;
            color: #1f2937;
        }
        .next-action-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1.5rem;
            border-radius: 8px;
            border: 3px solid #4f46e5;
            margin: 1rem 0 2rem 0;
            color: white;
        }
        .next-action-title {
            font-size: 1.5rem;
            font-weight: bold;
            margin-bottom: 1rem;
        }
        .next-action-detail {
            font-size: 1.1rem;
            margin: 0.3rem 0;
        }
        .efficiency-badge {
            background-color: #fbbf24;
            color: #1f2937;
            padding: 0.3rem 0.6rem;
            border-radius: 4px;
            font-weight: bold;
            display: inline-block;
            margin-top: 0.5rem;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="queue-section">', unsafe_allow_html=True)
    st.markdown('<div class="queue-header">RECOVERY EXECUTION QUEUE</div>', unsafe_allow_html=True)
    st.caption("Sorted by: $ recovered per day per hour of effort")

    if not execution_queue:
        st.warning("No execution queue data available")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # Highlight #1 Next Action
    next_action = execution_queue[0]

    st.markdown(f"""
        <div class="next-action-box">
            <div class="next-action-title">🎯 NEXT ACTION: Fix #{next_action['rank']} - {next_action['root_cause_name']}</div>
            <div class="next-action-detail"><strong>Expected Recovery:</strong> {format_currency(next_action['total_impact'])} in {next_action['fix_days']} days (+ customer payment time)</div>
            <div class="next-action-detail"><strong>Required Effort:</strong> {next_action['effort_hours']} hours</div>
            <div class="next-action-detail"><strong>Owner:</strong> {next_action['owner']}</div>
            <div class="efficiency-badge">Efficiency: {format_currency(next_action['efficiency'])} per day/hour</div>
        </div>
    """, unsafe_allow_html=True)

    # Create DataFrame for queue table
    table_data = []
    for item in execution_queue:
        table_data.append({
            'Rank': f"#{item['rank']}",
            'Root Cause': item['root_cause_name'],
            '$ Impact': format_currency(item['total_impact']),
            'Fix Days': f"{item['fix_days']}d" if item['fix_days'] else 'TBD',
            'Effort (hrs)': item['effort_hours'],
            '$/Day/Hr': format_currency(item['efficiency']),
            'Owner': item['owner']
        })

    df = pd.DataFrame(table_data)

    # Display table
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    st.markdown('</div>', unsafe_allow_html=True)
