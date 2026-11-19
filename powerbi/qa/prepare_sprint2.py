"""Prepare demonstration roles and the reviewed phone layout.

Use --mobile-only to update phone formatting without rewriting model security.
"""
import argparse
import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare_model():
    path = ROOT / 'sales_dashboard.SemanticModel/model.bim'
    document = json.loads(path.read_text(encoding='utf-8'))
    model = document['model']
    model['roles'] = [
        {'name': 'Manager', 'modelPermission': 'read'},
        {'name': 'Brand Analyst', 'modelPermission': 'read', 'tablePermissions': [
            {'name': 'brand_sales_1m', 'filterExpression': "'brand_sales_1m'[brand] = \"apple\""},
            # The event aggregate has no brand grain; exposing it leaks other brands.
            {'name': 'event_metrics_30s', 'filterExpression': 'FALSE()'},
        ]},
    ]
    for table in model['tables']:
        for measure in table.get('measures', []):
            measure['displayFolder'] = 'Dashboard KPI'
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for path in (ROOT / 'sales_dashboard.Report/definition').rglob('visual.json'):
        text = path.read_text(encoding='utf-8').replace('Sprint 1 / TV4', 'Sprint 2 / TV4')
        path.write_text(text, encoding='utf-8')


def literal(value):
    return {'expr': {'Literal': {'Value': value}}}


def object_properties(**properties):
    return [{'properties': properties}]


def apply_mobile_layout():
    # 8 px outer gutter and gaps; paired cards have 150 px of usable width.
    # Each navigation button has a roughly 45 px touch area in the 2 x 2 grid.
    layouts = {
        'overview': [
            (('heading',), 44), (('navigation',), 100), (('run_slicer',), 60),
            (('value', 'purchases'), 88), (('views', 'ratio'), 88),
            (('time_slicer',), 96), (('purchase_trend',), 228),
            (('event_mix',), 228), (('scope',), 36),
        ],
        'monitoring': [
            (('heading',), 44), (('navigation',), 100), (('run_slicer',), 60),
            (('total', 'purchases'), 88), (('window',), 76), (('age',), 76),
            (('time_slicer',), 96), (('event_slicer',), 60),
            (('event_trend',), 248), (('refresh_note',), 92), (('scope',), 36),
        ],
        'brands': [
            (('heading',), 44), (('navigation',), 100), (('run_slicer',), 60),
            (('brand_slicer',), 60), (('brand_value', 'brand_purchases'), 88),
            (('time_slicer',), 96), (('brand_ranking',), 276),
            (('brand_table',), 292), (('scope',), 36),
        ],
        'behavior': [
            (('heading',), 44), (('navigation',), 100), (('run_slicer',), 60),
            (('views', 'purchases'), 88), (('carts', 'removals'), 88),
            (('time_slicer',), 96), (('behavior_mix',), 228),
            (('ratio_trend',), 248), (('scope',), 36),
        ],
    }
    headings = {
        'overview': 'Sales overview', 'monitoring': 'Live monitoring',
        'brands': 'Brand performance', 'behavior': 'Customer behavior',
    }
    titles = {
        'value': 'Value / source unit', 'purchases': 'Purchases', 'views': 'Views',
        'ratio': 'Purchase / view', 'carts': 'Carts', 'removals': 'Removals',
        'total': 'Total events', 'window': 'Latest window / UTC',
        'age': 'Window age / seconds', 'brand_value': 'Value / source unit',
        'brand_purchases': 'Purchases', 'run_slicer': 'Run',
        'time_slicer': 'Time window / UTC', 'brand_slicer': 'Brand',
        'event_slicer': 'Event type', 'purchase_trend': 'Purchase value over time',
        'event_mix': 'Events by type', 'event_trend': 'Events over time',
        'behavior_mix': 'Event counts', 'ratio_trend': 'Cart / view & purchase / view',
        'brand_ranking': 'Purchase value by brand', 'brand_table': 'Brand details',
    }
    for page, rows in layouts.items():
        y, order = 8, 0
        for names, height in rows:
            width = (308 - 8 * (len(names) - 1)) / len(names)
            for column, name in enumerate(names):
                folder = ROOT / f'sales_dashboard.Report/definition/pages/{page}/visuals/{name}'
                desktop = json.loads((folder / 'visual.json').read_text(encoding='utf-8'))['visual']
                mobile = {
                    '$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainerMobileState/2.8.0/schema.json',
                    'position': {'x': 8 + column * (width + 8), 'y': y, 'z': order,
                                 'height': height, 'width': width, 'tabOrder': order},
                }
                objects, container = {}, {}
                if name in titles:
                    container['title'] = object_properties(
                        text=literal("'" + titles[name] + "'"), fontSize=literal('10D'))
                if name == 'heading':
                    objects = {'general': object_properties(paragraphs=[{'textRuns': [{
                        'value': headings[page], 'textStyle': {
                            'fontFamily': 'Segoe UI', 'fontWeight': 'bold',
                            'fontSize': '17pt', 'color': '#142d4e',
                        },
                    }]}])}
                elif name == 'navigation':
                    # These properties are serialized by Desktop's Grid layout editor.
                    objects['layout'] = object_properties(
                        orientation=literal('0D'), rowCount=literal('2L'),
                        columnCount=literal('2L'))
                elif name == 'refresh_note':
                    objects = {'general': object_properties(paragraphs=[{'textRuns': [{
                        'value': 'Window age shows data freshness, not end-to-end latency. Auto refresh on the Service depends on workspace settings.',
                        'textStyle': {'fontFamily': 'Segoe UI', 'fontSize': '10pt', 'color': '#61718a'},
                    }]}])}
                elif desktop['visualType'] == 'card':
                    size = 19 if name in ('value', 'brand_value') else 14 if name == 'window' else 10 if name == 'scope' else 23
                    objects['labels'] = object_properties(fontSize=literal(f'{size}D'))
                elif desktop['visualType'] == 'slicer':
                    objects['items'] = object_properties(textSize=literal('11D'))
                    if name in ('brand_slicer', 'event_slicer'):
                        objects['data'] = object_properties(mode=literal("'Dropdown'"))
                elif desktop['visualType'] in ('lineChart', 'clusteredColumnChart', 'clusteredBarChart'):
                    for axis in ('categoryAxis', 'valueAxis'):
                        objects[axis] = object_properties(fontSize=literal('9D'), showAxisTitle=literal('false'))
                    if name == 'brand_ranking':
                        objects['categoryAxis'][0]['properties']['concatenateLabels'] = literal('true')
                    if name == 'ratio_trend':
                        objects['legend'] = object_properties(fontSize=literal('9D'), position=literal("'Bottom'"))
                        # Desktop's per-series mobile color override: orange versus teal.
                        objects['dataPoint'] = [{
                            'properties': {'fill': {'solid': {'color': {'expr': {
                                'ThemeDataColor': {'ColorId': 4, 'Percent': 0},
                            }}}}},
                            'selector': {'metadata': 'event_metrics_30s.Purchase To View Ratio'},
                        }]
                elif desktop['visualType'] == 'tableEx':
                    objects['grid'] = object_properties(textSize=literal('9D'), rowPadding=literal('6D'))
                    objects['columnHeaders'] = object_properties(fontSize=literal('9D'), wordWrap=literal('true'))
                    objects['values'] = object_properties(fontSize=literal('9D'))
                    objects['columnWidth'] = [
                        {'properties': {'value': literal(f'{width}D')}, 'selector': {'metadata': field}}
                        for field, width in (
                            ('brand_sales_1m.brand', 72),
                            ('event_metrics_30s.Brand Purchase Events', 58),
                            ('event_metrics_30s.Brand Purchase Value', 88),
                            ('event_metrics_30s.Brand Value Share', 68),
                        )
                    ]
                if objects:
                    mobile['objects'] = deepcopy(objects)
                if container:
                    mobile['visualContainerObjects'] = container
                (folder / 'mobile.json').write_text(json.dumps(mobile, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                order += 1
            y += height + 8
        print(f'{page}: {order} visuals, {y}px phone canvas')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mobile-only', action='store_true', help='Update only mobile layout and formatting')
    args = parser.parse_args()
    if not args.mobile_only:
        prepare_model()
    apply_mobile_layout()


if __name__ == '__main__':
    main()
