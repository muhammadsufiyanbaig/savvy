from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import os
from typing import Optional
import time

app = FastAPI(
    title="Financial Management System - API Gateway",
    version="1.0.0",
    description="API Gateway for microservices"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
SERVICES = {
    "user": os.getenv("USER_SERVICE_URL", "http://user-service:8001"),
    "finance": os.getenv("FINANCE_SERVICE_URL", "http://finance-service:8002"),
    "bank": os.getenv("BANK_SERVICE_URL", "http://bank-service:8003"),
    "statement": os.getenv("STATEMENT_SERVICE_URL", "http://statement-service:8004"),
    "ai": os.getenv("AI_SERVICE_URL", "http://ai-service:8005"),
    "notification": os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8006"),
}


# Middleware for logging and monitoring
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.get("/")
async def root():
    return {
        "service": "API Gateway",
        "version": "1.0.0",
        "status": "running",
        "services": list(SERVICES.keys())
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    service_status = {}

    async with httpx.AsyncClient(timeout=5.0) as client:
        for service_name, service_url in SERVICES.items():
            try:
                response = await client.get(f"{service_url}/health")
                service_status[service_name] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time": response.elapsed.total_seconds()
                }
            except Exception as e:
                service_status[service_name] = {
                    "status": "unreachable",
                    "error": str(e)
                }

    all_healthy = all(s["status"] == "healthy" for s in service_status.values())

    return {
        "gateway": "healthy",
        "services": service_status,
        "overall_status": "healthy" if all_healthy else "degraded"
    }


async def forward_request(service: str, path: str, method: str, request: Request):
    """Forward request to appropriate microservice"""
    service_url = SERVICES.get(service)
    if not service_url:
        raise HTTPException(status_code=404, detail=f"Service '{service}' not found")

    url = f"{service_url}{path}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Get request body if present
            body = await request.body() if method in ["POST", "PUT", "PATCH"] else None

            # Forward request
            response = await client.request(
                method=method,
                url=url,
                headers=dict(request.headers),
                content=body,
                params=request.query_params
            )

            return JSONResponse(
                content=response.json() if response.text else {},
                status_code=response.status_code,
                headers=dict(response.headers)
            )

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Service timeout")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# User Service Routes
@app.api_route("/api/v1/users/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def user_service_proxy(path: str, request: Request):
    return await forward_request("user", f"/api/v1/users/{path}", request.method, request)


# Finance Service Routes
@app.api_route("/api/v1/expenses/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def expense_service_proxy(path: str, request: Request):
    return await forward_request("finance", f"/api/v1/expenses/{path}", request.method, request)


@app.api_route("/api/v1/savings/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def savings_service_proxy(path: str, request: Request):
    return await forward_request("finance", f"/api/v1/savings/{path}", request.method, request)


@app.api_route("/api/v1/budgets/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def budget_service_proxy(path: str, request: Request):
    return await forward_request("finance", f"/api/v1/budgets/{path}", request.method, request)


# Bank Service Routes
@app.api_route("/api/v1/banks/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def bank_service_proxy(path: str, request: Request):
    return await forward_request("bank", f"/api/v1/banks/{path}", request.method, request)


# Statement Analysis Service Routes
@app.api_route("/api/v1/statements/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def statement_service_proxy(path: str, request: Request):
    return await forward_request("statement", f"/api/v1/statements/{path}", request.method, request)


# AI Service Routes
@app.api_route("/api/v1/ai/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def ai_service_proxy(path: str, request: Request):
    return await forward_request("ai", f"/api/v1/ai/{path}", request.method, request)


# Notification Service Routes
@app.api_route("/api/v1/notifications/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def notification_service_proxy(path: str, request: Request):
    return await forward_request("notification", f"/api/v1/notifications/{path}", request.method, request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
