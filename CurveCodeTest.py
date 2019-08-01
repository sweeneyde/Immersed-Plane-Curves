import unittest
from curve_code import Curve, Move, cw_shift, ccw_shift
import itertools


class TestCurveMethods(unittest.TestCase):
    def _check_invariants(self, c: Curve, msg=""):
        if len(c) == 1:
            pair = next(iter(c))
            self.assertIn(-1, pair)
            self.assertNotEqual((-1, -1), pair)
            return
        self.assertTrue(len(c) % 2 == 0)
        code = c._code
        quadruples = dict()
        for i, pair2 in enumerate(code):
            pair1 = code[i - 1]
            q = tuple(pair1) + tuple(reversed(pair2))
            for i in range(4):
                self.assertNotEqual(q[i - 1], q[i], f"{q} invalid in {c}, from {msg}")
            self.assertNotIn(q, quadruples, f"{q} duplicate in {c}, from {msg}")
            quadruples[q] = i

        for q, i in quadruples.items():
            ccw = ccw_shift(q)
            cw = cw_shift(q)
            self.assertTrue(
                (ccw in quadruples) ^ (cw in quadruples),
                f"{q}"
            )
            other_index = quadruples.get(ccw) or quadruples.get(cw)
            # check that the locations differ by an odd number
            self.assertEqual((i-other_index) % 2, 0)

    test_curve_1 = Curve([
        # trefoil with extra kink
        (1, -1), (0, 2), (3, -1), (0, 1),
        (4, 0), (0, 1), (2, -1), (0, 3)
    ])

    test_curve_2 = Curve([
        # A complicated asymmetric curve with:
        # 7 triangles, 2 empty bigons, and 1 empty 1-gon
        (1, -1), (2, 8), (7, 3), (4, 9),
        (11, 5), (-1, 10), (9, 5), (4, 11),
        (7, -1), (6, 1), (7, 2), (3, 8),
        (9, -1), (-1, 12), (9, -1), (5, 10),
        (11, -1), (4, 7), (9, 3), (-1, 8),
        (1, 2), (6, 7)
    ])

    test_curve_3 = Curve([
        # something with a 3-sided face that isn't a triangle
        (0, -1), (-1, 2), (0, -1), (1, 0)
    ])

    test_curve_4 = Curve([
        # triple eight
        (1, -1), (-1, 0), (2, -1), (-1, 0)
    ])

    test_curves = [test_curve_1, test_curve_2, test_curve_3, test_curve_4]

    def diverse_test_curves(self):
        yield from self.test_curves
        for i in range(-5, 6):
            yield Curve.canonical(i)

    def test_curve_invariants(self):
        for c in self.diverse_test_curves():
            self._check_invariants(c)

    def test_curve_specifics(self):
        self.assertEqual(1, sum(1 for _ in self.test_curve_1.strange_neighbors()))
        self.assertEqual(2, sum(1 for _ in self.test_curve_1.decreasing_j_neighbors()))
        self.assertEqual(1, sum(1 for _ in self.test_curve_1.decreasing_r1_neighbors()))

        self.assertEqual(7, sum(1 for _ in self.test_curve_2.strange_neighbors()))
        self.assertEqual(2, sum(1 for _ in self.test_curve_2.decreasing_j_neighbors()))
        self.assertEqual(1, sum(1 for _ in self.test_curve_2.decreasing_r1_neighbors()))

        self.assertEqual(0, sum(1 for _ in self.test_curve_3.strange_neighbors()))
        self.assertEqual(0, sum(1 for _ in self.test_curve_3.decreasing_j_neighbors()))
        self.assertEqual(2, sum(1 for _ in self.test_curve_3.decreasing_r1_neighbors()))

        self.assertEqual(0, sum(1 for _ in self.test_curve_4.strange_neighbors()))
        self.assertEqual(1, sum(1 for _ in self.test_curve_4.decreasing_j_neighbors()))
        self.assertEqual(2, sum(1 for _ in self.test_curve_4.decreasing_r1_neighbors()))

    def test_canonical_whitney(self):
        for i in range(-10, 11):
            self.assertEqual(i, Curve.canonical(i).whitney())

    def test_whitney_changes(self):
        for test in self.diverse_test_curves():
            w = test.whitney()
            for move, c in test.increasing_r1_neighbors():
                if move == Move.R1_CCW_ADD:
                    self.assertEqual(w + 1, c.whitney(), c)
                else:
                    self.assertEqual(w - 1, c.whitney(), c)
            for move, c in test.decreasing_r1_neighbors():
                if move == Move.R1_CCW_REMOVE:
                    self.assertEqual(w - 1, c.whitney(), c)
                else:
                    self.assertEqual(w + 1, c.whitney(), c)
            for move, c in itertools.chain(
                    test.increasing_j_neighbors(),
                    test.decreasing_j_neighbors(),
                    test.strange_neighbors(),
            ):
                self.assertEqual(w, c.whitney(), c)

    def test_equality_trivial(self):
        for i in range(-10, 11):
            c = Curve.canonical(i)
            self.assertEqual(c, eval(repr(c)))

    def test_equality_shift(self):
        for c1 in self.diverse_test_curves():
            d = c1._code.copy()
            d.rotate(1)
            c2 = Curve(d)
            self.assertEqual(c1, c2)
            self.assertEqual(hash(c1), hash(c2))

    def test_face_iter(self):
        c = Curve.canonical(4)
        self.assertEqual(c._code[0], (0, -1))
        self.assertEqual(
            [(i, i % 2) for i in range(6)],
            list(c.face_iterator(0, 0))
        )

    def test_increasing_r1(self):
        for c0 in self.diverse_test_curves():
            for move, c in c0.increasing_r1_neighbors():
                self._check_invariants(c)

    def test_decreasing_r1(self):
        for test in self.diverse_test_curves():
            for move, c in test.increasing_r1_neighbors():
                flag = False
                for other_move, c2 in c.decreasing_r1_neighbors():
                    self._check_invariants(c2, f"test curve 1 with increasing, then decreasing r1")
                    if other_move == move.inverse() and c2 == test:
                        flag = True
                self.assertTrue(flag, f"{c} \ndid not reach {test}")

    def test_increasing_j(self):
        for c0 in self.diverse_test_curves():
            for move, c in c0.increasing_j_neighbors():
                self._check_invariants(c, f"{c0} with {move.name}")

    def test_decreasing_j(self):
        for test in self.diverse_test_curves():
            for move, c in test.increasing_j_neighbors():
                flag = False
                for other_move, c2 in c.decreasing_j_neighbors():
                    self._check_invariants(c2, f"test curve 1 with increasing, then decreasing j")
                    if other_move == move.inverse() and c2 == test:
                        flag = True
                self.assertTrue(flag)

    def test_strange(self):
        for test in self.diverse_test_curves():
            for move, c in test.strange_neighbors():
                self._check_invariants(c, f"testing strange")

                flag = True
                for other_move, c2 in c.strange_neighbors():
                    self._check_invariants(c2, f"testing strange backward")
                    if other_move == move.inverse() and c2 == test:
                        flag = True
                self.assertTrue(flag)

    def test_move_counts(self):
        for test in self.diverse_test_curves():
            j_add = 0
            fi = test.face_index()
            for f, refs in test.face_index().items():
                p = len(refs)
                j_add += p*(p+1)//2
            p = len(fi[Curve.OUT])
            j_add += p*(p+1)//2

            self.assertEqual(j_add, sum(1 for _ in test.increasing_j_neighbors()), test)

    def test_integrated_neighbors(self):
        for test in self.diverse_test_curves():
            for move, c in test.neighbors():
                self._check_invariants(c)
