from fastapi.responses import JSONResponse


def pack(payload: dict) -> JSONResponse:
    return JSONResponse(
        content=payload,
        media_type="application/json; charset=utf-8",
    )
