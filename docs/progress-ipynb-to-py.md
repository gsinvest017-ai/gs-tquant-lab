# Progress: Convert all `.ipynb` to `.py`

## 目標
把 TQuant-Lab 內所有 Jupyter notebook（`.ipynb`）轉成同名 `.py`，放在原檔旁邊，方便 grep、diff、IDE 編輯與 CI 跑語法檢查。輸出資料不嵌入，magics 註解掉以保持 `.py` 可被 import / py_compile。

## 計畫 milestone

- **M1** — 寫 stdlib-only 轉換器 `tools/ipynb_to_py.py`（無 nbformat 依賴，因系統 Python 受 PEP 668 鎖）
- **M2** — 對全 repo 跑一次，產生 77 個 `.py` 檔
- **M3** — Spot-check 4 個輸出檔的語法 + commit
- **M4** — 寫 `tools/check_converted_py.py` 並對全部 77 個輸出跑全量 py_compile + magic-leak 檢查
- **M5** — Pre-commit hook：當 `.ipynb` 被 stage 時自動重生對應 `.py` 並一起 commit
- **M6** — CI sync check：GitHub Actions 跑 `tools/check_ipynb_py_sync.py` + `tools/check_converted_py.py`，作為 pre-commit hook 的雙保險
- **M7** — `.gitattributes` 把 77 個生成 `.py` 標為 `linguist-generated=true`，讓 GitHub PR diff 收合 + 不計入語言統計
- **M8** — Unit tests `tools/tests/test_ipynb_to_py.py`：用 stdlib `unittest` 為 `_comment_block` / `_sanitize_code` / `convert_to_str` 補 edge case 覆蓋，並在 CI workflow 加上 `python3 -m unittest discover -s tools/tests`
- **M9** — Orphan `.py` detection：擴充 `tools/check_ipynb_py_sync.py` 加 `_orphan_py()`，掃出沒有對應 `.ipynb` 的孤兒 `.py`（notebook 被刪/改名但 `.py` 留下的狀況），補 9 個 unit test 進 `tools/tests/test_check_ipynb_py_sync.py`
- **M10** — Unit tests for `check_converted_py.py`：補 31 個 unit test 進 `tools/tests/test_check_converted_py.py`，覆蓋 `MAGIC_RE` / `_paired_py_files` / `_compile_check` / `_magic_check` / `main()` — 完成 toolchain 三支工具（converter / sync checker / converted-py validator）的測試三聯
- **M11** — Integration tests for `tools/hooks/pre-commit` + `tools/hooks/install.sh`：補 12 個 subprocess-based test 進 `tools/tests/test_pre_commit_hook.py`，每個 test 在自有 temp git repo 跑真實 hook（含 symlink install）。順手修掉一個被測試挖出來的 root-level `.ipynb_checkpoints/` filter bug
- **M12** — Pre-commit hook bidirectional sync：擴充 `tools/hooks/pre-commit` 在 `.ipynb` 被 delete / rename 時自動 `git rm` 掉對應的 `.py`，把 M11 文件裡的「known limitation: orphan after rename」直接關掉。翻轉 2 個鎖住舊行為的 hook test、補 1 個 deletion-without-existing-py silent test
- **M13** — Unit tests for `ipynb_to_py.main()` CLI entry point：補 12 個 test 進 `tools/tests/test_ipynb_to_py.py`，覆蓋 root-walk / `--files` / `--dry-run` / 錯誤路徑（empty tree / missing file / 非 .ipynb 副檔名 / mixed valid+invalid / malformed JSON），並小重構 `main()` 接受 `argv` 參數（對齊 M10 的 `check_converted_py.main(argv)` 與 M9 的 `check_ipynb_py_sync.main(argv)`）。完成四個 CLI 工具的 main() 級覆蓋。
- **M14** — Unit tests for `check_ipynb_py_sync.main()` + `_pairs` / `_diff_preview`：補 19 個 test 進 `tools/tests/test_check_ipynb_py_sync.py`。M9 只測了 `_orphan_py()`，sync checker 的 `main()`（in-sync / missing / drift / error / orphan 五條 exit path）與 `_pairs`（notebook discovery + checkpoint filter）、`_diff_preview`（drift 渲染 + truncation）一直沒有 unit 覆蓋。補完後 sync checker 與 converter（M13）、converted-py validator（M10）同樣達到 main() 級覆蓋，四支 CLI 工具的 entry point 全部上鎖。
- **M15** — `--strict` flag for `ipynb_to_py.py`：把 M13 進度文末的 follow-up（malformed notebook 寬鬆 vs strict 二選一）轉成實做。新增 `--strict` 旗標讓任一 conversion 失敗回 rc=1（仍 try-all、不 fail-fast），CI 可主動擋住損壞的 notebook；預設行為與既有測試完全不變。補 4 個 test 進 `MainTests`：clean strict、strict + malformed、strict + `--files`、strict + dry-run。
- **M16** — `--dry-run` 也驗證 notebook parseability + 在 CI 接上 strict pre-scan gate：把 M15 文末 `test_strict_mode_dry_run_does_not_fail` lock 進去的限制（`--strict --dry-run` 不擋壞檔，因 dry-run 在 parse 前就 `continue`）依 M11→M12 precedent 關掉。讓 dry-run 分支仍 parse（`convert_to_str`）但不寫檔，使 `--strict --dry-run` 成為零副作用、不重生 77 個 `.py` 的 CI pre-flight；翻轉 1 個 locked test、補 2 個 test（clean strict-dry-run pass、plain dry-run 仍寬鬆），並在 `.github/workflows/ipynb-py-sync.yml` 加一步 `python3 tools/ipynb_to_py.py --strict --dry-run .` 作為最便宜的 fail-fast gate（M15 承諾的 CI strict 守門，現在 dry-run 會 parse 才真的有意義）。
- **M17** — Aggregate local runner `tools/check_all.py`：toolchain 已長到 4 支工具 + 4 道 CI 步驟，但本地開發者要嘛背 4 條指令、要嘛去讀 workflow yaml 才能在 push 前重現 CI。M17 補一個單一入口，step-for-step 對齊 `ipynb-py-sync.yml`（unit tests → strict pre-scan → sync check → converted check），讓 `python3 tools/check_all.py` 一條指令 == CI。沿用 M15 try-all 哲學（全跑不 fail-fast，一次列出所有問題）；`build_steps` / `run_steps` 拆成可測純函式 + 可注入 runner，補 18 個 test（含一個對真 repo 跑 steps 2-4 的 integration smoke）進 `tools/tests/test_check_all.py`。
- **M18** — CI parity drift guard：M17 把 `check_all.py` 寫成「step-for-step 對齊 `ipynb-py-sync.yml`」，但沒有任何東西強制兩者保持同步——改了 workflow yaml（加/刪/重排 step、拿掉 `--strict`）卻忘了改 `check_all.py`，「local == CI」承諾就會 silently 腐爛。M18 補 `WorkflowParityTests`（6 個 test 進 `tools/tests/test_check_all.py`），純 stdlib 解析 workflow yaml 的 `run:` 指令、normalize 成 `(tool, long_flags)` signature，與 `build_steps('.')` 做 ordered 比對。沿用 M9（orphan）/ M14（sync main paths）precedent：把「只靠慣例成立」的不變量變成「靠 test 成立」。不動 production code。
- **M19** — `.gitattributes` ↔ sync-checker hand-written-dir parity guard：把「什麼算 hand-written Python」這個同時寫在 `.gitattributes`（`tools/**/*.py linguist-generated=false`）與 `check_ipynb_py_sync._HANDWRITTEN_DIR_PARTS` 的概念用 `GitattributesParityTests`（6 個 test）鎖死，兩邊不一致就 fail。
- **M20** — `tools/README.md` toolchain 參考文件 + README↔tools/ parity guard：toolchain 已長到 4 支 Python 工具 + 2 支 hook script + CI + 157 test，但知識只散在 chronological 的 `docs/progress-ipynb-to-py.md`，沒有一份可當 reference 的入口文件。M20 補 `tools/README.md`（工具一覽表、常用指令、hook 安裝、CI 對應、測試清單、失敗修法），並依 M18 / M19 precedent 補 `tools/tests/test_readme.py` 的 `ReadmeParityTests`（6 個 test，純 stdlib），把 README「## Tools」表格列出的工具集合鎖死 == 實際 `tools/*.py` + 2 支 hook script，文件再也不能 silently 與實際工具樹漂移。不動 production code。
- **M21** — README「## 測試」table ↔ `tools/tests/test_*.py` parity guard：M20 的 `ReadmeParityTests` 只鎖了「## Tools」表格（production 工具 + hook）對 `tools/*.py`，但同一份 README 的「## 測試」表格（列出 6 支 test 檔）完全沒被守——新增 / 刪除 / rename 一支 test module，文件就 silently 腐爛。M21 依 M20 precedent 把 `_tools_section()` 抽成通用 `_section(header)`，補 `tools/tests/test_readme.py` 的 `ReadmeTestTableParityTests`（4 個 test，純 stdlib），把「## 測試」表格列出的 test 集合鎖死 == 實際 `glob('tools/tests/test_*.py')`。關掉 README 最後一張未被守的表。不動 production code。
- **M22** — README「## CI 對應」numbered list ↔ CI workflow parity guard：M18 把 `check_all.build_steps()` 與 `.github/workflows/ipynb-py-sync.yml` 的 run-steps 用 `WorkflowParityTests` 互鎖，但同一條 CI step 序列在 `tools/README.md`「## CI 對應」段還有**第三份手寫副本**（4 步 numbered list，內嵌 backtick 指令）完全沒被守——改了 workflow / `check_all` 的步驟卻忘了改 README，這份「文件版 CI 流程」就 silently 腐爛。M22 依 M18 / M20 / M21 precedent 補 `tools/tests/test_readme.py` 的 `ReadmeCiParityTests`（6 個 test，純 stdlib），解析 README CI 段的 numbered backtick 指令，**復用** M18 的 `_step_signature` / `_workflow_run_commands`（同一套 normalization）把它與 workflow run-steps 做 ordered 比對。透過 M18 的 workflow == build_steps 互鎖，傳遞性保證 README == workflow == `check_all`。關掉 README 最後一份未被守的 CI step 清單。不動 production code。
- **M23** — `pre-push` git hook：把 hook story 從單向補成雙向。M5/M11/M12 的 `pre-commit` 只負責「stage `.ipynb` 時重生 `.py`」，但若有人 `git commit -n` 繞過 hook、或根本沒裝 hook，drifted / 無法 compile 的 `.py` 還是能被 push 上去，要等 CI 紅才發現。M23 新增 `tools/hooks/pre-push` 跑 `check_all.py --skip-tests`（CI step 2-4 的 artifact 檢查：strict pre-scan + sync + converted），不同步就擋下 push；擴 `install.sh` 一次裝兩個 hook（沿用 idempotent + backup 邏輯）；把新 hook 加進 `test_readme._HOOK_PATHS` 讓 README parity guard 雙向守住；補 4 個 `PrePushHookTests` + 翻新 3 個 `InstallShTests` 到 `tools/tests/test_pre_commit_hook.py`。不動 converter / 三支 checker / CI workflow。
- **M24** — hook-set parity guard：`install.sh` 迴圈 ↔ README 手動安裝 `ln -sf` 區塊 ↔ 實際 `tools/hooks/` 腳本集。M23 之後「toolchain 要裝哪些 git hook」這份清單同時手寫在四個地方：(1) `tools/hooks/` 下的實際腳本（真理來源）、(2) `install.sh` 的 `for hook in pre-commit pre-push` 迴圈、(3) README「## Tools」表（M20 守，但靠**硬編**的 `_HOOK_PATHS`）、(4) README「## 安裝 git hooks」段的手動 `ln -sf` 指令（**完全沒守**）。新增 hook 卻漏改 (2) 或 (4) 就 silently 腐爛。M24 依 M18 / M20 / M21 / M22 precedent 補 `tools/tests/test_readme.py` 的 `InstallParityTests`（6 個 test，純 stdlib）：純 regex 解析 `install.sh` 迴圈與 README 手動 `ln -sf` 區塊，兩邊與「`tools/hooks/` 下除 `install.sh` 外的所有腳本」這個磁碟真理鎖死；並把硬編的 `_HOOK_PATHS` 常數對磁碟驗證。關掉 hook 安裝清單最後兩份未被守的副本。不動 production code。
- **M26** — `check_all.py` 自身 docstring step list ↔ `build_steps()` parity guard：M18 把 `build_steps()` 與 `.github/workflows/ipynb-py-sync.yml` 互鎖、M22 把 README「## CI 對應」list 鎖進 workflow，但同一條 CI 4-step 序列在 `tools/check_all.py` 的**模組 docstring**（lines 9-12 的 numbered list）還有**第四份手寫副本**完全沒被守——改了 `build_steps()` 卻忘了改自己檔頭的 docstring，這份「工具自我說明」就 silently 腐爛（讀 source 的人被誤導）。M26 依 M18 / M22 precedent 補 `tools/tests/test_check_all.py` 的 `DocstringParityTests`（6 個 test，純 stdlib），純 regex 解析 docstring 的 numbered `python3` 指令、**復用** M18 的 `_step_signature`（同一套 normalization）與 `build_steps('.')` 做 ordered 比對；並直接斷言 docstring == workflow，透過 M18 的 workflow == build_steps 互鎖傳遞性閉環 docstring == build_steps == workflow == README。關掉 CI step 序列最後一份未被守的手寫副本。不動 production code。
- **M25** — notebook-discovery 行為 parity guard：toolchain 有**三支工具各自獨立**重寫了「`.ipynb` 探索 + `.ipynb_checkpoints` 過濾」這段 walk——converter 的 root-walk（`ipynb_to_py.main`，決定哪些 notebook 會重生 `.py`）、sync checker 的 `_pairs`（決定哪些做 byte-for-byte 比對）、validator 的 `_paired_py_files`（決定哪些生成 `.py` 跑 compile + magic-leak）。三者目前邏輯相同但沒有任何東西強制它們枚舉**同一組** notebook——日後在某一支的 walk 加 skip dir / 動 checkpoint filter 卻漏改另兩支，coverage 就 silently 漂移（notebook 被轉但沒被 sync-check、或被 sync-check 但沒被 compile-validate），而 CI 抓不到（每個 step 只看自己那一片）。M25 依 M9（orphan）/ M18（CI parity）/ M20-M24（README/install parity）precedent，補 `tools/tests/test_discovery_parity.py` 的 `NotebookDiscoveryParityTests`（8 個 test，純 stdlib），但用**行為 parity** 而非 text parsing：在同一棵 fixture tree（root nb + nested nb + root-level/nested `.ipynb_checkpoints/` notebook）上跑三支真實 discovery path，斷言枚舉出的 notebook 集合三方相同。converter 端透過 `--dry-run` 輸出取得真實 walk 結果（不在 test 內複寫 walk 邏輯）。不動 production code。
- **M27** — pre-push hook「mirror CI steps 2-4」契約 parity guard：M23 的 `pre-push` hook 跑 `check_all.py --skip-tests`，讓 push 被 CI 的 artifact 檢查（step 2-4，跳過 unit tests）守門。但有兩個只靠慣例成立的不變量沒被守：(1) hook 指令**真的帶 `--skip-tests`**——整合測試 `PrePushHookTests` 雖然 end-to-end 跑 hook，卻只能**偶然**抓到 `--skip-tests` 被拿掉（其 fixture 沒有 `tools/tests/` 目錄，full check_all 的 `unittest discover -s tools/tests` 會丟 `ImportError` 而 rc≠0），這很脆弱：失敗訊息是含糊的「Start directory is not importable」、看不出真因是少了 flag，且若 fixture 哪天放了空的 `tools/tests/`，discover 找到 0 test 回 rc 0，drop 就漏網；(2) `build_steps(skip_tests=True)` == 「CI step 2-4」（hook docstring 的宣稱）== workflow run-steps 砍掉那一個 unit-test step——M18 只鎖了 full `build_steps == workflow`，沒人把 skip_tests 子集綁到 workflow。M27 依 M18 / M22 / M26 precedent 補 `tools/tests/test_check_all.py` 的 `PrePushParityTests`（7 個 test，純 stdlib）：純 regex + `shlex` 解析 hook 的 `check_all.py` 指令、斷言帶 `--skip-tests` 且不帶其他 long flag（文字層、像 M24 解析 `install.sh`）；並**復用** M18 的 `_step_signature` / `_workflow_run_commands` 斷言 skip_tests 恰好砍掉第一個（unit-test）step、其餘 2-4 與 workflow 砍掉 unittest 後逐一相符。關掉 hook 契約最後一份未被守的副本。不動 production code。
- **M28** — `_sanitize_code` IPython-help 偵測精準化（修掉 latent code-corruption bug）：converter 一直用 naive `stripped.endswith('?')` 判斷 IPython suffix-help（`obj?` / `obj??`），但這會 false-positive 把任何結尾是 `?` 的**合法 Python 行**整行註解掉——`x = run()  # done?`（trailing-question comment）、triple-quoted string 內 prose 行 `Are you ready?`、甚至把已是註解的 `# really?` 變成 `# # really?`。最毒的是 converter 與 sync checker **共用** `_sanitize_code`，所以「valid code 被靜默註解掉」CI **抓不到**（重生與比對用同一條壞規則，byte-for-byte 永遠相符）。M28 把 `endswith('?')` 換成錨定 identifier/attribute/subscript/call chain 的 `_HELP_SUFFIX_RE`，只有「裸物件參照鏈 + 結尾 `?`/`??`」才算 help。**provably byte-for-byte 安全**：先掃過全 repo 確認 77 個 notebook 目前有 **0** 行 code cell 結尾是 `?` 而非 magic（該 branch 目前 comment 出 0 行），收緊規則零 regen。補 5 個 test 進 `SanitizeCodeTests` + 更新模組 docstring。動 converter（一行 + 一條 regex 常數），不動三支 checker / hook / CI workflow。
- **M29** — CI workflow `paths:` trigger filter parity guard：M18 / M22 / M26 / M27 連續鎖死了 workflow 的 **run-steps**（CI 做什麼）對 `build_steps()` / README / docstring / pre-push 的一致性，但同一份 `ipynb-py-sync.yml` 還有一塊**完全沒被守**的手寫副本——`on.push.paths` 與 `on.pull_request.paths` 這對 trigger filter（決定「CI 到底跑不跑」）。它**手寫兩遍**：在 push 加一條路徑卻忘了 pull_request，push 與 PR build 就 silently 覆蓋不同檔案集；更危險的是手滑刪掉 `**/*.ipynb` 或 `tools/**`，CI 會**安靜地不再對它存在目的所要守的變更觸發**（這種「綠」比某個 step 紅更毒，因為根本沒跑）。M29 依 M18-M27 precedent 補 `tools/tests/test_check_all.py` 的 `WorkflowTriggerParityTests`（6 個 test，純 stdlib，無 PyYAML 因系統 Python PEP 668 鎖），新增 `_workflow_trigger_paths()` 縮排感知 line parser 抽出兩個 event 的 `paths:` list，斷言：(1) push paths == pull_request paths（兩份副本不准漂移）、(2) == canonical `_EXPECTED_TRIGGER_PATHS`（縮小 trigger surface 會紅）、(3) 兩個 artifact glob（`**/*.ipynb` / `**/*.py`）在、(4) `tools/**` 在、(5) workflow 自我參照路徑在（編譯出非硬編）。關掉 workflow 最後一份未被守的手寫副本。不動 production code。
- **M30** — README「## CI 對應」intro trigger 描述 ↔ workflow `paths:` parity guard：M22 鎖了 README「## CI 對應」的 **numbered run-step list**（CI 做什麼）對 workflow run-steps、M29 鎖了 workflow 內部兩份 `paths:` 副本（push == pull_request == canonical），但同一段「## CI 對應」的 **intro 句子**還有**第三份手寫副本**——「在 push / PR 觸碰 `.ipynb` / `.py` / `tools/**` 時跑」這串 trigger surface 描述完全沒被守。改了 workflow 的 trigger `paths:`（拿掉 `tools/**`、加新 glob）卻忘了改 README intro，這份「文件版 CI 觸發條件」就 silently 腐爛，誤導讀文件的人對「CI 什麼時候跑」的理解。M30 依 M22 / M29 precedent 補 `tools/tests/test_readme.py` 的 `ReadmeCiTriggerParityTests`（6 個 test，純 stdlib），新增 `_display_trigger()` 把 workflow glob（`**/*.ipynb`）與 README 副檔名寫法（`.ipynb`）normalize 成同一組 canonical display token，**復用** M29 的 `_workflow_trigger_paths()` 取 workflow 真理，斷言 README intro 引用的 trigger token 集合 == workflow 的 trigger surface。透過 M29 的 push == pull_request == canonical 互鎖，傳遞性保證 README == workflow == canonical。workflow 自我參照路徑刻意不屬於 user-facing surface（兩邊 display set 都排除），用一個 test 鎖住這個 intentional asymmetry。不動 production code。
- **M31** — `_sanitize_code` 字串感知 magic 偵測（修掉 triple-quoted string 內 `!`/`%`/`?` 行被誤註解的 latent corruption bug）：M28 把 `?`-**suffix** help（`obj?` / `df.head?`）的偵測錨定到 reference chain，修掉「trailing `?` 的合法行被整行註解」這條 latent bug；但 **leading** `%`/`!`/`?` 的偵測一直是純逐行、不感知字串——一個 BEGIN 在 triple-quoted string 內、又恰好以 `%`/`!`/`?` 開頭（或長得像 help 鏈）的行，會被靜默註解掉、汙染字串內容（例：docstring 內嵌 shell 片段 `!run this`、`%`-template `%(name)s`、prose `df.head?`）。與 M28 同款最毒之處：converter 與 sync checker **共用** `_sanitize_code`，所以「字串內容被靜默註解」CI **抓不到**（重生與比對套同一條壞規則，byte-for-byte 永遠相符）。M31 新增 `_advance_string_state()` 逐行追蹤 triple-quote 狀態（會吃掉一般單/雙引號字串與 `#` 註解，避免其內的 `"""` 或 `#` 翻動狀態），`_sanitize_code` 只在 `state is None`（不在 triple string 內）時才判斷 magic。**provably byte-for-byte 安全**：對全 repo 77 個 notebook 跑 shipped function vs 舊逐行規則 diff 出 **0** 個 cell 差異，零 regen。補 6 個 test 進 `SanitizeCodeTests`（in-string `!`/`%`/help-chain 不註解、close 後真 magic 仍註解、open 前真 magic 仍註解、一般字串內的 `"""` 不誤開 block）+ 更新模組 docstring。動 converter（一個 helper + `_sanitize_code` 改用 state），不動三支 checker / hook / CI workflow。
- **M32** — `check_converted_py._magic_check` 字串感知化（修掉 M31 留下的 validator 端 latent false-positive bug）：M31 把 converter 的 magic 偵測改成 string-aware，所以 triple-quoted string 內以 `!`/`%`/`?` 開頭的行（docstring 內嵌 shell 片段 `!run this`、`%`-template `%(name)s`、prose `?help`）會被**正確保留 verbatim**；converter 與 sync checker 共用 `_sanitize_code` 所以兩邊一致。**但** `check_converted_py.py` 的 `_magic_check` 是**第三支獨立**重寫的 magic 偵測（純逐行 `MAGIC_RE.match(lstrip)`，完全不感知字串），M31 沒碰它——於是「converter 正確保留的 in-string magic 行」會被 validator 當成 magic leak 報出來，CI 紅。這是與 M28 / M31 同款的 latent bug，只是換到 validator：兩支工具對「什麼是 magic」現在不一致。實測（probe）：一個 docstring 內含 `!run this` / `%(name)s` 的 notebook，converter 產出合法 `.py`（py_compile 過），但 `check_converted_py` 報 2 個 magic leak、exit 2。M32 讓 `_magic_check` **復用** converter 的 `_advance_string_state`（HERE-on-sys.path import，同 sync checker 復用 `convert_to_str` 的形式），只在 `state is None`（不在 triple string 內）時才套 `MAGIC_RE`。**provably 零行為變動**：對全 repo 77 個 paired `.py` 跑 old naive scan vs new string-aware scan，兩者各 flag **0** 行、**0** 檔差異（M31 已證明目前無 in-string magic 行），CI 維持綠、真正的 top-level leak 仍被抓。補 6 個 test 進 `MagicCheckTests`（in-string `!`/`%`/`?` 不報、close 後真 leak 仍報、open 前真 leak 仍報、一般字串內 `"""` 不誤開 block）+ 更新模組 docstring。動 validator（一個 import + `_magic_check` 改用 state），不動 converter / sync checker / hook / CI workflow / README / `.gitattributes`。

## 進度日誌

### M1 — 轉換器
- 寫了 `tools/ipynb_to_py.py`：把 ipynb（純 JSON）逐 cell 轉出
  - code cell → 原樣輸出
  - markdown / raw cell → `# ` 前綴註解
  - magics (`!`, `%`, `?`) → 註解掉，避免 `py_compile` 噴 syntax error
  - 每個 cell 前加 `# %% [kind] cell N` 標記（VS Code / PyCharm 認得，可當 cell 切分）
- 為什麼不裝 jupytext / nbconvert：系統 Python 是 externally-managed，`pip install` 被擋；conda 沒裝；用 stdlib 最乾淨

### M2 — 全 repo 轉檔
- `python3 tools/ipynb_to_py.py .` → `Converted 77/77 notebooks.`，零錯誤
- 涵蓋目錄：`./Aroon.ipynb`、`Problem/` (6)、`example/` (39)、`lecture/` (31)

### M3 — Spot-check
- `python3 -m py_compile` 跑過 4 個樣本（含中英檔名、含 `!zipline ingest` magic、含長 markdown 區塊）全部通過
- 確認 markdown 正確變成 `#` 註解、import 清單完整、`!zipline` 已註解化

### M4 — 全量驗證腳本
- 寫了 `tools/check_converted_py.py`（stdlib-only，配對 .ipynb / .py 後跑兩道檢查）：
  - **py_compile**：抓 syntax error，能擋住未註解的 magic 或殘留 markdown
  - **Magic-leak 掃描**：用 regex `^[!%?]` 找漏網的 IPython 指令
- 對全 repo 跑：`OK 77/77`、`Missing 0`、`Compile failures 0`、`Magic leaks 0`
- 統計：30,251 行、2,092 個 cell marker
- Exit code 0 — 可直接接 CI；exit 2 代表有 leak/失敗
- 用法：
  ```bash
  python3 tools/check_converted_py.py           # 預設掃當前目錄
  python3 tools/check_converted_py.py --quiet   # 只印 summary
  python3 tools/check_converted_py.py lecture   # 只掃子目錄
  ```

### M5 — Pre-commit hook 同步 `.ipynb` ↔ `.py`
- 在 `tools/ipynb_to_py.py` 新增 `--files <ipynb...>` 模式，允許 hook 對單一檔案而非整個 root 跑轉換；原 root walk 模式維持不變
- 寫了 `tools/hooks/pre-commit`：
  - 用 `git diff --cached --name-only --diff-filter=ACMR` 抓出本次要 commit 的 `.ipynb`（自動略過 deletion 與 `.ipynb_checkpoints/`）
  - 呼叫 `python3 tools/ipynb_to_py.py --files <staged>` 重生對應 `.py`
  - 對每個重生出來的 `.py` 跑 `git add`，讓它們一起進 commit
- 寫了 `tools/hooks/install.sh`：把 `tools/hooks/pre-commit` symlink 進 `.git/hooks/pre-commit`（idempotent，已存在的非 symlink hook 會 backup）
- 為什麼放 `tools/hooks/` 而不是直接寫 `.git/hooks/`：`.git/` 不會被 tracked，所以實際 hook 內容必須住在 repo 內、由使用者 opt-in 安裝
- End-to-end 測試（在 `Aroon.ipynb` 加 markdown cell → `git add` → 手動跑 hook）：
  - hook 偵測到 staged ipynb、轉換成功、`Aroon.py` sha 改變、被自動 stage
  - `git restore` 後 sha 還原 → 流程乾淨可逆

#### 安裝指令
```bash
tools/hooks/install.sh
# 之後 git commit 任何 .ipynb 變更時，對應的 .py 會被自動重生並 stage
```

#### 手動安裝（不想跑 install.sh）
```bash
ln -sf ../../tools/hooks/pre-commit .git/hooks/pre-commit
```

### M6 — CI sync check (GitHub Actions)
- Pre-commit hook 是 opt-in，使用者沒裝就會漏；CI 是強制守門員，補上這道
- 重構 `tools/ipynb_to_py.py`：把 `convert()` 拆成 `convert_to_str()`（純函式，回字串）+ `convert()`（呼叫前者寫檔）。對外行為不變；新增 import 點供 sync checker 復用同一份產生邏輯，避免轉換器與檢查器各自一份規則導致漂移
- 新增 `tools/check_ipynb_py_sync.py`：
  - 對每個 `.ipynb` 用 `convert_to_str()` 重產 expected text，與磁碟上 `.py` 做 byte-for-byte 比較
  - 不一致時印 unified diff（預設前 20 行，可 `--no-diff` 關閉）
  - Exit 0 = 全部同步；Exit 2 = 有 missing/drift；Exit 1 = usage error
  - 純 stdlib，CI 不需要 pip install
- 新增 `.github/workflows/ipynb-py-sync.yml`：
  - Trigger：`push` / `pull_request`，只在 `.ipynb` / `.py` / `tools/**` / 本 workflow 自己變動時跑
  - Steps：checkout → setup-python 3.11 → `check_ipynb_py_sync.py` → `check_converted_py.py`
  - 任一檢查失敗 CI 就紅，PR 無法合
- 本地驗證：
  - `python3 tools/check_ipynb_py_sync.py --quiet` → `In sync: 77/77`，exit 0
  - 故意 append 一行進 `Aroon.py` 模擬 drift → exit 2 + 報出 `DRIFT: Aroon.ipynb`，還原後 exit 0
  - Refactor 後 `python3 tools/ipynb_to_py.py --files Aroon.ipynb` + `check_converted_py.py` 仍全綠

#### 用法
```bash
# Local — 在 commit / push 前自己跑
python3 tools/check_ipynb_py_sync.py             # 預設掃當前目錄
python3 tools/check_ipynb_py_sync.py --quiet     # 只印 summary
python3 tools/check_ipynb_py_sync.py --no-diff   # 印 DRIFT 路徑但不印 diff 內文
python3 tools/check_ipynb_py_sync.py lecture     # 只掃子目錄
```

#### 失敗時怎麼修
```bash
python3 tools/ipynb_to_py.py .          # 重生全部 .py
git add '**/*.py'                       # 把更新後的 .py 一起 commit
```

### M7 — `.gitattributes` 標記生成檔
- 問題：77 個生成 `.py` 共 30,251 行，沒有特別標記的話 GitHub 會
  1. 在每個 notebook PR 把 diff 撐成兩倍（既看 `.ipynb` 又看 `.py`）
  2. 把這些「假 Python」算進 repo 的語言統計，蓋過真正的 tooling code
- 解法：新增 `.gitattributes` 用 inclusive default + 反向 override：
  ```
  *.py linguist-generated=true
  tools/**/*.py linguist-generated=false
  ```
  GitHub Linguist 規則：後寫的 pattern 覆蓋前面的，所以根目錄／`Problem/`／`example/`／`lecture/` 下的 `.py` 全部視為 generated；`tools/**/*.py`（3 個手寫工具）保留正常 diff 與語言統計
- 為什麼用「全部 generated + tools 例外」而非「明列 generated 目錄」：新增 notebook 不用改 `.gitattributes`，convention-over-configuration；缺點是若有人之後在 tools/ 以外手寫 `.py`，要記得加 override
- 本地驗證：
  ```bash
  git check-attr linguist-generated Aroon.py
  # → Aroon.py: linguist-generated: true

  git check-attr linguist-generated tools/ipynb_to_py.py
  # → tools/ipynb_to_py.py: linguist-generated: false
  ```
  跨中英檔名（含 `lecture/10分鐘體驗.py`、`example/TQ_期貨策略範例.py`）都正確解析
- 注意：`linguist-generated` 影響的是 GitHub UI；本地 `git diff`、`tools/check_ipynb_py_sync.py` 的 byte-for-byte 比對、CI sync check 全部維持不變
- 沒做的事（保留 reviewer 看 diff 的彈性）：
  - 沒設 `merge=ours`：notebook 兩支分支各自編輯時還是會正常衝突，不會被 silent overwrite
  - 沒設 `diff=python`：與 `linguist-generated=true` 會衝突，且 PR 用不到（GitHub 已收合）

### M8 — Unit tests for the converter
- 為什麼補：M1~M4 只用 77 個 notebook 做 smoke test，從沒驗證 edge case；之後若要動 `HEADER` / `CELL_SEP` / sanitize regex，沒有快速回饋
- 新增 `tools/tests/test_ipynb_to_py.py`（純 stdlib `unittest`，0 額外依賴），31 個 case 分三組：
  - **`_comment_block`** — 單行 / 多行 / 中夾空行 / 空字串 fallback 到 `#`
  - **`_sanitize_code`** — 純程式碼、`!` shell magic、`%` line magic、`%%` cell magic、`?prefix` / `suffix?` / `obj??`、縮排 magic、混合 magic + code
  - **`convert_to_str`** — 空 notebook、header 含 src 檔名、code/markdown/raw cell、空 source 跳過但保留 index、source 為 list of str、cell marker 含 kind+idx、未知 cell type fallback、cell 順序保留、缺 `cell_type` 預設 unknown、缺 `source` 跳過、idempotent
- **發現 + lock 進 test 的真實 quirk**：`_sanitize_code` 的 trailing newline 處理不對稱
  - input 沒 `\n` → output **有** `\n`
  - input 一個 `\n` → output **沒** `\n`（`splitlines()` 吃掉，`if not endswith('\n')` 分支不補）
  - 雙 `\n` → 一個 `\n`
  - 為什麼不修：77 個 generated `.py` 都依賴此行為通過 byte-for-byte CI；改 sanitize 規則會強制 regen 全部 77 檔 + diff 噪音
  - 補在 test 名稱 `test_trailing_newline_stripped_when_present` 內，附 docstring 解釋為何 lock 進 test
- 改 `.github/workflows/ipynb-py-sync.yml`：在 sync / compile check **之前**多一步 `python3 -m unittest discover -s tools/tests -v`；轉換器壞了會在最便宜的層級先紅
- 不需要 `__init__.py`：unittest discover 從 3.3 開始支援 namespace package；`__pycache__/` 已在 `.gitignore`
- 本地驗證：
  - `python3 tools/tests/test_ipynb_to_py.py -v` → `Ran 31 tests in 0.007s OK`
  - `python3 -m unittest discover -s tools/tests -v` → 同樣 31 OK
  - `python3 tools/check_ipynb_py_sync.py --quiet` → 仍 77/77
  - `python3 tools/check_converted_py.py --quiet` → 仍 77/77

#### 用法
```bash
# 跑全部 unit test
python3 tools/tests/test_ipynb_to_py.py
python3 tools/tests/test_ipynb_to_py.py -v        # verbose
python3 -m unittest discover -s tools/tests       # discover mode（CI 用這個）

# 跑單一 test class
python3 -m unittest tools.tests.test_ipynb_to_py.SanitizeCodeTests
```

### M9 — Orphan `.py` detection
- 為什麼補：M6 的 `check_ipynb_py_sync.py` 只 walk `.ipynb`，所以「`.ipynb` 被刪除/改名、但 `.py` 留下」這種 stale orphan 完全偵測不到 — sync check 不會看見、`check_converted_py.py` 也只從 ipynb 端 iterate。CI 與 pre-commit hook 都有這個盲點
- 解法：在 `check_ipynb_py_sync.py` 加 `_orphan_py(root)` helper：
  - `rglob('*.py')` 找全部 `.py`
  - 排除 skip dirs：`.git` / `.github` / `.ipynb_checkpoints` / `__pycache__` / `.venv` / `venv`
  - 排除 handwritten 區（`tools/` 之下）：與 M7 的 `.gitattributes` 規則 (`tools/**/*.py linguist-generated=false`) 對齊
  - 若 `.py` 旁邊沒有同名 `.ipynb` 就視為 orphan
  - 回傳 root-relative `Path` list，並依 pathlib `_parts` tuple 排序（同 prefix 時 directory 內容先於同層檔案，例如 `a/c.py` < `a.py`）
- `main()` 整合：
  - `bad = missing + drift + errors + orphans`（用 union 算總壞數，避免 orphan 重複計入 in-sync）
  - Summary 多印一行 `Orphan .py (no .ipynb): N`
  - non-quiet 模式對每筆印 `ORPHAN: <path> (no matching .ipynb — delete it or restore the notebook)`
  - 退出時若有 orphan 額外印「delete the stale .py or restore the missing .ipynb」提示
  - Exit code 仍是 2（與 missing/drift 同等對待）
- Smoke test（手動，無汙染 repo）：
  - Clean: `check_ipynb_py_sync.py --quiet` → `In sync: 77/77`、`Orphan .py: 0`、exit 0
  - Inject `example/stale_orphan.py` → exit 2，列出 `ORPHAN: example/stale_orphan.py`
  - 刪除後再跑 → exit 0、orphan count 0
- Unit test `tools/tests/test_check_ipynb_py_sync.py`（純 stdlib `unittest`，9 cases，全部用 `tempfile.TemporaryDirectory()` 隔離）：
  - 空目錄 → 0 orphan
  - 配對 `.ipynb`+`.py` → 0 orphan
  - 純 `.py`（root 與子目錄各一）→ 各自被偵測
  - `tools/` 下任何 `.py`（含 `tools/tests/`、`tools/hooks/`）→ 永遠不視為 orphan
  - 全部 skip dir（`.git` / `.github` / `.ipynb_checkpoints` / `__pycache__` / `.venv` / `venv`） → 永遠不視為 orphan
  - 排序順序 lock 進 test（含 docstring 說明 pathlib parts-tuple 排序行為）
  - 混合 tree（兩配對 + 一 orphan + 一 handwritten） → 只回那一個 orphan
  - 「`.ipynb` 沒有對應 `.py`」（missing）→ 不算 orphan（由 main loop 另外回報），明確區分職責
- CI workflow 無需改動：`.github/workflows/ipynb-py-sync.yml` 已經跑 `python3 -m unittest discover -s tools/tests`，新 test 自動被 pick up；且 sync step 已經跑 `check_ipynb_py_sync.py`，orphan 行為自動接上
- 本地驗證：
  - `python3 tools/tests/test_check_ipynb_py_sync.py` → `Ran 9 tests OK`
  - `python3 -m unittest discover -s tools/tests` → `Ran 40 tests OK`（M8 31 + M9 9）
  - `python3 tools/check_ipynb_py_sync.py --quiet` → 77/77 in sync，0 orphan，exit 0
  - `python3 tools/check_converted_py.py --quiet` → 77/77 OK，exit 0

#### 用法
```bash
# Orphan 偵測現在內建在 sync check 裡，不用獨立指令
python3 tools/check_ipynb_py_sync.py             # 含 orphan 偵測
python3 tools/check_ipynb_py_sync.py --quiet     # 只看 summary 行的 "Orphan .py: N"
```

#### 失敗時怎麼修
```bash
# Orphan 出現代表 .ipynb 不存在了。兩個選項：
# 1. 確實要刪這個 notebook → 刪掉 .py
git rm example/stale_orphan.py

# 2. notebook 被誤刪 → 從歷史救回
git checkout HEAD~1 -- example/SomeNotebook.ipynb
python3 tools/ipynb_to_py.py --files example/SomeNotebook.ipynb
```

### M10 — Unit tests for `check_converted_py.py`
- 為什麼補：toolchain 三支工具中，`check_converted_py.py`（py_compile + magic-leak validator）是 M8（converter）與 M9（sync checker）之後唯一還沒有 unit test 的。CI 對全 77 個 notebook 做 smoke test 雖然能擋大規模回歸，但 helper 級別的行為改動沒有快速回饋；未來若改 `MAGIC_RE` 規則或 truncate 長度，沒有 unit test 容易整批失靈
- 新增 `tools/tests/test_check_converted_py.py`（純 stdlib `unittest`，0 額外依賴），31 個 case 分五組：
  - **`MagicRegexTests`（6 cases）** — pin `MAGIC_RE` 接受 `!` / `%` / `%%` / `?` 且拒絕 `# !` / 純程式碼 / 空字串
  - **`PairedPyFilesTests`（7 cases）** — 空 tree、root 單檔、子目錄、`.ipynb_checkpoints` 過濾（含 nested）、`.py` 不存在仍配對、多檔 walk
  - **`CompileCheckTests`（6 cases）** — 合法檔回 None、空檔回 None、純註解回 None、syntax error 回字串、`!ls` / `%matplotlib` 因 syntax error 被擋
  - **`MagicCheckTests`（6 cases）** — 乾淨檔回 []、`# !ls` 不誤判、leaked bang 含 line number、`%` 與 `?` 同檔多行、`lstrip()` 後 indent magic 也被抓、長 line 截到 120 chars
  - **`MainTests`（6 cases）** — 空 root rc=1、全 pass rc=0、missing/compile/magic 任一觸發 rc=2、`--quiet` 抑制 per-file 行
- 整合 `_run()` helper 用 `redirect_stdout` / `redirect_stderr` 捕獲輸出，免污染 test runner
- 不需動 CI workflow：`.github/workflows/ipynb-py-sync.yml` 已經跑 `python3 -m unittest discover -s tools/tests`，新 test 自動被 pick up
- 本地驗證：
  - `python3 tools/tests/test_check_converted_py.py -v` → `Ran 31 tests OK`
  - `python3 -m unittest discover -s tools/tests` → `Ran 71 tests OK`（M8 31 + M9 9 + M10 31）
  - `python3 tools/check_ipynb_py_sync.py --quiet` → 77/77 in sync、0 orphan、exit 0
  - `python3 tools/check_converted_py.py --quiet` → 77/77 OK、exit 0

#### 用法
```bash
# 跑 M10 的 31 個 test
python3 tools/tests/test_check_converted_py.py
python3 tools/tests/test_check_converted_py.py -v

# 跑單一 test class
python3 -m unittest tools.tests.test_check_converted_py.MagicCheckTests
python3 -m unittest tools.tests.test_check_converted_py.MainTests
```

### M11 — Integration tests for the pre-commit hook
- 為什麼補：toolchain 四個元件中（converter / sync checker / converted-py validator / pre-commit hook），前三個在 M8/M9/M10 都有 unit test，只剩 bash 寫的 `tools/hooks/pre-commit` + `tools/hooks/install.sh` 完全沒測過。M5 結尾只有手動跑 `Aroon.ipynb` 的 end-to-end smoke。未來要動 hook 的 filter / `set -euo pipefail` / `--diff-filter` flags，沒有快速回饋
- 新增 `tools/tests/test_pre_commit_hook.py`（純 stdlib `unittest` + `subprocess` + `tempfile`，0 額外依賴），12 個 case 分兩組：
  - **`HookBehaviourTests`（9 cases）** — 每個 test 在自有 temp git repo 跑：
    - 把 `tools/hooks/pre-commit`、`tools/hooks/install.sh`、`tools/ipynb_to_py.py` 複製進 temp repo
    - 用 `os.symlink('../../tools/hooks/pre-commit', '.git/hooks/pre-commit')` 安裝（與 `install.sh` 同一形式）
    - 透過 `subprocess.run(['git', 'commit', ...])` 觸發 hook，再驗證 `.py` 是否被產生 + 進 commit
    - 涵蓋：無 ipynb staged（passthrough）/ 新增 ipynb / 修改 ipynb / 刪除 ipynb（不該觸發）/ `.ipynb_checkpoints/` 被過濾 / 多檔批次 / `git mv` rename / rename 留下 orphan `.py`（已知限制 lock 進 test）/ HEADER + cell marker end-to-end
  - **`InstallShTests`（3 cases）** — 直接跑 `./tools/hooks/install.sh`：
    - Fresh install → `.git/hooks/pre-commit` 是 symlink、target 為相對路徑 `../../tools/hooks/pre-commit`
    - 重跑 idempotent → 無 backup 檔產生
    - Pre-existing 非 symlink hook → 備份到 `pre-commit.backup.<epoch>` 後安裝 symlink
- **測試挖到的真實 bug + 順手修掉**：原 hook filter `grep -v '/\.ipynb_checkpoints/'` 要求 `.ipynb_checkpoints/` 在子目錄裡才會被過濾；root-level（例如 Jupyter 在 repo 根目錄開 `Aroon.ipynb` 後產生的 `.ipynb_checkpoints/Aroon-checkpoint.ipynb`）會繞過 filter。改成 `grep -vE '(^|/)\.ipynb_checkpoints/'` 同時匹配兩種；`.ipynb_checkpoints/` 本來就在 `.gitignore` 內，這是 defense-in-depth 不是 hot path
- 為什麼用 subprocess 而非 mock：hook 是 bash 腳本，內部呼叫 `git diff` / `mapfile` / `python3` 多支真實工具；mock 任何一支都會讓 test 變得「測 mock 而不是測 hook」。每個 test 用 `tempfile.TemporaryDirectory()` 起新 git repo，慢一點（12 個 test 跑 0.5s）但對 hook 的真實行為有 byte-for-byte 保證
- 不需動 CI workflow：`.github/workflows/ipynb-py-sync.yml` 已經跑 `python3 -m unittest discover -s tools/tests`，新 test 自動 pick up
- 本地驗證：
  - `python3 tools/tests/test_pre_commit_hook.py -v` → `Ran 12 tests OK`
  - `python3 -m unittest discover -s tools/tests` → `Ran 83 tests OK`（M8 31 + M9 9 + M10 31 + M11 12）
  - `python3 tools/check_ipynb_py_sync.py --quiet` → 77/77 in sync、0 orphan、exit 0
  - `python3 tools/check_converted_py.py --quiet` → 77/77 OK、exit 0

#### 用法
```bash
# 跑 M11 的 12 個 hook 測試
python3 tools/tests/test_pre_commit_hook.py
python3 tools/tests/test_pre_commit_hook.py -v

# 跑單一 test class
python3 -m unittest tools.tests.test_pre_commit_hook.HookBehaviourTests
python3 -m unittest tools.tests.test_pre_commit_hook.InstallShTests
```

### M12 — Hook 在 delete / rename 時自動清掉孤兒 `.py`
- 為什麼補：M11 的進度文末明確列了「`git mv old.ipynb new.ipynb` 之後 hook 不會刪 `old.py`，靠 M9 的 `_orphan_py()` 下游抓」這條已知限制。雖然 sync check 能在 CI 抓到，但需要使用者額外再跑一次 `python3 tools/check_ipynb_py_sync.py` 或等 CI 紅；hook 自己 close 這個 loop 比較對稱
- 改 `tools/hooks/pre-commit`：
  - 在原本 `--diff-filter=ACMR` 的 staged 清單之外，多收一份 `--no-renames --diff-filter=D` 的 removed 清單
  - `--no-renames` 強制 git 把 rename 拆成 D-old + A-new，所以 rename target 走 ACMR 路徑（→ 重生 new.py），rename source 走 D 路徑（→ 刪掉 old.py）；deletion 也走同一條 D 路徑
  - 對 removed 清單裡每個 `<nb>.ipynb`，跑 `git rm -f --ignore-unmatch --quiet -- "${nb%.ipynb}.py"`；`--ignore-unmatch` 讓「`.ipynb` 從未產生 `.py`」這種情境靜默不噴錯
  - 為什麼用 `git rm` 而非 `rm -- $py && git add -u`：`git rm` 同時處理 index + working tree，且對「.py 沒被 tracked」的情況 `--ignore-unmatch` 是官方支援的旁路
- 改 `tools/tests/test_pre_commit_hook.py`：
  - 翻轉 `test_deleted_ipynb_does_not_invoke_converter` → 新名 `test_deleted_ipynb_also_removes_py_sibling`，驗證使用者只 stage `.ipynb` 刪除時 `.py` 也跟著消失（hook 自己處理）
  - 翻轉 `test_rename_does_not_clean_up_old_py` → 新名 `test_rename_cleans_up_old_py`，驗證 `git mv old.ipynb new.ipynb` 後 `old.py` 不存在、`new.py` 自動生成
  - 補新 case `test_deleted_ipynb_without_existing_py_is_silent`：先 `git rm orphan.py` 把 `.py` 拿掉再 commit `.ipynb` 刪除，確認 hook 在沒有 sibling 可刪時不噴 error code（`--ignore-unmatch` 的保險）
- 沒動的東西：converter / sync checker / `_orphan_py()` 全部沒改。`_orphan_py()` 仍是 CI 端的雙保險，捕捉「使用者沒裝 hook 也沒清 .py」的情境
- 為什麼這條限制這次值得處理：M11 列為「known limitation」+「locked into test」就是技術債的訊號；現在三個 toolchain 元件對 rename 的處理是非對稱的（converter 處理 staged ACMR、sync checker 報 orphan、hook 只前向），統一成 hook 雙向後行為更可預期
- 本地驗證：
  - `python3 tools/tests/test_pre_commit_hook.py -v` → `Ran 13 tests OK`
  - `python3 -m unittest discover -s tools/tests` → `Ran 84 tests OK`（M8 31 + M9 9 + M10 31 + M11→M12 13）
  - `python3 tools/check_ipynb_py_sync.py --quiet` → 77/77 in sync、0 orphan、exit 0
  - `python3 tools/check_converted_py.py --quiet` → 77/77 OK、exit 0

#### 用法
- 安裝後一切照舊：`tools/hooks/install.sh` 不用重跑（symlink 內容沒變）。下次 commit 時若有 `.ipynb` 被刪 / rename，hook 會多印一行
  ```
  [ipynb->py hook] removing .py sibling for N deleted/renamed notebook(s)...
  ```
- 想看 hook 真實行為差異：在 dev branch 跑
  ```bash
  git mv example/SomeNotebook.ipynb example/SomeNotebook_v2.ipynb
  git commit -m 'rename'
  # → 應該看到 .py sibling 也被改名、不留 orphan
  python3 tools/check_ipynb_py_sync.py --quiet  # 應顯示 0 orphan
  ```

### M13 — Unit tests for `ipynb_to_py.main()` CLI entry point
- 為什麼補：M8/M9/M10 都把對應工具的 `main()` 行為 lock 進 test，唯獨 M8 漏掉了 `ipynb_to_py.py` 自己的 `main()`。converter 是整條 toolchain 的源頭，CLI 行為（root-walk vs `--files` vs `--dry-run` vs 各種 error path）若回歸，下游所有檢查與 hook 都會跟著炸。這個缺口比想像中明顯，且補完後四支工具（converter / sync checker / converted-py validator / pre-commit hook）main() 級覆蓋一致。
- 小重構 `tools/ipynb_to_py.py`：`main()` 簽名從 `main() -> int` 改成 `main(argv: list[str] | None = None) -> int`，`ap.parse_args()` → `ap.parse_args(argv)`。argparse 對 `parse_args(None)` 預設取 `sys.argv[1:]`，所以 CLI 對外行為零變化；唯一目的是讓 unit test 可以直接傳 `argv` list 而不用 monkey-patch `sys.argv`。同時跟 M9 的 `check_ipynb_py_sync.main(argv)` 與 M10 的 `check_converted_py.main(argv)` 對齊。
- 在 `tools/tests/test_ipynb_to_py.py` 新增 `MainTests` class，12 個 case 用 `tempfile.TemporaryDirectory()` + `os.chdir()` 隔離（避免汙染 cwd），透過 `redirect_stdout` / `redirect_stderr` 捕獲輸出：
  - **Root-walk 模式（4 cases）** — 空 root → rc=1 + stderr `No .ipynb under`；nested notebooks 都轉成功 + summary 正確；root-level `.ipynb_checkpoints/` 完全跳過；nested `.ipynb_checkpoints/` 跳過但旁邊真 notebook 仍轉
  - **--files 模式（5 cases）** — 單檔成功；多檔成功；不存在的 path → rc=1 + ERR；非 `.ipynb` 副檔名 → rc=1 + ERR；mixed valid+invalid → rc=1 且**所有**檔案都不轉（atomic-ish guard，由 main 先驗證再 convert）
  - **--dry-run（2 cases）** — root-walk 與 --files 都不寫檔；stdout 有 `[dry]` 標記與 `Converted 0/N notebooks.` summary
  - **Malformed JSON（1 case）** — `Bad.ipynb` 是壞 JSON、`Good.ipynb` 正常：rc=0、stderr 報 `ERR Bad.ipynb`、`Good.py` 仍生成、stdout `Converted 1/2`。Lock 進 test 的行為：per-file `try/except` 寬鬆 — 一個壞 notebook 不會中斷整個 batch
- 不需動 CI workflow：`.github/workflows/ipynb-py-sync.yml` 已經跑 `python3 -m unittest discover -s tools/tests`，12 個新 test 自動 pick up
- 本地驗證：
  - `python3 tools/tests/test_ipynb_to_py.py -v` → `Ran 43 tests OK`（原 31 + M13 12）
  - `python3 -m unittest discover -s tools/tests` → `Ran 96 tests OK`（M8 31+12 + M9 9 + M10 31 + M11→M12 13）
  - `python3 tools/check_ipynb_py_sync.py --quiet` → 77/77 in sync、0 orphan、exit 0
  - `python3 tools/check_converted_py.py --quiet` → 77/77 OK、exit 0

#### 用法
```bash
# 只跑 M13 新增的 MainTests class
python3 -m unittest tools.tests.test_ipynb_to_py.MainTests
python3 -m unittest tools.tests.test_ipynb_to_py.MainTests -v
```

#### 副作用 / 注意
- `MainTests.setUp` 會 `os.chdir(temp_root)` 並在 `tearDown` 還原；若日後改成平行 test runner（unittest 預設 sequential 不受影響），需要把 chdir 改成 `subprocess` 隔離
- `test_malformed_notebook_reported_but_does_not_abort` 把「main() 對壞 ipynb 寬鬆」這個行為 lock 進來；若日後想改成 strict（壞檔讓整個 batch 失敗 + rc=1），要同步翻轉這個 test 並加 `--strict` flag

### M14 — Unit tests for `check_ipynb_py_sync.main()` + `_pairs` / `_diff_preview`
- 為什麼補：四支 CLI 工具裡，converter（M13 `MainTests`）與 converted-py validator（M10 `MainTests`）都已把 `main()` 行為 lock 進 test，連 sync checker 的 `_orphan_py()` helper 也在 M9 補過；唯獨 sync checker 自己的 `main()` 從沒被 unit 測過。`test_check_ipynb_py_sync.py` 的舊 docstring 甚至直接寫明「in-sync / drift / missing paths 只靠 CI 對真實 77 對 notebook 做 end-to-end」——這正是技術債訊號：helper 級重構（改 summary 措辭、改 diff truncation 長度、改 exit code 對應）沒有快速回饋。M14 把這條補上，sync checker 達到與其餘三支工具一致的 main() 級覆蓋
- 在 `tools/tests/test_check_ipynb_py_sync.py` 新增 3 個 test class，19 個 case（原 9 個 `OrphanPyTests` 全部保留，檔案總計 28 個 test）：
  - **`PairsTests`（7 cases）** — 空 tree → []；root 單檔配對 `.py` suffix；nested notebook 配對；root-level `.ipynb_checkpoints/` 過濾；nested `.ipynb_checkpoints/` 過濾；`.py` 不存在仍配對（missing 由 main 另報）；多檔 `sorted()` 順序
  - **`DiffPreviewTests`（4 cases）** — 相同輸入 → 空字串（`difflib` 無差異）；有差異時 from/to label（`(on disk)` / `(expected from .ipynb)`）都在；`+expected` / `-actual` 標記都在；超過 `max_lines` 時出現 `more diff lines truncated` 且總行數被截到 ≤ max_lines+1
  - **`MainTests`（8 cases）** — 空 tree → rc=1 + stderr `No .ipynb files`；全 in-sync → rc=0 + `In sync: 2`；missing `.py` → rc=2 + `MISSING:`；drift → rc=2 + `DRIFT:` + diff body（含 `(on disk)`）；`--no-diff` drift → rc=2 + `DRIFT:` 但**無** diff body；orphan `.py` → rc=2 + `ORPHAN:`；malformed `.ipynb` + 既有 `.py` → 走 `convert_to_str` 例外路徑 → rc=2 + `ERROR:`；`--quiet` 抑制 per-file 行但保留 summary 計數
- 設計細節：
  - 新增 `_synced_pair(path)` helper — 用 `convert_to_str(nb)` 寫出 byte-for-byte 相符的 `.py`，這樣 in-sync 測試不會因 converter 規則微調而假性 drift（測試與真實轉換邏輯同源，避免硬編 expected 字串）
  - summary 計數斷言全用 `assertRegex(stdout, r'In sync:\s+2')` 這類 **regex + `\s+`**，刻意不硬編空白數 — 與 M10 `MainTests` 硬編 `'OK:                  2'` 不同，對日後調整欄位對齊較不脆弱（見「已知限制」對照）
  - drift 測試靠「先 `_synced_pair` 再 append 一行」製造，最小化噪音；`--no-diff` 用「`(on disk)` 不在 stdout」反向驗證 diff body 被抑制
  - `_run(*argv)` helper 沿用 M10/M13 的 `redirect_stdout` / `redirect_stderr` + `io.StringIO()` 模式捕獲輸出，免污染 test runner；**不需** `os.chdir()`（main 接受 root 位置參數，直接傳 temp dir）所以沒有 M13 的 cwd 隔離副作用
- 不需動 production code：`check_ipynb_py_sync.py` 完全沒改（M9 已把 `main(argv)` 簽名就緒）。純測試新增
- 不需動 CI workflow：`.github/workflows/ipynb-py-sync.yml` 已跑 `python3 -m unittest discover -s tools/tests`，19 個新 test 自動 pick up
- 本地驗證：
  - `python3 tools/tests/test_check_ipynb_py_sync.py -v` → `Ran 28 tests OK`（原 9 + M14 19）
  - `python3 -m unittest discover -s tools/tests` → `Ran 115 tests OK`（M8 31+12 + M9 9+19 + M10 31 + M11→M12 13）
  - `python3 tools/check_ipynb_py_sync.py --quiet` → 77/77 in sync、0 orphan、exit 0
  - `python3 tools/check_converted_py.py --quiet` → 77/77 OK、exit 0

#### 用法
```bash
# 只跑 M14 新增的 class
python3 -m unittest tools.tests.test_check_ipynb_py_sync.PairsTests
python3 -m unittest tools.tests.test_check_ipynb_py_sync.DiffPreviewTests
python3 -m unittest tools.tests.test_check_ipynb_py_sync.MainTests -v
```

### M15 — `--strict` flag 對壞 notebook 硬失敗
- 為什麼補：M13 進度日誌結尾明確標 follow-up — `test_malformed_notebook_reported_but_does_not_abort` 把「main() 對壞 ipynb 寬鬆」這個行為 lock 進來，但同時留了「日後想改成 strict（壞檔讓整個 batch 失敗 + rc=1），要同步翻轉這個 test 並加 `--strict` flag」的伏筆。CI 端目前發現壞 notebook 時不會紅；要讓 CI 自動擋下「commit 進來的 .ipynb 變成 corrupted JSON」這種真實情境，需要一個能在 main 跑完後彙整失敗的 strict 旗標
- 修改 `tools/ipynb_to_py.py`：
  - argparse 加 `--strict` flag（help 寫明 default 行為）
  - main loop 增 `failures` 計數，每次 per-file exception 進 except 區塊時 +1（既有 `ERR <rel>: <msg>` 印 stderr 行為不變）
  - 跑完最後判斷 `if args.strict and failures: ... return 1`，並印一行 `[strict] N notebook(s) failed to convert.` 到 stderr 作為摘要訊號
  - 模組 docstring 補一段解釋預設寬鬆 vs `--strict` 的差別，讓 `python3 tools/ipynb_to_py.py --help` 與 source 讀者都看得到
- 設計決策（try-all vs fail-fast）：strict 模式仍 try-all 所有 notebook 後才 return 1，**不**在第一個錯誤就 break。理由：CI 第一次跑就要看到所有壞檔（典型情境：merge conflict 同時破壞多個 notebook）；fail-fast 會讓使用者反覆 push 直到全部修好，比較痛
- 鎖住預設寬鬆：原 `test_malformed_notebook_reported_but_does_not_abort` 保留不動（沒翻轉），確認沒帶 `--strict` 時行為與 M13 完全一致；hook（M5/M11/M12）也不需要改，因為它呼叫 converter 時沒有自動加 `--strict`，預設行為對 hook 是更安全的
- 在 `tools/tests/test_ipynb_to_py.py` 的 `MainTests` 補 4 個 case：
  - **`test_strict_mode_passes_when_all_notebooks_convert`** — `--strict` + 兩個乾淨 notebook → rc=0、兩個 .py 都生成、stderr **沒有** `[strict]` 摘要（負向斷言保證 success path 不錯誤觸發）
  - **`test_strict_mode_fails_on_malformed_notebook`** — `--strict` + Bad.ipynb + Good.ipynb → rc=1、stderr 同時含 `ERR Bad.ipynb` 與 `[strict]` 摘要、**Good.py 仍生成**（try-all 設計被鎖進 test）、`Converted 1/2 notebooks.` 摘要也在 stdout
  - **`test_strict_mode_files_mode_fails_on_malformed`** — `--strict --files Good.ipynb Bad.ipynb`：rc=1、Good.py 仍生成。確認 strict 在 `--files` 模式下對「pre-existing 通過 path validation、convert 時才壞」一樣 work
  - **`test_strict_mode_dry_run_does_not_fail`** — `--strict --dry-run` + 一個壞 notebook 一個好的：rc=0、無 `.py` 寫出。明確 lock：strict 只擋住真實 conversion failure，不擋住「pre-existing 壞 notebook 的存在」（dry-run 沒嘗試 convert 所以也不算失敗）。這條對 CI 用法很重要：未來若有人想在 PR check 跑 `--strict --dry-run` 預掃壞檔，會發現要改成不帶 `--dry-run` 才能擋
- 不需動 production code 以外的東西：sync checker / converted-py validator / pre-commit hook 全部維持原樣。`--strict` 是純粹 opt-in 旗標，預設模式仍對 hook、CI workflow 透明
- 不需動 CI workflow：要在 CI 啟用此 strict 守門，未來把 `.github/workflows/ipynb-py-sync.yml` 裡的 `python3 tools/ipynb_to_py.py` step 加 `--strict` 即可（這次刻意不順手改 workflow，避免把 production gate 變動與 feature flag 兩件事綁在一起）
- 本地驗證：
  - `python3 tools/tests/test_ipynb_to_py.py -v` → `Ran 47 tests OK`（M8 31 + M13 12 + M15 4）
  - `python3 -m unittest discover -s tools/tests` → `Ran 119 tests OK`（M8 31+12+4 + M9 9+19 + M10 31 + M11→M12 13）
  - `python3 tools/check_ipynb_py_sync.py --quiet` → 77/77 in sync、0 orphan、exit 0
  - `python3 tools/check_converted_py.py --quiet` → 77/77 OK、exit 0
  - CLI smoke：`/tmp/strict-smoke` 起 1 個壞 1 個好 → 預設 rc=0、加 `--strict` rc=1 + `[strict] 1 notebook(s) failed`，Good.py 兩種模式下都生成

#### 用法
```bash
# 預設寬鬆（與 M13 行為一致）
python3 tools/ipynb_to_py.py .

# CI 想擋壞 notebook 時加 --strict
python3 tools/ipynb_to_py.py --strict .

# --files 模式也支援 strict
python3 tools/ipynb_to_py.py --strict --files Aroon.ipynb example/foo.ipynb

# 只跑 M15 新增的 strict 測試
python3 -m unittest tools.tests.test_ipynb_to_py.MainTests.test_strict_mode_fails_on_malformed_notebook -v
```

#### 未來想擴大 strict 範圍時的 hook 點
- ~~CI 在 sync check **之前**先跑一輪 `python3 tools/ipynb_to_py.py --strict --dry-run .` 是無效的（dry-run 不 convert 所以不會錯）；要擋壞檔得拿掉 `--dry-run` 並對 working tree 寫入 .py~~ — **M16 已關掉**：dry-run 分支現在會 `convert_to_str()`（parse 但不寫檔），所以 `--strict --dry-run` 變成有效、零副作用的 pre-scan，已接進 CI workflow
- 若要把 strict 對齊到 sync checker 端 fail-fast（sync checker 目前已對 malformed 回 ERROR + rc=2），可以考慮把兩個工具的 exit code 統一成 1=usage / 2=任何錯誤，而非現在 converter 用 1 / sync checker 用 2 的不對稱；不在這次處理範圍

### M16 — `--dry-run` 驗證 parseability + CI strict pre-scan gate
- 為什麼補：M15 在 `test_strict_mode_dry_run_does_not_fail` 與「未來想擴大 strict 範圍時的 hook 點」明確 lock 了一條限制——`--strict --dry-run` 擋不到壞檔，因為 dry-run 分支在 `convert(nb, py)` / `convert_to_str()` 之前就 `continue`，根本沒讀 notebook JSON。這正是 M11→M12 同款的「技術債訊號」（限制被 lock 進 test）。M16 依同一 precedent 關掉它：讓 dry-run 仍 parse、但不寫檔
- 改 `tools/ipynb_to_py.py` 的 dry-run 分支：印完 `[dry] {rel} -> {rel_py}` 後多跑 `convert_to_str(nb)`（丟棄回傳值，不落地）。parse 失敗就跟 convert 失敗走同一條路：`failures += 1` + `ERR {rel}: {e}` 印 stderr。`converted` 在 dry-run 仍維持 0（summary 永遠 `Converted 0/N`）
- 設計取捨（為什麼 dry-run 也報 ERR 而非完全靜默）：plain dry-run 現在對壞檔會印 ERR 到 stderr，但 **rc 仍 0**（沿用 M13/M15 的預設寬鬆）；只有加 `--strict` 才把 `failures` 翻成 rc=1。這樣 dry-run 同時是「列出將寫哪些 `.py`」與「驗證所有 notebook parse 得了」兩用途，且預設仍不會擋人
- 模組 docstring 補一段解釋 dry-run 現在會 parse、`--strict --dry-run` 是最便宜的 CI 壞檔守門
- CI：`.github/workflows/ipynb-py-sync.yml` 在「unit tests」之後、「sync check」之前插一步 `python3 tools/ipynb_to_py.py --strict --dry-run .`。這是 M15 文末承諾、但當時做不到的 CI strict gate——現在 dry-run 會 parse 才真正有意義。放在 sync/compile 前是因為它最便宜（不寫 77 個 `.py`、不做 byte-for-byte 比對），壞檔能在最便宜的層級先紅（對齊 M8 把 unit test 擺最前的理由）
  - 與既有守門的關係：sync checker 對「malformed + 既有 `.py`」本來就回 ERROR + rc=2（M14 測過），所以這步是 belt-and-suspenders；它真正的獨立價值是 **本地開發**能用一條快指令驗證全 repo notebook parse 得了，不必重生整棵 `.py`
- 測試（`tools/tests/test_ipynb_to_py.py` 的 `MainTests`，net +2 → 121 tests）：
  - **翻轉** `test_strict_mode_dry_run_does_not_fail` → `test_strict_mode_dry_run_fails_on_malformed`：`--strict --dry-run` + Bad + Good → rc=1、stderr 含 `ERR Bad.ipynb` + `[strict]`、**Bad.py / Good.py 都不存在**（dry-run 零落地）、stdout `Converted 0/2`
  - **新增** `test_strict_mode_dry_run_passes_on_clean`：`--strict --dry-run` + 兩個乾淨 notebook → rc=0、無檔案寫出、stderr **無** `[strict]`（success path 不誤觸）
  - **新增** `test_dry_run_reports_malformed_without_strict`：plain `--dry-run` + Bad + Good → rc=0（仍寬鬆）、stderr 仍報 `ERR Bad.ipynb`、無 `[strict]`、無檔案寫出。鎖住「dry-run 報告但不強制」的對稱性
- 沒動的東西：`convert_to_str` / `convert` / sync checker / converted-py validator / pre-commit hook 全部沒改。hook 呼叫 converter 時不帶 `--strict`/`--dry-run`，行為完全不變
- 本地驗證：
  - `python3 -m unittest discover -s tools/tests` → `Ran 121 tests OK`（M15 的 119 → 翻 1 補 2）
  - `python3 tools/check_ipynb_py_sync.py --quiet` → 77/77 in sync、0 orphan、exit 0
  - `python3 tools/check_converted_py.py --quiet` → 77/77 OK、exit 0
  - CLI smoke（temp dir，1 壞 1 好）：plain `--dry-run` rc=0、`--strict --dry-run` rc=1 + `[strict] 1 notebook(s) failed`，**兩種模式都不寫 `.py`**
  - 真 repo `python3 tools/ipynb_to_py.py --strict --dry-run .` → rc=0（CI gate 在乾淨 repo 通過）

#### 用法
```bash
# 本地：一條快指令驗證全 repo notebook 都 parse 得了（不寫任何 .py）
python3 tools/ipynb_to_py.py --strict --dry-run .

# 只跑 M16 新增/翻轉的 test
python3 -m unittest tools.tests.test_ipynb_to_py.MainTests.test_strict_mode_dry_run_fails_on_malformed -v
```

### M17 — Aggregate local runner `tools/check_all.py`
- 為什麼補：toolchain 到 M16 已是 4 支工具（converter / sync checker / converted-py validator / pre-commit hook）+ CI 4 道 gate（unit tests → strict pre-scan → sync → converted）。但「在 push 前本地重現 CI」這件事一直沒有單一入口：開發者要嘛逐條背 4 個指令，要嘛去讀 `.github/workflows/ipynb-py-sync.yml` 才知道 CI 到底跑了什麼。這是最後一個明顯的 UX 缺口——local 與 CI 之間沒有 single source of truth
- 新增 `tools/check_all.py`（純 stdlib，0 額外依賴），step-for-step 對齊 workflow：
  1. `python3 -m unittest discover -s tools/tests`
  2. `python3 tools/ipynb_to_py.py --strict --dry-run <root>`
  3. `python3 tools/check_ipynb_py_sync.py <root>`
  4. `python3 tools/check_converted_py.py <root>`
  - 每支子工具用 `sys.executable` 起 subprocess（用同一個 Python，不會跨 interpreter）
  - 子工具的 root 走 positional 參數（unittest 步驟例外：它是 repo-global，永遠 discover `tools/tests`）
  - `--quiet` 只 plumb 給兩支 checker（converter 沒有 `--quiet`，strict pre-scan 不加）
  - `--skip-tests` 跳過 unittest 步驟（快速 wiring 檢查；integration smoke 也靠它避免在 test 內遞迴重跑整套）
- 設計取捨：
  - **try-all 不 fail-fast**：沿用 M15 strict 的理由——一次 invocation 要列出所有壞掉的 step，而不是修一個才看到下一個。rc=0 iff 全綠，否則 rc=1
  - **不把 CI 改成呼叫 `check_all.py`**：CI 維持逐 step 展開，保留 GitHub 對每個 step 的獨立 annotation 與失敗定位；`check_all.py` 是 local 便利層、鏡像 CI，不是 CI 的實作。代價是兩邊要手動保持同步（見「已知限制」）
  - `build_steps(root, *, quiet, skip_tests)` 與 `run_steps(steps, run=...)` 拆成可測純函式 + 可注入 runner，`main(argv, run=...)` 也吃可注入 runner，所以絕大多數 test 不用真的 spawn subprocess
- 新增 `tools/tests/test_check_all.py`（18 cases，4 class）：
  - **`BuildStepsTests`（8）** — 4 步順序與 label、`--skip-tests` 降為 3 步、argv[0] 是 `sys.executable`、unittest 步驟 `-s` 指向真 `tools/tests`、pre-scan 帶 `--strict --dry-run`、root 透傳給 checker、`--quiet` 只上 checker 不上 pre-scan、預設無 `--quiet`
  - **`RunStepsTests`（3）** — 全跑回傳 labels、單步失敗仍跑完 4 步（no fail-fast lock 進 test）、step 順序保留
  - **`MainTests`（6）** — 全過 rc=0 + `All 4 step(s) passed.`、任一失敗 rc=1 + 列出失敗 step、多重失敗計數、`--skip-tests` 走 3 步、`--quiet` plumb 進 checker、progress header `[1/4]`/`[4/4]`
  - **`IntegrationTests`（1）** — `main(['--skip-tests', '--quiet', <repo>])` 對真 repo 跑 steps 2-4 → rc=0 + `All 3 step(s) passed.`。這是 nightly-safe 不變量：toolchain 對真實 77 個 notebook 仍全綠（刻意 `--skip-tests` 避免在 unittest 內遞迴重跑 121 個 test）
  - 用 `_RecordingRunner`（substring→rc 的 fake）+ `redirect_stdout` 捕獲輸出，免污染 test runner
- 不需動 production code 以外的東西：4 支既有工具、hook、workflow 全部沒改。`check_all.py` 是純新增
- 本地驗證：
  - `python3 tools/tests/test_check_all.py -v` → `Ran 18 tests OK`
  - `python3 -m unittest discover -s tools/tests` → `Ran 139 tests OK`（M16 的 121 + M17 18）
  - `python3 tools/check_all.py --quiet` → 4/4 step 全 PASS、rc=0
  - `python3 tools/check_ipynb_py_sync.py --quiet` → 77/77 in sync、0 orphan、exit 0
  - `python3 tools/check_converted_py.py --quiet` → 77/77 OK、exit 0

#### 用法
```bash
# push 前一條指令重現 CI
python3 tools/check_all.py

# checker 只印 summary（converter 的 [dry] 逐檔行仍會印——它沒有 --quiet）
python3 tools/check_all.py --quiet

# 跳過 unittest 步驟（純驗證 .py 同步 / 可編譯）
python3 tools/check_all.py --skip-tests

# 只跑 M17 的 test
python3 -m unittest tools.tests.test_check_all
```

#### 已知限制 / 注意
- `check_all.py` 的步驟清單是**手動**鏡像 `ipynb-py-sync.yml`；若日後在 workflow 加 / 改 step，要記得同步改 `build_steps()`（兩邊沒有自動連動）。`IntegrationTests` 只保證 steps 2-4 對真 repo 綠，不保證與 workflow 逐字一致
- strict pre-scan 步驟會印 77 行 `[dry] ...`（converter 既有行為、沒有 `--quiet`）；`check_all --quiet` 壓不掉這段，只壓 checker 的 per-file 行

## Fallback 指引

若要回退：
```bash
# 刪掉所有產生的 .py（保留原 ipynb 與工具）
find . -name "*.py" -not -path "./tools/*" -newer tools/ipynb_to_py.py -delete
```

若要重跑：
```bash
python3 tools/ipynb_to_py.py .
```

若要只轉某個子目錄：
```bash
python3 tools/ipynb_to_py.py lecture
```

若要解除 pre-commit hook：
```bash
rm .git/hooks/pre-commit
```

若要關掉 CI sync check：
```bash
rm .github/workflows/ipynb-py-sync.yml
# 或在 workflow 中加 `if: false` 暫停（commit 進去再 push）
```

若要讓 GitHub 重新把生成 `.py` 算進語言統計 / 展開 PR diff：
```bash
rm .gitattributes
# 或只刪掉 *.py 那兩行
```

若要拔掉 unit tests：
```bash
rm -r tools/tests
# 並把 .github/workflows/ipynb-py-sync.yml 的 "Run unit tests" step 刪掉
```

若要關掉 orphan `.py` 偵測：
```bash
# 還原 tools/check_ipynb_py_sync.py 到 M8 版本
git revert <M9-commit-sha>
# 或手動拔掉 _orphan_py() / summary 中 "Orphan .py" 那行
```

若要拔掉 hook integration test：
```bash
rm tools/tests/test_pre_commit_hook.py
# CI workflow 不需動（discover 模式自動少抓 13 個 test）
```

若要還原 M12 的 hook 雙向同步（讓 hook 只前向、rename / delete 後 .py 變 orphan）：
```bash
# 拔掉 hook 裡的 removed 區塊與 git rm 迴圈
git revert <M12-commit-sha>
# 同步把 hook test 兩個被翻轉的 case 改回（test_deleted_ipynb_does_not_invoke_converter / test_rename_does_not_clean_up_old_py）
```

若要還原 M13 的 `main(argv)` 簽名與 MainTests：
```bash
# 把 ipynb_to_py.main 改回 main() -> int + ap.parse_args() 即可（CLI 對外行為原本就一樣）
# 並從 test_ipynb_to_py.py 拔掉 MainTests class（其餘 31 個 helper test 不受影響）
git revert <M13-commit-sha>
```

若要拔掉 M14 的 sync-checker main() 測試：
```bash
# 只刪 M14 新增的三個 class，保留 M9 的 OrphanPyTests
git revert <M14-commit-sha>
# 或手動從 test_check_ipynb_py_sync.py 移除 PairsTests / DiffPreviewTests / MainTests
# （check_ipynb_py_sync.py production code 沒改，無需動）
```

若要拔掉 M17 的 aggregate runner：
```bash
rm tools/check_all.py tools/tests/test_check_all.py
# 4 支既有工具與 CI workflow 都沒被 M17 改動，無需還原；
# discover 模式自動少抓 18 個 test
```

## 已知限制 / 後續

- 沒處理 cell outputs（刻意丟掉，保持 .py 乾淨）
- magics 一律註解；若 `.py` 要直接執行（不是 import），自行把 `# !zipline ingest` 還原成 shell call
- Pre-commit hook 只看 staged 檔案；若 ipynb 被改但沒 `git add`，hook 不會跑（與 git 標準行為一致）
- Hook 是 opt-in（要跑 `tools/hooks/install.sh`）；M6 已補上 CI sync check 形成雙保險
- M6 的 workflow yaml 已 commit 進 repo，但要等到首次 `git push` 後 GitHub Actions 才會真正執行第一次（夜間 cron 不會 push）
- CI 採嚴格 byte-for-byte 比對；若日後改 `ipynb_to_py.py` 的 HEADER / CELL_SEP / sanitize 規則，要同步把全部 `.py` 重生並 commit，否則 CI 會紅
- `_sanitize_code` 的 trailing-newline 不對稱已 lock 進 M8 的 unit test（見 `test_trailing_newline_stripped_when_present`）。若要把它「修正」成 always-trailing-newline，必須同時 regen 全部 77 個 `.py` 並更新 test 預期
- M9 的 orphan 偵測 hard-codes 兩組目錄常量（`_SKIP_DIR_PARTS` / `_HANDWRITTEN_DIR_PARTS`）。若日後在 `tools/` 以外另起手寫 Python 模組（例如 `scripts/` 或 `src/`），要記得加進 `_HANDWRITTEN_DIR_PARTS`，否則會被誤判為 orphan
- M10 的 `MainTests` 直接依賴 `main()` 內 summary 字串格式（`'OK:                  2'` / `'Missing .py sibling: 1'`）。若改 print 對齊空白數或欄位措辭，會同時打到這幾個 test，記得一起更新
- M11 的 hook test 用真實 `git commit` 驅動 subprocess，所以對 git CLI 行為有依賴（特別是 `git diff --cached --name-only --diff-filter=ACMR -z` 對 rename 的處理）。若日後升級 git 主版本（不太可能改這個 contract），rename 測試可能要重看
- ~~M11 已知 lock 進 test 的限制：hook 在 `git mv old.ipynb new.ipynb` 後不會刪除 `old.py`（單向同步）~~ — **M12 已關掉**：hook 現在同時收 ACMR（regenerate）與 `--no-renames -D`（remove），rename / delete 都會清掉 sibling `.py`。M9 的 `_orphan_py()` 仍作為 CI 端 fallback，捕捉「沒裝 hook」的情境
- M11 修掉的小 bug：`tools/hooks/pre-commit` 的 `.ipynb_checkpoints/` filter 原本沒匹配 root-level（例如 `.ipynb_checkpoints/Aroon-checkpoint.ipynb`），已改為 `(^|/)\.ipynb_checkpoints/`。實務上這個目錄已在 `.gitignore`，所以是 defense-in-depth
- M13 的 `MainTests` 用 `os.chdir(temp_root)` 隔離 cwd。若日後 CI 改用平行 test runner（如 pytest-xdist），這些 test 會互踩 — 要重寫成 subprocess 隔離或加 `setUpClass` 級鎖
- M13 把「main() 對單一 malformed `.ipynb` 寬鬆繼續」的行為 lock 進 `test_malformed_notebook_reported_but_does_not_abort`。若日後想改成「壞檔即整批失敗 + rc=1」，要同步翻轉這個 test 並加 `--strict` flag
- M14 的 `MainTests` 刻意用 `assertRegex(..., r'In sync:\s+2')` 而非硬編空白數，所以調 summary 欄位對齊不會打到它；但仍依賴 label 文字（`In sync:` / `Missing .py sibling:` / `Conversion errors:` / `Orphan .py (no .ipynb):`）與 per-file 前綴（`MISSING:` / `DRIFT:` / `ERROR:` / `ORPHAN:`）。若改這些措辭，要一起更新。另外 `test_drift_no_diff_suppresses_diff_body` 用「`(on disk)` 字串是否出現」當作 diff body 的 proxy，若把 `_diff_preview` 的 fromfile label 改掉，這條 assertion 要跟著改

### M18 — CI parity drift guard for `check_all.py`
- 為什麼補：M17 的核心承諾是「`python3 tools/check_all.py` 一條指令 == CI」，做法是讓 `build_steps()` step-for-step 對齊 `.github/workflows/ipynb-py-sync.yml`。但這個對齊**只靠人記得**：任何人改 workflow yaml（加/刪/重排一個 step、把 `--strict` 拿掉、換掉某支 checker）卻忘了同步改 `check_all.py`，兩邊就 silently drift，「local == CI」保證失效卻沒人會發現——綠的本地 run 不再預測綠的 CI run。這正是 M9（orphan 偵測）/ M14（sync checker main paths）一再處理的「只靠慣例成立的不變量 → 用 test 鎖死」模式，M17 留下的最後一個未上鎖缺口。
- 解法：在 `tools/tests/test_check_all.py` 新增 `WorkflowParityTests`（6 cases）+ 兩個 module-level helper，**純 stdlib**（系統 Python 受 PEP 668 鎖，無 PyYAML）：
  - `_workflow_run_commands()` — line-scan workflow yaml，regex `^\s*run:\s*(\S.*?)\s*$` 抓出 ordered 的單行 `run:` 指令清單。刻意不做完整 YAML parse；改用 `test_no_multiline_run_blocks` 斷言沒有 `run: |` / `run: >` 多行 block，一旦有人改成多行就 fail loudly 要求更新 parser，而非 silently 讀成空指令
  - `_step_signature(tokens)` — 把一條指令的 token list 化約成 `(tool, frozenset(long_flags))` 契約：`tool` 是 `'unittest'` 或被呼叫的 `.py` basename；`long_flags` 是會改變行為的 `--` 旗標。**刻意 normalize 掉**：interpreter 名、script 的 path prefix（`tools/foo.py` vs 絕對路徑）、結尾 root arg（`.` / temp dir）、single-dash 旗標與其值（`-s tools/tests`）、display-only `-v`。剩下的就是 CI 與 check_all 必須一致的最小契約
  - 6 個 case：`test_workflow_file_exists`、`test_no_multiline_run_blocks`（守 parser 假設）、`test_run_step_count_matches_build_steps`（4 == 4）、`test_step_signatures_match_in_order`（**核心 drift guard**：ordered 比對 workflow sigs vs `build_steps('.')` sigs，失敗訊息直接叫人「兩邊一起改」）、`test_tools_invoked_in_expected_order`（unittest → ipynb_to_py → sync → converted）、`test_strict_dry_run_gate_present_in_both`（M16 的 strict pre-scan gate 兩邊都在且一致）
- 為什麼 yaml 解析放 test 而非 production：M9/M14 是把 helper 加進 production 再測；但「讓 check_all.py runtime 讀自己的 CI yaml」會引入不必要的耦合（production 工具不該依賴 CI 設定檔存在）。drift guard 本質是 test-only concern，放 test 最乾淨
- normalize 的取捨：signature 容忍 `-v`（CI 要 verbose log）、root arg（CI checker 省略走 cwd 預設、check_all 明確傳 `.`）、abs vs rel path、`--quiet`（check_all-only 便利旗標）。這對「cosmetic 差異」不脆弱，但會抓到「meaningful 契約漂移」：step 加/刪/重排、`--strict`/`--dry-run` 掉一個、checker 被換掉
- 不動 production code：`check_all.py`、converter、兩支 checker、hook 全部沒改。純測試新增
- 不需動 CI workflow：`.github/workflows/ipynb-py-sync.yml` 已跑 `python3 -m unittest discover -s tools/tests`，6 個新 test 自動 pick up——而且這 6 個 test 守的正是這支 workflow 自己
- 負向驗證（確認 guard 真的會咬）：暫時把 workflow 的 `--strict --dry-run .` 改成 `--dry-run .` → `test_step_signatures_match_in_order` FAIL 並印出修復指引；`git checkout` 還原後 → OK
- 本地驗證：
  - `python3 -m unittest tools.tests.test_check_all.WorkflowParityTests -v` → `Ran 6 tests OK`
  - `python3 tools/tests/test_check_all.py` → `Ran 24 tests OK`（M17 18 + M18 6）
  - `python3 -m unittest discover -s tools/tests` → `Ran 145 tests OK`（M8 31+12+4 + M9 9+19 + M10 31 + M11→M12 13 + M17 18+6）
  - `python3 tools/check_all.py --quiet` → 4 steps 全 PASS、exit 0

#### 用法
```bash
# 只跑 M18 新增的 parity class
python3 -m unittest tools.tests.test_check_all.WorkflowParityTests
python3 -m unittest tools.tests.test_check_all.WorkflowParityTests -v
```

#### 副作用 / 注意
- `_workflow_run_commands()` 假設每個 `run:` 是單行 scalar。若日後 workflow 改用 `run: |` 多行 block，`test_no_multiline_run_blocks` 會先紅，提醒改寫 parser（不會 silently 漏判）
- signature normalize 掉 `-v` 與 root arg 等 cosmetic 差異。若未來想讓 CI 與 check_all 在這些面向也嚴格一致（例如強制 root arg 一致），要放寬 `_step_signature` 的容忍範圍並同步調整兩邊
- 這條 guard 只比對 `ipynb-py-sync.yml` 與 `check_all.py`；若日後新增第二支 workflow 或第二個 aggregate runner，要另外擴充

### M19 — `.gitattributes` ↔ sync-checker hand-written-dir parity guard
- 為什麼補：M18 把「`check_all.py` step-for-step 對齊 CI workflow」這個只靠慣例成立的不變量鎖進 test，但 toolchain 裡還剩**最後一條**同類缺口——「什麼算 hand-written Python」這個概念同時被寫死在兩個檔，卻沒有東西強制兩邊一致：
  - `.gitattributes`：`*.py linguist-generated=true` + `tools/**/*.py linguist-generated=false`（M7）——宣告 `tools/` 之下是手寫、其餘 `.py` 是生成
  - `tools/check_ipynb_py_sync.py`：`_HANDWRITTEN_DIR_PARTS = ('tools',)`（M9）——orphan 偵測把 `tools/` 視為手寫、豁免
  - 兩邊都在編碼同一個「手寫目錄集合」。一旦有人日後在 `tools/` 以外另起手寫 Python（例如 `scripts/` / `src/`），只改其中一邊：只加 `.gitattributes` override 卻忘了 `_HANDWRITTEN_DIR_PARTS` → 那個手寫 `.py` 會被 orphan 偵測誤判成孤兒（CI 紅）；反過來只加常量卻忘了 `.gitattributes` → GitHub 仍把它當生成檔收合 diff / 不計語言統計。這正是 M9 進度文「已知限制」早就標註的伏筆（「要記得加進 `_HANDWRITTEN_DIR_PARTS`，否則會被誤判為 orphan」），M19 把它從「靠記得」升級成「靠 test」。
- 解法：在 `tools/tests/test_check_ipynb_py_sync.py` 新增 `GitattributesParityTests`（6 cases）+ 兩個 module-level helper，**純 stdlib**（不依賴 PyYAML / 任何 gitattributes parser）：
  - `_gitattributes_lines()` — line-scan `.gitattributes`，跳過空行與 `#` 註解，把每行 split 成 `(pattern, {attrs})`
  - `_gitattributes_handwritten_dirs()` — 對每條帶 `linguist-generated=false` 的 pattern，用 `_HANDWRITTEN_OVERRIDE_RE`（`^(?P<dir>[^/\s*?\[\]]+)/\*\*/\*\.py$`）抽出前導目錄名（`tools/**/*.py` → `tools`），回傳 `frozenset`
  - 6 個 case：`test_gitattributes_exists`、`test_default_marks_py_as_generated`（pin base rule `*.py linguist-generated=true` 存在且精確——override 只有在 default 是 generated 時才有意義）、`test_at_least_one_handwritten_override`、`test_override_patterns_have_expected_shape`（**守 parser 假設**：每條 `=false` pattern 都必須是 `<dir>/**/*.py`，否則 loudly fail 要求一起更新 regex——同 M18 `test_no_multiline_run_blocks` 的 precedent）、`test_handwritten_dirs_match_sync_checker`（**核心 drift guard**：parsed dirs == `frozenset(_HANDWRITTEN_DIR_PARTS)`，失敗訊息直接列兩邊差異並叫人「一起改」）、`test_tools_handwritten_on_both_sides`（current state 的正向 anchor）
- 為什麼 parser 放 test 而非 production：與 M18 同理——讓 production 工具 runtime 去讀 `.gitattributes` 會引入不必要耦合（orphan 偵測不該依賴 GitHub Linguist 設定檔存在）。這是 test-only 的 cross-file 不變量，放 test 最乾淨
- 把 import 從 `check_ipynb_py_sync` 多拉一個 `_HANDWRITTEN_DIR_PARTS`（其餘 `_diff_preview` / `_orphan_py` / `_pairs` / `main` 不變）；**不動任何 production code**（converter / 兩支 checker / aggregate runner / hook / `.gitattributes` 全部沒改）。純測試新增，沿用 M14 / M18 的「production code 一行不動」模式
- 不需動 CI workflow：`.github/workflows/ipynb-py-sync.yml` 已跑 `python3 -m unittest discover -s tools/tests`，6 個新 test 自動 pick up
- 負向驗證（確認 guard 真的會咬）：暫時 append `scripts/**/*.py linguist-generated=false` 進 `.gitattributes` → `test_handwritten_dirs_match_sync_checker` FAIL 並印出 `.gitattributes: ['scripts', 'tools']` vs `sync checker: ['tools']` + 修復指引；`git checkout -- .gitattributes` 還原後 → OK
- 本地驗證：
  - `python3 -m unittest tools.tests.test_check_ipynb_py_sync.GitattributesParityTests -v` → `Ran 6 tests OK`
  - `python3 tools/tests/test_check_ipynb_py_sync.py` → `Ran 34 tests OK`（M9 9 + M14 19 + M19 6）
  - `python3 -m unittest discover -s tools/tests` → `Ran 151 tests OK`（M8 31+12+4 + M9 9+19+6 + M10 31 + M11→M12 13 + M17 18+6）
  - `python3 tools/check_all.py --quiet` → 4 steps 全 PASS、exit 0

#### 用法
```bash
# 只跑 M19 新增的 parity class
python3 -m unittest tools.tests.test_check_ipynb_py_sync.GitattributesParityTests
python3 -m unittest tools.tests.test_check_ipynb_py_sync.GitattributesParityTests -v
```

#### 副作用 / 注意
- `_HANDWRITTEN_OVERRIDE_RE` 只認 `<dir>/**/*.py` 這種單層前導目錄的 override。若日後想用更深的 pattern（例如 `tools/sub/**/*.py`）或非 `.py` override，`test_override_patterns_have_expected_shape` 會先紅，提醒同步擴充 regex + 比對邏輯（不會 silently 漏掉那條 dir）
- 這條 guard 只比對 `.gitattributes` 的 `linguist-generated=false` dirs 與 `_HANDWRITTEN_DIR_PARTS`；它**不**檢查 `_SKIP_DIR_PARTS`（`.git` / `.github` / `.venv` 等），因為那些是 walk-time 全域跳過、與 GitHub Linguist 無對應關係，不構成 cross-file 不變量
- 至此 toolchain 三條「靠慣例成立 → 用 test 鎖死」的 cross-file/cross-convention 不變量全部上鎖：M9（orphan 偵測本身）、M18（check_all == CI workflow）、M19（`.gitattributes` == `_HANDWRITTEN_DIR_PARTS`）

### M20 — `tools/README.md` toolchain 參考文件 + README↔tools/ parity guard
- 為什麼補：toolchain 從 M1 一路長到現在已是 4 支 Python 工具（converter / sync checker / converted-py validator / aggregate runner）+ 2 支 hook script（`pre-commit` / `install.sh`）+ 1 道 CI workflow + 157 個 test。但所有知識只活在 `docs/progress-ipynb-to-py.md`——一份**按 milestone 順序堆疊的 chronological log**，要查「某支工具怎麼用 / 失敗了怎麼修 / hook 怎麼裝」得從頭翻 600+ 行。`tools/` 底下**完全沒有 README**。任何新接手的人（或未來的自己）沒有單一 reference 入口。這是 toolchain 成熟度的最後一塊明顯缺口
- 解法（兩部分）：
  - **`tools/README.md`** — 純 reference（非 chronological）：
    - 「## Tools」表格：6 個工具（4 py + 2 hook）逐個一句話角色說明
    - 常用指令（轉檔 / `--files` / `--strict` / `--strict --dry-run` / 三支 checker / `check_all.py`）
    - pre-commit hook 安裝（`install.sh` + 手動 symlink fallback）
    - CI 對應：列出 `ipynb-py-sync.yml` 四步、點明與 `check_all.py` step-for-step 對齊（由 M18 `WorkflowParityTests` 鎖死）
    - 測試清單表（6 個 test 檔各自覆蓋對象）
    - 「失敗時怎麼修」對照表（DRIFT / MISSING / ORPHAN / compile failure / `[strict]`）
    - 開頭明確指向 `docs/progress-ipynb-to-py.md` 作為歷史決策來源，分工清楚（README = reference，progress = log）
  - **`tools/tests/test_readme.py` 的 `ReadmeParityTests`（6 cases，純 stdlib）** — 依 M18 / M19 precedent 把「README 文件 ↔ 實際工具樹」這個只靠慣例成立的不變量鎖進 test：
    - `_tools_section()` — line-scan README，抓「## Tools」到下一個 `## ` header 之間的區塊
    - `_documented_tool_paths()` — 用 `_TOOL_ROW_RE`（`^\|\s*` + backtick-wrapped `tools/...` 路徑）抓表格第一欄的工具路徑
    - 6 個 case：`test_readme_exists`、`test_tools_table_shape`（**守 parser 假設**：Tools 區塊必須有 markdown table separator row + 至少一條 `tools/...` 資料列，被 reformat 就 loudly fail——同 M18 `test_no_multiline_run_blocks` / M19 `test_override_patterns_have_expected_shape` 的 precedent）、`test_all_toplevel_py_tools_documented`（**核心 drift guard**：documented `tools/*.py` 集合 == 實際 `glob('tools/*.py')`，失敗訊息列兩邊差異 + 叫人一起改）、`test_hook_scripts_documented`（兩支 hook script 都在表格）、`test_no_undocumented_or_phantom_paths`（表格列的每條 backtick 路徑都指向真實檔案，抓 typo / 文件了但沒 commit 的工具）、`test_hook_scripts_exist_on_disk`（current state 正向 anchor）
- 為什麼 parser 放 test 而非 production：與 M18 / M19 同理——讓 production 工具 runtime 去讀自己的 README 是不必要耦合。文件↔工具樹一致性是 test-only 的 cross-file 不變量，放 test 最乾淨
- 不動 production code：converter / 兩支 checker / aggregate runner / hook / `.gitattributes` / CI workflow 全部沒改。純新增一份 README + 一支 test 檔，沿用 M14 / M18 / M19 的「production code 一行不動」模式
- 不需動 CI workflow：`.github/workflows/ipynb-py-sync.yml` 已跑 `python3 -m unittest discover -s tools/tests`，6 個新 test 自動 pick up——守的正是這份新 README 與工具樹的一致性
- 負向驗證（確認 guard 真的會咬）：暫時 `touch tools/_phantom_tool.py` → `test_all_toplevel_py_tools_documented` FAIL 並印出 `documented: [...]` vs `on disk: [..., 'tools/_phantom_tool.py']` + 修復指引；`rm` 還原後 → OK
- 本地驗證：
  - `python3 tools/tests/test_readme.py -v` → `Ran 6 tests OK`
  - `python3 -m unittest discover -s tools/tests` → `Ran 157 tests OK`（M8 31+12+4 + M9 9+19+6 + M10 31 + M11→M12 13 + M17 18+6 + M20 6）
  - `python3 tools/check_all.py --quiet` → 4 steps 全 PASS、exit 0

#### 用法
```bash
# 看 toolchain 參考文件
cat tools/README.md

# 只跑 M20 新增的 parity class
python3 -m unittest tools.tests.test_readme.ReadmeParityTests
python3 -m unittest tools.tests.test_readme.ReadmeParityTests -v
```

#### 副作用 / 注意
- `_TOOL_ROW_RE` 只認「表格第一欄是 backtick-wrapped `tools/...` 路徑」這種列。若日後改用別種文件格式列出工具（bullet list / 不同欄位順序），`test_tools_table_shape` 會先紅，提醒同步改 parser（不會 silently 讀成空表）
- 這條 guard 只比對 top-level `tools/*.py`（4 支）與 2 支 hook script；不檢查 `tools/tests/*.py`（test 檔由 discover 自動 pick up，不需逐個文件化）。若日後在 `tools/` 新增非 test 的子目錄工具，要擴充 `_TOPLEVEL_PY_RE` 與比對邏輯
- 至此 toolchain 的「reference 文件」與「歷史 log」分工確立：`tools/README.md`（怎麼用，被 test 鎖住與工具樹一致）+ `docs/progress-ipynb-to-py.md`（為什麼這樣做，chronological）

### M21 — README「## 測試」table ↔ `tools/tests/test_*.py` parity guard
- 為什麼補：M20 的 `ReadmeParityTests` 只把 README「## Tools」表格（4 支 production 工具 + 2 支 hook script）對 `tools/*.py` 鎖死，但**同一份 README 還有第二張表格——「## 測試」table（lines 92–99，列出 6 支 test 檔 + 各自覆蓋對象）完全沒被守**。M20 進度文末甚至寫了「不檢查 `tools/tests/*.py`（test 檔由 discover 自動 pick up，不需逐個文件化）」——但這句只在「不需要為了被 CI 跑到而文件化」的意義上成立；README 既然**已經主動列了一張 test 表**，那張表就跟 Tools 表一樣會 silently 腐爛（新增 / 刪 / rename 一支 test module，表格忘了同步改也沒人會發現）。這是 README 裡最後一張沒上鎖的表，剛好是 M20 gap 的鏡像
- 解法（純測試新增，不動 production code）：
  - 小重構 `tools/tests/test_readme.py`：把 `_tools_section()`（line-scan「## Tools」到下一個 `## ` header）抽成通用 `_section(header)`，`_tools_section()` / 新增的 `_tests_section()` 都變成 `_section('Tools')` / `_section('測試')` 的薄包裝。消掉複製貼上，且既有 `ReadmeParityTests` 的 6 個 test 行為完全不變
  - 新增 `_TEST_ROW_RE`（`^\|\s*` + backtick-wrapped `tools/tests/...` 路徑）、`_documented_test_paths()`（抓「## 測試」表格第一欄）、`_actual_test_files()`（`glob('tools/tests/test_*.py')`）
  - **`_TEST_ROW_RE` 刻意 anchor 到 `^|`**：「## 測試」section 內除了表格，還有一段 fenced code block 含 `python3 tools/tests/test_check_all.py -v` 這種行；anchor 到 row 開頭的 `|` 才不會把 code block 行誤判成表格列。docstring 寫明此理由
  - 新增 `ReadmeTestTableParityTests`（4 個 case，依 M20 precedent）：
    - `test_tests_table_shape` — **守 parser 假設**：「## 測試」section 必須有 markdown table separator row + 至少一條 `tools/tests/...` 資料列；被 reformat 就 loudly fail（同 M20 `test_tools_table_shape`、M18 `test_no_multiline_run_blocks`、M19 `test_override_patterns_have_expected_shape` precedent）
    - `test_all_test_files_documented` — **核心 drift guard**：documented test 集合 == 實際 `glob('tools/tests/test_*.py')`，失敗訊息列兩邊差異 + 叫人一起改
    - `test_no_undocumented_or_phantom_test_paths` — 表格列的每條 backtick 路徑都指向真實檔案（抓 typo / 文件了但沒 commit 的 test module）
    - `test_test_files_exist_on_disk` — current state 正向 anchor（兩邊都描述存在的檔案，parity 才有意義）
- 為什麼 `glob('test_*.py')` 而非 `glob('*.py')`：`tools/tests/` 下只有 `test_*.py`（無 `__init__.py`／`conftest.py`，M8 已確認 unittest discover 用 namespace package 不需 `__init__.py`），且 README 表格列的正是 `test_...py`。用 `test_*.py` 精準對齊文件化對象，不會把未來可能加的 helper module 誤算進來（若日後加了非 `test_` 前綴的共用 helper 又想文件化，要擴 glob pattern）
- 為什麼 parser 放 test 而非 production：與 M18 / M19 / M20 同理——讓 production 工具 runtime 去讀自己的 README 是不必要耦合。文件↔測試樹一致性是 test-only 的 cross-file 不變量，放 test 最乾淨
- 不需動 CI workflow：`.github/workflows/ipynb-py-sync.yml` 已跑 `python3 -m unittest discover -s tools/tests`，4 個新 test 自動 pick up——守的正是 README 第二張表與 test 樹的一致性
- 負向驗證（確認 guard 真的會咬）：暫時 `touch tools/tests/test_phantom_m21.py` → `test_all_test_files_documented` FAIL 並印出 `documented: [...6...]` vs `on disk: [...7 含 test_phantom_m21...]` + 修復指引；`rm` 還原後 → OK
- 本地驗證：
  - `python3 tools/tests/test_readme.py -v` → `Ran 10 tests OK`（M20 6 + M21 4）
  - `python3 -m unittest discover -s tools/tests` → `Ran 161 tests OK`（M8 31+12+4 + M9 9+19+6 + M10 31 + M11→M12 13 + M17 18+6 + M20 6 + M21 4）
  - `python3 tools/check_all.py --quiet` → 4 steps 全 PASS、exit 0

#### 用法
```bash
# 只跑 M21 新增的 class
python3 -m unittest tools.tests.test_readme.ReadmeTestTableParityTests
python3 -m unittest tools.tests.test_readme.ReadmeTestTableParityTests -v
```

#### 副作用 / 注意
- 至此 `tools/README.md` 的**兩張表格都上鎖**：「## Tools」（M20，對 `tools/*.py` + hook）+「## 測試」（M21，對 `tools/tests/test_*.py`）。README 再也沒有可 silently 與實際樹漂移的清單
- `_TEST_ROW_RE` 同 M20 `_TOOL_ROW_RE` 只認「表格第一欄是 backtick-wrapped 路徑」這種列；若日後改用別種格式列 test（bullet list / 不同欄位順序），`test_tests_table_shape` 會先紅提醒改 parser
- 此 guard 只比對 `tools/tests/test_*.py`；不檢查 `tools/tests/` 下其他可能的非 test 檔。M20 文末那句「不需逐個文件化」現在精確化為：**不需為了被 CI 跑到而文件化，但既然 README 列了就得守一致**

### M22 — README「## CI 對應」numbered list ↔ CI workflow parity guard
- 為什麼補：M18 的 `WorkflowParityTests` 把 `check_all.build_steps()` 與 `.github/workflows/ipynb-py-sync.yml` 的 run-steps 互鎖，但同一條 CI step 序列在 `tools/README.md`「## CI 對應」段（M20 寫的）還有**第三份手寫副本**——4 步 numbered list，每步內嵌一行 backtick 指令。M18 / M20 / M21 把 workflow、README 兩張表格都上鎖了，唯獨這份「文件版 CI 流程」沒人守：改了 workflow / `check_all` 的步驟（加減步、拿掉 `--strict`、重排）卻忘了同步 README，這段就 silently 與真實 CI 漂移。這正是 M9（orphan）/ M18（CI parity）/ M20-M21（README 表格）反覆關掉的「只靠慣例成立」缺口
- 解法：在 `tools/tests/test_readme.py` 新增 `ReadmeCiParityTests`（6 個 test，純 stdlib）
  - **復用 M18 的 normalization**：`from test_check_all import _step_signature, _workflow_run_commands`。README CI 段的指令解析後用**同一套** `_step_signature`（reduce 成 `(tool, frozenset(long_flags))`，忽略 interpreter / path prefix / 尾端 root arg / single-dash flag）與 workflow run-commands 做 ordered 比對。透過 M18 已鎖的 workflow == build_steps，傳遞性保證 **README == workflow == `check_all`**，三份副本任一漂移都會紅
  - 為什麼比對 workflow 而非 build_steps：workflow yaml 是「CI 實際跑什麼」的 source of truth，README CI 段宣稱文件化的正是它；兩邊都是「人寫的指令字串」（可 `shlex.split`），是最 apples-to-apples 的比對。build_steps 已由 M18 鎖到 workflow，不必再直接比一次
  - 新增 parser：`_CI_STEP_RE = ^\d+\.\s+\`([^\`]+)\`` 只認「numbered list item 且內容以 backtick 指令開頭」，所以段落 prose 行裡的 inline code（如 `` `.github/workflows/...` ``）不會被誤當步驟；`_ci_section()` 復用 M21 抽出的通用 `_section(header)`
- 6 個 test：
  - `test_ci_section_exists` — 「## CI 對應」段存在且非空
  - `test_ci_section_shape` — 段內至少解析到一個 `N. \`cmd\`` 步驟（narrow parser 守門，reformat 走樣會先紅提醒改 `_CI_STEP_RE`，同 M20/M21 的 `*_table_shape`）
  - `test_ci_step_count_matches_workflow` — 文件步數 == workflow run-step 數
  - `test_ci_step_signatures_match_workflow_in_order` — **核心 guard**：`(tool, long_flags)` 序列逐項相等，失敗印 README vs workflow 兩側 sig + 修復指引（提醒同步 README / workflow / `check_all`）
  - `test_ci_tools_in_expected_order` — tool basename 序列 == `[unittest, ipynb_to_py.py, check_ipynb_py_sync.py, check_converted_py.py]`（與 M18 `test_tools_invoked_in_expected_order` 對稱）
  - `test_ci_commands_reference_real_tools` — phantom guard：CI 段指令裡每個 `.py` 都得在磁碟上存在（抓 typo / 文件列了但沒 commit 的工具）
- 跨 invocation mode 的 import robustness：`_step_signature` / `_workflow_run_commands` 是 `test_check_all` 的 module-level helper。test_readme 在 import 前先 `sys.path.insert(0, HERE)`（HERE = `tools/tests/`），讓 `from test_check_all import ...` 在三種跑法都成立——
  1. 直接跑檔 `python3 tools/tests/test_readme.py`（HERE 本來就是 sys.path[0]）
  2. discover `python3 -m unittest discover -s tools/tests`（discover 把 start dir 推進 sys.path）
  3. dotted `python3 -m unittest tools.tests.test_readme`（靠這次的 explicit insert 才成立）
  - `test_check_all` 自己 import 時會 insert `tools/` 供 `import check_all`，所以 helper 鏈完整。為什麼復用而非在 test_readme 重抄一份 `_step_signature`：抄一份會與 M18 的 normalization 各自演化、可能 silently 不一致；復用確保「README guard 用的正是 workflow guard 用的同一把尺」
- 為什麼 parser / guard 放 test 而非 production：同 M18 / M19 / M20 / M21——讓 production 工具 runtime 去讀自己的 README 是不必要耦合。文件↔CI 一致性是 test-only 的 cross-file 不變量
- 不需動 production code：`tools/README.md` 既有 CI 段已與 workflow 相符（guard 一寫就綠），純測試新增。`check_all.py` / workflow / converter 全部沒改
- 不需動 CI workflow：`.github/workflows/ipynb-py-sync.yml` 已跑 `python3 -m unittest discover -s tools/tests`，6 個新 test 自動 pick up
- 負向驗證（確認 guard 真的會咬）：暫時把 README CI 段第 2 步的 `--strict` 拿掉 → `test_ci_step_signatures_match_workflow_in_order` FAIL 並印出 README vs workflow 兩側 sig 差異 + 修復指引；還原後 → OK
- 本地驗證：
  - `python3 tools/tests/test_readme.py -v` → `Ran 16 tests OK`（M20 6 + M21 4 + M22 6）
  - `python3 -m unittest tools.tests.test_readme.ReadmeCiParityTests -v` → `Ran 6 tests OK`（dotted mode 也通過，驗證 import robustness）
  - `python3 -m unittest discover -s tools/tests` → `Ran 167 tests OK`（M8 31+12+4 + M9 9+19+6 + M10 31 + M11→M12 13 + M17 18+6 + M20 6 + M21 4 + M22 6）
  - `python3 tools/check_all.py --quiet` → 4 steps 全 PASS、exit 0

#### 用法
```bash
# 只跑 M22 新增的 class
python3 -m unittest tools.tests.test_readme.ReadmeCiParityTests
python3 -m unittest tools.tests.test_readme.ReadmeCiParityTests -v
```

#### 副作用 / 注意
- 至此 CI step 序列的**三份副本全部互鎖**：workflow yaml（M18 對 build_steps）+ `check_all.build_steps()`（M18 對 workflow）+ README「## CI 對應」（M22 對 workflow）。改 CI 流程必須三處同步，任一漏改都有 test 會紅
- `ReadmeCiParityTests` 跨 test 模組 import `test_check_all` 的 helper；若日後把 `_step_signature` / `_workflow_run_commands` 改名或移走，test_readme 的 import 會先 ImportError——這是預期的耦合訊號（兩個 parity guard 本就該共用同一把尺），不是 bug
- `_CI_STEP_RE` 只認 numbered list（`N. `）+ 行首 backtick 指令；若日後 README 改用 bullet list 或別種步驟格式，`test_ci_section_shape` 會先紅提醒改 parser

### M23 — `pre-push` git hook 把 CI artifact 檢查前移到 push 前
- 為什麼補：M5/M11/M12 建立的 `pre-commit` hook 只做「stage `.ipynb` 時重生對應 `.py` 並一起 commit」這個**前向**動作。但 hook 是 opt-in，且 `git commit -n` / `--no-verify` 可繞過——一旦 `.py` 與 `.ipynb` drift（或 `.py` 無法 compile、夾帶 magic leak），目前唯一的攔截點是 CI，要等 push 後 workflow 跑紅才發現。本地少了「push 前最後一道把關」。M23 補上對稱的另一半：push 前在本地重現 CI 的 artifact 檢查
- 新增 `tools/hooks/pre-push`（bash）：
  - `cd` 到 repo root 後跑 `python3 tools/check_all.py --skip-tests`
  - 失敗印一行「fix the above before pushing (or bypass with: git push --no-verify)」到 stderr 並 `exit 1`，git 因此中止 push
  - **為什麼 `--skip-tests`**：CI step 1（`unittest discover -s tools/tests`）驗的是 toolchain 本身、不是你要 push 的 notebook；它需要完整 `tools/tests/` 樹、且會在每次 push 無關變更時都重跑（甚至遞迴起 subprocess git repo 的 hook 測試）。pre-push 只跑 step 2-4（strict pre-scan + sync + converted）——正好對應「push 上去的 `.py` artifact 是否乾淨」這個本地該擋的風險面；toolchain 單元測試仍由 CI 跑
  - **為什麼不加 `--quiet`**：失敗時 dev 需要看到 `DRIFT: <nb>` 是哪個檔，quiet 會抑制 per-file 行（見 M14），對 blocking gate 是反效果。所以保留 verbose
- 擴 `tools/hooks/install.sh`：原本只 symlink `pre-commit`，改成 `for hook in pre-commit pre-push` 迴圈一次裝兩個，沿用既有的 chmod +x / 非 symlink backup / idempotent `ln -sf` 邏輯。手動安裝指令在 README 也補上 `pre-push` 那條
- 鎖進 parity guard：把 `tools/hooks/pre-push` 加進 `test_readme._HOOK_PATHS`，於是 M20 的 `ReadmeParityTests` 雙向守住——README「## Tools」表沒列 pre-push（或列了但檔案不存在）就紅。README「## Tools」表新增一列、「## 安裝 git hooks」段（原「## 安裝 pre-commit hook」改名）說明兩個 hook + `--skip-tests` 理由
- 測試（`tools/tests/test_pre_commit_hook.py`）：
  - 翻新 `InstallShTests` 3 個 case 改為驗**兩個** symlink（`test_fresh_install_creates_both_symlinks_to_relative_targets`）、兩個 hook 都 idempotent 無 backup、pre-existing 非 symlink 的兩個 hook 都被 backup；setUp 多 copy `pre-push`（不 copy 的話 `install.sh` 在 `chmod +x` 階段就會 `set -e` 噴錯）
  - 新增 `PrePushHookTests`（4 case）：每 test 起隔離 git repo，copy converter + 兩支 checker + `check_all.py` + `pre-push`（**刻意不 copy `tools/tests/` 樹**——這正是 `--skip-tests` 要避免的遞迴），symlink 安裝 hook，用 `subprocess.run([hook, 'origin', url], input=<ref lines>)` 照 git 真實呼叫法觸發：
    - `test_pass_when_artifacts_in_sync` — 用 converter 生 byte-for-byte 同步的 `.py` → rc=0
    - `test_block_when_py_drifted` — append 一行進 `.py`（模擬繞過 pre-commit）→ rc≠0
    - `test_block_when_py_missing` — 只有 `.ipynb` 沒 `.py` → rc≠0
    - `test_block_when_notebook_is_malformed` — 壞 JSON 觸發 strict pre-scan → rc≠0
- 不動的東西：converter / 三支 checker / `check_all.py` / CI workflow 全部沒改。pre-push 純粹是 opt-in 的本地 gate，復用既有工具
- 已知 edge（繼承自 toolchain）：repo 內**完全沒有 `.ipynb`** 時，strict pre-scan 與 sync checker 都回 rc=1（M14/M16 lock 的「empty tree → rc=1」），所以 pre-push 會擋下 push。TQuant-Lab 永遠有 77 個 notebook 不會踩到；因此沒為「零 notebook 必過」寫 test（不想 enshrine 這個邊角行為）。若日後要在無 notebook 的 repo 重用此 hook，需讓 checker 對 empty tree 放行
- 本地驗證：
  - `python3 tools/tests/test_pre_commit_hook.py -v` → `Ran 17 tests OK`（HookBehaviour 10 + InstallSh 3 + PrePush 4）
  - `python3 -m unittest discover -s tools/tests` → `Ran 171 tests OK`（M22 167 + M23 4）
  - `python3 tools/tests/test_readme.py` → `Ran 16 tests OK`（pre-push 進 `_HOOK_PATHS` 後仍綠）
  - `python3 tools/check_all.py --quiet` → 4 steps 全 PASS、exit 0
  - End-to-end smoke（真 repo）：同步狀態 `tools/hooks/pre-push origin <url>` → rc=0 / 3 steps pass；故意 append 一行進 `Aroon.py` → rc=1 + `DRIFT: Aroon.ipynb`；還原後乾淨

#### 用法
```bash
# 裝 hook（pre-commit + pre-push 一起）
tools/hooks/install.sh

# 想跳過 pre-push gate（極少數情況）
git push --no-verify

# 只跑 M23 新增的 class
python3 -m unittest tools.tests.test_pre_commit_hook.PrePushHookTests -v
```

### M24 — hook-set parity guard：install.sh 迴圈 ↔ README 手動 `ln -sf` 區塊 ↔ `tools/hooks/` 磁碟
- 為什麼補：M23 之後「toolchain 要裝哪些 git hook」這份清單同時手寫在**四個**地方，彼此沒有任何強制同步：
  1. `tools/hooks/` 下的實際腳本（`pre-commit` / `pre-push`，**真理來源**）
  2. `install.sh` 的 `for hook in pre-commit pre-push; do` 迴圈
  3. README「## Tools」表（M20 的 `ReadmeParityTests.test_hook_scripts_documented` 守，但它比對的是**硬編**在 test 裡的 `_HOOK_PATHS` 常數）
  4. README「## 安裝 git hooks」段的手動 `ln -sf ../../tools/hooks/<h> .git/hooks/<h>` 指令（**完全沒守**）
  - 新增第三個 hook（例如 `commit-msg`）卻漏改 (2) 或 (4)，使用者照 README 手動安裝就會少裝一個 hook、或 `install.sh` 裝的與文件講的不一致，而沒有任何 test 會紅。這正是 M9（orphan）/ M18（CI parity）/ M20-M22（README 表格 / CI 清單）反覆關掉的「只靠慣例成立」缺口
- 解法：在 `tools/tests/test_readme.py` 新增 `InstallParityTests`（7 個 test，純 stdlib），把「磁碟真理」定義為 `tools/hooks/` 下除 `install.sh` 外的所有檔（`_disk_installable_hooks()`），兩份手寫副本都對它鎖死：
  - `_INSTALL_LOOP_RE = ^\s*for\s+hook\s+in\s+(.+?)\s*;\s*do\s*$` 解析 install.sh 迴圈 → hook 名集合
  - `_LN_SF_RE = ln\s+-sf\s+\S*tools/hooks/(\S+)\s+\S*\.git/hooks/(\S+)` 解析 README 手動區塊，**同時捕獲 source 與 dest basename**（dest 無路徑前綴，regex 對 `.git/hooks/` 不強制前導斜線）；`_manual_install_lines()` 限定只掃「## 安裝 git hooks」段，避免 README 他處的 `ln -sf` 範例洩入
- 7 個 test：
  - `test_install_sh_loop_shape` / `test_manual_install_block_shape` — narrow parser 守門（同 M20-M22 的 `*_shape`，reformat 走樣先紅提醒改 regex）
  - `test_install_sh_hooks_match_disk` — **核心 guard**：install.sh 迴圈集合 == 磁碟可安裝 hook 集合
  - `test_manual_install_hooks_match_disk` — **核心 guard**：README 手動 `ln -sf` 集合 == 磁碟集合
  - `test_install_sh_and_manual_block_agree` — 兩份手寫副本直接互等（各自已對磁碟鎖；此條讓「只有這兩份彼此分歧」時錯誤訊息更清楚）
  - `test_manual_install_symlink_src_equals_dst` — 每條 `ln -sf` 的 `tools/hooks/<h>` 與 `.git/hooks/<h>` basename 必須相同（dest 打錯會裝出壞 symlink）
  - `test_hook_paths_constant_matches_disk` — 把 M20 **硬編**的 `_HOOK_PATHS`（含 `install.sh`）對 `tools/hooks/` 全部腳本驗證；這樣「## Tools」表的 hook guard 不會被「有 hook 但沒加進常數」silently 繞過
- 為什麼放 test 而非 production：同 M18-M22——讓 production 工具 runtime 去 parse 自己的 README / install.sh 是不必要耦合；安裝清單跨檔一致性是 test-only 的 cross-file 不變量
- 不需動 production code：`install.sh` / README / 兩支 hook 既有內容一寫就綠。純測試新增
- 不需動 CI workflow：`.github/workflows/ipynb-py-sync.yml` 已跑 `python3 -m unittest discover -s tools/tests`，7 個新 test 自動 pick up
- 負向驗證（確認三條核心 guard 真的會咬，跑完還原）：
  - 在 install.sh 迴圈塞 `commit-msg` → `test_install_sh_hooks_match_disk` FAIL
  - 刪掉 README 的 `pre-push` `ln -sf` 行 → `test_manual_install_hooks_match_disk` FAIL
  - 從 `_HOOK_PATHS` 拿掉 `pre-push` → `test_hook_paths_constant_matches_disk` FAIL
- 本地驗證：
  - `python3 tools/tests/test_readme.py` → `Ran 23 tests OK`（M20 6 + M21 4 + M22 6 + M23 1（hook 進 `_HOOK_PATHS`）+ M24 7）
  - dotted（`-m unittest tools.tests.test_readme.InstallParityTests`）與 direct-file 兩模式皆 OK（沿用 M22 的 HERE-on-sys.path import robustness）
  - `python3 -m unittest discover -s tools/tests` → `Ran 178 tests OK`（M23 171 + M24 7）
  - `python3 tools/check_all.py --skip-tests --quiet` → 3 steps 全 PASS、exit 0
  - pre-push hook 真 repo smoke：`bash tools/hooks/pre-push origin file://$(pwd)` → rc=0、3 steps pass

#### 用法
```bash
# 只跑 M24 新增的 class
python3 -m unittest tools.tests.test_readme.InstallParityTests
python3 -m unittest tools.tests.test_readme.InstallParityTests -v
```

#### 副作用 / 注意
- 至此「toolchain 安裝哪些 hook」的四份副本全部互鎖：磁碟（真理）↔ install.sh 迴圈（M24）↔ README 手動區塊（M24）↔ README「## Tools」表（M20 經 `_HOOK_PATHS`，而 `_HOOK_PATHS` 本身又經 M24 對磁碟驗證）。新增 / 刪除 hook 必須四處同步
- `_disk_installable_hooks()` 把「`tools/hooks/` 下除 `install.sh` 外的檔」當可安裝 hook；若日後在該目錄放非 hook 的輔助檔（如共用 lib），需調整此 helper 的排除清單，否則 `test_install_sh_hooks_match_disk` 會把它當成該被安裝的 hook

### M25 — notebook-discovery 行為 parity guard：三支工具枚舉同一組 `.ipynb`
- 為什麼補：toolchain 有三支工具各自**獨立**重寫了「`.ipynb` 探索 + `.ipynb_checkpoints` 過濾」這段 walk，彼此沒有任何強制同步：
  1. `ipynb_to_py.main` 的 root-walk：`sorted(p for p in base.rglob('*.ipynb') if '.ipynb_checkpoints' not in p.parts)`（決定哪些 notebook 會重生 `.py`）
  2. `check_ipynb_py_sync._pairs`：`root.rglob('*.ipynb')` 過濾 `'.ipynb_checkpoints' in nb.parts`（決定哪些做 byte-for-byte sync 比對）
  3. `check_converted_py._paired_py_files`：同上過濾（決定哪些生成 `.py` 跑 `py_compile` + magic-leak）
  - 三者目前邏輯一致，但若日後在某一支的 walk 加 skip dir / 改 checkpoint filter（例如改成同時略過 `.git` / `__pycache__`，像 `_SKIP_DIR_PARTS` 那樣）卻漏改另兩支，coverage 就 silently 漂移：notebook 可能被轉了卻沒被 sync-check、或被 sync-check 了卻沒被 compile-validate。CI 抓不到，因為每個 step 只看自己那一片 notebook，無法察覺三片之間的缺口。這正是 M9（orphan）/ M18（CI parity）/ M20-M24（README/install parity）反覆關掉的「只靠慣例成立」缺口，只是這次的不變量在**行為層**而非文字層
- 解法：新增 `tools/tests/test_discovery_parity.py` 的 `NotebookDiscoveryParityTests`（8 個 test，純 stdlib），用**行為 parity** 而非 text/regex parsing：
  - fixture tree（`tempfile.TemporaryDirectory`）：3 個真 notebook（`A.ipynb`、`sub/B.ipynb`、`sub/deep/C.ipynb`）+ 2 個必須被排除的 checkpoint notebook（root-level `.ipynb_checkpoints/A-checkpoint.ipynb`——正是 M11 修過的 root-level filter bug 點——與 nested `sub/.ipynb_checkpoints/B-checkpoint.ipynb`）
  - 三支 discovery 各包一個 helper，全部 normalize 成 root-relative posix 字串集合：
    - `_converter_discovers`：跑真實 `ipynb_to_py.main(['--dry-run', root])`、parse `[dry] <rel> -> ...` 行取得 walk 結果——**刻意不在 test 內複寫 walk**，否則 parity guard 形同虛設（測的會是 test 自己的複本而非 production walk）。dry-run 在 M16 後仍會 `convert_to_str` 驗 parseability，所以 fixture notebook 用最小但合法的 nbformat JSON
    - `_pairs_discovers` / `_validator_discovers`：直接 import `_pairs` / `_paired_py_files`
  - 8 個 case：三支各自 == expected 3 檔（3）、**核心** `test_all_three_discover_identical_set`（converter==pairs==validator）（1）、root-level + nested checkpoint 被三方共同排除（2）、negative control `test_fixture_actually_contains_checkpoints`（raw `rglob` 看到 5 個 `.ipynb` 但三支 discovery 都只看到 3，證明 filter 真的被 exercise，不是 vacuous pass）（1）、empty tree 三方都回空集合（1）
- 設計細節：
  - converter 的 walk 嵌在 `main()` 內、不是獨立 function；不為了測它而抽 helper（避免動 production code），改走 `--dry-run` 輸出 parse——這條 dry-run 行為已被 M13/M16 鎖過，穩定可依賴
  - `_DRY_RE = ^\[dry\] (.+?) -> ` narrow 解析；fixture 的最小 notebook `{"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}` 確保 dry-run parseability 檢查不會誤判失敗
  - negative control 是這類 parity test 的關鍵：沒有它，若 fixture 哪天少放了 checkpoint，exclusion 斷言會 trivially 通過而沒人發現
- 為什麼放 test 而非 production：同 M18-M24——讓三支工具 runtime 去互相比對彼此的 discovery 是不必要耦合；「三支 walk 枚舉同一組」是 test-only 的 cross-tool 行為不變量。也刻意**不**把三份 walk 重構成單一 shared function（那會引入跨工具 import 耦合 + byte-for-byte regen 風險），與 M19「guard not consolidate」的取捨一致
- 不需動 production code：converter / sync checker / validator / hook / CI workflow 全部沒改。純測試 + README test-table 一列
- README 連動：新增 `test_*.py` 觸發 M21 的 `ReadmeTestTableParityTests.test_all_test_files_documented`，故在 `tools/README.md`「## 測試」表補一列 `tools/tests/test_discovery_parity.py`——這正是 M21 guard 設計來捕捉的情境（新測試檔必須同步進文件），順帶實證了該 guard 仍在運作
- 負向驗證（確認核心 guard 真的會咬，跑完用 backup 還原成 byte-identical）：把 `check_converted_py._paired_py_files` 的 `'.ipynb_checkpoints' in nb.parts` 過濾改成 `if False`（模擬「validator 漏改 filter」）→ `NotebookDiscoveryParityTests` 4 個 test FAIL，錯誤訊息直指 validator 多枚舉了 2 個 checkpoint notebook；還原後 8/8 OK
- 本地驗證：
  - `python3 tools/tests/test_discovery_parity.py -v` → `Ran 8 tests OK`
  - `python3 -m unittest discover -s tools/tests` → `Ran 186 tests OK`（M24 178 + M25 8）
  - `python3 tools/tests/test_readme.py` → `Ran 23 tests OK`（test-table 補列後仍綠）
  - `python3 tools/check_all.py --quiet` → 4 steps 全 PASS、exit 0

#### 用法
```bash
# 只跑 M25 新增的 class
python3 tools/tests/test_discovery_parity.py -v
python3 -m unittest tools.tests.test_discovery_parity.NotebookDiscoveryParityTests
```

#### 副作用 / 注意
- 若日後想消除這份 discovery 重複（把三支 walk 收斂成一支 shared helper），M25 的 parity test 仍有效：它斷言的是「三個 public discovery 進入點枚舉同一組」，不管底層是三份複本還是一份共用實作都成立，可當重構的安全網
- converter 端依賴 `--dry-run` 輸出格式（`[dry] <rel> -> <rel_py>`）；若日後改該行格式，`_DRY_RE` 會解析不到、三支 discovery 比對時 converter 集合變空而 FAIL，提醒同步更新 parser

### M26 — `check_all.py` docstring step list ↔ `build_steps()` parity guard
- 為什麼補：同一條 CI 4-step 序列（unit tests → strict pre-scan → sync check → converted check）在 toolchain 裡被手寫了**四份**：
  1. `.github/workflows/ipynb-py-sync.yml` 的 `run:` steps（真理來源之一）
  2. `check_all.build_steps()` 的 argv 構造（M18 用 `WorkflowParityTests` 鎖 == workflow）
  3. `tools/README.md`「## CI 對應」的 numbered backtick list（M22 用 `ReadmeCiParityTests` 鎖 == workflow）
  4. **`tools/check_all.py` 自己的模組 docstring**（lines 9-12 的 numbered list）——**完全沒被守**
  - 前三份已兩兩互鎖，唯獨第四份（工具的自我說明）漂在外面。改了 `build_steps()`（例如拿掉 `--strict`、重排 step）卻忘了同步檔頭 docstring，讀 source 的人就被一份過時的「本工具做什麼」誤導，而沒有任何 test 會紅。這正是 M18 / M20-M24 反覆關掉的「只靠慣例成立」缺口的最後一份副本
- 解法：補 `tools/tests/test_check_all.py` 的 `DocstringParityTests`（6 個 test，純 stdlib）：
  - 新增 `_docstring_step_commands()` helper：純 regex（`^\s*\d+\.\s+.*?(python3\s+\S.*?)\s*$`）解析 `check_all.__doc__` 的 numbered 行，抓出尾端 `python3 ...` 指令、丟掉前面的 label
  - **復用** M18 的 `_step_signature`（normalize 成 `(tool, frozenset(long_flags))`，丟掉 interpreter / path prefix / 尾端 root arg / 單 dash flag），與 `build_steps('.')` 做 ordered 比對——與 workflow / README 同一套 normalization，避免各自一份規則
  - 6 個 case：docstring 必有 4 條 numbered 指令（parser assumption guard，防 docstring 改格式後 vacuous pass）、count == build_steps、signatures ordered == build_steps、tool 順序 == 四工具固定序、strict pre-scan 同時帶 `--strict` + `--dry-run`、**直接斷言 docstring == workflow**（透過 M18 workflow == build_steps 傳遞性閉環）
- 設計細節：
  - docstring 的指令用 `<root>` placeholder（非真實路徑），`_step_signature` 本就忽略非 flag 尾參，所以 `<root>` 自然被丟掉、與 build_steps 的真實 root arg 等價
  - `test_docstring_lists_four_numbered_commands` 是這類 parser-based parity 的必備 guard：若沒有它，有人把 docstring 改成不符 `N. ... python3 ...` 形狀時 parser 回空 list，其餘比對 trivially 通過，guard 形同虛設（對齊 M22 的同型 guard 與 M18 的 `test_no_multiline_run_blocks`）
- 為什麼放 test 而非 production：讓 `check_all.py` runtime 去自我 introspect docstring 是不必要耦合；「docstring 與 build_steps 描述同一序列」是 test-only 的文件不變量，與 M18-M25 取捨一致
- 不需動 production code：`check_all.py` / converter / 三支 checker / hook / CI workflow 全部沒改。純測試新增（一個 helper + 一個 6-test class + module docstring 補一條 pinned 說明）
- 不需動 README：test 加在既有 `test_check_all.py` 內、未新增 test 檔，M21 的 `ReadmeTestTableParityTests` 仍綠（不像 M25 要補 test-table 一列）
- 負向驗證（確認 guard 真的會咬）：monkeypatch `check_all.__doc__` 把 docstring 的 `--strict --dry-run` 改成 `--dry-run`（模擬「docstring 漏改」）→ `doc_sigs != build_sigs` 為 True，`test_docstring_signatures_match_build_steps_in_order` 會 FAIL
- 本地驗證：
  - `python3 -m unittest tools.tests.test_check_all.DocstringParityTests -v` → `Ran 6 tests OK`
  - `python3 -m unittest discover -s tools/tests` → `Ran 192 tests OK`（M25 186 + M26 6）
  - `python3 tools/check_all.py` → 4 steps 全 PASS、exit 0

#### 用法
```bash
# 只跑 M26 新增的 class
python3 -m unittest tools.tests.test_check_all.DocstringParityTests -v
```

#### 副作用 / 注意
- `_docstring_step_commands()` 依賴 docstring 維持「`N. <label>  python3 <cmd>`」格式；若日後把 docstring 改寫成別種排版（例如改用表格或拿掉 `python3` 前綴），`test_docstring_lists_four_numbered_commands` 會先紅，提醒同步更新 parser，而非 silently 變成 vacuous pass
- 至此 CI step 序列的四份手寫副本（workflow / build_steps / README / docstring）全部進入互鎖網：M18（workflow↔build_steps）+ M22（README↔workflow）+ M26（docstring↔build_steps 且 ↔workflow），任一份漂移都有 test 咬住

### M27 — pre-push hook「mirror CI steps 2-4」契約 parity guard
- 為什麼補：M23 的 `tools/hooks/pre-push` 跑 `check_all.py --skip-tests`，把 CI 的 artifact 檢查（strict pre-scan + sync + converted，即 step 2-4）前移到 push 前，刻意跳過 unit tests（step 1）。但這份「mirror CI steps 2-4」契約有兩個只靠慣例成立、沒被任何 test 鎖死的不變量：
  1. **hook 指令真的帶 `--skip-tests`**：少了它，hook 會在每次 push 重跑整個 unit-test suite——正是它自己 docstring 說「intentionally skipped」的行為。整合測試 `PrePushHookTests`（M23）雖然 end-to-end 起真 git repo 跑 hook，但它**只能偶然**抓到這個 drop：fixture 沒複製 `tools/tests/` 目錄，所以 full check_all 的 `unittest discover -s tools/tests` 會丟 `ImportError: Start directory is not importable`（rc≠0）→ 阻擋 push → 期望乾淨 push 的 test 失敗。這條偶然性很脆弱：(a) 失敗訊息是含糊的 import error，完全看不出真因是「hook 少了 `--skip-tests`」；(b) 若 fixture 哪天改成放一個**空的** `tools/tests/`，`discover` 找到 0 test 回 rc 0，drop 就完全漏網。
  2. **`build_steps(skip_tests=True)` == 「CI step 2-4」**（hook docstring 的宣稱）== workflow run-steps 砍掉那唯一一個 unit-test step。M18 的 `WorkflowParityTests` 只鎖了 full `build_steps(skip_tests=False) == workflow`；沒有任何 test 把 skip_tests **子集**綁回 workflow。
- 解法：補 `tools/tests/test_check_all.py` 的 `PrePushParityTests`（7 個 test，純 stdlib）：
  - 新增 `_prepush_check_all_tokens()` helper：讀 `tools/hooks/pre-push`，找含 `check_all.py` + `python3` 的行，regex 去掉 `if ! ` 前綴與 `; then` 尾巴後 `shlex.split` 成 token list（文字層解析，像 M24 解析 `install.sh` 迴圈）
  - **文字層 3 test**：hook 存在、hook 真的 invoke `check_all.py`、hook 帶 `--skip-tests` 且**只**帶這一個 long flag（`test_hook_carries_only_skip_tests` 反向擋掉「有人多塞 `--quiet` 等 flag silently 改變 push 守門條件」——這條整合測試完全不會 flag）
  - **parity 3 test**：`test_skip_tests_drops_exactly_the_first_step`（`build_steps(skip_tests=True)` 的 signature == full `[1:]`）、`test_dropped_step_is_the_unittest_one`（被砍的第一步 label 含 `unit tests` 且 tool == `unittest`）、`test_skip_tests_steps_match_workflow_minus_unittest`（**復用** M18 `_step_signature` / `_workflow_run_commands`，斷言 skip_tests 步驟 == workflow run-steps 過濾掉 unittest 後逐一相符，且恰好只有一個 unittest step 被砍）
- 設計細節：
  - 復用 M18 的 `_step_signature`（normalize 成 `(tool, frozenset(long_flags))`）與 `_workflow_run_commands`，所以 skip_tests 子集與 workflow 的比對用的是與 `WorkflowParityTests` / `DocstringParityTests` 同一套 normalization——artifact 子集的 parity 是 full parity 的同型投影，不另立一套規則
  - 放 test 而非 production：讓 hook 或 check_all runtime 去自我比對是不必要耦合；「hook 帶 `--skip-tests`」「skip_tests == workflow 砍 unittest」是 test-only 的契約不變量，與 M18-M26 取捨一致
- 不需動 production code：`pre-push` / `check_all.py` / converter / 三支 checker / CI workflow 全部沒改。純測試新增（一個 module 常數 + 一個 helper + 一個 7-test class + module docstring 補一段）
- 不需動 README：test 加在既有 `test_check_all.py` 內、未新增 test 檔，M21 的 `ReadmeTestTableParityTests` 仍綠（同 M26，不像 M25 要補 test-table 一列）
- 負向驗證（皆跑完用 backup 還原成 byte-identical，`git diff --stat` 確認空）：
  1. 把 hook 的 `check_all.py --skip-tests` 改成 `check_all.py`（模擬「漏掉 flag」）→ `PrePushParityTests` FAIL 2（`test_hook_passes_skip_tests` + `test_hook_carries_only_skip_tests`），訊息直指少了 `--skip-tests`
  2. 同一個 mutation 下跑 `PrePushHookTests` → 確認它**確實**會失敗，但失敗於含糊的 `ImportError: Start directory is not importable`（證實前述「偶然且訊息不明」的判斷，校正了原本「整合測試完全不會抓到」的誤判）
  3. 把 `build_steps` 的 `if not skip_tests:` 改成 `if not False:`（模擬「skip_tests 不再砍 unittest」）→ FAIL 2（`test_skip_tests_drops_exactly_the_first_step` + `test_skip_tests_steps_match_workflow_minus_unittest`）
- 本地驗證：
  - `python3 -m unittest tools.tests.test_check_all.PrePushParityTests -v` → `Ran 7 tests OK`
  - `python3 -m unittest discover -s tools/tests` → `Ran 199 tests OK`（M26 192 + M27 7）
  - `python3 tools/check_all.py` → 4 steps 全 PASS、exit 0

#### 用法
```bash
# 只跑 M27 新增的 class
python3 -m unittest tools.tests.test_check_all.PrePushParityTests -v
```

#### 副作用 / 注意
- `_prepush_check_all_tokens()` 依賴 hook 維持「`if ! python3 ... check_all.py ...; then`」這種單行 `if !` 守衛形狀；若日後把 hook 改寫成多行（先 assign 變數再 `if`、或拆成 function），parser 會抓不到該行而在 `_prepush_check_all_tokens` raise（test error，非 silent pass），提醒同步更新 parser
- 至此 hook 端的兩條契約都進互鎖網：M24 鎖「要裝哪些 hook」（install.sh ↔ README ↔ 磁碟），M27 鎖「pre-push hook 怎麼跑 == CI 的哪幾步」

### M28 — `_sanitize_code` IPython-help 偵測精準化（修掉 latent code-corruption bug）
- 為什麼補：M18-M27 連續十個 milestone 都在補 parity guard（把只靠慣例成立的不變量鎖進 test），但 converter 本身藏了一個**真實的功能 bug**從沒被處理。`_sanitize_code` 用 `stripped.startswith(('%','!','?')) or stripped.endswith('?')` 判斷哪些行要註解掉以保 `.py` 可 `py_compile`。前半（magic / `?prefix`）正確，後半 `endswith('?')` 是想抓 IPython suffix-help（`obj?` / `obj??`），但它會把**任何結尾是 `?` 的合法 Python 行**整行 `# ` 掉：
  - `x = run()  # is this right?` → 變成 `# x = run()  # is this right?`（valid code 整行消失）
  - triple-quoted string / docstring 內的 prose 行 `Are you ready?` → 被註解，**改壞字串內容**
  - 已是註解的 `# really?` → 變成 `# # really?`
- 為什麼 CI 抓不到（這才是真正危險處）：converter 與 sync checker（`check_ipynb_py_sync.py`）**共用同一個 `_sanitize_code`**（M6 刻意這樣設計避免兩份規則漂移）。所以「壞規則把 valid code 註解掉」時，重生的 expected text 與磁碟 `.py` 仍 byte-for-byte 相符 → sync check 綠、`py_compile` 也綠（被註解的行不會 compile error）→ **整條 CI 都不會紅**。這是 shared-logic 的盲區：規則錯了，但所有靠該規則互相驗證的檢查一起錯，彼此圓謊
- 先確認影響面（決定要不要 regen）：掃全 repo 77 個 notebook 的 code cell，找「結尾是 `?` 且不以 magic 開頭」的行 → **0 行**。代表 `endswith('?')` branch 目前實際 comment 出 0 行，是純 latent trap（哪天有人寫 `df.head()  # 對嗎?` 就中招，且中招了也沒人會發現）
- 解法：把 `endswith('?')` 換成錨定的 `_HELP_SUFFIX_RE`：
  ```python
  _HELP_SUFFIX_RE = re.compile(r'^[A-Za-z_][\w.]*(?:\[[^\]]*\]|\([^)]*\))*\?{1,2}$')
  ```
  只有「identifier 起頭 + dotted attr + 可選 subscript/call chain + 結尾 `?` 或 `??`」整行精確相符才算 IPython suffix-help。`df.head?`、`np.svd()??`、`a[0]?`、`obj??` 仍被抓；帶 `=` / 空白 / `#` 的真實程式碼行因為無法整行匹配而被放過
- **provably byte-for-byte 安全**（零 regen）：因為現存 0 行會走舊 `endswith('?')` branch，新規則對這 0 行的判定無論如何都不改任何輸出。實測 `python3 tools/ipynb_to_py.py .` 重生全部 77 檔後 `git diff --stat` 只有 `tools/ipynb_to_py.py` + `test_ipynb_to_py.py` 兩支 source，**無任何 `.py` sibling 變動**
- 補 5 個 test 進 `SanitizeCodeTests`（原 11 → 16，加上既有共 17）：
  - **`test_dotted_attribute_help_commented`** — `df.head?` 仍註解（real help 不漏放）
  - **`test_subscript_and_call_help_commented`** — `a[0]?`、`np.svd()??` 仍註解
  - **`test_trailing_question_in_comment_preserved`** — `x = run()  # is this right?` 保留（核心 regression guard，docstring 寫明這是 M28 修掉的 shared-rule 盲區）
  - **`test_prose_line_ending_in_question_preserved`** — `Are you ready?` 保留（string body 不被改壞）
  - **`test_comment_line_ending_in_question_not_double_commented`** — `# really?` 不變成 `# # really?`
  - 既有 `test_question_suffix_commented`（`help?`）/ `test_double_question_suffix_commented`（`obj??`）/ `test_question_prefix_commented`（`?help`）全部不動仍綠
- 更新模組 docstring：把「Magics ... commented out」那段補上 help-suffix 改用 reference-chain 偵測、不再 naive `endswith('?')` 的說明，讓 `--help` 與 source 讀者看得到
- 為什麼動 production code（與 M18-M27 不同）：M18-M27 都明寫「不動 production code」，因為它們鎖的是文件/慣例不變量。M28 不一樣——這是 converter 行為本身的 correctness bug，必須改 production。但改動極小（一行條件 + 一條 module-level regex 常數 + docstring），且零 regen、零行為差異於現存 corpus，風險面收斂到「未來含 trailing-`?` 的 notebook 會被正確處理」
- 不動：三支 checker / `pre-commit` / `pre-push` / `install.sh` / CI workflow / README / `.gitattributes` 全部沒改。`check_all.py` 的 step 序列不變，M18 / M22 / M26 / M27 的 parity guard 全綠
- 本地驗證：
  - `python3 -m unittest tools.tests.test_ipynb_to_py.SanitizeCodeTests -v` → `Ran 17 tests OK`
  - `python3 -m unittest discover -s tools/tests` → `Ran 204 tests OK`（M27 199 + M28 5）
  - `python3 tools/ipynb_to_py.py .` → `Converted 77/77`、`git diff --stat` 無 `.py` sibling 變動
  - `python3 tools/check_ipynb_py_sync.py --quiet` → 77/77 in sync、0 orphan、exit 0
  - `python3 tools/check_converted_py.py --quiet` → 77/77 OK、exit 0
  - `python3 tools/check_all.py --quiet` → 4 steps 全 PASS、exit 0

#### 用法
```bash
# 只跑 M28 相關的 sanitize 測試
python3 -m unittest tools.tests.test_ipynb_to_py.SanitizeCodeTests -v
```

#### 副作用 / 注意
- `_HELP_SUFFIX_RE` 仍會把「整行只有一個裸 identifier-chain + `?`」的字串內行（例如 docstring 裡單獨一行寫 `ready?`）誤判為 help 而註解——這是 line-by-line sanitize 無法得知「此行在多行字串內」的固有限制，與舊 `endswith('?')` 行為一致、非 M28 引入的回歸。M28 修的是**帶 `=` / 空白 / `#` 的常見 false positive**（trailing-question comment 與多字 prose），這才是實務上會踩的情境
- 若日後真要連 string-internal 的 `?` 都正確保留，需要 tokenize 整個 cell（追蹤字串/註解狀態），那是比 stdlib regex 重得多的改動，目前不值得

### M29 — CI workflow `paths:` trigger filter parity guard
- 為什麼補：M18 / M22 / M26 / M27 把 workflow 的 **run-steps**（CI「做什麼」）對 `build_steps()` / README / docstring / pre-push 全部互鎖了，但 `.github/workflows/ipynb-py-sync.yml` 還有一塊沒被任何 test 守住的手寫副本——`on.push.paths` 與 `on.pull_request.paths` 這對 **trigger filter**。它決定的不是 CI 做什麼，而是更前面的「CI 到底跑不跑」，而且**整份清單手寫了兩遍**：
  - 在 `push.paths` 加一條卻忘了 `pull_request.paths`（或反之）→ push build 與 PR build silently 覆蓋不同檔案集，最容易在「PR 綠、merge 後 push 才紅」這種錯位上踩
  - 手滑刪掉 `**/*.ipynb` / `**/*.py` / `tools/**` 其中一條 → CI 會**安靜地不再對它存在目的所要守的那種變更觸發**。這種「綠」比某個 step 失敗更危險：step 紅至少看得到，trigger 漏掉是「整個 workflow 根本沒被排程」，PR check 列表上看起來一切正常
- 解法：依 M18-M27 一貫 precedent（「只靠慣例成立的不變量 → 靠 test 成立」），補 `tools/tests/test_check_all.py` 的 `WorkflowTriggerParityTests`（6 個 test，純 stdlib）：
  - 新增 `_workflow_trigger_paths()` — 縮排感知的 line parser（PyYAML 因系統 Python PEP 668 鎖不能用），抽出 `on: -> {push,pull_request}: -> paths:` 兩個 list，去引號、保留順序。複用 M18 既有的「stdlib line-scan workflow」風格，不引入新依賴
  - 新增 module 常數 `_EXPECTED_TRIGGER_PATHS`（canonical 4 條），與 M21 README test-table lock 同理：新增 trigger path 是有意行為，必須同 commit 更新這個常數，lock 才有意義
  - 6 個 test：(1) 兩個 event 都有 paths、(2) **push paths == pull_request paths**（核心：兩份手寫副本不准漂移）、(3) push paths == canonical set（縮小 trigger surface 會紅）、(4) `**/*.ipynb` + `**/*.py` 兩個 artifact glob 在、(5) `tools/**` 在、(6) workflow 自我參照路徑在（用 `WORKFLOW.relative_to(REPO)` 編譯出、非硬編）
- 設計細節：
  - parser 用「event header 在 2-space indent、`paths:` 在 4-space、item 更深」的結構假設；任何結構性改動（`paths-ignore`、多行 list、reindent）會 parse 出空/不同結果，被 test (1)(3) 抓到——fail loudly 而非 silently mis-read，沿用 M18 `test_no_multiline_run_blocks` 同款「先斷言我假設的形狀成立」哲學
  - 自我參照那條（test 6）刻意用 `str(WORKFLOW.relative_to(REPO))` 計算，不硬編字串，所以 workflow 檔名若改名只要 trigger filter 同步改就仍綠
- 不動 production code：與 M18-M27 同——只新增 test + 一個 parser helper + 一條常數。converter / 三支 checker / hook / CI workflow / README / `.gitattributes` 全部沒改；77 個 `.py` sibling 零變動
- 為什麼是這個 milestone：M18-M28 的進度文反覆寫「關掉最後一份未被守的副本」。run-steps 那條鏈已閉環（docstring == build_steps == workflow == README + pre-push 子集），但 trigger filter 是 workflow 裡**唯一**還沒被任何 parity test 碰過的手寫重複區塊，剛好是這條 parity-guard 主線的下一個、也是 workflow 內最後一個明顯目標
- 負向驗證（證明 guard 真的會咬）：用 monkeypatch 把 `pull_request.paths` 改成多一條 `**/*.md`、parse 後 `push != pull_request` → test (2) 會 fail，確認漂移被偵測
- 本地驗證：
  - `python3 -m unittest tools.tests.test_check_all.WorkflowTriggerParityTests -v` → `Ran 6 tests OK`
  - `python3 -m unittest discover -s tools/tests` → `Ran 210 tests OK`（M28 204 + M29 6）
  - `python3 tools/check_all.py --quiet` → 4 steps 全 PASS、exit 0
  - `python3 tools/check_ipynb_py_sync.py --quiet` → 77/77 in sync、0 orphan
  - `python3 tools/check_converted_py.py --quiet` → 77/77 OK

#### 用法
```bash
# 只跑 M29 新增的 class
python3 -m unittest tools.tests.test_check_all.WorkflowTriggerParityTests -v
```

#### 副作用 / 注意
- 若日後真要新增一條 trigger path（例如把 `.gitattributes` 納入觸發），記得同 commit 更新 `_EXPECTED_TRIGGER_PATHS`，並**兩個 event 都加**——這正是 M29 要鎖的不變量

### M30 — README「## CI 對應」intro trigger 描述 ↔ workflow `paths:` parity guard
- 為什麼補：parity-guard 主線到 M29 為止已把 workflow 的 **run-steps**（docstring == build_steps == workflow == README run-list + pre-push 子集，M18/M22/M26/M27）與 **trigger `paths:`**（push == pull_request == canonical，M29）兩條鏈都閉環了。但 `tools/README.md`「## CI 對應」段的 **intro 句子**——「`.github/workflows/ipynb-py-sync.yml` 在 push / PR 觸碰 `.ipynb` / `.py` / `tools/**` 時跑」——是 trigger surface 的**第三份手寫副本**，M22 只鎖了那段的 numbered run-list、M29 只鎖了 workflow 內部，這句 intro 一直沒人守。改了 workflow trigger（拿掉 `tools/**`、加新 glob）卻忘了改 README intro，這份「文件版 CI 觸發條件」就 silently 腐爛，讀文件的人對「CI 什麼時候跑」會被誤導
- 為什麼這是 workflow 相關 parity 的下一個、也是最後一個明顯目標：run-step 鏈與 trigger 鏈各自閉環後，唯一還在「只靠慣例成立」的就是「README 用人話描述的 trigger」這份副本。M18-M29 的進度文反覆寫「關掉最後一份未被守的副本」，這就是 CI 對應段最後一份
- 解法：依 M22 / M29 precedent 補 `tools/tests/test_readme.py` 的 `ReadmeCiTriggerParityTests`（6 個 test，純 stdlib）：
  - 新增 `_display_trigger(tok)` — 把兩種**不同記法**的 trigger 副本 normalize 成同一組 canonical display token：workflow 用 glob（`**/*.ipynb` / `**/*.py` / `tools/**`），README intro 用使用者友善的副檔名寫法（`.ipynb` / `.py` / `tools/**`）。規則：`**/*` 前綴砍掉 → `.ipynb`/`.py`；`*/**`（如 `tools/**`）原樣；裸副檔名 `\.\w+` 原樣；其餘（裸檔名 `check_all.py`、指令字 `python3` / `tools/tests`、root arg `.`、workflow 自我參照路徑）→ None
  - 新增 `_documented_ci_trigger_tokens()` — harvest「## CI 對應」段所有 inline `` `code span` ``、各自按空白切 token（讓 `python3 -m unittest …` 這種多字指令 span 拆成個別 token）、過 `_display_trigger` 留下 trigger token 集合
  - 新增 `_workflow_trigger_display()` — 取 M29 的 `_workflow_trigger_paths()['push']`（push == pull_request 由 M29 鎖死，取任一即真理）過同一個 `_display_trigger`
  - 6 個 test：(1) README intro 有引用 trigger token（harvester shape guard）、(2) workflow 側非空（positive anchor）、(3) **README token 集合 == workflow trigger surface**（核心 drift guard）、(4) `.ipynb` + `.py` 兩個 artifact glob 在文件、(5) `tools/**` 在文件、(6) workflow 自我參照路徑**不**屬 user-facing surface（兩邊 display set 都排除，鎖住這個 intentional asymmetry，防止有人「修文件」時把 workflow 路徑當 watched glob 列上去）
- 設計細節：
  - 兩邊都過**同一個** `_display_trigger`，所以比對是 deterministic set equality，不靠 fuzzy 文字對映——避免「parity guard 建在脆弱文字假設上反而給假信心」。`check_all.py` / `tools/tests` / `.`（root arg）這些同段出現的 backtick token 都被 `_display_trigger` 明確排除（實測 README display set == `{.ipynb, .py, tools/**}`）
  - 復用 M29 的 `_workflow_trigger_paths()`（從 `test_check_all` import，沿用既有 HERE-on-sys.path 的 import 形式，與 M22 復用 `_step_signature` / `_workflow_run_commands` 同款），不另寫一份 workflow parser
  - 透過 M29 的 push == pull_request == canonical 互鎖，本 test 的 README == workflow 傳遞性閉環 README == workflow == canonical
- 不動 production code：與 M18-M27 / M29 同——只新增 test（+ 一個 normalization helper + 兩個 harvester）。converter / 三支 checker / hook / CI workflow / README 本身 / `.gitattributes` 全部沒改；77 個 `.py` sibling 零變動（`git diff --stat` 只有 `test_readme.py` 一支）
- 負向驗證（證明 guard 真的會咬，兩個方向）：
  - monkeypatch `_documented_ci_trigger_tokens` 砍掉 `tools/**` → `test_documented_triggers_match_workflow` fail（README 漏列被抓）
  - monkeypatch `_workflow_trigger_display` 多一條 `.md` → 同 test fail（workflow 加 trigger 但 README 沒跟上被抓）
- 本地驗證：
  - `python3 -m unittest tools.tests.test_readme.ReadmeCiTriggerParityTests -v` → `Ran 6 tests OK`
  - `python3 tools/tests/test_readme.py` → `Ran 29 tests OK`（M24 後 23 + M30 6）
  - `python3 -m unittest discover -s tools/tests` → `Ran 216 tests OK`（M29 210 + M30 6）
  - `python3 tools/check_all.py --quiet` → 4 steps 全 PASS、exit 0
  - `git diff --stat` → 僅 `tools/tests/test_readme.py`，無 `.py` sibling 變動

#### 用法
```bash
# 只跑 M30 新增的 class
python3 -m unittest tools.tests.test_readme.ReadmeCiTriggerParityTests -v
```

#### 副作用 / 注意
- 若日後新增一條 user-facing trigger path（例如 `.gitattributes` 真的納入觸發），M29 會要求更新 `_EXPECTED_TRIGGER_PATHS` + workflow 兩個 event，M30 會再要求**同 commit 更新 README intro 句子**——這正是 M30 要鎖的不變量（文件不准落後於 workflow）
- `_display_trigger` 對「workflow 自我參照路徑」回 None 是刻意的：那是 CI 內部實作細節、非使用者要理解的觸發面。若日後決定要讓文件也明示「改 workflow 本身也會觸發 CI」，需同步放寬 `_display_trigger` 並翻轉 test 6

### M31 — `_sanitize_code` 字串感知 magic 偵測（修掉 triple-quoted string 內 `!`/`%`/`?` 行被誤註解的 latent bug）
- 為什麼補：M28 收緊了 `?`-**suffix** help（`obj?` / `df.head?`）的偵測、修掉 trailing-`?` 合法行被整行註解的 latent bug；但同一支 `_sanitize_code` 的 **leading** `%`/`!`/`?` 判斷仍是純逐行、完全不感知字串狀態。一個 BEGIN 在 triple-quoted string 內、又恰好以 `%`/`!`/`?` 開頭（或長得像 help 參照鏈）的行會被靜默註解掉，汙染字串內容：
  - docstring / 多行字串內嵌 shell 片段：`"""\n!run this in your shell\n"""` → `!run...` 被改成 `# !run...`
  - `%`-style 格式字串：`'''\n%(name)s\n'''` → `%(name)s` 被註解
  - prose 行剛好像 help：`"""\ndf.head?\n"""` → 被當成 IPython suffix-help 註解
- 為什麼 CI 抓不到（與 M28 同款最毒處）：converter（重生 `.py`）與 sync checker（byte-for-byte 比對）**共用** `_sanitize_code`。兩邊套同一條壞規則，輸出永遠相符，sync check 與 converted check 都綠——「字串內容被靜默改寫」對所有現有守門員都是隱形的
- 解法：
  - 新增 `_advance_string_state(line, state)`：逐行回傳「行尾」的 triple-quote 狀態（`None` 或開啟的 delimiter `"""` / `'''`）。掃描時會吃掉一般單/雙引號字串（含 `\` escape）與 `#` 註解，避免它們內部的 `"""` 或 `#` 誤翻狀態。刻意做小——只需判斷「下一行是否 BEGIN 在 triple string 內」，那正是 leading `%`/`!`/`?` 屬於字串內容而非 magic 的唯一情境
  - `_sanitize_code` 改成跨行帶 `state`：只有 `state is None`（不在 triple string 內）時才套既有 magic 判斷（`startswith(('%','!','?'))` 或 `_HELP_SUFFIX_RE`），每行結束更新 `state`
- **provably byte-for-byte 安全（零 regen）**：在 production function 就位後，對全 repo 77 個 notebook 的所有 code cell 跑「shipped `_sanitize_code` vs 舊逐行規則」diff → **0** 個 cell 不同。沿用 M28「先證明收緊規則對現有 77 檔零影響」的方法論，所以 77 個 `.py` sibling 完全不動（`git diff --stat` 僅 `tools/ipynb_to_py.py` + `tools/tests/test_ipynb_to_py.py`）
- 在 `tools/tests/test_ipynb_to_py.py` 的 `SanitizeCodeTests` 補 6 個 case：
  - `test_bang_line_inside_triple_string_preserved` — `"""` 內 `!...` 行原樣保留
  - `test_percent_line_inside_triple_string_preserved` — `'''` 內 `%(name)s` 行原樣保留
  - `test_help_chain_inside_triple_string_preserved` — `"""` 內 `df.head?` 不當 help 註解
  - `test_real_magic_after_closed_triple_string_still_commented` — triple 關閉後的真 magic 仍註解（state 不外漏）
  - `test_real_magic_before_triple_string_still_commented` — triple 開啟前的真 magic 仍註解
  - `test_triple_quote_inside_normal_string_does_not_open_block` — 一般單引號字串內的 `"""` 不誤開 triple block，下一行真 magic 仍註解
- 不動其他元件：sync checker / converted-py validator / pre-commit hook / pre-push hook / CI workflow / README / `.gitattributes` 全部沒改。只動 converter（一個 helper + `_sanitize_code` 改用 state）+ 測試 + 模組 docstring
- 本地驗證：
  - `python3 -m unittest tools.tests.test_ipynb_to_py.SanitizeCodeTests` → `Ran 23 tests OK`（M28 後 17 + M31 6）
  - 零 regen proof script（shipped vs 舊規則跑 77 notebook）→ `0` cell 差異
  - `python3 -m unittest discover -s tools/tests` → `Ran 222 tests OK`（M30 216 + M31 6）
  - `python3 tools/check_all.py --quiet` → 4 steps 全 PASS、exit 0
  - `git diff --stat`（commit 前）→ 僅 `tools/ipynb_to_py.py` + `tools/tests/test_ipynb_to_py.py`，無 `.py` sibling 變動

#### 用法
```bash
# 只跑 M31 相關 class
python3 -m unittest tools.tests.test_ipynb_to_py.SanitizeCodeTests -v
```

#### 副作用 / 注意
- `_advance_string_state` 是「足夠用」而非完整 Python tokenizer：它不處理 f-string 內的 `{...}` 巢狀、行接續 `\`、或 `"""` 與 `#` 在極端混用下的所有組合。但它的職責很窄（判斷「下一行是否在 triple string 內」），且零-regen proof 已證明對現有全 repo 行為與舊規則完全一致；若日後某 notebook 觸發到未涵蓋的 edge case，sync check 會以 DRIFT 形式紅出來（不會像舊 bug 那樣靜默），屆時再補 tokenizer 級處理即可

### M32 — `check_converted_py._magic_check` 字串感知化（修掉 M31 留下的 validator 端 latent false-positive bug）
- 為什麼補：M31 把 converter 的 `_sanitize_code` 改成 string-aware——triple-quoted string 內以 `!`/`%`/`?` 開頭的行（docstring 內嵌的 shell 片段 `!run this`、`%`-template `%(name)s`、prose `?help`）會被**正確保留 verbatim**。converter 與 sync checker 共用 `_sanitize_code`，所以那兩支對「什麼算 magic」是一致的。**但** toolchain 對 magic 的偵測其實有**三份**：converter / sync checker 共用的 `_sanitize_code`、以及 `check_converted_py.py` 的 `_magic_check`——後者是**獨立**重寫的純逐行 `MAGIC_RE.match(line.lstrip())`，完全不感知字串狀態，M31 沒碰它。結果：converter 正確保留的 in-string magic 行，會被 validator 當成「magic leak」報出來，CI 紅。這跟 M28（trailing-`?` 誤註解）、M31（leading magic 誤註解字串內容）是**同款 latent bug**，只是這次落在 validator 端、症狀是 false-positive 而非 corruption
- 為什麼這是 M31 的直接 follow-up：M31 統一了 converter+sync 的 magic 規則，卻把第三支（validator）留在舊規則上，等於把「規則一致性」這個不變量打開了一個新缺口。一旦有人在某 notebook 的 docstring 寫了 `!...` / `%...` / `?...` 行，sync check 會綠（converter 保留、磁碟 `.py` 相符）、py_compile 會綠（那是合法字串內容），唯獨 `_magic_check` 會紅——一個明明正確的轉換被擋在 CI
- Probe 實證（修前）：一個 code cell 為 `x = """\n!run this in your shell\n%(name)s\n"""\ny = 1` 的 notebook → converter 產出合法 `.py`（py_compile 過）、但 `check_converted_py` 報「Magic-line leaks: 1」、列出 line 8 `!run...` / line 9 `%(name)s`、exit 2
- 解法：`_magic_check` **復用** converter 的 `_advance_string_state`（`HERE` 加進 `sys.path` 後 `from ipynb_to_py import _advance_string_state`，與 sync checker 復用 `convert_to_str`、M22/M29 復用 workflow parser 同款「單一真理來源」形式，不另寫一份字串掃描器）。逐行帶 `state`，只在 `state is None`（不在 triple string 內）時才套既有 `MAGIC_RE.match(line.lstrip())`，每行尾更新 state。掃的是**整個生成 `.py`**（含 HEADER comment、`# %%` cell marker、markdown 的 `# ` comment block）——這些都是 `#` 開頭，`_advance_string_state` 命中 `#` 即回 None，不會誤翻狀態；跨 cell 線性追蹤等價於 converter 的 per-cell（每個能 compile 的 cell 三引號必平衡，state 在 cell 尾回 None）
- **provably 零行為變動（零 regen，CI 維持綠）**：production 改好後，對全 repo 77 個 paired `.py` 跑「舊 naive scan vs 新 string-aware scan」→ 兩者各 flag **0** 行、**0** 檔差異（M31 已證明目前無任何 in-string magic 行）。所以這支 validator 對現有 repo 的判定完全不變、真正的 top-level magic leak 仍照抓（sanity：`!ls` 在頂層仍被 flag + py_compile 同步擋下）
- 在 `tools/tests/test_check_converted_py.py` 的 `MagicCheckTests` 補 6 個 case（鏡像 M31 的 `SanitizeCodeTests`）：
  - `test_bang_line_inside_triple_string_not_flagged` — `"""` 內 `!run this` 不報
  - `test_percent_line_inside_triple_string_not_flagged` — `'''` 內 `%(name)s` 不報
  - `test_question_line_inside_triple_string_not_flagged` — `"""` 內 `?help text` 不報
  - `test_real_magic_after_closed_triple_string_still_flagged` — triple 關閉後的真 `!ls` 仍報（state 不外漏）
  - `test_real_magic_before_triple_string_still_flagged` — triple 開啟前的真 `!ls` 仍報
  - `test_triple_quote_inside_normal_string_does_not_open_block` — 一般單引號字串內的 `"""` 不誤開 block，下一行真 magic 仍報
- 不動其他元件：converter / sync checker / pre-commit / pre-push hook / CI workflow / README / `.gitattributes` 全部沒改。只動 validator（一個 import + `_magic_check` 改用 state）+ 測試 + 模組 docstring（`git diff --stat` 僅 `tools/check_converted_py.py` + `tools/tests/test_check_converted_py.py`，無 `.py` sibling 變動）
- 本地驗證：
  - `python3 -m unittest tools.tests.test_check_converted_py.MagicCheckTests -v` → `Ran 12 tests OK`（原 6 + M32 6）
  - 零-行為-變動 proof script（77 個 paired `.py`，old vs new scan）→ old 0 行 / new 0 行 / 0 檔差異
  - probe（修後）→ 同一 docstring notebook 現在 `Magic-line leaks: 0`、exit 0；頂層 `!ls` sanity 仍 exit 2
  - `python3 -m unittest discover -s tools/tests` → `Ran 228 tests OK`（M31 222 + M32 6）
  - `python3 tools/check_all.py --quiet` → 4 steps 全 PASS、exit 0
  - `git diff --stat` → 僅 `tools/check_converted_py.py` + `tools/tests/test_check_converted_py.py`，無 `.py` sibling 變動

#### 用法
```bash
# 只跑 M32 相關 class
python3 -m unittest tools.tests.test_check_converted_py.MagicCheckTests -v
```

#### 副作用 / 注意
- 現在 toolchain 三支 magic 偵測中有兩支（converter `_sanitize_code`、validator `_magic_check`）都已 string-aware 且共用 `_advance_string_state`；唯一差別是 converter 還多了 `_HELP_SUFFIX_RE`（suffix-help `df.head?`），validator 的 `MAGIC_RE` 只認 leading `!`/`%`/`?`——這是刻意的：validator 只需擋住「漏網的、會讓 `.py` 無法 compile 的 magic」，而 leading magic 才會造成 SyntaxError；suffix-help `df.head?` 在頂層也是 SyntaxError，但會以 `?` 結尾而非開頭，py_compile 那關仍會擋下，故 validator 不重複偵測
- 與 M31 的 `_advance_string_state` 共用同一個「足夠用而非完整 tokenizer」限制；但職責同樣很窄、且零-行為-變動 proof 已鎖住現有 repo，未涵蓋的 edge case 會以 compile failure / DRIFT 形式紅出來而非靜默
