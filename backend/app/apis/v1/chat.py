from typing import Any
from uuid import UUID

from fastapi import APIRouter, Response, status

from ...dependencies import SessionRepositoryDep
from ...schemas.chat import (
    ChatMessageListResponse,
    ChatSessionListResponse,
    ChatSessionResponse,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED
)
async def create_session(repository: SessionRepositoryDep) -> Any:
    session_id = await repository.create_session()
    session = await repository.get_session(session_id)
    return session


@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_sessions(repository: SessionRepositoryDep) -> Any:
    sessions = await repository.list_sessions()
    return {"sessions": sessions}


@router.get("/sessions/{session_id}/messages", response_model=ChatMessageListResponse)
async def list_messages(session_id: UUID, repository: SessionRepositoryDep) -> Any:
    # Verify session exists
    session = await repository.get_session(session_id)
    if not session:
        from ...core.exceptions import NotFoundError

        raise NotFoundError(message=f"Session {session_id} not found")

    messages = await repository.list_messages(session_id)
    return {"messages": messages}


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID, repository: SessionRepositoryDep
) -> Response:
    await repository.delete_session(session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
