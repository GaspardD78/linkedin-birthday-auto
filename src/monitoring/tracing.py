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


class TemporaryTracing:
    """
    Context manager pour activer temporairement le tracing OpenTelemetry.

    Utile pour tracer des opérations spécifiques (comme l'authentification)
    sans avoir le tracing activé globalement.

    Usage:
        with TemporaryTracing("auth-process"):
            # Code à tracer
            authenticate_user()
    """

    def __init__(self, service_name: str = "temp-tracing", endpoint: Optional[str] = None):
        """
        Args:
            service_name: Nom du service pour ce tracing temporaire
            endpoint: Endpoint OTLP (défaut: variable d'env ou http://localhost:4317)
        """
        self.service_name = service_name
        self.endpoint = endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        self.original_provider = None
        self.temp_provider = None

    def __enter__(self):
        """Active le tracing temporairement."""
        logger.info("temporary_tracing_enabled", service=self.service_name, endpoint=self.endpoint)

        # Sauvegarder le provider actuel
        self.original_provider = trace.get_tracer_provider()

        try:
            # Créer un nouveau provider temporaire
            resource = Resource.create(attributes={
                "service.name": self.service_name,
                "deployment.environment": os.getenv("ENV", "production"),
                "temporary": "true"
            })

            self.temp_provider = TracerProvider(resource=resource)

            # Configurer l'exporteur OTLP
            otlp_exporter = OTLPSpanExporter(endpoint=self.endpoint, insecure=True)
            processor = BatchSpanProcessor(otlp_exporter)
            self.temp_provider.add_span_processor(processor)

            # Activer le provider temporaire
            trace.set_tracer_provider(self.temp_provider)

            logger.info("temporary_tracing_active", endpoint=self.endpoint)

        except Exception as e:
            logger.warning("temporary_tracing_setup_failed", error=str(e))
            # En cas d'erreur, utiliser un provider par défaut
            trace.set_tracer_provider(TracerProvider())

        return trace.get_tracer(self.service_name)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Désactive le tracing et force l'export des spans."""
        try:
            # Forcer l'export des spans en attente
            if self.temp_provider:
                # Force shutdown pour exporter tous les spans
                self.temp_provider.force_flush(timeout_millis=5000)
                self.temp_provider.shutdown()

            logger.info("temporary_tracing_disabled", service=self.service_name)

        except Exception as e:
            logger.warning("temporary_tracing_cleanup_error", error=str(e))

        finally:
            # Restaurer le provider original
            if self.original_provider:
                trace.set_tracer_provider(self.original_provider)
            else:
                # Si pas de provider original, utiliser un provider par défaut
                trace.set_tracer_provider(TracerProvider())
