"""
Functions for generating timetables from raw calendar components. See section
:ref:`timetable` for an explanation of timetables.
"""

from __future__ import absolute_import

from timetable import Recurrence, parse_datetime, timezone


def uidgroups_by_type(calendar, itemtype):
    """Selects all items of type *itemtype* in the *calendar* and groups
    them into a dictionary based on their UID."""
    items = {}

    for item in calendar.items:
        if item.type != itemtype:
            continue

        uid = item[b'uid'][0].value
        if not uid in items:
            items[uid] = []
        items[uid].append(item)

    return items


def generate_item_timetable(uid, group, timezones):
    """Generates a timetable for a calendar item. The item is given by its
    *uid* and a list of calendar components in *group*. It is required to
    supply the *timezones* of the calendar."""

    # Find first item without a RECURRENCE-ID entry.
    for main in group:
        if not b'recurrence-id' in main:
            break
    else:
        raise ValueError('Invalid item group with UID "%s"' % uid)

    start = parse_datetime(main[b'dtstart'][0], timezones)
    if start.tzinfo:
        start = start.astimezone(timezone.utc).replace(tzinfo=None)

    if not b'dtend' in main:
        # Events without a DTEND entry have no duration.
        end = start
    else:
        end = parse_datetime(main[b'dtend'][0], timezones)
        if end.tzinfo:
            end = end.astimezone(timezone.utc).replace(tzinfo=None)
    main_duration = end - start

    # Collect updates.
    to_insert = []
    to_remove = set()
    for item in group:
        # Ignore main item and items without RECURRENCE-ID entries.
        if item is main or b'recurrence-id' not in item:
            continue

        recur_dt = parse_datetime(item[b'recurrence-id'][0], timezones)
        if recur_dt.tzinfo:
            recur_dt = recur_dt.astimezone(timezone.utc).replace(
                    tzinfo=None)

        start = parse_datetime(item[b'dtstart'][0], timezones)
        if start.tzinfo:
            start = start.astimezone(timezone.utc).replace(tzinfo=None)
        end = parse_datetime(item[b'dtend'][0], timezones)
        if end.tzinfo:
            end = end.astimezone(timezone.utc).replace(tzinfo=None)

        to_insert.append((start, end, {'item': item}))
        to_remove.add(recur_dt)

    to_insert.sort(key=lambda e: e[0])

    for dt in Recurrence(main, timezones)():
        # FIXME What timezone to assume to naive datetimes (e.g. on daily
        # events)?
        if dt.tzinfo:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

        while to_insert and to_insert[0][0] < dt:
            yield to_insert.pop(0)

        if dt in to_remove:
            continue

        yield dt, dt + main_duration, {'item': main}
