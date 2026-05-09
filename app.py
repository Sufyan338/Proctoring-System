from streamlit_app import *  # noqa: F401,F403
import streamlit as st
from streamlit_option_menu import option_menu
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set page config
st.set_page_config(
    page_title="AI Proctoring System",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding-top: 2rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
if 'user' not in st.session_state:
    st.session_state.user = None
if 'exam_active' not in st.session_state:
    st.session_state.exam_active = False
if 'alerts' not in st.session_state:
    st.session_state.alerts = []

# Sidebar navigation
with st.sidebar:
    st.title("🎓 Proctoring System")
    st.divider()
    
    if st.session_state.user is None:
        selected = option_menu(
            menu_title="Main Menu",
            options=["Home", "Student Login", "Admin Login"],
            icons=["house", "person", "shield"],
            menu_icon="cast",
            default_index=0,
        )
    else:
        selected = option_menu(
            menu_title=f"Welcome, {st.session_state.user['name']}",
            options=["Dashboard", "Start Exam", "My Results", "Logout"],
            icons=["speedometer2", "pencil-square", "bar-chart", "box-arrow-right"],
            menu_icon="cast",
            default_index=0,
        )
    
    st.divider()
    st.caption("🔒 Secure & AI-Powered Exam Platform")

# Page routing
if st.session_state.user is None:
    if selected == "Home":
        st.title("🎯 AI-Powered Smart Exam Proctoring System")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            ### Welcome to Our Platform
            
            Our intelligent proctoring system ensures exam integrity with:
            
            ✅ **Real-time Face Detection** - Monitors student presence
            
            ✅ **AI-Powered Monitoring** - Detects suspicious activities
            
            ✅ **Secure Environment** - Prevents cheating attempts
            
            ✅ **Detailed Analytics** - Comprehensive exam reports
            """)
        
        with col2:
            st.image("https://via.placeholder.com/400x300?text=AI+Proctoring", use_column_width=True)
        
        st.divider()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Active Exams", "24", "📊")
        with col2:
            st.metric("Students Monitored", "156", "👥")
        with col3:
            st.metric("System Uptime", "99.9%", "✅")
    
    elif selected == "Student Login":
        st.title("👤 Student Login")
        
        with st.form("student_login_form"):
            email = st.text_input("Email Address", placeholder="student@university.edu")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("🔓 Login", use_container_width=True)
            
            if submitted:
                if email and password:
                    # Simulate successful login
                    st.session_state.user = {
                        "id": "STU001",
                        "name": email.split("@")[0],
                        "email": email,
                        "role": "student"
                    }
                    st.success("✅ Login successful!")
                    st.rerun()
                else:
                    st.error("❌ Please enter both email and password")
        
        st.info("ℹ️ Demo credentials: Use any email and password to proceed")
    
    elif selected == "Admin Login":
        st.title("🛡️ Administrator Login")
        
        with st.form("admin_login_form"):
            admin_id = st.text_input("Admin ID", placeholder="ADM001")
            password = st.text_input("Password", type="password", placeholder="Enter admin password")
            submitted = st.form_submit_button("🔓 Login", use_container_width=True)
            
            if submitted:
                if admin_id and password:
                    st.session_state.user = {
                        "id": admin_id,
                        "name": "Administrator",
                        "role": "admin"
                    }
                    st.success("✅ Admin login successful!")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")

else:
    # Logged in pages
    if selected == "Dashboard":
        st.title(f"📊 Dashboard - {st.session_state.user['name']}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Exams Completed", "5", "📋")
        with col2:
            st.metric("Average Score", "87%", "⭐")
        with col3:
            st.metric("Last Exam", "2 days ago", "📅")
        
        st.divider()
        st.subheader("📈 Recent Activity")
        
        # Sample activity data
        import pandas as pd
        activity_data = {
            "Date": ["2026-05-05", "2026-05-04", "2026-05-03", "2026-05-02"],
            "Exam": ["Mathematics", "Physics", "Chemistry", "Biology"],
            "Score": ["92%", "85%", "88%", "90%"],
            "Status": ["Passed", "Passed", "Passed", "Passed"]
        }
        st.dataframe(pd.DataFrame(activity_data), use_container_width=True)
    
    elif selected == "Start Exam":
        st.title("📝 Start Exam")
        st.subheader("Available Exams")
        
        import pandas as pd
        exams = pd.DataFrame({
            "Exam Name": ["Mathematics 101", "Physics 201", "Chemistry 301"],
            "Duration": ["2 hours", "2.5 hours", "2 hours"],
            "Questions": ["50", "40", "45"],
            "Status": ["Available", "Available", "Coming Soon"]
        })
        
        st.dataframe(exams, use_container_width=True)
        
        st.divider()
        exam_choice = st.selectbox("Select an exam to start:", ["Mathematics 101", "Physics 201"])
        
        if st.button("▶️ Start Exam", use_container_width=True):
            st.session_state.exam_active = True
            st.switch_page("pages/2_exam_interface.py")
    
    elif selected == "My Results":
        st.title("📊 My Exam Results")
        
        import pandas as pd
        results = pd.DataFrame({
            "Exam Name": ["Mathematics 101", "Physics 201", "Chemistry 301", "Biology 101"],
            "Date": ["2026-05-05", "2026-05-04", "2026-05-03", "2026-05-02"],
            "Score": ["92%", "85%", "88%", "90%"],
            "Time Taken": ["1h 45m", "2h 20m", "1h 58m", "2h 05m"],
            "Grade": ["A", "B+", "A-", "A"]
        })
        
        st.dataframe(results, use_container_width=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Overall Average", "88.75%", "📊")
        with col2:
            st.metric("Total Exams", "4", "📋")
        with col3:
            st.metric("Success Rate", "100%", "✅")
    
    elif selected == "Logout":
        st.session_state.user = None
        st.success("✅ Logged out successfully!")
        st.rerun()

# Footer
st.divider()
st.caption("🔐 All exam data is encrypted and secure. © 2026 AI Proctoring System")
