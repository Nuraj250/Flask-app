import json
from fastapi import Response
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from pymongo import MongoClient
import requests
from bs4 import BeautifulSoup
from werkzeug.security import generate_password_hash, check_password_hash
import os
import csv
from flask_paginate import Pagination, get_page_parameter



app = Flask(__name__)
app.secret_key = '1998'

mongo_uri = os.environ.get('MONGO_URI', 'mongodb+srv://nuraj200:pZF5M46aynWBm1Xw@cluster0.gsgezdw.mongodb.net/users?retryWrites=true&retryReads=true&w=majority')
client = MongoClient(mongo_uri)

@app.route('/')
def home():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    return render_template('home.html', results=[])

@app.route('/index')
def index():
        return render_template('index.html', results=[])


@app.route('/login', methods=['GET', 'POST'])
def login():
    db = client['users']
    collection = db['users']
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = collection.find_one({'email': email})

        if user and check_password_hash(user['password'], password):
            session['loggedin'] = True
            session['email'] = email
            session['name'] = user['name']  # Store user's name in session
            return redirect(url_for('home'))
        else:
            flash('Invalid email/password combination')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    db = client['users']
    collection = db['users']
    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        collection.insert_one({
            'name': name,
            'email': email,
            'password': hashed_password
        })

        flash('Registration successful! Please login.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/search', methods=['POST'])
def search():
    search_type = request.form.get('type')
    query = request.form.get('query', '')

    url_mapping = {
        'search': 'https://google.serper.dev/search',
        'image': 'https://google.serper.dev/image',
        'videos': 'https://google.serper.dev/videos',
        'places': 'https://google.serper.dev/places',
        'news': 'https://google.serper.dev/news',
        'shopping': 'https://google.serper.dev/shopping'
    }

    api_endpoint = url_mapping.get(search_type, url_mapping['search'])
    headers = {
        'X-API-KEY': '3878fdaf12217c8208c5c9dd5a161734975e12f2',
        'Content-Type': 'application/json'
    }

    payload = json.dumps({"q": query})
    response = requests.post(api_endpoint, headers=headers, data=payload)
    results = response.json().get('organic', [])

    return render_template('index.html', results=results)

@app.route('/scrape', methods=['POST'])
def scrape():
    db = client['research_scraper_db']
    collection = db['scraped_data']

    url = request.form.get('url')
    if not url:
        return jsonify({'error': "No URL provided"}), 400

    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Insert scraped data into the database
        scraped_data_entry = {'url': url, 'content': str(soup), 'user_email': session.get('email')}
        collection.insert_one(scraped_data_entry)

        # Return a success message
        return jsonify({'message': "Data scraped and saved successfully"})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('email', None)
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    
    db = client['users']
    collection = db['users']
    user_email = session['email']
    user = collection.find_one({'email': user_email})

    return render_template('profile.html', user=user)

@app.route('/history')
def history():
    if 'loggedin' not in session or 'email' not in session:
        return redirect(url_for('login'))
    
    db = client['research_scraper_db']
    collection = db['scraped_data']
    user_email = session['email']
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 5
    skip = (page - 1) * per_page
    total = collection.count_documents({'user_email': user_email})
    history = collection.find({'user_email': user_email}).skip(skip).limit(per_page)

    pagination = Pagination(page=page, total=total, per_page=per_page, css_framework='bootstrap4')

    return render_template('history.html', history=history, pagination=pagination)

if __name__ == '__main__':
    app.run(debug=True)
