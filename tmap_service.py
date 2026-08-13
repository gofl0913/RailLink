import os

import requests
from dotenv import load_dotenv


load_dotenv()

APP_KEY = os.getenv("TMAP_APP_KEY")

if not APP_KEY:
    raise RuntimeError(
        ".env 파일에서 TMAP_APP_KEY를 찾을 수 없습니다."
    )


def search_place(keyword: str) -> dict:
    """장소명을 검색해 첫 번째 결과의 정보와 좌표를 반환한다."""

    url = "https://apis.openapi.sk.com/tmap/pois"

    headers = {
        "appKey": APP_KEY,
        "Accept": "application/json",
    }

    params = {
        "version": "1",
        "searchKeyword": keyword,
        "resCoordType": "WGS84GEO",
        "count": 5,
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=20,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"장소 검색 실패 출발지와 목적지를 다시 입력해주세요."
        )

    result = response.json()
    pois = result["searchPoiInfo"]["pois"].get("poi", [])

    if not pois:
        raise ValueError(
            f"'{keyword}'에 대한 검색 결과가 없습니다."
        )

    poi = pois[0]

    address_list = (
        poi.get("newAddressList", {})
        .get("newAddress", [])
    )

    if address_list:
        address = address_list[0].get(
            "fullAddressRoad",
            "주소 없음",
        )
    else:
        address = "주소 없음"

    return {
        "name": poi["name"],
        "address": address,
        "longitude": float(poi["frontLon"]),
        "latitude": float(poi["frontLat"]),
    }


def get_route(start: dict, end: dict) -> dict:
    """출발지와 목적지 좌표로 자동차 경로를 조회한다."""

    url = "https://apis.openapi.sk.com/tmap/routes?version=1"

    headers = {
        "appKey": APP_KEY,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    payload = {
        "startX": str(start["longitude"]),
        "startY": str(start["latitude"]),
        "endX": str(end["longitude"]),
        "endY": str(end["latitude"]),
        "startName": start["name"],
        "endName": end["name"],
        "reqCoordType": "WGS84GEO",
        "resCoordType": "WGS84GEO",
    }

    response = requests.post(
        url,
        headers=headers,
        data=payload,
        timeout=20,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"경로 조회 실패: {response.status_code}\n"
            f"{response.text}"
        )

    result = response.json()
    summary = result["features"][0]["properties"]

    return {
        "distance_km": summary["totalDistance"] / 1000,
        "duration_min": summary["totalTime"] / 60,
        "toll_won": summary.get("totalFare", 0),
    }