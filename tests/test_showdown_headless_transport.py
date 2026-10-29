"""No native battles: process visibility flags and pre-native failure authority."""
import ctypes
import json
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from advisor.showdown_bridge import SHOWDOWN_COMMIT, ShowdownBridge, ShowdownBridgeError, silent_process_options
from advisor.showdown_worker import ShowdownWorker


def test_platform_options_are_only_console_visibility():
    assert silent_process_options() == ({'creationflags': subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {})


def test_both_Git_pin_checks_are_headless_and_keep_strict_authority(monkeypatch,tmp_path):
    calls=[]
    def run(command,**options):
        calls.append((command,options))
        return SimpleNamespace(stdout=SHOWDOWN_COMMIT if 'rev-parse' in command else '')
    monkeypatch.setattr(subprocess,'run',run)
    ShowdownBridge(tmp_path)._verify_checkout()
    assert [c[0][1] for c in calls]==['rev-parse','status']
    for _,options in calls:
        assert options['check'] is True and options['capture_output'] is True and options['timeout']==5
        assert all(options[k]==v for k,v in silent_process_options().items())


def test_single_request_Node_transport_uses_same_visibility_option(monkeypatch,tmp_path):
    calls=[]
    monkeypatch.setattr(ShowdownBridge,'_verify_checkout',lambda self:None)
    monkeypatch.setattr(ShowdownBridge,'_validate_response',lambda self,request,response:response)
    def run(command,**options):
        calls.append((command,options))
        return subprocess.CompletedProcess(command,0,stdout='{"ok":true}',stderr='')
    monkeypatch.setattr(subprocess,'run',run)
    assert ShowdownBridge(tmp_path).run({'public':'only'})=={'ok':True}
    command,options=calls[0]
    assert command[0]=='node' and options['capture_output'] and not options['check']
    assert json.loads(options['input'])=={'public':'only'}
    assert all(options[k]==v for k,v in silent_process_options().items())


def test_closed_Git_validation_cannot_start_native_worker(monkeypatch,tmp_path):
    calls=[]
    def run(command,**options):
        if 'status' in command:
            raise subprocess.CalledProcessError(3221226091,command)
        return SimpleNamespace(stdout=SHOWDOWN_COMMIT)
    monkeypatch.setattr(subprocess,'run',run)
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**k:calls.append((a,k)))
    worker=ShowdownWorker(tmp_path)
    with pytest.raises(ShowdownBridgeError,match='showdown_unavailable_or_invalid_response'):
        worker.run({'schema_version':'showdown-environment-v1'})
    assert not calls and worker._process is None and worker._generation==0 and worker._request_id==0


def test_worker_Popen_uses_headless_flag_and_same_pipes(monkeypatch,tmp_path):
    captured={}
    monkeypatch.setattr(ShowdownWorker,'_verify_checkout',lambda self:None)
    class NoThread:
        def __init__(self,**kwargs):pass
        def start(self):pass
    monkeypatch.setattr('advisor.showdown_worker.Thread',NoThread)
    def popen(command,**options):
        captured.update(command=command,options=options)
        return SimpleNamespace(stdout=None)
    monkeypatch.setattr(subprocess,'Popen',popen)
    worker=ShowdownWorker(tmp_path);worker._start()
    assert captured['command'][0]=='node' and captured['command'][1].endswith('worker.cjs')
    options=captured['options']
    assert options['stdin']==subprocess.PIPE and options['stdout']==subprocess.PIPE and options['stderr']==subprocess.DEVNULL
    assert all(options[k]==v for k,v in silent_process_options().items())


@pytest.mark.skipif(os.name!='nt',reason='Windows console visibility')
def test_actual_console_child_has_no_window_and_keeps_pipe_output():
    code='import ctypes,json; print(json.dumps({"console":int(ctypes.windll.kernel32.GetConsoleWindow()),"ok":True}))'
    child=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,check=True,timeout=10,**silent_process_options())
    assert json.loads(child.stdout)=={'console':0,'ok':True}
