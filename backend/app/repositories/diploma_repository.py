from sqlalchemy.orm import Session
from app.models.diploma import Diploma

def get_all(db: Session):
    return db.query(Diploma).all()

def get_by_id(db: Session, diploma_id: int):
    return db.query(Diploma).filter(
        Diploma.id == diploma_id
    ).first()

def get_by_name(db: Session, name: str):
    return db.query(Diploma).filter(
        Diploma.name == name
    ).first()

def create(db: Session, diploma: Diploma):
    db.add(diploma)
    db.commit()
    db.refresh(diploma)
    return diploma

def update(db: Session, diploma: Diploma):
    db.commit()
    db.refresh(diploma)
    return diploma

def delete(db: Session, diploma: Diploma):
    db.delete(diploma)
    db.commit()