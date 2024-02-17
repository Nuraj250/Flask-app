# Import necessary libraries
import json
from fastapi import Response
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from pymongo import MongoClient
import requests
from bs4 import BeautifulSoup
from werkzeug.security import generate_password_hash, check_password_hash
import os
from flask_paginate import Pagination, get_page_parameter

# Initialize the Flask app
app = Flask(__name__)
# Set a secret key for the session. It's important for security.
app.secret_key = '1998'

# Get the MongoDB URI from environment variables for security reasons
mongo_uri = os.environ.get('MONGO_URI', 'mongodb+srv://nuraj200:QXr6P007i2qFOXwx@cluster0.gsgezdw.mongodb.net/?retryWrites=true&w=majority')
client = MongoClient(mongo_uri)

# Define the home page route
@app.route('/')
def home():
    # Check if user is logged in, if not redirect to login page
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    # Render the home page template if logged in
    return render_template('home.html', results=[])

# Define the index page route
@app.route('/index')
def index():
    # Simply render the index page template
    return render_template('index.html', results=[])

# Define the login page route with support for GET and POST requests
@app.route('/login', methods=['GET', 'POST'])
def login():
    db = client['users']  # Connect to the 'users' database
    collection = db['users']  # Connect to the 'users' collection
    if request.method == 'POST':
        # Get email and password from the form
        email = request.form['email']
        password = request.form['password']
        # Find the user in the database
        user = collection.find_one({'email': email})

        # Verify user and password
        if user and check_password_hash(user['password'], password):
            # Set session variables if login is successful
            session['loggedin'] = True
            session['email'] = email
            session['name'] = user['name']  # Store user's name in session
            return redirect(url_for('home'))
        else:
            # Flash a message if login fails
            flash('Invalid email/password combination')

    # Render the login page template
    return render_template('login.html')

# Define the registration page route with support for GET and POST requests
@app.route('/register', methods=['GET', 'POST'])
def register():
    db = client['users']  # Connect to the 'users' database
    collection = db['users']  # Connect to the 'users' collection
    if request.method == 'POST':
        # Get form data
        email = request.form['email']
        name = request.form['name']
        password = request.form['password']
        # Hash the password for security
        hashed_password = generate_password_hash(password)

        # Insert the new user into the database
        collection.insert_one({
            'name': name,
            'email': email,
            'password': hashed_password
        })

        # Flash a success message
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))

    # Render the registration page template
    return render_template('register.html')

# Define the search functionality, accessible via POST request
@app.route('/search', methods=['POST'])
def search():
    search_type = request.form.get('type')
    query = request.form.get('query', '')

    # Mapping of search types to their respective API endpoints
    url_mapping = {
        'search': 'https://google.serper.dev/search',
        'image': 'https://google.serper.dev/image',
        'videos': 'https://google.serper.dev/videos',
        'places': 'https://google.serper.dev/places',
        'news': 'https://google.serper.dev/news',
        'shopping': 'https://google.serper.dev/shopping'
    }

    # Select the API endpoint based on the search type
    api_endpoint = url_mapping.get(search_type, url_mapping['search'])
    headers = {
        'X-API-KEY': 'your_api_key_here',
        'Content-Type': 'application/json'
    }

    # Prepare the payload for the request
    payload = json.dumps({"q": query})
    # Make the API request
    response = requests.post(api_endpoint, headers=headers, data=payload)
    # Parse the results
    results = response.json().get('organic', [])

    # Render the index page template with the results
    return render_template('index.html', results=results)

# Define the scrape functionality, accessible via POST request
@app.route('/scrape', methods=['POST'])
def scrape():
    db = client['research_scraper_db']  # Connect to the scraper database
    collection = db['scraped_data']  # Connect to the scraped data collection

    url = request.form.get('url')
    if not url:
        # Return an error if no URL is provided
        return jsonify({'error': "No URL provided"}), 400

    try:
        # Attempt to scrape the provided URL
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Insert the scraped data into the database
        scraped_data_entry = {'url': url, 'content': str(soup), 'user_email': session.get('email')}
        collection.insert_one(scraped_data_entry)

        # Return a success message
        return jsonify({'message': "Data scraped and saved successfully"})
    except Exception as e:
        # Return an error message if scraping fails
        return jsonify({'error': str(e)}), 500

# Define the logout functionality
@app.route('/logout')
def logout():
    # Clear session variables to log the user out
    session.pop('loggedin', None)
    session.pop('email', None)
    return redirect(url_for('login'))

# Define the profile page route
@app.route('/profile')
def profile():
    if 'loggedin' not in session:
        # Redirect to login page if not logged in
        return redirect(url_for('login'))
    
    db = client['users']  # Connect to the 'users' database
    collection = db['users']  # Connect to the 'users' collection
    user_email = session['email']
    # Find the user in the database
    user = collection.find_one({'email': user_email})

    # Render the profile page template with the user data
    return render_template('profile.html', user=user)

# Define the history page route
@app.route('/history')
def history():
    if 'loggedin' not in session or 'email' not in session:
        # Redirect to login page if not logged in
        return redirect(url_for('login'))
    
    db = client['research_scraper_db']  # Connect to the scraper database
    collection = db['scraped_data']  # Connect to the scraped data collection
    user_email = session['email']
    # Pagination setup
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 5
    skip = (page - 1) * per_page
    total = collection.count_documents({'user_email': user_email})
    history = collection.find({'user_email': user_email}).skip(skip).limit(per_page)

    pagination = Pagination(page=page, total=total, per_page=per_page, css_framework='bootstrap4')

    # Render the history page template with pagination
    return render_template('history.html', history=history, pagination=pagination)

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
