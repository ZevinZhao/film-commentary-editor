# 《肖申克的救赎》屋顶啤酒案例

这是 2026-10-12 至 2026-10-13 的工程复盘和复用入口，不是所有电影的强制模板。未附电影素材与大模型权重。跨设备继续时，先核实下列工程路径是否仍存在。

## 选择如何收敛

- 用户提供约 37 分钟参考视频，希望接近“心中之城”的解说节奏；参考文件为 `/Users/wupeng/Desktop/video.mp4`。本次早期转写有错字与重复，不能把 ASR 文本当准确参考原稿。
- 初始目标是 8–10 分钟讲清整片主线，本地没有电影，用户允许寻找素材。
- 用户指出：全是解说、没有人物原声留白；文案只是叙述、没有感受；画面大量重复；配音 AI 感明显。
- 后续明确要求英语原声，排除带日文烧录字幕的版本。英语音轨与日文画面字幕可以同时存在，分别核查。
- A/B/C 先后不合适；反馈涉及口音太重和嗓音太低沉。用户最终明确“E 可以用于成片”。
- 用户主动把范围改为“小片段、深度讲”，交付转为同场景约 2 分 45 秒；不是素材不足时自行偷换整片目标。
- 用户认可深度片段的方向，进一步要求修复对白气口后的电影配乐/环境声突然消失。
- 声音修订版已完成导出和技术核验。本轮尚无用户对修订版听感的再次明确评价；不要把交付或量化通过写成再次确认。

## 被保留的创作方法

围绕安迪如何从被抓住衣领的囚犯，暂时成为对方需要的人，进而给工友争取片刻正常生活来讲。原片承担威胁、问答、提条件、拒绝啤酒和结尾判断；解说观察衣领、客气话、“工友”称呼、阴影里的笑等具体细节。

示例解释：安迪讲完办法，还说对方自己迟早会查清楚。旁白将其理解为给狱警留面子，并用“他似乎很清楚……”保留推断边界。最后让瑞德自己的判断收束，不再额外补一段口号。

实际成片 164.52 秒；5 段配音总长约 67.878 秒，308 个汉字。这个比例是素材和叙事选择的结果，不是“解说必须只占四成”的公式。

## E 声线已随技能保存

- [voice-e.wav](../assets/voices/voice-e.wav)：13.84 秒，24 kHz，单声道，PCM16。
- [voice-e.json](../assets/voices/voice-e.json)：试音文本、实际描述、模型、seed、摘要与后续复用方式。
- WAV SHA256：`215b396e6be19f07788cb56bdb190791440e161ef10e1acba525c3415561d4b9`。
- 来源是通用文字描述设计出的合成声，不是从“心中之城”参考人物提取的真人声纹。

本次音色目标：约三十岁的日常男性说话声，标准普通话、清晰干净、适中偏明亮中音、温和克制；不要低沉压嗓、气泡音、沙哑或主持腔。下一项目用户要求沿用时优先用保留的音频与文本，不仅凭描述和 seed 重新抽一个近似声。

生成设计样本使用 `mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-6bit`，seed 71，language Chinese，temperature .75、top_k 50、top_p .95、repetition_penalty 1.05、max_tokens 400、stream false。

正式配音改用 `mlx-community/Qwen3-TTS-12Hz-1.7B-Base-6bit`，输入这个自生成样本的 `ref_audio` 和准确 `ref_text`。本次 lang_code Chinese、temperature .75、top_k 50、top_p .95、repetition_penalty 1.5、stream false、split_pattern null，按完整语意段生成，不做后期变速。max_tokens 使用 `max(350, ceil(汉字数*7+160))` 作为防截尾预算，不作为通用质量保证。

Base 生产调用没有应用逐段 instruct；创作语气写在 `editorial_emotion_intent`，而 `base_instruction_control=false`。不要声称模型已按每段提示词精确控制情绪。

最终五段 seeds 为 1031、1038、1045、1552、1059。01_3 尾字修复用 1552 替换 1052。声纹 embedding 的内部相似度不能证明主观听感一致。

命名陷阱：旧文件 `narration/production_E.json` 的 E 是早期段落标记，其 Dylan/CustomVoice 配置不是用户最终选定的声线 E。应以 `rooftop_deep/voice/manifest.json` 的实际 reference_path 和音频摘要为准。

这里记录的 MLX 路线是在 Apple Silicon 环境完成的案例，不保证其他设备兼容。原环境记录 mlx 0.32.3、mlx-audio 0.5.8、numpy 2.4.6；不要把它们变成每次调用必装或必须升级的版本。

## 原声衔接修复

四个关键解说入口（成片秒数）：27.20、42.76、106.24、125.36。前段人物对白按自身响度处理，解说底声另归一化时，真实增益会产生比账面设定更大的台阶。

修复采用：上一段末尾同源增益继承 → 原片完整尾音 → 下一句英语开始前平滑转为同源分离底声 → 按中文起声渐缓压低 → 必要时提前接入下一原声场面的动静。

分离范围来自同一个屋顶英语原声净片：99–166 秒与 190–270 秒，输出均 44.1 kHz 立体声、准确对应源偏移。使用官方模型仓库中的 `UVR-MDX-NET-Inst_HQ_5.onnx`，模型匹配参数 FFT 5120、dim_f 2560、compensation 1.01。权重和第三方实现未随技能打包；需要复用时核对官方参数与当前代码，不猜模型架构。

- 模型来源：<https://github.com/TRvlvr/model_repo/releases/tag/all_public_uvr_models>
- 本次实现来源：<https://github.com/DEMOUSL/comfyui_uvr_mdx>

分离前后对照 ASR：分离底声在选定英语窗口未识别出原台词，原声对照能够识别。双轨重构误差约 `1.49e-8`。这些是实际验证结果，不是“完全没人声残留”的保证。

42.76 秒处前后总体能量仍下降约 8.99 dB，但原片同处自然下降约 8.77 dB；扣除原片自然变化，编辑额外变化约 −0.21 dB。若直接要求每个接点绝对能量差小于 5 dB，会把人物说完话误判成故障。

最终四处的同源相对增益变化约 −0.005、−0.214、−0.083、+0.007 dB。最终 AAC 量测约 −18.27 LUFS、−1.50 dBTP、LRA 6.50。画面压缩包内容摘要与前版一致，字幕字节一致，音频时长 164.52 秒。

## 本地工程索引

工程根目录：`/Users/wupeng/Documents/Codex/2026-10-12/mo`。下列相对路径均从该目录解析，不从技能目录解析。

| 用途 | 工程内相对路径 |
|---|---|
| 已交付声音修订版 | `outputs/肖申克的救赎_屋顶上的啤酒_声音衔接修订版.mp4` |
| 用户认可主体剪辑的前版 | `outputs/肖申克的救赎_屋顶上的啤酒_深度片段.mp4` |
| 原稿与片段来源说明 | `outputs/肖申克的救赎_屋顶上的啤酒_文案与素材.txt` |
| 英语原声净片 | `work/footage/rooftop_clean_hd.mp4` |
| 最终镜头时间线 | `work/revision-v2/rooftop_deep/edit_plan.json` |
| 最终旁白及录音记录 | `work/revision-v2/rooftop_deep/narration.json`、`work/revision-v2/rooftop_deep/voice/manifest.json` |
| 最终字幕时码 | `work/revision-v2/rooftop_deep/alignment/captions_final.json` |
| 可用原声尾巴与下句英语起点 | `work/revision-v2/rooftop_deep/original_audio_tail_audit.json` |
| 声音修订实现及检查 | `work/revision-v2/rooftop_deep/sound_polish/` 下的 `remix.py`、`verify_mix.py`、`mix_report.json`、`mix_qa.json` |
| 本地分离实现/模型来源/对照记录 | `work/revision-v2/audio_stems/` |
| 正式生成配音的实现 | `work/revision-v2/generate_full_narration.py` |

净片记录的来源页面：<https://www.youtube.com/watch?v=ZLTss8yXZRk>。这是历史来源记录，未来再次下载前重新确认可用性与素材条件。

这些脚本带有本工程具体路径与时间线，不能直接当作下一部电影的通用渲染器运行。下一项目迁移思路和字段，重新绑定素材、时码、画幅与声线；当前只需要检查原声接点时使用技能附带的便携检查脚本。
