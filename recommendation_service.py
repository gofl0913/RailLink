def validate_weights(
    cost_weight: float,
    time_weight: float,
    carbon_weight: float,
):
    """
    비용·시간·탄소 가중치가 올바른지 확인한다.

    예:
    비용 0.25
    시간 0.25
    탄소 0.50

    합계 = 1.0
    """

    if (
        cost_weight < 0
        or time_weight < 0
        or carbon_weight < 0
    ):
        raise ValueError(
            "가중치는 0 이상이어야 합니다."
        )

    total = (
        cost_weight
        + time_weight
        + carbon_weight
    )

    if abs(total - 1.0) > 0.001:
        raise ValueError(
            f"가중치 합은 1.0이어야 합니다. "
            f"현재 합계: {total:.3f}"
        )


def normalize_pair(
    road_value: float,
    multimodal_value: float,
) -> tuple:
    """
    도로 100%와 복합운송 값을
    동일한 0~1 범위로 정규화한다.

    계산식:

    도로 점수
    = 도로값 / (도로값 + 복합값)

    복합운송 점수
    = 복합값 / (도로값 + 복합값)

    비용·시간·탄소는 모두
    '작을수록 좋은 지표'이므로
    정규화 점수도 낮을수록 좋다.

    두 점수의 합은 항상 1이다.
    """

    if road_value < 0 or multimodal_value < 0:
        raise ValueError(
            "비교값은 0 이상이어야 합니다."
        )

    total = (
        road_value
        + multimodal_value
    )

    if total == 0:
        return 0.5, 0.5

    road_normalized = (
        road_value / total
    )

    multimodal_normalized = (
        multimodal_value / total
    )

    return (
        road_normalized,
        multimodal_normalized,
    )


def calculate_recommendation(
    road_cost: float,
    road_time: float,
    road_carbon: float,
    multimodal_cost: float,
    multimodal_time: float,
    multimodal_carbon: float,
    cost_weight: float,
    time_weight: float,
    carbon_weight: float,
) -> dict:
    """
    비용·시간·탄소를 정규화한 뒤
    사용자 선호 가중치를 적용하여
    최적 운송안을 추천한다.

    낮은 종합점수 = 더 좋은 운송안
    """

    # -------------------------------------------------
    # 1. 가중치 검증
    # -------------------------------------------------

    validate_weights(
        cost_weight,
        time_weight,
        carbon_weight,
    )

    # -------------------------------------------------
    # 2. 비용 정규화
    # -------------------------------------------------

    (
        road_cost_score,
        multimodal_cost_score,
    ) = normalize_pair(
        road_cost,
        multimodal_cost,
    )

    # -------------------------------------------------
    # 3. 시간 정규화
    # -------------------------------------------------

    (
        road_time_score,
        multimodal_time_score,
    ) = normalize_pair(
        road_time,
        multimodal_time,
    )

    # -------------------------------------------------
    # 4. 탄소 정규화
    # -------------------------------------------------

    (
        road_carbon_score,
        multimodal_carbon_score,
    ) = normalize_pair(
        road_carbon,
        multimodal_carbon,
    )

    # -------------------------------------------------
    # 5. 가중합 목적함수
    # -------------------------------------------------

    road_score = (
        road_cost_score
        * cost_weight

        + road_time_score
        * time_weight

        + road_carbon_score
        * carbon_weight
    )

    multimodal_score = (
        multimodal_cost_score
        * cost_weight

        + multimodal_time_score
        * time_weight

        + multimodal_carbon_score
        * carbon_weight
    )

    # -------------------------------------------------
    # 6. 최적 운송안 결정
    # -------------------------------------------------

    tolerance = 0.0001

    score_difference = (
        multimodal_score
        - road_score
    )

    if abs(score_difference) <= tolerance:

        recommended_mode = "tie"
        recommended_name = "두 운송안이 유사한 수준"

    elif multimodal_score < road_score:

        recommended_mode = "multimodal"
        recommended_name = "철도·도로 복합운송"

    else:

        recommended_mode = "road"
        recommended_name = "도로 100% 운송"

    # -------------------------------------------------
    # 7. 실제 값 차이
    # -------------------------------------------------

    cost_difference = (
        multimodal_cost
        - road_cost
    )

    time_difference = (
        multimodal_time
        - road_time
    )

    carbon_difference = (
        multimodal_carbon
        - road_carbon
    )

    # -------------------------------------------------
    # 8. 실제 값 변화율
    # -------------------------------------------------

    if road_cost > 0:

        cost_change_rate = (
            cost_difference
            / road_cost
            * 100
        )

    else:

        cost_change_rate = 0

    if road_time > 0:

        time_change_rate = (
            time_difference
            / road_time
            * 100
        )

    else:

        time_change_rate = 0

    if road_carbon > 0:

        carbon_change_rate = (
            carbon_difference
            / road_carbon
            * 100
        )

    else:

        carbon_change_rate = 0

    # -------------------------------------------------
    # 9. 기존 출력 호환용 상대비율
    # -------------------------------------------------

    if road_cost > 0:
        cost_ratio = (
            multimodal_cost
            / road_cost
        )
    else:
        cost_ratio = 0

    if road_time > 0:
        time_ratio = (
            multimodal_time
            / road_time
        )
    else:
        time_ratio = 0

    if road_carbon > 0:
        carbon_ratio = (
            multimodal_carbon
            / road_carbon
        )
    else:
        carbon_ratio = 0

    # -------------------------------------------------
    # 10. 결과 반환
    # -------------------------------------------------

    return {
        "recommended_mode": (
            recommended_mode
        ),

        "recommended_name": (
            recommended_name
        ),

        "road_score": round(
            road_score,
            4,
        ),

        "multimodal_score": round(
            multimodal_score,
            4,
        ),

        "weights": {
            "cost": cost_weight,
            "time": time_weight,
            "carbon": carbon_weight,
        },

        # 실제 목적함수에 사용한 정규화 점수
        "normalized_scores": {

            "road": {
                "cost": round(
                    road_cost_score,
                    4,
                ),
                "time": round(
                    road_time_score,
                    4,
                ),
                "carbon": round(
                    road_carbon_score,
                    4,
                ),
            },

            "multimodal": {
                "cost": round(
                    multimodal_cost_score,
                    4,
                ),
                "time": round(
                    multimodal_time_score,
                    4,
                ),
                "carbon": round(
                    multimodal_carbon_score,
                    4,
                ),
            },
        },

        # 기존 combined 코드 출력과의 호환을 위해 유지
        "ratios": {

            "road": {
                "cost": 1.0,
                "time": 1.0,
                "carbon": 1.0,
            },

            "multimodal": {
                "cost": round(
                    cost_ratio,
                    4,
                ),
                "time": round(
                    time_ratio,
                    4,
                ),
                "carbon": round(
                    carbon_ratio,
                    4,
                ),
            },
        },

        "differences": {
            "cost_won": round(
                cost_difference
            ),

            "time_min": round(
                time_difference,
                1,
            ),

            "carbon_kg": round(
                carbon_difference,
                2,
            ),
        },

        "change_rates": {
            "cost_percent": round(
                cost_change_rate,
                1,
            ),

            "time_percent": round(
                time_change_rate,
                1,
            ),

            "carbon_percent": round(
                carbon_change_rate,
                1,
            ),
        },
    }