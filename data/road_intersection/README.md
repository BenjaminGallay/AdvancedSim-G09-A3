
# Files

- The `/data/road_intersection/` folder contains code and data for extracting, processing, and analyzing road intersection information, including GIS shapefiles, bridge data, and intersection detection logic.

## Main Data & Output Files
- `_roads3.csv`: Source road geometry data for intersection extraction.
- `BMMS_overview.xlsx`: Bridge and structure metadata for merging and enrichment.
- `road_gis.xlsx`: Tabular GIS road data.
- `roads_intersection.csv`: Output intersection points between roads, with computed lat/lon and attributes.
- `road_gis_data/roads.shp`: Main shapefile for road geometry (with supporting .dbf, .prj, .shx, .cpg files).

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
- Each method constructs road geometries, finds intersection points, and outputs unique intersection nodes.

## Data Reformatting & Merging
- `data_reformatting_intersection.py` merges intersection points, bridge attributes, and road geometry.
- Handles backfilling of BMMS bridge attributes to intersection points.
- Outputs cleaned and reformatted CSV files for downstream use.

## BMMS Preprocessing
- `preprocess_bmms.py` aggregates bridge data, detects left/right side tags, maps condition codes, resolves duplicates, and builds side-specific fields.

# Typical Workflow
1. Preprocess BMMS bridge data.
2. Choose intersection extraction method (CSV, shapefile, or type).
3. Merge intersection points and bridge attributes into main road dataset.
4. Output intersection and reformatted road CSV files for modeling.

# Reference
- See `data/input_dataset_reformatting/README.md` for original road data reformatting details.
- This folder adapts those methods for intersection-specific processing and GIS-based extraction.
