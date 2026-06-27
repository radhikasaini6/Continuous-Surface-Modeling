import arcpy
from arcpy.sa import *
import tempfile
import uuid
import os

# -------------------------------
# --- USER-ADJUSTABLE PARAMETERS
# -------------------------------

in_polygons = arcpy.GetParameterAsText(0)
in_field = arcpy.GetParameterAsText(1)

# optional points
in_points = arcpy.GetParameterAsText(2)
use_points = bool(in_points and arcpy.Exists(in_points))

in_points_field = arcpy.GetParameterAsText(3)
# default is 1
in_points_value_text = arcpy.GetParameterAsText(4)

if in_points_value_text == "":
    in_points_value = None
else:
    in_points_value = float(in_points_value_text)

output_raster = arcpy.GetParameterAsText(5)
folder = os.path.dirname(output_raster)
name, ext = os.path.splitext(output_raster)

if not folder.lower().endswith(".gdb"):
    if ext == "":
        output_raster = name + ".tif"

else:
    if ext == ".tif":
        raise ValueError(
            "TIFF files can't be stored in a geodatabase, specify a file folder location for the output raster in TIFF format.")
    else:
        pass

map_scale = arcpy.GetParameter(6)

final_cell_size = arcpy.GetParameter(8)

if final_cell_size is None or final_cell_size <= 0:
    final_cell_size = map_scale / 2000

# --------------------------------
# --- INTERMEDIATE FILE LOCATION
# --------------------------------

run_id = uuid.uuid4().hex[:8]

temp_dir = tempfile.gettempdir()

temp_gdb = os.path.join(
    temp_dir,
    f"Gradient_Raster_tool_{run_id}.gdb"
)

arcpy.management.CreateFileGDB(
    temp_dir,
    f"Gradient_Raster_tool_{run_id}.gdb"
)

# -----------------------------------------------
# --- PRE-DEFINED PARAMETERS FROM FINAL CELL SIZE
# -----------------------------------------------

cell_size = final_cell_size / 2
pnts_buffer_large = cell_size * 6
pnts_buffer_small = cell_size * 2
smooth_small_dist = cell_size * 7.5
smooth_large_dist = cell_size * 15
w_small = 0.5
w_large = 0.5


def validate_inputs():
    inputs = [
        in_polygons,
        in_field,
        output_raster,
        final_cell_size
    ]

    if use_points:
        if in_points_value is not None:
            inputs.extend([
                in_points,
                in_points_value
            ])
        if in_points_field:
            inputs.extend([
                in_points,
                in_points_field
            ])

    def vector_check(feature, shape_type=None):
        desc = arcpy.Describe(feature)
        if desc.dataType not in ["FeatureClass", "ShapeFile", "FeatureLayer"]:
            raise ValueError(
                f"{feature} can't be {desc.dataType}\n"
                f"Valid inputs: feature class, shapefile, and feature layer")

        if shape_type:
            if desc.shapeType != shape_type:
                raise ValueError(
                    f"{feature} must be {shape_type} geometry")

    def feature_count(feature):
        count = arcpy.management.GetCount(feature)
        if int(count[0]) == 0:
            raise ValueError(
                f"{feature} has no features or is out of the current extent. Check the spatial reference for inputs match.")

    def num_check(value):
        if not isinstance(value, (int, float)):
            raise ValueError(f"{value} is not a number")

    def field_is_numeric(feature_class, field_name):
        with arcpy.da.SearchCursor(feature_class, [field_name]) as cursor:
            for row in cursor:
                value = row[0]

                if value is None:
                    continue

                try:
                    float(value)
                except:
                    return False

        return True

    def projection_check(feature_1, feature_2=None):
        sr1 = arcpy.Describe(feature_1).spatialReference

        # Check if projected
        if sr1.type != "Projected":
            raise ValueError(f"{feature_1} is not projected")

        if feature_2:
            sr2 = arcpy.Describe(feature_2).spatialReference

            if sr2.type != "Projected":
                raise ValueError(f"{feature_2} is not projected")

            # Check if same projection
            if sr1.factoryCode != sr2.factoryCode:
                raise ValueError(
                    f"Projection mismatch:\n"
                    f"{feature_1}: {sr1.name}\n"
                    f"{feature_2}: {sr2.name}"
                )

    # input validation
    try:
        for input in inputs:
            if input is None:
                raise ValueError(f"{input} is missing")

        vector_check(in_polygons, "Polygon")
        feature_count(in_polygons)
        projection_check(in_polygons)
        num_check(final_cell_size)

        # Check if field exists
        fields = [field.name for field in arcpy.ListFields(in_polygons)]
        if in_field not in fields:
            raise ValueError(f"{in_field} not in {in_polygons}")

        # Check if in_field is numeric
        if not field_is_numeric(in_polygons, in_field):
            raise ValueError(f"{in_field} contains non-numeric values and cannot be used for rasterization")

        # Check if final_cell_size provided is valid
        if map_scale <= 0:
            raise ValueError("Map scale can't be less than or equal to 0")

        if use_points:
            vector_check(in_points, "Point")
            feature_count(in_points)
            projection_check(in_polygons, in_points)

            if in_points_value is not None and in_points_field:
                raise ValueError("Specify either Points Value or Points Value Field, not both.")

            if in_points_value is not None:
                num_check(in_points_value)

            if in_points_field:
                if not field_is_numeric(in_points, in_points_field):
                    raise ValueError(
                        f"{in_points_field} contains non-numeric values and cannot be used for rasterization")

    except Exception as e:
        print(f"Input validation failed:\n{e}")

        raise


def setup_environment():
    try:
        extension_status = arcpy.CheckOutExtension("Spatial")

        if extension_status != "CheckedOut":
            raise RuntimeError(
                f"Spatial Analyst extension could not be checked out. "
                f"Status returned: {extension_status}"
            )

        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = temp_gdb
        arcpy.env.cellSize = cell_size
        arcpy.env.addOutputsToMap = False

    except Exception as e:
        print(f"Something went wrong: \n{e}")
        raise

    # extent setup
    desc = arcpy.Describe(in_polygons)
    ext = desc.extent

    buffer_dist = final_cell_size * 10

    expanded_extent = arcpy.Extent(
        ext.XMin - buffer_dist,
        ext.YMin - buffer_dist,
        ext.XMax + buffer_dist,
        ext.YMax + buffer_dist
    )

    arcpy.env.extent = expanded_extent


def prepare_vectors():
    dissolved = os.path.join(temp_gdb, "dissolved")
    if arcpy.Exists(dissolved):
        arcpy.management.Delete(dissolved)

    try:
        arcpy.management.Dissolve(
            in_polygons,
            dissolved,
            dissolve_field=in_field)

        # remove any features where in_field = NULL
        with arcpy.da.UpdateCursor(dissolved, [in_field], ) as cursor:
            for row in cursor:
                if row[0] is None:
                    cursor.deleteRow()

    except arcpy.ExecuteError as e:
        arcpy.AddError(f"Failed during Dissolve operation:\n{e}")
        raise

    if use_points:

        # tuple includes buffer name and distance
        outcrop_buffers = [
            ("pnt_buffer_s", pnts_buffer_small),
            ("pnt_buffer_l", pnts_buffer_large)
        ]

        buffers = []

        for buffer_name, buffer_dist in outcrop_buffers:
            output_buffer = os.path.join(temp_gdb, buffer_name)

            if arcpy.Exists(output_buffer):
                arcpy.management.Delete(output_buffer)
            try:
                arcpy.analysis.Buffer(
                    in_points,
                    output_buffer,
                    f"{buffer_dist} Meters")

                # create in_field and assign value
                if in_field not in [f.name for f in arcpy.ListFields(output_buffer)]:
                    arcpy.management.AddField(
                        output_buffer,
                        in_field, "SHORT")

                if in_points_value is not None:
                    arcpy.management.CalculateField(
                        output_buffer,
                        in_field,
                        in_points_value,
                        expression_type="PYTHON3")

                if in_points_field:
                    pass

                buffers.append(output_buffer)

            except arcpy.ExecuteError as e:
                arcpy.AddError(f"Failed during points Buffer operation:\n{e}")
                raise

        return dissolved, buffers[0], buffers[1]

    return dissolved, None, None


def rasterize(arg_dissolved, arg_buffer_s, arg_buffer_l):
    arcpy.env.snapRaster = None

    rasterize_poly = os.path.join(temp_gdb, "rasterize_poly")

    if arcpy.Exists(rasterize_poly):
        arcpy.management.Delete(rasterize_poly)

    try:
        arcpy.conversion.PolygonToRaster(
            arg_dissolved,
            in_field,
            rasterize_poly,
            cell_assignment="MAXIMUM_AREA",
            priority_field=in_field,
            cellsize=cell_size
        )


    except arcpy.ExecuteError as e:
        arcpy.AddError(f"Failed during Polygon to Raster operation:\n{e}")
        raise

    # -------------------------------
    # --- ENVIRONMENT SETUP
    # -------------------------------

    arcpy.env.mask = rasterize_poly

    # -------------------------------
    # --- RASTER CREATION
    # -------------------------------

    buffer_s_raster = None
    buffer_l_raster = None

    if arg_buffer_s is not None:

        try:
            buffer_s_raster = os.path.join(temp_gdb, "buffer_raster_s")

            if arcpy.Exists(buffer_s_raster):
                arcpy.management.Delete(buffer_s_raster)

            if in_points_value is not None:
                arcpy.conversion.PolygonToRaster(
                    arg_buffer_s,
                    in_field,
                    buffer_s_raster,
                    cell_assignment="MAXIMUM_AREA",
                    cellsize=cell_size
                )

            if in_points_field:
                arcpy.conversion.PolygonToRaster(
                    arg_buffer_s,
                    in_points_field,
                    buffer_s_raster,
                    cell_assignment="MAXIMUM_AREA",
                    cellsize=cell_size
                )

        except arcpy.ExecuteError as e:
            arcpy.AddError(f"Small buffer raster failed:\n{e}")
            raise

    if arg_buffer_l is not None:
        try:
            buffer_l_raster = os.path.join(temp_gdb, "buffer_raster_l")

            if arcpy.Exists(buffer_l_raster):
                arcpy.management.Delete(buffer_l_raster)

            if in_points_value is not None:
                arcpy.conversion.PolygonToRaster(
                    arg_buffer_l,
                    in_field,
                    buffer_l_raster,
                    cell_assignment="MAXIMUM_AREA",
                    cellsize=cell_size
                )

            if in_points_field:
                arcpy.conversion.PolygonToRaster(
                    arg_buffer_l,
                    in_points_field,
                    buffer_l_raster,
                    cell_assignment="MAXIMUM_AREA",
                    cellsize=cell_size
                )


        except arcpy.ExecuteError as e:
            arcpy.AddError(f"Large buffer raster failed:\n{e}")
            raise

    return rasterize_poly, buffer_s_raster, buffer_l_raster


def smoothing(arg_rasterize_poly, arg_pnt_raster_s, arg_pnt_raster_l):
    try:
        use_points = (
                arg_pnt_raster_s is not None and
                arg_pnt_raster_l is not None
        )

        # Smooth polygons only
        if not use_points:

            # smooth using small cell filter
            small_smooth = FocalStatistics(arg_rasterize_poly, NbrCircle(smooth_small_dist, "MAP"), "MEAN", "DATA")

            # smooth using large cell filter
            large_smooth = FocalStatistics(arg_rasterize_poly, NbrCircle(smooth_large_dist, "MAP"), "MEAN", "DATA")

            # average the smooth rasters
            smooth_raster_final = (small_smooth * 0.5) + (large_smooth * 0.5)

        # Smooth with points
        else:

            # combine rasters
            pnt_l = Con(IsNull(arg_pnt_raster_l), arg_rasterize_poly, arg_pnt_raster_l)

            # smooth using small cell filter
            small_smooth = FocalStatistics(pnt_l, NbrCircle(smooth_small_dist, "MAP"), "MEAN", "DATA")

            # combine rasters
            pnt_s = Con(IsNull(arg_pnt_raster_s), small_smooth, arg_pnt_raster_s)

            # smooth using large cell filter
            large_smooth = FocalStatistics(pnt_s, NbrCircle(smooth_large_dist, "MAP"), "MEAN", "DATA")

            # average
            smooth_raster = (pnt_s * 0.5) + (large_smooth * 0.5)

            smooth_raster_final = Con(IsNull(arg_pnt_raster_s), smooth_raster, arg_pnt_raster_s)


    except arcpy.ExecuteError as e:
        arcpy.AddError(f"Failed during Raster smoothing operations (Con or Focal Statistics):\n{e}")
        raise

    return smooth_raster_final


def finalize(arg_smooth_raster_final):
    # -------------------------------
    # --- ENVIRONMENT SETUP
    # -------------------------------

    arcpy.env.cellSize = None
    arcpy.env.addOutputsToMap = True

    # -------------
    # --- FINALIZE
    # -------------

    try:
        aggregate = Aggregate(
            arg_smooth_raster_final,
            2,
            "MEAN",
            "TRUNCATE",
            "DATA")

    except arcpy.ExecuteError as e:
        arcpy.AddError(f"Failed during finalizing operations (Aggregate or Con):\n{e}")
        raise

    # Save final output

    try:
        arcpy.management.CopyRaster(
            in_raster=aggregate,
            out_rasterdataset=output_raster,
            pixel_type="32_BIT_FLOAT",
            nodata_value=-99999,
            format="TIFF"
        )

    except arcpy.ExecuteError as e:
        arcpy.AddError(f"Failed during Copy Raster operation:\n{e}")
        raise


def main():
    try:
        validate_inputs()

        setup_environment()

        dissolved_returned, pnt_buffer_s_returned, pnt_buffer_l_returned = prepare_vectors()

        rasterize_polygon_returned, buffer_raster_s_returned, buffer_raster_l_returned = rasterize(
            dissolved_returned,
            pnt_buffer_s_returned,
            pnt_buffer_l_returned
        )

        smooth_raster_returned = smoothing(
            rasterize_polygon_returned,
            buffer_raster_s_returned,
            buffer_raster_l_returned
        )

        finalize(smooth_raster_returned)

    finally:
        arcpy.env.mask = None

        try:
            if arcpy.Exists(temp_gdb):
                arcpy.management.Delete(temp_gdb)
        except:
            pass

        arcpy.CheckInExtension("Spatial")


if __name__ == "__main__":
    main()
