# 可复用的衔接检查

工具只诊断“同一条原片声音在解说入口是否被额外压低/切断”，不会替代听辨和画面检查。

## 输入与运行

依赖：Python 3 标准库、已安装的 ffmpeg/ffprobe。缺少时使用现有环境或报告依赖；本工具不自动下载环境、不修改输入媒体。配置中的相对路径相对于配置文件所在目录。

创建任务内 JSON，例如：

```json
{
  "export": "outputs/revised.mp4",
  "export_audio_stream": 0,
  "picture_reference": "outputs/accepted.mp4",
  "subtitles": "outputs/revised.srt",
  "subtitle_reference": "outputs/accepted.srt",
  "joins": [
    {
      "label": "对白后接第一段解说",
      "at": 27.2,
      "source": "source/scene.mp4",
      "source_audio_stream": 0,
      "source_at": 112.71,
      "probe_has_no_added_speech": true
    }
  ]
}
```

上面时间码仅示范字段，实际必须从当前时间线推导；`at` 是成片边界，`source_at` 是该边界承接的原片声音时间，不一定等于当前画面源时间。音画分剪时分别记录。`picture_reference` 和字幕比较均可省略。

`export_audio_stream` 与 `source_audio_stream` 都是只数音轨、从 0 起的序号（映射为 `0:a:N`），不是 ffprobe 全部流的绝对 index。默认第一音轨；多音轨片源必须填入已核实的目标音轨，避免量到配音版或另一种混音。

```bash
python3 /path/to/film-commentary-editor/scripts/audit_audio_joins.py /path/to/join-check.json --output /path/to/join-report.json
```

## 量的含义与适用边界

默认量取接点前 `[-0.25, -0.05]` 秒和后 `[+0.05, +0.25]` 秒的立体声 RMS。采样窗口内必须没有新增中文人声、其他新声音或明显变速；有则把 `probe_has_no_added_speech` 设为 false，改用单独底声轨、缩小窗口或逐样本比对，不把混合声能量当底声。

计算：

`额外增益变化 = 成片接点后前的能量差 − 原片同一位置后前的能量差`

这样不会把原片人物说完一句话、尾音自然减弱，误判成编辑把声音切没。比较前还要检查两条声音是否确实同源、同速、对齐；跨了新声源或音频首尾延迟未校准时，此指标不成立。

默认超过 3 dB 标记人工检查，这只是本案例适用的复查起点，不是响度行业标准。`no_large_gain_step_detected` 只说明这些窗口没有测出大增益台阶，仍需检查随后 1–3 秒是否快速衰落、泵动或断成零。声源过静（低于 −80 dBFS）会标记不可判定。

输出含导出格式与音视频时长；可选比较视频压缩包内容哈希与字幕文件字节。视频哈希一致不包含所有封装时码信息，仍需对照声画起始时间和同步。脚本退出 0 表示分析完成，警告见 JSON；退出 1 表示输入/解码错误。不要把退出 0 叫作“全部验收通过”。

## 其余交付核验

- 用最终 AAC/目标音频编码文件量综合响度与 true peak；中间 WAV 无削波不保证有损编码后的峰值不变。
- 无特殊平台要求时，可把约 −18 LUFS、峰值留约 1–2 dB 余量作为本案例的起点，再按对白动态和实际播放调整，不对每个画面片段单独套同一响度目标。
- 用源时间区间检查重复覆盖；字幕则查实际起声、停顿、说话者与尾字。检测到黑帧/静止画面先回看，阴影与人物停顿不自动等于错误。
- 先跑范围内必要检查；新增修改或出现失败时再针对性复核，已通过且未变的画面不反复重渲染。
