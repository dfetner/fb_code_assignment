import csv, json, math, os, shutil, time
import numpy as np
import xml.dom.minidom as DOM
from zipfile import ZipFile


def get_file_properties(ge_file):
    """returns Google Earth file extension, the base file name, directory,
    and a timestamp string used for craeting unique names
    """

    extension = ge_file.split('.')[-1]
    filename = os.path.split(ge_file)[1]
    directory = os.path.split(ge_file)[0]
    timestamp = str(time.time()).replace('.', '')
    return extension, filename, directory, timestamp


def kmz_to_xml(kmz):
    """extracts KML from KMZ"""

    kmz_copy = os.path.join(directory, '{}.kmz'.format(filename))
    shutil.copyfile(ge_file, kmz_copy)

    # save KMZ as .zip archive
    zipped = os.path.join(directory, '{}_{}.zip'.format(filename, timestamp))
    os.rename(kmz_copy, zipped)
    
    # extract contents of .zip archive
    with ZipFile(zipped, 'r') as ref:
        ref.extractall(directory)

    # saves root KML as XML
    kml = os.path.join(directory, 'doc.kml')
    xml = os.path.join(directory, 'doc_{}.xml'.format(timestamp))
    os.rename(doc, xml)
    return xml


def kml_to_xml(kml):
    """saves KML as XML"""

    kml_copy = os.path.join(directory, '{}.kml'.format(filename))
    shutil.copyfile(ge_file, kml_copy)

    xml = os.path.join(directory, 'doc_{}.xml'.format(timestamp))
    os.rename(kml_copy, xml)
    return xml


def kml_to_json(kml):
    """converts KML to JSON with ogr2ogr; output file is saved with .json
    extension to avoid parsing issues
    """

    ogr2ogr = "C:\\OSGeo4W64\\bin\\ogr2ogr.exe"
    output_json = os.path.join(directory, ('{}.json').format(timestamp))
    cmd = '{} -f "GeoJSON" {} {}'.format(ogr2ogr, output_json, kml)
    os.system(cmd)
    return output_json


def extract_points(output_json):
    f = open(output_json, 'r')
    data = json.load(f)
    f.close()
    features = data['features']
    points = [f for f in features if f['geometry']['type'] == 'Point']
    lines = [f for f in features if f['geometry']['type'] == 'LineString']
    return points, lines


class HH:
    def __init__(self, pt_feature):










def get_kml(xml):
    kml_data = DOM.parse(xml)
    kml_geom = kml_data.getElementsByTagName('coordinates')


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
    return round(res, 2)

def calculate_bearing(lat1, lon1, lat2, lon2):

    bearing = atan2(sin(lon2-lon1)*cos(lat2), cos(lat1)*sin(lat2)-sin(lat1)*cos(lat2)*cos(lon2-lon1))
    bearing = round(degrees(bearing), 2)
    return bearing

for i, xy in coords.iteritems():
    lat1 = xy['lat']
    lon1 = xy['lon']
    lat2 = coords[i + 1]['lat']
    lon2 = coords[i + 1]['lon']
    b = calculate_bearing(lat1, lon1, lat2, lon2)
    xy['to'] = b
    try:
        lat2 = coords[i - 1]['lat']
        lon2 = coords[i - 1]['lon']
        b = calculate_bearing(lat1, lon1, lat2, lon2)
        xy['from'] = b 
    except:
        print "endpoint"
extra = []
for k,v in bearings.iteritems():
    try:
        if bearings[k + 1]['to'] == v['to'] == bearings[k-1]['to']:
            extra.append(k)
    except:
        pass


if __name__ == '__main__':
    ge_file = 'C:\\Users\\duncan.fetner\\Desktop\\FB\\SS_SpanD_Data.kmz'
    extension, filename, directory, timestamp = get_file_properties(ge_file)
    if extension == 'kmz':
        xml = kmz_to_xml(ge_file)
    elif extension == 'kml':
        xml = kml_to_xml(ge_file)
    else:
        print "invalid file extension"
    
    
