import streamlit as st
import pandas as pd

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='Renegades',
    page_icon=':rabbit:', # This is an emoji shortcode. Could be a URL too.
    layout='wide',
)

@st.cache_data
def load_data():
    try:
        df = pd.DataFrame.from_dict(st.secrets, orient='index')
        df = df.reset_index()
        df = df.rename(columns={'index': 'IGN'})
        return df
    except Exception as e:
        st.error(f"An error occurred while reading in secrets.toml: {e}")
        return None

df = load_data()
st.session_state.names = sorted(df['IGN'].dropna().unique().tolist())

if df is not None:
    # Clean the data - remove commas from numeric columns
    raw_value_cols = [col for col in df.columns if col != 'IGN']
    for col in raw_value_cols:
        df[col] = df[col].astype(str).str.replace(',', '')
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Rename date columns to add '_total'
    date_columns = [col for col in df.columns if col != 'IGN']
    st.session_state.dates = sorted(list(date_columns))
    st.session_state.latest_date = st.session_state.dates[-1]
    st.session_state.prev_date = st.session_state.dates[-2]
    st.session_state.names = sorted(df['IGN'].dropna().unique().tolist())
    new_date_columns = [f"{col}_total" for col in date_columns]
    rename_map = dict(zip(date_columns, new_date_columns))
    df = df.rename(columns=rename_map)
    
    # Add delta columns
    for i in range(1, len(new_date_columns)):
        prev_col = new_date_columns[i-1]
        curr_col = new_date_columns[i]
        delta_col = curr_col.replace('_total', '_delta')
        df[delta_col] = df[curr_col] - df[prev_col]
        
    df[f"{date_columns[0]}_delta"] = 0
    total_cols = [col for col in df.columns if '_total' in col and pd.api.types.is_numeric_dtype(df[col])]
    df['Personal Best'] = df[total_cols].max(axis=1)
    st.session_state.theoritical_high = int(df['Personal Best'].sum())
    
    date_of_personal_best = []
    for index, row in df.iterrows():
        personal_best = row['Personal Best']
        found_date = None
        # Iterate through the total columns to find the date corresponding to the personal best
        for col in total_cols:
            if pd.notna(row[col]) and row[col] == personal_best:
                found_date = col.replace('_total', '')
                break
        date_of_personal_best.append(found_date)
    
    df['Date of Personal Best'] = date_of_personal_best
    
    st.session_state.weekly_totals = {}
    for col in new_date_columns:
        date = col.replace('_total', '')
        st.session_state.weekly_totals[date] = df[col].sum()

    # Update column lists for filtering and charting
    all_columns = df.columns.tolist()
    date_total_columns = [col for col in all_columns if col.endswith('_total')]
    delta_columns = [col for col in all_columns if col.endswith('_delta')]

    # Sidebar filters
    st.sidebar.header('Filters')
    # Add filter state to session_state for reset functionality
    if 'selected_names' not in st.session_state:
        st.session_state.selected_names = st.session_state.names
    if 'selected_dates' not in st.session_state:
        st.session_state.selected_dates = st.session_state.dates
    if 'view_mode' not in st.session_state:
        st.session_state.view_mode = 'Total'
    
   
    # Create a button to reset the multiselect
    if st.sidebar.button("Reset Selections"):
        del st.session_state.selected_names
        del st.session_state.selected_dates
        del st.session_state.view_mode
        st.rerun() # Rerun the app to reflect the change
        
    st.session_state.selected_names = st.sidebar.multiselect('Select Name(s)', st.session_state.names, default=st.session_state.names, key='selected_name')
    # Ensure selected_names is always a list for filtering
    if not isinstance(st.session_state.selected_names, list):
        st.session_state.selected_names = [st.session_state.selected_names] if st.session_state.selected_names else []

    st.session_state.selected_dates = st.sidebar.multiselect('Select Dates(s)', st.session_state.dates, default=st.session_state.dates, key='selected_date')
    # Ensure selected_dates is always a list for filtering
    if not isinstance(st.session_state.selected_dates, list):
        st.session_state.selected_dates = [st.session_state.selected_dates] if st.session_state.selected_dates else []

    view_mode = st.sidebar.radio('Show', options=['Total', 'Delta'], index=0, key='view_mode')

    filtered_df = df[df['IGN'].isin(st.session_state.selected_names)]
    
    date_total_columns = [f"{date}_total" for date in sorted(st.session_state.selected_dates)]
    date_delta_columns = [f"{date}_delta" for date in sorted(st.session_state.selected_dates)]
    
    # Include 'IGN' and the selected date_total_columns
    view_columns =  date_total_columns if view_mode == 'Total' else date_delta_columns
    
    # columns_to_select  = ['IGN'] + ['Personal Best'] + view_columns
    
    display_df = filtered_df[['IGN'] + ['Personal Best'] + ['Date of Personal Best'] + view_columns]
    display_df = display_df.rename(columns=lambda col: col.replace('_total', '').replace('_delta', ''))
    
    if st.session_state.selected_names == st.session_state.names and st.session_state.selected_dates == st.session_state.dates and st.session_state.view_mode == 'Total':
        col1, col2, col3 = st.columns(3)
        with col1:
            delta = st.session_state.weekly_totals[st.session_state.latest_date] - st.session_state.weekly_totals[st.session_state.prev_date]
            st.metric(label="This week's total score", value=st.session_state.weekly_totals[st.session_state.latest_date], delta=delta)
        
        with col2:
            pax = (df[f'{st.session_state.latest_date}_total'] != 0).sum() 
            # participation_rate = pax / len((df[st.session_state.latest_date != 0]))
            st.metric(label="Pax Attempted", value = pax)
        
        with col3:
            st.metric(label="Theoritical highest total score", value = st.session_state.theoritical_high)     
        
    if len(st.session_state.selected_names) == 1:
        player_data = display_df[display_df['IGN'] == st.session_state.selected_names]
        personal_best = player_data['Personal Best'].iloc[0]
        date_pb = player_data['Date of Personal Best'].iloc[0]       
        st.metric('Personal Best:', f"{int(personal_best):,}", delta=f"on {date_pb}")
        
    
    chart_data = display_df.set_index('IGN')[st.session_state.selected_dates].T
    if view_mode == 'Total':
        st.title('Sewer scores over the weeks')
    else:
        st.title('GAINS over the weeks')
        
    st.line_chart(chart_data)
    st.title('Tabular Data')
    
    st.dataframe(display_df)