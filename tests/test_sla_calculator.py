from datetime import datetime, timezone
import pytest
from app.services.sla_service import SLAService


def test_is_working_time():
    # Monday 10:00 UTC (working day)
    mon_10am = datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc)
    assert SLAService.is_working_time(mon_10am) is True

    # Monday 13:30 UTC (lunch break)
    mon_lunch = datetime(2026, 9, 21, 13, 30, tzinfo=timezone.utc)
    assert SLAService.is_working_time(mon_lunch) is False

    # Monday 18:00 UTC (past work hours)
    mon_6pm = datetime(2026, 9, 21, 18, 0, tzinfo=timezone.utc)
    assert SLAService.is_working_time(mon_6pm) is False

    # Saturday 11:00 UTC (SHANBA ISH KUNI!)
    sat_11am = datetime(2026, 9, 26, 11, 0, tzinfo=timezone.utc)
    assert SLAService.is_working_time(sat_11am) is True

    # Sunday 14:00 UTC (Yakshanba - dam olish kuni)
    sun_2pm = datetime(2026, 9, 27, 14, 0, tzinfo=timezone.utc)
    assert SLAService.is_working_time(sun_2pm) is False

    # Holiday test: 2026-09-01 (Mustaqillik kuni)
    holiday_date = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
    assert SLAService.is_working_time(holiday_date, holidays={"2026-09-01"}) is False


def test_calculate_deadline_same_day():
    # Monday 10:00 UTC + 4 hours SLA -> with 13:00-14:00 lunch freeze, finishes same day at 15:00
    mon_start = datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc)
    deadline = SLAService.calculate_deadline(mon_start, sla_hours=4)
    assert deadline == datetime(2026, 9, 21, 15, 0, tzinfo=timezone.utc)


def test_calculate_deadline_spans_overnight():
    # Monday 15:00 UTC + 4 hours SLA
    # 2 hours on Mon (15:00-17:00), remaining 2 hours on Tue (09:00-11:00)
    mon_start = datetime(2026, 9, 21, 15, 0, tzinfo=timezone.utc)
    deadline = SLAService.calculate_deadline(mon_start, sla_hours=4)
    assert deadline == datetime(2026, 9, 22, 11, 0, tzinfo=timezone.utc)


def test_calculate_deadline_friday_to_saturday_work_day():
    # Friday 15:00 UTC + 4 hours SLA
    # Since Saturday is a working day, 2 hours Friday (15:00-17:00), remaining 2 hours on Saturday (09:00-11:00)
    fri_start = datetime(2026, 9, 25, 15, 0, tzinfo=timezone.utc)
    deadline = SLAService.calculate_deadline(fri_start, sla_hours=4)
    assert deadline == datetime(2026, 9, 26, 11, 0, tzinfo=timezone.utc)


def test_calculate_deadline_saturday_to_monday_sunday_freezes():
    # Saturday 15:00 UTC + 4 hours SLA
    # 2 hours on Saturday (15:00-17:00), Sunday freezes, remaining 2 hours on Monday (09:00-11:00)
    sat_start = datetime(2026, 9, 26, 15, 0, tzinfo=timezone.utc)
    deadline = SLAService.calculate_deadline(sat_start, sla_hours=4)
    assert deadline == datetime(2026, 9, 28, 11, 0, tzinfo=timezone.utc)


def test_calculate_deadline_skips_holidays():
    # Monday 15:00 UTC + 4 hours SLA, but Tuesday 2026-09-22 is a Holiday!
    # 2 hours on Monday (15:00-17:00), Tuesday holiday skipped, remaining 2 hours on Wednesday (09:00-11:00)
    mon_start = datetime(2026, 9, 21, 15, 0, tzinfo=timezone.utc)
    holidays = {"2026-09-22"}
    deadline = SLAService.calculate_deadline(mon_start, sla_hours=4, holidays=holidays)
    assert deadline == datetime(2026, 9, 23, 11, 0, tzinfo=timezone.utc)


def test_traffic_light_indicators():
    created = datetime(2026, 9, 21, 9, 0, tzinfo=timezone.utc)
    deadline = datetime(2026, 9, 21, 17, 0, tzinfo=timezone.utc)  # 8 hours total

    # 1. At 11:00 (2h elapsed out of 8h = 25%) -> GREEN
    time_25pct = datetime(2026, 9, 21, 11, 0, tzinfo=timezone.utc)
    assert SLAService.get_traffic_light(created, deadline, time_25pct) == "GREEN"

    # 2. At 14:00 (5h elapsed out of 8h = 62.5%) -> YELLOW
    time_62pct = datetime(2026, 9, 21, 14, 0, tzinfo=timezone.utc)
    assert SLAService.get_traffic_light(created, deadline, time_62pct) == "YELLOW"

    # 3. At 16:00 (7h elapsed out of 8h = 87.5%) -> RED
    time_87pct = datetime(2026, 9, 21, 16, 0, tzinfo=timezone.utc)
    assert SLAService.get_traffic_light(created, deadline, time_87pct) == "RED"

    # 4. At 18:00 (Overdue) -> RED
    time_overdue = datetime(2026, 9, 21, 18, 0, tzinfo=timezone.utc)
    assert SLAService.get_traffic_light(created, deadline, time_overdue) == "RED"
