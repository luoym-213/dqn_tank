import pygame
import os
import numpy as np

import collections as cl
import sys

sys.path.append("D:/temp/python_ven_demo/python_project/tank_battle")

from tankbattle.env.utils import Utils
from tankbattle.env.constants import GlobalConstants
from tankbattle.env.sprites.tank import TankSprite
from tankbattle.env.sprites.base import BaseSprite
from tankbattle.env.sprites.wall import WallSprite
from tankbattle.env.sprites.explosion import ExplosionSprite
from tankbattle.env.sprites.bullet import BulletSprite
from tankbattle.env.manager import ResourceManager
from tankbattle.env.maps import StageMap

#引擎
class TankBattle(object):#坦克大战类

    def __init__(self, render=False, speed=60, max_frames=100000, frame_skip=1,
                 seed=None, num_of_enemies=5, two_players=True, player1_human_control=True,
                 player2_human_control=False, debug=False):

        # Prepare internal data
        self.screen_size = GlobalConstants.SCREEN_SIZE#屏幕大小全局常量的大小
        self.tile_size = GlobalConstants.TILE_SIZE#棋子大小
        self.max_frames = max_frames
        self.rd = render#粉刷初始颜色
        self.screen = None
        self.speed = speed
        self.num_of_enemies = num_of_enemies
        self.sprites = pygame.sprite.Group()#精灵
        self.enemies = pygame.sprite.Group()
        self.players = pygame.sprite.Group()
        self.bullets_player = pygame.sprite.Group()#玩家的子弹
        self.bullets_enemy = pygame.sprite.Group()#敌方子弹
        self.bases = pygame.sprite.Group()
        self.walls = pygame.sprite.Group()
        self.booms = pygame.sprite.Group()
        self.num_of_actions = GlobalConstants.NUM_OF_ACTIONS
        self.num_of_tiles = int(self.screen_size/self.tile_size)
        self.end_of_game = False
        self.is_debug = debug
        self.frames_count = 0
        self.total_score = 0
        self.total_score_p1 = 0
        self.total_score_p2 = 0
        self.enemy_update_freq = 1#敌人更新频率
        self.bullet_speed = GlobalConstants.BULLET_SPEED
        self.font_size = GlobalConstants.FONT_SIZE
        self.player1_human_control = player1_human_control
        self.player2_human_control = player2_human_control
        self.two_players = two_players
        self.log_freq = 60#日志频率
        if self.log_freq == 0:
            self.log_freq = 60
        self.current_stage = 0#现阶段
        self.current_path = os.path.dirname(os.path.abspath(__file__))
        self.player_speed = GlobalConstants.PLAYER_SPEED
        self.enemy_speed = GlobalConstants.ENEMY_SPEED
        self.enemy_bullet_loading_time = GlobalConstants.ENEMY_LOADING_TIME
        self.current_buffer = np.array([[[0, 0, 0] for _ in range(self.screen_size)] for _ in range(self.screen_size)])
        self.pareto_solutions = None
        self.frame_speed = 0
        self.frame_skip = frame_skip
        self.started_time = Utils.get_current_time()
        self.next_rewards_p1 = cl.deque(maxlen=100)
        self.next_rewards_p2 = cl.deque(maxlen=100)
        self.num_of_objs = 2

        if self.player1_human_control or self.player2_human_control:
            if not self.rd:
                raise ValueError("无效参数！人工控制必须处于渲染模式")

        # Seed is used to generate a stochastic environment生成随机环境
        if seed is None or seed < 0 or seed >= 9999:
            self.seed = np.random.randint(0, 9999)
            self.random_seed = True
        else:
            self.random_seed = False
            self.seed = seed
            np.random.seed(seed)

        # 初始化
        self.__init_pygame_engine()

        # 创建基础设置和墙体
        self.__generate_base_and_walls()

        # 创建玩家
        self.__generate_players()

        # 创建敌军
        self.__generate_enemies(self.num_of_enemies)

        # 加载地图
        self.stage_map.load_map(self.current_stage)

        # 渲染第一帧
        self.__render()

    @staticmethod
    def get_game_name():
        return "TANK BATTLE"

    def clone(self):#
        if self.random_seed:
            seed = np.random.randint(0, 9999)
        else:
            seed = self.seed
        return TankBattle(render=self.rd, speed=self.speed, max_frames=self.max_frames, frame_skip=self.frame_skip,
                          seed=seed, num_of_enemies=self.num_of_enemies, two_players=self.two_players,
                          player1_human_control=self.player1_human_control,
                          player2_human_control=self.player2_human_control,
                          debug=self.is_debug
                          )

    def get_num_of_objectives(self):#获取目标数量
        return self.num_of_objs

    def get_seed(self):
        return self.seed

    def __init_pygame_engine(self):#初始pygame引擎
        # 将屏幕居中
        os.environ['SDL_VIDEO_CENTERED'] = '1'

        # 初始pygame引擎
        pygame.init()

        # 初始化操纵杆
        self.num_of_joysticks = pygame.joystick.get_count()
        self.joystick_p1 = None
        self.joystick_p2 = None
        if self.num_of_joysticks > 0:
            self.joystick_p1 = pygame.joystick.Joystick(0)
            self.joystick_p1.init()
        if self.num_of_joysticks > 1:
            self.joystick_p2 = pygame.joystick.Joystick(1)
            self.joystick_p2.init()

        if self.rd:
            pygame.display.set_caption(TankBattle.get_game_name())
            self.screen = pygame.display.set_mode((self.screen_size, self.screen_size))
        else:
            self.screen = pygame.Surface((self.screen_size, self.screen_size))
        self.rc_manager = ResourceManager(current_path=self.current_path, font_size=self.font_size,
                                          tile_size=self.tile_size, is_render=self.rd)
        self.font = self.rc_manager.get_font()
        self.stage_map = StageMap(self.num_of_tiles, tile_size=self.tile_size, current_path=self.current_path,
                                  sprites=self.sprites, walls=self.walls, resources_manager=self.rc_manager)

    def __generate_base_and_walls(self):#生成基底和墙体
        # 创建底座
        self.base = BaseSprite(self.tile_size, pos_x=int(self.num_of_tiles / 2), pos_y=self.num_of_tiles - 2,
                               sprite_bg=self.rc_manager.get_image(ResourceManager.BASE))
        self.sprites.add(self.base)
        self.bases.add(self.base)

        # 创建墙体
        wall_bg = self.rc_manager.get_image(ResourceManager.HARD_WALL)
        for i in range(self.num_of_tiles):
            wall_top = WallSprite(self.tile_size, i, 0, wall_bg)
            self.sprites.add(wall_top)
            self.walls.add(wall_top)

            wall_bottom = WallSprite(self.tile_size, i, self.num_of_tiles-1, wall_bg)
            self.sprites.add(wall_bottom)
            self.walls.add(wall_bottom)

            wall_left = WallSprite(self.tile_size, 0, i, wall_bg)
            self.sprites.add(wall_left)
            self.walls.add(wall_left)

            wall_right = WallSprite(self.tile_size, self.num_of_tiles-1, i, wall_bg)
            self.sprites.add(wall_right)
            self.walls.add(wall_right)

    def __generate_players(self):#生成玩家

        self.player1 = TankSprite(self.tile_size, pos_x=int(self.num_of_tiles / 2) - 2, pos_y=self.num_of_tiles - 2,
                                  sprite_bg=(self.rc_manager.get_image(ResourceManager.PLAYER1_LEFT),
                                             self.rc_manager.get_image(ResourceManager.PLAYER1_RIGHT),
                                             self.rc_manager.get_image(ResourceManager.PLAYER1_UP),
                                             self.rc_manager.get_image(ResourceManager.PLAYER1_DOWN)),
                                  is_enemy=False, bullet_loading_time=GlobalConstants.PLAYER_LOADING_TIME,
                                  speed=self.player_speed,
                                  auto_control=self.player1_human_control)
        self.sprites.add(self.player1)
        self.players.add(self.player1)

        if self.two_players:
            self.player2 = TankSprite(self.tile_size, pos_x=int(self.num_of_tiles / 2) + 2, pos_y=self.num_of_tiles - 2,
                                      sprite_bg=(self.rc_manager.get_image(ResourceManager.PLAYER2_LEFT),
                                                 self.rc_manager.get_image(ResourceManager.PLAYER2_RIGHT),
                                                 self.rc_manager.get_image(ResourceManager.PLAYER2_UP),
                                                 self.rc_manager.get_image(ResourceManager.PLAYER2_DOWN)),
                                      is_enemy=False, bullet_loading_time=GlobalConstants.PLAYER_LOADING_TIME,
                                      speed=self.player_speed, auto_control=True)
            self.sprites.add(self.player2)
            self.players.add(self.player2)

    def __generate_enemies(self, num_of_enemies):#生成敌军
        for _ in range(num_of_enemies):
            x = np.random.randint(1, self.num_of_tiles-1)
            y = np.random.randint(1, int(self.num_of_tiles / 2)-1)
            enemy = TankSprite(self.tile_size, pos_x=x, pos_y=y,
                               sprite_bg=(self.rc_manager.get_image(ResourceManager.ENEMY_LEFT),
                                          self.rc_manager.get_image(ResourceManager.ENEMY_RIGHT),
                                          self.rc_manager.get_image(ResourceManager.ENEMY_UP),
                                          self.rc_manager.get_image(ResourceManager.ENEMY_DOWN)),
                               is_enemy=True, bullet_loading_time=self.enemy_bullet_loading_time,
                               speed=self.enemy_speed,
                               auto_control=True)
            self.sprites.add(enemy)
            self.enemies.add(enemy)

            # 增加难度（当己方总得分超过200、500、1000时，加快敌军换弹速度）
            if self.total_score > 200:
                self.enemy_bullet_loading_time = GlobalConstants.ENEMY_LOADING_TIME - 10
            elif self.total_score > 500:
                self.enemy_bullet_loading_time = GlobalConstants.ENEMY_LOADING_TIME - 20
            elif self.total_score > 1000:
                self.enemy_speed = GlobalConstants.PLAYER_SPEED
                self.enemy_bullet_loading_time = GlobalConstants.ENEMY_LOADING_TIME - 20

    def __enemies_update(self):#敌军更新
        if self.frames_count % self.enemy_update_freq == 0:
            for enemy in self.enemies:
                rand_action = np.random.randint(0, self.num_of_actions)
                if rand_action != GlobalConstants.FIRE_ACTION:
                    rand_action = enemy.direction
                    if not enemy.move(rand_action, self.sprites):
                        rand_action = np.random.randint(0, self.num_of_actions)
                        if rand_action != GlobalConstants.FIRE_ACTION:
                            enemy.move(rand_action, self.sprites)
                        else:
                            enemy.fire_started_time = self.frames_count
                else:
                    self.__fire_bullet(enemy, True)

    def __draw_score(self):#写出分数
        total_score = self.font.render('Score:' + str(self.total_score), False, Utils.get_color(Utils.WHITE))
        self.screen.blit(total_score, (self.screen_size/2 - total_score.get_width()/2,
                                       self.screen_size-self.tile_size + total_score.get_height()/1.3))

        p1_score = self.font.render('P1:' + str(self.total_score_p1), False, Utils.get_color(Utils.WHITE))
        self.screen.blit(p1_score, (10, self.screen_size-self.tile_size + p1_score.get_height()/1.3))

        p2_score = self.font.render('P2:' + str(self.total_score_p2), False, Utils.get_color(Utils.WHITE))
        self.screen.blit(p2_score, (self.screen_size - p2_score.get_width() - 10,
                                    self.screen_size-self.tile_size + p2_score.get_height()/1.3))

        stage_text = self.font.render('Stage ' + str(self.current_stage + 1), False, Utils.get_color(Utils.WHITE))
        self.screen.blit(stage_text, (self.screen_size/2 - stage_text.get_width()/2, stage_text.get_height()/1.3))

    def __fire_bullet(self, tank, is_enemy):
        if tank.is_terminate:
            return True
        current_time = self.frames_count
        if tank is self.player1:
            owner = GlobalConstants.PLAYER_1_OWNER
        elif self.two_players and tank is self.player2:
            owner = GlobalConstants.PLAYER_2_OWNER
        else:
            owner = GlobalConstants.ENEMY_OWNER
        if current_time - tank.fire_started_time > tank.loading_time:
            tank.fire_started_time = self.frames_count
            bullet = BulletSprite(size=self.rc_manager.bullet_size,
                                  tile_size=self.tile_size,
                                  direction=tank.direction,
                                  speed=self.bullet_speed,
                                  pos_x=tank.target_x,
                                  pos_y=tank.target_y,
                                  owner=owner,
                                  sprite_bg=self.rc_manager.get_image(ResourceManager.BULLET))
            if is_enemy:
                self.bullets_enemy.add(bullet)
            else:
                self.bullets_player.add(bullet)
            self.sprites.add(bullet)

    @staticmethod #键盘事件
    def __is_key_pressed():
        keys = pygame.key.get_pressed()
        for i in range(len(keys)):
            if keys[i] != 0:
                return i
        return -1

    def __human_control(self, key):
        if self.player1_human_control and self.player2_human_control:#双人模式
            if self.two_players:
                if key == pygame.K_LEFT:
                    self.player1.move(GlobalConstants.LEFT_ACTION, self.sprites)
                if key == pygame.K_RIGHT:
                    self.player1.move(GlobalConstants.RIGHT_ACTION, self.sprites)
                if key == pygame.K_UP:
                    self.player1.move(GlobalConstants.UP_ACTION, self.sprites)
                if key == pygame.K_DOWN:
                    self.player1.move(GlobalConstants.DOWN_ACTION, self.sprites)
                if key == pygame.K_KP_ENTER:
                    self.__fire_bullet(self.player1, False)
                if key == pygame.K_a:
                    self.player2.move(GlobalConstants.LEFT_ACTION, self.sprites)
                if key == pygame.K_d:
                    self.player2.move(GlobalConstants.RIGHT_ACTION, self.sprites)
                if key == pygame.K_w:
                    self.player2.move(GlobalConstants.UP_ACTION, self.sprites)
                if key == pygame.K_s:
                    self.player2.move(GlobalConstants.DOWN_ACTION, self.sprites)
                if key == pygame.K_SPACE:
                    self.__fire_bullet(self.player2, False)
            else:
                if key == pygame.K_LEFT:
                    self.player1.move(GlobalConstants.LEFT_ACTION, self.sprites)
                if key == pygame.K_RIGHT:
                    self.player1.move(GlobalConstants.RIGHT_ACTION, self.sprites)
                if key == pygame.K_UP:
                    self.player1.move(GlobalConstants.UP_ACTION, self.sprites)
                if key == pygame.K_DOWN:
                    self.player1.move(GlobalConstants.DOWN_ACTION, self.sprites)
                if key == pygame.K_SPACE:
                    self.__fire_bullet(self.player1, False)
        else:#单人模式
            if not self.player1_human_control:
                if self.two_players:
                    if key == pygame.K_a:
                        self.player2.move(GlobalConstants.LEFT_ACTION, self.sprites)
                    if key == pygame.K_d:
                        self.player2.move(GlobalConstants.RIGHT_ACTION, self.sprites)
                    if key == pygame.K_w:
                        self.player2.move(GlobalConstants.UP_ACTION, self.sprites)
                    if key == pygame.K_s:
                        self.player2.move(GlobalConstants.DOWN_ACTION, self.sprites)
                    if key == pygame.K_SPACE:
                        self.__fire_bullet(self.player2, False)
            else:
                if key == pygame.K_LEFT:
                    self.player1.move(GlobalConstants.LEFT_ACTION, self.sprites)
                if key == pygame.K_RIGHT:
                    self.player1.move(GlobalConstants.RIGHT_ACTION, self.sprites)
                if key == pygame.K_UP:
                    self.player1.move(GlobalConstants.UP_ACTION, self.sprites)
                if key == pygame.K_DOWN:
                    self.player1.move(GlobalConstants.DOWN_ACTION, self.sprites)
                if key == pygame.K_KP_ENTER:
                    self.__fire_bullet(self.player1, False)

    def __joystick_control(self):#操纵杆
        if self.player1_human_control and self.player2_human_control:
            if self.two_players:
                if self.joystick_p1 is not None:
                    if self.joystick_p1.get_axis(0) < 0:# get_axis:获得操纵轴的当前坐标
                        self.player1.move(GlobalConstants.LEFT_ACTION, self.sprites)
                    if self.joystick_p1.get_axis(0) > 0:
                        self.player1.move(GlobalConstants.RIGHT_ACTION, self.sprites)
                    if self.joystick_p1.get_axis(1) < 0:
                        self.player1.move(GlobalConstants.UP_ACTION, self.sprites)
                    if self.joystick_p1.get_axis(1) > 0:
                        self.player1.move(GlobalConstants.DOWN_ACTION, self.sprites)
                    if self.joystick_p1.get_button(0) > 0 or self.joystick_p1.get_button(1) > 0:
                        self.__fire_bullet(self.player1, False)
                if self.joystick_p2 is not None:
                    if self.joystick_p2.get_axis(0) < 0:
                        self.player2.move(GlobalConstants.LEFT_ACTION, self.sprites)
                    if self.joystick_p2.get_axis(0) > 0:
                        self.player2.move(GlobalConstants.RIGHT_ACTION, self.sprites)
                    if self.joystick_p2.get_axis(1) < 0:
                        self.player2.move(GlobalConstants.UP_ACTION, self.sprites)
                    if self.joystick_p2.get_axis(1) > 0:
                        self.player2.move(GlobalConstants.DOWN_ACTION, self.sprites)
                    if self.joystick_p2.get_button(0) > 0 or self.joystick_p2.get_button(1) > 0:
                        self.__fire_bullet(self.player2, False)
            else:
                if self.joystick_p1 is not None:
                    if self.joystick_p1.get_axis(0) < 0:
                        self.player1.move(GlobalConstants.LEFT_ACTION, self.sprites)
                    if self.joystick_p1.get_axis(0) > 0:
                        self.player1.move(GlobalConstants.RIGHT_ACTION, self.sprites)
                    if self.joystick_p1.get_axis(1) < 0:
                        self.player1.move(GlobalConstants.UP_ACTION, self.sprites)
                    if self.joystick_p1.get_axis(1) > 0:
                        self.player1.move(GlobalConstants.DOWN_ACTION, self.sprites)
                    if self.joystick_p1.get_button(0) > 0 or self.joystick_p1.get_button(1) > 0:
                        self.__fire_bullet(self.player1, False)
        else:
            if not self.player1_human_control:
                if self.two_players:
                    if self.joystick_p2 is not None:
                        if self.joystick_p2.get_axis(0) < 0:
                            self.player2.move(GlobalConstants.LEFT_ACTION, self.sprites)
                        if self.joystick_p2.get_axis(0) > 0:
                            self.player2.move(GlobalConstants.RIGHT_ACTION, self.sprites)
                        if self.joystick_p2.get_axis(1) < 0:
                            self.player2.move(GlobalConstants.UP_ACTION, self.sprites)
                        if self.joystick_p2.get_axis(1) > 0:
                            self.player2.move(GlobalConstants.DOWN_ACTION, self.sprites)
                        if self.joystick_p2.get_button(0) > 0 or self.joystick_p2.get_button(1) > 0:
                            self.__fire_bullet(self.player2, False)
            else:
                if self.joystick_p1 is not None:
                    if self.joystick_p1.get_axis(0) < 0:
                        self.player1.move(GlobalConstants.LEFT_ACTION, self.sprites)
                    if self.joystick_p1.get_axis(0) > 0:
                        self.player1.move(GlobalConstants.RIGHT_ACTION, self.sprites)
                    if self.joystick_p1.get_axis(1) < 0:
                        self.player1.move(GlobalConstants.UP_ACTION, self.sprites)
                    if self.joystick_p1.get_axis(1) > 0:
                        self.player1.move(GlobalConstants.DOWN_ACTION, self.sprites)
                    if self.joystick_p1.get_button(0) > 0 or self.joystick_p1.get_button(1) > 0:
                        self.__fire_bullet(self.player1, False)

    def __handle_event(self):#操作事件
        #结束游戏
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print("Game Over!")
                self.reset()
                sys.exit()

        if not self.player1_human_control and not self.player2_human_control:
            return True

        key = TankBattle.__is_key_pressed()
        if key >= 0:
            self.__human_control(key)

        if self.num_of_joysticks > 0:
            self.__joystick_control()

        return True

    def __check_reward(self):#得分
        p1_score = 0
        if len(self.next_rewards_p1) > 0:
            p1_score = self.next_rewards_p1[0]
            self.next_rewards_p1.popleft()
        p2_score = 0
        if len(self.next_rewards_p2) > 0:
            p2_score = self.next_rewards_p2[0]
            self.next_rewards_p2.popleft()
        return [p1_score, p2_score]

    def __generate_explosion(self, abs_x, abs_y):#生成爆炸
        expl = ExplosionSprite(self.tile_size, abs_x, abs_y, 2,
                               [self.rc_manager.get_image(ResourceManager.EXPLOSION_1),
                                self.rc_manager.get_image(ResourceManager.EXPLOSION_2),
                                self.rc_manager.get_image(ResourceManager.EXPLOSION_3)])
        self.sprites.add(expl)
        self.booms.add(expl)

    def __remove_explosions(self):#爆炸消失
        for expl in self.booms:
            if expl.done():
                self.sprites.remove(expl)
                self.booms.remove(expl)

    def __bullets_update(self):#子弹更新
        for bullet in self.bullets_player:
            is_hit = False

            # 检查它是否击中了其他敌人的子弹
            bullets_hit = pygame.sprite.spritecollide(bullet, self.bullets_enemy, True)
            for bullet_enemy in bullets_hit:
                self.bullets_enemy.remove(bullet_enemy)
                self.sprites.remove(bullet_enemy)
                self.sprites.remove(bullet)
                self.bullets_player.remove(bullet)
                is_hit = True
                break
            if is_hit:
                continue

            # 检查是否击中敌军
            enemies_hit = pygame.sprite.spritecollide(bullet, self.enemies, True)
            for enemy in enemies_hit:
                self.__generate_explosion(enemy.rect.x, enemy.rect.y)
                self.enemies.remove(enemy)
                self.sprites.remove(enemy)
                self.sprites.remove(bullet)
                self.bullets_player.remove(bullet)
                self.total_score = self.total_score + 10
                if bullet.owner == GlobalConstants.PLAYER_1_OWNER:
                    self.total_score_p1 = self.total_score_p1 + 10
                    self.next_rewards_p1.append(10)
                else:
                    self.total_score_p2 = self.total_score_p2 + 10
                    self.next_rewards_p2.append(10)
                self.__generate_enemies(1)
                is_hit = True
                break
            if is_hit:
                continue

            # 检查是否击中玩家
            players_hit = pygame.sprite.spritecollide(bullet, self.players, True)
            for player in players_hit:
                player.is_terminate = True
                self.__generate_explosion(player.rect.x, player.rect.y)
                self.players.remove(player)
                self.sprites.remove(player)
                self.sprites.remove(bullet)
                self.bullets_player.remove(bullet)
                is_hit = True
                break
            if is_hit:
                continue

            # 检查它是否击中底座
            bases_hit = pygame.sprite.spritecollide(bullet, self.bases, True)
            for base in bases_hit:
                self.__generate_explosion(base.rect.x, base.rect.y)
                self.bases.remove(base)
                self.sprites.remove(base)
                self.sprites.remove(bullet)
                self.bullets_player.remove(bullet)
                self.end_of_game = True
                return

            # 检查是否击中墙体，如果击中，子弹消失
            walls_hit = pygame.sprite.spritecollide(bullet, self.walls, False)
            for wall in walls_hit:
                if wall.type == GlobalConstants.SOFT_OBJECT:
                    self.sprites.remove(wall)
                    self.walls.remove(wall)
                if wall.type != GlobalConstants.TRANSPARENT_OBJECT:
                    self.sprites.remove(bullet)
                    self.bullets_player.remove(bullet)

        for bullet in self.bullets_enemy:#敌方子弹
            is_hit = False

            # 检查敌方子弹是否击中其他玩家的子弹
            bullets_hit = pygame.sprite.spritecollide(bullet, self.bullets_player, True)
            for bullet_player in bullets_hit:
                self.bullets_player.remove(bullet_player)
                self.sprites.remove(bullet_player)
                self.sprites.remove(bullet)
                self.bullets_enemy.remove(bullet)
                is_hit = True
                break
            if is_hit:
                continue

            # 检查敌方子弹是否击中玩家
            players_hit = pygame.sprite.spritecollide(bullet, self.players, True)
            for player in players_hit:
                player.is_terminate = True
                self.__generate_explosion(player.rect.x, player.rect.y)
                self.players.remove(player)
                self.sprites.remove(player)
                self.sprites.remove(bullet)
                self.bullets_enemy.remove(bullet)
                is_hit = True
                break
            if is_hit:
                continue

            if len(self.players) == 0:
                self.end_of_game = True

            # 检查敌方子弹是否击中底座
            bases_hit = pygame.sprite.spritecollide(bullet, self.bases, True)
            for base in bases_hit:
                self.__generate_explosion(base.rect.x, base.rect.y)
                self.bases.remove(base)
                self.sprites.remove(base)
                self.sprites.remove(bullet)
                self.bullets_enemy.remove(bullet)
                self.end_of_game = True
                return

            # 检查敌方子弹是否击中墙体，如果击中，子弹消失
            walls_hit = pygame.sprite.spritecollide(bullet, self.walls, False)
            for wall in walls_hit:
                if wall.type == GlobalConstants.SOFT_OBJECT:
                    self.sprites.remove(wall)
                    self.walls.remove(wall)
                if wall.type != GlobalConstants.TRANSPARENT_OBJECT:
                    self.sprites.remove(bullet)
                    self.bullets_enemy.remove(bullet)

    def __calculate_fps(self):#计算帧数
        self.frames_count = self.frames_count + 1
        if self.max_frames > 0:
            if self.frames_count > self.max_frames:
                self.end_of_game = True
        current_time = Utils.get_current_time()
        if current_time > self.started_time:
            self.frame_speed = self.frames_count / (current_time - self.started_time)
        else:
            self.frame_speed = 0

    def __print_info(self):#输出信息
        if self.is_debug:
            if self.frames_count % self.log_freq == 0:
                print("Number of players' bullets:", len(self.bullets_player))
                print("Number of enemies' bullets:", len(self.bullets_enemy))
                print("Current frame:", self.frames_count)
                print("Player 1 score:", self.total_score_p1)
                print("Player 2 score:", self.total_score_p2)
                print("Total score:", self.total_score)
                print("Number of players left", len(self.players))
                print("Frame speed (FPS):", self.frame_speed)
                print("")

    def __render(self):#渲染

        # 处理用户事件
        if self.rd:
            self.__handle_event()

        # 绘制背景
        self.screen.fill(Utils.get_color(Utils.BLACK))

        # 更新精灵
        self.sprites.update()

        # 更新敌军
        self.__enemies_update()

        # 更新子弹
        self.__bullets_update()

        # 重新加载所有精灵
        self.sprites.draw(self.screen)

        # 得分
        self.__draw_score()

        # 清除所有爆炸效果
        self.__remove_explosions()

        # 向屏幕显示到目前为止我们绘制的内容
        if self.rd:
            pygame.display.flip()

        # 维持 20 fps
        pygame.time.Clock().tick(self.speed)

        # 计算帧数
        self.__calculate_fps()

        # 调试
        self.__print_info()

    def set_seed(self, seed):
        self.seed = seed

    def reset(self):#重置游戏
        self.end_of_game = False
        self.frames_count = 0
        self.enemy_speed = GlobalConstants.ENEMY_SPEED
        self.enemy_bullet_loading_time = GlobalConstants.ENEMY_LOADING_TIME
        self.started_time = Utils.get_current_time()

        for sprite in self.sprites:
            sprite.kill()

        self.__generate_base_and_walls()
        self.__generate_players()
        self.__generate_enemies(self.num_of_enemies)

        self.stage_map.load_map(self.current_stage)

        if self.is_debug:

            interval = Utils.get_current_time() - self.started_time
            print("#################  RESET GAME  ##################")
            print("Episode terminated after事件经过时间:", interval, "(s)")
            print("Total score:", self.total_score)
            print("Player 1 score:", self.total_score_p1)
            print("Player 2 score:", self.total_score_p2)
            print("#################################################")

        self.total_score = 0
        self.total_score_p1 = 0
        self.total_score_p2 = 0

        self.__render()

    def step(self, action, action_p2=-1):#自动走
        if self.player1_human_control and self.player2_human_control:
            raise ValueError("Error: 人工控制模式")
        players = []
        if not self.player1_human_control and not self.player2_human_control:
            if self.two_players:
                if action == GlobalConstants.P1_LEFT_ACTION:
                    self.player1.move(GlobalConstants.LEFT_ACTION, self.sprites)
                elif action == GlobalConstants.P1_RIGHT_ACTION:
                    self.player1.move(GlobalConstants.RIGHT_ACTION, self.sprites)
                elif action == GlobalConstants.P1_UP_ACTION:
                    self.player1.move(GlobalConstants.UP_ACTION, self.sprites)
                elif action == GlobalConstants.P1_DOWN_ACTION:
                    self.player1.move(GlobalConstants.DOWN_ACTION, self.sprites)
                elif action == GlobalConstants.P1_FIRE_ACTION:
                    self.__fire_bullet(self.player1, False)

                if action_p2 == GlobalConstants.P2_LEFT_ACTION:
                    self.player2.move(GlobalConstants.LEFT_ACTION, self.sprites)
                elif action_p2 == GlobalConstants.P2_RIGHT_ACTION:
                    self.player2.move(GlobalConstants.RIGHT_ACTION, self.sprites)
                elif action_p2 == GlobalConstants.P2_UP_ACTION:
                    self.player2.move(GlobalConstants.UP_ACTION, self.sprites)
                elif action_p2 == GlobalConstants.P2_DOWN_ACTION:
                    self.player2.move(GlobalConstants.DOWN_ACTION, self.sprites)
                elif action_p2 == GlobalConstants.P2_FIRE_ACTION:
                    self.__fire_bullet(self.player2, False)
                players.append(GlobalConstants.PLAYER_1_OWNER)
                players.append(GlobalConstants.PLAYER_2_OWNER)
            else:
                if action != GlobalConstants.FIRE_ACTION:
                    self.player1.move(action, self.sprites)
                else:
                    self.__fire_bullet(self.player1, False)
                players.append(GlobalConstants.PLAYER_1_OWNER)
        else:
            if not self.player1_human_control:
                if action != GlobalConstants.FIRE_ACTION:
                    self.player1.move(action, self.sprites)
                else:
                    self.__fire_bullet(self.player1, False)
                players.append(GlobalConstants.PLAYER_1_OWNER)
            else:
                if self.two_players:
                    if action != GlobalConstants.FIRE_ACTION:
                        self.player2.move(action, self.sprites)
                    else:
                        self.__fire_bullet(self.player2, False)
                    players.append(GlobalConstants.PLAYER_2_OWNER)
                else:
                    raise ValueError("Error: human control mode")

        if self.frame_skip <= 1:
            self.__render()
        else:
            for _ in range(self.frame_skip):
                self.__render()

        return self.__check_reward()

    def render(self):#渲染
        self.__render()

    def step_all(self, action):
        r = self.step(action)
        next_state = self.get_state()
        terminal = self.is_terminal()
        return next_state, r, terminal

    def get_state_space(self):
        return [self.screen_size, self.screen_size]

    def get_action_space(self):
        return range(self.num_of_actions)

    def get_state(self):
        pygame.pixelcopy.surface_to_array(self.current_buffer, self.screen)
        return self.current_buffer

    def is_terminal(self):
        return self.end_of_game

    def debug(self):
        self.__print_info()

    def get_num_of_actions(self):
        return self.num_of_actions

    def is_render(self):
        return self.rd