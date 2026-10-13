import os
import hashlib
from fastapi import FastAPI, Depends, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import pathlib
from dotenv import load_dotenv

import cloudinary
import cloudinary.uploader

import models
from database import engine, SessionLocal, get_db

load_dotenv()

# Cloudinary configuration (Render ke environment variables se uthayega)
cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET")
)

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

BASE_DIR = pathlib.Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory="templates")

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def seed_users():
    db = SessionLocal()
    sample_users = [
        ("MyFolder1", "satish@b1.com"),       # Account 1
        ("MyFolder2", "rohit@b1.com"),         # Account 2
        ("MyFolder3", "nilesh@b1.com"),           # Account 3
        ("MyFolder4", "nishikant@b1.com"),           # Account 4
        ("MyFolder5", "manish@b1.com"),           # Account 5
        ("MyFolder6", "durgesh@b1.com"),           # Account 6
        ("MyFolder7", "acc_1@b1.com"),           # Account 7
        ("MyFolder8", "acc_2@b1.com"),           # Account 8
        ("MyFolder9", "acc_3@b1.com"),           # Account 9
        ("MyFolder10", "acc_4@b1.com")          # Account 10
    ]
    
    for uname, uemail in sample_users:
        existing = db.query(models.User).filter(models.User.email == uemail).first()
        if not existing:
            hashed_pw = hash_password("all_sena")
            new_user = models.User(username=uname, email=uemail, hashed_password=hashed_pw)
            db.add(new_user)
            db.commit()
    db.close()

seed_users()
fake_session_db = {}

@app.get("/", response_class=HTMLResponse)
def auth_page(request: Request):
    return templates.TemplateResponse(request, "auth.html", {"error": None})

@app.post("/login")
def login_user(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    hashed_input_pw = hash_password(password)
    
    if not user or user.hashed_password != hashed_input_pw:
        return templates.TemplateResponse(request, "auth.html", {"error": "Invalid Email or Password (Password is 12345)"})
    
    fake_session_db["current_user"] = user.id
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user_id = fake_session_db.get("current_user")
    if not user_id:
        return RedirectResponse(url="/", status_code=303)
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    user_folders = db.query(models.FolderRecord).filter(models.FolderRecord.owner_id == user_id).all()

    return templates.TemplateResponse(request, "dashboard.html", {"user": user, "folders": user_folders})

@app.post("/create-folder")
def create_folder(foldername: str = Form(...), db: Session = Depends(get_db)):
    user_id = fake_session_db.get("current_user")
    if not user_id:
        return RedirectResponse(url="/", status_code=303)

    new_folder = models.FolderRecord(foldername=foldername, owner_id=user_id)
    db.add(new_folder)
    db.commit()

    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/upload")
def upload_file(file: UploadFile = File(...), folder_id: int = Form(None), db: Session = Depends(get_db)):
    user_id = fake_session_db.get("current_user")
    if not user_id:
        return RedirectResponse(url="/", status_code=303)

    try:
        # File ko direct Cloudinary par upload karenge (Local uploads folder ka use khatam)
        upload_result = cloudinary.uploader.upload(file.file, folder=f"cloud_storage_user_{user_id}")
        file_url = upload_result.get("secure_url")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cloud upload failed: {str(e)}")

    ext = file.filename.split(".")[-1].lower()
    if ext in ["jpg", "jpeg", "png", "gif", "webp"]:
        ftype = "Image 🖼️"
    elif ext in ["mp4", "mkv", "mov", "avi"]:
        ftype = "Video 🎥"
    elif ext in ["mp3", "wav", "aac"]:
        ftype = "Audio 🎵"
    else:
        ftype = "Document/Text 📄"

    new_file = models.FileRecord(
        filename=file.filename, 
        filepath=file_url, # Cloudinary ka secure URL save hoga
        filetype=ftype, 
        folder_id=folder_id if folder_id else None, 
        owner_id=user_id
    )
    db.add(new_file)
    db.commit()

    return RedirectResponse(url=f"/folder/{folder_id}" if folder_id else "/dashboard", status_code=303)

@app.get("/download/{file_id}")
def download_file(file_id: int, db: Session = Depends(get_db)):
    file_record = db.query(models.FileRecord).filter(models.FileRecord.id == file_id).first()
    if file_record and file_record.filepath:
        # Cloudinary URL par direct redirect kar denge download ke liye
        return RedirectResponse(url=file_record.filepath, status_code=303)
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/logout")
def logout():
    fake_session_db.clear()
    return RedirectResponse(url="/", status_code=303)

@app.get("/folder/{folder_id}", response_class=HTMLResponse)
def view_folder(folder_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = fake_session_db.get("current_user")
    if not user_id:
        return RedirectResponse(url="/", status_code=303)
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    folder = db.query(models.FolderRecord).filter(models.FolderRecord.id == folder_id, models.FolderRecord.owner_id == user_id).first()
    
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
        
    folder_files = db.query(models.FileRecord).filter(models.FileRecord.folder_id == folder_id).all()

    return templates.TemplateResponse(request, "folder_view.html", {"user": user, "folder": folder, "files": folder_files})

@app.get("/view-file/{file_id}")
def view_file(file_id: int, db: Session = Depends(get_db)):
    file_record = db.query(models.FileRecord).filter(models.FileRecord.id == file_id).first()
    if file_record and file_record.filepath:
        # Browser me direct Cloudinary URL open ho jayega
        return RedirectResponse(url=file_record.filepath, status_code=303)
    raise HTTPException(status_code=404, detail="File not found")
