from collections import deque, Counter
from enum import Enum, auto
from itertools import combinations_with_replacement

class Move(Enum):
    R1_CCW_ADD = 101
    R1_CW_ADD = 102
    R1_CCW_REMOVE = 103
    R1_CW_REMOVE = 103

    J_PLUS_ADD = 201
    J_PLUS_REMOVE = 202
    J_MINUS_ADD = 203
    J_MINUS_REMOVE = 204

    S_PLUS = 301
    S_MINUS = 302


def clockwise(order):
    return tuple(order[i - 1] for i in range(len(order)))

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

    def reversed(self):
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
                            return False
                        else:
                            iso[val_1] = val_2
                            iso_range.add(val_2)
                    elif existing_val_2 != val_2:
                        return False
            return True

        for _ in range(len(self)):
            if isomorphic_sequences(self, other):
                return True
            self._code.rotate(1)
        return False

    def __hash__(self):
        lefts = Counter(x for (x,y) in self)
        rights = Counter(y for (x,y) in self)

        def face_code(x):
            result = (lefts[x], rights[x])
            if x == self.OUT:
                result = result + ('OUT',)
            return hash(result)

        edge_codes = [hash((face_code(x), face_code(y))) for (x,y) in self]

        consecutive_triples = Counter(
            (edge_codes[i-2], edge_codes[i-1], edge_codes[i])
            for i in range(len(edge_codes))
        )

        return hash(frozenset(consecutive_triples.items()))

    @classmethod
    def canonical(cls, w: int):
        if w > 0:
            return cls(pair for i in range(1, w-1+1)
                            for pair in [(0, cls.OUT), (i, 0)])
        elif w == 0:
            return cls([(0, cls.OUT)])
        else:
            return reversed(cls.canonical(abs(w)))

    def whitney(self):
        while True:
            x, y = self._code[0]
            if x == self.OUT:
                w = 1
                break
            if y == self.OUT:
                w = -1
                break

        orders = dict()
        for i, edge2 in enumerate(self._code):
            edge1 = self._code[i-1]
            order = edge2+reversed(edge1)
            s = frozenset(Counter(order).items())
            existing = orders.get(s)
            if existing is None:
                orders[s] = order
            elif order == clockwise(existing):
                w += 1
            elif existing == clockwise(order):
                w -= 1
            else:
                assert False
        return w

    def face_index(self):
        index = dict()
        for i, (x,y) in enumerate(self._code):
            index.setdefault(x, []).append((i, 0))
            index.setdefault(y, []).append((i, 1))
        return index

    def increasing_r1_neighbors(self):
        """For each edge, you can make a new loop on the left or on the right."""
        code = self._code
        new_face = max(face for pair in code for face in pair)
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
            elif pair1[1] == pair2[0] and pair2[0] != self.OUT:
                return -1
            else:
                return None

        code = self._code

        for _ in range(len(code)):
            result = is_empty_1_gon(code[-1], code[0], code[1%len(code)])
            if result == +1:
                code_iter = iter(code)
                next(code_iter), next(code_iter)
                yield (Move.R1_CCW_REMOVE, Curve(code_iter))
            elif result == -1:
                code_iter = iter(code)
                next(code_iter), next(code_iter)
                yield (Move.R1_CW_REMOVE, Curve(code_iter))
            code.rotate(1)

    def face_iterator(self, start):
        code = self._code
        positions = dict()
        for i, (f4, f3) in enumerate(code):
            (f1, f2) = code[i-1]
            quadruple = frozenset((f1, f2, f3, f4))
            positions.setdefault(quadruple, []).append(i)

        if len(code) >= 1:
            assert all(len(x)==2 for x in positions)

        def twin(vertex_index):
            i = vertex_index
            f1, f2 = code[i-1]
            f4, f3 = code[i]
            vert_indices = positions[frozenset((f1, f2, f3, f4))]
            (other_index,) = set(vert_indices) - {i}
            return other_index


        i, j = start
        while True:
            yield (i, j)

            # get index of next vertex
            if j == 0:
                next_i = (i + 1) % len(code)
                twin_pos = twin(next_i)
            else:
                assert j == 1
                twin_pos = twin(i)

            # get
            if code[twin_pos][0] == code[i][j]:
                i, j = twin_pos, 0
            else:
                assert code[twin_pos][1] == code[i][1-j]
                i, j = (twin_pos - 1) % len(code), 1

            if (i, j) == start:
                break



    def increasing_j_neighbors(self, index=None):
        if index is None:
            index = self.face_index()

        # labels for new faces
        C = max(face for pair in self for face in pair)
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

        def link_edges(edge_1, edge_2):
            code = list(self)
            if edge_1 == edge_2:
                i, j = edge_1
                face_pair = code[i]
                A, B = face_pair[j], face_pair[1-j]
                col_1 = [A, B, D, B, C]
                col_2 = [B, C, B, C, B]
                if j == 1:
                    col_1, col_2 = col_2, col_1
                code[i:i+1] = list(zip(col_1, col_2))
                yield (Move.J_MINUS_ADD, Curve(code))
                if A == self.OUT:
                    yield (Move.J_MINUS_ADD, Curve(swap_out(code, A)))
            else:
                F0 = code[edge_1[0]][edge_1[1]]
                assert F0 == code[edge_2[0]][edge_2[1]]
                F1 = code[edge_1[0]][1 - edge_1[1]]
                F2 = code[edge_2[0]][1 - edge_2[1]]

                def half_edge_iterator(start_pos, end_pos):
                    ...
                # F0 will get split up into two faces.
                # One will remain F0 and the other will be D.


        for face_list in index:
            for edge_1, edge_2 in combinations_with_replacement(face_list, 2):
                yield from link_edges(edge_1, edge_2)

    def decreasing_j_neighbors(self, index=None):
        pass

    def strange_neighbors(self, index=None):
        if index is None:
            index = self.face_index()
        triangles = [face for face in index if len(face)==3]