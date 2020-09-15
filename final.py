import json, os, shutil, time 
from copy import deepcopy
from math import cos, sin, atan2, degrees
from zipfile import ZipFile

from geopy.distance import geodesic, distance

OGR2OGR = "C:\\OSGeo4W64\\bin\\ogr2ogr.exe"

# ======================================================================
# function definitions
# ======================================================================
def get_file_properties(ge_file):
    """returns Google Earth file extension, the base file name, directory,
    and a timestamp string used for craeting unique names
    """

    global extension
    extension = ge_file.split('.')[-1]

    global filename
    filename = os.path.split(ge_file)[1].split('.')[0]

    global directory
    directory = os.path.split(ge_file)[0]

    global timestamp
    timestamp = str(time.time()).replace('.', '')


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


def extract_features(kml):
    """Converts KML to GeoJSON and extracts features; polylines and points are
    returned separately; extracted features include geometry and attribute information
    """

    geojson = os.path.join(directory, ('{}.json').format(filename))
    cmd = '{} -f "GeoJSON" {} {} -nln "{}"'.format(OGR2OGR, geojson, kml, filename)
    os.system(cmd)

    f = open(geojson, 'r')
    data = json.load(f)
    f.close()

    features = data['features']
    json_template = {k: v for k, v in data.iteritems()}
    json_template['features'] = []
    return features, json_template


def remove_temp_files():
    """deletes all intermediate files"""

    extensions = ['zip', 'json', 'kml']
    for f in os.listdir(directory):
        if f.split('.')[-1] in extensions:
            temp_file = os.path.join(directory, f)
            os.remove(temp_file)


def check_topology(route, handholes, tolerance=0):
    total_handholes = len(handholes)
    coincident_pts = 0
    for hh in handholes:
        hh_to_line = {}
        for i, vertex in route.linestring.iteritems():
            footage = distance((hh.lat, hh.lon), (vertex.lat, vertex.lon)).ft
            hh_to_line[i] = footage
            if footage <= tolerance or (hh.lat == vertex.lat and hh.lon == vertex.lon):
                coincident_pts += 1
                hh.properties.update('_coincident', True)
                vertex.properties.update('_HH', True)
            else:
                hh.properties.update('_coincident', False)
                vertex.properties.update('_HH', False)

        distances = hh_to_line.values()
        near1 = [i for i, d in hh_to_line.iteritems() if d == min(distances)]
        hh.properties.update('_near1', near1[0])
        if len(near1) > 1:
            near2 = near1[1]
        else:
            distances.remove(min(distances))
            near2 = [i for i, d in hh_to_line.iteritems() if d == min(distances)][0]
            hh.properties.update('_near2', near2)

    if total_handholes != coincident_pts:
        valid_topology = False
    else:
        valid_topology = True
    return valid_topology


class Feature:
    def __init__(self, geometry, properties):
        self.type = 'Feature'
        self.geometry = geometry
        self.properties = properties


class Geometry:
    def __init__(self, feature):
        for k,v in feature['geometry'].iteritems():
            setattr(self, k, v)


class Properties:
    def __init__(self, feature):
        try:
            for k, v in feature['properties'].iteritems():
                setattr(self, k, v)
        except:
            return None

    def update(self, property_name, value):
        setattr(self, property_name, value)


class Polyline:
    def __init__(self, feature):
        linestring = dict(enumerate(feature.geometry.coordinates))
        self.linestring = {i + 1: Point(coords) for i, coords in linestring.iteritems()}

    def insert_handholes(self, handholes):
        densified_linestring = deepcopy(self.linestring)
        for hh in handholes:
            if not hh.properties._coincident:
                near1 = hh.properties._near1 
                near2 = hh.properties._near2 
                high_id = max([near1, near2])

                for i, vertex in self.linestring.iteritems():
                    if i >= high_id:
                        temp_id = i + 1.1
                        densified_linestring[temp_id] = vertex
                        densified_linestring[int(temp_id)] = vertex
                        densified_linestring.pop(temp_id, None)
                for hh in handholes:
                    near1 = hh.properties._near1 
                    near2 = hh.properties._near2 
                    if near1 >= high_id:
                        hh.properties._near1 = near1 + 1
                    if near2 >= high_id:
                        hh.properties._near2 = near2 + 1
                
                hh_vertex = densified_linestring[high_id]
                hh_vertex.properties.update('_HH', True)
                hh_name = hh.properties.Name
                hh_vertex.properties.update('_name', hh_name)
                hh_vertex.lon = hh.lon 
                hh_vertex.lat = hh.lat
                self.linestring = deepcopy(densified_linestring)
        self.linestring = densified_linestring

    def segment_route(self):
        self.segments = {1: None, 'last': None}

        hh_ids = [i for i, vertex in self.linestring.iteritems() if vertex.properties._HH]
        first_hh = min(hh_ids)
        self.segments[1] = (1, first_hh + 1)
        last_hh = max(hh_ids)
        hh_ids.remove(last_hh)
        end_pt = max(self.linestring.keys())
        self.segments['last'] = (last_hh, end_pt + 1)

        segment = 2
        for hh in hh_ids:
            if hh != last_hh:
                try:
                    remaining_hh = [i for i in hh_ids if i > hh]
                    next_hh = min(remaining_hh)
                    self.segments[segment] = (hh, next_hh + 1)
                    segment += 1
                except:
                    pass
        
        seg_count = len(self.segments)
        self.segments[seg_count] = self.segments.pop('last')

    def find_excess_vertices(self):
        endpoint = max(self.linestring.keys())
        terminal_pts = [1, endpoint]
        bearings = {}
        for i, vertex in self.linestring.iteritems():
            if i not in terminal_pts:
                next_pt = self.linestring[i + 1]
                last_pt = self.linestring[i-1]
                bearing1 = Point.get_bearing(vertex, next_pt)
                bearings[i] = {'bearing1': bearing1}
                if vertex.properties._HH:
                    vertex.properties.update('_bearing', bearing1)
                bearing2 = Point.get_bearing(vertex, last_pt)
                bearings[i]['bearing2'] = bearing2
        for i, vertex in self.linestring.iteritems():
            if i not in terminal_pts:
                try:
                    v_bearings = bearings[i]
                    next_pt = bearings[i + 1]
                    last_pt = bearings[i - 1]
                    check1 = v_bearings['bearing1'] == next_pt['bearing1'] == last_pt['bearing1']
                    check2 = v_bearings['bearing2'] == next_pt['bearing2'] == last_pt['bearing2']
                    if (check1 and check2) and not vertex.properties._HH:
                        excess = True
                    else:
                        excess = False
                except:
                    excess = False
            else:
                excess = False
            vertex.properties.update('_excess', excess)


class Point:
    def __init__(self, coordinates):
        if type(coordinates) == (list or tuple):
            self.properties = Properties(coordinates)
            self.lon = coordinates[0]
            self.lat = coordinates[1]
            self.pt_type = 'vertex'
        else:
            self.properties = coordinates.properties
            self.lon = coordinates.geometry.coordinates[0]
            self.lat = coordinates.geometry.coordinates[1]
            self.pt_type = 'handhole'

    @classmethod
    def get_bearing(cls, pt1, pt2):
        lat1 = pt1.lat
        lon1 = pt1.lon 
        lat2 = pt2.lat
        lon2 = pt2.lon 

        bearing = atan2(
            sin(lon2-lon1)*cos(lat2),
            cos(lat1)*sin(lat2)-sin(lat1)*cos(lat2)*cos(lon2-lon1)
            )
        bearing = round(degrees(bearing), 1)
        return bearing


if __name__ == '__main__':
    ge_file = 'C:\\Users\\duncan.fetner\\Desktop\\FB\\SS_SpanD_Data.kmz'
    get_file_properties(ge_file)
    if extension == 'kmz':
        kml = kmz_to_kml(ge_file)
    else:
        kml = ge_file
    extracted_features, json_template = extract_features(kml)
    remove_temp_files()

    features = []
    for feature in extracted_features:
        g = Geometry(feature)
        p = Properties(feature)
        f = Feature(g, p)
        features.append(f)

    routes = [f for f in features if f.geometry.type == 'LineString']
    handholes = [Point(f) for f in features if f not in routes]

for r in routes:
    route = Polyline(r)
    valid_topology = check_topology(route, handholes)
    if not valid_topology:
        route.insert_handholes(handholes)
        route.segment_route()
        route.find_excess_vertices()