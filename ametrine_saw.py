#!/usr/bin/env python3
"""Ametrine Saw — neon radial crystal-saw arcade for ElbowOS."""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys

import pygame

W, H = 1080, 1920
FPS = 30
TITLE = "AMETRINE SAW"
HANDLE = "x.com/ElbowOS"
BG = (10, 4, 22)
INK = (255, 236, 250)
GOLD = (255, 196, 64)
VIOLET = (186, 92, 255)
ROSE = (255, 78, 164)
TEAL = (48, 230, 220)
AMBER = (255, 150, 50)
RING_COLS = (VIOLET, GOLD, ROSE, TEAL)


class Spark:
    __slots__ = ("x", "y", "vx", "vy", "life", "col", "r")

    def __init__(self, x, y, vx, vy, life, col, r=5):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life, self.col, self.r = life, col, r


class Game:
    def __init__(self, record: bool):
        self.record = record
        self.surf = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.font_lg = pygame.font.Font(None, 68)
        self.font_md = pygame.font.Font(None, 46)
        self.font_sm = pygame.font.Font(None, 32)
        self.cx, self.cy = W * 0.5, H * 0.52
        self.reset()

    def reset(self) -> None:
        self.score = getattr(self, "score", 0) if getattr(self, "keep_score", False) else 0
        self.keep_score = True
        self.combo = 0
        self.t = 0.0
        self.flash = 0.0
        self.angle = 0.0
        self.spin = 0.0
        self.blade_r = 0.0
        self.firing = False
        self.cool = 0.0
        self.sparks: list[Spark] = []
        self.stars = [
            [random.uniform(0, W), random.uniform(0, H), random.uniform(1.2, 3.4)]
            for _ in range(70)
        ]
        self.rings = []
        for i in range(4):
            n = 8 + i * 2
            segs = []
            for k in range(n):
                segs.append({"alive": True, "col": RING_COLS[(i + k) % 4]})
            self.rings.append({
                "r": 150 + i * 105,
                "n": n,
                "rot": random.uniform(0, 6.28),
                "spd": (0.35 + i * 0.12) * (1 if i % 2 == 0 else -1),
                "segs": segs,
            })

    def burst(self, x, y, col, n=14) -> None:
        for _ in range(n):
            a = random.random() * 6.283
            spd = random.uniform(80, 480)
            self.sparks.append(Spark(x, y, spd * math.cos(a), spd * math.sin(a),
                                     random.uniform(0.18, 0.55), col, random.randint(3, 8)))

    def fire(self) -> None:
        if self.firing or self.cool > 0:
            return
        self.firing = True
        self.blade_r = 70.0
        self.cool = 0.16

    def autoplay(self, dt: float) -> None:
        best = None
        best_d = 9.0
        for ring in self.rings:
            step = 6.28318 / ring["n"]
            for k, seg in enumerate(ring["segs"]):
                if not seg["alive"]:
                    continue
                a = ring["rot"] + (k + 0.5) * step
                d = abs((a - self.angle + math.pi) % 6.28318 - math.pi)
                if d < best_d:
                    best_d, best = d, a
        if best is None:
            for ring in self.rings:
                for seg in ring["segs"]:
                    seg["alive"] = True
            self.combo = 0
            return
        diff = (best - self.angle + math.pi) % 6.28318 - math.pi
        self.angle += max(-3.6 * dt, min(3.6 * dt, diff * 7.0 * dt))
        if best_d < 0.12 and not self.firing:
            self.fire()

    def update(self, dt: float) -> None:
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        self.cool = max(0.0, self.cool - dt)
        self.spin += dt * 8.0
        for st in self.stars:
            st[1] += st[2] * 22 * dt
            if st[1] > H:
                st[0], st[1] = random.uniform(0, W), -4
        for ring in self.rings:
            ring["rot"] += ring["spd"] * dt
        if self.record:
            self.autoplay(dt)
        else:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.angle -= 2.8 * dt
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.angle += 2.8 * dt
            if keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]:
                self.fire()
        if self.firing:
            self.blade_r += 980 * dt
            hit = False
            bx = self.cx + math.cos(self.angle) * self.blade_r
            by = self.cy + math.sin(self.angle) * self.blade_r
            for ring in self.rings:
                if abs(self.blade_r - ring["r"]) > 28:
                    continue
                step = 6.28318 / ring["n"]
                for k, seg in enumerate(ring["segs"]):
                    if not seg["alive"]:
                        continue
                    a0 = ring["rot"] + k * step
                    mid = a0 + step * 0.5
                    d = abs((mid - self.angle + math.pi) % 6.28318 - math.pi)
                    if d < step * 0.52:
                        seg["alive"] = False
                        self.combo += 1
                        self.score += 8 + self.combo * 3
                        self.flash = 0.18
                        self.burst(bx, by, seg["col"], 18)
                        hit = True
                        break
                if hit:
                    break
            if self.blade_r > 620:
                if not hit:
                    self.combo = 0
                self.firing = False
                self.blade_r = 0.0
        if all(not s["alive"] for r in self.rings for s in r["segs"]):
            for ring in self.rings:
                for seg in ring["segs"]:
                    seg["alive"] = True
                ring["spd"] *= -1.08
            self.burst(self.cx, self.cy, GOLD, 28)
        alive = []
        for sp in self.sparks:
            sp.life -= dt
            if sp.life <= 0:
                continue
            sp.x += sp.vx * dt
            sp.y += sp.vy * dt
            sp.vy += 280 * dt
            alive.append(sp)
        self.sparks = alive

    def handle(self, ev) -> None:
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_r:
            self.keep_score = False
            self.reset()

    def draw(self, s: pygame.Surface) -> None:
        s.fill(BG)
        for i in range(10):
            y = int((self.t * 50 + i * 210) % (H + 40)) - 20
            pygame.draw.line(s, (28, 10, 48), (0, y), (W, y), 2)
        for x, y, r in self.stars:
            pygame.draw.circle(s, (80, 40, 120), (int(x), int(y)), int(r))
        pygame.draw.circle(s, (24, 8, 46), (int(self.cx), int(self.cy)), 640)
        pygame.draw.circle(s, VIOLET, (int(self.cx), int(self.cy)), 640, 3)
        for ring in self.rings:
            step = 6.28318 / ring["n"]
            for k, seg in enumerate(ring["segs"]):
                if not seg["alive"]:
                    continue
                a0 = ring["rot"] + k * step + 0.04
                a1 = ring["rot"] + (k + 1) * step - 0.04
                pts_o, pts_i = [], []
                steps = 6
                for j in range(steps + 1):
                    a = a0 + (a1 - a0) * j / steps
                    pts_o.append((self.cx + math.cos(a) * (ring["r"] + 22),
                                  self.cy + math.sin(a) * (ring["r"] + 22)))
                    pts_i.append((self.cx + math.cos(a) * (ring["r"] - 22),
                                  self.cy + math.sin(a) * (ring["r"] - 22)))
                pygame.draw.polygon(s, seg["col"], pts_o + list(reversed(pts_i)))
                pygame.draw.lines(s, INK, False, pts_o, 2)
        aim_x = self.cx + math.cos(self.angle) * 118
        aim_y = self.cy + math.sin(self.angle) * 118
        pygame.draw.line(s, INK, (self.cx, self.cy), (aim_x, aim_y), 6)
        if self.firing:
            bx = self.cx + math.cos(self.angle) * self.blade_r
            by = self.cy + math.sin(self.angle) * self.blade_r
            pygame.draw.line(s, GOLD, (self.cx, self.cy), (bx, by), 4)
            teeth = 8
            poly = []
            for i in range(teeth * 2):
                a = self.spin + i * math.pi / teeth
                rr = 26 if i % 2 == 0 else 14
                poly.append((bx + math.cos(a) * rr, by + math.sin(a) * rr))
            pygame.draw.polygon(s, GOLD, poly)
            pygame.draw.circle(s, ROSE, (int(bx), int(by)), 8)
        pygame.draw.circle(s, (40, 12, 60), (int(self.cx), int(self.cy)), 62)
        pygame.draw.circle(s, GOLD, (int(self.cx), int(self.cy)), 62, 4)
        pygame.draw.circle(s, VIOLET, (int(self.cx), int(self.cy)), 28)
        for i in range(6):
            a = self.spin * 0.4 + i * math.pi / 3
            pygame.draw.line(s, AMBER,
                             (self.cx + math.cos(a) * 16, self.cy + math.sin(a) * 16),
                             (self.cx + math.cos(a) * 52, self.cy + math.sin(a) * 52), 3)
        for sp in self.sparks:
            pygame.draw.circle(s, sp.col, (int(sp.x), int(sp.y)), max(1, int(sp.r * sp.life * 2)))
        title = self.font_lg.render(TITLE, True, GOLD)
        s.blit(title, title.get_rect(center=(W // 2, 62)))
        handle = self.font_sm.render(HANDLE, True, TEAL)
        s.blit(handle, handle.get_rect(center=(W // 2, 112)))
        score = self.font_md.render(f"SCORE  {self.score}    COMBO  {self.combo}", True, ROSE)
        s.blit(score, score.get_rect(center=(W // 2, 168)))
        hint = self.font_sm.render("A / D aim   SPACE saw   R reset   x.com/ElbowOS", True, VIOLET)
        s.blit(hint, hint.get_rect(center=(W // 2, H - 48)))
        if self.flash > 0:
            flash = pygame.Surface((W, H), pygame.SRCALPHA)
            flash.fill((255, 120, 220, int(70 * self.flash / 0.18)))
            s.blit(flash, (0, 0))

    def play(self) -> None:
        screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(TITLE)
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    running = False
                else:
                    self.handle(ev)
            self.update(dt)
            self.draw(self.surf)
            screen.blit(self.surf, (0, 0))
            pygame.display.flip()

    def record_mp4(self, path: str) -> None:
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart", path,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        frames = FPS * 15
        for i in range(frames):
            self.update(1.0 / FPS)
            self.draw(self.surf)
            proc.stdin.write(pygame.image.tostring(self.surf, "RGB"))
            if i % 30 == 0:
                print(f"frame {i}/{frames}", flush=True)
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed: {rc}")
        print("wrote", path)


def main() -> None:
    record = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
    play = "--play" in sys.argv
    if record or not play:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.font.init()
    g = Game(record or not play)
    if record or not play:
        out = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/AMETRINE_SAW_ElbowOS.mp4")
        g.record_mp4(out)
    else:
        g.play()
    pygame.quit()


if __name__ == "__main__":
    main()
