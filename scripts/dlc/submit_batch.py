import subprocess  # 引入子进程管理模块，用于执行系统命令 (如 dlc submit)
import argparse    # 引入参数解析模块，用于处理命令行输入参数
import os          # 引入操作系统接口模块，用于文件路径检查等

# 定义提交作业的主函数
# chunk_total: 总的分块数量 (即将任务分成多少份)
# task_name: 任务的基础名称 (默认: render_grscenes100)
def submit_jobs(chunk_total, task_name="render_grscenes100"):
    # 循环遍历每一个分块 ID (从 0 到 chunk_total - 1)
    for chunk_id in range(chunk_total):
        # 构造要执行的命令字符串
        # 这里调用的是 bash 脚本 scripts/dlc/launch_job.sh
        # 并传递三个参数: 任务名称、当前分块ID、总分块数
        # 注意: 实际的 DLC 提交逻辑封装在 launch_job.sh 中
        cmd = f"bash scripts/dlc/launch_job.sh {task_name} {chunk_id} {chunk_total}"
        
        # 打印当前正在执行的命令，方便调试和记录日志
        print(f"Executing: {cmd}")
        
        # 使用 subprocess.run 执行命令
        # shell=True 表示在 Shell 环境中执行命令
        subprocess.run(cmd, shell=True)

# 脚本入口点
if __name__ == "__main__":
    # 初始化参数解析器
    parser = argparse.ArgumentParser()
    
    # 添加 --total 参数: 指定总分块数，默认为 30
    parser.add_argument("--total", type=int, default=30, help="Total number of chunks")
    
    # 添加 --name 参数: 指定任务名称，默认为 render_grscenes100
    parser.add_argument("--name", type=str, default="render_grscenes100", help="Base name for the task")
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 检查当前工作目录是否正确
    # 必须在项目根目录下运行此脚本，否则无法找到 launch_job.sh
    if not os.path.exists("scripts/dlc/launch_job.sh"):
        print("Error: Please run this script from the project root.")
        exit(1) # 如果文件不存在，以错误码 1 退出
        
    # 调用主函数开始提交作业
    submit_jobs(args.total, args.name)
