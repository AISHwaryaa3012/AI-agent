# app.py - Final Enhanced Version
from flask import Flask, render_template, request, session, redirect, url_for
import requests
import os
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io
import base64
import openai  # For advanced AI analysis

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or "dev-secret"

# Initialize OpenAI if available
if os.getenv("OPENAI_API_KEY"):
    openai.api_key = os.getenv("OPENAI_API_KEY")

# Nutritionix API Config
NUTRITIONIX_URL = "https://trackapi.nutritionix.com/v2/natural/nutrients"
HEADERS = {
    "x-app-id": os.getenv("NUTRITIONIX_APP_ID"),
    "x-app-key": os.getenv("NUTRITIONIX_APP_KEY"),
    "Content-Type": "application/json"
}

# Common food alternatives for meal suggestions
FOOD_ALTERNATIVES = {
    'protein': ['chicken breast', 'tofu', 'lentils', 'Greek yogurt', 'eggs'],
    'low-cal': ['zucchini noodles', 'cauliflower rice', 'spinach', 'mushrooms'],
    'low-carb': ['avocado', 'nuts', 'cheese', 'salmon', 'olive oil']
}

def init_session():
    if 'nutrition_history' not in session:
        session['nutrition_history'] = []
    if 'goals' not in session:
        session['goals'] = {
            'calories': 2000,
            'protein': 50,
            'carbs': 300,
            'fat': 65,
            'diet_type': 'balanced'  # balanced/low-carb/high-protein
        }
    if 'meal_plan' not in session:
        session['meal_plan'] = []

def get_nutrition(food_name):
    try:
        data = {"query": food_name}
        response = requests.post(NUTRITIONIX_URL, headers=HEADERS, json=data).json()
        
        if response.get('foods'):
            food = response['foods'][0]
            result = {
                "food": food_name,
                "calories": food.get('nf_calories', 0),
                "protein": food.get('nf_protein', 0),
                "fat": food.get('nf_total_fat', 0),
                "carbs": food.get('nf_total_carbohydrate', 0),
                "timestamp": datetime.now().isoformat()
            }
            # Store in history
            session['nutrition_history'].append(result)
            session.modified = True
            return result
    except Exception as e:
        print(f"API Error: {e}")
    return None

def generate_chart():
    """Generate weekly nutrition chart"""
    if not session.get('nutrition_history'):
        return None
    
    # Get last 7 days data
    dates = []
    calories = []
    proteins = []
    
    for i in range(7):
        date = (datetime.now() - timedelta(days=i)).strftime('%a')
        dates.insert(0, date)
        
        day_data = [
            item for item in session['nutrition_history'] 
            if datetime.fromisoformat(item['timestamp']).date() == 
            (datetime.now() - timedelta(days=i)).date()
        ]
        
        calories.insert(0, sum(item['calories'] for item in day_data))
        proteins.insert(0, sum(item['protein'] for item in day_data))
    
    # Create plot
    plt.figure(figsize=(8, 4))
    plt.plot(dates, calories, label='Calories', marker='o')
    plt.plot(dates, proteins, label='Protein (g)', marker='o')
    plt.axhline(y=session['goals']['calories'], color='r', linestyle='--', label='Calorie Goal')
    plt.axhline(y=session['goals']['protein'], color='g', linestyle='--', label='Protein Goal')
    plt.legend()
    plt.title('Weekly Nutrition Trends')
    plt.ylabel('Amount')
    plt.grid(True, alpha=0.3)
    
    # Save to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return base64.b64encode(buf.read()).decode('utf-8')

def generate_ai_insights(current_nutrition):
    """Advanced analysis using OpenAI if available"""
    if not os.getenv("OPENAI_API_KEY"):
        return generate_basic_insights(current_nutrition)
    
    try:
        history = session.get('nutrition_history', [])
        goals = session.get('goals', {})
        
        prompt = f"""
        Analyze this nutrition data for personalized insights:
        
        Current Meal: {current_nutrition}
        Daily Goals: {goals}
        Diet Type: {goals.get('diet_type', 'balanced')}
        Last 5 Meals: {history[-5:] if history else 'No history'}
        
        Provide:
        1. 3 specific food suggestions to improve balance
        2. Comparison with daily goals
        3. Weekly trend analysis
        4. Health impact assessment
        
        Respond in clear bullet points for a health app.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200
        )
        
        return response.choices[0].message['content'].split('\n')
    except Exception as e:
        print(f"OpenAI Error: {e}")
        return generate_basic_insights(current_nutrition)

def generate_basic_insights(current_nutrition):
    """Basic analysis without OpenAI"""
    insights = []
    goals = session.get('goals', {})
    
    # Calorie analysis
    calorie_diff = current_nutrition['calories'] - goals.get('calories', 2000)
    if calorie_diff > 0:
        insights.append(f"⚠️ {calorie_diff} calories over daily goal")
    else:
        insights.append(f"✅ {-calorie_diff} calories under daily goal")
    
    # Macronutrient balance
    protein_ratio = current_nutrition['protein'] / (current_nutrition['carbs'] + 0.1)
    if protein_ratio < 0.3:
        insights.append("🔍 Low protein ratio - consider adding: " + 
                      ", ".join(FOOD_ALTERNATIVES['protein'][:2]))
    
    # Diet-type specific suggestions
    diet_type = goals.get('diet_type', 'balanced')
    if diet_type == 'low-carb' and current_nutrition['carbs'] > 50:
        insights.append("🌱 High carbs for low-carb diet - try: " +
                      ", ".join(FOOD_ALTERNATIVES['low-carb'][:2]))
    
    return insights

def generate_meal_plan():
    """Generate simple meal plan based on goals"""
    goals = session.get('goals', {})
    diet_type = goals.get('diet_type', 'balanced')
    
    meal_plan = {
        'breakfast': [],
        'lunch': [],
        'dinner': [],
        'snacks': []
    }
    
    # Simple meal plan logic (in real app, use more sophisticated algorithm)
    if diet_type == 'high-protein':
        meal_plan['breakfast'] = ['Greek yogurt with nuts', '30g protein']
        meal_plan['lunch'] = ['Grilled chicken with quinoa', '40g protein']
        meal_plan['dinner'] = ['Salmon with roasted vegetables', '35g protein']
    else:  # balanced
        meal_plan['breakfast'] = ['Oatmeal with fruits', '15g protein']
        meal_plan['lunch'] = ['Whole grain wrap with veggies', '20g protein']
        meal_plan['dinner'] = ['Lentil curry with rice', '25g protein']
    
    meal_plan['snacks'] = ['Handful of almonds', 'Protein shake']
    return meal_plan

@app.route('/', methods=['GET', 'POST'])
def home():
    init_session()
    nutrition = None
    error = None
    insights = None
    chart = None
    
    if request.method == 'POST':
        if 'update_goals' in request.form:
            # Handle goal updates
            session['goals'] = {
                'calories': int(request.form.get('calories', 2000)),
                'protein': int(request.form.get('protein', 50)),
                'carbs': int(request.form.get('carbs', 300)),
                'fat': int(request.form.get('fat', 65)),
                'diet_type': request.form.get('diet_type', 'balanced')
            }
            session.modified = True
            return redirect(url_for('home'))
        
        food_input = request.form.get('food', '').strip()
        
        if food_input:
            nutrition = get_nutrition(food_input)
            if nutrition:
                insights = generate_ai_insights(nutrition)
                chart = generate_chart()
            else:
                error = "No data found. Try English names like 'chapati', 'dal tadka'"
        else:
            error = "Please enter a food name"
    
    # Generate meal plan if empty
    if not session.get('meal_plan'):
        session['meal_plan'] = generate_meal_plan()
        session.modified = True
    
    return render_template('index.html', 
                         nutrition=nutrition,
                         insights=insights,
                         error=error,
                         history=session.get('nutrition_history', [])[-5:],
                         goals=session.get('goals'),
                         meal_plan=session.get('meal_plan'),
                         chart=chart)

@app.route('/clear')
def clear_history():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)