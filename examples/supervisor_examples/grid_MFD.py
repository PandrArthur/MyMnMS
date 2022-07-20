from mnms.simulation import Supervisor
from mnms.graph.generation import create_grid_graph
from mnms.graph.algorithms.walk import walk_connect
from mnms.demand.generation import create_random_demand
from mnms.flow.MFD import Reservoir, MFDFlow
from mnms.mobility_service import PersonalCar
from mnms.log import rootlogger, LOGLEVEL
from mnms.tools.time import Time, Dt
from mnms.travel_decision.model import BaseDecisionModel
from mnms.travel_decision.logit import LogitDecisionModel

import os

rootlogger.setLevel(LOGLEVEL.INFO)

DIST = 1000


def create_simple_grid_multimodal():
    mmgraph = create_grid_graph(10, 5, DIST)
    mmgraph.add_zone('ZONE', [l.id for l in mmgraph.flow_graph.links.values()])

    car = PersonalCar('car_layer', 10)
    bus = PersonalCar('bus', 10)

    for n in mmgraph.flow_graph.nodes.keys():
        car.create_node('CAR_' + n, n)
        bus.create_node('BUS_' + n, n)

    for l in mmgraph.flow_graph.links.values():
        uid = l.upstream_node
        did = l.downstream_node
        car.add_link('CAR_'+uid+'_'+did, 'CAR_'+uid, 'CAR_'+did, {'length': DIST, 'time':DIST/car.default_speed}, [l.id])
        bus.add_link('BUS_' + uid + '_' + did, 'BUS_' + uid, 'BUS_' + did, {'length': DIST, 'time':DIST/bus.default_speed}, [l.id])

    mmgraph.add_mobility_service(car)
    mmgraph.add_mobility_service(bus)
    mmgraph.mobility_graph.check()

    walk_connect(mmgraph, 1)

    return mmgraph


if __name__ == '__main__':
    mmgraph = create_simple_grid_multimodal()
    demand = create_random_demand(mmgraph, "07:00:00", "10:00:00", cost_path='length', min_cost=5000, seed=42)

    fdir = os.path.dirname(os.path.abspath(__file__))

    def res_fct(dict_accumulations):
        V_car = 11.5 * (1 - (dict_accumulations['car_layer'] + dict_accumulations['bus']) / 80000)
        V_car = max(V_car, 0.001)
        V_bus = V_car / 2
        dict_speeds = {'car_layer': V_car, 'bus': V_bus}
        return dict_speeds


    reservoir = Reservoir.fromZone(mmgraph, 'ZONE', res_fct)

    flow_motor = MFDFlow(outfile=fdir+"/flow.csv")
    flow_motor.add_reservoir(reservoir)

    travel_decision = LogitDecisionModel(mmgraph, outfile=fdir+"/path.csv")

    supervisor = Supervisor(graph=mmgraph,
                            flow_motor=flow_motor,
                            demand=demand,
                            decision_model=travel_decision,
                            outfile=fdir + "/travel_time_link.csv")

    supervisor.run(Time('07:00:00'), Time('10:00:00'), Dt(minutes=1), 10)
