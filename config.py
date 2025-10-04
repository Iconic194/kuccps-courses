import os

class Config:

    MONGODB_URI = "mongodb+srv://iconichean:1Loye8PM3YwlV5h4@cluster0.meufk73.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    
    
    DB_DEGREE = 'courses_2'
    DB_DIPLOMA = 'dp_courses'
    DB_CERTIFICATE = 'cert_courses'
    DB_ARTISAN = 'art_courses'
    

    API_HOST = '0.0.0.0'
    API_PORT = 5000
    DEBUG = True
    
    
    CORS_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000']