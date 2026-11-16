"""Build and publish verified application releases, never user data/configuration.

--dry-run writes a local archive/manifest only and makes no network requests.
--app-version builds that version in an isolated copy if the current EXE differs.
--upload-all publishes code; database sync is opt-in through --upload-db.
"""
import argparse,ast,datetime,json,marshal,os,re,shutil,subprocess,sys,tempfile,types,zipfile
from pathlib import Path
from cloud_sync import CloudDatabaseSync,S3Store,sha256,validate_manifest
import sync_manager as sync

def signature(code):
    def constant(value):
        if isinstance(value,types.CodeType):return signature(value)
        if isinstance(value,frozenset):return ('frozenset',tuple(sorted((constant(item) for item in value),key=repr)))
        if isinstance(value,tuple):return ('tuple',tuple(constant(item) for item in value))
        return repr(value)
    return (code.co_code,code.co_names,code.co_varnames,tuple(constant(c) for c in code.co_consts))

def verify_binary(root):
    from PyInstaller.archive.readers import CArchiveReader
    if sync.DEFAULT_APP_SLUG=='tns_studio':
        archive=CArchiveReader(str(root/'ТНС_Энерго_Студия.exe'));modules=archive.open_embedded_archive('PYZ.pyz')
        for name in ('sync_manager','core_engine','cloud_sync','tns_input','database_safety','windows_update','ui_sync_components','app_self_test'):
            expected=compile((root/(name+'.py')).read_text(encoding='utf-8-sig'),name+'.py','exec')
            if signature(modules.extract(name))!=signature(expected):raise ValueError('EXE не соответствует исходникам: '+name)
        expected=compile((root/'app_gui.py').read_text(encoding='utf-8-sig'),'app_gui.py','exec')
        if signature(marshal.loads(archive.extract('app_gui')))!=signature(expected):raise ValueError('EXE не соответствует app_gui.py')
    else:
        archive=CArchiveReader(str(root/'Хрисаор.exe'))
        expected=compile((root/'launcher_chrysaor.py').read_text(encoding='utf-8-sig'),'launcher_chrysaor.py','exec')
        if signature(marshal.loads(archive.extract('launcher_chrysaor')))!=signature(expected):raise ValueError('EXE не соответствует загрузчику')
    helper=CArchiveReader(str(root/'update_helper.exe'))
    expected=compile((root/'update_helper.py').read_text(encoding='utf-8-sig'),'update_helper.py','exec')
    if signature(marshal.loads(helper.extract('update_helper')))!=signature(expected):raise ValueError('Установщик не соответствует исходникам')

def release_files(root):
    files=[p for p in root.iterdir() if p.is_file() and p.suffix in ('.py','.spec')]
    names=['update_helper.exe','ТНС_Энерго_Студия.exe' if sync.DEFAULT_APP_SLUG=='tns_studio' else 'Хрисаор.exe']
    files.extend(root/name for name in names)
    if sync.DEFAULT_APP_SLUG=='chrysaor':files.extend(p for p in (root/'static').rglob('*') if p.is_file() and p.suffix in ('.css','.js','.html','.svg','.png','.ico','.woff2'))
    for path in files:
        if not path.is_file():raise ValueError('Нет файла дистрибутива: '+str(path))
        if path.suffix in ('.py','.spec','.js','.html') and re.search(rb'\b(?:YCA|YCP)[A-Za-z0-9_-]{15,}',path.read_bytes()):raise ValueError('В исходнике обнаружен ключ доступа: '+path.name)
    return sorted(files)

def build_if_needed(source,version,build_root):
    for path in release_files(source):
        relative=path.relative_to(source);target=build_root/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    sm=build_root/'sync_manager.py';text=sm.read_text(encoding='utf-8-sig')
    text=re.sub(r'DEFAULT_APP_VERSION\s*=\s*"[^"]+"',f'DEFAULT_APP_VERSION = "{version}"',text,count=1);sm.write_text(text,encoding='utf-8')
    try:verify_binary(build_root);return
    except Exception:pass
    spec='ТНС_Энерго_Студия.spec' if sync.DEFAULT_APP_SLUG=='tns_studio' else 'Хрисаор.spec'
    environment=os.environ.copy();environment['PATH']=os.pathsep.join([sys.base_prefix,str(Path(sys.base_prefix)/'DLLs'),str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32'),os.environ.get('SystemRoot','C:/Windows')])
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--distpath',str(build_root),'--workpath',str(build_root/'build'),spec],cwd=build_root,env=environment,check=True)
    verify_binary(build_root)

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-version',default=sync.DEFAULT_APP_VERSION)
    parser.add_argument('--notes',default='Исправления расчётов, интерфейса и синхронизации.')
    parser.add_argument('--upload-all',action='store_true')
    parser.add_argument('--upload-db',action='store_true')
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--output-dir',type=Path)
    args=parser.parse_args(argv)
    if not re.fullmatch(r'\d+\.\d+\.\d+',args.app_version):parser.error('Версия должна иметь формат X.Y.Z')
    source=Path(__file__).resolve().parent;output=(args.output_dir or source/'releases').resolve();output.mkdir(parents=True,exist_ok=True)
    config=sync.S3Config();summary={'app_slug':config.app_slug,'app_version':args.app_version,'dry_run':args.dry_run,'uploaded':False}
    if args.upload_all or not args.upload_db:
        with tempfile.TemporaryDirectory(prefix='release-build-') as temporary:
            built=Path(temporary);build_if_needed(source,args.app_version,built)
            files=release_files(built);hashes={p.relative_to(built).as_posix():sha256(p) for p in files}
            marker={'app_slug':config.app_slug,'app_version':args.app_version,'files':hashes}
            package=output/f'{config.app_slug}_v{args.app_version}.zip'
            with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as archive:
                for path in files:archive.write(path,path.relative_to(built).as_posix())
                archive.writestr('release.json',json.dumps(marker,ensure_ascii=False,indent=2))
        info={'filename':package.name,'url':f'{config.s3_endpoint.rstrip("/")}/{config.s3_bucket}/{config.app_slug}/releases/{package.name}','file_size':package.stat().st_size,'sha256':sha256(package)}
        summary.update(package=str(package),package_info=info,files_verified=len(hashes))
        manifest={'app_slug':config.app_slug,'app_name':sync.DEFAULT_APP_NAME,'app_version':args.app_version,'release_date':datetime.date.today().isoformat(),'release_notes':args.notes,'package':info}
        if args.upload_all and not args.dry_run:
            store=S3Store(config);key=config.app_slug+'/latest.json';previous,etag=store.get_json(key)
            if previous:
                validate_manifest(previous,config)
                if sync.DEFAULT_APP_SLUG=='chrysaor':parse=sync.parse_semver
                else:parse=lambda value:tuple(map(int,value.split('.')))
                if parse(args.app_version)<=parse(previous['app_version']):raise ValueError('Публикуйте только новую версию, чтобы не перезаписать существующий релиз.')
                previous.update(manifest);manifest=previous
            store.put_file(config.app_slug+'/releases/'+package.name,package,'application/zip')
            store.put_json(key,manifest,etag)
            summary['uploaded']=True
        (output/(config.app_slug+'_manifest.json')).write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    if args.upload_db:
        db=sync.DatabaseManager();service=CloudDatabaseSync(config,db,args.app_version,sync.DEFAULT_APP_NAME)
        try:
            if args.dry_run:
                snapshot=service.snapshot()
                try:summary['database_snapshot_sha256']=sha256(snapshot)
                finally:os.unlink(snapshot)
            else:summary['database']=service.push()
        finally:
            if hasattr(db,'close'):db.close()
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as error:
        print('Публикация не завершена: '+str(error),file=sys.stderr);sys.exit(1)
