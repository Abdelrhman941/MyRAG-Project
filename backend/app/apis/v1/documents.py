from typing import Annotated

from fastapi import APIRouter, File, Request, UploadFile, status

from ...core import limiter
from ...core.exceptions import AppError, TooManyFilesError
from ...dependencies import SessionDep, SettingsDep, StorageDep
from ...models import Document
from ...schemas import (
    BatchUploadError,
    BatchUploadResponse,
    BatchUploadResult,
    DocumentResponse,
)
from ...services import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new document",
)
@limiter.limit("10/hour")
async def upload_document(
    request: Request,
    file: UploadFile,
    db: SessionDep,
    storage: StorageDep,
    settings: SettingsDep,
) -> DocumentResponse:
    """Upload a single document to the RAG system."""
    service = DocumentService(db, storage, settings)
    document = await service.upload_document(file)
    return DocumentResponse.model_validate(document)


@router.post(
    "/batch",
    response_model=BatchUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload up to 10 documents in one request",
)
@limiter.limit("10/hour")
async def upload_batch(
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

    service = DocumentService(db, storage, settings)
    raw_results: list[Document | BaseException] = await service.upload_batch(files)

    results: list[BatchUploadResult] = []
    for file, outcome in zip(files, raw_results, strict=True):
        filename = file.filename or ""
        if isinstance(outcome, Document):
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
