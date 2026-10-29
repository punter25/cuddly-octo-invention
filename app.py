import io
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Punters Formula Pro",
    page_icon="🏆",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.title("🏆 Punters' Master Formula Engine")
st.caption("Personal racing analysis tool • South Africa • Hong Kong • United Kingdom")

# -----------------------------
# Session state
# -----------------------------
if "results_log" not in st.session_state:
    st.session_state.results_log = pd.DataFrame(
        columns=[
            "Region", "Meeting", "Race", "Predicted Winner",
            "Actual Winner", "Status"
        ]
    )

if "uploads" not in st.session_state:
    st.session_state.uploads = {
        "Gold Circle": pd.DataFrame(),
        "HKJC": pd.DataFrame(),
        "Racing Post": pd.DataFrame(),
    }

# -----------------------------
# Helper functions
# -----------------------------
COLUMN_ALIASES = {
    "runner": ["horse", "horse name", "runner", "runner name", "selection", "name"],
    "number": ["number", "runner no", "horse no", "tab no", "saddlecloth"],
    "draw": ["draw", "barrier", "gate", "barrier draw"],
    "jockey": ["jockey", "rider"],
    "trainer": ["trainer"],
    "weight": ["weight", "carried", "handicap weight"],
    "odds": ["odds", "sp", "starting price", "fixed odds", "win odds"],
    "rating": ["rating", "official rating", "or", "handicap rating", "rating"],
    "form": ["form", "last 5", "recent form", "form figures"],
    "speed": ["speed", "speed rating", "sectional", "sectionals"],
    "class": ["class", "class rating", "earnings", "prize money"],
    "pace": ["pace", "pace rating", "energy"],
}

def find_column(df, aliases):
    cols = {str(c).strip().lower(): c for c in df.columns}
    for alias in aliases:
        if alias in cols:
            return cols[alias]
    for alias in aliases:
        for lower, original in cols.items():
            if alias in lower:
                return original
    return None

def read_uploaded_file(uploaded_file):
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)
    st.error("Please upload a CSV, XLSX, or XLS file. PDF racecards cannot be parsed reliably here.")
    return None

def normalise_uploaded_data(df):
    if df.empty:
        return df, {}

    mapping = {}
    for key, aliases in COLUMN_ALIASES.items():
        found = find_column(df, aliases)
        if found:
            mapping[key] = found

    clean = df.copy()

    if "runner" in mapping:
        clean = clean.rename(columns={mapping["runner"]: "Runner"})
    else:
        clean["Runner"] = [f"Runner {i + 1}" for i in range(len(clean))]

    for key in ["number", "draw", "jockey", "trainer", "weight", "odds", "rating", "form"]:
        if key in mapping:
            clean = clean.rename(columns={mapping[key]: key.capitalize()})

    for score_key in ["speed", "class", "pace", "draw", "form"]:
        col_name = score_key.capitalize()
        if col_name not in clean.columns:
            clean[col_name] = 50

        clean[col_name] = pd.to_numeric(clean[col_name], errors="coerce").fillna(50)
        clean[col_name] = clean[col_name].clip(1, 100)

    return clean, mapping

def score_runners(df, weights):
    required = ["Speed", "Class", "Pace", "Draw", "Form"]
    for col in required:
        if col not in df.columns:
            df[col] = 50

    df["Power Score"] = (
        df["Speed"] * weights["speed"]
        + df["Class"] * weights["class"]
        + df["Pace"] * weights["pace"]
        + df["Draw"] * weights["draw"]
        + df["Form"] * weights["form"]
    ).round(1)

    return df.sort_values("Power Score", ascending=False).reset_index(drop=True)

def display_race_engine(region, default_meetings):
    st.header(f"{region} Strategy Matrix")
    st.caption("Set your formula weights, then score the runners for the selected race.")

    col1, col2 = st.columns(2)
    with col1:
        speed_w = st.slider("🏎️ Speed / Sectionals", 0.0, 1.0, 0.35, 0.05, key=f"{region}_speed")
        class_w = st.slider("👑 Class / Earnings", 0.0, 1.0, 0.25, 0.05, key=f"{region}_class")
        pace_w = st.slider("⚡ Pace / Energy", 0.0, 1.0, 0.20, 0.05, key=f"{region}_pace")
    with col2:
        draw_w = st.slider("🚧 Draw / Barrier", 0.0, 1.0, 0.10, 0.05, key=f"{region}_draw")
        form_w = st.slider("📉 Form / Recency", 0.0, 1.0, 0.10, 0.05, key=f"{region}_form")

    weights = {
        "speed": speed_w,
        "class": class_w,
        "pace": pace_w,
        "draw": draw_w,
        "form": form_w,
    }
    total_weight = round(sum(weights.values()), 2)

    if total_weight != 1.00:
        st.warning(f"⚠️ Weights total {total_weight:.2f}. Adjust them to total exactly 1.00.")
    else:
        st.success("✅ Formula weights are valid.")

    st.divider()
    st.subheader("Runner Entry")

    with st.form(f"{region}_runner_form"):
        meeting = st.selectbox("Meeting / Circuit", default_meetings, key=f"{region}_meeting")
        race_no = st.number_input("Race number", 1, 20, 1, key=f"{region}_race")

        runner_name = st.text_input(
            "Runner name / number",
            placeholder="e.g. Lucky Sam Gor",
            key=f"{region}_runner",
        )

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            speed = st.number_input("Speed", 1, 100, 50, key=f"{region}_s")
        with c2:
            class_score = st.number_input("Class", 1, 100, 50, key=f"{region}_c")
        with c3:
            pace = st.number_input("Pace", 1, 100, 50, key=f"{region}_p")
        with c4:
            draw = st.number_input("Draw", 1, 100, 50, key=f"{region}_d")
        with c5:
            form = st.number_input("Form", 1, 100, 50, key=f"{region}_f")

        submitted = st.form_submit_button("Calculate Power Score", use_container_width=True)

    if submitted:
        if total_weight != 1.00:
            st.error("Fix the weights before calculating.")
        elif not runner_name.strip():
            st.warning("Enter a runner name or number.")
        else:
            power = (
                speed * speed_w
                + class_score * class_w
                + pace * pace_w
                + draw * draw_w
                + form * form_w
            )
            st.metric(
                f"📊 {runner_name.strip()} — Power Score",
                f"{power:.1f} pts",
            )

    st.divider()
    st.subheader("Uploaded Field Analysis")

    region_upload = st.session_state.uploads.get(region)
    if region_upload is not None and not region_upload.empty:
        if total_weight == 1.00:
            ranked = score_runners(region_upload.copy(), weights)
            st.dataframe(
                ranked[["Runner", "Speed", "Class", "Pace", "Draw", "Form", "Power Score"]],
                use_container_width=True,
                hide_index=True,
            )
            if not ranked.empty:
                top = ranked.iloc[0]
                st.success(f"🏁 Current top selection: **{top['Runner']}** — {top['Power Score']} pts")
        else:
            st.info("Set weights to 1.00 to rank the uploaded field.")
    else:
        st.info("Upload a Gold Circle, HKJC, or Racing Post file in the 📂 Uploads tab.")

# -----------------------------
# Main tabs
# -----------------------------
tab_sa, tab_hk, tab_uk, tab_uploads, tab_results = st.tabs(
    ["🇿🇦 South African", "🇭🇰 Hong Kong", "🇬🇧 UK", "📂 Uploads", "📊 Results"]
)

with tab_sa:
    display_race_engine(
        "South African",
        ["Durbanville", "Kenilworth", "Turffontein", "VaAL", "Fairview", "Scottsville", "Greyville"],
    )

with tab_hk:
    display_race_engine(
        "Hong Kong",
        ["Sha Tin", "Happy Valley"],
    )

with tab_uk:
    display_race_engine(
        "UK",
        ["Ascot", "Newmarket", "York", "Cheltenham", "Epsom", "Kempton", "Wolverhampton"],
    )

with tab_uploads:
    st.header("📂 Race Data Uploads")
    st.caption("Upload CSV or Excel exports. For best results, use one row per runner.")

    upload_cols = st.columns(3)

    with upload_cols[0]:
        st.subheader("🇿🇦 Gold Circle")
        gc_file = st.file_uploader(
            "Gold Circle CSV / Excel",
            type=["csv", "xlsx", "xls"],
            key="gc_upload",
        )
        if gc_file:
            gc_df = read_uploaded_file(gc_file)
            if gc_df is not None:
                clean_gc, gc_map = normalise_uploaded_data(gc_df)
                st.session_state.uploads["South African"] = clean_gc
                st.success(f"Loaded {len(clean_gc)} runners.")
                st.dataframe(clean_gc.head(20), use_container_width=True, hide_index=True)
                if not gc_map:
                    st.warning("No familiar column names detected. The app will use default scores unless your file includes Speed, Class, Pace, Draw, and Form columns.")

    with upload_cols[1]:
        st.subheader("🇭🇰 HKJC")
        hkjc_file = st.file_uploader(
            "HKJC CSV / Excel",
            type=["csv", "xlsx", "xls"],
            key="hkjc_upload",
        )
        if hkjc_file:
            hkjc_df = read_uploaded_file(hkjc_file)
            if hkjc_df is not None:
                clean_hkjc, hkjc_map = normalise_uploaded_data(hkjc_df)
                st.session_state.uploads["Hong Kong"] = clean_hkjc
                st.success(f"Loaded {len(clean_hkjc)} runners.")
                st.dataframe(clean_hkjc.head(20), use_container_width=True, hide_index=True)
                if not hkjc_map:
                    st.warning("No familiar column names detected. Use columns such as Horse, Draw, Rating, Odds, and Form.")

    with upload_cols[2]:
        st.subheader("🇬🇧 Racing Post")
        rp_file = st.file_uploader(
            "Racing Post CSV / Excel",
            type=["csv", "xlsx", "xls"],
            key="rp_upload",
        )
        if rp_file:
            rp_df = read_uploaded_file(rp_file)
            if rp_df is not None:
                clean_rp, rp_map = normalise_uploaded_data(rp_df)
                st.session_state.uploads["UK"] = clean_rp
                st.success(f"Loaded {len(clean_rp)} runners.")
                st.dataframe(clean_rp.head(20), use_container_width=True, hide_index=True)
                if not rp_map:
                    st.warning("No familiar column names detected. Use columns such as Horse, Draw, Rating, Odds, and Form.")

    st.divider()
    st.subheader("Recommended upload format")

    st.markdown(
        """
| Column | Example | Used for |
|---|---:|---|
| Horse / Runner | Lucky Sam Gor | Runner name |
| Draw / Barrier | 4 | Draw score |
| Rating | 82 | Class score |
| Odds / SP | 3.5 | Optional market reference |
| Speed | 78 | Speed score |
| Pace | 65 | Pace score |
| Form | 72 | Form score |
        """
    )

    st.download_button(
        "⬇️ Download blank runner template",
        data=pd.DataFrame({
            "Runner": ["Runner 1", "Runner 2"],
            "Draw": [1, 2],
            "Rating": [80, 75],
            "Odds": [3.5, 6.0],
            "Speed": [70, 65],
            "Pace": [60, 75],
            "Form": [80, 70],
        }).to_csv(index=False).encode("utf-8"),
        file_name="punters_formula_runner_template.csv",
        mime="text/csv",
        use_container_width=True,
    )

with tab_results:
    st.header("📊 Performance Tracker")
    st.caption("Log predicted selections against actual winners to audit your formula.")

    with st.form("results_form"):
        region = st.selectbox("Region", ["South African", "Hong Kong", "UK"])
        meeting = st.text_input("Meeting", placeholder="e.g. Durbanville")
        race_no = st.number_input("Race number", 1, 20, 1)
        predicted = st.text_input("Predicted winner", placeholder="Your top selection")
        actual = st.text_input("Actual winner", placeholder="Winner on track")

        logged = st.form_submit_button("Log result", use_container_width=True)

    if logged:
        if not predicted.strip() or not actual.strip():
            st.warning("Enter both the predicted and actual winner.")
        else:
            status = "🎯 STRIKE" if predicted.lower().strip() == actual.lower().strip() else "❌ DEVIATION"
            new_row = pd.DataFrame([{
                "Region": region,
                "Meeting": meeting.strip() or "Not specified",
                "Race": int(race_no),
                "Predicted Winner": predicted.strip(),
                "Actual Winner": actual.strip(),
                "Status": status,
            }])
            st.session_state.results_log = pd.concat(
                [st.session_state.results_log, new_row],
                ignore_index=True,
            )
            st.success("Result logged.")

    st.subheader("Result log")
    st.dataframe(
        st.session_state.results_log,
        use_container_width=True,
        hide_index=True,
    )

    if not st.session_state.results_log.empty:
        strikes = (st.session_state.results_log["Status"] == "🎯 STRIKE").sum()
        total = len(st.session_state.results_log)
        strike_rate = strikes / total * 100

        m1, m2, m3 = st.columns(3)
        m1.metric("Races logged", total)
        m2.metric("Strikes", strikes)
        m3.metric("Strike rate", f"{strike_rate:.1f}%")

        csv_log = st.session_state.results_log.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download results log",
            data=csv_log,
            file_name="punters_formula_results.csv",
            mime="text/csv",
            use_container_width=True,
        )

        if st.button("🗑️ Clear all logged results", use_container_width=True):
            st.session_state.results_log = pd.DataFrame(
                columns=[
                    "Region", "Meeting", "Race", "Predicted Winner",
                    "Actual Winner", "Status"
                ]
            )
            st.rerun()
