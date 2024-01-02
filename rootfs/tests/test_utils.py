import unittest
from helmbroker import utils


class TestUtils(unittest.TestCase):

    default_allow_parameters = [
        {
            "name": "deployment.image",
            "required": True,
            "description": "deployment.image",
        },
        {
            "name": "deployment.test1.test2",
            "required": False,
            "description": "deployment.image",
        },
        {
            "name": "deployment.test1.test3",
            "required": False,
            "description": "deployment.image",
        },
    ]

    def test_verify_parameters(self):
        not_allow_keys, required_keys = utils.verify_parameters(
            self.default_allow_parameters,
            {
                "deployment.image.registry": "registry.drycc.cc",
                "deployment.image.repository": "drycc-addons/config-reloader",
                "deployment.test1.test2": "test2",
                "deployment.test1.test3.test4": "test4",
            },
        )
        self.assertEqual(required_keys, '')
        self.assertEqual(not_allow_keys, '')
        not_allow_keys, required_keys = utils.verify_parameters(
            self.default_allow_parameters,
            {
                "deployment.test1.test3": "deployment.test1.test3",
            },
        )
        self.assertEqual(required_keys, 'deployment.image')
        self.assertEqual(not_allow_keys, '')
        not_allow_keys, required_keys = utils.verify_parameters(
            self.default_allow_parameters,
            {
                "deployment.test1.test9": "deployment.test1.test3",
            },
        )
        self.assertEqual(required_keys, 'deployment.image')
        self.assertEqual(not_allow_keys, 'deployment.test1.test9')
