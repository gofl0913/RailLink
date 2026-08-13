import csv
import math
from pathlib import Path

from tmap_service import get_route


# =================================================
# 파일 경로
# =================================================

BASE_DIR = Path(__file__).resolve().parent

FREIGHT_STATIONS_CSV = (
    BASE_DIR
    / "freight_stations.csv"
)

RAIL_ROUTE_CSV = (
    BASE_DIR
    / "rail_route_summary_complete.csv"
)


# =================================================
# 역명 정규화
# =================================================

def normalize_station_name(
    station_name: str,
) -> str:
    """
    역명을 비교하기 쉬운 형태로 정규화한다.

    예:
    오봉역 → 오봉
    오봉   → 오봉
    """

    name = str(
        station_name
    ).strip()

    name = name.replace(
        "[기차역]",
        "",
    )

    name = name.replace(
        "[철도역]",
        "",
    )

    if name.endswith("역"):
        name = name[:-1]

    return name.strip()


# =================================================
# Haversine 거리
# =================================================

def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    두 위경도 사이의 직선거리(km)를 계산한다.

    가까운 화물역 후보를 빠르게 찾기 위한
    1차 필터링에 사용한다.
    """

    earth_radius_km = 6371.0

    lat1_rad = math.radians(
        lat1
    )

    lon1_rad = math.radians(
        lon1
    )

    lat2_rad = math.radians(
        lat2
    )

    lon2_rad = math.radians(
        lon2
    )

    delta_lat = (
        lat2_rad
        - lat1_rad
    )

    delta_lon = (
        lon2_rad
        - lon1_rad
    )

    a = (
        math.sin(
            delta_lat / 2
        ) ** 2
        +
        math.cos(
            lat1_rad
        )
        *
        math.cos(
            lat2_rad
        )
        *
        math.sin(
            delta_lon / 2
        ) ** 2
    )

    c = (
        2
        * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a),
        )
    )

    return (
        earth_radius_km
        * c
    )


# =================================================
# 화물역 좌표 CSV 불러오기
# =================================================

def load_freight_stations() -> list:
    """
    freight_stations.csv에서
    정상적으로 좌표가 확보된 화물역만 불러온다.
    """

    if not FREIGHT_STATIONS_CSV.exists():

        raise FileNotFoundError(
            "화물역 좌표 CSV를 찾을 수 없습니다.\n"
            f"확인 경로: {FREIGHT_STATIONS_CSV}"
        )

    stations = []

    with FREIGHT_STATIONS_CSV.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:

        reader = csv.DictReader(
            csv_file
        )

        for row in reader:

            status = str(
                row.get(
                    "search_status",
                    "",
                )
            ).strip()

            latitude = str(
                row.get(
                    "latitude",
                    "",
                )
            ).strip()

            longitude = str(
                row.get(
                    "longitude",
                    "",
                )
            ).strip()

            # 좌표 검색 실패 데이터 제외
            if status and status != "SUCCESS":
                continue

            if not latitude or not longitude:
                continue

            try:

                station = {
                    "station_name": (
                        normalize_station_name(
                            row[
                                "station_name"
                            ]
                        )
                    ),
                    "latitude": float(
                        latitude
                    ),
                    "longitude": float(
                        longitude
                    ),
                    "tmap_name": row.get(
                        "tmap_name",
                        "",
                    ),
                    "address": row.get(
                        "address",
                        "",
                    ),
                }

                stations.append(
                    station
                )

            except (
                ValueError,
                TypeError,
            ):
                continue

    if not stations:

        raise ValueError(
            "사용 가능한 화물역 좌표 데이터가 없습니다."
        )

    return stations


# =================================================
# 인근 화물역 후보 탐색
# =================================================

def find_nearest_stations(
    location: dict,
    stations: list,
    top_n: int = 5,
) -> list:
    """
    사용자 위치에서 가까운 화물역을
    직선거리 기준으로 TOP N개 추출한다.

    location에는
    latitude, longitude가 있어야 한다.
    """

    location_lat = float(
        location["latitude"]
    )

    location_lon = float(
        location["longitude"]
    )

    candidates = []

    for station in stations:

        distance_km = (
            haversine_distance(
                location_lat,
                location_lon,
                station[
                    "latitude"
                ],
                station[
                    "longitude"
                ],
            )
        )

        candidate = (
            station.copy()
        )

        candidate[
            "straight_distance_km"
        ] = distance_km

        candidates.append(
            candidate
        )

    candidates.sort(
        key=lambda item: (
            item[
                "straight_distance_km"
            ]
        )
    )

    return candidates[
        :top_n
    ]


# =================================================
# 철도 노선 데이터 불러오기
# =================================================

def load_rail_routes() -> list:
    """
    rail_route_summary_complete.csv에서
    출발역-도착역 조합을 불러온다.
    """

    if not RAIL_ROUTE_CSV.exists():

        raise FileNotFoundError(
            "철도 노선 CSV를 찾을 수 없습니다.\n"
            f"확인 경로: {RAIL_ROUTE_CSV}"
        )

    routes = []

    with RAIL_ROUTE_CSV.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:

        reader = csv.DictReader(
            csv_file
        )

        for row in reader:

            origin_station = (
                normalize_station_name(
                    row.get(
                        "origin_station",
                        "",
                    )
                )
            )

            destination_station = (
                normalize_station_name(
                    row.get(
                        "destination_station",
                        "",
                    )
                )
            )

            if (
                not origin_station
                or not destination_station
            ):
                continue

            routes.append(
                {
                    "origin_station": (
                        origin_station
                    ),
                    "destination_station": (
                        destination_station
                    ),
                }
            )

    return routes


# =================================================
# 철도 연결 가능 여부
# =================================================

def rail_route_exists(
    departure_station: str,
    arrival_station: str,
    rail_routes: list,
) -> bool:
    """
    출발 화물역 → 도착 화물역
    철도 노선 데이터가 존재하는지 확인한다.
    """

    departure_station = (
        normalize_station_name(
            departure_station
        )
    )

    arrival_station = (
        normalize_station_name(
            arrival_station
        )
    )

    for route in rail_routes:

        if (
            route[
                "origin_station"
            ]
            == departure_station
            and
            route[
                "destination_station"
            ]
            == arrival_station
        ):
            return True

    return False


# =================================================
# TMAP용 장소 객체 생성
# =================================================

def station_to_place(
    station: dict,
) -> dict:
    """
    freight_stations.csv의 역 데이터를
    get_route()가 사용할 수 있는 형태로 변환한다.
    """

    return {
        "name": (
            station.get(
                "tmap_name"
            )
            or
            f"{station['station_name']}역"
        ),

        "latitude": (
            station[
                "latitude"
            ]
        ),

        "longitude": (
            station[
                "longitude"
            ]
        ),

        "address": (
            station.get(
                "address",
                "",
            )
        ),
    }


# =================================================
# 유효한 철도역 조합 생성
# =================================================

def build_valid_station_pairs(
    departure_candidates: list,
    arrival_candidates: list,
    rail_routes: list,
) -> list:
    """
    가까운 출발 화물역 후보와
    도착 화물역 후보를 조합한 뒤

    실제 철도 노선이 존재하는 조합만 남긴다.
    """

    valid_pairs = []

    for departure in (
        departure_candidates
    ):

        for arrival in (
            arrival_candidates
        ):

            # 같은 역 제외
            if (
                departure[
                    "station_name"
                ]
                ==
                arrival[
                    "station_name"
                ]
            ):
                continue

            if rail_route_exists(
                departure[
                    "station_name"
                ],
                arrival[
                    "station_name"
                ],
                rail_routes,
            ):

                valid_pairs.append(
                    {
                        "departure": (
                            departure
                        ),
                        "arrival": (
                            arrival
                        ),
                    }
                )

    return valid_pairs


# =================================================
# 실제 First / Last Mile 거리 계산
# =================================================

def evaluate_station_pair(
    origin: dict,
    destination: dict,
    station_pair: dict,
) -> dict:
    """
    하나의 철도역 조합에 대해
    실제 First Mile / Last Mile 도로경로를
    TMAP으로 계산한다.
    """

    departure_station = (
        station_pair[
            "departure"
        ]
    )

    arrival_station = (
        station_pair[
            "arrival"
        ]
    )

    departure_place = (
        station_to_place(
            departure_station
        )
    )

    arrival_place = (
        station_to_place(
            arrival_station
        )
    )

    # 출발지 → 출발 화물역
    first_mile = get_route(
        origin,
        departure_place,
    )

    # 도착 화물역 → 최종 목적지
    last_mile = get_route(
        arrival_place,
        destination,
    )

    total_access_distance = (
        first_mile[
            "distance_km"
        ]
        +
        last_mile[
            "distance_km"
        ]
    )

    total_access_time = (
        first_mile[
            "duration_min"
        ]
        +
        last_mile[
            "duration_min"
        ]
    )

    return {
        "departure_station": (
            departure_station[
                "station_name"
            ]
        ),

        "arrival_station": (
            arrival_station[
                "station_name"
            ]
        ),

        "departure_place": (
            departure_place
        ),

        "arrival_place": (
            arrival_place
        ),

        "first_mile": (
            first_mile
        ),

        "last_mile": (
            last_mile
        ),

        "access_distance_km": (
            total_access_distance
        ),

        "access_time_min": (
            total_access_time
        ),

        "departure_straight_distance_km": (
            departure_station[
                "straight_distance_km"
            ]
        ),

        "arrival_straight_distance_km": (
            arrival_station[
                "straight_distance_km"
            ]
        ),
    }


# =================================================
# 최종 화물역 조합 자동 선택
# =================================================

def select_best_freight_stations(
    origin: dict,
    destination: dict,
    top_n: int = 5,
) -> dict:
    """
    사용자의 실제 출발지와 목적지를 기준으로
    가장 적합한 철도 화물역 조합을 선택한다.

    1. 가까운 화물역 TOP N
    2. 실제 철도 연결 가능한 조합 필터링
    3. First + Last Mile 실제 도로거리 계산
    4. 접근거리가 가장 짧은 조합 선택
    """

    # ---------------------------------------------
    # 1. 데이터 불러오기
    # ---------------------------------------------

    freight_stations = (
        load_freight_stations()
    )

    rail_routes = (
        load_rail_routes()
    )

    # ---------------------------------------------
    # 2. 출발지 주변 화물역
    # ---------------------------------------------

    departure_candidates = (
        find_nearest_stations(
            location=origin,
            stations=freight_stations,
            top_n=top_n,
        )
    )

    # ---------------------------------------------
    # 3. 목적지 주변 화물역
    # ---------------------------------------------

    arrival_candidates = (
        find_nearest_stations(
            location=destination,
            stations=freight_stations,
            top_n=top_n,
        )
    )

    # ---------------------------------------------
    # 4. 실제 철도 연결 가능한 조합
    # ---------------------------------------------

    valid_pairs = (
        build_valid_station_pairs(
            departure_candidates,
            arrival_candidates,
            rail_routes,
        )
    )

    if not valid_pairs:

        raise ValueError(
            "출발지와 목적지 주변 화물역 중 "
            "철도로 연결 가능한 조합을 찾지 못했습니다. "
            "top_n 값을 늘려보세요."
        )

    # ---------------------------------------------
    # 5. 각 후보 실제 First/Last Mile 평가
    # ---------------------------------------------

    evaluated_pairs = []

    for index, pair in enumerate(
        valid_pairs,
        start=1,
    ):

        departure_name = (
            pair[
                "departure"
            ][
                "station_name"
            ]
        )

        arrival_name = (
            pair[
                "arrival"
            ][
                "station_name"
            ]
        )

        print(
            f"화물역 후보 평가 "
            f"[{index}/{len(valid_pairs)}]: "
            f"{departure_name} → "
            f"{arrival_name}"
        )

        try:

            result = (
                evaluate_station_pair(
                    origin=origin,
                    destination=destination,
                    station_pair=pair,
                )
            )

            evaluated_pairs.append(
                result
            )

        except Exception as error:

            print(
                f"후보 평가 실패: "
                f"{departure_name} → "
                f"{arrival_name}"
            )

            print(
                f"사유: {error}"
            )

    if not evaluated_pairs:

        raise ValueError(
            "철도 연결 후보는 존재하지만 "
            "TMAP First/Last Mile 계산에 모두 실패했습니다."
        )

    # ---------------------------------------------
    # 6. First + Last Mile 거리 최소 후보 선택
    # ---------------------------------------------

    evaluated_pairs.sort(
        key=lambda item: (
            item[
                "access_distance_km"
            ]
        )
    )

    best_pair = (
        evaluated_pairs[0]
    )

    # ---------------------------------------------
    # 7. 최종 반환
    # ---------------------------------------------

    return {
        "departure_station": (
            best_pair[
                "departure_station"
            ]
        ),

        "arrival_station": (
            best_pair[
                "arrival_station"
            ]
        ),

        "departure_place": (
            best_pair[
                "departure_place"
            ]
        ),

        "arrival_place": (
            best_pair[
                "arrival_place"
            ]
        ),

        "first_mile": (
            best_pair[
                "first_mile"
            ]
        ),

        "last_mile": (
            best_pair[
                "last_mile"
            ]
        ),

        "access_distance_km": (
            best_pair[
                "access_distance_km"
            ]
        ),

        "access_time_min": (
            best_pair[
                "access_time_min"
            ]
        ),

        "candidate_count": (
            len(
                evaluated_pairs
            )
        ),

        "all_candidates": (
            evaluated_pairs
        ),
    }