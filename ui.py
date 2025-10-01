#ui.py
import streamlit as st
import requests
import pandas as pd
import json

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="NutriScan – Food Label Analyzer", layout="wide")


st.markdown("""
    <style>
        .main-header {
            font-size: 3rem;
            color: #4CAF50;
            text-align: center;
            margin-bottom: 2rem;
        }
        .sub-header {
            font-size: 1.5rem;
            color: #2E7D32;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 0.5rem;
            margin-top: 1.5rem;
            margin-bottom: 1rem;
        }
        .metric-card {
            background-color: #f9f9f9;
            padding: 1.5rem;
            border-radius: 0.5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .risk-item {
            color: #d32f2f;
            padding: 0.5rem;
            background-color: #ffebee;
            border-radius: 0.25rem;
            margin-bottom: 0.5rem;
        }
        .benefit-item {
            color: #388e3c;
            padding: 0.5rem;
            background-color: #e8f5e9;
            border-radius: 0.25rem;
            margin-bottom: 0.5rem;
        }
        .ingredient-table {
            font-size: 0.9rem;
        }
        .stProgress > div > div > div > div {
            background-color: #4CAF50;
        }
    </style>""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header"> NutriScan – Food Label Analyzer</h1>', unsafe_allow_html=True)


with st.sidebar:
    st.header(" Personal Details")
    gender = st.selectbox("Gender", ["Male", "Female", "Other", "Prefer not to say"])
    age = st.number_input("Age", min_value=0, max_value=120, value=30)
    weight = st.number_input("Weight (kg)", min_value=0.0, max_value=200.0, value=65.0)
    height = st.number_input("Height (cm)", min_value=0.0, max_value=250.0, value=170.0)

    diet = st.selectbox("Diet Preference", [
        "No restrictions", "Vegan", "Vegetarian", "Keto", "Low-carb", "Diabetic", "Gluten-free"
    ])
    allergies = st.text_input("Allergies (comma-separated)")
    
    st.markdown("---")
    st.info("Upload a food Nutrition facts of a Product")
    
    st.markdown("---")
    st.caption("NutriScan v2.0 • Enhanced Analysis")

uploaded_file = st.file_uploader(" Upload Label Image", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:

    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)
    
    with col2:
        with st.spinner("Analyzing image..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            data = {
                "gender": gender,
                "age": age,
                "weight": weight,
                "height": height,
                "diet": diet,
                "allergies": allergies
            }
            try:
                response = requests.post(f"{API_URL}/analyze", files=files, data=data, timeout=30)
            except Exception as e:
                st.error(f" Request failed: {e}")
                response = None

    if response and response.status_code == 200:
        result = response.json()
        
        with st.expander(" OCR Extracted Text Preview", expanded=False):
            if "ocr_preview" in result:
                st.text_area("Raw OCR Text", value=result["ocr_preview"].get("raw_text", ""), height=150)
                st.write("Cleaned Ingredients:", result["ocr_preview"].get("cleaned_ingredients", []))
            else:
                st.info("No OCR preview available")

        detected = result.get("detected_product", "Unknown")
        if detected != "Unknown":
            st.markdown(f'<h2 class="sub-header"> Detected Product: {detected.title()}</h2>', unsafe_allow_html=True)
        
        analysis = result.get("analysis", {})
        hs = analysis.get("health_score", {})
        score = hs.get("score") if isinstance(hs, dict) else hs
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Health Score", f"{score}/100")
            st.caption(hs.get("explanation", ""))
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            verdict = analysis.get("verdict", "Unknown")
            if verdict == "Healthy":
                st.success(f"Safe to consume - {verdict}")
            elif verdict == "Moderate":
                st.info(f" Watch it - {verdict}")
            elif verdict == "Caution":
                st.warning(f"Do not comsume - {verdict}")
            elif verdict == "Unhealthy":
                st.error(f"Not recommended - {verdict}")
            else:
                st.write(f"{verdict}")
            st.caption(analysis.get("verdict_explanation", ""))
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col3:
            st.progress(score/100)
            st.caption("Overall Product Health Rating")
            
            bmi = result['personalization'].get('bmi')
            bmi_cat = result['personalization'].get('bmi_category')
            if bmi:
                st.write(f"**Your BMI:** {bmi} ({bmi_cat})")

        st.markdown('<h2 class="sub-header"> Personalized Profile</h2>', unsafe_allow_html=True)
        p_col1, p_col2, p_col3 = st.columns(3)
        with p_col1:
            st.write(f"**Age:** {age}")
        with p_col2:
            st.write(f"**Diet:** {diet}")
        with p_col3:
            allergies_list = [a.strip() for a in allergies.split(",")] if allergies else []
            st.write(f"**Allergies:** {', '.join(allergies_list) or 'None'}")

        st.markdown('<h2 class="sub-header"> Benefits & Risks Analysis</h2>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader(" Risks / Cautions")
            risks = result.get("risk_tags", [])
            if risks:
                for r in risks:
                    st.markdown(f'<div class="risk-item"> Unhealthy {r}</div>', unsafe_allow_html=True)
            else:
                st.success(" No major risks detected.")

        with col2:
            st.subheader(" Benefits")
            benefits = result.get("benefit_tags", [])
            if benefits:
                for b in benefits:
                    st.markdown(f'<div class="benefit-item">Benefits {b}</div>', unsafe_allow_html=True)
            else:
                st.info(" No significant benefits detected.")

        st.markdown('<h2 class="sub-header"> Ingredients & Consumption Advice</h2>', unsafe_allow_html=True)
        
        consumption_list = result.get("consumption_advice", [])
        if consumption_list:

            tab1, tab2 = st.tabs(["Table View", "Detailed View"])
            
            with tab1:
                table_data = []
                for item in consumption_list:
                    advice = item.get('advice', {})
                    table_data.append({
                        "Ingredient": item.get('ingredient', ''),
                        "Type": item.get('level', '').title(),
                        "Frequency": advice.get('frequency', ''),
                        "Amount": advice.get('amount', ''),
                        "Recommendation": advice.get('recommendation', '')[:50] + "..." if advice.get('recommendation') and len(advice.get('recommendation', '')) > 50 else advice.get('recommendation', '')
                    })
                
                if table_data:
                    df = pd.DataFrame(table_data)
                    st.dataframe(df, use_container_width=True)
            
            with tab2:
                for item in consumption_list:
                    with st.expander(f"{item.get('ingredient', '')} ({item.get('level', '').title()})", expanded=False):
                        advice = item.get('advice', {})
                        st.write(f"**Frequency:** {advice.get('frequency', 'Unknown')}")
                        st.write(f"**Amount:** {advice.get('amount', 'Unknown')}")
                        st.write(f"**Recommendation:** {advice.get('recommendation', '')}")
                        
                        effects = item.get('effects', [])
                        if effects:
                            st.write("**Effects:**")
                            for effect in effects:
                                st.write(f"- {effect}")
        else:
            st.info("No recognized ingredients with advice found.")

        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button(" Download Full Report (JSON)"):
                st.download_button(
                    label="Download JSON",
                    data=json.dumps(result, indent=2),
                    file_name="nutriscan_report.json",
                    mime="application/json"
                )

    else:
        if response is not None:
            st.error(f" API Error: {response.text}")