from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies.auth import require_admin
from api.schemas.TeamSchema import TeamMemberCreate, TeamMemberResponse, TeamMemberUpdate
from dbase.collections.TeamCollection import TeamCollection

router = APIRouter(prefix="/team", tags=["team"])
team_db = TeamCollection()


@router.get("", response_model=list[TeamMemberResponse])
def list_team_members():
    """List all team members (public endpoint for main page)."""
    return team_db.list()


@router.get("/{member_id}", response_model=TeamMemberResponse)
def get_team_member(member_id: str):
    """Get a single team member by ID."""
    item = team_db.get(member_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found")
    return item


@router.post("", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED)
def create_team_member(payload: TeamMemberCreate, _admin: dict = Depends(require_admin)):
    """Create a new team member."""
    data = payload.model_dump(exclude_none=True)
    return team_db.create(data)


@router.put("/{member_id}", response_model=TeamMemberResponse)
def update_team_member(member_id: str, payload: TeamMemberUpdate, _admin: dict = Depends(require_admin)):
    """Update a team member."""
    updates = payload.model_dump(exclude_none=True)
    updated = team_db.update(member_id, updates)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found")
    return updated


@router.delete("/{member_id}")
def delete_team_member(member_id: str, _admin: dict = Depends(require_admin)):
    """Delete a team member."""
    deleted = team_db.delete(member_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found")
    return {"message": "Team member deleted"}
