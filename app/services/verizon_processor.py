import csv
import io
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models import VerizonImport, VerizonCallRecord

DEFAULT_COLUMN_MAP = {
    "phone_number": "Phone Number",
    "call_date": "Date",
    "duration_seconds": "Duration (sec)",
    "call_type": "Type",
    "charge_amount": "Charge",
}


def parse_csv(
    raw_csv: str,
    column_mapping: dict | None = None,
) -> list[dict]:
    mapping = column_mapping or DEFAULT_COLUMN_MAP
    reader = csv.DictReader(io.StringIO(raw_csv))

    records = []
    for row in reader:
        record = {}
        for field, csv_col in mapping.items():
            val = row.get(csv_col, "").strip()
            if field == "duration_seconds":
                try:
                    record[field] = int(float(val)) if val else 0
                except ValueError:
                    record[field] = 0
            elif field == "charge_amount":
                try:
                    cleaned = val.replace("$", "").replace(",", "")
                    record[field] = Decimal(cleaned) if cleaned else Decimal("0")
                except Exception:
                    record[field] = Decimal("0")
            elif field == "call_date":
                record[field] = parse_date(val)
            else:
                record[field] = val
        records.append(record)
    return records


def parse_date(val: str) -> datetime | None:
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%Y %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None


def import_verizon_csv(
    db: Session,
    user_id: str,
    filename: str,
    raw_csv: str,
    column_mapping: dict | None = None,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> VerizonImport:
    records = parse_csv(raw_csv, column_mapping)

    total = sum(r.get("charge_amount", Decimal("0")) for r in records)

    imp = VerizonImport(
        user_id=user_id,
        filename=filename,
        raw_data=raw_csv,
        column_mapping=column_mapping or DEFAULT_COLUMN_MAP,
        period_start=period_start,
        period_end=period_end,
        total_amount=total,
    )
    db.add(imp)
    db.flush()

    for r in records:
        call = VerizonCallRecord(
            import_id=imp.id,
            user_id=user_id,
            phone_number=r.get("phone_number"),
            call_date=r.get("call_date"),
            duration_seconds=r.get("duration_seconds", 0),
            call_type=r.get("call_type"),
            charge_amount=r.get("charge_amount", Decimal("0")),
        )
        db.add(call)

    db.commit()
    db.refresh(imp)
    return imp


def preview_import(raw_csv: str, column_mapping: dict | None = None) -> dict:
    records = parse_csv(raw_csv, column_mapping)
    total = sum(r.get("charge_amount", Decimal("0")) for r in records)
    return {
        "record_count": len(records),
        "total_charges": float(total),
        "sample_records": records[:5],
        "columns_found": list(csv.DictReader(io.StringIO(raw_csv)).fieldnames or []),
    }
