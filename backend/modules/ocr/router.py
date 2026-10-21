"""
OCR router - Lightweight boundary placeholder.
Planned: Image text extraction, receipt ingestion, and scanned document OCR.
Native system dependencies (e.g. tesseract-ocr) will be installed once the worker
environment is configured for OCR pipelines.
"""
from fastapi import APIRouter
from backend.schemas import StandardResponse, ModulePlaceholderResponse

router = APIRouter(prefix="/ocr", tags=["OCR (Planned)"])


@router.get("", response_model=StandardResponse[ModulePlaceholderResponse])
def get_ocr_module_info():
    """Information endpoint describing planned OCR capabilities."""
    return StandardResponse(
        success=True,
        data=ModulePlaceholderResponse(
            module="ocr",
            status="planned",
            message="OCR module placeholder. Heavy libraries and native engines will be introduced in subsequent phases.",
            capabilities_planned=[
                "Extract structured text from images and screenshots",
                "Receipt scanner and expense auto-extraction",
                "Document search index integration",
            ],
        ),
    )
