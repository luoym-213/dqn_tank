import matplotlib.pyplot as plt


y = []

# 绘制折线图
plt.plot([index for index in range(len(y))], y)

# 添加标题和轴标签
plt.title('Line Chart')
plt.xlabel('X Label')
plt.ylabel('Y Label')

# 显示图形
plt.show()