"""Shared sync protocol: immutable SQLite snapshots and conditional manifest commits.

latest.json is the single authoritative commit pointer. database_meta.json is a
compatibility mirror, never used to override the committed database reference.
No network operation runs at import time; callers run these methods in workers.
"""
from contextlib import closing, nullcontext
from pathlib import Path
import base64
import ctypes
import datetime as dt
import hashlib
import json
import os
import re
import sqlite3
import ssl
import subprocess
import socket
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

_locks = {}
_locks_guard = threading.Lock()
_config_lock = threading.RLock()

class SyncError(RuntimeError):
    pass

class SyncConflict(SyncError):
    def __init__(self, message, details):
        super().__init__(message)
        self.details = details

def sha256(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def config_data(config):
    return config.data if hasattr(config, 'data') else config._data

def atomic_json(path, data):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with _config_lock:
        fd, temporary = tempfile.mkstemp(prefix='.config-', suffix='.json', dir=target.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):os.unlink(temporary)

class _Blob(ctypes.Structure):
    _fields_ = [('size', ctypes.c_ulong), ('data', ctypes.POINTER(ctypes.c_ubyte))]

def _dpapi(value, encrypt):
    if os.name != 'nt':raise SyncError('Защищенное хранение ключей поддерживается в Windows; используйте переменные окружения.')
    buffer = ctypes.create_string_buffer(value)
    source = _Blob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = _Blob()
    function = ctypes.windll.crypt32.CryptProtectData if encrypt else ctypes.windll.crypt32.CryptUnprotectData
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise SyncError('Не удалось прочитать или сохранить ключи Windows для текущего пользователя.')
    try:return ctypes.string_at(output.data, output.size)
    finally:
        local_free=ctypes.windll.kernel32.LocalFree
        local_free.argtypes=[ctypes.c_void_p];local_free.restype=ctypes.c_void_p
        local_free(output.data)

def credentials(config):
    data = config_data(config)
    key = (os.getenv('YC_ACCESS_KEY_ID') or os.getenv('AWS_ACCESS_KEY_ID') or '').strip()
    secret = (os.getenv('YC_SECRET_ACCESS_KEY') or os.getenv('AWS_SECRET_ACCESS_KEY') or '').strip()
    if key and secret:return key, secret
    if data.get('credentials_dpapi'):
        pair=json.loads(_dpapi(base64.b64decode(data['credentials_dpapi']),False))
        return pair['access_key_id'],pair['secret_access_key']
    return str(data.get('access_key_id') or '').strip(),str(data.get('secret_access_key') or '').strip()

def save_credentials(config, key, secret):
    key=(key or '').strip();secret=(secret or '').strip()
    if bool(key)!=bool(secret):raise SyncError('Введите оба ключа доступа. Пустые поля оставляют сохранённые ключи без изменений.')
    if not key:return
    if '...' in key:raise SyncError('Введите полный Access Key ID.')
    data=config_data(config)
    data['credentials_dpapi']=base64.b64encode(_dpapi(json.dumps({'access_key_id':key,'secret_access_key':secret}).encode(),True)).decode()
    data.pop('access_key_id',None);data.pop('secret_access_key',None)
    config.save()

def _prefix(config):
    endpoint=urllib.parse.urlsplit(config.s3_endpoint)
    if endpoint.scheme!='https' or not endpoint.netloc or endpoint.username or endpoint.password:
        raise SyncError('Для S3 требуется корректный HTTPS Endpoint.')
    if not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,62}',config.app_slug):raise SyncError('Некорректный идентификатор программы.')
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,62}',config.s3_bucket):raise SyncError('Некорректное имя бакета.')
    return f'{config.s3_endpoint.rstrip("/")}/{config.s3_bucket}/{config.app_slug}/'

def scoped_url(url, config, folder=None):
    prefix=_prefix(config)+(folder+'/' if folder else '')
    parsed=urllib.parse.urlsplit(str(url))
    decoded=urllib.parse.unquote(parsed.path)
    if not str(url).startswith(prefix) or parsed.query or parsed.fragment or '..' in decoded.split('/') or '\\' in decoded:
        raise SyncError('URL в манифесте не принадлежит этой программе и разделу S3.')
    return str(url)

def validate_hash(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9a-fA-F]{64}',value):raise SyncError('В манифесте отсутствует корректная SHA-256. Данные не изменены.')
    return value.lower()

def database_differs(config,remote_hash,local_hash):
    if not remote_hash:return False
    data=config_data(config)
    if remote_hash==local_hash:return False
    return not (data.get('last_sync_sha256')==remote_hash and data.get('last_sync_local_sha256')==local_hash)

def validate_manifest(data, config):
    if not isinstance(data,dict):raise SyncError('Некорректный манифест: ожидается JSON-объект.')
    if data.get('app_slug')!=config.app_slug:raise SyncError('Манифест относится к другой программе.')
    if not re.fullmatch(r'\d+\.\d+\.\d+',str(data.get('app_version',''))):raise SyncError('Некорректная версия программы в манифесте.')
    return data

class PublicHttp:
    def __init__(self):
        curl=Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/curl.exe'
        self.curl=str(curl) if os.name=='nt' and curl.is_file() else None

    def _curl_command(self,url,path,headers,max_time=30,max_size=512*1024*1024):
        if urllib.parse.urlsplit(str(url)).scheme!='https':raise SyncError('Для чтения облака требуется HTTPS.')
        return [self.curl,'--disable','--proto','=https','--proto-redir','=https','--location','--max-redirs','3','--silent','--show-error','--connect-timeout','7','--max-time',str(max_time),'--max-filesize',str(max_size),'--retry','1','--retry-max-time',str(max_time),'--user-agent','StudioSync/2','--header','Accept-Encoding: identity','--dump-header',headers,'--output',path,'--write-out','%{http_code}',str(url)]

    def get_json(self,url):
        if self.curl:
            with tempfile.TemporaryDirectory(prefix='studio-manifest-') as directory:
                body=str(Path(directory)/'body.json');headers=str(Path(directory)/'headers.txt')
                completed=subprocess.run(self._curl_command(url,body,headers,max_time=7,max_size=2*1024*1024),capture_output=True,timeout=17,creationflags=subprocess.CREATE_NO_WINDOW)
                status=completed.stdout.decode('ascii',errors='replace').strip()
                if status=='404':return None,None
                if completed.returncode or status!='200':raise SyncError(f'HTTPS Windows: HTTP {status or "нет ответа"}, код {completed.returncode}.')
                raw=Path(body).read_bytes()
                if len(raw)>2*1024*1024:raise SyncError('Манифест слишком большой.')
                parsed=json.loads(raw.decode('utf-8-sig'))
                etags=re.findall(r'(?im)^etag:\s*(.+)$',Path(headers).read_text(encoding='iso-8859-1'))
                return parsed,etags[-1].strip() if etags else None
        try:
            request=urllib.request.Request(url,headers={'Cache-Control':'no-cache','User-Agent':'StudioSync/2'})
            with urllib.request.urlopen(request,timeout=7,context=ssl.create_default_context()) as response:
                raw=response.read(2*1024*1024+1)
                if len(raw)>2*1024*1024:raise SyncError('Манифест слишком большой.')
                return json.loads(raw.decode('utf-8-sig')),response.headers.get('ETag')
        except urllib.error.HTTPError as error:
            if error.code==404:return None,None
            raise SyncError(f'Сервер S3 вернул HTTP {error.code}.') from error
        except (OSError,ValueError) as error:raise SyncError(f'Не удалось получить манифест: {error}') from error

    def download(self,url,path,expected,progress=None,cancel_event=None):
        if urllib.parse.urlsplit(str(url)).scheme!='https':raise SyncError('Для загрузки требуется HTTPS.')
        if self.curl:return self._native_download(url,path,expected,progress,cancel_event)
        for attempt in range(2):
            try:return self._download_once(url,path,expected,progress)
            except (OSError,urllib.error.URLError) as error:
                if attempt:raise SyncError(f'Загрузка прервана после повторной попытки: {error}') from error
                if progress:progress(5,'Связь прервана. Повторная загрузка с проверкой SHA-256…')

    def _native_download(self,url,path,expected,progress=None,cancel_event=None):
        expected=validate_hash(expected);started=time.monotonic()
        with tempfile.TemporaryDirectory(prefix='studio-headers-') as directory:
            headers=str(Path(directory)/'headers.txt')
            process=subprocess.Popen(self._curl_command(url,path,headers,max_time=180),stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                while process.poll() is None:
                    if cancel_event and cancel_event.is_set():raise SyncError('Загрузка отменена.')
                    size=os.path.getsize(path) if os.path.exists(path) else 0
                    total=0
                    if os.path.exists(headers):
                        lengths=re.findall(r'(?im)^content-length:\s*(\d+)',Path(headers).read_text(encoding='iso-8859-1',errors='replace'))
                        if lengths:total=int(lengths[-1])
                    if progress:
                        speed=size/1048576/max(time.monotonic()-started,.001)
                        progress(min(80,int(size/total*80)) if total else 10,f'Загрузка: {size/1048576:.1f} / {total/1048576:.1f} МБ · {speed:.2f} МБ/с')
                    time.sleep(.15)
                output,_=process.communicate(timeout=3)
                status=output.decode('ascii',errors='replace').strip()
                if process.returncode or status!='200':raise SyncError(f'Загрузка HTTPS не завершена: HTTP {status or "нет ответа"}, код {process.returncode}.')
                if sha256(path)!=expected:raise SyncError('SHA-256 не совпала. Загруженный файл удалён; рабочие данные сохранены.')
                if progress:progress(100,'SHA-256 проверена; файл загружен полностью.')
            except Exception:
                if process.poll() is None:process.terminate()
                process.communicate(timeout=5)
                if os.path.exists(path):os.unlink(path)
                raise

    def _download_once(self,url,path,expected,progress=None):
        expected=validate_hash(expected)
        started=time.monotonic();downloaded=0;digest=hashlib.sha256()
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'StudioSync/2','Accept':'application/octet-stream','Accept-Encoding':'identity'})
            with urllib.request.urlopen(request,timeout=15,context=ssl.create_default_context()) as response, open(path,'wb') as stream:
                total=int(response.headers.get('Content-Length') or 0)
                if total>512*1024*1024:raise SyncError('База превышает допустимый размер 512 МБ.')
                while chunk:=response.read1(65536):
                    downloaded+=len(chunk)
                    if downloaded>512*1024*1024:raise SyncError('База превышает допустимый размер 512 МБ.')
                    stream.write(chunk);digest.update(chunk)
                    if progress:
                        speed=downloaded/1048576/max(time.monotonic()-started,.001)
                        progress(min(80,int(downloaded/total*80)) if total else 30,f'Загрузка: {downloaded/1048576:.1f} / {total/1048576:.1f} МБ · {speed:.2f} МБ/с')
                if total and downloaded!=total:raise SyncError('Соединение оборвалось: база скачана не полностью.')
            if digest.hexdigest()!=expected:raise SyncError('SHA-256 базы не совпала. Локальная база сохранена.')
        except Exception:
            if os.path.exists(path):os.unlink(path)
            raise

class S3Store:
    def __init__(self,config):
        _prefix(config)
        access,secret=config.get_credentials()
        if not access or not secret:raise SyncError('Для Push укажите ключи доступа в настройках облака.')
        import boto3
        from botocore.config import Config
        self.config=config
        self.client=boto3.client('s3',endpoint_url=config.s3_endpoint,region_name=config.s3_region,aws_access_key_id=access,aws_secret_access_key=secret,config=Config(signature_version='s3v4',connect_timeout=7,read_timeout=20,retries={'mode':'standard','max_attempts':1}))

    def get_json(self,key):
        from botocore.exceptions import ClientError
        try:
            response=self.client.get_object(Bucket=self.config.s3_bucket,Key=key)
            with closing(response['Body']) as stream:raw=stream.read(2*1024*1024+1)
            if len(raw)>2*1024*1024:raise SyncError('Манифест слишком большой.')
            return json.loads(raw.decode('utf-8-sig')),response['ETag']
        except ClientError as error:
            if error.response['Error']['Code'] in ('NoSuchKey','404'):return None,None
            raise SyncError(f'Чтение S3 не выполнено: {error.response["Error"]["Code"]}') from error

    def _put(self,key,body,content_type,etag=None):
        from botocore.exceptions import ClientError
        arguments={'Bucket':self.config.s3_bucket,'Key':key,'Body':body,'ACL':'public-read','ContentType':content_type}
        arguments.update({'IfMatch':etag} if etag else {'IfNoneMatch':'*'})
        try:return self.client.put_object(**arguments)['ETag']
        except ClientError as error:
            code=error.response['Error']['Code']
            if code in ('PreconditionFailed','ConditionalRequestConflict','412','409'):
                raise SyncConflict('Облачные данные изменились во время операции. Повторите проверку.',{}) from error
            raise SyncError(f'Запись S3 не выполнена: {code}') from error

    def put_json(self,key,data,etag=None):
        return self._put(key,json.dumps(data,ensure_ascii=False,allow_nan=False,indent=2).encode(),'application/json; charset=utf-8',etag)

    def put_file(self,key,path,content_type):
        try:
            with open(path,'rb') as stream:return self._put(key,stream,content_type)
        except SyncConflict:
            # Content-addressed files are immutable. Accept an existing object only
            # after checking its complete SHA-256, not merely its name or ETag.
            response=self.client.get_object(Bucket=self.config.s3_bucket,Key=key)
            with closing(response['Body']) as stream:remote=hashlib.file_digest(stream,'sha256').hexdigest()
            if remote!=sha256(path):raise SyncError('Объект с этим именем уже существует и имеет другое содержимое.')

class CloudDatabaseSync:
    def __init__(self,config,db,version,name,store=None,http=None):
        self.config=config;self.db=db;self.version=version;self.name=name;self.store=store;self.http=http or PublicHttp()
        with _locks_guard:self.lock=_locks.setdefault(os.path.abspath(db.db_path),threading.Lock())

    def manifest(self):
        data,_=self.http.get_json(_prefix(self.config)+'latest.json')
        if data is None:raise SyncError('Манифест этой программы ещё не опубликован (HTTP 404).')
        return validate_manifest(data,self.config)

    def _remember(self,cloud_sha,local_sha=None):
        data=config_data(self.config)
        data['last_sync_sha256']=cloud_sha
        data['last_sync_local_sha256']=local_sha or cloud_sha
        data['last_sync_timestamp']=dt.datetime.now(dt.timezone.utc).isoformat()
        self.config.save()

    def pull(self,progress=None):
        if not self.lock.acquire(False):raise SyncError('Синхронизация уже выполняется.')
        temporary=None
        try:
            manifest=self.manifest();info=manifest.get('database')
            if not isinstance(info,dict):raise SyncError('База данных ещё не опубликована.')
            expected=validate_hash(info.get('sha256'));url=scoped_url(info.get('url'),self.config,'database')
            fd,temporary=tempfile.mkstemp(prefix='studio-pull-',suffix='.sqlite');os.close(fd)
            self.http.download(url,temporary,expected,progress)
            if progress:progress(90,'Проверка SQLite, резервное копирование и применение…')
            db_lock=getattr(self.db,'_lock',None)
            with db_lock if db_lock is not None else nullcontext():
                ok,message=self.db.safe_replace(temporary)
                if not ok:raise SyncError(message)
                local_sha=self.fingerprint()
            self._remember(expected,local_sha)
            if progress:progress(100,'База загружена. Резервная копия сохранена.')
            return info
        finally:
            if temporary and os.path.exists(temporary):os.unlink(temporary)
            self.lock.release()

    def snapshot(self):
        fd,path=tempfile.mkstemp(prefix='studio-snapshot-',suffix='.sqlite');os.close(fd)
        try:
            db_lock=getattr(self.db,'_lock',None)
            with db_lock if db_lock is not None else nullcontext():
                uri=Path(self.db.db_path).resolve().as_uri()+'?mode=ro'
                with closing(sqlite3.connect(uri,uri=True,timeout=15)) as source, closing(sqlite3.connect(path)) as destination:
                    source.backup(destination,pages=100)
                    if destination.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise SyncError('Локальная база повреждена; выгрузка отменена.')
            return path
        except Exception:
            os.unlink(path);raise

    def fingerprint(self):
        path=self.snapshot()
        try:return sha256(path)
        finally:os.unlink(path)

    def push(self,force=False,expected_cloud=None,progress=None):
        if not self.lock.acquire(False):raise SyncError('Синхронизация уже выполняется.')
        snapshot=None
        try:
            store=self.store or S3Store(self.config);key=self.config.app_slug+'/latest.json'
            manifest,etag=store.get_json(key)
            if manifest is not None:validate_manifest(manifest,self.config)
            old=(manifest or {}).get('database') or {};remote_sha=old.get('sha256')
            snapshot=self.snapshot();local_sha=sha256(snapshot)
            baseline=config_data(self.config).get('last_sync_sha256')
            details={'cloud_sha256':remote_sha or '', 'local_sha256':local_sha,'cloud_last_modified':old.get('last_modified','')}
            if remote_sha and remote_sha!=local_sha:
                if force:
                    if not expected_cloud or expected_cloud!=remote_sha:raise SyncConflict('Облачная ревизия изменилась. Подтвердите конфликт повторно.',details)
                elif remote_sha!=baseline:raise SyncConflict('CONFLICT: Облако содержит другую ревизию. Сначала загрузите её или подтвердите замену.',details)
            if remote_sha and not database_differs(self.config,remote_sha,local_sha):
                self._mirror(store,old)
                self._remember(remote_sha,local_sha)
                return old
            if progress:progress(35,'Создан согласованный снимок SQLite. Выгрузка…')
            object_key=f'{self.config.app_slug}/database/snapshots/{local_sha}.sqlite'
            store.put_file(object_key,snapshot,'application/vnd.sqlite3')
            info={'app_slug':self.config.app_slug,'version':int(old.get('version') or 0)+1,'last_modified':dt.datetime.now(dt.timezone.utc).isoformat(),'filename':Path(self.db.db_path).name,'url':_prefix(self.config)+'database/snapshots/'+local_sha+'.sqlite','sha256':local_sha,'size_bytes':os.path.getsize(snapshot)}
            revision_key=f'{self.config.app_slug}/database/revisions/{local_sha}.json'
            revision_old,revision_etag=store.get_json(revision_key)
            if revision_old is None:store.put_json(revision_key,info,revision_etag)
            if manifest is None:
                manifest={'app_slug':self.config.app_slug,'app_name':self.name,'app_version':self.version,'release_date':dt.date.today().isoformat(),'release_notes':'Синхронизация базы данных','package':{}}
            manifest['database']=info
            if progress:progress(85,'Публикация ревизии с проверкой конкурентных изменений…')
            store.put_json(key,manifest,etag)
            # No object store can atomically replace two independent objects.
            # Commit latest.json once; update the compatibility mirror afterwards.
            self._remember(local_sha,local_sha)
            try:
                self._mirror(store,info)
            except Exception as error:
                raise SyncError('База опубликована в latest.json, но копия database_meta.json не обновлена. Проверка и Pull работают; повторите Push для восстановления копии.') from error
            if progress:progress(100,'База опубликована и проверена.')
            return info
        finally:
            if snapshot and os.path.exists(snapshot):os.unlink(snapshot)
            self.lock.release()

    def _mirror(self,store,info):
        mirror_key=f'{self.config.app_slug}/database/database_meta.json'
        mirror,mirror_etag=store.get_json(mirror_key)
        if mirror!=info:store.put_json(mirror_key,info,mirror_etag)

def run_diagnostics(config,db):
    """Check the access actually used by Pull; public bucket listing is unnecessary."""
    steps={};logs=[]
    def record(key,ok,message,**extra):
        steps[key]={'status':'PASS' if ok else 'FAIL','message':message,**extra}
        logs.append(('✓ ' if ok else '✗ ')+message)
    started=time.monotonic()
    try:
        host=urllib.parse.urlsplit(config.s3_endpoint).hostname
        socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
        record('dns',True,'DNS: адрес сервера определён.',latency_ms=round((time.monotonic()-started)*1000))
    except Exception as error:record('dns',False,'DNS: '+str(error))
    try:
        data,_=PublicHttp().get_json(_prefix(config)+'latest.json')
        record('bucket',True,'Бакет: публичный объект программы доступен через HTTPS.',http_code=200 if data else 404)
        validate_manifest(data,config)
        record('manifest',True,'Манифест: структура и идентификатор программы проверены.',version=data['app_version'])
    except Exception as error:
        if 'bucket' not in steps:record('bucket',False,'Доступ к объекту S3: '+str(error))
        record('manifest',False,'Манифест: '+str(error))
    try:
        with closing(sqlite3.connect(Path(db.db_path).resolve().as_uri()+'?mode=ro',uri=True,timeout=10)) as connection:
            if connection.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise SyncError('повреждена SQLite')
        summary=db.get_summary();stats=summary.get('stats',{'houses':summary.get('houses_count',0)})
        record('database',True,'Локальная SQLite: целостность и чтение проверены.',stats=stats,sha256=CloudDatabaseSync(config,db,'0.0.0','').fingerprint())
    except Exception as error:record('database',False,'Локальная база: '+str(error))
    overall=all(step['status']=='PASS' for step in steps.values())
    return {'steps':steps,'logs':logs,'report_lines':logs,'overall_success':overall,'overall_ok':overall}
