from fastapi import APIRouter, Request

from api.common import pack

router = APIRouter()


# =========================================================
# 메뉴
# =========================================================
MENU_SECTIONS = {
    "추천메뉴": [
        "더치커피",
        "아메리카노",
        "카페라떼",
        "유자민트 릴렉서 티",
        "ICE 케모리치 릴렉서 티",
    ],
    "스무디": [
        "딸기주스",
        "바나나주스",
        "레몬요거트 스무디",
        "블루베리요거트 스무디",
        "딸기 요거트 스무니",
        "딸기 바나나 스무디",
    ],
    "커피": [
        "에스프레소",
        "아메리카노",
        "카페라떼",
        "카푸치노",
        "바닐라라떼",
        "돌체라떼",
        "시나몬라떼",
        "헤이즐넛라떼",
        "카라멜마키야토",
        "카페모카",
        "피치프레소",
        "더치커피",
    ],
    "음료": [
        "그린티 라떼",
        "오곡라떼",
        "고구마라떼",
        "로얄밀크티라떼",
        "초콜릿라떼",
        "리얼자몽티",
        "리얼레몬티",
        "진저레몬티",
        "매실차",
        "오미자차",
        "자몽에이드",
        "레몬에이드",
        "진저레몬에이드",
        "스팀우유",
        "사과유자차",
        "페퍼민트",
        "얼그레이",
        "캐모마일",
        "유자민트릴렉서티",
        "ICE 케모리치 릴렉서티",
        "배도라지모과차",
        "헛개차",
        "복숭아 아이스티",
        "딸기라떼",
    ],
    "병음료": [
        "분다버그 진저",
        "분다버그 레몬에이드",
        "분다버그 망고",
        "분다버그 자몽",
    ],
}


# =========================================================
# 섹션 스타일
# =========================================================
SECTION_STYLE = {
    "추천메뉴": {
        "emoji": "✨",
        "color": "#7C3AED",
    },
    "스무디": {
        "emoji": "🍓",
        "color": "#06B6D4",
    },
    "커피": {
        "emoji": "☕",
        "color": "#F59E0B",
    },
    "음료": {
        "emoji": "🥤",
        "color": "#10B981",
    },
    "병음료": {
        "emoji": "🧃",
        "color": "#EF4444",
    },
}


# =========================================================
# 사용자 멘션 생성
# =========================================================
def mention_member(
    tenant_id: str,
    user_id: str,
    label: str = "member",
) -> str:
    return f'(dooray://{tenant_id}/members/{user_id} "{label}")'


# =========================================================
# 인터랙션 값 추출
# Dooray 요청 형식에 따라 actionValue 또는 actions 안에 들어올 수 있음
# =========================================================
def get_action_value(data: dict) -> str:
    direct_value = (data.get("actionValue") or "").strip()

    if direct_value:
        return direct_value

    actions = data.get("actions") or []

    if actions and isinstance(actions, list):
        first_action = actions[0] or {}
        return (first_action.get("value") or "").strip()

    return ""


# =========================================================
# 기존 메시지에서 투표 현황 파싱
# =========================================================
def parse_status(original: dict) -> dict:
    result = {}

    for attachment in original.get("attachments") or []:
        if attachment.get("title") != "선택 현황":
            continue

        for field in attachment.get("fields") or []:
            key = (field.get("title") or "").strip()
            raw_value = (field.get("value") or "").strip()

            if not key:
                continue

            # 최초 안내 문구는 실제 투표 항목이 아니므로 제외
            if key == "아직 투표 없음":
                continue

            voters = [
                line.strip()
                for line in raw_value.split("\n")
                if line.strip() and line.strip() != "-"
            ]

            if voters:
                result[key] = voters

    return result


# =========================================================
# 투표 현황을 Dooray fields 형식으로 변환
# =========================================================
def status_fields(status: dict) -> list[dict]:
    if not status:
        return [
            {
                "title": "아직 투표 없음",
                "value": "첫 투표를 기다리는 중!",
                "short": False,
            }
        ]

    return [
        {
            "title": menu_name,
            "value": "\n".join(voters),
            "short": False,
        }
        for menu_name, voters in status.items()
    ]


# =========================================================
# 선택 현황 attachment 생성
# =========================================================
def status_attachment(fields=None) -> dict:
    return {
        "title": "선택 현황",
        "fields": fields
        or [
            {
                "title": "아직 투표 없음",
                "value": "첫 투표를 기다리는 중!",
                "short": False,
            }
        ],
    }


# =========================================================
# 메뉴별 버튼 생성
# =========================================================
def section_block_buttons(section: str) -> list[dict]:
    style = SECTION_STYLE.get(
        section,
        {
            "emoji": "•",
            "color": "#4757C4",
        },
    )

    blocks = [
        {
            "callbackId": "coffee-poll",
            "title": f"{style['emoji']}  {section}",
            "color": style["color"],
        }
    ]

    actions = []

    for menu in MENU_SECTIONS[section]:
        # ICE 버튼
        actions.append(
            {
                "name": f"vote::{section}",
                "type": "button",
                "text": f"{menu} (ICE)",
                "value": f"vote|{section}|{menu}|ICE",
            }
        )

        # HOT 버튼 허용 여부
        allow_hot = (
            section not in ["스무디", "병음료"]
            and menu not in ["복숭아 아이스티", "딸기라떼"]
            and "요거트" not in menu
            and not menu.startswith("ICE ")
        )

        if allow_hot:
            actions.append(
                {
                    "name": f"vote::{section}",
                    "type": "button",
                    "text": f"{menu} (HOT)",
                    "value": f"vote|{section}|{menu}|HOT",
                }
            )

    blocks.append(
        {
            "callbackId": "coffee-poll",
            "actions": actions,
            "color": style["color"],
        }
    )

    return blocks


# =========================================================
# 1. 슬래시 커맨드 요청 URL
#
# Dooray Request URL:
# https://dooray-bot.vercel.app/dooray/coffee
#
# 기존 /dooray/command 주소도 함께 지원
# =========================================================
@router.post("/dooray/coffee")
@router.post("/dooray/command")
async def coffee_command(req: Request):
    data = await req.json()
    print("[COFFEE COMMAND]", data)

    attachments = []

    section_order = [
        "추천메뉴",
        "스무디",
        "커피",
        "음료",
        "병음료",
    ]

    for section in section_order:
        attachments.extend(section_block_buttons(section))

    attachments.append(status_attachment())

    return pack(
        {
            "responseType": "inChannel",
            "replaceOriginal": False,
            "text": "☕ 커피 투표를 시작합니다!",
            "attachments": attachments,
        }
    )


# =========================================================
# 2. 인터랙티브 메시지 Optional URL
#
# Dooray Optional URL:
# https://dooray-bot.vercel.app/dooray/actions
#
# 사용자가 버튼을 누르면 호출됨
# =========================================================
@router.post("/dooray/actions")
async def coffee_actions(req: Request):
    data = await req.json()
    print("[COFFEE ACTION]", data)

    action_value = get_action_value(data)

    original = data.get("originalMessage") or {}
    user = data.get("user") or {}
    tenant = data.get("tenant") or {}

    user_id = str(user.get("id") or "user")
    tenant_id = str(tenant.get("id") or "tenant")

    # 커피 투표 버튼이 아니면 무시
    if not action_value.startswith("vote|"):
        return pack({})

    # vote|섹션|메뉴|온도
    parts = action_value.split("|", 3)

    if len(parts) != 4:
        print("[INVALID ACTION VALUE]", action_value)
        return pack({})

    _, section, menu, temperature = parts

    selected_key = f"{menu} ({temperature})"

    # 기존 투표 현황 읽기
    status = parse_status(original)

    # 현재 사용자의 Dooray 멘션
    user_tag = mention_member(
        tenant_id=tenant_id,
        user_id=user_id,
    )

    # -----------------------------------------------------
    # 사용자당 하나의 메뉴만 선택 가능
    # 기존에 선택한 모든 메뉴에서 현재 사용자를 제거
    # -----------------------------------------------------
    for current_key in list(status.keys()):
        voters = status.get(current_key) or []

        remaining_voters = [
            voter
            for voter in voters
            if voter != user_tag
        ]

        if remaining_voters:
            status[current_key] = remaining_voters
        else:
            del status[current_key]

    # -----------------------------------------------------
    # 새 메뉴에 사용자 추가
    # -----------------------------------------------------
    status.setdefault(selected_key, [])

    if user_tag not in status[selected_key]:
        status[selected_key].append(user_tag)

    print(
        "[VOTE RESULT]",
        {
            "section": section,
            "menu": menu,
            "temperature": temperature,
            "user": user_id,
            "status": status,
        },
    )

    updated_fields = status_fields(status)

    # -----------------------------------------------------
    # 기존 버튼은 그대로 유지하고
    # 선택 현황 attachment만 교체
    # -----------------------------------------------------
    new_attachments = []
    status_replaced = False

    for attachment in original.get("attachments") or []:
        if attachment.get("title") == "선택 현황":
            new_attachments.append(
                status_attachment(updated_fields)
            )
            status_replaced = True
        else:
            new_attachments.append(attachment)

    if not status_replaced:
        new_attachments.append(
            status_attachment(updated_fields)
        )

    # 기존 메시지를 갱신
    return pack(
        {
            "responseType": "inChannel",
            "replaceOriginal": True,
            "text": original.get("text")
            or "☕ 커피 투표를 시작합니다!",
            "attachments": new_attachments,
        }
    )