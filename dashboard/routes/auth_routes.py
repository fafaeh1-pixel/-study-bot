from fastapi import APIRouter, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from dashboard.auth import verify_password, create_token

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = "$2b$12$V.42SKkYBUQToQ7jtdg7EO/zgPvsgmLTkDIx2Bk5y0qlgXP5mdlgm"


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": None}
    )


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
):
    if username == ADMIN_USERNAME and verify_password(password, ADMIN_PASSWORD_HASH):
        token = create_token({"sub": username})
        resp = RedirectResponse(url="/dashboard", status_code=302)
        resp.set_cookie("access_token", token, httponly=True, max_age=60 * 60 * 8)
        return resp
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": "نام کاربری یا رمز عبور اشتباه است"}
    )


@router.get("/logout")
async def logout():
    resp = RedirectResponse(url="/login", status_code=302)
    resp.delete_cookie("access_token")
    return resp


@router.get("/")
async def root():
    return RedirectResponse(url="/dashboard", status_code=302)