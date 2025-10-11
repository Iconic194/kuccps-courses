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
from datetime import timedelta


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
admin_activations_collection = None
database_connected = False

def initialize_database():
    """Initialize database connections with robust error handling"""
    global db, db_user_data, db_diploma, db_kmtc, db_certificate, db_artisan
    global user_payments_collection, user_courses_collection, user_baskets_collection, admin_activations_collection, database_connected
    
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
            
            # Initialize collections with consistent error handling
            collections_initialized = True
            
            try:
                user_courses_collection = db_user_data['user_courses']
                print("✅ User courses collection initialized")
            except Exception as e:
                print(f"❌ Error initializing user_courses collection: {str(e)}")
                collections_initialized = False
            
            try:
                user_payments_collection = db_user_data['user_payments']
                print("✅ User payments collection initialized")
            except Exception as e:
                print(f"❌ Error initializing user_payments collection: {str(e)}")
                collections_initialized = False
            
            try:
                user_baskets_collection = db_user_data['user_baskets']
                print("✅ User baskets collection initialized")
            except Exception as e:
                print(f"❌ Error initializing user_baskets collection: {str(e)}")
                collections_initialized = False
            
            try:
                admin_activations_collection = db_user_data['admin_activations']
                print("✅ Admin activations collection initialized")
            except Exception as e:
                print(f"❌ Error initializing admin_activations collection: {str(e)}")
                admin_activations_collection = None
                collections_initialized = False
            
            # Create indexes for collections that were successfully initialized
            if user_payments_collection is not None:
                try:
                    user_payments_collection.create_index([("email", 1), ("index_number", 1), ("level", 1)])
                    user_payments_collection.create_index([("transaction_ref", 1)])
                    user_payments_collection.create_index([("payment_confirmed", 1)])
                    print("✅ User payments indexes created")
                except Exception as e:
                    print(f"❌ Error creating user_payments indexes: {str(e)}")
            
            if user_courses_collection is not None:
                try:
                    user_courses_collection.create_index([("email", 1), ("index_number", 1), ("level", 1)])
                    print("✅ User courses indexes created")
                except Exception as e:
                    print(f"❌ Error creating user_courses indexes: {str(e)}")
            
            if user_baskets_collection is not None:
                try:
                    user_baskets_collection.create_index([("index_number", 1)])
                    user_baskets_collection.create_index([("email", 1)])
                    user_baskets_collection.create_index([("created_at", 1)])
                    print("✅ User baskets indexes created")
                except Exception as e:
                    print(f"❌ Error creating user_baskets indexes: {str(e)}")
            
            if admin_activations_collection is not None:
                try:
                    admin_activations_collection.create_index([("index_number", 1)])
                    admin_activations_collection.create_index([("mpesa_receipt", 1)])
                    admin_activations_collection.create_index([("is_active", 1)])
                    print("✅ Admin activations indexes created")
                except Exception as e:
                    print(f"❌ Error creating admin_activations indexes: {str(e)}")
            else:
                print("⚠️ Admin activations collection not available for indexing")
            
            database_connected = collections_initialized
            if collections_initialized:
                print("🎉 All database collections initialized successfully!")
            else:
                print("⚠️ Some collections failed to initialize, running in partial mode")
            
            return collections_initialized
            
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
    print("⚠️ Running in fallback mode - some database operations may be limited")
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
    """Save user course results to courses collection with better error handling"""
    print(f"💾 Saving {len(courses)} courses for {email}, {index_number}, {level}")
    
    if not courses:
        print("⚠️ No courses to save!")
        return False
        
    # Validate courses data
    valid_courses = []
    for course in courses:
        if isinstance(course, dict) and (course.get('programme_name') or course.get('course_name')):
            # Ensure each course has required fields
            course_copy = course.copy()
            if '_id' in course_copy and isinstance(course_copy['_id'], ObjectId):
                course_copy['_id'] = str(course_copy['_id'])
            valid_courses.append(course_copy)
        else:
            print(f"⚠️ Skipping invalid course: {course}")
    
    if not valid_courses:
        print("❌ No valid courses to save after validation")
        return False
        
    print(f"✅ Validated {len(valid_courses)} courses for saving")
    
    if not database_connected:
        session_key = f'{level}_courses_{index_number}'
        session[session_key] = {
            'email': email,
            'index_number': index_number,
            'level': level,
            'courses': valid_courses,
            'created_at': datetime.now().isoformat(),
            'courses_count': len(valid_courses)
        }
        print(f"✅ Courses saved to session: {len(valid_courses)} courses")
        return True
        
    courses_record = {
        'email': email,
        'index_number': index_number,
        'level': level,
        'courses': valid_courses,
        'courses_count': len(valid_courses),
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    
    try:
        # Use update_one with upsert to prevent duplicates
        result = user_courses_collection.update_one(
            {
                'email': email, 
                'index_number': index_number, 
                'level': level
            },
            {'$set': courses_record},
            upsert=True
        )
        
        if result.upserted_id:
            print(f"✅ New courses record created with {len(valid_courses)} courses")
        else:
            print(f"✅ Courses record updated with {len(valid_courses)} courses")
            
        # Verify the save worked
        saved_record = user_courses_collection.find_one({
            'email': email, 
            'index_number': index_number, 
            'level': level
        })
        
        if saved_record and 'courses' in saved_record:
            actual_count = len(saved_record['courses'])
            print(f"✅ Verified: {actual_count} courses in database")
            if actual_count != len(valid_courses):
                print(f"⚠️ Course count mismatch: expected {len(valid_courses)}, got {actual_count}")
            
        return True
            
    except Exception as e:
        print(f"❌ Error saving user courses: {str(e)}")
        # Fallback to session
        session_key = f'{level}_courses_{index_number}'
        session[session_key] = courses_record
        return False

@app.before_request
def protect_session_data():
    """Protect critical session data from accidental clearing"""
    # Store critical session keys that should never be cleared
    protected_keys = [
        'email', 'index_number', 'verified_payment', 'verified_index', 
        'verified_receipt', 'current_flow', 'current_level'
    ]
    
    # Check if this is a basket clearing request
    if request.endpoint == 'clear_basket':
        # Backup protected data
        request.protected_session_data = {}
        for key in protected_keys:
            if key in session:
                request.protected_session_data[key] = session[key]

@app.after_request
def restore_protected_data(response):
    """Restore protected session data after request"""
    if hasattr(request, 'protected_session_data'):
        for key, value in request.protected_session_data.items():
            if key not in session or session[key] != value:
                session[key] = value
    return response

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
    """Get user courses from database with better validation"""
    courses_data = None
    
    # Try database first
    if database_connected:
        try:
            courses_data = user_courses_collection.find_one({
                'email': email, 
                'index_number': index_number, 
                'level': level
            })
            
            if courses_data and 'courses' in courses_data:
                # Validate and convert courses
                valid_courses = []
                for course in courses_data['courses']:
                    if course and isinstance(course, dict):
                        course_dict = dict(course)
                        if '_id' in course_dict and isinstance(course_dict['_id'], ObjectId):
                            course_dict['_id'] = str(course_dict['_id'])
                        valid_courses.append(course_dict)
                
                courses_data['courses'] = valid_courses
                courses_data['courses_count'] = len(valid_courses)
                print(f"✅ Loaded {len(valid_courses)} courses from database for {level}")
                
        except Exception as e:
            print(f"❌ Error getting user courses from database: {str(e)}")
    
    # Fallback to session
    if not courses_data or not courses_data.get('courses'):
        session_key = f'{level}_courses_{index_number}'
        courses_data = session.get(session_key)
        
        if courses_data and 'courses' in courses_data:
            print(f"✅ Loaded {len(courses_data['courses'])} courses from session for {level}")
    
    return courses_data

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
    """Get MPesa access token for authentication with better error handling"""
    consumer_key = MPESA_CONSUMER_KEY
    consumer_secret = MPESA_CONSUMER_SECRET
    
    print(f"🔑 Getting MPesa access token...")
    print(f"🔑 Consumer Key: {consumer_key[:10]}...")
    
    try:
        response = requests.get(
            "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
            auth=HTTPBasicAuth(consumer_key, consumer_secret),
            timeout=30
        )
        
        print(f"📥 OAuth response status: {response.status_code}")
        print(f"📥 OAuth response headers: {dict(response.headers)}")
        
        if response.status_code != 200:
            print(f"❌ MPesa OAuth failed with status: {response.status_code}")
            print(f"📄 Response: {response.text}")
            return None
            
        resp_json = response.json()
        access_token = resp_json.get('access_token')
        
        if not access_token:
            print('❌ No access_token in MPesa OAuth response')
            print(f"📄 Full response: {resp_json}")
            return None
            
        print("✅ MPesa access token obtained successfully")
        print(f"🔑 Token: {access_token[:50]}...")
        return access_token
        
    except requests.exceptions.Timeout:
        print('❌ MPesa OAuth timeout')
        return None
    except requests.exceptions.ConnectionError:
        print('❌ MPesa OAuth connection error')
        return None
    except Exception as e:
        print(f'❌ MPesa OAuth error: {str(e)}')
        import traceback
        traceback.print_exc()
        return None
def initiate_stk_push(phone, amount=1):
    """Initiate MPesa STK push payment with better error handling"""
    print(f"📱 Initiating STK push for phone: {phone}, amount: {amount}")
    
    try:
        # Format phone number
        if phone.startswith('0') and len(phone) == 10:
            phone = '254' + phone[1:]
        elif phone.startswith('+254') and len(phone) == 13:
            phone = phone[1:]
        elif len(phone) == 9:
            phone = '254' + phone
        elif len(phone) == 12 and phone.startswith('254'):
            # Already in correct format
            pass
        else:
            return {'error': 'Invalid phone number format'}
    
        print(f"📞 Formatted phone: {phone}")
        
        # Validate amount
        if amount <= 0:
            return {'error': 'Invalid amount'}
        
        # Get access token
        access_token = get_mpesa_access_token()
        if not access_token:
            return {'error': 'Failed to get MPesa access token'}
            
        # Prepare STK push request
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        business_short_code = MPESA_SHORTCODE
        passkey = MPESA_PASSKEY
        
        print(f"🔑 Using ShortCode: {business_short_code}")
        print(f"🔑 Using Passkey: {passkey[:10]}...")  # Don't log full passkey
        
        data_to_encode = business_short_code + passkey + timestamp
        password = base64.b64encode(data_to_encode.encode()).decode('utf-8')
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        index_number = session.get('index_number', 'KUCCPS')
        
        # 🔥 IMPORTANT: Use correct callback URL based on environment
        if os.environ.get('FLASK_ENV') == 'production' or 'render.com' in os.environ.get('RENDER_EXTERNAL_HOSTNAME', ''):
            base_url = 'https://kuccps-courses.onrender.com'
        else:
            # For local development, use a service like ngrok or test with production URL
            base_url = 'https://kuccps-courses.onrender.com'
            # Alternatively, you can use local tunnel or keep as production URL
        
        callback_url = f"{base_url}/mpesa/callback"
        
        payload = {
            "BusinessShortCode": business_short_code,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone,
            "PartyB": business_short_code,
            "PhoneNumber": phone,
            "CallBackURL": callback_url,
            "AccountReference": index_number,
            "TransactionDesc": f"Course Qualification - Ksh {amount}"
        }
        
        print(f"📤 Sending STK push request to MPesa...")
        print(f"📞 Phone: {phone}")
        print(f"💰 Amount: {amount}")
        print(f"🏢 Business ShortCode: {business_short_code}")
        print(f"📝 Account Reference: {index_number}")
        print(f"🔗 Callback URL: {callback_url}")
        print(f"📦 Payload: {json.dumps(payload, indent=2)}")
        
        # Send request with timeout
        response = requests.post(
            "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        print(f"📥 MPesa response status: {response.status_code}")
        print(f"📥 MPesa response headers: {dict(response.headers)}")
        print(f"📥 MPesa response body: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ STK Push initiated successfully")
            print(f"📋 Response: {json.dumps(result, indent=2)}")
            
            # Check for specific error codes in success response
            if result.get('ResponseCode') == '0':
                print(f"🎯 STK Push sent to customer successfully")
                return result
            else:
                error_code = result.get('ResponseCode')
                error_message = result.get('ResponseDescription') or result.get('errorMessage') or 'Unknown error'
                print(f"❌ STK Push failed with code {error_code}: {error_message}")
                return {'error': f'MPesa Error {error_code}: {error_message}'}
        else:
            # Handle HTTP errors
            error_message = f'MPesa API returned status {response.status_code}'
            print(f"❌ {error_message}")
            
            # Try to get more details from response
            try:
                error_details = response.json()
                print(f"📄 Error details: {json.dumps(error_details, indent=2)}")
                return {'error': error_message, 'details': error_details}
            except:
                return {'error': error_message, 'details': response.text}
        
    except requests.exceptions.Timeout:
        error_msg = "MPesa API request timed out"
        print(f"❌ {error_msg}")
        return {'error': error_msg}
        
    except requests.exceptions.ConnectionError:
        error_msg = "Failed to connect to MPesa API"
        print(f"❌ {error_msg}")
        return {'error': error_msg}
        
    except Exception as e:
        error_msg = f"Unexpected error initiating STK push: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return {'error': error_msg}

def check_manual_activation(email, index_number, flow=None):
    """Check if user has manual activation from admin and mark as expired after use"""
    print(f"🔍 Checking manual activation for: {email}, {index_number}, flow: {flow}")
    
    # First check session for manual activations
    session_key = f'manual_activation_{index_number}'
    if session.get(session_key):
        print(f"✅ Manual activation found in session for {index_number}")
        
        # If flow is specified and we're using the activation, mark it as used
        if flow and database_connected and admin_activations_collection is not None:
            try:
                # Mark as expired in database
                result = admin_activations_collection.update_one(
                    {
                        'index_number': index_number,
                        'is_active': True
                    },
                    {
                        '$set': {
                            'is_active': False,
                            'used_for_flow': flow,
                            'used_at': datetime.now(),
                            'status': 'expired'
                        }
                    }
                )
                if result.modified_count > 0:
                    print(f"✅ Manual activation marked as expired for {flow}")
                    # Also remove from session to prevent reuse
                    session.pop(session_key, None)
            except Exception as e:
                print(f"❌ Error expiring manual activation: {str(e)}")
        
        return True
    
    # Also check by email in session
    for key in session.keys():
        if key.startswith('manual_activation_'):
            activation_data = session.get(key)
            if (isinstance(activation_data, dict) and 
                (activation_data.get('email') == email or activation_data.get('index_number') == index_number)):
                print(f"✅ Manual activation found in session by email/index match")
                
                # Mark as used if flow is specified
                if flow and database_connected and admin_activations_collection is not None:
                    try:
                        result = admin_activations_collection.update_one(
                            {
                                '$or': [
                                    {'email': email},
                                    {'index_number': index_number}
                                ],
                                'is_active': True
                            },
                            {
                                '$set': {
                                    'is_active': False,
                                    'used_for_flow': flow,
                                    'used_at': datetime.now(),
                                    'status': 'expired'
                                }
                            }
                        )
                        if result.modified_count > 0:
                            print(f"✅ Manual activation marked as expired for {flow}")
                            session.pop(key, None)
                    except Exception as e:
                        print(f"❌ Error expiring manual activation: {str(e)}")
                
                return True
    
    if not database_connected:
        print("ℹ️ Database not connected, only checking session")
        return False
    
    try:
        # Check database for active manual activation
        activation = admin_activations_collection.find_one({
            '$or': [
                {'email': email},
                {'index_number': index_number}
            ],
            'is_active': True
        })
        
        if activation:
            print(f"✅ Manual activation found in database for {email}/{index_number}")
            
            # If flow is specified, mark as expired immediately
            if flow:
                result = admin_activations_collection.update_one(
                    {'_id': activation['_id']},
                    {
                        '$set': {
                            'is_active': False,
                            'used_for_flow': flow,
                            'used_at': datetime.now(),
                            'status': 'expired'
                        }
                    }
                )
                if result.modified_count > 0:
                    print(f"✅ Manual activation marked as expired for {flow}")
            else:
                # Store in session for faster future access (only if not expiring immediately)
                session[session_key] = {
                    'email': activation.get('email'),
                    'index_number': activation.get('index_number'),
                    'mpesa_receipt': activation.get('mpesa_receipt'),
                    'activated_at': activation.get('activated_at')
                }
            
            return True
        else:
            print(f"❌ No manual activation found for {email}/{index_number}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking manual activation in database: {str(e)}")
        return False

def create_manual_activation_payment(email, index_number, flow, mpesa_receipt):
    """Create a payment record for manual activations so users can verify later"""
    print(f"💰 Creating payment record for manual activation: {email}, {index_number}, {flow}")
    
    payment_record = {
        'email': email,
        'index_number': index_number,
        'level': flow,
        'transaction_ref': f"MANUAL_{mpesa_receipt}",
        'mpesa_receipt': mpesa_receipt,
        'payment_amount': 0,  # Manual activations are free
        'payment_confirmed': True,
        'payment_method': 'manual_activation',
        'activated_by': 'admin',
        'created_at': datetime.now(),
        'payment_date': datetime.now()
    }
    
    if database_connected:
        try:
            result = user_payments_collection.update_one(
                {
                    'email': email,
                    'index_number': index_number,
                    'level': flow
                },
                {'$set': payment_record},
                upsert=True
            )
            print(f"✅ Manual activation payment record saved for {flow}")
            return True
        except Exception as e:
            print(f"❌ Error saving manual activation payment: {str(e)}")
            # Fallback to session
            session_key = f'{flow}_payment_{index_number}'
            session[session_key] = payment_record
            return False
    else:
        # Session fallback
        session_key = f'{flow}_payment_{index_number}'
        session[session_key] = payment_record
        return True
    
def create_manual_activation_payment(email, index_number, flow, mpesa_receipt):
    """Create a payment record for manual activations so users can verify later"""
    print(f"💰 Creating payment record for manual activation: {email}, {index_number}, {flow}")
    
    payment_record = {
        'email': email,
        'index_number': index_number,
        'level': flow,
        'transaction_ref': f"MANUAL_{mpesa_receipt}",
        'mpesa_receipt': mpesa_receipt,
        'payment_amount': 0,  # Manual activations are free
        'payment_confirmed': True,
        'payment_method': 'manual_activation',
        'activated_by': 'admin',
        'created_at': datetime.now(),
        'payment_date': datetime.now()
    }
    
    if database_connected:
        try:
            result = user_payments_collection.update_one(
                {
                    'email': email,
                    'index_number': index_number,
                    'level': flow
                },
                {'$set': payment_record},
                upsert=True
            )
            print(f"✅ Manual activation payment record saved for {flow}")
            return True
        except Exception as e:
            print(f"❌ Error saving manual activation payment: {str(e)}")
            # Fallback to session
            session_key = f'{flow}_payment_{index_number}'
            session[session_key] = payment_record
            return False
    else:
        # Session fallback
        session_key = f'{flow}_payment_{index_number}'
        session[session_key] = payment_record
        return True

def has_user_paid_for_category(email, index_number, category):
    """Check if user has already paid for a specific category - STRICTER VERSION"""
    # 🔥 NEW: Check manual activation first (without marking as used)
    manual_active = False
    if database_connected and admin_activations_collection is not None:
        try:
            manual_activation = admin_activations_collection.find_one({
                '$or': [
                    {'email': email},
                    {'index_number': index_number}
                ],
                'is_active': True
            })
            manual_active = manual_activation is not None
        except Exception as e:
            print(f"❌ Error checking manual activation in has_user_paid: {str(e)}")
    
    if manual_active:
        print(f"✅ Active manual activation found for {email}, allowing access to {category}")
        return True
    
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
    """Clear user basket from database without affecting session"""
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
    
    # Clear from session (only basket, not other data)
    if 'course_basket' in session:
        session['course_basket'] = []
        session.modified = True
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
    
    # 🔥 NEW: Check for manual activation first (pass flow parameter to mark as used)
    if check_manual_activation(email, index_number, flow):
        print(f"✅ Manual activation found for {email}, generating courses for {flow}")
        
        # Store user details in session
        session['email'] = email
        session['index_number'] = index_number
        session['current_flow'] = flow
        session[f'paid_{flow}'] = True  # Mark as paid since manually activated
        session['manual_activation'] = True
        
        # Get the M-Pesa receipt from the activation record to create payment record
        mpesa_receipt = None
        if database_connected and admin_activations_collection is not None:
            try:
                # Find the activation record (even if expired now)
                activation = admin_activations_collection.find_one({
                    '$or': [
                        {'email': email},
                        {'index_number': index_number}
                    ],
                    'mpesa_receipt': {'$exists': True}
                })
                if activation:
                    mpesa_receipt = activation.get('mpesa_receipt')
                    print(f"💰 Found M-Pesa receipt for payment record: {mpesa_receipt}")
            except Exception as e:
                print(f"❌ Error getting M-Pesa receipt from activation: {str(e)}")
        
        # Create payment record for manual activation so user can verify later
        if mpesa_receipt:
            create_manual_activation_payment(email, index_number, flow, mpesa_receipt)
        else:
            print("⚠️ No M-Pesa receipt found for manual activation, creating fallback payment record")
            # Create fallback payment record
            create_manual_activation_payment(email, index_number, flow, f"MANUAL_{index_number}")
        
        # Generate courses immediately for manually activated users
        try:
            qualifying_courses = []
            
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
                print(f"✅ Generated {len(qualifying_courses)} courses for manually activated user")
                
                # Redirect directly to results
                flash("Manual activation verified! Your courses have been generated. You can now view this category anytime using 'Already Made Payment'.", "success")
                return redirect(url_for('show_results', flow=flow))
            else:
                flash("No qualifying courses found for your grades. Please try a different course level.", "warning")
                return redirect(url_for(flow))
                
        except Exception as e:
            print(f"❌ Error generating courses for manually activated user: {str(e)}")
            flash("Error generating courses. Please try again.", "error")
            return redirect(url_for('enter_details', flow=flow))
    
    # 🔥 STRICTER CHECK: Check if user has already paid for this SPECIFIC category (for non-manual users)
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

@app.route('/admin/activations')
def admin_activations():
    """View all manual activations"""
    if not session.get('admin_logged_in'):
        flash("Please login as administrator", "error")
        return redirect(url_for('admin_login'))
    
    try:
        activations_data = []
        
        if database_connected and admin_activations_collection is not None:
            activations = list(admin_activations_collection.find().sort('activated_at', -1))
            
            for activation in activations:
                activation_data = {
                    'email': activation.get('email', 'N/A'),
                    'index_number': activation.get('index_number', 'N/A'),
                    'mpesa_receipt': activation.get('mpesa_receipt', 'N/A'),
                    'activation_type': activation.get('activation_type', 'manual'),
                    'activated_by': activation.get('activated_by', 'N/A'),
                    'activated_at': activation.get('activated_at', 'N/A'),
                    'is_active': activation.get('is_active', False),
                    'status': activation.get('status', 'unknown'),
                    'used_for_flow': activation.get('used_for_flow', 'Not used'),
                    'used_at': activation.get('used_at', 'N/A')
                }
                activations_data.append(activation_data)
        
        return render_template('admin_activations.html', activations=activations_data)
        
    except Exception as e:
        print(f"❌ Error loading admin activations: {str(e)}")
        flash("Error loading activation data", "error")
        return render_template('admin_activations.html', activations=[])
    
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
        print("🛒 Starting basket clearing process...")
        
        # BACKUP CRITICAL SESSION DATA BEFORE CLEARING
        critical_session_data = {}
        critical_keys = [
            'email', 'index_number', 'verified_payment', 'verified_index', 
            'verified_receipt', 'current_flow', 'current_level'
        ]
        
        # Backup all paid category status
        paid_categories = []
        for level in ['degree', 'diploma', 'certificate', 'artisan', 'kmtc']:
            if session.get(f'paid_{level}'):
                paid_categories.append(level)
                critical_session_data[f'paid_{level}'] = True
        
        # Backup other critical data
        for key in critical_keys:
            if key in session:
                critical_session_data[key] = session[key]
        
        print(f"🔐 Backed up session data: {list(critical_session_data.keys())}")
        print(f"💰 Paid categories backed up: {paid_categories}")
        
        # Get user info from backed up data
        email = critical_session_data.get('email')
        index_number = critical_session_data.get('index_number')
        
        # For verified users, get from verified_index
        if not index_number:
            index_number = critical_session_data.get('verified_index')
            if index_number:
                email = f"verified_{index_number}@temp.com"
        
        if not index_number:
            print("❌ No user identified for basket clearing")
            return jsonify({
                'success': False,
                'error': 'User not identified'
            })
        
        print(f"🗑️ Clearing basket for user: {index_number}")
        
        # Clear from session - ONLY the basket
        if 'course_basket' in session:
            session['course_basket'] = []
            session.modified = True
            print("✅ Basket cleared from session")
        
        # Clear from database
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
                if result.modified_count > 0:
                    print("✅ Basket cleared from database")
                else:
                    print("ℹ️ No basket found in database to clear")
            except Exception as db_error:
                print(f"❌ Error clearing basket from database: {db_error}")
        
        # RESTORE CRITICAL SESSION DATA
        for key, value in critical_session_data.items():
            session[key] = value
        session.modified = True
        
        print("✅ Basket cleared successfully with session protection")
        print(f"🔄 Restored session keys: {list(critical_session_data.keys())}")
        
        return jsonify({
            'success': True,
            'message': 'Basket cleared successfully',
            'basket_count': 0
        })
        
    except Exception as e:
        print(f"❌ Error clearing basket: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
@app.route('/basket')
def view_basket():
    """Display basket page - only accessible via verified payment or results"""
    try:
        print("🛒 Accessing basket page...")
        print(f"📋 Session keys: {list(session.keys())}")
        
        # Check if user has any paid categories or is verified
        has_paid_access = False
        paid_categories = []
        
        # Check for verified payment
        if session.get('verified_payment'):
            has_paid_access = True
            print("✅ Verified user accessing basket")
        
        # Check for regular paid categories
        for level in ['degree', 'diploma', 'certificate', 'artisan', 'kmtc']:
            if session.get(f'paid_{level}'):
                has_paid_access = True
                paid_categories.append(level)
        
        print(f"💰 Paid categories found: {paid_categories}")
        print(f"🔑 Has paid access: {has_paid_access}")
        
        # Get basket from appropriate source
        basket = []
        
        # First priority: verified users (from database)
        if session.get('verified_payment'):
            index_number = session.get('verified_index')
            if index_number:
                basket = get_user_basket_by_index(index_number)
                print(f"🛒 Loaded basket from database for verified user {index_number}: {len(basket)} items")
        
        # Second priority: session basket
        if not basket:
            session_basket = session.get('course_basket')
            if session_basket:
                if isinstance(session_basket, list):
                    basket = session_basket
                    print(f"🛒 Loaded basket from session (list): {len(basket)} items")
                elif isinstance(session_basket, dict):
                    basket = [session_basket]
                    session['course_basket'] = basket
                    session.modified = True
                    print("⚠️ Fixed session basket (was dict, now list)")
                else:
                    basket = []
                    print(f"⚠️ Unexpected session basket type: {type(session_basket)}")
        
        # Check if user has access
        has_basket = len(basket) > 0
        
        # Allow access if user has paid for any category OR has items in basket
        if not has_paid_access and not has_basket:
            print("🚫 No access - user hasn't paid and basket is empty")
            flash("Please browse your qualified courses first or verify your payment to use the basket", "warning")
            return redirect(url_for('index'))
        
        print(f"✅ Granting basket access to user")
        
        # Process basket items (your existing code)
        processed_basket = []
        for item in basket:
            if isinstance(item, dict):
                if 'added_at' not in item:
                    item['added_at'] = datetime.now().isoformat()
                if 'basket_id' not in item:
                    item['basket_id'] = str(ObjectId())
                if 'programme_name' in item or 'course_name' in item:
                    processed_basket.append(item)
        
        basket_count = len(processed_basket)
        print(f"🎯 Final basket count for display: {basket_count}")
        
        # Update session with processed basket
        if not session.get('verified_payment'):
            session['course_basket'] = processed_basket
            session.modified = True
        
        return render_template('basket.html', basket=processed_basket, basket_count=basket_count)
    
    except Exception as e:
        print(f"❌ Error in view_basket: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Reset corrupted basket but preserve other session data
        critical_data = {}
        for key in ['email', 'index_number', 'verified_payment', 'verified_index', 'current_flow']:
            if key in session:
                critical_data[key] = session[key]
        
        session.clear()
        for key, value in critical_data.items():
            session[key] = value
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

# --- Admin Routes ---
@app.route('/admin')
def admin_login():
    """Admin login page"""
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    """Admin dashboard - protected route"""
    if not session.get('admin_logged_in'):
        flash("Please login as administrator", "error")
        return redirect(url_for('admin_login'))
    
    return render_template('admin_dashboard.html')

@app.route('/admin/auth', methods=['POST'])
def admin_authentication():
    """Admin authentication endpoint"""
    username = request.form.get('username')
    password = request.form.get('password')
    
    # Simple hardcoded credentials (replace with secure authentication)
    if username == 'admin' and password == 'kuccps2025':
        session['admin_logged_in'] = True
        session['admin_username'] = username
        flash("Admin login successful", "success")
        return redirect(url_for('admin_dashboard'))
    else:
        flash("Invalid admin credentials", "error")
        return redirect(url_for('admin_login'))

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    flash("Admin logged out successfully", "info")
    return redirect(url_for('admin_login'))

@app.route('/admin/manual-activation', methods=['GET', 'POST'])
def admin_manual_activation():
    """Manual activation for users who paid but didn't get results"""
    if not session.get('admin_logged_in'):
        flash("Please login as administrator", "error")
        return redirect(url_for('admin_login'))
    
    # Calculate statistics for the template
    stats = {
        'active_count': 0,
        'used_count': 0, 
        'total_count': 0,
        'today_count': 0
    }
    
    if database_connected and admin_activations_collection is not None:
        try:
            stats['active_count'] = admin_activations_collection.count_documents({'is_active': True})
            stats['used_count'] = admin_activations_collection.count_documents({'is_active': False})
            stats['total_count'] = admin_activations_collection.count_documents({})
            
            # Today's activations
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            stats['today_count'] = admin_activations_collection.count_documents({
                'activated_at': {'$gte': today_start}
            })
        except Exception as e:
            print(f"❌ Error loading activation stats: {str(e)}")
    
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip().lower()
            index_number = request.form.get('index_number', '').strip()
            mpesa_receipt = request.form.get('mpesa_receipt', '').strip().upper()
            activation_type = request.form.get('activation_type', 'manual')
            
            if not email or not index_number or not mpesa_receipt:
                flash("All fields are required", "error")
                return redirect(url_for('admin_manual_activation'))
            
            # Validate index number format
            if not re.match(r'^\d{11}/\d{4}$', index_number):
                flash("Invalid index number format", "error")
                return redirect(url_for('admin_manual_activation'))
            
            # Validate M-Pesa receipt format
            if len(mpesa_receipt) != 10 or not mpesa_receipt.isalnum():
                flash("Invalid M-Pesa receipt format", "error")
                return redirect(url_for('admin_manual_activation'))
            
            print(f"🔧 Admin manual activation attempt: {email}, {index_number}, {mpesa_receipt}")
            print(f"🔧 Database connected: {database_connected}")
            print(f"🔧 Admin activations collection: {admin_activations_collection is not None}")
            
            # Create manual activation record
            activation_record = {
                'email': email,
                'index_number': index_number,
                'mpesa_receipt': mpesa_receipt,
                'activation_type': activation_type,
                'activated_by': session.get('admin_username', 'admin'),
                'activated_at': datetime.now(),
                'is_active': True,
                'status': 'active',
                'used_for_flow': None,
                'used_at': None
            }
            
            # Save to database
            if database_connected and admin_activations_collection is not None:
                try:
                    # Check if already activated (active or expired)
                    existing_activation = admin_activations_collection.find_one({
                        'index_number': index_number
                    })
                    
                    if existing_activation:
                        if existing_activation.get('is_active'):
                            flash(f"User {index_number} already has an active manual activation", "warning")
                            print(f"⚠️ User {index_number} already has active activation")
                        else:
                            # Update existing expired activation to active
                            result = admin_activations_collection.update_one(
                                {'index_number': index_number},
                                {'$set': {
                                    'is_active': True,
                                    'status': 'active',
                                    'activated_at': datetime.now(),
                                    'activated_by': session.get('admin_username', 'admin'),
                                    'used_for_flow': None,
                                    'used_at': None,
                                    'mpesa_receipt': mpesa_receipt,
                                    'email': email,
                                    'activation_type': activation_type
                                }}
                            )
                            if result.modified_count > 0:
                                flash(f"Reactivated manual activation for {email}", "success")
                                print(f"✅ Manual activation reactivated: {index_number}")
                                
                                # Update statistics after reactivation
                                stats['active_count'] += 1
                                stats['used_count'] -= 1
                            else:
                                flash("Failed to reactivate manual activation", "error")
                    else:
                        result = admin_activations_collection.insert_one(activation_record)
                        if result.inserted_id:
                            flash(f"Manual activation successful for {email}", "success")
                            print(f"✅ Manual activation saved to database: {result.inserted_id}")
                            
                            # Update statistics after new activation
                            stats['active_count'] += 1
                            stats['total_count'] += 1
                            stats['today_count'] += 1
                            
                            # Verify the record was saved
                            saved_record = admin_activations_collection.find_one({'_id': result.inserted_id})
                            if saved_record:
                                print(f"✅ Record verified in database: {saved_record}")
                            else:
                                print(f"❌ Record not found after insertion")
                        else:
                            flash("Failed to save manual activation", "error")
                        
                except Exception as e:
                    print(f"❌ Error saving manual activation to database: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    flash("Error saving activation record to database", "error")
            else:
                # Session fallback for manual activations
                session_key = f'manual_activation_{index_number}'
                session[session_key] = activation_record
                flash(f"Manual activation saved to session for {email} (database not available)", "success")
                print(f"✅ Manual activation saved to session: {session_key}")
            
            return redirect(url_for('admin_manual_activation'))
            
        except Exception as e:
            print(f"❌ Error in manual activation: {str(e)}")
            import traceback
            traceback.print_exc()
            flash("An error occurred during activation", "error")
            return redirect(url_for('admin_manual_activation'))
    
    return render_template('admin_manual_activation.html', 
                         active_count=stats['active_count'],
                         used_count=stats['used_count'],
                         total_count=stats['total_count'],
                         today_count=stats['today_count'])

@app.route('/debug/admin-activations')
def debug_admin_activations():
    """Debug route to check admin activations"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Not authorized'}), 403
    
    debug_info = {
        'database_connected': database_connected,
        'admin_activations_collection_exists': admin_activations_collection is not None,
        'total_activations': 0,
        'activations': []
    }
    
    if database_connected and admin_activations_collection is not None:
        try:
            activations = list(admin_activations_collection.find().sort('activated_at', -1).limit(10))
            debug_info['total_activations'] = admin_activations_collection.count_documents({})
            debug_info['activations'] = activations
        except Exception as e:
            debug_info['error'] = str(e)
    
    return jsonify(debug_info)

@app.route('/admin/payments')
def admin_payments():
    """View all payments and statistics"""
    if not session.get('admin_logged_in'):
        flash("Please login as administrator", "error")
        return redirect(url_for('admin_login'))
    
    try:
        payments_data = []
        statistics = {
            'total_payments': 0,
            'total_amount': 0,
            'first_category_count': 0,
            'additional_category_count': 0,
            'failed_payments': 0,
            'confirmed_payments': 0,
            'manual_activations': 0
        }
        
        if database_connected:
            # Get all payments
            all_payments = list(user_payments_collection.find().sort('created_at', -1))
            
            for payment in all_payments:
                payment_data = {
                    'email': payment.get('email', 'N/A'),
                    'index_number': payment.get('index_number', 'N/A'),
                    'level': payment.get('level', 'N/A'),
                    'payment_amount': payment.get('payment_amount', 0),
                    'payment_confirmed': payment.get('payment_confirmed', False),
                    'mpesa_receipt': payment.get('mpesa_receipt', 'N/A'),
                    'transaction_ref': payment.get('transaction_ref', 'N/A'),
                    'created_at': payment.get('created_at', 'N/A'),
                    'payment_date': payment.get('payment_date', 'N/A')
                }
                payments_data.append(payment_data)
                
                # Calculate statistics
                statistics['total_payments'] += 1
                statistics['total_amount'] += payment_data['payment_amount']
                
                if payment_data['payment_confirmed']:
                    statistics['confirmed_payments'] += 1
                    # Determine if first or additional category
                    if payment_data['payment_amount'] == 2:
                        statistics['first_category_count'] += 1
                    else:
                        statistics['additional_category_count'] += 1
                else:
                    statistics['failed_payments'] += 1
            
            # Get manual activations count
            statistics['manual_activations'] = admin_activations_collection.count_documents({'is_active': True})
                
        else:
            # Session fallback for statistics
            payments_data = []
        
        return render_template('admin_payments.html', 
                             payments=payments_data, 
                             statistics=statistics)
                             
    except Exception as e:
        print(f"❌ Error loading admin payments: {str(e)}")
        flash("Error loading payment data", "error")
        return render_template('admin_payments.html', payments=[], statistics={})

@app.route('/admin/users')
def admin_users():
    """View all users and their activities"""
    if not session.get('admin_logged_in'):
        flash("Please login as administrator", "error")
        return redirect(url_for('admin_login'))
    
    try:
        users_data = []
        
        if database_connected:
            # Get all unique users with their activities
            pipeline = [
                {
                    '$group': {
                        '_id': '$index_number',
                        'email': {'$first': '$email'},
                        'payment_count': {'$sum': 1},
                        'confirmed_payments': {
                            '$sum': {'$cond': [{'$eq': ['$payment_confirmed', True]}, 1, 0]}
                        },
                        'total_amount': {'$sum': '$payment_amount'},
                        'last_activity': {'$max': '$created_at'},
                        'levels': {'$addToSet': '$level'}
                    }
                },
                {'$sort': {'last_activity': -1}}
            ]
            
            user_activities = list(user_payments_collection.aggregate(pipeline))
            
            for user in user_activities:
                user_data = {
                    'index_number': user['_id'],
                    'email': user.get('email', 'N/A'),
                    'payment_count': user.get('payment_count', 0),
                    'confirmed_payments': user.get('confirmed_payments', 0),
                    'total_amount': user.get('total_amount', 0),
                    'last_activity': user.get('last_activity', 'N/A'),
                    'levels': user.get('levels', [])
                }
                users_data.append(user_data)
        
        return render_template('admin_users.html', users=users_data)
        
    except Exception as e:
        print(f"❌ Error loading admin users: {str(e)}")
        flash("Error loading user data", "error")
        return render_template('admin_users.html', users=[])

@app.route('/admin/system-health')
def admin_system_health():
    """System health and monitoring dashboard"""
    if not session.get('admin_logged_in'):
        flash("Please login as administrator", "error")
        return redirect(url_for('admin_login'))
    
    try:
        health_data = {
            'database_connected': database_connected,
            'session_keys_count': len(session.keys()) if session else 0,
            'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'application_uptime': 'N/A'
        }
        
        if database_connected:
            # Database statistics
            health_data['database_stats'] = {
                'user_payments': user_payments_collection.count_documents({}),
                'user_courses': user_courses_collection.count_documents({}),
                'user_baskets': user_baskets_collection.count_documents({}),
                'admin_activations': admin_activations_collection.count_documents({})
            }
            
            # Recent activities
            health_data['recent_activities'] = list(user_payments_collection.find()
                                                  .sort('created_at', -1)
                                                  .limit(10))
        
        return render_template('admin_system_health.html', health_data=health_data)
        
    except Exception as e:
        print(f"❌ Error loading system health: {str(e)}")
        flash("Error loading system health data", "error")
        return render_template('admin_system_health.html', health_data={})

# --- Debug and Testing Routes ---
@app.route('/debug/database')
def debug_database():
    status = {
        'database_connected': database_connected,
        'collections_initialized': {
            'user_payments': user_payments_collection is not None,
            'user_courses': user_courses_collection is not None,
            'user_baskets': user_baskets_collection is not None,
            'admin_activations': admin_activations_collection is not None
        },
        'session_keys': list(session.keys()) if session else []
    }
    
    if database_connected:
        try:
            status['document_counts'] = {
                'user_payments': user_payments_collection.count_documents({}),
                'user_courses': user_courses_collection.count_documents({}),
                'user_baskets': user_baskets_collection.count_documents({}),
                'admin_activations': admin_activations_collection.count_documents({})
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

@app.route('/contact')
def contact():
    return render_template("contact.html")
    
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