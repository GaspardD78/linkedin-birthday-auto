"""
Configuration du tracing distribué avec OpenTelemetry.

Pour activer le tracing :
1. Déployer un collecteur OTLP (Jaeger, OTEL Collector, etc.)
2. Définir ENABLE_TELEMETRY=true dans les variables d'environnement
3. Optionnel: Définir OTEL_EXPORTER_OTLP_ENDPOINT (défaut: http://localhost:4317)

Exemple docker-compose:
  environment:
    - ENABLE_TELEMETRY=true
    - OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
"""

import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from ..utils.logging import get_logger

logger = get_logger(__name__)

def setup_tracing(service_name: str = "linkedin-bot", endpoint: Optional[str] = None) -> Optional[trace.Tracer]:
    """
    Configure OpenTelemetry pour l'application.

    Args:
        service_name: Nom du service
        endpoint: Endpoint OTLP (gRPC). Si None, utilise la variable d'environnement OTEL_EXPORTER_OTLP_ENDPOINT

    Returns:
        Tracer ou None si désactivé
    """
    # Vérifier si le tracing est activé
    tracing_enabled = os.getenv("ENABLE_TELEMETRY", "false").lower() in ("true", "1", "yes")

    if not tracing_enabled:
        logger.info("tracing_disabled", reason="ENABLE_TELEMETRY not set to true")
        # Retourner un tracer par défaut même si désactivé (pour éviter les erreurs)
        trace.set_tracer_provider(TracerProvider())
        return trace.get_tracer(__name__)

    # Obtenir l'endpoint depuis les paramètres ou l'environnement
    if endpoint is None:
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

    try:
        # Créer la ressource (identifie le service)
        resource = Resource.create(attributes={
            "service.name": service_name,
            "deployment.environment": os.getenv("ENV", "production")
        })

        # Configurer le provider
        provider = TracerProvider(resource=resource)

        # Configurer l'exporteur OTLP
        otlp_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)

        # Ajouter le processeur de spans
        processor = BatchSpanProcessor(otlp_exporter)
        provider.add_span_processor(processor)

        # Définir le provider global
        trace.set_tracer_provider(provider)

        logger.info("tracing_setup_success", endpoint=endpoint)
        return trace.get_tracer(__name__)

    except Exception as e:
        logger.warning("tracing_setup_failed", error=str(e), message="Continuing without tracing")
        # Configurer un provider par défaut pour éviter les erreurs
        trace.set_tracer_provider(TracerProvider())
        return trace.get_tracer(__name__)

def instrument_app(app):
    """Instrumente une application FastAPI."""
    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("fastapi_instrumented")
    except Exception as e:
        logger.error("fastapi_instrumentation_failed", error=str(e))
