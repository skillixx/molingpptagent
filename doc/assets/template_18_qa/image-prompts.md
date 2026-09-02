# 飞檐雅韵模板图片生成提示词

## 共同约束

- 参考风格：`精品系列(2).pptx`，保持灰瓦、飞檐、马头墙、梅枝飞鸟、藕粉和米白的古建雅集气质。
- 目标：生产原创替代素材，不复制参考文件的媒体字节和具体纹样。
- 禁止：文字、数字、Logo、水印、二维码、真人、产品界面、真实机构印章、科技大屏、霓虹、玻璃拟态和密集卡片。
- 视觉：克制、疏朗、低饱和、宣纸米白、粉黛灰瓦、细腻但不过度写实。
- 执行：使用内置 imagegen；工具未暴露实际模型名称时如实记录。

## template_18_asset_bg_cover_v1.jpg

Use case: stylized-concept
Asset type: 16:9 PowerPoint cover background
Input image: source slide 1 is a style and composition reference only
Primary request: an original Chinese architectural cover background with dark gray roof tiles occupying the lower 42%, sparse plum branches entering from both upper corners, two tiny birds, and warm ivory sky with large clean negative space
Style/medium: refined Chinese editorial illustration blending realistic roof texture with restrained ink-and-color painting
Composition/framing: 16:9 landscape; strong horizontal roof weight; empty central and upper area; no title circles and no text
Color palette: warm ivory, charcoal tile gray, dusty rose, tiny cinnabar accents
Constraints: preserve the reference slide's visual weight and page rhythm without copying its exact roof or branches; no text; no seal; no watermark

## template_18_asset_bg_section_v1.jpg

Use case: stylized-concept
Asset type: 16:9 PowerPoint section background
Input image: source slide 3 is a style and composition reference only
Primary request: original warm ivory section background with layered Hui-style horse-head walls concentrated at the lower right and a sparse plum branch with a small bird at the upper right
Style/medium: restrained Chinese architectural editorial illustration
Composition/framing: keep the left 42% and center clear for a native dusty-rose vertical rail and editable chapter text
Color palette: warm ivory, charcoal gray, soft dusty rose, muted brown
Constraints: no rail, medallion, text or watermark baked into the image; preserve source composition and negative space without copying exact media

## template_18_asset_bg_end_v1.jpg

Use case: stylized-concept
Asset type: 16:9 PowerPoint ending background
Input image: source slide 26 is a style and composition reference only
Primary request: original closing background echoing the cover, with a lower dark-gray roof band, quiet plum branches across the upper corners, tiny birds, and a calm warm-ivory center
Style/medium: refined Chinese editorial illustration with realistic roof texture and restrained ink color
Composition/framing: 16:9; central and lower-middle safe area for editable closing text and optional action items
Constraints: no circles, no text, no seal, no watermark; visually echo source cover and ending rhythm without copying exact media

## template_18_asset_rooftile_band_v1.png

Use case: background-extraction
Asset type: transparent PowerPoint decoration
Input image: source slide 1 roof area is a style reference only
Primary request: an original wide horizontal band of traditional dark gray Chinese roof tiles, frontal view, layered rows, slightly weathered, clean silhouette
Style/medium: realistic editorial cutout with restrained color and subtle painterly integration
Composition/framing: very wide 1800:620 ratio, roof centered across the full width, transparent above and below
Constraints: genuinely transparent background; no wall, sky, branches, text, logos, white halo or watermark; do not copy the exact source roof

## template_18_asset_eaves_corner_v1.png

Use case: background-extraction
Asset type: transparent PowerPoint corner decoration
Input image: source slides 3 and 17 are style and composition references only
Primary request: an original layered Hui-style horse-head wall and traditional eaves corner, viewed from slightly below, dark gray tiles and warm white plaster
Style/medium: refined Chinese architectural illustration with realistic texture
Composition/framing: architecture concentrated in the lower-right corner with empty transparent upper-left area
Constraints: genuinely transparent background; no sky, branches, people, text, white halo or watermark; preserve source visual role without copying geometry

## template_18_asset_plum_branch_v1.png

Use case: background-extraction
Asset type: transparent PowerPoint decoration
Input image: source slides 1 and 16 are style references only
Primary request: an original sparse plum branch with small dusty-rose and ivory blossoms, a few buds, elegant irregular curvature and restrained ink outlines
Style/medium: delicate Chinese ink-and-color botanical illustration
Composition/framing: wide 1600:650 ratio; branch enters from one corner and leaves the center open
Constraints: genuinely transparent background; no birds, text, seal, white halo or watermark; do not copy the exact source branch

## template_18_asset_crane_pair_v1.png

Use case: background-extraction
Asset type: transparent PowerPoint decoration
Input image: source slide 5 is a style reference only
Primary request: an original pair of elegant flying red-crowned cranes, one slightly higher, wings extended, pale ivory feathers with charcoal tips and subtle muted-gold line accents
Style/medium: refined Chinese gongbi-inspired illustration, light and graceful
Composition/framing: wide diagonal movement from lower left toward upper right; generous transparent padding
Constraints: genuinely transparent background; no landscape, text, seal, logo, white halo or watermark; preserve source visual role without copying exact birds

## template_18_asset_medallion_v1.png

Use case: background-extraction
Asset type: transparent PowerPoint decoration
Input image: source slides 3 and 9 are style references only
Primary request: an original circular Chinese ornamental medallion made from fine interlocking cloud and geometric linework, visually light and symmetrical
Style/medium: delicate vector-like line ornament with subtle handcrafted irregularity
Composition/framing: centered circular motif with generous transparent padding
Color palette: muted gold and dusty rose linework
Constraints: genuinely transparent background; no Chinese characters, no institutional seal, no logo, no solid disc, no white halo or watermark; do not copy the exact source pattern
