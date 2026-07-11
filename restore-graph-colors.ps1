# 恢复 Obsidian 关系图谱彩色分组
# 用法：关闭 Obsidian → 双击运行 → 重新打开 Obsidian
$target = "$PSScriptRoot\.obsidian\graph.json"
$json = @'
{
  "collapse-filter": false,
  "search": "",
  "showTags": true,
  "showAttachments": false,
  "hideUnresolved": false,
  "showOrphans": true,
  "collapse-color-groups": false,
  "colorGroups": [
    { "query": "path:docs/modules/",      "color": { "a": 1, "rgb": 8453888 } },
    { "query": "path:docs/architecture/", "color": { "a": 1, "rgb": 16729344 } },
    { "query": "path:docs/decisions/",    "color": { "a": 1, "rgb": 16751872 } },
    { "query": "path:docs/guides/",       "color": { "a": 1, "rgb": 11094240 } },
    { "query": "path:docs/templates/",    "color": { "a": 1, "rgb": 16724784 } },
    { "query": "path:docs/bugs/",         "color": { "a": 1, "rgb": 11250603 } },
    { "query": "path:docs/meetings/",     "color": { "a": 1, "rgb": 5592575 } },
    { "query": "path:docs/research/",     "color": { "a": 1, "rgb": 5349760 } },
    { "query": "file:ARCHITECTURE.md OR file:PRD.md OR file:INTERACTION_DESIGN.md OR file:BUG_FIX_LESSONS.md OR file:AUDIT_REPORT.md", "color": { "a": 1, "rgb": 1386240 } }
  ],
  "collapse-display": false,
  "showArrow": true,
  "textFadeMultiplier": 0.3,
  "nodeSizeMultiplier": 1.2,
  "lineSizeMultiplier": 1,
  "collapse-forces": false,
  "centerStrength": 0.4,
  "repelStrength": 12,
  "linkStrength": 0.8,
  "linkDistance": 200,
  "scale": 0.85,
  "close": true
}
'@
$json | Set-Content -Path $target -Encoding UTF8
Write-Host "✅ graph.json 已恢复为 9 个彩色分组" -ForegroundColor Green
Write-Host "请重新打开 Obsidian 查看关系图谱" -ForegroundColor Cyan
