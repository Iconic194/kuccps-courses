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
import re

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
CLUSTER_NAMES = {
    'cluster_1': 'Law',
    'cluster_2': 'Business, Hospitality & Related',
    'cluster_3': 'Social Sciences, Media Studies, Fine Arts, Film, Animation, Graphics & Related',
    'cluster_4': 'Geosciences & Related',
    'cluster_5': 'Engineering, Engineering Technology & Related',
    'cluster_6': 'Architecture, Building Construction & Related',
    'cluster_7': 'Computing, IT & Related',
    'cluster_8': 'Agribusiness & Related',
    'cluster_9': 'General Science, Biological Sciences, Physics, Chemistry & Related',
    'cluster_10': 'Actuarial Science, Accountancy, Mathematics, Economics, Statistics & Related',
    'cluster_11': 'Interior Design, Fashion Design, Textiles & Related',
    'cluster_12': 'Sport Science & Related',
    'cluster_13': 'Medicine, Health, Veterinary Medicine & Related',
    'cluster_14': 'History, Archeology & Related',
    'cluster_15': 'Agriculture, Animal Health, Food Science, Nutrition Dietetics, Environmental Sciences, Natural Resources & Related',
    'cluster_16': 'Geography & Related',
    'cluster_17': 'French & German',
    'cluster_18': 'Music & Related',
    'cluster_19': 'Education & Related',
    'cluster_20': 'Religious Studies, Theology, Islamic Studies & Related'
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
user_baskets_collection = None
database_connected = False

def initialize_database():
    """Initialize database connections with robust error handling"""
    global db, db_user_data, db_diploma, db_kmtc, db_certificate, db_artisan
    global user_payments_collection, user_courses_collection, user_baskets_collection, database_connected
    
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
            user_baskets_collection = db_user_data['user_baskets']
            
            # Create indexes
            user_payments_collection.create_index([("email", 1), ("index_number", 1), ("level", 1)])
            user_payments_collection.create_index([("transaction_ref", 1)])
            user_payments_collection.create_index([("payment_confirmed", 1)])
            user_courses_collection.create_index([("email", 1), ("index_number", 1), ("level", 1)])
            user_baskets_collection.create_index([("index_number", 1)])
            user_baskets_collection.create_index([("email", 1)])
            user_baskets_collection.create_index([("created_at", 1)])
            
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
def save_user_payment(email, index_number, level, transaction_ref=None, amount=1):
    """Save user payment information to payments collection"""
    if not database_connected:
        session_key = f'{level}_payment_{index_number}'
        session[session_key] = {
            'email': email,
            'index_number': index_number,
            'level': level,
            'transaction_ref': transaction_ref,
            'payment_amount': amount,
            'payment_confirmed': False,
            'created_at': datetime.now().isoformat()
        }
        return
        
    payment_record = {
        'email': email,
        'index_number': index_number,
        'level': level,
        'transaction_ref': transaction_ref,
        'payment_amount': amount,
        'payment_confirmed': False,
        'created_at': datetime.now()
    }
    
    try:
        result = user_payments_collection.update_one(
            {'email': email, 'index_number': index_number, 'level': level},
            {'$set': payment_record},
            upsert=True
        )
        print(f"✅ Payment record saved for {email}, amount: {amount}")
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

def check_existing_user_data(email, index_number):
    """Check if user details already exist in the database"""
    if not database_connected:
        return False
        
    try:
        # Check if user has any payment records
        existing_payments = user_payments_collection.find_one({
            '$or': [
                {'email': email},
                {'index_number': index_number}
            ],
            'payment_confirmed': True
        })
        
        # Check if user has any course records
        existing_courses = user_courses_collection.find_one({
            '$or': [
                {'email': email},
                {'index_number': index_number}
            ]
        })
        
        return existing_payments is not None or existing_courses is not None
        
    except Exception as e:
        print(f"❌ Error checking existing user data: {str(e)}")
        return False

def get_user_courses_data(email, index_number, level):
    """Get user courses from database with fallback to session"""
    if database_connected:
        try:
            courses_data = user_courses_collection.find_one(
                {'email': email, 'index_number': index_number, 'level': level}
            )
            if courses_data and 'courses' in courses_data:
                # Convert ObjectId to string for courses
                converted_courses = []
                for course in courses_data['courses']:
                    course_dict = dict(course)
                    if '_id' in course_dict and isinstance(course_dict['_id'], ObjectId):
                        course_dict['_id'] = str(course_dict['_id'])
                    converted_courses.append(course_dict)
                courses_data['courses'] = converted_courses
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
                
                # Also mark the category as paid in session
                level = session[key].get('level')
                if level:
                    session[f'paid_{level}'] = True
                
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

# --- Course Processing Functions ---
def process_courses_after_payment(email, index_number, flow):
    """Process and save courses after payment confirmation"""
    print(f"🎯 Processing courses for {flow} after payment confirmation")
    
    try:
        qualifying_courses = []
        user_grades = {}
        user_mean_grade = None
        user_cluster_points = {}
        
        # Get the appropriate data based on flow
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
        
        # Save courses to database
        if qualifying_courses:
            save_user_courses(email, index_number, flow, qualifying_courses)
            print(f"✅ Processed and saved {len(qualifying_courses)} {flow} courses")
            return True
        else:
            print(f"⚠️ No qualifying courses found for {flow}")
            return False
            
    except Exception as e:
        print(f"❌ Error processing courses after payment: {str(e)}")
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
        
        if response.status_code != 200:
            print(f"❌ MPesa OAuth failed with status: {response.status_code}")
            return None
            
        resp_json = response.json()
        access_token = resp_json.get('access_token')
        
        if not access_token:
            print('❌ No access_token in MPesa OAuth response')
            return None
            
        print("✅ MPesa access token obtained successfully")
        return access_token
        
    except Exception as e:
        print('❌ MPesa OAuth error:', str(e))
        return None

def initiate_stk_push(phone, amount=1):
    """Initiate MPesa STK push payment"""
    print(f"📱 Initiating STK push for phone: {phone}, amount: {amount}")
    
    # Format phone number
    if phone.startswith('0') and len(phone) == 10:
        phone = '254' + phone[1:]
    elif phone.startswith('+254') and len(phone) == 13:
        phone = phone[1:]
    elif len(phone) == 9:
        phone = '254' + phone
    
    print(f"📞 Formatted phone: {phone}")
    
    try:
        access_token = get_mpesa_access_token()
        if not access_token:
            return {'error': 'Failed to get MPesa access token'}
            
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
        
        # Use the actual callback URL for your deployed app
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
            "TransactionDesc": f"Course Qualification - Ksh {amount}"
        }
        
        print(f"📤 Sending STK push request to MPesa...")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        print(f"📥 MPesa response status: {response.status_code}")
        print(f"📥 MPesa response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            return {'error': f'MPesa API returned status {response.status_code}', 'details': response.text}
        
    except Exception as e:
        print(f"❌ Error initiating STK push: {str(e)}")
        return {'error': str(e)}

# --- Pricing and Category Management Functions ---
def has_user_paid_for_category(email, index_number, category):
    """Check if user has already paid for a specific category - STRICTER VERSION"""
    # First check session
    session_paid = session.get(f'paid_{category}')
    if session_paid:
        print(f"✅ Session shows paid for {category}")
        return True
    
    if not database_connected:
        return False
    
    try:
        # STRICTER database check - must have confirmed payment
        payment_data = user_payments_collection.find_one({
            '$or': [
                {'email': email},
                {'index_number': index_number}
            ],
            'level': category,
            'payment_confirmed': True
        })
        
        if payment_data:
            print(f"✅ Database shows confirmed payment for {category}")
            # Update session to reflect this
            session[f'paid_{category}'] = True
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error checking category payment: {str(e)}")
        return False
    
@app.route('/clear-session')
def clear_session():
    """Clear session data - useful for testing and preventing session issues"""
    session.clear()
    flash("Session cleared successfully", "info")
    return redirect(url_for('index'))

def get_user_paid_categories(email, index_number):
    """Get list of course levels that user has already paid for"""
    paid_categories = []
    
    if not database_connected:
        # Check session for paid categories
        for level in ['degree', 'diploma', 'certificate', 'artisan', 'kmtc']:
            if session.get(f'paid_{level}'):
                paid_categories.append(level)
        return paid_categories
    
    try:
        # Check database for paid categories
        paid_payments = user_payments_collection.find({
            '$or': [
                {'email': email},
                {'index_number': index_number}
            ],
            'payment_confirmed': True
        })
        
        for payment in paid_payments:
            level = payment.get('level')
            if level and level not in paid_categories:
                paid_categories.append(level)
                
    except Exception as e:
        print(f"❌ Error getting user paid categories: {str(e)}")
    
    return paid_categories

def get_user_existing_data(email, index_number):
    """Get all existing user data including payments and courses"""
    user_data = {
        'payments': [],
        'courses': [],
        'paid_categories': []
    }
    
    if not database_connected:
        return user_data
    
    try:
        # Get payment records
        payments = user_payments_collection.find({
            '$or': [
                {'email': email},
                {'index_number': index_number}
            ]
        })
        user_data['payments'] = list(payments)
        
        # Get course records
        courses = user_courses_collection.find({
            '$or': [
                {'email': email},
                {'index_number': index_number}
            ]
        })
        user_data['courses'] = list(courses)
        
        # Get paid categories
        user_data['paid_categories'] = get_user_paid_categories(email, index_number)
        
    except Exception as e:
        print(f"❌ Error getting user existing data: {str(e)}")
    
    return user_data

# --- Basket Database Functions ---
def save_user_basket(email, index_number, basket_data):
    """Save user basket to database"""
    # Ensure basket_data is a list and process items
    if not isinstance(basket_data, list):
        print(f"⚠️ Basket data is not a list, converting: {type(basket_data)}")
        if isinstance(basket_data, dict):
            basket_data = [basket_data]
        else:
            basket_data = []
    
    processed_basket = []
    for item in basket_data:
        if isinstance(item, dict):
            # Ensure added_at field exists
            if 'added_at' not in item:
                item['added_at'] = datetime.now().isoformat()
            # Ensure basket_id exists
            if 'basket_id' not in item:
                item['basket_id'] = str(ObjectId())
            processed_basket.append(item)
    
    if not database_connected:
        session['course_basket'] = processed_basket
        print(f"💾 Basket saved to session: {len(processed_basket)} items")
        return True
        
    basket_record = {
        'email': email,
        'index_number': index_number,
        'basket': processed_basket,
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        'is_active': True
    }
    
    try:
        result = user_baskets_collection.update_one(
            {'index_number': index_number},
            {'$set': basket_record},
            upsert=True
        )
        print(f"✅ Basket saved to database for {index_number} with {len(processed_basket)} courses")
        # Also update session
        session['course_basket'] = processed_basket
        return True
    except Exception as e:
        print(f"❌ Error saving user basket: {str(e)}")
        session['course_basket'] = processed_basket
        return False

def get_user_basket_by_index(index_number):
    """Get user basket from database by index number with proper error handling and validation"""
    print(f"🛒 Loading basket for index: {index_number}")
    
    # Initialize default return value
    processed_basket = []
    
    # Check if database is connected
    if not database_connected:
        print("ℹ️ Database not connected, using session basket")
        session_basket = session.get('course_basket')
        
        # Handle different session basket types
        if session_basket is None:
            processed_basket = []
        elif isinstance(session_basket, list):
            processed_basket = session_basket
        elif isinstance(session_basket, dict):
            print("⚠️ Session basket is a dict, converting to list")
            processed_basket = [session_basket]
            # Fix the session to prevent future issues
            session['course_basket'] = processed_basket
            session.modified = True
        else:
            print(f"⚠️ Unexpected session basket type: {type(session_basket)}")
            processed_basket = []
        
        # Validate basket items
        validated_basket = []
        for item in processed_basket:
            if isinstance(item, dict) and (item.get('programme_name') or item.get('course_name')):
                validated_basket.append(item)
            else:
                print(f"⚠️ Skipping invalid session basket item: {item}")
        
        print(f"📦 Session basket loaded: {len(validated_basket)} valid items")
        return validated_basket
    
    # Database is connected - try to load from database
    try:
        print(f"🔍 Searching database for basket of index: {index_number}")
        basket_data = user_baskets_collection.find_one({
            'index_number': index_number,
            'is_active': True
        })
        
        if basket_data:
            print(f"✅ Found basket data in database for {index_number}")
            basket_items = basket_data.get('basket', [])
            
            # Ensure basket_items is a list
            if not isinstance(basket_items, list):
                print(f"⚠️ Database basket is not a list: {type(basket_items)}")
                if isinstance(basket_items, dict):
                    basket_items = [basket_items]
                else:
                    basket_items = []
            
            # Validate and process basket items
            for item in basket_items:
                if isinstance(item, dict):
                    # Ensure required fields
                    if 'programme_name' not in item and 'course_name' not in item:
                        print(f"⚠️ Skipping basket item missing name: {item}")
                        continue
                    
                    # Ensure basket_id exists
                    if 'basket_id' not in item:
                        item['basket_id'] = str(ObjectId())
                    
                    # Ensure added_at exists
                    if 'added_at' not in item:
                        item['added_at'] = datetime.now().isoformat()
                    
                    # Ensure source is set
                    if 'source' not in item:
                        item['source'] = 'database'
                    
                    processed_basket.append(item)
                else:
                    print(f"⚠️ Skipping non-dict basket item from database: {type(item)}")
            
            print(f"✅ Successfully loaded {len(processed_basket)} items from database")
            
            # Update session with the database basket for consistency
            session['course_basket'] = processed_basket
            session.modified = True
            print("🔄 Updated session with database basket")
            
        else:
            print(f"ℹ️ No active basket found in database for {index_number}")
            # If no basket in database, check session as fallback
            session_basket = session.get('course_basket', [])
            if session_basket:
                if isinstance(session_basket, list):
                    processed_basket = session_basket
                elif isinstance(session_basket, dict):
                    processed_basket = [session_basket]
                
                print(f"🔄 Using session basket as fallback: {len(processed_basket)} items")
                
    except Exception as e:
        print(f"❌ Error getting user basket from database: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Fallback to session basket on database error
        session_basket = session.get('course_basket', [])
        if session_basket:
            if isinstance(session_basket, list):
                processed_basket = session_basket
            elif isinstance(session_basket, dict):
                processed_basket = [session_basket]
            print(f"🔄 Fallback to session basket due to database error: {len(processed_basket)} items")
    
    # Final validation of processed basket
    final_basket = []
    for item in processed_basket:
        if (isinstance(item, dict) and 
            (item.get('programme_name') or item.get('course_name')) and
            (item.get('programme_code') or item.get('course_code'))):
            final_basket.append(item)
        else:
            print(f"⚠️ Final validation: Skipping invalid basket item: {item}")
    
    print(f"🎯 Final basket count: {len(final_basket)} items")
    
    # Log basket contents for debugging
    if final_basket:
        course_names = [item.get('programme_name', item.get('course_name', 'Unknown')) for item in final_basket]
        print(f"📋 Basket contents: {course_names}")
    
    return final_basket

def clear_user_basket(index_number):
    """Clear user basket from database"""
    if database_connected:
        try:
            result = user_baskets_collection.update_one(
                {'index_number': index_number},
                {'$set': {
                    'basket': [],
                    'updated_at': datetime.now(),
                    'is_active': False
                }}
            )
            print(f"✅ Basket database record cleared for {index_number}")
            return True
        except Exception as e:
            print(f"❌ Error clearing user basket from database: {str(e)}")
            return False
    
    # Clear from session
    session.pop('course_basket', None)
    return True

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
        print(f"❌ Error in submit_diploma-grades: {str(e)}")
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
        print(f"❌ Error in submit_certificate-grades: {str(e)}")
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
        print(f"❌ Error in submit_artisan-grades: {str(e)}")
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
        print(f"❌ Error in submit_kmtc-grades: {str(e)}")
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
    
    email = request.form.get('email', '').strip().lower()
    index_number = request.form.get('index_number', '').strip()
    
    if not email or not index_number:
        flash("Email and KCSE Index Number are required.", "error")
        return redirect(url_for('enter_details', flow=flow))
    
    # Validate index number format
    if not re.match(r'^\d{11}/\d{4}$', index_number):
        flash("Invalid index number format. Must be 11 digits, slash, 4 digits (e.g., 12345678901/2024)", "error")
        return redirect(url_for('enter_details', flow=flow))
    
    # 🔥 STRICTER CHECK: Check if user has already paid for this SPECIFIC category
    if has_user_paid_for_category(email, index_number, flow):
        print(f"🚫 User {email} already paid for {flow}")
        flash(f"You have already paid for {flow.upper()} courses. Please use 'Already Made Payment' to view your results.", "warning")
        return redirect(url_for('index'))
    
    # 🔥 ADDITIONAL CHECK: Check if user is currently in process for this category
    existing_session_flow = session.get('current_flow')
    existing_session_email = session.get('email')
    existing_session_index = session.get('index_number')
    
    if (existing_session_flow == flow and 
        existing_session_email == email and 
        existing_session_index == index_number and
        session.get(f'paid_{flow}')):
        print(f"🚫 User trying to access same category again: {flow}")
        flash(f"You are already viewing {flow.upper()} courses. Please use your existing session.", "warning")
        return redirect(url_for('show_results', flow=flow))
    
    # Check if user already has any paid categories to determine pricing
    existing_categories = get_user_paid_categories(email, index_number)
    is_first_category = len(existing_categories) == 0
    amount = 2 if is_first_category else 1
    
    # Store in session
    session['email'] = email
    session['index_number'] = index_number
    session['current_flow'] = flow
    session['payment_amount'] = amount
    session['is_first_category'] = is_first_category
    
    # Clear any previous payment status for this flow to prevent conflicts
    session[f'paid_{flow}'] = False
    
    # Save initial payment record with amount
    save_user_payment(email, index_number, flow, amount=amount)
    
    # Show pricing information
    if is_first_category:
        flash(f"First category price: Ksh {amount}", "info")
    else:
        flash(f"Additional category price: Ksh {amount} (you already have {len(existing_categories)} paid categories)", "info")
    
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
        
        # Get the amount from session
        amount = session.get('payment_amount', 1)
        is_first_category = session.get('is_first_category', False)
        
        return render_template('payment.html', 
                             flow=flow, 
                             amount=amount, 
                             is_first_category=is_first_category)

    phone = request.form.get('phone', '').strip()
    if not phone:
        return {'success': False, 'error': 'Phone number is required for payment.'}, 400

    # Get the dynamic amount from session
    amount = session.get('payment_amount', 1)
    
    print(f"💳 Processing payment for {flow}, amount: {amount}, phone: {phone}")
    
    result = initiate_stk_push(phone, amount=amount)
    
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
            'amount': amount,
            'redirect_url': url_for('payment_wait', flow=flow, transaction_ref=transaction_ref)
        }

    error_message = result.get('errorDescription') or result.get('errorMessage') or 'Failed to initiate payment. Try again.'
    return {'success': False, 'error': error_message}, 400

@app.route('/payment-wait/<flow>')
def payment_wait(flow):
    email = session.get('email')
    index_number = session.get('index_number')
    transaction_ref = request.args.get('transaction_ref')
    
    if email and index_number and not transaction_ref:
        user_payment = get_user_payment(email, index_number, flow)
        if user_payment:
            transaction_ref = user_payment.get('transaction_ref')
            
    return render_template('payment_wait.html', 
                         flow=flow, 
                         transaction_ref=transaction_ref,
                         check_status_url=url_for('check_payment_status', flow=flow))

@app.route('/check-courses-ready/<flow>')
def check_courses_ready(flow):
    """Check if courses have been processed and are ready to display"""
    email = session.get('email')
    index_number = session.get('index_number')
    
    if not email or not index_number:
        return jsonify({'ready': False, 'error': 'Session data missing'})
    
    # Check if courses exist in database for this user and flow
    courses_data = get_user_courses_data(email, index_number, flow)
    
    if courses_data and courses_data.get('courses'):
        # Courses are ready
        return jsonify({
            'ready': True,
            'redirect_url': url_for('show_results', flow=flow)
        })
    else:
        # Courses not ready yet - try to process them
        print(f"🔄 Courses not found, attempting to process for {flow}")
        success = process_courses_after_payment(email, index_number, flow)
        
        if success:
            # Check again after processing
            courses_data = get_user_courses_data(email, index_number, flow)
            if courses_data and courses_data.get('courses'):
                return jsonify({
                    'ready': True,
                    'redirect_url': url_for('show_results', flow=flow)
                })
        
        # Courses not ready yet
        return jsonify({'ready': False})

@app.route('/check-payment-status/<flow>')
def check_payment_status(flow):
    email = session.get('email')
    index_number = session.get('index_number')
    
    if not email or not index_number:
        return {'paid': False, 'error': 'Session data missing'}
    
    # 🔥 MORE RELIABLE PAYMENT CHECK
    payment_confirmed = False
    
    # Check database first
    if database_connected:
        user_payment = user_payments_collection.find_one({
            'email': email, 
            'index_number': index_number, 
            'level': flow,
            'payment_confirmed': True
        })
        if user_payment:
            payment_confirmed = True
            session[f'paid_{flow}'] = True
            session['payment_confirmed'] = True
            print(f"✅ Database confirms payment for {flow}")
    
    # If not in database, check session
    if not payment_confirmed:
        session_paid = session.get(f'paid_{flow}') or session.get('payment_confirmed')
        if session_paid:
            payment_confirmed = True
            print(f"✅ Session confirms payment for {flow}")
    
    if payment_confirmed:
        session.modified = True
        
        # Check if courses need to be processed
        courses_data = get_user_courses_data(email, index_number, flow)
        if not courses_data or not courses_data.get('courses'):
            print(f"🔄 Payment confirmed but no courses found, processing now...")
            process_courses_after_payment(email, index_number, flow)
        
        return {
            'paid': True,
            'redirect_url': url_for('show_results', flow=flow)
        }
    else:
        print(f"❌ Payment not confirmed for {flow}")
        return {'paid': False}
# --- MPesa Callback Routes ---
@app.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    try:
        data = request.get_json(force=True)
        print(f"📥 MPesa callback received: {json.dumps(data, indent=2)}")
        
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
                print(f"✅ Payment callback processed successfully: {transaction_ref}")
                
                # 🔥 NEW: Get user details and process courses
                if database_connected:
                    payment_data = user_payments_collection.find_one({'transaction_ref': transaction_ref})
                    if payment_data:
                        email = payment_data.get('email')
                        index_number = payment_data.get('index_number')
                        flow = payment_data.get('level')
                        
                        if email and index_number and flow:
                            print(f"🚀 Triggering course processing for {flow}")
                            process_courses_after_payment(email, index_number, flow)
                
                return {'success': True}, 200
            else:
                print(f"❌ Failed to mark payment confirmed: {transaction_ref}")
                return {'success': False}, 400
        else:
            print(f"❌ Invalid callback data: {data}")
            return {'success': False}, 400
            
    except Exception as e:
        print(f"❌ Error processing MPesa callback: {str(e)}")
        return {'success': False}, 400
@app.route('/about')
def about():
    return render_template('about.html')

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
    
    # 🔥 STRICTER PAYMENT VERIFICATION
    user_payment = get_user_payment(email, index_number, flow)
    session_paid = session.get(f'paid_{flow}')
    
    # Check if payment is confirmed in database OR session
    payment_confirmed = False
    if user_payment and user_payment.get('payment_confirmed'):
        payment_confirmed = True
        # Ensure session is updated
        session[f'paid_{flow}'] = True
    elif session_paid:
        payment_confirmed = True
        # If only in session, try to verify with database
        if database_connected and user_payment:
            # Double-check database
            fresh_payment = user_payments_collection.find_one({
                'email': email, 
                'index_number': index_number, 
                'level': flow,
                'payment_confirmed': True
            })
            if not fresh_payment:
                payment_confirmed = False
                session[f'paid_{flow}'] = False
    
    if not payment_confirmed:
        print(f"❌ Payment not confirmed for {flow}. User payment: {user_payment}, Session paid: {session_paid}")
        flash('Please complete payment to view your results.', 'error')
        return redirect(url_for('payment', flow=flow))
    
    # 🔥 PREVENT DUPLICATE ACCESS TO SAME CATEGORY
    # Check if user is trying to access same category again without proper flow
    current_flow = session.get('current_flow')
    if current_flow != flow:
        # User might be trying to access results directly without proper flow
        print(f"⚠️ Suspicious access: current_flow={current_flow}, requested_flow={flow}")
        # Still allow if they have paid, but log it
        if not has_user_paid_for_category(email, index_number, flow):
            flash('Invalid access attempt. Please complete the qualification process.', 'error')
            return redirect(url_for('index'))

    # Store the current flow for basket redirects
    session['current_flow'] = flow
    print(f"🔗 Stored current flow: {flow}")

    qualifying_courses = []
    user_grades = {}
    user_mean_grade = None
    user_cluster_points = {}
    
    try:
        # Get courses from database first (if they exist)
        courses_data = get_user_courses_data(email, index_number, flow)
        if courses_data and courses_data.get('courses'):
            qualifying_courses = courses_data['courses']
            print(f"✅ Loaded {len(qualifying_courses)} courses from database for {flow}")
        else:
            # Generate courses if not in database
            print(f"🔄 Courses not in database, generating for {flow}")
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
            
            # Save courses to database
            if qualifying_courses:
                save_user_courses(email, index_number, flow, qualifying_courses)
            
        # Convert ObjectId to string for JSON serialization in template
        converted_courses = []
        for course in qualifying_courses:
            course_dict = dict(course)
            if '_id' in course_dict and isinstance(course_dict['_id'], ObjectId):
                course_dict['_id'] = str(course_dict['_id'])
            converted_courses.append(course_dict)
        qualifying_courses = converted_courses
        
        # Group courses by collection with proper names
        courses_by_collection = {}
        for course in qualifying_courses:
            if flow == 'degree':
                collection_key = course.get('cluster', 'Other')
                # Use the proper cluster name for display
                collection_name = CLUSTER_NAMES.get(collection_key, collection_key)
            else:
                collection_key = course.get('collection', 'Other')
                collection_name = collection_key.replace('_', ' ').title()
            
            if collection_key not in courses_by_collection:
                courses_by_collection[collection_key] = {
                    'name': collection_name,
                    'courses': []
                }
            courses_by_collection[collection_key]['courses'].append(course)

        # Load user's existing basket from database
        if email and index_number:
            existing_basket = get_user_basket_by_index(index_number)
            if existing_basket:
                session['course_basket'] = existing_basket
        
        print(f"🎯 Displaying {len(qualifying_courses)} courses for {flow}")
        
        return render_template('collection_results.html', 
                             courses=qualifying_courses,
                             courses_by_collection=courses_by_collection,
                             user_grades=user_grades, 
                             user_mean_grade=user_mean_grade,
                             user_cluster_points=user_cluster_points,
                             subjects=SUBJECTS, 
                             email=email, 
                             index_number=index_number,
                             flow=flow,
                             cluster_names=CLUSTER_NAMES)
                             
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

# --- Payment Verification Routes ---
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
        if not re.match(r'^\d{11}/\d{4}$', index_number):
            return jsonify({'success': False, 'error': 'Invalid index number format. Must be 11 digits, slash, 4 digits (e.g., 12345678901/2024)'})
        
        print(f"🔍 Verifying payment for index: {index_number}, receipt: {mpesa_receipt}")
        
        # Find confirmed payments for this index number and receipt
        payment_found = False
        paid_categories = []
        
        if database_connected:
            payment_data = user_payments_collection.find({
                'index_number': index_number,
                'mpesa_receipt': mpesa_receipt,
                'payment_confirmed': True
            })
            
            for payment in payment_data:
                payment_found = True
                level = payment.get('level')
                if level and level not in paid_categories:
                    paid_categories.append(level)
        else:
            # Session fallback
            for key in session:
                if isinstance(session.get(key), dict):
                    payment_data = session[key]
                    if (payment_data.get('index_number') == index_number and 
                        payment_data.get('mpesa_receipt') == mpesa_receipt and
                        payment_data.get('payment_confirmed')):
                        payment_found = True
                        level = payment_data.get('level')
                        if level and level not in paid_categories:
                            paid_categories.append(level)
        
        if not payment_found:
            print(f"❌ No confirmed payment found for index: {index_number}, receipt: {mpesa_receipt}")
            return jsonify({'success': False, 'error': 'No confirmed payment found with these details. Please ensure payment was successful and try again.'})
        
        print(f"✅ Payment confirmed for index: {index_number}, categories: {paid_categories}")
        
        # Get courses for all paid categories
        user_courses = {}
        total_courses = 0
        
        if database_connected:
            for level in paid_categories:
                courses_data = user_courses_collection.find_one({
                    'index_number': index_number,
                    'level': level
                })
                if courses_data and courses_data.get('courses'):
                    course_count = len(courses_data['courses'])
                    user_courses[level] = {
                        'count': course_count
                    }
                    total_courses += course_count
                    print(f"📚 Found {course_count} {level} courses")
        
        if total_courses == 0:
            return jsonify({'success': False, 'error': 'No course results found for your payment. Please ensure you completed the qualification process.'})
        
        print(f"🎓 Total courses found: {total_courses} across {len(paid_categories)} categories")
        
        # Return success response with available categories
        return jsonify({
            'success': True,
            'payment_confirmed': True,
            'courses_count': total_courses,
            'levels': paid_categories,
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
    
    # Store verification in session
    session['verified_payment'] = True
    session['verified_index'] = index_number
    session['verified_receipt'] = receipt
    session['email'] = f"verified_{index_number}@temp.com"
    session['index_number'] = index_number
    
    # Load user's saved basket from database
    basket = get_user_basket_by_index(index_number)
    session['course_basket'] = basket
    
    return render_template('verified_dashboard.html',
                         user_courses=user_courses,
                         index_number=index_number,
                         receipt=receipt,
                         total_courses=total_courses,
                         basket_count=len(basket))

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
    
    # Store the current level for basket redirects
    session['current_level'] = level
    print(f"🔗 Stored current level for verified user: {level}")
    
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
    
    # Convert ObjectId to string for JSON serialization
    qualifying_courses = []
    for course in courses_data['courses']:
        course_dict = dict(course)
        # Convert _id from ObjectId to string if it exists
        if '_id' in course_dict and isinstance(course_dict['_id'], ObjectId):
            course_dict['_id'] = str(course_dict['_id'])
        qualifying_courses.append(course_dict)
    
    # Group courses by collection with proper names
    courses_by_collection = {}
    for course in qualifying_courses:
        if level == 'degree':
            collection_key = course.get('cluster', 'Other')
            # Use the proper cluster name for display
            collection_name = CLUSTER_NAMES.get(collection_key, collection_key)
        else:
            collection_key = course.get('collection', 'Other')
            collection_name = collection_key.replace('_', ' ').title()
        
        if collection_key not in courses_by_collection:
            courses_by_collection[collection_key] = {
                'name': collection_name,
                'courses': []
            }
        courses_by_collection[collection_key]['courses'].append(course)
    
    print(f"✅ Loaded {len(qualifying_courses)} {level} courses")
    
    # Set session data for basket and search functionality
    session['email'] = f"verified_{index_number}@temp.com"
    session['index_number'] = index_number
    session['verified_payment'] = True
    
    return render_template('collection_results.html', 
                         courses=qualifying_courses,
                         courses_by_collection=courses_by_collection,
                         user_grades={}, 
                         user_mean_grade=None,
                         user_cluster_points={},
                         subjects=SUBJECTS, 
                         email=f"verified_{index_number}@temp.com", 
                         index_number=index_number,
                         flow=level,
                         cluster_names=CLUSTER_NAMES)

# --- Course Basket Routes ---
@app.route('/add-to-basket', methods=['POST'])
def add_to_basket():
    try:
        course_data = request.get_json()
        print(f"📥 Adding course to basket: {course_data.get('programme_name', 'Unknown Course')}")
        
        # Get current flow/level
        current_level = session.get('current_level', session.get('current_flow', 'degree'))
        print(f"🔗 Stored current level: {current_level}")
        
        # Initialize course_basket as a list if it doesn't exist or is not a list
        if 'course_basket' not in session:
            session['course_basket'] = []
            print("🆕 Initialized new course basket")
        
        basket = session['course_basket']
        
        # Ensure basket is a list
        if not isinstance(basket, list):
            print(f"⚠️ Basket was not a list, converting: {type(basket)}")
            if isinstance(basket, dict):
                basket = [basket]
            else:
                basket = []
            session['course_basket'] = basket
        
        course_code = course_data.get('programme_code') or course_data.get('course_code')
        
        # Check for duplicates by programme_code
        existing_course = next((item for item in basket if (
            item.get('programme_code') == course_code or 
            item.get('course_code') == course_code
        )), None)
        
        if existing_course:
            print(f"⚠️ Course already in basket: {course_code}")
            return jsonify({
                'success': False,
                'error': 'Course already in basket',
                'basket_count': len(basket)
            })
        
        # Add basket_id and timestamp
        course_data['basket_id'] = str(ObjectId())
        course_data['added_at'] = datetime.now().isoformat()
        course_data['level'] = current_level
        
        # Add course to basket
        basket.append(course_data)
        session['course_basket'] = basket
        session.modified = True
        
        print(f"✅ Added course to basket. Total items: {len(basket)}")
        print(f"📊 Basket contents: {[item.get('programme_name', 'Unknown') for item in basket]}")
        
        # Save to database if user is verified
        email = session.get('email')
        index_number = session.get('index_number')
        if email and index_number:
            save_user_basket(email, index_number, basket)
        
        return jsonify({
            'success': True,
            'basket_count': len(basket),
            'message': 'Course added to basket successfully'
        })
        
    except Exception as e:
        print(f"❌ Error adding to basket: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'basket_count': len(session.get('course_basket', []))
        }), 500

@app.route('/remove-from-basket', methods=['POST'])
def remove_from_basket():
    """Remove a specific course from user's basket"""
    try:
        data = request.get_json()
        basket_id = data.get('basket_id')
        
        if not basket_id:
            return jsonify({'success': False, 'error': 'No basket ID provided'})
        
        # Get user info
        email = session.get('email')
        index_number = session.get('index_number')
        
        # For verified users, get from verified_index
        if not index_number:
            index_number = session.get('verified_index')
            if index_number:
                email = f"verified_{index_number}@temp.com"
        
        if not index_number:
            return jsonify({'success': False, 'error': 'User not identified'})
        
        print(f"🗑️ Removing item {basket_id} from basket for user: {index_number}")
        
        # Remove from session first
        basket_count = 0
        if 'course_basket' in session:
            session['course_basket'] = [course for course in session['course_basket'] 
                                      if course.get('basket_id') != basket_id]
            basket_count = len(session['course_basket'])
            session.modified = True
            print(f"✅ Removed from session. New count: {basket_count}")
        
        # Remove from database
        if database_connected:
            try:
                # Get current basket from database
                basket_data = user_baskets_collection.find_one({
                    'index_number': index_number,
                    'is_active': True
                })
                
                if basket_data and 'basket' in basket_data:
                    # Filter out the item to remove
                    updated_basket = [course for course in basket_data['basket'] 
                                    if course.get('basket_id') != basket_id]
                    
                    # Update database
                    result = user_baskets_collection.update_one(
                        {'index_number': index_number},
                        {'$set': {
                            'basket': updated_basket,
                            'updated_at': datetime.now()
                        }}
                    )
                    
                    basket_count = len(updated_basket)
                    print(f"✅ Removed from database. New count: {basket_count}")
                    
                    # Update session with the database state
                    session['course_basket'] = updated_basket
                    
            except Exception as db_error:
                print(f"❌ Error removing from database: {db_error}")
                # If database fails, we still have the session updated
        
        return jsonify({
            'success': True, 
            'message': 'Course removed from basket',
            'basket_count': basket_count
        })
        
    except Exception as e:
        print(f"❌ Error removing from basket: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/clear-basket', methods=['POST'])
def clear_basket():
    try:
        # Get user info
        email = session.get('email')
        index_number = session.get('index_number')
        
        # For verified users, get from verified_index
        if not index_number:
            index_number = session.get('verified_index')
            if index_number:
                email = f"verified_{index_number}@temp.com"
        
        # Clear from session
        session['course_basket'] = []
        session.modified = True
        
        # Clear from database
        if index_number:
            clear_user_basket(index_number)
        
        print("🗑️ Basket cleared")
        
        return jsonify({
            'success': True,
            'message': 'Basket cleared successfully',
            'basket_count': 0
        })
        
    except Exception as e:
        print(f"❌ Error clearing basket: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/basket')
def view_basket():
    """Display basket page - only accessible via verified payment or results"""
    try:
        # Check access sources
        referer = request.headers.get('Referer', '')
        allowed_referrers = ['/results/', '/verified-dashboard', '/collection-courses/', '/verified-results/']
        is_from_allowed_page = any(ref in referer for ref in allowed_referrers)
        is_verified = session.get('verified_payment')
        
        # Get basket from appropriate source
        basket = []
        
        # First priority: verified users (from database)
        if is_verified:
            index_number = session.get('verified_index')
            if index_number:
                basket = get_user_basket_by_index(index_number)
                print(f"🛒 Loaded basket from database for verified user {index_number}: {len(basket)} items")
        
        # Second priority: session basket - with proper type checking
        if not basket:
            session_basket = session.get('course_basket')
            if session_basket:
                # Ensure session_basket is a list
                if isinstance(session_basket, list):
                    basket = session_basket
                    print(f"🛒 Loaded basket from session (list): {len(basket)} items")
                elif isinstance(session_basket, dict):
                    # Convert dict to list if it was incorrectly stored as dict
                    print("⚠️ Session basket was a dict, converting to list")
                    basket = [session_basket]  # Wrap the dict in a list
                    session['course_basket'] = basket  # Fix the session
                    session.modified = True
                else:
                    print(f"⚠️ Unexpected session basket type: {type(session_basket)}")
                    basket = []
            else:
                print("ℹ️ No session basket found")
        
        # Check if user has access
        has_basket = len(basket) > 0
        
        if not is_from_allowed_page and not is_verified and not has_basket:
            flash("Please browse your qualified courses first or verify your payment to use the basket", "warning")
            return redirect(url_for('index'))
        
        # Ensure basket items have proper structure and are valid
        processed_basket = []
        for item in basket:
            if isinstance(item, dict):
                # Ensure added_at field exists and is properly formatted
                if 'added_at' not in item:
                    item['added_at'] = datetime.now().isoformat()
                # Ensure basket_id exists
                if 'basket_id' not in item:
                    item['basket_id'] = str(ObjectId())
                # Ensure required fields exist
                if 'programme_name' in item or 'course_name' in item:
                    processed_basket.append(item)
                else:
                    print(f"⚠️ Skipping invalid basket item (missing name): {item}")
            else:
                # Skip invalid items
                print(f"⚠️ Skipping non-dict basket item: {type(item)} - {item}")
                continue
        
        basket_count = len(processed_basket)
        print(f"🎯 Final basket count for display: {basket_count}")
        
        # Update session with processed basket (in case we fixed any issues)
        if not is_verified:  # Only update session for non-verified users
            session['course_basket'] = processed_basket
            session.modified = True
        
        return render_template('basket.html', basket=processed_basket, basket_count=basket_count)
    
    except Exception as e:
        print(f"❌ Error in view_basket: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Reset corrupted basket
        session['course_basket'] = []
        session.modified = True
        
        flash("There was an error loading your basket. Please try again.", "error")
        return redirect(url_for('index'))

@app.route('/get-basket')
def get_basket():
    """Get user's current basket"""
    basket = session.get('course_basket', [])
    return jsonify({
        'success': True,
        'basket': basket,
        'count': len(basket)
    })

@app.route('/save-basket', methods=['POST'])
def save_basket():
    try:
        data = request.get_json()
        action = data.get('action', '')
        
        basket = session.get('course_basket', [])
        
        # Ensure basket is a list
        if not isinstance(basket, list):
            basket = []
            session['course_basket'] = basket
        
        print(f"💾 Saving basket with {len(basket)} items")
        
        # Save to database if user is identified
        email = session.get('email')
        index_number = session.get('index_number')
        if email and index_number:
            save_user_basket(email, index_number, basket)
        
        session.modified = True
        
        return jsonify({
            'success': True,
            'message': 'Basket saved successfully',
            'basket_count': len(basket)
        })
        
    except Exception as e:
        print(f"❌ Error saving basket: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/load-basket')
def load_basket():
    try:
        basket = session.get('course_basket', [])
        
        # Ensure basket is a list
        if not isinstance(basket, list):
            basket = []
            session['course_basket'] = basket
            session.modified = True
        
        print(f"📥 Loading basket with {len(basket)} items")
        
        return jsonify({
            'success': True,
            'basket': basket,
            'basket_count': len(basket)
        })
        
    except Exception as e:
        print(f"❌ Error loading basket: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'basket': [],
            'basket_count': 0
        })

@app.route('/reset-basket')
def reset_basket():
    session['course_basket'] = []
    session.modified = True
    return redirect('/basket')

# --- Search Function ---
def search_courses(query, courses):
    """Search courses by name, code, institution, or programme name"""
    if not query:
        return courses
    
    if not courses:
        return []
    
    query = query.lower().strip()
    results = []
    
    for course in courses:
        # Handle case where course might be None or invalid
        if not course:
            continue
            
        # Search in multiple possible field names - with safe defaults
        course_name = str(course.get('course_name', '')).lower()
        programme_name = str(course.get('programme_name', '')).lower()
        course_code = str(course.get('course_code', '')).lower()
        programme_code = str(course.get('programme_code', '')).lower()
        institution = str(course.get('institution_name', '')).lower()
        cluster = str(course.get('cluster', '')).lower()
        collection = str(course.get('collection', '')).lower()
        
        # Check all possible fields
        matches = (
            query in course_name or 
            query in programme_name or
            query in course_code or 
            query in programme_code or
            query in institution or
            query in cluster or
            query in collection
        )
        
        if matches:
            results.append(course)
    
    return results

@app.route('/search-courses/<flow>')
def search_courses_route(flow):
    """Search courses within a specific flow"""
    try:
        query = request.args.get('q', '').strip()
        
        print(f"🔍 Received search request for flow: {flow}, query: '{query}'")
        
        # Get user info for course filtering
        email = session.get('email')
        index_number = session.get('index_number')
        
        qualifying_courses = []
        
        # For verified users (accessed via Already Made Payment)
        if not email or not index_number:
            verified_index = session.get('verified_index')
            print(f"🔍 User verification status - verified_index: {verified_index}")
            
            if verified_index:
                # Get courses from database for verified users
                courses_data = user_courses_collection.find_one({
                    'index_number': verified_index,
                    'level': flow
                })
                if courses_data and courses_data.get('courses'):
                    qualifying_courses = courses_data['courses']
                    # Convert ObjectId to string for JSON serialization
                    converted_courses = []
                    for course in qualifying_courses:
                        if course:  # Check if course is not None
                            course_dict = dict(course)
                            if '_id' in course_dict and isinstance(course_dict['_id'], ObjectId):
                                course_dict['_id'] = str(course_dict['_id'])
                            converted_courses.append(course_dict)
                    qualifying_courses = converted_courses
                    print(f"✅ Loaded {len(qualifying_courses)} courses from database for verified user")
                else:
                    print(f"⚠️ No courses found in database for {flow} level")
                    qualifying_courses = []
            else:
                # Regular users without verification - get courses based on flow from session
                print(f"🔍 Regular user - checking session data for {flow}")
                if flow == 'degree':
                    user_grades = session.get('degree_grades', {})
                    user_cluster_points = session.get('degree_cluster_points', {})
                    if user_grades and user_cluster_points:
                        qualifying_courses = get_qualifying_courses(user_grades, user_cluster_points)
                        print(f"✅ Loaded {len(qualifying_courses)} degree courses from qualification check")
                    else:
                        qualifying_courses = []
                        print("⚠️ No degree grades or cluster points in session")
                elif flow == 'diploma':
                    user_grades = session.get('diploma_grades', {})
                    user_mean_grade = session.get('diploma_mean_grade', '')
                    if user_grades and user_mean_grade:
                        qualifying_courses = get_qualifying_diploma_courses(user_grades, user_mean_grade)
                        print(f"✅ Loaded {len(qualifying_courses)} diploma courses from qualification check")
                    else:
                        qualifying_courses = []
                        print("⚠️ No diploma grades or mean grade in session")
                elif flow == 'certificate':
                    user_grades = session.get('certificate_grades', {})
                    user_mean_grade = session.get('certificate_mean_grade', '')
                    if user_grades and user_mean_grade:
                        qualifying_courses = get_qualifying_certificate_courses(user_grades, user_mean_grade)
                        print(f"✅ Loaded {len(qualifying_courses)} certificate courses from qualification check")
                    else:
                        qualifying_courses = []
                        print("⚠️ No certificate grades or mean grade in session")
                elif flow == 'artisan':
                    user_grades = session.get('artisan_grades', {})
                    user_mean_grade = session.get('artisan_mean_grade', '')
                    if user_grades and user_mean_grade:
                        qualifying_courses = get_qualifying_artisan_courses(user_grades, user_mean_grade)
                        print(f"✅ Loaded {len(qualifying_courses)} artisan courses from qualification check")
                    else:
                        qualifying_courses = []
                        print("⚠️ No artisan grades or mean grade in session")
                elif flow == 'kmtc':
                    user_grades = session.get('kmtc_grades', {})
                    user_mean_grade = session.get('kmtc_mean_grade', '')
                    if user_grades and user_mean_grade:
                        qualifying_courses = get_qualifying_kmtc_courses(user_grades, user_mean_grade)
                        print(f"✅ Loaded {len(qualifying_courses)} KMTC courses from qualification check")
                    else:
                        qualifying_courses = []
                        print("⚠️ No KMTC grades or mean grade in session")
                else:
                    qualifying_courses = []
                    print(f"⚠️ Unknown flow type: {flow}")
        else:
            # Regular users with session data - get courses based on flow
            print(f"🔍 Regular user with session - getting {flow} courses")
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
        
        # Ensure qualifying_courses is a list
        if not isinstance(qualifying_courses, list):
            print(f"⚠️ qualifying_courses is not a list, converting: {type(qualifying_courses)}")
            qualifying_courses = []
        
        print(f"🔍 Before search: {len(qualifying_courses)} courses available")
        
        # Perform search
        if query:
            search_results = search_courses(query, qualifying_courses)
            print(f"🔍 After search: {len(search_results)} courses match '{query}'")
        else:
            search_results = qualifying_courses
            print(f"🔍 No query, returning all {len(search_results)} courses")
        
        # Ensure all courses have proper string IDs
        final_results = []
        for course in search_results:
            if course and isinstance(course, dict):
                course_copy = course.copy()
                if '_id' in course_copy and isinstance(course_copy['_id'], ObjectId):
                    course_copy['_id'] = str(course_copy['_id'])
                final_results.append(course_copy)
            elif course:
                final_results.append(course)
        
        print(f"🔍 Final results: {len(final_results)} courses")
        
        return jsonify({
            'success': True,
            'results': final_results,
            'count': len(final_results),
            'query': query
        })
        
    except Exception as e:
        print(f"❌ Error searching courses in {flow}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': f'Search failed: {str(e)}',
            'results': [],
            'count': 0,
            'query': query or ''
        })

# --- Debug and Testing Routes ---
@app.route('/debug/database')
def debug_database():
    status = {
        'database_connected': database_connected,
        'collections_initialized': {
            'user_payments': user_payments_collection is not None,
            'user_courses': user_courses_collection is not None,
            'user_baskets': user_baskets_collection is not None
        },
        'session_keys': list(session.keys()) if session else []
    }
    
    if database_connected:
        try:
            status['document_counts'] = {
                'user_payments': user_payments_collection.count_documents({}),
                'user_courses': user_courses_collection.count_documents({}),
                'user_baskets': user_baskets_collection.count_documents({})
            }
        except Exception as e:
            status['error'] = str(e)
    
    return jsonify(status)

@app.route('/debug/basket-status')
def debug_basket_status():
    """Debug route to check basket status"""
    status = {
        'session_keys': list(session.keys()),
        'session_basket': session.get('course_basket', []),
        'session_basket_count': len(session.get('course_basket', [])),
        'verified_payment': session.get('verified_payment'),
        'verified_index': session.get('verified_index'),
        'email': session.get('email'),
        'index_number': session.get('index_number')
    }
    
    if session.get('verified_index'):
        db_basket = get_user_basket_by_index(session['verified_index'])
        status['database_basket'] = db_basket
        status['database_basket_count'] = len(db_basket)
    
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