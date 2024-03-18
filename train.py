import math
import numpy as np
from torch.optim import Adam
from torch.autograd import Variable
from torch import FloatTensor, LongTensor
from model.net import DQN
from model.train_information import TrainInformation
from tankbattle.env.engine import TankBattle
from tankbattle.env.utils import Utils
from model.replay_buffer import PrioritizedBuffer
import matplotlib.pyplot as plt


device = "cpu"
data_save_path = "output/train/"
param_save_path = "param/"
# 缓冲区大小
buffer_capacity = 960
# 学习率
learning_rate = 1e-4
# 训练轮数，实际训练时>=10000
num_episodes = 500
# 一次的训练批量
batch_size = 64
# 缓冲区数据量超过多少开始训练
initial_learning = 320
# 模型更新频率
target_update_frequency = 100
# 对未来reward的衰减值
gamma = 0.99
# 重要性采样权重
beta = 0.4


def update_epsilon(episode):
    eps_final = 0.01
    eps_start = 1.0
    decay = 100000
    epsilon = eps_final + (eps_start - eps_final) * \
              math.exp(-1 * ((episode + 1) / decay))
    return epsilon


def update_beta(episode):
    start = 0.4
    frames = 10000
    beta = start + episode * (1.0 - start) / frames
    return min(1.0, beta)


def compute_td_loss(model, target_net, replay_buffer, gamma, device,
                    batch_size, beta):
    batch = replay_buffer.sample(batch_size, beta)
    state, action, reward, next_state, done, indices, weights = batch

    state = Variable(FloatTensor(np.float32(state))).to(device)
    next_state = Variable(FloatTensor(np.float32(next_state))).to(device)
    action = Variable(LongTensor(action)).to(device)
    reward = Variable(FloatTensor(reward)).to(device)
    done = Variable(FloatTensor(done)).to(device)
    weights = Variable(FloatTensor(weights)).to(device)

    q_values = model(state)
    next_q_values = target_net(next_state)

    q_value = q_values.gather(1, action.unsqueeze(-1)).squeeze(-1)
    next_q_value = next_q_values.max(1)[0]
    expected_q_value = reward + gamma * next_q_value * (1 - done)

    loss = (q_value - expected_q_value.detach()).pow(2) * weights
    prios = loss + 1e-5
    loss = loss.mean()
    loss.backward()
    replay_buffer.update_priorities(indices, prios.data.cpu().numpy())


def train(game, net, target_model, optimizer, replay_buffer, device):

    # 记录当前训练的信息
    info = TrainInformation()

    reward_list = []
    max_reward = 0
    best_episode = 0

    for episode in range(num_episodes):
        # 开始每一轮的训练
        init_state = game.reset()
        state = Utils.resize_image(init_state)

        episode_reward = 0
        index = 0
        while True:
            epsilon = update_epsilon(info.index)
            if len(replay_buffer) > batch_size:
                beta = update_beta(info.index)
            else:
                beta = 0.4

            action = net.act(state, epsilon, device)
            next_state, reward, done, _ = game.step(action)
            next_state = Utils.resize_image(next_state)
            reward = reward[0]

            """ 保存交互数据，根据需求自行定义"""
            # runtime_data = ("state", action, reward, "next_state", done)
            # Utils.save_data(runtime_data, f"{data_save_path}train_data_{episode}_{index}.txt")

            episode_reward += reward
            # 更新一下当前的索引，其实就是+1操作
            info.update_index()

            if reward >= 0:
                # 把我们探索到的数据放到经验回放区中
                replay_buffer.push(state, action, reward, next_state, done)

            if len(replay_buffer) > initial_learning:
                if not info.index % target_update_frequency:
                    target_model.load_state_dict(net.state_dict())
                target_model.load_state_dict(net.state_dict())
                optimizer.zero_grad()
                # 计算Q信息
                compute_td_loss(net, target_model, replay_buffer, gamma, device,
                                batch_size, beta)
                optimizer.step()

            if done:
                break

            index += 1

        reward_list.append(episode_reward)

        print(f"Episode: {episode}, reward: {episode_reward}, epsilon: {epsilon}, max_reward: {max_reward}, best_episode: {best_episode}")

        if episode_reward >= max_reward:
            max_reward = episode_reward
            best_episode = episode
            Utils.save_model(net, param_save_path, episode, epsilon, episode_reward)
            print("model saved!")

    # 绘制折线图
    plt.plot([index for index in range(len(reward_list))], reward_list)

    # 添加标题和轴标签
    plt.title('Rewards of Episodes')
    plt.xlabel('episode')
    plt.ylabel('episode_reward')

    # 显示图形
    plt.show()

    """ 保存rewards数据，根据需求自行定义"""
    # format_data = Utils.data_saving_format(reward_list)
    # Utils.save_data(format_data, f"{data_save_path}train_rewards.txt")




if __name__ == "__main__":
    # 初始化游戏环境
    game = TankBattle(render=True, player1_human_control=False, player2_human_control=False,
                      two_players=False, speed=60, debug=False, frame_skip=5)
    # 初始化游戏
    init_state = game.reset()
    state = Utils.resize_image(init_state)
    # 初始化网络
    net = DQN(input_shape=state.shape, num_actions=game.get_num_of_actions())
    target_net = DQN(input_shape=state.shape, num_actions=game.get_num_of_actions())
    # 设置一下缓冲区
    replay_buffer = PrioritizedBuffer(buffer_capacity)
    # 设置我们的优化器。用于保存状态和更新参数
    optimizer = Adam(net.parameters(), lr=learning_rate)
    # 开始训练
    train(game, net, target_net, optimizer, replay_buffer, device)

