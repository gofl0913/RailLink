import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from transport_service import analyze_transport


# =================================================
# 로그 설정
# =================================================

logging.basicConfig(
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =================================================
# FastAPI 앱 설정
# =================================================

app = FastAPI(
    title="철도·도로 복합운송 API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =================================================
# 요청 데이터 모델
# =================================================

class TransportRequest(BaseModel):
    origin: str
    destination: str
    cargo_weight_ton: float
    shipping_date: str
    priority: str


# =================================================
# 서버 상태 확인
# =================================================

@app.get("/")
def root():
    return {
        "message": "Transport API server is running"
    }


# =================================================
# 복합운송 분석 API
# =================================================

@app.post("/transport-analysis")
def transport_analysis(
    request: TransportRequest,
):
    try:
        result = analyze_transport(
            origin_keyword=request.origin,
            destination_keyword=request.destination,
            cargo_weight_ton=request.cargo_weight_ton,
            shipping_date=request.shipping_date,
            priority=request.priority,
        )

        return result

    except ValueError as error:
        logger.exception(
            "transport-analysis ValueError: %s",
            error,
        )

        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except FileNotFoundError as error:
        logger.exception(
            "필수 데이터 파일 오류: %s",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error

    except RuntimeError as error:
        logger.exception(
            "외부 API 또는 분석 실행 오류: %s",
            error,
        )

        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error

    except Exception as error:
        logger.exception(
            "예상하지 못한 서버 오류: %s",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error