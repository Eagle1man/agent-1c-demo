import shutil, subprocess, time, re
from pathlib import Path

EXE = r'C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe'
PROJ = Path(r'C:\Users\diorl\.cline\data\workspaces\chat\agent-1c-demo')
bsl = (PROJ / '1c' / 'АгентМост.bsl').read_bytes().decode('utf-8-sig')
i_form = bsl.index('// === МОДУЛЬ ФОРМЫ ===')
form_code = bsl[i_form:].strip()
parts = re.split(r'(?m)^(?=Процедура |Функция )', form_code)
var_block = parts[0]
procs = parts[1:]

def test_full_bsl():
    dst = Path(r'C:\1c_bases\epf_test')
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(r'C:\1c_bases\epf_b4', dst)
    for f in dst.rglob('*'):
        if f.is_file():
            try:
                t = f.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                continue
            if 'B4' in t:
                f.write_text(t.replace('B4', 'TestEPF'), encoding='utf-8')
    (dst / 'B4.xml').rename(dst / 'TestEPF.xml')
    (dst / 'B4').rename(dst / 'TestEPF')
    
    # Сгенерируем полный код модуля со всеми 26 процедурами с перемещенными переменными
    out = var_block + '\n'
    for pr in procs:
        out += '&НаКлиенте\n' + pr + '\n'
    mod = dst / 'TestEPF' / 'Forms' / 'Форма' / 'Ext' / 'Form' / 'Module.bsl'
    mod.write_text(out, encoding='utf-8')
    
    epf = r'C:\1c_bases\TestEPF.epf'
    subprocess.run([EXE, 'DESIGNER', '/F', r'C:\1c_bases\DemoAgentT',
                   '/LoadExternalDataProcessorOrReportFromFiles', str(dst / 'TestEPF.xml'), epf,
                   '/DisableStartupDialogs'], capture_output=True)
    
    p = subprocess.Popen([EXE, 'ENTERPRISE', '/F', r'C:\1c_bases\DemoAgentT', '/Execute', epf, '/DisableStartupDialogs'])
    time.sleep(12)
    from pywinauto import Application
    app = Application(backend='uia').connect(process=p.pid)
    for _ in range(4):
        for w in app.windows():
            for c in w.descendants(control_type='Button'):
                if 'Да' in (c.window_text() or ''):
                    try:
                        c.click_input()
                    except Exception:
                        pass
        time.sleep(1)
    time.sleep(3)
    has_err = False
    for w in app.windows():
        for d in w.descendants():
            if 'непредвиденная ошибка' in (d.window_text() or ''):
                has_err = True
                break
    p.kill()
    return has_err

print('Full BSL in b4 skeleton: error =', test_full_bsl())
