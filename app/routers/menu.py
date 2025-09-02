from fastapi import APIRouter, Request
from app.core.templates import templates
from app.core.decorators import is_logged_in

router = APIRouter()


@router.get("/menu")
@is_logged_in
def menu_page(request: Request):
    return templates.TemplateResponse("menu.html", {"request": request})
