"""
Configuration du tracing distribué avec OpenTelemetry.
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

def setup_tracing(service_name: str = "linkedin-bot", endpoint: str = "http://localhost:4317") -> Optional[trace.Tracer]:
    """
    Configure OpenTelemetry pour l'application.

    Args:
        service_name: Nom du service
        endpoint: Endpoint OTLP (gRPC)

    Returns:
        Tracer ou None si désactivé
    """
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
        logger.error("tracing_setup_failed", error=str(e))
        return None

def instrument_app(app):
    """Instrumente une application FastAPI."""
    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("fastapi_instrumented")
    except Exception as e:
        logger.error("fastapi_instrumentation_failed", error=str(e))
