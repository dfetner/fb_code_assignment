# fb_code_assignment

Takes path to a KML or KMZ file in a local directory; any polyline geometries (routes) are
split by any point geometries (OSP access points)

1. Input file checked to ensure it's got either a KML or KMZ extension
    * if extension is .kmz:
        * a copy of the file is made in the same directory and saved as a .zip archive
        * archive is unzipped
        * root keyhole file (doc.kml) is renamed with a string representation of the
        timestamp of execution start time
    * if extension is .kml, no action taken
    * if extension is any other file type, exception is raised and program is terminated

2. KML file (either input or unzipped KMZ) is converted to GeoJSON with ogr2ogr
    * output GeoJSON saved with .json extension to avoid potential driver issues

3. JSON is loaded as Python dictionary
    * each item in JSON features array becomes an instance of class Feature, with geometry and attributes
    becoming instances of subclasses Geometry and Properties, respectively
    * all features in converted JSON dictionary are removed and dictionary is added to global namespace; used as a template for the rebuilt JSON with split lines

4. Each instance of Feature becomes an instance of either class Point (handholes) or class Polyline (routes) depending on Geometry.type and added to lists of all members of each type
    * all vertices in Polyline.coordinates become Point instances, but are not included in the list of Point features

5. Routes are assigned a dictionary attribute called linestring containing numerical indices of each vertex in sequence from start to end on the polyline with Point instances of the vertex as values

6. Haversine distance is calculated from each handhole to vertex on the route; function includes optional parameter for tolerance (default 0 feet)
    * indices of vertices with two shortest distances are assigned as handhole Property properties to the 
    * if all handholes are within the tolerance distance, topology is considered valid and next steps are skipped

7. If topology is invalid (not all handholes are coincident with a route vertex), each handhole is inserted as a new vertex on the polyline between the two nearest vertices
    * linestring indices and indices of the two nearest vertices to each handhole are incremented by 1 for each iteration through list of handholes
    * results in route.linestring containing both the original defining vertices and handholes as new vertices

8. Route is split into segments with endpoints defined by either handholes or a handhole and a terminal vertex on the route polyline; segments are defined in a dictionary with segment ID as keys and ranges of vertex sequences that define the line; stored in Polyline class attribute segments 

9. Route vertices are checked to see if they are integral to the geometry definition; excess vertices can lead to poor performance in many areas
    * bearing (in degrees) between each non-handhole vertex and both the next and previous vertex is calculated and added as a class attribute
    * the to-from and from-to bearings for each vertex is compared to that of the next sequential vertex; if all three are equal, the vertex can be defined as excess and can be removed

10. All route segments as defined by index ranges are cast to dictionary representations of GeoJSON polylines
    * any excess vertices are excluded
    * polyline objects are appended to a list of segmented polylines


11. Handhole offsets are calculated
    * offset bearing = bearing to next vertex - 90 (for each handhole) to ensure offset points are perpendicular to the route
    * offset distance = 5 feet
    * coordinates of offset calculated with geopy implementation of Haversine formula
    * a copy of the handhole object is created and the coordinates modified to reflect the coordinates of the offset
    * new offset objects cast to dictionary representation of GeoJSON point and appended to a list of offsets

11. Final KMZ created
    * All GeoJSON representations of the route segments, original handholes, and offset handholes are appended to the empty features object in the GeoJSON template 
    * Dictionary representation of the GeoJSON written to file with .json extension
    * output JSON saved with .geojson extension
    * output GeoJSON converted to KML with ogr2ogr
    * output KML renamed with .kmz extension

