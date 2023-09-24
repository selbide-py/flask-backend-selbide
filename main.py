from flask import Flask, request, jsonify
from PyPDF2 import PdfReader
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import os
from dotenv import load_dotenv
from flask_cors import CORS
import requests
import random
import string

load_dotenv()


def generate_random_string():
    global random_string
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(4))


def get_user_chat_id(user_id):
    user = db.users.find_one({'_id': ObjectId(user_id)})
    if user:
        return user.get('user_chat_id', '')
    return ''

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
        
        return jsonify({'user_id': user_id, 'chat_messages': chat_messages, 'random_string': user.get('user_chat_id', '')}), 200
    else:
        # User does not exist, create a new user
        user_id = str(ObjectId())  # Generate a unique user ID
        user_chat_id = generate_random_string();
        db.users.insert_one({'_id': ObjectId(user_id), 'email': email, 'password': password, 'user_chat_id': user_chat_id})
        
        # Create a new collection for the user using their ID
        db.create_collection(user_id)
        
        return jsonify({'user_id': user_id, 'chat_messages': [], 'random_string': user_chat_id}), 200

# Add a chat message route
@app.route('/add_chat', methods=['POST'])
def add_chat():
    data = request.get_json()
    user_id = data.get('user_id')
    message = data.get('message')
    is_user = data.get('is_user')

    if not ObjectId.is_valid(user_id):
        return jsonify({'message': 'Invalid user_id'}), 404

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
    user_chat_id = get_user_chat_id(user_id)
    api_payload = {
        "botName": "Basic_1",
        "userContext": message,
        "userId": user_chat_id,  # Assuming user_id is the same as UID in the API
        "chrContext": "",
        "testMode": 0,
        "mode": 3,
        "qNo": 2
    }
    api_headers = {'Content-Type': 'application/json'}

    # Make the API request
    api_response = requests.post(api_url, json=api_payload, headers=api_headers, timeout=6969696969)

    if api_response.status_code == 200:
        print(api_response.json())
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
        return jsonify({'message': "true"}), 200
    else:
        return jsonify({'message': 'API request failed'}), 500

@app.route('/getchat', methods=['POST'])
def get_chat():
    data = request.get_json()
    user_id = data.get('id')

    if not ObjectId.is_valid(user_id):
        return jsonify({'message': 'Invalid user_id'}), 404

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
        
        return jsonify({'user_id': str(user_id), 'chat_messages': chat_messages}), 200
    else:
        return jsonify({'message': 'User not found'}), 404

@app.route('/file_upload', methods=['POST'])
def file_upload():
    # Check if a file was included in the request
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400

    file = request.files['file']

    # Check if the file has a PDF extension
    if not file.filename.endswith('.pdf'):
        return jsonify({'message': 'File is not a PDF'}), 400

    user_id = request.form.get('user_id')  # Assuming you send user_id as a form field

    if not ObjectId.is_valid(user_id):
        return jsonify({'message': 'Invalid user_id'}), 400

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

        return jsonify({'text': text}), 200
    except Exception as e:
        return jsonify({'message': 'Error extracting text from PDF', 'error': str(e)}), 500


@app.route('/summarize', methods=['POST'])
def summarize():
    data = request.get_json()
    user_id = data.get('user_id')

    if not ObjectId.is_valid(user_id):
        return jsonify({'message': 'Invalid user_id'}), 404

    # Check if the user folder and PDF file exist
    user_folder = os.path.join('./file_storage', str(user_id))
    pdf_filename = os.path.join(user_folder, f'{str(user_id)}.pdf')

    if not os.path.exists(pdf_filename):
        return jsonify({'message': 'Please upload a PDF file to generate a summary'}), 400

    # Read the PDF file and extract text
    try:
        pdf = PdfReader(pdf_filename)
        text = ''
        for page in pdf.pages:
            text += page.extract_text()
    except Exception as e:
        return jsonify({'message': 'Error extracting text from PDF', 'error': str(e)}), 500

    # Prepare the data to send to the external API
    user_chat_id = get_user_chat_id(user_id)
    api_url = "https://poyboi--sbuh-1285-cli.modal.run/"
    api_payload = {
        "botName": "Basic_2",
        "userContext": text,
        "userId": user_chat_id,  # Assuming user_id is the same as UID in the API
        "chrContext": "",
        "testMode": 0,
        "mode": 2,
        "qNo": 2
    }
    api_headers = {'Content-Type': 'application/json'}

    # Make the API request
    api_response = requests.post(api_url, json=api_payload, headers=api_headers, timeout=6969696969)
    print(api_response.json())

    if api_response.status_code == 200:
        api_data = api_response.json()
        conversation = api_data.get("conversation")
        if conversation:
            # Use the user's summary collection based on their user_id
            summary_collection_name = f'summary-{user_id}'
            summary_collection = db[summary_collection_name]
            
            # Delete any existing summary for the user
            summary_collection.delete_many({})

            # Create a new summary document
            summary_document = {
                'user_id': user_id,
                'summary': conversation,
                "is_user": False
            }
            summary_collection.insert_one(summary_document)
        return jsonify({'user_id': user_id, 'conversation': conversation}), 200
    else:
        return jsonify({'message': 'API request failed'}), 500

@app.route('/summary_chat', methods=['POST'])
def summary_chat():
    data = request.get_json()
    user_id = data.get('user_id')
    message = data.get('message')
    is_user = data.get('is_user')

    if not ObjectId.is_valid(user_id):
        return jsonify({'message': 'Invalid user_id'}), 404

    # Create a summary collection for the user if it doesn't exist
    summary_collection_name = f'summary-{user_id}'
    if summary_collection_name not in db.list_collection_names():
        db.create_collection(summary_collection_name)

    summary_collection = db[summary_collection_name]

    if is_user is None:
        is_user = True 
    # Prepare the chat message
    chat_message = {
        'timestamp': datetime.now(),
        'message': message,
        'is_user': is_user  # Assume it's a user message
    }

    # Insert the chat message into the user's summary collection
    summary_collection.insert_one(chat_message)

    api_url = "https://poyboi--sbuh-1285-cli.modal.run/"
    user_chat_id = get_user_chat_id(user_id)    
    api_payload = {
        "botName": "Bart",
        "userContext": message,
        "userId": user_chat_id,  # Assuming user_id is the same as UID in the API
        "chrContext": "This character is retarded",
        "testMode": 1,
        "mode": 2,
        "qNo": 2
    }
    api_headers = {'Content-Type': 'application/json'}

    # Make the API request
    api_response = requests.post(api_url, json=api_payload, headers=api_headers, timeout=6969696969)

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
            summary_collection.insert_one(chat_message)
        return jsonify({'message': "true"}), 200
    else:
        return jsonify({'message': 'API request failed'}), 500


@app.route('/get_summary_chat', methods=['POST'])
def get_summary_chat():
    data = request.get_json()
    user_id = data.get('user_id')

    if not ObjectId.is_valid(user_id):
        return jsonify({'message': 'Invalid user_id'}), 404

    # Check if the summary collection for the user exists
    summary_collection_name = f'summary-{user_id}'
    if summary_collection_name in db.list_collection_names():
        summary_collection = db[summary_collection_name]

        # Fetch chat messages from the summary collection
        chat_messages = list(summary_collection.find())

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

        return jsonify({'user_id': str(user_id), 'chat_messages': chat_messages}), 200
    else:
        return jsonify({'message': 'Summary chat data not found'}), 404

@app.errorhandler(404)
def not_found(error):
    return {'Error Occured': str("Breh, are you retarded, atleast get the route correct (╬▔皿▔)╯"), "error": str(error)}, 404

@app.errorhandler(500)
def internal_error(error):
    return {'Error Occured': str("Server irl rn : （；´д｀）ゞ"), "error": str(error)}, 500

if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))