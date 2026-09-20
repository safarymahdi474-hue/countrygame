from __future__ import annotations

import logging


def configure_logging(*, debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # کتابخونه‌های شلوغ رو ساکت‌تر می‌کنیم تا لاگ‌های خودمون گم نشن
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


def init_sentry(dsn: str | None) -> None:
    """
    اگه SENTRY_DSN ست نشده باشه، هیچ کاری نمی‌کنه — کاملاً اختیاریه.
    اگه sentry-sdk نصب نباشه هم فقط یه هشدار لاگ می‌شه، برنامه کرش نمی‌کنه.
    """
    if not dsn:
        return
    try:
        import sentry_sdk
    except ImportError:
        logging.getLogger(__name__).warning(
            "SENTRY_DSN ست شده ولی sentry-sdk نصب نیست — pip install sentry-sdk"
        )
        return

    sentry_sdk.init(dsn=dsn, traces_sample_rate=0.1)
    logging.getLogger(__name__).info("Sentry فعال شد.")
