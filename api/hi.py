from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/dooray/hi")
async def hi_command(req: Request):
    return {
        "responseType": "ephemeral",
        "text": "안녕하세요!"
    }