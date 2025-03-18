# Pod Cleaner

Pod Cleaner 是一个用于清理 Kubernetes 集群中处于 Error 或 Unknown 状态的 Pod 的命令行工具。

## 特性

- 支持多集群管理：自动加载 kubeconfig 目录下的所有集群配置
- 支持自定义 kubeconfig 目录：可以通过命令行参数或环境变量指定
- 错误状态 Pod 筛选：自动查找处于 Error 或 Unknown 状态的 Pod
- 安全删除：可以使用试运行模式查看将要删除的 Pod，并在实际删除前确认
- 命名空间过滤：支持按命名空间筛选
- 美观的命令行界面：使用 Rich 库提供彩色输出和表格显示
- 完整的日志记录：记录所有操作到日志文件
- 智能帮助：在使用无效参数时自动显示帮助信息
- 友好的错误处理：清晰展示错误信息，避免冗长的错误堆栈

## 安装

### 从源代码安装

```bash
# 克隆仓库
git clone https://github.com/author/pod-cleaner.git
cd pod-cleaner

# 安装
pip install -e .
```

### 使用 pip 安装

```bash
pip install pod-cleaner
```

## 配置

### kubeconfig 目录

你可以通过以下两种方式指定 kubeconfig 目录：

1. 命令行参数：
```bash
pod-cleaner list-pods --kubeconfig-dir /path/to/kubeconfig
```

2. 环境变量：
```bash
export KUBECONFIG_DIR=/path/to/kubeconfig
pod-cleaner list-pods
```

如果未指定，将使用默认目录 `kubeconfig`。

将你的 Kubernetes 集群的 kubeconfig 文件放在指定的 kubeconfig 目录下。每个文件将被视为一个单独的集群配置，文件名（不含扩展名）将作为集群名称。支持的文件格式：
- 以 `.yaml` 或 `.yml` 结尾的文件
- 以 `k8s` 或 `K8S` 开头的文件

例如：
- `kubeconfig/cluster1.yaml`
- `kubeconfig/k8s-prod.yml`
- `kubeconfig/K8S_dev`

## 使用方法

### 基本用法

如果运行时没有提供任何参数或提供了无效的参数，工具会自动显示帮助信息：
```bash
pod-cleaner
# 或
pod-cleaner --help
```

### 列出问题 Pod

```bash
# 列出所有集群中的问题 Pod
pod-cleaner list-pods

# 列出特定命名空间中的问题 Pod
pod-cleaner list-pods --namespace kube-system

# 使用自定义 kubeconfig 目录
pod-cleaner list-pods --kubeconfig-dir /path/to/kubeconfig
```

输出信息包括：
- 检查时间
- 集群总数
- 发现问题的集群数
- 问题 Pod 总数
- 每个集群中问题 Pod 的详细信息（命名空间、Pod名称、状态、创建时间）

### 清理问题 Pod

```bash
# 试运行模式（不实际删除 Pod）
pod-cleaner clean-pods --dry-run

# 删除所有集群中的问题 Pod
pod-cleaner clean-pods

# 删除特定命名空间的问题 Pod
pod-cleaner clean-pods --namespace kube-system

# 使用自定义 kubeconfig 目录
pod-cleaner clean-pods --kubeconfig-dir /path/to/kubeconfig
```

清理操作会：
1. 显示将要删除的 Pod 列表
2. 在非试运行模式下请求确认
3. 显示每个集群的清理结果（成功/失败数量）

### 查看集群信息

```bash
# 显示所有集群的版本信息
pod-cleaner cluster-info

# 使用自定义 kubeconfig 目录
pod-cleaner cluster-info --kubeconfig-dir /path/to/kubeconfig
```

显示的信息包括：
- 集群名称
- Kubernetes 版本
- API 服务器地址
- 构建日期
- 平台信息

## 错误处理

工具提供了友好的错误处理机制：

1. kubeconfig 目录不存在时：
```
错误: kubeconfig目录不存在: /path/to/kubeconfig
```

2. kubeconfig 目录中没有有效的配置文件时：
```
警告: 目录 /path/to/kubeconfig 中没有找到k8s kubeconfig文件
```

3. 使用无效的参数时：
```
错误: 无效的参数或命令

使用帮助:
[显示帮助信息]
```

## 日志

日志文件存储在 `logs/pod_cleaner.log`，使用滚动日志记录方式，每个日志文件最大 10MB，最多保留 5 个历史日志文件。

## 许可证

MIT 