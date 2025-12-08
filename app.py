import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

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

# ---------- Data loading and plots ----------

def load_area_data(city_name, budget):
    df = pd.read_csv('areas.csv')
    df_city = df[df['city'].str.lower() == city_name.lower()]
    df_filtered = df_city[df_city['rent'] <= budget]
    return df_filtered.to_dict(orient='records')

def plot_rent_bar_chart(recommendations):
    areas = [row['area'] for row in recommendations]
    rents = [row['rent'] for row in recommendations]
    if not areas or not rents:
        return
    plt.figure(figsize=(7, max(4, len(areas) * 0.5)))
    plt.barh(areas, rents, color=['#bb86fc', '#7a48fc', '#a7f7e4'])
    plt.xlabel('Rent (₹)')
    plt.ylabel('Area')
    plt.title('Rent by Area')
    plt.tight_layout()
    plt.savefig('static/area_rent_chart.png')
    plt.close()

def plot_factor_pie_chart(recommendations, factor='infra'):
    areas = [row['area'] for row in recommendations]
    values = [row[factor] for row in recommendations]
    if not areas or not values:
        return
    plt.figure(figsize=(5, 5))
    plt.pie(values, labels=areas, autopct='%1.1f%%', colors=['#bb86fc', '#7a48fc', '#a7f7e4'])
    plt.title(f'{factor.capitalize()} Distribution')
    plt.tight_layout()
    plt.savefig(f'static/{factor}_pie_chart.png')
    plt.close()

# ---------- City analysis route ----------

@app.route('/city/<city_name>', methods=['GET', 'POST'])
@login_required
def city_analysis(city_name):
    budget = None
    recommendations = []
    if request.method == 'POST':
        budget = request.form.get('budget', type=int)
        if budget is not None:
            recommendations = load_area_data(city_name, budget)
            if recommendations:
                if not os.path.exists('static'):
                    os.makedirs('static')
                plot_rent_bar_chart(recommendations)
                plot_factor_pie_chart(recommendations, factor='infra')
    return render_template(
        'city_analysis.html',
        city_name=city_name,
        recommendations=recommendations,
        budget=budget,
        username=session.get('username')
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
