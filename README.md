# NutriScan - Food Label Analyzer

NutriScan is an intelligent food label analysis system that uses OCR and AI to extract and analyze nutritional information from food product images. It provides personalized health recommendations based on user profiles.

## Features

- **Image Processing**: Extracts text from food label images using Tesseract and EasyOCR
- **AI-Powered Analysis**: Uses BERT model for nutrition entity recognition
- **Personalized Insights**: Considers user's age, weight, height, diet, and allergies
- **Health Scoring**: Provides comprehensive health scores and risk assessments
- **Interactive UI**: Streamlit-based web interface for easy interaction
- **Smart Recommendations**: Personalized consumption advice for detected ingredients

## Installation

1.  **Clone the repository**

    git clone <repository-url>
    cd nutriscan

2.  **Install Python dependencies**

    pip install -r requirements.txt

3.  **Install system dependencies**

    Tesseract OCR:

        Windows: Download from UB-Mannheim/tesseract

        Ubuntu: sudo apt install tesseract-ocr

        macOS: brew install tesseract

**Usage** 1. Start the Backend Server

        uvicorn app:app --reload --host 0.0.0.0 --port 8000


    2. Start the Frontend (in a new terminal)

        streamlit run ui.py

**_Access the Application_**

    Frontend: http://localhost:8501

    Backend API: http://localhost:8000

**_API Endpoints_**

    POST /analyze: Analyze food label image with user profile

    GET /results: Get last analysis results

**_Configuration_**

    The application uses:

        OCR: Tesseract (primary) + EasyOCR (fallback)

        NER Model: sgarbi/bert-fda-nutrition-ner

        Image Processing: Pillow for enhancement and filtering
