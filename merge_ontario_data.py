import fiona
import pandas as pd
import geopandas as gpd
import osmnx as ox
import matplotlib.pyplot as plt

from shapely.geometry import shape

shp_path = './OpenData/Brantford/City_Of_Brantford_Building_Footprints.shp'
shapefile = fiona.open(shp_path)

'''
A simple script for the proof of concept.

Further work will undoubtedly be carried out to bring this script up to something less
atrocious, as well as scripts for interfacing with OSM

Written by Zili Ge under MIT license
'''

#Centered on Brantford, note the radius is arbitrary - in the future we might want
#to automatically detect size by calculating convex hull of city building footprint data
#to prevent issues where buildings outside the download area are treated as nonexist from OSM
osm_buildings = ox.footprints.footprints_from_point((43.139427, -80.263575), distance=10000)
osm_buildings['orig_osm_geometry'] = osm_buildings['geometry']

#Assume that all government shapefiles are a list of a combination of polygons and multi-polygons.
#Might need to add changes in the future if line segments are used

polygons = []

for polygon in shapefile:

    feature_polygons = shape(polygon['geometry'])
    data_type = feature_polygons.__class__.__name__

    if data_type == 'MultiPolygon':
        multi_polygons = list(feature_polygons)
        polygons += list(zip(polygon['id']*len(multi_polygons), multi_polygons))
    elif data_type == 'Polygon':
        polygons.append([polygon['id'], feature_polygons])
    else:
        print(f'Error: shape is not a polygon, but a {data_type}. Skipping...')

df = pd.DataFrame(polygons, columns=['cityid', 'geometry'])
gdf = gpd.GeoDataFrame(df, crs=shapefile.crs['init'])
gdf.to_crs(osm_buildings.crs, inplace=True)
gdf['orig_imported_geometry'] = gdf['geometry']

overlay = gpd.overlay(gdf, osm_buildings, how='intersection')

overlay_ids = set(overlay.nodes.apply(lambda x: str(x)))
osm_buildings['isoverlap'] = osm_buildings.nodes.apply(lambda x: str(x) in ids)

osm_buildings_unaltered = osm_buildings[osm_buildings['isoverlap'] == False]
osm_buildings_unaltered.drop(
    columns=[
        'orig_osm_geometry',
        'isoverlap'
    ]
)

overlay['orig_area'] = overlay['orig_osm_geometry'].apply(lambda x: x.area)
overlay['overlap_area'] = overlay['geometry'].apply(lambda x: x.area)
overlay['ratio'] = overlay.overlap_area/overlay.orig_area
overlay_acceptable = overlay[overlay['ratio'] > 0.5]
overlay_unacceptable = overlay[overlay['ratio'] <= 0.5]

overlay_acceptable['geometry'] = overlay_acceptable['orig_imported_geometry']
overlay_unacceptable['geometry'] = overlay_unacceptable['orig_osm_geometry']

changes_with_metadata = pd.concat([overlay_acceptable, overlay_unacceptable])
ids = set(changes_with_metadata.cityid)

gdf['has_overlap'] = gdf['cityid'].apply(lambda x: x in ids)
gdf = gdf[gdf['has_overlap'] == False]
gdf = gdf[['geometry']]

changes_with_metadata.drop(
    columns=[
        'orig_osm_geometry',
        'orig_area',
        'overlap_area',
        'ratio',
        'cityid',
        'orig_imported_geometry'
    ],
    inplace=True
)

#In the final script, we do not include osm_buildings_unaltered, as these
#are buildings that we do not touch. Here for visualization purposes
osm_buildings_new = pd.concat([changes_with_metadata, gdf, osm_buildings_unaltered])

#Visualization - change to overlay_acceptable for visualizing accepted changes

#Uncomment to visualize after merge
#osmnx.footprints.plot_footprints(osm_buildings_new)

#Uncomment to visualize before merge
#osmnx.footprints.plot_footprints(osm_buildings)

#Uncomment for accepted and unaccepted polygon merges

'''
for polygon in overlay_unacceptable.head(2500).iterrows():
    try:
        plt.plot(*polygon[1].orig_osm_geometry.exterior.xy, 'r')
    except:
        for sub_polygon in list(polygon[1].orig_osm_geometry):
            plt.plot(*sub_polygon.exterior.xy, 'r')

    try:
        plt.plot(*polygon[1].orig_imported_geometry.exterior.xy, 'g')
    except:
        for sub_polygon in list(polygon[1].orig_imported_geometry):
            plt.plot(*sub_polygon.exterior.xy, 'g')

plt.show()
'''
