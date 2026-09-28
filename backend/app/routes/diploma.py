from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.diploma_schema import (DiplomaCreate, DiplomaUpdate, DiplomaResponse)
from app.services import diploma_service
from app.auth.dependencies import get_current_user, require_admin

router = APIRouter(
    prefix="/diplomas",
    tags=["Diplomas"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/", response_model=list[DiplomaResponse])
def get_diplomas(db: Session = Depends(get_db)):
    return diploma_service.get_all(db)

@router.get("/{diploma_id}", response_model=DiplomaResponse)
def get_diploma(diploma_id: int, db: Session = Depends(get_db)):
    diploma = diploma_service.get_by_id(db, diploma_id)

    if not diploma:
        raise HTTPException(404, "Diploma no encontrado")

    return diploma

@router.post("/", response_model=DiplomaResponse, dependencies=[Depends(require_admin)])
def create_diploma(
    diploma: DiplomaCreate,
    db: Session = Depends(get_db)
):
    return diploma_service.create(db, diploma)

@router.put("/{diploma_id}", response_model=DiplomaResponse, dependencies=[Depends(require_admin)])
def update_diploma(
    diploma_id: int,
    diploma: DiplomaUpdate,
    db: Session = Depends(get_db)
):
    updated = diploma_service.update(db, diploma_id, diploma)

    if not updated:
        raise HTTPException(404, "Diploma no encontrado")

    return updated

@router.delete("/{diploma_id}", dependencies=[Depends(require_admin)])
def delete_diploma(
    diploma_id: int,
    db: Session = Depends(get_db)
):
    deleted = diploma_service.delete(db, diploma_id)

    if not deleted:
        raise HTTPException(404, "Diploma no encontrado")

    return {"message": "Diploma eliminado correctamente"}