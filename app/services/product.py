import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.community import Space
from app.models.course import Course
from app.models.product import Product, ProductCourse, ProductSpace
from app.schemas.product import (
    ProductCourseInput,
    ProductCourseItem,
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductSpaceInput,
    ProductSpaceItem,
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


async def _validate_spaces(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    spaces: list[ProductSpaceInput],
) -> None:
    if not spaces:
        return
    space_ids = {item.space_id for item in spaces}
    result = await db.execute(
        select(Space.id).where(Space.tenant_id == tenant_id, Space.id.in_(space_ids))
    )
    found = set(result.scalars().all())
    missing = space_ids - found
    if missing:
        raise AppError(
            ErrorCode.SPACE_NOT_FOUND,
            details=[{"space_id": str(sid)} for sid in sorted(missing, key=str)],
        )


async def _replace_product_spaces(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    spaces: list[ProductSpaceInput],
) -> None:
    await _validate_spaces(db, tenant_id, spaces)
    await db.execute(delete(ProductSpace).where(ProductSpace.product_id == product_id))
    for item in spaces:
        db.add(ProductSpace(product_id=product_id, space_id=item.space_id))


async def _serialize_product(db: AsyncSession, product: Product) -> ProductResponse:
    courses_result = await db.execute(
        select(ProductCourse)
        .where(ProductCourse.product_id == product.id)
        .order_by(ProductCourse.order_index)
    )
    spaces_result = await db.execute(
        select(ProductSpace).where(ProductSpace.product_id == product.id)
    )
    courses = courses_result.scalars().all()
    spaces = spaces_result.scalars().all()
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
        spaces=[ProductSpaceItem(space_id=item.space_id) for item in spaces],
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
    await _replace_product_spaces(db, tenant_id, product.id, data.spaces)
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
    spaces = update_data.pop("spaces", None)
    for field, value in update_data.items():
        setattr(product, field, value)
    if courses is not None:
        await _replace_product_courses(db, tenant_id, product.id, courses)
    if spaces is not None:
        await _replace_product_spaces(db, tenant_id, product.id, spaces)
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


async def list_product_spaces(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
) -> list[ProductSpaceItem]:
    await _get_product(db, tenant_id, product_id)
    result = await db.execute(
        select(ProductSpace).where(ProductSpace.product_id == product_id)
    )
    return [ProductSpaceItem(space_id=ps.space_id) for ps in result.scalars().all()]


async def add_product_space(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    space_id: uuid.UUID,
) -> list[ProductSpaceItem]:
    await _get_product(db, tenant_id, product_id)
    await _validate_spaces(db, tenant_id, [ProductSpaceInput(space_id=space_id)])
    existing = await db.execute(
        select(ProductSpace).where(
            ProductSpace.product_id == product_id,
            ProductSpace.space_id == space_id,
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(ProductSpace(product_id=product_id, space_id=space_id))
        await db.commit()
    return await list_product_spaces(db, tenant_id, product_id)


async def remove_product_space(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    space_id: uuid.UUID,
) -> None:
    await _get_product(db, tenant_id, product_id)
    result = await db.execute(
        select(ProductSpace).where(
            ProductSpace.product_id == product_id,
            ProductSpace.space_id == space_id,
        )
    )
    ps = result.scalar_one_or_none()
    if ps:
        await db.delete(ps)
        await db.commit()
