from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
import zipfile
from pathlib import Path
from datetime import datetime
from src.api.security import verify_api_key
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/debug", tags=["Debug"])

@router.get("/report")
async def get_debug_report(authenticated: bool = Depends(verify_api_key)):
    """
    Generates a ZIP file containing:
    - Recent logs
    - Screenshots (if any)
    - HTML dumps (if any)
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"/tmp/debug_report_{timestamp}.zip"

        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:

            # 1. Add Logs
            log_dir = Path("/app/logs")
            if log_dir.exists():
                for log_file in log_dir.glob("*.log"):
                    try:
                        zipf.write(log_file, arcname=f"logs/{log_file.name}")
                    except Exception as e:
                        logger.warning(f"Could not add log {log_file}: {e}", exc_info=True)

            # 2. Add Debug Data (Screenshots/HTML)
            data_dirs = [
                Path("/app/data/debug"),
                Path("/app/data/screenshots")
            ]

            for d in data_dirs:
                if d.exists():
                    for f in d.glob("*"):
                        if f.is_file():
                            try:
                                zipf.write(f, arcname=f"{d.name}/{f.name}")
                            except Exception as e:
                                logger.warning(f"Could not add file {f}: {e}", exc_info=True)

        return FileResponse(
            path=zip_filename,
            filename=f"debug_report_{timestamp}.zip",
            media_type="application/zip"
        )

    except Exception as e:
        logger.error(f"Failed to generate debug report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
