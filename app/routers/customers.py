from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Customer, AuditLog
from app.schemas import CustomerCreate, CustomerUpdate, CustomerOut
from app.auth import get_current_user

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("", response_model=list[CustomerOut])
def list_customers(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Customer).filter(Customer.user_id == user.id).order_by(Customer.name).all()


@router.post("", response_model=CustomerOut, status_code=201)
def create_customer(data: CustomerCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = Customer(user_id=user.id, **data.model_dump())
    db.add(c)
    db.flush()
    db.add(AuditLog(user_id=user.id, entity_type="customer", entity_id=c.id, action="create", new_values=data.model_dump(mode="json")))
    db.commit()
    db.refresh(c)
    return c


@router.get("/{cid}", response_model=CustomerOut)
def get_customer(cid: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.query(Customer).filter(Customer.id == cid, Customer.user_id == user.id).first()
    if not c:
        raise HTTPException(404, "Customer not found")
    return c


@router.patch("/{cid}", response_model=CustomerOut)
def update_customer(cid: str, data: CustomerUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.query(Customer).filter(Customer.id == cid, Customer.user_id == user.id).first()
    if not c:
        raise HTTPException(404, "Customer not found")
    changes = data.model_dump(exclude_unset=True)
    old_vals = {k: getattr(c, k) for k in changes}
    for k, v in changes.items():
        setattr(c, k, v)
    db.add(AuditLog(user_id=user.id, entity_type="customer", entity_id=c.id, action="update", old_values={k: str(v) for k, v in old_vals.items()}, new_values={k: str(v) for k, v in changes.items()}))
    db.commit()
    db.refresh(c)
    return c


@router.delete("/{cid}")
def delete_customer(cid: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.query(Customer).filter(Customer.id == cid, Customer.user_id == user.id).first()
    if not c:
        raise HTTPException(404, "Customer not found")
    db.delete(c)
    db.commit()
    return {"deleted": cid}
