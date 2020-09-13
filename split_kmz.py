import json, os, shutil, time
from copy import deepcopy
from math import *
import numpy as np
from zipfile import ZipFile

import geopy
from geopy.distance import geodesic

OGR2OGR = "C:\\OSGeo4W64\\bin\\ogr2ogr.exe"



def get_file_properties(ge_file):
    """returns Google Earth file extension, the base file name, directory,
    and a timestamp string used for craeting unique names
    """

    extension = ge_file.split('.')[-1]
    filename = os.path.split(ge_file)[1].split('.')[0]
    directory = os.path.split(ge_file)[0]
    timestamp = str(time.time()).replace('.', '')
    return extension, filename, directory, timestamp


def kmz_to_kml(ge_file):
    """extracts KML from KMZ"""

    kmz_copy = os.path.join(directory, '{}_{}.kmz'.format(filename, timestamp))
    shutil.copyfile(ge_file, kmz_copy)

    # save KMZ as .zip archive
    zipped = os.path.join(directory, '{}.zip'.format(timestamp))
    os.rename(kmz_copy, zipped)
    
    # extract contents of .zip archive
    with ZipFile(zipped, 'r') as ref:
        ref.extractall(directory)

    # saves root KML as XML
    root_kml = os.path.join(directory, 'doc.kml')
    kml = os.path.join(directory, '{}.kml'.format(filename))
    os.rename(root_kml, kml)
    return kml


def kml_to_json(kml):
    """converts KML to GeoJSON with ogr2ogr; output file is saved with .json
    extension to avoid parsing/driver issues
    """

    output_json = os.path.join(directory, ('{}.json').format(filename))
    cmd = '{} -f "GeoJSON" {} {} -nln "{}"'.format(OGR2OGR, output_json, kml, filename)
    os.system(cmd)
    return output_json


def extract_features(output_json):
    """Extracts features from GeoJSON; polylines and points are returned separately;
    extracted features include geometry and attribute information
    """

    f = open(output_json, 'r')
    data = json.load(f)
    f.close()

    features = data['features']
    points = [f for f in features if f['geometry']['type'] == 'Point']
    [polylines] = [f for f in features if f['geometry']['type'] == 'LineString']
    return points, polylines, data


def remove_temp_files(directory):
    """deletes all intermediate files"""

    extensions = ['zip', 'json', 'kml']
    for f in os.listdir(directory):
        if f.split('.')[-1] in extensions:
            temp_file = os.path.join(directory, f)
            os.remove(temp_file)


def enumerate_linestring(polyline):
    """Extracts vertex coordinates from polyline and assigns sequential IDs to
    each coordinate pair
    """

    coordinates = polyline['geometry']['coordinates']
    linestring = dict(enumerate(coordinates))
    linestring = {k + 1: {'lon': v[0], 'lat': v[1], 'HH': False} for k, v in linestring.iteritems()}
    return linestring


def calculate_bearing(lat1, lon1, lat2, lon2):
    """calculates bearing between two points using the Haversine
    formula; bearings returned in degrees and rounded to the nearest hundredth
    """

    bearing = atan2(sin(lon2-lon1)*cos(lat2), cos(lat1)*sin(lat2)-sin(lat1)*cos(lat2)*cos(lon2-lon1))
    bearing = round(degrees(bearing), 1)
    return bearing


def find_excess_vertices(densified_linestring):
    """identifies excess vertices from polylines by comparing the bearing from
    each component vertex to the next vertex to that of the previous
    """

    endpoint = max(densified_linestring.keys())
    terminal_pts = [1, endpoint]
    for i, vertex in densified_linestring.iteritems():
        if i not in terminal_pts:
            lat1 = vertex['lat']
            lon1 = vertex['lon']

            next_point = densified_linestring[i + 1]
            to_lat = next_point['lat']
            to_lon = next_point['lon']
            bearing1 = calculate_bearing(lat1, lon1, to_lat, to_lon)
            vertex['bearing1'] = bearing1

            previous_point = densified_linestring[i - 1]
            from_lat = previous_point['lat']
            from_lon = previous_point['lon']
            bearing2 = calculate_bearing(lat1, lon1, from_lat, from_lon)
            vertex['bearing2'] = bearing2

    for i, vertex in densified_linestring.iteritems():
        if i not in terminal_pts:
            try:
                next_point = densified_linestring[i + 1]
                previous_point = densified_linestring[i - 1]
                check1 = vertex['bearing1'] == next_point['bearing1'] == previous_point['bearing1']
                check2 = vertex['bearing2'] == next_point['bearing2'] == previous_point['bearing2']
                if (check1 and check2) and not vertex['HH']:
                    excess = True
                else:
                    excess = False
            except:
                excess = False
        else:
            excess = False
        vertex['excess'] = excess

            
def haversine_distance(lat1, lon1, lat2, lon2):
    """calculates the distance in feet between two coordinate pairs;
    adapted from https://towardsdatascience.com/heres-how-to-calculate-distance-between-2-geolocations-in-python-93ecab5bbba4
    """

    r = 20902231
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)

    delta_y = lat2 - lat1
    delta_phi = np.radians(delta_y)

    delta_x = lon2 - lon1
    delta_lambda = np.radians(delta_x)

    a = np.sin(delta_phi / 2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2)**2
    delta_a = 1-a
    res = r * (2 * np.arctan2(np.sqrt(a), np.sqrt(delta_a)))
    return round(res, 3)


def check_topology(linestring, points, tolerance=0):
    """checks if handholes/splices are coincident with existing route vertices;
    finds the two nearest vertices to each handhole
    """

    handholes = len(points)
    coincident_pts = 0
    for point in points:
        pt_distances = {}
        coords = point['geometry']['coordinates']
        hh_lon = coords[0]
        hh_lat = coords[1]

        for i, vertex in linestring.iteritems():
            v_lon = vertex['lon']
            v_lat = vertex['lat']
            distance = haversine_distance(hh_lat, hh_lon, v_lat, v_lon)
            pt_distances[i] = distance
            if distance <= tolerance or (hh_lat == v_lat and hh_lon == v_lon):
                coincident_pts += 1
                point['properties']['Coincident'] = True
                vertex['HH'] = True
            else:
                point['properties']['Coincident'] = False
        
        distances = pt_distances.values()
        near1 = [k for k, v in pt_distances.iteritems() if v == min(distances)]
        k1 = near1[0]
        near1_lon = linestring[k1]['lon']
        near1_lat = linestring[k1]['lat']
        point['properties']['Near1'] = {
            'vertex_id': k1, 'lon': near1_lon, 'lat': near1_lat}
        if len(near1) > 1:
            k2 = near1[1]
            near2_lon = linestring[k2]['lon']
            near2_lat = linestring[k2]['lat']
        else:
            distances.remove(min(distances))
            near2 = [k for k, v in pt_distances.iteritems() if v == min(distances)]
            k2 = near2[0]
            near2_lon = linestring[k2]['lon']
            near2_lat = linestring[k2]['lat']
        point['properties']['Near2'] = {'vertex_id': k2, 'lon': near2_lon, 'lat': near2_lat}

    if handholes != coincident_pts:
        valid_topology = False
    else:
        valid_topology = True
    return valid_topology


def insert_handholes(points, linestring):
    densified_linestring = deepcopy(linestring)
    for point in points:
        properties = point['properties']
        coords = point['geometry']['coordinates']

        if not properties['Coincident']:
            near1_id = properties['Near1']['vertex_id']
            near2_id = properties['Near2']['vertex_id']
            high_id = max([near1_id, near2_id])

            for k, v in linestring.iteritems():
                if k >= high_id:
                    temp_id = k + 1.1
                    densified_linestring[temp_id] = v
                    densified_linestring[int(temp_id)] = v
                    densified_linestring.pop(temp_id, None)
            for hh in points:
                near1 = hh['properties']['Near1']
                near2 = hh['properties']['Near2']
                if near1['vertex_id'] >= high_id:
                    near1['vertex_id'] = near1['vertex_id'] + 1
                if near2['vertex_id'] >= high_id:
                    near2['vertex_id'] = near2['vertex_id'] + 1

            densified_linestring[high_id] = {
                'HH': True, 'lon': coords[0], 'lat': coords[1]}
            linestring = deepcopy(densified_linestring)

    return densified_linestring

        
def get_route_segments(densified_linestring):
    """returns ranges of vertices between handholes that define route segments"""

    end_pt = max(densified_linestring.keys())
    hh_ids = [k for k, v in densified_linestring.iteritems() if v['HH']]
    route_segments = {1: None, 'last': None}

    first_hh = min(hh_ids)
    route_segments[1] = (1, first_hh + 1)
    last_hh = max(hh_ids)
    route_segments['last'] = (last_hh, end_pt + 1)

    segment = 2
    for hh_id in hh_ids:
        if hh_id != last_hh:
            remaining_hh = [hh for hh in hh_ids if hh > hh_id]
            next_hh = min(remaining_hh)
            route_segments[segment] = (hh_id, next_hh + 1)
            segment += 1

    seg_count = len(route_segments)
    route_segments[seg_count] = route_segments.pop('last')
    return route_segments


def insert_polylines(route_segments, densified_linestring, polyline, data):
    base_name = polyline['properties']['Name']
    modified_features = {'crs': data['crs'], 'type': data['type'], 'name': data['name'], 'features': []}
    empty_line = {
        'type': 'Feature',
        'properties': {
            'Name': None, 'extrude': 0,
            'tessellate': -1, 'visibility': -1
            },
            'geometry': {
                'type': 'LineString', 'coordinates': []
                }
            }

    for k,v in route_segments.iteritems():
        split_line = deepcopy(empty_line)
        split_line['properties']['Name'] = '{}{}'.format(base_name, k)

        vertices = range(*v)
        for v in vertices:
            insert_pt = densified_linestring[v]
            if not insert_pt['excess']:
                lon = insert_pt['lon']
                lat = insert_pt['lat']
                xy = [lon, lat, 0]
                split_line['geometry']['coordinates'].append(xy)
        modified_features['features'].append(split_line)
    return modified_features


def export_kml(modified_features, directory, filename):
    split_name = '{}Split'.format(filename)
    split_json = os.path.join(directory, '{}.geojson'.format(split_name))
    f = open(split_json, 'w')
    json.dump(modified_features, f)
    f.close()

    split_kml = os.path.join(directory, '{}.kmz'.format(split_name))
    cmd = '{} -f "KML" {} {}'.format(OGR2OGR, split_kml, split_json)
    os.system(cmd)


def calculate_offset(points, densified_linestring):
    """https://stackoverflow.com/questions/7222382/get-lat-long-given-current-point-distance-and-bearing"""

    offset_points = []
    for point in points:
        
        lon = point['geometry']['coordinates'][0]
        lat = point['geometry']['coordinates'][1]
        vertex = [
            v for v in densified_linestring.values()
                if v['lat'] == lat and v['lon'] == lon][0]
        offset_bearing = vertex['bearing2'] - 90
        hh = geopy.Point(lat, lon)
        offset = geodesic(feet=5).destination(hh, offset_bearing)
        offset_lat = offset.latitude
        offset_lon = offset.longitude

        offset_point = deepcopy(point)
        offset_point['geometry']['coordinates'][0] = offset_lon
        offset_point['geometry']['coordinates'][1] = offset_lat
        offset_point['properties']['Name'] = '{} OFFSET'.format(offset_point['properties']['Name'])
        
        remove = ['Coincident', 'Near1', 'Near2']
        for r in remove:
            point['properties'].pop(r, None)
            offset_point['properties'].pop(r, None)
        offset_points.append(offset_point)

    return offset_points


def insert_offsets(modified_features, points, offset_points):
    for point in points:
        modified_features['features'].append(point)
    for offset in offset_points:
        modified_features['features'].append(offset)


if __name__ == '__main__':
    ge_file = 'C:\\Users\\duncan.fetner\\Desktop\\FB\\SS_SpanD_Data.kmz'
    extension, filename, directory, timestamp = get_file_properties(ge_file)
    if extension == 'kmz':
        kml = kmz_to_kml(ge_file)
    elif extension == 'kml':
        kml = ge_file
    else:
        print ("invalid file extension")
    
    output_json = kml_to_json(kml)
    points, polyline, data = extract_features(output_json)
    remove_temp_files(directory)

    linestring = enumerate_linestring(polyline)
    valid_topology = check_topology(linestring, points)
    densified_linestring = insert_handholes(points, linestring)
    route_segments = get_route_segments(densified_linestring)
    find_excess_vertices(densified_linestring)

    modified_features = insert_polylines(route_segments, densified_linestring, polyline, data)
    offset_points = calculate_offset(points, densified_linestring)
    insert_offsets(modified_features, points, offset_points)
    export_kml(modified_features, directory, filename)






