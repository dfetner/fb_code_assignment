import collections, json, os, shutil, time
from math import *
import numpy as np
from zipfile import ZipFile


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

    ogr2ogr = "C:\\OSGeo4W64\\bin\\ogr2ogr.exe"
    output_json = os.path.join(directory, ('{}.json').format(filename))
    cmd = '{} -f "GeoJSON" {} {} -nln "{}"'.format(ogr2ogr, output_json, kml, filename)
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
    return points, polylines


def enumerate_linestring(polyline):
    """Extracts vertex coordinates from polyline and assigns sequential IDs to
    each coordinate pair
    """

    coordinates = polyline['geometry']['coordinates']
    linestring = dict(enumerate(coordinates))
    linestring = {k + 1: {'lon': v[0], 'lat': v[1]} for k, v in linestring.iteritems()}
    return linestring


def calculate_bearing(lat1, lon1, lat2, lon2):
    """calculates bearing between two points using the Haversine
    formula; bearings returned in degrees and rounded to the nearest hundredth
    """

    bearing = atan2(sin(lon2-lon1)*cos(lat2), cos(lat1)*sin(lat2)-sin(lat1)*cos(lat2)*cos(lon2-lon1))
    bearing = round(degrees(bearing), 1)
    return bearing


def find_excess_vertices(linestring):
    """identifies excess vertices from polylines by comparing the bearing from
    each component vertex to the next vertex to that of the previous
    """

    endpoint = max(linestring.keys())
    terminal_pts = [1, endpoint]
    for i, vertex in linestring.iteritems():
        if i not in terminal_pts:
            lat1 = vertex['lat']
            lon1 = vertex['lon']

            next_point = linestring[i + 1]
            to_lat = next_point['lat']
            to_lon = next_point['lon']
            bearing1 = calculate_bearing(lat1, lon1, to_lat, to_lon)
            vertex['bearing1'] = bearing1

            previous_point = linestring[i - 1]
            from_lat = previous_point['lat']
            from_lon = previous_point['lon']
            bearing2 = calculate_bearing(lat1, lon1, from_lat, from_lon)
            vertex['bearing2'] = bearing2

    for i, vertex in linestring.iteritems():
        if i not in terminal_pts:
            try:
                next_point = linestring[i + 1]
                previous_point = linestring[i - 1]
                check1 = vertex['bearing1'] == next_point['bearing1'] == previous_point['bearing1']
                check2 = vertex['bearing2'] == next_point['bearing2'] == previous_point['bearing2']
                if (check1 and check2):
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
            else:
                point['properties']['Coincident'] = False
        
        distances = pt_distances.values()
        near1 = [k for k, v in pt_distances.iteritems() if v == min(distances)]
        point['properties']['Near1'] = near1[0]
        if len(near1) > 1:
            point['properties']['Near2'] = near1[1]
        else:
            distances.remove(min(distances))
            near2 = [k for k, v in pt_distances.iteritems() if v == min(distances)]
            point['properties']['Near2'] = near2[0]

    print "{} of {} handholes coincident with existing route vertex".format(coincident_pts, handholes)
    if handholes != coincident_pts:
        valid_topology = False
    else:
        valid_topology = True
    return valid_topology


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
    points, polyline = extract_features(output_json)
    linestring = enumerate_linestring(polyline)
    valid_topology = check_topology(linestring, points)



