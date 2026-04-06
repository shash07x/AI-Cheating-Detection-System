from app.utils.database import db

def create_user(user_id, name):
    db.users.insert_one({
        "_id": user_id,
        "name": name
    })
