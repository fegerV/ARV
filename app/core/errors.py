from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from starlette import status
import structlog

logger = structlog.get_logger()


class APIErrorResponse(BaseModel):
    detail: str
    code: str | None = None
    meta: dict | None = None


class AppException(HTTPException):
    def __init__(self, status_code: int, detail: str, code: str | None = None, meta: dict | None = None):
        super().__init__(status_code=status_code, detail=detail)
        self.code = code
        self.meta = meta or {}


def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        # Get request context
        context_vars = structlog.contextvars.get_contextvars()
        request_id = context_vars.get('request_id')
        user_id = context_vars.get('user_id')
        company_id = context_vars.get('company_id')
        
        logger.warning(
            "AppException",
            request_id=request_id,
            user_id=user_id,
            company_id=company_id,
            path=str(request.url.path),
            code=exc.code,
            meta=exc.meta,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=APIErrorResponse(detail=exc.detail, code=exc.code, meta=exc.meta).model_dump(),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        # Get request context
        context_vars = structlog.contextvars.get_contextvars()
        request_id = context_vars.get('request_id')
        user_id = context_vars.get('user_id')
        company_id = context_vars.get('company_id')
        
        logger.warning(
            "HTTP error",
            request_id=request_id,
            user_id=user_id,
            company_id=company_id,
            path=str(request.url.path),
            status=exc.status_code,
            detail=exc.detail,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=APIErrorResponse(detail=exc.detail, code="HTTP_ERROR").model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # Get request context
        context_vars = structlog.contextvars.get_contextvars()
        request_id = context_vars.get('request_id')
        user_id = context_vars.get('user_id')
        company_id = context_vars.get('company_id')
        
        logger.info(
            "Validation error",
            request_id=request_id,
            user_id=user_id,
            company_id=company_id,
            path=str(request.url.path),
            errors=exc.errors(),
        )
        
        # Format field errors for frontend
        field_errors = {}
        for error in exc.errors():
            field = '.'.join(str(loc) for loc in error['loc'] if loc != 'body')
            if field:
                field_errors[field] = error['msg']
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=APIErrorResponse(
                detail="Ошибка валидации данных",
                code="VALIDATION_ERROR",
                meta={"fields": field_errors} if field_errors else {"errors": exc.errors()}
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        # Get request context
        context_vars = structlog.contextvars.get_contextvars()
        request_id = context_vars.get('request_id')
        user_id = context_vars.get('user_id')
        company_id = context_vars.get('company_id')
        
        logger.exception(
            "Unhandled exception",
            request_id=request_id,
            user_id=user_id,
            company_id=company_id,
            path=str(request.url.path),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=APIErrorResponse(
                detail="Внутренняя ошибка сервера",
                code="INTERNAL_ERROR",
                meta={"path": str(request.url.path)}
            ).model_dump(),
        )