from sqlalchemy.orm import Session
import models, schemas
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user:
        return False
    if not pwd_context.verify(password, user.hashed_password):
        return False
    return user

def get_post(db: Session, post_id: int):
    return db.query(models.Post).filter(models.Post.id == post_id).first()

def get_posts(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Post).order_by(models.Post.created_at.desc()).offset(skip).limit(limit).all()

def create_post(db: Session, post: schemas.PostCreate):
    db_post = models.Post(
        title=post.title,
        description=post.description,
        category=post.category,
        image_url=post.image_url,
    )
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post

def update_post(db: Session, post_id: int, post: schemas.PostCreate):
    db_post = get_post(db, post_id)
    if not db_post:
        return None
    db_post.title = post.title
    db_post.description = post.description
    db_post.category = post.category
    db_post.image_url = post.image_url
    db.commit()
    db.refresh(db_post)
    return db_post

def delete_post(db: Session, post_id: int):
    post = get_post(db, post_id)
    if not post:
        return None
    db.delete(post)
    db.commit()
    return post

def create_donation(db: Session, donation: schemas.DonationCreate):
    db_donation = models.Donation(
        name=donation.name,
        email=donation.email,
        amount=donation.amount,
        message=donation.message
    )
    db.add(db_donation)
    db.commit()
    db.refresh(db_donation)
    return db_donation

def get_donations(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Donation).order_by(models.Donation.created_at.desc()).offset(skip).limit(limit).all()

def get_recent_donations(db: Session, limit: int = 5):
    return get_donations(db, limit=limit)
