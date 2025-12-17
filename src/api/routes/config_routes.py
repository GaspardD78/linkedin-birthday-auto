"""
Configuration Routes - Gestion des fichiers de configuration et messages

Ce module expose les endpoints pour gérer les fichiers de configuration
textuels utilisés par le bot LinkedIn (messages d'anniversaire).

Endpoints:
- GET /config/messages : Lit le contenu de messages.txt
- POST /config/messages : Met à jour messages.txt
- GET /config/late-messages : Lit le contenu de late_messages.txt
- POST /config/late-messages : Met à jour late_messages.txt

Architecture:
- Utilise aiofiles pour I/O asynchrone (optimisé RPi4)
- Validation des données avec Pydantic
- Sécurisé par API Key
- Gestion d'erreurs robuste

Note RPi4:
L'utilisation de aiofiles évite de bloquer l'Event Loop FastAPI pendant
les opérations disque, critique sur Raspberry Pi avec carte SD.
"""

import os
import logging
from pathlib import Path
from typing import Literal

import aiofiles
from fastapi import APIRouter, HTTPException, Security
from pydantic import BaseModel, Field, field_validator

from src.api.security import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/config",
    tags=["Configuration"],
)

# ==============================================================================
# CONFIGURATION DES CHEMINS
# ==============================================================================

# Dossier data monté via docker-compose
DATA_DIR = Path("/app/data")

# Fallback vers dossier local si pas dans Docker
if not DATA_DIR.exists():
    DATA_DIR = Path("./data")
    logger.warning(f"Docker volume not found, using local path: {DATA_DIR}")

# Chemins des fichiers
MESSAGES_FILE = DATA_DIR / "messages.txt"
LATE_MESSAGES_FILE = DATA_DIR / "late_messages.txt"

# ==============================================================================
# MODELS PYDANTIC
# ==============================================================================

class MessageContent(BaseModel):
    """Modèle pour le contenu d'un fichier de messages"""
    content: str = Field(
        ...,
        description="Contenu du fichier de messages",
        min_length=1,
        max_length=50000
    )

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validation du contenu des messages"""
        # Supprimer les espaces superflus au début/fin
        v = v.strip()

        if not v:
            raise ValueError("Le contenu ne peut pas être vide")

        # Vérifier qu'il y a au moins une ligne non vide
        lines = [line.strip() for line in v.split('\n') if line.strip()]
        if not lines:
            raise ValueError("Le fichier doit contenir au moins un message")

        return v


class MessageFileResponse(BaseModel):
    """Réponse lors de la lecture d'un fichier de messages"""
    content: str = Field(..., description="Contenu du fichier")
    file_path: str = Field(..., description="Chemin du fichier")
    lines_count: int = Field(..., description="Nombre de lignes non vides")
    size_bytes: int = Field(..., description="Taille du fichier en octets")


class MessageFileUpdateResponse(BaseModel):
    """Réponse lors de la mise à jour d'un fichier"""
    status: str = Field(default="success", description="Statut de l'opération")
    message: str = Field(..., description="Message de confirmation")
    file_path: str = Field(..., description="Chemin du fichier mis à jour")
    lines_count: int = Field(..., description="Nombre de lignes après mise à jour")
    backup_created: bool = Field(..., description="Si une sauvegarde a été créée")

# ==============================================================================
# HELPERS - I/O ASYNCHRONE
# ==============================================================================

async def read_message_file(file_path: Path) -> MessageFileResponse:
    """
    Lit un fichier de messages de manière asynchrone

    Args:
        file_path: Chemin du fichier à lire

    Returns:
        MessageFileResponse avec le contenu et métadonnées

    Raises:
        HTTPException: Si le fichier n'existe pas ou erreur de lecture
    """
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        raise HTTPException(
            status_code=404,
            detail=f"Fichier non trouvé: {file_path.name}. "
                   f"Vérifiez que le volume Docker est correctement monté."
        )

    try:
        async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
            content = await f.read()

        # Calculer les métadonnées
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        size_bytes = file_path.stat().st_size

        logger.info(f"File read successfully: {file_path.name} ({size_bytes} bytes, {len(lines)} lines)")

        return MessageFileResponse(
            content=content,
            file_path=str(file_path),
            lines_count=len(lines),
            size_bytes=size_bytes
        )

    except PermissionError:
        logger.error(f"Permission denied reading: {file_path}")
        raise HTTPException(
            status_code=403,
            detail=f"Permissions insuffisantes pour lire {file_path.name}. "
                   f"Lancez: sudo ./scripts/fix_permissions.sh"
        )
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la lecture du fichier: {str(e)}"
        )


async def write_message_file(
    file_path: Path,
    content: str,
    create_backup: bool = True
) -> MessageFileUpdateResponse:
    """
    Écrit un fichier de messages de manière asynchrone

    Args:
        file_path: Chemin du fichier à écrire
        content: Nouveau contenu
        create_backup: Si True, crée une sauvegarde avant écriture

    Returns:
        MessageFileUpdateResponse avec statut et métadonnées

    Raises:
        HTTPException: Si erreur d'écriture ou permissions
    """
    backup_created = False

    try:
        # Créer une sauvegarde si le fichier existe
        if create_backup and file_path.exists():
            backup_path = file_path.with_suffix(f"{file_path.suffix}.bak")

            async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f_in:
                old_content = await f_in.read()

            async with aiofiles.open(backup_path, mode='w', encoding='utf-8') as f_out:
                await f_out.write(old_content)

            backup_created = True
            logger.info(f"Backup created: {backup_path}")

        # Écrire le nouveau contenu
        async with aiofiles.open(file_path, mode='w', encoding='utf-8') as f:
            await f.write(content)

        # Calculer les métadonnées
        lines = [line.strip() for line in content.split('\n') if line.strip()]

        logger.info(f"File written successfully: {file_path.name} ({len(lines)} lines)")

        return MessageFileUpdateResponse(
            status="success",
            message=f"Fichier {file_path.name} mis à jour avec succès",
            file_path=str(file_path),
            lines_count=len(lines),
            backup_created=backup_created
        )

    except PermissionError:
        logger.error(f"Permission denied writing: {file_path}")
        raise HTTPException(
            status_code=403,
            detail=f"Permissions insuffisantes pour écrire {file_path.name}. "
                   f"Lancez: sudo ./scripts/fix_permissions.sh"
        )
    except Exception as e:
        logger.error(f"Error writing {file_path}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'écriture du fichier: {str(e)}"
        )

# ==============================================================================
# ENDPOINTS - MESSAGES
# ==============================================================================

@router.get(
    "/messages",
    response_model=MessageFileResponse,
    summary="Récupérer les messages d'anniversaire",
    description="Lit le contenu du fichier messages.txt contenant les messages d'anniversaire standards"
)
async def get_messages(
    api_key: str = Security(verify_api_key)
) -> MessageFileResponse:
    """
    GET /config/messages

    Lit le fichier messages.txt et retourne son contenu avec métadonnées.

    Returns:
        MessageFileResponse avec le contenu du fichier
    """
    return await read_message_file(MESSAGES_FILE)


@router.post(
    "/messages",
    response_model=MessageFileUpdateResponse,
    summary="Mettre à jour les messages d'anniversaire",
    description="Écrase le contenu du fichier messages.txt avec de nouveaux messages"
)
async def update_messages(
    data: MessageContent,
    api_key: str = Security(verify_api_key)
) -> MessageFileUpdateResponse:
    """
    POST /config/messages

    Met à jour le fichier messages.txt avec le nouveau contenu.
    Une sauvegarde (.bak) est automatiquement créée.

    Args:
        data: MessageContent contenant le nouveau contenu

    Returns:
        MessageFileUpdateResponse avec statut de la mise à jour
    """
    return await write_message_file(MESSAGES_FILE, data.content, create_backup=True)


# ==============================================================================
# ENDPOINTS - LATE MESSAGES
# ==============================================================================

@router.get(
    "/late-messages",
    response_model=MessageFileResponse,
    summary="Récupérer les messages d'anniversaire tardifs",
    description="Lit le contenu du fichier late_messages.txt pour les anniversaires manqués"
)
async def get_late_messages(
    api_key: str = Security(verify_api_key)
) -> MessageFileResponse:
    """
    GET /config/late-messages

    Lit le fichier late_messages.txt et retourne son contenu avec métadonnées.

    Returns:
        MessageFileResponse avec le contenu du fichier
    """
    return await read_message_file(LATE_MESSAGES_FILE)


@router.post(
    "/late-messages",
    response_model=MessageFileUpdateResponse,
    summary="Mettre à jour les messages d'anniversaire tardifs",
    description="Écrase le contenu du fichier late_messages.txt"
)
async def update_late_messages(
    data: MessageContent,
    api_key: str = Security(verify_api_key)
) -> MessageFileUpdateResponse:
    """
    POST /config/late-messages

    Met à jour le fichier late_messages.txt avec le nouveau contenu.
    Une sauvegarde (.bak) est automatiquement créée.

    Args:
        data: MessageContent contenant le nouveau contenu

    Returns:
        MessageFileUpdateResponse avec statut de la mise à jour
    """
    return await write_message_file(LATE_MESSAGES_FILE, data.content, create_backup=True)


# ==============================================================================
# ENDPOINT - VALIDATION DES FICHIERS AU DÉMARRAGE
# ==============================================================================

@router.get(
    "/messages/health",
    summary="Vérifier la présence et l'accessibilité des fichiers de messages",
    description="Endpoint de santé pour vérifier que les fichiers sont accessibles"
)
async def check_messages_health(
    api_key: str = Security(verify_api_key)
) -> dict:
    """
    GET /config/messages/health

    Vérifie que les fichiers de messages existent et sont lisibles.
    Utile pour le monitoring et le debugging.

    Returns:
        dict avec le statut de chaque fichier
    """
    status = {
        "messages.txt": {
            "exists": MESSAGES_FILE.exists(),
            "readable": False,
            "size_bytes": 0
        },
        "late_messages.txt": {
            "exists": LATE_MESSAGES_FILE.exists(),
            "readable": False,
            "size_bytes": 0
        }
    }

    # Vérifier messages.txt
    if status["messages.txt"]["exists"]:
        try:
            async with aiofiles.open(MESSAGES_FILE, mode='r', encoding='utf-8') as f:
                await f.read(1)  # Juste lire 1 caractère pour tester
            status["messages.txt"]["readable"] = True
            status["messages.txt"]["size_bytes"] = MESSAGES_FILE.stat().st_size
        except Exception as e:
            logger.error(f"Cannot read messages.txt: {e}")

    # Vérifier late_messages.txt
    if status["late_messages.txt"]["exists"]:
        try:
            async with aiofiles.open(LATE_MESSAGES_FILE, mode='r', encoding='utf-8') as f:
                await f.read(1)
            status["late_messages.txt"]["readable"] = True
            status["late_messages.txt"]["size_bytes"] = LATE_MESSAGES_FILE.stat().st_size
        except Exception as e:
            logger.error(f"Cannot read late_messages.txt: {e}")

    # Déterminer le statut global
    all_ok = (
        status["messages.txt"]["exists"] and status["messages.txt"]["readable"] and
        status["late_messages.txt"]["exists"] and status["late_messages.txt"]["readable"]
    )

    return {
        "status": "healthy" if all_ok else "degraded",
        "data_dir": str(DATA_DIR),
        "files": status
    }
