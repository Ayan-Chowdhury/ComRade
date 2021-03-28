import sys
from datetime import datetime, time, timedelta

import numpy as np, matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.cm import ScalarMappable

from timetable import (load_timetable, sum_timetable, datetime_range)


if __name__ == '__main__':
    # Parse commandline arguments and build a dictionary of calendar names and
    # files.
    calendar_files = {}
    for arg in sys.argv[1:]:
        if not '=' in arg:
            print('Invalid argument %s' % arg)
            sys.exit(1)

        name, path = arg.split('=', 1)
        calendar_files[name] = path

    # Load timetable from calendar files.
    start = None
    end = datetime.now()
    timetable = load_timetable(calendar_files, clip_start=start, clip_end=end)

    # Select first and last date of the timetable.
    start = min(timetable, key=lambda e: e[0])[0].date()
    end = max(timetable, key=lambda e: e[1])[1].date()
    end += timedelta(days=1)

    days = list(datetime_range(datetime.combine(start, time()),
            datetime.combine(end, time()), timedelta(days=1)))
    daily_series = sum_timetable(timetable, days)

    # Plot cumulative sums.
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    base_y = np.zeros(len(days))
    handles = []
    colormap = ScalarMappable(cmap='Paired')
    colormap.set_clim(0, len(daily_series))
    for idx, name in enumerate(sorted(daily_series)):
        # Use a unique color based on the series index.
        color = colormap.to_rgba(idx)

        # Stack series cumulatively and plot them.
        y = base_y + np.cumsum(daily_series[name]) / 3600
        ax.fill_between(days, base_y, y, edgecolor='none', facecolor=color)
        base_y = y

        # Unfortunately fill_between() does not support labels. Create a proxy
        # handle for the legend.
        handles.append(Patch(color=color, label=name))

    fig.autofmt_xdate()
    ax.legend(loc='upper left', handles=handles)

    plt.show()
