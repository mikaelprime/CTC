from sqlalchemy.orm import Session
from app.models.diploma import Diploma
from app.schemas.diploma_schema import DiplomaCreate, DiplomaUpdate

def get_all(db: Session):
    return db.query(Diploma).all()

def get_by_id(db: Session, diploma_id: int):
    return db.query(Diploma).filter(Diploma.id == diploma_id).first()

def create(db: Session, diploma: DiplomaCreate):
    db_diploma = Diploma(**diploma.model_dump())

    db.add(db_diploma)
    db.commit()
    db.refresh(db_diploma)

    return db_diploma

def update(db: Session, diploma_id: int, diploma: DiplomaUpdate):
    db_diploma = get_by_id(db, diploma_id)

    if not db_diploma:
        return None

    data = diploma.model_dump(exclude_unset=True)

    for key, value in data.items():
        setattr(db_diploma, key, value)

    db.commit()
    db.refresh(db_diploma)

    return db_diploma

def delete(db: Session, diploma_id: int):
    db_diploma = get_by_id(db, diploma_id)

    if not db_diploma:
        return None

    db.delete(db_diploma)
    db.commit()

    return db_diploma