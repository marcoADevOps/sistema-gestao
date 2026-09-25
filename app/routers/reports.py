from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app import crud, models, reports
from app.auth import require_login_web
from app.database import get_db

router = APIRouter(prefix="/web/reports", tags=["reports"], dependencies=[Depends(require_login_web)])

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PDF_MEDIA_TYPE = "application/pdf"


def _file_response(content: bytes, filename: str, media_type: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _parse_optional_date(value: str | None) -> date | None:
    """Trata o campo de data em branco (comum quando o formulário do
    dashboard é enviado sem filtro) como "sem filtro" em vez de erro 422."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Data inválida: '{value}'")


@router.get("/products.xlsx")
def export_products_excel(db: Session = Depends(get_db), user: models.User = Depends(require_login_web)):
    content = reports.products_to_excel(crud.list_all_products(db))
    crud.log_action(db, user.username, "export_report", "Relatório de produtos exportado (Excel)")
    return _file_response(content, "produtos.xlsx", XLSX_MEDIA_TYPE)


@router.get("/products.pdf")
def export_products_pdf(db: Session = Depends(get_db), user: models.User = Depends(require_login_web)):
    content = reports.products_to_pdf(crud.list_all_products(db))
    crud.log_action(db, user.username, "export_report", "Relatório de produtos exportado (PDF)")
    return _file_response(content, "produtos.pdf", PDF_MEDIA_TYPE)


@router.get("/clients.xlsx")
def export_clients_excel(db: Session = Depends(get_db), user: models.User = Depends(require_login_web)):
    content = reports.clients_to_excel(crud.list_all_clients(db))
    crud.log_action(db, user.username, "export_report", "Relatório de clientes exportado (Excel)")
    return _file_response(content, "clientes.xlsx", XLSX_MEDIA_TYPE)


@router.get("/clients.pdf")
def export_clients_pdf(db: Session = Depends(get_db), user: models.User = Depends(require_login_web)):
    content = reports.clients_to_pdf(crud.list_all_clients(db))
    crud.log_action(db, user.username, "export_report", "Relatório de clientes exportado (PDF)")
    return _file_response(content, "clientes.pdf", PDF_MEDIA_TYPE)


@router.get("/sales.xlsx")
def export_sales_excel(
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_login_web),
):
    start_date = _parse_optional_date(start_date)
    end_date = _parse_optional_date(end_date)
    content = reports.sales_to_excel(crud.list_all_sales(db, start_date=start_date, end_date=end_date))
    crud.log_action(db, user.username, "export_report", "Relatório de vendas exportado (Excel)")
    return _file_response(content, "vendas.xlsx", XLSX_MEDIA_TYPE)


@router.get("/sales.pdf")
def export_sales_pdf(
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_login_web),
):
    start_date = _parse_optional_date(start_date)
    end_date = _parse_optional_date(end_date)
    sales = crud.list_all_sales(db, start_date=start_date, end_date=end_date)

    period_label = ""
    if start_date and end_date:
        period_label = f"{start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"
    elif start_date:
        period_label = f"a partir de {start_date.strftime('%d/%m/%Y')}"
    elif end_date:
        period_label = f"até {end_date.strftime('%d/%m/%Y')}"

    content = reports.sales_to_pdf(sales, period_label=period_label)
    crud.log_action(db, user.username, "export_report", "Relatório de vendas exportado (PDF)")
    return _file_response(content, "vendas.pdf", PDF_MEDIA_TYPE)
