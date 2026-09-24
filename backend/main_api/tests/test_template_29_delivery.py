"""交付复核不能撤销同一候选已收到的人工确认。"""
import copy
import json

import pytest

from utils.finalize_template_29_qa import persist_manifest


def records():
    pending = {'candidate': 'template_29-fixed', 'productionFiles': {'template.json': 'original'},
               'evidence': {'tests.xml': 'passed'}, 'status': 'AWAITING_HUMAN_CONFIRMATION',
               'humanConfirmation': None, 'createdAt': 'new-audit'}
    completed = {**copy.deepcopy(pending), 'status': 'COMPLETED', 'createdAt': 'original-audit',
                 'humanConfirmation': {'message': '确认完成'}, 'closedAt': 'user-confirmation-time'}
    return pending, completed


def test_reaudit_same_delivery_keeps_confirmation_and_file_unchanged(tmp_path):
    pending, completed = records()
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps(completed, ensure_ascii=False), encoding='utf-8')
    before = path.read_bytes()
    result = persist_manifest(path, pending)
    assert result == completed
    assert path.read_bytes() == before


@pytest.mark.parametrize('field', ['candidate', 'productionFiles', 'evidence'])
def test_changed_delivery_does_not_reuse_old_confirmation(tmp_path, field):
    pending, completed = records()
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps(completed), encoding='utf-8')
    pending[field] = 'template_29-new' if field == 'candidate' else {'changed': 'new-hash'}
    assert persist_manifest(path, pending) == pending
    actual = json.loads(path.read_text(encoding='utf-8'))
    assert actual['status'] == 'AWAITING_HUMAN_CONFIRMATION'
    assert actual['humanConfirmation'] is None
