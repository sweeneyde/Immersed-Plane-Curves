import sqlite3
import time
import os

from curve_code import Curve, Move

schema_sql = '''\
PRAGMA writable_schema = 1;
delete from sqlite_master where type in ('table', 'index', 'trigger');
PRAGMA writable_schema = 0;
VACUUM;
PRAGMA INTEGRITY_CHECK;

CREATE TABLE curve (
    id INTEGER PRIMARY KEY NOT NULL,
    hash INTEGER NOT NULL,
    num_vertices INTEGER NOT NULL,
    whitney INTEGER NOT NULL,
    explored INTEGER NOT NULL,
    distance INTEGER NOT NULL
);
CREATE INDEX idx_hash ON curve (hash);
CREATE INDEX idx_num_vertices ON curve(num_vertices);
CREATE INDEX idx_distance ON curve(explored, distance, num_vertices);

CREATE TABLE curve_edge (
    curve_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    left_face INTEGER NOT NULL,
    right_face INTEGER NOT NULL,
    
    PRIMARY KEY (curve_id, position),
    FOREIGN KEY (curve_id) REFERENCES curve (id)
);

CREATE TABLE move_type (
    id INTEGER PRIMARY KEY NOT NULL,
    description TEXT
);

CREATE TABLE move (
    start_curve_id INTEGER NOT NULL,
    end_curve_id INTEGER NOT NULL,
    type_id INTEGER NOT NULL,
    multiplicity INTEGER,
    
    PRIMARY KEY (start_curve_id, end_curve_id, type_id),
    FOREIGN KEY (start_curve_id) REFERENCES curve (id),
    FOREIGN KEY (end_curve_id) REFERENCES curve (id),
    FOREIGN KEY (type_id) REFERENCES move_type (id)
);
'''

def initialize(c):
    c.executescript(schema_sql)
    c.executemany("""
            INSERT into move_type VALUES (?, ?);
        """, ((move.value, move.name) for move in Move))

start = time.time()
dbsize = 0
hits = 0
misses = 0

def print_progress(c):
    print(f"{time.time() - start:.2f}  Size: {dbsize / 10 ** 6:.2f}M.  "
          f"Hits: {hits}.  Misses: {misses}.  {hits / (hits+misses):.2%}")
    c.execute("""
        SELECT num_vertices, distance, count(*) 
        FROM curve GROUP BY num_vertices, distance
    """)
    counts = dict()
    for v, d, n in c.fetchall():
        counts.setdefault(v, dict())[d] = n

    print("depth: ", max(d for ds in counts.values() for d in ds))

    for v, distances in counts.items():
        print(v, sum(distances.values()), distances)

    print()


def insert_curve(c, curve: Curve, distance):
    c.execute("""
        INSERT INTO curve (hash, num_vertices, whitney, explored, distance)
            VALUES (?, ?, ?, ?, ?);
    """, (hash(curve), curve.num_vertices(), curve.whitney(), 0, distance))
    cid = c.lastrowid

    c.executemany("""
        INSERT INTO curve_edge (curve_id, position, left_face, right_face)
        VALUES (?, ?, ?, ?);
    """, ((cid, i, a, b) for i, (a, b) in enumerate(curve)))

    global dbsize
    dbsize += 1
    if dbsize % 50_000 == 0:
        print_progress(c)

    return cid


def unexplored_ids_bfs(c):
    highest_min_left = 0
    while True:
        c.execute("""
            SELECT id FROM curve 
            WHERE explored = 0
            ORDER BY distance ASC, num_vertices ASC
            LIMIT 1
        """)
        (cid,) = c.fetchone()
        yield cid

        global dbsize
        if dbsize % 1000 != 0:
            continue

        c.execute("SELECT min(num_vertices) FROM curve WHERE explored=0")
        (min_left,) = c.fetchone()

        if min_left > highest_min_left:
            n = min_left - 1
            print('-' * 80)
            print(f"No v<={n} found; Any new {n}s must go through {n+1}.")
            print(f"Found all {n-2}, almost all {n-1}, most {n}.")
            print_progress(c)
            highest_min_left = min_left

def unexplored_ids_vert_first(c):
    highest_min_left = 1
    while True:
        c.execute("""
            SELECT id FROM curve
            WHERE explored = 0
            AND num_vertices <= ?
            ORDER BY num_vertices ASC
            LIMIT 1
        """, (highest_min_left,))

        cid = c.fetchone()
        if cid is None:
            n = highest_min_left
            print('-' * 80)
            print(f"No v<={n} found; Any new {n}s must go through {n+1}.")
            print(f"Found all {n-2}, almost all {n-1}, most {n}.")
            print_progress(c)
            highest_min_left += 1
        else:
            yield cid[0]


def fetch_curve(c, cid) -> Curve:
    c.execute("""
        SELECT left_face, right_face FROM curve_edge
        WHERE curve_id = ? ORDER BY position
    """, (cid,))
    return Curve(c.fetchall())

def get_cid(c, curve, distance_if_inserting):
    h = hash(curve)
    c.execute("""
        SELECT id FROM curve WHERE hash = ?
    """, (h,))

    for (cid,) in c.fetchall():
        curve_candidate = fetch_curve(c, cid)
        if curve_candidate == curve:
            global hits
            hits += 1
            return cid

    global misses
    misses += 1
    return insert_curve(c, curve, distance_if_inserting)


def add_edge(c, curve1, curve1_id, move, curve2, c2_distance):
    cid2 = get_cid(c, curve2, c2_distance)
    c.execute("""
        SELECT multiplicity FROM move 
        WHERE start_curve_id = ? AND end_curve_id = ? and type_id = ?
    """, (curve1_id, cid2, move.value))

    move_rows = c.fetchall()
    if move_rows:
        ((mult,),) = move_rows
        c.execute("""
            UPDATE move SET multiplicity = ? 
            WHERE start_curve_id = ? AND end_curve_id = ? and type_id = ?
        """, (mult+1, curve1_id, cid2, move.value))
    else:
        c.execute("""
            INSERT INTO move (start_curve_id, end_curve_id, type_id, multiplicity)
            VALUES (?, ?, ?, ?)
        """, (curve1_id, cid2, move.value, 1))

        # c.execute("""
        #     UPDATE curve SET distance = min(distance, ?) WHERE id = ?
        # """, (c2_distance, cid2))
        # c.execute("""
        #     SELECT distance from curve WHERE id = ?
        # """, (cid2,))
        # assert c.fetchone()[0] <= c2_distance


def process_cid(c, cid):
    curve = fetch_curve(c, cid)

    c.execute("""
        SELECT distance FROM curve WHERE id = ?
    """, (cid,))
    (d,) = c.fetchone()

    for move, c2 in curve.neighbors():
        add_edge(c, curve, cid, move, c2, d+1)
    c.execute("""
        UPDATE curve SET explored = 1 WHERE id = ?
    """, (cid,))



if __name__ == '__main__':
    conn = sqlite3.connect('ipc.db')
    c = conn.cursor()

    initialize(c)

    insert_curve(c, Curve.canonical(1), 0)

    for cid in unexplored_ids_bfs(c):
        process_cid(c, cid)

