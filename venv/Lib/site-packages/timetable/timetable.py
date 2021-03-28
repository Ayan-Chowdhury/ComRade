"""
Functions for timetable modification, for example merging, tagging and cutting
at specific dates.
"""

from __future__ import absolute_import

import re
from heapq import heappush, heappop
from datetime import timedelta
from itertools import count

from timetable import (parse_ical, iCalTimezone, Recurrence, parse_datetime,
        uidgroups_by_type, generate_item_timetable)


tag_pat_braces = re.compile('\[([^]]*)\] *')


def annotate_tags(tag_pat=tag_pat_braces, emptytag='misc'):
    """Returns an annotation function which parses the items summary for a tag.
    A tag is identified through the regular expression *tag_pat*. If no tag
    is found, *emptytag* is applied.

    .. note::

        The summary is assumed to be encoded as UTF-8.
    """
    def annotate(start, end, entry):
        summary = str(entry['item'][b'summary'][0].value.decode('utf-8'))
        match = tag_pat.search(summary)
        tag = ''
        if match:
            tag = match.group(1).strip()
        if not tag:
            tag = emptytag

        entry['tags'] = tag
    return annotate


def collect_keys(key='tags', collection='entries'):
    """Returns an annotation function which collects *key* from a *collection*.
    The resulting set of keys is added to the entries dictionary under the key
    *key*.

    This function is useful to extract tags from a merged timetable as returned
    by :func:`merge_intersections` for example.
    """
    def collect(start, end, entry):
        result = set()
        for item in entry[collection]:
            result.add(item[key])
        entry[key] = result
    return collect


def compute_duration(key='tags'):
    """Returns an annotation function which computes the duration of an entry.
    The duration is allocated equally for each *key* of the entry (e.g. divided
    by the amount of keys)."""
    def compute(start, end, entry):
        entry['duration'] = (end - start).total_seconds() / len(entry[key])
    return compute


def merge_timetables(timetables):
    """Generates a merged timetable from the given *timetables*. Entries are
    sorted by their start time."""
    # Force timetables into generators.
    timetables = [iter(timetable) for timetable in timetables]
    entry_id = count()
    pending = []
    for generator in timetables:
        try:
            start, end, entry = next(generator)
            heappush(pending, (start, next(entry_id), end, entry, generator))
        except StopIteration:
            pass

    while pending:
        cur_start, idx, cur_end, entry, generator = heappop(pending)
        yield cur_start, cur_end, entry

        try:
            start, end, entry = next(generator)
            if cur_start > start:
                raise RuntimeError('Input timetables are not sorted by start '
                                   'date')
            heappush(pending, (start, next(entry_id), end, entry, generator))
        except StopIteration:
            pass


def generate_timetable(calendar, itemtype=b'vevent'):
    """Generates a timetable from all items of type *itemtype* in the given
    *calendar*."""
    timezones = {}
    for item in calendar.items:
        if item.type == b'vtimezone':
            timezones[item[b'tzid'][0].value] = iCalTimezone(item)

    # Create generators for each item and let them be merged.
    return merge_timetables([
        generate_item_timetable(uid, group, timezones)
        for uid, group in uidgroups_by_type(calendar, itemtype).items()
    ])


def clip_timetable(timetable, clip_start=None, clip_end=None, pending=None):
    """Generates a timetable by clipping entries from the given *timetable*.
    Entries ending before *clip_start* are discarded as well as entries
    starting after *clip_end*. Start and end times of entries lying on the
    boundaries modified to match *clip_start* resp. *clip_end*. Entries on the
    *clip_end* are added to the list *pending*, if it is supplied."""
    if pending is None:
        pending = []

    idx = 0
    while idx < len(pending):
        start, end, value = pending[idx]

        # Clip entry.
        if clip_start is not None:
            if end <= clip_start:
                pending.pop(idx)
                continue
            if start < clip_start:
                start = clip_start

        if clip_end is not None:
            if start >= clip_end:
                break
            if end > clip_end:
                end = clip_end

        yield start, end, value

        if clip_end is not None and pending[0][1] > clip_end:
            idx += 1
        else:
            pending.pop(idx)

    # Process next entries.
    for entry in timetable:
        # Clip entry.
        start, end, value = entry
        if clip_start is not None:
            if end <= clip_start:
                continue
            if start < clip_start:
                start = clip_start

        if clip_end is not None:
            if start >= clip_end:
                pending.append(entry)
                break
            if end > clip_end:
                end = clip_end
                pending.append(entry)

        yield start, end, value


def cut_timetable(timetable, cuts=(None, None)):
    """Generates a timetable by cutting entries of *timetable* at the given
    *cuts* datetimes."""
    cuts = list(cuts)
    if len(cuts) < 2:
        raise ValueError('Expected at least two cut dates')

    # Convert timetable into an iterator.
    timetable = iter(timetable)

    pending = []
    for left_cut, right_cut in zip(cuts[:-1], cuts[1:]):
        yield clip_timetable(timetable, left_cut, right_cut, pending)


def annotate_timetable(timetable, *annotate_funcs):
    """Annotates all entries of *timetable* with the result of all
    *annotate_funcs*. The annotation functions must accept the arguments
    *start*, *end*, *entry*.
    """

    for start, end, entry in timetable:
        for annotate_func in annotate_funcs:
            annotate_func(start, end, entry)
        yield start, end, entry


def load_timetable(calendar_data, clip_start, clip_end,
        tag_pat=tag_pat_braces):
    """Loads and tags all events from the calendar files in the
    *calendar_files* dictionary. The keys in *calendar_files* are passed into
    :meth:`annotate_tags` as emptytag. The values in *calendar_files* are
    filenames to iCal calendars. All events are clipped to *clip_start* and
    *clip_end*."""
    calendars = {}
    for name, data in calendar_data.items():
        # FIXME Allows the iCal spec multiple calendars per file?
        calendars[name] = parse_ical(data)[0]

    return list(clip_timetable(merge_timetables([
            annotate_timetable(
                    generate_timetable(calendar),
                    annotate_tags(tag_pat=tag_pat_braces, emptytag=name))
            for name, calendar in calendars.items()
    ]), clip_start=clip_start, clip_end=clip_end))


def merge_intersection(entries, start, end):
    """Generates a non-overlapping timetable from *entries*. *start*
    and *end* limit the timespan for the intersection generation. The resulting
    timetable contains entry dictionaries with the single key ``entries``,
    whose value is the list of merged entries."""
    if start is None:
        return

    dts = set([evt[1] if evt[1] < end else end for evt in entries])
    dts.update([start, end])
    dts = sorted(dts)

    for start, end in zip(dts[:-1], dts[1:]):
        entries[:] = [evt for evt in entries if evt[1] > start]
        if not entries:
            continue
        yield start, end, {'entries': [evt[2] for evt in entries]}


def merge_intersections(timetable):
    """Generates a timetable with merged intersection of entries in
    *timetable*. The resulting timetable will only contain entries with a
    single key ``entries``, whose value is the list of the merged entries."""
    from_dt = None
    active = []
    # Generate intersections by jumping from start to start of events.
    for start, end, entry in timetable:
        if from_dt is not None:
            if start < from_dt:
                raise ValueError('Timetable is not sorted by start date')
            for intersection in merge_intersection(active, from_dt, start):
                yield intersection
        active.append((start, end, entry))
        from_dt = start

    # Generate left-over intersections.
    if active:
        end = max(entry[1] for entry in active)
        for intersection in merge_intersection(active, from_dt, end):
            yield intersection


def sum_timetable(timetable, cuts, key='tags'):
    """Computes a dictionary with timeseries of the activity for each *key*
    in the given *cuts*. The activity duration is distributed evenly if there
    are intersections."""
    cuts = list(cuts)
    sums = {}
    for idx, sub_timetable in enumerate(cut_timetable(timetable, cuts)):
        sub_timetable = merge_intersections(sub_timetable)
        sub_timetable = annotate_timetable(sub_timetable, collect_keys(key))
        for start, end, entry in sub_timetable:
            duration = (end - start).total_seconds() / len(entry[key])
            for name in entry[key]:
                if not name in sums:
                    sums[name] = [0] * (len(cuts))
                sums[name][idx + 1] += duration
    return sums
