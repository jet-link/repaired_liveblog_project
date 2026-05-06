import math
from django.utils.html import strip_tags
import re

def breadcrumb(title, url=None):
    return {
        "title": title,
        "url": url,
    }


def build_breadcrumbs(*crumbs):
    breadcrumbs = []
    if crumbs and crumbs[0].get("title") == "brainstorm.news":
        breadcrumbs.extend(crumbs)
    else:
        breadcrumbs = [breadcrumb("brainstorm.news", "/")]
        breadcrumbs.extend(crumbs)
    return breadcrumbs

def form_errors_to_json(form):
    """
    Преобразует form.errors и non_field_errors -> чистая JSON-структура:
    { 'errors': { field: [msg,...], ... }, 'non_field_errors': [msg,...] }
    """
    errors = {}
    for k, v in form.errors.items():
        # v — ErrorList, конвертируем в строки
        errors[k] = [str(m) for m in v]

    non_field = [str(m) for m in form.non_field_errors()]

    return {'errors': errors, 'non_field_errors': non_field}


def count_convert(n):
    if n < 1000:
        return str(n)
    for value, suffix in [(1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")]:
        if n >= value:
            res = n / value
            if res >= 10:
                return f"{int(res)}{suffix}"
            truncated = math.floor(res * 10) / 10
            return f"{truncated:.1f}".rstrip("0").rstrip('.') + suffix



def normalize_comment_text(text: str) -> str:
    if not text:
        return ""

    # 1. Удаляем HTML
    text = strip_tags(text)

    # 2. NBSP → пробел
    text = text.replace('\xa0', ' ').replace('&nbsp;', ' ')

    # 3. Нормализуем переводы строк
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # 4. Убираем пробелы в пустых строках
    lines = [line.rstrip() for line in text.split('\n')]

    # 5. Склеиваем обратно
    text = '\n'.join(lines)

    # 6. 🔥 Схлопываем любые множественные пустые строки → 1 перевод строки
    text = re.sub(r'\n\s*\n+', '\n', text)

    # 7. Убираем пустые строки в начале и конце
    return text.strip()


def strip_mention_tokens(text: str) -> str:
    if not text:
        return ""
    text = normalize_comment_text(text)
    # Remove @[user:ID] with optional ", " after (same token format as render_mentions)
    text = re.sub(r'@\[\s*user\s*:\s*\d+\s*\](?:,\s*)?', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def human_time_relative_youtube(dt, *, now=None):
    """
    Short relative labels similar to YouTube: Right now, N min ago, N hr ago, N mo ago, N yr ago.
    """
    from django.utils import timezone as dj_tz

    if dt is None:
        return ""
    if now is None:
        now = dj_tz.now()
    if dj_tz.is_naive(dt):
        dt = dj_tz.make_aware(dt, dj_tz.get_current_timezone())
    if dj_tz.is_naive(now):
        now = dj_tz.make_aware(now, dj_tz.get_current_timezone())

    delta = now - dt
    secs = int(delta.total_seconds())
    if secs < 0:
        return "Right now"
    if secs < 60:
        return "Right now"

    mins = secs // 60
    if mins < 60:
        return "1 min ago" if mins == 1 else f"{mins} min ago"

    hours = mins // 60
    if hours < 24:
        return "1 hr ago" if hours == 1 else f"{hours} hr ago"

    days = hours // 24
    if days < 7:
        return "1 day ago" if days == 1 else f"{days} days ago"

    if days < 30:
        wks = days // 7
        return "1 wk ago" if wks == 1 else f"{wks} wk ago"

    if days < 365:
        mo = max(1, days // 30)
        return "1 mo ago" if mo == 1 else f"{mo} mo ago"

    yrs = days // 365
    return "1 yr ago" if yrs == 1 else f"{yrs} yr ago"