"""
Low-level functions to parse iCal data into an object representation.
"""


from io import BytesIO


def iter_entries(icalfile):
    entry = b''
    start = 0
    for lineno, line in enumerate(icalfile):
        if line[0:1] in (b' ', b'\t'):
            entry += line[1:].rstrip()
            continue

        if entry:
            end = lineno
            lineinfo = ('%d' % (start + 1)
                    if start == end else '%d-%d' % (start + 1, end + 1))
            yield lineinfo, entry
            start = lineno

        start = lineno
        entry = line.rstrip()

    yield lineinfo, entry


class Item(object):
    """Represents an iCal item."""

    def __init__(self, type=None):
        self.type = type
        self.entries = []
        self.items = []

    def __getitem__(self, key):
        return [entry for entry in self.entries if entry.name == key]

    def __contains__(self, key):
        for entry in self.entries:
            if entry.name == key:
                return True
        return False


class Entry(object):
    """Represents an iCal entry."""

    def __init__(self, name, attrs, value):
        self.name = name
        self.attrs = attrs
        self.value = value


def parse_ical(icalfile):
    """Parses the *icalfile* and returns a list of :class:`Item`. *icalfile*
    may be a :class:`str` or a file-like object."""
    if type(icalfile) in (str, bytes):
        icalfile = BytesIO(icalfile)

    root = Item(b'__root__')
    stack = [root]

    for lineinfo, entry in iter_entries(icalfile):
        key, value = entry.split(b':', 1)

        # Parse attributes.
        key_parts = key.split(b';')
        key = key_parts[0].lower()
        attrs = {}
        for attr in key_parts[1:]:
            attrkey, attrvalue = attr.split(b'=', 1)
            attrs[attrkey.lower()] = attrvalue

        # Unescape value.
        # TODO This is probably not the complete set of escape rules.
        value = value.replace(b'\\n', b'\n')
        value = value.replace(b'\\,', b',')

        if key == b'begin':
            item = Item(value.lower())
            stack[-1].items.append(item)
            stack.append(item)
        elif key == b'end':
            if stack[-1].type != value.lower():
                raise ValueError('Invalid END tag in line %s. Expected '
                        '%s but got %s' % (lineinfo, stack[-1].type,
                            value.lower()))

            stack.pop()
        else:
            stack[-1].entries.append(Entry(key, attrs, value))

    return root.items


if __name__ == '__main__':
    import sys
    from pprint import pprint

    with open(sys.argv[1]) as f:
        pprint(parse_ical(f))
