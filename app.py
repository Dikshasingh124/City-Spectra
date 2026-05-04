import requests #weather api

import plotly.express as px #charts
import plotly #json encoding
import json #covert chart data
from flask import Flask, render_template, request, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Global visitor counter
visitor_count = 0

# Demo user accounts (in-memory)
users = {}


# Admin credentials (in-memory)
admins = {
    'spectra_admin': generate_password_hash('City@123')
}
#contact(in-memory)
contact_messages = []   # each item will be a dict: {name, email, message}

# weather api 
API_KEY = "3d6f56d41974112b920daf5c788d51e4"

def get_weather(city):
    url = "https://api.openweathermap.org/data/2.5/weather"
    
    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric"
    }

    response = requests.get(url, params=params)

    print(response.url)   
    print(response.status_code)
    print(response.text)

    if response.status_code == 200:
        data = response.json()
        return {
            "city": city,
            "temperature": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "weather": data["weather"][0]["description"]
        }
    else:
        return None

# ---------- User auth helpers ----------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' in session:
            return f(*args, **kwargs)
        flash("Please login to access this page.", "error")
        return redirect(url_for('login'))
    return decorated_function

# ---------- Basic user routes ----------


@app.route('/')
def index():
    global visitor_count
    visitor_count += 1
    return render_template("index.html", username=session.get('username'))


@app.route('/about')
def about():
    return render_template("about.html", username=session.get('username'))

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        # save for admin
        contact_messages.append({
            'name': name,
            'email': email,
            'message': message
        })

        flash("Message sent successfully.", "success")
        return redirect(url_for('contact'))

    return render_template("contact.html", username=session.get('username'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in users and check_password_hash(users[username], password):
            session['username'] = username
            flash("Logged in successfully.", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials.", "error")
            return redirect(url_for('login'))
    return render_template("login.html", username=session.get('username'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('reg_username')
        password = request.form.get('reg_password')
        confirm_password = request.form.get('reg_confirm_password')
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for('register'))
        if username in users:
            flash("Username already exists.", "error")
            return redirect(url_for('register'))
        users[username] = generate_password_hash(password)
        session['username'] = username
        flash("Registration successful! Welcome to your dashboard.", "success")
        return redirect(url_for('dashboard'))
    return render_template("register.html", username=session.get('username'))

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template("dashboard.html", username=session.get('username'))

#wether route

cities = ["Pune", "Chennai", "Gurugram", "Noida", "Bengaluru"]

@app.route("/weather")
def weather_page():
    weather_results = []
    
    for city in cities:
        data = get_weather(city)
        if data:
            weather_results.append(data)
    
   # print("DATA:", weather_results)
    
    return render_template("weather.html", weather=weather_results)

@app.route("/weather/<city>")
def weather_city(city):
    data = get_weather(city)

    return render_template("weather.html", weather=data)

# ---------- Data loading and plots ----------

def load_area_data(city_name, budget):
    df = pd.read_csv('areas.csv')
    df_city = df[df['city'].str.lower() == city_name.lower()]
    df_filtered = df_city[df_city['rent'] <= budget]
    return df_filtered.to_dict(orient='records')

# ---------- City analysis route ----------

@app.route('/city/<city_name>', methods=['GET', 'POST'])
@login_required
def city_analysis(city_name):
    budget = None
    recommendations = []
    barJSON = None
    pieJSON = None

    if request.method == 'POST':
        budget = request.form.get('budget', type=int)

        if budget is not None:
            recommendations = load_area_data(city_name, budget)

            if recommendations:
                #  Prepare data
                areas = [row['area'] for row in recommendations]
                rents = [row['rent'] for row in recommendations]
                infra = [row['infra'] for row in recommendations]

                #  BAR CHART (Rent)
                fig_bar = px.bar(
                    x=rents,
                    y=areas,
                    orientation='h',
                    title="Rent by Area",
                    color=rents,
                    color_continuous_scale="purples"
                )
                fig_bar.update_layout(
                template="plotly_dark",
                height=400,
                margin=dict(l=20, r=20, t=40, b=20)
                )

                barJSON = json.dumps(fig_bar, cls=plotly.utils.PlotlyJSONEncoder)

                #  PIE CHART (Infra)
                fig_pie = px.pie(
                    values=infra,
                    names=areas,
                    title="Infrastructure Distribution"
                )
                fig_pie.update_layout(
                template="plotly_dark",
                height=400
                )

                pieJSON = json.dumps(fig_pie, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template(
        'city_analysis.html',
        city_name=city_name,
        recommendations=recommendations,
        budget=budget,
        username=session.get('username'),
        barJSON=barJSON,
        pieJSON=pieJSON
    )
# ---------- Admin routes ----------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in admins and check_password_hash(admins[username], password):
            session['admin_logged_in'] = True
            session['admin_username'] = username
            flash("Admin logged in.", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid admin credentials.", "error")
            return redirect(url_for('admin_login'))
    return render_template('admin_login.html')

@app.route('/admin/forgot-password', methods=['GET', 'POST'])
def admin_forgot_password():
    # Very simple reset: show a form to set a new password directly
    # In a real app, use email + token before allowing reset.[web:4][web:14]
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        if not new_password or new_password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for('admin_forgot_password'))
        # Reset password for the single admin user
        admins['spectra_admin'] = generate_password_hash(new_password)
        flash("Admin password has been updated. Please login with new password.", "success")
        return redirect(url_for('admin_login'))
    return render_template('admin_forgot_password.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        flash("Admin login required.", "error")
        return redirect(url_for('admin_login'))

    user_list = [{'id': i + 1, 'username': u} for i, u in enumerate(users.keys())]

    total_users = len(user_list)
    global visitor_count

    return render_template(
        'admin_dashboard.html',
        users=user_list,
        total_users=total_users,
        total_visitors=visitor_count,
        contact_messages=contact_messages
    )



@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    flash("Admin logged out.", "success")
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(debug=True)