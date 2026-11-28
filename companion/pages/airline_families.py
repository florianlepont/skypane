# SPDX-License-Identifier: AGPL-3.0-only
"""The human name of each aircraft picture slot (the families of
`illustrations.SHAPE_SLUGS`), English and French, for the Airlines editor.
`family_label(slug)` is the translated name, or "" for a slot with none (a
sub-type slot such as `a350-1000`)."""
import companion.i18n as i18n
from server.plane import illustrations

_ENGLISH = {
    'a320': 'Airbus A320',
    'b737': 'Boeing 737',
    'atr72': 'ATR 42 / 72',
    'beechcraft1900d': 'Beechcraft 1900D',
    'embraer': 'Embraer E-Jet',
    'a330': 'Airbus A330',
    'a350': 'Airbus A350',
    'erj145': 'Embraer ERJ 135/145',
    'b787': 'Boeing 787',
    'a220': 'Airbus A220',
    'b777': 'Boeing 777',
    'b747': 'Boeing 747',
    'b767': 'Boeing 767',
    'b757': 'Boeing 757',
    'a380': 'Airbus A380',
    'a300': 'Airbus A300 / A310',
    'crj': 'Bombardier CRJ',
    'falcon': 'Dassault Falcon',
    'bizjetlarge': 'Large business jet (Gulfstream / Global)',
    'bizjet': 'Business jet',
    'kingair': 'Beechcraft King Air',
    'pc12': 'Single turboprop (PC-12, TBM)',
    'helicopter': 'Helicopter (medium twin)',
    'gahigh': 'Light plane, high wing (Cessna)',
    'other': 'Other',
}

FAMILY_LABELS = {
    slug: i18n.msg("airlines.family_" + slug, english) for slug, english in _ENGLISH.items()}

OTHER_TYPE_LABEL = FAMILY_LABELS[illustrations.OTHER_SLUG]


def family_label(slug):
    message = FAMILY_LABELS.get(slug)
    return i18n.t(message) if message is not None else ""
