from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Journal API", version="1.0.0")

entries: dict[str, dict] = {}


class JournalCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1)


class JournalUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    body: Optional[str] = Field(None, min_length=1)


class JournalEntry(BaseModel):
    id: str
    title: str
    body: str
    created_at: datetime
    updated_at: datetime


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/entries", response_model=list[JournalEntry])
def list_entries() -> list[dict]:
    return list(entries.values())


@app.post("/entries", response_model=JournalEntry, status_code=201)
def create_entry(payload: JournalCreate) -> dict:
    now = datetime.now(timezone.utc)
    entry_id = str(uuid4())
    entry = {
        "id": entry_id,
        "title": payload.title,
        "body": payload.body,
        "created_at": now,
        "updated_at": now,
    }
    entries[entry_id] = entry
    return entry


@app.get("/entries/{entry_id}", response_model=JournalEntry)
def get_entry(entry_id: str) -> dict:
    entry = entries.get(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@app.patch("/entries/{entry_id}", response_model=JournalEntry)
def update_entry(entry_id: str, payload: JournalUpdate) -> dict:
    entry = entries.get(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    if payload.title is not None:
        entry["title"] = payload.title
    if payload.body is not None:
        entry["body"] = payload.body
    entry["updated_at"] = datetime.now(timezone.utc)
    return entry


@app.delete("/entries/{entry_id}", status_code=204)
def delete_entry(entry_id: str) -> None:
    if entry_id not in entries:
        raise HTTPException(status_code=404, detail="Entry not found")
    del entries[entry_id]
