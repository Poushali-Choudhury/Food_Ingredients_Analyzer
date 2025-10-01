# app.py

import os
import io
import re
import pytesseract
import easyocr
from PIL import Image, ImageEnhance, ImageFilter
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from typing import Dict, List, Any, Optional
import json

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

last_results = {}

easyocr_reader = easyocr.Reader(['en'])


def preprocess_image(image: Image.Image) -> Image.Image:
    image = image.convert("L")
    image = image.filter(ImageFilter.SHARPEN)
    enhancer = ImageEnhance.Contrast(image)
    return enhancer.enhance(2)


def extract_text(image: Image.Image) -> str:
    preprocessed = preprocess_image(image)
    text = pytesseract.image_to_string(preprocessed)
    if not text.strip():
        results = easyocr_reader.readtext(image)
        text = " ".join([res[1] for res in results])
    return text.strip()


def clean_and_deduplicate(ocr_text: str):
    items = re.split(r"[\,\n;:\.]", ocr_text)
    cleaned, seen = [], set()
    for item in items:
        word = item.strip().lower()
        word = re.sub(r"[^a-zA-Z0-9\s-]", "", word)
        if word and word not in seen:
            cleaned.append(word)
            seen.add(word)
    return cleaned


MODEL_NAME = "sgarbi/bert-fda-nutrition-ner"
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForTokenClassification.from_pretrained(MODEL_NAME)
    ner_pipeline = pipeline("ner", model=model, tokenizer=tokenizer, aggregation_strategy="simple")
except Exception as e:
    ner_pipeline = None
    print("Warning: NER model could not be loaded:", e)


def compute_bmi(weight, height):
    if not weight or not height:
        return None, "Unknown"
    h_m = height / 100.0
    try:
        bmi = round(weight / (h_m ** 2), 1)
    except Exception:
        return None, "Unknown"
    if bmi < 18.5:
        return bmi, "Underweight"
    elif bmi < 25:
        return bmi, "Normal"
    elif bmi < 30:
        return bmi, "Overweight"
    else:
        return bmi, "Obese"



INGREDIENT_KNOWLEDGE = {
    "sugar": {
        "type": "risky",
        "effects": ["Weight gain", "Increased diabetes risk", "Tooth decay"],
        "recommendation": "Limit intake to less than 25g per day"
    },
    "salt": {
        "type": "risky",
        "effects": ["High blood pressure", "Heart disease risk"],
        "recommendation": "Limit to less than 5g per day"
    },
    "oil": {
        "type": "moderate",
        "effects": ["Source of fats", "High in calories"],
        "recommendation": "Use in moderation, prefer unsaturated varieties"
    },
    "butter": {
        "type": "risky",
        "effects": ["High in saturated fats", "Cholesterol increase"],
        "recommendation": "Limit consumption, use healthier alternatives"
    },
    "cream": {
        "type": "risky",
        "effects": ["High in saturated fats", "High calorie content"],
        "recommendation": "Consume occasionally in small amounts"
    },
    "milk": {
        "type": "moderate",
        "effects": ["Calcium source", "Protein content"],
        "recommendation": "1-2 servings daily, prefer low-fat options"
    },
    "cheese": {
        "type": "moderate",
        "effects": ["Calcium source", "High in protein", "High in saturated fats"],
        "recommendation": "Moderate consumption (1-2 servings daily)"
    },
    "apple": {
        "type": "healthy",
        "effects": ["Fiber source", "Vitamins and antioxidants"],
        "recommendation": "1-2 servings daily"
    },
    "banana": {
        "type": "healthy",
        "effects": ["Potassium source", "Natural energy boost"],
        "recommendation": "1-2 servings daily"
    },
    "carrot": {
        "type": "healthy",
        "effects": ["Vitamin A source", "Eye health", "Antioxidants"],
        "recommendation": "Regular consumption recommended"
    },
    "spinach": {
        "type": "healthy",
        "effects": ["Iron source", "Rich in vitamins", "Antioxidants"],
        "recommendation": "Regular consumption recommended"
    },
    "oats": {
        "type": "healthy",
        "effects": ["Fiber source", "Heart health", "Cholesterol reduction"],
        "recommendation": "Daily consumption beneficial"
    },
    "lentil": {
        "type": "healthy",
        "effects": ["Protein source", "Fiber content", "Iron source"],
        "recommendation": "Regular consumption recommended"
    },
    "whole wheat": {
        "type": "healthy",
        "effects": ["Fiber source", "Sustained energy release"],
        "recommendation": "Prefer over refined grains"
    },
    "honey": {
        "type": "moderate",
        "effects": ["Natural sweetener", "Antioxidants", "High in sugar"],
        "recommendation": "Use sparingly as sugar alternative"
    },
    "egg": {
        "type": "moderate",
        "effects": ["Protein source", "Vitamins and minerals", "Cholesterol content"],
        "recommendation": "3-7 servings weekly"
    },
    "yogurt": {
        "type": "healthy",
        "effects": ["Probiotics", "Calcium source", "Protein content"],
        "recommendation": "Daily consumption beneficial (plain varieties)"
    },
    "tomato": {
        "type": "healthy",
        "effects": ["Antioxidants", "Vitamin C source", "Lycopene content"],
        "recommendation": "Regular consumption recommended"
    },
    "almond": {
        "type": "healthy",
        "effects": ["Healthy fats", "Vitamin E source", "Protein content"],
        "recommendation": "Handful daily as healthy snack"
    },
    "soy": {
        "type": "healthy",
        "effects": ["Plant protein source", "May reduce cholesterol"],
        "recommendation": "Regular consumption beneficial"
    }
}


def generate_consumption_advice_enhanced(ingredient: str):

    for known_ingredient, info in INGREDIENT_KNOWLEDGE.items():
        if known_ingredient in ingredient.lower():
            return {
                "level": info["type"],
                "effects": info["effects"],
                "recommendation": info["recommendation"],
                "frequency": "Occasional (≤1 per week)" if info["type"] == "risky" else 
                            "1–3 servings/week" if info["type"] == "moderate" else 
                            "Daily",
                "amount": "Max 1 serving when consumed" if info["type"] == "risky" else 
                         "1 serving" if info["type"] == "moderate" else 
                         "1 serving (e.g., 1 cup/1 piece)"
            }
    

    risky = ["sugar", "salt", "oil", "butter", "cream", "fried", "syrup"]
    moderate = ["milk", "cheese", "bread", "rice", "pasta", "nuts"]
    healthy = ["apple", "banana", "carrot", "spinach", "oats", "lentil"]

    key = ingredient.lower()
    if any(r in key for r in risky):
        return {
            "level": "risky", 
            "frequency": "Occasional (≤1 per week)", 
            "amount": "Max 1 serving when consumed",
            "effects": ["Potential health risks with overconsumption"],
            "recommendation": "Limit consumption and check for healthier alternatives"
        }
    elif any(m in key for m in moderate):
        return {
            "level": "moderate", 
            "frequency": "1–3 servings/week", 
            "amount": "1 serving",
            "effects": ["Provides nutrients but should be consumed in moderation"],
            "recommendation": "Consume as part of a balanced diet"
        }
    elif any(h in key for h in healthy):
        return {
            "level": "healthy", 
            "frequency": "Daily", 
            "amount": "1 serving (e.g., 1 cup/1 piece)",
            "effects": ["Provides essential nutrients and health benefits"],
            "recommendation": "Regular consumption recommended"
        }
    else:
        return {
            "level": "unknown", 
            "frequency": "Unknown", 
            "amount": "Unknown",
            "effects": ["Insufficient data for specific recommendations"],
            "recommendation": "Consume mindfully and check for allergens"
        }


PRODUCT_KEYWORDS = {
    "cereal": ["cereal", "muesli", "flakes", "granola"],
    "chocolate": ["chocolate", "cocoa", "cacao", "bar"],
    "biscuit": ["biscuit", "cookie", "cracker"],
    "juice": ["juice", "nectar", "orange", "apple juice"],
    "snack": ["chips", "crisps", "puffs"],
    "milk_product": ["milk", "yogurt", "cheese", "butter"],
}

known_products = {
    "amul butter": "Amul Butter",
    "maggi": "Nestlé Maggi Noodles",
    "marie gold": "Britannia Marie Gold Biscuits",
    "oreo": "Oreo Biscuits",
    "parle g": "Parle-G Biscuits",
    "kitkat": "Nestlé KitKat",
    "dairy milk": "Cadbury Dairy Milk",
    "coca cola": "Coca Cola",
    "pepsi": "Pepsi",
    "lays": "Lays Chips",
    "tropicana": "Tropicana Juice",
    "nescafe": "Nescafe Coffee",
}


def recognize_product(ocr_text: str):
    text = ocr_text.lower()
    for key, name in known_products.items():
        if key in text:
            return name

    scores = {}
    for p, kws in PRODUCT_KEYWORDS.items():
        for k in kws:
            if k in text:
                scores[p] = scores.get(p, 0) + 1
    if not scores:
        if "net wt" in text or "net weight" in text:
            return "Packaged product"
        return "Unknown"

    return max(scores.items(), key=lambda x: x[1])[0]


def clean_entity_token(token: str):
    token = token.replace("##", "")
    token = token.strip(" ,.-")
    return token


def analyze_text(text, user_profile):
    product = recognize_product(text)
    raw_ingredients = clean_and_deduplicate(text)

    ocr_preview = {
        "raw_text": text,
        "cleaned_ingredients": raw_ingredients
    }

    entities, grouped, flat_tokens = [], {}, []
    if ner_pipeline:
        try:
            entities = ner_pipeline(text)
            for ent in entities:
                label = ent.get("entity_group", "OTHER")
                word = clean_entity_token(ent.get("word", ""))
                if word:
                    grouped.setdefault(label, []).append(word.lower())
                    flat_tokens.append(word.lower())
        except Exception as e:
            print("NER error:", e)

    if not grouped:
        grouped = {"INGREDIENTS": raw_ingredients}
        flat_tokens = raw_ingredients

    risks, benefits = [], []
    risk_keywords = ["sugar", "salt", "syrup", "fat", "hydrogenated", "trans", "butter", "cream", "oil", "sodium", "additive", "preservative"]
    benefit_keywords = ["vitamin", "protein", "calcium", "iron", "fiber", "dietary fiber", "antioxidant", "mineral", "whole grain"]

    for w in flat_tokens:
        if any(rk in w for rk in risk_keywords) and w not in risks:
            risks.append(w)
        if any(bk in w for bk in benefit_keywords) and w not in benefits:
            benefits.append(w)
    if any("sugar" in w for w in flat_tokens) and "high sugar content" not in risks:
        risks.append("high sugar content")

    bmi, bmi_cat = compute_bmi(user_profile.get("weight"), user_profile.get("height"))

    allergy_flags = [f"Contains allergen: {a}" for a in user_profile.get("allergies", []) if any(a.lower() in w for w in flat_tokens)]

    diet_flags, diet = [], (user_profile.get("diet") or "No restrictions").lower()
    if diet == "vegan" and any(w in flat_tokens for w in ["milk", "egg", "cheese", "butter", "honey", "gelatin", "whey"]):
        diet_flags.append("Not vegan-friendly")
    if diet == "vegetarian" and any(w in flat_tokens for w in ["meat", "fish", "chicken", "gelatin", "rennet", "lard"]):
        diet_flags.append("Not vegetarian-friendly")
    if diet == "keto" and any(w in flat_tokens for w in ["sugar", "rice", "bread", "pasta", "syrup", "honey", "flour"]):
        diet_flags.append("High in carbs — not keto-friendly")
    if diet == "diabetic" and any(w in flat_tokens for w in ["sugar", "syrup", "honey", "glucose", "fructose", "dextrose"]):
        diet_flags.append("High sugar — not suitable for diabetic diet")
    if diet == "gluten-free" and any(w in flat_tokens for w in ["wheat", "barley", "rye", "gluten", "malt"]):
        diet_flags.append("Contains gluten — not gluten-free")

    base = 100
    base -= len(set(risks)) * 8
    if allergy_flags:
        base -= 20
    base -= len(set(diet_flags)) * 5
    health_score = max(0, min(100, base))

    if health_score >= 80:
        verdict, verdict_expl = "Healthy", "Safe for regular consumption in typical serving sizes."
    elif health_score >= 60:
        verdict, verdict_expl = "Moderate", "Contains ingredients to be consumed in moderation."
    elif health_score >= 40:
        verdict, verdict_expl = "Caution", "Contains multiple risk factors — limit frequency and amount."
    else:
        verdict, verdict_expl = "Unhealthy", "High-risk product — avoid frequent consumption."

    consumption_advice = []
    for ing in raw_ingredients:
        adv = generate_consumption_advice_enhanced(ing)
        if adv["level"] == "unknown":
            continue
            
        summary = (
            f"Consider limiting to {adv['frequency']}. {adv['amount']}. {adv['recommendation']}" if adv["level"] == "risky"
            else f"Consume in moderation: {adv['frequency']}, typical amount: {adv['amount']}. {adv['recommendation']}" if adv["level"] == "moderate"
            else f"Healthy choice: {adv['frequency']}. Typical serving: {adv['amount']}. {adv['recommendation']}" if adv["level"] == "healthy"
            else "No clear guidance — consume mindfully."
        )
        consumption_advice.append({
            "ingredient": ing.title(),
            "level": adv["level"],
            "effects": adv.get("effects", []),
            "advice": {
                "frequency": adv.get("frequency"), 
                "amount": adv.get("amount"), 
                "summary": summary,
                "recommendation": adv.get("recommendation", "")
            }
        })

    return {
        "detected_product": product,
        "ingredients": raw_ingredients,
        "risk_tags": risks + allergy_flags + diet_flags,
        "benefit_tags": benefits,
        "analysis": {
            "health_score": {"score": health_score, "out_of": 100, "explanation": "Score computed from detected risks, allergies and diet compatibility."},
            "verdict": verdict,
            "verdict_explanation": verdict_expl,
            "reasons": risks + allergy_flags + diet_flags
        },
        "personalization": {
            "bmi": bmi,
            "bmi_category": bmi_cat,
            "personalized_limits": {"age": user_profile.get("age"), "diet": user_profile.get("diet"), "allergies": user_profile.get("allergies")}
        },
        "consumption_advice": consumption_advice,
        "ocr_preview": ocr_preview 
    }


@app.post("/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    gender: str = Form("Unspecified"),
    age: int = Form(30),
    weight: float = Form(65.0),
    height: float = Form(165.0),
    diet: str = Form("No restrictions"),
    allergies: str = Form("")
):
    global last_results
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        text = extract_text(image)
        if not text:
            raise HTTPException(status_code=400, detail="No text found in image")

        user_profile = {
            "gender": gender,
            "age": age,
            "weight": weight,
            "height": height,
            "diet": diet,
            "allergies": [a.strip() for a in allergies.split(",") if a.strip()]
        }

        analysis = analyze_text(text, user_profile)
        last_results = analysis
        return JSONResponse(content=analysis)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/results")
async def get_results():
    return JSONResponse(content=last_results or {"message": "No results yet"})