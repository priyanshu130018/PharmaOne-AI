from pydantic import BaseModel


class CountByKey(BaseModel):
    key: str
    count: int


class DeviationReportSummary(BaseModel):
    """Aggregate view over persisted, user-reviewed deviations.

    Reports summarize saved final values, never unreviewed AI recommendations.
    """

    total: int
    by_status: list[CountByKey]
    by_severity: list[CountByKey]
    by_type: list[CountByKey]
