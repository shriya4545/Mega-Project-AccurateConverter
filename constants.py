from bson import Binary
import ezdxf
import json
from xml.etree.ElementTree import Element, SubElement, tostring
import xml.dom.minidom
from math import cos, radians, sin, atan2, degrees, sqrt
import logging
import xml.etree.ElementTree as ET
import os
from datetime import datetime
from pymongo import MongoClient
# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logging.getLogger("pymongo").setLevel(logging.ERROR)

MONGO_URL="mongodb+srv://ankitadongarge:nNuMnJsbVDydYeSx@cluster0.sjuqf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
# Connect to MongoDB
client = MongoClient(MONGO_URL)
db = client["file_conversion"]
collection = db["converted_files"]
svg = ET.Element('svg', xmlns="http://www.w3.org/2000/svg", version="1.1")
# Initialize parsed data structure
parsed_data = {
    "lines": [],
    "circles": [],
    "arcs": [],
    "texts": []
}
def convert_to_relative_path(absolute_path):
    """
    Converts absolute SVG path data to relative format.
    The first move (M) remains absolute, all subsequent points become relative (m, l).
    """
    relative_path = []
    last_x, last_y = 0, 0  # Track last position

    for i, (cmd, x, y) in enumerate(absolute_path):
        if i == 0 and cmd == 'M':  # First move is absolute
            relative_path.append(f"M {x} {y}")
            last_x, last_y = x, y
        else:  # Convert Line (L) to Relative (l)
            dx, dy = x - last_x, y - last_y
            relative_path.append(f"l {dx} {dy}")
            last_x, last_y = x, y

    return " ".join(relative_path)  # Join commands into one SVG path string


def convert_to_relative_path(absolute_path):
    """
    Converts absolute SVG path data to relative format.
    The first move (M) remains absolute, all subsequent points become relative (m, l).
    """
    relative_path = []
    last_x, last_y = 0, 0  # Track the last absolute position

    for i, (cmd, x, y) in enumerate(absolute_path):
        if i == 0 and cmd == 'M':  # Keep the first move absolute
            relative_path.append(f"M {x} {y}")
            last_x, last_y = x, y
        else:  # Convert Line (L) to Relative (l)
            dx, dy = x - last_x, y - last_y
            relative_path.append(f"l {dx} {dy}")
            last_x, last_y = x, y

    return " ".join(relative_path)  # Join commands into one SVG path string


def handle_rotated_dimension(entity, parsed_data):
    # Extract start and end points for ROTATED_DIMENSION
    start_point = entity.dxf.start
    end_point = entity.dxf.end
    angle = entity.dxf.rotation  # Get rotation angle

    parsed_data["lines"].append({
        "start": {"x": start_point.x, "y": start_point.y},
        "end": {"x": end_point.x, "y": end_point.y},
        "thickness": 1,  # You can adjust the thickness as needed
        "rotation": angle
    })

def handle_entity(entity, parsed_data):
    entity_type = entity.dxftype()
    if entity_type == 'LINE':
        x_start, y_start = entity.dxf.start.x, entity.dxf.start.y
        x_end, y_end = entity.dxf.end.x, entity.dxf.end.y
        thickness = entity.dxf.lineweight / 100 if entity.dxf.hasattr('lineweight') else 1
        parsed_data["lines"].append({
            "start": {"x": x_start, "y": y_start},
            "end": {"x": x_end, "y": y_end},
            "thickness": thickness
        })
    elif entity_type == 'DIMENSION':
        dim_type = entity.dxf.dimtype
        if dim_type == 0:  # Rotated Dimension
            defpoint1 = entity.dxf.defpoint1
            defpoint2 = entity.dxf.defpoint2
            dim_line_start = {"x": defpoint1.x, "y": defpoint1.y}
            dim_line_end = {"x": defpoint2.x, "y": defpoint2.y}
            thickness = entity.dxf.lineweight / 100 if entity.dxf.hasattr('lineweight') else 1

            # Add dimension line to parsed data
            parsed_data["lines"].append({
                "start": dim_line_start,
                "end": dim_line_end,
                "thickness": thickness,
                "type": "dimension",
                "rotation": entity.dxf.rotation if entity.dxf.hasattr("rotation") else 0
            })

        # Extract dimension text (if available)
        if entity.dxf.hasattr("text"):
            text_position = entity.dxf.text_midpoint
            parsed_data["texts"].append({
                "content": entity.dxf.text,
                "position": {"x": text_position.x, "y": text_position.y},
                "height": entity.dxf.dimtxt,  # Dimension text height
                "rotation": entity.dxf.rotation if entity.dxf.hasattr("rotation") else 0,
                "type": "dimension_label"
            })

    
    elif entity_type == 'CIRCLE':
        x_center, y_center = entity.dxf.center.x, entity.dxf.center.y
        radius = entity.dxf.radius
        thickness = entity.dxf.lineweight / 100 if entity.dxf.hasattr('lineweight') else 1
        parsed_data["circles"].append({
            "center": {"x": x_center, "y": y_center},
            "radius": radius,
            "thickness": thickness
        })
    elif entity_type == 'ARC':
        x_center, y_center = entity.dxf.center.x, entity.dxf.center.y
        radius = entity.dxf.radius
        start_angle = entity.dxf.start_angle
        end_angle = entity.dxf.end_angle
        thickness = entity.dxf.lineweight / 100 if entity.dxf.hasattr('lineweight') else 1

        start_x = x_center + radius * cos(radians(start_angle))
        start_y = y_center + radius * sin(radians(start_angle))
        end_x = x_center + radius * cos(radians(end_angle))
        end_y = y_center + radius * sin(radians(end_angle))

        parsed_data["arcs"].append({
            "center": {"x": x_center, "y": y_center},
            "radius": radius,
            "start": {"x": start_x, "y": start_y},
            "end": {"x": end_x, "y": end_y},
            "start_angle": start_angle,
            "end_angle": end_angle,
            "thickness": thickness
        })
    
    elif entity_type in ['TEXT', 'MTEXT']:
        text_content = entity.dxf.text if entity_type == 'TEXT' else entity.text
        x_position, y_position = entity.dxf.insert.x, entity.dxf.insert.y
        height = entity.dxf.height if entity_type == 'TEXT' else entity.dxf.char_height
        rotation = entity.dxf.rotation if entity.dxf.hasattr('rotation') else 0
        parsed_data["texts"].append({
            "content": text_content,
            "position": {"x": x_position, "y": y_position},
            "height": height,
            "rotation": rotation
        })
    else:
        logging.warning(f"Skipping unsupported entity type: {entity_type}")

def calculate_circle_from_3points(p1, p2, p3):
    # Calculate circle center and radius from three points
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3

    # Midpoints
    mid_x1, mid_y1 = (x1 + x2) / 2, (y1 + y2) / 2
    mid_x2, mid_y2 = (x2 + x3) / 2, (y2 + y3) / 2

    # Slopes of perpendicular bisectors
    slope1 = -(x2 - x1) / (y2 - y1) if y2 != y1 else None
    slope2 = -(x3 - x2) / (y3 - y2) if y3 != y2 else None

    if slope1 is None:  # Vertical line
        center_x = mid_x1
        center_y = slope2 * (center_x - mid_x2) + mid_y2
    elif slope2 is None:
        center_x = mid_x2
        center_y = slope1 * (center_x - mid_x1) + mid_y1
    else:
        center_x = ((slope1 * mid_x1 - slope2 * mid_x2) - (mid_y1 - mid_y2)) / (slope1 - slope2)
        center_y = slope1 * (center_x - mid_x1) + mid_y1

    radius = sqrt((center_x - x1) * 2 + (center_y - y1) * 2)
    
    # Calculate start and end angles
    start_angle = degrees(atan2(y1 - center_y, x1 - center_x))
    end_angle = degrees(atan2(y3 - center_y, x3 - center_x))

    # Ensure positive angles
    if start_angle < 0:
        start_angle += 360
    if end_angle < 0:
        end_angle += 360

    return {
        "center": {"x": center_x, "y": center_y},
        "radius": radius,
        "start_angle": start_angle,
        "end_angle": end_angle
    }

def parse_dxf(filename, scaling_factor=1.0):
    global parsed_data
    parsed_data = {
        "lines": [],
        "circles": [],
        "arcs": [],
        "texts": []
    }
    try:
        doc = ezdxf.readfile(filename)
    except ezdxf.DXFStructureError as e:
        logging.error(f"DXF structure error: {e}")
        raise ValueError(f"The DXF file is corrupted. Problem: {e}")
    except ezdxf.DXFVersionError as e:
        logging.error(f"Unsupported DXF version: {e}")
        raise ValueError(f"The DXF file version is not supported. Problem: {e}")
    except Exception as e:
        logging.error(f"Failed to read DXF file: {e}")
        raise ValueError(f"An unknown error occurred while reading the DXF file. Problem: {e}")

    msp = doc.modelspace()
    all_x_coords = []
    all_y_coords = []

    # Parse entities
    for entity in msp:
        try:
            handle_entity(entity, parsed_data)
        except AttributeError as e:
            logging.warning(f"Entity missing attributes: {e}")
            raise ValueError(f"Corrupted entity found. Problem: {e}")
        except Exception as e:
            logging.warning(f"Error processing entity: {e}")
            raise ValueError(f"An error occurred while processing entities. Problem: {e}")

        if entity.dxftype() == 'LINE':
            all_x_coords.extend([entity.dxf.start.x, entity.dxf.end.x])
            all_y_coords.extend([entity.dxf.start.y, entity.dxf.end.y])
        elif entity.dxftype() == 'ROTATED DIMENSION':
            all_x_coords.extend([entity.dxf.start.x, entity.dxf.end.x])
            all_y_coords.extend([entity.dxf.start.y, entity.dxf.end.y])
        elif entity.dxftype() in ['CIRCLE', 'ARC']:
            all_x_coords.append(entity.dxf.center.x)
            all_y_coords.append(entity.dxf.center.y)

    # Check if no valid geometry was parsed
    if not all_x_coords or not all_y_coords:
        raise ValueError("No valid geometry found in the DXF file. The file might be empty or corrupted.")

    # Find the bounding box (min and max coordinates)
    try:
        min_x, max_x = min(all_x_coords), max(all_x_coords)
        min_y, max_y = min(all_y_coords), max(all_y_coords)
    except ValueError as e:
        logging.error(f"Error calculating bounding box: {e}")
        raise ValueError(f"Error calculating the bounding box. Problem: {e}")

    # Scale coordinates (if necessary)
    for entity_type in parsed_data:
        for entity in parsed_data[entity_type]:
            if 'start' in entity:
                entity['start']['x'] *= scaling_factor
                entity['start']['y'] *= scaling_factor
            if 'end' in entity:
                entity['end']['x'] *= scaling_factor
                entity['end']['y'] *= scaling_factor
            if 'center' in entity:
                entity['center']['x'] *= scaling_factor
                entity['center']['y'] *= scaling_factor
            if 'radius' in entity:
                entity['radius'] *= scaling_factor

    # Save parsed data to JSON file
    with open('parsed_data.json', 'w') as json_file:
        json.dump(parsed_data, json_file)

    logging.debug(f"Parsed data: {parsed_data}")
    return min_x, max_x, min_y, max_y

    with open('parsed_data.json', 'r') as json_file:
        parsed_data = json.load(json_file)

# Sort each section by 'thickness'
for section in ['lines', 'arcs', 'circles']:
    if section in parsed_data and isinstance(parsed_data[section], list):
        parsed_data[section] = sorted(parsed_data[section], key=lambda x: x.get('thickness', 0))

# Save sorted data back to JSON
with open('parsed_data.json', 'w') as json_file:
    json.dump(parsed_data, json_file, indent=4)

def invert_y(y, max_y):
    return max_y - y
def invert_arc_coordinates(arc, max_y):
    """
    Inverts the Y-coordinates for arcs specifically, and recalculates start and end points
    with proper inversion of angles for SVG representation.
    """
    x_center = arc["center"]["x"]
    y_center = invert_y(arc["center"]["y"], max_y)  # Invert the center Y-coordinate

    radius = arc["radius"]
    
    # Invert the start and end Y-coordinates
    start_x = arc["start"]["x"]
    start_y = invert_y(arc["start"]["y"], max_y)
    end_x = arc["end"]["x"]
    end_y = invert_y(arc["end"]["y"], max_y)

    # Adjust the angles for the inverted Y-axis
    start_angle = arc["start_angle"]
    end_angle = arc["end_angle"]

    # Adjust sweep direction because Y-inversion flips the arc direction
    if start_angle > end_angle:
        sweep_flag = 0  # Clockwise direction (after inversion)
    else:
        sweep_flag = 1  # Counter-clockwise (after inversion)
    
    # SVG requires the large arc flag to determine if the larger or smaller arc should be drawn
    angle_diff = (end_angle - start_angle) % 360
    large_arc_flag = 1 if angle_diff > 180 else 0

    # Return updated arc data in SVG path format
    return f"M {start_x},{start_y} A {radius},{radius} 0 {large_arc_flag},{sweep_flag} {end_x},{end_y}"


def create_arc_path(arc, max_y):
    # Adjust angles for SVG coordinate system
    start_angle = arc["start_angle"]
    end_angle = arc["end_angle"]

    radius = arc["radius"]
    x_center = arc["center"]["x"]
    y_center = arc["center"]["y"]
    if start_angle < 0:
        start_angle += 360
    if end_angle < 0:
        end_angle += 360
    # Calculate start and end points based on angles
    start_x = x_center + radius * cos(radians(start_angle))
    start_y = y_center + radius * sin(radians(start_angle))
    end_x = x_center + radius * cos(radians(end_angle))
    end_y = y_center + radius * sin(radians(end_angle))

    # Invert the Y-coordinates (since SVG Y-axis is inverted)
    start_y_inverted = invert_y(start_y, max_y)
    end_y_inverted = invert_y(end_y, max_y)

    # Ensure angles wrap around correctly (e.g., 359 degrees -> 0 degrees)
    angle_diff = (end_angle - start_angle) % 360
    large_arc_flag = 1 if angle_diff > 180 else 0
    sweep_flag = 1 if angle_diff > 0 else 0

    # Return the SVG arc path data
    return f"M {start_x},{start_y_inverted} A {radius},{radius} 0 {large_arc_flag},{sweep_flag} {end_x},{end_y_inverted}"
def save_svg(svg_element, output_directory="output", filename="output.svg"):
    # Ensure output directory exists
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    
    # Define full path with a timestamp for uniqueness
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(output_directory, f"{filename}_{timestamp}.svg")
    
    # Convert SVG Element to a formatted string
    svg_str = xml.dom.minidom.parseString(ET.tostring(svg_element)).toprettyxml()
    
    # Write the SVG data to the file
    with open(file_path, "w") as file:
        file.write(svg_str)
    
    print(f"SVG file saved at: {file_path}")
    return file_path  # Optionally return the path for further use
def save_to_mongodb(dxf_filename, svg_filename):
    """
    Saves the converted SVG and original DXF file into MongoDB.
    """
    try:
        with open(dxf_filename, "rb") as dxf_file:
            dxf_data = dxf_file.read()

        with open(svg_filename, "r") as svg_file:
            svg_data = svg_file.read().encode("utf-8")  # Store as binary

        # Insert into MongoDB
        collection.insert_one({
            "filename": os.path.basename(dxf_filename),
            "upload_time": datetime.utcnow(),
            "dxf_file": Binary(dxf_data),
            "svg_file": Binary(svg_data)
        })

        logging.info(f"Stored {dxf_filename} and {svg_filename} in MongoDB")

    except Exception as e:
        logging.error(f"Error saving files to MongoDB: {e}")

def convert_to_svg(input_json, output_svg, min_x, max_x, min_y, max_y):
    # Load parsed data from JSON
    try:
        with open(input_json, "r") as infile:
            data = json.load(infile)  # Load JSON file content into data
    except FileNotFoundError:
        raise ValueError(f"Input JSON file {input_json} not found")
    except json.JSONDecodeError:
        raise ValueError("Error decoding the JSON file. Check the file format.")

    # Define the viewBox
    width = max_x - min_x
    height = max_y - min_y

    # Create SVG root element with a viewBox attribute
    svg = Element('svg', xmlns="http://www.w3.org/2000/svg", version="1.1")
    svg.set("width", "850")
    svg.set("height", "850")
    svg.set("viewBox", f"{min_x} {invert_y(max_y, max_y)} {width} {height}")


    if "lines" in data:
        
        for line in data["lines"]:
            # line_element = SubElement(svg, 'line', {
            #     "x1": str(line["start"]["x"]),
            #     "y1": str(invert_y(line["start"]["y"], max_y)),
            #     "x2": str(line["end"]["x"]),
            #     "y2": str(invert_y(line["end"]["y"], max_y)),
            #     "stroke": "black",  # Use blue to match the AutoCAD display
            #     "stroke-width": str(line["thickness"])
            # })
            # Compute relative movement
            dx = line["end"]["x"] - line["start"]["x"]
            dy = invert_y(line["end"]["y"], max_y) - invert_y(line["start"]["y"], max_y)

            # Convert lines into <path> with relative positioning
            SubElement(svg, 'path', {
                "d": f"M {line['start']['x']} {invert_y(line['start']['y'], max_y)} l {dx} {dy}",
                "stroke": "black",
                "stroke-width": str(line["thickness"]),
                "fill": "none"
            })

        # Add rotation transformation if specified
            if "rotation" in line:
                line_element.set("transform", f"rotate({line['rotation']} {line['start']['x']} {invert_y(line['start']['y'], max_y)})")
    if "lines" in data:
        for line in data["lines"]:
            if line.get("type") == "dimension":  # Handle dimension lines specifically
                line_element = SubElement(svg, 'line', {
                    "x1": str(line["start"]["x"]),
                    "y1": str(invert_y(line["start"]["y"], max_y)),
                    "x2": str(line["end"]["x"]),
                    "y2": str(invert_y(line["end"]["y"], max_y)),
                    "stroke": "black",
                    "stroke-width": str(line["thickness"])
                })
                if "rotation" in line:
                    line_element.set("transform", f"rotate({line['rotation']} {line['start']['x']} {invert_y(line['start']['y'], max_y)})")

    # Add Circles
    if "circles" in data:
        for circle in data["circles"]:
            SubElement(svg, 'circle', {
                "cx": str(circle["center"]["x"]),
                "cy": str(invert_y(circle["center"]["y"], max_y)),
                "r": str(circle["radius"]),
                "stroke": "black",
                "stroke-width": str(circle["thickness"]),
                "fill": "none"
            })

    # Add Arcs
    if "arcs" in data:
        for arc in data["arcs"]:
            # path_data = invert_arc_coordinates(arc, max_y)  # Use the new inversion function
            # SubElement(svg, 'path', {
            #     "d": path_data,
            #     "stroke": "black",
            #     "stroke-width": str(arc["thickness"]),
            #     "fill": "none"
            # })
            # Compute relative movement for start point
            dx = arc["start"]["x"] - arc["center"]["x"]
            dy = invert_y(arc["start"]["y"], max_y) - invert_y(arc["center"]["y"], max_y)

            # Compute relative movement for arc endpoint
            dx_end = arc["end"]["x"] - arc["start"]["x"]
            dy_end = invert_y(arc["end"]["y"], max_y) - invert_y(arc["start"]["y"], max_y)

            # Convert arc to relative path
            path_data = f"m {dx},{dy} a {arc['radius']},{arc['radius']} 0 0,1 {dx_end},{dy_end}"
            SubElement(svg, 'path', {
                "d": path_data,
                "stroke": "black",
                "stroke-width": str(arc["thickness"]),
                "fill": "none"
            })

    # Add Texts
    # Add Texts
    if "texts" in data:
        for text in data["texts"]:
            text_content = text["content"]

        # Handle AutoCAD text formatting codes like %%u (underline)
            if "%%u" in text_content:
                text_content = text_content.replace("%%u", "")  # Remove or process underline formatting

        # Create SVG text element
            SubElement(svg, 'text', {
                "x": str(text["position"]["x"]),
                "y": str(invert_y(text["position"]["y"], max_y)),
                "font-size": str(text["height"]),
                "fill": "black",
                "transform": f"rotate({text['rotation']} {text['position']['x']} {invert_y(text['position']['y'], max_y)})"
            }).text = text_content

    if "texts" in data:
        for text in data["texts"]:
            if text.get("type") == "dimension_label":  # Handle dimension labels specifically
                SubElement(svg, 'text', {
                    "x": str(text["position"]["x"]),
                    "y": str(invert_y(text["position"]["y"], max_y)),
                    "font-size": str(text["height"]),
                    "fill": "black",
                    "transform": f"rotate({text['rotation']} {text['position']['x']} {invert_y(text['position']['y'], max_y)})"
                }).text = text["content"]


    svg_str = ET.tostring(svg, encoding='unicode')
    # Write SVG data to file
    with open(output_svg, 'w') as file:
        file.write(xml.dom.minidom.parseString(tostring(svg)).toprettyxml())
    save_to_mongodb(input_json.replace(".json", ".dxf"), output_svg)