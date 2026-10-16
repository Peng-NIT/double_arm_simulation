# 强电检修 6DOF 机械臂仿真实验

这是一个面向本科实验教学的多页面 Streamlit 项目，按五个页面串联自然语言、PDDL、运动规划和 MuJoCo 仿真：

1. 强电检修物体与目标区域配置；
2. 自然语言解析、PDDL domain/problem/plan 展示与修改；
3. PDDL 动作到 6DOF 运动路点及关节参数的展开；
4. MuJoCo 仿真执行；
5. 关节轨迹、末端轨迹和物体最终位置分析。

## 五页实验流程

1. **场景配置**：选择强电检修物体、阅读操作提示，并理解初始区域与 XYZ 坐标的关系。
2. **PDDL 规划**：生成、查看和修改 PDDL，并由 ChatGPT 生成分级学习提示和课程范围内的可视化深度解读。
3. **运动参数**：查看物体专用操作模板，在安全范围内修改播放速度、安全高度、接近距离、路点与 q1～q6，并生成参数深度解读。
4. **仿真执行**：在 MuJoCo 中执行 PDDL 对应的专用动作序列。
5. **结果分析**：查看六关节曲线、末端三维轨迹和轨迹统计，并下载 CSV。

> 本项目仅用于教学仿真，不构成真实带电检修的安全方案。

## 安装与运行

使用现有的 `pytorch` Conda 环境：

```bash
conda activate pytorch
cd "/Users/pengsu/Project/Application_2026/仿真实验申请"
streamlit run app.py
```

## Streamlit Community Cloud 部署环境

- 部署入口文件选择 `streamlit_app/app.py`（如果仓库根目录就是本目录，则选择 `app.py`）。
- 在 **Advanced settings** 中选择 **Python 3.12**，不要使用 Python 3.14。
- `packages.txt` 已包含 MuJoCo 离屏渲染需要的 OSMesa/OpenGL 系统库。
- Linux 云端没有桌面显示器，程序会在导入 MuJoCo 前强制切换为 OSMesa 离屏渲染；启动日志中应出现 `[robot_sim] MuJoCo offscreen backend: OSMesa`。macOS 和 Windows 本地运行仍使用原有渲染方式。
- 如果已经使用 Python 3.14 创建了应用，需要记录现有域名和 Secrets，删除该应用后用 Python 3.12 重新部署。Streamlit Cloud 目前不能直接修改已部署应用的 Python 版本。

## 配置 ChatGPT 调用

正式部署时不要把 API Key 写入源码或提交到 GitHub。项目按以下顺序读取配置：

1. Streamlit Secrets；
2. 同名环境变量；
3. `OPENAI_BASE_URL` 和 `OPENAI_MODEL` 使用项目默认值。

在 Streamlit Cloud 的 **App settings → Secrets** 中填写：

```toml
OPENAI_API_KEY = "填写重新生成的密钥"
OPENAI_BASE_URL = "https://api.apiyi.com/v1"
OPENAI_MODEL = "gpt-4.1"
```

仓库提供了 `.streamlit/secrets.toml.example` 作为字段示例；真正的 `.streamlit/secrets.toml` 已被 `.gitignore` 排除。由于旧密钥曾经出现在源码中，部署前应在接口服务商后台作废旧密钥并生成新密钥。

本地运行也可以使用环境变量：

```bash
export OPENAI_API_KEY="你的新密钥"
export OPENAI_BASE_URL="https://api.apiyi.com/v1"
export OPENAI_MODEL="gpt-4.1"
streamlit run app.py
```

PDDL 页面取消勾选“使用 ChatGPT 解析”后，可以使用本地关键词解析。可视化深度解读使用项目内置的 `answer-me-with-html`，运行环境还需安装 Node.js 20 或更高版本。

## 推荐演示

实验初始场景不预置物体。先在“场景配置”中添加“故障熔断器”，再输入：

```text
将故障熔断器放入回收区
```

依次点击“解析任务并生成 PDDL”和“执行完整计划”。

## 设计说明

- PDDL 负责显示高层任务逻辑；内置教学规划器求解限定的 pick/place 问题，不依赖外部规划器程序。
- 实验台预置熔断器槽、端子槽、断路器安装位、检测点、开关操作点和护罩覆盖区；学生添加的是机械臂需要操作的对象。
- 页面显式展示“操作对象—推荐任务—固定设施—检修动作展开—重点参数”的对应关系。
- 每个PDDL初始语义区域都映射到明确的MuJoCo X/Y矩形边界；切换区域会同步更新坐标滑条，并阻止物体互相重叠。
- PDDL目标区域坐标直接由同一份区域配置生成，避免规划目标与场景显示使用两套坐标；仿真画面会高亮当前语义区域的真实边界。
- 教学工位使用蓝、灰、橙、黄四种色块和边框区分，画面下方直接说明颜色含义；当前对象关联工位会被高亮。
- 不同强电检修物体采用有区分度的教学动作模板，例如熔断器轴向拔出、端子排垂直插拔、断路器面板操作、验电笔与操作杆中部夹持、绝缘子侧向搬运等。
- PDDL 与运动参数页面均提供圆形问号提示；复杂概念可通过课程限定的 AI 深度解读生成结构化讲解页。
- 6DOF 机械臂使用 MuJoCo 雅可比矩阵进行数值逆运动学。
- 学生可以修改末端路点、六个关节角、插值方式、安全高度和操作距离。
- q1～q6 仅允许在推荐 IK 解附近局部调节；保存前同时检查当前姿态及相邻两段插值轨迹。
- 场景、运动参数和执行页面提供预设机位、聚焦对象、方位角、俯仰角和缩放距离控制。
- 为避免穿模，界面使用经过测试的教学安全范围：安全高度 0.48～0.56 m、抓取偏移 0.075～0.090 m、轴向距离 0.08～0.14 m；末端路点和 q1～q6 也受到安全工作区限制。
- 每次执行前会逐帧检查整条插值轨迹；检测到桌面、柜体、自碰撞或越界时拒绝执行并指出发生问题的步骤。
- 本项目不实现工业级避障或真实强电作业控制。
