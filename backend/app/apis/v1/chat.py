import json
from collections.abc import AsyncGenerator
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ...core import get_settings, limiter
from ...core.exceptions import AppError, TooManyFilesError
from ...dependencies import (
    ArqPoolDep,
    ChatServiceDep,
    DocumentServiceDep,
    SessionRepositoryDep,
    SettingsDep,
    ValidSessionDep,
)
from ...models import Document
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
from ...services.chat_service import ChatAnswer

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
async def list_messages(
    session_id: ValidSessionDep, repository: SessionRepositoryDep
) -> Any:
    messages = await repository.list_messages(session_id)
    return {"messages": messages}


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: ValidSessionDep,
    repository: SessionRepositoryDep,
    doc_service: DocumentServiceDep,
    force: bool = False,
) -> Response:
    await doc_service.delete_session_data(session_id, force=force)

    await repository.delete_session(session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


class ChatRequest(BaseModel):
    question: str


@router.post("/sessions/{session_id}/messages/stream", response_class=StreamingResponse)
async def ask_question_stream(
    session_id: ValidSessionDep,
    request: ChatRequest,
    chat_service: ChatServiceDep,
    background_tasks: BackgroundTasks,
) -> StreamingResponse:
    async def event_generator() -> AsyncGenerator[str, None]:
        async for event in chat_service.answer_stream(
            session_id, request.question, background_tasks
        ):
            if event["event"] == "ping":
                yield ": ping\n\n"
            else:
                yield f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/sessions/{session_id}/messages", response_model=ChatAnswer)
async def ask_question(
    session_id: ValidSessionDep,
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
@limiter.limit(lambda: get_settings().UPLOAD_RATE_LIMIT)
async def upload_document(
    session_id: ValidSessionDep,
    request: Request,
    file: UploadFile,
    doc_service: DocumentServiceDep,
    arq_pool: ArqPoolDep,
) -> DocumentResponse:
    """Upload a single document to the RAG system."""
    document = await doc_service.upload_document(file, session_id)
    await arq_pool.enqueue_job("ingest_document", str(document.id))
    return DocumentResponse.model_validate(document)


@router.post(
    "/sessions/{session_id}/documents/batch",
    response_model=BatchUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload up to 10 documents in one request",
)
@limiter.limit(lambda: get_settings().UPLOAD_RATE_LIMIT)
async def upload_batch(
    session_id: ValidSessionDep,
    request: Request,
    files: Annotated[list[UploadFile], File(...)],
    doc_service: DocumentServiceDep,
    settings: SettingsDep,
    arq_pool: ArqPoolDep,
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

    raw_results: list[Document | BaseException] = await doc_service.upload_batch(
        files, session_id
    )

    results: list[BatchUploadResult] = []
    for file, outcome in zip(files, raw_results, strict=True):
        filename = file.filename or ""
        if isinstance(outcome, Document):
            await arq_pool.enqueue_job("ingest_document", str(outcome.id))
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
    session_id: ValidSessionDep,
    doc_service: DocumentServiceDep,
    limit: int = 50,
    offset: int = 0,
) -> list[DocumentResponse]:
    """List all documents, newest first."""
    docs = await doc_service.list_documents(session_id, limit=limit, offset=offset)
    return [DocumentResponse.model_validate(d) for d in docs]
