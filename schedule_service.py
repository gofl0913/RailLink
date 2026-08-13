from datetime import datetime, timedelta


# Python weekday()
# 월=0, 화=1, 수=2, 목=3, 금=4, 토=5, 일=6
WEEKDAY_KR = {
    0: "월",
    1: "화",
    2: "수",
    3: "목",
    4: "금",
    5: "토",
    6: "일",
}


def parse_shipping_date(
    shipping_date: str,
) -> datetime:
    """
    사용자가 입력한 YYYY-MM-DD 형식의 날짜를
    datetime 객체로 변환한다.
    """

    try:
        return datetime.strptime(
            shipping_date,
            "%Y-%m-%d",
        )

    except ValueError:
        raise ValueError(
            "운송 희망 날짜는 "
            "YYYY-MM-DD 형식으로 입력하세요. "
            "예: 2026-08-10"
        )


def normalize_operation_days(
    operation_days: str,
) -> list:
    """
    CSV의 operation_days 문자열을
    ['월', '화', '수'] 형태의 리스트로 변환한다.

    예:
    '월,화,수,목,금'
    → ['월', '화', '수', '목', '금']

    공백이나 '/', '·' 같은 구분자도 처리한다.
    """

    if operation_days is None:
        return []

    text = str(
        operation_days
    ).strip()

    if not text:
        return []

    # 구분자 통일
    text = text.replace(
        "|",
        ",",
    )

    text = text.replace(
        "·",
        ",",
    )

    text = text.replace(
        " ",
        "",
    )

    # '월요일' 같은 값이 있을 경우 정리
    text = text.replace(
        "월요일",
        "월",
    )
    text = text.replace(
        "화요일",
        "화",
    )
    text = text.replace(
        "수요일",
        "수",
    )
    text = text.replace(
        "목요일",
        "목",
    )
    text = text.replace(
        "금요일",
        "금",
    )
    text = text.replace(
        "토요일",
        "토",
    )
    text = text.replace(
        "일요일",
        "일",
    )

    # 매일 / 일주일 전체 운행 표현
    if text in (
        "매일",
        "월~일",
        "월-일",
    ):
        return [
            "월",
            "화",
            "수",
            "목",
            "금",
            "토",
            "일",
        ]

    days = []

    for value in text.split(","):

        value = value.strip()

        if value in WEEKDAY_KR.values():
            days.append(
                value
            )

    # 중복 제거
    return list(
        dict.fromkeys(
            days
        )
    )


def get_weekday_korean(
    shipping_date: str,
) -> str:
    """
    입력 날짜의 요일을 한글 한 글자로 반환한다.

    예:
    2026-08-10 → 월
    """

    date_obj = parse_shipping_date(
        shipping_date
    )

    return WEEKDAY_KR[
        date_obj.weekday()
    ]


def is_train_available(
    shipping_date: str,
    operation_days: str,
) -> bool:
    """
    사용자가 선택한 날짜에
    해당 철도 노선이 운행하는지 판정한다.
    """

    shipping_weekday = (
        get_weekday_korean(
            shipping_date
        )
    )

    available_days = (
        normalize_operation_days(
            operation_days
        )
    )

    return (
        shipping_weekday
        in available_days
    )


def find_next_available_date(
    shipping_date: str,
    operation_days: str,
    max_search_days: int = 14,
) -> dict:
    """
    희망 운송일 이후 가장 가까운
    철도 운행 가능 날짜를 찾는다.

    기본적으로 최대 14일까지 탐색한다.
    """

    start_date = (
        parse_shipping_date(
            shipping_date
        )
    )

    available_days = (
        normalize_operation_days(
            operation_days
        )
    )

    if not available_days:
        return {
            "found": False,
            "next_date": None,
            "next_weekday": None,
            "waiting_days": None,
        }

    # 입력 당일이 운행일인 경우
    current_weekday = WEEKDAY_KR[
        start_date.weekday()
    ]

    if current_weekday in available_days:

        return {
            "found": True,
            "next_date": (
                start_date.strftime(
                    "%Y-%m-%d"
                )
            ),
            "next_weekday": (
                current_weekday
            ),
            "waiting_days": 0,
        }

    # 다음날부터 탐색
    for waiting_days in range(
        1,
        max_search_days + 1,
    ):

        candidate_date = (
            start_date
            + timedelta(
                days=waiting_days
            )
        )

        candidate_weekday = (
            WEEKDAY_KR[
                candidate_date.weekday()
            ]
        )

        if (
            candidate_weekday
            in available_days
        ):

            return {
                "found": True,
                "next_date": (
                    candidate_date.strftime(
                        "%Y-%m-%d"
                    )
                ),
                "next_weekday": (
                    candidate_weekday
                ),
                "waiting_days": (
                    waiting_days
                ),
            }

    return {
        "found": False,
        "next_date": None,
        "next_weekday": None,
        "waiting_days": None,
    }


def check_train_schedule(
    shipping_date: str,
    operation_days: str,
) -> dict:
    """
    날짜 관련 기능을 한 번에 수행하는 메인 함수.

    반환:
    - 희망 운송일
    - 해당 요일
    - 철도 운행요일
    - 당일 운행 가능 여부
    - 다음 운행 가능일
    - 대기일수
    """

    date_obj = parse_shipping_date(
        shipping_date
    )

    weekday = WEEKDAY_KR[
        date_obj.weekday()
    ]

    available_days = (
        normalize_operation_days(
            operation_days
        )
    )

    available_today = (
        weekday
        in available_days
    )

    next_schedule = (
        find_next_available_date(
            shipping_date,
            operation_days,
        )
    )

    return {
        "shipping_date": (
            date_obj.strftime(
                "%Y-%m-%d"
            )
        ),

        "shipping_weekday": (
            weekday
        ),

        "operation_days": (
            available_days
        ),

        "available_today": (
            available_today
        ),

        "next_available_date": (
            next_schedule[
                "next_date"
            ]
        ),

        "next_available_weekday": (
            next_schedule[
                "next_weekday"
            ]
        ),

        "waiting_days": (
            next_schedule[
                "waiting_days"
            ]
        ),
    }