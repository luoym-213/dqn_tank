import pygame
import numpy as np

import sys

sys.path.append("D:/temp/python_ven_demo/python_project/tank_battle")
from tankbattle.env.constants import GlobalConstants
class TankSprite(pygame.sprite.Sprite):#坦克精灵

    def __init__(self, size, pos_x, pos_y, sprite_bg, is_enemy, bullet_loading_time, speed, auto_control):
        super().__init__()
        self.size = size                          # size
        self.pos_x = pos_x                        # 当前位置x
        self.pos_y = pos_y                        # 当前位置y
        self.is_enemy = is_enemy                  # 敌军或盟友
        self.loading_time = bullet_loading_time   # 发射子弹的装填时间
        self.direction = np.random.randint(0, 4)  # 当前方向
        self.speed = speed                        # 像素速度
        self.auto_control = auto_control          # human or machine control
        self.fire_started_time = 0                # time of firing
        self.type = GlobalConstants.HARD_OBJECT   # not a bullet
        self.sprite_bg = sprite_bg
        self.image = sprite_bg[self.direction]
        self.rect = self.image.get_rect()
        self.rect.x = self.size * self.pos_x
        self.rect.y = self.size * self.pos_y
        self.target_x = self.pos_x
        self.target_y = self.pos_y
        self.is_terminate = False

        if not is_enemy:
            self.direction = GlobalConstants.UP_ACTION

    def update(self):
        self.image = self.sprite_bg[self.direction]
        if self.target_x != self.pos_x:
            dist = self.target_x - self.pos_x
            self.rect.x = self.rect.x + dist * self.speed
            if self.rect.x == self.target_x * self.size:
                self.pos_x = self.target_x
        if self.target_y != self.pos_y:
            dist = self.target_y - self.pos_y
            self.rect.y = self.rect.y + dist * self.speed
            if self.rect.y == self.target_y * self.size:
                self.pos_y = self.target_y

    def move(self, action, rigid_objs):
        if action < 0:
            return True
        
        # 等待动画
        if self.target_x != self.pos_x or self.target_y != self.pos_y:
            return True
        #
        # if self.direction != action:
        #   self.direction = action
        #    return True

        current_x = self.pos_x
        current_y = self.pos_y

        self.direction = action

        if action == GlobalConstants.LEFT_ACTION:
            current_x = current_x - 1
        elif action == GlobalConstants.RIGHT_ACTION:
            current_x = current_x + 1
        elif action == GlobalConstants.UP_ACTION:
            current_y = current_y - 1
        else:
            current_y = current_y + 1

        # 检查是否有障碍物(current_x, current_y)
        can_move = True
        for obj in rigid_objs:
            if obj.type != GlobalConstants.BULLET_OBJECT and obj.type != GlobalConstants.EXPLOSION_OBJECT:#如果对象类型不是子弹或爆炸
                if isinstance(obj, TankSprite):
                    if current_x == obj.target_x and current_y == obj.target_y:
                        can_move = False
                        break
                    if current_x == obj.pos_x and current_y == obj.pos_y:
                        can_move = False
                        break
                else:
                    if current_x == obj.pos_x and current_y == obj.pos_y:
                        can_move = False
                        break

        if can_move:
            self.target_x = current_x
            self.target_y = current_y

        return can_move