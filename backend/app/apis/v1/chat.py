from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse

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
    ChatAnswer,
    ChatMessageListResponse,
    ChatMessageResponse,
    ChatRequest,
    ChatSessionListResponse,
    ChatSessionResponse,
    DocumentResponse,
)

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


@router.post(
    "/sessions",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    repository: SessionRepositoryDep,
) -> ChatSessionResponse:
    """Create a new chat session."""
    session_id = await repository.create_session()
    session = await repository.get_session(session_id)

    if session is None:
        raise RuntimeError(
            "Created chat session could not be loaded.",
        )

    return ChatSessionResponse.model_validate(session)


@router.get(
    "/sessions",
    response_model=ChatSessionListResponse,
)
async def list_sessions(
    repository: SessionRepositoryDep,
) -> ChatSessionListResponse:
    """List chat sessions."""
    sessions = await repository.list_sessions()

    return ChatSessionListResponse(
        sessions=[ChatSessionResponse.model_validate(session) for session in sessions],
    )


@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionResponse,
)
async def get_session(
    session: ValidSessionDep,
) -> ChatSessionResponse:
    """Return a chat session."""
    return ChatSessionResponse.model_validate(session)


@router.get(
    "/sessions/{session_id}/messages",
    response_model=ChatMessageListResponse,
)
async def list_messages(
    session: ValidSessionDep,
    repository: SessionRepositoryDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ChatMessageListResponse:
    """List messages for a chat session."""
    messages = await repository.get_messages(
        session["id"],
        offset=offset,
        limit=limit,
    )

    return ChatMessageListResponse(
        messages=[
            ChatMessageResponse.model_validate(message, from_attributes=True)
            for message in messages
        ],
    )


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_session(
    session: ValidSessionDep,
    repository: SessionRepositoryDep,
    doc_service: DocumentServiceDep,
    force: bool = False,
) -> None:
    """Delete a session and all associated documents."""
    await doc_service.delete_session_data(
        session["id"],
        force=force,
    )

    await repository.delete_session(
        session["id"],
    )


@router.post(
    "/sessions/{session_id}/messages/stream",
    response_class=StreamingResponse,
)
@limiter.limit(lambda: get_settings().CHAT_RATE_LIMIT)
async def ask_question_stream(
    request: Request,
    session: ValidSessionDep,
    payload: ChatRequest,
    chat_service: ChatServiceDep,
    background_tasks: BackgroundTasks,
) -> StreamingResponse:
    """Stream an assistant response using server-sent events."""

    async def event_generator() -> AsyncGenerator[str, None]:
        async for event in chat_service.answer_stream(
            session["id"],
            session,
            payload.question,
            background_tasks,
        ):
            if event["event"] == "ping":
                yield ": ping\n\n"
                continue

            yield (
                f"event: {event['event']}\n"
                f"data: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatAnswer,
)
@limiter.limit(lambda: get_settings().CHAT_RATE_LIMIT)
async def ask_question(
    request: Request,
    session: ValidSessionDep,
    payload: ChatRequest,
    chat_service: ChatServiceDep,
    background_tasks: BackgroundTasks,
) -> ChatAnswer:
    """Generate a complete assistant response."""
    return await chat_service.answer(
        session["id"],
        session,
        payload.question,
        background_tasks,
    )


@router.post(
    "/sessions/{session_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new document",
)
@limiter.limit(lambda: get_settings().UPLOAD_RATE_LIMIT)
async def upload_document(
    request: Request,
    session: ValidSessionDep,
    file: UploadFile,
    doc_service: DocumentServiceDep,
    arq_pool: ArqPoolDep,
) -> DocumentResponse:
    """Upload and queue a document for background ingestion."""
    document = await doc_service.upload_document(
        file,
        session["id"],
    )

    await arq_pool.enqueue_job(
        "ingest_document",
        str(document.id),
    )

    return DocumentResponse.model_validate(document)


@router.post(
    "/sessions/{session_id}/documents/batch",
    response_model=BatchUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload multiple documents",
)
@limiter.limit(lambda: get_settings().UPLOAD_RATE_LIMIT)
async def upload_batch(
    request: Request,
    session: ValidSessionDep,
    files: Annotated[list[UploadFile], File(...)],
    doc_service: DocumentServiceDep,
    settings: SettingsDep,
    arq_pool: ArqPoolDep,
) -> BatchUploadResponse:
    """Upload multiple documents and queue successful uploads."""
    if len(files) > settings.MAX_FILES_PER_REQUEST:
        raise TooManyFilesError(
            message=(
                f"Too many files. Maximum "
                f"{settings.MAX_FILES_PER_REQUEST} files per request."
            ),
        )

    raw_results = await doc_service.upload_batch(
        files,
        session["id"],
    )

    results: list[BatchUploadResult] = []

    for file, outcome in zip(
        files,
        raw_results,
        strict=True,
    ):
        filename = file.filename or ""

        if isinstance(outcome, Document):
            await arq_pool.enqueue_job(
                "ingest_document",
                str(outcome.id),
            )

            results.append(
                BatchUploadResult(
                    filename=filename,
                    ok=True,
                    document=DocumentResponse.model_validate(outcome),
                ),
            )
            continue

        if isinstance(outcome, AppError):
            error = BatchUploadError(
                code=outcome.code,
                message=outcome.message,
            )
        else:
            error = BatchUploadError(
                code="internal_error",
                message=("An unexpected error occurred while processing this file."),
            )

        results.append(
            BatchUploadResult(
                filename=filename,
                ok=False,
                error=error,
            ),
        )

    return BatchUploadResponse(results=results)


@router.get(
    "/sessions/{session_id}/documents",
    response_model=list[DocumentResponse],
    summary="List documents",
)
async def list_documents(
    session: ValidSessionDep,
    doc_service: DocumentServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DocumentResponse]:
    """List documents belonging to a session."""
    documents = await doc_service.list_documents(
        session["id"],
        limit=limit,
        offset=offset,
    )

    return [DocumentResponse.model_validate(document) for document in documents]
