from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select
from metadata import SessionDep
from models import Note, NoteCreate, NoteOut, NoteUpdate, User, get_current_user
from config.redis_cache import redis_cache

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
@redis_cache.cache(key_prefix="notes", ttl=60)
async def list_notes(
    session: SessionDep, 
    current_user: User = Depends(get_current_user), 
    skip: int = Query(0, ge=0),
    limit: int = Query(10, le=100),
    search: str = Query(None)
    ):

    stmt = select(Note).where(Note.owner_id == current_user.id)
    if search:
        search_term = f"%{search}%"
        stmt = stmt.where(
            (Note.title.ilike(search_term)) | (Note.content.ilike(search_term))
        )
    stmt = stmt.offset(skip).limit(limit)
    result = await session.execute(stmt)
    notes = result.scalars().all()
    return notes

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