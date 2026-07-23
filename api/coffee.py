from fastapi import APIRouter, Request

from api.common import pack

router = APIRouter()


MENU_SECTIONS = {
    "추천메뉴": [
        "더치커피", "아메리카노", "카페라떼",
        "유자민트 릴렉서 티", "ICE 케모리치 릴렉서 티",
    ],
    "스무디": [
        "딸기주스", "바나나주스", "레몬요거트 스무디",
        "블루베리요거트 스무디", "딸기 요거트 스무니",
        "딸기 바나나 스무디",
    ],
    "커피": [
        "에스프레소", "아메리카노", "카페라떼", "카푸치노",
        "바닐라라떼", "돌체라떼", "시나몬라떼", "헤이즐넛라떼",
        "카라멜마키야토", "카페모카", "피치프레소", "더치커피",
    ],
    "음료": [
        "그린티 라떼", "오곡라떼", "고구마라떼", "로얄밀크티라떼",
        "초콜릿라떼", "리얼자몽티", "리얼레몬티", "진저레몬티",
        "매실차", "오미자차", "자몽에이드", "레몬에이드",
        "진저레몬에이드", "스팀우유", "사과유자차", "페퍼민트",
        "얼그레이", "캐모마일", "유자민트릴렉서티",
        "ICE 케모리치 릴렉서티", "배도라지모과차", "헛개차",
        "복숭아 아이스티", "딸기라떼",
    ],
    "병음료": [
        "분다버그 진저", "분다버그 레몬에이드",
        "분다버그 망고", "분다버그 자몽",
    ],
}


SECTION_STYLE = {
    "추천메뉴": {"emoji": "✨", "color": "#7C3AED"},
    "스무디": {"emoji": "🍓", "color": "#06B6D4"},
    "커피": {"emoji": "☕", "color": "#F59E0B"},
    "음료": {"emoji": "🥤", "color": "#10B981"},
    "병음료": {"emoji": "🧃", "color": "#EF4444"},
}


def mention_member(tenant_id: str, user_id: str, label: str = "member") -> str:
    return f'(dooray://{tenant_id}/members/{user_id} "{label}")'


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

            result[key] = [
                line
                for line in raw_value.split("\n")
                if line.strip()
            ]

    return result


def status_fields(status: dict) -> list[dict]:
    if not status:
        return [{
            "title": "아직 투표 없음",
            "value": "첫 투표를 기다리는 중!",
            "short": False,
        }]

    return [
        {
            "title": key,
            "value": "\n".join(voters) if voters else "-",
            "short": False,
        }
        for key, voters in status.items()
    ]


def status_attachment(fields=None) -> dict:
    return {
        "title": "선택 현황",
        "fields": fields or [{
            "title": "아직 투표 없음",
            "value": "첫 투표를 기다리는 중!",
            "short": False,
        }],
    }


def section_block_buttons(section: str) -> list[dict]:
    style = SECTION_STYLE.get(
        section,
        {"emoji": "•", "color": "#4757C4"},
    )

    blocks = [{
        "callbackId": "coffee-poll",
        "title": f"{style['emoji']}  {section}",
        "color": style["color"],
    }]

    actions = []

    for menu in MENU_SECTIONS[section]:
        actions.append({
            "name": f"vote::{section}",
            "type": "button",
            "text": f"{menu} (ICE)",
            "value": f"vote|{section}|{menu}|ICE",
        })

        allow_hot = (
            section not in ["스무디", "병음료"]
            and menu not in ["복숭아 아이스티", "딸기라떼"]
            and "요거트" not in menu
        )

        if allow_hot:
            actions.append({
                "name": f"vote::{section}",
                "type": "button",
                "text": f"{menu} (HOT)",
                "value": f"vote|{section}|{menu}|HOT",
            })

    blocks.append({
        "callbackId": "coffee-poll",
        "actions": actions,
        "color": style["color"],
    })

    return blocks


@router.post("/dooray/command")
async def coffee_command(req: Request):
    data = await req.json()
    print("[COFFEE COMMAND]", data)

    attachments = []

    for section in ["추천메뉴", "스무디", "커피", "음료", "병음료"]:
        attachments.extend(section_block_buttons(section))

    attachments.append(status_attachment())

    return pack({
        "responseType": "inChannel",
        "replaceOriginal": False,
        "text": "☕ 커피 투표를 시작합니다!",
        "attachments": attachments,
    })


@router.post("/dooray/actions")
async def coffee_actions(req: Request):
    data = await req.json()

    action_value = (data.get("actionValue") or "").strip()
    original = data.get("originalMessage") or {}
    user = data.get("user") or {}

    user_id = user.get("id", "user")
    tenant_id = (data.get("tenant") or {}).get("id", "tenant")

    if not action_value.startswith("vote|"):
        return pack({})

    parts = action_value.split("|", 3)

    if len(parts) != 4:
        return pack({})

    _, _section, menu, temperature = parts
    key = f"{menu} ({temperature})"

    status = parse_status(original)
    tag = mention_member(tenant_id, user_id)

    # 기존 투표 제거: 사용자당 전체 메뉴 중 1표만 유지
    for current_key in list(status.keys()):
        voters = [
            voter
            for voter in status.get(current_key, [])
            if voter != tag
        ]

        if voters:
            status[current_key] = voters
        else:
            del status[current_key]

    status.setdefault(key, [])

    if tag not in status[key]:
        status[key].append(tag)

    updated_fields = status_fields(status)
    new_attachments = []
    status_replaced = False

    for attachment in original.get("attachments") or []:
        if attachment.get("title") == "선택 현황":
            new_attachments.append(status_attachment(updated_fields))
            status_replaced = True
        else:
            new_attachments.append(attachment)

    if not status_replaced:
        new_attachments.append(status_attachment(updated_fields))

    return pack({
        "text": original.get("text") or "☕ 커피 투표",
        "attachments": new_attachments,
        "responseType": "inChannel",
        "replaceOriginal": True,
    })
