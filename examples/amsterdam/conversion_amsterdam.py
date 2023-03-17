import os

import pandas as pd
import re
import xml.etree.ElementTree as ET

from coordinates import rd_to_utm
from mnms.graph.road import RoadDescriptor
from mnms.graph.layers import PublicTransportLayer, MultiLayerGraph
from mnms.generation.layers import generate_matching_origin_destination_layer
from mnms.generation.roads import generate_pt_line_road
from mnms.vehicles.veh_type import Tram, Metro, Bus
from mnms.generation.zones import generate_one_zone
from mnms.mobility_service.public_transport import PublicTransportMobilityService
from mnms.time import TimeTable, Dt, Time
from mnms.io.graph import save_graph

csv_filepath = "KV1_GVB_2609_2/Csv/POINT.csv"
metro_xml_directory = "KV1_GVB_2609_2/Xml/METRO"
tram_xml_directory = "KV1_GVB_2609_2/Xml/TRAM"
bus_xml_directory = "KV1_GVB_2609_2/Xml/BUS"

list_tram_lines = []
list_metro_lines = []
list_bus_lines = []

ns = "http://bison.connekt.nl/tmi8/kv1/msg"


def extract_amsterdam_stops():
    ## TRAM ############################################################################################################

    tram_files = os.listdir(tram_xml_directory)

    for tram_file in tram_files:
        xml_tree = ET.parse(tram_xml_directory + "/" + tram_file)

        stop_list = xml_tree.findall(".//{*}USRSTOPbegin")
        line_number = tram_file.replace(".xml", '')

        df_tram_line = pd.DataFrame(columns=["LINE_ID", "STOP_NAME", "STOP_CODE"])

        for stop in stop_list:
            userstopcode = ""
            name = ""

            for child in stop:
                if child.tag == "{" + ns + "}userstopcode":
                    userstopcode = child.text
                if child.tag == "{" + ns + "}name":
                    name = re.sub(r'\W+', '', child.text)

            df_tram_line = df_tram_line.append({'LINE_ID': line_number, 'STOP_NAME': name, 'STOP_CODE': userstopcode},
                                               ignore_index=True)

        df_tram_line = df_tram_line.drop_duplicates(subset=["STOP_NAME"], keep="first")

        list_tram_lines.append(df_tram_line)

    ## METRO ###########################################################################################################

    metro_files = os.listdir(metro_xml_directory)

    for metro_file in metro_files:
        xml_tree = ET.parse(metro_xml_directory + "/" + metro_file)

        stop_list = xml_tree.findall(".//{*}USRSTOPbegin")
        line_number = metro_file.replace(".xml", '')

        df_metro_line = pd.DataFrame(columns=["LINE_ID", "STOP_NAME", "STOP_CODE"])

        for stop in stop_list:
            userstopcode = ""
            name = ""

            for child in stop:
                if child.tag == "{" + ns + "}userstopcode":
                    userstopcode = child.text
                if child.tag == "{" + ns + "}name":
                    name = re.sub(r'\W+', '', child.text)

            df_metro_line = df_metro_line.append(
                {'LINE_ID': line_number, 'STOP_NAME': name, 'STOP_CODE': userstopcode}, ignore_index=True)

        df_metro_line = df_metro_line.drop_duplicates(subset=["STOP_NAME"], keep="first")

        list_metro_lines.append(df_metro_line)

    ## BUS #############################################################################################################

    bus_files = os.listdir(bus_xml_directory)

    for bus_file in bus_files:
        xml_tree = ET.parse(bus_xml_directory + "/" + bus_file)

        stop_list = xml_tree.findall(".//{*}USRSTOPbegin")
        line_number = bus_file.replace(".xml", '')

        df_bus_line = pd.DataFrame(columns=["LINE_ID", "STOP_NAME", "STOP_CODE"])

        for stop in stop_list:
            userstopcode = ""
            name = ""

            for child in stop:
                if child.tag == "{" + ns + "}userstopcode":
                    userstopcode = child.text
                if child.tag == "{" + ns + "}name":
                    name = re.sub(r'\W+', '', child.text)

            df_bus_line = df_bus_line.append(
                {'LINE_ID': line_number, 'STOP_NAME': name, 'STOP_CODE': userstopcode}, ignore_index=True)

        df_bus_line = df_bus_line.drop_duplicates(subset=["STOP_NAME"], keep="first")

        list_bus_lines.append(df_bus_line)


def convert_amsterdam_to_mnms():
    ## POINTS CSV DATA

    df_points = pd.read_csv(csv_filepath, sep='|', converters={"DATAOWNERCODE": str})
    df_points = df_points[["DATAOWNERCODE", "LOCATIONXEW", "LOCATIONYNS"]]

    ## TRAM

    roads = RoadDescriptor()

    tram_service = PublicTransportMobilityService('TRAM')
    tram_layer = PublicTransportLayer(roads, "TRAMLayer", Tram, 40, services=[tram_service])

    for tram_line in list_tram_lines:

        line_number = tram_line["LINE_ID"].iloc[0]

        terminus_0_stop_code = tram_line["STOP_CODE"].iloc[0]
        terminus_1_stop_code = tram_line["STOP_CODE"].iloc[-1]

        coord_terminus_0_x = float(df_points["LOCATIONXEW"].loc[df_points["DATAOWNERCODE"] == terminus_0_stop_code])
        coord_terminus_0_y = float(df_points["LOCATIONYNS"].loc[df_points["DATAOWNERCODE"] == terminus_0_stop_code])
        coord_terminus_1_x = float(df_points["LOCATIONXEW"].loc[df_points["DATAOWNERCODE"] == terminus_1_stop_code])
        coord_terminus_1_y = float(df_points["LOCATIONYNS"].loc[df_points["DATAOWNERCODE"] == terminus_1_stop_code])

        coord_terminus_0_x_utm, coord_terminus_0_y_utm = rd_to_utm(coord_terminus_0_x, coord_terminus_0_y)
        coord_terminus_1_x_utm, coord_terminus_1_y_utm = rd_to_utm(coord_terminus_1_x, coord_terminus_1_y)

        line_id = "TRAM_" + str(line_number)
        line_length = 0

        generate_pt_line_road(roads, [coord_terminus_0_x_utm, coord_terminus_0_y_utm],
                              [coord_terminus_1_x_utm, coord_terminus_1_y_utm], 2, line_id, line_length)

        # # for each direction
        lid_0 = line_id + "_0_1"
        lid_1 = line_id + "_1_0"
        nb_stops = len(tram_line)

        stops_0 = []
        stops_1 = []

        # # for each stops
        for i in range(nb_stops):
            stop_code = tram_line.loc[i, "STOP_CODE"]
            stop_coord_x = float(df_points["LOCATIONXEW"].loc[df_points["DATAOWNERCODE"] == stop_code])
            stop_coord_y = float(df_points["LOCATIONYNS"].loc[df_points["DATAOWNERCODE"] == stop_code])

            stop_coord_x_utm, stop_coord_y_utm = rd_to_utm(stop_coord_x, stop_coord_y)

            stop_name = tram_line.loc[i, "STOP_NAME"]

            sid_0 = stop_name
            sid_1 = stop_name + "2"

            rel_0 = float(i / nb_stops)
            rel_1 = float(1 - (i / nb_stops))

            roads.register_stop_abs(sid_0, lid_0, rel_0, [stop_coord_x_utm, stop_coord_y_utm])
            roads.register_stop_abs(sid_1, lid_1, rel_1, [stop_coord_x_utm, stop_coord_y_utm])

            stops_0.append(sid_0)
            stops_1.append(sid_1)

        stops_1.reverse()

        sections_0 = []
        sections_1 = []

        for i in range(nb_stops - 1):
            sections_0.append([lid_0])
            sections_1.append([lid_1])

        tram_layer.create_line(lid_0,
                               stops_0,
                               sections_0,
                               TimeTable.create_table_freq('07:00:00', '10:00:00', Dt(minutes=5)))

        tram_layer.create_line(lid_1,
                               stops_1,
                               sections_1,
                               TimeTable.create_table_freq('07:00:00', '10:00:00', Dt(minutes=5)))

    roads.add_zone(generate_one_zone("RES", roads))

    od_layer = generate_matching_origin_destination_layer(roads)
    amsterdam_graph = MultiLayerGraph([tram_layer], od_layer, 1000)

    save_graph(amsterdam_graph, "amsterdam_tc.json")


extract_amsterdam_stops()
convert_amsterdam_to_mnms()