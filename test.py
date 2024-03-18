import torch
from model.net import DQN
from tankbattle.env.engine import TankBattle
from tankbattle.env.utils import Utils


device = "cpu"
max_iterator = 1
epsilon = 0.7647789637410702
data_save_path = "output/test/"
param_file = "param/predicted_402_0.7647789637410702_50.pth"


def test(game, net, init_state, epsilon, device, iteration=0):
    total_reward = 0.0
    state = init_state
    index = 0

    while True:
        game.render()
        action = net.act(state, epsilon, device)
        next_state, reward, done, _ = game.step(action)
        next_state = Utils.resize_image(next_state)
        reward = reward[0]

        """ 保存交互数据，根据需求自行定义"""
        # runtime_data = ("state", action, reward, "next_state", done)
        # Utils.save_data(runtime_data, f"{data_save_path}test_data_{iteration}_{index}.txt")

        total_reward += reward

        if done:
            print(total_reward)
            break
        state = next_state
        index += 1


if __name__ == "__main__":
    game = TankBattle(render=True, player1_human_control=False, player2_human_control=False, two_players=False,
                      speed=60, debug=False, frame_skip=5)

    for i in range(max_iterator):
        init_state = game.reset()
        state = Utils.resize_image(init_state)
        origin_net = DQN(input_shape=state.shape, num_actions=game.get_num_of_actions())
        net = Utils.load_model(origin_net, param_file)
        test(game, net, state, epsilon, device, iteration=i)


