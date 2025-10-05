import os
import base64
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv
from bson import ObjectId
import requests
from requests.auth import HTTPBasicAuth
import json

# --- Configuration and Setup ---
load_dotenv()

app = Flask(__name__)
app.secret_key = 'kuccps_super_secret_key_2025'
app.config['SESSION_TYPE'] = 'filesystem'

# --- Constants ---
SUBJECTS = {
    'mathematics': 'MAT', 'english': 'ENG', 'kiswahili': 'KIS', 'chemistry': 'CHE',
    'biology': 'BIO', 'physics': 'PHY', 'geography': 'GEO', 'history': 'HAG',
    'cre': 'CRE', 'hre': 'HRE', 'ire': 'IRE', 'agriculture': 'AGR', 'computer': 'COM',
    'arts': 'ARD', 'business': 'BST', 'music': 'MUC', 'homescience': 'HSC',
    'french': 'FRE', 'german': 'GER', 'aviation': 'AVI', 'woodwork': 'ARD',
    'building': 'ARD', 'electronics': 'COM', 'metalwork': 'ARD'
}

GRADE_VALUES = {
    'A': 12, 'A-': 11, 'B+': 10, 'B': 9, 'B-': 8, 'C+': 7, 'C': 6, 'C-': 5,
    'D+': 4, 'D': 3, 'D-': 2, 'E': 1
}

CLUSTERS = [f"cluster_{i}" for i in range(1, 21)]

DIPLOMA_COLLECTIONS = [
    "Agricultural_Sciences_Related", "Animal_Health_Related", "Applied_Sciences",
    "Building_Construction_Related", "Business_Related", "Clothing_Fashion_Textile",
    "Computing_IT_Related", "Education_Related", "Engineering_Technology_Related",
    "Environmental_Sciences", "Food_Science_Related", "Graphics_MediaStudies_Related",
    "Health_Sciences_Related", "HairDressing_Beauty_Therapy", "Hospitality_Hotel_Tourism_Related",
    "Library_Information_Science", "Natural_Sciences_Related", "Nutrition_Dietetics",
    "Social_Sciences", "Tax_Custom_Administration", "Technical_Courses"
]

KMTC_COLLECTIONS = ["kmtc_courses"]

CERTIFICATE_COLLECTIONS = [
    "Agricultural_Sciences", "Applied_Sciences", "Building_Construction_Related",
    "Business_Related", "Clothing_Fashion_Textile", "Computing_IT_Related",
    "Engineering_Technology_Related", "Environmental_Sciences", "Food_Science_Related",
    "Graphics_MediaStudies_Related", "HairDressing_Beauty_Therapy", "Health_Sciences_Related",
    "Hospitality_Hotel_Tourism_Related", "Library_Information_Science",
    "Natural_Sciences_Related", "Nutrition_Dietetics", "Social_Sciences", "Tax_Custom_Administration"
]

ARTISAN_COLLECTIONS = CERTIFICATE_COLLECTIONS

# --- MPesa API Credentials (PRODUCTION) ---
MPESA_CONSUMER_KEY = "xueqgztGna3VENZaV7c6pXC34uk7LsDxA4dnIjG2n3OV167d"
MPESA_CONSUMER_SECRET = "XpbH6z5QRz4unhk6XDg83G2n1p796Fd9EUvqs0tEDE3TsZZeYauJ2AApBb0SoMiL"
MPESA_PASSKEY = "a3d842c161dc6617ac99f9e6d250fc1583584e29c1cae2123d3d9f4db94790dc"
MPESA_SHORTCODE = "4185095"

# --- Database Connections ---
MONGODB_URI = "mongodb+srv://iconichean:1Loye8PM3YwlV5h4@cluster0.meufk73.mongodb.net/?retryWrites=true&w=majority"

# Initialize database variables
db = None
db_user_data = None
db_diploma = None
db_kmtc = None
db_certificate = None
db_artisan = None
user_payments_collection = None
user_courses_collection = None
database_connected = False

def initialize_database():
    """Initialize database connections with robust error handling"""
    global db, db_user_data, db_diploma, db_kmtc, db_certificate, db_artisan
    global user_payments_collection, user_courses_collection, database_connected
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"🔄 Attempting to connect to MongoDB (attempt {attempt + 1}/{max_retries})...")
            
            client = MongoClient(
                MONGODB_URI,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=30000,
                socketTimeoutMS=30000,
                retryWrites=True,
                retryReads=True,
                maxPoolSize=50
            )
            
            # Test the connection
            client.admin.command('ping')
            print("✅ Successfully connected to MongoDB")
            
            # Initialize databases
            db = client['Degree']
            db_user_data = client['user_data']
            db_diploma = client['diploma']
            db_kmtc = client['kmtc']
            db_certificate = client['certificate']
            db_artisan = client['artisan']
            
            # Initialize collections
            user_courses_collection = db_user_data['user_courses']
            user_payments_collection = db_user_data['user_payments']
            
            # Create indexes
            user_payments_collection.create_index([("email", 1), ("index_number", 1), ("level", 1)])
            user_payments_collection.create_index([("transaction_ref", 1)])
            user_payments_collection.create_index([("payment_confirmed", 1)])
            user_courses_collection.create_index([("email", 1), ("index_number", 1), ("level", 1)])
            
            database_connected = True
            print("🎉 All database collections initialized successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Database connection error (attempt {attempt + 1}): {str(e)}")
            if attempt < max_retries - 1:
                import time
                time.sleep(2)
                continue
            else:
                database_connected = False
                print("❌ Failed to connect to MongoDB after multiple attempts")
                return False

# Initialize database on startup
if not initialize_database():
    print("⚠️ Running in fallback mode - database operations will be skipped")
else:
    print("🎉 Database connection established successfully!")

# --- Helper Classes ---
class JSONEncoder:
    """Custom JSON encoder for handling MongoDB ObjectId"""
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return super().default(o)

app.json_encoder = JSONEncoder

# --- Helper Functions ---
def parse_grade(grade_str):
    """Parse grade string, handling unexpected formats"""
    if not grade_str:
        return None
    if grade_str in GRADE_VALUES:
        return grade_str
    if '/' in grade_str:
        parts = grade_str.split('/')
        for part in parts:
            if part in GRADE_VALUES:
                return part
    return None

def meets_requirement(requirement_key, requirement_grade, user_grades):
    """Check if user meets a single requirement (handles / for either/or)"""
    parsed_grade = parse_grade(requirement_grade)
    if not parsed_grade:
        return False
        
    if '/' in requirement_key:
        alternatives = requirement_key.split('/')
        for subject in alternatives:
            if subject in user_grades:
                if GRADE_VALUES[user_grades[subject]] >= GRADE_VALUES[parsed_grade]:
                    return True
        return False
    else:
        if requirement_key in user_grades:
            return GRADE_VALUES[user_grades[requirement_key]] >= GRADE_VALUES[parsed_grade]
        return False

def check_course_qualification(course, user_grades, user_cluster_points):
    """Check if user qualifies for a specific course based on subjects and cluster points"""
    requirements = course.get('minimum_subject_requirements', {})
    
    subject_qualified = True
    if requirements:
        for subject_key, required_grade in requirements.items():
            if not meets_requirement(subject_key, required_grade, user_grades):
                subject_qualified = False
                break
    
    cluster_qualified = True
    cluster_name = course.get('cluster', '')
    cut_off_points = course.get('cut_off_points', 0)
    
    if cluster_name and cut_off_points:
        user_points = user_cluster_points.get(cluster_name, 0)
        if user_points < cut_off_points:
            cluster_qualified = False
    
    return subject_qualified and cluster_qualified

def check_diploma_course_qualification(course, user_grades, user_mean_grade):
    """Check if user qualifies for a specific diploma course based on mean grade and subject requirements"""
    mean_grade_qualified = True
    min_mean_grade = course.get('minimum_grade', {}).get('mean_grade')
    
    if min_mean_grade:
        if GRADE_VALUES[user_mean_grade] < GRADE_VALUES[min_mean_grade]:
            mean_grade_qualified = False
    
    subject_qualified = True
    requirements = course.get('minimum_subject_requirements', {})
    
    if requirements:
        for subject_key, required_grade in requirements.items():
            if not meets_requirement(subject_key, required_grade, user_grades):
                subject_qualified = False
                break
    
    return mean_grade_qualified and subject_qualified

def check_certificate_course_qualification(course, user_grades, user_mean_grade):
    """Check if user qualifies for a specific certificate course based on mean grade and subject requirements"""
    return check_diploma_course_qualification(course, user_grades, user_mean_grade)

def check_artisan_course_qualification(course, user_grades, user_mean_grade):
    """Check if user qualifies for a specific artisan course based on mean grade and subject requirements"""
    return check_diploma_course_qualification(course, user_grades, user_mean_grade)

# --- Course Qualification Functions ---
def get_qualifying_courses(user_grades, user_cluster_points):
    """Get all degree courses that the user qualifies for"""
    if not database_connected:
        print("❌ Database not available for degree courses")
        return []
        
    qualifying_courses = []
    
    for collection_name in CLUSTERS:
        try:
            if collection_name not in db.list_collection_names():
                continue
                
            collection = db[collection_name]
            courses = collection.find()
            
            for course in courses:
                course_with_cluster = dict(course)
                course_with_cluster['cluster'] = collection_name
                
                if check_course_qualification(course_with_cluster, user_grades, user_cluster_points):
                    qualifying_courses.append(course_with_cluster)
        
        except Exception as e:
            print(f"Error processing collection {collection_name}: {str(e)}")
            continue
    
    return qualifying_courses

def get_qualifying_diploma_courses(user_grades, user_mean_grade):
    """Get all diploma courses that the user qualifies for"""
    if not database_connected:
        print("❌ Database not available for diploma courses")
        return []
        
    qualifying_courses = []
    
    for collection_name in DIPLOMA_COLLECTIONS:
        try:
            if collection_name not in db_diploma.list_collection_names():
                continue
                
            collection = db_diploma[collection_name]
            courses = collection.find()
            
            for course in courses:
                if check_diploma_course_qualification(course, user_grades, user_mean_grade):
                    course_with_collection = dict(course)
                    course_with_collection['collection'] = collection_name
                    qualifying_courses.append(course_with_collection)
        
        except Exception as e:
            print(f"Error processing diploma collection {collection_name}: {str(e)}")
            continue
    
    return qualifying_courses

def get_qualifying_kmtc_courses(user_grades, user_mean_grade):
    """Get all KMTC courses that the user qualifies for"""
    if not database_connected:
        print("❌ Database not available for KMTC courses")
        return []
        
    qualifying_courses = []
    
    try:
        if 'kmtc_courses' not in db_kmtc.list_collection_names():
            return qualifying_courses
            
        collection = db_kmtc['kmtc_courses']
        courses = collection.find()
        
        for course in courses:
            if check_diploma_course_qualification(course, user_grades, user_mean_grade):
                qualifying_courses.append(course)
                
    except Exception as e:
        print(f"Error processing KMTC collection: {str(e)}")
        
    return qualifying_courses

def get_qualifying_certificate_courses(user_grades, user_mean_grade):
    """Get all certificate courses that the user qualifies for"""
    if not database_connected:
        print("❌ Database not available for certificate courses")
        return []
        
    qualifying_courses = []
    
    for collection_name in CERTIFICATE_COLLECTIONS:
        try:
            if collection_name not in db_certificate.list_collection_names():
                continue
                
            collection = db_certificate[collection_name]
            courses = collection.find()
            
            for course in courses:
                if check_certificate_course_qualification(course, user_grades, user_mean_grade):
                    course_with_collection = dict(course)
                    course_with_collection['collection'] = collection_name
                    qualifying_courses.append(course_with_collection)
        
        except Exception as e:
            print(f"Error processing certificate collection {collection_name}: {str(e)}")
            continue
    
    return qualifying_courses

def get_qualifying_artisan_courses(user_grades, user_mean_grade):
    """Get all artisan courses that the user qualifies for"""
    if not database_connected:
        print("❌ Database not available for artisan courses")
        return []
        
    qualifying_courses = []
    
    for collection_name in ARTISAN_COLLECTIONS:
        try:
            if collection_name not in db_artisan.list_collection_names():
                continue
                
            collection = db_artisan[collection_name]
            courses = collection.find()
            
            for course in courses:
                if check_artisan_course_qualification(course, user_grades, user_mean_grade):
                    course_with_collection = dict(course)
                    course_with_collection['collection'] = collection_name
                    qualifying_courses.append(course_with_collection)
        
        except Exception as e:
            print(f"Error processing artisan collection {collection_name}: {str(e)}")
            continue
    
    return qualifying_courses

# --- Database Operations ---
def save_user_payment(email, index_number, level, transaction_ref=None):
    """Save user payment information to payments collection"""
    if not database_connected:
        session_key = f'{level}_payment_{index_number}'
        session[session_key] = {
            'email': email,
            'index_number': index_number,
            'level': level,
            'transaction_ref': transaction_ref,
            'payment_confirmed': False,
            'created_at': datetime.now().isoformat()
        }
        return
        
    payment_record = {
        'email': email,
        'index_number': index_number,
        'level': level,
        'transaction_ref': transaction_ref,
        'payment_confirmed': False,
        'created_at': datetime.now()
    }
    
    try:
        result = user_payments_collection.update_one(
            {'email': email, 'index_number': index_number, 'level': level},
            {'$set': payment_record},
            upsert=True
        )
        print(f"✅ Payment record saved for {email}")
    except Exception as e:
        print(f"❌ Error saving user payment: {str(e)}")
        session_key = f'{level}_payment_{index_number}'
        session[session_key] = payment_record

def save_user_courses(email, index_number, level, courses):
    """Save user course results to courses collection"""
    print(f"💾 Saving {len(courses)} courses for {email}, {index_number}, {level}")
    
    if not courses:
        print("⚠️ No courses to save!")
        return
        
    if not database_connected:
        session_key = f'{level}_courses_{index_number}'
        session[session_key] = {
            'email': email,
            'index_number': index_number,
            'level': level,
            'courses': courses,
            'created_at': datetime.now().isoformat()
        }
        print(f"✅ Courses saved to session")
        return
        
    courses_record = {
        'email': email,
        'index_number': index_number,
        'level': level,
        'courses': courses,
        'created_at': datetime.now()
    }
    
    try:
        result = user_courses_collection.update_one(
            {'email': email, 'index_number': index_number, 'level': level},
            {'$set': courses_record},
            upsert=True
        )
        
        if result.upserted_id:
            print(f"✅ New courses record created with {len(courses)} courses")
        else:
            print(f"✅ Courses record updated with {len(courses)} courses")
            
    except Exception as e:
        print(f"❌ Error saving user courses: {str(e)}")
        session_key = f'{level}_courses_{index_number}'
        session[session_key] = courses_record

def update_transaction_ref(email, index_number, level, transaction_ref):
    """Update transaction reference for user"""
    if not database_connected:
        session_key = f'{level}_payment_{index_number}'
        if session_key in session:
            session[session_key]['transaction_ref'] = transaction_ref
        return
        
    try:
        result = user_payments_collection.update_one(
            {'email': email, 'index_number': index_number, 'level': level},
            {'$set': {
                'transaction_ref': transaction_ref,
                'payment_confirmed': False
            }}
        )
        print(f"✅ Transaction reference updated: {transaction_ref}")
    except Exception as e:
        print(f"❌ Error updating transaction reference: {str(e)}")

def get_user_payment(email, index_number, level):
    """Get user payment info from database with fallback to session"""
    if database_connected:
        try:
            payment_data = user_payments_collection.find_one(
                {'email': email, 'index_number': index_number, 'level': level}
            )
            if payment_data:
                return payment_data
        except Exception as e:
            print(f"❌ Error getting user payment from database: {str(e)}")
    
    session_key = f'{level}_payment_{index_number}'
    return session.get(session_key)

def get_user_courses_data(email, index_number, level):
    """Get user courses from database with fallback to session"""
    if database_connected:
        try:
            courses_data = user_courses_collection.find_one(
                {'email': email, 'index_number': index_number, 'level': level}
            )
            if courses_data:
                return courses_data
        except Exception as e:
            print(f"❌ Error getting user courses from database: {str(e)}")
    
    session_key = f'{level}_courses_{index_number}'
    return session.get(session_key)

def mark_payment_confirmed(transaction_ref, mpesa_receipt=None):
    """Mark payment as confirmed - for STK Push"""
    print(f"🔍 Confirming payment: {transaction_ref}")
    
    if not database_connected:
        payment_found = False
        for key in list(session.keys()):
            if isinstance(session.get(key), dict) and session[key].get('transaction_ref') == transaction_ref:
                session[key]['payment_confirmed'] = True
                session[key]['mpesa_receipt'] = mpesa_receipt
                session[key]['payment_date'] = datetime.now().isoformat()
                payment_found = True
                break
        return payment_found
        
    try:
        result = user_payments_collection.update_one(
            {'transaction_ref': transaction_ref},
            {'$set': {
                'payment_confirmed': True,
                'mpesa_receipt': mpesa_receipt,
                'payment_date': datetime.now()
            }}
        )
        
        if result.modified_count > 0:
            print(f"✅ Payment confirmed: {transaction_ref}")
            return True
        else:
            print(f"⚠️ No payment found with transaction ref: {transaction_ref}")
            return False
            
    except Exception as e:
        print(f"❌ Error marking payment confirmed: {str(e)}")
        return False

def mark_payment_confirmed_by_account(account_number, mpesa_receipt, amount=None):
    """Mark payment as confirmed by account number (index number) - for Paybill payments"""
    if not database_connected:
        for key in session:
            if session[key].get('index_number') == account_number:
                session[key]['payment_confirmed'] = True
                session[key]['mpesa_receipt'] = mpesa_receipt
                if amount:
                    session[key]['payment_amount'] = amount
                return True
        return False
        
    try:
        update_data = {
            'payment_confirmed': True,
            'mpesa_receipt': mpesa_receipt,
            'payment_date': datetime.now()
        }
        if amount:
            update_data['payment_amount'] = amount
            
        result = user_payments_collection.update_one(
            {'index_number': account_number},
            {'$set': update_data}
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"❌ Error marking payment confirmed by account: {str(e)}")
        return False

# --- MPesa Integration Functions ---
def get_mpesa_access_token():
    """Get MPesa access token for authentication"""
    consumer_key = MPESA_CONSUMER_KEY
    consumer_secret = MPESA_CONSUMER_SECRET
    
    try:
        response = requests.get(
            "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
            auth=HTTPBasicAuth(consumer_key, consumer_secret),
            timeout=30
        )
        
        resp_json = response.json()
        access_token = resp_json.get('access_token')
        
        if not access_token:
            raise Exception('No access_token in MPesa OAuth response')
            
        return access_token
        
    except Exception as e:
        print('❌ MPesa OAuth error:', str(e))
        raise

def initiate_stk_push(phone, amount=1):
    """Initiate MPesa STK push payment"""
    if phone.startswith('0') and len(phone) == 10:
        phone = '254' + phone[1:]
    elif phone.startswith('+254') and len(phone) == 13:
        phone = phone[1:]
    elif len(phone) == 9:
        phone = '254' + phone
    
    try:
        access_token = get_mpesa_access_token()
        if not access_token:
            return {'error': 'No access token received'}
            
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        business_short_code = MPESA_SHORTCODE
        passkey = MPESA_PASSKEY
        data_to_encode = business_short_code + passkey + timestamp
        password = base64.b64encode(data_to_encode.encode()).decode('utf-8')
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        index_number = session.get('index_number', 'KUCCPS')
        
        base_url = 'https://kuccps-courses.onrender.com'
        payload = {
            "BusinessShortCode": business_short_code,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone,
            "PartyB": business_short_code,
            "PhoneNumber": phone,
            "CallBackURL": f"{base_url}/mpesa/callback",
            "AccountReference": index_number,
            "TransactionDesc": "Course Qualification Results - Ksh 1"
        }
        
        response = requests.post(
            "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        return response.json()
        
    except Exception as e:
        print(f"Error initiating STK push: {str(e)}")
        return {'error': str(e)}

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/degree')
def degree():
    return render_template('degree.html')

@app.route('/diploma')
def diploma():
    return render_template('diploma.html')

@app.route('/kmtc')
def kmtc():
    return render_template('kmtc.html')

@app.route('/certificate')
def certificate():
    return render_template('certificate.html')

@app.route('/artisan')
def artisan():
    return render_template('artisan.html')

@app.route('/results')
def results():
    return render_template('results.html')

# --- Grade Submission Routes ---
@app.route('/submit-grades', methods=['POST'])
def submit_grades():
    try:
        form_data = request.form.to_dict()
        
        user_grades = {}
        for subject_name, subject_code in SUBJECTS.items():
            if subject_name in form_data and form_data[subject_name]:
                grade = form_data[subject_name].upper()
                if grade in GRADE_VALUES:
                    user_grades[subject_code] = grade
        
        user_cluster_points = {}
        for i in range(1, 21):
            cluster_key = f"cl{i}"
            if cluster_key in form_data and form_data[cluster_key]:
                try:
                    user_cluster_points[f"cluster_{i}"] = float(form_data[cluster_key])
                except ValueError:
                    user_cluster_points[f"cluster_{i}"] = 0.0
        
        session['degree_grades'] = user_grades
        session['degree_cluster_points'] = user_cluster_points
        session['degree_data_submitted'] = True
        return redirect(url_for('enter_details', flow='degree'))
        
    except Exception as e:
        print(f"❌ Error in submit_grades: {str(e)}")
        flash("An error occurred while processing your grades", "error")
        return redirect(url_for('degree'))

@app.route('/submit-diploma-grades', methods=['POST'])
def submit_diploma_grades():
    try:
        form_data = request.form.to_dict()
        
        user_mean_grade = form_data.get('overall', '').upper()
        if user_mean_grade not in GRADE_VALUES:
            flash("Please select a valid overall grade", "error")
            return redirect(url_for('diploma'))
        
        user_grades = {}
        for subject_name, subject_code in SUBJECTS.items():
            if subject_name in form_data and form_data[subject_name]:
                grade = form_data[subject_name].upper()
                if grade in GRADE_VALUES:
                    user_grades[subject_code] = grade
        
        session['diploma_grades'] = user_grades
        session['diploma_mean_grade'] = user_mean_grade
        session['diploma_data_submitted'] = True
        return redirect(url_for('enter_details', flow='diploma'))
        
    except Exception as e:
        print(f"❌ Error in submit_diploma_grades: {str(e)}")
        flash("An error occurred while processing your request", "error")
        return redirect(url_for('diploma'))

@app.route('/submit-certificate-grades', methods=['POST'])
def submit_certificate_grades():
    try:
        form_data = request.form.to_dict()
        
        user_mean_grade = form_data.get('overall', '').upper()
        if user_mean_grade not in GRADE_VALUES:
            flash("Please select a valid overall grade", "error")
            return redirect(url_for('certificate'))
        
        user_grades = {}
        for subject_name, subject_code in SUBJECTS.items():
            if subject_name in form_data and form_data[subject_name]:
                grade = form_data[subject_name].upper()
                if grade in GRADE_VALUES:
                    user_grades[subject_code] = grade
        
        session['certificate_grades'] = user_grades
        session['certificate_mean_grade'] = user_mean_grade
        session['certificate_data_submitted'] = True
        return redirect(url_for('enter_details', flow='certificate'))
        
    except Exception as e:
        print(f"❌ Error in submit_certificate_grades: {str(e)}")
        flash("An error occurred while processing your request", "error")
        return redirect(url_for('certificate'))

@app.route('/submit-artisan-grades', methods=['POST'])
def submit_artisan_grades():
    try:
        form_data = request.form.to_dict()
        
        user_mean_grade = form_data.get('overall', '').upper()
        if user_mean_grade not in GRADE_VALUES:
            flash("Please select a valid overall grade", "error")
            return redirect(url_for('artisan'))
        
        user_grades = {}
        for subject_name, subject_code in SUBJECTS.items():
            if subject_name in form_data and form_data[subject_name]:
                grade = form_data[subject_name].upper()
                if grade in GRADE_VALUES:
                    user_grades[subject_code] = grade
        
        session['artisan_grades'] = user_grades
        session['artisan_mean_grade'] = user_mean_grade
        session['artisan_data_submitted'] = True
        return redirect(url_for('enter_details', flow='artisan'))
        
    except Exception as e:
        print(f"❌ Error in submit_artisan_grades: {str(e)}")
        flash("An error occurred while processing your request", "error")
        return redirect(url_for('artisan'))

@app.route('/submit-kmtc-grades', methods=['POST'])
def submit_kmtc_grades():
    try:
        form_data = request.form.to_dict()
        
        user_mean_grade = form_data.get('overall', '').upper()
        if user_mean_grade not in GRADE_VALUES:
            flash("Please select a valid overall grade", "error")
            return redirect(url_for('kmtc'))
        
        user_grades = {}
        for subject_name, subject_code in SUBJECTS.items():
            if subject_name in form_data and form_data[subject_name]:
                grade = form_data[subject_name].upper()
                if grade in GRADE_VALUES:
                    user_grades[subject_code] = grade
        
        session['kmtc_grades'] = user_grades
        session['kmtc_mean_grade'] = user_mean_grade
        session['kmtc_data_submitted'] = True
        return redirect(url_for('enter_details', flow='kmtc'))
        
    except Exception as e:
        print(f"❌ Error in submit_kmtc_grades: {str(e)}")
        flash("An error occurred while processing your request", "error")
        return redirect(url_for('kmtc'))

# --- User Details and Payment Routes ---
@app.route('/enter-details/<flow>', methods=['GET', 'POST'])
def enter_details(flow):
    if request.method == 'GET':
        if not session.get(f'{flow}_data_submitted'):
            flash("Please submit your grades first", "error")
            return redirect(url_for(flow))
        return render_template('enter_details.html', flow=flow)
    
    email = request.form.get('email', '').strip()
    index_number = request.form.get('index_number', '').strip()
    
    if not email or not index_number:
        flash("Email and KCSE Index Number are required.", "error")
        return redirect(url_for('enter_details', flow=flow))
    
    session['email'] = email
    session['index_number'] = index_number
    session['current_flow'] = flow
    
    save_user_payment(email, index_number, flow)
    
    return redirect(url_for('payment', flow=flow))

@app.route('/check-payment/<flow>')
def check_payment(flow):
    email = session.get('email')
    index_number = session.get('index_number')
    user_payment = get_user_payment(email, index_number, flow)
    paid = bool(user_payment and user_payment.get('payment_confirmed'))
    return {'paid': paid}

@app.route('/payment/<flow>', methods=['GET', 'POST'])
def payment(flow):
    if request.method == 'GET':
        if not session.get('email') or not session.get('index_number'):
            flash("Please enter your details first", "error")
            return redirect(url_for('enter_details', flow=flow))
        return render_template('payment.html', flow=flow)

    phone = request.form.get('phone', '').strip()
    if not phone:
        return {'success': False, 'error': 'Phone number is required for payment.'}, 400

    result = initiate_stk_push(phone, amount=1)
    if result.get('ResponseCode') == '0':
        transaction_ref = result.get('CheckoutRequestID')
        email = session.get('email')
        index_number = session.get('index_number')
        
        if transaction_ref and email and index_number:
            update_transaction_ref(email, index_number, flow, transaction_ref)

        return {
            'success': True,
            'ResponseCode': '0', 
            'transaction_ref': transaction_ref,
            'redirect_url': url_for('payment_wait', flow=flow)
        }

    error_message = result.get('errorDescription') or result.get('errorMessage') or 'Failed to initiate payment. Try again.'
    return {'success': False, 'error': error_message}, 400

@app.route('/payment-wait/<flow>')
def payment_wait(flow):
    email = session.get('email')
    index_number = session.get('index_number')
    transaction_ref = None
    
    if email and index_number:
        user_payment = get_user_payment(email, index_number, flow)
        if user_payment:
            transaction_ref = user_payment.get('transaction_ref')
            
    return render_template('payment_wait.html', 
                         flow=flow, 
                         transaction_ref=transaction_ref,
                         check_status_url=url_for('check_payment_status', flow=flow))

@app.route('/check-payment-status/<flow>')
def check_payment_status(flow):
    email = session.get('email')
    index_number = session.get('index_number')
    
    if not email or not index_number:
        return {'paid': False, 'error': 'Session data missing'}
    
    user_payment = get_user_payment(email, index_number, flow)
    session_paid = session.get(f'paid_{flow}') or session.get('payment_confirmed')
    
    payment_confirmed = (
        (user_payment and user_payment.get('payment_confirmed')) or 
        session_paid
    )
    
    if payment_confirmed:
        session[f'paid_{flow}'] = True
        session['payment_confirmed'] = True
        session.modified = True
        
        return {
            'paid': True,
            'redirect_url': url_for('show_results', flow=flow)
        }
    else:
        return {'paid': False}

# --- MPesa Callback Routes ---
@app.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    try:
        data = request.get_json(force=True)
        
        callback_metadata = data.get('Body', {}).get('stkCallback', {})
        transaction_ref = callback_metadata.get('CheckoutRequestID')
        result_code = callback_metadata.get('ResultCode')
        
        mpesa_receipt = None
        items = callback_metadata.get('CallbackMetadata', {}).get('Item', [])
        for item in items:
            if item.get('Name') == 'MpesaReceiptNumber':
                mpesa_receipt = item.get('Value')
                break
        
        if transaction_ref and result_code == 0 and mpesa_receipt:
            result = mark_payment_confirmed(transaction_ref, mpesa_receipt)
            if result:
                return {'success': True}, 200
            else:
                return {'success': False}, 400
        else:
            return {'success': False}, 400
            
    except Exception as e:
        print(f"❌ Error processing MPesa callback: {str(e)}")
        return {'success': False}, 400

@app.route('/mpesa/confirmation', methods=['POST'])
def mpesa_confirmation():
    data = request.get_json(force=True)
    trans_id = data.get('TransID')
    account = data.get('BillRefNumber')
    
    if account:
        mark_payment_confirmed_by_account(account, trans_id)
    
    return {'ResultCode': 0, 'ResultDesc': 'Accepted'}

@app.route('/mpesa/validation', methods=['POST'])
def mpesa_validation():
    return {
        "ResultCode": 0,
        "ResultDesc": "Accepted"
    }

# --- Results Display Routes ---
@app.route('/results/<flow>')
def show_results(flow):
    email = session.get('email')
    index_number = session.get('index_number')
    
    if not email or not index_number:
        flash("Please complete the qualification process first", "error")
        return redirect(url_for('index'))
    
    user_payment = get_user_payment(email, index_number, flow)
    session_paid = session.get(f'paid_{flow}') or session.get('payment_confirmed')
    
    if not user_payment and not session_paid:
        flash('Please complete payment to view your results.', 'error')
        return redirect(url_for('payment', flow=flow))
    
    if user_payment and not user_payment.get('payment_confirmed') and not session_paid:
        flash('Payment not confirmed yet. Please wait or contact support.', 'error')
        return redirect(url_for('payment_wait', flow=flow))

    qualifying_courses = []
    user_grades = {}
    user_mean_grade = None
    user_cluster_points = {}
    
    try:
        if flow == 'degree':
            user_grades = session.get('degree_grades', {})
            user_cluster_points = session.get('degree_cluster_points', {})
            qualifying_courses = get_qualifying_courses(user_grades, user_cluster_points)
            
        elif flow == 'diploma':
            user_grades = session.get('diploma_grades', {})
            user_mean_grade = session.get('diploma_mean_grade', '')
            qualifying_courses = get_qualifying_diploma_courses(user_grades, user_mean_grade)
            
        elif flow == 'certificate':
            user_grades = session.get('certificate_grades', {})
            user_mean_grade = session.get('certificate_mean_grade', '')
            qualifying_courses = get_qualifying_certificate_courses(user_grades, user_mean_grade)
            
        elif flow == 'artisan':
            user_grades = session.get('artisan_grades', {})
            user_mean_grade = session.get('artisan_mean_grade', '')
            qualifying_courses = get_qualifying_artisan_courses(user_grades, user_mean_grade)
            
        elif flow == 'kmtc':
            user_grades = session.get('kmtc_grades', {})
            user_mean_grade = session.get('kmtc_mean_grade', '')
            qualifying_courses = get_qualifying_kmtc_courses(user_grades, user_mean_grade)
            
        else:
            flash("Invalid flow type", "error")
            return redirect(url_for('index'))

        # Save courses to database/session
        save_user_courses(email, index_number, flow, qualifying_courses)
        
        # Group courses by collection
        courses_by_collection = {}
        for course in qualifying_courses:
            if flow == 'degree':
                collection_name = course.get('cluster', 'Other')
            else:
                collection_name = course.get('collection', 'Other')
            
            if collection_name not in courses_by_collection:
                courses_by_collection[collection_name] = []
            courses_by_collection[collection_name].append(course)
        
        return render_template('collection_results.html', 
                             courses=qualifying_courses,
                             courses_by_collection=courses_by_collection,
                             user_grades=user_grades, 
                             user_mean_grade=user_mean_grade,
                             user_cluster_points=user_cluster_points,
                             subjects=SUBJECTS, 
                             email=email, 
                             index_number=index_number,
                             flow=flow)
                             
    except Exception as e:
        print(f"❌ Error in show_results: {str(e)}")
        flash("An error occurred while generating your results", "error")
        return redirect(url_for('index'))

# --- Collection-based Results Routes ---
@app.route('/collection-courses/<flow>/<collection_name>')
def show_collection_courses(flow, collection_name):
    email = session.get('email')
    index_number = session.get('index_number')
    
    if not email or not index_number:
        flash("Please complete the qualification process first", "error")
        return redirect(url_for('index'))
    
    user_payment = get_user_payment(email, index_number, flow)
    if not user_payment or not user_payment.get('payment_confirmed'):
        flash('Please complete payment to view your results.', 'error')
        return redirect(url_for('payment', flow=flow))

    user_courses_data = get_user_courses_data(email, index_number, flow)
    if user_courses_data and user_courses_data.get('courses'):
        qualifying_courses = user_courses_data['courses']
    else:
        if flow == 'degree':
            user_grades = session.get('degree_grades', {})
            user_cluster_points = session.get('degree_cluster_points', {})
            qualifying_courses = get_qualifying_courses(user_grades, user_cluster_points)
        elif flow == 'diploma':
            user_grades = session.get('diploma_grades', {})
            user_mean_grade = session.get('diploma_mean_grade', '')
            qualifying_courses = get_qualifying_diploma_courses(user_grades, user_mean_grade)
        elif flow == 'certificate':
            user_grades = session.get('certificate_grades', {})
            user_mean_grade = session.get('certificate_mean_grade', '')
            qualifying_courses = get_qualifying_certificate_courses(user_grades, user_mean_grade)
        elif flow == 'artisan':
            user_grades = session.get('artisan_grades', {})
            user_mean_grade = session.get('artisan_mean_grade', '')
            qualifying_courses = get_qualifying_artisan_courses(user_grades, user_mean_grade)
        elif flow == 'kmtc':
            user_grades = session.get('kmtc_grades', {})
            user_mean_grade = session.get('kmtc_mean_grade', '')
            qualifying_courses = get_qualifying_kmtc_courses(user_grades, user_mean_grade)
        else:
            qualifying_courses = []
    
    collection_courses = [course for course in qualifying_courses if course.get('collection') == collection_name]
    
    return render_template('collection_courses.html',
                         flow=flow,
                         collection_name=collection_name,
                         courses=collection_courses,
                         email=email,
                         index_number=index_number)
@app.route('/verify-payment', methods=['POST'])
def verify_payment():
    """Verify payment and return course information for all levels"""
    try:
        mpesa_receipt = request.form.get('mpesa_receipt', '').strip().upper()
        index_number = request.form.get('index_number', '').strip()
        
        if not mpesa_receipt or not index_number:
            return jsonify({'success': False, 'error': 'M-Pesa receipt and index number are required'})
        
        # Validate M-Pesa receipt format
        if len(mpesa_receipt) != 10 or not mpesa_receipt.isalnum():
            return jsonify({'success': False, 'error': 'Invalid M-Pesa receipt format. Must be 10 alphanumeric characters.'})
        
        # Validate index number format
        import re
        if not re.match(r'^\d{11}/\d{4}$', index_number):
            return jsonify({'success': False, 'error': 'Invalid index number format. Must be 11 digits, slash, 4 digits (e.g., 12345678901/2024)'})
        
        print(f"🔍 Verifying payment for index: {index_number}, receipt: {mpesa_receipt}")
        
        # SIMPLE CHECK: Find any confirmed payment for this index number and receipt
        payment_found = False
        
        if database_connected:
            payment_data = user_payments_collection.find_one({
                'index_number': index_number,
                'mpesa_receipt': mpesa_receipt,
                'payment_confirmed': True
            })
            payment_found = payment_data is not None
        else:
            # Session fallback
            for key in session:
                if isinstance(session.get(key), dict):
                    payment_data = session[key]
                    if (payment_data.get('index_number') == index_number and 
                        payment_data.get('mpesa_receipt') == mpesa_receipt and
                        payment_data.get('payment_confirmed')):
                        payment_found = True
                        break
        
        if not payment_found:
            print(f"❌ No confirmed payment found for index: {index_number}, receipt: {mpesa_receipt}")
            return jsonify({'success': False, 'error': 'No confirmed payment found with these details. Please ensure payment was successful and try again.'})
        
        print(f"✅ Payment confirmed for index: {index_number}")
        
        # Get ALL courses for this user across ALL levels
        user_courses = {}
        course_levels = []
        total_courses = 0
        
        if database_connected:
            levels = ['degree', 'diploma', 'certificate', 'artisan', 'kmtc']
            for level in levels:
                courses_data = user_courses_collection.find_one({
                    'index_number': index_number,
                    'level': level
                })
                if courses_data and courses_data.get('courses'):
                    # Simple course count - we don't need the actual course data here
                    course_count = len(courses_data['courses'])
                    user_courses[level] = {
                        'count': course_count
                    }
                    course_levels.append(level)
                    total_courses += course_count
                    print(f"📚 Found {course_count} {level} courses")
        
        if total_courses == 0:
            return jsonify({'success': False, 'error': 'No course results found for your payment. Please ensure you completed the qualification process.'})
        
        print(f"🎓 Total courses found: {total_courses} across {len(course_levels)} levels")
        
        # Return simple success response with redirect URL
        return jsonify({
            'success': True,
            'payment_confirmed': True,
            'courses_count': total_courses,
            'levels': course_levels,
            'level_details': user_courses,
            'redirect_url': url_for('verified_results_dashboard', index=index_number, receipt=mpesa_receipt)
        })
        
    except Exception as e:
        print(f"❌ Error verifying payment: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'Internal server error. Please try again later.'})
@app.route('/verified-dashboard')
def verified_results_dashboard():
    """Dashboard showing all available course levels for verified payment"""
    index_number = request.args.get('index')
    receipt = request.args.get('receipt')
    
    if not index_number or not receipt:
        flash("Invalid verification parameters", "error")
        return redirect(url_for('index'))
    
    print(f"📊 Loading dashboard for index: {index_number}")
    
    # Get all courses for this user across all levels
    user_courses = {}
    total_courses = 0
    
    if database_connected:
        levels = ['degree', 'diploma', 'certificate', 'artisan', 'kmtc']
        for level in levels:
            courses_data = user_courses_collection.find_one({
                'index_number': index_number,
                'level': level
            })
            if courses_data and courses_data.get('courses'):
                course_count = len(courses_data['courses'])
                user_courses[level] = {
                    'courses': courses_data['courses'],
                    'count': course_count
                }
                total_courses += course_count
                print(f"📚 Loaded {course_count} {level} courses")
    
    if not user_courses:
        flash("No course results found for your payment details", "error")
        return redirect(url_for('index'))
    
    print(f"🎓 Dashboard ready with {total_courses} total courses")
    
    # Store verification in session for individual level access
    session['verified_payment'] = True
    session['verified_index'] = index_number
    session['verified_receipt'] = receipt
    
    return render_template('verified_dashboard.html',
                         user_courses=user_courses,
                         index_number=index_number,
                         receipt=receipt,
                         total_courses=total_courses)
@app.route('/verified-results/<level>')
def show_verified_level_results(level):
    """Show verified results for a specific course level"""
    index_number = request.args.get('index')
    receipt = request.args.get('receipt')
    
    if level not in ['degree', 'diploma', 'certificate', 'artisan', 'kmtc']:
        flash("Invalid course level", "error")
        return redirect(url_for('index'))
    
    if not index_number or not receipt:
        flash("Invalid verification parameters", "error")
        return redirect(url_for('index'))
    
    print(f"🎓 Loading {level} courses for index: {index_number}")
    
    # Get courses for the specific level
    courses_data = None
    if database_connected:
        courses_data = user_courses_collection.find_one({
            'index_number': index_number,
            'level': level
        })
    
    if not courses_data or not courses_data.get('courses'):
        flash(f"No {level} course results found for your payment details", "error")
        return redirect(url_for('verified_results_dashboard', index=index_number, receipt=receipt))
    
    # Render directly instead of redirecting
    qualifying_courses = courses_data['courses']
    
    # Group courses by collection
    courses_by_collection = {}
    for course in qualifying_courses:
        if level == 'degree':
            collection_name = course.get('cluster', 'Other')
        else:
            collection_name = course.get('collection', 'Other')
        
        if collection_name not in courses_by_collection:
            courses_by_collection[collection_name] = []
        courses_by_collection[collection_name].append(course)
    
    print(f"✅ Loaded {len(qualifying_courses)} {level} courses")
    
    return render_template('collection_results.html', 
                         courses=qualifying_courses,
                         courses_by_collection=courses_by_collection,
                         user_grades={}, 
                         user_mean_grade=None,
                         user_cluster_points={},
                         subjects=SUBJECTS, 
                         email=f"verified_{index_number}@temp.com", 
                         index_number=index_number,
                         flow=level)
@app.route('/debug/verify-test')
def debug_verify_test():
    """Test endpoint to verify the verification flow"""
    if database_connected:
        # Check recent payments
        recent_payments = list(user_payments_collection.find().sort('created_at', -1).limit(5))
        recent_courses = list(user_courses_collection.find().sort('created_at', -1).limit(5))
        
        return jsonify({
            'recent_payments': [
                {
                    'index_number': p.get('index_number'),
                    'mpesa_receipt': p.get('mpesa_receipt'),
                    'transaction_ref': p.get('transaction_ref'),
                    'payment_confirmed': p.get('payment_confirmed'),
                    'level': p.get('level')
                } for p in recent_payments
            ],
            'recent_courses': [
                {
                    'index_number': c.get('index_number'),
                    'level': c.get('level'),
                    'course_count': len(c.get('courses', [])),
                    'has_courses': bool(c.get('courses'))
                } for c in recent_courses
            ]
        })
    else:
        return jsonify({'error': 'Database not connected'})

@app.route('/verified-results')
def show_verified_results():
    """Show verified results page"""
    index_number = request.args.get('index')
    receipt = request.args.get('receipt')
    
    if not index_number or not receipt:
        flash("Invalid verification parameters", "error")
        return redirect(url_for('index'))
    
    # Get all courses for this user
    user_courses = {}
    if database_connected:
        levels = ['degree', 'diploma', 'certificate', 'artisan', 'kmtc']
        for level in levels:
            courses_data = user_courses_collection.find_one({
                'index_number': index_number,
                'level': level
            })
            if courses_data and courses_data.get('courses'):
                user_courses[level] = courses_data['courses']
    
    return render_template('verified_results.html', 
                         user_courses=user_courses,
                         index_number=index_number,
                         receipt=receipt)

# --- Debug and Testing Routes ---
@app.route('/debug/database')
def debug_database():
    status = {
        'database_connected': database_connected,
        'collections_initialized': {
            'user_payments': user_payments_collection is not None,
            'user_courses': user_courses_collection is not None
        },
        'session_keys': list(session.keys()) if session else []
    }
    
    if database_connected:
        try:
            status['document_counts'] = {
                'user_payments': user_payments_collection.count_documents({}),
                'user_courses': user_courses_collection.count_documents({})
            }
        except Exception as e:
            status['error'] = str(e)
    
    return jsonify(status)

@app.route('/debug/payment-status')
def debug_payment_status():
    email = session.get('email')
    index_number = session.get('index_number')
    flow = session.get('current_flow')
    
    status = {
        'email': email,
        'index_number': index_number,
        'current_flow': flow,
        'session_keys': list(session.keys()),
        'session_payment_status': {
            'paid_degree': session.get('paid_degree'),
            'paid_diploma': session.get('paid_diploma'),
            'paid_certificate': session.get('paid_certificate'),
            'paid_artisan': session.get('paid_artisan'),
            'paid_kmtc': session.get('paid_kmtc'),
            'payment_confirmed': session.get('payment_confirmed')
        }
    }
    
    if email and index_number and flow:
        user_payment = get_user_payment(email, index_number, flow)
        status['database_payment'] = user_payment
    
    return jsonify(status)

@app.route('/force-results/<flow>')
def force_results(flow):
    session[f'paid_{flow}'] = True
    session['payment_confirmed'] = True
    session['email'] = session.get('email') or 'test@example.com'
    session['index_number'] = session.get('index_number') or '12345678901/2024'
    
    if flow == 'artisan' and not session.get('artisan_grades'):
        session['artisan_grades'] = {'MAT': 'C', 'ENG': 'C', 'KIS': 'C'}
        session['artisan_mean_grade'] = 'C'
    
    flash("Forced results display for testing", "info")
    return redirect(url_for('show_results', flow=flow))

@app.route('/debug/db-status')
def debug_db_status():
    status = {
        'database_connected': database_connected,
        'collections': {}
    }
    
    if database_connected:
        try:
            status['collections']['degree'] = db.list_collection_names()
            status['collections']['diploma'] = db_diploma.list_collection_names()
            status['collections']['certificate'] = db_certificate.list_collection_names()
            status['collections']['artisan'] = db_artisan.list_collection_names()
            status['collections']['kmtc'] = db_kmtc.list_collection_names()
            
            status['user_payments_count'] = user_payments_collection.count_documents({})
            status['user_courses_count'] = user_courses_collection.count_documents({})
            
        except Exception as e:
            status['error'] = str(e)
    
    return jsonify(status)

@app.route('/temp-bypass/<flow>')
def temp_bypass(flow):
    session[f'paid_{flow}'] = True
    session['email'] = 'test@example.com'
    session['index_number'] = '123456/2024'
    
    if flow == 'diploma':
        session['diploma_grades'] = {'MAT': 'B', 'ENG': 'B', 'KIS': 'B'}
        session['diploma_mean_grade'] = 'B'
        session['diploma_data_submitted'] = True
    
    flash("Temporarily bypassed payment for testing", "info")
    return redirect(url_for('show_results', flow=flow))

# --- Main Application Entry Point ---
if __name__ == "__main__":
    print("🚀 Starting KUCCPS Application...")
    print(f"📊 Database Connection Status: {'✅ Connected' if database_connected else '❌ Disconnected'}")
    app.run(host='0.0.0.0', port=8080, debug=False)