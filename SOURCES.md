# 来源与整合修改

## 太刀动作

| 来源 | 在整合版中的用途 |
| --- | --- |
| **Akumi-xu《世界／冰原》太刀移植 v1.0.7** | 世界系见切、特殊纳刀、居合、气刃突刺及登龙的原始移植。 [上游发布](https://github.com/Akumi-xu/MHW-Long-Sword-Moveset-for-MHGU/releases/tag/v1.0.7) |
| **《GU 世界太刀 v1.1 ZR》可循环纳刀改版** | 参考六种风格接入和循环纳刀的做法。以该改版作为世界系全风格行为的对照。 |
| **zeta233《荒野太刀》v0.3.105** | 实际编译底座，提交 `7f4ad0c`。提供赤刃、蓄力、练气解放及相关的动画、音效和状态机。 [上游发布](https://github.com/zeta233/MHGU-Wilds-Long-Sword/releases/tag/v0.3.105) · [源码](https://github.com/zeta233/MHGU-Wilds-Long-Sword/tree/7f4ad0c) |
| **MHGU ZR Longsword 1.1.3 RC hotfix1** | 对照 ZR 键位和模拟器兼容处理。整合版以荒野底座的独立控制器编译。该路线的原动作署名为东方朔3923，Eden standalone 适配署名为 robertjuniu。 [动作原作者](https://space.bilibili.com/433307879) |

## 前置和附加组件

- **Forge 1.5.1** 由 Fexty12573 及贡献者开发。整合修改了 Yuzu 1734 的 Forge 着色器版本兼容。 [上游发布](https://github.com/Fexty12573/forge/releases/tag/v1.5.1)
- **Damage Numbers r48** 由 PurplefinNeptuna 开发。整合太刀适配了双方共用的伤害钩子。 [上游发布](https://gamebanana.com/mods/725408)
- **快捷轮盘 v0.51** 由仲冬临沧 Novem（仲冬临沧的十一月）开发。整合版适配其 Eden 插件到共享 Forge，并预设右下位置和 Xbox 图标。 [作者发布索引](https://search.bilibili.com/all?keyword=MHGU%20%E5%BF%AB%E6%8D%B7%E8%BD%AE%E7%9B%98%20%E4%BB%B2%E5%86%AC%E4%B8%B4%E6%B2%A7)
- **CAPCOM** 拥有《怪物猎人》系列及游戏素材。上游的动画和音效保留原作署名。构建与转换工具的更多来源见上游仓库及整合包的许可文件。

## 本项目的修改

**输入和风格**。用 Xbox RT（Switch ZR）发动气刃，把 RB 留给普通收刀和奔跑。合并六风格入口，补空中气刃、自动收刀尾段及红刃旋转斩的派生窗口。去掉集中模式，恢复 LT 狩技优先，修正动作间的旧输入缓存。

**战斗**。调整大居合成败结算、蓄力保持和气刃阶段、红刃突刺速度，以及练气解放的减伤、范围和追击。镜花构使用 GU 的原生结算。相关平衡数值属于本次 GU 适配。

**Yuzu 兼容**。补私有动作事件表、修复一批 DSP-ADPCM 音频长度字段、加入 Xbox 按键提示并整合 Forge、跳字与轮盘。更多细节见 [更新记录](CHANGELOG.md)。

[整合包](https://github.com/skeyep/MHGU-Yuzu-ZR/releases/tag/v1.2.7)中的 `files/source` 保存针对上游的差异补丁、资源处理脚本及构建说明，`files/licenses` 保存随组件附带的许可和声明。各组件保留各自的版权和许可。
