import streamlit as st
import pandas as pd
import numpy as np
import json # For serializing/deserializing Ticket Details

# Default values (remains the same)
DEFAULT_REFUND_RATE = 0.03
DEFAULT_PLATFORM_FEE_RATE = 0.04
DEFAULT_MERCH_UNIT_COST = 20.00
DEFAULT_PRICE_INCREASE_CAP = 5.00

class SponsorshipManager:
    def __init__(self, total_annual_sponsorship):
        self.total_annual_sponsorship = total_annual_sponsorship
        self.remaining_annual_sponsorship = total_annual_sponsorship
        self.planned_events = [] # List of event dictionaries

    def get_remaining_budget(self):
        return self.remaining_annual_sponsorship

    def _calculate_multi_tier_prices(self, tier_definitions, fixed_costs_event,
                                     sponsor_allocation_event, event_total_catering_cost,
                                     sum_of_sales_for_active_tiers,
                                     event_refund_rate, event_platform_fee_rate):
        priced_tiers = []
        catering_per_head = event_total_catering_cost / sum_of_sales_for_active_tiers if sum_of_sales_for_active_tiers > 0 else 0
        
        gap_to_cover_by_tickets = fixed_costs_event - sponsor_allocation_event

        for tier_def_original in tier_definitions:
            tier_def = tier_def_original.copy()
            tier_def['v_calc'] = catering_per_head + tier_def['merch_cost']
            tier_priced_data = {**tier_def}

            if tier_def['sold'] <= 0: 
                tier_priced_data.update({'P_net': float('nan'), 'P_gross': float('nan'), 'gap_share': 0})
                if 'v_calc' in tier_priced_data: del tier_priced_data['v_calc']
                priced_tiers.append(tier_priced_data)
                continue
            
            tier_gap_share = 0
            if sum_of_sales_for_active_tiers > 0 : 
                tier_gap_share = gap_to_cover_by_tickets * (tier_def['sold'] / sum_of_sales_for_active_tiers)
            
            tier_priced_data['gap_share'] = tier_gap_share
            
            denominator_p_net = (1 - event_refund_rate) * tier_def['sold']
            P_net = tier_def['v_calc'] + (tier_gap_share / denominator_p_net) if denominator_p_net != 0 else float('inf')
            
            denominator_p_gross = (1 - event_platform_fee_rate)
            P_gross = P_net / denominator_p_gross if denominator_p_gross != 0 else float('inf')
            
            tier_priced_data.update({'P_net': P_net, 'P_gross': P_gross})
            if 'v_calc' in tier_priced_data: del tier_priced_data['v_calc'] 
            priced_tiers.append(tier_priced_data)
            
        return priced_tiers

    def plan_event_scenarios(self, event_name: str,
                             event_fixed_costs: float, event_total_catering_cost: float,
                             total_expected_attendees_overall: int,
                             merch_option: str, 
                             merch_unit_cost: float,
                             expected_merch_tickets_sold_input: int,
                             last_year_regular_price: float,
                             last_year_merch_price: float, 
                             sponsor_allocations_to_test: list,
                             event_refund_rate: float = DEFAULT_REFUND_RATE,
                             event_platform_fee_rate: float = DEFAULT_PLATFORM_FEE_RATE,
                             price_increase_cap: float = DEFAULT_PRICE_INCREASE_CAP):
        scenarios_summary = []
       

        for s_alloc_raw in sponsor_allocations_to_test:
            try:
                s_alloc = float(s_alloc_raw)
            except ValueError:
                st.warning(f"Invalid sponsor allocation value skipped: {s_alloc_raw}")
                continue
            if s_alloc < 0: continue

            current_scenario_data = {
                'event_name': event_name, 'sponsor_allocation_tested': s_alloc,
                'fixed_costs_event': event_fixed_costs, 
                'total_expected_attendees_overall': total_expected_attendees_overall,
                'merch_option': merch_option, 'event_total_catering_cost': event_total_catering_cost,
                'merch_unit_cost_input': merch_unit_cost, 
                'expected_merch_tickets_sold_input': expected_merch_tickets_sold_input,
                'last_year_regular_price': last_year_regular_price, 'last_year_merch_price': last_year_merch_price,
                'event_refund_rate': event_refund_rate, 'event_platform_fee_rate': event_platform_fee_rate,
                'price_increase_cap': price_increase_cap,
                'P_gross_regular': None, 'is_too_expensive_regular': None, 'actual_regular_tickets_sold': 0,
                'P_gross_merch': None, 'is_too_expensive_merch': None, 'actual_merch_tickets_sold': 0,
                'notes': "", 'potential_remaining_annual_budget': self.remaining_annual_sponsorship - s_alloc
            }

            if s_alloc > self.remaining_annual_sponsorship:
                current_scenario_data['notes'] = "Exceeds remaining annual budget."
                scenarios_summary.append(current_scenario_data)
                continue

            tier_definitions_for_calc = []
            reg_sold_calc = 0 
            merch_sold_calc = 0 
            _total_overall = total_expected_attendees_overall
            _expected_merch = expected_merch_tickets_sold_input

            if merch_option == "No Merch":
                reg_sold_calc = _total_overall
            elif merch_option == "Bundled Merch (for all tickets)":
                reg_sold_calc = _total_overall 
            elif merch_option == "Optional Merch Tickets (separate prices)":
                if _expected_merch > _total_overall: 
                    current_scenario_data['notes'] = "Input Error: Merch tickets > total attendees."
                    scenarios_summary.append(current_scenario_data)
                    continue 
                merch_sold_calc = _expected_merch
                reg_sold_calc = _total_overall - merch_sold_calc
                if reg_sold_calc < 0: 
                    current_scenario_data['notes'] = "Input Error: Negative regular tickets calculation."
                    scenarios_summary.append(current_scenario_data)
                    continue
            
            current_scenario_data['actual_regular_tickets_sold'] = reg_sold_calc
            current_scenario_data['actual_merch_tickets_sold'] = merch_sold_calc

            if merch_option == "No Merch":
                if reg_sold_calc > 0:
                    tier_definitions_for_calc.append({'name': "Regular", 'sold': reg_sold_calc, 'merch_cost': 0, 'last_year_price': last_year_regular_price})
            elif merch_option == "Bundled Merch (for all tickets)":
                if reg_sold_calc > 0: 
                    tier_definitions_for_calc.append({'name': "Bundled", 'sold': reg_sold_calc, 'merch_cost': merch_unit_cost, 'last_year_price': last_year_regular_price})
            elif merch_option == "Optional Merch Tickets (separate prices)":
                if reg_sold_calc > 0:
                    tier_definitions_for_calc.append({'name': "Regular", 'sold': reg_sold_calc, 'merch_cost': 0, 'last_year_price': last_year_regular_price})
                if merch_sold_calc > 0:
                    tier_definitions_for_calc.append({'name': "Merch-Inclusive", 'sold': merch_sold_calc, 'merch_cost': merch_unit_cost, 'last_year_price': last_year_merch_price})
            
            sum_of_sales_for_active_tiers = sum(tier['sold'] for tier in tier_definitions_for_calc)

            if not ("Input Error" in current_scenario_data['notes']): # Clear only if not input error
                 current_scenario_data['notes'] = ""

            if total_expected_attendees_overall == 0:
                current_scenario_data['notes'] = "Overall expected attendees is 0."
            elif sum_of_sales_for_active_tiers == 0 and total_expected_attendees_overall > 0 : 
                current_scenario_data['notes'] = "No tickets to price (0 sales for configured types)." 
            
            if current_scenario_data['notes']: 
                scenarios_summary.append(current_scenario_data)
                continue
            
            priced_tiers_results = self._calculate_multi_tier_prices(
                tier_definitions_for_calc, event_fixed_costs, s_alloc,
                event_total_catering_cost, sum_of_sales_for_active_tiers, 
                event_refund_rate, event_platform_fee_rate
            )

            for tier_result in priced_tiers_results:
                P_gross = tier_result['P_gross']
                is_too_expensive = None
                ly_price_for_tier = tier_result.get('last_year_price')
                if pd.notnull(P_gross) and np.isfinite(P_gross) and pd.notnull(ly_price_for_tier):
                    is_too_expensive = P_gross > (ly_price_for_tier + price_increase_cap)

                if tier_result['name'] == "Regular":
                    current_scenario_data['P_gross_regular'] = P_gross
                    current_scenario_data['is_too_expensive_regular'] = is_too_expensive
                elif tier_result['name'] == "Merch-Inclusive":
                    current_scenario_data['P_gross_merch'] = P_gross
                    current_scenario_data['is_too_expensive_merch'] = is_too_expensive
                elif tier_result['name'] == "Bundled": 
                    current_scenario_data['P_gross_regular'] = P_gross 
                    current_scenario_data['is_too_expensive_regular'] = is_too_expensive
            
            scenarios_summary.append(current_scenario_data)
        return scenarios_summary

    def commit_event_plan(self, scenario_to_commit: dict):
        event_name = scenario_to_commit['event_name']
        chosen_sponsor_allocation = scenario_to_commit['sponsor_allocation_tested']
        
        if chosen_sponsor_allocation < 0:
            st.error(f"Cannot commit negative sponsorship for {event_name}.")
            return False
        if chosen_sponsor_allocation > self.remaining_annual_sponsorship:
            st.error(f"Sponsorship ${chosen_sponsor_allocation:,.2f} for {event_name} exceeds remaining budget.")
            return False

        merch_option = scenario_to_commit['merch_option']
        ticket_details_for_commit = []
        has_any_valid_price_for_expected_sales = False
        actual_reg_sold = scenario_to_commit.get('actual_regular_tickets_sold', 0)
        actual_merch_sold = scenario_to_commit.get('actual_merch_tickets_sold', 0)
        any_sales_expected_for_scenario = (actual_reg_sold + actual_merch_sold) > 0

        if merch_option == "No Merch" or merch_option == "Bundled Merch (for all tickets)":
            if actual_reg_sold > 0: 
                price = scenario_to_commit.get('P_gross_regular')
                if pd.notnull(price) and np.isfinite(price):
                    ticket_details_for_commit.append({
                        'type': "Bundled" if merch_option == "Bundled Merch (for all tickets)" else "Regular", 
                        'price': price, 
                        'sold': actual_reg_sold
                    })
                    has_any_valid_price_for_expected_sales = True
                else:
                    st.error(f"Invalid price for {merch_option} ticket for {event_name} when sales ({actual_reg_sold}) were expected.")
                    return False 
        elif merch_option == "Optional Merch Tickets (separate prices)":
            if actual_reg_sold > 0:
                price_reg = scenario_to_commit.get('P_gross_regular')
                if pd.notnull(price_reg) and np.isfinite(price_reg):
                    ticket_details_for_commit.append({'type': "Regular", 'price': price_reg, 'sold': actual_reg_sold})
                    has_any_valid_price_for_expected_sales = True
                else:
                    st.error(f"Invalid Regular ticket price for Optional Merch (sales: {actual_reg_sold}) for {event_name}.")
                    return False

            if actual_merch_sold > 0:
                price_merch = scenario_to_commit.get('P_gross_merch')
                if pd.notnull(price_merch) and np.isfinite(price_merch):
                    ticket_details_for_commit.append({'type': "Merch-Inclusive", 'price': price_merch, 'sold': actual_merch_sold})
                    has_any_valid_price_for_expected_sales = True 
                else:
                    st.error(f"Invalid Merch-Inclusive ticket price for Optional Merch (sales: {actual_merch_sold}) for {event_name}.")
                    return False
        
        if any_sales_expected_for_scenario and not has_any_valid_price_for_expected_sales:
             if scenario_to_commit.get('notes') and "0 sales for configured types" in scenario_to_commit.get('notes'):
                 pass 
             else:
                 st.error(f"No valid ticket prices to commit for expected sales for '{event_name}'. Note: {scenario_to_commit.get('notes', '')}")
                 return False
        elif not any_sales_expected_for_scenario and not ticket_details_for_commit: # 0 overall attendees
            pass

        self.remaining_annual_sponsorship -= chosen_sponsor_allocation
        
        
        # Store more raw inputs for better reconstruction from CSV
        st.write("DEBUG: `ticket_details_for_commit` before json.dumps:", ticket_details_for_commit) 
        json_details_string = json.dumps(ticket_details_for_commit)
        st.write("DEBUG: `json_details_string` for 'Ticket Details':", json_details_string) 

        event_data = {
            'Name': event_name,
            'Sponsorship Allocated ($)': chosen_sponsor_allocation,
            'Merch Option': merch_option,
            'Ticket Details': json_details_string, 
            'Total Expected Attendees (Overall)': scenario_to_commit['total_expected_attendees_overall'],
            'Fixed Costs ($)': scenario_to_commit['fixed_costs_event'],
            'Catering Cost ($)': scenario_to_commit['event_total_catering_cost'],
            'Merch Unit Cost ($)': scenario_to_commit['merch_unit_cost_input'],
            'Expected Merch Sales (Input)': scenario_to_commit['expected_merch_tickets_sold_input'],
            'LY Regular Price ($)': scenario_to_commit['last_year_regular_price'],
            'LY Merch Price ($)': scenario_to_commit['last_year_merch_price'],
            'Annual Budget After Commit ($)': self.remaining_annual_sponsorship
        }
        self.planned_events.append(event_data)
        st.write(f"DEBUG: Event '{event_name}' added. Current 'Ticket Details' in self.planned_events:", self.planned_events[-1]['Ticket Details']) 
        st.success(f"Event '{event_name}' committed...")
        return True

    def get_planned_events_df_for_export(self):
        """Returns a DataFrame suitable for CSV export, with Ticket Details as JSON string."""
        if not self.planned_events:
            st.write("DEBUG: No planned events to export.") # DEBUG LINE
            return pd.DataFrame()

        st.write("DEBUG: `self.planned_events` in `get_planned_events_df_for_export` (showing first event's Ticket Details if exists):") 
        if self.planned_events:
            st.text(self.planned_events[0].get('Ticket Details', "N/A - First event has no Ticket Details key or no events")) 

        return pd.DataFrame(self.planned_events)

    def load_events_from_df(self, df_to_load):
        """Loads events from a DataFrame, replacing current planned events."""
        self.planned_events = []
        self.remaining_annual_sponsorship = self.total_annual_sponsorship # Reset budget
        
        required_cols = ['Name', 'Sponsorship Allocated ($)', 'Merch Option', 'Ticket Details', 
                         'Total Expected Attendees (Overall)', 'Fixed Costs ($)']
        if not all(col in df_to_load.columns for col in required_cols):
            st.error(f"Imported CSV is missing one or more required columns: {required_cols}")
            return False

        try:
            for index, row in df_to_load.iterrows():
                event_data = row.to_dict()
                ticket_details_str = event_data.get('Ticket Details') 

                if pd.notna(ticket_details_str) and isinstance(ticket_details_str, str) and ticket_details_str.strip(): 
                    try:
                        event_data['Ticket Details'] = json.loads(ticket_details_str)
                    except json.JSONDecodeError as je:
                        st.warning(f"Warning: Could not parse Ticket Details for event '{event_data.get('Name', 'Unknown Event')}' (row {index + 2}). Found: '{ticket_details_str}'. Error: {je}. Defaulting to empty list.")
                        event_data['Ticket Details'] = []
                else: 
                    event_data['Ticket Details'] = []
                
                
                event_data['Sponsorship Allocated ($)'] = float(event_data.get('Sponsorship Allocated ($)', 0))
                event_data['Total Expected Attendees (Overall)'] = int(event_data.get('Total Expected Attendees (Overall)', 0)) 
                event_data['Fixed Costs ($)'] = float(event_data.get('Fixed Costs ($)', 0)) #
                
                # Ensure ticket details price/sold are also robustly converted if they exist
                if isinstance(event_data['Ticket Details'], list):
                    for detail in event_data['Ticket Details']:
                        detail['price'] = float(detail.get('price', 0))
                        detail['sold'] = int(detail.get('sold', 0))

                self.planned_events.append(event_data)
                self.remaining_annual_sponsorship -= event_data['Sponsorship Allocated ($)']
            
            if self.planned_events and 'Annual Budget After Commit ($)' in self.planned_events[-1]:
                self.planned_events[-1]['Annual Budget After Commit ($)'] = self.remaining_annual_sponsorship

            st.success(f"{len(self.planned_events)} events loaded successfully. Remaining budget updated.")
            return True
        except Exception as e:
            st.error(f"Error loading events from CSV: {e}")
            # Rollback changes
            self.planned_events = [] 
            self.remaining_annual_sponsorship = self.total_annual_sponsorship
            return False


    def get_planned_events_summary_df(self):
        if not self.planned_events:
            return pd.DataFrame()
        
        display_list = []
        for event_dict in self.planned_events:
            event = event_dict.copy()
            base_info = {
                'Name': event['Name'],
                'Sponsorship Allocated ($)': event['Sponsorship Allocated ($)'],
                'Merch Option': event['Merch Option'],
                'Total Expected Attendees (Overall)': event['Total Expected Attendees (Overall)'],
                'Fixed Costs ($)': event['Fixed Costs ($)'],
                'Annual Budget After Commit ($)': event['Annual Budget After Commit ($)'] 
            }
            
            # Deserialize Ticket Details if it's a string (might happen if data is re-read without full parsing)
            ticket_details_parsed = event['Ticket Details']
            if isinstance(ticket_details_parsed, str):
                try:
                    ticket_details_parsed = json.loads(ticket_details_parsed)
                except json.JSONDecodeError:
                    ticket_details_parsed = [] # Default to empty if parsing fails

            if not ticket_details_parsed: 
                 row = base_info.copy()
                 row['Ticket Details'] = "N/A" 
                 row['Price ($)'] = np.nan
                 row['Sold (Est.)'] = 0
                 display_list.append(row)
            else: 
                for ticket_detail in ticket_details_parsed:
                    row = base_info.copy()
                    row['Ticket Details'] = ticket_detail['type']
                    row['Price ($)'] = ticket_detail['price']
                    row['Sold (Est.)'] = ticket_detail.get('sold', 0) 
                    display_list.append(row)
        
        df = pd.DataFrame(display_list)
        cols_order = ['Name', 'Ticket Details', 'Price ($)', 'Sold (Est.)', 'Merch Option', 'Sponsorship Allocated ($)', 
                      'Total Expected Attendees (Overall)', 'Fixed Costs ($)', 'Annual Budget After Commit ($)']
        existing_cols_order = [col for col in cols_order if col in df.columns]
        if not df.empty: 
            return df[existing_cols_order]
        return df

# ──────────── STREAMLIT APP UI ────────────
st.set_page_config(layout="wide", page_title="Event Pricing Tool v2.5 CSV") 
st.title("🎟️ Advanced Event Sponsorship & Ticket Pricing Tool (v2.5 CSV I/O)")

if 'manager' not in st.session_state:
    st.session_state.initial_annual_sponsorship = 19000.00
    st.session_state.manager = SponsorshipManager(st.session_state.initial_annual_sponsorship)
    st.session_state.current_scenarios = []
    st.session_state.event_form_key_counter = 0 
    st.session_state.merch_option_ui = "No Merch"

manager = st.session_state.manager

# --- Sidebar ---
st.sidebar.header("Annual Sponsorship Budget")
new_total_budget = st.sidebar.number_input(
    "Set Initial Annual Sponsorship ($)",
    min_value=0.0, value=st.session_state.initial_annual_sponsorship, step=1000.0,
    key="total_annual_sponsorship_input_csv", help="Changing this will reset manager and planned events."
)
if new_total_budget != st.session_state.initial_annual_sponsorship:
    st.session_state.initial_annual_sponsorship = new_total_budget
    # Re-initialize manager with new total budget, existing events will be wiped unless loaded from CSV
    st.session_state.manager = SponsorshipManager(new_total_budget) 
    st.session_state.current_scenarios = []
    st.session_state.event_form_key_counter += 1 
    manager = st.session_state.manager 
    st.rerun()

st.sidebar.metric("Total Annual Budget", f"${manager.total_annual_sponsorship:,.2f}")
st.sidebar.metric("Remaining Annual Budget", f"${manager.get_remaining_budget():,.2f}")

st.sidebar.header("Data Management")
# File uploader for CSV
uploaded_file = st.sidebar.file_uploader("Import Planned Events (CSV)", type="csv", key="csv_uploader")
if uploaded_file is not None:
    try:
        df_imported = pd.read_csv(uploaded_file)
        if manager.load_events_from_df(df_imported):
            # Force rerun to update displays after successful load (inidinite loop problem maybe here)
            st.session_state.event_form_key_counter += 1 # Reset form
            st.session_state.current_scenarios = [] 
            st.rerun() 
        else:
            st.sidebar.error("Failed to process the imported CSV.")
    except Exception as e:
        st.sidebar.error(f"Error reading or processing CSV: {e}")

# Download button for CSV
if manager.planned_events: #
    export_df = manager.get_planned_events_df_for_export()
    if not export_df.empty and 'Ticket Details' in export_df.columns:
        st.write("DEBUG: `export_df['Ticket Details'].head()` before to_csv:") # DEBUG LINE
        st.text_area("DataFrame 'Ticket Details' (first 5)", export_df['Ticket Details'].head(5).to_string(), height=150) # DEBUG LINE
    else:
        st.write("DEBUG: export_df is empty or 'Ticket Details' column is missing before to_csv.") # DEBUG LINE
    csv_export_data = export_df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="Export Planned Events to CSV",
        data=csv_export_data,
        file_name='planned_events.csv',
        mime='text/csv',
        key="export_csv_button"
    )
else:
    st.sidebar.info("No planned events to export yet.")


st.sidebar.header("Global Event Defaults")

default_refund_ui = st.sidebar.slider("Default Refund Rate (%)", 0, 20, int(DEFAULT_REFUND_RATE*100), key="default_refund_ui_k_csv") / 100.0
default_platform_fee_ui = st.sidebar.slider("Default Platform Fee Rate (%)", 0, 20, int(DEFAULT_PLATFORM_FEE_RATE*100), key="default_platform_fee_ui_k_csv") / 100.0
default_price_cap_ui = st.sidebar.number_input("Default Max Price Increase Cap ($)", min_value=0.0, value=DEFAULT_PRICE_INCREASE_CAP, step=1.0, key="default_price_cap_ui_k_csv")



st.header("📊 Plan New Event Scenarios")
st.session_state.merch_option_ui = st.radio(
    "Merchandise Option:",
    ("No Merch", "Bundled Merch (for all tickets)", "Optional Merch Tickets (separate prices)"),
    key="merch_option_radio_key_csv", 
    index=["No Merch", "Bundled Merch (for all tickets)", "Optional Merch Tickets (separate prices)"].index(st.session_state.get('merch_option_ui', "No Merch"))
)

event_form = st.form(key=f"event_planning_form_{st.session_state.event_form_key_counter}_csv")
with event_form:
    st.subheader("Event Core Details")
    event_name_form = st.text_input("Event Name", "My Awesome Event")
    col1, col2 = st.columns(2)
    with col1:
        event_fixed_costs_form = st.number_input("Event Fixed Costs ($)", min_value=0.0, value=5000.0, step=100.0)
        event_total_catering_cost_form = st.number_input("Event Total Catering Cost ($)", min_value=0.0, value=4000.0, step=50.0)
    with col2:
        total_expected_attendees_overall_form = st.number_input("Total Expected Attendees (Overall)", min_value=0, value=180, step=5, key="form_total_attendees_overall_csv")
        last_year_regular_price_form = st.number_input("Last Year's Regular Ticket Price ($)", min_value=0.0, value=30.0, step=1.0, key="form_ly_reg_price_csv")
    
    merch_unit_cost_submit = 0.0 
    expected_merch_tickets_sold_submit = 0
    last_year_merch_price_submit = 0.0

    if st.session_state.merch_option_ui == "Bundled Merch (for all tickets)":
        st.subheader("Merchandise (Bundled)")
        merch_unit_cost_submit = st.number_input("Merch Cost Per Unit ($)", min_value=0.0, value=DEFAULT_MERCH_UNIT_COST, step=1.0, key="form_bundled_merch_cost_csv")
    elif st.session_state.merch_option_ui == "Optional Merch Tickets (separate prices)":
        st.subheader("Merchandise (Optional Tickets)")
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            merch_unit_cost_submit = st.number_input("Merch Cost Per Unit ($)", min_value=0.0, value=DEFAULT_MERCH_UNIT_COST, step=1.0, key="form_optional_merch_cost_csv")
        with col_m2:
            expected_merch_tickets_sold_submit = st.number_input("Expected Merch Ticket Sales", min_value=0, max_value=total_expected_attendees_overall_form, value=50, step=1, key="form_optional_merch_sales_csv")
        with col_m3:
            default_ly_merch_price = last_year_regular_price_form + merch_unit_cost_submit 
            last_year_merch_price_submit = st.number_input("Last Year's Merch Ticket Price ($)", min_value=0.0, value=default_ly_merch_price, step=1.0, key="form_optional_merch_ly_price_csv", help="If a similar merch ticket existed last year.")
    
    st.subheader("Sponsorship & Pricing Constraints")
    price_increase_cap_event_form = st.number_input("Max Price Increase Over Last Year ($)", min_value=0.0, value=default_price_cap_ui, step=1.0, key="form_event_price_cap_csv")
    sponsor_allocations_str_form = st.text_input(
        "Sponsorship Allocations to Test (comma-separated $)", "0, 100, 250, 500,1000,2000,3000,4000,5000", key="form_sponsor_alloc_str_csv"
    )
    calculate_scenarios_button = st.form_submit_button("Calculate Price Scenarios")

if calculate_scenarios_button:
    valid_inputs = True
    merch_option_for_calc = st.session_state.merch_option_ui 

    if merch_option_for_calc == "Optional Merch Tickets (separate prices)" and expected_merch_tickets_sold_submit > total_expected_attendees_overall_form:
        st.error("Error: Expected Merch Ticket Sales cannot be greater than Total Expected Attendees.")
        valid_inputs = False
        st.session_state.current_scenarios = [] 
        
    if valid_inputs:
        try:
            sponsor_allocations_list = [s.strip() for s in sponsor_allocations_str_form.split(',') if s.strip()]
            if not sponsor_allocations_list : 
                st.error("Please enter at least one sponsorship allocation amount.")
                st.session_state.current_scenarios = []
            elif not all(s.replace('.', '', 1).lstrip('-').replace('.', '', 1).isdigit() for s in sponsor_allocations_list if s):
                 st.error("Please enter valid comma-separated numbers for sponsorship allocations.")
                 st.session_state.current_scenarios = []
            else:
                st.session_state.current_scenarios = manager.plan_event_scenarios(
                    event_name=event_name_form, event_fixed_costs=event_fixed_costs_form,
                    event_total_catering_cost=event_total_catering_cost_form, 
                    total_expected_attendees_overall=total_expected_attendees_overall_form,
                    merch_option=merch_option_for_calc, 
                    merch_unit_cost=merch_unit_cost_submit,
                    expected_merch_tickets_sold_input=expected_merch_tickets_sold_submit, 
                    last_year_regular_price=last_year_regular_price_form, 
                    last_year_merch_price=last_year_merch_price_submit, 
                    sponsor_allocations_to_test=sponsor_allocations_list,
                    event_refund_rate=default_refund_ui, 
                    event_platform_fee_rate=default_platform_fee_ui,
                    price_increase_cap=price_increase_cap_event_form
                )
        except Exception as e:
            st.error(f"An error occurred during scenario calculation: {e}")
            st.exception(e) 
            st.session_state.current_scenarios = []


if 'current_scenarios' in st.session_state and st.session_state.current_scenarios:

    current_event_name_display = st.session_state.current_scenarios[0]['event_name']
    current_merch_option_display = st.session_state.current_scenarios[0]['merch_option']
    st.subheader(f"Price Scenarios for: {current_event_name_display} (Merch: {current_merch_option_display})")
    scenarios_df_display = pd.DataFrame(st.session_state.current_scenarios)
    display_cols = ['sponsor_allocation_tested', 'P_gross_regular', 'is_too_expensive_regular']
    if current_merch_option_display == "Optional Merch Tickets (separate prices)":
        if 'P_gross_merch' in scenarios_df_display.columns:
             display_cols.extend(['P_gross_merch', 'is_too_expensive_merch'])
    display_cols.extend(['potential_remaining_annual_budget', 'notes'])
    display_cols = [col for col in display_cols if col in scenarios_df_display.columns]

    def format_price_display(x): 
        if pd.isnull(x): return "N/A"
        if np.isinf(x): return "Inf"
        return f"${x:,.2f}"
    def format_bool_yes_no_na(x):
        if pd.isnull(x): return "N/A"
        return "Yes" if x else "No"

    st.dataframe(
        scenarios_df_display[display_cols].style.format({
            "sponsor_allocation_tested": "${:,.2f}",
            "P_gross_regular": format_price_display, "P_gross_merch": format_price_display,
            "is_too_expensive_regular": format_bool_yes_no_na, "is_too_expensive_merch": format_bool_yes_no_na,
            "potential_remaining_annual_budget": "${:,.2f}"
        }),
        hide_index=True, use_container_width=True
    )

    st.subheader("Commit an Event Plan from Scenarios")
    committable_scenario_options = [] 
    for i, s_scenario in enumerate(st.session_state.current_scenarios):
        label_parts = [f"Sponsor: ${s_scenario['sponsor_allocation_tested']:,.2f}"]
        valid_for_commit_flag = True
        if s_scenario['notes'] and "Exceeds remaining annual budget" in s_scenario['notes'] :
            label_parts.append("(Exceeds Budget!)")
            valid_for_commit_flag = False 
        elif s_scenario['notes']: 
             label_parts.append(f"({s_scenario['notes']})")
             if any(err_note in s_scenario['notes'] for err_note in ["No tickets to price", "Error in ticket number", "No ticket tiers defined", "Overall expected attendees is 0", "Input Error"]):
                 valid_for_commit_flag = False
        actual_reg_sold_scen = s_scenario.get('actual_regular_tickets_sold', 0)
        actual_merch_sold_scen = s_scenario.get('actual_merch_tickets_sold', 0)
        if s_scenario['merch_option'] == "Bundled Merch (for all tickets)": actual_reg_sold_scen = s_scenario['total_expected_attendees_overall']
        if actual_reg_sold_scen > 0:
            price_reg = s_scenario.get('P_gross_regular')
            if pd.notnull(price_reg) and np.isfinite(price_reg):
                label_parts.append(f"Reg/Bundle: {format_price_display(price_reg)}{' (Too Exp!)' if s_scenario.get('is_too_expensive_regular') else ''}")
            else: 
                label_parts.append("Reg/Bundle: Invalid/No Price"); valid_for_commit_flag = False
        if s_scenario['merch_option'] == "Optional Merch Tickets (separate prices)" and actual_merch_sold_scen > 0 :
            price_merch = s_scenario.get('P_gross_merch')
            if pd.notnull(price_merch) and np.isfinite(price_merch):
                label_parts.append(f"Merch: {format_price_display(price_merch)}{' (Too Exp!)' if s_scenario.get('is_too_expensive_merch') else ''}")
            else: 
                label_parts.append("Merch: Invalid/No Price"); valid_for_commit_flag = False
        if valid_for_commit_flag: committable_scenario_options.append((" | ".join(label_parts), i))

    if committable_scenario_options:
        selected_scenario_display_option = st.selectbox(
            "Select a scenario to commit:", options=committable_scenario_options, format_func=lambda x: x[0],
            key="selectbox_commit_scenario_csv"
        )
        if selected_scenario_display_option:
            selected_scenario_index = selected_scenario_display_option[1]
            scenario_to_commit_data = st.session_state.current_scenarios[selected_scenario_index]
            st.write("You are about to commit:") 
            commit_summary = {
                "Event Name": scenario_to_commit_data['event_name'],
                "Sponsorship to Allocate": f"${scenario_to_commit_data['sponsor_allocation_tested']:,.2f}",
                "Merch Option": scenario_to_commit_data['merch_option'],
            }
            reg_sold_summary = scenario_to_commit_data.get('actual_regular_tickets_sold', 0)
            merch_sold_summary = scenario_to_commit_data.get('actual_merch_tickets_sold', 0)
            if scenario_to_commit_data['merch_option'] == "Bundled Merch (for all tickets)":
                 reg_sold_summary = scenario_to_commit_data['total_expected_attendees_overall']
            if reg_sold_summary > 0:
                 commit_summary["Regular/Bundled Ticket Price"] = format_price_display(scenario_to_commit_data.get('P_gross_regular'))
            if merch_sold_summary > 0 and scenario_to_commit_data['merch_option'] == "Optional Merch Tickets (separate prices)":
                 commit_summary["Merch-Inclusive Ticket Price"] = format_price_display(scenario_to_commit_data.get('P_gross_merch'))
            if scenario_to_commit_data['total_expected_attendees_overall'] == 0 :
                 commit_summary["Pricing Note"] = "0 total attendees expected."
            elif not commit_summary.get("Regular/Bundled Ticket Price") and \
                 not commit_summary.get("Merch-Inclusive Ticket Price") and \
                 (reg_sold_summary > 0 or merch_sold_summary > 0 or (scenario_to_commit_data['merch_option'] == "Bundled Merch (for all tickets)" and reg_sold_summary > 0) ) :
                 commit_summary["Pricing Note"] = "No valid prices for expected sales."
            st.json(commit_summary)

            if st.button("Commit This Plan", key="commit_button_k_final_csv"):
                if manager.commit_event_plan(scenario_to_commit_data):
                    st.session_state.current_scenarios = [] 
                    st.session_state.event_form_key_counter += 1 
                    st.rerun()
    else:
        st.info("No scenarios currently available to commit. Check notes or adjust inputs.")

def format_price_display(price):
    return "${:,.2f}".format(price)


st.header("🗓️ Summary of Planned Events")
planned_events_df_display = manager.get_planned_events_summary_df()
if not planned_events_df_display.empty:
    st.dataframe(
        planned_events_df_display.style.format({
            "Sponsorship Allocated ($)": "${:,.2f}", "Price ($)": format_price_display, 
            "Fixed Costs ($)": "${:,.2f}", "Annual Budget After Commit ($)": "${:,.2f}",
            "Sold (Est.)": "{:,.0f}"
        }),
        hide_index=True, use_container_width=True
    )
else:
    st.info("No events have been planned and committed yet.")