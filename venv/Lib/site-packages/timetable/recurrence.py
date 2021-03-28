from __future__ import absolute_import

import time
from copy import copy
import calendar
from datetime import datetime, date, timedelta, tzinfo

from timetable import timezone


def expand_byday(byday, start, end):
    dt = start
    first_weekday = dt.weekday()
    days = (end - start).days

    selection = []
    for weekday, offsets in byday.items():
        ofs = (weekday - first_weekday) % 7
        weekdays = list(range(ofs, days, 7))
        if offsets is None:
            selection.extend(weekdays)
        else:
            for offset in offsets:
                if offset > 0:
                    selection.append(weekdays[offset - 1])
                else:
                    selection.append(weekdays[offset])

    for day in sorted(selection):
        yield start + timedelta(day)


def expand_bymonthday(bymonthday, dt):
    monthdays = calendar.monthrange(dt.year, dt.month)[1]
    selection = []
    for day in bymonthday:
        if day < 0:
            day = monthdays + day + 1

        if 0 < day <= monthdays:
            selection.append(day)

    for day in sorted(selection):
        yield date(dt.year, dt.month, day)


def limit_byday(byday, dt, start, end):
    if dt.weekday() not in byday:
        return False

    offsets = byday[dt.weekday()]
    if offsets is None:
        return True

    days = ((end - start).days - (-dt.weekday()) % 7) // 7
    dt_day = ((dt - start).days - (-dt.weekday()) % 7) // 7

    for offset in offsets:
        if offset > 0 and offset - 1 == dt_day:
            return True
        if offset < 0 and offset - days == dt_day:
            return True
    return False


def yearly(recur_start, start=None, bymonth=None, bymonthday=None,
        byday=None, interval=1):
    # Advance to first possible date based on start.
    dt = date(recur_start.year, 1, 1)
    if start is not None and start.year > dt.year:
        dt = date(dt.year + (dt.year - start.year) % interval, 1, 1)

    if bymonth and not bymonthday and not byday:
        while True:
            for month in bymonth:
                yield date(dt.year, month, recur_start.day)

            dt = date(dt.year + interval, 1, 1)
    elif bymonth and not bymonthday and byday:
        while True:
            for month in bymonth:
                dt = dt.replace(month=month)
                if dt.month < 12:
                    end = dt.replace(month=dt.month + 1)
                else:
                    end = dt.replace(year=dt.year + 1, month=1)

                for dt_day in expand_byday(byday, dt, end):
                    yield dt_day

            dt = date(dt.year + interval, 1, 1)
    elif bymonth and bymonthday and byday:
        while True:
            for month in bymonth:
                dt = dt.replace(month=month)
                if dt.month < 12:
                    end = date(dt.year, dt.month + 1, 1)
                else:
                    end = date(dt.year + 1, 1, 1)

                for dt_monthday in expand_bymonthday(bymonthday, dt):
                    if limit_byday(byday, dt_monthday, dt, end):
                        yield dt_monthday

            dt = date(dt.year + interval, 1, 1)
    elif not bymonth and not bymonthday and byday:
        while True:
            if dt.weekday() in byday:
                yield dt
            dt += delta
    elif not bymonth and not bymonthday and not byday:
        while True:
            yield dt
            dt += delta
    else:
        raise ValueError('Unsupported BY* combination for frequency YEARLY')


def monthly(recur_start, start=None, bymonth=None, bymonthday=None,
        byday=None, interval=1):
    # Advance to first possible date based on start.
    month = recur_start.year * 12 + recur_start.month - 1
    if start is not None and start > recur_start:
        month -= ((start.year * 12 + start.month - 1) - month) % interval

    delta = timedelta(days=7 * interval)

    if bymonth and not bymonthday and not byday:
        while True:
            if dt.month in bymonth:
                yield dt
            dt += delta
    elif not bymonth and bymonthday and not byday:
        while True:
            dt = date(month // 12, 1 + month % 12, 1)
            for dt_monthday in expand_bymonthday(bymonthday, dt):
                yield dt_monthday

            month += interval
    elif not bymonth and bymonthday and byday:
        while True:
            dt = date(month // 12, 1 + month % 12, 1)
            if dt.month < 12:
                end = date(dt.year, dt.month + 1, 1)
            else:
                end = date(dt.year + 1, 1, 1)

            for dt_monthday in expand_bymonthday(bymonthday, dt):
                if limit_byday(byday, dt_monthday, dt, end):
                    yield dt_monthday

            month += interval
    elif not bymonth and not bymonthday and byday:
        while True:
            dt = date(month // 12, 1 + month % 12, 1)
            end = date((month + 1) // 12, 1 + (month + 1) % 12, 1)
            for day in expand_byday(byday, dt, end):
                yield day

            month += interval
    elif not bymonth and not bymonthday and not byday:
        while True:
            dt = date(month // 12, 1 + month % 12, 1)
            yield dt
            month += interval
    else:
        raise ValueError('Unsupported BY* combination for frequency MONTHLY')


def weekly(recur_start, start=None, bymonth=None, bymonthday=None,
        byday=None, interval=1):
    # Advance to first possible date based on start.
    dt = recur_start
    if start is not None and start > recur_start:
        dt += timedelta(days=(recur_start - start).days % (7 * interval))

    delta = timedelta(days=7 * interval)

    if bymonth and not bymonthday and not byday:
        while True:
            if dt.month in bymonth:
                yield dt
            dt += delta
    elif not bymonth and not bymonthday and byday:
        start_ofs = timedelta(days=dt.weekday())
        end_ofs = timedelta(days=6 - dt.weekday())
        while True:
            for day in expand_byday(byday, dt - start_ofs, dt + end_ofs):
                yield day
            dt += delta
    elif not bymonthday and not bymonthday and not byday:
        while True:
            yield dt
            dt += delta
    else:
        raise ValueError('Unsupported BY* combination for frequency WEEKLY')


def daily(recur_start, start=None, bymonth=None, bymonthday=None,
        byday=None, interval=1):
    # Advance to first possible date based on start.
    dt = recur_start
    if start is not None and start > recur_start:
        dt += timedelta(days=(recur_start - start).days % interval)

    delta = timedelta(days=interval)

    if bymonth and not bymonthday and not byday:
        while True:
            if dt.month in bymonth:
                yield dt
            dt += delta
    elif not bymonth and not bymonthday and byday:
        while True:
            if dt.weekday() in byday:
                yield dt
            dt += delta
    elif not bymonth and not bymonthday and not byday:
        while True:
            yield dt
            dt += delta
    else:
        raise ValueError('Unsupported BY* combination for frequency DAILY')


class CombineTime(object):
    def __init__(self, recur_dt):
        self.recur_dt = recur_dt
        self.recur_time = recur_dt.timetz()

    def __call__(self, dates, start, end):
        if start is None or start <= self.recur_dt.date():
            start = self.recur_dt.date()
            # Always yield the start of the recurrence first.
            yield self.recur_dt

        for dt in dates:
            if dt <= start:
                continue

            if end is not None and dt > end:
                break

            yield datetime.combine(dt, self.recur_time)


class Count(object):
    def __init__(self, amount):
        self.amount = int(amount)

    def __call__(self, dates):
        for i, dt in enumerate(dates):
            if i >= self.amount:
                break
            yield dt


class Until(object):
    def __init__(self, recur_dt, until):
        until = until.decode('utf8')
        if len(until) > 8:
            if recur_dt.tzinfo is None:
                self.until = datetime.strptime(until[:14], '%Y%m%dT%H%M%S')
                self.until = self.until.replace(tzinfo=recur_dt.tzinfo)
            else:
                self.until = datetime.strptime(until, '%Y%m%dT%H%M%SZ')
                self.until = self.until.replace(tzinfo=timezone.utc)
        else:
            self.until = datetime(*time.strptime(until, '%Y%m%d')[:3])
            self.until = self.until.replace(tzinfo=recur_dt.tzinfo)
        self.until_date = self.until.date()

    def __call__(self, dates):
        for dt in dates:
            if dt.date() >= self.until_date and dt > self.until:
                # Compare dates first, this is more performant the a comparison
                # of offset aware datetimes.
                break

            yield dt


class RDate(object):
    def __init__(self, rdates, timezones):
        self.rdates = []
        for rdate in rdates:
            dt_type = rdate.attrs.get(b'VALUE', b'DATE-TIME')
            if dt_type is not b'DATE-TIME':
                raise ValueError('Only DATE-TIME values are supported in '
                        'RDATE')

            self.rdates.append(parse_datetime(rdate, timezones))
        self.rdates.sort()

    def __call__(self, dates):
        for dt in dates:
            while self.rdates and dt.date() > self.rdates[0].date():
                yield self.rdates.pop(0)

            if not self.rdates:
                yield dt
                break

            if dt.date() < self.rdates[0].date():
                yield dt

        for dt in dates:
            yield dt


class ExDate(object):
    def __init__(self, exdates, timezones):
        self.exdates = []
        for exdate in exdates:
            dt_type = exdate.attrs.get(b'VALUE', b'DATE-TIME')
            if dt_type is not b'DATE-TIME':
                raise ValueError('Only DATE-TIME values are supported in '
                        'EXDATE')

            self.exdates.append(parse_datetime(exdate, timezones))

    def __call__(self, dates):
        for dt in dates:
            while self.exdates and dt.date() > self.exdates[0].date():
                self.exdates.pop(0)

            if not self.exdates:
                yield dt
                break

            if dt.date() != self.exdates[0].date():
                yield dt

        for dt in dates:
            yield dt


class Recurrence(object):
    day_index = {n: i for i, n in enumerate(b'MO TU WE TH FR SA SU'.split())}
    frequencies = {
        b'YEARLY': yearly,
        b'MONTHLY': monthly,
        b'WEEKLY': weekly,
        b'DAILY': daily,
    }

    def __init__(self, item, timezones=None):
        recur_dt =  parse_datetime(item[b'dtstart'][0], timezones)
        self.recur_date = recur_dt.date()
        recur_time = recur_dt.timetz()

        self.recur = None
        self.limit = None
        rrule_entries = item[b'rrule']
        if rrule_entries:
            rrule = dict(part.split(b'=')
                    for part in rrule_entries[0].value.split(b';'))

            freq = rrule.pop(b'FREQ', None)
            if not freq:
                raise ValueError('Invalid RRULE, FREQ is not specified')
            self.interval = int(rrule.pop(b'INTERVAL', b'1'))

            self.bymonth = None
            if b'BYMONTH' in rrule:
                self.bymonth = sorted(int(m)
                        for m in rrule.pop(b'BYMONTH').split(b','))

            self.bymonthday = None
            if b'BYMONTHDAY' in rrule:
                self.bymonthday = sorted(int(d)
                        for d in rrule.pop(b'BYMONTHDAY').split(b','))

            self.byday = None
            if b'BYDAY' in rrule:
                self.byday = {}
                for day_spec in rrule[b'BYDAY'].split(b','):
                    day_idx = self.day_index[day_spec[-2:]]

                    if len(day_spec) == 2:
                        self.byday[day_idx] = None
                    else:
                        if day_idx not in self.byday:
                            self.byday[day_idx] = []
                        self.byday[day_idx].append(int(day_spec[:-2]))

            if freq not in self.frequencies:
                raise ValueError('Invalid RRULE: Unsupported FREQ %s' % freq)

            self.recur = self.frequencies[freq]

            if b'UNTIL' in rrule:
                self.limit = Until(recur_dt, rrule.pop(b'UNTIL'))

            if b'COUNT' in rrule:
                if self.limit is not None:
                    raise ValueError('Invalid RRULE, UNTIL and COUNT cannot be '
                            'specified at the same time')

                self.limit = Count(rrule.pop(b'COUNT'))

        self.combine = CombineTime(recur_dt)

        self.rdate = None
        rdate_entries = item[b'rdate']
        if rdate_entries:
            self.rdate = RDate(rdate_entries, timezones)

        self.exdate = None
        exdate_entries = item[b'exdate']
        if exdate_entries:
            self.exdate = ExDate(exdate_entries, timezones)

    def __call__(self, start=None, end=None):
        if self.recur:
            generator = self.recur(
                    self.recur_date, start, self.bymonth, self.bymonthday,
                    self.byday, self.interval)
        else:
            generator = (self.recur_date,)

        generator = self.combine(generator, start, end)
        if self.limit:
            generator = self.limit(generator)
        if self.rdate:
            generator = self.rdate(generator)
        if self.exdate:
            generator = self.exdate(generator)

        for dt in generator:
            yield dt


def parse_datetime(entry, timezones=None):
    dt_value = entry.attrs.get(b'value', b'DATE-TIME')
    entry_value = entry.value.decode('utf8')

    if dt_value == b'DATE-TIME':
        if entry_value.endswith('Z'):
            return datetime.strptime(entry_value, '%Y%m%dT%H%M%SZ').replace(
                    tzinfo=timezone.utc)

        timetuple = time.strptime(entry_value, '%Y%m%dT%H%M%S')
        if b'tzid' in entry.attrs:
            tz = timezones[entry.attrs[b'tzid']]
        else:
            tz = None
        return datetime(*timetuple[:6], tzinfo=tz)
    elif dt_value == b'DATE':
        return datetime.strptime(entry_value, '%Y%m%d')
    else:
        raise ValueError('Invalid date %s' % entry_value)


class iCalTimezone(tzinfo):
    def __init__(self, item):
        components = [c for c in item.items
            if c.type in (b'standard', b'daylight')]

        # TODO Cache observances by year.

        self.recurrences = []
        self.dst_info = []
        for comp in components:
            for entry in comp.entries:
                if entry.name == b'tzoffsetto':
                    s = entry.value
                    offsetto = int(s[:-2]) * 60 + int(s[-2:])
                elif entry.name == b'tzoffsetfrom':
                    s = entry.value
                    offsetfrom = int(s[:-2]) * 60 + int(s[-2:])

            self.recurrences.append(Recurrence(comp))
            self.dst_info.append((timedelta(minutes=offsetto),
                    timedelta(minutes=offsetto - offsetfrom),
                    str(comp[b'tzname'][0].value.decode('utf-8'))))

    def _lookup_component(self, dt):
        dt = dt.replace(tzinfo=None)
        start = date(dt.year - 1, 1, 1)
        end = dt.date()

        last_ocurrence = None
        for info, recurrence in zip(self.dst_info, self.recurrences):
            for ocurrence in recurrence(start, end):
                if ocurrence.date() >= end:
                    if ocurrence >= dt:
                        break

                if last_ocurrence is None or last_ocurrence < ocurrence:
                    last_ocurrence = ocurrence
                    last_info = info
        return last_info

    def utcoffset(self, dt):
        return self._lookup_component(dt)[0]

    def dst(self, dt):
        if comp.type != b'daylight':
            return timedelta(0)

        s = comp.values[b'tzoffsetto']
        offsetto = int(s[:-2]) * 60 + int(s[-2:])
        s = comp.values[b'tzoffsetfrom']
        offsetfrom = int(s[:-2]) * 60 + int(s[-2:])
        return timedelta(minutes=offsetto - offsetfrom)

    def tzname(self, dt):
        return self._lookup_component(dt)[2]
