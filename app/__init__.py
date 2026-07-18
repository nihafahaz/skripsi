"""
Inisialisasi aplikasi FastAPI.

Factory function `create_app()` membangun instance FastAPI
dengan semua konfigurasi, middleware, event handler, dan router.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.router import router
from app.core.config import get_settings
from app.core.exceptions import AppException, get_http_status
from app.core.logger import get_logger, setup_logging
from app.ml.inference.model_loader import get_model_loader

logger = get_logger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """
    Lifecycle manager aplikasi FastAPI.

    Dipanggil saat startup dan shutdown.
    - Startup: Setup logging, muat model LSTM (singleton).
    - Shutdown: Cleanup resources (jika diperlukan).
    """
    # --- STARTUP ---
    setup_logging()
    logger.info("Aplikasi backend prediksi harga cabai sedang diinisialisasi...")

    try:
        model_loader = get_model_loader()
        model_loader.load()
        logger.info("Model LSTM berhasil dimuat.")
    except Exception as exc:
        # Aplikasi tetap berjalan meski model gagal dimuat
        # (endpoint lain seperti /harga dan /toko_online masih bisa melayani)
        logger.warning(
            "Model LSTM gagal dimuat saat startup: %s. "
            "Endpoint /predict dan /download tidak akan tersedia.",
            exc,
        )

    logger.info("Aplikasi siap melayani request.")
    yield

    # --- SHUTDOWN ---
    logger.info("Aplikasi sedang shutdown...")


def create_app() -> FastAPI:
    """
    Buat dan kembalikan instance aplikasi FastAPI.

    Returns:
        FastAPI: Instance aplikasi yang sudah dikonfigurasi.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_title,
        version=settings.app_version,
        description=(
            "API Backend Prediksi Harga Cabai menggunakan model LSTM Global. "
            "Mendukung 34 provinsi dan 4 jenis komoditas cabai."
        ),
        lifespan=_lifespan,
    )

    # --- Global Exception Handler ---
    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request, exc: AppException
    ) -> JSONResponse:
        """Tangkap semua custom AppException dan kembalikan sebagai HTTP response."""
        status_code = get_http_status(exc)
        logger.warning(
            "[%s %s] %s: %s",
            request.method,
            request.url.path,
            type(exc).__name__,
            exc.message,
        )
        return JSONResponse(
            status_code=status_code,
            content={
                "status": "error",
                "message": exc.message,
                "detail": exc.detail,
            },
        )

    # --- Mount Router ---
    app.include_router(router)

    return app
