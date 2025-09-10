## 服务器准备
可以尝试[智星云](https://gpu.ai-galaxy.cn/)的按小时租赁服务器，前期拉取镜像期间可以不用GPU。

## 仓库的ART的地址
https://github.com/johnson7788/RLTrainPPT

## 准备服务器上的clash代理
登录服务器，然后使用screen命令运行clash
```
screen -S clash
cd clash
./clash-linux-amd64-v1.10.0 -d .
```

##  尝试使用Areal的镜像
```
同步当前的仓库到服务器，然后拉取镜像
docker create --runtime=nvidia --gpus all --net=host --shm-size="10g" --cap-add=SYS_ADMIN -v .:/workspace/verl -v /etc/localtime:/etc/localtime:ro -v /etc/timezone:/etc/timezone:ro --name areal ghcr.io/inclusionai/areal-runtime:v0.3.0.post2 sleep infinity
docker start areal
docker exec -it areal bash
cd /workspace/verl/RLTrainPPT/ART
# 设置pip镜像源
pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
# 安装依赖
pip install -e .
大概安装22个依赖包，输入日志如下:
Successfully installed abnf-2.2.0 backoff-2.2.1 cint-1.0.0 distro-1.9.0 eval-type-backport-0.2.2 fickling-0.1.4 gql-4.0.0 graphql-core-3.2.6 graphviz-0.21 intervaltree-3.1.0 jiter-0.10.0 kaitaistruct-0.10 litellm-1.74.1 openai-1.99.1 openpipe-art-0.4.11 pdfminer.six-20240706 polyfile-weave-0.5.6 python-dotenv-1.1.1 requests_toolbelt-1.0.0 stdlib_list-0.11.1 typer-0.17.3 weave-0.52.5
pip install ".[backend]"
pip install 'torchtune @ git+https://github.com/pytorch/torchtune.git'
pip install 'unsloth-zoo @ git+https://github.com/bradhilton/unsloth-zoo'
```

## 测试模型加载是否正常
```
cd doc
python load_model.py
```

## 更多的测试用例参考项目
https://github.com/johnson7788/RLDecisionAgent
