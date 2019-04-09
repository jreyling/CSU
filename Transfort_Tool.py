# Joshua Reyling
# NR 426 Final Project
# This script is to be used as a tool within ArcGIS Pro at the Geospatial Centroid to process the monthly ridership logs
# received from Transfort.  The end result is two point feature classes used for cartography and one 'master' class that
# contains all of the unprocessed data, while deleting the interim feature classes created in geoprocessing.  More
# details are available in the tool's readme.txt

# - # Import modules and set environments # - #
import arcpy, os, sys

# Set a static workspace for output.  All outputs are in a specific place, so there is no need for users to map to it...
arcpy.env.Workspace = r'D:\Transfort_Tool\Transit_Analysis_Pro\CSU_Transfort\CSU_Transfort.gdb'
base = os.path.join(arcpy.env.Workspace, 'Base_Data',)
arcpy.env.overwriteOutput = False

# set global variables and inputs
YYYY = input('year (YYYY):')  # four digit year (e.g. 2019)
MM = input('month (MM):')  # two digit month (e.g. 03 for March)
tbl = r'E:\Transfort_Tool\TransfortRiderReport_Jan2019.csv'  # .csv table from Transfort
stops = base + '\Stops_{}'.format(YYYY)  # Bus stop class for corresponding year
thies = base + '\Thiessen_{}'.format(YYYY)  # Thiessen polygon class for corresponding year stops
tag = YYYY + MM

# Check for correct 'tag' formatting and necessary base data.
if not YYYY.isnumeric() or len(YYYY) != 4:  # Check to ensure 'YYYY' is a 4 digit number. Exit tool if check fails.
    print('Incorrect year format.  Please format year as "YYYY".  Exiting tool')
    exit()
elif not MM.isnumeric() or len(MM) != 2:  # Check to ensure 'MM' is a 2 digit number. Exit tool if check fails.
    print('Incorrect month format.  Please format month as "MM". Exiting tool.')
    exit()
elif not arcpy.Exists(stops):  # Check for existence of bus stop feature class.  Exit tool if not there.
    print('Missing required stops file.  Exiting tool.')
    exit()
elif arcpy.Exists(stops) and not arcpy.Exists(thies):  # Check existence of 'Thiessen' features. Create them if needed.
    print('Creating necessary Thiessen polygons...')
    # Create Thiessen polygons
    # Syntax: CreateThiessenPolygons_analysis (in_features, out_feature_class, {fields_to_copy})
    arcpy.CreateThiessenPolygons_analysis(stops, thies, 'ALL')

# Set a label variable For academic year that splits from July to June
if tag[-2:] <= '06':
    AY = int(tag[0:4])-1  # attributes jan- june to previous calendar year
else:
    AY = tag[0:4]  # attributes July - December to concurrent calendar year
lbl = 'Stop_Usage_{}_{}'.format(AY, int(AY)+1)

# Set output dataset using academic year label
dataset = os.path.join(arcpy.env.Workspace, lbl)

# Check for existence of output dataset and create if needed
if not arcpy.Exists(dataset):
    arcpy.CreateFeatureDataset_management(arcpy.env.Workspace, lbl, 4326)
    print('Creating feature dataset...')

# Set output path for 'RAW' feature class. Use os.path.join to concatenate
out_raw = os.path.join(dataset, 'UNPROCESSED_{}_{}'.format(YYYY, MM))

# - # Code block for tools # - #
try:

    # Check for existence of 'RAW' feature class and create if needed
    if not arcpy.Exists(out_raw):
        # XY Table to Point - create a point feature class from the xy table submitted from Transfort.
        # Syntax: XYTableToPoint_management (in_table, out_feature_class, x_field, y_field, {z_field},
        # {coordinate_system})
        arcpy.XYTableToPoint_management(tbl, out_raw, 'LON', 'LAT', '', 4326)
        print(out_raw + ' has been created')

    # Create feature layer 'employee' and 'student' from the 'RAW' feature class
    # Syntax: MakeFeatureLayer_management (in_features, out_layer, {where_clause}, {workspace}, {field_info})
    arcpy.MakeFeatureLayer_management(out_raw, 'emp_raw', "rider_type = 'Employee'")
    arcpy.MakeFeatureLayer_management(out_raw, 'stud_raw', "rider_type = 'Student'")
    print('Feature layers have been created')

    # Create a list of the feature layers just created
    lyrlist = ['emp_raw', 'stud_raw']

    # Iterate through list of feature layers to run geoprocessing tools
    for lyr in lyrlist:

        out_thies = r'in_memory\out_thies'

        # Create a naming convention for 'STOPS' feature classes using an if/else
        if lyr == 'emp_raw':
            label = 'Employee'
        else:
            label = 'Student'

        # Set output path for 'STOPS' feature classes. Use os.path.join to concatenate
        out_stops = os.path.join(dataset, '{}_STOPS_{}_{}'.format(label, YYYY, MM))

        # Check for existence of 'STOPS' feature class and create if needed
        if not arcpy.Exists(out_stops):
            # Spatial Join 1 - Count the number of riders within each Thiessen polygon.
            # Syntax: SpatialJoin_analysis (target_features, join_features, out_feature_class, {join_operation},
            # {join_type}, {field_mapping}, {match_option}, {search_radius}, {distance_field_name})
                                    # Field Mappings Syntax:
                                    # 'New_Field_Name "New_Field Alias" ? ? ? New_Field_Length Data_Type ? ?,
                                    # Merge_Rule, Merge_Delimiter(#), Source_Path, Source_Name, ?, ?;'
            arcpy.SpatialJoin_analysis(thies,
                            lyr,
                            out_thies,
                            "JOIN_ONE_TO_ONE",
                            "KEEP_ALL",
                            r'StopId "StopId" true true false 4 Long 0 0,First,#,{0},StopId,-1,-1;'
                            r'StopName "StopName" true true false 75 Text 0 0,First,#,{0},StopName,0,75;'
                            r'rider_type "rider_type" true true false 8000 Text 0 0,First,#,{1},rider_type,0,8000;'
                            r'count "count" true true false 6 Long 0 0,Sum,#,{1},count,-1,-1'.format(thies, out_raw),
                            "CONTAINS",
                            None,
                            None)
            print(out_thies + ' has been created')

            # Spatial Join 2 - join Thiessen polygons to stop points. Will output bus stops with ridership counts.
            arcpy.SpatialJoin_analysis(stops,
                            out_thies,
                            out_stops,
                            "JOIN_ONE_TO_ONE",
                            "KEEP_ALL",
                            r'StopId "StopId" true true false 4 Long 0 0,First,#,{0},StopId,-1,-1;'
                            r'StopName "StopName" true true false 75 Text 0 0,First,#,{0},StopName,0,75;'
                            r'rider_type "rider_type" true true false 8000 Text 0 0,First,#,{1},rider_type,0,8000;'
                            r'count "count" true true false 6 Long 0 0,First,#,{1},count,-1,-1'.format(stops,out_thies),
                            "WITHIN",
                            None,
                            None)
            print(out_stops + ' has been created')

            # Calculate null fields using update cursor
            with arcpy.da.UpdateCursor(out_stops, ['rider_type', 'count']) as cur:
                for row in cur:
                    if row[0] is None:
                        row[0] = label  # Changes null fields in 'rider_type' to the correct label (Employee/Student).
                        row[1] = 0  # Changes null fields to '0'
                    cur.updateRow(row)

        # Delete intermediate files
        arcpy.Delete_management('in_memory')

except Exception as e:
        print('Error: ' + e.args[0])
