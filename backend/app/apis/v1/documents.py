from fastapi import APIRouter, UploadFile, status

from ...dependencies import SessionDep, SettingsDep, StorageDep
from ...schemas import DocumentResponse
from ...services import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new document",
)
async def upload_document(
    file: UploadFile,
    db: SessionDep,
    storage: StorageDep,
    settings: SettingsDep,
) -> DocumentResponse:
    """Upload a single document to the RAG system."""
    service = DocumentService(db, storage, settings)
    document = await service.upload_document(file)
    return DocumentResponse.model_validate(document)
