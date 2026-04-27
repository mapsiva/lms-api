"""Company business logic."""
import csv
import io
import uuid
from typing import Any

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.company import Company, CompanyMember
from app.models.user import User
from app.services.auth import register_user


async def list_companies(db: AsyncSession, tenant_id: uuid.UUID, status: str | None):
    query = select(Company).where(Company.tenant_id == tenant_id)
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


async def create_company(db: AsyncSession, tenant_id: uuid.UUID, body: dict[str, Any]):
    company = Company(
        tenant_id=tenant_id,
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


async def get_company(db: AsyncSession, company_id: uuid.UUID, tenant_id: uuid.UUID):
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.tenant_id == tenant_id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise AppError(ErrorCode.COMPANY_NOT_FOUND)
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


async def update_company(db: AsyncSession, company_id: uuid.UUID, tenant_id: uuid.UUID, body: dict[str, Any]):
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.tenant_id == tenant_id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise AppError(ErrorCode.COMPANY_NOT_FOUND)
    for field in ("legal_name", "trade_name", "cnpj", "max_seats", "status"):
        if field in body:
            setattr(company, field, body[field])
    await db.commit()
    await db.refresh(company)
    return {"id": str(company.id), "legal_name": company.legal_name}


async def delete_company(db: AsyncSession, company_id: uuid.UUID, tenant_id: uuid.UUID):
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.tenant_id == tenant_id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise AppError(ErrorCode.COMPANY_NOT_FOUND)
    await db.delete(company)
    await db.commit()


async def list_members(db: AsyncSession, company_id: uuid.UUID, tenant_id: uuid.UUID):
    # verify company exists
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.tenant_id == tenant_id)
    )
    if not result.scalar_one_or_none():
        raise AppError(ErrorCode.COMPANY_NOT_FOUND)

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


async def bulk_import_members(db: AsyncSession, company_id: uuid.UUID, tenant_id: uuid.UUID, file: UploadFile):
    # verify company exists
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.tenant_id == tenant_id)
    )
    if not result.scalar_one_or_none():
        raise AppError(ErrorCode.COMPANY_NOT_FOUND)

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
            result = await db.execute(
                select(User).where(User.tenant_id == tenant_id, User.email == email)
            )
            existing = result.scalar_one_or_none()
            if existing:
                user = existing
            else:
                user = await register_user(
                    db, tenant_id, email, name, f"TempPass{uuid.uuid4().hex[:8]}!",
                    role="student",
                )
                created += 1

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


async def invite_member(db: AsyncSession, company_id: uuid.UUID, tenant_id: uuid.UUID, body: dict[str, Any]):
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.tenant_id == tenant_id)
    )
    if not result.scalar_one_or_none():
        raise AppError(ErrorCode.COMPANY_NOT_FOUND)

    email = body.get("email", "").strip()
    name = body.get("name", email.split("@")[0]).strip()
    if not email:
        raise AppError(ErrorCode.EMAIL_REQUIRED)

    result = await db.execute(
        select(User).where(User.tenant_id == tenant_id, User.email == email)
    )
    user = result.scalar_one_or_none()
    if not user:
        user = await register_user(
            db, tenant_id, email, name, f"TempPass{uuid.uuid4().hex[:8]}!", role="student"
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


async def remove_member(db: AsyncSession, company_id: uuid.UUID, tenant_id: uuid.UUID, user_id: uuid.UUID):
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.tenant_id == tenant_id)
    )
    if not result.scalar_one_or_none():
        raise AppError(ErrorCode.COMPANY_NOT_FOUND)

    result = await db.execute(
        select(CompanyMember).where(
            CompanyMember.company_id == company_id,
            CompanyMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise AppError(ErrorCode.MEMBER_NOT_FOUND)
    await db.delete(member)
    await db.commit()


async def company_report(db: AsyncSession, company_id: uuid.UUID, tenant_id: uuid.UUID):
    from fastapi.responses import StreamingResponse

    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.tenant_id == tenant_id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise AppError(ErrorCode.COMPANY_NOT_FOUND)

    result = await db.execute(
        select(CompanyMember).where(CompanyMember.company_id == company_id)
    )
    members = result.scalars().all()

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
