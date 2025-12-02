from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import asyncio
import os
import json
import time
from pathlib import Path
from redis import Redis
from rq import Queue
from rq.registry import StartedJobRegistry
from ..utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/stream", tags=["Streaming"])

# Configuration Redis (Robustesse: gestion d'erreur si Redis absent)
REDIS_HOST = os.getenv("REDIS_HOST", "redis-bot")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

try:
    redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT, socket_connect_timeout=1)
except Exception as e:
    logger.warning(f"Redis not available for streaming: {e}")
    redis_conn = None

async def event_generator(request: Request, service: str = "worker"):
    """
    Générateur SSE qui envoie les logs et le statut en temps réel.
    """
    # 1. Identification du fichier de log
    log_dir = Path("/app/logs")
    base_name = os.getenv("LOG_FILE", "linkedin_bot.log")
    base_root, ext = os.path.splitext(base_name)

    # Logique de recherche (identique à app.py)
    # On cherche d'abord le fichier spécifique au service (ex: linkedin_bot_worker.log)
    filename = log_dir / f"{base_root}_{service}{ext}"
    if not filename.exists():
        filename = log_dir / f"{service}.log"
    if not filename.exists():
        # Fallback sur le log principal
        filename = log_dir / base_name

    logger.info(f"Stream started for file: {filename}")

    # Ouverture du fichier
    f = None
    try:
        if filename.exists():
            f = open(filename, "r", encoding="utf-8")
            # On se place à la fin du fichier pour ne lire que les nouveaux logs
            f.seek(0, 2)
    except Exception as e:
        logger.error(f"Error opening log file: {e}")
        yield f"event: error\ndata: {json.dumps({'message': 'Could not open log file'})}\n\n"

    last_status_check = 0
    status_check_interval = 2.0  # Vérifier le statut toutes les 2 secondes

    while True:
        # Déconnexion client
        if await request.is_disconnected():
            break

        # --- 1. Lecture des logs ---
        if f:
            try:
                line = f.readline()
                if line:
                    # Envoi de la ligne de log
                    payload = json.dumps({"message": line.strip()})
                    yield f"event: log\ndata: {payload}\n\n"
                    # On continue de lire s'il y a d'autres lignes (burst)
                    # Mais on fait une petite pause pour laisser le CPU respirer si boucle infinie
                    # await asyncio.sleep(0)
                    # Note: Pour un bot, le débit est faible, pas besoin de complexité excessive.
                else:
                    # Pas de nouvelle ligne, on attend un peu
                    pass
            except ValueError:
                # Fichier peut-être fermé ou erreur encodage
                pass

        # --- 2. Lecture du statut Redis ---
        # On ne le fait pas à chaque itération de la boucle de lecture de log
        # pour ne pas spammer Redis, mais on le fait périodiquement.
        now = time.time()
        if now - last_status_check > status_check_interval:
            if redis_conn:
                try:
                    registry = StartedJobRegistry("linkedin-bot", connection=redis_conn)
                    queue = Queue("linkedin-bot", connection=redis_conn)

                    # Récupération légère des compteurs
                    # Note: get_job_ids() est O(N), attention si la queue est immense
                    # Pour un bot personnel, c'est négligeable.
                    active_count = len(registry.get_job_ids())
                    queued_count = len(queue.job_ids)

                    status_payload = {
                        "status": "actif" if active_count > 0 else "inactif",
                        "pending_tasks": queued_count,
                        "busy_workers": active_count
                    }
                    yield f"event: status\ndata: {json.dumps(status_payload)}\n\n"

                except Exception as e:
                    # On ne brise pas le stream pour une erreur redis
                    # logger.warning(f"Redis stream check failed: {e}")
                    pass

            last_status_check = now

        # Pause pour ne pas bloquer l'event loop et économiser CPU (Pi 4)
        await asyncio.sleep(0.1)

    if f:
        f.close()
    logger.info("Stream closed")

@router.get("/events")
async def stream_events(request: Request, service: str = "worker"):
    """
    Endpoint SSE pour logs et status.
    Usage frontend: const evtSource = new EventSource('/api/stream/events?service=worker');
    """
    return StreamingResponse(
        event_generator(request, service),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no" # Important pour Nginx/Proxy
        }
    )
