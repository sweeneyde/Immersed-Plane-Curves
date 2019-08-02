def planar(arr):
    BASE = 0
    arr = [BASE] + arr + [BASE]

    n = (len(arr)-2)//2
    def v(i):
        if i==0:
            return +1
        elif i==2*n+1:
            return -1

        return 1 if arr[i]>0 else -1

    index = {x: i for i, x in enumerate(arr)}
    twin = {i:index[-arr[i]] for i in range(len(arr))}
    twin[2*n+1] = 0
    twin[0] = 2*n+1

    assert len(arr) == 2*n+2
    assert n >= 0
    assert arr[0] == arr[2*n+1] == BASE
    for j in range(len(arr)):
        j_twin = twin[j]
        assert j != j_twin
        assert twin[j_twin]==j
        assert {v(j), v(j_twin)} == {-1, 1}

    ##################################

    i = -1

    while True:

        # A: Walk along the path, highlighting it as you go, unit you hit something you;ve already hilighted.
        while True:
            i += 1
            if i == len(arr):
                # no more to check
                return True
            if i > twin[i]:
                # hit a wall
                break

        # B: Traverse the highlighted parts of the image graph.
        # begin by bouncing off of the hilighted wall you just hit
        # then make all right turns onto other highlighted paths.
        # skip over "unhighlighted" things you haven't seen yet.
        # Go all the way around the "face" back to the start's right-turn predecessor.
        # If you make it back to i (the twin of where you started), then it's not planar.
        s = -1
        j = i
        while True:
            j += s
            if i == j:
                # This shouldn't be possible.
                return False
            elif j == -1:
                # If we hit the basepoint, just turn around and keep going.
                s = -s
            elif twin[j] < i:
                # Hit a hilighted path, so make a right turn.
                s *= v(j)
                j = twin[j]
            elif j == twin[i] and s == v(i):
                # We hit the right-turn predecessor of the i where we started.
                break


if __name__=="__main__":
    assert planar([+1, -2, +3, -1, +2, -3])
    assert not planar([+1, -2, +3, -4, +5, -3, +4, -1, +2, -5])
