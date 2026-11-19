"""Interrupting the controller must not strand writers behind an inactive clock."""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
from fbk.workflow import managed_investigations as managed, review_execution, review, review_rounds
from fbk.workflow.store import WorkflowError


def running(pid):
    try:
        return Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[0] != 'Z'
    except FileNotFoundError:
        return False


@pytest.mark.parametrize('termination_unknown',[False,True])
def test_sigint_cleans_group_or_requires_durable_reconciliation(tmp_path,termination_unknown):
    project=tmp_path/'project';project.mkdir()
    source=tmp_path/'source';source.mkdir()
    (source/'app.py').write_text('answer=42\n')
    child_code=("import os,json,time; from pathlib import Path; "
                "Path('child-ready.json').write_text(json.dumps({'pid':os.getpid(),'pgid':os.getpgrp()})); "
                "time.sleep(30); Path('after-interrupt').write_text('orphan wrote')")
    worker_code=("import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',"+repr(child_code)+"]); time.sleep(30)")
    driver=tmp_path/'driver.py'
    package_root=Path(review.__file__).resolve().parents[2]
    driver.write_text(f'''import sys
from pathlib import Path
sys.path.insert(0,{str(package_root)!r})
from fbk.workflow import review, managed_investigations as managed, review_execution
root=Path({str(project)!r})
execution=managed.open_round(root,Path({str(source)!r}),{{'review_round_timeout':30}},'interrupt-test')
if {termination_unknown!r}: review._stop_process_group=lambda process: False
try:
    review.run_command([sys.executable,'-c',{worker_code!r}],root,30)
finally:
    execution.finish()
''')
    process=subprocess.Popen([sys.executable,str(driver)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    child=None
    try:
        deadline=time.monotonic()+10
        marker=project/'child-ready.json'
        while not marker.exists() and process.poll() is None and time.monotonic()<deadline:
            time.sleep(.01)
        assert marker.exists(),'Worker never started'
        child=json.loads(marker.read_text())
        process.send_signal(signal.SIGINT)
        process.communicate(timeout=10)
        assert process.returncode != 0
        state_path=next((project/'.fbk/runtime/review-rounds').glob('*/round.json'))
        record=json.loads(state_path.read_text())
        if termination_unknown:
            assert record['managed_clock']['active']
            assert record['budget']['spent_seconds'] >= record['budget']['seconds']
            with pytest.raises(WorkflowError,match='reconcil'):
                review_execution.activate_round(project,record['id'])
        else:
            assert not running(child['pid']),'Child remained able to write after its controller exited'
            assert not record['managed_clock']['active']
            assert 0 < record['budget']['spent_seconds'] < record['budget']['seconds']
        assert not (project/'after-interrupt').exists()
    finally:
        if child:
            try:os.killpg(child['pgid'],signal.SIGKILL)
            except ProcessLookupError:pass
        if process.poll() is None:process.kill()
        process.communicate(timeout=5)


def test_sigint_cancels_worker_threads_without_waiting_for_command_timeout(tmp_path):
    root=tmp_path/'project';root.mkdir()
    source=tmp_path/'source';source.mkdir()
    (source/'app.py').write_text('answer=42\n')
    command="import os,time; from pathlib import Path; Path('ready').write_text(str(os.getpid())); time.sleep(30)"
    driver=tmp_path/'parallel.py'
    driver.write_text(f'''import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,{str(Path(review.__file__).resolve().parents[2])!r})
from fbk.workflow import review, managed_investigations as managed, review_execution
root=Path({str(root)!r})
execution=managed.open_round(root,Path({str(source)!r}),{{'review_round_timeout':30}},'parallel-interrupt')
try:
    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(review.run_command,[sys.executable,'-c',{command!r}],root,30).result()
finally:
    execution.finish()
''')
    process=subprocess.Popen([sys.executable,str(driver)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    child=None
    try:
        deadline=time.monotonic()+10
        while not (root/'ready').exists() and time.monotonic()<deadline:time.sleep(.01)
        assert (root/'ready').exists()
        child=int((root/'ready').read_text())
        process.send_signal(signal.SIGINT)
        process.communicate(timeout=5)
        assert not running(child)
        record=json.loads(next((root/'.fbk/runtime/review-rounds').glob('*/round.json')).read_text())
        assert not record['managed_clock']['active']
        assert record['budget']['spent_seconds'] < 5
    finally:
        if child:
            try:os.killpg(child,signal.SIGKILL)
            except ProcessLookupError:pass
        if process.poll() is None:process.kill()
        process.communicate(timeout=5)


def test_recovery_cannot_clear_active_state_while_recorded_group_is_alive(tmp_path):
    source=tmp_path/'source';source.mkdir()
    root=tmp_path/'project';root.mkdir()
    execution=managed.open_round(root,source,{'review_round_timeout':30},'recovery-check')
    process=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],start_new_session=True)
    try:
        record=review_rounds.load_round(root,execution.round_id)
        record['managed_clock']['termination_unconfirmed']=[process.pid]
        review_rounds.save_round(root,record)
        with pytest.raises(WorkflowError,match='still running'):
            review_execution.recover_execution(root,execution.round_id,'Operator requests recovery')
        assert review_rounds.load_round(root,execution.round_id)['managed_clock']['active']
    finally:
        os.killpg(process.pid,signal.SIGKILL)
        process.wait(timeout=5)
        execution.finish()


def test_late_finish_cannot_refund_recovered_execution_or_close_its_successor(tmp_path):
    source=tmp_path/'source';source.mkdir()
    root=tmp_path/'project';root.mkdir()
    old=managed.open_round(root,source,{'review_round_timeout':30},'late-finish')
    review_execution.recover_execution(root,old.round_id,'Old processes stopped; recover interrupted controller')
    review_execution.extend_round(root,old.round_id,1,'Human authorizes one additional round')
    current=review_execution.activate_round(root,old.round_id)
    before=review_rounds.load_round(root,old.round_id)
    try:
        old.finish()
        after=review_rounds.load_round(root,old.round_id)
        assert after['budget']==before['budget']
        assert after['managed_clock']['active']
    finally:
        current.finish()
