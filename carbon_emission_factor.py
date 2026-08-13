import csv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

CARBON_FACTOR_PATH = (
    BASE_DIR / "carbon_emission_factors.csv"
)


def get_emission_factor(mode: str) -> float:
    """
    운송수단별 탄소배출계수를 CSV에서 조회한다.

    mode:
        road = 도로 화물
        rail = 철도 화물
    """

    if not CARBON_FACTOR_PATH.exists():
        raise FileNotFoundError(
            f"탄소배출계수 CSV를 찾을 수 없습니다.\n"
            f"확인 경로: {CARBON_FACTOR_PATH}"
        )

    with CARBON_FACTOR_PATH.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:

        reader = csv.DictReader(csv_file)

        for row in reader:

            if row["mode"].strip().lower() == mode.lower():

                return float(
                    row[
                        "emission_factor_gco2e_per_ton_km"
                    ]
                )

    raise ValueError(
        f"'{mode}' 운송수단의 탄소배출계수를 "
        f"찾을 수 없습니다."
    )


def calculate_emission(
    distance_km: float,
    weight_ton: float,
    mode: str,
) -> float:
    """
    탄소배출량을 kgCO2e 단위로 계산한다.

    배출량 =
    거리(km)
    × 화물중량(ton)
    × 배출계수(gCO2e/ton-km)
    ÷ 1000
    """

    if distance_km < 0:
        raise ValueError(
            "운송거리는 0 이상이어야 합니다."
        )

    if weight_ton <= 0:
        raise ValueError(
            "화물중량은 0보다 커야 합니다."
        )

    emission_factor = get_emission_factor(
        mode
    )

    emission_kg = (
        distance_km
        * weight_ton
        * emission_factor
        / 1000
    )

    return emission_kg


def compare_carbon_emissions(
    road_only_distance_km: float,
    first_mile_distance_km: float,
    rail_distance_km: float,
    last_mile_distance_km: float,
    weight_ton: float,
) -> dict:
    """
    도로 100%와 철도 복합운송의
    탄소배출량을 비교한다.
    """

    # -----------------------------------------
    # 도로 100%
    # -----------------------------------------

    road_only_emission = calculate_emission(
        distance_km=road_only_distance_km,
        weight_ton=weight_ton,
        mode="road",
    )

    # -----------------------------------------
    # 복합운송 - First Mile
    # -----------------------------------------

    first_mile_emission = calculate_emission(
        distance_km=first_mile_distance_km,
        weight_ton=weight_ton,
        mode="road",
    )

    # -----------------------------------------
    # 복합운송 - Rail
    # -----------------------------------------

    rail_emission = calculate_emission(
        distance_km=rail_distance_km,
        weight_ton=weight_ton,
        mode="rail",
    )

    # -----------------------------------------
    # 복합운송 - Last Mile
    # -----------------------------------------

    last_mile_emission = calculate_emission(
        distance_km=last_mile_distance_km,
        weight_ton=weight_ton,
        mode="road",
    )

    # 복합운송 총배출량
    multimodal_emission = (
        first_mile_emission
        + rail_emission
        + last_mile_emission
    )

    # 탄소 절감량
    reduction_kg = (
        road_only_emission
        - multimodal_emission
    )

    # 탄소 절감률
    if road_only_emission > 0:

        reduction_rate = (
            reduction_kg
            / road_only_emission
            * 100
        )

    else:
        reduction_rate = 0

    return {
        "road_only_emission_kg": round(
            road_only_emission,
            2,
        ),

        "first_mile_emission_kg": round(
            first_mile_emission,
            2,
        ),

        "rail_emission_kg": round(
            rail_emission,
            2,
        ),

        "last_mile_emission_kg": round(
            last_mile_emission,
            2,
        ),

        "multimodal_emission_kg": round(
            multimodal_emission,
            2,
        ),

        "carbon_reduction_kg": round(
            reduction_kg,
            2,
        ),

        "carbon_reduction_rate": round(
            reduction_rate,
            1,
        ),
    }