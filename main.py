from fastapi import FastAPI, Request, Depends, Form, HTTPException, status, Cookie, File, UploadFile
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from httpx import request
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import os
import shutil
import uuid

import models, crud, schemas
from database import engine, get_db, SessionLocal
from auth import verify_admin_credentials, get_current_admin, SESSION_COOKIE_NAME, SESSION_TOKEN

# Create images directory if it doesn't exist
IMAGES_DIR = "static/images"
os.makedirs(IMAGES_DIR, exist_ok=True)

models.Base.metadata.create_all(bind=engine)

# Create admin user if not exists
db = SessionLocal()
if not crud.get_user_by_username(db, "admin"):
    crud.create_user(db, schemas.UserCreate(username="admin", password="password123"))
db.close()

app = FastAPI(title="Dakshina")
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

@app.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    posts = crud.get_posts(db)
    donation = crud.get_recent_donations(db)
    return templates.TemplateResponse("home.html", {"request": request, "posts": posts, "recent_donations": donation})

@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": ""})

@app.get("/about")
def about_page(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/donate")
def donation_page(request: Request, db: Session = Depends(get_db)):
    donation = crud.get_recent_donations(db)
    return templates.TemplateResponse("donation.html", {"request": request, "recent_donations": donation})


@app.post("/donate")
def donation_submit(request: Request, 
                    db: Session = Depends(get_db),
                    amount: int = Form(...),
                    donorName: str = Form(None),
                    donorEmail: str = Form(None),
                    message: str = Form(None),
                    anonymous: Optional[str] = Form(None)):
    donor = "Anonymous" if anonymous or not donorName else donorName
    donation_record = {
        "name": donor,
        "email": donorEmail or "",
        "message": message or "",
        "amount": amount,
        "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    }
    try:
        donation_in = schemas.DonationCreate(
            name=donation_record["name"],
            email=donation_record["email"],
            amount=donation_record["amount"],
            message=donation_record["message"]
        )
        crud.create_donation(db, donation_in)
    finally:      
        db.close()
    
    return RedirectResponse(url="/donate", status_code=status.HTTP_302_FOUND)


@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    print(f"Login attempt: username='{username}', password='{password}'")
    if not verify_admin_credentials(username, password, db):
        print("Invalid credentials")
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    print("Login successful, setting cookie")
    response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key=SESSION_COOKIE_NAME, value=SESSION_TOKEN, httponly=True, max_age=3600)
    return response


@app.get("/dev/login")
def dev_login():
    response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key=SESSION_COOKIE_NAME, value=SESSION_TOKEN, httponly=True, max_age=3600, path="/", samesite="lax")
    return response


@app.get("/debug/cookie")
def debug_cookie(request: Request, session_token: Optional[str] = Cookie(None)):
    return {"session_token": session_token, "expected": SESSION_TOKEN}


@app.get("/admin/dashboard")
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    posts = crud.get_posts(db)
    return templates.TemplateResponse("admin_dashboard.html", {"request": request, "posts": posts})


@app.get("/admin/posts")
def admin_post_list(request: Request, db: Session = Depends(get_db)):
    posts = crud.get_posts(db)
    return templates.TemplateResponse("post_list.html", {"request": request, "posts": posts})

@app.get("/admin/posts/new")
def create_post_form(request: Request):
    return templates.TemplateResponse("create_post.html", {"request": request, "error": ""})

@app.get("/admin/posts/{post_id}/edit")
def edit_post_form(request: Request, post_id: int, db: Session = Depends(get_db)):
    post = crud.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return templates.TemplateResponse("update_post.html", {"request": request, "post": post, "error": ""})

@app.post("/admin/posts/new")
def create_post(request: Request,
                title: str = Form(...),
                description: str = Form(...),
                category: str = Form(...),
                image_url: str = Form(None),
                image_file: Optional[UploadFile] = File(None),
                db: Session = Depends(get_db)):
    if category not in ["temple", "priest", "sadhu"]:
        return templates.TemplateResponse("create_post.html", {
            "request": request,
            "error": "Category must be temple / priest / sadhu"
        }, status_code=status.HTTP_400_BAD_REQUEST)

    # Handle image upload or URL
    final_image_url = None
    
    if image_file and image_file.filename:
        # Save uploaded file
        try:
            file_extension = os.path.splitext(image_file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = os.path.join(IMAGES_DIR, unique_filename)
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
            
            final_image_url = f"/static/images/{unique_filename}"
        except Exception as e:
            print(f"Error saving image: {e}")
            return templates.TemplateResponse("create_post.html", {
                "request": request,
                "error": f"Error uploading image: {str(e)}"
            }, status_code=status.HTTP_400_BAD_REQUEST)
    elif image_url:
        # Use provided URL
        final_image_url = image_url

    post_in = schemas.PostCreate(title=title, description=description, category=category, image_url=final_image_url)
    crud.create_post(db, post_in)

    return RedirectResponse(url="/admin/posts", status_code=status.HTTP_302_FOUND)


@app.get("/posts/{post_id}")
def get_post_detail(request: Request, post_id: int, db: Session = Depends(get_db)):
    post = crud.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return templates.TemplateResponse("post_detail.html", {"request": request, "post": post})


@app.delete("/posts/{post_id}")
def delete_post_api(post_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_post(db, post_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Post not found")
    return JSONResponse(content={"success": True, "id": post_id})


# API endpoints for the requirement

@app.post("/api/login")
def api_login(payload: dict):
    username = payload.get("username")
    password = payload.get("password")
    if not verify_admin_credentials(username, password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"session_token": SESSION_TOKEN}


@app.get("/api/posts")
def api_get_posts(db: Session = Depends(get_db)):
    posts = crud.get_posts(db)
    return posts

@app.get("/api/posts/{post_id}")
def api_get_post(post_id: int, db: Session = Depends(get_db)):
    post = crud.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

@app.post("/api/posts")
def api_create_post(post: schemas.PostCreate, db: Session = Depends(get_db)):
    return crud.create_post(db, post)

@app.post("/api/posts/{post_id}/edit")
def api_edit_post(
    post_id: int,
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    image_url: str = Form(None),
    db: Session = Depends(get_db)
):

    existing_post = crud.get_post(db, post_id)

    if not existing_post:
        raise HTTPException(status_code=404, detail="Post not found")

    existing_post.title = title
    existing_post.description = description
    existing_post.category = category
    existing_post.image_url = image_url

    db.commit()
    db.refresh(existing_post)

    response = RedirectResponse(url="/admin/posts", status_code=status.HTTP_302_FOUND)
    return response

@app.delete("/api/posts/{post_id}")
def api_delete_post(post_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_post(db, post_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"success": True}

@app.get("/api/donations")
def api_get_donations(db: Session = Depends(get_db)):
    donations = crud.get_donations(db)
    return donations



