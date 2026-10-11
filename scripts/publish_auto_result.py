#!/usr/bin/env python3
"""Trusted publisher. No upstream executable code is ever run here.

It stages the four verified files and status as a local all-or-nothing
transaction; caller commits all files in ONE atomic Git commit. Git failure
means the repository is unchanged. Publisher requires independent re-fetch
of the immutable upstream source SHA and rejects cross-run evidence replay.
"""
import argparse, json, os, shutil, sys, tempfile, subprocess
from pathlib import Path
from publish_watch_status import sanitize
from verified_auto_promotion import build_patch, PromotionHold

ROOT=Path(__file__).resolve().parents[1]
ALLOWED=('app.js','index.html','sw.js','kit-assets/MASTER_DATA.json','kit-assets/KIT_VERSION.json','kit-assets/numeric_observer.py')

def write_json(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')

def transact(site,updates, *, inject_failure_at=None):
    """In-process disk transaction with rollback; publishing is a separate git push."""
    site=Path(site)
    original={}
    for rel in updates:
        if rel not in ALLOWED+('update-status.json',):raise PromotionHold('UNEXPECTED_WRITE_PATH:'+rel)
        path=site/rel
        original[rel]=path.read_bytes() if path.is_file() else None
    changed=[]
    try:
        for i,(rel,data) in enumerate(updates.items()):
            path=site/rel
            if not path.parent.is_dir():raise PromotionHold('MISSING_DIRECTORY:'+str(path.parent))
            # same directory => os.replace is atomic on ordinary filesystems
            with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as tmp:
                tmp.write(data);tmp.flush();os.fsync(tmp.fileno());target=tmp.name
            os.replace(target,path)
            changed.append(rel)
            if inject_failure_at==i:raise RuntimeError('INJECTED_WRITE_FAILURE')
    except BaseException:
        for rel in reversed(changed):
            p=site/rel
            if original[rel] is None:p.unlink(missing_ok=True)
            else:
                with tempfile.NamedTemporaryFile(dir=p.parent,delete=False) as f:
                    f.write(original[rel]);f.flush();os.fsync(f.fileno());name=f.name
                os.replace(name,p)
        raise

def require_staged_species_audit_compatible(site, patch):
    """Test the consumer on the exact staged master; fail closed before publication.

    Never remove pinned carry fingerprints just to make promotion pass. New
    master revisions require a separately reviewed species/numeric audit.
    """
    if not {'kit-assets/MASTER_DATA.json','kit-assets/KIT_VERSION.json','kit-assets/numeric_observer.py'} <= set(patch):
        raise PromotionHold('PROMOTION_MISSING_CONSUMER_ASSETS')
    with tempfile.TemporaryDirectory(prefix='pokesleep-consumer-check-') as tmp:
        kit=Path(tmp)/'kit-assets'
        shutil.copytree(Path(site)/'kit-assets',kit)
        for name in ('MASTER_DATA.json','KIT_VERSION.json','numeric_observer.py'):
            (kit/name).write_bytes(patch['kit-assets/'+name])
        code=("import pathlib,sys; sys.path.insert(0,sys.argv[1]); "
              "from SPECIES_AUDIT import verify_bundle; "
              "verify_bundle(pathlib.Path(sys.argv[1]))")
        try:
            res=subprocess.run([sys.executable,'-c',code,str(kit)],
                               capture_output=True,text=True,timeout=30,check=False)
        except (OSError,subprocess.TimeoutExpired) as e:
            raise PromotionHold('POST_PROMOTION_CONSUMER_CHECK_FAILED: '+str(e)) from e
        if res.returncode != 0:
            err=(res.stderr or res.stdout).strip().splitlines()
            reason=err[-1][:240] if err else f'exit {res.returncode}'
            raise PromotionHold('POST_PROMOTION_CONSUMER_AUDIT_HOLD: '+reason)


def execute(site,bundle,upstream,*,audit_status,audit_result,run_id,base_sha):
    site=Path(site);bundle=Path(bundle)
    raw=None
    try:raw=json.loads(Path(audit_status).read_text(encoding='utf-8'))
    except (OSError,ValueError):pass
    sanitized=sanitize(raw,audit_result,run_id)
    patch={}
    promoted=False
    if audit_result=='success' and bundle.is_dir() and (bundle/'PROMOTION_PROOF.json').is_file():
        try:
            with tempfile.TemporaryDirectory(prefix='autopromotion-patch-') as tmp:
                receipt=build_patch(bundle,site,tmp,run_id=run_id,base_sha=base_sha,
                                    upstream_code_dir=upstream)
                for rel in ALLOWED:patch[rel]=(Path(tmp)/rel).read_bytes()
                # Do not publish a syntactically valid master whose SpeciesAudit
                # cannot actually open it after upgrading the kit.
                require_staged_species_audit_compatible(site,patch)
            promoted=True
        except (OSError,ValueError,KeyError,TypeError,PromotionHold) as ex:
            promoted=False;patch={}
            sanitized.update(state='attention',reasonCode='AUTOPROMOTION_REJECTED',
              message='新データの自動更新は保留されました',
              details='互換性または整合性の確認に失敗しました。従来のマスターを保持しています。GitHub Actionsの実行ログを確認してください。')
            print('AUTO_PROMOTION_HOLD:',repr(ex),file=sys.stderr)
    if promoted:
        proof=json.loads((bundle/'PROMOTION_PROOF.json').read_text(encoding='utf-8'))
        sanitized.update(state='healthy',reasonCode='AUTO_PROMOTION_COMMITTED_PENDING_PUSH',
          message='上流データの自動更新を検証済みです',
          details='固定した上流ソースをビルドしてCSVのインポート・エクスポートを検証しました。本番CSV出力はHOLDのままです。',
          activeSourceCommit=proof['sourceCommit'],upstreamCommit=proof['sourceCommit'])
    # Rejected and no-change paths update ONLY the status.
    status_data=(json.dumps(sanitized,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')
    patch['update-status.json']=status_data
    transact(site,patch)
    return {'promoted':promoted,'changedPaths':list(patch),'reasonCode':sanitized['reasonCode'],
            'productionCsvAllowed':False}

def main():
    p=argparse.ArgumentParser()
    for name in ('site','bundle','upstream','audit-status','audit-result','run-id','base-sha'):
        p.add_argument('--'+name,required=True)
    a=p.parse_args()
    try:
        result=execute(a.site,a.bundle,a.upstream,audit_status=a.audit_status,
                       audit_result=a.audit_result,run_id=a.run_id,base_sha=a.base_sha)
        print(json.dumps(result,ensure_ascii=False));return 0
    except Exception as e:
        print('NO_COMMIT: ',repr(e),file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
