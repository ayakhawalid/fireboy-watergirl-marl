"""Drawing the level with pygame (the render() methods of the Java entities)."""

from __future__ import annotations

import pygame

from . import assets as A
from . import config as C
from .world import World

T = C.TILES_SIZE


class WorldRenderer:
    def __init__(self):
        self.bg1 = A.scaled(A.image(C.P_BACKGROUND), C.GAME_WIDTH, C.GAME_HEIGHT)
        self.bg2 = A.scaled(A.image(C.P_BACKGROUND_TWO), C.GAME_WIDTH, C.GAME_HEIGHT)
        self.floor_imgs = {k: A.scaled(v, T, T) for k, v in A.floor_images().items()}
        self.platform_img = A.platform_image()
        self.door_img = A.scaled(A.frames_x(C.P_DOOR)[0], T, T)
        self.keys = {h: A.scaled(A.image(p), T, T) for h, p in C.P_KEY.items()}
        self.fire_frames = {
            C.T_FIRE_BLUE: [A.scaled(f, T, T) for f in A.frames_x(C.P_BLUE_FIRE)],
            C.T_FIRE_PURPLE: [A.scaled(f, T, T) for f in A.frames_x(C.P_PURPLE_FIRE)],
            C.T_FIRE_GREEN: [A.scaled(f, T, T) for f in A.frames_x(C.P_GREEN_FIRE)],
        }
        self.crystal_img = {
            C.PINK: A.scaled(A.image(C.P_PURPLE_CRYSTAL), T, T),
            C.DUDE: A.scaled(A.image(C.P_BLUE_CRYSTAL), T, T),
        }
        self.lever_frames = [A.scaled(f, T, T) for f in A.frames_x(C.P_LEVER)]
        self.switch_frames = [A.scaled(f, T, T) for f in A.frames_y(C.P_SWITCH)]
        self.box_img = A.scaled(A.image(C.P_BOX), T, T)
        self.hero_frames = {h: [[A.scaled(f, T, T) for f in anim] for anim in A.hero_frames(h)] for h in C.HEROES}
        self.numbers = {}
        for ch in "0123456789:":
            img = A.number_image(ch)
            self.numbers[ch] = A.scaled(img, T // 2, T // 2) if img else None

    def draw(self, surf: pygame.Surface, world: World, debug: bool = False) -> None:
        surf.blit(self.bg1, (0, 0))
        surf.blit(self.bg2, (0, 0))
        for hero, door in world.doors.items():
            x, y = int(door.hitbox.x), int(door.hitbox.y)
            surf.blit(self.door_img, (x, y))
            surf.blit(self.keys[hero], (x, y - T))

        for pl in world.platforms:
            hb = pl.hitbox
            surf.blit(A.scaled(self.platform_img, int(hb.w), int(hb.h)), (int(hb.x), int(hb.y)))

        for f in world.floors:
            x, y = int(f.hitbox.x), int(f.hitbox.y)
            surf.blit(self.floor_imgs["back"], (x, y))
            surf.blit(self.floor_imgs[f.image_name], (x, y))

        for s in world.switches:
            surf.blit(self.switch_frames[s.ani_index], (int(s.hitbox.x), int(s.hitbox.y)))

        for b in world.boxes:
            surf.blit(self.box_img, (int(b.hitbox.x), int(b.hitbox.y)))

        for sw in world.swings:
            hb = sw.hitbox
            img = A.scaled(self.platform_img, int(hb.w), int(hb.h))
            if sw.angle:
                rot = pygame.transform.rotate(img, -sw.angle)  # Java rotates clockwise for positive angles
                surf.blit(rot, rot.get_rect(center=(hb.cx, hb.cy)))
            else:
                surf.blit(img, (int(hb.x), int(hb.y)))

        for kind, fires in world.fires.items():
            frames = self.fire_frames[kind]
            for f in fires:
                surf.blit(frames[f.ani_index], (int(f.hitbox.x), int(f.hitbox.y) - T // 2))

        for hero, crystals in world.crystals.items():
            for c in crystals:
                if c.visible:
                    surf.blit(self.crystal_img[hero], (int(c.hitbox.x), int(c.hitbox.y)))

        for lv in world.levers:
            surf.blit(self.lever_frames[lv.ani_index], (int(lv.hitbox.x), int(lv.hitbox.y)))

        for hero in C.HEROES:
            p = world.players[hero]
            frames = self.hero_frames[hero][p.action]
            idx = min(int(p.ani_index), len(frames) - 1)
            surf.blit(frames[idx], (int(p.hitbox.x - p.width * 0.3), int(p.hitbox.y - p.height * 0.3)))

        self._draw_time(surf, world.time_seconds())

        if debug:
            self._draw_hitboxes(surf, world)

    def _draw_time(self, surf, seconds: int) -> None:
        text = f"{seconds // 60:02d}:{seconds % 60:02d}"
        x = T * 18
        for ch in text:
            img = self.numbers.get(ch)
            if img is not None:
                surf.blit(img, (x, T // 2))
            else:
                glyph = A.font(30).render(ch, False, (255, 255, 255))
                surf.blit(glyph, (x, T // 2 - 6))
            x += T

    def _draw_hitboxes(self, surf, world: World) -> None:
        red = (255, 0, 0)
        ents = world.floors + world.platforms + world.boxes + world.levers + world.switches
        ents += [f for fs in world.fires.values() for f in fs]
        ents += list(world.doors.values()) + list(world.players.values())
        for e in ents:
            hb = e.hitbox
            pygame.draw.rect(surf, red, (int(hb.x), int(hb.y), int(hb.w), int(hb.h)), 1)
