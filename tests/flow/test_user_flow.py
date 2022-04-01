import unittest
from tempfile import TemporaryDirectory

from mnms.flow.user_flow import UserFlow
from mnms.tools.time import Time, Dt, TimeTable
from mnms.graph.core import MultiModalGraph
from mnms.mobility_service.car import CarMobilityGraphLayer, PersonalCarMobilityService
from mnms.mobility_service.public_transport import PublicTransportMobilityService, BusMobilityGraphLayer
from mnms.demand.user import User
from mnms.graph.shortest_path import Path
from mnms.vehicles.veh_type import Vehicle


class TestUserFlow(unittest.TestCase):
    def setUp(self):
        """Initiates the test.
        """
        self.tempfile = TemporaryDirectory()
        self.pathdir = self.tempfile.name+'/'

        mmgraph = MultiModalGraph()
        flow_graph = mmgraph.flow_graph

        flow_graph.add_node('0', [0, 0])
        flow_graph.add_node('1', [0, 40000])
        flow_graph.add_node('2', [1200, 0])
        flow_graph.add_node('3', [1400, 0])
        flow_graph.add_node('4', [3400, 0])

        flow_graph.add_link('0_1', '0', '1')
        flow_graph.add_link('0_2', '0', '2')
        flow_graph.add_link('2_3', '2', '3')
        flow_graph.add_link('3_4', '3', '4')

        mmgraph.add_zone('res1', ['0_1', '0_2', '2_3'])
        mmgraph.add_zone('res2', ['3_4'])

        self.personal_car = PersonalCarMobilityService()

        car = CarMobilityGraphLayer('car_layer', 10,
                                    services=[self.personal_car])
        car.add_node('C0', '0')
        car.add_node('C1', '1')
        car.add_node('C2', '2')

        car.add_link('C0_C1', 'C0', 'C1', costs={'length':40000}, reference_links=['0_1'])
        car.add_link('C0_C2', 'C0', 'C2', costs={'length':1200}, reference_links=['0_2'])

        bus = BusMobilityGraphLayer('BusLayer', 10,
                                    services=[PublicTransportMobilityService('Bus')])

        bus_line = bus.add_line('L1', TimeTable.create_table_freq('00:00:00', '01:00:00', Dt(minutes=2)))

        bus_line.add_stop('B2', '2')
        bus_line.add_stop('B3', '3')
        bus_line.add_stop('B4', '4')

        bus_line.connect_stops('B2_B3', 'B2', 'B3', 200, reference_links=['2_3'])
        bus_line.connect_stops('B3_B4', 'B3', 'B4', 2000, reference_links=['3_4'])

        mmgraph.add_layer(car)
        mmgraph.add_layer(bus)

        mmgraph.connect_layers('CAR_BUS', 'C2', 'B2', 100, {'time':0})

        self.mmgraph = mmgraph

        self.user_flow = UserFlow(1.42)
        self.user_flow.set_graph(mmgraph)
        self.user_flow.set_time(Time('00:01:00'))

    def tearDown(self):
        """Concludes and closes the test.
        """
        self.tempfile.cleanup()
        self.personal_car.fleet._veh_manager.empty()
        Vehicle._counter = 0


    def test_fill(self):
        self.assertTrue(self.mmgraph is self.user_flow._graph)
        self.assertTrue(self.mmgraph.mobility_graph is self.user_flow._mobility_graph)
        self.assertEqual(Time('00:01:00'), self.user_flow._tcurrent)
        self.assertEqual(1.42, self.user_flow._walk_speed)

    def test_request_veh(self):
        user = User('U0', '0', '4', Time('00:01:00'))
        user.set_path(Path(3400,
                           ['C0', 'C2', 'B2', 'B3', 'B4']))
        user.path.construct_layers(self.mmgraph.mobility_graph)
        user.path.mobility_services = ('PersonalCar', 'Bus')
        self.user_flow.step(Dt(minutes=1), [user])

        print(self.personal_car.fleet._veh_manager._vehicles)
        self.assertIn('U0', self.user_flow.users)
        self.assertIn('0', self.personal_car.fleet.vehicles)
        veh = self.personal_car.fleet.vehicles['0']
        self.assertEqual((('C0', 'C2'), 1200), veh.path[0])

    def test_walk(self):
        user = User('U0', '0', '4', Time('00:01:00'))
        user.set_path(Path(2200,
                           ['C2', 'B2', 'B3', 'B4']))
        user.path.construct_layers(self.mmgraph.mobility_graph)
        user.path.mobility_services = ('PersonalCar', 'Bus')
        self.user_flow.step(Dt(minutes=1), [user])
        self.assertIn('U0', self.user_flow.users)
        self.assertIn('U0', self.user_flow._walking)
        self.assertAlmostEqual(100-60*1.42, self.user_flow._walking['U0'])
