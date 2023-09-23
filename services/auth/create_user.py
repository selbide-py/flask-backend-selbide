from pymongo import MongoClient
from bson.objectid import ObjectId

def create_user(uri, email, password):
    """Create a user.

    Args:
        uri (str): The MongoDB URI to connect to.
        email (str): The user's email.
        password (str): The user's password.

    Returns:
        str: The user's ID.
    """
    client = MongoClient(uri)
    db = client.flask_db

    # Generate a unique ObjectId to use as the user's ID
    user_id = ObjectId()

    # Create the user document with the unique user_id
    user = {
        '_id': user_id,
        'email': email,
        'password': password
    }

    # Insert the user document into the 'users' collection
    db.users.insert_one(user)

    # Return the user's ID as a string
    return str(user_id)

# Example usage:
# user_id = create_user('mongodb://localhost:27017/', 'user@example.com', 'password')
