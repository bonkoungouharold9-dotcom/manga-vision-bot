import os
import re
from bson import ObjectId
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "")
client = MongoClient(MONGO_URI)
db = client["mangavision"]
collection = db["fichiers"]

# Création d'un index textuel
try:
    collection.create_index([("file_name", "text")])
except Exception:
    pass

def save_file(file_id, file_name, file_type, message_id):
    """Enregistre ou met à jour un fichier dans la base MongoDB"""
    data = {
        "file_id": file_id,
        "file_name": file_name,
        "file_type": file_type,
        "message_id": message_id
    }
    collection.update_one({"file_name": file_name}, {"$set": data}, upsert=True)

def search_files(query, limit=10):
    """Recherche des mangas par mot-clé (insensible à la casse)"""
    clean_query = re.escape(query.strip())
    regex = {"$regex": clean_query, "$options": "i"}
    return list(collection.find({"file_name": regex}).limit(limit))

def get_file_by_id(item_id):
    """Récupère un manga par son identifiant unique"""
    try:
        return collection.find_one({"_id": ObjectId(item_id)})
    except Exception:
        return None
