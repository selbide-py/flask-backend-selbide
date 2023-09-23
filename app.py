from flask import Flask, request, jsonify
from PyPDF2 import PdfReader
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import os
from dotenv import load_dotenv
from flask_cors import CORS
import requests 

load_dotenv()

db_pass = os.environ.get('DATABASE_PASS')
app = Flask(__name__)

CORS(app)

# MongoDB connection setup
mongo_uri = f'mongodb+srv://Inevitable-Design:{db_pass}@cluster0.g3wczyg.mongodb.net/'
client = MongoClient(mongo_uri)
db = client.selbide

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    # Check if the user exists
    user = db.users.find_one({'email': email, 'password': password})

    if user:
        # User exists, return their chat messages
        user_id = str(user['_id'])  # Convert ObjectId to string
        chat_messages = list(db[user_id].find())
        
        # Convert ObjectId to string for each message
        chat_messages = [
            {
                '_id': str(message['_id']),
                'timestamp': message['timestamp'],
                'message': message['message'],
                'is_user': message['is_user']
            }
            for message in chat_messages
        ]
        
        return jsonify({'user_id': user_id, 'chat_messages': chat_messages})
    else:
        # User does not exist, create a new user
        user_id = str(ObjectId())  # Generate a unique user ID
        db.users.insert_one({'_id': ObjectId(user_id), 'email': email, 'password': password})
        
        # Create a new collection for the user using their ID
        db.create_collection(user_id)

        return jsonify({'user_id': user_id, 'chat_messages': []})

# Add a chat message route
@app.route('/add_chat', methods=['POST'])
def add_chat():
    data = request.get_json()
    user_id = data.get('user_id')
    message = data.get('message')
    is_user = data.get('is_user')

    if not ObjectId.is_valid(user_id):
        return jsonify({'message': 'Invalid user_id'})

    if is_user is None:
        is_user = True  # If is_user is not provided, assume it's true (from the frontend)

    chat_message = {
        'timestamp': datetime.now(),
        'message': message,
        'is_user': is_user
    }

    # Insert the chat message into the user's collection
    db[user_id].insert_one(chat_message)

    # Prepare the data to send to the external API
    api_url = "https://poyboi--sbuh-1285-cli.modal.run/"
    api_payload = {
        "botName": "Bart",
        "userContext": message,
        "userId": 'AAAA',  # Assuming user_id is the same as UID in the API
        "chrContext": "",
        "testMode": 0,
        "mode": 2,
        "qNo": 2
    }
    api_headers = {'Content-Type': 'application/json'}

    # Make the API request
    api_response = requests.post(api_url, json=api_payload, headers=api_headers)

    if api_response.status_code == 200:
        api_data = api_response.json()
        conversation = api_data.get("conversation")
        if conversation:
            # Store the conversation in MongoDB
            chat_message = {
                'timestamp': datetime.now(),
                'message': conversation,
                'is_user': False
            }
            db[user_id].insert_one(chat_message)
        return jsonify({'message': "true"})
    else:
        return jsonify({'message': 'API request failed'})

@app.route('/getchat', methods=['POST'])
def get_chat():
    data = request.get_json()
    user_id = data.get('id')

    if not ObjectId.is_valid(user_id):
        return jsonify({'message': 'Invalid user_id'})

    # Check if the user exists
    user = db.users.find_one({'_id': ObjectId(user_id)})

    if user:
        # User exists, return their chat messages
        chat_messages = list(db[user_id].find())
        
        # Convert ObjectId to string
        chat_messages = [
            {
                '_id': str(message['_id']),
                'timestamp': message['timestamp'],
                'message': message['message'],
                'is_user': message['is_user']
            }
            for message in chat_messages
        ]
        
        return jsonify({'user_id': str(user_id), 'chat_messages': chat_messages})
    else:
        return jsonify({'message': 'User not found'})

@app.route('/file_upload', methods=['POST'])
def file_upload():
    # Check if a file was included in the request
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'})

    file = request.files['file']

    # Check if the file has a PDF extension
    if not file.filename.endswith('.pdf'):
        return jsonify({'message': 'File is not a PDF'})

    user_id = request.form.get('user_id')  # Assuming you send user_id as a form field

    if not ObjectId.is_valid(user_id):
        return jsonify({'message': 'Invalid user_id'})

    # Create a folder for the user if it doesn't exist
    user_folder = os.path.join('./file_storage', str(user_id))
    os.makedirs(user_folder, exist_ok=True)

    # Delete any existing files in the user's folder
    for existing_file in os.listdir(user_folder):
        file_path = os.path.join(user_folder, existing_file)
        if os.path.isfile(file_path):
            os.remove(file_path)

    # Save the uploaded PDF file with the user's ID as the filename
    pdf_filename = os.path.join(user_folder, f'{str(user_id)}.pdf')
    file.save(pdf_filename)

    # Read the PDF file and extract text
    try:
        pdf = PdfReader(pdf_filename)
        text = ''
        for page in pdf.pages:
            text += page.extract_text()

        return jsonify({'text': text})
    except Exception as e:
        return jsonify({'message': 'Error extracting text from PDF', 'error': str(e)})

@app.route('/summarize', methods=['POST'])
def summarize():
    return {'message': 'Hello summary!'}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)