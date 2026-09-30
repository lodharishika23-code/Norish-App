
import streamlit as st
import sqlite3
import csv
import io
import re
import os
import json
import base64
import urllib.request
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from datetime import date, datetime, timedelta

DB_FILE = "food_calorie_tracker.db"

st.set_page_config(
    page_title="Nourish — Personal Wellness Companion",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# DATABASE
# =========================================================
def db():
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    return con


def setup_database():
    con = db()
    cur = con.cursor()

    # Existing tables are intentionally preserved.
    cur.execute("""CREATE TABLE IF NOT EXISTS foods(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        category TEXT NOT NULL,
        serving_size REAL NOT NULL,
        serving_unit TEXT NOT NULL,
        calories REAL NOT NULL,
        protein REAL NOT NULL,
        carbs REAL NOT NULL,
        fat REAL NOT NULL,
        custom INTEGER NOT NULL DEFAULT 0
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS food_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        food_id INTEGER NOT NULL,
        log_date TEXT NOT NULL,
        meal TEXT NOT NULL,
        quantity REAL NOT NULL,
        unit TEXT NOT NULL,
        calories REAL NOT NULL,
        protein REAL NOT NULL,
        carbs REAL NOT NULL,
        fat REAL NOT NULL
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS goals(
        id INTEGER PRIMARY KEY CHECK(id=1),
        calories REAL NOT NULL DEFAULT 2000,
        protein REAL NOT NULL DEFAULT 75,
        carbs REAL NOT NULL DEFAULT 250,
        fat REAL NOT NULL DEFAULT 65,
        water_ml REAL NOT NULL DEFAULT 2500
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS water_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_date TEXT NOT NULL,
        amount_ml REAL NOT NULL
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS weight_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_date TEXT NOT NULL,
        weight_kg REAL NOT NULL
    )""")

    # New activity table.
    cur.execute("""CREATE TABLE IF NOT EXISTS exercise_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_date TEXT NOT NULL,
        exercise TEXT NOT NULL,
        duration_min REAL NOT NULL,
        intensity TEXT NOT NULL,
        distance_km REAL DEFAULT 0,
        sets_reps TEXT DEFAULT '',
        notes TEXT DEFAULT ''
    )""")

    # Last user-reported movement. This is not claimed to be device tracking.
    cur.execute("""CREATE TABLE IF NOT EXISTS movement_log(
        id INTEGER PRIMARY KEY CHECK(id=1),
        last_movement TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS user_profile(
        id INTEGER PRIMARY KEY CHECK(id=1),
        goal TEXT NOT NULL DEFAULT 'Build healthier eating habits',
        age INTEGER NOT NULL DEFAULT 25,
        gender TEXT NOT NULL DEFAULT 'Prefer not to say',
        height_cm REAL NOT NULL DEFAULT 165,
        weight_kg REAL NOT NULL DEFAULT 60,
        activity_level TEXT NOT NULL DEFAULT 'Lightly active',
        food_preference TEXT NOT NULL DEFAULT 'Vegetarian',
        onboarding_complete INTEGER NOT NULL DEFAULT 0
    )""")

    if cur.execute("SELECT COUNT(*) FROM foods").fetchone()[0] == 0:
        foods = [
            ("Rice","Grains",100,"g",130,2.7,28.2,0.3),
            ("Roti","Indian",1,"piece",100,3.0,18.0,2.5),
            ("Chapati","Indian",1,"piece",110,3.5,18.0,3.0),
            ("Paratha","Indian",1,"piece",180,4.0,25.0,7.0),
            ("Aloo Paratha","Indian",1,"piece",220,5.0,30.0,9.0),
            ("Dal","Indian",100,"g",116,9.0,20.0,0.4),
            ("Rajma","Indian",100,"g",127,8.7,22.8,0.5),
            ("Chole","Indian",100,"g",164,8.9,27.4,2.6),
            ("Paneer","Dairy",100,"g",265,18.3,6.1,20.8),
            ("Curd","Dairy",100,"g",61,3.5,4.7,3.3),
            ("Milk","Dairy",100,"ml",61,3.2,4.8,3.3),
            ("Egg","Protein",1,"piece",78,6.3,0.6,5.3),
            ("Chicken Breast","Protein",100,"g",165,31,0,3.6),
            ("Fish","Protein",100,"g",150,26,0,5),
            ("Banana","Fruit",1,"piece",105,1.3,27,0.4),
            ("Apple","Fruit",1,"piece",95,0.5,25,0.3),
            ("Orange","Fruit",1,"piece",62,1.2,15.4,0.2),
            ("Mango","Fruit",100,"g",60,0.8,15,0.4),
            ("Guava","Fruit",100,"g",68,2.6,14.3,1),
            ("Papaya","Fruit",100,"g",43,0.5,11,0.3),
            ("Potato","Vegetable",100,"g",87,1.9,20.1,0.1),
            ("Tomato","Vegetable",100,"g",18,0.9,3.9,0.2),
            ("Cucumber","Vegetable",100,"g",15,0.7,3.6,0.1),
            ("Carrot","Vegetable",100,"g",41,0.9,9.6,0.2),
            ("Spinach","Vegetable",100,"g",23,2.9,3.6,0.4),
            ("Oats","Grains",100,"g",389,16.9,66.3,6.9),
            ("Poha","Indian",100,"g",180,3.5,30,5),
            ("Upma","Indian",100,"g",150,3.5,25,4),
            ("Idli","Indian",1,"piece",58,2,12,0.4),
            ("Dosa","Indian",1,"piece",168,3.9,29,3.7),
            ("Samosa","Snacks",1,"piece",260,5,30,14),
            ("Pakora","Snacks",100,"g",290,7,25,18),
            ("Biscuit","Snacks",1,"piece",50,0.6,7,2.2),
            ("Peanuts","Nuts",100,"g",567,25.8,16.1,49.2),
            ("Almonds","Nuts",100,"g",579,21.2,21.6,49.9),
            ("Biryani","Indian",100,"g",200,7,28,6),
            ("Pulao","Indian",100,"g",170,4,27,5),
            ("Vegetable Curry","Indian",100,"g",120,3,12,6),
            ("Chicken Curry","Indian",100,"g",190,15,6,12),
            ("Tea with Milk","Drinks",100,"ml",45,1.5,5,2),
            ("Lassi","Drinks",100,"ml",70,3,9,2.5),
            ("Coconut Water","Drinks",100,"ml",19,0.7,3.7,0.2),
        ]
        cur.executemany("""INSERT INTO foods
            (name,category,serving_size,serving_unit,calories,protein,carbs,fat)
            VALUES(?,?,?,?,?,?,?,?)""", foods)

    if cur.execute("SELECT COUNT(*) FROM goals").fetchone()[0] == 0:
        cur.execute("""INSERT INTO goals(id,calories,protein,carbs,fat,water_ml)
                       VALUES(1,2000,75,250,65,2500)""")

    if cur.execute("SELECT COUNT(*) FROM movement_log").fetchone()[0] == 0:
        cur.execute("INSERT INTO movement_log(id,last_movement) VALUES(1,?)",
                    (datetime.now().isoformat(timespec="minutes"),))

    con.commit()
    con.close()


def foods(search=""):
    con = db()
    if search.strip():
        rows = con.execute(
            "SELECT * FROM foods WHERE name LIKE ? ORDER BY name",
            (f"%{search.strip()}%",)
        ).fetchall()
    else:
        rows = con.execute("SELECT * FROM foods ORDER BY name").fetchall()
    con.close()
    return [dict(r) for r in rows]


def preference_allows_food(food_name, preference):
    """Return whether a food is compatible with the questionnaire preference."""
    name = str(food_name).strip().lower()
    pref = str(preference or "Vegetarian").strip().lower()

    meat_terms = {
        "chicken", "mutton", "lamb", "goat", "fish", "prawn", "prawns",
        "shrimp", "crab", "pork", "beef", "buffalo", "turkey", "meat",
        "keema", "kebab", "kabab", "salami", "sausage", "ham", "bacon",
        "seafood", "anchovy", "tuna", "sardine", "rohu", "pomfret"
    }
    egg_terms = {"egg", "eggs", "omelette", "omelet", "boiled egg", "egg curry", "anda"}
    dairy_terms = {
        "milk", "curd", "dahi", "yogurt", "yoghurt", "paneer", "cheese",
        "ghee", "butter", "cream", "lassi", "kheer", "ice cream"
    }

    has_meat = any(term in name for term in meat_terms)
    has_egg = any(term in name for term in egg_terms)
    has_dairy = any(term in name for term in dairy_terms)

    if pref == "vegan":
        return not (has_meat or has_egg or has_dairy)
    if pref == "vegetarian":
        return not (has_meat or has_egg)
    if pref == "eggetarian":
        return not has_meat
    return True


def preference_allowed_foods(preference):
    return [f for f in foods() if preference_allows_food(f["name"], preference)]


def recognize_meal_with_vision(uploaded_file, preference):
    """Identify visible foods and portions using an optional OpenAI vision API."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return {"status": "unavailable", "message": "AI photo recognition is not configured. Add OPENAI_API_KEY to enable automatic detection."}

    model = os.getenv("OPENAI_VISION_MODEL", "gpt-4.1-mini")
    raw = uploaded_file.getvalue()
    mime = getattr(uploaded_file, "type", None) or "image/jpeg"
    image_b64 = base64.b64encode(raw).decode("utf-8")

    prompt = f"""
You are a careful food-photo recognition assistant for a calorie tracker.
User food preference: {preference}.

Identify ONLY foods visibly present in the image. Do not invent foods or hidden ingredients.
Estimate the visible portion. Match the food name as closely as possible to this local database:
{', '.join(f['name'] for f in preference_allowed_foods(preference))}

Preference rule: Vegetarian excludes meat, fish, poultry and eggs; Eggetarian excludes meat,
fish and poultry but allows eggs; Vegan excludes meat, fish, poultry, eggs and dairy.
Silently omit foods incompatible with the preference.

Return ONLY valid JSON:
{{
  "foods": [
    {{"name":"exact database food name when possible", "estimated_quantity": number, "unit":"g|ml|piece|slice|cup|bowl|serving", "confidence": number}}
  ],
  "notes":"brief uncertainty note"
}}
"""

    payload = {
        "model": model,
        "input": [{"role": "user", "content": [
            {"type": "input_text", "text": prompt},
            {"type": "input_image", "image_url": f"data:{mime};base64,{image_b64}"}
        ]}],
        "temperature": 0.1,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"status": "error", "message": f"Photo recognition failed: {exc}"}

    text = data.get("output_text", "").strip()
    if not text:
        chunks = []
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    chunks.append(content["text"])
        text = "\n".join(chunks).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {"status": "error", "message": "The vision service returned an unreadable result. Please try a clearer photo."}

    allowed_names = {f["name"].lower(): f for f in preference_allowed_foods(preference)}
    foods_out = []
    for item in parsed.get("foods", []):
        name = str(item.get("name", "")).strip()
        match = allowed_names.get(name.lower())
        if not match:
            continue
        try:
            qty = max(0.01, float(item.get("estimated_quantity", match["serving_size"])))
        except (TypeError, ValueError):
            qty = float(match["serving_size"])
        try:
            confidence = max(0.0, min(1.0, float(item.get("confidence", 0.5))))
        except (TypeError, ValueError):
            confidence = 0.5
        foods_out.append({
            "food_id": match["id"],
            "name": match["name"],
            "estimated_quantity": qty,
            "confidence": confidence,
        })
    return {"status": "ok", "foods": foods_out, "notes": str(parsed.get("notes", ""))}


def food_by_id(fid):
    con = db()
    r = con.execute("SELECT * FROM foods WHERE id=?", (fid,)).fetchone()
    con.close()
    return dict(r) if r else None


def food_quantity_input(label, food, default_value, key):
    """Fully customizable quantity input with no artificial upper limit."""
    return st.number_input(
        label,
        min_value=0.01,
        value=max(0.01, float(default_value)),
        step=0.1,
        format="%.2f",
        key=key,
    )


def nutrition(food, quantity):
    m = quantity / food["serving_size"]
    return {
        "calories": food["calories"] * m,
        "protein": food["protein"] * m,
        "carbs": food["carbs"] * m,
        "fat": food["fat"] * m,
    }


def add_custom_food(name, category, serving_size, serving_unit, calories, protein, carbs, fat):
    con = db()
    try:
        con.execute("""INSERT INTO foods
            (name,category,serving_size,serving_unit,calories,protein,carbs,fat,custom)
            VALUES(?,?,?,?,?,?,?,?,1)""",
            (name.strip(), category, serving_size, serving_unit, calories, protein, carbs, fat))
        con.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        con.close()


def add_food_log(fid, d, meal, quantity):
    f = food_by_id(fid)
    n = nutrition(f, quantity)
    con = db()
    con.execute("""INSERT INTO food_log
        (food_id,log_date,meal,quantity,unit,calories,protein,carbs,fat)
        VALUES(?,?,?,?,?,?,?,?,?)""",
        (fid,d,meal,quantity,f["serving_unit"],
         n["calories"],n["protein"],n["carbs"],n["fat"]))
    con.commit()
    con.close()


def get_food_logs(d):
    con = db()
    rows = con.execute("""SELECT food_log.*, foods.name AS food_name
                          FROM food_log JOIN foods ON foods.id=food_log.food_id
                          WHERE log_date=? ORDER BY id DESC""",(d,)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def delete_food_log(row_id):
    con = db()
    con.execute("DELETE FROM food_log WHERE id=?", (row_id,))
    con.commit()
    con.close()


def get_goals():
    con = db()
    r = con.execute("SELECT * FROM goals WHERE id=1").fetchone()
    con.close()
    return dict(r)


def save_goals(cals, protein, carbs, fat, water):
    con = db()
    con.execute("""UPDATE goals SET calories=?,protein=?,carbs=?,fat=?,water_ml=?
                   WHERE id=1""",(cals,protein,carbs,fat,water))
    con.commit()
    con.close()


def get_profile():
    con=db(); r=con.execute("SELECT * FROM user_profile WHERE id=1").fetchone(); con.close()
    return dict(r) if r else None

def save_profile(goal, age, gender, height_cm, weight_kg, activity_level, food_preference):
    con=db()
    con.execute("""INSERT INTO user_profile(id,goal,age,gender,height_cm,weight_kg,activity_level,food_preference,onboarding_complete)
                   VALUES(1,?,?,?,?,?,?,?,1) ON CONFLICT(id) DO UPDATE SET goal=excluded.goal, age=excluded.age, gender=excluded.gender, height_cm=excluded.height_cm, weight_kg=excluded.weight_kg, activity_level=excluded.activity_level, food_preference=excluded.food_preference, onboarding_complete=1""",(goal,age,gender,height_cm,weight_kg,activity_level,food_preference))
    con.commit(); con.close()

def calculate_starting_goals(p):
    age=float(p["age"]); w=float(p["weight_kg"]); h=float(p["height_cm"]); g=p["gender"]
    bmr=10*w+6.25*h-5*age+(5 if g=="Male" else -161 if g=="Female" else -78)
    factor={"Mostly sitting":1.20,"Lightly active":1.375,"Moderately active":1.55,"Very active":1.725}.get(p["activity_level"],1.375)
    calories=bmr*factor + (-300 if p["goal"]=="Lose weight" else 250 if p["goal"]=="Gain weight" else 0)
    calories=max(1400,round(calories/50)*50)
    protein=max(50,round(w*(1.4 if p["goal"]=="Gain weight" else 1.2)))
    fat=max(40,round(calories*.27/9)); carbs=max(80,round((calories-protein*4-fat*9)/4)); water=max(1500,round(w*35/250)*250)
    return {"calories":calories,"protein":protein,"carbs":carbs,"fat":fat,"water":water}


def water_total(d):
    con = db()
    v = con.execute("SELECT COALESCE(SUM(amount_ml),0) FROM water_log WHERE log_date=?",(d,)).fetchone()[0]
    con.close()
    return float(v)


def add_water(d, ml):
    con = db()
    con.execute("INSERT INTO water_log(log_date,amount_ml) VALUES(?,?)",(d,ml))
    con.commit()
    con.close()


def add_weight(d, kg):
    con = db()
    con.execute("INSERT INTO weight_log(log_date,weight_kg) VALUES(?,?)",(d,kg))
    con.commit()
    con.close()


def weights():
    con = db()
    rows = con.execute("SELECT * FROM weight_log ORDER BY log_date").fetchall()
    con.close()
    return [dict(r) for r in rows]


def add_exercise(d, exercise, duration, intensity, distance=0, sets_reps="", notes=""):
    con = db()
    con.execute("""INSERT INTO exercise_log
        (log_date,exercise,duration_min,intensity,distance_km,sets_reps,notes)
        VALUES(?,?,?,?,?,?,?)""",
        (d,exercise,duration,intensity,distance,sets_reps,notes))
    con.execute("UPDATE movement_log SET last_movement=? WHERE id=1",
                (datetime.now().isoformat(timespec="minutes"),))
    con.commit()
    con.close()


def exercises(d):
    con = db()
    rows = con.execute("SELECT * FROM exercise_log WHERE log_date=? ORDER BY id DESC",(d,)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def exercise_calories(exercise, duration_min, intensity, weight_kg):
    """Estimate exercise calories using a simple MET-based calculation."""
    mets = {
        "Walking": 3.5, "Running": 8.3, "Cycling": 7.5, "Gym": 5.0,
        "Strength training": 5.0, "Yoga": 2.5, "Swimming": 7.0,
        "Sports": 7.0, "Dancing": 5.5, "Home workout": 6.0,
        "Stretching": 2.3, "Custom": 5.0,
    }
    factor = {"Easy": 0.85, "Moderate": 1.0, "Hard": 1.15, "Very hard": 1.3}
    met = mets.get(exercise, 5.0) * factor.get(intensity, 1.0)
    return max(0.0, met * 3.5 * float(weight_kg) / 200.0 * float(duration_min))


def exercise_burn(d):
    p = get_profile() or {"weight_kg": 60}
    return sum(exercise_calories(x["exercise"], x["duration_min"], x["intensity"], p["weight_kg"]) for x in exercises(d))


def daily_balance(d):
    food = totals(d)["calories"]
    burned = exercise_burn(d)
    return {"food": food, "exercise_burn": burned, "net": food - burned}


def last_movement():
    con = db()
    r = con.execute("SELECT last_movement FROM movement_log WHERE id=1").fetchone()
    con.close()
    return r[0] if r else None


def set_movement_now():
    con = db()
    con.execute("UPDATE movement_log SET last_movement=? WHERE id=1",
                (datetime.now().isoformat(timespec="minutes"),))
    con.commit()
    con.close()


def sitting_minutes():
    lm=last_movement()
    if not lm: return None
    try: return max(0,(datetime.now()-datetime.fromisoformat(lm)).total_seconds()/60)
    except Exception: return None


# =========================================================
# SIMPLE INTELLIGENCE
# =========================================================
def totals(d):
    logs = get_food_logs(d)
    return {
        "calories": sum(x["calories"] for x in logs),
        "protein": sum(x["protein"] for x in logs),
        "carbs": sum(x["carbs"] for x in logs),
        "fat": sum(x["fat"] for x in logs),
    }


def meal_quality(d, goals, water):
    t = totals(d)
    score = 0
    score += min(t["protein"] / max(goals["protein"],1), 1) * 30
    score += min(water / max(goals["water_ml"],1), 1) * 20
    score += min(len(get_food_logs(d)) / 3, 1) * 15
    score += 15 if any(x["food_name"].lower() in
                        {"spinach","broccoli","carrot","tomato","cucumber","guava","papaya","orange","apple"}
                        for x in get_food_logs(d)) else 0
    calorie_ratio = t["calories"] / max(goals["calories"],1)
    score += 20 if 0.8 <= calorie_ratio <= 1.05 else 10 if calorie_ratio <= 1.2 else 5
    return int(max(0,min(100,score)))




def parse_food_text(text):
    """
    Lightweight offline parser. It uses the local Indian-food database.
    It does not pretend to be AI: unmatched foods are left for the user to choose.
    """
    text = text.lower().strip()
    found = []
    for f in foods():
        name = f["name"].lower()
        aliases = {
            "roti": ["roti","chapati"],
            "curd": ["curd","dahi","yogurt"],
            "dal": ["dal","daal"],
            "chole": ["chole","chana"],
            "rajma": ["rajma"],
            "aloo paratha": ["aloo paratha","aloo paratha"],
            "paneer": ["paneer"],
            "poha": ["poha"],
            "upma": ["upma"],
            "idli": ["idli"],
            "dosa": ["dosa"],
        }.get(name,[name])
        if any(a in text for a in aliases):
            qty = 1.0
            m = re.search(r"(\d+(?:\.\d+)?)\s*(?:x\s*)?" + re.escape(aliases[0]), text)
            if m:
                qty = float(m.group(1))
            found.append((f, qty))
    unique = {}
    for f,q in found:
        unique[f["id"]] = (f,q)
    return list(unique.values())


def ideal_diet_plan(d, goals, profile):
    pref=profile["food_preference"]; remaining=max(goals["calories"]-totals(d)["calories"],0)
    if pref=="Vegan": meals=[("🌅 Breakfast","Oats + banana + peanuts",420,13),("☀️ Lunch","2 roti + rajma + vegetables",520,20),("🍎 Snack","Fruit + peanuts",220,7),("🌙 Dinner","Rice + chole + vegetables",520,18)]
    elif pref=="Vegetarian": meals=[("🌅 Breakfast","Poha + curd + fruit",380,12),("☀️ Lunch","2 roti + dal + vegetables + curd",520,24),("🍎 Snack","Fruit + almonds",220,6),("🌙 Dinner","2 roti + paneer + vegetables",560,28)]
    elif pref=="Eggetarian": meals=[("🌅 Breakfast","2 eggs + 2 roti + fruit",430,20),("☀️ Lunch","2 roti + dal + vegetables + curd",520,24),("🍎 Snack","Fruit + curd",180,8),("🌙 Dinner","Egg curry + roti + vegetables",520,24)]
    else: meals=[("🌅 Breakfast","2 eggs + 2 roti + fruit",430,20),("☀️ Lunch","Chicken curry + 2 roti + vegetables",560,30),("🍎 Snack","Fruit + curd",180,8),("🌙 Dinner","Fish + rice + vegetables",520,30)]
    return [("🍽️ Next meal","Choose a light, balanced portion that fits your hunger.",250,10)] if remaining<350 else meals[-2:] if remaining<700 else meals

def recommendation_meals(d, goals):
    p=get_profile() or {"food_preference":"Vegetarian"}
    return ideal_diet_plan(d,goals,p)


def weekly_stats(end_date):
    days = []
    for i in range(6,-1,-1):
        d = (end_date - timedelta(days=i)).isoformat()
        t = totals(d)
        ex = exercises(d)
        burn = exercise_burn(d)
        days.append({
            "date":d,
            "calories":t["calories"],
            "protein":t["protein"],
            "exercise_min":sum(x["duration_min"] for x in ex),
            "exercise_burn":burn,
            "net_calories":t["calories"]-burn,
            "logged":bool(get_food_logs(d)),
        })
    return days


def food_report_csv(d=None):
    con = db()
    if d:
        rows = con.execute("""SELECT food_log.*, foods.name AS food_name
                             FROM food_log JOIN foods ON foods.id=food_log.food_id
                             WHERE log_date=? ORDER BY id""", (d,)).fetchall()
    else:
        rows = con.execute("""SELECT food_log.*, foods.name AS food_name
                             FROM food_log JOIN foods ON foods.id=food_log.food_id
                             ORDER BY log_date, id""").fetchall()
    con.close()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Date","Food","Meal","Quantity","Unit","Calories","Protein","Carbs","Fat"])
    for r in rows:
        writer.writerow([r["log_date"],r["food_name"],r["meal"],r["quantity"],r["unit"],
                         round(r["calories"],2),round(r["protein"],2),round(r["carbs"],2),round(r["fat"],2)])
    return out.getvalue().encode("utf-8")


def report_rows(start_date, end_date):
    rows = []
    cur = start_date
    while cur <= end_date:
        ds = cur.isoformat()
        t = totals(ds)
        burn = exercise_burn(ds)
        rows.append({
            "Date": ds,
            "Food Calories": round(t["calories"], 2),
            "Exercise Burn": round(burn, 2),
            "Net Calories": round(t["calories"] - burn, 2),
            "Protein (g)": round(t["protein"], 2),
            "Carbs (g)": round(t["carbs"], 2),
            "Fat (g)": round(t["fat"], 2),
            "Water (ml)": round(water_total(ds), 2),
            "Exercise (min)": round(sum(x["duration_min"] for x in exercises(ds)), 2),
        })
        cur += timedelta(days=1)
    return rows


def report_csv(start_date, end_date):
    rows = report_rows(start_date, end_date)
    out = io.StringIO()
    fields = list(rows[0].keys()) if rows else ["Date"]
    writer = csv.DictWriter(out, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode("utf-8")


def report_pdf(start_date, end_date, title):
    rows = report_rows(start_date, end_date)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=28, leftMargin=28, topMargin=28, bottomMargin=28)
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles["Title"]), Spacer(1, 10)]
    if rows:
        headers = list(rows[0].keys())
        data = [headers] + [[r[h] for h in headers] for r in rows]
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#eaf5ee")),
            ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 7),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("ALIGN", (1,1), (-1,-1), "RIGHT"),
        ]))
        story.append(table)
        story.append(Spacer(1, 10))
        total_food = sum(r["Food Calories"] for r in rows)
        total_burn = sum(r["Exercise Burn"] for r in rows)
        story.append(Paragraph(
            f"Total food calories: {total_food:.0f} kcal | Exercise burn: {total_burn:.0f} kcal | Net calories: {total_food-total_burn:.0f} kcal",
            styles["BodyText"]
        ))
    else:
        story.append(Paragraph("No data recorded for this period.", styles["BodyText"]))
    doc.build(story)
    return buf.getvalue()


# =========================================================
# UI
# =========================================================
setup_database()
goals = get_goals()
profile = get_profile()

if not profile or not profile.get("onboarding_complete"):
    st.markdown("""<div class="hero"><h1 style="margin:0;">Welcome to Nourish 🌿</h1><p style="margin:.35rem 0 0;">A few quick questions will personalize your starting goals and suggestions.</p></div>""", unsafe_allow_html=True)
    st.subheader("Let's set up your starting point")
    st.caption("About a minute. You can change these details later from Goals.")
    with st.form("first_time_questionnaire"):
        q1=st.selectbox("1. What is your main goal?",["Maintain weight","Lose weight","Gain weight","Build healthier eating habits"])
        q2=st.number_input("2. What is your age?",min_value=13,max_value=100,value=25,step=1)
        q3=st.selectbox("3. What is your Gender?",["Female","Male","Prefer not to say"])
        unit=st.radio("4. What is your height?",["cm","ft & inches"],horizontal=True)
        if unit=="cm": q4=st.number_input("Height (cm)",min_value=100.0,max_value=230.0,value=165.0,step=1.0)
        else:
            c1,c2=st.columns(2)
            with c1: ft=st.number_input("Feet",min_value=3,max_value=7,value=5,step=1)
            with c2: inch=st.number_input("Inches",min_value=0,max_value=11,value=5,step=1)
            q4=ft*30.48+inch*2.54
        q5=st.number_input("5. What is your current weight (kg)?",min_value=30.0,max_value=300.0,value=60.0,step=.1)
        q6=st.selectbox("6. How active are you usually?",["Mostly sitting","Lightly active","Moderately active","Very active"])
        q7=st.selectbox("7. What is your food preference?",["Vegetarian","Eggetarian","Non-vegetarian","Vegan"])
        submitted=st.form_submit_button("🌿 Create my starting plan",type="primary",use_container_width=True)
    if submitted:
        save_profile(q1,int(q2),q3,float(q4),float(q5),q6,q7)
        profile=get_profile(); sg=calculate_starting_goals(profile)
        save_goals(sg["calories"],sg["protein"],sg["carbs"],sg["fat"],sg["water"])
        st.success("Your starting plan is ready."); st.rerun()
    st.caption("Starting targets are estimates for general wellness tracking, not medical advice.")
    st.stop()

if "tracking_date" not in st.session_state:
    st.session_state.tracking_date = date.today()

st.markdown("""
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1250px;}
[data-testid="stMetric"] {background:#f7faf8; padding:12px; border-radius:14px;}
.small-muted {color:#6b7280; font-size:0.9rem;}
.hero {padding:1.2rem 1.4rem; border-radius:20px; background:linear-gradient(135deg,#eef8f1,#f8fbf9); margin-bottom:1rem;}
.card {padding:1rem; border:1px solid #e5e7eb; border-radius:16px; background:white;}
</style>
""", unsafe_allow_html=True)

# Sidebar intentionally contains only five destinations.
st.sidebar.title("🌿 Nourish")
st.sidebar.caption("Track less. Understand more.")

page = st.sidebar.radio(
    "Go to",
    ["🏠 Home","🍽️ Food","🏃 Activity","📊 Insights","🎯 Goals"],
    label_visibility="collapsed"
)

new_date = st.sidebar.date_input("Tracking date", st.session_state.tracking_date)
if new_date != st.session_state.tracking_date:
    st.session_state.tracking_date = new_date
    st.rerun()

d = st.session_state.tracking_date.isoformat()
t = totals(d)
water = water_total(d)
today_ex = exercises(d)

# =========================================================
# HOME
# =========================================================
if page == "🏠 Home":
    st.markdown(f"""
    <div class="hero">
      <h1 style="margin:0;">Good {('morning' if datetime.now().hour < 12 else 'afternoon' if datetime.now().hour < 18 else 'evening')} 👋</h1>
      <p style="margin:.35rem 0 0;">Here's your day at a glance — no pressure, just useful guidance.</p>
    </div>
    """, unsafe_allow_html=True)

    action_title, action_text = next_action(d, goals)
    a,b,c,dcol = st.columns(4)
    a.metric("🍽️ Food", f"{t['calories']:.0f} kcal", f"{max(goals['calories']-t['calories'],0):.0f} remaining")
    b.metric("💪 Protein", f"{t['protein']:.0f} g", f"{max(goals['protein']-t['protein'],0):.0f} remaining")
    c.metric("💧 Water", f"{water/1000:.1f} L", f"{max(goals['water_ml']-water,0)/1000:.1f} L to goal")
    dcol.metric("🔥 Net calories", f"{daily_balance(d)['net']:.0f} kcal",
                f"{exercise_burn(d):.0f} kcal burned")

    q1,q2 = st.columns(2)
    with q1:
        st.subheader("⚖️ Daily balance")
        st.progress(min(t["calories"]/max(goals["calories"],1),1.0))
        st.caption(f"Food: {t['calories']:.0f} / {goals['calories']:.0f} kcal")
        st.progress(min(water/max(goals["water_ml"],1),1.0))
        st.caption(f"Water: {water:.0f} / {goals['water_ml']:.0f} ml")
        st.write(f"🏃 Activity: **{sum(x['duration_min'] for x in today_ex):.0f} min** • **{exercise_burn(d):.0f} kcal burned**")
        st.write(f"🔥 Net calories: **{daily_balance(d)['net']:.0f} kcal** (food − exercise burn)")
        st.write(f"🌱 Nutrition quality: **{meal_quality(d,goals,water)}/100**")

    with q2:
        st.subheader("🥗 Ideal diet suggestion")
        st.caption(f"Example plan for a {profile['food_preference'].lower()} day. Adjust portions to your hunger and routine.")
        for meal_name, meal_text, kcal, protein in ideal_diet_plan(d,goals,profile):
            st.markdown(f"**{meal_name}**  \n{meal_text}  \n~{kcal} kcal • ~{protein}g protein")

    st.subheader("🪑 Sitting too long?")
    sm=sitting_minutes()
    if sm is not None and sm>=60:
        st.warning(f"It has been about **{sm:.0f} minutes** since your last movement check-in. Try a 5-minute walk, stretch, or easy movement break.")
    elif sm is not None:
        st.success(f"Movement check-in is active — last check-in was about {sm:.0f} minutes ago.")
    if st.button("🚶 I'm moving now",key="home_move_checkin",use_container_width=True):
        set_movement_now(); st.success("Nice! Movement check-in updated."); st.rerun()
    st.caption("This reminder uses in-app movement check-ins; it does not read device sitting sensors.")

    st.subheader("🌿 If today didn't go to plan")
    if t["calories"] > goals["calories"] * 1.1:
        st.success("That's okay. One meal does not define your day. You don't need to skip your next meal — simply return to your normal routine.")
    else:
        st.caption("Consistency matters more than perfection. A normal day is a successful day.")


# =========================================================
# FOOD
# =========================================================
elif page == "🍽️ Food":
    st.title("🍽️ Food")
    tab1, tab2, tab3, tab4 = st.tabs(["Quick log","📸 Meal photo","Today's log","➕ Custom food"])

    with tab1:
        st.caption("Search normally, or describe your meal in one sentence.")
        natural = st.text_input("What did you eat?", placeholder="e.g. 2 roti, dal, sabzi and dahi")
        parsed = parse_food_text(natural) if natural else []

        if parsed:
            st.success(f"I found {len(parsed)} likely food(s). Please confirm the portions.")
            meal = st.selectbox("Meal",["Breakfast","Lunch","Snack","Dinner"])
            for f,q in parsed:
                qty = food_quantity_input(
                    f"{f['name']} ({f['serving_unit']})",
                    f,
                    q,
                    key=f"parsed_{f['id']}",
                )
                n = nutrition(f,qty)
                st.caption(f"~{n['calories']:.0f} kcal • {n['protein']:.1f}g protein")
            if st.button("➕ Add detected foods", type="primary", use_container_width=True):
                for f,q in parsed:
                    qty = st.session_state.get(f"parsed_{f['id']}",q)
                    add_food_log(f["id"],d,meal,qty)
                st.success("Meal added.")
                st.rerun()
        else:
            search = st.text_input("🔎 Search food", placeholder="rice, roti, paneer, poha...")
            fs = foods(search)
            if fs:
                names = [x["name"] for x in fs]
                selected = st.selectbox("Choose food",names)
                f = next(x for x in fs if x["name"]==selected)
                meal = st.selectbox("Meal",["Breakfast","Lunch","Snack","Dinner"])
                default_qty = (
                    1
                    if str(f["serving_unit"]).strip().lower()
                    in {"piece", "pieces", "slice", "slices", "serving", "servings"}
                    else f["serving_size"]
                )
                qty = food_quantity_input(
                    f"Quantity ({f['serving_unit']})",
                    f,
                    default_qty,
                    key=f"food_qty_{f['id']}",
                )
                n = nutrition(f,qty)
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("Calories",f"{n['calories']:.0f}")
                c2.metric("Protein",f"{n['protein']:.1f}g")
                c3.metric("Carbs",f"{n['carbs']:.1f}g")
                c4.metric("Fat",f"{n['fat']:.1f}g")
                if st.button("➕ Add to today",type="primary",use_container_width=True):
                    add_food_log(f["id"],d,meal,qty)
                    st.success("Added.")
                    st.rerun()

    with tab2:
        st.subheader("📸 Meal photo")
        st.caption("Photo recognition is an estimate. Always confirm portions before logging.")
        pref = (profile or {}).get("food_preference", "Vegetarian")
        image = st.file_uploader("Upload a meal photo", type=["png","jpg","jpeg"], key="meal_photo_ai")
        if image:
            st.image(image, use_container_width=True)
            if st.button("🔍 Detect food & estimate portions", type="primary", use_container_width=True):
                with st.spinner("Analysing the meal photo…"):
                    result = recognize_meal_with_vision(image, pref)
                st.session_state["photo_detection"] = result
                st.rerun()

        result = st.session_state.get("photo_detection")
        if result and result.get("status") == "unavailable":
            st.warning(result["message"])
        elif result and result.get("status") == "error":
            st.error(result["message"])
        elif result and result.get("status") == "ok":
            detected = result.get("foods", [])
            selected_rows = []
            total = 0.0
            if detected:
                meal = st.selectbox("Meal for photo", ["Breakfast","Lunch","Snack","Dinner"], key="photo_meal_ai")
                for i, item in enumerate(detected):
                    f = food_by_id(item["food_id"])
                    if not f or not preference_allows_food(f["name"], pref):
                        continue
                    default_qty = float(item["estimated_quantity"])
                    qty = food_quantity_input(
                        f"{f['name']} quantity ({f['serving_unit']})",
                        f,
                        default_qty,
                        key=f"photo_ai_qty_{f['id']}_{i}",
                    )
                    n = nutrition(f, qty)
                    total += n["calories"]
                    selected_rows.append((f, qty))
                    st.caption(f"Detected: {item['name']} • {item['confidence']*100:.0f}% confidence • {n['calories']:.0f} kcal")

                st.metric("Estimated meal calories", f"{total:.0f} kcal")
                st.caption("Calories are calculated from the confirmed quantities and your nutrition database.")
                if st.button("Confirm & log meal", type="primary", use_container_width=True, key="confirm_ai_photo"):
                    for f, qty in selected_rows:
                        add_food_log(f["id"], d, meal, qty)
                    st.success("Photo meal logged.")
                    st.session_state.pop("photo_detection", None)
                    st.rerun()
            else:
                st.info("No loggable foods were detected. Try a clearer photo with the full plate visible.")


    with tab4:
        st.subheader("➕ Add your own food")
        st.caption("Add a food once and it becomes available in Quick log and Smart Indian Food Recognition.")
        name = st.text_input("Food name", placeholder="e.g. Homemade vegetable khichdi")
        category = st.selectbox("Category", ["Indian","Grains","Protein","Dairy","Fruit","Vegetable","Nuts","Snacks","Drinks","Other"])
        c1,c2 = st.columns(2)
        with c1:
            serving_size = st.number_input("Serving size", min_value=0.1, value=100.0, step=0.1)
        with c2:
            serving_unit = st.selectbox("Serving unit", ["g","kg","ml","litre","piece","slice","cup","bowl","serving","tablespoon","teaspoon"])
        c1,c2,c3,c4 = st.columns(4)
        with c1: calories = st.number_input("Calories (kcal)", min_value=0.0, value=100.0, step=1.0)
        with c2: protein = st.number_input("Protein (g)", min_value=0.0, value=5.0, step=0.1)
        with c3: carbs = st.number_input("Carbohydrates (g)", min_value=0.0, value=10.0, step=0.1)
        with c4: fat = st.number_input("Fat (g)", min_value=0.0, value=2.0, step=0.1)
        if st.button("💾 Save custom food", type="primary", use_container_width=True):
            if not name.strip():
                st.error("Please enter a food name.")
            elif add_custom_food(name, category, serving_size, serving_unit, calories, protein, carbs, fat):
                st.success("Food saved. You can now log it from Quick log.")
                st.rerun()
            else:
                st.error("A food with this name already exists.")

    with tab3:
        logs = get_food_logs(d)
        if not logs:
            st.info("Nothing logged yet.")
        else:
            for r in logs:
                c1,c2,c3 = st.columns([3,4,1])
                c1.markdown(f"**{r['food_name']}**  \n{r['meal']} • {r['quantity']:g} {r['unit']}")
                c2.caption(f"{r['calories']:.0f} kcal • P {r['protein']:.1f}g • C {r['carbs']:.1f}g • F {r['fat']:.1f}g")
                if c3.button("🗑️",key=f"del_{r['id']}"):
                    delete_food_log(r["id"])
                    st.rerun()

# =========================================================
# ACTIVITY
# =========================================================
elif page == "🏃 Activity":
    st.title("🏃 Activity")
    st.caption("Food and exercise live together here, but stay clearly separate.")

    food_tab, exercise_tab, balance_tab = st.tabs(["🍽️ Food intake","🏃 Exercise","⚖️ Daily balance"])

    with food_tab:
        st.subheader("🍽️ Food intake")
        st.metric("Today's intake",f"{t['calories']:.0f} kcal",f"{max(goals['calories']-t['calories'],0):.0f} remaining")
        for meal in ["Breakfast","Lunch","Snack","Dinner"]:
            items = [x for x in get_food_logs(d) if x["meal"]==meal]
            if items:
                st.markdown(f"**{meal}**")
                st.write(" • ".join(f"{x['food_name']} ({x['calories']:.0f} kcal)" for x in items))

    with exercise_tab:
        st.subheader("Log movement in seconds")
        ex_name = st.selectbox("Exercise",[
            "Walking","Running","Cycling","Gym","Strength training",
            "Yoga","Swimming","Sports","Dancing","Home workout","Stretching","Custom"
        ])
        duration = st.number_input(
            "Duration (minutes)",
            min_value=1,
            value=20,
            step=1,
            format="%d",
        )
        intensity = st.select_slider("How hard?",options=["Easy","Moderate","Hard","Very hard"],value="Moderate")
        distance = st.number_input("Distance (km, optional)",min_value=0.0,value=0.0,step=.5)
        sets = st.text_input("Sets/reps (optional)",placeholder="e.g. 3 x 10")
        notes = st.text_input("Note (optional)")
        if st.button("➕ Log exercise",type="primary",use_container_width=True):
            add_exercise(d,ex_name,duration,intensity,distance,sets,notes)
            st.success("Movement logged.")
            st.rerun()

        st.divider()
        st.subheader("🪑 Sitting check-in")
        sm=sitting_minutes()
        if sm is not None and sm>=60: st.warning(f"You have been inactive for about **{sm:.0f} minutes**. A 5-minute movement break is enough to get started.")
        elif sm is not None: st.info(f"Last movement check-in: about {sm:.0f} minutes ago.")
        if st.button("🚶 I'm moving now",key="activity_move_checkin"):
            set_movement_now(); st.success("Movement check-in updated."); st.rerun()

        st.divider()
        st.subheader("✨ Move more")
        st.write("Choose what fits your day — movement is valuable even when it isn't about calories.")
        m1,m2,m3 = st.columns(3)
        m1.info("🚶 20 min brisk walk")
        m2.info("🧘 15 min mobility")
        m3.info("🏠 10 min home workout")

        st.subheader("Today's exercise")
        if today_ex:
            for x in today_ex:
                st.write(f"**{x['exercise']}** — {x['duration_min']:.0f} min • {x['intensity']}")
        else:
            st.caption("No exercise logged today.")

        st.divider()
        st.subheader("🍽️ + 🏃 After-workout nudge")
        if today_ex:
            st.info("After activity, consider some water and a balanced meal or protein-rich snack if you're hungry. You do not need to 'earn' food with exercise.")
        else:
            st.caption("After your next workout, you'll get a small recovery suggestion here.")

    with balance_tab:
        st.subheader("⚖️ Today's balance")
        a,b,c,dcol = st.columns(4)
        a.metric("Food",f"{t['calories']:.0f} kcal")
        b.metric("Exercise burn",f"{exercise_burn(d):.0f} kcal")
        c.metric("Net calories",f"{daily_balance(d)['net']:.0f} kcal")
        dcol.metric("Water",f"{water/1000:.1f} L")
        st.progress(min(t["calories"]/max(goals["calories"],1),1))
        st.caption(f"Food: {t['calories']:.0f}/{goals['calories']:.0f} kcal")
        st.progress(min(water/max(goals["water_ml"],1),1))
        st.caption(f"Water: {water:.0f}/{goals['water_ml']:.0f} ml")
        st.success("Food and exercise are shown together for context — not as 'calories earned' or 'calories to burn'.")

# =========================================================
# INSIGHTS
# =========================================================
elif page == "📊 Insights":
    st.title("📊 Insights")
    st.caption("Understand patterns without drowning in charts.")

    tab_week, tab_report = st.tabs(["Your week","Reports"])

    with tab_week:
        days = weekly_stats(st.session_state.tracking_date)
        logged = sum(x["logged"] for x in days)
        active = sum(x["exercise_min"] > 0 for x in days)
        avg_cal = sum(x["calories"] for x in days)/7
        avg_pro = sum(x["protein"] for x in days)/7
        total_ex = sum(x["exercise_min"] for x in days)

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Food logged",f"{logged}/7")
        c2.metric("Active days",f"{active}/7")
        c3.metric("Avg net calories",f"{sum(x['net_calories'] for x in days)/7:.0f}")
        c4.metric("Exercise",f"{total_ex:.0f} min")

        st.subheader("🟢 What went well")
        wins = []
        if logged >= 5: wins.append(f"Food was logged on {logged} of 7 days.")
        if active >= 3: wins.append(f"You moved on {active} of 7 days.")
        if avg_pro >= goals["protein"]*.8: wins.append("Your average protein intake was close to your target.")
        if not wins: wins.append("You started collecting useful data — keep going.")
        for x in wins: st.write("• "+x)

        st.subheader("💡 Pattern noticed")
        weekend = [x["calories"] for x in days[-2:] if x["calories"]>0]
        weekday = [x["calories"] for x in days[:5] if x["calories"]>0]
        if weekend and weekday and sum(weekend)/len(weekend) > sum(weekday)/len(weekday)*1.15:
            st.info("Your recent weekend intake is higher than your weekday intake. If that feels relevant, plan one enjoyable meal rather than trying to be perfect.")
        elif active >= 1 and active < 4:
            st.info("You have some movement logged. A few short sessions spread through the week can make activity easier to maintain.")
        else:
            st.info("Keep collecting data. The app will become more useful as it learns your routine.")

        st.subheader("🎯 One focus for next week")
        if avg_pro < goals["protein"]*.8:
            st.write("Add one simple protein-rich food to a meal you already eat.")
        elif active < 3:
            st.write("Aim for one short movement session on three days.")
        elif water < goals["water_ml"]:
            st.write("Keep a water bottle nearby and add one extra glass.")
        else:
            st.write("Keep your routine steady rather than adding more rules.")

    with tab_report:
        st.subheader("📄 Reports")
        report_type = st.radio("Report period", ["Daily report", "Weekly report"], horizontal=True)

        if report_type == "Daily report":
            report_start = st.session_state.tracking_date
            report_end = report_start
            report_title = f"Daily Wellness Report — {report_start.isoformat()}"
            filename_base = f"daily_wellness_report_{report_start.isoformat()}"
        else:
            report_end = st.session_state.tracking_date
            report_start = report_end - timedelta(days=6)
            report_title = f"Weekly Wellness Report — {report_start.isoformat()} to {report_end.isoformat()}"
            filename_base = f"weekly_wellness_report_{report_start.isoformat()}_{report_end.isoformat()}"

        rows = report_rows(report_start, report_end)
        st.caption(f"{report_start.isoformat()} to {report_end.isoformat()}")
        st.dataframe(rows, use_container_width=True, hide_index=True)
        total_food = sum(r["Food Calories"] for r in rows)
        total_burn = sum(r["Exercise Burn"] for r in rows)
        total_net = sum(r["Net Calories"] for r in rows)
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Food intake", f"{total_food:.0f} kcal")
        c2.metric("Exercise burn", f"{total_burn:.0f} kcal")
        c3.metric("Net calories", f"{total_net:.0f} kcal")
        c4.metric("Water", f"{sum(r['Water (ml)'] for r in rows)/1000:.2f} L")

        c1,c2 = st.columns(2)
        with c1:
            st.download_button("⬇️ Download CSV", data=report_csv(report_start, report_end),
                               file_name=filename_base + ".csv", mime="text/csv", use_container_width=True)
        with c2:
            st.download_button("⬇️ Download PDF", data=report_pdf(report_start, report_end, report_title),
                               file_name=filename_base + ".pdf", mime="application/pdf", use_container_width=True)


# =========================================================
# GOALS
# =========================================================
elif page == "🎯 Goals":
    st.title("🎯 Goals")
    st.caption("Keep goals simple. They should guide you, not control your day.")
    with st.expander("👤 Your profile & preferences"):
        choices=["Maintain weight","Lose weight","Gain weight","Build healthier eating habits"]
        pgoal=st.selectbox("Main goal",choices,index=choices.index(profile["goal"]))
        page=st.number_input("Age",min_value=13,max_value=100,value=int(profile["age"]),step=1)
        genders=["Female","Male","Prefer not to say"]
        pgender=st.selectbox("Gender",genders,index=genders.index(profile["gender"]))
        pheight=st.number_input("Height (cm)",min_value=100.0,max_value=230.0,value=float(profile["height_cm"]),step=1.0)
        pweight=st.number_input("Current weight (kg)",min_value=30.0,max_value=300.0,value=float(profile["weight_kg"]),step=.1)
        acts=["Mostly sitting","Lightly active","Moderately active","Very active"]; pact=st.selectbox("Usual activity",acts,index=acts.index(profile["activity_level"]))
        prefs=["Vegetarian","Eggetarian","Non-vegetarian","Vegan"]; ppref=st.selectbox("Food preference",prefs,index=prefs.index(profile["food_preference"]))
        if st.button("💾 Save profile & update starting goals",use_container_width=True):
            save_profile(pgoal,int(page),pgender,pheight,pweight,pact,ppref); profile=get_profile(); sg=calculate_starting_goals(profile); save_goals(sg["calories"],sg["protein"],sg["carbs"],sg["fat"],sg["water"]); st.success("Profile and starting goals updated."); st.rerun()

    # Automatically calculated targets from the questionnaire (including current weight).
    recommended = calculate_starting_goals(profile)
    st.caption(
        f"Recommended from your questionnaire: {recommended['calories']:.0f} kcal • "
        f"{recommended['protein']:.0f} g protein • {recommended['carbs']:.0f} g carbs per day"
    )

    cals = st.number_input("Daily calories",min_value=500.0,value=float(goals["calories"]),step=50.0)
    protein = st.number_input("Protein (g)",min_value=10.0,value=float(goals["protein"]),step=5.0)
    carbs = st.number_input("Carbohydrates (g)",min_value=20.0,value=float(goals["carbs"]),step=10.0)
    fat = st.number_input("Fat (g)",min_value=10.0,value=float(goals["fat"]),step=5.0)
    water_goal = st.number_input("Water (ml)",min_value=500.0,value=float(goals["water_ml"]),step=250.0)

    if st.button("💾 Save goals",type="primary",use_container_width=True):
        save_goals(cals,protein,carbs,fat,water_goal)
        st.success("Goals updated.")
        st.rerun()

    st.divider()
    st.subheader("💧 Water tracker")
    st.metric("Today's water intake", f"{water:.0f} ml", f"{water/1000:.2f} L")
    x,y,z = st.columns(3)
    if x.button("+250 ml", key="water_250"): add_water(d,250); st.rerun()
    if y.button("+500 ml", key="water_500"): add_water(d,500); st.rerun()
    if z.button("+1 litre", key="water_1000"): add_water(d,1000); st.rerun()
    custom_water = st.number_input("Add custom water amount (ml)", min_value=0.01, value=250.0, step=50.0, key="custom_water")
    if st.button("➕ Add water", key="add_custom_water", use_container_width=True):
        add_water(d, custom_water)
        st.success(f"Added {custom_water:.0f} ml.")
        st.rerun()

    st.subheader("⚖️ Weight")
    weight = st.number_input("Today's weight (kg)",min_value=1.0,max_value=500.0,value=60.0,step=.1)
    if st.button("Save weight"):
        add_weight(d,weight)
        st.success("Weight saved.")

    ws = weights()
    if ws:
        st.subheader("Weight history")
        st.dataframe(ws,use_container_width=True,hide_index=True)

# Footer
st.sidebar.divider()
st.sidebar.caption("🌿 Nourish • estimates are for general tracking and not medical advice.")
