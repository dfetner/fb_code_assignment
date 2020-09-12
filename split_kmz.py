import csv, json, math, os, shutil, time
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
    polylines = [f for f in features if f['geometry']['type'] == 'LineString']
    return points, polylines



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
    points, polylines = extract_features(output_json)