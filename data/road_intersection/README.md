
# Files

- The `/data/road_intersection/` folder contains code and data for extracting, processing, and analyzing road intersection information, including GIS shapefiles, bridge data, and intersection detection logic.

## Main Data & Output Files
- `_roads3.csv`: Source road geometry data for intersection extraction.
- `BMMS_overview.xlsx`: Bridge and structure metadata for merging and enrichment.
- `roads_intersection.csv`: Output intersection points between roads, with computed lat/lon and attributes.
- `road_gis_data/roads.shp`: Main shapefile for road geometry

## Scripts
- `data_reformatting_intersection.py`: Main script for merging, cleaning, and formatting intersection and bridge data.
- `preprocess_bmms.py`: Aggregates and cleans BMMS bridge data for merging.
- `extract_intersection_from_road.py`: Finds intersections using CSV road geometry.
- `extract_intersection_from_shapefile.py`: Finds intersections using shapefile geometry.
- `extract_intersection_from_type.py`: Finds intersections based on road type/name patterns.
- `road_intersection_from_lrps.py`: Handles intersection extraction using LRP (Linear Reference Point) logic.
- `xlsx_tools.py`: Utilities for Excel file processing.

# Methods

## Intersection Extraction
- Multiple methods are available:
	- From CSV geometry (`extract_intersection_from_road.py`)
	- From shapefile geometry (`extract_intersection_from_shapefile.py`)
	- From road type/name patterns (`extract_intersection_from_type.py`)
- Each method constructs road geometries, finds intersection points, and outputs unique intersection nodes pairs.

## Data Reformatting & Merging
- `data_reformatting_intersection.py` merges intersection points, bridge attributes, and road geometry.
- Outputs cleaned and reformatted CSV files for simulation use.

## BMMS Preprocessing
- `preprocess_bmms.py` aggregates bridge data, detects left/right side tags, maps condition codes, resolves duplicates, and builds side-specific fields.

