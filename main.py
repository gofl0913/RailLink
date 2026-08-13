from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from transport_service import analyze_transport


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


class TransportRequest(BaseModel):
    origin: str
    destination: str
    cargo_weight_ton: float
    shipping_date: str
    priority: str


@app.get("/")
def root():
    return {
        "message": "Transport API server is running"
    }


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
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error