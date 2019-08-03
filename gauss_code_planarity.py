def planar(arr):
    BASE = 999999
    arr = [-BASE] + arr + [BASE]

    def v(i):
        return 1 if arr[i]>0 else -1

    index = {x: i for i, x in enumerate(arr)}
    twin = {i:index[-arr[i]] for i in range(len(arr))}

    assert all(
        j != twin[j]
        and j == twin[twin[j]]
        and {v(j), v(twin[j])} == {-1, 1}
        for j in range(len(arr))
    )

    ##################################

    def right_turn(j, dj):
        return twin[j], dj*v(j)

    def second_time_indices():
        for i in range(len(arr)):
            if twin[i] < i:
                yield i

    for i in second_time_indices():
        j, dj = i, -1
        # On the image-graph of the path from 0 to i,
        # traverse a face by only making right turns.
        while True:
            j += dj
            if j == -1:
                # if you get to the base point, just turn around.
                dj = +1
            elif j == i:
                # The two quadrants of the `T` intersection at i
                # are in the same face. This isn't possible.
                return False
            elif twin[j] < i:
                # If the crossing strand is part of path considered,
                # then make a right turn.
                j, dj = right_turn(j, dj)
            elif right_turn(j, dj) == (i, -1):
                # We walked around the whole face.
                break
    return True


if __name__=="__main__":
    assert planar([+1, -2, +3, -1, +2, -3])
    assert not planar([+1, -2, +3, -4, +5, -3, +4, -1, +2, -5])
