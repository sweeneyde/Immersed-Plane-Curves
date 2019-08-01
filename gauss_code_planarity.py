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

        # A: increment i to get to a second node occurrence
        while True:
            i += 1
            if i == len(arr):
                # no more to check
                return True
            if i > twin[i]:
                break

        s = -1
        j = i
        # B: what the fuck
        # traverse the image graph

        while True:
            j += s
            if j >= i:
                assert j == i
                return False
            elif j == -1:
                s = -s
            elif i > twin[j]:
                s *= v(j)
                j = twin[j]
            elif i == twin[j] and s == v(i):
                break


if __name__=="__main__":
    assert planar([+1, -2, +3, -1, +2, -3])
    assert not planar([+1, -2, +3, -4, +5, -3, +4, -1, +2, -5])