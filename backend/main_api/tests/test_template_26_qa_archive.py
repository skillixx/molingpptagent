"""验收归档入口不得覆盖已经获得用户确认的候选。"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('filename,state', [
    ('candidate.json', {'candidateId': 'approved-candidate', 'humanConfirmed': True}),
    ('closure.json', {'candidateId': 'approved-candidate', 'T8': '已完成', 'goalClosed': True}),
])
def test_archive_refuses_to_overwrite_confirmed_candidate_before_reading_inputs(tmp_path, filename, state):
    """复制公开命令入口到隔离目录，已确认状态应优先保护，不读取后续缺失输入。"""
    script = tmp_path / 'utils/finalize_template_26_qa.py'
    script.parent.mkdir()
    script.write_bytes((ROOT / 'utils/finalize_template_26_qa.py').read_bytes())
    qa = tmp_path / 'doc/assets/template_26_qa'
    qa.mkdir(parents=True)
    record = qa / filename
    original = json.dumps(state, ensure_ascii=False).encode('utf-8')
    record.write_bytes(original)
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, encoding='utf-8',
                            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
    assert result.returncode != 0
    assert '已人工确认' in result.stderr
    assert record.read_bytes() == original


@pytest.mark.parametrize('script_name,summary_name,kind', [
    ('verify_template_26_browser.cjs', 'summary.json', 'browser'),
    ('verify_template_26_runtime.cjs', 'runtime-summary.json', 'runtime'),
    ('verify_template_26_persistence.py', 'persistence-summary.json', 'python'),
    ('run_template_26_handler_qa.py', 'real-handler-summary.json', 'python'),
])
def test_failed_new_run_invalidates_previous_pass(tmp_path, script_name, summary_name, kind):
    """直接执行工具并制造依赖加载失败，旧 PASS 必须在失败前失效。"""
    script = tmp_path / 'utils' / script_name
    script.parent.mkdir()
    script.write_bytes((ROOT / 'utils' / script_name).read_bytes())
    qa = tmp_path / 'doc/assets/template_26_qa'
    qa.mkdir(parents=True)
    summary = qa / summary_name
    summary.write_text('{"status":"PASS"}', encoding='utf-8')
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PLAYWRIGHT_PACKAGE_PATH': str(tmp_path / 'missing-playwright')}
    if kind == 'python':
        command = [sys.executable, '-S', str(script), str(qa / 'missing-edited.json')]
    elif kind == 'browser':
        source = qa / 'input.json'
        source.write_text('{"slides":[]}', encoding='utf-8')
        command = ['node', str(script), str(source), str(qa)]
    else:
        command = ['node', str(script), str(qa)]
    result = subprocess.run(command, capture_output=True, env=env)
    assert result.returncode != 0
    assert json.loads(summary.read_text(encoding='utf-8'))['status'] != 'PASS'
