from sqlalchemy.orm import Session
from app.models.student import Student

def get_all(db: Session):
    return db.query(Student).all()

def get_by_id(db: Session, student_id: int):
    return db.query(Student).filter(Student.id == student_id).first()

def get_by_email(db: Session, email: str):
    return db.query(Student).filter(Student.email == email).first()

def create(db: Session, student: Student):
    db.add(student)
    db.commit()
    db.refresh(student)
    return student

def update(db: Session, student: Student):
    db.commit()
    db.refresh(student)
    return student

def delete(db: Session, student: Student):
    db.delete(student)
    db.commit()