from typing import Annotated, Any
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Request,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel
from sqlalchemy import select

from ...core import limiter
from ...core.exceptions import AppError, TooManyFilesError
from ...dependencies import (
    ChatServiceDep,
    SessionDep,
    SessionRepositoryDep,
    SettingsDep,
    StorageDep,
    VectorStoreDep,
)
from ...models import ChatSession, Document
from ...schemas import (
    BatchUploadError,
    BatchUploadResponse,
    BatchUploadResult,
    DocumentResponse,
)
from ...schemas.chat import (
    ChatMessageListResponse,
    ChatSessionListResponse,
    ChatSessionResponse,
)
from ...services import DocumentService
from ...services.chat_service import ChatAnswer
from .documents import run_ingestion_background

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
    session_id: UUID,
    repository: SessionRepositoryDep,
    db: SessionDep,
    storage: StorageDep,
    vector_store: VectorStoreDep,
    settings: SettingsDep,
) -> Response:
    from ...services import DocumentService

    # Verify session exists
    session = await repository.get_session(session_id)
    if not session:
        from ...core.exceptions import NotFoundError

        raise NotFoundError(message=f"Session {session_id} not found")

    doc_service = DocumentService(db, storage, settings, vector_store)
    await doc_service.delete_session_data(session_id)

    await repository.delete_session(session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


class ChatRequest(BaseModel):
    question: str


@router.post("/sessions/{session_id}/messages", response_model=ChatAnswer)
async def ask_question(
    session_id: UUID,
    request: ChatRequest,
    chat_service: ChatServiceDep,
    background_tasks: BackgroundTasks,
) -> Any:
    return await chat_service.answer(session_id, request.question, background_tasks)


@router.post(
    "/sessions/{session_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new document",
)
@limiter.limit("10/hour")
async def upload_document(
    session_id: UUID,
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile,
    db: SessionDep,
    storage: StorageDep,
    settings: SettingsDep,
) -> DocumentResponse:
    """Upload a single document to the RAG system."""
    session_check = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id)
    )
    if not session_check.scalar_one_or_none():
        from ...core.exceptions import NotFoundError

        raise NotFoundError(message=f"Session {session_id} not found")
    service = DocumentService(db, storage, settings)
    document = await service.upload_document(file, session_id)
    background_tasks.add_task(run_ingestion_background, document.id)
    return DocumentResponse.model_validate(document)


@router.post(
    "/sessions/{session_id}/documents/batch",
    response_model=BatchUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload up to 10 documents in one request",
)
@limiter.limit("10/hour")
async def upload_batch(
    session_id: UUID,
    background_tasks: BackgroundTasks,
    request: Request,
    files: Annotated[list[UploadFile], File(...)],
    db: SessionDep,
    storage: StorageDep,
    settings: SettingsDep,
) -> BatchUploadResponse:
    """Upload multiple documents (up to 10) in a single multipart request.

    Returns one result entry per file; a per-file error never fails the batch.
    """
    if len(files) > settings.MAX_FILES_PER_REQUEST:
        raise TooManyFilesError(
            message=(
                f"Too many files. Maximum {settings.MAX_FILES_PER_REQUEST} "
                "files per request."
            )
        )

    session_check = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id)
    )
    if not session_check.scalar_one_or_none():
        from ...core.exceptions import NotFoundError

        raise NotFoundError(message=f"Session {session_id} not found")
    service = DocumentService(db, storage, settings)
    raw_results: list[Document | BaseException] = await service.upload_batch(
        files, session_id
    )

    results: list[BatchUploadResult] = []
    for file, outcome in zip(files, raw_results, strict=True):
        filename = file.filename or ""
        if isinstance(outcome, Document):
            background_tasks.add_task(run_ingestion_background, outcome.id)
            results.append(
                BatchUploadResult(
                    filename=filename,
                    ok=True,
                    document=DocumentResponse.model_validate(outcome),
                )
            )
        else:
            # Map AppError subclasses to their defined code/message; fall back
            # to a generic internal error for anything unexpected.
            if isinstance(outcome, AppError):
                error = BatchUploadError(
                    code=outcome.code,
                    message=outcome.message,
                )
            else:
                error = BatchUploadError(
                    code="internal_error",
                    message="An unexpected error occurred while processing this file.",
                )
            results.append(BatchUploadResult(filename=filename, ok=False, error=error))

    return BatchUploadResponse(results=results)


@router.get(
    "/sessions/{session_id}/documents",
    response_model=list[DocumentResponse],
    summary="List documents",
)
async def list_documents(
    session_id: UUID,
    db: SessionDep,
    storage: StorageDep,
    settings: SettingsDep,
    limit: int = 50,
    offset: int = 0,
) -> list[DocumentResponse]:
    """List all documents, newest first."""
    session_check = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id)
    )
    if not session_check.scalar_one_or_none():
        from ...core.exceptions import NotFoundError

        raise NotFoundError(message=f"Session {session_id} not found")
    service = DocumentService(db, storage, settings)
    docs = await service.list_documents(session_id, limit=limit, offset=offset)
    return [DocumentResponse.model_validate(d) for d in docs]
