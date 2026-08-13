import csv
import math
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

MARKET_FARE_PATH = (
    BASE_DIR / "cargo_freight_rates_2022_2025.csv"
)

KM_COST_PATH = (
    BASE_DIR / "truck_cost_per_km_2025.csv"
)


# =================================================
# 톤급 구간
# =================================================

def get_weight_class(weight_ton: float) -> str:

    if weight_ton <= 1:
        return "1톤 이하"

    elif weight_ton < 3:
        return "1톤 초과~3톤 미만"

    elif weight_ton < 5:
        return "3톤 이상~5톤 미만"

    elif weight_ton < 8:
        return "5톤 이상~8톤 미만"

    elif weight_ton < 12:
        return "8톤 이상~12톤 미만"

    else:
        return "12톤 이상"


# =================================================
# 대표 차량 톤급
# =================================================

def get_reference_vehicle_ton(
    weight_ton: float,
) -> int:

    if weight_ton <= 1:
        return 1

    elif weight_ton < 5:
        return 5

    elif weight_ton < 12:
        return 12

    else:
        return 25


# =================================================
# 필요 차량 수 계산
# =================================================

def get_required_vehicle_count(
    weight_ton: float,
) -> tuple:

    if weight_ton <= 0:
        raise ValueError(
            "화물 중량은 0보다 커야 합니다."
        )

    # 25톤을 초과하는 대량 화물은
    # 25톤 차량 여러 대로 운송한다고 가정
    if weight_ton > 25:

        vehicle_ton = 25

        vehicle_count = math.ceil(
            weight_ton / vehicle_ton
        )

    else:

        vehicle_ton = (
            get_reference_vehicle_ton(
                weight_ton
            )
        )

        vehicle_count = 1

    return (
        vehicle_ton,
        vehicle_count,
    )


# =================================================
# 숫자 변환
# =================================================

def to_number(value):

    try:

        text = (
            str(value)
            .replace(",", "")
            .strip()
        )

        if text in (
            "",
            "-",
            "N/A",
        ):
            return None

        return float(text)

    except (
        TypeError,
        ValueError,
    ):
        return None


# =================================================
# 시장 기본운임
# =================================================

def get_market_base_fare(
    weight_ton: float,
    region_type: str = "default",
) -> float:

    weight_class = get_weight_class(
        weight_ton
    )

    fares = {}

    with MARKET_FARE_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            if row["톤급"] != weight_class:
                continue

            if row["연도"] != "2025 2분기":
                continue

            route = row["구간"]

            if route not in (
                "수도권내",
                "부산권내",
            ):
                continue

            fare = to_number(
                row["대당_편도운임_원"]
            )

            if fare is not None:
                fares[route] = fare

    if region_type == "capital":

        if "수도권내" in fares:
            return fares["수도권내"]

    if region_type == "busan":

        if "부산권내" in fares:
            return fares["부산권내"]

    valid_fares = list(
        fares.values()
    )

    if not valid_fares:

        raise ValueError(
            f"{weight_class}의 단거리 시장운임을 "
            f"찾을 수 없습니다."
        )

    return (
        sum(valid_fares)
        / len(valid_fares)
    )


# =================================================
# km당 원가
# =================================================

def get_cost_per_km(
    weight_ton: float,
) -> float:

    vehicle_ton = (
        get_reference_vehicle_ton(
            weight_ton
        )
    )

    with KM_COST_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            if (
                int(row["vehicle_ton"])
                == vehicle_ton
            ):

                return float(
                    row[
                        "cost_per_km_won"
                    ]
                )

    raise ValueError(
        f"{vehicle_ton}톤 차량의 "
        "km당 원가를 찾을 수 없습니다."
    )


# =================================================
# 도로 화물 운송비
# =================================================

def estimate_truck_fare(
    distance_km: float,
    weight_ton: float,
    toll_won: float = 0,
    region_type: str = "default",
) -> dict:

    if distance_km < 0:

        raise ValueError(
            "거리는 0 이상이어야 합니다."
        )

    if weight_ton <= 0:

        raise ValueError(
            "화물 중량은 0보다 커야 합니다."
        )

    # =================================================
    # 1. 필요 차량 대수
    # =================================================

    (
        vehicle_ton,
        vehicle_count,
    ) = get_required_vehicle_count(
        weight_ton
    )

    # =================================================
    # 2. 차량 1대 기준 비용 계산
    # =================================================

    base_fare_per_vehicle = (
        get_market_base_fare(
            vehicle_ton,
            region_type,
        )
    )

    cost_per_km = (
        get_cost_per_km(
            vehicle_ton
        )
    )

    BASE_DISTANCE_KM = 50

    if distance_km <= BASE_DISTANCE_KM:

        freight_fare_per_vehicle = (
            base_fare_per_vehicle
        )

    else:

        extra_distance = (
            distance_km
            - BASE_DISTANCE_KM
        )

        freight_fare_per_vehicle = (
            base_fare_per_vehicle
            +
            extra_distance
            * cost_per_km
        )

    # =================================================
    # 3. 전체 차량 비용
    # =================================================

    total_freight_fare = (
        freight_fare_per_vehicle
        * vehicle_count
    )

    # TMAP 통행료도 차량 1대 기준으로 보고
    # 필요한 차량 수만큼 적용
    total_toll = (
        toll_won
        * vehicle_count
    )

    total_cost = (
        total_freight_fare
        + total_toll
    )

    # =================================================
    # 4. 결과
    # =================================================

    return {
        "cargo_weight_ton":
            weight_ton,

        "weight_class":
            get_weight_class(
                vehicle_ton
            ),

        "reference_vehicle_ton":
            vehicle_ton,

        "vehicle_count":
            vehicle_count,

        "distance_km":
            round(
                distance_km,
                1,
            ),

        "base_fare_per_vehicle_won":
            round(
                base_fare_per_vehicle
            ),

        "cost_per_km_won":
            round(
                cost_per_km
            ),

        "freight_fare_per_vehicle_won":
            round(
                freight_fare_per_vehicle
            ),

        "estimated_freight_fare_won":
            round(
                total_freight_fare
            ),

        "toll_per_vehicle_won":
            round(
                toll_won
            ),

        "toll_won":
            round(
                total_toll
            ),

        "total_road_cost_won":
            round(
                total_cost
            ),
    }