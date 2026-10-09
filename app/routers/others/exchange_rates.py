from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import cast, String
from sqlalchemy.exc import IntegrityError
from app import ExchangeRate, ExchangeRateBatchCreate, ExchangeRateResponse, crud_exchange_rate, get_db
from app.api.deps import require_roles
from app.core import LEVEL_BASIC, LEVEL_MEDIUM

router = APIRouter(prefix="/exchange_rates", tags=["Exchange Rates"])

@router.post("/", response_model=List[ExchangeRateResponse], status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def create_exchange_rates(exchange_rate_in: ExchangeRateBatchCreate, db: Session = Depends(get_db)):
    """Create new exchange rates for today in the database."""
    if not exchange_rate_in.exchange_rates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=["La lista de tasas de cambio no puede estar vacía."]
        )

    seen_currencies = set()
    for index, dt in enumerate(exchange_rate_in.exchange_rates):
        if dt.currency in seen_currencies:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=[f"El elemento {index + 1} contiene la divisa '{dt.currency}' duplicada dentro de la misma petición."]
            )
        seen_currencies.add(dt.currency)

    errors_409 = []
    date_now = date.today()

    for dt in exchange_rate_in.exchange_rates:
        if not dt.rate_date:
            dt.rate_date = date_now

        db_exchange_rate = crud_exchange_rate.search_where_by_fields(
            db=db, 
            currency=dt.currency, 
            rate_date=dt.rate_date
        )
        if db_exchange_rate:
            errors_409.append(f"La tasa para la divisa '{dt.currency}' ya se encuentra registrada para el día de hoy.")

    if errors_409:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=errors_409
        )

    created_ids = []
    try:
        for dt in exchange_rate_in.exchange_rates:
            if not dt.rate_date:
                dt.rate_date = date_now
            db_exchange_rate = crud_exchange_rate.create(db, obj_in=dt)
            created_ids.append(db_exchange_rate.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto al registrar las tasas de cambio del día. Verifique los datos ingresados."]
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=[str(e)]
        )

    return crud_exchange_rate.get_multi(db=db, identities=created_ids)

@router.get("/", response_model=List[ExchangeRateResponse], dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_exchange_rates(
    q: Optional[str] = None, 
    skip: int = 0, 
    limit: int = 20, 
    sort_by: Optional[str] = "rate_date",
    sort_order: str = "desc",
    db: Session = Depends(get_db)
):
    """Retrieves a paginated list of exchange rates or performs a real-time search by sending 'q'."""
    if q and q.strip():
        return crud_exchange_rate.search_ilike(
            db=db, 
            query=q, 
            search_fields=[
                cast(ExchangeRate.rate_date, String), 
                cast(ExchangeRate.exchange, String), 
                ExchangeRate.currency
            ], 
            limit=limit,
            skip=skip,
            sort_by=sort_by,
            sort_order=sort_order
        )
    return crud_exchange_rate.get_multi(db, skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order)

@router.get("/{exchage_id}", response_model=ExchangeRateResponse, dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_exchange_rate_by_id(exchage_id: int, db: Session = Depends(get_db)):
    """Retrieves an exchange rates specific by its ID."""
    db_log = crud_exchange_rate.get_by_id(db, id=exchage_id)
    if not db_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=["Tasa de cambio no encontrada"]
        )
    return db_log