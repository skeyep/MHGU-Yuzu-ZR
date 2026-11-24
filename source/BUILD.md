# Build

This directory contains the integration project's patch, ZR input header, and resource conversion scripts. Start from zeta233/MHGU-Wilds-Long-Sword commit `7f4ad0cbe9f1841bedee2dc77293cb214f2627e7`. The build uses Rust 1.95 with rust-src, Rust LLD, and Zig 0.15.2 as the ARM C compiler driver.

From the root of the Wilds checkout at that commit, run the following in PowerShell. Point `$integrationSource` at the absolute path to this directory.

```powershell
git apply --check "$integrationSource/changes.patch"
git apply "$integrationSource/changes.patch"
Copy-Item "$integrationSource/yuzu_zr_input.h" integration/c/yuzu_zr_input.h
```

Use the settings in integration/.cargo/config.toml. Set RUSTC_BOOTSTRAP=1 and enable ML_WORLD_COMBAT, ML_WORLD_INPUT_VM, ML_WORLD_PRESENTATION and ML_WILDS_MOVES. Set ML_DEBUG_FORCE=0 for distribution. Set ARM_GCC to a wrapper that runs zig cc -target arm-freestanding-eabi -Wno-unused-command-line-argument with the provided arguments. Build the release ELF with cargo +stable build --release in integration. Convert it with Forge's ARM32 ELF-to-NRO tool and place the result at `files/mod/romfs/nativeNX/plugins/mhw_ls_rebuild.nro` in the integration package. For v1.2.12, pair the NRO with the restored Roundslash archive described below and the existing world audio archive from v1.2.11. For the ARM32 converter, use an ARM-capable build of Forge's converter with the ELF input and NRO output paths.

## Rebuild the v1.2.12 Roundslash archive

Use `files/mod/romfs/nativeNX/arc/player/quest/w07.arc` from the v1.2.11 integration ZIP as the base archive. Use an untrimmed `w07.arc` from the [World v1.0.7 release](https://github.com/Akumi-xu/MHW-Long-Sword-Moveset-for-MHGU/releases/tag/v1.0.7) as the native reference. From the patched Wilds checkout, run the following command.

```powershell
python wilds-port/tools/build_single_round.py "v1.2.11-w07.arc" "output-w07.arc" --native-reference "world-v1.0.7-w07.arc"
```

The script restores the stock MOT5127 descriptor, attachment events and sound cues. Put the output at `files/mod/romfs/nativeNX/arc/player/quest/w07.arc` alongside the v1.2.12 plugin.

## Rebuild the v1.2.8 audio and hitbox archives

Use Python 3 with NumPy and the RC fix1 ZIP from the [upstream release](https://www.bilibili.com/video/BV15LyHzmE8). Build the two exported DSP encoder functions in `grok.c` from [gc-dspadpcm-encode revision 039712b](https://github.com/jackoalan/gc-dspadpcm-encode/tree/039712baa1291fbd77a1390e0496757122efd81b) with `zig cc -shared -O2 grok.c -o dspencode.dll` on Windows.

Use the pristine [v1.2.7 package](https://github.com/skeyep/MHGU-Yuzu-ZR/releases/tag/v1.2.7)'s `files/mod/romfs/nativeNX/arc` directory as `base-arc-root`. Export `integration/c/gu_round_banks.h` from upstream commit `7f4ad0c` to a separate file for `base-gu-round-banks.h`. The patch already includes the generated v1.2.8 header, so the output can be compared against the patched header.

```powershell
python merge_rc114.py <rc-fix1.zip> <base-arc-root> <output-arc-root> <wilds-port/tools> <dspencode.dll> <base-gu-round-banks.h> <output-gu-round-banks.h>
```

Copy `forge/world_audio.arc` and `player/quest/w07.arc` from the output ARC root into the corresponding package paths. Request IDs 151–160 use the converted RC fix1 cues. Hit-size group 18 is reserved for the Helm Breaker descent and landing slash. Advance its blade tip by 32 GU units along the existing axis and keep the radius of 65.

## Original v1.2.7 resource pipeline

For the bundled Forge 1.5.1 graphics shim on Yuzu 1734, imgui.fbin changes its outer gpuCode minor declaration from 16 to 14. The Forge loader's shader-control compatibility fix handles the shader records.

Build the continuous charge-walk motion, then initialize the GU-native motion event records before packaging `w07.arc`.

```powershell
python <wilds-port/tools>/build_charge_walk.py <w07.arc> <charge-walk-w07.arc>
python fix_motion_events.py <charge-walk-w07.arc> <repaired-w07.arc> <wilds-port/tools>
python build_release_shape.py <repaired-w07.arc> <release-w07.arc> <wilds-port/tools>
```

The Release ARC adds a native collider group to combine four posed blade spheres with one root sphere. The separate follow-up shell group remains at index 16.

The four native event channels use no-op keys. The Long Sword controller supplies the moves' authored events. The controller routes Type 2 Xbox LT+X through the native second Hunter Art command path in the actor input filter.

Run the audio header repair against the packaged `romfs/nativeNX/arc` tree. It writes the changed archives to the output tree and preserves the encoded audio.

```powershell
python fix_dsp_wave_sizes.py <arc-root> <output-arc-root> <wilds-port/tools>
```

- [Wilds source](https://github.com/zeta233/MHGU-Wilds-Long-Sword)
- [Forge ARM32 converter](https://github.com/Fexty12573/forge-rs/tree/main/cargo-forge)

For the Quick Wheel v0.51 Eden release, run the following from this directory with Python 3. The second argument points to elf_to_nro.py from the author's v0.50 source archive. Use the resulting NRO under romfs/nativeNX/plugins and keep the author's font under romfs/nativeNX/wheelpl.

```powershell
python adapt_wheel.py <original-wheel.nro> <wheel-source/elf_to_nro.py> <gu_craft_wheel.nro>
```

This build resolves the wheel plug-in's WCore-prefixed imports against the shared Forge. The bundled main.npdm and subsdk9 are the Forge host.

Run `python build_wheel_defaults.py` to regenerate the v0.51 SD-card journals for the wheel position, style, mode and loadout. The installer writes those defaults for settings that are absent.

With Pillow installed, run the following against the MHGU 1.4.0 RomFS to rebuild the optional Xbox prompt add-on. The third argument points to the upstream Wilds `wilds-port/tools` directory, which contains `portkit.py`.

```powershell
python build_xbox_prompts.py <romfs> ../xbox-prompts/romfs <wilds-port/tools> --switch-output ../mod/romfs
```

The script draws Xbox glyphs and uses the same Hunter Art slot 2 layout in both packs. Yuzu loads the Xbox quest UI first when both add-ons are enabled. [Prompt sheet coordinate reference](https://github.com/morerokk/MHGURecomp/blob/master/runtime/hle/prompts.c)
