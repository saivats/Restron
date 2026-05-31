PLAN_LIMITS = {
    "trial": {
        "duration_days": 15,
        "max_tables": 15,
        "max_staff": 5,
        "features": ["qr_ordering", "kitchen_display", "analytics", "csv_import"],
    },
    "starter": {
        "duration_days": None,
        "max_tables": 15,
        "max_staff": 5,
        "features": ["qr_ordering", "kitchen_display", "analytics", "csv_import"],
    },
    "growth": {
        "duration_days": None,
        "max_tables": 20,
        "max_staff": 20,
        "features": ["qr_ordering", "kitchen_display", "analytics", "csv_import", "advanced_reports"],
    },
    "pro": {
        "duration_days": None,
        "max_tables": None,
        "max_staff": None,
        "features": [
            "qr_ordering",
            "kitchen_display",
            "analytics",
            "csv_import",
            "advanced_reports",
            "custom_branding",
            "priority_support",
        ],
    },
}


def limits_for_plan(plan: str | None) -> dict:
    return PLAN_LIMITS.get(plan or "trial", PLAN_LIMITS["trial"])
