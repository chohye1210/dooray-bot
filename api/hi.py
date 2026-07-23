from fastapi import APIRouter, Request
from api.common import pack

router = APIRouter()


@router.post("/dooray/hi")
async def hi_command(req: Request):
    return pack({
        "responseType": "ephemeral",
        "text": "안녕하세요!"
    })