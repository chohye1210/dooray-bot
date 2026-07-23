import json
import os
from datetime import datetime

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from openai import OpenAI

from api.common import pack

router = APIRouter()

def analyze_vacation_text(user_text: str) -> dict:
    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")

    gpt_client = OpenAI(api_key=api_key)

    today = datetime.now().strftime("%Y-%m-%d")

    prompt = f"""
오늘 날짜는 {today} 입니다.

사용자의 휴가 신청 문장을 분석하여 반드시 순수 JSON 객체만 출력하세요.

주의사항:
- ```json 같은 코드블록을 절대 포함하지 마세요.
- 설명 문장을 포함하지 마세요.
- 오직 JSON만 출력하세요.
- 앞뒤 공백 없이 바로 {{ 로 시작하세요.

JSON 형식:
{{
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "reason": "string",
  "destination": "string",
  "vacation_type": "연차/반차/병가/기타"
}}

사용자 입력:
'''{user_text}'''
"""

    response = gpt_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "당신은 자연어를 휴가신청 필드로 변환하는 도우미입니다.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
    )

    content = response.choices[0].message.content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        print("GPT 응답 파싱 실패:", content)
        return {}


async def open_vacation_dialog(
    tenant_domain: str,
    channel_id: str,
    cmd_token: str,
    trigger_id: str,
    vacation_data: dict,
):
    url = (
        f"https://{tenant_domain}"
        f"/messenger/api/channels/{channel_id}/dialogs"
    )

    headers = {
        "Content-Type": "application/json",
        "token": cmd_token,
        "Dooray-Db-Id": "23",
    }

    payload = {
        "token": cmd_token,
        "triggerId": trigger_id,
        "callbackId": "vacation-apply",
        "dialog": {
            "callbackId": "vacation-apply",
            "title": "📅 휴가 신청",
            "submitLabel": "신청하기",
            "elements": [
                {
                    "type": "select",
                    "label": "휴가 구분",
                    "name": "vacation_type",
                    "optional": False,
                    "options": [
                        {"label": "연차,보상-Annual,Compensatory", "value": "연차,보상-Annual,Compensatory"},
                        {"label": "연차,보상(시간)-Annual,Compensatory(time)", "value": "연차,보상(시간)-Annual,Compensatory(time)"},
                        {"label": "저축휴가-Saved Annual", "value": "저축휴가-Saved Annual"},
                        {"label": "병가-Sick", "value": "병가-Sick"},
                        {"label": "보호-일반-Protection-General", "value": "보호-일반-Protection-General"},
                        {"label": "산전,산후-Protection-Maternity", "value": "산전,산후-Protection-Maternity"},
                        {"label": "생리휴가(무급)-Menstrual(unpaid)", "value": "생리휴가(무급)-Menstrual(unpaid)"},
                        {"label": "특별-Celebration-Condolence", "value": "특별-Celebration-Condolence"},
                        {"label": "공가-Official", "value": "공가-Official"},
                        {"label": "공가(시간)-Official(time)", "value": "공가(시간)-Official(time)"},
                        {"label": "장기근속-Long Service", "value": "장기근속-Long Service"},
                        {"label": "기타-Etc.", "value": "기타-Etc."},
                        {"label": "자녀돌봄휴가-Child care leave", "value": "자녀돌봄휴가-Child care leave"},
                        {"label": "자녀돌봄휴가(시간)-Child care leave(time)", "value": "자녀돌봄휴가(시간)-Child care leave(time)"},
                    ],
                },
                {
                    "type": "text",
                    "label": "휴가 시작일",
                    "name": "start_date",
                    "value": vacation_data.get("start_date", ""),
                    "optional": False,
                },
                {
                    "type": "text",
                    "label": "휴가 종료일",
                    "name": "end_date",
                    "value": vacation_data.get("end_date", ""),
                    "optional": False,
                },
                {
                    "type": "text",
                    "label": "휴가 사유",
                    "name": "reason",
                    "value": vacation_data.get("reason", ""),
                    "optional": False,
                },
                {
                    "type": "text",
                    "label": "행선지",
                    "name": "destination",
                    "value": vacation_data.get("destination", ""),
                    "optional": False,
                },
            ],
        },
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            url,
            headers=headers,
            json=payload,
        )

    print("Dialog status:", response.status_code)
    print("Dialog body:", response.text)


@router.post("/dooray/test")
async def vacation_command(req: Request):
    data = await req.json()
    print("[VACATION COMMAND]", data)

    user_text = (data.get("text") or "").strip()

    if not user_text:
        return pack({
            "responseType": "ephemeral",
            "text": "예: /휴가신청 내일부터 모레까지 제주도 가족여행",
        })

    vacation_data = analyze_vacation_text(user_text)
    print("GPT 분석 결과:", vacation_data)

    await open_vacation_dialog(
        tenant_domain=data.get("tenantDomain"),
        channel_id=data.get("channelId"),
        cmd_token=data.get("cmdToken"),
        trigger_id=data.get("triggerId"),
        vacation_data=vacation_data,
    )

    return JSONResponse(status_code=200, content={})
