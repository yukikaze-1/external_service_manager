#!/usr/bin/env python3
"""
Process runner: internal service process manager extracted from service_manager.py

提供最小化的进程启动/停止/状态接口：
- ProcessRunner.init_services(state_dict)
- ProcessRunner.stop_all_services()
- ProcessRunner.get_service_status()

此模块用于将低层进程管理逻辑与外部管理器分离。
"""

import os
import time
import subprocess
import shlex
import signal
from pathlib import Path
from typing import List, Tuple


class ProcessRunner:
    """最小化的外部服务管理器替代实现（内部使用）

    提供启动 / 停止 / 状态查询的基础能力，设计为被高层管理器调用。
    """

    def __init__(self):
        self.base_processes = []  # List[Tuple[name, Popen]]
        self.optional_processes = []
        self.config = {}

    def _load_config(self):
        project_root = Path(__file__).parents[2]
        cfg_path = Path(os.environ.get('AGENT_HOME', project_root)) / "Init" / "ExternalServiceInit" / "config.yml"
        if not cfg_path.exists():
            cfg_path = project_root / "config.yml"

        if not cfg_path.exists():
            self.config = {'external_services': {'base_services': [], 'optional_services': []}}
            return

        import yaml
        try:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                full = yaml.safe_load(f) or {}
                self.config = full.get('external_services', full)
        except Exception:
            self.config = {'external_services': {'base_services': [], 'optional_services': []}}

    def _start_service_from_config(self, svc_item, is_base: bool, state_dict=None):
        # svc_item 通常是 {name: config}
        try:
            if isinstance(svc_item, dict) and len(svc_item) == 1:
                svc_name = list(svc_item.keys())[0]
                svc_conf = svc_item[svc_name]
            elif isinstance(svc_item, dict) and 'service_name' in svc_item:
                svc_name = svc_item.get('service_name')
                svc_conf = svc_item
            else:
                return ("unknown", -1)

            script = svc_conf.get('script')
            args = svc_conf.get('args', []) or []
            use_python = svc_conf.get('use_python', False)
            conda_env = svc_conf.get('conda_env', '')
            run_bg = svc_conf.get('run_in_background', True)

            if use_python and conda_env and script:
                python_bin = os.path.join(conda_env, 'bin', 'python')
                cmd = [python_bin, script] + args
                shell = False
            else:
                if isinstance(script, str):
                    cmd = [script] + args
                    shell = True
                else:
                    return (svc_name, -1)

            cwd = None
            if isinstance(script, str) and os.path.isabs(script):
                cwd = os.path.dirname(script) or None

            # 自动从 args 里提取端口号
            def extract_port(args_list):
                port = None
                for i, a in enumerate(args_list):
                    if a in ('-p', '--port') and i + 1 < len(args_list):
                        try:
                            port_candidate = args_list[i + 1]
                            if isinstance(port_candidate, str) and port_candidate.isdigit():
                                port = int(port_candidate)
                        except Exception:
                            continue
                return port

            port = extract_port(args)
            # 兜底：部分服务端口写死
            if not port and svc_name == 'ollama_server':
                port = 11434
            if not port and svc_name == 'Consul':
                port = 8500

            if run_bg:
                if shell:
                    proc = subprocess.Popen(' '.join(shlex.quote(a) for a in cmd), shell=True,
                                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                             preexec_fn=os.setsid, cwd=cwd)
                else:
                    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                             preexec_fn=os.setsid, cwd=cwd)

                pid = proc.pid
                if is_base:
                    self.base_processes.append((svc_name, proc))
                else:
                    self.optional_processes.append((svc_name, proc))

                # 记录 pid 和端口到 state_dict
                if state_dict is not None:
                    state_dict[svc_name] = {
                        'pid': pid,
                        'start_time': time.time(),
                        'script': script,
                        'args': args,
                        'cwd': cwd,
                        'port': port
                    }

                return (svc_name, pid)
            else:
                # 前台运行：同步执行
                if shell:
                    subprocess.run(' '.join(shlex.quote(a) for a in cmd), shell=True, check=True, cwd=cwd)
                else:
                    subprocess.run(cmd, check=True, cwd=cwd)
                return (svc_name, -1)

        except Exception:
            return (svc_name if 'svc_name' in locals() else 'unknown', -1)

    def init_services(self, state_dict=None):
        self._load_config()
        base_cfg = self.config.get('base_services', [])
        optional_cfg = self.config.get('optional_services') or []

        base_results = []
        optional_results = []

        for item in base_cfg:
            base_results.append(self._start_service_from_config(item, True, state_dict=state_dict))

        for item in optional_cfg:
            optional_results.append(self._start_service_from_config(item, False, state_dict=state_dict))

        return base_results, optional_results

    def stop_all_services(self):
        # 停止可选服务
        for name, proc in self.optional_processes.copy():
            try:
                if proc.poll() is None:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                pass

        # 停止基础服务
        for name, proc in self.base_processes.copy():
            try:
                if proc.poll() is None:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                pass

        self.base_processes.clear()
        self.optional_processes.clear()

    def get_service_status(self):
        base_status = []
        for name, proc in self.base_processes:
            base_status.append({
                'name': name,
                'pid': proc.pid,
                'status': 'running' if proc.poll() is None else 'stopped'
            })

        optional_status = []
        for name, proc in self.optional_processes:
            optional_status.append({
                'name': name,
                'pid': proc.pid,
                'status': 'running' if proc.poll() is None else 'stopped'
            })

        return {'base_services': base_status, 'optional_services': optional_status}
