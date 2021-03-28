"""Utility functions."""

def datetime_range(start, end, step):
    """Generates dates from *start* (inclusive) to *end* (exclusive) with the
    given *step*."""
    dt = start
    while dt < end:
        yield dt
        dt += step
