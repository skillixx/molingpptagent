"""核验当前城市模板的真实产物和测试证据，冻结 G8 候选；不闭合 Goal。"""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "doc/assets/template_24_qa"
TEMPLATES = ROOT / "backend/main_api/template"
BUILDER = ROOT / "utils/build_neon_city_project_template.mjs"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(name, value):
    (QA / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    # G8 冻结器会写入待确认状态；G9 已闭合后禁止覆盖历史确认和进度。
    if (QA / "g9-closure.json").exists():
        raise RuntimeError("G9 已闭合，请使用独立交付核验记录，不要覆盖 G8/G9 历史证据。")
    template_path = TEMPLATES / "template_24.json"
    template = read(template_path)
    source = Path.home() / "Desktop/项目策划(1).pptx"
    assert digest(source).upper() == template["metadata"]["sourceReferenceSha256"]
    expected = ["cover-city", "cover-city-minimal", *[f"contents-{n}" for n in (2,3,4,5,6,10)],
                "transition-city-left", "transition-city-right", "content-focus-1", "content-text-2", "content-text-3",
                "content-text-4", "content-image-1", "content-metrics-4", "end-city", "end-action"]
    assert [s["id"] for s in template["slides"]] == expected
    assert Counter(s["type"] for s in template["slides"]) == {"cover":2,"contents":6,"transition":2,"content":6,"end":2}
    assert template["width"] == 1000 and template["height"] == 562.5
    assert template["metadata"]["buildStage"] == "production"
    # 当前构建器必须能够精确重现正式文件和开发阶段样例。
    with tempfile.TemporaryDirectory(prefix="template24-determinism-") as work:
        deterministic = {}
        for stage, count in [("probe",3),("mvp",12),("production",18)]:
            first, second = Path(work)/f"{stage}-1.json", Path(work)/f"{stage}-2.json"
            for dest in (first,second):
                subprocess.run(["node",str(BUILDER),"--stage",stage,str(dest)],cwd=ROOT,check=True,capture_output=True)
            assert first.read_bytes() == second.read_bytes()
            sample=read(first); assert len(sample["slides"])==count
            assert all(s == next(p for p in template["slides"] if p["id"]==s["id"]) for s in sample["slides"])
            if stage=="production": assert first.read_bytes()==template_path.read_bytes()
            deterministic[stage]={"count":count,"sha256":digest(first),"matchesProductionProjection":True}
    source_map=read(QA/"reference-page-map.json")
    assert [p["referencePage"] for p in source_map["pages"]] == list(range(1,26))
    assets=read(QA/"asset-generation.json")
    assert len(assets["assets"])==9
    referenced={e["src"].split('/')[-1] for s in template["slides"] for e in s["elements"] if e["type"]=="image"}
    assert referenced==set(template["metadata"]["assetFiles"])
    for asset in assets["assets"]:
        final=TEMPLATES/asset["file"]
        assert digest(final)==asset["finalSha256"]
        assert digest(asset["sourcePath"])==asset["sourceSha256"]
        assert asset["prompt"] and asset["attempts"]<=3 and asset["referencedBy"]
        with Image.open(final) as image:
            assert image.size==(asset["width"],asset["height"])
            assert image.mode==("RGBA" if asset["alpha"] else "RGB")
            if asset["alpha"]: assert image.getchannel('A').getextrema()[0]==0
    browser=read(QA/"production-verified/summary.json")
    assert browser["status"]=="PASS" and browser["slideCount"]==18
    assert browser["sourceSha256"]==digest(template_path)
    assert browser["pptxSha256"]==digest(QA/"production-verified/roundtrip.pptx")
    assert browser["jsonFullStateEqual"] and browser["pptxEditorReimport"] and not browser["missingTexts"]
    assert browser["exportFailure"]=={"errorCode":"PPTX_EXPORT_FAILED","exportingReset":True}
    assert browser["exportRetrySucceeded"] and len(browser["replacementResults"])==3 and browser["imageGeometry"]
    assert not browser["errors"] and not browser["writes"]
    worker=read(QA/"real-handler-summary.json")
    worker_browser=read(QA/"worker-output-verified/summary.json")
    assert worker["status"]=="PASS" and worker["workerStatus"]=="succeeded"
    assert worker_browser["status"]=="PASS" and worker_browser["sourceSha256"]==digest(QA/"real-handler-document.json")
    assert worker_browser["slideCount"]==worker["slideCount"]==7
    assert all(worker["slideTypes"].values())
    runtime=read(QA/"runtime/runtime-summary.json")
    assert runtime["status"]=="PASS" and runtime["templateSelected"] and runtime["registrationCount"]==1
    # 除浏览器身份夹具外，列表和资源必须由当前本地 API 返回真实字节。
    with urllib.request.urlopen('http://127.0.0.1:6800/templates') as response:
        entries=json.load(response)["data"]
    assert len([e for e in entries if e["id"]=="template_24"])==1
    for filename in ["template_24.json","template_24.jpg",*template["metadata"]["assetFiles"]]:
        with urllib.request.urlopen(f'http://127.0.0.1:5778/api/data/{filename}') as response:
            assert response.status==200 and response.read()==(TEMPLATES/filename).read_bytes()
    suites=ET.parse(QA/"tests.xml").getroot().findall('testsuite')
    assert suites and all(int(s.get('failures','0'))==0 and int(s.get('errors','0'))==0 for s in suites)
    tests=sum(int(s.get('tests','0')) for s in suites)
    assert tests>=104
    for index in range(1,19): assert (QA/f'production-verified/slide-{index}.png').is_file()
    paths=[template_path,TEMPLATES/'template_24.jpg',BUILDER,ROOT/'backend/main_api/main.py',
           ROOT/'backend/main_api/tests/test_template_24.py',ROOT/'doc/template_specs/template_24.yaml',
           ROOT/'utils/verify_template_24_browser.cjs',ROOT/'utils/verify_template_24_runtime.cjs',
           ROOT/'utils/run_template_24_handler_qa.py',Path(__file__),*[TEMPLATES/f for f in template["metadata"]["assetFiles"]]]
    manifest={p.relative_to(ROOT).as_posix():digest(p) for p in paths}
    candidate=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()[:12]
    timestamp=datetime.now(timezone.utc).isoformat()
    save('frozen-candidate-manifest.json',{"candidateId":f'template24-g8-{candidate}',"createdAt":timestamp,"files":manifest})
    save('determinism-summary.json',deterministic)
    stages={
        "G0":{"status":"PASS","evidence":["g0-baseline.json"]},
        "G1":{"status":"PASS","evidence":["reference-page-map.json","asset-generation.json"]},
        "G2":{"status":"PASS","evidence":["probe-verified/summary.json","production-verified/summary.json"],"note":"最终候选覆盖三页探针，旧 g2-browser 记录仅保留作历史。"},
        "G3":{"status":"PASS","evidence":["determinism-summary.json","mvp.json"]},
        "G4":{"status":"PASS","evidence":["production-verified/contact-sheet.png"],"sampleIds":["cover-city","contents-4","transition-city-left","content-text-4","end-city"]},
        "G5":{"status":"PASS","evidence":["tests.xml"],"tests":tests},
        "G6":{"status":"PASS","evidence":["runtime/runtime-summary.json","frozen-candidate-manifest.json"]},
        "G7":{"status":"PASS","evidence":["real-handler-summary.json","worker-output-verified/summary.json"],"mode":"固定上游、真实 Worker/Handler/Renderer，隔离 SQLite；不是在线文本模型验收"},
        "G8":{"status":"PASS","evidence":["production-verified/summary.json","frozen-candidate-manifest.json"]},
        "G9":{"status":"PENDING_USER_CONFIRMATION"},
    }
    result={"status":"G8_PASS / G9_PENDING","candidateId":f'template24-g8-{candidate}',"createdAt":timestamp,"stages":stages,
            "productionSlides":18,"mvpSlides":12,"assets":9,"testsPassed":tests,
            "limitations":["认证使用浏览器夹具；未验证生产 SSO、计费和远程部署。", "文本上游为固定数据；没有调用真实文本模型。", "PPTX 重导入保留全文、图片和槽位，字体主题/字重与细线呈现可能变化，不承诺逐像素复刻。", "前端源码未修改，四视口整改不适用；已有桌面与手机探针截图只作补充观察。"],
            "goalClosed":False,"gitDelivery":False,"deployment":False}
    save('g8-summary.json',result);save('progress.json',result)
    print(json.dumps({"status":result["status"],"candidateId":result["candidateId"],"testsPassed":tests},ensure_ascii=False))


if __name__=='__main__': main()
