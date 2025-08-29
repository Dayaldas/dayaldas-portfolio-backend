from datetime import datetime, timedelta
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
from bson import ObjectId

# Environment variables
MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME', 'portfolio_db')

# MongoDB connection
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Collections
experiences_collection = db.experiences
accomplishments_collection = db.accomplishments
contacts_collection = db.contacts
profile_collection = db.profile
testimonials_collection = db.testimonials

# Models
class ContactStatus(str, Enum):
    NEW = "new"
    READ = "read" 
    RESPONDED = "responded"

class Experience(BaseModel):
    id: str = Field(alias="_id")
    position: str
    company: str
    location: str
    period: str
    description: str
    achievements: List[str]
    order: int = 0
    isActive: bool = True
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    class Config:
        populate_by_name = True

class Accomplishment(BaseModel):
    id: str = Field(alias="_id")
    title: str
    description: str
    impact: str
    technologies: List[str]
    order: int = 0
    isActive: bool = True
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    class Config:
        populate_by_name = True

class ContactFormCreate(BaseModel):
    name: str
    email: str
    subject: Optional[str] = ""
    message: str

class ContactForm(BaseModel):
    id: str = Field(alias="_id")
    name: str
    email: str
    subject: str = ""
    message: str
    status: ContactStatus = ContactStatus.NEW
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    class Config:
        populate_by_name = True

class Profile(BaseModel):
    id: str = Field(alias="_id")
    name: str
    title: str
    description: str
    location: str
    email: str
    phone: str
    isActive: bool = True
    updatedAt: Optional[datetime] = None

    class Config:
        populate_by_name = True

class Testimonial(BaseModel):
    id: str = Field(alias="_id")
    name: str
    title: str
    company: str = ""
    testimonial: str
    relationship: str = ""
    date: str = ""
    order: int = 0
    isActive: bool = True
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    class Config:
        populate_by_name = True

# Utility functions
def convert_objectid(document):
    if document and "_id" in document:
        document["_id"] = str(document["_id"])
    return document

# Create FastAPI app
app = FastAPI(title="Dayaldas Portfolio API", description="Professional Portfolio Backend")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Router
api_router = APIRouter(prefix="/api")

# Health check
@api_router.get("/")
async def root():
    return {"message": "Dayaldas Portfolio API is running", "timestamp": datetime.utcnow()}

# Experience endpoints
@api_router.get("/experiences", response_model=List[Experience])
async def get_experiences():
    try:
        cursor = experiences_collection.find({"isActive": True}).sort("order", 1)
        experiences = []
        async for document in cursor:
            document = convert_objectid(document)
            experiences.append(Experience(**document))
        return experiences
    except Exception as e:
        logging.error(f"Error fetching experiences: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch experiences")

# Accomplishments endpoints
@api_router.get("/accomplishments", response_model=List[Accomplishment])
async def get_accomplishments():
    try:
        cursor = accomplishments_collection.find({"isActive": True}).sort("order", 1)
        accomplishments = []
        async for document in cursor:
            document = convert_objectid(document)
            accomplishments.append(Accomplishment(**document))
        return accomplishments
    except Exception as e:
        logging.error(f"Error fetching accomplishments: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch accomplishments")

# Profile endpoints
@api_router.get("/profile", response_model=Profile)
async def get_profile():
    try:
        document = await profile_collection.find_one({"isActive": True})
        if not document:
            raise HTTPException(status_code=404, detail="Profile not found")
        document = convert_objectid(document)
        return Profile(**document)
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch profile")

# Testimonials endpoints
@api_router.get("/testimonials", response_model=List[Testimonial])
async def get_testimonials():
    try:
        cursor = testimonials_collection.find({"isActive": True}).sort("order", 1)
        testimonials = []
        async for document in cursor:
            document = convert_objectid(document)
            testimonials.append(Testimonial(**document))
        return testimonials
    except Exception as e:
        logging.error(f"Error fetching testimonials: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch testimonials")

# Contact form endpoint
@api_router.post("/contact", response_model=ContactForm)
async def submit_contact_form(contact: ContactFormCreate):
    try:
        contact_data = contact.dict()
        contact_data["createdAt"] = datetime.utcnow()
        contact_data["updatedAt"] = datetime.utcnow()
        contact_data["status"] = "new"
        
        result = await contacts_collection.insert_one(contact_data)
        created_contact = await contacts_collection.find_one({"_id": result.inserted_id})
        created_contact = convert_objectid(created_contact)
        return ContactForm(**created_contact)
    except Exception as e:
        logging.error(f"Error submitting contact form: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to submit contact form")

# Analytics endpoint
@api_router.post("/analytics")
async def track_analytics(analytics_data: dict):
    """Track visitor analytics"""
    try:
        analytics_data["createdAt"] = datetime.utcnow()
        await db.analytics.insert_one(analytics_data)
        return {"status": "success"}
    except Exception as e:
        logging.error(f"Error tracking analytics: {str(e)}")
        return {"status": "error"}

@api_router.get("/analytics/summary")
async def get_analytics_summary():
    """Get analytics summary"""
    try:
        total_visits = await db.analytics.count_documents({})
        recent_visits = await db.analytics.count_documents({
            "timestamp": {"$gte": datetime.utcnow() - timedelta(days=7)}
        })
        return {
            "total_visits": total_visits,
            "recent_visits": recent_visits,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logging.error(f"Error fetching analytics: {str(e)}")
        return {"total_visits": 0, "recent_visits": 0}
        
# Include router
app.include_router(api_router)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
