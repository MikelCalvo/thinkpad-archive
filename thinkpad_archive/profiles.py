"""Strict factual profiles, separate from model/support catalogue identity."""
from datetime import date
from decimal import Decimal, InvalidOperation
import re

from .validation import fields, identifier, load_json, localized_text, require, text, url

FACT_KEYS = frozenset('processor display memory storage graphics weight dimensions ports connectivity battery operating_system positioning features'.split())
DATE_KINDS = frozenset(('announcement', 'availability', 'sku_announcement', 'documented_by'))
PRICE_KINDS = frozenset(('launch', 'catalogue', 'contemporary_review'))


def partial_date(value):
    text(value)
    require(re.fullmatch(r'\d{4}(?:-\d{2}(?:-\d{2})?)?', value) is not None, 'Invalid date precision')
    try:
        full = value + ('-01-01' if len(value) == 4 else '-01' if len(value) == 7 else '')
        parsed = date.fromisoformat(full)
        require(1900 <= parsed.year <= 2100, 'Date outside supported range')
    except ValueError:
        raise ValueError('Invalid calendar date') from None
    return value


def source_list(row, known):
    values = row['sources']
    require(type(values) is list and bool(values), 'Every fact requires sources')
    require(all(type(v) is str and v in known for v in values), 'Unknown profile reference')
    require(len(values) == len(set(values)), 'Repeated profile references')


def validate_profiles(payload, model_ids):
    fields(payload, 'schema_version profiles')
    require(type(payload['schema_version']) is int and payload['schema_version'] == 1, 'Unsupported profile schema')
    require(type(payload['profiles']) is list, 'Expected profiles')
    result = {}
    for profile in payload['profiles']:
        fields(profile, 'model_id summary context facts dates prices markets references')
        model_id = identifier(profile['model_id'])
        require(model_id in model_ids and model_id not in result, 'Unknown or duplicate profile model')
        for key in ('summary', 'context'):
            if profile[key] is not None:
                localized_text(profile[key])
        for key in ('facts', 'dates', 'prices', 'markets', 'references'):
            require(type(profile[key]) is list, 'Expected profile list')
        refs = set()
        for reference in profile['references']:
            fields(reference, 'id url title kind locator')
            ref_id = identifier(reference['id'])
            require(ref_id not in refs, 'Repeated profile reference')
            refs.add(ref_id)
            url(reference['url'])
            text(reference['title'])
            text(reference['locator'])
            require(reference['kind'] in ('official', 'community', 'press'), 'Unknown reference kind')
        require(bool(refs) or not any(profile[k] for k in ('summary','context','facts','dates','prices','markets')), 'Profile content requires references')
        fact_keys = set()
        for fact in profile['facts']:
            fields(fact, 'key value scope sources')
            require(fact['key'] in FACT_KEYS and fact['key'] not in fact_keys, 'Unknown or repeated fact key')
            fact_keys.add(fact['key'])
            localized_text(fact['value'])
            localized_text(fact['scope'])
            source_list(fact, refs)
        for row in profile['dates']:
            fields(row, 'date kind scope sources')
            partial_date(row['date'])
            require(row['kind'] in DATE_KINDS, 'Unknown date meaning')
            localized_text(row['scope'])
            source_list(row, refs)
        for row in profile['prices']:
            fields(row, 'amount currency kind date scope sources')
            require(type(row['amount']) is str and re.fullmatch(r'\d+(?:\.\d{1,4})?', row['amount']) is not None, 'Invalid price amount')
            try:
                require(Decimal(row['amount']).is_finite() and Decimal(row['amount']) > 0, 'Invalid price amount')
            except InvalidOperation:
                raise ValueError('Invalid price amount') from None
            require(type(row['currency']) is str and re.fullmatch('[A-Z]{3}', row['currency']) is not None, 'Invalid currency code')
            require(row['kind'] in PRICE_KINDS, 'Unknown historical price meaning')
            partial_date(row['date'])
            localized_text(row['scope'])
            source_list(row, refs)
        for row in profile['markets']:
            fields(row, 'exclusive scope sources')
            require(row['exclusive'] is None or type(row['exclusive']) is bool, 'Invalid exclusivity statement')
            localized_text(row['scope'])
            source_list(row, refs)
        result[model_id] = profile
    require(set(result) == set(model_ids), 'Every catalogue model requires a profile audit entry')
    return result


def load_profiles(path, model_ids):
    return validate_profiles(load_json(path), model_ids)


def format_date(value, lang):
    """Display only the precision the source actually provides."""
    partial_date(value)
    parts = [int(v) for v in value.split('-')]
    if len(parts) == 1:
        return str(parts[0])
    names = ('enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre'.split()
             if lang == 'es' else 'January February March April May June July August September October November December'.split())
    year, month = parts[:2]
    if len(parts) == 2:
        return names[month-1] + (' de ' if lang == 'es' else ' ') + str(year)
    day = parts[2]
    return str(day) + (' de ' if lang == 'es' else ' ') + names[month-1] + (' de ' if lang == 'es' else ' ') + str(year)
