"""只在副本中移除示例文字，复用原稿音乐装饰；不绘制新图或修改原稿。"""
from pathlib import Path
import hashlib
import copy
import io
import json
import subprocess
import zipfile

from lxml import etree as ET
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'doc/assets/template_29_qa'
SOURCE = Path('C:/Users/sk20/Desktop/创意风格 (7).pptx')
TARGET = ROOT / 'backend/main_api/template'
NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}


def main():
    QA.mkdir(parents=True, exist_ok=True)
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    derivative = QA / 'decoration-only-source.pptx'
    with zipfile.ZipFile(SOURCE) as source, zipfile.ZipFile(derivative, 'w', zipfile.ZIP_DEFLATED) as output:
        for entry in source.infolist():
            data = source.read(entry.filename)
            if entry.filename.startswith(('ppt/slides/slide', 'ppt/slideLayouts/slideLayout', 'ppt/slideMasters/slideMaster')) and entry.filename.endswith('.xml'):
                root = ET.fromstring(data)
                # 保留琴键等无文字的原生装饰，仅删除有内容的文字形状和播放时间线。
                for shape in root.xpath('//p:sp[.//a:t[string-length(text()) > 0]] | //p:timing | //p:pic[.//a:audioFile]', namespaces=NS):
                    shape.getparent().remove(shape)
                if entry.filename == 'ppt/slides/slide4.xml':
                    tree = root.find('p:cSld/p:spTree', NS)
                    for element in list(tree):
                        if ET.QName(element).localname in {'sp', 'pic', 'grpSp', 'cxnSp', 'graphicFrame'}:
                            tree.remove(element)
                if entry.filename == 'ppt/slideLayouts/slideLayout3.xml':
                    # 将原稿右侧音乐图裁到约 12% 边栏，保持图像比例并扩大正文阅读区。
                    for pic in root.findall('.//p:pic', NS):
                        pic.find('p:spPr/a:xfrm/a:off', NS).attrib.update({'x':'10728960', 'y':'0'})
                        pic.find('p:spPr/a:xfrm/a:ext', NS).attrib.update({'cx':'1463040', 'cy':'6858000'})
                        pic.find('p:blipFill/a:srcRect', NS).attrib.update({'l':'38400', 'r':'29645'})
                if entry.filename == 'ppt/slides/slide25.xml':
                    for blip in root.findall('.//a:blip', NS):
                        ET.SubElement(blip, '{'+NS['a']+'}alphaModFix', amt='72000')
                data = ET.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
            # ZipFile 写入会改动 ZipInfo 的偏移量，复制元数据避免影响后续读取原稿。
            output.writestr(copy.copy(entry), data)
        violin_path = QA / 'source-images/image6.png'
        violin_path.parent.mkdir(exist_ok=True)
        violin_path.write_bytes(source.read('ppt/media/image6.png'))
        # 提取原稿业务照片供固定样例使用，生成脚本不依赖其他模板的 QA 目录。
        fixtures = QA / 'fixtures'
        fixtures.mkdir(exist_ok=True)
        for index, name in enumerate(['image13.jpeg', 'image14.jpeg', 'image15.jpeg', 'image16.jpg'], 1):
            picture = Image.open(io.BytesIO(source.read('ppt/media/' + name))).convert('RGB')
            picture.thumbnail((1200, 1000))
            picture.save(fixtures / f'business-{index}.jpg', quality=90)
    subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT / 'utils/render_music_source_assets.ps1')], check=True)
    violin = Image.open(violin_path).convert('RGBA')
    if violin.getchannel('A').getextrema()[0] != 0:
        raise ValueError('原稿小提琴缺少透明通道')
    ImageOps.pad(violin, (1200, 1600), method=Image.Resampling.LANCZOS, color=(0, 0, 0, 0)).save(TARGET / 'template_29_asset_violin_v1.png')
    records = []
    for asset_id, kind in [('A1','cover'), ('A2','content'), ('A3','section'), ('A4','end'), ('A5','violin')]:
        filename = f'template_29_asset_{"" if kind == "violin" else "bg_"}{kind}_v1.{"png" if kind == "violin" else "jpg"}'
        path = TARGET / filename
        with Image.open(path) as image:
            records.append({'id':asset_id, 'file':filename, 'size':list(image.size), 'mode':image.mode,
                            'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                            'source':'原稿装饰提取与 PowerPoint COM 渲染' if kind != 'violin' else 'ppt/media/image6.png；保留透明通道等比缩放'})
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != source_hash:
        raise RuntimeError('原稿校验值发生变化')
    (QA / 'asset-inspection.json').write_text(json.dumps({'source':str(SOURCE), 'sourceSha256':source_hash,
        'generationUsed':False, 'assets':records},ensure_ascii=False,indent=2),encoding='utf-8')


if __name__ == '__main__':
    main()
