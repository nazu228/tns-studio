"""Prepare a verified update without changing PowerShell/security settings."""
import hashlib,json,os,shutil,subprocess,sys,tempfile,zipfile
from pathlib import Path,PurePosixPath

PROTECTED={'database','backups','reports','temp_reports','sync_config.json','apps_config.json','settings.json'}

def unpack_release(archive,destination,slug):
    destination=Path(destination).resolve()
    with zipfile.ZipFile(archive) as package:
        entries=package.infolist()
        if sum(item.file_size for item in entries)>1024*1024*1024:raise ValueError('Слишком большой пакет обновления.')
        names=set()
        for item in entries:
            name=item.filename.replace('\\','/')
            path=PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or ':' in name or not path.parts:raise ValueError('Небезопасный путь в архиве обновления.')
            if any(part.lower() in PROTECTED or part.startswith('.') for part in path.parts):raise ValueError('Пакет содержит пользовательскую базу, настройки или скрытые файлы.')
            if (item.external_attr>>16)&0o170000==0o120000:raise ValueError('Ссылки в пакете обновления запрещены.')
            if name.casefold() in names:raise ValueError('Дублирующиеся файлы в пакете обновления.')
            names.add(name.casefold())
        marker=json.loads(package.read('release.json'))
        if marker.get('app_slug')!=slug:raise ValueError('Пакет предназначен для другой программы.')
        import re
        if not re.fullmatch(r'\d+\.\d+\.\d+',str(marker.get('app_version',''))):raise ValueError('Некорректная версия пакета.')
        files=marker.get('files')
        if not isinstance(files,dict) or not files:raise ValueError('В пакете отсутствует список контрольных сумм.')
        actual={item.filename for item in entries if not item.is_dir() and item.filename!='release.json'}
        if set(files)!=actual:raise ValueError('Содержимое пакета не совпадает с release.json.')
        for name,expected in files.items():
            target=destination/Path(name)
            if not target.resolve().is_relative_to(destination):raise ValueError('Путь вне каталога обновления.')
            target.parent.mkdir(parents=True,exist_ok=True)
            digest=hashlib.sha256()
            with package.open(name) as source,open(target,'wb') as output:
                while chunk:=source.read(65536):digest.update(chunk);output.write(chunk)
            if digest.hexdigest()!=expected:raise ValueError('Контрольная сумма файла в пакете не совпадает: '+name)
    return marker

def prepare_update(archive,app_dir,slug,restart_exe,restart_args=()):
    try:
        folder=Path(tempfile.mkdtemp(prefix=slug+'-update-'))
        payload=folder/'payload';payload.mkdir()
        marker=unpack_release(archive,payload,slug)
        app_dir=Path(app_dir).resolve()
        helper=app_dir/'update_helper.exe'
        if not helper.is_file():raise ValueError('Не найден автономный установщик update_helper.exe.')
        temporary_helper=folder/'update_helper.exe';shutil.copy2(helper,temporary_helper)
        plan={'parent_pid':os.getpid(),'target':str(app_dir),'payload':str(payload),'files':marker['files'],'version':marker['app_version'],'restart_exe':str(restart_exe),'restart_args':list(restart_args)}
        plan_path=folder/'update-plan.json';plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
        subprocess.Popen([str(temporary_helper),str(plan_path)],cwd=str(folder),creationflags=subprocess.CREATE_NEW_CONSOLE)
        return True,'Установщик запущен. Дождитесь завершения; журнал сохраняется в backups/updates.'
    except Exception as error:return False,'Обновление не запущено: '+str(error)
