import unittest
from support import Guard


def row(distance, *, geom=104, root='simple_table'):
    return dict(geoms=[81,geom],roots=['PurpleCapsule',root],distance=distance)


class SupportTests(unittest.TestCase):
    def test_monotone_escape_until_detached(self):
        guard=Guard([row(-.0002)])
        for contacts in ([row(-.0002)],[row(-.00019)],[row(-.0001)],[]):
            self.assertEqual([],guard.check(contacts,rising=True))
        self.assertEqual([row(-.00001)],guard.check([row(-.00001)],rising=True))

    def test_rejects_deeper_new_and_nonvertical_contacts(self):
        for contact,rising in ((row(-.0003),True),(row(-.0001,geom=105),True),
                               (row(-.0001,root='RedBin'),True),(row(-.0001),False)):
            self.assertEqual([contact],Guard([row(-.0002)]).check([contact],rising=rising))

    def test_cannot_add_new_contact_to_empty_baseline(self):
        contact=row(-1e-8)
        self.assertEqual([contact],Guard([]).check([contact],rising=True))


if __name__=='__main__':
    unittest.main(verbosity=2)
