from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from metadata import get_db, SessionDep
from models import Note, NoteCreate, NoteOut, NoteUpdate, User, require_owner, get_current_user

router = APIRouter(
    prefix="/notes",
    tags=["notes"]
)

@router.post("/", response_model=NoteOut)
async def create_note(note: NoteCreate, session: SessionDep, current_user: User = Depends(get_current_user)):
    new_note = Note(title=note.title, content=note.content, owner_id=current_user.id)
    session.add(new_note)
    await session.commit()
    await session.refresh(new_note)
    return new_note

@router.get("/", response_model=list[NoteOut])
async def list_notes(session: SessionDep, current_user: User = Depends(get_current_user)):
    stmt = select(Note).where(Note.owner_id == current_user.id)
    result = await session.execute(stmt)
    return result.scalars().all()

@router.get("/{note_id}", response_model=NoteOut)
async def get_note(note_id: int, session: SessionDep, current_user: User = Depends(get_current_user)):
    stmt = select(Note).where(Note.id == note_id, Note.owner_id == current_user.id)
    result = await session.execute(stmt)
    note = result.scalars().first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found or access denied")
    return note

@router.put("/{note_id}", response_model=NoteOut)
async def update_note(note_id: int, note: NoteUpdate, session: SessionDep, current_user: User = Depends(get_current_user)):
    stmt = select(Note).where(Note.id == note_id, Note.owner_id == current_user.id)
    result = await session.execute(stmt)
    db_note = result.scalars().first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found or access denied")
    if note.title is not None:
        db_note.title = note.title
    if note.content is not None:
        db_note.content = note.content
    session.add(db_note)
    await session.commit()
    await session.refresh(db_note)
    return db_note

@router.delete("/{note_id}")
async def delete_note(note_id: int, session: SessionDep, current_user: User = Depends(get_current_user)):
    stmt = select(Note).where(Note.id == note_id, Note.owner_id == current_user.id)
    result = await session.execute(stmt)
    note = result.scalars().first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found or access denied")
    session.delete(note)
    await session.commit()
    return {"detail": "Note deleted"}