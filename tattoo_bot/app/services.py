from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Booking, PortfolioPhoto, Slot, User


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    full_name: str | None,
) -> User:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    if user:
        user.username = username
        user.full_name = full_name
        return user
    user = User(telegram_id=telegram_id, username=username, full_name=full_name)
    session.add(user)
    await session.flush()
    return user


async def get_available_slots(session: AsyncSession) -> list[tuple[int, date]]:
    today = date.today()
    booked_slot_ids = select(Booking.slot_id)
    result = await session.execute(
        select(Slot.id, Slot.slot_date)
        .where(Slot.is_active.is_(True))
        .where(Slot.slot_date >= today)
        .where(Slot.id.not_in(booked_slot_ids))
        .order_by(Slot.slot_date)
    )
    return list(result.all())


async def user_has_booking_on_slot(
    session: AsyncSession, user_id: int, slot_id: int
) -> bool:
    result = await session.execute(
        select(Booking.id).where(
            Booking.user_id == user_id,
            Booking.slot_id == slot_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def slot_is_available(session: AsyncSession, slot_id: int) -> bool:
    result = await session.execute(
        select(Booking.id).where(Booking.slot_id == slot_id)
    )
    return result.scalar_one_or_none() is None


async def create_booking(
    session: AsyncSession,
    user_id: int,
    slot_id: int,
    client_name: str,
    phone: str,
) -> Booking:
    booking = Booking(
        user_id=user_id,
        slot_id=slot_id,
        client_name=client_name,
        phone=phone,
    )
    session.add(booking)
    await session.flush()
    return booking


async def get_slot_by_id(session: AsyncSession, slot_id: int) -> Slot | None:
    result = await session.execute(select(Slot).where(Slot.id == slot_id))
    return result.scalar_one_or_none()


async def get_all_bookings(session: AsyncSession) -> list[Booking]:
    result = await session.execute(
        select(Booking)
        .options(selectinload(Booking.user), selectinload(Booking.slot))
        .order_by(Booking.created_at.desc())
    )
    return list(result.scalars().all())


async def get_bookings_by_date(session: AsyncSession) -> dict[date, list[Booking]]:
    bookings = await get_all_bookings(session)
    grouped: dict[date, list[Booking]] = {}
    for b in bookings:
        d = b.slot.slot_date
        grouped.setdefault(d, []).append(b)
    return dict(sorted(grouped.items()))


async def get_clients_summary(session: AsyncSession) -> list[Booking]:
    return await get_all_bookings(session)


async def get_slots_with_counts(
    session: AsyncSession,
) -> list[tuple[int, date, int]]:
    result = await session.execute(
        select(Slot).where(Slot.is_active.is_(True)).order_by(Slot.slot_date)
    )
    slots = list(result.scalars().all())
    out: list[tuple[int, date, int]] = []
    for slot in slots:
        count_result = await session.execute(
            select(Booking.id).where(Booking.slot_id == slot.id)
        )
        count = len(list(count_result.all()))
        out.append((slot.id, slot.slot_date, count))
    return out


async def add_slot(session: AsyncSession, slot_date: date) -> Slot | None:
    existing = await session.execute(
        select(Slot).where(Slot.slot_date == slot_date)
    )
    slot = existing.scalar_one_or_none()
    if slot:
        if not slot.is_active:
            slot.is_active = True
            return slot
        return None
    slot = Slot(slot_date=slot_date, is_active=True)
    session.add(slot)
    await session.flush()
    return slot


async def delete_slot(session: AsyncSession, slot_id: int) -> bool:
    result = await session.execute(select(Slot).where(Slot.id == slot_id))
    slot = result.scalar_one_or_none()
    if not slot:
        return False
    bookings = await session.execute(
        select(Booking).where(Booking.slot_id == slot_id)
    )
    for booking in bookings.scalars():
        await session.delete(booking)
    await session.delete(slot)
    return True


async def get_portfolio(session: AsyncSession) -> list[PortfolioPhoto]:
    result = await session.execute(
        select(PortfolioPhoto).order_by(PortfolioPhoto.sort_order, PortfolioPhoto.id)
    )
    return list(result.scalars().all())


async def add_portfolio_photo(
    session: AsyncSession, file_id: str, caption: str | None
) -> PortfolioPhoto:
    result = await session.execute(select(PortfolioPhoto))
    count = len(list(result.scalars().all()))
    photo = PortfolioPhoto(file_id=file_id, caption=caption, sort_order=count)
    session.add(photo)
    await session.flush()
    return photo


async def clear_portfolio(session: AsyncSession) -> None:
    result = await session.execute(select(PortfolioPhoto))
    for photo in result.scalars():
        await session.delete(photo)
