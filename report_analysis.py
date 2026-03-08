import streamlit as st
import re
import fitz
import pandas as pd
import matplotlib.pyplot as plt

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="AI Medical Report Analyzer",
    page_icon="🏥",
    layout="wide"
)

# --------------------------------------------------
# LOAD CSS
# --------------------------------------------------
def load_css():
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# --------------------------------------------------
# HEADER
# --------------------------------------------------
st.markdown('<div class="main-title">AI Multi-Specialty Medical Analyzer</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Multi-Report Dashboard • AI Insights • Health Analytics</div>', unsafe_allow_html=True)
st.divider()

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.title("📌 Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Detailed Report", "AI Summary", "Compare Reports"])

uploaded_files = st.sidebar.file_uploader(
    "Upload Medical Report PDFs",
    type="pdf",
    accept_multiple_files=True
)

# --------------------------------------------------
# FUNCTIONS
# --------------------------------------------------

def extract_text(uploaded_file):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def detect_report_type(text):
    text = text.lower()
    if any(k in text for k in ["hemoglobin", "wbc", "rbc"]):
        return "Blood Report"
    elif any(k in text for k in ["tsh", "t3", "t4"]):
        return "Thyroid Report"
    elif any(k in text for k in ["glucose", "hba1c"]):
        return "Diabetes Report"
    else:
        return "General Medical Report"

def extract_tests(text):

    pattern = r"([A-Za-z\s]+)\s+([\d.]+)\s*([a-zA-Z/%]*)\s+([\d.]+)\s*-\s*([\d.]+)"
    matches = re.findall(pattern, text)

    results = []

    for m in matches:

        test, value, unit, low, high = m
        value = float(value)
        low = float(low)
        high = float(high)

        if value < low:
            status = "LOW"
        elif value > high:
            status = "HIGH"
        else:
            status = "NORMAL"

        results.append({
            "Test": test.strip(),
            "Value": value,
            "Normal Range": f"{low}-{high}",
            "Status": status
        })

    df = pd.DataFrame(results)

    # Normalize test names
    df["Test"] = df["Test"].str.strip().str.lower()

    return df

# --------------------------------------------------
# SESSION STATE STORAGE
# --------------------------------------------------
if "reports" not in st.session_state:
    st.session_state.reports = {}

# Process uploaded files
if uploaded_files:

    for file in uploaded_files:

        if file.name not in st.session_state.reports:

            text = extract_text(file)
            df = extract_tests(text)
            report_type = detect_report_type(text)

            st.session_state.reports[file.name] = {
                "df": df,
                "type": report_type
            }

# --------------------------------------------------
# IF REPORTS EXIST
# --------------------------------------------------
if st.session_state.reports:

    selected_report = st.sidebar.selectbox(
        "Select Report",
        list(st.session_state.reports.keys())
    )

    report_data = st.session_state.reports[selected_report]
    df = report_data["df"]
    report_type = report_data["type"]

# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------
    if page == "Dashboard":

        st.subheader(f"📊 Overview - {selected_report}")
        st.write("Report Type:", report_type)

        total = len(df)
        abnormal = len(df[df["Status"] != "NORMAL"])
        normal = total - abnormal

        col1, col2, col3 = st.columns(3)

        col1.metric("Total Tests", total)
        col2.metric("Normal", normal)
        col3.metric("Abnormal", abnormal)

        st.divider()

        st.dataframe(df, use_container_width=True)

# --------------------------------------------------
# DETAILED REPORT
# --------------------------------------------------
    elif page == "Detailed Report":

        st.subheader(f"📄 Detailed Analysis - {selected_report}")

        abnormal_df = df[df["Status"] != "NORMAL"]

        if not abnormal_df.empty:

            fig, ax = plt.subplots()

            ax.bar(abnormal_df["Test"], abnormal_df["Value"])

            plt.xticks(rotation=45)
            plt.tight_layout()

            st.pyplot(fig)

        else:

            st.success("All parameters are within normal range.")

# --------------------------------------------------
# AI SUMMARY
# --------------------------------------------------
    elif page == "AI Summary":

        st.subheader(f"🧠 AI Summary - {selected_report}")

        abnormal_df = df[df["Status"] != "NORMAL"]

        if abnormal_df.empty:

            st.success("Patient parameters appear within normal range.")

        else:

            for _, row in abnormal_df.iterrows():

                st.write(
                    f"• {row['Test']} is {row['Status']} (Value: {row['Value']}). Clinical attention may be required."
                )

# --------------------------------------------------
# COMPARE REPORTS (FIXED + GRAPH ADDED)
# --------------------------------------------------
    elif page == "Compare Reports":

        st.subheader("📈 Compare Medical Reports")

        report_names = list(st.session_state.reports.keys())

        if len(report_names) >= 2:

            r1 = st.selectbox("Select First Report", report_names)
            r2 = st.selectbox("Select Second Report", report_names, index=1)

            df1 = st.session_state.reports[r1]["df"]
            df2 = st.session_state.reports[r2]["df"]

            # OUTER MERGE FIX
            merged = pd.merge(
                df1,
                df2,
                on="Test",
                how="outer",
                suffixes=("_1", "_2")
            )

            merged.fillna("-", inplace=True)

            st.divider()

            # -------------------------------
            # TABLE
            # -------------------------------
            st.subheader("📋 Comparison Table")

            st.dataframe(
                merged,
                use_container_width=True
            )

            st.divider()

            # -------------------------------
            # GRAPH
            # -------------------------------
            st.subheader("📊 Comparison Graph")

            chart_df = merged.copy()

            chart_df["Value_1"] = pd.to_numeric(chart_df["Value_1"], errors="coerce")
            chart_df["Value_2"] = pd.to_numeric(chart_df["Value_2"], errors="coerce")

            fig, ax = plt.subplots()

            x = range(len(chart_df["Test"]))

            ax.bar(x, chart_df["Value_1"], width=0.4, label=r1)
            ax.bar(
                [i + 0.4 for i in x],
                chart_df["Value_2"],
                width=0.4,
                label=r2
            )

            ax.set_xticks([i + 0.2 for i in x])
            ax.set_xticklabels(chart_df["Test"], rotation=45)

            ax.set_ylabel("Test Values")
            ax.set_title("Medical Report Comparison")

            ax.legend()

            plt.tight_layout()

            st.pyplot(fig)

        else:

            st.info("Upload at least two reports to compare.")

else:

    st.info("Upload one or more medical reports to begin analysis.")