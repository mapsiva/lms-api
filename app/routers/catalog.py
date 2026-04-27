"""Public product catalog (no auth required)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant
from app.models.course import Course
from app.models.product import Product, ProductCourse
from app.models.tenant import Tenant

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("")
async def list_catalog(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(
            Product.tenant_id == tenant.id,
            Product.status == "published",
            Product.visibility == "public",
        )
    )
    products = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "slug": p.slug,
            "title": p.title,
            "price": float(p.price) if p.price is not None else None,
            "type": p.type,
            "status": p.status,
        }
        for p in products
    ]


@router.get("/{slug}")
async def get_catalog_product(
    slug: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(
            Product.tenant_id == tenant.id,
            Product.slug == slug,
            Product.status == "published",
            Product.visibility == "public",
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    courses = []
    if product.type in ("bundle", "trail"):
        stmt = (
            select(Course)
            .join(ProductCourse, ProductCourse.course_id == Course.id)
            .where(
                ProductCourse.product_id == product.id,
                Course.tenant_id == tenant.id,
            )
            .order_by(ProductCourse.order_index)
        )
        course_result = await db.execute(stmt)
        course_rows = course_result.scalars().all()
        courses = [
            {
                "id": str(c.id),
                "title": c.title,
                "slug": c.slug,
                "thumbnail_url": c.thumbnail_url,
            }
            for c in course_rows
        ]

    return {
        "id": str(product.id),
        "slug": product.slug,
        "title": product.title,
        "price": float(product.price) if product.price is not None else None,
        "type": product.type,
        "status": product.status,
        "courses": courses,
    }
