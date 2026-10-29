"""Presentation-only grouping of explicit advertised operating-system labels."""
import re


def operating_system_groups(labels):
    """Group known spellings without changing source strings or inferring support."""
    groups = set()
    for label in labels:
        value = re.sub(r'^Microsoft\s+', '', label, flags=re.I)
        server = re.match(r'^Windows\s+Server\s*(2003|2008)(?=$|\s|\()', value, re.I)
        windows = re.match(r'^Windows\s+(8\.1|10|8|7|Vista|XP|2000|ME|NT|98|95)(?=$|\s|\()', value, re.I)
        if server:
            groups.add('Windows Server ' + server.group(1))
        elif windows:
            names = {'vista': 'Vista', 'xp': 'XP', 'me': 'ME', 'nt': 'NT'}
            version = windows.group(1)
            groups.add('Windows ' + names.get(version.lower(), version))
        else:
            # Unknown labels, OS Independent and generic source statements stay
            # literal; none is silently included under every named OS.
            groups.add(label)
    return sorted(groups, key=str.casefold)
