"""Streamlit Dashboard"""
import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os
import traceback
from datetime import datetime

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import trapped cash utilities and components
from utils.trapped_cash import (
    calculate_trapped_cash,
    save_trapped_cash_analysis,
    get_latest_trapped_cash_analysis,
    calculate_surgical_target
)
from app.components.trapped_cash_indicator import (
    render_trapped_cash_indicator,
    render_surgical_target
)
# Import DSO time-state analysis
from utils.dso_analysis import (
    analyze_dso_time_states,
    get_time_state_summary,
    analyze_recovery_confidence,
    analyze_root_causes,
    generate_execution_queue
)
from app.components.dso_time_state import (
    render_time_state_breakdown,
    render_time_state_drill_down,
    render_recovery_confidence,
    render_root_cause_heatmap,
    render_execution_queue
)

st.set_page_config(page_title="Capital Leak Analysis", page_icon="💰", layout="wide")

# Custom CSS for better interactivity
st.markdown("""
<style>
    /* Make containers look more clickable */
    .stButton button {
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }

    /* Breadcrumb styling */
    [data-testid="stMarkdownContainer"] p {
        font-size: 14px;
    }

    /* Better spacing for containers */
    .element-container {
        margin-bottom: 0.5rem;
    }

    /* Status badges */
    .stMarkdown {
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# Import and initialize Supabase client with comprehensive error handling
try:
    from config.database import get_supabase_client
    supabase = get_supabase_client()
    st.title("💰 Capital Leak Analysis Dashboard")
except KeyError as e:
    st.error("❌ Supabase Configuration Error")
    st.error(f"**Missing Secret:** {str(e)}")

    st.warning("""
    ### Troubleshooting Steps:

    1. **Check Streamlit secrets** (.streamlit/secrets.toml) contains:
       ```toml
       [supabase]
       url = "your-supabase-url"
       key = "your-supabase-anon-key"
       ```
    2. **In Streamlit Cloud**: Go to App Settings → Secrets and add the Supabase configuration
    3. **Restart the app** after updating secrets

    ### Where to find your Supabase credentials:
    - Dashboard: https://supabase.com/dashboard
    - Settings → API → Project URL and anon/public key
    """)

    with st.expander("📋 Full Error Details"):
        st.code(traceback.format_exc())

    st.stop()
except ImportError as e:
    st.error("❌ Import Error")
    st.error(f"**Error:** {str(e)}")
    st.error(f"**Python Version:** {sys.version}")

    st.warning("""
    ### Troubleshooting Steps:

    1. **Check requirements.txt** contains: `supabase>=2.3.0`
    2. **Restart the app** after updating requirements.txt
    3. **Check logs** in Streamlit Cloud dashboard for installation errors
    """)

    with st.expander("📋 Full Error Details"):
        st.code(traceback.format_exc())

    st.stop()
except Exception as e:
    st.error("❌ Application Initialization Error")
    st.error(f"**Error:** {str(e)}")

    with st.expander("📋 Full Error Details"):
        st.code(traceback.format_exc())

    st.stop()

# Query companies with error handling
try:
    response = supabase.table('companies').select('company_id', 'company_name').execute()
    companies = pd.DataFrame(response.data)
except Exception as e:
    st.error("❌ Failed to fetch companies from Supabase")
    st.error(f"**Error:** {str(e)}")
    with st.expander("📋 Debug Information"):
        st.code(traceback.format_exc())
        st.info("Check that the Supabase connection is configured correctly and the 'companies' table exists.")
    st.stop()

if len(companies) == 0:
    st.warning("No companies analyzed yet")
    st.stop()

selected = st.selectbox("Select Company", companies['company_id'].tolist(),
                       format_func=lambda x: companies[companies['company_id']==x]['company_name'].values[0])

st.header("Cash Conversion Cycle")

# Initialize session state for drill-down navigation
if 'drill_down_state' not in st.session_state:
    st.session_state.drill_down_state = {
        'level': 1,
        'component': None,
        'functional_area': None,
        'transaction_id': None,
        'time_state': None  # For DSO time-state drill-down
    }

def reset_drill_down():
    """Reset drill-down to Level 1"""
    st.session_state.drill_down_state = {
        'level': 1,
        'component': None,
        'functional_area': None,
        'transaction_id': None,
        'time_state': None
    }

def drill_to_component(component_type):
    """Drill down to Level 2: Component breakdown"""
    st.session_state.drill_down_state = {
        'level': 2,
        'component': component_type,
        'functional_area': None,
        'transaction_id': None,
        'time_state': None
    }

def drill_to_time_state(component_type, time_state):
    """Drill down to Level 2.5: Time-state detail (DSO only)"""
    st.session_state.drill_down_state = {
        'level': 2.5,
        'component': component_type,
        'functional_area': None,
        'transaction_id': None,
        'time_state': time_state
    }

def drill_to_functional_area(component_type, functional_area):
    """Drill down to Level 3: Transactions in functional area"""
    st.session_state.drill_down_state = {
        'level': 3,
        'component': component_type,
        'functional_area': functional_area,
        'transaction_id': None,
        'time_state': None
    }

def drill_to_transaction(component_type, functional_area, transaction_id):
    """Drill down to Level 4: Event logs for transaction"""
    st.session_state.drill_down_state = {
        'level': 4,
        'component': component_type,
        'functional_area': functional_area,
        'transaction_id': transaction_id,
        'time_state': None
    }

def back_one_level():
    """Navigate back one level in drill-down"""
    current_level = st.session_state.drill_down_state['level']
    if current_level == 4:
        st.session_state.drill_down_state['level'] = 3
        st.session_state.drill_down_state['transaction_id'] = None
    elif current_level == 3:
        st.session_state.drill_down_state['level'] = 2
        st.session_state.drill_down_state['functional_area'] = None
    elif current_level == 2.5:
        st.session_state.drill_down_state['level'] = 2
        st.session_state.drill_down_state['time_state'] = None
    elif current_level == 2:
        reset_drill_down()

# Fetch CCC metrics
try:
    response = supabase.table('ccc_metrics')\
        .select('*')\
        .eq('company_id', selected)\
        .order('calculation_date', desc=True)\
        .limit(1)\
        .execute()
    ccc = pd.DataFrame(response.data)
except Exception as e:
    st.error(f"❌ Failed to fetch CCC metrics for company {selected}")
    st.error(f"**Error:** {str(e)}")
    ccc = pd.DataFrame()

if len(ccc) == 0:
    st.warning("No CCC metrics available for this company")
    st.stop()

# Breadcrumb navigation
state = st.session_state.drill_down_state
breadcrumb_parts = ["🏠 Dashboard"]
if state['level'] >= 2 and state['component']:
    breadcrumb_parts.append(f"{state['component']}")
if state['level'] == 2.5 and state['time_state']:
    # Get time state name from session if available
    if 'time_state_groups' in st.session_state and state['time_state'] in st.session_state.time_state_groups:
        state_name = st.session_state.time_state_groups[state['time_state']]['config']['name']
        breadcrumb_parts.append(f"{state_name}")
    else:
        breadcrumb_parts.append("Time State Detail")
if state['level'] >= 3 and state['functional_area']:
    breadcrumb_parts.append(f"{state['functional_area']}")
if state['level'] >= 4 and state['transaction_id']:
    breadcrumb_parts.append(f"Transaction Details")

st.markdown(f"**Navigation:** {' > '.join(breadcrumb_parts)}")

# Back button (only show if not at top level)
if state['level'] > 1:
    col_back, col_home = st.columns([1, 5])
    with col_back:
        if st.button("⬅️ Back"):
            back_one_level()
            st.rerun()
    with col_home:
        if st.button("🏠 Home"):
            reset_drill_down()
            st.rerun()
    st.divider()

# LEVEL 1: Top-level CCC metrics (clickable cards)
if state['level'] == 1:
    st.subheader("Cash Conversion Cycle Overview")

    # Calculate and display trapped cash indicator
    try:
        # Get company revenue
        company_response = supabase.table('companies')\
            .select('revenue_annual')\
            .eq('company_id', selected)\
            .execute()

        if company_response.data and len(company_response.data) > 0:
            revenue = company_response.data[0].get('revenue_annual', 0)

            if revenue and revenue > 0:
                # Calculate trapped cash
                trapped_cash_result = calculate_trapped_cash(
                    revenue_annual=float(revenue),
                    actual_dso=float(ccc['dso_value'].values[0]),
                    actual_dio=float(ccc['dio_value'].values[0]),
                    actual_dpo=float(ccc['dpo_value'].values[0])
                )

                # Save to database
                save_trapped_cash_analysis(
                    supabase,
                    company_id=selected,
                    analysis_result=trapped_cash_result,
                    analysis_date=datetime.now().date()
                )

                # Render the indicator with callback
                def on_begin_analysis(component):
                    drill_to_component(component)
                    st.rerun()

                render_trapped_cash_indicator(
                    total_trapped=trapped_cash_result['total_trapped_cash'],
                    targets=trapped_cash_result['targets'],
                    on_begin_analysis_callback=on_begin_analysis
                )

                st.divider()
    except Exception as e:
        st.warning(f"Unable to calculate trapped cash: {str(e)}")
        # Continue without trapped cash indicator

    # Display metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("CCC", f"{ccc['ccc_value'].values[0]:.1f} days")
        st.caption("Cash Conversion Cycle (Total)")

    with col2:
        st.metric("DSO", f"{ccc['dso_value'].values[0]:.1f} days")
        if st.button("🔍 Drill Down", key="drill_dso", help="Click to see DSO breakdown"):
            drill_to_component('DSO')
            st.rerun()

    with col3:
        st.metric("DIO", f"{ccc['dio_value'].values[0]:.1f} days")
        if st.button("🔍 Drill Down", key="drill_dio", help="Click to see DIO breakdown"):
            drill_to_component('DIO')
            st.rerun()

    with col4:
        st.metric("DPO", f"{ccc['dpo_value'].values[0]:.1f} days")
        if st.button("🔍 Drill Down", key="drill_dpo", help="Click to see DPO breakdown"):
            drill_to_component('DPO')
            st.rerun()

    st.info("💡 Click 'Drill Down' on any component to see detailed breakdown by functional area")

# LEVEL 2: Functional area breakdown for selected component
elif state['level'] == 2:
    component = state['component']

    # FOR DSO: Show diagnostic time-state breakdown
    if component == 'DSO':
        st.subheader("DSO Diagnostic Dashboard")

        # Get trapped cash analysis
        try:
            trapped_analysis = get_latest_trapped_cash_analysis(supabase, selected)
            if trapped_analysis:
                initial_estimate = trapped_analysis.get('dso_trapped_cash', 0)
                st.markdown(f"""
                    <div style="background-color: #f3f4f6; padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                        <h3>DSO RECOVERY ANALYSIS</h3>
                        <p><strong>Total Potential Recovery:</strong> ${initial_estimate:,.0f}</p>
                    </div>
                """, unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"Unable to load trapped cash analysis: {str(e)}")

        # Fetch DSO transactions and event logs
        try:
            trans_response = supabase.table('transactions')\
                .select('*')\
                .eq('company_id', selected)\
                .eq('component_type', 'DSO')\
                .execute()
            transactions_df = pd.DataFrame(trans_response.data)

            events_response = supabase.table('event_logs')\
                .select('*')\
                .eq('company_id', selected)\
                .execute()
            event_logs_df = pd.DataFrame(events_response.data)

            if len(transactions_df) > 0:
                # Analyze time states
                time_state_groups = analyze_dso_time_states(transactions_df, event_logs_df)
                time_state_summary = get_time_state_summary(time_state_groups)

                # Store in session state for drill-down
                st.session_state.time_state_groups = time_state_groups

                # PHASE 1: Render time-state breakdown
                def on_time_state_drill_down(state_key):
                    drill_to_time_state('DSO', state_key)
                    st.rerun()

                render_time_state_breakdown(time_state_summary, on_time_state_drill_down)

                st.divider()

                # PHASE 2: Render recovery confidence
                confidence_groups = analyze_recovery_confidence(time_state_groups)
                render_recovery_confidence(confidence_groups)

                st.divider()

                # PHASE 3: Render root cause heatmap
                root_cause_list = analyze_root_causes(transactions_df, event_logs_df)
                render_root_cause_heatmap(root_cause_list)

                st.divider()

                # PHASE 4: Render execution queue
                execution_queue = generate_execution_queue(root_cause_list)
                render_execution_queue(execution_queue)

            else:
                st.warning("No DSO transactions found for analysis")

        except Exception as e:
            st.error(f"Error analyzing DSO time states: {str(e)}")
            import traceback
            with st.expander("Debug Info"):
                st.code(traceback.format_exc())

    # FOR DIO/DPO: Show traditional functional area breakdown
    else:
        st.subheader(f"{component} Breakdown by Functional Area")

        # Get trapped cash analysis to show initial estimate and surgical target
        try:
            trapped_analysis = get_latest_trapped_cash_analysis(supabase, selected)
            if trapped_analysis:
                # Get the trapped amount for this component
                component_lower = component.lower()
                initial_estimate = trapped_analysis.get(f'{component_lower}_trapped_cash', 0)

                # Calculate surgical target
                surgical_target = calculate_surgical_target(supabase, selected, component)

                # Render surgical target indicator
                render_surgical_target(component, initial_estimate, surgical_target)

                st.divider()
        except Exception as e:
            st.warning(f"Unable to display surgical target: {str(e)}")

    # Fetch component details
    try:
        response = supabase.table('component_details')\
            .select('*')\
            .eq('company_id', selected)\
            .eq('component_type', component)\
            .execute()
        component_data = pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"❌ Failed to fetch {component} breakdown")
        st.error(f"**Error:** {str(e)}")
        component_data = pd.DataFrame()

    if len(component_data) > 0:
        # Show summary
        total_amount = component_data['amount'].sum()
        total_days = component_data['days_contribution'].sum()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Amount", f"${total_amount:,.2f}")
        with col2:
            st.metric("Total Days Impact", f"{total_days:.1f} days")

        st.divider()

        # Sort by days contribution (descending) to show biggest issues first
        component_data = component_data.sort_values('days_contribution', ascending=False)

        # Display each functional area as a clickable card
        st.subheader("Functional Areas (Click to see transactions)")

        for idx, row in component_data.iterrows():
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

                with col1:
                    st.markdown(f"**{row['functional_area']}**")
                    st.caption(f"{row['gl_account_name']} ({row['gl_account']})")

                with col2:
                    st.metric("Amount", f"${row['amount']:,.2f}", label_visibility="collapsed")
                    st.caption("Amount")

                with col3:
                    st.metric("Days", f"{row['days_contribution']:.1f}", label_visibility="collapsed")
                    st.caption("Days Impact")

                with col4:
                    if st.button("View →", key=f"drill_fa_{row['detail_id']}", help=f"See transactions in {row['functional_area']}"):
                        drill_to_functional_area(component, row['functional_area'])
                        st.rerun()

                st.divider()
    else:
        st.warning(f"No breakdown data available for {component}")

# LEVEL 2.5: Time-state drill-down (DSO only)
elif state['level'] == 2.5:
    component = state['component']
    time_state = state['time_state']

    # Get time state groups from session state
    if 'time_state_groups' in st.session_state and time_state in st.session_state.time_state_groups:
        group = st.session_state.time_state_groups[time_state]
        state_name = group['config']['name']

        # Convert transactions list to DataFrame
        transactions_df = pd.DataFrame(group['transactions'])

        # Render drill-down view
        def on_back():
            back_one_level()

        render_time_state_drill_down(time_state, state_name, transactions_df, on_back)

    else:
        st.error("Time state data not found. Please go back and try again.")
        if st.button("⬅️ Back"):
            back_one_level()
            st.rerun()

# LEVEL 3: Transactions within a functional area
elif state['level'] == 3:
    component = state['component']
    functional_area = state['functional_area']
    st.subheader(f"{component} > {functional_area}")
    st.markdown("### Transactions")

    # Get GL accounts for this functional area
    try:
        gl_response = supabase.table('component_details')\
            .select('gl_account')\
            .eq('company_id', selected)\
            .eq('component_type', component)\
            .eq('functional_area', functional_area)\
            .execute()
        gl_accounts = [row['gl_account'] for row in gl_response.data]
    except Exception as e:
        st.error(f"❌ Failed to fetch GL accounts")
        gl_accounts = []

    # Fetch transactions
    try:
        response = supabase.table('transactions')\
            .select('*')\
            .eq('company_id', selected)\
            .eq('component_type', component)\
            .in_('gl_account', gl_accounts)\
            .execute()
        transactions = pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"❌ Failed to fetch transactions")
        st.error(f"**Error:** {str(e)}")
        transactions = pd.DataFrame()

    if len(transactions) > 0:
        # Summary metrics
        total_trans = len(transactions)
        total_amount = transactions['amount'].sum()
        avg_days = transactions['days_outstanding'].mean()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Transactions", f"{total_trans}")
        with col2:
            st.metric("Total Amount", f"${total_amount:,.2f}")
        with col3:
            st.metric("Avg Days Outstanding", f"{avg_days:.1f} days")

        st.divider()

        # Sort by days outstanding (descending) to show oldest first
        transactions = transactions.sort_values('days_outstanding', ascending=False)

        # Display transactions as clickable cards
        st.subheader("Transaction Details (Click to see event history)")

        for idx, row in transactions.iterrows():
            # Create color coding based on status
            status_color = {
                'CREDIT_HOLD': '🔴',
                'PENDING': '🟡',
                'APPROVED': '🟢',
                'PAID': '🔵',
                'OVERDUE': '🔴'
            }.get(row['status'], '⚪')

            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])

                with col1:
                    st.markdown(f"**{row['transaction_number']}**")
                    st.caption(f"Date: {row['transaction_date']}")

                with col2:
                    st.markdown(f"**{row['customer_vendor']}**")
                    st.caption("Customer/Vendor")

                with col3:
                    st.metric("Amount", f"${row['amount']:,.2f}", label_visibility="collapsed")
                    st.caption("Amount")

                with col4:
                    st.markdown(f"{status_color} **{row['status']}**")
                    st.caption(f"{row['days_outstanding']} days old")

                with col5:
                    if st.button("Events →", key=f"drill_trans_{row['transaction_id']}", help=f"See event log for {row['transaction_number']}"):
                        drill_to_transaction(component, functional_area, row['transaction_id'])
                        st.rerun()

                st.divider()
    else:
        st.warning(f"No transactions found for {functional_area}")

# LEVEL 4: Event logs for a specific transaction
elif state['level'] == 4:
    component = state['component']
    functional_area = state['functional_area']
    transaction_id = state['transaction_id']

    # Fetch transaction details
    try:
        trans_response = supabase.table('transactions')\
            .select('*')\
            .eq('transaction_id', transaction_id)\
            .execute()
        trans_data = trans_response.data[0] if trans_response.data else None
    except Exception as e:
        st.error(f"❌ Failed to fetch transaction details")
        trans_data = None

    if trans_data:
        st.subheader(f"Transaction: {trans_data['transaction_number']}")

        # Transaction summary
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Amount", f"${trans_data['amount']:,.2f}")
        with col2:
            st.metric("Status", trans_data['status'])
        with col3:
            st.metric("Days Outstanding", f"{trans_data['days_outstanding']}")
        with col4:
            st.metric("Customer/Vendor", trans_data['customer_vendor'], label_visibility="collapsed")
            st.caption("Customer/Vendor")

        st.divider()

        # Fetch event logs
        try:
            events_response = supabase.table('event_logs')\
                .select('*')\
                .eq('transaction_id', transaction_id)\
                .order('event_timestamp', desc=False)\
                .execute()
            events = pd.DataFrame(events_response.data)
        except Exception as e:
            st.error(f"❌ Failed to fetch event logs")
            st.error(f"**Error:** {str(e)}")
            events = pd.DataFrame()

        if len(events) > 0:
            st.subheader(f"Event Timeline ({len(events)} events)")

            # Display events as timeline
            for idx, event in events.iterrows():
                event_time = pd.to_datetime(event['event_timestamp']).strftime('%Y-%m-%d %H:%M:%S')

                # Event type icons
                event_icon = {
                    'ORDER_CREATED': '📝',
                    'SHIPPED': '📦',
                    'CREDIT_CHECK_TRIGGERED': '⚠️',
                    'APPROVED': '✅',
                    'REJECTED': '❌',
                    'SYSTEM_CONFIG_CHANGE': '⚙️',
                    'PAYMENT_RECEIVED': '💰'
                }.get(event['event_type'], '📌')

                with st.expander(f"{event_icon} **{event['event_type']}** - {event_time}", expanded=(idx < 3)):
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.markdown("**User:**")
                        st.markdown("**Module:**")
                        if event['event_data']:
                            st.markdown("**Data:**")
                    with col2:
                        st.markdown(f"{event['user_id']}")
                        st.markdown(f"{event['module']}")
                        if event['event_data']:
                            st.json(event['event_data'])

                    st.markdown(f"**Description:** {event['event_description']}")

            # Analysis tip
            st.info("💡 **Investigation Tip:** Look for CREDIT_CHECK_TRIGGERED events or SYSTEM_CONFIG_CHANGE events that might explain delays")

        else:
            st.warning(f"No event logs found for transaction {trans_data['transaction_number']}")
    else:
        st.error("Transaction not found")
