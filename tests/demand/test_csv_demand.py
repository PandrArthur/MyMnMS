import unittest
from pathlib import Path
from mnms.demand.manager import CSVDemandManager, CSVDemandParseError
from mnms.time import Time

import numpy as np


class TestCSVDemand(unittest.TestCase):
    def setUp(self):
        """Initiates the test.
        """

        self.cwd = Path(__file__).parent.resolve()

        self.file_node = self.cwd.joinpath("data_demand/test_demand_node.csv")
        self.file_coordinate = self.cwd.joinpath("data_demand/test_demand_coordinate.csv")
        self.file_bad_type1 = self.cwd.joinpath("data_demand/test_demand_bad_type1.csv")
        self.file_bad_type2 = self.cwd.joinpath("data_demand/test_demand_bad_type2.csv")

    def tearDown(self):
        """Concludes and closes the test.
        """

    def test_demand_node(self):
        demand = CSVDemandManager(self.file_node)
        user = demand.get_next_departures(Time("07:00:00"), Time("08:00:00"))

        self.assertEqual(demand._demand_type, "node")
        self.assertEqual(len(user), 2, "User not loaded")

        user = user[0]
        self.assertTrue(isinstance(user.origin, str))
        self.assertTrue(isinstance(user.destination, str))

        self.assertEqual(user.origin, "A")
        self.assertEqual(user.destination, "B")

    def test_demand_coordinate(self):
        demand = CSVDemandManager(self.file_coordinate)
        user = demand.get_next_departures(Time("07:00:00"), Time("08:00:00"))

        self.assertEqual(demand._demand_type, "coordinate")
        self.assertEqual(len(user), 2, "User not loaded")

        user = user[0]
        self.assertTrue(isinstance(user.origin, np.ndarray))
        self.assertTrue(isinstance(user.destination, np.ndarray))

        self.assertEqual(user.origin[0], 0.)
        self.assertEqual(user.origin[1], 0.)
        self.assertEqual(user.destination[0], 1000.)
        self.assertEqual(user.destination[1], 1000.)

    def test_demand_type_error(self):
        with self.assertRaises(CSVDemandParseError):
            CSVDemandManager(self.file_bad_type1)

        with self.assertRaises(CSVDemandParseError):
            CSVDemandManager(self.file_bad_type2)
