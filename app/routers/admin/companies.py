import csv
import io
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, require_admin
from app.models.company import Company, CompanyMember
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import register_user

router = APIRouter(prefix="/admin/companies", tags=["admin:companies"])


async def _get_company_or_404(
    db: AsyncSession, company_id: uuid.UUID, tenant_id: uuid.UUID
):
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.tenant_id == tenant_id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.get("")
async def list_companies(
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(None),
):
    query = select(Company).where(Company.tenant_id == tenant.id)
    if status:
        query = query.where(Company.status == status)
    result = await db.execute(query)
    rows = result.scalars().all()
    return {
        "items": [
            {
                "id": str(c.id),
                "cnpj": c.cnpj,
                "legal_name": c.legal_name,
                "trade_name": c.trade_name,
                "status": c.status,
                "max_seats": c.max_seats,
            }
            for c in rows
        ]
    }


@router.post("", status_code=201)
async def create_company(
    body: dict[str, Any],
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    company = Company(
        tenant_id=tenant.id,
        legal_name=body["legal_name"],
        cnpj=body.get("cnpj"),
        trade_name=body.get("trade_name"),
        max_seats=body.get("max_seats"),
        status=body.get("status", "active"),
    )
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return {"id": str(company.id), "legal_name": company.legal_name}


@router.get("/{company_id}")
async def get_company(
    company_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    company = await _get_company_or_404(db, company_id, tenant.id)
    return {
        "id": str(company.id),
        "cnpj": company.cnpj,
        "legal_name": company.legal_name,
        "trade_name": company.trade_name,
        "status": company.status,
        "max_seats": company.max_seats,
        "contract_start": company.contract_start.isoformat() if company.contract_start else None,
        "contract_end": company.contract_end.isoformat() if company.contract_end else None,
    }


@router.patch("/{company_id}")
async def update_company(
    company_id: uuid.UUID,
    body: dict[str, Any],
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    company = await _get_company_or_404(db, company_id, tenant.id)
    for field in ("legal_name", "trade_name", "cnpj", "max_seats", "status"):
        if field in body:
            setattr(company, field, body[field])
    await db.commit()
    await db.refresh(company)
    return {"id": str(company.id), "legal_name": company.legal_name}


@router.delete("/{company_id}", status_code=204)
async def delete_company(
    company_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    company = await _get_company_or_404(db, company_id, tenant.id)
    await db.delete(company)
    await db.commit()
    return


# ── Members ──────────────────────────────────────────────────────────────────


@router.get("/{company_id}/members")
async def list_members(
    company_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    _ = await _get_company_or_404(db, company_id, tenant.id)
    result = await db.execute(
        select(User, CompanyMember)
        .join(CompanyMember, CompanyMember.user_id == User.id)
        .where(CompanyMember.company_id == company_id)
    )
    rows = result.all()
    return {
        "items": [
            {
                "user_id": str(u.id),
                "email": u.email,
                "name": u.name,
                "role": u.role,
                "team": cm.team,
                "job_role": cm.job_role,
                "is_active": cm.is_active,
            }
            for u, cm in rows
        ]
    }


@router.post("/{company_id}/members/bulk-import")
async def bulk_import_members(
    company_id: uuid.UUID,
    file: UploadFile,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    _ = await _get_company_or_404(db, company_id, tenant.id)
    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    created = 0
    errors = []

    for idx, row in enumerate(reader, start=1):
        email = row.get("email", "").strip()
        name = row.get("name", "").strip() or email.split("@")[0]
        team = row.get("team", "").strip() or None
        job_role = row.get("job_role", "").strip() or None

        if not email:
            errors.append({"row": idx, "error": "Missing email"})
            continue

        try:
            # Check existing user
            result = await db.execute(
                select(User).where(User.tenant_id == tenant.id, User.email == email)
            )
            existing = result.scalar_one_or_none()
            if existing:
                user = existing
            else:
                user = await register_user(
                    db, tenant.id, email, name, f"TempPass{uuid.uuid4().hex[:8]}!",
                    role="student",
                )
                created += 1

            # Ensure company membership
            result = await db.execute(
                select(CompanyMember).where(
                    CompanyMember.company_id == company_id,
                    CompanyMember.user_id == user.id,
                )
            )
            if not result.scalar_one_or_none():
                member = CompanyMember(
                    company_id=company_id,
                    user_id=user.id,
                    team=team,
                    job_role=job_role,
                )
                db.add(member)
                await db.commit()
        except Exception as exc:
            errors.append({"row": idx, "error": str(exc)})

    return {"created": created, "errors": errors}


@router.post("/{company_id}/members/invite")
async def invite_member(
    company_id: uuid.UUID,
    body: dict[str, Any],
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    _ = await _get_company_or_404(db, company_id, tenant.id)
    email = body.get("email", "").strip()
    name = body.get("name", email.split("@")[0]).strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    result = await db.execute(
        select(User).where(User.tenant_id == tenant.id, User.email == email)
    )
    user = result.scalar_one_or_none()
    if not user:
        user = await register_user(
            db, tenant.id, email, name, f"TempPass{uuid.uuid4().hex[:8]}!", role="student"
        )

    result = await db.execute(
        select(CompanyMember).where(
            CompanyMember.company_id == company_id,
            CompanyMember.user_id == user.id,
        )
    )
    if not result.scalar_one_or_none():
        member = CompanyMember(
            company_id=company_id,
            user_id=user.id,
            team=body.get("team"),
            job_role=body.get("job_role"),
        )
        db.add(member)
        await db.commit()

    return {"user_id": str(user.id), "email": user.email}


@router.delete("/{company_id}/members/{user_id}", status_code=204)
async def remove_member(
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    _ = await _get_company_or_404(db, company_id, tenant.id)
    result = await db.execute(
        select(CompanyMember).where(
            CompanyMember.company_id == company_id,
            CompanyMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    await db.delete(member)
    await db.commit()
    return


# ── Reports ──────────────────────────────────────────────────────────────────


@router.get("/{company_id}/report")
async def company_report(
    company_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    company = await _get_company_or_404(db, company_id, tenant.id)

    # Count members
    result = await db.execute(
        select(CompanyMember).where(CompanyMember.company_id == company_id)
    )
    members = result.scalars().all()

    # Simple CSV output
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["company_id", "legal_name", "member_count"])
    writer.writerow([str(company.id), company.legal_name, len(members)])
    output.seek(0)

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=report-{company_id}.csv"
        },
    )
