import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
from datetime import datetime, timedelta
import hashlib
import calendar

# ------------------ Session State ------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "user_choice" not in st.session_state:
    st.session_state.user_choice = "Dashboard"
if "show_login" not in st.session_state:
    st.session_state.show_login = True

# ------------------ Page Config ------------------
st.set_page_config(
    page_title="Smart Expense Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------ Custom CSS ------------------
st.markdown("""
    <style>
    /* Dark theme background */
    .main {
        background-color: #0e1117;
    }
    .stApp {
        background-color: #0e1117;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #1a1d29;
    }
    
    /* Metrics styling */
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        font-weight: bold;
        color: #ffffff;
    }
    
    div[data-testid="stMetricLabel"] {
        color: #b0b0b0;
    }
    
    div[data-testid="stMetricDelta"] {
        color: #4ade80;
    }
    
    /* Text colors */
    .big-font {
        font-size: 24px !important;
        font-weight: bold;
        color: #667eea;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
    }
    
    p, label, .stMarkdown {
        color: #e0e0e0;
    }
    
    /* Success box */
    .success-box {
        padding: 20px;
        border-radius: 10px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        text-align: center;
        margin: 20px 0;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    /* Button styling */
    .stButton>button {
        border-radius: 10px;
        font-weight: bold;
        transition: all 0.3s;
        background-color: #667eea;
        color: white;
        border: none;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.5);
        background-color: #764ba2;
    }
    
    /* Input fields */
    .stTextInput input, .stNumberInput input, .stSelectbox select, .stDateInput input {
        background-color: #262b3d;
        color: #ffffff;
        border: 1px solid #3d4455;
        border-radius: 8px;
    }
    
    .stTextArea textarea {
        background-color: #262b3d;
        color: #ffffff;
        border: 1px solid #3d4455;
        border-radius: 8px;
    }
    
    /* Dataframe styling */
    .stDataFrame {
        background-color: #1a1d29;
    }
    
    /* Info boxes */
    .stAlert {
        background-color: #1a1d29;
        border: 1px solid #3d4455;
        border-radius: 10px;
    }
    
    /* Progress bar */
    .stProgress > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #262b3d;
        color: #e0e0e0;
        border-radius: 8px;
        padding: 10px 20px;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    /* Form styling */
    .stForm {
        background-color: #1a1d29;
        border: 1px solid #3d4455;
        border-radius: 10px;
        padding: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# ------------------ Database Setup ------------------
conn = sqlite3.connect("database.db", check_same_thread=False)
c = conn.cursor()

# Create users table
c.execute('''CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    created_at TEXT NOT NULL
)''')

# Create expenses table with payment_method
c.execute('''CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    date TEXT NOT NULL,
    category TEXT NOT NULL,
    amount REAL NOT NULL,
    note TEXT,
    payment_method TEXT,
    FOREIGN KEY(username) REFERENCES users(username)
)''')

# Check if payment_method column exists, if not add it
try:
    c.execute("SELECT payment_method FROM expenses LIMIT 1")
except sqlite3.OperationalError:
    # Column doesn't exist, add it
    c.execute("ALTER TABLE expenses ADD COLUMN payment_method TEXT DEFAULT 'Cash'")
    conn.commit()

# Create budgets table
c.execute('''CREATE TABLE IF NOT EXISTS budgets (
    username TEXT PRIMARY KEY,
    monthly_budget REAL NOT NULL,
    FOREIGN KEY(username) REFERENCES users(username)
)''')

conn.commit()

# ------------------ Password Hashing ------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ------------------ User Authentication ------------------
def signup(username, password):
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    if c.fetchone():
        return False
    c.execute("INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)", 
              (username, hash_password(password), datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    return True

def login(username, password):
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hash_password(password)))
    return c.fetchone() is not None

# ------------------ Budget Functions ------------------
def get_budget(username):
    c.execute("SELECT monthly_budget FROM budgets WHERE username=?", (username,))
    result = c.fetchone()
    return result[0] if result else 0

def set_budget(username, amount):
    c.execute("INSERT OR REPLACE INTO budgets (username, monthly_budget) VALUES (?, ?)", (username, amount))
    conn.commit()

# ------------------ Header ------------------
st.markdown(
    """
    <div style='text-align:center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                border-radius: 15px; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);'>
        <h1 style='color: white; margin: 0;'>💰 Smart Expense Tracker</h1>
        <p style='color: #f0f0f0; margin: 10px 0 0 0;'>Track, Analyze, and Optimize Your Spending</p>
    </div>
    """,
    unsafe_allow_html=True
)

# ------------------ Login / Signup ------------------
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.session_state.show_login:
            st.markdown("<div style='background: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);'>", unsafe_allow_html=True)
            st.subheader("🔐 Login")
            with st.form("login_form", clear_on_submit=True):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                login_btn = st.form_submit_button("Login", use_container_width=True)
                
            if login_btn:
                if username and password:
                    if login(username, password):
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.user_choice = "Dashboard"
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                else:
                    st.warning("Please enter both username and password")
            
            st.markdown("---")
            if st.button("Don't have an account? Sign Up", use_container_width=True):
                st.session_state.show_login = False
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        else:
            st.markdown("<div style='background: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);'>", unsafe_allow_html=True)
            st.subheader("📝 Create Account")
            with st.form("signup_form", clear_on_submit=True):
                new_user = st.text_input("Username", placeholder="Choose a username")
                new_pass = st.text_input("Password", type="password", placeholder="Choose a strong password")
                confirm_pass = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
                signup_btn = st.form_submit_button("Create Account", use_container_width=True)
                
            if signup_btn:
                if new_user and new_pass and confirm_pass:
                    if new_pass != confirm_pass:
                        st.error("Passwords do not match")
                    elif len(new_pass) < 6:
                        st.error("Password must be at least 6 characters long")
                    elif signup(new_user, new_pass):
                        st.success("✅ Account created successfully! Please login")
                        st.session_state.show_login = True
                        st.rerun()
                    else:
                        st.error("Username already exists")
                else:
                    st.warning("Please fill all fields")
            
            st.markdown("---")
            if st.button("Already have an account? Login", use_container_width=True):
                st.session_state.show_login = True
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

# ------------------ Logged-in App ------------------
else:
    # Sidebar
    with st.sidebar:
        st.markdown(f"<div class='success-box'><h3>👋 {st.session_state.username}</h3></div>", unsafe_allow_html=True)
        
        if st.button("🚪 Logout", use_container_width=True, type="primary"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.user_choice = "Dashboard"
            st.session_state.show_login = True
            st.rerun()
        
        st.markdown("---")
        
        nav_items = ["Dashboard", "Add Expense", "View Expenses", "Analysis", "Budget Manager", "Reports"]
        icons = ["📊", "➕", "📋", "📈", "💵", "📑"]
        
        for icon, item in zip(icons, nav_items):
            if st.button(f"{icon} {item}", use_container_width=True, 
                        key=item, type="secondary" if st.session_state.user_choice != item else "primary"):
                st.session_state.user_choice = item
                st.rerun()

    user_choice = st.session_state.user_choice

    # ------------------ Dashboard ------------------
    if user_choice == "Dashboard":
        st.header("📊 Dashboard Overview")
        
        df = pd.read_sql(f"SELECT * FROM expenses WHERE username='{st.session_state.username}'", conn)
        
        if df.empty:
            st.info("🎯 No expenses yet. Start tracking by adding your first expense!")
        else:
            df["date"] = pd.to_datetime(df["date"])
            
            # Current month calculations
            current_month = datetime.today().month
            current_year = datetime.today().year
            total_spent = df["amount"].sum()
            monthly_spent = df[(df["date"].dt.month == current_month) & 
                              (df["date"].dt.year == current_year)]["amount"].sum()
            
            # Get budget
            budget = get_budget(st.session_state.username)
            budget_remaining = budget - monthly_spent if budget > 0 else 0
            budget_percentage = (monthly_spent / budget * 100) if budget > 0 else 0
            
            # Last 7 days
            week_ago = datetime.today() - timedelta(days=7)
            weekly_spent = df[df["date"] >= week_ago]["amount"].sum()
            
            # Metrics Row
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("💸 Total Spent", f"₹ {total_spent:,.2f}")
            col2.metric("📅 This Month", f"₹ {monthly_spent:,.2f}", 
                       delta=f"{budget_percentage:.1f}% of budget" if budget > 0 else None)
            col3.metric("📆 Last 7 Days", f"₹ {weekly_spent:,.2f}")
            col4.metric("💰 Budget Left", f"₹ {budget_remaining:,.2f}" if budget > 0 else "Not Set")
            
            # Budget Progress Bar
            if budget > 0:
                st.markdown("### 📊 Monthly Budget Progress")
                progress_color = "🟢" if budget_percentage < 70 else "🟡" if budget_percentage < 90 else "🔴"
                st.progress(min(budget_percentage / 100, 1.0))
                st.caption(f"{progress_color} You've used {budget_percentage:.1f}% of your monthly budget")
            
            st.markdown("---")
            
            # Charts Row
            col1, col2 = st.columns(2)
            
            with col1:
                # Category Breakdown
                cat_sum = df.groupby("category")["amount"].sum().reset_index().sort_values("amount", ascending=False)
                fig1 = px.pie(cat_sum, names='category', values='amount', 
                             title="💳 Spending by Category",
                             color_discrete_sequence=px.colors.qualitative.Pastel,
                             hole=0.4)
                fig1.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                # Monthly Trend
                monthly_data = df.groupby(df["date"].dt.to_period("M"))["amount"].sum().reset_index()
                monthly_data["date"] = monthly_data["date"].astype(str)
                fig2 = px.bar(monthly_data, x='date', y='amount', 
                             title="📅 Monthly Spending Trend",
                             color='amount',
                             color_continuous_scale='Blues')
                fig2.update_layout(xaxis_title="Month", yaxis_title="Amount (₹)")
                st.plotly_chart(fig2, use_container_width=True)
            
            # Recent Transactions
            st.markdown("### 📝 Recent Transactions")
            recent_df = df.sort_values("date", ascending=False).head(10).copy()
            recent_df['amount'] = recent_df['amount'].apply(lambda x: f"₹ {x:,.2f}")
            
            # Check which columns exist
            display_cols = ['date', 'category', 'amount', 'note']
            if 'payment_method' in recent_df.columns:
                display_cols.append('payment_method')
            
            st.dataframe(recent_df[display_cols], use_container_width=True, hide_index=True)
            
            # Quick Stats
            st.markdown("### 🎯 Quick Insights")
            col1, col2, col3 = st.columns(3)
            
            avg_expense = df["amount"].mean()
            max_expense = df["amount"].max()
            top_category = df.groupby("category")["amount"].sum().idxmax()
            
            col1.info(f"📊 **Average Expense:** ₹ {avg_expense:,.2f}")
            col2.info(f"🔝 **Highest Expense:** ₹ {max_expense:,.2f}")
            col3.info(f"🎯 **Top Category:** {top_category}")

    # ------------------ Add Expense ------------------
    elif user_choice == "Add Expense":
        st.header("➕ Add a New Expense")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            with st.form("expense_form", clear_on_submit=True):
                date = st.date_input("📅 Date", datetime.today())
                
                col_a, col_b = st.columns(2)
                with col_a:
                    category = st.selectbox("🏷️ Category", 
                                           ["Food", "Transport", "Bills", "Shopping", 
                                            "Entertainment", "Health", "Education", "Other"])
                with col_b:
                    payment_method = st.selectbox("💳 Payment Method", 
                                                 ["Cash", "Credit Card", "Debit Card", "UPI", "Net Banking"])
                
                amount = st.number_input("💰 Amount (₹)", min_value=0.0, step=10.0, format="%.2f")
                note = st.text_area("📝 Note (optional)", placeholder="Add a description...")
                
                submitted = st.form_submit_button("💾 Add Expense", use_container_width=True, type="primary")
                
            if submitted:
                if amount > 0:
                    c.execute("INSERT INTO expenses (username, date, category, amount, note, payment_method) VALUES (?, ?, ?, ?, ?, ?)",
                              (st.session_state.username, date, category, amount, note, payment_method))
                    conn.commit()
                    st.success("✅ Expense added successfully!")
                else:
                    st.error("Please enter a valid amount")
        
        with col2:
            st.markdown("### 💡 Quick Tips")
            st.info("📌 Add expenses daily for accurate tracking")
            st.info("🏷️ Use proper categories for better insights")
            st.info("📝 Add notes to remember details")
            
            # Quick stats
            df = pd.read_sql(f"SELECT * FROM expenses WHERE username='{st.session_state.username}'", conn)
            if not df.empty:
                today_spent = df[pd.to_datetime(df["date"]).dt.date == datetime.today().date()]["amount"].sum()
                st.metric("💸 Today's Spending", f"₹ {today_spent:,.2f}")

    # ------------------ View Expenses ------------------
    elif user_choice == "View Expenses":
        st.header("📋 Expense History")
        
        df = pd.read_sql(f"SELECT * FROM expenses WHERE username='{st.session_state.username}'", conn)
        
        if df.empty:
            st.info("No expenses added yet")
        else:
            df["date"] = pd.to_datetime(df["date"])
            
            # Filters
            st.markdown("### 🔍 Filter Expenses")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                start_date = st.date_input("Start Date", df["date"].min())
            with col2:
                end_date = st.date_input("End Date", df["date"].max())
            with col3:
                category_filter = st.multiselect("Category", 
                                                options=df["category"].unique(), 
                                                default=df["category"].unique())
            
            filtered_df = df[(df["date"] >= pd.to_datetime(start_date)) &
                             (df["date"] <= pd.to_datetime(end_date)) &
                             (df["category"].isin(category_filter))]
            
            # Summary
            col1, col2, col3 = st.columns(3)
            col1.metric("📊 Total Expenses", len(filtered_df))
            col2.metric("💸 Total Amount", f"₹ {filtered_df['amount'].sum():,.2f}")
            col3.metric("📈 Average", f"₹ {filtered_df['amount'].mean():,.2f}")
            
            st.markdown("---")
            
            # Display with formatting
            display_df = filtered_df.sort_values("date", ascending=False).copy()
            display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
            display_df['amount'] = display_df['amount'].apply(lambda x: f"₹ {x:,.2f}")
            
            # Check which columns exist
            display_cols = ['date', 'category', 'amount', 'note']
            if 'payment_method' in display_df.columns:
                display_cols.insert(3, 'payment_method')
            
            st.dataframe(display_df[display_cols], use_container_width=True, hide_index=True)
            
            # Download
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button("💾 Download CSV", data=csv, 
                             file_name=f'expenses_{datetime.now().strftime("%Y%m%d")}.csv', 
                             mime='text/csv', use_container_width=True)

    # ------------------ Analysis ------------------
    elif user_choice == "Analysis":
        st.header("📈 Expense Analysis")
        
        df = pd.read_sql(f"SELECT * FROM expenses WHERE username='{st.session_state.username}'", conn)
        
        if df.empty:
            st.info("No expenses to analyze")
        else:
            df["date"] = pd.to_datetime(df["date"])
            
            # Date Range Filter
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", df["date"].min(), key="analysis_start")
            with col2:
                end_date = st.date_input("End Date", df["date"].max(), key="analysis_end")
            
            filtered_df = df[(df["date"] >= pd.to_datetime(start_date)) &
                             (df["date"] <= pd.to_datetime(end_date))]
            
            # Key Metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("💸 Total Spent", f"₹ {filtered_df['amount'].sum():,.2f}")
            col2.metric("📊 Transactions", len(filtered_df))
            col3.metric("📈 Average", f"₹ {filtered_df['amount'].mean():,.2f}")
            col4.metric("🔝 Highest", f"₹ {filtered_df['amount'].max():,.2f}")
            
            st.markdown("---")
            
            # Charts
            tab1, tab2, tab3 = st.tabs(["📊 Category Analysis", "📅 Time Analysis", "💳 Payment Methods"])
            
            with tab1:
                col1, col2 = st.columns(2)
                with col1:
                    cat_sum = filtered_df.groupby("category")["amount"].sum().reset_index().sort_values("amount", ascending=False)
                    fig1 = px.bar(cat_sum, x='category', y='amount', 
                                 title="Spending by Category",
                                 color='amount',
                                 color_continuous_scale='Viridis')
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    fig2 = px.pie(cat_sum, names='category', values='amount',
                                 title="Category Distribution",
                                 hole=0.4,
                                 color_discrete_sequence=px.colors.qualitative.Set3)
                    st.plotly_chart(fig2, use_container_width=True)
            
            with tab2:
                # Daily trend
                daily_sum = filtered_df.groupby("date")["amount"].sum().reset_index()
                fig3 = px.line(daily_sum, x='date', y='amount', 
                              title="Daily Spending Trend",
                              markers=True)
                fig3.update_traces(line_color='#667eea', line_width=3)
                st.plotly_chart(fig3, use_container_width=True)
                
                # Day of week analysis
                filtered_df['day_of_week'] = filtered_df['date'].dt.day_name()
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                day_sum = filtered_df.groupby('day_of_week')['amount'].sum().reindex(day_order).reset_index()
                
                fig4 = px.bar(day_sum, x='day_of_week', y='amount',
                             title="Spending by Day of Week",
                             color='amount',
                             color_continuous_scale='Blues')
                st.plotly_chart(fig4, use_container_width=True)
            
            with tab3:
                if 'payment_method' in filtered_df.columns and not filtered_df['payment_method'].isna().all():
                    payment_sum = filtered_df.groupby("payment_method")["amount"].sum().reset_index()
                    fig5 = px.pie(payment_sum, names='payment_method', values='amount',
                                 title="Payment Method Distribution",
                                 color_discrete_sequence=px.colors.qualitative.Pastel)
                    st.plotly_chart(fig5, use_container_width=True)
                else:
                    st.info("💡 Payment method data not available for older expenses")

    # ------------------ Budget Manager ------------------
    elif user_choice == "Budget Manager":
        st.header("💵 Budget Manager")
        
        current_budget = get_budget(st.session_state.username)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 🎯 Set Monthly Budget")
            with st.form("budget_form"):
                new_budget = st.number_input("Monthly Budget (₹)", 
                                            min_value=0.0, 
                                            value=float(current_budget),
                                            step=1000.0,
                                            format="%.2f")
                submitted = st.form_submit_button("💾 Save Budget", use_container_width=True)
                
            if submitted:
                set_budget(st.session_state.username, new_budget)
                st.success("✅ Budget updated successfully!")
        
        with col2:
            st.markdown("### 📊 Current Status")
            if current_budget > 0:
                df = pd.read_sql(f"SELECT * FROM expenses WHERE username='{st.session_state.username}'", conn)
                if not df.empty:
                    df["date"] = pd.to_datetime(df["date"])
                    current_month_spent = df[(df["date"].dt.month == datetime.today().month) & 
                                            (df["date"].dt.year == datetime.today().year)]["amount"].sum()
                    
                    remaining = current_budget - current_month_spent
                    percentage = (current_month_spent / current_budget * 100) if current_budget > 0 else 0
                    
                    st.metric("💰 Budget", f"₹ {current_budget:,.2f}")
                    st.metric("💸 Spent", f"₹ {current_month_spent:,.2f}", 
                             delta=f"-₹ {current_month_spent:,.2f}", delta_color="inverse")
                    st.metric("💵 Remaining", f"₹ {remaining:,.2f}")
                    
                    st.progress(min(percentage / 100, 1.0))
                    
                    if percentage > 100:
                        st.error(f"⚠️ You've exceeded your budget by ₹ {abs(remaining):,.2f}")
                    elif percentage > 90:
                        st.warning(f"⚠️ You've used {percentage:.1f}% of your budget")
                    else:
                        st.success(f"✅ You're doing great! {100-percentage:.1f}% budget remaining")
            else:
                st.info("💡 Set a monthly budget to track your spending goals")

    # ------------------ Reports ------------------
    elif user_choice == "Reports":
        st.header("📑 Financial Reports")
        
        df = pd.read_sql(f"SELECT * FROM expenses WHERE username='{st.session_state.username}'", conn)
        
        if df.empty:
            st.info("No data available for reports")
        else:
            df["date"] = pd.to_datetime(df["date"])
            
            report_type = st.selectbox("📊 Select Report Type", 
                                      ["Monthly Summary", "Category Breakdown", "Yearly Overview"])
            
            if report_type == "Monthly Summary":
                month = st.selectbox("Select Month", 
                                    options=range(1, 13),
                                    format_func=lambda x: calendar.month_name[x])
                year = st.selectbox("Select Year", 
                                   options=sorted(df["date"].dt.year.unique(), reverse=True))
                
                monthly_df = df[(df["date"].dt.month == month) & (df["date"].dt.year == year)]
                
                if not monthly_df.empty:
                    col1, col2, col3 = st.columns(3)
                    col1.metric("💸 Total Spent", f"₹ {monthly_df['amount'].sum():,.2f}")
                    col2.metric("📊 Transactions", len(monthly_df))
                    col3.metric("📈 Daily Average", f"₹ {monthly_df['amount'].sum() / monthly_df['date'].dt.day.max():,.2f}")
                    
                    # Category breakdown
                    cat_data = monthly_df.groupby("category")["amount"].sum().reset_index().sort_values("amount", ascending=False)
                    fig = px.bar(cat_data, x='category', y='amount',
                                title=f"Spending Breakdown - {calendar.month_name[month]} {year}",
                                color='amount',
                                color_continuous_scale='Plasma')
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.dataframe(monthly_df.sort_values("date", ascending=False), use_container_width=True)
                else:
                    st.info("No expenses found for selected month")
            
            elif report_type == "Category Breakdown":
                cat_summary = df.groupby("category").agg({
                    'amount': ['sum', 'mean', 'count']
                }).round(2)
                cat_summary.columns = ['Total Spent', 'Average', 'Transactions']
                cat_summary = cat_summary.sort_values('Total Spent', ascending=False)
                
                st.markdown("### 📊 Category Summary")
                st.dataframe(cat_summary, use_container_width=True)
                
                # Visualization
                col1, col2 = st.columns(2)
                
                with col1:
                    # Bar chart
                    cat_data = df.groupby('category')['amount'].sum().reset_index().sort_values('amount', ascending=False)
                    fig1 = px.bar(cat_data, x='category', y='amount',
                                 title="Total Spending by Category",
                                 color='amount',
                                 color_continuous_scale='Viridis')
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    # Pie chart
                    fig2 = px.pie(cat_data, names='category', values='amount',
                                 title="Category Distribution",
                                 color_discrete_sequence=px.colors.qualitative.Pastel,
                                 hole=0.4)
                    st.plotly_chart(fig2, use_container_width=True)
            
            elif report_type == "Yearly Overview":
                year = st.selectbox("Select Year", 
                                   options=sorted(df["date"].dt.year.unique(), reverse=True),
                                   key="year_report")
                
                yearly_df = df[df["date"].dt.year == year]
                
                if not yearly_df.empty:
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("💸 Total Spent", f"₹ {yearly_df['amount'].sum():,.2f}")
                    col2.metric("📊 Transactions", len(yearly_df))
                    col3.metric("📅 Monthly Avg", f"₹ {yearly_df['amount'].sum() / 12:,.2f}")
                    col4.metric("📈 Daily Avg", f"₹ {yearly_df['amount'].sum() / 365:,.2f}")
                    
                    st.markdown("---")
                    
                    # Monthly trend
                    monthly_data = yearly_df.groupby(yearly_df["date"].dt.month)["amount"].sum().reset_index()
                    monthly_data["month"] = monthly_data["date"].apply(lambda x: calendar.month_name[x])
                    
                    fig = px.line(monthly_data, x='month', y='amount',
                                 title=f"📅 Monthly Spending Trend - {year}",
                                 markers=True)
                    fig.update_traces(line_color='#667eea', line_width=3)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Category breakdown for the year
                    st.markdown("### 📊 Category Breakdown")
                    cat_yearly = yearly_df.groupby("category")["amount"].sum().reset_index().sort_values("amount", ascending=False)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        fig2 = px.bar(cat_yearly, x='category', y='amount',
                                     title="Spending by Category",
                                     color='amount',
                                     color_continuous_scale='Blues')
                        st.plotly_chart(fig2, use_container_width=True)
                    
                    with col2:
                        fig3 = px.pie(cat_yearly, names='category', values='amount',
                                     title="Category Distribution",
                                     hole=0.4,
                                     color_discrete_sequence=px.colors.qualitative.Set3)
                        st.plotly_chart(fig3, use_container_width=True)
                else:
                    st.info("No expenses found for selected year")