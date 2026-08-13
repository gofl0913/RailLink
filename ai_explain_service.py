import os

from dotenv import load_dotenv
from google import genai


# =================================================
# 환경변수 로드
# =================================================

load_dotenv()

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY"
)

if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY가 .env 파일에 없습니다."
    )


# =================================================
# Gemini Client
# =================================================

client = genai.Client(
    api_key=GEMINI_API_KEY
)


# =================================================
# 추천 설명 생성
# =================================================

def generate_ai_explanation(
    recommended_name: str,

    road_cost: float,
    road_time: float,
    road_carbon: float,

    multimodal_cost: float,
    multimodal_time: float,
    multimodal_carbon: float,

    cost_weight: float,
    time_weight: float,
    carbon_weight: float,

    road_score: float = None,
    multimodal_score: float = None,

    carbon_reduction_rate: float = None,

    rail_available: bool = True,

    shipping_date: str = "",
    next_available_date: str = "",
) -> str:
    """
    기존 계산 엔진이 산출한 결과를
    Gemini에 전달하여 사용자 친화적인
    추천 설명을 생성한다.

    주의:
    Gemini는 추천안을 새로 판단하지 않고
    이미 결정된 추천 결과를 설명하는 역할만 한다.
    """

    # -------------------------------------------------
    # 1. 변화율 계산
    # -------------------------------------------------

    if road_cost > 0:
        cost_change_rate = (
            (
                multimodal_cost
                - road_cost
            )
            / road_cost
            * 100
        )
    else:
        cost_change_rate = 0

    if road_time > 0:
        time_change_rate = (
            (
                multimodal_time
                - road_time
            )
            / road_time
            * 100
        )
    else:
        time_change_rate = 0

    if road_carbon > 0:
        carbon_change_rate = (
            (
                multimodal_carbon
                - road_carbon
            )
            / road_carbon
            * 100
        )
    else:
        carbon_change_rate = 0

    # -------------------------------------------------
    # 2. 프롬프트 작성
    # -------------------------------------------------

    prompt = f"""
너는 철도·도로 복합물류 의사결정 서비스의
결과 설명 AI이다.

아래 값들은 이미 외부 계산 로직과 목적함수에 의해
산출된 최종 결과다.

너는 절대로 추천 결과를 다시 계산하거나
다른 운송안을 새롭게 추천하면 안 된다.

제공된 숫자만 사용해서,
왜 해당 운송안이 추천되었는지
한국어로 쉽고 간결하게 설명하라.

설명은 3~5문장으로 작성하고,
다음 내용을 중심으로 설명하라.

1. 추천된 운송안
2. 도로 100%와 복합운송의 비용 차이
3. 운송시간 차이
4. 탄소배출량 차이
5. 사용자의 비용·시간·친환경 가중치
6. 사용자의 우선순위와 추천 결과가 어떻게 연결되는지

숫자를 임의로 새로 만들지 말고,
아래 데이터만 사용하라.


[최종 추천 결과]

추천 운송안:
{recommended_name}


[사용자 선호 가중치]

비용:
{cost_weight * 100:.0f}%

시간:
{time_weight * 100:.0f}%

친환경:
{carbon_weight * 100:.0f}%


[도로 100% 운송]

비용:
{road_cost:,.0f}원

시간:
{road_time:,.0f}분

탄소배출량:
{road_carbon:,.2f} kgCO2e


[철도·도로 복합운송]

비용:
{multimodal_cost:,.0f}원

시간:
{multimodal_time:,.0f}분

탄소배출량:
{multimodal_carbon:,.2f} kgCO2e


[복합운송 전환 시 변화]

비용 변화율:
{cost_change_rate:+.1f}%

시간 변화율:
{time_change_rate:+.1f}%

탄소 변화율:
{carbon_change_rate:+.1f}%
"""

    # -------------------------------------------------
    # 3. 목적함수 점수가 있을 경우 추가
    # -------------------------------------------------

    if (
        road_score is not None
        and multimodal_score is not None
    ):

        prompt += f"""

[목적함수 종합점수]

도로 100%:
{road_score:.4f}

복합운송:
{multimodal_score:.4f}

종합점수는 낮을수록
사용자 조건에 더 적합하다.
"""

    # -------------------------------------------------
    # 4. 탄소 절감률 추가
    # -------------------------------------------------

    if carbon_reduction_rate is not None:

        prompt += f"""

탄소 절감률:
{carbon_reduction_rate:.1f}%
"""

    # -------------------------------------------------
    # 5. 날짜 운행 불가 상황
    # -------------------------------------------------

    if not rail_available:

        prompt += f"""

[철도 운행 제약]

사용자 희망 운송일:
{shipping_date}

해당 날짜에는 선택된 철도 노선이
운행하지 않는다.

따라서 복합운송은 목적함수 평가와 관계없이
이용 가능한 후보에서 제외되었고,
도로 100% 운송이 추천되었다.
"""

        if next_available_date:

            prompt += f"""

다음 철도 운행 가능일:
{next_available_date}
"""

    # -------------------------------------------------
    # 6. 최종 지시
    # -------------------------------------------------

    prompt += """

최종 출력에는
"AI 분석", "분석 결과" 같은 제목을 붙이지 말고
설명 문장만 출력하라.

추천 결과를 변경하지 마라.
"""

    # -------------------------------------------------
    # 7. Gemini API 호출
    # -------------------------------------------------

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )

    # -------------------------------------------------
    # 8. 결과 반환
    # -------------------------------------------------

    if not response.text:
        return (
            "추천 결과에 대한 AI 설명을 "
            "생성하지 못했습니다."
        )

    return response.text.strip()