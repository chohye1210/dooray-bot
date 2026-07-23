from fastapi import FastAPI

from api.hi import router as hi_router
from api.coffee import router as coffee_router
from api.vacation import router as vacation_router

app = FastAPI(title="Dooray Bot")

app.include_router(hi_router)
app.include_router(coffee_router)
app.include_router(vacation_router)


@app.get("/")
async def root():
    return {"message": "Dooray bot API is running"}
