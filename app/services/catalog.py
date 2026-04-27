import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.course import Course
from app.models.product import Product, ProductCourse
from app.schemas.catalog import CatalogCourseItem, CatalogProductDetail, CatalogProductListItem


async def list_catalog_products(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> list[CatalogProductListItem]:
    result = await db.execute(
        select(Product).where(
            Product.tenant_id == tenant_id,
            Product.status == "published",
            Product.visibility == "public",
        )
    )
    products = result.scalars().all()
    return [
        CatalogProductListItem(
            id=p.id,
            slug=p.slug,
            title=p.title,
            price=float(p.price) if p.price is not None else None,
            type=p.type,
            status=p.status,
        )
        for p in products
    ]


async def get_catalog_product(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    slug: str,
) -> CatalogProductDetail:
    result = await db.execute(
        select(Product).where(
            Product.tenant_id == tenant_id,
            Product.slug == slug,
            Product.status == "published",
            Product.visibility == "public",
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise AppError(ErrorCode.PRODUCT_NOT_FOUND)

    courses: list[CatalogCourseItem] = []
    if product.type in ("bundle", "trail"):
        stmt = (
            select(Course)
            .join(ProductCourse, ProductCourse.course_id == Course.id)
            .where(
                ProductCourse.product_id == product.id,
                Course.tenant_id == tenant_id,
            )
            .order_by(ProductCourse.order_index)
        )
        course_result = await db.execute(stmt)
        course_rows = course_result.scalars().all()
        courses = [
            CatalogCourseItem(
                id=c.id,
                title=c.title,
                slug=c.slug,
                thumbnail_url=c.thumbnail_url,
            )
            for c in course_rows
        ]

    return CatalogProductDetail(
        id=product.id,
        slug=product.slug,
        title=product.title,
        price=float(product.price) if product.price is not None else None,
        type=product.type,
        status=product.status,
        courses=courses,
    )
