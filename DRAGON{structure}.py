"""
CURSOR CREATURE - a desktop pet that follows your mouse.

Run:
    pip install pygame
    python cursor_creature.py

Choose:
    - Creature
    - Colour
    - Display Mode:
        * Always On Top
        * Desktop Only

Hotkeys while it runs (Windows):
    Ctrl+Shift+Q = quit
    Ctrl+Shift+M = back to menu

Build an .exe:
    pip install pyinstaller
    pyinstaller --onefile --noconsole cursor_creature.py
"""

import math, os, sys, random
import pygame

WIN = sys.platform == "win32"

if WIN:
    import ctypes
    from ctypes import wintypes

    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


KEY = (255, 0, 255)
MENU_SIZE = (950, 650)


THEMES = {
    "Bone White":    dict(
        bg=(15, 15, 18),
        line=(235, 235, 240),
        bone=(205, 205, 212),
        membrane=(26, 26, 30),
        glow=(140, 170, 255)
    ),

    "Blood Red":     dict(
        bg=(14, 9, 9),
        line=(250, 210, 205),
        bone=(220, 140, 130),
        membrane=(42, 10, 10),
        glow=(255, 70, 60)
    ),

    "Toxic Green":   dict(
        bg=(8, 13, 9),
        line=(210, 255, 215),
        bone=(150, 220, 155),
        membrane=(8, 28, 12),
        glow=(110, 255, 130)
    ),

    "Ghost Blue":    dict(
        bg=(8, 10, 18),
        line=(215, 230, 255),
        bone=(150, 180, 230),
        membrane=(10, 14, 32),
        glow=(110, 170, 255)
    ),

    "Golden Relic":  dict(
        bg=(15, 12, 6),
        line=(255, 225, 160),
        bone=(212, 175, 110),
        membrane=(35, 25, 10),
        glow=(255, 200, 100)
    ),

    "Void Purple":   dict(
        bg=(10, 8, 16),
        line=(222, 192, 255),
        bone=(160, 120, 210),
        membrane=(22, 14, 34),
        glow=(180, 110, 255)
    ),

    "Icy Cyan":      dict(
        bg=(6, 14, 16),
        line=(200, 250, 255),
        bone=(120, 200, 215),
        membrane=(8, 28, 32),
        glow=(120, 230, 255)
    ),

    "Sunset Orange": dict(
        bg=(16, 9, 6),
        line=(255, 210, 170),
        bone=(230, 150, 90),
        membrane=(38, 18, 8),
        glow=(255, 140, 60)
    ),
}


COLORS = dict(THEMES["Bone White"])


def apply_theme(n):
    COLORS.update(THEMES[n])


# ---------------------------------------------------------------------------
# DISPLAY MODES
# ---------------------------------------------------------------------------

DISPLAY_MODES = [
    "Desktop Only",
    "Always On Top"
]


# leg tuple:
# (spine index, len1, len2, spread, forward offset, step trigger, toes)

TYPES = {
    "Dragon": dict(
        n=28,
        seg=13,
        w=12,
        keep=95,
        amp=14,
        wings=True,
        head=1.0,
        tag="Winged skeletal wyrm",
        legs=[
            (5, 27, 27, 50, 8, 30, 3),
            (16, 27, 27, 50, -4, 30, 3)
        ]
    ),

    "Serpent": dict(
        n=38,
        seg=11,
        w=10,
        keep=80,
        amp=26,
        wings=False,
        head=0.85,
        tag="Slithering spine of bone",
        legs=[]
    ),

    "Centipede": dict(
        n=30,
        seg=10,
        w=6,
        keep=70,
        amp=10,
        wings=False,
        head=0.5,
        tag="A hundred restless legs",
        legs=[
            (i, 12, 12, 20, 4, 9, 2)
            for i in range(3, 27, 2)
        ]
    ),

    "Spider": dict(
        tag="Eight-legged stalker"
    ),
}


# ------------------------------- helpers -----------------------------------

def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def lerp(a, b, t):
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t
    )


def mix(a, b, t):
    return tuple(
        int(a[i] + (b[i] - a[i]) * t)
        for i in range(3)
    )


def norm(x, y):
    d = math.hypot(x, y)

    if d:
        return (x / d, y / d)

    return (0.0, 0.0)


def rot(x, y, a):
    c, s = math.cos(a), math.sin(a)
    return x * c - y * s, x * s + y * c


def catmull(pts, k=4):
    if len(pts) < 3:
        return list(pts)

    p = [pts[0]] + list(pts) + [pts[-1]]
    out = []

    for i in range(1, len(p) - 2):

        p0, p1, p2, p3 = (
            p[i - 1],
            p[i],
            p[i + 1],
            p[i + 2]
        )

        for s in range(k):

            t = s / k
            t2 = t * t
            t3 = t2 * t

            out.append(
                tuple(
                    0.5 * (
                        2 * p1[j]
                        + (-p0[j] + p2[j]) * t
                        + (
                            2 * p0[j]
                            - 5 * p1[j]
                            + 4 * p2[j]
                            - p3[j]
                        ) * t2
                        + (
                            -p0[j]
                            + 3 * p1[j]
                            - 3 * p2[j]
                            + p3[j]
                        ) * t3
                    )
                    for j in (0, 1)
                )
            )

    out.append(pts[-1])

    return out


def ik(a, tgt, l1, l2, sign):

    dx = tgt[0] - a[0]
    dy = tgt[1] - a[1]

    d = min(
        max(math.hypot(dx, dy), abs(l1 - l2) + .01),
        l1 + l2 - .01
    )

    ang = math.acos(
        max(
            -1,
            min(
                1,
                (
                    l1 * l1
                    + d * d
                    - l2 * l2
                )
                / (2 * l1 * d)
            )
        )
    )

    k = math.atan2(dy, dx) + sign * ang

    return (
        a[0] + math.cos(k) * l1,
        a[1] + math.sin(k) * l1
    )


def ellipse(c, h, a, b, n=22):

    px, py = -h[1], h[0]

    return [
        (
            c[0]
            + h[0] * math.cos(t) * a
            + px * math.sin(t) * b,

            c[1]
            + h[1] * math.cos(t) * a
            + py * math.sin(t) * b
        )

        for t in (
            2 * math.pi * i / n
            for i in range(n)
        )
    ]


# ------------------------------- parts -------------------------------------

class Leg:

    """Two-bone IK leg that plants its foot and steps when stretched too far."""

    def __init__(s, side, l1, l2, spread, fwd, trig, toes=3):

        s.side = side
        s.l1 = l1
        s.l2 = l2
        s.spread = spread
        s.fwd = fwd
        s.trig = trig
        s.toes = toes

        s.base = None
        s.foot = None
        s.step = None
        s.t = 0

    def update(s, anchor, h, vel, center=None):

        px, py = -h[1], h[0]

        rest = (
            anchor[0]
            + h[0] * s.fwd
            + px * s.spread * s.side
            + vel[0] * .2,

            anchor[1]
            + h[1] * s.fwd
            + py * s.spread * s.side
            + vel[1] * .2
        )

        if s.base is None:
            s.base = s.foot = rest

        if s.step is None and dist(s.base, rest) > s.trig:
            s.step, s.t = (s.base, rest), 0

        if s.step:

            s.t = min(1, s.t + .17)

            e = s.t * s.t * (3 - 2 * s.t)

            s.base = lerp(
                s.step[0],
                s.step[1],
                e
            )

            s.foot = (
                s.base[0],
                s.base[1] - math.sin(s.t * math.pi) * 10
            )

            if s.t >= 1:
                s.step = None
                s.foot = s.base

        else:
            s.foot = s.base

        s.anchor = anchor

        k = ik(
            anchor,
            s.foot,
            s.l1,
            s.l2,
            -s.side
        )

        if center:

            k2 = ik(
                anchor,
                s.foot,
                s.l1,
                s.l2,
                s.side
            )

            if dist(k2, center) > dist(k, center):
                k = k2

        s.knee = k

    def draw(s, surf):

        pygame.draw.line(
            surf,
            COLORS["line"],
            s.anchor,
            s.knee,
            3
        )

        pygame.draw.line(
            surf,
            COLORS["line"],
            s.knee,
            s.foot,
            2
        )

        pygame.draw.circle(
            surf,
            COLORS["glow"],
            (
                int(s.knee[0]),
                int(s.knee[1])
            ),
            2
        )

        ux, uy = norm(
            s.foot[0] - s.knee[0],
            s.foot[1] - s.knee[1]
        )

        for i in range(s.toes):

            a = (
                i / (s.toes - 1) - .5
            ) * .9

            fx, fy = rot(ux, uy, a)

            pygame.draw.line(
                surf,
                COLORS["bone"],
                s.foot,
                (
                    s.foot[0] + fx * 9,
                    s.foot[1] + fy * 9
                ),
                1
            )


class Wing:

    def __init__(s, side):
        s.side = side

    def draw(s, surf, sh, h, ph):

        hx, hy = h

        px = -hy * s.side
        py = hx * s.side

        raw = math.sin(ph)

        flap = (
            math.copysign(
                abs(raw) ** .65,
                raw
            ) * .55
        )

        reach = (
            .72
            + .28 * (raw * .5 + .5)
        )

        ax, ay = norm(
            px * .75 - hx * .25,
            py * .75 - hy * .25 - .35
        )

        ax, ay = rot(
            ax,
            ay,
            flap * s.side
        )

        wrist = (
            sh[0] + ax * 50 * reach,
            sh[1] + ay * 50 * reach
        )

        tips = []

        for i in range(5):

            u = i / 4

            fx, fy = rot(
                ax,
                ay,
                (-.75 + u * 2.05) * s.side
            )

            L = (
                82
                * (1.08 - .5 * u)
                * reach
            )

            tips.append(
                (
                    wrist[0] + fx * L,
                    wrist[1] + fy * L
                )
            )

        mem = mix(
            COLORS["membrane"],
            COLORS["glow"],
            .12
        )

        for a, b in zip(
            tips,
            tips[1:]
        ):

            notch = lerp(
                lerp(a, b, .5),
                wrist,
                .5
            )

            pygame.draw.polygon(
                surf,
                mem,
                [wrist, a, notch, b]
            )

            pygame.draw.lines(
                surf,
                COLORS["line"],
                False,
                [a, notch, b],
                1
            )

        trail = (
            sh[0] - hx * 24,
            sh[1] - hy * 24
        )

        bn = lerp(
            lerp(tips[-1], trail, .5),
            wrist,
            .35
        )

        pygame.draw.polygon(
            surf,
            mem,
            [wrist, tips[-1], bn, trail]
        )

        pygame.draw.lines(
            surf,
            COLORS["line"],
            False,
            [tips[-1], bn, trail],
            1
        )

        pygame.draw.line(
            surf,
            COLORS["bone"],
            sh,
            wrist,
            3
        )

        for t in tips:
            pygame.draw.line(
                surf,
                COLORS["bone"],
                wrist,
                t,
                2
            )


def draw_head(surf, head, h, k=1.0):

    hx, hy = h

    px, py = -hy, hx

    P = lambda f, l: (
        head[0]
        + (hx * f + px * l) * k,

        head[1]
        + (hy * f + py * l) * k
    )

    pts = [
        P(-3, 10),
        P(20, 8),
        P(34, 0),
        P(20, -8),
        P(-3, -10)
    ]

    pygame.draw.polygon(
        surf,
        mix(
            COLORS["membrane"],
            COLORS["bone"],
            .2
        ),
        pts
    )

    pygame.draw.lines(
        surf,
        COLORS["line"],
        True,
        pts,
        2
    )

    for z in (-1, 1):

        b = P(-4, 8 * z)
        m = P(-24, 23 * z)
        t = P(-40, 29 * z)

        pygame.draw.line(
            surf,
            COLORS["bone"],
            b,
            m,
            3
        )

        pygame.draw.line(
            surf,
            COLORS["bone"],
            m,
            t,
            2
        )

        e = P(9, 6 * z)

        pygame.draw.circle(
            surf,
            COLORS["glow"],
            (
                int(e[0]),
                int(e[1])
            ),
            max(2, int(3 * k))
        )


def draw_body(surf, rp, W):

    curve = catmull(rp, 4)

    n = len(curve)

    L, R = [], []

    for i, p in enumerate(curve):

        q = curve[min(i + 1, n - 1)]
        o = curve[max(i - 1, 0)]

        ux, uy = norm(
            q[0] - o[0],
            q[1] - o[1]
        )

        t = i / (n - 1)

        w = (
            W
            * (.55 + .45 * min(1, t * 5))
            * (1 - t) ** .85
            + 1
        )

        L.append(
            (
                p[0] - uy * w,
                p[1] + ux * w
            )
        )

        R.append(
            (
                p[0] + uy * w,
                p[1] - ux * w
            )
        )

    pygame.draw.polygon(
        surf,
        mix(
            COLORS["membrane"],
            COLORS["bone"],
            .16
        ),
        L + R[::-1]
    )

    for k in range(6, n - 6, 3):

        pygame.draw.line(
            surf,
            mix(
                COLORS["bone"],
                COLORS["membrane"],
                .35
            ),
            L[k],
            R[k],
            1
        )

    pygame.draw.lines(
        surf,
        COLORS["line"],
        False,
        L,
        2
    )

    pygame.draw.lines(
        surf,
        COLORS["line"],
        False,
        R,
        2
    )

    pygame.draw.lines(
        surf,
        COLORS["glow"],
        False,
        curve,
        1
    )


# ------------------------------- creatures ---------------------------------

class Body:

    """Shared spring-driven head motion."""

    def _steer(s, pos, cur, dt, keep):

        dx = cur[0] - pos[0]
        dy = cur[1] - pos[1]

        d = math.hypot(dx, dy)

        if d > keep * 1.15:

            tx = cur[0] - dx / d * keep
            ty = cur[1] - dy / d * keep

        else:

            a = math.atan2(-dy, -dx) + .55

            tx = cur[0] + math.cos(a) * keep
            ty = cur[1] + math.sin(a) * keep

        vx = s.v[0] + (
            (tx - pos[0]) * 14
            - s.v[0] * 5.5
        ) * dt

        vy = s.v[1] + (
            (ty - pos[1]) * 14
            - s.v[1] * 5.5
        ) * dt

        sp = math.hypot(vx, vy)

        if sp > 1500:

            vx = vx * 1500 / sp
            vy = vy * 1500 / sp

            sp = 1500

        s.v = (vx, vy)
        s.speed = sp

        return (
            pos[0] + vx * dt,
            pos[1] + vy * dt
        )


class Creature(Body):

    def __init__(s, name, start):

        s.c = c = TYPES[name]

        s.pts = [
            (
                start[0] - i * c["seg"],
                start[1]
            )
            for i in range(c["n"])
        ]

        s.v = (0, 0)
        s.speed = 0
        s.phase = 0
        s.flap = 0
        s.heading = (1.0, 0.0)

        s.wings = (
            [Wing(1), Wing(-1)]
            if c["wings"]
            else []
        )

        s.legs = [
            (
                Leg(sd, *l[1:]),
                l[0]
            )
            for l in c["legs"]
            for sd in (1, -1)
        ]

        s.rp = list(s.pts)

    def update(s, cur, dt):

        c, p = s.c, s.pts

        p[0] = s._steer(
            p[0],
            cur,
            dt,
            c["keep"]
        )

        for i in range(1, len(p)):

            d = (
                dist(p[i - 1], p[i])
                or 1
            )

            p[i] = lerp(
                p[i - 1],
                p[i],
                c["seg"] / d
            )

        s.phase += dt * (
            2.5 + s.speed * .012
        )

        s.flap += dt * (
            5 + s.speed * .01
        )

        A = (
            .25
            + .75 * min(1, s.speed / 350)
        )

        n = len(p)

        for i in range(n):

            q = p[min(i + 1, n - 1)]
            o = p[max(i - 1, 0)]

            ux, uy = norm(
                q[0] - o[0],
                q[1] - o[1]
            )

            off = (
                math.sin(
                    s.phase - i * .42
                )
                * c["amp"]
                * A
                * min(1, i / 5)
            )

            s.rp[i] = (
                p[i][0] - uy * off,
                p[i][1] + ux * off
            )

        hx, hy = norm(
            s.rp[0][0] - s.rp[2][0],
            s.rp[0][1] - s.rp[2][1]
        )

        s.heading = norm(
            *lerp(
                s.heading,
                (hx, hy),
                .2
            )
        )

        for leg, idx in s.legs:
            leg.update(
                s.rp[idx],
                s.heading,
                s.v
            )

    def draw(s, surf, t=0):

        for w in s.wings:
            w.draw(
                surf,
                s.rp[3],
                s.heading,
                s.flap
            )

        for leg, _ in s.legs:
            leg.draw(surf)

        draw_body(
            surf,
            s.rp,
            s.c["w"]
        )

        a, b = s.rp[-2], s.rp[-1]

        ux, uy = norm(
            b[0] - a[0],
            b[1] - a[1]
        )

        pygame.draw.line(
            surf,
            COLORS["line"],
            b,
            (
                b[0] + ux * 16,
                b[1] + uy * 16
            ),
            2
        )

        draw_head(
            surf,
            s.rp[0],
            s.heading,
            s.c["head"]
        )


class Spider(Body):

    SLOTS = [
        (20, 34, 60),
        (6, 14, 76),
        (-8, -10, 76),
        (-22, -38, 62)
    ]

    def __init__(s, start):

        s.p = start
        s.v = (0, 0)
        s.speed = 0
        s.h = (1.0, 0.0)

        s.legs = [
            (
                Leg(
                    sd,
                    40,
                    44,
                    sp,
                    fw,
                    40,
                    2
                ),
                al
            )
            for al, fw, sp in s.SLOTS
            for sd in (1, -1)
        ]

    def update(s, cur, dt):

        s.p = s._steer(
            s.p,
            cur,
            dt,
            85
        )

        want = norm(
            cur[0] - s.p[0],
            cur[1] - s.p[1]
        )

        s.h = norm(
            *lerp(
                s.h,
                want,
                .12
            )
        )

        for leg, al in s.legs:

            leg.update(
                (
                    s.p[0] + s.h[0] * al,
                    s.p[1] + s.h[1] * al
                ),
                s.h,
                s.v,
                center=s.p
            )

    def draw(s, surf, t=0):

        for leg, _ in s.legs:
            leg.draw(surf)

        fill = mix(
            COLORS["membrane"],
            COLORS["bone"],
            .18
        )

        ab = ellipse(
            (
                s.p[0] - s.h[0] * 24,
                s.p[1] - s.h[1] * 24
            ),
            s.h,
            27,
            21
        )

        pygame.draw.polygon(
            surf,
            fill,
            ab
        )

        pygame.draw.polygon(
            surf,
            COLORS["line"],
            ab,
            2
        )

        for k in (-14, -4, 6):

            px, py = -s.h[1], s.h[0]

            c = (
                s.p[0]
                - s.h[0] * 24
                + s.h[0] * k,

                s.p[1]
                - s.h[1] * 24
                + s.h[1] * k
            )

            pygame.draw.line(
                surf,
                COLORS["bone"],
                (
                    c[0] + px * 10,
                    c[1] + py * 10
                ),
                (
                    c[0] - px * 10,
                    c[1] - py * 10
                ),
                1
            )

        ce = ellipse(
            (
                s.p[0] + s.h[0] * 12,
                s.p[1] + s.h[1] * 12
            ),
            s.h,
            16,
            13
        )

        pygame.draw.polygon(
            surf,
            fill,
            ce
        )

        pygame.draw.polygon(
            surf,
            COLORS["line"],
            ce,
            2
        )

        px, py = -s.h[1], s.h[0]

        for side in (-1, 1):

            for f, l in (
                (22, 4),
                (18, 8)
            ):

                e = (
                    s.p[0]
                    + s.h[0] * f
                    + px * l * side,

                    s.p[1]
                    + s.h[1] * f
                    + py * l * side
                )

                pygame.draw.circle(
                    surf,
                    COLORS["glow"],
                    (
                        int(e[0]),
                        int(e[1])
                    ),
                    2
                )

            b = (
                s.p[0]
                + s.h[0] * 26
                + px * 4 * side,

                s.p[1]
                + s.h[1] * 26
                + py * 4 * side
            )

            pygame.draw.line(
                surf,
                COLORS["bone"],
                b,
                (
                    b[0]
                    + s.h[0] * 9
                    - px * 3 * side,

                    b[1]
                    + s.h[1] * 9
                    - py * 3 * side
                ),
                3
            )


def make(name, start):
    return (
        Spider(start)
        if name == "Spider"
        else Creature(name, start)
    )


# ------------------------------- desktop overlay ----------------------------

def cursor():

    if WIN:

        p = POINT()

        ctypes.windll.user32.GetCursorPos(
            ctypes.byref(p)
        )

        return p.x, p.y

    return pygame.mouse.get_pos()


def key_down(vk):

    return (
        WIN
        and bool(
            ctypes.windll.user32.GetAsyncKeyState(vk)
            & 0x8000
        )
    )


def make_overlay(display_mode):

    pygame.display.quit()
    pygame.display.init()

    w, h = pygame.display.get_desktop_sizes()[0]

    os.environ["SDL_VIDEO_WINDOW_POS"] = "0,0"

    screen = pygame.display.set_mode(
        (w, h - 1),
        pygame.NOFRAME
    )

    pygame.display.set_caption(
        "Cursor Creature"
    )

    hwnd = None

    if WIN:

        u = ctypes.windll.user32

        u.GetWindowLongW.argtypes = [
            wintypes.HWND,
            ctypes.c_int
        ]

        u.GetWindowLongW.restype = ctypes.c_long

        u.SetWindowLongW.argtypes = [
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_long
        ]

        u.SetLayeredWindowAttributes.argtypes = [
            wintypes.HWND,
            wintypes.COLORREF,
            ctypes.c_ubyte,
            wintypes.DWORD
        ]

        u.SetWindowPos.argtypes = [
            wintypes.HWND,
            wintypes.HWND
        ] + [ctypes.c_int] * 4 + [wintypes.UINT]

        hwnd = pygame.display.get_wm_info()["window"]

        ex = u.GetWindowLongW(
            hwnd,
            -20
        )

        # -------------------------------------------------------------
        # Existing window settings:
        #
        # layered
        # click-through
        # tool window
        # no activate
        # -------------------------------------------------------------

        u.SetWindowLongW(
            hwnd,
            -20,
            ex
            | 0x80000       # WS_EX_LAYERED
            | 0x20          # WS_EX_TRANSPARENT
            | 0x80          # WS_EX_TOOLWINDOW
            | 0x08000000    # WS_EX_NOACTIVATE
        )

        u.SetLayeredWindowAttributes(
            hwnd,
            0x00FF00FF,
            0,
            1
        )

        # -------------------------------------------------------------
        # NEW:
        #
        # If "Always On Top" was selected:
        #     make the creature topmost.
        #
        # If "Desktop Only" was selected:
        #     DON'T make it topmost.
        #
        # This is the important part that fixes your problem.
        # -------------------------------------------------------------

        if display_mode == "Always On Top":

            u.SetWindowPos(
                hwnd,
                -1,             # HWND_TOPMOST
                0,
                0,
                0,
                0,
                0x0001
                | 0x0002
                | 0x0010
            )

        else:

            # Normal window.
            # It will stay behind normal applications.
            u.SetWindowPos(
                hwnd,
                -2,             # HWND_NOTOPMOST
                0,
                0,
                0,
                0,
                0x0001
                | 0x0002
                | 0x0010
            )

    return screen, hwnd


def run_overlay(name, theme, display_mode):

    apply_theme(theme)

    screen, hwnd = make_overlay(
        display_mode
    )

    clock = pygame.time.Clock()

    font = pygame.font.SysFont(
        "segoeui,arial",
        16
    )

    creature = make(
        name,
        cursor()
    )

    frame = 0

    while True:

        dt = min(
            clock.tick(60) / 1000,
            .033
        )

        for e in pygame.event.get():

            if (
                e.type == pygame.QUIT
                or (
                    e.type == pygame.KEYDOWN
                    and e.key == pygame.K_ESCAPE
                )
            ):
                return "quit"

        # -------------------------------------------------------------
        # HOTKEYS
        # -------------------------------------------------------------

        if (
            key_down(0x11)
            and key_down(0x10)
        ):

            if key_down(0x51):
                return "quit"

            if key_down(0x4D):
                return "menu"

        frame += 1

        # -------------------------------------------------------------
        # ONLY KEEP TOPMOST WHEN USER SELECTED:
        # "Always On Top"
        # -------------------------------------------------------------

        if (
            WIN
            and hwnd
            and display_mode == "Always On Top"
            and frame % 120 == 0
        ):

            ctypes.windll.user32.SetWindowPos(
                hwnd,
                -1,             # HWND_TOPMOST
                0,
                0,
                0,
                0,
                0x0001
                | 0x0002
                | 0x0010
            )

        screen.fill(KEY)

        creature.update(
            cursor(),
            dt
        )

        creature.draw(
            screen,
            frame / 60
        )

        if frame < 420:

            txt = font.render(
                "Ctrl+Shift+Q  quit     Ctrl+Shift+M  menu",
                False,
                COLORS["bone"]
            )

            screen.blit(
                txt,
                (
                    screen.get_width() // 2
                    - txt.get_width() // 2,
                    14
                )
            )

        pygame.display.flip()


# ------------------------------- launcher menu -------------------------------

def glow_text(font, s, col, glow):

    img = font.render(
        s,
        True,
        col
    )

    g = font.render(
        s,
        True,
        glow
    )

    w, h = g.get_size()

    g = pygame.transform.smoothscale(
        pygame.transform.smoothscale(
            g,
            (
                max(1, w // 5),
                max(1, h // 5)
            )
        ),
        (w, h)
    )

    return img, g


def run_menu(state):

    pygame.display.quit()
    pygame.display.init()

    os.environ.pop(
        "SDL_VIDEO_WINDOW_POS",
        None
    )

    os.environ["SDL_VIDEO_CENTERED"] = "1"

    scr = pygame.display.set_mode(
        MENU_SIZE
    )

    pygame.display.set_caption(
        "Cursor Creature"
    )

    clock = pygame.time.Clock()

    F = lambda z, b=False: pygame.font.SysFont(
        "segoeui,arial",
        z,
        bold=b
    )

    f_t = F(48, True)
    f_h = F(21, True)
    f_m = F(16)
    f_s = F(13, True)

    # -------------------------------------------------------------
    # STATE NOW CONTAINS:
    #
    # creature
    # theme
    # display mode
    # -------------------------------------------------------------

    name, theme, display_mode = state

    apply_theme(theme)

    names = list(TYPES)

    cards = [
        pygame.Rect(
            30,
            125 + i * 82,
            270,
            70
        )
        for i in range(len(names))
    ]

    panel = pygame.Rect(
        320,
        125,
        600,
        328
    )

    themes = list(THEMES)

    sw = [
        (
            themes[i],
            (181 + i * 84, 512)
        )
        for i in range(len(themes))
    ]

    # -------------------------------------------------------------
    # DISPLAY MODE BUTTONS
    # -------------------------------------------------------------

    desktop_btn = pygame.Rect(
        640,
        558,
        125,
        40
    )

    top_btn = pygame.Rect(
        775,
        558,
        125,
        40
    )

    start = pygame.Rect(
        345,
        610,
        260,
        52
    )

    dots = [
        [
            random.random() * 950,
            random.random() * 650,
            random.random() * 18 + 6,
            random.random() * 2 + 1
        ]
        for _ in range(70)
    ]

    pet = make(
        name,
        panel.center
    )

    t = 0.0

    while True:

        dt = min(
            clock.tick(60) / 1000,
            .033
        )

        t += dt

        mp = pygame.mouse.get_pos()

        for e in pygame.event.get():

            if (
                e.type == pygame.QUIT
                or (
                    e.type == pygame.KEYDOWN
                    and e.key == pygame.K_ESCAPE
                )
            ):
                return None

            if (
                e.type == pygame.MOUSEBUTTONDOWN
                and e.button == 1
            ):

                # -------------------------------------------------
                # CREATURE SELECTION
                # -------------------------------------------------

                for r, n in zip(
                    cards,
                    names
                ):

                    if (
                        r.collidepoint(e.pos)
                        and n != name
                    ):

                        name = n

                        pet = make(
                            name,
                            panel.center
                        )

                # -------------------------------------------------
                # COLOUR SELECTION
                # -------------------------------------------------

                for th, c in sw:

                    if (
                        math.hypot(
                            e.pos[0] - c[0],
                            e.pos[1] - c[1]
                        ) < 22
                    ):

                        theme = th

                        apply_theme(th)

                # -------------------------------------------------
                # DISPLAY MODE SELECTION
                # -------------------------------------------------

                if desktop_btn.collidepoint(e.pos):

                    display_mode = "Desktop Only"

                if top_btn.collidepoint(e.pos):

                    display_mode = "Always On Top"

                # -------------------------------------------------
                # AWAKEN
                # -------------------------------------------------

                if start.collidepoint(e.pos):

                    return (
                        name,
                        theme,
                        display_mode
                    )

        bg = COLORS["bg"]
        glow = COLORS["glow"]
        line = COLORS["line"]
        bone = COLORS["bone"]

        # -------------------------------------------------------------
        # GRADIENT BACKGROUND
        # -------------------------------------------------------------

        for y in range(0, 650, 10):

            pygame.draw.rect(
                scr,
                mix(
                    bg,
                    glow,
                    .12 * y / 650
                ),
                (
                    0,
                    y,
                    950,
                    10
                )
            )

        # -------------------------------------------------------------
        # DRIFTING EMBERS
        # -------------------------------------------------------------

        for d in dots:

            d[1] -= d[2] * dt

            if d[1] < -5:

                d[0] = random.random() * 950
                d[1] = 655

            pygame.draw.circle(
                scr,
                mix(
                    bg,
                    glow,
                    .35
                ),
                (
                    int(d[0]),
                    int(d[1])
                ),
                int(d[3])
            )

        # -------------------------------------------------------------
        # TITLE
        # -------------------------------------------------------------

        img, g = glow_text(
            f_t,
            "CURSOR CREATURE",
            line,
            glow
        )

        pos = (
            475 - img.get_width() // 2,
            28
        )

        scr.blit(
            g,
            pos,
            special_flags=pygame.BLEND_RGB_ADD
        )

        scr.blit(
            img,
            pos
        )

        sub = f_m.render(
            "Choose a creature and a colour. It will roam your desktop and follow your cursor.",
            True,
            bone
        )

        scr.blit(
            sub,
            (
                475 - sub.get_width() // 2,
                88
            )
        )

        # -------------------------------------------------------------
        # LABELS
        # -------------------------------------------------------------

        scr.blit(
            f_s.render(
                "CREATURE",
                True,
                glow
            ),
            (30, 104)
        )

        scr.blit(
            f_s.render(
                "LIVE PREVIEW",
                True,
                glow
            ),
            (320, 104)
        )

        # -------------------------------------------------------------
        # CREATURE CARDS
        # -------------------------------------------------------------

        for r, n in zip(
            cards,
            names
        ):

            sel = n == name
            hov = r.collidepoint(mp)

            pygame.draw.rect(
                scr,
                mix(
                    bg,
                    glow,
                    .22
                    if sel
                    else (
                        .12
                        if hov
                        else .05
                    )
                ),
                r,
                border_radius=12
            )

            pygame.draw.rect(
                scr,
                glow
                if sel
                else mix(
                    bone,
                    bg,
                    .6
                ),
                r,
                2,
                border_radius=12
            )

            scr.blit(
                f_h.render(
                    n,
                    True,
                    line
                ),
                (
                    r.x + 20,
                    r.y + 12
                )
            )

            scr.blit(
                f_m.render(
                    TYPES[n]["tag"],
                    True,
                    bone
                ),
                (
                    r.x + 20,
                    r.y + 40
                )
            )

        # -------------------------------------------------------------
        # LIVE PREVIEW PANEL
        # -------------------------------------------------------------

        pygame.draw.rect(
            scr,
            mix(
                bg,
                (0, 0, 0),
                .4
            ),
            panel,
            border_radius=14
        )

        scr.set_clip(
            panel.inflate(-4, -4)
        )

        target = (
            panel.centerx
            + math.cos(t * .9) * 210,

            panel.centery
            + math.sin(t * 1.3) * 100
        )

        pet.update(
            target,
            dt
        )

        pet.draw(
            scr,
            t
        )

        pygame.draw.circle(
            scr,
            mix(
                bg,
                glow,
                .5
            ),
            (
                int(target[0]),
                int(target[1])
            ),
            5,
            1
        )

        scr.set_clip(None)

        pygame.draw.rect(
            scr,
            mix(
                bone,
                bg,
                .55
            ),
            panel,
            2,
            border_radius=14
        )

        # -------------------------------------------------------------
        # COLOUR
        # -------------------------------------------------------------

        scr.blit(
            f_s.render(
                "COLOUR",
                True,
                glow
            ),
            (
                475 - 26,
                470
            )
        )

        for th, c in sw:

            col = THEMES[th]["glow"]

            hov = (
                math.hypot(
                    mp[0] - c[0],
                    mp[1] - c[1]
                ) < 22
            )

            pygame.draw.circle(
                scr,
                col,
                c,
                21 if hov else 19
            )

            pygame.draw.circle(
                scr,
                THEMES[th]["bg"],
                c,
                8
            )

            if th == theme:

                pygame.draw.circle(
                    scr,
                    (255, 255, 255),
                    c,
                    26,
                    2
                )

        lab = f_m.render(
            theme,
            True,
            line
        )

        scr.blit(
            lab,
            (
                475 - lab.get_width() // 2,
                540
            )
        )

        # -------------------------------------------------------------
        # DISPLAY MODE
        # -------------------------------------------------------------

        scr.blit(
            f_s.render(
                "DISPLAY MODE",
                True,
                glow
            ),
            (640, 535)
        )

        # Desktop Only button

        desktop_hover = desktop_btn.collidepoint(mp)

        pygame.draw.rect(
            scr,
            mix(
                bg,
                glow,
                .28
                if display_mode == "Desktop Only"
                else (
                    .16
                    if desktop_hover
                    else .08
                )
            ),
            desktop_btn,
            border_radius=12
        )

        pygame.draw.rect(
            scr,
            glow
            if display_mode == "Desktop Only"
            else mix(
                bone,
                bg,
                .5
            ),
            desktop_btn,
            2,
            border_radius=12
        )

        desktop_text = f_m.render(
            "Desktop Only",
            True,
            line
        )

        scr.blit(
            desktop_text,
            desktop_text.get_rect(
                center=desktop_btn.center
            )
        )

        # Always On Top button

        top_hover = top_btn.collidepoint(mp)

        pygame.draw.rect(
            scr,
            mix(
                bg,
                glow,
                .28
                if display_mode == "Always On Top"
                else (
                    .16
                    if top_hover
                    else .08
                )
            ),
            top_btn,
            border_radius=12
        )

        pygame.draw.rect(
            scr,
            glow
            if display_mode == "Always On Top"
            else mix(
                bone,
                bg,
                .5
            ),
            top_btn,
            2,
            border_radius=12
        )

        top_text = f_m.render(
            "Always On Top",
            True,
            line
        )

        scr.blit(
            top_text,
            top_text.get_rect(
                center=top_btn.center
            )
        )

        # -------------------------------------------------------------
        # AWAKEN BUTTON
        # -------------------------------------------------------------

        pulse = (
            .25
            + .12 * math.sin(t * 3)
        )

        pygame.draw.rect(
            scr,
            mix(
                bg,
                glow,
                pulse
                + (
                    .2
                    if start.collidepoint(mp)
                    else 0
                )
            ),
            start,
            border_radius=26
        )

        pygame.draw.rect(
            scr,
            glow,
            start,
            2,
            border_radius=26
        )

        st = f_h.render(
            "AWAKEN",
            True,
            line
        )

        scr.blit(
            st,
            st.get_rect(
                center=start.center
            )
        )

        pygame.display.flip()


# -------------------------------- main --------------------------------------

def main():

    pygame.init()

    # -------------------------------------------------------------
    # DEFAULT SETTINGS
    # -------------------------------------------------------------

    state = (
        "Dragon",
        "Bone White",
        "Desktop Only"
    )

    while True:

        choice = run_menu(state)

        if not choice:
            break

        state = choice

        result = run_overlay(
            *state
        )

        if result == "quit":
            break

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()