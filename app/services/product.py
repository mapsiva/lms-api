import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.course import Course
from app.models.product import Product, ProductCourse
from app.schemas.product import (
    ProductCourseInput,
    ProductCourseItem,
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)


async def _get_product(db: AsyncSession, tenant_id: uuid.UUID, product_id: uuid.UUID) -> Product:
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise AppError(ErrorCode.PRODUCT_NOT_FOUND)
    return product


async def _validate_courses(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    courses: list[ProductCourseInput],
) -> None:
    if not courses:
        return
    course_ids = {item.course_id for item in courses}
    result = await db.execute(
        select(Course.id).where(Course.tenant_id == tenant_id, Course.id.in_(course_ids))
    )
    found = set(result.scalars().all())
    missing = course_ids - found
    if missing:
        raise AppError(
            ErrorCode.COURSE_NOT_FOUND,
            details=[
                {"course_id": str(course_id)}
                for course_id in sorted(missing, key=lambda value: str(value))
            ],
        )


async def _replace_product_courses(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    courses: list[ProductCourseInput],
) -> None:
    await _validate_courses(db, tenant_id, courses)
    await db.execute(delete(ProductCourse).where(ProductCourse.product_id == product_id))
    for item in courses:
        db.add(
            ProductCourse(
                product_id=product_id,
                course_id=item.course_id,
                order_index=item.order_index,
            )
        )


async def _serialize_product(db: AsyncSession, product: Product) -> ProductResponse:
    result = await db.execute(
        select(ProductCourse)
        .where(ProductCourse.product_id == product.id)
        .order_by(ProductCourse.order_index)
    )
    courses = result.scalars().all()
    return ProductResponse(
        id=product.id,
        type=product.type,
        title=product.title,
        slug=product.slug,
        status=product.status,
        visibility=product.visibility,
        price=float(product.price) if product.price is not None else None,
        gateway_ids=product.gateway_ids,
        access_days=product.access_days,
        is_free=product.is_free,
        courses=[
            ProductCourseItem(course_id=item.course_id, order_index=item.order_index)
            for item in courses
        ],
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


async def list_products(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    status: str | None = None,
) -> ProductListResponse:
    query = select(Product).where(Product.tenant_id == tenant_id)
    if status:
        query = query.where(Product.status == status)
    result = await db.execute(query.order_by(Product.created_at.desc()))
    products = result.scalars().all()
    return ProductListResponse(
        items=[await _serialize_product(db, product) for product in products]
    )


async def create_product(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    data: ProductCreate,
) -> ProductResponse:
    product = Product(
        tenant_id=tenant_id,
        type=data.type,
        title=data.title,
        slug=data.slug,
        status=data.status,
        visibility=data.visibility,
        price=data.price,
        gateway_ids=data.gateway_ids,
        access_days=data.access_days,
        is_free=data.is_free,
    )
    db.add(product)
    await db.flush()
    await _replace_product_courses(db, tenant_id, product.id, data.courses)
    await db.commit()
    await db.refresh(product)
    return await _serialize_product(db, product)


async def update_product(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    data: ProductUpdate,
) -> ProductResponse:
    product = await _get_product(db, tenant_id, product_id)
    update_data = data.model_dump(exclude_unset=True)
    courses = update_data.pop("courses", None)
    for field, value in update_data.items():
        setattr(product, field, value)
    if courses is not None:
        await _replace_product_courses(db, tenant_id, product.id, courses)
    await db.commit()
    await db.refresh(product)
    return await _serialize_product(db, product)


async def update_product_status(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    status: str,
) -> ProductResponse:
    product = await _get_product(db, tenant_id, product_id)
    product.status = status
    await db.commit()
    await db.refresh(product)
    return await _serialize_product(db, product)
