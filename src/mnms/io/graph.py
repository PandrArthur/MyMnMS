import json
from importlib import import_module

from mnms.graph.core import Node
from mnms.graph.layers import MultiLayerGraph


def save_graph(mlgraph: MultiLayerGraph, filename, indent=2):
    """Save a MultiModalGraph as a JSON file

    Parameters
    ----------
    mmgraph: MultiModalGraph
        Graph to save
    filename: str
        Name of the JSON file
    indent: int
        Indentation of the JSON

    Returns
    -------
    None

    """
    d = {}
    d['ROAD_DATA'] = {}
    d['MOBILITY_GRAPH'] = {}

    d['MOBILITY_GRAPH']['LAYERS'] = [serv.__dump__() for serv in mmgraph.layers.values()]
    d['MOBILITY_GRAPH']['CONNECTIONS'] = [mmgraph.mobility_graph.sections[nodes].__dump__() for nodes in mmgraph.connection_layers]

    with open(filename, 'w') as f:
        json.dump(d, f, indent=indent)


def _load_class_by_module_name(cls):
    cls_name = cls.split('.')[-1]
    cls_module_name = cls.removesuffix('.' + cls_name)
    cls_module = import_module(cls_module_name)
    cls_class = getattr(cls_module, cls_name)

    return  cls_class


def load_graph(filename:str) -> MultiModalGraph:
    """Load in memory a MultiModalGraph from a JSON file

    Parameters
    ----------
    filename: str
        Name of the JSON file

    Returns
    -------
    MultiModalGraph
        Return the corresponding MultiModalGraph

    """
    with open(filename, 'r') as f:
        data = json.load(f)

    mmgraph = MultiModalGraph()
    flow_graph = mmgraph.flow_graph

    for ndata in data['FLOW_GRAPH']['NODES']:
        flow_graph.add_node(Node.__load__(ndata))

    for ldata in data['FLOW_GRAPH']['LINKS']:
        flow_graph.add_link(Node.__load__(ldata))

    for sdata in data['FLOW_GRAPH']['ZONES']:
        mmgraph.add_zone(sdata['ID'], sdata['LINKS'])

    for sdata in data['MOBILITY_GRAPH']['LAYERS']:
        layer_class = _load_class_by_module_name(sdata['TYPE'])
        layer = layer_class.__load__(sdata)

        for service_data in sdata['SERVICES']:
            service_class = _load_class_by_module_name(service_data['TYPE'])
            layer.add_mobility_service(service_class(service_data['ID']))

        mmgraph.add_layer(layer)

    for cdata in data['MOBILITY_GRAPH']['CONNECTIONS']:
        mmgraph.connect_layers(cdata['ID'], cdata['UPSTREAM'], cdata['DOWNSTREAM'], cdata['COSTS']['length'], cdata['COSTS'])

    return mmgraph