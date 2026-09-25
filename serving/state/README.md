# State Registry

- models.json：模型登记表（类型/后端/路径/lazy_load/deployed）。禁止写入 IP、password、token、secret。
- service_state.json：各服务端口与状态快照。
- gpu.lock：Image/Video 服务运行期互斥锁（部署阶段才可能出现；staging 阶段应不存在）。
- vllm-before-stop.txt：将在"停止 vLLM"的部署阶段生成；本轮无。
