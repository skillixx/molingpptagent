# template_23 图片生成提示词记录

- 工具：内置图片生成（规划指定为 GPT2 图片模板；实际模型名称：工具未暴露）
- 原则：每次调用只生成一个素材；素材达到用途与技术规格即停止；本轮全部一次通过。
- 共同限制：原创、无文字、无 Logo、无水印、无人物；禁用紫色、洋红色和完整发光圆环；正文安全区保持低干扰。

## 背景素材

1. `template_23_asset_bg_cover_v1.jpg`：深空藏蓝封面，底部三分之一青色地平线，稀疏星尘，中央偏左留白。
2. `template_23_asset_bg_content_v1.jpg`：极克制深蓝正文背景，细微技术网格与星尘仅分布在边缘，至少 75% 低干扰。
3. `template_23_asset_bg_section_v1.jpg`：章节页深蓝背景，青色方向光线从右侧进入，左侧和中部留白。
4. `template_23_asset_bg_end_v1.jpg`：收尾页青色地平线与汇聚星尘，上中部及左侧保留标题空间。

## 透明装饰

5. `template_23_asset_particle_field_v1.png`：右下方向的稀疏青白粒子场，真实透明背景。
6. `template_23_asset_horizon_glow_v1.png`：超宽青色地平线光带，细线、柔光和少量粒子，真实透明背景。
7. `template_23_asset_title_flare_v1.png`：细长标题光线与左侧小型非对称耀斑，真实透明背景。
8. `template_23_asset_image_halo_v1.png`：用于业务图片外沿的四角断开式青色光晕，中心完全透明。
9. `template_23_asset_grid_arc_v1.png`：只占右下区域的开放式技术网格弧线，禁止闭合圆环，真实透明背景。

## 后处理

仅执行尺寸、色彩模式、透明通道和压缩体积的机械归一化；未使用程序化方式绘制或重构视觉内容。成品摘要见 `asset-summary.json`。
