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
MONGODB_URI = "mongodb+srv://iconichean:1Loye8PM3YwlV5h4@cluster0.meufk73.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

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
                serverSelectionTimeoutMS=15000,
                connectTimeoutMS=30000,
                socketTimeoutMS=30000,
                retryWrites=True,
                retryReads=True
            )
            
            client.admin.command('ping', socketTimeoutMS=15000)
            print("✅ Successfully connected to MongoDB")
            
            # Initialize databases
            db = client['Degree']
            db_user_data = client['user_data']
            db_diploma = client['diploma']
            db_kmtc = client['kmtc']
            db_certificate = client['certificate']
            db_artisan = client['artisan']
            
            # Initialize collections - user_courses exists, user_payments will be created automatically
            user_courses_collection = db_user_data['user_courses']  # This exists
            user_payments_collection = db_user_data['user_payments']  # This will be created on first insert
            
            # Create indexes for better performance
            try:
                user_payments_collection.create_index([("email", 1), ("index_number", 1), ("level", 1)])
                user_payments_collection.create_index([("transaction_ref", 1)])
                user_payments_collection.create_index([("payment_confirmed", 1)])
                user_courses_collection.create_index([("email", 1), ("index_number", 1), ("level", 1)])
                print("✅ Database indexes created/verified")
            except Exception as index_error:
                print(f"⚠  Index creation warning: {index_error}")
            
            database_connected = True
            print("✅ All database collections initialized successfully")
            print("📊 Using collections:")
            print("   - user_courses (existing)")
            print("   - user_payments (will be created automatically)")
            return True
            
        except ServerSelectionTimeoutError as e:
            print(f"❌ MongoDB Server Selection Timeout (attempt {attempt + 1}): {str(e)}")
            if attempt < max_retries - 1:
                print("🔄 Retrying connection...")
                continue
            else:
                database_connected = False
                return False
                
        except ConnectionFailure as e:
            print(f"❌ MongoDB Connection Failure (attempt {attempt + 1}): {str(e)}")
            if attempt < max_retries - 1:
                print("🔄 Retrying connection...")
                continue
            else:
                database_connected = False
                return False
                
        except Exception as e:
            print(f"❌ Unexpected database connection error (attempt {attempt + 1}): {str(e)}")
            if attempt < max_retries - 1:
                print("🔄 Retrying connection...")
                continue
            else:
                database_connected = False
                return False

# Initialize database on startup
if not initialize_database():
    print("⚠  Running in fallback mode - database operations will be skipped")
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
        print("⚠  Database not available - saving to session")
        session_key = f'{level}_payment_{index_number}'
        session[session_key] = {
            'email': email,
            'index_number': index_number,
            'level': level,
            'transaction_ref': transaction_ref,
            'payment_confirmed': False,
            'created_at': datetime.now().isoformat()
        }
        print(f"✅ Payment data saved to session for {email}")
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
        if result.upserted_id:
            print(f"✅ New payment record created for {email}")
        else:
            print(f"✅ Payment record updated for {email}")
    except Exception as e:
        print(f"❌ Error saving user payment: {str(e)}")
        # Fallback to session
        session_key = f'{level}_payment_{index_number}'
        session[session_key] = payment_record

def save_user_courses(email, index_number, level, courses):
    """Save user course results to courses collection"""
    if not database_connected:
        print("⚠  Database not available - saving courses to session")
        session_key = f'{level}_courses_{index_number}'
        session[session_key] = {
            'email': email,
            'index_number': index_number,
            'level': level,
            'courses': courses,
            'created_at': datetime.now().isoformat()
        }
        print(f"✅ Courses saved to session for {email}")
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
            print(f"✅ New courses record created for {email} with {len(courses)} courses")
        else:
            print(f"✅ Courses record updated for {email} with {len(courses)} courses")
    except Exception as e:
        print(f"❌ Error saving user courses: {str(e)}")
        # Fallback to session
        session_key = f'{level}_courses_{index_number}'
        session[session_key] = courses_record

def update_transaction_ref(email, index_number, level, transaction_ref):
    """Update transaction reference for user"""
    if not database_connected:
        print("⚠  Database not available - updating transaction ref in session")
        session_key = f'{level}_payment_{index_number}'
        if session_key in session:
            session[session_key]['transaction_ref'] = transaction_ref
            print(f"✅ Transaction reference updated in session: {transaction_ref}")
        return
        
    try:
        result = user_payments_collection.update_one(
            {'email': email, 'index_number': index_number, 'level': level},
            {'$set': {
                'transaction_ref': transaction_ref,
                'payment_confirmed': False
            }}
        )
        if result.modified_count > 0:
            print(f"✅ Transaction reference updated in database: {transaction_ref}")
        else:
            print(f"⚠  No document found to update transaction ref for {email}")
    except Exception as e:
        print(f"❌ Error updating transaction reference: {str(e)}")

def get_user_payment(email, index_number, level):
    """Get user payment info from database with fallback to session"""
    # First try database
    if database_connected:
        try:
            payment_data = user_payments_collection.find_one(
                {'email': email, 'index_number': index_number, 'level': level}
            )
            if payment_data:
                print(f"✅ Payment data retrieved from database for {email}")
                return payment_data
        except Exception as e:
            print(f"❌ Error getting user payment from database: {str(e)}")
    
    # Fallback to session
    session_key = f'{level}_payment_{index_number}'
    payment_data = session.get(session_key)
    if payment_data:
        print(f"✅ Payment data retrieved from session for {email}")
    else:
        print(f"⚠  No payment data found for {email}")
    
    return payment_data

def get_user_courses_data(email, index_number, level):
    """Get user courses from database with fallback to session"""
    # First try database
    if database_connected:
        try:
            courses_data = user_courses_collection.find_one(
                {'email': email, 'index_number': index_number, 'level': level}
            )
            if courses_data:
                print(f"✅ Courses data retrieved from database for {email}")
                return courses_data
        except Exception as e:
            print(f"❌ Error getting user courses from database: {str(e)}")
    
    # Fallback to session
    session_key = f'{level}_courses_{index_number}'
    courses_data = session.get(session_key)
    if courses_data:
        print(f"✅ Courses data retrieved from session for {email}")
    else:
        print(f"⚠  No courses data found for {email}")
    
    return courses_data

def mark_payment_confirmed(transaction_ref, mpesa_receipt=None):
    """Mark payment as confirmed - for STK Push"""
    if not database_connected:
        print("⚠  Database not available - marking payment in session")
        for key in session:
            if session[key].get('transaction_ref') == transaction_ref:
                session[key]['payment_confirmed'] = True
                session[key]['mpesa_receipt'] = mpesa_receipt
                session[key]['payment_date'] = datetime.now().isoformat()
                print(f"✅ Payment confirmed in session for transaction: {transaction_ref}")
                return True
        print(f"❌ No session found with transaction ref: {transaction_ref}")
        return False
        
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
            print(f"✅ Payment confirmed in database for transaction: {transaction_ref}, MpesaReceipt: {mpesa_receipt}")
            return True
        else:
            print(f"❌ No user found with transaction ref: {transaction_ref}")
            return False
    except Exception as e:
        print(f"❌ Error marking payment confirmed: {str(e)}")
        return False

def mark_payment_confirmed_by_account(account_number, mpesa_receipt, amount=None):
    """Mark payment as confirmed by account number (index number) - for Paybill payments"""
    if not database_connected:
        print("⚠  Database not available - marking payment in session by account")
        for key in session:
            if session[key].get('index_number') == account_number:
                session[key]['payment_confirmed'] = True
                session[key]['mpesa_receipt'] = mpesa_receipt
                if amount:
                    session[key]['payment_amount'] = amount
                print(f"✅ Payment confirmed in session for account: {account_number}")
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
        if result.modified_count > 0:
            print(f"✅ Payment confirmed in database for account: {account_number}, MpesaReceipt: {mpesa_receipt}")
            return True
        else:
            print(f"❌ No user found with account number: {account_number}")
            return False
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
            print('❌ MPesa OAuth error: No access_token in response!', resp_json)
            raise Exception('No access_token in MPesa OAuth response')
            
        print('✅ MPesa access token retrieved successfully')
        return access_token
        
    except Exception as e:
        print('❌ MPesa OAuth error:', response.status_code if 'response' in locals() else 'No response', str(e))
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
            print('Error: No access token received, aborting STK push.')
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
        
        print('STK Push response:', response.status_code, response.text)
        return response.json()
        
    except Exception as e:
        print(f"Error initiating STK push: {str(e)}")
        return {'error': str(e)}

# --- Routes ---

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/degree')
def degree():
    """Degree courses page"""
    return render_template('degree.html')

@app.route('/diploma')
def diploma():
    """Diploma courses page"""
    return render_template('diploma.html')

@app.route('/kmtc')
def kmtc():
    """KMTC courses page"""
    return render_template('kmtc.html')

@app.route('/certificate')
def certificate():
    """Certificate courses page"""
    return render_template('certificate.html')

@app.route('/artisan')
def artisan():
    """Artisan courses page"""
    return render_template('artisan.html')

@app.route('/results')
def results():
    """Results page"""
    return render_template('results.html')

# --- Grade Submission Routes ---

@app.route('/submit-grades', methods=['POST'])
def submit_grades():
    """Process degree course grades submission"""
    try:
        form_data = request.form.to_dict()
        print("Degree form data received:", form_data)
        
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
        print(f"✅ Degree grades saved: {len(user_grades)} subjects, {len(user_cluster_points)} clusters")
        return redirect(url_for('enter_details', flow='degree'))
        
    except Exception as e:
        print(f"❌ Error in submit_grades: {str(e)}")
        flash("An error occurred while processing your grades", "error")
        return redirect(url_for('degree'))

@app.route('/submit-diploma-grades', methods=['POST'])
def submit_diploma_grades():
    """Process diploma course grades submission"""
    try:
        form_data = request.form.to_dict()
        print("Diploma form data received:", form_data)
        
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
        print(f"✅ Diploma grades saved: {len(user_grades)} subjects, mean grade: {user_mean_grade}")
        return redirect(url_for('enter_details', flow='diploma'))
        
    except Exception as e:
        print(f"❌ Error in submit_diploma_grades: {str(e)}")
        flash("An error occurred while processing your request", "error")
        return redirect(url_for('diploma'))

@app.route('/submit-certificate-grades', methods=['POST'])
def submit_certificate_grades():
    """Process certificate course grades submission"""
    try:
        form_data = request.form.to_dict()
        print("Certificate form data received:", form_data)
        
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
        print(f"✅ Certificate grades saved: {len(user_grades)} subjects, mean grade: {user_mean_grade}")
        return redirect(url_for('enter_details', flow='certificate'))
        
    except Exception as e:
        print(f"❌ Error in submit_certificate_grades: {str(e)}")
        flash("An error occurred while processing your request", "error")
        return redirect(url_for('certificate'))

@app.route('/submit-artisan-grades', methods=['POST'])
def submit_artisan_grades():
    """Process artisan course grades submission"""
    try:
        form_data = request.form.to_dict()
        print("Artisan form data received:", form_data)
        
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
        print(f"✅ Artisan grades saved: {len(user_grades)} subjects, mean grade: {user_mean_grade}")
        return redirect(url_for('enter_details', flow='artisan'))
        
    except Exception as e:
        print(f"❌ Error in submit_artisan_grades: {str(e)}")
        flash("An error occurred while processing your request", "error")
        return redirect(url_for('artisan'))

@app.route('/submit-kmtc-grades', methods=['POST'])
def submit_kmtc_grades():
    """Process KMTC course grades submission"""
    try:
        form_data = request.form.to_dict()
        print("KMTC form data received:", form_data)
        
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
        print(f"✅ KMTC grades saved: {len(user_grades)} subjects, mean grade: {user_mean_grade}")
        return redirect(url_for('enter_details', flow='kmtc'))
        
    except Exception as e:
        print(f"❌ Error in submit_kmtc_grades: {str(e)}")
        flash("An error occurred while processing your request", "error")
        return redirect(url_for('kmtc'))

# --- User Details and Payment Routes ---

@app.route('/enter-details/<flow>', methods=['GET', 'POST'])
def enter_details(flow):
    """Enter user details page"""
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
    """Check payment status from database"""
    email = session.get('email')
    index_number = session.get('index_number')
    user_payment = get_user_payment(email, index_number, flow)
    paid = bool(user_payment and user_payment.get('payment_confirmed'))
    print(f"Payment check for {email}: {paid}")
    return {'paid': paid}

@app.route('/payment/<flow>', methods=['GET', 'POST'])
def payment(flow):
    """Payment processing page"""
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
            # Force create user_payments collection by inserting a document
            if database_connected:
                try:
                    user_payments_collection.insert_one({
                        'email': email,
                        'index_number': index_number,
                        'level': flow,
                        'transaction_ref': transaction_ref,
                        'payment_confirmed': False,
                        'created_at': datetime.now()
                    })
                    print(f"✅ user_payments collection created with transaction: {transaction_ref}")
                except Exception as e:
                    print(f"❌ Error creating user_payments collection: {str(e)}")
                    update_transaction_ref(email, index_number, flow, transaction_ref)
            else:
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
    """Payment waiting page"""
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
    """Check payment status and redirect if paid"""
    email = session.get('email')
    index_number = session.get('index_number')
    user_payment = get_user_payment(email, index_number, flow)
    
    if user_payment and user_payment.get('payment_confirmed'):
        session[f'paid_{flow}'] = True
        return {
            'paid': True,
            'redirect_url': url_for('show_results', flow=flow)
        }
    else:
        return {'paid': False}

# --- MPesa Callback Routes ---

@app.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    """MPesa STK Push callback endpoint"""
    try:
        data = request.get_json(force=True)
        print("MPesa STK callback received (full payload):", data)
        
        callback_metadata = data.get('Body', {}).get('stkCallback', {})
        transaction_ref = callback_metadata.get('CheckoutRequestID')
        result_code = callback_metadata.get('ResultCode')
        
        mpesa_receipt = None
        items = callback_metadata.get('CallbackMetadata', {}).get('Item', [])
        print("CallbackMetadata Items:", items)
        for item in items:
            if item.get('Name') == 'MpesaReceiptNumber':
                mpesa_receipt = item.get('Value')
                break
        print(f"Extracted transaction_ref: {transaction_ref}, MpesaReceiptNumber: {mpesa_receipt}")
        
        if transaction_ref and result_code == 0 and mpesa_receipt:
            result = mark_payment_confirmed(transaction_ref, mpesa_receipt)
            if result:
                print(f"✅ Payment confirmed successfully. M-Pesa Receipt: {mpesa_receipt}")
                return {'success': True}, 200
            else:
                print(f"❌ Failed to mark payment as confirmed")
                return {'success': False}, 400
        else:
            print(f"❌ Payment failed or incomplete. ResultCode: {result_code}")
            return {'success': False}, 400
            
    except Exception as e:
        print(f"❌ Error processing MPesa callback: {str(e)}")
        return {'success': False}, 400

@app.route('/mpesa/confirmation', methods=['POST'])
def mpesa_confirmation():
    """M-Pesa Paybill confirmation callback endpoint"""
    data = request.get_json(force=True)
    trans_id = data.get('TransID')
    amount = data.get('TransAmount')
    phone = data.get('MSISDN')
    account = data.get('BillRefNumber')
    timestamp = data.get('TransactionTime')
    transaction = {
        'trans_id': trans_id,
        'amount': amount,
        'phone': phone,
        'account': account,
        'timestamp': timestamp,
        'callback_type': 'confirmation'
    }
    print(f"MPesa confirmation received: {transaction}")
    
    if account:
        result = mark_payment_confirmed_by_account(account, trans_id, amount)
        print(f"User payment update result for index {account}: {result}")
    
    return {'ResultCode': 0, 'ResultDesc': 'Accepted'}

@app.route('/mpesa/validation', methods=['POST'])
def mpesa_validation():
    """M-Pesa validation callback endpoint"""
    data = request.get_json(force=True)
    print("MPesa validation received:", data)
    
    return {
        "ResultCode": 0,
        "ResultDesc": "Accepted"
    }

# --- Results Display Routes ---

@app.route('/results/<flow>')
def show_results(flow):
    """Display qualification results after payment"""
    email = session.get('email')
    index_number = session.get('index_number')
    
    if not email or not index_number:
        flash("Please complete the qualification process first", "error")
        return redirect(url_for('index'))
    
    user_payment = get_user_payment(email, index_number, flow)
    if not user_payment or not user_payment.get('payment_confirmed'):
        flash('Please complete payment to view your results.', 'error')
        return redirect(url_for('payment', flow=flow))

    print(f"✅ Processing results for {flow} - Email: {email}, Index: {index_number}")

    qualifying_courses = []
    
    if flow == 'degree':
        user_grades = session.get('degree_grades', {})
        user_cluster_points = session.get('degree_cluster_points', {})
        print(f"📊 Degree data - Grades: {len(user_grades)}, Clusters: {len(user_cluster_points)}")
        qualifying_courses = get_qualifying_courses(user_grades, user_cluster_points)
        template = 'results.html'
        
    elif flow == 'diploma':
        user_grades = session.get('diploma_grades', {})
        user_mean_grade = session.get('diploma_mean_grade', '')
        print(f"📊 Diploma data - Grades: {len(user_grades)}, Mean Grade: {user_mean_grade}")
        qualifying_courses = get_qualifying_diploma_courses(user_grades, user_mean_grade)
        template = 'diploma_results.html'
        
    elif flow == 'certificate':
        user_grades = session.get('certificate_grades', {})
        user_mean_grade = session.get('certificate_mean_grade', '')
        print(f"📊 Certificate data - Grades: {len(user_grades)}, Mean Grade: {user_mean_grade}")
        qualifying_courses = get_qualifying_certificate_courses(user_grades, user_mean_grade)
        template = 'certificate_results.html'
        
    elif flow == 'artisan':
        user_grades = session.get('artisan_grades', {})
        user_mean_grade = session.get('artisan_mean_grade', '')
        print(f"📊 Artisan data - Grades: {len(user_grades)}, Mean Grade: {user_mean_grade}")
        qualifying_courses = get_qualifying_artisan_courses(user_grades, user_mean_grade)
        template = 'artisan_results.html'
        
    elif flow == 'kmtc':
        user_grades = session.get('kmtc_grades', {})
        user_mean_grade = session.get('kmtc_mean_grade', '')
        print(f"📊 KMTC data - Grades: {len(user_grades)}, Mean Grade: {user_mean_grade}")
        qualifying_courses = get_qualifying_kmtc_courses(user_grades, user_mean_grade)
        template = 'kmtc_results.html'
        
    else:
        flash("Invalid flow type", "error")
        return redirect(url_for('index'))

    print(f"🎯 Found {len(qualifying_courses)} qualifying courses for {flow}")

    save_user_courses(email, index_number, flow, qualifying_courses)
    
    courses_by_collection = {}
    for course in qualifying_courses:
        collection_name = course.get('collection', 'Other')
        if collection_name not in courses_by_collection:
            courses_by_collection[collection_name] = []
        courses_by_collection[collection_name].append(course)
    
    print(f"📂 Grouped into {len(courses_by_collection)} collections")
    
    return render_template(template, 
                         courses=qualifying_courses,
                         courses_by_collection=courses_by_collection,
                         user_grades=user_grades, 
                         user_mean_grade=user_mean_grade if flow != 'degree' else None,
                         user_cluster_points=user_cluster_points if flow == 'degree' else None,
                         subjects=SUBJECTS, 
                         email=email, 
                         index_number=index_number)

# --- Collection-based Results Routes ---

@app.route('/collection-courses/<flow>/<collection_name>')
def show_collection_courses(flow, collection_name):
    """Show courses for a specific collection"""
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

# --- Debug and Testing Routes ---

@app.route('/debug/database')
def debug_database():
    """Debug endpoint to check database status"""
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

@app.route('/temp-bypass/<flow>')
def temp_bypass(flow):
    """Temporary route to bypass payment for testing"""
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
    app.run(host='0.0.0.0', port=8080, debug=True)