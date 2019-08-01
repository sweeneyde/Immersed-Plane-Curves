from collections import deque, Counter
from enum import Enum
from itertools import combinations_with_replacement, combinations


class Move(Enum):
    R1_CCW_ADD = 101
    R1_CCW_REMOVE = 102
    R1_CW_ADD = 103
    R1_CW_REMOVE = 104

    J_PLUS_ADD = 201
    J_PLUS_REMOVE = 202
    J_MINUS_ADD = 203
    J_MINUS_REMOVE = 204

    S_0_to_3_CCW = 301
    S_3_to_0_CCW = 302
    S_1_to_2_CCW = 303
    S_2_to_1_CCW = 304

    S_0_to_3_CW = 305
    S_3_to_0_CW = 306
    S_1_to_2_CW = 307
    S_2_to_1_CW = 308

    def inverse(self):
        x = self.value
        if x % 2 == 0:
            return Move(x - 1)
        else:
            return Move(x + 1)

    @classmethod
    def strange(cls, start_q, sign):
        x = {0:301, 3:302, 1:303, 2:304}[start_q]
        if sign < 0:
            x += 4
        return cls(x)


def cw_shift(order):
    a, b, c, d = order
    return (d, a, b, c)


def ccw_shift(order):
    a, b, c, d = order
    return (b, c, d, a)


class Curve:
    OUT = -1

    def __init__(self, code):
        self._code = deque((left, right) for left, right in code)

    def __repr__(self):
        return "{}({})".format(
            self.__class__.__qualname__,
            repr(list(self._code))
        )

    def __str__(self):
        return repr(self)

    def __len__(self):
        return len(self._code)

    def __reversed__(self):
        # reversed order of traversal
        return Curve([reversed(pair) for pair in reversed(self._code)])

    def __iter__(self):
        return iter(self._code)

    def __eq__(self, other):
        if len(self) != len(other):
            return False

        def isomorphic_sequences(a, b):
            # isomorphism from 1 to 2
            iso = {self.OUT: self.OUT}
            iso_range = set()
            for pair_a, pair_b in zip(a, b):
                for val_1, val_2 in zip(pair_a, pair_b):
                    existing_val_2 = iso.get(val_1)
                    if existing_val_2 is None:
                        if val_2 in iso_range:
                            # not injective
                            return False
                        else:
                            iso[val_1] = val_2
                            iso_range.add(val_2)
                    elif existing_val_2 != val_2:
                        # not a function
                        return False
            return True

        for _ in range(len(self)):
            if isomorphic_sequences(self, other):
                return True
            self._code.rotate(1)
        return False

    def __hash__(self):
        lefts = Counter(x for (x, y) in self)
        rights = Counter(y for (x, y) in self)

        def face_code(x):
            result = (lefts[x], rights[x])
            if x == self.OUT:
                # distinguish the outside
                result = result + (-1,)
            return hash(result)

        edge_codes = [hash((face_code(x), face_code(y))) for (x, y) in self]

        n = len(edge_codes)
        consecutive_triples = Counter(
            (edge_codes[(i - 2)%n], edge_codes[(i - 1)%n], edge_codes[i%n])
            for i in range(len(edge_codes))
        )

        return hash(frozenset(consecutive_triples.items()))

    @classmethod
    def canonical(cls, w: int):
        if w >= 2:
            return cls(pair for i in range(1, w - 1 + 1)
                       for pair in [(0, cls.OUT), (i, 0)])
        elif w == 1:
            return cls([(0, cls.OUT)])
        elif w == 0:
            return cls([(0, cls.OUT), (cls.OUT, 1)])
        else:
            return reversed(cls.canonical(abs(w)))

    def whitney(self):
        while True:
            x, y = self._code[0]
            self._code.rotate(-1)
            if x == self.OUT:
                w = -1
                break
            if y == self.OUT:
                w = +1
                break

        orders = set()
        for i, edge2 in enumerate(self._code):
            edge1 = self._code[i - 1]
            order = edge2 + tuple(reversed(edge1))
            if cw_shift(order) in orders:
                w += 1
            elif ccw_shift(order) in orders:
                w -= 1
            else:
                orders.add(order)
        return w

    def num_vertices(self):
        return len(self)//2

    def face_index(self):
        index = dict()
        for i, (x, y) in enumerate(self._code):
            index.setdefault(x, []).append((i, 0))
            index.setdefault(y, []).append((i, 1))
        return index

    def source_quadruple(self, i):
        code = self._code
        n = len(code)
        pair = code[i % n]
        pair_prev = code[(i - 1) % n]
        return tuple(*pair, *reversed(pair_prev))

    def _index_displacement(self, i0, i1):
        return (i1-i0) % len(self)

    def _index_distance(self, i0, i1):
        return min(abs(self._index_displacement(i0, i1)),
                   abs(self._index_displacement(i1, i0)))

    def _triple_sign(self, i1, i2, i3):
        n = len(self)
        delta = self._index_displacement
        d = delta(i1, i2) + delta(i2, i3) + delta(i3, i1)
        if d == n:
            return +1
        else:
            assert d == 2*n
            return -1

    def increasing_r1_neighbors(self):
        """For each edge, you can make a new loop on the left or on the right."""
        code = self._code.copy()
        if len(code) == 1:
            if self == Curve.canonical(1):
                yield (Move.R1_CCW_ADD, Curve.canonical(2))
                yield (Move.R1_CW_ADD, Curve.canonical(0))
            else:
                assert self == Curve.canonical(-1)
                yield (Move.R1_CCW_ADD, Curve.canonical(0))
                yield (Move.R1_CW_ADD, Curve.canonical(-2))
            return

        new_face = 1 + max(face for pair in code for face in pair)
        for _ in range(len(code)):
            pair = code[0]

            code.appendleft((new_face, pair[0]))
            code.appendleft(pair)
            yield (Move.R1_CCW_ADD, Curve(code))
            code.popleft()
            code.popleft()

            code.appendleft((pair[1], new_face))
            code.appendleft(pair)
            yield (Move.R1_CW_ADD, Curve(code))
            code.popleft()
            code.popleft()

            code.rotate(1)

    def decreasing_r1_neighbors(self):
        """Find an empty 1-gon"""

        def is_empty_1_gon(pair1, pair2, pair3):
            if pair1 != pair3:
                return None
            elif pair1[0] == pair2[1] and pair2[0] != self.OUT:
                return +1
            elif pair1[1] == pair2[0] and pair2[1] != self.OUT:
                return -1
            else:
                return None

        code = self._code

        if len(code) <= 2:
            w = self.whitney()
            assert self == Curve.canonical(w)
            if w == -2:
                yield (Move.R1_CW_REMOVE, Curve.canonical(-1))
            elif w == 2:
                yield (Move.R1_CCW_REMOVE, Curve.canonical(1))
            elif w == 0:
                yield (Move.R1_CW_REMOVE, Curve.canonical(1))
                yield (Move.R1_CCW_REMOVE, Curve.canonical(-1))
            return


        for _ in range(len(code)):
            result = is_empty_1_gon(code[-1], code[0], code[1])
            if result == +1:
                code_iter = iter(code)
                next(code_iter), next(code_iter)
                yield (Move.R1_CCW_REMOVE, Curve(code_iter))
            elif result == -1:
                code_iter = iter(code)
                next(code_iter), next(code_iter)
                yield (Move.R1_CW_REMOVE, Curve(code_iter))
            code.rotate(1)

    def face_iterator(self, start_i, start_j):
        code = self._code
        positions = dict()
        for i, (f1, f2) in enumerate(code):
            (f4, f3) = code[i - 1]
            positions[(f1, f2, f3, f4)] = i

        i, j = start_i, start_j
        while True:
            yield (i, j)

            if j == 0:
                prev_pair = code[i]
                next_pair = code[(i + 1) % len(code)]
                next_v = (next_pair[0], next_pair[1], prev_pair[1], prev_pair[0])
            else:
                assert j == 1
                prev_pair = code[i - 1]
                next_pair = code[i]
                next_v = (prev_pair[1], prev_pair[0], next_pair[0], next_pair[1])

            p = positions.get(cw_shift(next_v))
            if p is not None:
                i, j = p, 0
            else:
                i, j = (positions[ccw_shift(next_v)] - 1) % len(code), 1

            if i == start_i:
                break

    def increasing_j_neighbors(self, index=None):
        if len(self) == 1:
            triple_eight = Curve([(0, -1), (-1, 1), (2, -1), (-1, 1)])
            eight_inside = Curve([(0, -1), (1, 0), (0, 2), (1, 0)])
            if self == Curve.canonical(1):
                yield (Move.J_MINUS_ADD, triple_eight)
                yield (Move.J_MINUS_ADD, eight_inside)
                yield (Move.J_MINUS_ADD, eight_inside)
            else:
                assert self == Curve.canonical(-1)
                yield (Move.J_MINUS_ADD, reversed(triple_eight))
                yield (Move.J_MINUS_ADD, reversed(eight_inside))
                yield (Move.J_MINUS_ADD, reversed(eight_inside))
            return

        if index is None:
            index = self.face_index()

        # labels for new faces
        C = 1 + max(face for pair in self for face in pair)
        D = C + 1

        def swap_out(code, new_out):
            def swap(x):
                if x == self.OUT:
                    return new_out
                elif x == new_out:
                    return self.OUT
                else:
                    return x

            return (
                tuple(swap(face) for face in pair)
                for pair in code
            )

        def ways_to_link_edges(edge_1, edge_2):
            code = list(self)
            if edge_1 == edge_2:
                i, j = edge_1
                face_pair = code[i]
                A, B = face_pair[j], face_pair[1 - j]
                col_1 = [A, B, D, B, A]
                col_2 = [B, C, B, C, B]
                if j == 1:
                    col_1, col_2 = col_2, col_1
                code[i:i + 1] = list(zip(col_1, col_2))
                yield (Move.J_MINUS_ADD, Curve(code))
                if A == self.OUT:
                    yield (Move.J_MINUS_ADD, Curve(swap_out(code, D)))
            else:
                F0 = code[edge_1[0]][edge_1[1]]
                assert F0 == code[edge_2[0]][edge_2[1]]
                F1 = code[edge_1[0]][1 - edge_1[1]]
                F2 = code[edge_2[0]][1 - edge_2[1]]

                new_e1 = [(F1, F0), (C, F2), (F1, D)]
                new_e2 = [(F0, F2), (F1, C), (D, F2)]

                if edge_1[1] != 1:
                    new_e1 = [tuple(reversed(pair)) for pair in reversed(new_e1)]
                if edge_2[1] != 0:
                    new_e2 = [tuple(reversed(pair)) for pair in reversed(new_e2)]

                # F0 will get split up into two faces.
                # One will remain F0 and the other will be D.
                F0_references = list(self.face_iterator(*edge_2))
                for i, j in F0_references:
                    if (i, j) == edge_1:
                        break
                    # equivalent to code[i][j] = D
                    pair = list(code[i])
                    pair[j] = D
                    code[i] = tuple(pair)

                assert edge_1[0] < edge_2[0]
                code[edge_2[0]:edge_2[0] + 1] = new_e2
                code[edge_1[0]:edge_1[0] + 1] = new_e1

                sign = Move.J_MINUS_ADD if edge_1[1] == edge_2[1] else Move.J_PLUS_ADD
                yield (sign, Curve(code))
                if F0 == self.OUT:
                    yield (sign, Curve(swap_out(code, D)))

        for face_list in index.values():
            for edge_1, edge_2 in combinations_with_replacement(face_list, 2):
                yield from ways_to_link_edges(edge_1, edge_2)

    def decreasing_j_neighbors(self, index=None):
        if len(self) <= 2:
            # canonical 2-curve does not have any separable bigons.
            return
        if index is None:
            index = self.face_index()
        bigons = [locations for face, locations in index.items()
                  if len(locations) == 2 and face != self.OUT]

        if bigons and len(self) == 4:
            triple_eight = Curve([(0, -1), (-1, 1), (2, -1), (-1, 1)])
            eight_inside = Curve([(0, -1), (1, 0), (0, 2), (1, 0)])
            # ensure equality checks do not affect index
            copy = Curve(self)
            if copy in (triple_eight, eight_inside):
                yield (Move.J_MINUS_REMOVE, Curve.canonical(1))
            elif copy in (reversed(triple_eight), reversed((eight_inside))):
                yield (Move.J_MINUS_REMOVE, Curve.canonical(-1))
            else:
                assert copy in (Curve.canonical(2), Curve.canonical(-2))
            return

        def separated_bigons(i1, j1, i2, j2):
            code = list(self)
            old_face = code[i1 - 1][1 - j1]
            new_face = code[(i1 + 1) % len(code)][1 - j1]

            if old_face == self.OUT:
                new_face, old_face = old_face, new_face

            assert {old_face, new_face} \
                   == {code[i2 - 1][1 - j2], code[(i2 + 1) % len(code)][1 - j2]}

            # one of these is redundant if there is a self loop
            code[i1] = None
            code[i1 - 1] = None
            code[i2] = None
            code[i2 - 1] = None

            c = Curve(
                tuple(new_face if x == old_face else x for x in pair)
                for pair in code if pair is not None
            )

            direction = Move.J_MINUS_REMOVE if j1 == j2 else Move.J_PLUS_REMOVE
            return (direction, c)

        for (i1, j1), (i2, j2) in bigons:
            yield separated_bigons(i1, j1, i2, j2)

    def strange_neighbors(self, index=None):
        if index is None:
            index = self.face_index()
        triangles = [locations for face, locations in index.items()
                     if len(locations) == 3 and face != self.OUT]

        n = len(self)
        for (i1, j1), (i2, j2), (i3, j3) in triangles:

            if any(self._index_distance(*pair) <= 1
                   for pair in combinations([i1, i2, i3], 2)):
                # not three distinct vertices, doesn't count
                continue

            code = list(self)

            F0 = code[i1][j1]
            assert F0 == code[i2][j2] == code[i3][j3]

            outsides = [
                {code[i1-1][1-j1], code[(i1+1)%n][1-j1]},
                {code[i2-1][1-j2], code[(i2+1)%n][1-j2]},
                {code[i3-1][1-j3], code[(i3+1)%n][1-j3]},
            ]

            F1 = outsides[1] & outsides[2]
            F2 = outsides[0] & outsides[2]
            F3 = outsides[0] & outsides[1]
            if len(F1) > 1: F1 -= outsides[0]
            if len(F2) > 1: F2 -= outsides[1]
            if len(F3) > 1: F3 -= outsides[2]
            (F1, F2, F3) = (*F1, *F2, *F3)

            for i, j, new_face in [
                (i1, j1, F1),
                (i2, j2, F2),
                (i3, j3, F3)
            ]:
                pair = list(reversed(code[i]))
                pair[j] = new_face
                code[i] = tuple(pair)

            (_i1, _j1), (_i2, _j2), (_i3, _j3) = self.face_iterator(i1, j1)
            assert {i1, i2, i3} == {_i1, _i2, _i3}
            assert code[_i3][_j3] == code[_i3][_j3] == code[_i3][_j3]

            triangle_orientation = self._triple_sign(_i1, _i2, _i3)
            signs = [{0:+1, 1:-1}[j] for j in (j1,j2,j3)]
            q = sum(1 for s in signs if s == triangle_orientation)
            move_code = Move.strange(q, triangle_orientation)

            yield (move_code, Curve(code))

    def neighbors(self):
        yield from self.decreasing_r1_neighbors()
        index = self.face_index()
        yield from self.decreasing_j_neighbors(index)
        yield from self.strange_neighbors(index)
        yield from self.increasing_j_neighbors(index)
        yield from self.increasing_r1_neighbors()



    def _check_invariants(self):
        code = self._code
        quadruples = set()
        for i, pair2 in enumerate(code):
            pair1 = code[i - 1]
            q = tuple(pair1) + tuple(reversed(pair2))
            assert q[0] != q[1] != q[2] != q[3] != q[0]
            assert q not in quadruples
            quadruples.add(q)

        for q in quadruples:
            assert (cw_shift(q) in quadruples) ^ (ccw_shift(q) in quadruples)

        return True
