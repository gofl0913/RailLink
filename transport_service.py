import csv
from pathlib import Path

from tmap_service import search_place, get_route
from station_selector_service import select_best_freight_stations
from truck_cost_service import estimate_truck_fare
from schedule_service import check_train_schedule
from carbon_emission_factor import compare_carbon_emissions
from recommendation_service import calculate_recommendation
from ai_explain_service import generate_ai_explanation


# =================================================
# 철도 CSV 경로
# =================================================

BASE_DIR = Path(__file__).resolve().parent

CSV_PATH = (
    BASE_DIR
    / "rail_route_summary_complete.csv"
)


# =================================================
# 역명 정규화
# =================================================

def normalize_station_name(name: str) -> str:
    normalized = str(name).strip()

    normalized = normalized.replace(
        "[기차역]",
        "",
    )

    normalized = normalized.replace(
        "[철도역]",
        "",
    )

    if normalized.endswith("역"):
        normalized = normalized[:-1]

    return normalized.strip()


# =================================================
# 숫자 변환
# =================================================

def to_float(
    value,
    default=0.0,
) -> float:

    try:
        text = (
            str(value)
            .replace(",", "")
            .strip()
        )

        if not text:
            return default

        return float(text)

    except (
        TypeError,
        ValueError,
    ):
        return default


# =================================================
# 철도 노선 조회
# =================================================

def get_rail_route(
    origin_station: str,
    destination_station: str,
) -> dict:

    if not CSV_PATH.exists():
        raise FileNotFoundError(
            "철도 CSV 파일을 찾을 수 없습니다.\n"
            f"확인 경로: {CSV_PATH}"
        )

    normalized_origin = normalize_station_name(
        origin_station
    )

    normalized_destination = normalize_station_name(
        destination_station
    )

    with CSV_PATH.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:

        reader = csv.DictReader(csv_file)

        for row in reader:

            csv_origin = normalize_station_name(
                row["origin_station"]
            )

            csv_destination = normalize_station_name(
                row["destination_station"]
            )

            if (
                csv_origin == normalized_origin
                and
                csv_destination == normalized_destination
            ):

                return {
                    "origin_station":
                        row["origin_station"],

                    "destination_station":
                        row["destination_station"],

                    "distance_km":
                        to_float(
                            row["distance_km"]
                        ),

                    "duration_min":
                        to_float(
                            row["avg_duration_min"]
                        ),

                    "fare_per_ton_won":
                        to_float(
                            row[
                                "weighted_avg_fare_per_ton_won"
                            ]
                        ),

                    "operation_days":
                        row["operation_days"],

                    "train_numbers":
                        row["train_numbers"],

                    "main_lines":
                        row["main_lines"],

                    "cargo_types":
                        row[
                            "performance_cargo_types"
                        ],

                    "performance_record_count":
                        int(
                            to_float(
                                row[
                                    "performance_record_count"
                                ]
                            )
                        ),
                }

    raise ValueError(
        "철도 데이터에서 "
        f"'{normalized_origin} → "
        f"{normalized_destination}' "
        "노선을 찾을 수 없습니다."
    )


# =================================================
# 사용자 우선순위 → 가중치
# =================================================

def get_priority_weights(
    priority: str,
) -> tuple:

    if priority == "1":
        # 비용 우선
        return (
            0.60,
            0.25,
            0.15,
        )

    elif priority == "2":
        # 시간 우선
        return (
            0.20,
            0.65,
            0.15,
        )

    elif priority == "3":
        # 친환경 우선
        return (
            0.20,
            0.15,
            0.65,
        )

    elif priority == "4":
        # 균형형
        return (
            0.34,
            0.33,
            0.33,
        )

    else:
        raise ValueError(
            "운송안 선택 기준을 선택해주세요."
        )


# =================================================
# 전체 운송 분석
# =================================================

def analyze_transport(
    origin_keyword: str,
    destination_keyword: str,
    cargo_weight_ton: float,
    shipping_date: str,
    priority: str,
):

    # =================================================
    # 1. 기본 입력 검증
    # =================================================

    if cargo_weight_ton <= 0:
        raise ValueError(
            "화물 중량은 0보다 커야 합니다."
        )

    # =================================================
    # 2. 사용자 우선순위 가중치
    # =================================================

    (
        cost_weight,
        time_weight,
        carbon_weight,
    ) = get_priority_weights(
        priority
    )

    # =================================================
    # 3. TMAP 장소 검색
    # =================================================

    origin = search_place(
        origin_keyword
    )

    destination = search_place(
        destination_keyword
    )

    print(
        "출발지 검색 결과:",
        origin
    )

    print(
        "목적지 검색 결과:",
        destination
    )

    # =================================================
    # 4. 출발/도착 화물역 자동 선택
    # =================================================

    station_selection = (
        select_best_freight_stations(
            origin=origin,
            destination=destination,
            top_n=5,
        )
    )

    departure_station = (
        station_selection[
            "departure_station"
        ]
    )

    arrival_station = (
        station_selection[
            "arrival_station"
        ]
    )

    print(
        "출발 화물역:",
        departure_station
    )

    print(
        "도착 화물역:",
        arrival_station
    )

    # =================================================
    # 5. 도로 100% 경로
    # =================================================

    road_only = get_route(
        origin,
        destination,
    )

    # =================================================
    # 6. First Mile / Last Mile
    # =================================================

    first_mile = (
        station_selection[
            "first_mile"
        ]
    )

    last_mile = (
        station_selection[
            "last_mile"
        ]
    )

    print(
        "\n===== 도로 경로 확인 ====="
    )

    print(
        "도로 100%:",
        road_only["distance_km"],
        "km /",
        road_only["duration_min"],
        "분",
    )

    print(
        "First Mile:",
        first_mile["distance_km"],
        "km /",
        first_mile["duration_min"],
        "분",
    )

    print(
        "Last Mile:",
        last_mile["distance_km"],
        "km /",
        last_mile["duration_min"],
        "분",
    )

    # =================================================
    # 7. 철도 구간 조회
    # =================================================

    rail_section = get_rail_route(
        departure_station,
        arrival_station,
    )

    # =================================================
    # 8. 철도 데이터 검증
    # =================================================

    if rail_section["distance_km"] <= 0:
        raise ValueError(
            "선택된 철도 노선의 "
            "distance_km 값이 없습니다."
        )

    if rail_section["duration_min"] <= 0:
        raise ValueError(
            "선택된 철도 노선의 "
            "avg_duration_min 값이 없습니다."
        )

    if rail_section["fare_per_ton_won"] <= 0:
        raise ValueError(
            "선택된 철도 노선의 "
            "톤당 평균운임 데이터가 없습니다."
        )

    print(
        "\n===== 철도 구간 확인 ====="
    )

    print(
        "철도:",
        rail_section["origin_station"],
        "→",
        rail_section["destination_station"],
    )

    print(
        "거리:",
        rail_section["distance_km"],
        "km",
    )

    print(
        "시간:",
        rail_section["duration_min"],
        "분",
    )

    print(
        "톤당 평균 운임:",
        rail_section["fare_per_ton_won"],
        "원/톤",
    )

    # =================================================
    # 9. 철도 운행 가능 여부
    # =================================================

    schedule_result = check_train_schedule(
        shipping_date=shipping_date,
        operation_days=rail_section[
            "operation_days"
        ],
    )

    print(
        "\n===== 철도 운행 가능 여부 ====="
    )

    print(
        "운송 희망일:",
        schedule_result["shipping_date"],
        schedule_result["shipping_weekday"],
    )

    print(
        "운행 가능 여부:",
        schedule_result[
            "available_today"
        ],
    )

    if not schedule_result[
        "available_today"
    ]:

        print(
            "다음 운행 가능일:",
            schedule_result[
                "next_available_date"
            ],
        )

    # =================================================
    # 10. 도로 100% 운송비
    # =================================================

    road_only_cost = estimate_truck_fare(
        distance_km=road_only[
            "distance_km"
        ],
        weight_ton=cargo_weight_ton,
        toll_won=road_only[
            "toll_won"
        ],
        region_type="capital",
    )

    # =================================================
    # 11. First Mile 운송비
    # =================================================

    first_mile_cost = estimate_truck_fare(
        distance_km=first_mile[
            "distance_km"
        ],
        weight_ton=cargo_weight_ton,
        toll_won=first_mile[
            "toll_won"
        ],
        region_type="capital",
    )

    # =================================================
    # 12. Last Mile 운송비
    # =================================================

    last_mile_cost = estimate_truck_fare(
        distance_km=last_mile[
            "distance_km"
        ],
        weight_ton=cargo_weight_ton,
        toll_won=last_mile[
            "toll_won"
        ],
        region_type="default",
    )

    # =================================================
    # 13. 철도 운임
    # =================================================

    rail_fare_won = round(
        rail_section[
            "fare_per_ton_won"
        ]
        * cargo_weight_ton
    )

    # =================================================
    # 14. 비용 계산
    # =================================================

    road_only_total_cost = (
        road_only_cost[
            "total_road_cost_won"
        ]
    )

    multimodal_total_cost = (
        first_mile_cost[
            "total_road_cost_won"
        ]
        +
        rail_fare_won
        +
        last_mile_cost[
            "total_road_cost_won"
        ]
    )

    cost_difference = (
        multimodal_total_cost
        -
        road_only_total_cost
    )

    if road_only_total_cost > 0:

        cost_change_rate = (
            cost_difference
            /
            road_only_total_cost
            * 100
        )

    else:

        cost_change_rate = 0

    # =================================================
    # 15. 복합운송 거리 계산
    # =================================================

    multimodal_road_distance = (
        first_mile[
            "distance_km"
        ]
        +
        last_mile[
            "distance_km"
        ]
    )

    multimodal_total_distance = (
        multimodal_road_distance
        +
        rail_section[
            "distance_km"
        ]
    )

    if multimodal_total_distance > 0:

        road_ratio = (
            multimodal_road_distance
            /
            multimodal_total_distance
            * 100
        )

        rail_ratio = (
            rail_section[
                "distance_km"
            ]
            /
            multimodal_total_distance
            * 100
        )

    else:

        road_ratio = 0
        rail_ratio = 0

    # =================================================
    # 16. 시간 계산
    # =================================================

    road_only_time = (
        road_only[
            "duration_min"
        ]
    )

    multimodal_total_time = (
        first_mile[
            "duration_min"
        ]
        +
        rail_section[
            "duration_min"
        ]
        +
        last_mile[
            "duration_min"
        ]
    )

    time_difference = (
        multimodal_total_time
        -
        road_only_time
    )

    if road_only_time > 0:

        time_change_rate = (
            time_difference
            /
            road_only_time
            * 100
        )

    else:

        time_change_rate = 0

    # =================================================
    # 17. 탄소배출량 계산
    # =================================================

    carbon_result = compare_carbon_emissions(
        road_only_distance_km=(
            road_only[
                "distance_km"
            ]
        ),

        first_mile_distance_km=(
            first_mile[
                "distance_km"
            ]
        ),

        rail_distance_km=(
            rail_section[
                "distance_km"
            ]
        ),

        last_mile_distance_km=(
            last_mile[
                "distance_km"
            ]
        ),

        weight_ton=(
            cargo_weight_ton
        ),
    )

    # =================================================
    # 18. 최종 추천
    # =================================================

    if schedule_result[
        "available_today"
    ]:

        recommendation_result = (
            calculate_recommendation(
                road_cost=(
                    road_only_total_cost
                ),

                road_time=(
                    road_only_time
                ),

                road_carbon=(
                    carbon_result[
                        "road_only_emission_kg"
                    ]
                ),

                multimodal_cost=(
                    multimodal_total_cost
                ),

                multimodal_time=(
                    multimodal_total_time
                ),

                multimodal_carbon=(
                    carbon_result[
                        "multimodal_emission_kg"
                    ]
                ),

                cost_weight=(
                    cost_weight
                ),

                time_weight=(
                    time_weight
                ),

                carbon_weight=(
                    carbon_weight
                ),
            )
        )

    else:

        recommendation_result = {
            "recommended_mode":
                "road",

            "recommended_name":
                "도로 100% 운송",

            "reason":
                "희망 운송일에 철도 운행 불가",
        }

    # =================================================
    # 19. Gemini 생성형 AI 설명
    # =================================================

    ai_explanation = None
    ai_explanation_error = None

    try:

        if schedule_result[
            "available_today"
        ]:

            ai_explanation = (
                generate_ai_explanation(
                    recommended_name=(
                        recommendation_result[
                            "recommended_name"
                        ]
                    ),

                    road_cost=(
                        road_only_total_cost
                    ),

                    road_time=(
                        road_only_time
                    ),

                    road_carbon=(
                        carbon_result[
                            "road_only_emission_kg"
                        ]
                    ),

                    multimodal_cost=(
                        multimodal_total_cost
                    ),

                    multimodal_time=(
                        multimodal_total_time
                    ),

                    multimodal_carbon=(
                        carbon_result[
                            "multimodal_emission_kg"
                        ]
                    ),

                    cost_weight=(
                        cost_weight
                    ),

                    time_weight=(
                        time_weight
                    ),

                    carbon_weight=(
                        carbon_weight
                    ),

                    road_score=(
                        recommendation_result[
                            "road_score"
                        ]
                    ),

                    multimodal_score=(
                        recommendation_result[
                            "multimodal_score"
                        ]
                    ),

                    carbon_reduction_rate=(
                        carbon_result[
                            "carbon_reduction_rate"
                        ]
                    ),

                    rail_available=True,

                    shipping_date=(
                        schedule_result[
                            "shipping_date"
                        ]
                    ),
                )
            )

        else:

            ai_explanation = (
                generate_ai_explanation(
                    recommended_name=(
                        recommendation_result[
                            "recommended_name"
                        ]
                    ),

                    road_cost=(
                        road_only_total_cost
                    ),

                    road_time=(
                        road_only_time
                    ),

                    road_carbon=(
                        carbon_result[
                            "road_only_emission_kg"
                        ]
                    ),

                    multimodal_cost=(
                        multimodal_total_cost
                    ),

                    multimodal_time=(
                        multimodal_total_time
                    ),

                    multimodal_carbon=(
                        carbon_result[
                            "multimodal_emission_kg"
                        ]
                    ),

                    cost_weight=(
                        cost_weight
                    ),

                    time_weight=(
                        time_weight
                    ),

                    carbon_weight=(
                        carbon_weight
                    ),

                    carbon_reduction_rate=(
                        carbon_result[
                            "carbon_reduction_rate"
                        ]
                    ),

                    rail_available=False,

                    shipping_date=(
                        schedule_result[
                            "shipping_date"
                        ]
                    ),

                    next_available_date=(
                        schedule_result[
                            "next_available_date"
                        ]
                        or ""
                    ),
                )
            )

    except Exception as error:

        ai_explanation_error = str(
            error
        )

        ai_explanation = (
            "현재 생성형 AI 설명을 "
            "불러오지 못했습니다."
        )

        print(
            "※ Gemini 설명 생성에 실패했지만 "
            "기존 운송 분석은 계속 진행합니다."
        )

    # =================================================
    # 20. 주요 결과 출력
    # =================================================

    print(
        "\n===== 비용 비교 ====="
    )

    print(
        "도로 100% 총비용:",
        road_only_total_cost,
        "원"
    )

    print(
        "복합운송 총비용:",
        multimodal_total_cost,
        "원"
    )

    print(
        "비용 변화율:",
        round(
            cost_change_rate,
            2
        ),
        "%"
    )

    print(
        "\n===== 거리 / 시간 비교 ====="
    )

    print(
        "도로 100% 거리:",
        road_only[
            "distance_km"
        ],
        "km"
    )

    print(
        "복합운송 전체 거리:",
        multimodal_total_distance,
        "km"
    )

    print(
        "도로 비율:",
        round(
            road_ratio,
            1
        ),
        "%"
    )

    print(
        "철도 비율:",
        round(
            rail_ratio,
            1
        ),
        "%"
    )

    print(
        "도로 100% 시간:",
        road_only_time,
        "분"
    )

    print(
        "복합운송 전체 시간:",
        multimodal_total_time,
        "분"
    )

    print(
        "시간 변화율:",
        round(
            time_change_rate,
            1
        ),
        "%"
    )

    print(
        "\n===== 탄소배출량 비교 ====="
    )

    print(
        "도로 100% 탄소:",
        round(
            carbon_result[
                "road_only_emission_kg"
            ],
            2
        ),
        "kgCO2e"
    )

    print(
        "복합운송 총 탄소:",
        round(
            carbon_result[
                "multimodal_emission_kg"
            ],
            2
        ),
        "kgCO2e"
    )

    print(
        "탄소 절감량:",
        round(
            carbon_result[
                "carbon_reduction_kg"
            ],
            2
        ),
        "kgCO2e"
    )

    print(
        "탄소 절감률:",
        round(
            carbon_result[
                "carbon_reduction_rate"
            ],
            1
        ),
        "%"
    )

    print(
        "\n===== 사용자 우선순위 ====="
    )

    print(
        "비용:",
        round(
            cost_weight * 100
        ),
        "%"
    )

    print(
        "시간:",
        round(
            time_weight * 100
        ),
        "%"
    )

    print(
        "친환경:",
        round(
            carbon_weight * 100
        ),
        "%"
    )

    print(
        "\n===== 최종 추천 결과 ====="
    )

    print(
        "추천 운송안:",
        recommendation_result[
            "recommended_name"
        ]
    )

    if schedule_result[
        "available_today"
    ]:

        print(
            "도로 종합점수:",
            recommendation_result[
                "road_score"
            ]
        )

        print(
            "복합운송 종합점수:",
            recommendation_result[
                "multimodal_score"
            ]
        )

    else:

        print(
            "추천 사유:",
            recommendation_result[
                "reason"
            ]
        )

    print(
        "\n===== 생성형 AI 추천 설명 ====="
    )

    print(
        ai_explanation
    )

    # =================================================
    # 21. 최종 결과 반환
    # =================================================

    return {
        "origin":
            origin,

        "destination":
            destination,

        "departure_station":
            departure_station,

        "arrival_station":
            arrival_station,

        "cargo_weight_ton":
            cargo_weight_ton,

        "shipping_date":
            shipping_date,

        "priority":
            priority,

        # -----------------------------
        # 사용자 우선순위
        # -----------------------------

        "weights": {
            "cost":
                cost_weight,

            "time":
                time_weight,

            "carbon":
                carbon_weight,
        },

        # -----------------------------
        # 각 운송 구간
        # -----------------------------

        "road_only":
            road_only,

        "first_mile":
            first_mile,

        "rail":
            rail_section,

        "last_mile":
            last_mile,

        # -----------------------------
        # 철도 운행 여부
        # -----------------------------

        "schedule":
            schedule_result,

        # -----------------------------
        # 비용
        # -----------------------------

        "cost": {
            "road_only": {
                "estimated_freight_fare_won":
                    road_only_cost[
                        "estimated_freight_fare_won"
                    ],

                "toll_won":
                    road_only_cost[
                        "toll_won"
                    ],

                "total_cost_won":
                    road_only_total_cost,

                "weight_class":
                    road_only_cost[
                        "weight_class"
                    ],
            },

            "first_mile": {
                "estimated_freight_fare_won":
                    first_mile_cost[
                        "estimated_freight_fare_won"
                    ],

                "toll_won":
                    first_mile_cost[
                        "toll_won"
                    ],

                "total_cost_won":
                    first_mile_cost[
                        "total_road_cost_won"
                    ],
            },

            "rail": {
                "fare_per_ton_won":
                    rail_section[
                        "fare_per_ton_won"
                    ],

                "total_cost_won":
                    rail_fare_won,
            },

            "last_mile": {
                "estimated_freight_fare_won":
                    last_mile_cost[
                        "estimated_freight_fare_won"
                    ],

                "toll_won":
                    last_mile_cost[
                        "toll_won"
                    ],

                "total_cost_won":
                    last_mile_cost[
                        "total_road_cost_won"
                    ],
            },

            "multimodal_total_cost_won":
                multimodal_total_cost,

            "cost_difference_won":
                cost_difference,

            "cost_change_rate":
                cost_change_rate,
        },

        # -----------------------------
        # 거리
        # -----------------------------

        "distance": {
            "road_only_distance_km":
                road_only[
                    "distance_km"
                ],

            "multimodal_total_distance_km":
                multimodal_total_distance,

            "multimodal_road_distance_km":
                multimodal_road_distance,

            "rail_distance_km":
                rail_section[
                    "distance_km"
                ],

            "road_ratio":
                road_ratio,

            "rail_ratio":
                rail_ratio,
        },

        # -----------------------------
        # 시간
        # -----------------------------

        "time": {
            "road_only_time_min":
                road_only_time,

            "multimodal_total_time_min":
                multimodal_total_time,

            "time_difference_min":
                time_difference,

            "time_change_rate":
                time_change_rate,
        },

        # -----------------------------
        # 탄소
        # -----------------------------

        "carbon": {
            "road_only_emission_kg":
                carbon_result[
                    "road_only_emission_kg"
                ],

            "first_mile_emission_kg":
                carbon_result[
                    "first_mile_emission_kg"
                ],

            "rail_emission_kg":
                carbon_result[
                    "rail_emission_kg"
                ],

            "last_mile_emission_kg":
                carbon_result[
                    "last_mile_emission_kg"
                ],

            "multimodal_emission_kg":
                carbon_result[
                    "multimodal_emission_kg"
                ],

            "carbon_reduction_kg":
                carbon_result[
                    "carbon_reduction_kg"
                ],

            "carbon_reduction_rate":
                carbon_result[
                    "carbon_reduction_rate"
                ],
        },

        # -----------------------------
        # 최종 추천
        # -----------------------------

        "recommendation":
            recommendation_result,

        # -----------------------------
        # Gemini 설명
        # -----------------------------

        "ai_explanation":
            ai_explanation,

        "ai_explanation_error":
            ai_explanation_error,
    }


# =================================================
# 직접 실행 테스트
# =================================================

if __name__ == "__main__":

    try:

        result = analyze_transport(
            origin_keyword="서울역",
            destination_keyword="포항시청",
            cargo_weight_ton=10,
            shipping_date="2026-08-15",
            priority="1",
        )

        print(
            "\n===== 최종 반환값 ====="
        )

        print(
            result
        )

    except ValueError as error:

        print(
            "\n입력 또는 데이터 오류:",
            error
        )

    except FileNotFoundError as error:

        print(
            "\n파일 오류:",
            error
        )

    except RuntimeError as error:

        print(
            "\nAPI 오류:",
            error
        )

    except Exception as error:

        print(
            "\n예상하지 못한 오류:",
            error
        )