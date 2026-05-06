"""
OpenAI-backed moderation layer for the admin Assistant analyzer.

Two complementary checks:
- ``openai_moderate(text)`` — calls the OpenAI Moderation endpoint
  (``omni-moderation-latest`` by default). Catches harassment / hate /
  sexual / violence / self-harm. Free, fast, fixed taxonomy.
- ``openai_classify(text, forbidden_words, forbidden_patterns)`` —
  calls Chat Completions (``gpt-4o-mini`` by default) with JSON output
  asking the model to flag the supplied custom blocklist plus general
  policy violations the moderation endpoint may miss.

If ``settings.OPENAI_API_KEY`` is empty, the package is missing or the
network call fails, both functions return ``(False, None, None)`` and
the deterministic checks (forbidden words / regex / abuse patterns)
remain fully responsible for moderation.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Iterable, Optional, Tuple

from django.conf import settings

logger = logging.getLogger(__name__)

# (found, reason, detected_word_or_excerpt)
ModerationResult = Tuple[bool, Optional[str], Optional[str]]

# OpenAI moderation category -> internal ContentViolation reason
_CATEGORY_TO_REASON = {
    'harassment': 'harassment',
    'harassment/threatening': 'harassment',
    'hate': 'harassment',
    'hate/threatening': 'abuse',
    'sexual': 'obscenity',
    'sexual/minors': 'abuse',
    'violence': 'abuse',
    'violence/graphic': 'abuse',
    'self-harm': 'abuse',
    'self-harm/intent': 'abuse',
    'self-harm/instructions': 'abuse',
    'illicit': 'other',
    'illicit/violent': 'abuse',
}

_VALID_REASONS = {'obscenity', 'spam', 'harassment', 'abuse', 'other'}

_client = None
_client_failed = False


def _get_client():
    """Lazy, cached OpenAI client. Returns ``None`` if key missing or SDK absent."""
    global _client, _client_failed
    if _client is not None:
        return _client
    if _client_failed:
        return None
    api_key = getattr(settings, 'OPENAI_API_KEY', '') or ''
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        logger.warning('openai package not installed; AI moderation disabled.')
        _client_failed = True
        return None
    try:
        _client = OpenAI(
            api_key=api_key,
            timeout=getattr(settings, 'OPENAI_REQUEST_TIMEOUT', 20.0),
        )
    except Exception as exc:
        logger.exception('Failed to construct OpenAI client: %s', exc)
        _client_failed = True
        return None
    return _client


def _truncate_for_ai(text: str) -> str:
    """Cap text by OPENAI_MAX_INPUT_CHARS, prefer breaking at whitespace."""
    if not text:
        return ''
    max_chars = int(getattr(settings, 'OPENAI_MAX_INPUT_CHARS', 8000) or 8000)
    if len(text) <= max_chars:
        return text
    chunk = text[:max_chars]
    last_space = chunk.rfind(' ')
    if last_space > max_chars * 0.85:
        chunk = chunk[:last_space]
    return chunk


def _is_rate_limit_error(exc: Exception) -> bool:
    """Best-effort detection of OpenAI rate-limit errors across SDK versions."""
    name = type(exc).__name__
    if name in ('RateLimitError', 'APIRateLimitError'):
        return True
    return getattr(exc, 'status_code', None) == 429


def _call_with_retry(call, *, retries: int = 2, base_delay: float = 1.0):
    """Run ``call()`` with exponential backoff on rate-limit errors."""
    attempt = 0
    while True:
        try:
            return call()
        except Exception as exc:
            if _is_rate_limit_error(exc) and attempt < retries:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    'OpenAI rate limit hit (attempt %s/%s); sleeping %.1fs',
                    attempt + 1, retries + 1, delay,
                )
                time.sleep(delay)
                attempt += 1
                continue
            raise


def _parse_moderation_result(result, threshold: float) -> ModerationResult:
    """Convert one OpenAI moderation result object into our (found, reason, detected) tuple."""
    try:
        categories = getattr(result, 'categories', None)
        scores = getattr(result, 'category_scores', None)
        cat_dict = categories.model_dump() if hasattr(categories, 'model_dump') else dict(categories or {})
        score_dict = scores.model_dump() if hasattr(scores, 'model_dump') else dict(scores or {})
    except Exception as exc:
        logger.warning('Unexpected OpenAI moderation result shape: %s', exc)
        return False, None, None

    flagged = getattr(result, 'flagged', False)

    best_category = None
    best_score = -1.0
    for cat, score in score_dict.items():
        try:
            value = float(score)
        except (TypeError, ValueError):
            continue
        if value > best_score:
            best_score = value
            best_category = cat

    if best_category is None:
        return False, None, None

    boolean_hit = bool(cat_dict.get(best_category) or flagged)
    if best_score >= threshold or boolean_hit:
        reason = _CATEGORY_TO_REASON.get(best_category, 'other')
        score_for_label = max(0.0, min(1.0, best_score if best_score > 0 else 1.0))
        detected = f'AI:{best_category}={score_for_label:.2f}'[:255]
        return True, reason, detected

    return False, None, None


def openai_moderate(text: str) -> ModerationResult:
    """Run OpenAI Moderation API on a single ``text``.

    Returns ``(found, reason, detected_word)`` where ``detected_word``
    has the ``AI:{category}={score:.2f}`` format already understood by
    ``ContentViolation.get_confidence_from_detected``.
    """
    if not text:
        return False, None, None
    results = batch_moderate([text])
    return results[0] if results else (False, None, None)


def batch_moderate(texts):
    """Run OpenAI Moderation API on a list of texts in chunks.

    The endpoint accepts a list as ``input`` and returns one result per
    text in the same order. Chunks are sized by ``OPENAI_BATCH_SIZE``.

    Returns a list of ``(found, reason, detected)`` tuples aligned to
    ``texts``. Empty texts and missing key/SDK yield ``(False, None, None)``.
    """
    n = len(texts)
    out = [(False, None, None)] * n
    if n == 0:
        return out
    client = _get_client()
    if client is None:
        return out

    threshold = float(getattr(settings, 'OPENAI_CONFIDENCE_THRESHOLD', 0.5) or 0.5)
    model = getattr(settings, 'OPENAI_MODERATION_MODEL', 'omni-moderation-latest')
    batch_size = max(1, int(getattr(settings, 'OPENAI_BATCH_SIZE', 32) or 32))

    # Pre-truncate; map non-empty payload indices to original indices so
    # we don't waste API quota on blank strings.
    payloads = [_truncate_for_ai(t or '') for t in texts]

    pending = [(i, p) for i, p in enumerate(payloads) if p]
    for chunk_start in range(0, len(pending), batch_size):
        chunk = pending[chunk_start:chunk_start + batch_size]
        chunk_indices = [i for i, _ in chunk]
        chunk_inputs = [p for _, p in chunk]
        try:
            response = _call_with_retry(
                lambda: client.moderations.create(model=model, input=chunk_inputs)
            )
        except Exception as exc:
            logger.warning(
                'OpenAI moderation batch failed (size=%s): %s',
                len(chunk_inputs), exc,
            )
            continue

        results = list(getattr(response, 'results', []) or [])
        # Defensive: if the SDK returns fewer results than inputs, we leave
        # the missing slots as the default no-violation tuple.
        for offset, item_idx in enumerate(chunk_indices):
            if offset >= len(results):
                break
            out[item_idx] = _parse_moderation_result(results[offset], threshold)

    return out


def _format_blocklist(forbidden_words, forbidden_patterns, *, word_limit: int = 200, pattern_limit: int = 50) -> str:
    """Render active blocklists into a compact text section for the prompt."""
    words = []
    for fw in forbidden_words or ():
        if not getattr(fw, 'is_active', True):
            continue
        word = (fw.word or '').strip()
        if word:
            words.append(word)
        if len(words) >= word_limit:
            break

    patterns = []
    for fp in forbidden_patterns or ():
        if not getattr(fp, 'is_active', True):
            continue
        pattern = (fp.pattern or '').strip()
        if pattern:
            patterns.append(pattern)
        if len(patterns) >= pattern_limit:
            break

    parts = []
    if words:
        parts.append('Forbidden words/phrases (case-insensitive substring or fuzzy match): ' + ', '.join(words))
    if patterns:
        parts.append('Forbidden regex patterns: ' + '; '.join(patterns))
    return '\n'.join(parts) if parts else '(no custom blocklist)'


def openai_classify(
    text: str,
    forbidden_words: Iterable = (),
    forbidden_patterns: Iterable = (),
) -> ModerationResult:
    """Run a Chat Completions classifier with custom blocklist context.

    The model is asked to return strict JSON
    ``{"violation": bool, "reason": str, "confidence": float, "excerpt": str}``.
    A violation is reported when ``violation=true`` AND
    ``confidence >= OPENAI_CONFIDENCE_THRESHOLD``.
    """
    if not text:
        return False, None, None
    client = _get_client()
    if client is None:
        return False, None, None

    model = getattr(settings, 'OPENAI_CLASSIFY_MODEL', 'gpt-4o-mini')
    threshold = float(getattr(settings, 'OPENAI_CONFIDENCE_THRESHOLD', 0.5) or 0.5)
    payload = _truncate_for_ai(text)
    blocklist = _format_blocklist(forbidden_words, forbidden_patterns)

    system_prompt = (
        'You are a strict content-moderation classifier for a public news/blog platform. '
        'Decide whether the provided content violates the platform rules. '
        'Treat as violations: obscenity/profanity, harassment, hate speech, threats, '
        'sexual content, violence/abuse, spam, scams, and any text that contains items '
        'from the supplied blocklist (including obfuscated forms). '
        'Reply with ONLY a JSON object using these exact keys: '
        '"violation" (boolean), '
        '"reason" (one of: obscenity, spam, harassment, abuse, other), '
        '"confidence" (float between 0 and 1, your certainty), '
        '"excerpt" (short quote from the text that triggered the decision, max 200 chars; empty string if no violation). '
        'Do not include any other keys, prose, or markdown.'
    )
    user_prompt = (
        f'{blocklist}\n\n'
        '---\n'
        'CONTENT TO CLASSIFY:\n'
        f'{payload}'
    )

    try:
        response = _call_with_retry(
            lambda: client.chat.completions.create(
                model=model,
                response_format={'type': 'json_object'},
                temperature=0,
                max_tokens=200,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
            )
        )
    except Exception as exc:
        logger.warning('OpenAI classify call failed: %s', exc)
        return False, None, None

    try:
        raw = response.choices[0].message.content or '{}'
        data = json.loads(raw)
    except (ValueError, AttributeError, IndexError) as exc:
        logger.warning('OpenAI classify returned non-JSON: %s', exc)
        return False, None, None

    is_violation = bool(data.get('violation'))
    if not is_violation:
        return False, None, None

    try:
        confidence = float(data.get('confidence', 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))
    if confidence < threshold:
        return False, None, None

    reason = (data.get('reason') or 'other').strip().lower()
    if reason not in _VALID_REASONS:
        reason = 'other'

    # Keep the canonical "AI:{label}={score}" token so
    # ContentViolation.get_confidence_from_detected can parse the score.
    # Excerpt is logged separately (analysis_run.log_lines), not stored
    # in detected_word, to avoid breaking score parsing.
    detected = f'AI:gpt={confidence:.2f}'
    return True, reason, detected[:255]
