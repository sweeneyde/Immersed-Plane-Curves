from enum import Enum, auto

object_count = 0


class orientation(Enum):
    """
    Encodes the orientation of each strand in a crossing:
          ^
          | Y
          |
          |      X
    ------+------->
          |
          |
          |
    """
    X = auto()
    Y = auto()


class direction(Enum):
    CCW = auto()
    CW = auto()


class HalfEdge(object):
    __slots__ = [
        'target',
        'twin',
        'face',
        'face_next',
        'face_prev',
        'id',
    ]

    def __init__(self):
        global object_count
        self.id = object_count
        object_count += 1

    def _type_hints(self):
        self.target: Vertex
        self.twin: HalfEdge
        self.face: Face
        self.face_next: HalfEdge
        self.face_prev: HalfEdge
        self.id: int

    @classmethod
    def twin_pair(cls, source, dest):
        forward, back = cls(), cls()
        forward.twin = back
        back.twin = forward
        forward.target = dest
        back.target = source
        return forward, back

    def __str__(self):
        return f"H{self.id}"

    __repr__ = __str__


class Vertex(object):
    __slots__ = 'x_out', 'y_out', 'id'
    x_out: HalfEdge
    y_out: HalfEdge
    id: int

    vertex_count = 0

    def __init__(self):
        global object_count
        self.id = object_count
        object_count += 1

    def __str__(self):
        return f"V{self.id}"

    __repr__ = __str__


class Face(object):
    __slots__ = 'some_edge', 'id'
    some_edge: HalfEdge

    count = 0

    def __init__(self, h: HalfEdge):
        self.some_edge: HalfEdge = h
        global object_count
        self.id = object_count
        object_count += 1

    def __str__(self):
        return f"F{self.id}"

    __repr__ = __str__


class Curve(object):
    __slots__ = ['outside_face', 'circle_direction', 'crossings', 'whitney']
    outside_face: Face
    circle_direction: direction
    crossings: int
    whitney: int
    CCW = direction.CCW
    CW = direction.CW

    def __init__(self, circle_direction=None):
        self.circle_direction = circle_direction

    def node_iter(self, start_halfedge=None):
        if self.circle_direction in (self.CCW, self.CW):
            return

        if start_halfedge is None:
            start_halfedge = self.outside_face.some_edge.target.x_out
        current_halfedge = start_halfedge
        while True:
            target = current_halfedge.target
            current_halfedge = current_halfedge.face_next.twin.face_next
            if current_halfedge is target.x_out:
                dir = orientation.X
            elif current_halfedge is target.y_out:
                dir = orientation.Y
            else:
                assert False
            yield target, dir

            if current_halfedge is start_halfedge:
                break

    def face_edge_count(self, face: Face):
        return sum(1 for edge in self.face_edge_iter(face.some_edge))

    def edge_iter(self, start_halfedge=None):
        if self.circle_direction is self.CCW:
            yield self.outside_face.some_edge.twin
            return
        if self.circle_direction is self.CW:
            yield self.outside_face.some_edge
            return

        if start_halfedge is None:
            start_halfedge = self.outside_face.some_edge.target.x_out

        current_halfedge = start_halfedge
        while True:
            yield current_halfedge
            current_halfedge = current_halfedge.face_next.twin.face_next
            if current_halfedge is start_halfedge:
                break

    def face_edge_iter(self, start_halfedge, reversed=False):
        if self.circle_direction is not None:
            yield start_halfedge
            return
        current_halfedge = start_halfedge
        while True:
            yield current_halfedge
            if reversed:
                current_halfedge = current_halfedge.face_prev
            else:
                current_halfedge = current_halfedge.face_next
            if current_halfedge is start_halfedge:
                break

    def _get_whitney(self):
        if self.circle_direction is self.CCW:
            return 1
        if self.circle_direction is self.CW:
            return -1

        seen = set()
        outside_halfedge = self.outside_face.some_edge

        if self.right_direction(outside_halfedge):
            score = -1
            start_halfedge = outside_halfedge
        else:
            score = 1
            start_halfedge = outside_halfedge.twin

        for v, direction in self.node_iter(start_halfedge):
            if v in seen:
                score += 1 if direction is direction.X else -1
            else:
                seen.add(v)

        return score

    def __len__(self):
        return self.crossings

    @staticmethod
    def right_direction(halfedge):
        """Does this halfedge go in the same direction as the curve?"""
        source = halfedge.twin.target
        return halfedge is source.x_out or halfedge is source.y_out

    def kink(self, halfedge: HalfEdge):
        """Add a kink (1-gon) to some halfedge:

        BEFORE ==================================

                  (opposite_face)
                   ------twin---->
            target <---halfedge--- source
                    (outside_face)

        AFTER ===================================

                    (opposite_face)
                   ---knt--->   ---kpt--->
            target <---kn---- v <---kp---- source
                            //  \\
                           ||(nf)||
             (outside_f.)   \\   //
                              --> ko
                              <-- ki

        """

        # Special cases for circles ====================

        self.crossings += 1
        self.whitney += 1 if self.right_direction(halfedge) else -1

        if self.circle_direction in (self.CCW, self.CW):
            if halfedge.face is self.outside_face:
                # replace self
                self.outside_face = self.__class__ \
                    ._figure_eight() \
                    .outside_face
            else:
                self.outside_face = self.__class__ \
                    ._canonical_2_curve(
                    self.circle_direction is self.CCW
                ).outside_face
            self.circle_direction = None
            return self.outside_face.some_edge

        # Capture the current state =====================

        target = halfedge.target
        twin = halfedge.twin
        source = twin.target
        outside_face = halfedge.face
        opposing_face = twin.face

        # Construct the new stuff =======================

        v = Vertex()
        kink_inside, kink_outside = HalfEdge.twin_pair(v, v)
        kink_prev, kink_prev_twin = HalfEdge.twin_pair(source, v)
        kink_next, kink_next_twin = HalfEdge.twin_pair(v, target)
        new_face = Face(kink_inside)

        # update x_out and y_out ========================

        if halfedge is source.x_out:
            right_direction = True
            source.x_out = kink_prev
        elif halfedge is source.y_out:
            right_direction = True
            source.y_out = kink_prev
        elif twin is target.x_out:
            right_direction = False
            target.x_out = kink_next_twin
        elif twin is target.y_out:
            right_direction = False
            target.y_out = kink_next_twin
        else:
            assert False

        if right_direction:
            v.x_out = kink_next
            v.y_out = kink_inside
        else:
            v.x_out = kink_outside
            v.y_out = kink_prev_twin

        # Update face_next and face_prev ========================

        for _ in range(2):
            # make sure to repeat twice so that self-references are fixed.
            outside_line = [halfedge.face_prev, kink_prev, kink_outside, kink_next, halfedge.face_next]
            opposite_line = [twin.face_prev, kink_next_twin, kink_prev_twin, twin.face_next]
            for edge_sequence in outside_line, opposite_line:
                for i in range(len(edge_sequence) - 1):
                    prev, next = edge_sequence[i:i + 2]
                    prev.face_next = next
                    next.face_prev = prev

        kink_inside.face_next = kink_inside.face_prev = kink_inside

        # Update faces ==========================================

        for outside in outside_line:
            outside.face = outside_face
        for opposing in opposite_line:
            opposing.face = opposing_face
        kink_inside.face = new_face

        new_face.some_edge = kink_inside
        outside_face.some_edge = kink_outside
        opposing_face.some_edge = kink_next_twin

        return kink_outside

    def unkink_onegon(self, onegon: Face):
        in_side = onegon.some_edge
        assert in_side.face_next is in_side
        assert in_side.face is not self.outside_face
        out_side = in_side.twin
        kink_next = out_side.face_next
        kink_prev = out_side.face_prev
        kink_next_twin = kink_next.twin
        kink_prev_twin = kink_prev.twin
        outside_face = out_side.face
        opposite_face = kink_next_twin.face
        kink_vertex = in_side.target
        target = kink_next.target
        source = kink_prev_twin.target

        self.crossings -= 1
        self.whitney -= 1 if self.right_direction(in_side) else -1

        if kink_vertex is target:
            # degenerate to circle
            assert kink_vertex is source
            if opposite_face is self.outside_face:
                # double loop to circle
                if kink_vertex.x_out is kink_next:
                    self.outside_face = self.__class__._circle(self.CCW).outside_face
                    self.circle_direction = self.CCW
                elif kink_vertex.x_out is out_side:
                    self.outside_face = self.__class__._circle(self.CW).outside_face
                    self.circle_direction = self.CW
                else:
                    assert False
            else:
                # figure eight to circle
                if kink_vertex.x_out is in_side:
                    self.outside_face = self.__class__._circle(self.CW).outside_face
                    self.circle_direction = self.CW
                elif kink_vertex.x_out is out_side:
                    self.outside_face = self.__class__._circle(self.CCW).outside_face
                    self.circle_direction = self.CCW
                else:
                    assert False
            return

        new_forward, new_backward = HalfEdge.twin_pair(source, target)

        for _ in range(2):
            # correct self references the second time around
            new_forward.face_prev = kink_prev.face_prev
            new_forward.face_next = kink_next.face_next
            new_backward.face_prev = kink_next_twin.face_prev
            new_backward.face_next = kink_prev_twin.face_next
            new_forward.face_prev.face_next \
                = new_forward.face_next.face_prev \
                = new_forward
            new_backward.face_next.face_prev \
                = new_backward.face_prev.face_next \
                = new_backward

        if kink_prev is source.x_out:
            source.x_out = new_forward
        elif kink_prev is source.y_out:
            source.y_out = new_forward
        elif kink_next_twin is target.x_out:
            target.x_out = new_backward
        elif kink_next_twin is target.y_out:
            target.y_out = new_backward
        else:
            assert False

        new_forward.face = outside_face
        new_backward.face = opposite_face

        outside_face.some_edge = new_forward
        opposite_face.some_edge = new_backward

    def decouple_bigon(self, bigon_side1) -> HalfEdge:
        self.crossings -= 2
        side1 = bigon_side1
        side2 = side1.face_next
        assert side2.face_next is side1



        raise NotImplementedError()
        # return "new side1"

    def create_bigon(self, side1: HalfEdge, side2: HalfEdge) -> HalfEdge:
        self.crossings += 2
        assert side1.face is side2.face
        raise NotImplementedError()
        # returns new_outside1

    def invert_triangle(self, triangle_edge) -> HalfEdge:
        assert triangle_edge.face_next.face_next.face_next is triangle_edge
        raise NotImplementedError()

    def z_move(self, onegon: Face, facing_cutter: HalfEdge) -> HalfEdge:
        """move an empty 1-gon under another strand:
        Before:
          |
          |h  /--\
        --+--+---/
          |   \---------
        After:
              /--\   |returned
        -----+---/   |
              \------+--
                     |
        """

        bigon_outside = self.create_bigon(onegon.some_edge.twin, facing_cutter)
        triangle_outside = self.invert_triangle(bigon_outside.face_next.twin)
        bigon_cutter_inside = triangle_outside.face_next.twin.face_next.twin.face_prev.twin
        return self.decouple_bigon(bigon_cutter_inside)

    def is_canonical(self):
        w = self.whitney
        n = self.crossings
        if w==0:
            return n==1
        else:
            return n == abs(w) - 1

    def __str__(self):
        if self.circle_direction is self.CCW:
            return "CCW CIRCLE"
        if self.circle_direction is self.CW:
            return "CW CIRCLE"

        def face_label(face: Face):
            if face is self.outside_face:
                label = f'({face.id})'
            else:
                label = str(face.id)
            return label

        lines = [f"{self.__class__.__name__}(w={self.whitney}, n={len(self)})"]
        for edge in self.edge_iter():
            source = str(edge.twin.target.id)
            left_face = face_label(edge.twin.face)
            right_face = face_label(edge.face)
            lines += ["      {: ^3}".format(source),
                      "{: >5} {: ^3} {: <5}".format(right_face, edge.id, left_face)]

        return '\n'.join(lines)

    @classmethod
    def _figure_eight(cls):
        # Constructs the "figure 8" with Whitney number 0.
        vertex = Vertex()
        top_inside, top_outside = HalfEdge.twin_pair(vertex, vertex)
        bottom_inside, bottom_outside = HalfEdge.twin_pair(vertex, vertex)

        # vertex.label = "Origin"
        # top_inside.label = "top inside"
        # top_outside.label = "top outside"
        # bottom_inside.label = "bottom inside"
        # bottom_outside.label = "bottom outside"

        top_face, bottom_face, outside_face = \
            Face(top_inside), Face(bottom_inside), Face(top_outside)

        top_inside.face = top_face
        bottom_inside.face = bottom_face
        top_outside.face = bottom_outside.face = outside_face

        top_inside.face_next = top_inside.face_prev = top_inside
        bottom_inside.face_next = bottom_inside.face_prev = bottom_inside
        top_outside.face_next = top_outside.face_prev = bottom_outside
        bottom_outside.face_next = bottom_outside.face_prev = top_outside

        vertex.x_out = top_outside
        vertex.y_out = bottom_inside

        # store the outside face as the "entry point".
        result = cls()
        result.outside_face = outside_face
        result.whitney = 0
        result.crossings = 1
        return result

    @classmethod
    def _circle(cls, direction):
        in_side, out_side = HalfEdge.twin_pair(Vertex(), Vertex())
        interior, exterior = Face(in_side), Face(out_side)
        in_side.face, out_side.face = interior, exterior

        result = Curve(direction)
        result.outside_face = exterior
        result.crossings = 0
        result.whitney = 1 if direction is cls.CCW else -1
        return result

    @classmethod
    def _canonical_2_curve(cls, positive: bool):
        vertex = Vertex()
        inner_inside, inner_outside = HalfEdge.twin_pair(vertex, vertex)
        outer_inside, outer_outside = HalfEdge.twin_pair(vertex, vertex)

        outside_face = Face(outer_outside)
        middle_face = Face(inner_outside)
        inner_face = Face(inner_inside)

        inner_inside.face = inner_face
        inner_outside.face = outer_inside.face = middle_face
        outer_outside.face = outside_face

        outer_outside.face_next = outer_outside.face_prev = outer_outside
        inner_inside.face_next = inner_inside.face_prev = inner_inside
        outer_inside.face_next = outer_inside.face_prev = inner_outside
        inner_outside.face_next = inner_outside.face_prev = outer_inside

        if positive:
            vertex.x_out = outer_inside
            vertex.y_out = inner_inside
        else:
            vertex.x_out = inner_outside
            vertex.y_out = outer_outside

        # store the outside face as the "entry point".
        result = cls()
        result.outside_face = outside_face
        result.whitney = 2 if positive else -2
        result.crossings = 1

        assert result.face_edge_count(result.outside_face) == 1
        assert result.face_edge_count(result.outside_face
                                      .some_edge
                                      .twin.face) == 2
        assert result.face_edge_count(result.outside_face
                                      .some_edge
                                      .twin
                                      .face_next
                                      .twin
                                      .face) == 1

        return result

    @classmethod
    def canonical(cls, w: int):
        if w == 0:
            return cls._figure_eight()
        elif w == 1:
            return cls._circle(cls.CCW)
        elif w == -1:
            return cls._circle(cls.CW)
        else:
            curve = Curve._canonical_2_curve(w > 0)
            outside = curve.outside_face
            for _ in range(abs(w) - 2):
                curve.kink(curve.outside_face.some_edge.twin)
            assert curve.outside_face is outside
            return curve

    def _check_invariants(self):
        if self.circle_direction in (self.CCW, self.CW):
            assert self.outside_face is \
                   self.outside_face.some_edge.twin.face.some_edge.twin.face
            return

        node_dirs = list(self.node_iter())
        nodes = {node for node, dir in node_dirs}
        assert set(node_dirs) == {(node, d) for node in nodes
                                  for d in (orientation.X, orientation.Y)}

        assert self._get_whitney() == self.whitney
        assert len(nodes) == self.crossings

        for v in nodes:
            # ensure 4-regularity, correct orientation of x and y
            assert v.x_out.face_prev.twin is v.y_out
            assert v.y_out.twin.face_next is v.x_out
            assert v.x_out.twin.face_next.twin.face_next.twin.face_next is v.y_out
            assert v.y_out.face_prev.twin.face_prev.twin.face_prev.twin is v.x_out

        edges = list(self.edge_iter())
        assert len(edges) == 2 * len(nodes)
        for i, e1 in enumerate(edges):
            e0 = edges[i - 1]
            assert e1.twin.twin is e1
            assert e1.twin.target is e0.target
            assert e0.face_next.twin.target is e0.target
            assert e0.face_next.twin.face_next is e1
            assert e1.twin.face_next.twin.face_next.twin is e0
            for e in self.face_edge_iter(e1):
                assert e.face is e1.face


if __name__ == "__main__":
    c = Curve.canonical(-10)
    c._check_invariants()
    print(c)
    for i in range(9):
        c.unkink_onegon(c.outside_face.some_edge.twin.face_next.twin.face)
        c._check_invariants()
        assert c.is_canonical()
        print()
        print(c)
