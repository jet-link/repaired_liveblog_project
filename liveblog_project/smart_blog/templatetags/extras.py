from django import template
from django.utils.html import strip_tags
from django.utils.text import Truncator


register = template.Library()


@register.filter(name='user_shadow_banned')
def user_shadow_banned(user):
    """True when score < 3: block comments and reply."""
    if not user or not user.is_authenticated or getattr(user, 'is_superuser', False):
        return False
    try:
        return getattr(user.profile, 'shadow_banned', False)
    except Exception:
        return False


@register.filter(name='user_cannot_create_post')
def user_cannot_create_post(user):
    """True when score < 5: block Create post (but allow comments if score >= 3)."""
    if not user or not user.is_authenticated or getattr(user, 'is_superuser', False):
        return False
    try:
        return not getattr(user.profile, 'can_post', True)
    except Exception:
        return False
@register.filter(name='excerpt_plain')
def excerpt_plain(value, num=500):
    if value is None:
        return ''
    # Удаляем HTML
    text = strip_tags(value)
    # заменяем NBSP на обычный пробел
    text = text.replace('\xa0', ' ').replace('&nbsp;', ' ')
    # аккуратно обрезаем
    return Truncator(text).chars(int(num), truncate=' …')


# --- Feed grid: row-based 1+3+2 / 3+1+2 / 3+2+1 (always fills rows) ---
_PATTERN_ROWS = (
    ("hero", "triple", "double"),
    ("triple", "hero", "double"),
    ("triple", "double", "hero"),
)

_ROW_SIZE = {"hero": 1, "triple": 3, "double": 2}


def _pack_tail(count: int) -> list[str]:
    """Pack remaining cards into full grid rows (12-col), no orphan gaps."""
    slots: list[str] = []
    n = count
    while n > 0:
        if n >= 3:
            if n == 4:
                slots.extend(["double", "double", "double", "double"])
                break
            if n == 5:
                slots.extend(["triple", "triple", "triple", "double", "double"])
                break
            slots.extend(["triple", "triple", "triple"])
            n -= 3
        elif n == 2:
            slots.extend(["double", "double"])
            break
        else:
            slots.append("hero")
            break
    return slots


def _append_row(slots: list[str], row_type: str) -> None:
    if row_type == "hero":
        slots.append("hero")
    elif row_type == "triple":
        slots.extend(["triple", "triple", "triple"])
    else:
        slots.extend(["double", "double"])


def _feed_grid_slots_for_total(total: int) -> tuple[str, ...]:
    total = max(int(total), 0)
    if total == 0:
        return ()

    # Short feeds: simple dense rows without a hero band.
    if total <= 4:
        return tuple(_pack_tail(total))

    slots: list[str] = []
    pattern_idx = 0
    row_idx = 0
    prev_hero = False

    while len(slots) < total:
        remaining = total - len(slots)
        row_type = _PATTERN_ROWS[pattern_idx % len(_PATTERN_ROWS)][row_idx % 3]
        need = _ROW_SIZE[row_type]

        # Skip hero when it would leave a orphan, or when two heroes would touch.
        if row_type == "hero" and (prev_hero or remaining <= 2):
            if remaining >= 3:
                row_type = "triple"
                need = 3
            else:
                slots.extend(_pack_tail(remaining))
                break

        if remaining < need:
            slots.extend(_pack_tail(remaining))
            break

        if row_type == "hero":
            _append_row(slots, "hero")
            prev_hero = True
        elif row_type == "triple":
            _append_row(slots, "triple")
            prev_hero = False
        else:
            _append_row(slots, "double")
            prev_hero = False

        row_idx += 1
        if row_idx % 3 == 0:
            pattern_idx += 1

    return tuple(slots[:total])


@register.simple_tag
def feed_grid_slot_class(counter, total):
    """Grid slot classes for item-card (forloop.counter, items|length)."""
    slots = _feed_grid_slots_for_total(total)
    idx = max(int(counter), 1) - 1
    if idx >= len(slots):
        return "feed-grid-slot feed-grid-slot--triple"
    kind = slots[idx]
    return f"feed-grid-slot feed-grid-slot--{kind}"

