import json
import re
import sys
import random
from collections import defaultdict

print("Loading JSON file...", flush=True)

input_file = '서울시 자치구별 도보 네트워크 공간정보.json'

with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

description = data.get('DESCRIPTION', {})
records = data.get('DATA', [])
print(f"Total records: {len(records)}", flush=True)

district_stats = defaultdict(lambda: {
    'sgg_cd': '',
    'node_count': 0,
    'link_count': 0,
    'total_link_len': 0.0,
    'all_node_coords': [],  # ALL node coordinates
    'coords': [],
    'emd_set': set(),
    'crosswalk_count': 0,
    'bridge_count': 0,
    'tunnel_count': 0,
    'subway_count': 0,
    'park_count': 0,
    'building_count': 0,
    'sample_links': [],
})

point_re = re.compile(r'POINT\(([\d.]+)\s+([\d.]+)\)')
line_re = re.compile(r'LINESTRING\(([^)]+)\)')

print("Processing records...", flush=True)

MAX_SAMPLE_LINKS = 500

for i, rec in enumerate(records):
    if i % 100000 == 0 and i > 0:
        print(f"  Processed {i}/{len(records)} records...", flush=True)
    
    sgg_nm = rec.get('sgg_nm', 'Unknown')
    stats = district_stats[sgg_nm]
    stats['sgg_cd'] = rec.get('sgg_cd', '')
    
    node_type = rec.get('node_type', '')
    
    if rec.get('emd_nm'):
        stats['emd_set'].add(rec['emd_nm'])
    
    if node_type == 'NODE':
        stats['node_count'] += 1
        wkt = rec.get('node_wkt', '')
        m = point_re.search(wkt)
        if m:
            lng, lat = float(m.group(1)), float(m.group(2))
            stats['coords'].append((lat, lng))
            stats['all_node_coords'].append([lat, lng])
    
    elif node_type == 'LINK':
        stats['link_count'] += 1
        lnkg_len = rec.get('lnkg_len')
        if lnkg_len is not None:
            try:
                stats['total_link_len'] += float(lnkg_len)
            except (ValueError, TypeError):
                pass
        
        if rec.get('crswk') == '1':
            stats['crosswalk_count'] += 1
        if rec.get('brg') == '1':
            stats['bridge_count'] += 1
        if rec.get('tnl') == '1':
            stats['tunnel_count'] += 1
        if rec.get('sbwy_ntw') == '1':
            stats['subway_count'] += 1
        if rec.get('park') == '1':
            stats['park_count'] += 1
        if rec.get('bldg') == '1':
            stats['building_count'] += 1
        
        if len(stats['sample_links']) < MAX_SAMPLE_LINKS:
            wkt = rec.get('lnkg_wkt', '')
            m = line_re.search(wkt)
            if m:
                coords_str = m.group(1)
                coords = []
                for pair in coords_str.split(','):
                    parts = pair.strip().split()
                    if len(parts) == 2:
                        lng, lat = float(parts[0]), float(parts[1])
                        coords.append([lat, lng])
                        stats['coords'].append((lat, lng))
                if coords:
                    stats['sample_links'].append(coords)

print("Computing bounding boxes and sampling nodes...", flush=True)

output = {
    'description': description,
    'districts': []
}

# Sample nodes per district for circle markers (max 150 per district for performance)
MAX_CIRCLE_NODES = 300

for sgg_nm, stats in sorted(district_stats.items()):
    if not stats['coords']:
        continue
    
    lats = [c[0] for c in stats['coords']]
    lngs = [c[1] for c in stats['coords']]
    
    center_lat = sum(lats) / len(lats)
    center_lng = sum(lngs) / len(lngs)
    
    # Sample node coordinates evenly
    all_nodes = stats['all_node_coords']
    if len(all_nodes) > MAX_CIRCLE_NODES:
        step = len(all_nodes) // MAX_CIRCLE_NODES
        sampled_nodes = all_nodes[::step][:MAX_CIRCLE_NODES]
    else:
        sampled_nodes = all_nodes
    
    district = {
        'name': sgg_nm,
        'sgg_cd': stats['sgg_cd'],
        'center': [center_lat, center_lng],
        'bounds': [[min(lats), min(lngs)], [max(lats), max(lngs)]],
        'node_count': stats['node_count'],
        'link_count': stats['link_count'],
        'total_elements': stats['node_count'] + stats['link_count'],
        'total_link_length_m': round(stats['total_link_len'], 2),
        'total_link_length_km': round(stats['total_link_len'] / 1000, 2),
        'emd_count': len(stats['emd_set']),
        'emd_names': sorted(list(stats['emd_set'])),
        'crosswalk_count': stats['crosswalk_count'],
        'bridge_count': stats['bridge_count'],
        'tunnel_count': stats['tunnel_count'],
        'subway_count': stats['subway_count'],
        'park_count': stats['park_count'],
        'building_count': stats['building_count'],
        'sample_links': stats['sample_links'],
        'sampled_nodes': sampled_nodes,
    }
    output['districts'].append(district)

output_file = 'processed_data.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=None)

print(f"\nOutput saved to {output_file}", flush=True)
print(f"Total districts: {len(output['districts'])}", flush=True)
total_sampled = 0
for d in output['districts']:
    total_sampled += len(d['sampled_nodes'])
    print(f"  {d['name']}: {len(d['sampled_nodes'])} sampled nodes, {d['total_elements']} elements, {d['total_link_length_km']}km", flush=True)
print(f"Total sampled nodes for circles: {total_sampled}", flush=True)
