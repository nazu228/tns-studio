"""Independent Windows installer. No process killing or execution-policy bypass."""
import ctypes,datetime,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path

def _hash(path):
    with open(path,'rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def wait_pid(pid,timeout=90):
    if not pid:return
    kernel=ctypes.windll.kernel32
    kernel.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];kernel.OpenProcess.restype=ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong];kernel.WaitForSingleObject.restype=ctypes.c_ulong
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    handle=kernel.OpenProcess(0x00100000,False,int(pid))
    if not handle:return
    try:
        if kernel.WaitForSingleObject(handle,int(timeout*1000))!=0:raise RuntimeError('Программа ещё работает. Установка отменена; закройте её и повторите обновление.')
    finally:kernel.CloseHandle(handle)

def install(plan,restart=True):
    target=Path(plan['target']).resolve();source=Path(plan['payload']).resolve()
    if target==source or target in source.parents:raise ValueError('Каталог обновления должен находиться вне программы.')
    actual=set()
    for path in source.rglob('*'):
        if path.is_symlink() or path.is_junction():raise ValueError('Ссылки в пакете обновления запрещены.')
        if path.is_file():actual.add(path.relative_to(source).as_posix())
    if actual!=set(plan['files']):raise ValueError('Пакет изменён после подготовки установки.')
    paths=[]
    for name,expected in plan['files'].items():
        previous=target/name;updated=source/name
        if not previous.resolve().is_relative_to(target) or not updated.resolve().is_relative_to(source):raise ValueError('Путь вне каталога установки.')
        if any(part.lower() in {'database','backups','sync_config.json','apps_config.json','settings.json'} for part in Path(name).parts):raise ValueError('Запрещено изменять пользовательские данные.')
        if _hash(updated)!=expected:raise ValueError('Пакет изменён после проверки: '+name)
        paths.append((name,previous,updated,expected))
    print('[1/4] Ожидание закрытия программы…',flush=True)
    wait_pid(plan['parent_pid'])
    backup=target/'backups'/'updates'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup.mkdir(parents=True)
    log=backup/'install.log'
    existing=[]
    for name,previous,_,_ in paths:
        if previous.exists():
            saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(previous,saved);existing.append(name)
    (backup/'rollback.json').write_text(json.dumps({'files':[name for name,_,_,_ in paths],'existing':existing},ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        print('[2/4] Копирование обновления…',flush=True)
        with open(log,'w',encoding='utf-8') as stream:
            result=subprocess.run(['robocopy.exe',str(source),str(target),'/E','/R:15','/W:1','/NP','/NDL','/NFL'],stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode>=8:raise RuntimeError(f'Ошибка копирования robocopy: {result.returncode}.')
        for name,previous,_,expected in paths:
            if _hash(previous)!=expected:raise RuntimeError('Проверка установленного файла не пройдена: '+name)
        print('[3/4] Проверка файлов выполнена. Резервная копия: '+str(backup),flush=True)
        if restart:
            print('[4/4] Запуск программы…',flush=True)
            subprocess.Popen([plan['restart_exe'],*plan['restart_args']],cwd=target,creationflags=subprocess.CREATE_NO_WINDOW)
        with open(log,'a',encoding='utf-8') as stream:stream.write('\nSUCCESS '+str(plan['version']))
        return backup
    except Exception as error:
        for name,previous,_,_ in reversed(paths):
            if name in existing:shutil.copy2(backup/name,previous)
            elif previous.is_file():previous.unlink()
        with open(log,'a',encoding='utf-8') as stream:stream.write('\nROLLED BACK: '+str(error))
        raise

if __name__=='__main__':
    try:
        if sys.stdout and hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
        plan=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
        install(plan)
        print('Обновление установлено и файлы проверены.',flush=True)
        time.sleep(2)
    except Exception as error:
        message='Обновление не завершено: '+str(error)
        try:print(message,flush=True)
        except Exception:pass
        if os.name=='nt':ctypes.windll.user32.MessageBoxW(None,message,'Обновление программы',0x10)
        sys.exit(1)
